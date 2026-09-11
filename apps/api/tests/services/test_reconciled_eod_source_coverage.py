from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
)
from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageDisposition,
    ReconciledEodSourceCoverageSessionV1,
    ReconciledEodSourceCoverageV1,
    ReconciledEodSourceOrigin,
    seal_reconciled_eod_source_coverage,
)
from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.services import reconciled_eod_source_coverage as module
from tip_api.services.historical_identity_source_custody import (
    HistoricalIdentitySourceCustodyError,
)


SESSION = date(2026, 9, 9)
NOW = datetime(2026, 9, 11, 1, tzinfo=UTC)


class OneSessionCalendar:
    calendar_id = "XNYS"

    def sessions_in_range(self, first: date, last: date) -> tuple[date, ...]:
        assert first == last == SESSION
        return (SESSION,)


class WarmupCalendar:
    calendar_id = "XNYS"

    def sessions_in_range(self, first: date, last: date) -> tuple[date, ...]:
        assert first == date(2026, 9, 8)
        assert last == SESSION
        return (date(2026, 9, 8), SESSION)


class FakeRepository:
    def inspect_session(self, session_date: date):
        assert session_date == SESSION
        return SimpleNamespace(
            content_fingerprint="1" * 64,
            identity_snapshot_fingerprint="2" * 64,
        )


def spec(
    tmp_path: Path,
    origin: ReconciledEodSourceOrigin,
) -> module._SourceCandidateSpec:
    return module._SourceCandidateSpec(
        origin=origin,
        package_path=tmp_path / origin.value,
        plan_path=(
            None
            if origin == ReconciledEodSourceOrigin.LATER_REACQUISITION
            else tmp_path / f"{origin.value}.plan.json"
        ),
        provenance=(
            ReconciledEodSourceProvenance.LATER_REACQUISITION
            if origin == ReconciledEodSourceOrigin.LATER_REACQUISITION
            else ReconciledEodSourceProvenance.RETAINED_ORIGINAL
        ),
    )


def validated(
    origin: ReconciledEodSourceOrigin,
) -> module._ValidatedSourceCandidate:
    provenance = (
        ReconciledEodSourceProvenance.LATER_REACQUISITION
        if origin == ReconciledEodSourceOrigin.LATER_REACQUISITION
        else ReconciledEodSourceProvenance.RETAINED_ORIGINAL
    )
    return module._ValidatedSourceCandidate(
        origin=origin,
        provenance=provenance,
        source_observed_at=NOW,
        package_manifest_sha256="3" * 64,
        package_content_sha256="4" * 64,
        binding_plan_sha256=None if provenance.value.startswith("later") else "5" * 64,
    )


def bind_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "read_identity_source_custody_at_data_root",
        lambda **_kwargs: SimpleNamespace(
            manifest=SimpleNamespace(canonical_snapshot_fingerprint="2" * 64)
        ),
    )


def test_selects_one_formally_bound_retained_original(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = spec(tmp_path, ReconciledEodSourceOrigin.HISTORICAL_BACKFILL)
    monkeypatch.setattr(module, "_discover_candidates", lambda _date: ((selected,), ()))
    monkeypatch.setattr(
        module,
        "_validate_candidate",
        lambda **_kwargs: validated(selected.origin),
    )
    bind_identity(monkeypatch)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.disposition == (
        ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
    )
    assert evidence.selected_source_origin == selected.origin
    assert evidence.selected_binding_plan_sha256 == "5" * 64


def test_retained_original_has_explicit_precedence_over_reacquisition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = spec(tmp_path, ReconciledEodSourceOrigin.DAILY_AUTOMATION)
    later = spec(tmp_path, ReconciledEodSourceOrigin.LATER_REACQUISITION)
    monkeypatch.setattr(
        module,
        "_discover_candidates",
        lambda _date: ((original, later), ()),
    )
    monkeypatch.setattr(
        module,
        "_validate_candidate",
        lambda **values: validated(values["spec"].origin),
    )
    bind_identity(monkeypatch)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.selected_source_origin == original.origin
    assert evidence.observed_candidate_count == 2


def test_selects_later_reacquisition_only_with_visible_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    later = spec(tmp_path, ReconciledEodSourceOrigin.LATER_REACQUISITION)
    monkeypatch.setattr(module, "_discover_candidates", lambda _date: ((later,), ()))
    monkeypatch.setattr(
        module,
        "_validate_candidate",
        lambda **_values: validated(later.origin),
    )
    bind_identity(monkeypatch)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.disposition == (
        ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION
    )
    assert evidence.selected_source_provenance == (
        ReconciledEodSourceProvenance.LATER_REACQUISITION
    )
    assert evidence.selected_binding_plan_sha256 is None


def test_multiple_retained_originals_fail_as_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    historical = spec(tmp_path, ReconciledEodSourceOrigin.HISTORICAL_BACKFILL)
    daily = spec(tmp_path, ReconciledEodSourceOrigin.DAILY_AUTOMATION)
    monkeypatch.setattr(
        module,
        "_discover_candidates",
        lambda _date: ((historical, daily), ()),
    )
    monkeypatch.setattr(
        module,
        "_validate_candidate",
        lambda **values: validated(values["spec"].origin),
    )
    bind_identity(monkeypatch)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.disposition == ReconciledEodSourceCoverageDisposition.CONFLICT
    assert evidence.reason_codes == ("multiple_eligible_source_packages",)


def test_invalid_package_binding_is_not_silently_skipped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = spec(tmp_path, ReconciledEodSourceOrigin.HISTORICAL_BACKFILL)
    monkeypatch.setattr(module, "_discover_candidates", lambda _date: ((selected,), ()))

    def fail(**_kwargs):
        raise SameDayCatchupError("invalid")

    monkeypatch.setattr(module, "_validate_candidate", fail)
    bind_identity(monkeypatch)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.disposition == ReconciledEodSourceCoverageDisposition.INVALID
    assert evidence.reason_codes == (
        "historical_backfill_source_binding_invalid",
    )


def test_missing_identity_source_blocks_otherwise_available_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = spec(tmp_path, ReconciledEodSourceOrigin.HISTORICAL_BACKFILL)
    monkeypatch.setattr(module, "_discover_candidates", lambda _date: ((selected,), ()))

    def fail(**_kwargs):
        raise HistoricalIdentitySourceCustodyError("missing")

    monkeypatch.setattr(module, "read_identity_source_custody_at_data_root", fail)

    evidence = module._assess_session(
        data_root=tmp_path,
        repository=FakeRepository(),
        session_date=SESSION,
    )

    assert evidence.disposition == ReconciledEodSourceCoverageDisposition.INVALID
    assert evidence.reason_codes == ("identity_source_custody_unavailable",)


def test_daily_identity_package_is_not_misclassified_as_grouped_daily_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    historical = tmp_path / "historical"
    daily = tmp_path / "daily"
    later = tmp_path / "later"
    for root in (historical, daily, later):
        root.mkdir()
    monkeypatch.setattr(module, "HISTORICAL_SESSIONS_ROOT", historical)
    monkeypatch.setattr(module, "DAILY_SESSIONS_ROOT", daily)
    monkeypatch.setattr(module, "LATER_REACQUISITION_SESSIONS_ROOT", later)
    package = daily / f"session_date={SESSION.isoformat()}" / "acquisition-package"
    package.mkdir(parents=True)
    (package / "package.json").write_text(
        json.dumps({"package_type": "identity_reference"}),
        encoding="utf-8",
    )

    candidates, reasons = module._discover_candidates(SESSION)

    assert candidates == ()
    assert reasons == ()


def test_whole_census_seals_incomplete_counts_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root.resolve())
    for name in (
        "HISTORICAL_SESSIONS_ROOT",
        "DAILY_SESSIONS_ROOT",
        "LATER_REACQUISITION_SESSIONS_ROOT",
    ):
        root = tmp_path / name.lower()
        root.mkdir(mode=0o700)
        monkeypatch.setattr(module, name, root)
    missing = ReconciledEodSourceCoverageSessionV1(
        session_date=SESSION,
        disposition=ReconciledEodSourceCoverageDisposition.MISSING,
        observed_candidate_count=0,
        reason_codes=("grouped_daily_source_package_missing",),
    )
    monkeypatch.setattr(module, "_assess_session", lambda **_kwargs: missing)

    evidence = module.assess_reconciled_eod_source_coverage(
        data_root=data_root.resolve(),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
        created_at=NOW,
        calendar=OneSessionCalendar(),
    )

    assert evidence.status == "incomplete"
    assert evidence.target_session_count == 1
    assert evidence.missing_session_count == 1
    assert evidence.external_request_count == 0
    assert evidence.canonical_data_write_count == 0
    assert evidence.candidate_session_write_count == 0


def test_whole_census_rejects_unbounded_worker_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root.resolve())
    for name in (
        "HISTORICAL_SESSIONS_ROOT",
        "DAILY_SESSIONS_ROOT",
        "LATER_REACQUISITION_SESSIONS_ROOT",
    ):
        monkeypatch.setattr(module, name, tmp_path / f"absent-{name.lower()}")

    with pytest.raises(module.ReconciledEodSourceCoverageError, match="one and four"):
        module.assess_reconciled_eod_source_coverage(
            data_root=data_root.resolve(),
            evaluation_first_session=SESSION,
            evaluation_last_session=SESSION,
            created_at=NOW,
            calendar=OneSessionCalendar(),
            workers=5,
        )


def test_whole_census_includes_declared_warmup_without_moving_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root.resolve())
    for name in (
        "HISTORICAL_SESSIONS_ROOT",
        "DAILY_SESSIONS_ROOT",
        "LATER_REACQUISITION_SESSIONS_ROOT",
    ):
        root = tmp_path / f"warmup-{name.lower()}"
        root.mkdir(mode=0o700)
        monkeypatch.setattr(module, name, root)

    def missing(**values):
        return ReconciledEodSourceCoverageSessionV1(
            session_date=values["session_date"],
            disposition=ReconciledEodSourceCoverageDisposition.MISSING,
            observed_candidate_count=0,
            reason_codes=("grouped_daily_source_package_missing",),
        )

    monkeypatch.setattr(module, "_assess_session", missing)

    evidence = module.assess_reconciled_eod_source_coverage(
        data_root=data_root.resolve(),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
        warmup_first_session=date(2026, 9, 8),
        warmup_last_session=date(2026, 9, 8),
        created_at=NOW,
        calendar=WarmupCalendar(),
    )

    assert evidence.target_session_count == 2
    assert evidence.warmup_first_session == date(2026, 9, 8)
    assert evidence.evaluation_first_session == SESSION


def missing_coverage() -> ReconciledEodSourceCoverageV1:
    session = ReconciledEodSourceCoverageSessionV1(
        session_date=SESSION,
        disposition=ReconciledEodSourceCoverageDisposition.MISSING,
        observed_candidate_count=0,
        reason_codes=("grouped_daily_source_package_missing",),
    )
    return seal_reconciled_eod_source_coverage(
        {
            "status": "incomplete",
            "evaluation_first_session": SESSION,
            "evaluation_last_session": SESSION,
            "sessions": (session,),
            "target_session_count": 1,
            "retained_original_session_count": 0,
            "later_reacquisition_session_count": 0,
            "missing_session_count": 1,
            "invalid_session_count": 0,
            "conflict_session_count": 0,
            "created_at": NOW,
        }
    )


def ready_coverage() -> ReconciledEodSourceCoverageV1:
    session = ReconciledEodSourceCoverageSessionV1(
        session_date=SESSION,
        disposition=(
            ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
        ),
        observed_candidate_count=1,
        observed_candidate_origins=(ReconciledEodSourceOrigin.HISTORICAL_BACKFILL,),
        canonical_eod_fingerprint="1" * 64,
        canonical_identity_fingerprint="2" * 64,
        selected_source_origin=ReconciledEodSourceOrigin.HISTORICAL_BACKFILL,
        selected_source_provenance=(
            ReconciledEodSourceProvenance.RETAINED_ORIGINAL
        ),
        selected_source_observed_at=NOW,
        selected_package_manifest_sha256="3" * 64,
        selected_package_content_sha256="4" * 64,
        selected_binding_plan_sha256="5" * 64,
    )
    return seal_reconciled_eod_source_coverage(
        {
            "status": "ready_for_candidate_build",
            "evaluation_first_session": SESSION,
            "evaluation_last_session": SESSION,
            "sessions": (session,),
            "target_session_count": 1,
            "retained_original_session_count": 1,
            "later_reacquisition_session_count": 0,
            "missing_session_count": 0,
            "invalid_session_count": 0,
            "conflict_session_count": 0,
            "created_at": NOW,
        }
    )


def test_writes_and_formally_rereads_owner_only_immutable_coverage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source-coverage.json"
    written = module.write_reconciled_eod_source_coverage(
        coverage=missing_coverage(),
        path=path,
    )
    reread = module.read_reconciled_eod_source_coverage(
        path=path,
        expected_file_sha256=written.file_sha256,
    )

    assert written == reread
    assert path.stat().st_mode & 0o777 == 0o400
    with pytest.raises(module.ReconciledEodSourceCoverageError, match="already"):
        module.write_reconciled_eod_source_coverage(
            coverage=missing_coverage(),
            path=path,
        )


def test_coverage_write_does_not_replace_concurrent_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "source-coverage.json"

    def simulate_concurrent_create(
        _source: Path,
        target: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        assert follow_symlinks is False
        Path(target).write_bytes(b"concurrent evidence")
        Path(target).chmod(0o400)
        raise FileExistsError

    monkeypatch.setattr(module.os, "link", simulate_concurrent_create)

    with pytest.raises(module.ReconciledEodSourceCoverageError, match="already"):
        module.write_reconciled_eod_source_coverage(
            coverage=missing_coverage(),
            path=path,
        )

    assert path.read_bytes() == b"concurrent evidence"
    assert not tuple(tmp_path.glob(".*.staging.*"))


def test_coverage_reread_rejects_wrong_byte_hash(tmp_path: Path) -> None:
    path = tmp_path / "source-coverage.json"
    module.write_reconciled_eod_source_coverage(
        coverage=missing_coverage(),
        path=path,
    )

    with pytest.raises(module.ReconciledEodSourceCoverageError, match="hash"):
        module.read_reconciled_eod_source_coverage(
            path=path,
            expected_file_sha256="f" * 64,
        )


def test_resolves_only_sealed_selected_source_for_bounded_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root.resolve())
    historical = tmp_path / "historical"
    daily = tmp_path / "daily"
    later = tmp_path / "later"
    for root in (historical, daily, later):
        root.mkdir(mode=0o700)
    monkeypatch.setattr(module, "HISTORICAL_SESSIONS_ROOT", historical)
    monkeypatch.setattr(module, "DAILY_SESSIONS_ROOT", daily)
    monkeypatch.setattr(module, "LATER_REACQUISITION_SESSIONS_ROOT", later)
    monkeypatch.setattr(
        module,
        "_validate_candidate",
        lambda **values: validated(values["spec"].origin),
    )

    sources = module.resolve_reconciled_eod_batch_sources(
        coverage=ready_coverage(),
        data_root=data_root.resolve(),
        session_dates=(SESSION,),
    )

    assert len(sources) == 1
    assert sources[0].package_path == (
        historical / f"session_date={SESSION.isoformat()}" / "eod-acquisition-package"
    )
    assert sources[0].source_provenance == (
        ReconciledEodSourceProvenance.RETAINED_ORIGINAL
    )


def test_incomplete_coverage_cannot_feed_candidate_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root.resolve())
    for name in (
        "HISTORICAL_SESSIONS_ROOT",
        "DAILY_SESSIONS_ROOT",
        "LATER_REACQUISITION_SESSIONS_ROOT",
    ):
        root = tmp_path / name.lower()
        root.mkdir(mode=0o700)
        monkeypatch.setattr(module, name, root)

    with pytest.raises(module.ReconciledEodSourceCoverageError, match="incomplete"):
        module.resolve_reconciled_eod_batch_sources(
            coverage=missing_coverage(),
            data_root=data_root.resolve(),
            session_dates=(SESSION,),
        )
