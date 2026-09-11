from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
    reconciled_eod_fingerprint,
)
from tip_api.persistence.parquet.manifest import content_fingerprint
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ParquetReconciledEodEditionCandidateRepository,
    ReconciledEodEditionConflictError,
    ReconciledEodEditionCorruptionError,
    ReconciledEodEditionPersistenceError,
    read_reconciled_eod_edition,
    read_reconciled_eod_session,
)
from tip_api.services.reconciled_eod_edition import (
    ReconciledEodSessionCandidate,
    compare_reconciled_eod_records,
)


SESSION = date(2022, 10, 7)
NOW = datetime(2026, 9, 10, 23, tzinfo=UTC)
ID1 = UUID("00000000-0000-0000-0000-000000000001")
ID2 = UUID("00000000-0000-0000-0000-000000000002")
REVISION = "a" * 40


def bar(instrument_id: UUID) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=SESSION,
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal("11"),
        volume=Decimal("1000"),
        vwap=Decimal("10.5"),
        trade_count=25,
        notional=Decimal("11000"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=Decimal("11"),
        source="massive_stocks_basic",
        ingested_at=NOW,
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.VALID,
    )


def candidate(*, unexpected: bool = False) -> ReconciledEodSessionCandidate:
    base = (bar(ID1),)
    rebuilt = (bar(ID1), bar(ID2))
    expected = frozenset() if unexpected else frozenset({ID2})
    diff = compare_reconciled_eod_records(
        base_records=base,
        rebuilt_records=rebuilt,
        expected_added_instrument_ids=expected,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )
    return ReconciledEodSessionCandidate(
        session_date=SESSION,
        rebuilt_records=rebuilt,
        diff=diff,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        source_observed_at=NOW,
        source_package_manifest_sha256="1" * 64,
        source_package_content_sha256="2" * 64,
        identity_snapshot_fingerprint="3" * 64,
        identity_source_fingerprint="4" * 64,
        base_eod_fingerprint=content_fingerprint(base),
        rebuilt_eod_fingerprint=content_fingerprint(rebuilt),
        quality_summary_fingerprint=reconciled_eod_fingerprint(("valid",)),
        quality_warnings=("case_sensitive_provider_tickers_present",),
    )


def repository(root: Path) -> ParquetReconciledEodEditionCandidateRepository:
    return ParquetReconciledEodEditionCandidateRepository(
        root=root,
        edition_id="massive-exact-symbol-v1",
        implementation_revision=REVISION,
        created_at=NOW,
    )


def test_publishes_formally_rereads_and_reuses_identical_candidate(
    tmp_path: Path,
) -> None:
    root = tmp_path / "edition-candidate"
    first = repository(root).publish_session(candidate())
    second = repository(root).publish_session(candidate())
    completed = read_reconciled_eod_session(
        root=root,
        edition_id="massive-exact-symbol-v1",
        session_date=SESSION,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.manifest_fingerprint == completed.manifest.logical_fingerprint
    assert len(completed.records) == 2
    assert completed.manifest.candidate_authority is False
    assert completed.manifest.production_authority is False
    assert sorted(item.stat().st_mode & 0o777 for item in first.partition_path.iterdir()) == [
        0o600,
        0o600,
    ]


def test_interval_manifest_is_the_only_complete_edition_boundary(
    tmp_path: Path,
) -> None:
    root = tmp_path / "edition-candidate"
    store = repository(root)
    store.publish_session(candidate())
    with pytest.raises(ReconciledEodEditionCorruptionError, match="interval manifest"):
        read_reconciled_eod_edition(
            root=root,
            edition_id="massive-exact-symbol-v1",
        )

    completed = store.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )
    reread = read_reconciled_eod_edition(
        root=root,
        edition_id="massive-exact-symbol-v1",
    )
    reused = store.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )

    assert completed.manifest == reread.manifest == reused.manifest
    assert completed.manifest.added_record_count == 1
    assert len(completed.sessions) == 1


def test_interval_manifest_rerun_without_fixed_clock_is_idempotent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "edition-candidate"
    store = ParquetReconciledEodEditionCandidateRepository(
        root=root,
        edition_id="massive-exact-symbol-v1",
        implementation_revision=REVISION,
    )
    store.publish_session(candidate())

    first = store.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )
    second = store.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )

    assert second.manifest == first.manifest


def test_interval_manifest_rejects_residue_before_writing_marker(
    tmp_path: Path,
) -> None:
    root = tmp_path / "edition-candidate"
    store = repository(root)
    result = store.publish_session(candidate())
    marker = result.partition_path.parent / "interval-manifest.json"
    (result.partition_path.parent / "unexpected").write_text("x", encoding="utf-8")

    with pytest.raises(ReconciledEodEditionPersistenceError, match="file set"):
        store.publish_interval_manifest(
            session_dates=(SESSION,),
            evaluation_first_session=SESSION,
            evaluation_last_session=SESSION,
        )

    assert not marker.exists()


def test_completed_interval_rejects_unlisted_residue(tmp_path: Path) -> None:
    root = tmp_path / "edition-candidate"
    store = repository(root)
    result = store.publish_session(candidate())
    store.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )
    (result.partition_path.parent / "unexpected").write_text("x", encoding="utf-8")

    with pytest.raises(ReconciledEodEditionCorruptionError, match="file set"):
        read_reconciled_eod_edition(
            root=root,
            edition_id="massive-exact-symbol-v1",
        )


def test_rejects_quarantine_and_conflicting_rerun(tmp_path: Path) -> None:
    root = tmp_path / "edition-candidate"
    with pytest.raises(ReconciledEodEditionPersistenceError, match="quarantined"):
        repository(root).publish_session(candidate(unexpected=True))

    repository(root).publish_session(candidate())
    changed = replace(candidate(), source_package_content_sha256="9" * 64)
    with pytest.raises(ReconciledEodEditionConflictError, match="differs"):
        repository(root).publish_session(changed)


def test_formal_reread_rejects_manifest_tampering(tmp_path: Path) -> None:
    root = tmp_path / "edition-candidate"
    result = repository(root).publish_session(candidate())
    manifest_path = result.partition_path / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["base_eod_fingerprint"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReconciledEodEditionCorruptionError, match="manifest"):
        read_reconciled_eod_session(
            root=root,
            edition_id="massive-exact-symbol-v1",
            session_date=SESSION,
        )


def test_candidate_writer_rejects_non_tmp_root() -> None:
    with pytest.raises(ReconciledEodEditionPersistenceError, match="invalid"):
        repository(Path("relative-root")).publish_session(candidate())
