from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.persistence.instrument_master import (
    InstrumentMasterSnapshotCorruptionError,
)
from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.services import historical_identity_package_equivalence_census as module
from tip_api.services.historical_identity_package_equivalence_census import (
    HistoricalIdentityPackageEquivalenceCensusError,
    run_historical_identity_package_equivalence_census,
    write_historical_identity_package_equivalence_census_report,
)

NOW = datetime(2026, 9, 4, 18, tzinfo=UTC)
SHA = "a" * 64


def _write_manifest(
    root: Path,
    name: str,
    session: date,
    *,
    package_type: str = "identity_reference",
) -> Path:
    package = root / name
    package.mkdir()
    endpoint = (
        "/v3/reference/tickers"
        if package_type == "identity_reference"
        else "/v2/aggs/grouped/locale/us/market/stocks/{session_date}"
    )
    payload = {
        "schema_version": "1.0",
        "package_type": package_type,
        "provider_id": "massive_stocks_basic",
        "session_date": session.isoformat(),
        "endpoint_class": endpoint,
        "adjusted": None if package_type == "identity_reference" else False,
        "request_count": 1,
        "pagination_complete": True,
        "fetched_at": NOW.isoformat().replace("+00:00", "Z"),
        "artifacts": [
            {
                "sequence": 1,
                "file_name": "response-01.json",
                "canonical_response_sha256": SHA,
                "response_bytes": 1,
            }
        ],
        "package_content_sha256": SHA,
    }
    (package / "package.json").write_text(json.dumps(payload), encoding="utf-8")
    return package


def test_census_keeps_source_failure_classes_and_duplicates_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = tuple(date(2026, 8, day) for day in range(1, 7))
    outside = date(2026, 7, 31)
    source_root = tmp_path / "packages"
    source_root.mkdir()
    _write_manifest(source_root, "exact", sessions[1])
    _write_manifest(source_root, "mismatch", sessions[2])
    _write_manifest(source_root, "custody", sessions[3])
    _write_manifest(source_root, "duplicate-a", sessions[4])
    _write_manifest(source_root, "duplicate-b", sessions[4])
    _write_manifest(source_root, "canonical-unavailable", sessions[5])
    _write_manifest(source_root, "outside", outside)
    _write_manifest(
        source_root,
        "grouped",
        sessions[0],
        package_type="grouped_daily",
    )
    invalid = source_root / "invalid"
    invalid.mkdir()
    (invalid / "package.json").write_text("not-json", encoding="utf-8")

    data_root = tmp_path / "data"
    data_root.mkdir()

    class FakeEodRepository:
        def __init__(self, root):
            assert root == data_root.resolve()

        def list_session_index(self):
            return sessions

    identity = SimpleNamespace(
        as_of_date=None,
        snapshot_content_sha256="b" * 64,
        instrument_content_sha256="c" * 64,
        identity_content_sha256="d" * 64,
        resolver_content_sha256="e" * 64,
    )

    class FakeIdentityRepository:
        def __init__(self, root):
            assert root == data_root.resolve()

        def inspect_snapshot(self, session):
            if session == sessions[5]:
                raise InstrumentMasterSnapshotCorruptionError("fixture")
            identity.as_of_date = session
            return identity

    def inspect(**kwargs):
        session = kwargs["session_date"]
        package_name = kwargs["package_path"].name
        if session == sessions[3]:
            raise SameDayCatchupError("fixture")
        exact = session == sessions[1] or package_name == "duplicate-a"
        return SimpleNamespace(
            exact_match=exact,
            rebuilt_instrument_fingerprint="c" * 64 if exact else "1" * 64,
            rebuilt_identity_fingerprint="d" * 64 if exact else "2" * 64,
            rebuilt_resolver_fingerprint="e" * 64 if exact else "3" * 64,
            instrument_match=exact,
            identity_match=exact,
            resolver_match=exact,
        )

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeEodRepository)
    monkeypatch.setattr(
        module,
        "ParquetInstrumentMasterSnapshotRepository",
        FakeIdentityRepository,
    )
    monkeypatch.setattr(
        module,
        "inspect_historical_identity_package_equivalence",
        inspect,
    )

    result = run_historical_identity_package_equivalence_census(
        data_root=data_root,
        package_roots=(source_root,),
        evaluated_at=NOW,
    )

    assert result.canonical_session_count == 6
    assert result.evaluated_session_count == 6
    assert result.scope == "full_canonical_index"
    assert result.rebuild_profile == "current_v1"
    assert result.worker_count == 1
    assert result.discovered_identity_package_count == 7
    assert result.ignored_non_identity_package_count == 1
    assert result.unroutable_manifest_count == 1
    assert result.outside_canonical_session_package_count == 1
    assert result.exact_equivalent_session_count == 1
    assert result.duplicate_source_session_count == 1
    assert [item.status for item in result.sessions] == [
        "missing_source",
        "exact_equivalent",
        "identity_snapshot_mismatch",
        "package_custody_failed",
        "duplicate_source_review_required",
        "canonical_identity_unavailable",
    ]
    duplicate = result.sessions[4]
    assert duplicate.candidate_count == 2
    assert duplicate.custody_valid_candidate_count == 2
    assert duplicate.exact_equivalent_candidate_count == 1
    assert result.external_request_count == 0
    assert result.canonical_data_write_count == 0

    report_path = tmp_path / "census.json"
    written = write_historical_identity_package_equivalence_census_report(
        report=result,
        report_path=report_path,
    )
    assert written == report_path
    assert written.stat().st_mode & 0o777 == 0o600
    stored = json.loads(written.read_text(encoding="utf-8"))
    assert stored["sessions"][1]["status"] == "exact_equivalent"
    with pytest.raises(
        HistoricalIdentityPackageEquivalenceCensusError,
        match="already exists",
    ):
        write_historical_identity_package_equivalence_census_report(
            report=result,
            report_path=report_path,
        )


def test_package_roots_must_be_non_overlapping_tmp_directories(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    data_root = tmp_path / "data"
    data_root.mkdir()
    with pytest.raises(
        HistoricalIdentityPackageEquivalenceCensusError,
        match="non-overlapping",
    ):
        run_historical_identity_package_equivalence_census(
            data_root=data_root,
            package_roots=(root, child),
            evaluated_at=NOW,
        )


def test_bounded_sample_is_explicit_and_cannot_claim_full_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = (date(2026, 8, 1), date(2026, 8, 4))
    source_root = tmp_path / "packages"
    source_root.mkdir()
    data_root = tmp_path / "data"
    data_root.mkdir()

    class FakeEodRepository:
        def __init__(self, _root):
            pass

        def list_session_index(self):
            return sessions

    identity = SimpleNamespace(
        snapshot_content_sha256="b" * 64,
        instrument_content_sha256="c" * 64,
        identity_content_sha256="d" * 64,
        resolver_content_sha256="e" * 64,
    )

    class FakeIdentityRepository:
        def __init__(self, _root):
            pass

        def inspect_snapshot(self, _session):
            return identity

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeEodRepository)
    monkeypatch.setattr(
        module,
        "ParquetInstrumentMasterSnapshotRepository",
        FakeIdentityRepository,
    )
    result = run_historical_identity_package_equivalence_census(
        data_root=data_root,
        package_roots=(source_root,),
        evaluated_at=NOW,
        sample_sessions=(sessions[1],),
    )
    assert result.scope == "bounded_sample"
    assert result.canonical_session_count == 2
    assert result.evaluated_session_count == 1
    assert [item.session_date for item in result.sessions] == [
        sessions[1].isoformat()
    ]
