from __future__ import annotations

import json
import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    HistoricalDatasetFamily,
    InstrumentLifecycleObservationV1,
    InstrumentLifecycleStatus,
    KnowledgeTimeStatus,
    LineageEvidenceStatus,
    ResolutionStatus,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchConflictError,
    HistoricalResearchCorruptionError,
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.parquet.historical_research import (
    ADJUSTMENT_LEDGER_ARROW_SCHEMA,
    CORPORATE_ACTION_OBSERVATION_ARROW_SCHEMA,
    INSTRUMENT_LIFECYCLE_ARROW_SCHEMA,
    UNIVERSE_MEMBERSHIP_ARROW_SCHEMA,
    ParquetHistoricalResearchRepository,
)

AS_OF = date(2026, 8, 27)
OBSERVED_AT = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
INGESTED_AT = OBSERVED_AT + timedelta(minutes=2)
ID1 = UUID("11111111-1111-4111-8111-111111111111")
ID2 = UUID("22222222-2222-4222-8222-222222222222")


def evaluated_base_fingerprint(*instrument_ids: UUID) -> str:
    payload = json.dumps(
        [str(item) for item in sorted(set(instrument_ids), key=str)],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def action(
    source_action_id: str = "split-1",
    instrument_id: UUID = ID1,
    ratio_to: Decimal = Decimal("2"),
) -> CorporateActionSourceObservationV1:
    return CorporateActionSourceObservationV1(
        provider="massive",
        source_action_id=source_action_id,
        source_revision=1,
        record_status=CorporateActionRecordStatus.ACTIVE,
        action_type=CorporateActionType.STOCK_SPLIT,
        provider_ticker="TEST",
        instrument_resolution_status=ResolutionStatus.RESOLVED,
        instrument_id=instrument_id,
        effective_date=AS_OF,
        split_ratio_from=Decimal("1"),
        split_ratio_to=ratio_to,
        knowledge_time_status=KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        source_available_at=OBSERVED_AT - timedelta(hours=1),
        first_observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID,
    )


def lifecycle(
    instrument_id: UUID = ID1,
    ticker: str = "TEST",
) -> InstrumentLifecycleObservationV1:
    return InstrumentLifecycleObservationV1(
        instrument_id=instrument_id,
        as_of_date=AS_OF,
        valid_from=date(2020, 1, 2),
        lifecycle_status=InstrumentLifecycleStatus.ACTIVE,
        ticker=ticker,
        primary_exchange="XNYS",
        first_tradable_date=date(2020, 1, 2),
        lineage_evidence_status=LineageEvidenceStatus.PROVIDER_EXPLICIT,
        source="massive",
        source_record_id=f"ticker-{ticker.lower()}",
        source_revision=1,
        knowledge_time_status=KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        source_available_at=OBSERVED_AT,
        first_observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID,
    )


def membership(
    instrument_id: UUID = ID1,
    disposition: UniverseMembershipDisposition = UniverseMembershipDisposition.INCLUDED,
) -> UniverseMembershipDecisionV1:
    is_member = {
        UniverseMembershipDisposition.INCLUDED: True,
        UniverseMembershipDisposition.EXCLUDED: False,
        UniverseMembershipDisposition.QUARANTINED: None,
    }[disposition]
    quality = (
        QualityStatus.PENDING_REVIEW
        if disposition is UniverseMembershipDisposition.QUARANTINED
        else QualityStatus.VALID
    )
    return UniverseMembershipDecisionV1(
        universe_id="primary",
        instrument_id=instrument_id,
        session_date=AS_OF,
        methodology_version="provider-form-primary-v1",
        origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        disposition=disposition,
        is_member=is_member,
        reason_codes=("provider_cs",),
        evaluated_base_fingerprint=evaluated_base_fingerprint(ID1, ID2),
        source_fingerprints=("b" * 64, "c" * 64),
        source_data_cutoff=OBSERVED_AT,
        evaluated_at=INGESTED_AT,
        quality_status=quality,
    )


def adjustment(
    instrument_id: UUID = ID1,
    price_factor: Decimal = Decimal("0.5"),
) -> AdjustmentLedgerEntryV1:
    return AdjustmentLedgerEntryV1(
        instrument_id=instrument_id,
        source_session=date(2026, 8, 26),
        basis_session=AS_OF,
        split_price_multiplier_to_basis=price_factor,
        split_volume_multiplier_to_basis=Decimal("2"),
        split_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
        total_return_multiplier_to_basis=Decimal("0.49"),
        total_return_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
        source_action_set_fingerprint="d" * 64,
        calculation_methodology_version="adjustment-ledger-v1",
        source_data_cutoff=OBSERVED_AT,
        calculated_at=INGESTED_AT,
        revision=1,
        quality_status=QualityStatus.VALID,
    )


def test_explicit_arrow_schemas_have_no_inferred_fields() -> None:
    assert CORPORATE_ACTION_OBSERVATION_ARROW_SCHEMA.names[0] == "schema_version"
    assert "first_observed_at" in CORPORATE_ACTION_OBSERVATION_ARROW_SCHEMA.names
    assert "first_observed_at" in INSTRUMENT_LIFECYCLE_ARROW_SCHEMA.names
    assert UNIVERSE_MEMBERSHIP_ARROW_SCHEMA.field("is_member").nullable
    assert ADJUSTMENT_LEDGER_ARROW_SCHEMA.field(
        "total_return_multiplier_to_basis"
    ).nullable


def test_corporate_action_round_trip_is_sorted_and_idempotent(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    records = (action("split-2", ID2), action("split-1", ID1))

    result = repository.publish_corporate_action_observations(
        records,
        provider_id="massive",
        event_year=2026,
    )
    reread = repository.read_corporate_action_observations(result.partition_path)

    assert result.status == "published"
    assert result.family is HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION
    assert result.record_count == 2
    assert tuple(row.source_action_id for row in reread) == ("split-1", "split-2")
    assert reread[0].split_ratio_to == Decimal("2")
    again = repository.publish_corporate_action_observations(
        tuple(reversed(records)),
        provider_id="massive",
        event_year=2026,
    )
    assert again.status == "already_present"
    assert again.written_record_count == 0
    assert again.logical_fingerprint == result.logical_fingerprint


def test_empty_corporate_action_observation_partition_proves_zero_source_rows(
    tmp_path,
) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)

    result = repository.publish_corporate_action_observations(
        (),
        provider_id="massive",
        event_year=2025,
    )

    assert result.record_count == 0
    assert repository.read_corporate_action_observations(result.partition_path) == ()


def test_lifecycle_round_trip_preserves_stable_identity_and_clocks(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_instrument_lifecycle(
        (lifecycle(ID2, "TESTB"), lifecycle(ID1, "TESTA")),
        as_of_date=AS_OF,
    )

    reread = repository.read_instrument_lifecycle(result.partition_path)

    assert tuple(row.instrument_id for row in reread) == (ID1, ID2)
    assert reread[0].first_observed_at == OBSERVED_AT
    assert reread[0].ticker == "TESTA"


def test_membership_round_trip_preserves_explicit_three_state(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_universe_membership(
        (
            membership(ID2, UniverseMembershipDisposition.QUARANTINED),
            membership(ID1, UniverseMembershipDisposition.INCLUDED),
        ),
        methodology_version="provider-form-primary-v1",
        session_date=AS_OF,
    )

    reread = repository.read_universe_membership(result.partition_path)

    assert reread[0].is_member is True
    assert reread[1].disposition is UniverseMembershipDisposition.QUARANTINED
    assert reread[1].is_member is None
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == "1.1"
    assert manifest["evaluated_base_count"] == 2
    assert manifest["universe_ids"] == ["primary"]
    assert manifest["disposition_summaries"] == [
        {
            "excluded_count": 0,
            "included_count": 1,
            "quarantined_count": 1,
            "universe_id": "primary",
        }
    ]


def test_membership_partition_rejects_incomplete_cross_universe_coverage(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    primary = membership(ID1)
    secondary = membership(ID2).model_copy(update={"universe_id": "secondary"})

    with pytest.raises(HistoricalResearchPersistenceError, match="same evaluated base"):
        repository.publish_universe_membership(
            (primary, secondary),
            methodology_version="provider-form-primary-v1",
            session_date=AS_OF,
        )


def test_membership_reader_rejects_tampered_coverage_manifest(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_universe_membership(
        (
            membership(ID1, UniverseMembershipDisposition.INCLUDED),
            membership(ID2, UniverseMembershipDisposition.EXCLUDED),
        ),
        methodology_version="provider-form-primary-v1",
        session_date=AS_OF,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest["disposition_summaries"][0]["excluded_count"] = 0
    result.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(HistoricalResearchCorruptionError, match="coverage manifest"):
        repository.read_universe_membership(result.partition_path)


def test_adjustment_round_trip_keeps_price_volume_and_total_return_distinct(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_adjustment_ledger(
        (adjustment(ID2, Decimal("0.25")), adjustment(ID1)),
        methodology_version="adjustment-ledger-v1",
        basis_session=AS_OF,
    )

    reread = repository.read_adjustment_ledger(result.partition_path)

    assert reread[0].split_price_multiplier_to_basis == Decimal("0.5")
    assert reread[0].split_volume_multiplier_to_basis == Decimal("2")
    assert reread[0].total_return_multiplier_to_basis == Decimal("0.49")


def test_conflicting_immutable_rerun_is_rejected(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    repository.publish_corporate_action_observations(
        (action(),),
        provider_id="massive",
        event_year=2026,
    )

    with pytest.raises(HistoricalResearchConflictError):
        repository.publish_corporate_action_observations(
            (action(ratio_to=Decimal("3")),),
            provider_id="massive",
            event_year=2026,
        )


def test_duplicate_business_key_is_rejected_before_write(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    with pytest.raises(HistoricalResearchConflictError):
        repository.publish_instrument_lifecycle(
            (lifecycle(), lifecycle()),
            as_of_date=AS_OF,
        )
    assert not (tmp_path / "market-data").exists()


def test_partition_mismatch_and_unsafe_segment_are_rejected(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    with pytest.raises(HistoricalResearchPersistenceError):
        repository.publish_corporate_action_observations(
            (action(),),
            provider_id="massive",
            event_year=2025,
        )
    with pytest.raises(HistoricalResearchPersistenceError):
        repository.publish_universe_membership(
            (membership(),),
            methodology_version="../provider-form-primary-v1",
            session_date=AS_OF,
        )


def test_tampered_parquet_and_manifest_fail_formal_reread(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_adjustment_ledger(
        (adjustment(),),
        methodology_version="adjustment-ledger-v1",
        basis_session=AS_OF,
    )
    result.parquet_path.write_bytes(result.parquet_path.read_bytes() + b"tamper")

    with pytest.raises(HistoricalResearchCorruptionError):
        repository.read_adjustment_ledger(result.partition_path)

    second_root = tmp_path / "second"
    second = ParquetHistoricalResearchRepository(second_root, created_at=INGESTED_AT)
    second_result = second.publish_instrument_lifecycle(
        (lifecycle(),),
        as_of_date=AS_OF,
    )
    manifest = json.loads(second_result.manifest_path.read_text(encoding="utf-8"))
    manifest["record_count"] = 2
    second_result.manifest_path.write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(HistoricalResearchCorruptionError):
        second.read_instrument_lifecycle(second_result.partition_path)


def test_incomplete_partition_and_symlink_root_fail_closed(tmp_path) -> None:
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    partition = (
        tmp_path
        / "market-data"
        / "instrument-lifecycle"
        / "schema_version=1"
        / "as_of_date=2026-08-27"
    )
    partition.mkdir(parents=True)
    with pytest.raises(HistoricalResearchCorruptionError):
        repository.publish_instrument_lifecycle((lifecycle(),), as_of_date=AS_OF)

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked-root"
    link.symlink_to(target, target_is_directory=True)
    linked_repository = ParquetHistoricalResearchRepository(link, created_at=INGESTED_AT)
    with pytest.raises(HistoricalResearchPersistenceError):
        linked_repository.publish_instrument_lifecycle((lifecycle(),), as_of_date=AS_OF)


def test_reader_rejects_partition_outside_repository_root(tmp_path) -> None:
    first = ParquetHistoricalResearchRepository(tmp_path / "first", created_at=INGESTED_AT)
    result = first.publish_instrument_lifecycle((lifecycle(),), as_of_date=AS_OF)
    second = ParquetHistoricalResearchRepository(tmp_path / "second", created_at=INGESTED_AT)

    with pytest.raises(HistoricalResearchPersistenceError):
        second.read_instrument_lifecycle(result.partition_path)
