from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationRecordV1, SecurityTypeCountV1
from tip_api.contracts.market_data.v2.dashboard_universe_activation import DashboardUniverseActivationRecordV2
from tip_api.persistence.parquet import dashboard_universe_activation as v1repo
from tip_api.persistence.parquet import dashboard_universe_activation_active as repo
from tip_api.services import dashboard_universe_activation_v2_cli as cli
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.universe_pre_activation import membership_fingerprint


SESSION = date(2026, 8, 19)
AT = datetime(2026, 8, 20, tzinfo=UTC)
SHA = "a" * 64
SOURCE_SHA = "b" * 64
FORM_SHA = "c" * 64
IDS = (
    UUID("00000000-0000-5000-8000-500000000001"),
    UUID("00000000-0000-5000-8000-500000000002"),
    UUID("00000000-0000-5000-8000-500000000003"),
)


def _v1_records():
    common = frozenset(IDS[:2]); broad = frozenset(IDS)
    def row(universe_id, uid, members, composition, default):
        return DashboardUniverseActivationRecordV1(
            activation_id=UUID(uid), analysis_session=SESSION,
            membership_evidence_as_of=date(2026, 8, 14), activated_at=AT,
            universe_id=universe_id, display_name="fixture", long_display_name="fixture",
            description="fixture", is_default=default, member_count=len(members),
            security_type_composition=tuple(SecurityTypeCountV1(provider_type_code=k, count=v) for k, v in composition.items()),
            membership_fingerprint=membership_fingerprint(members),
            trailing_liquidity_source_fingerprint=SHA, reviewed_override_source_fingerprint=SHA,
            pre_activation_review_fingerprint=SHA, current_eod_fingerprint=SHA,
            previous_eod_fingerprint=SHA, legacy_rollback_reference="market-data/snapshots/legacy",
            limitations=("fixture",),
        )
    return (
        row(CANDIDATE_A_ID, "00000000-0000-5000-8000-500000000010", common, {"CS": 2}, True),
        row(v1repo.PUBLIC_SECONDARY_ID, "00000000-0000-5000-8000-500000000011", broad, {"CS": 2, "ADRC": 1}, False),
    ), {CANDIDATE_A_ID: common, v1repo.PUBLIC_SECONDARY_ID: broad}


def _v2_records():
    common = frozenset(IDS[:2]); broad = frozenset(IDS)
    def row(universe_id, uid, members, composition, default):
        return DashboardUniverseActivationRecordV2(
            activation_id=UUID(uid), analysis_session=SESSION,
            membership_evidence_as_of=date(2026, 8, 14), activated_at=AT,
            universe_id=universe_id, display_name="fixture", long_display_name="fixture",
            description="fixture", is_default=default, member_count=len(members),
            security_type_composition=tuple(SecurityTypeCountV1(provider_type_code=k, count=v) for k, v in composition.items()),
            membership_fingerprint=membership_fingerprint(members),
            source_publication_fingerprint=SOURCE_SHA,
            trailing_liquidity_source_fingerprint=SHA,
            reviewed_security_form_fingerprint=FORM_SHA,
            current_eod_fingerprint=SHA, previous_eod_fingerprint=SHA,
            legacy_rollback_reference=f"{repo.V1_LOGICAL_BASE}/analysis_session={SESSION}",
            limitations=("fixture",),
        )
    return (
        row(CANDIDATE_A_ID, "00000000-0000-5000-8000-500000000020", common, {"CS": 2}, True),
        row(v1repo.PUBLIC_SECONDARY_ID, "00000000-0000-5000-8000-500000000021", broad, {"CS": 2, "ADRC": 1}, False),
    )


def _sources(monkeypatch, tmp_path):
    values, members = _v1_records()
    review = SimpleNamespace(manifest=SimpleNamespace(
        logical_content_fingerprint=SHA, legacy_count=3, legacy_membership_fingerprint=SHA,
        review_dataset=SimpleNamespace(dataset_path="fixture"), override_dataset=SimpleNamespace(record_count=2),
    ))
    monkeypatch.setattr(v1repo, "read_completed_universe_review", lambda *a, **k: review)
    monkeypatch.setattr(v1repo, "_read_review_members", lambda *a, **k: {
        CANDIDATE_A_ID: members[CANDIDATE_A_ID], CANDIDATE_B_ID: members[v1repo.PUBLIC_SECONDARY_ID],
    })
    v1repo.ParquetDashboardUniverseActivationRepository(tmp_path).publish(
        records=values, legacy_count=3, legacy_fingerprint=SHA,
        trailing_window_start=date(2026, 7, 22), trailing_window_end=date(2026, 8, 18),
        trailing_window_session_count=20, reviewed_override_count=2, activated_at=AT,
    )
    memberships = tuple(
        SimpleNamespace(policy_id=policy, instrument_id=instrument, provider_type_code=("ADRC" if instrument == IDS[2] else "CS"))
        for policy, selected in ((FULL_BASE_A_ID, IDS[:2]), (FULL_BASE_B_ID, IDS))
        for instrument in selected
    )
    source = SimpleNamespace(
        manifest=SimpleNamespace(
            logical_content_fingerprint=SOURCE_SHA,
            reviewed_security_form_dataset=SimpleNamespace(content_fingerprint=FORM_SHA),
        ),
        memberships=memberships,
    )
    monkeypatch.setattr(repo, "read_completed_superseding_full_base", lambda *a, **k: source)
    monkeypatch.setattr(repo, "superseding_target_path", lambda root, session: root / "source")
    inspected = SimpleNamespace(content_fingerprint=SHA)
    monkeypatch.setattr(repo, "CanonicalEodReadRepository", lambda root: SimpleNamespace(inspect_session=lambda session: inspected))
    monkeypatch.setattr(repo, "EXPECTED_SOURCE_FINGERPRINT", SOURCE_SHA)
    monkeypatch.setattr(repo, "EXPECTED_PRIMARY_COUNT", 2)
    monkeypatch.setattr(repo, "EXPECTED_PRIMARY_FINGERPRINT", membership_fingerprint(frozenset(IDS[:2])))
    monkeypatch.setattr(repo, "EXPECTED_SECONDARY_COUNT", 3)
    monkeypatch.setattr(repo, "EXPECTED_SECONDARY_FINGERPRINT", membership_fingerprint(frozenset(IDS)))
    return values


def _publish(monkeypatch, tmp_path, *, failpoint=None):
    _sources(monkeypatch, tmp_path)
    current = v1repo.read_completed_dashboard_universe_activation(tmp_path, analysis_session=SESSION)
    return repo.ParquetDashboardUniverseActivationV2Repository(tmp_path).publish_and_activate(
        records=_v2_records(), source_publication_path="source",
        source_publication_fingerprint=SOURCE_SHA, reviewed_security_form_fingerprint=FORM_SHA,
        legacy_member_count=3, legacy_membership_fingerprint=SHA,
        trailing_window_start=date(2026, 7, 22), trailing_window_end=date(2026, 8, 18),
        trailing_window_session_count=20, reviewed_override_count=2, reviewed_security_form_count=1,
        activated_at=AT, expected_current_fingerprint=current.manifest.logical_content_fingerprint,
        failpoint=failpoint,
    )


def test_v1_no_pointer_compatibility(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    assert repo.read_dashboard_universe_activation_pointer(tmp_path) is None
    active = repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION)
    assert active.manifest.policy_version == "dashboard-universe-v1"


def test_v2_atomic_publication_pointer_and_formal_reread(monkeypatch, tmp_path):
    result = _publish(monkeypatch, tmp_path)
    assert result.target_path.is_dir() and result.pointer_path.is_file()
    active = repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION)
    assert active.manifest.policy_version == "dashboard-universe-v2"
    assert active.select(None)[0].universe_id == CANDIDATE_A_ID
    assert not tuple(tmp_path.rglob("*staging*"))


def test_crash_before_target_rename_cleans_everything(monkeypatch, tmp_path):
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="before target"):
        _publish(monkeypatch, tmp_path, failpoint="before_target_rename")
    assert not repo.v2_target_path(tmp_path, SESSION).exists()
    assert not repo.active_pointer_path(tmp_path).exists()
    assert not tuple(tmp_path.rglob("*staging*"))


def test_crash_after_target_publish_keeps_inactive_immutable_target(monkeypatch, tmp_path):
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="after target"):
        _publish(monkeypatch, tmp_path, failpoint="after_target_publish")
    assert repo.v2_target_path(tmp_path, SESSION).is_dir()
    assert not repo.active_pointer_path(tmp_path).exists()
    assert repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION).manifest.policy_version == "dashboard-universe-v1"


def test_crash_after_pointer_is_detectable_as_active(monkeypatch, tmp_path):
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="after pointer"):
        _publish(monkeypatch, tmp_path, failpoint="after_pointer_switch")
    assert repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION).manifest.policy_version == "dashboard-universe-v2"


def test_existing_and_partial_target_rejected(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    repo.v2_target_path(tmp_path, SESSION).mkdir(parents=True)
    current = v1repo.read_completed_dashboard_universe_activation(tmp_path, analysis_session=SESSION)
    with pytest.raises(repo.DashboardUniverseActivationV2ConflictError, match="already exists"):
        repo.ParquetDashboardUniverseActivationV2Repository(tmp_path).publish_and_activate(
            records=_v2_records(), source_publication_path="source", source_publication_fingerprint=SOURCE_SHA,
            reviewed_security_form_fingerprint=FORM_SHA, legacy_member_count=3, legacy_membership_fingerprint=SHA,
            trailing_window_start=date(2026, 7, 22), trailing_window_end=date(2026, 8, 18),
            trailing_window_session_count=20, reviewed_override_count=2, reviewed_security_form_count=1,
            activated_at=AT, expected_current_fingerprint=current.manifest.logical_content_fingerprint,
        )


def test_preflight_rejects_staging_residue(tmp_path):
    parent = repo.v2_target_path(tmp_path, SESSION).parent
    parent.mkdir(parents=True)
    (parent / f".{repo.v2_target_path(tmp_path, SESSION).name}.staging-fixture").mkdir()
    with pytest.raises(repo.DashboardUniverseActivationV2ConflictError, match="staging residue"):
        repo.validate_activation_v2_preflight(tmp_path, SESSION)


def test_bad_pointer_fails_closed_without_v1_fallback(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    path = repo.active_pointer_path(tmp_path); path.parent.mkdir(parents=True); path.write_text("{}")
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="malformed"):
        repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION)


def test_pointer_fingerprint_and_path_traversal_fail_closed(monkeypatch, tmp_path):
    _publish(monkeypatch, tmp_path)
    path = repo.active_pointer_path(tmp_path)
    payload = json.loads(path.read_text())
    payload["default_universe_id"] = v1repo.PUBLIC_SECONDARY_ID
    path.write_text(json.dumps(payload))
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="fingerprint"):
        repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION)
    reference = payload["active"]
    reference["logical_path"] = "../escape"
    with pytest.raises(ValueError):
        repo.DashboardUniverseActivationPointerV1.model_validate(payload)


def test_wrong_approved_membership_fingerprint_rejected(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    bad = list(_v2_records())
    bad[0] = bad[0].model_copy(update={"membership_fingerprint": "d" * 64})
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="approved membership"):
        repo._validate_v2_records(tuple(bad), None)


def test_source_fingerprint_mismatch_rejected(monkeypatch, tmp_path):
    _publish(monkeypatch, tmp_path)
    bad = SimpleNamespace(
        manifest=SimpleNamespace(logical_content_fingerprint="d" * 64, reviewed_security_form_dataset=SimpleNamespace(content_fingerprint=FORM_SHA)),
        memberships=(),
    )
    monkeypatch.setattr(repo, "read_completed_superseding_full_base", lambda *a, **k: bad)
    with pytest.raises(repo.DashboardUniverseActivationV2Error, match="source publication"):
        repo.read_completed_dashboard_universe_activation_v2(tmp_path, analysis_session=SESSION)


def test_rollback_is_separate_atomic_pointer_switch(monkeypatch, tmp_path):
    _publish(monkeypatch, tmp_path)
    before = repo.read_dashboard_universe_activation_pointer(tmp_path)
    replacement = repo.rollback_active_dashboard_universe_activation(
        tmp_path, analysis_session=SESSION,
        expected_active_fingerprint=before.active.logical_content_fingerprint, switched_at=AT,
    )
    assert replacement.active.target_schema_version == "1.0"
    assert replacement.rollback.target_schema_version == "2.0"
    assert repo.read_active_dashboard_universe_activation(tmp_path, analysis_session=SESSION).manifest.policy_version == "dashboard-universe-v1"


def test_concurrent_lock_rejected(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    with repo._exclusive_activation_lock(tmp_path):
        with pytest.raises(repo.DashboardUniverseActivationV2ConflictError, match="in progress"):
            repo.ParquetDashboardUniverseActivationV2Repository(tmp_path).publish_and_activate(
                records=_v2_records(), source_publication_path="source", source_publication_fingerprint=SOURCE_SHA,
                reviewed_security_form_fingerprint=FORM_SHA, legacy_member_count=3, legacy_membership_fingerprint=SHA,
                trailing_window_start=date(2026, 7, 22), trailing_window_end=date(2026, 8, 18),
                trailing_window_session_count=20, reviewed_override_count=2, reviewed_security_form_count=1,
                activated_at=AT, expected_current_fingerprint=SHA,
            )


def test_cli_dry_run_zero_write_and_argument_boundary(monkeypatch, tmp_path, capsys):
    values = _v2_records()
    plan = cli.ActivationV2Plan(values, "source", SOURCE_SHA, FORM_SHA, 3, SHA, 2, 1, AT, SHA, "v1_compatibility_fallback")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "_prepare_plan", lambda: plan)
    assert cli.main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "dry_run_ready"
    assert not tuple(tmp_path.rglob("*"))
    assert cli.main(["--bad"]) == 2
    assert cli.main(["--apply", "extra"]) == 2


def test_cli_apply_success_path_returns_zero(monkeypatch, tmp_path, capsys):
    values = _v2_records()
    plan = cli.ActivationV2Plan(values, "source", SOURCE_SHA, FORM_SHA, 3, SHA, 2, 1, AT, SHA, "v1_compatibility_fallback")
    published = SimpleNamespace(content_fingerprint=SHA, parquet_sha256=SHA, logical_content_fingerprint=SOURCE_SHA, pointer_content_fingerprint=FORM_SHA)
    completed = SimpleNamespace(manifest=SimpleNamespace(logical_content_fingerprint=SOURCE_SHA))
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "_prepare_plan", lambda: plan)
    monkeypatch.setattr(cli, "ParquetDashboardUniverseActivationV2Repository", lambda root: SimpleNamespace(publish_and_activate=lambda **kwargs: published))
    monkeypatch.setattr(cli, "read_completed_dashboard_universe_activation_v2", lambda *a, **k: completed)
    monkeypatch.setattr(cli, "read_active_dashboard_universe_activation", lambda *a, **k: completed)
    assert cli.main(["--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
