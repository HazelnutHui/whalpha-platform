from __future__ import annotations

import json
import shutil
import socket
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from tip_api.ingestion.instrument_master_snapshot import (
    InstrumentMasterSnapshotQualityGates,
)
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodDiffDisposition,
    ReconciledEodSourceProvenance,
)
from tip_api.providers.massive import same_day_catchup as module
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.grouped_daily_ingestion import (
    bind_case_sensitive_provider_ticker_source,
    ingest_grouped_daily,
    load_identity_snapshot,
    process_grouped_daily_payload,
)
from tip_api.providers.massive.instrument_master_snapshot import (
    FixedIntervalRateLimiter,
    ingest_massive_instrument_master_snapshot,
)
from tip_api.providers.massive.same_day_catchup import (
    SameDayCatchupError,
    _plan_content_fingerprint,
    _read_fetch_package,
    apply_approved_plan,
    build_eod_plan,
    build_identity_plan,
    build_identity_source_plan,
    eod_main,
    fetch_eod_package,
    fetch_identity_package,
    file_sha256,
    identity_main,
    inventory_fingerprint,
    read_catchup_approval_plan_evidence,
    read_fetch_package_evidence,
    read_grouped_daily_package,
    read_identity_reference_package,
)
from tip_api.services.historical_identity_source_custody import (
    read_identity_source_custody_at_data_root,
)
from tip_api.services.market_calendar import ExchangeCalendar, evaluate_market_data_freshness
from tip_api.services.reconciled_eod_edition import (
    build_reconciled_eod_session_candidate,
)

FETCHED_AT = datetime(2026, 8, 23, 12, tzinfo=UTC)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get_json(self, path, *, params, api_key, timeout_seconds, base_url):
        assert api_key.get_secret_value() == "fixture-only"
        assert "apiKey" not in params and "apikey" not in params
        self.calls.append((path, dict(params), base_url))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def reference_record(index: int, session: date) -> dict[str, object]:
    ticker = f"T{index:05d}"
    return {
        "ticker": ticker,
        "name": f"{ticker} Holdings",
        "market": "stocks",
        "locale": "us",
        "primary_exchange": "XNYS",
        "type": "CS",
        "active": True,
        "currency_name": "usd",
        "cik": f"{index:010d}",
        "composite_figi": f"COMP{index:08d}",
        "share_class_figi": f"SHARE{index:08d}",
        "last_updated_utc": f"{session.isoformat()}T20:00:00Z",
    }


def reference_pages(session: date, count: int = 5001):
    rows = [reference_record(index, session) for index in range(count)]
    return (
        {
            "results": rows[:3000],
            "next_url": (
                "https://api.massive.com/v3/reference/tickers"
                f"?cursor=page2&date={session.isoformat()}"
            ),
        },
        {"results": rows[3000:]},
    )


def grouped_payload(session: date, count: int = 5001, **override):
    timestamp = int(
        datetime(
            session.year,
            session.month,
            session.day,
            12,
            tzinfo=ZoneInfo("America/New_York"),
        ).timestamp()
        * 1000
    )
    rows = [
        {
            "T": f"T{index:05d}",
            "o": "10.00",
            "h": "12.00",
            "l": "9.00",
            "c": "11.00",
            "v": "1000.5",
            "vw": "10.50",
            "n": 25,
            "t": timestamp,
        }
        for index in range(count)
    ]
    if override:
        rows[0].update(override)
    return {"results": rows}


def no_wait_limiter() -> FixedIntervalRateLimiter:
    return FixedIntervalRateLimiter(clock=lambda: 1.0, sleeper=lambda _seconds: None)


def fetch_identity(tmp_path: Path, session: date) -> tuple[Path, FakeTransport]:
    package = tmp_path / f"identity-{session.isoformat()}"
    transport = FakeTransport(reference_pages(session))
    result = fetch_identity_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=transport,
        session_date=session,
        package_path=package,
        fetched_at=FETCHED_AT,
        rate_limiter=no_wait_limiter(),
    )
    assert result.request_count == 2
    return package, transport


def test_historical_identity_plan_can_admit_bounded_quarantined_aliases(
    tmp_path: Path,
) -> None:
    session = date(2025, 1, 22)
    pages = reference_pages(session)
    rows = pages[0]["results"] + pages[1]["results"]
    for pair_number in range(6):
        first = rows[pair_number * 2]
        second = rows[pair_number * 2 + 1]
        second["share_class_figi"] = first["share_class_figi"]
        second["composite_figi"] = first["composite_figi"]
    package = tmp_path / "historical-alias-identity"
    fetch_identity_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport(pages),
        session_date=session,
        package_path=package,
        fetched_at=FETCHED_AT,
        rate_limiter=no_wait_limiter(),
    )
    plan_path = tmp_path / "historical-alias-plan.json"
    data_root = tmp_path / "historical-alias-data"
    data_root.mkdir()

    with pytest.raises(SameDayCatchupError, match="quality gates"):
        build_identity_plan(
            package_path=package,
            plan_path=plan_path,
            data_root=data_root,
        )

    plan = build_identity_plan(
        package_path=package,
        plan_path=plan_path,
        data_root=data_root,
        quality_gates=InstrumentMasterSnapshotQualityGates(
            maximum_malformed_ratio=0.02,
            maximum_stable_identifier_collision_ratio=0.01,
        ),
    )

    assert plan.counts["malformed_rows"] == 0
    assert plan.counts["malformed_ratio_gate_ppm"] == 20_000
    assert plan.counts["stable_identifier_collision_rows"] == 12
    assert plan.counts["stable_identifier_collision_gate_ppm"] == 10_000
    assert plan.counts["instrument_rows"] == 4_989


def test_public_fetch_package_evidence_formally_rereads_without_payload(tmp_path) -> None:
    session = date(2026, 8, 21)
    package = tmp_path / "eod-evidence"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped_payload(session, count=1)]),
        session_date=session,
        package_path=package,
        fetched_at=FETCHED_AT,
    )
    evidence = read_fetch_package_evidence(
        package_path=package,
        operation="eod",
        expected_session=session,
    )
    assert evidence.request_count == 1
    assert evidence.package_type == "grouped_daily"
    assert len(evidence.package_manifest_sha256) == 64
    assert len(evidence.package_content_sha256) == 64
    assert "results" not in evidence.model_dump()

    grouped = read_grouped_daily_package(
        package_path=package,
        expected_session=session,
    )
    assert grouped.manifest.session_date == session
    assert len(grouped.payload["results"]) == 1
    assert len(grouped.package_manifest_sha256) == 64


def test_exact_persistent_session_custody_supports_fetch_and_plan_reread(
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 21)
    owner = Path("/var/tmp") / f"whalpha-daily-custody-test-{uuid4().hex}"
    workspace = owner / "daily-eod"
    sessions = workspace / "sessions"
    session_root = sessions / f"session_date={session.isoformat()}"
    for path in (owner, workspace, sessions, session_root):
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    package = session_root / "acquisition-package"
    plan_path = session_root / "canonical-apply-plan.json"
    data_root = tmp_path / "persistent-custody-data"
    data_root.mkdir()
    try:
        fetch_identity_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport(reference_pages(session)),
            session_date=session,
            package_path=package,
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )
        plan = build_identity_plan(
            package_path=package,
            plan_path=plan_path,
            data_root=data_root,
        )
        evidence = read_catchup_approval_plan_evidence(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_operation="identity",
            expected_session=session,
            expected_data_root=data_root,
        )
        assert evidence.fetch_package_path == str(package)
        assert plan_path.is_file()
        assert plan_path.with_suffix(".artifacts").is_dir()
        assert plan.plan_content_sha256 == evidence.plan_content_sha256
    finally:
        shutil.rmtree(owner)


def test_validated_identity_reference_package_exposes_only_sanitized_pages(tmp_path) -> None:
    session = date(2026, 8, 21)
    package, _ = fetch_identity(tmp_path, session)
    validated = read_identity_reference_package(
        package_path=package,
        expected_session=session,
    )

    assert validated.manifest.session_date == session
    assert len(validated.pages) == validated.manifest.request_count == 2
    assert len(validated.package_manifest_sha256) == 64
    assert all("apiKey" not in str(page) for page in validated.pages)


def test_plan_builder_reuses_a_validated_caller_state_without_rescanning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 21)
    root = tmp_path / "prevalidated-state-data"
    root.mkdir()
    package, _ = fetch_identity(tmp_path, session)
    expected_state = inventory_fingerprint(root)

    def unexpected_rescan(_root: Path) -> str:
        raise AssertionError("caller-supplied state was recomputed")

    monkeypatch.setattr(module, "inventory_fingerprint", unexpected_rescan)
    plan = build_identity_plan(
        package_path=package,
        plan_path=tmp_path / "prevalidated-state.plan.json",
        data_root=root,
        expected_current_state_fingerprint=expected_state,
    )

    assert plan.expected_current_state_fingerprint == expected_state


def plan_and_apply_identity(tmp_path: Path, root: Path, session: date):
    package, _ = fetch_identity(tmp_path, session)
    plan_path = tmp_path / f"identity-{session.isoformat()}.plan.json"
    plan = build_identity_plan(package_path=package, plan_path=plan_path, data_root=root)
    applied = apply_approved_plan(
        plan_path=plan_path,
        approved_plan_sha256=file_sha256(plan_path),
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        data_root=root,
        expected_operation="identity",
        expected_session=session,
    )
    return plan_path, applied


def test_public_approval_plan_evidence_formally_rereads_without_artifacts(
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 20)
    root = tmp_path / "plan-evidence-data"
    root.mkdir()
    package, _ = fetch_identity(tmp_path, session)
    plan_path = tmp_path / "identity-evidence.plan.json"
    plan = build_identity_plan(
        package_path=package,
        plan_path=plan_path,
        data_root=root,
    )

    evidence = read_catchup_approval_plan_evidence(
        plan_path=plan_path,
        approved_plan_sha256=file_sha256(plan_path),
        expected_operation="identity",
        expected_session=session,
        expected_data_root=root,
    )

    assert evidence.plan_content_sha256 == plan.plan_content_sha256
    assert evidence.fetch_package_path == str(package)
    assert evidence.publication_order == plan.publication_order
    assert plan.schema_version == "1.1"
    assert len(plan.publication_order) == 5
    assert len(plan.artifacts) == 9
    assert "provider-identity-reference-observation" in plan.publication_order[-2]
    assert plan.counts["source_observation_rows"] == 5001
    assert "artifacts" not in evidence.model_dump()
    assert "responses" not in evidence.model_dump()


def test_legacy_identity_plan_remains_readable_and_source_only_repair_is_append_only(
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 20)
    root = tmp_path / "legacy-data"
    root.mkdir()
    package, _ = fetch_identity(tmp_path, session)
    current_path = tmp_path / "current.plan.json"
    current = build_identity_plan(
        package_path=package,
        plan_path=current_path,
        data_root=root,
    )
    source_target = current.publication_order[-2]
    values = current.model_dump(mode="json")
    values["schema_version"] = "1.0"
    values["publication_order"] = [
        item for item in values["publication_order"] if item != source_target
    ]
    values["artifacts"] = [
        item
        for item in values["artifacts"]
        if str(Path(item["target_path"]).parent) != source_target
    ]
    values["counts"].pop("source_observation_rows")
    values["content_fingerprints"].pop("source_observation")
    values["content_fingerprints"].pop("source_custody")
    values["inventory_change_file_count"] = len(values["artifacts"])
    values["inventory_change_bytes"] = sum(
        item["size"] for item in values["artifacts"]
    )
    values["recovery_boundary"] = (
        "verify_matching_completed_components_then_publish_missing_components_and_logical_marker"
    )
    values["plan_content_sha256"] = _plan_content_fingerprint(
        {
            key: value
            for key, value in values.items()
            if key != "plan_content_sha256"
        }
    )
    legacy_path = tmp_path / "legacy.plan.json"
    legacy_path.write_text(json.dumps(values), encoding="utf-8")
    legacy_path.chmod(0o444)
    apply_approved_plan(
        plan_path=legacy_path,
        approved_plan_sha256=file_sha256(legacy_path),
        expected_current_state_fingerprint=current.expected_current_state_fingerprint,
        data_root=root,
        expected_operation="identity",
        expected_session=session,
    )
    assert not Path(source_target).exists()

    mixed_case_package = tmp_path / "legacy-mixed-case-eod"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped_payload(session, T="T00000w")]),
        session_date=session,
        package_path=mixed_case_package,
        fetched_at=FETCHED_AT,
    )
    with pytest.raises(
        SameDayCatchupError,
        match="case-sensitive Identity source evidence is unavailable",
    ):
        build_eod_plan(
            package_path=mixed_case_package,
            plan_path=tmp_path / "legacy-mixed-case-eod.plan.json",
            data_root=root,
        )

    repair_path = tmp_path / "source-repair.plan.json"
    repair = build_identity_source_plan(
        package_path=package,
        plan_path=repair_path,
        data_root=root,
    )
    assert repair.operation == "identity_source"
    assert len(repair.publication_order) == 1
    assert len(repair.artifacts) == 2
    apply_approved_plan(
        plan_path=repair_path,
        approved_plan_sha256=file_sha256(repair_path),
        expected_current_state_fingerprint=repair.expected_current_state_fingerprint,
        data_root=root,
        expected_operation="identity_source",
        expected_session=session,
    )
    source = read_identity_source_custody_at_data_root(
        data_root=root.resolve(),
        provider="massive_stocks_basic",
        session_date=session,
    )
    assert source.manifest.contract_version == (
        "historical-identity-source-custody/1.1"
    )
    assert source.manifest.point_in_time_eligibility == (
        "eligible_at_source_observed_at"
    )
    assert source.manifest.record_count == 5001
    apply_approved_plan(
        plan_path=repair_path,
        approved_plan_sha256=file_sha256(repair_path),
        expected_current_state_fingerprint=repair.expected_current_state_fingerprint,
        data_root=root,
        verify_then_complete=True,
        expected_operation="identity_source",
        expected_session=session,
    )


def test_eod_plan_binds_exact_provider_symbol_to_identity_source(
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 20)
    root = tmp_path / "case-sensitive-data"
    root.mkdir()
    pages = reference_pages(session, count=5002)
    rows = pages[0]["results"] + pages[1]["results"]
    rows[0]["ticker"] = "TPC"
    rows[1]["ticker"] = "TpC"
    rows[1]["type"] = "PFD"

    identity_package = tmp_path / "case-sensitive-identity"
    fetch_identity_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport(pages),
        session_date=session,
        package_path=identity_package,
        fetched_at=FETCHED_AT,
        rate_limiter=no_wait_limiter(),
    )
    identity_plan_path = tmp_path / "case-sensitive-identity.plan.json"
    identity_plan = build_identity_plan(
        package_path=identity_package,
        plan_path=identity_plan_path,
        data_root=root,
    )
    apply_approved_plan(
        plan_path=identity_plan_path,
        approved_plan_sha256=file_sha256(identity_plan_path),
        expected_current_state_fingerprint=(
            identity_plan.expected_current_state_fingerprint
        ),
        data_root=root,
        expected_operation="identity",
        expected_session=session,
    )

    grouped = grouped_payload(session, count=5002)
    grouped["results"][0]["T"] = "TPC"
    grouped["results"][1]["T"] = "TpC"
    eod_package = tmp_path / "case-sensitive-eod"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped]),
        session_date=session,
        package_path=eod_package,
        fetched_at=FETCHED_AT,
    )
    eod_plan = build_eod_plan(
        package_path=eod_package,
        plan_path=tmp_path / "case-sensitive-eod.plan.json",
        data_root=root,
    )

    assert eod_plan.counts["case_sensitive_provider_ticker_rows"] == 1
    assert eod_plan.counts["case_sensitive_provider_ticker_excluded_rows"] == 1
    assert eod_plan.counts["case_sensitive_provider_ticker_quarantined_rows"] == 0
    assert len(eod_plan.content_fingerprints["identity_source"]) == 64


def test_reconciled_eod_candidate_recovers_only_expected_missing_common(
    tmp_path: Path,
) -> None:
    session = date(2026, 8, 20)
    root = tmp_path / "reconciled-data"
    root.mkdir()
    pages = reference_pages(session, count=5003)
    rows = pages[0]["results"] + pages[1]["results"]
    rows[0]["ticker"] = "TPC"
    rows[1]["ticker"] = "TpC"
    rows[1]["type"] = "PFD"

    identity_package = tmp_path / "reconciled-identity"
    fetch_identity_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport(pages),
        session_date=session,
        package_path=identity_package,
        fetched_at=FETCHED_AT,
        rate_limiter=no_wait_limiter(),
    )
    identity_plan_path = tmp_path / "reconciled-identity.plan.json"
    identity_plan = build_identity_plan(
        package_path=identity_package,
        plan_path=identity_plan_path,
        data_root=root,
    )
    apply_approved_plan(
        plan_path=identity_plan_path,
        approved_plan_sha256=file_sha256(identity_plan_path),
        expected_current_state_fingerprint=(
            identity_plan.expected_current_state_fingerprint
        ),
        data_root=root,
        expected_operation="identity",
        expected_session=session,
    )

    source = read_identity_source_custody_at_data_root(
        data_root=root.resolve(),
        provider="massive_stocks_basic",
        session_date=session,
    )
    identity = bind_case_sensitive_provider_ticker_source(
        load_identity_snapshot(
            root,
            provider_id="massive_stocks_basic",
            as_of_date=session,
        ),
        source_payloads=tuple(item.source_payload() for item in source.records),
        source_fingerprint=source.manifest.logical_fingerprint,
    )
    grouped = grouped_payload(session, count=5003)
    grouped["results"][0]["T"] = "TPC"
    grouped["results"][1]["T"] = "TpC"
    base = process_grouped_daily_payload(
        {"results": grouped["results"][2:]},
        identity=identity,
        session_date=session,
        endpoint="fixture",
        data_root=root,
        ingested_at=FETCHED_AT,
        publish=True,
    )
    assert base.status == "published"
    assert base.canonical_bar_count == 5001

    eod_package = tmp_path / "reconciled-eod"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped]),
        session_date=session,
        package_path=eod_package,
        fetched_at=FETCHED_AT,
    )
    candidate = build_reconciled_eod_session_candidate(
        data_root=root.resolve(),
        package_path=eod_package,
        working_root=tmp_path / "reconciled-working",
        session_date=session,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )

    assert candidate.diff.disposition == (
        ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
    )
    assert candidate.diff.added_record_count == 1
    assert candidate.diff.unexpected_added_record_count == 0
    assert len(candidate.rebuilt_records) == 5002


def fetch_plan_apply_eod(tmp_path: Path, root: Path, session: date):
    package = tmp_path / f"eod-{session.isoformat()}"
    transport = FakeTransport([grouped_payload(session)])
    fetched = fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=transport,
        session_date=session,
        package_path=package,
        fetched_at=FETCHED_AT,
    )
    assert fetched.adjusted is False
    assert transport.calls == [
        (
            f"/v2/aggs/grouped/locale/us/market/stocks/{session.isoformat()}",
            {"adjusted": False},
            "https://api.massive.com",
        )
    ]
    plan_path = tmp_path / f"eod-{session.isoformat()}.plan.json"
    plan = build_eod_plan(package_path=package, plan_path=plan_path, data_root=root)
    apply_approved_plan(
        plan_path=plan_path,
        approved_plan_sha256=file_sha256(plan_path),
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        data_root=root,
        expected_operation="eod",
        expected_session=session,
    )
    return plan_path, plan


def test_two_session_end_to_end_and_freshness(tmp_path):
    root = tmp_path / "isolated-data"
    root.mkdir()
    for session in (date(2026, 8, 20), date(2026, 8, 21)):
        _, identity_plan = plan_and_apply_identity(tmp_path, root, session)
        identity = load_identity_snapshot(
            root, provider_id="massive_stocks_basic", as_of_date=session
        )
        assert (
            identity.manifest["snapshot_content_sha256"]
            == identity_plan.content_fingerprints["logical"]
        )
        _, eod_plan = fetch_plan_apply_eod(tmp_path, root, session)
        integrity = CanonicalEodReadRepository(root).inspect_session(session)
        assert integrity.record_count == 5001
        assert integrity.content_fingerprint == eod_plan.content_fingerprints["eod"]
        assert integrity.identity_snapshot_date == session

    sessions = CanonicalEodReadRepository(root).list_sessions()
    actual = sessions[-1].session_date
    freshness = evaluate_market_data_freshness(
        calendar=ExchangeCalendar(),
        actual_latest_completed_session=actual,
        checked_at=datetime(2026, 8, 23, 12, tzinfo=UTC),
    )
    assert actual == date(2026, 8, 21)
    assert freshness.expected_latest_completed_session == date(2026, 8, 21)
    assert freshness.session_lag == 0
    assert freshness.freshness_status.value == "fresh"
    assert not tuple(root.rglob("*.staging.*"))


def test_identity_completed_components_recover_without_overwrite(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    package, _ = fetch_identity(tmp_path, date(2026, 8, 20))
    plan_path = tmp_path / "identity.plan.json"
    plan = build_identity_plan(package_path=package, plan_path=plan_path, data_root=root)
    with pytest.raises(SameDayCatchupError, match="injected failure"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
            fail_after_target_count=3,
            expected_operation="identity",
            expected_session=date(2026, 8, 20),
        )
    logical = Path(plan.publication_order[-1])
    assert not logical.exists()
    completed_hashes = {
        item.target_path: file_sha256(Path(item.target_path))
        for item in plan.artifacts
        if Path(item.target_path).exists()
    }
    first_completed = next(Path(item.target_path) for item in plan.artifacts if Path(item.target_path).exists())
    first_ref = next(item for item in plan.artifacts if Path(item.target_path) == first_completed)
    first_completed.write_bytes(first_completed.read_bytes() + b"tamper")
    with pytest.raises(SameDayCatchupError, match="artifact mismatch"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
            verify_then_complete=True,
        )
    shutil.copyfile(first_ref.source_path, first_completed)
    unrelated = root / "unexpected-state.txt"
    unrelated.write_text("changed", encoding="utf-8")
    with pytest.raises(SameDayCatchupError, match="recovery base state changed"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
            verify_then_complete=True,
        )
    unrelated.unlink()
    apply_approved_plan(
        plan_path=plan_path,
        approved_plan_sha256=file_sha256(plan_path),
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        data_root=root,
        verify_then_complete=True,
        expected_operation="identity",
        expected_session=date(2026, 8, 20),
    )
    assert all(file_sha256(Path(path)) == digest for path, digest in completed_hashes.items())
    load_identity_snapshot(
        root, provider_id="massive_stocks_basic", as_of_date=date(2026, 8, 20)
    )


def test_tamper_and_state_change_fail_before_target(tmp_path):
    session = date(2026, 8, 20)
    root = tmp_path / "data"
    root.mkdir()
    package, _ = fetch_identity(tmp_path, session)
    plan_path = tmp_path / "identity.plan.json"
    plan = build_identity_plan(package_path=package, plan_path=plan_path, data_root=root)
    before = inventory_fingerprint(root)

    response = package / "response-01.json"
    response.chmod(0o600)
    response.write_text(response.read_text() + " ")
    with pytest.raises(SameDayCatchupError, match="package"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
        )
    assert inventory_fingerprint(root) == before

    shutil.rmtree(package)
    package, _ = fetch_identity(tmp_path, session)
    plan2_path = tmp_path / "identity2.plan.json"
    plan2 = build_identity_plan(package_path=package, plan_path=plan2_path, data_root=root)
    (root / "state-changed").write_text("x")
    with pytest.raises(SameDayCatchupError, match="current state changed"):
        apply_approved_plan(
            plan_path=plan2_path,
            approved_plan_sha256=file_sha256(plan2_path),
            expected_current_state_fingerprint=plan2.expected_current_state_fingerprint,
            data_root=root,
        )
    assert not Path(plan2.publication_order[0]).exists()


def test_grouped_wrong_date_previous_identity_and_invalid_ohlc_fail(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    plan_and_apply_identity(tmp_path, root, date(2026, 8, 20))
    wrong_package = tmp_path / "wrong-eod"
    with pytest.raises(SameDayCatchupError, match="session mismatch"):
        fetch_eod_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport([grouped_payload(date(2026, 8, 20))]),
            session_date=date(2026, 8, 21),
            package_path=wrong_package,
            fetched_at=FETCHED_AT,
        )
    package = tmp_path / "no-same-day-identity"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped_payload(date(2026, 8, 21))]),
        session_date=date(2026, 8, 21),
        package_path=package,
        fetched_at=FETCHED_AT,
    )
    with pytest.raises(SameDayCatchupError, match="same-day completed Identity"):
        build_eod_plan(
            package_path=package,
            plan_path=tmp_path / "wrong-identity.plan.json",
            data_root=root,
        )

    bad = tmp_path / "bad-ohlc"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped_payload(date(2026, 8, 20), h="8")]),
        session_date=date(2026, 8, 20),
        package_path=bad,
        fetched_at=FETCHED_AT,
    )
    with pytest.raises(SameDayCatchupError, match="quality gates"):
        build_eod_plan(
            package_path=bad,
            plan_path=tmp_path / "bad-ohlc.plan.json",
            data_root=root,
        )


def test_duplicate_pages_cross_date_pagination_and_credential_material_rejected(tmp_path):
    session = date(2026, 8, 20)
    with pytest.raises(SameDayCatchupError, match="allowlist"):
        fetch_identity_package(
            config=MassiveProviderConfig(
                api_key="fixture-only", base_url="https://example.test"
            ),
            transport=FakeTransport([]),
            session_date=session,
            package_path=tmp_path / "foreign-base",
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )
    duplicate = {"results": [reference_record(1, session)]}
    duplicate_first = {
        **duplicate,
        "next_url": (
            "https://api.massive.com/v3/reference/tickers"
            f"?cursor=two&date={session.isoformat()}"
        ),
    }
    with pytest.raises(SameDayCatchupError, match="duplicate reference page"):
        fetch_identity_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport([duplicate_first, duplicate]),
            session_date=session,
            package_path=tmp_path / "duplicate",
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )

    cross_date = {
        "results": [reference_record(1, session)],
        "next_url": "https://api.massive.com/v3/reference/tickers?cursor=x&date=2026-08-21",
    }
    transport = FakeTransport([cross_date])
    with pytest.raises(RuntimeError, match="date changed"):
        fetch_identity_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=transport,
            session_date=session,
            package_path=tmp_path / "cross-date",
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )

    for label, next_url, error in (
        ("host", "https://evil.example/v3/reference/tickers?date=2026-08-20", "host changed"),
        ("path", "https://api.massive.com/v3/reference/tickers/types?date=2026-08-20", "path changed"),
        ("scheme", "http://api.massive.com/v3/reference/tickers?date=2026-08-20", "scheme changed"),
    ):
        with pytest.raises(RuntimeError, match=error):
            fetch_identity_package(
                config=MassiveProviderConfig(api_key="fixture-only"),
                transport=FakeTransport([{"results": [], "next_url": next_url}]),
                session_date=session,
                package_path=tmp_path / label,
                fetched_at=FETCHED_AT,
                rate_limiter=no_wait_limiter(),
            )

    loop_page = {
        "results": [],
        "next_url": (
            "https://api.massive.com/v3/reference/tickers"
            "?cursor=loop&date=2026-08-20"
        ),
    }
    with pytest.raises(RuntimeError, match="pagination loop"):
        fetch_identity_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport([loop_page, loop_page]),
            session_date=session,
            package_path=tmp_path / "loop",
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )

    sanitized_package = tmp_path / "sanitized-next-url"
    fetch_identity_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport(
            [
                {
                    "results": [reference_record(1, session)],
                    "next_url": (
                        "https://api.massive.com/v3/reference/tickers"
                        "?cursor=second&date=2026-08-20&apiKey=MUST_NOT_PERSIST"
                    ),
                },
                {"results": [reference_record(2, session)]},
            ]
        ),
        session_date=session,
        package_path=sanitized_package,
        fetched_at=FETCHED_AT,
        rate_limiter=no_wait_limiter(),
    )
    assert b"MUST_NOT_PERSIST" not in b"".join(
        path.read_bytes() for path in sanitized_package.iterdir()
    )
    assert len(transport.calls) == 1

    with pytest.raises(SameDayCatchupError, match="credential"):
        fetch_eod_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport(
                [{**grouped_payload(session), "Authorization": "secret"}]
            ),
            session_date=session,
            package_path=tmp_path / "secret",
            fetched_at=FETCHED_AT,
        )


def test_partial_symlink_replay_and_eod_post_rename_state(tmp_path):
    session = date(2026, 8, 20)
    root = tmp_path / "data"
    root.mkdir()
    identity_path, identity_plan = plan_and_apply_identity(tmp_path, root, session)
    with pytest.raises(SameDayCatchupError, match="current state changed"):
        apply_approved_plan(
            plan_path=identity_path,
            approved_plan_sha256=file_sha256(identity_path),
            expected_current_state_fingerprint=identity_plan.expected_current_state_fingerprint,
            data_root=root,
        )

    package = tmp_path / "eod"
    fetch_eod_package(
        config=MassiveProviderConfig(api_key="fixture-only"),
        transport=FakeTransport([grouped_payload(session)]),
        session_date=session,
        package_path=package,
        fetched_at=FETCHED_AT,
    )
    plan_path = tmp_path / "eod.plan.json"
    plan = build_eod_plan(package_path=package, plan_path=plan_path, data_root=root)
    with pytest.raises(SameDayCatchupError, match="injected failure"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
            fail_after_target_count=1,
        )
    integrity = CanonicalEodReadRepository(root).inspect_session(session)
    assert integrity.record_count == 5001
    with pytest.raises(SameDayCatchupError):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=file_sha256(plan_path),
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
        )

    symlink_root = tmp_path / "linked-root"
    symlink_root.symlink_to(root, target_is_directory=True)
    with pytest.raises(SameDayCatchupError):
        inventory_fingerprint(symlink_root)


def test_plan_and_package_tamper_cli_contract_and_apply_socket_guard(tmp_path, monkeypatch):
    root = tmp_path / "data"
    root.mkdir()
    session = date(2026, 8, 20)
    with pytest.raises(RuntimeError, match="direct network-to-production"):
        ingest_massive_instrument_master_snapshot(
            config=None,
            transport=None,
            as_of_date=session,
            data_root=tmp_path,
        )
    with pytest.raises(RuntimeError, match="direct network-to-production"):
        ingest_grouped_daily(
            config=None,
            transport=None,
            session_date=session,
            identity_as_of_date=session,
            data_root=tmp_path,
        )
    real_package_parent = tmp_path / "real-package-parent"
    real_package_parent.mkdir()
    linked_package_parent = tmp_path / "linked-package-parent"
    linked_package_parent.symlink_to(real_package_parent, target_is_directory=True)
    with pytest.raises(SameDayCatchupError, match="symlink"):
        fetch_identity_package(
            config=MassiveProviderConfig(api_key="fixture-only"),
            transport=FakeTransport([]),
            session_date=session,
            package_path=linked_package_parent / "package",
            fetched_at=FETCHED_AT,
            rate_limiter=no_wait_limiter(),
        )
    package, _ = fetch_identity(tmp_path, session)
    plan_path = tmp_path / "identity.plan.json"
    plan = build_identity_plan(package_path=package, plan_path=plan_path, data_root=root)
    approved_sha = file_sha256(plan_path)
    plan_path.chmod(0o600)
    content = json.loads(plan_path.read_text())
    content["counts"]["raw_records"] += 1
    plan_path.write_text(json.dumps(content))
    with pytest.raises(SameDayCatchupError, match="SHA-256"):
        apply_approved_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_sha,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            data_root=root,
        )
    assert not Path(plan.publication_order[0]).exists()

    with pytest.raises(SystemExit) as exc:
        identity_main(["--apply", "--session-date", session.isoformat()])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        eod_main(["--apply", "--session-date", session.isoformat()])
    assert exc.value.code == 2

    package2, _ = fetch_identity(tmp_path, date(2026, 8, 21))
    plan2_path = tmp_path / "identity2.plan.json"
    plan2 = build_identity_plan(package_path=package2, plan_path=plan2_path, data_root=root)
    original = socket.create_connection
    observed = {"blocked": False}

    import tip_api.providers.massive.same_day_catchup as module

    publish = module._publish_target_directory

    def probe(*args, **kwargs):
        with pytest.raises(SameDayCatchupError, match="network access"):
            socket.create_connection(("example.invalid", 443))
        observed["blocked"] = True
        return publish(*args, **kwargs)

    monkeypatch.setattr(module, "_publish_target_directory", probe)
    apply_approved_plan(
        plan_path=plan2_path,
        approved_plan_sha256=file_sha256(plan2_path),
        expected_current_state_fingerprint=plan2.expected_current_state_fingerprint,
        data_root=root,
    )
