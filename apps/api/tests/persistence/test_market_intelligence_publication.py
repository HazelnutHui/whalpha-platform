from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tip_api.config import AppConfig
from tip_api.contracts.analytics.v1 import (
    MarketIntelligenceActivationSourceV1,
    MarketIntelligenceEodSourceV1,
    MarketIntelligenceSourceBindingV1,
)
from tip_api.main import create_app
from tip_api.persistence.parquet import market_intelligence_active as repo
from tip_api.services import market_intelligence_publication_cli as cli
from tip_api.services.market_regime_preview import _fingerprint, _write_and_read_bundle
from tests.services.test_market_regime_preview import PRIMARY, SECONDARY, SESSION, _payload


AT = datetime(2026, 8, 25, 11, tzinfo=UTC)
STATE = "c" * 64


def _source(payload):
    return MarketIntelligenceSourceBindingV1(
        eod=MarketIntelligenceEodSourceV1(
            dataset_path="market-data/eod-price-bars/schema_version=1/session_date=2026-08-21",
            session_date=SESSION,
            record_count=9941,
            content_fingerprint="1" * 64,
            business_key_fingerprint="2" * 64,
            parquet_sha256="3" * 64,
            manifest_sha256="4" * 64,
            identity_logical_fingerprint="5" * 64,
            history_first_session=date(2026, 7, 17),
            history_last_session=SESSION,
            history_session_count=26,
            history_source_fingerprint="6" * 64,
        ),
        activation=MarketIntelligenceActivationSourceV1(
            pointer_fingerprint="7" * 64,
            logical_fingerprint="8" * 64,
            universes=tuple(item.definition for item in payload.universes),
        ),
        phase_logical_fingerprints=payload.source_logical_fingerprints,
        preview_payload_logical_fingerprint=payload.logical_fingerprint,
        preview_payload_sha256="9" * 64,
        preview_manifest_sha256="a" * 64,
        preview_generated_at=AT,
    )


def _setup(monkeypatch, tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir(mode=0o700)
    monkeypatch.setattr(
        "tip_api.services.market_regime_preview._safe_new_output_dir", lambda path: path
    )
    monkeypatch.setattr(
        "tip_api.services.market_regime_preview._safe_bundle_dir", lambda path: path
    )
    base = _payload()
    candidate_payload = base.model_copy(
        update={"relationship_history": tuple(base.relationship_history) * 21}
    )
    payload = candidate_payload.model_copy(
        update={
            "logical_fingerprint": _fingerprint(
                candidate_payload.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        }
    )
    preview = _write_and_read_bundle(preview_dir, payload, AT, payload.source_logical_fingerprints)
    source = _source(payload)
    monkeypatch.setattr(repo, "validate_source_binding", lambda **kwargs: (source, preview))
    candidate_parent = tmp_path / "approval"
    candidate_parent.mkdir(mode=0o700)
    candidate = repo.build_market_intelligence_candidate(
        data_root=root,
        analysis_session=SESSION,
        publication_id="2026-08-21T110000Z-abcdef0",
        generated_at=AT,
        preview_bundle_path=preview_dir,
        phase1a_audit_path=tmp_path / "phase1a",
        phase1b_audit_path=tmp_path / "phase1b",
        phase2_audit_path=tmp_path / "phase2",
        candidate_path=candidate_parent / "market-intelligence.plan.artifacts",
    )
    monkeypatch.setattr(repo, "inventory_fingerprint", lambda *args, **kwargs: STATE)
    plan = repo.build_approval_plan(
        root=root,
        candidate=candidate.path,
        preview_bundle_path=preview_dir,
        phase1a_audit_path=tmp_path / "phase1a",
        phase1b_audit_path=tmp_path / "phase1b",
        phase2_audit_path=tmp_path / "phase2",
        expected_current_state_fingerprint=STATE,
        expected_latest_completed_session=SESSION,
        actual_latest_completed_session=SESSION,
        freshness_status="fresh",
        session_lag=0,
        created_at=AT,
    )
    monkeypatch.setattr(repo, "_validate_plan_sources", lambda *args, **kwargs: None)
    monkeypatch.setattr(repo, "_validate_completed_source_binding", lambda *args, **kwargs: None)
    return root, candidate, plan


def test_candidate_reader_is_language_neutral_deterministic_and_strict(monkeypatch, tmp_path):
    root, candidate, plan = _setup(monkeypatch, tmp_path)
    assert candidate.payload.language_neutral is True
    assert candidate.payload.supported_interface_locales == ("en", "zh")
    assert tuple(item.definition.universe_id for item in candidate.payload.analytics.universes) == (
        PRIMARY,
        SECONDARY,
    )
    assert len(candidate.payload.analytics.relationships) == 16
    assert len(candidate.payload.analytics.relationship_history) == 336
    assert plan.payload_sha256 == candidate.manifest.payload_sha256
    extra = candidate.path / "extra.json"
    extra.write_text("{}\n")
    extra.chmod(0o400)
    with pytest.raises(repo.MarketIntelligencePublicationError, match="extras"):
        repo.read_market_intelligence_release(candidate.path)


def test_atomic_publish_reread_replay_and_rollback_boundary(monkeypatch, tmp_path):
    root, _, plan = _setup(monkeypatch, tmp_path)
    result = repo.publish_and_activate(
        root=root,
        plan=plan,
        expected_current_state_fingerprint=STATE,
        freshness_validator=lambda: None,
    )
    assert result.pointer is not None
    assert result.pointer.pointer_content_fingerprint == plan.planned_pointer_fingerprint
    assert result.payload.analytics.logical_fingerprint == plan.analytics_logical_fingerprint
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="changed|exists"):
        repo.publish_and_activate(
            root=root, plan=plan, expected_current_state_fingerprint=STATE
        )
    with pytest.raises(repo.MarketIntelligenceUnavailable, match="no prior"):
        repo.rollback(
            root=root,
            expected_active_pointer_fingerprint=result.pointer.pointer_content_fingerprint,
            apply=True,
        )


def test_crash_before_target_is_zero_write_and_after_target_recovers(monkeypatch, tmp_path):
    root, _, plan = _setup(monkeypatch, tmp_path)
    with pytest.raises(repo.MarketIntelligencePublicationError, match="before target"):
        repo.publish_and_activate(
            root=root,
            plan=plan,
            expected_current_state_fingerprint=STATE,
            failpoint="before_target_rename",
        )
    assert not Path(plan.target_path).exists()
    assert repo.read_market_intelligence_pointer(root) is None
    with pytest.raises(repo.MarketIntelligencePublicationError, match="after target"):
        repo.publish_and_activate(
            root=root,
            plan=plan,
            expected_current_state_fingerprint=STATE,
            failpoint="after_target_rename",
        )
    before = {
        item.name: item.read_bytes() for item in Path(plan.target_path).iterdir() if item.is_file()
    }
    result = repo.verify_then_link(
        root=root,
        plan=plan,
        expected_current_state_fingerprint=STATE,
        freshness_validator=lambda: None,
    )
    after = {
        item.name: item.read_bytes() for item in Path(plan.target_path).iterdir() if item.is_file()
    }
    assert before == after
    assert result.pointer is not None


def test_tamper_state_symlink_partial_and_stale_fail_closed(monkeypatch, tmp_path):
    root, _, plan = _setup(monkeypatch, tmp_path)
    tampered = plan.model_copy(update={"payload_sha256": "f" * 64})
    with pytest.raises(repo.MarketIntelligencePublicationError, match="plan fingerprint"):
        repo.publish_and_activate(root=root, plan=tampered, expected_current_state_fingerprint=STATE)
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="differs"):
        repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint="e" * 64)
    stale_body = plan.model_dump(mode="json", exclude={"plan_content_fingerprint"})
    stale_body["activation_allowed"] = False
    stale = type(plan).model_validate(
        {**stale_body, "plan_content_fingerprint": repo.canonical_fingerprint(stale_body)}
    )
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="freshness"):
        repo.publish_and_activate(root=root, plan=stale, expected_current_state_fingerprint=STATE)
    target = Path(plan.target_path)
    target.parent.mkdir(parents=True)
    target.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(Exception, match="target|symlink"):
        repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint=STATE)


def test_source_change_and_partial_target_are_zero_write_rejections(monkeypatch, tmp_path):
    root, _, plan = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        repo,
        "_validate_plan_sources",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            repo.MarketIntelligencePublicationConflict("approved source binding changed")
        ),
    )
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="source"):
        repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint=STATE)
    assert not Path(plan.target_path).exists()
    monkeypatch.setattr(repo, "_validate_plan_sources", lambda *args, **kwargs: None)
    target = Path(plan.target_path)
    target.mkdir(parents=True)
    (target / "partial").write_text("partial")
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="target"):
        repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint=STATE)


@pytest.mark.parametrize("failing_call", (1, 2, 3, 4, 5))
def test_fsync_fault_matrix_has_unambiguous_recovery(monkeypatch, tmp_path, failing_call):
    root, _, plan = _setup(monkeypatch, tmp_path)
    original = repo._fsync_directory
    calls = 0

    def fail_at(path):
        nonlocal calls
        calls += 1
        if calls == failing_call:
            raise OSError(f"fsync fault {failing_call}")
        return original(path)

    monkeypatch.setattr(repo, "_fsync_directory", fail_at)
    with pytest.raises(OSError, match="fsync fault"):
        repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint=STATE)
    assert not tuple(root.rglob("*.staging-*"))
    target_exists = Path(plan.target_path).exists()
    pointer_exists = Path(plan.pointer_path).exists()
    assert (target_exists, pointer_exists) in {(False, False), (True, False), (True, True)}
    if pointer_exists:
        assert repo.read_market_intelligence_pointer(root) is not None


def test_second_release_rollback_dry_run_and_apply_use_approved_digest(monkeypatch, tmp_path):
    root, first_candidate, first_plan = _setup(monkeypatch, tmp_path)
    first = repo.publish_and_activate(
        root=root, plan=first_plan, expected_current_state_fingerprint=STATE
    )
    second_candidate = repo.build_market_intelligence_candidate(
        data_root=root,
        analysis_session=SESSION,
        publication_id="2026-08-21T120000Z-abcdef0",
        generated_at=AT.replace(hour=12),
        preview_bundle_path=tmp_path / "preview",
        phase1a_audit_path=tmp_path / "phase1a",
        phase1b_audit_path=tmp_path / "phase1b",
        phase2_audit_path=tmp_path / "phase2",
        candidate_path=tmp_path / "approval" / "second.plan.artifacts",
    )
    second_plan = repo.build_approval_plan(
        root=root,
        candidate=second_candidate.path,
        preview_bundle_path=tmp_path / "preview",
        phase1a_audit_path=tmp_path / "phase1a",
        phase1b_audit_path=tmp_path / "phase1b",
        phase2_audit_path=tmp_path / "phase2",
        expected_current_state_fingerprint=STATE,
        expected_latest_completed_session=SESSION,
        actual_latest_completed_session=SESSION,
        freshness_status="fresh",
        session_lag=0,
        created_at=AT.replace(hour=12),
    )
    second = repo.publish_and_activate(
        root=root, plan=second_plan, expected_current_state_fingerprint=STATE
    )
    assert second.pointer is not None and second.pointer.rollback == first.reference
    digest = second.pointer.pointer_content_fingerprint
    preview = repo.rollback(root=root, expected_active_pointer_fingerprint=digest)
    assert preview.payload.publication_id == first.payload.publication_id
    with pytest.raises(repo.MarketIntelligencePublicationConflict, match="digest"):
        repo.rollback(root=root, expected_active_pointer_fingerprint="f" * 64, apply=True)
    restored = repo.rollback(
        root=root, expected_active_pointer_fingerprint=digest, apply=True
    )
    assert restored.payload.publication_id == first.payload.publication_id


def test_fsync_and_pointer_cas_are_exercised(monkeypatch, tmp_path):
    root, _, plan = _setup(monkeypatch, tmp_path)
    calls: list[Path] = []
    original = repo._fsync_directory
    monkeypatch.setattr(
        repo, "_fsync_directory", lambda path: (calls.append(path), original(path))[1]
    )
    repo.publish_and_activate(root=root, plan=plan, expected_current_state_fingerprint=STATE)
    assert Path(plan.target_path).parent in calls
    assert Path(plan.pointer_path).parent in calls


def test_formal_route_uses_one_startup_read_and_default_is_unchanged(monkeypatch, tmp_path):
    root, candidate, _ = _setup(monkeypatch, tmp_path)
    default = TestClient(create_app(AppConfig(market_data_root=root)))
    assert default.get("/api/v1/health").status_code == 200
    assert default.get("/api/v1/private/market-regime/overview").status_code == 404
    calls = []
    monkeypatch.setattr(
        "tip_api.main.read_active_market_intelligence",
        lambda *args, **kwargs: (calls.append(1), candidate)[1],
    )
    enabled = TestClient(
        create_app(AppConfig(market_data_root=root, enable_market_intelligence_routes=True))
    )
    first = enabled.get("/api/v1/private/market-regime/overview")
    second = enabled.get(
        "/api/v1/private/market-regime/overview", params={"universe_id": SECONDARY}
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["regime"]["composite"]["regime_score"] == "63.9102"
    assert second.json()["regime"]["composite"]["regime_score"] == "64.8167"
    assert len(calls) == 1


def test_cli_naked_apply_missing_binding_wrong_sha_and_network_guard(tmp_path):
    parser_cases = (
        ["--apply", "--data-root", str(tmp_path)],
        ["--verify-then-link", "--data-root", str(tmp_path)],
        ["--rollback", "--data-root", str(tmp_path)],
    )
    for arguments in parser_cases:
        with pytest.raises(SystemExit) as error:
            cli.main(arguments)
        assert error.value.code == 2
    with cli._socket_guard():
        import socket

        with pytest.raises(repo.MarketIntelligencePublicationError, match="network"):
            socket.create_connection(("127.0.0.1", 1))


def test_cli_plan_loader_rejects_wrong_full_file_sha(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text("{}\n")
    with pytest.raises(repo.MarketIntelligencePublicationError, match="full-file"):
        cli._load_plan(plan_path, "0" * 64)


def test_config_rejects_preview_and_formal_routes_together():
    with pytest.raises(ValueError, match="mutually exclusive"):
        AppConfig(
            enable_market_regime_preview_routes=True,
            market_regime_preview_bundle=Path("/tmp/bundle"),
            enable_market_intelligence_routes=True,
        )
