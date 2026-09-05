from __future__ import annotations

import hashlib
import socket
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    EodHistoryMethodologyMode,
    FullBaseDisposition,
    InstrumentType,
    TrailingLiquidityEligibilityStatus,
    TrailingLiquidityResultV1,
)
from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus,
    EvidenceGrade,
    ProviderInstrumentSecurityEvidenceV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotReadResult
from tip_api.providers.massive.instrument_master_snapshot import (
    build_snapshot_from_payloads,
)
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.historical_identity_rebuild_profile_map import (
    HistoricalIdentityRebuildProfileBindingV1,
    PRE_ETV_IDENTITY_REBUILD_PROFILE,
    historical_identity_profile_fingerprint,
)
from tip_api.services.historical_universe_membership_shadow import (
    HistoricalUniverseMembershipShadowError,
    _apply_historical_identity_rebuild_profile,
    _validate_identity_profile_binding,
    _validate_policy_relationship,
    build_complete_point_in_time_source_decisions,
    read_identity_replay_ingested_at,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
    _paths_overlap,
)

SESSION = date(2026, 9, 3)
PREVIOUS = date(2026, 9, 2)
NOW = datetime(2026, 9, 4, tzinfo=UTC)
SHA = "a" * 64


def _identity_read_with_replay_times(
    tmp_path: Path,
    *,
    instrument_time: datetime,
    identity_time: datetime,
    resolver_time: datetime,
) -> InstrumentMasterSnapshotReadResult:
    partitions = []
    for family, replay_time in (
        ("instrument", instrument_time),
        ("identity", identity_time),
        ("resolver", resolver_time),
    ):
        partition = tmp_path / family
        partition.mkdir()
        table = pa.table(
            {
                "ingested_at": pa.array(
                    [replay_time],
                    type=pa.timestamp("us", tz="UTC"),
                )
            }
        )
        pq.write_table(table, partition / "part-00000.parquet")
        partitions.append(partition)
    return InstrumentMasterSnapshotReadResult(
        schema_version="1",
        as_of_date=SESSION,
        provider_id="massive_stocks_basic",
        instrument_count=1,
        identity_count=1,
        resolver_count=1,
        instrument_partition_path=partitions[0],
        identity_partition_path=partitions[1],
        resolver_partition_path=partitions[2],
        snapshot_manifest_path=tmp_path / "manifest.json",
        instrument_content_sha256="1" * 64,
        identity_content_sha256="2" * 64,
        resolver_content_sha256="3" * 64,
        snapshot_content_sha256="4" * 64,
        created_at=NOW,
    )


def test_identity_replay_time_reads_one_shared_canonical_row_timestamp(
    tmp_path: Path,
) -> None:
    replay_time = datetime(2026, 8, 16, 13, 35, tzinfo=UTC)
    identity = _identity_read_with_replay_times(
        tmp_path,
        instrument_time=replay_time,
        identity_time=replay_time,
        resolver_time=replay_time,
    )

    assert read_identity_replay_ingested_at(identity) == replay_time


def test_identity_replay_time_rejects_family_timestamp_disagreement(
    tmp_path: Path,
) -> None:
    replay_time = datetime(2026, 8, 16, 13, 35, tzinfo=UTC)
    identity = _identity_read_with_replay_times(
        tmp_path,
        instrument_time=replay_time,
        identity_time=replay_time,
        resolver_time=datetime(2026, 8, 16, 13, 36, tzinfo=UTC),
    )

    with pytest.raises(
        HistoricalUniverseMembershipShadowError,
        match="do not share one replay timestamp",
    ):
        read_identity_replay_ingested_at(identity)


def test_legacy_etv_profile_changes_only_the_versioned_noninstrument_identity() -> None:
    current = build_snapshot_from_payloads(
        payloads=({"ticker": "TESTV", "type": "ETV"},),
        as_of_date=SESSION,
        ingested_at=NOW,
        request_count=1,
        pagination_complete=True,
    )

    legacy = _apply_historical_identity_rebuild_profile(
        current,
        rebuild_profile=PRE_ETV_IDENTITY_REBUILD_PROFILE,
    )

    assert current.identities[0].resolution_status.value == "excluded"
    assert current.identities[0].quality_status.value == "warning"
    assert current.identities[0].quality_flags == ("exchange_traded_vehicle",)
    assert legacy.instruments == current.instruments == ()
    assert legacy.resolvers == current.resolvers == ()
    assert legacy.identities[0].resolution_status.value == "rejected"
    assert legacy.identities[0].quality_status.value == "rejected"
    assert legacy.identities[0].quality_flags == ("unknown_provider_type_etv",)
    assert legacy.expected_exclusion_count == current.expected_exclusion_count - 1
    assert legacy.malformed_rejected_count == current.malformed_rejected_count + 1
    assert dict(legacy.category_counts) == {"malformed": 1}
    assert dict(legacy.unknown_type_counts) == {"ETV": 1}


def test_membership_rejects_package_that_differs_from_profile_binding(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "identity-package"
    package_path.mkdir()
    binding_values = {
        "session_date": SESSION.isoformat(),
        "rebuild_profile": PRE_ETV_IDENTITY_REBUILD_PROFILE,
        "source_locator_sha256": hashlib.sha256(
            str(package_path.resolve()).encode("utf-8")
        ).hexdigest(),
        "package_manifest_sha256": "1" * 64,
        "package_content_sha256": "2" * 64,
        "package_fetched_at": "2026-09-04T00:00:00Z",
        "canonical_snapshot_fingerprint": "3" * 64,
        "canonical_instrument_fingerprint": "4" * 64,
        "canonical_identity_fingerprint": "5" * 64,
        "canonical_resolver_fingerprint": "6" * 64,
    }
    binding = HistoricalIdentityRebuildProfileBindingV1.model_validate(
        {
            **binding_values,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                binding_values
            ),
        }
    )
    equivalence = SimpleNamespace(
        rebuild_profile=PRE_ETV_IDENTITY_REBUILD_PROFILE,
        package=SimpleNamespace(
            package_manifest_sha256="9" * 64,
            manifest=SimpleNamespace(
                package_content_sha256="2" * 64,
                fetched_at=datetime(2026, 9, 4, tzinfo=UTC),
            ),
        ),
        identity=SimpleNamespace(
            snapshot_content_sha256="3" * 64,
            instrument_content_sha256="4" * 64,
            identity_content_sha256="5" * 64,
            resolver_content_sha256="6" * 64,
        ),
    )

    with pytest.raises(
        HistoricalUniverseMembershipShadowError,
        match="package custody mismatch",
    ):
        _validate_identity_profile_binding(
            binding=binding,
            package_path=package_path,
            equivalence=equivalence,
            session_date=SESSION,
        )


def iid(number: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{number:012d}")


def evidence(instrument_id: UUID, code: str, *, exchange: str = "XNYS") -> ProviderInstrumentSecurityEvidenceV1:
    form = {
        "CS": SecurityForm.COMMON_SHARE,
        "ADRC": SecurityForm.ADR_ADS,
        "ETF": SecurityForm.FUND_SHARE,
    }[code]
    return ProviderInstrumentSecurityEvidenceV1(
        as_of_date=SESSION,
        instrument_id=instrument_id,
        provider="massive_stocks_basic",
        provider_ticker=f"T{str(instrument_id)[-2:]}",
        provider_type_code=code,
        provider_type_description=code,
        primary_exchange=exchange,
        security_form_evidence=form,
        evidence_source="/v3/reference/tickers",
        evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,
        classification_status=(
            ClassificationStatus.EXCLUDED_RESOLVED
            if code == "ETF"
            else ClassificationStatus.UNKNOWN
        ),
        universe_disposition=(
            UniverseDisposition.EXCLUDED
            if code == "ETF"
            else UniverseDisposition.QUARANTINE
        ),
        decision_flags=("provider_security_form_only",),
        review_flags=("issuer_structure_unresolved",),
        provider_observation_ids=(SHA,),
        observed_at=NOW,
        ingested_at=NOW,
    )


def bar(
    instrument_id: UUID,
    session: date,
    *,
    close: str = "10",
    exchange: str = "XNYS",
) -> EodMarketBarReadModel:
    value = Decimal(close)
    return EodMarketBarReadModel(
        instrument_id=instrument_id,
        ticker=f"T{str(instrument_id)[-2:]}",
        name="Test",
        instrument_type=InstrumentType.COMMON_STOCK,
        primary_exchange=exchange,
        session_date=session,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("3000000"),
        vwap=value,
        trade_count=100,
        currency="USD",
        source="fixture",
        quality_status=QualityStatus.WARNING,
        quality_flags=("adjustment_factors_unverified",),
    )


def trailing(
    instrument_id: UUID,
    status: TrailingLiquidityEligibilityStatus = TrailingLiquidityEligibilityStatus.PASSED,
) -> TrailingLiquidityResultV1:
    return TrailingLiquidityResultV1(
        instrument_id=instrument_id,
        analysis_session=SESSION,
        window_start=date(2026, 8, 5),
        window_end=PREVIOUS,
        observed_observation_count=20,
        missing_observation_count=0,
        median_dollar_volume_proxy=Decimal("30000000"),
        threshold=Decimal("20000000"),
        price_gate_status="passed",
        liquidity_gate_status=("passed" if status is TrailingLiquidityEligibilityStatus.PASSED else "failed"),
        eligibility_status=status,
        reason_codes=("adjustment_factors_unverified",),
        source_session_fingerprints=(),
        methodology_mode=EodHistoryMethodologyMode.CURRENT_AS_OF_CONSTITUENT_LIQUIDITY,
        policy_version="fixture",
        fingerprint=SHA,
    )


def build(
    ids: tuple[UUID, ...],
    *,
    source_evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    source_quarantines: dict[UUID, tuple[str, ...]] | None = None,
    current: tuple[EodMarketBarReadModel, ...] | None = None,
    previous: tuple[EodMarketBarReadModel, ...] | None = None,
    liquidity: tuple[TrailingLiquidityResultV1, ...] | None = None,
):
    return build_complete_point_in_time_source_decisions(
        session_date=SESSION,
        evaluated_base_ids=frozenset(ids),
        evidence=source_evidence,
        source_quarantines=source_quarantines or {},
        current_bars=current if current is not None else tuple(bar(item, SESSION) for item in ids),
        previous_bars=previous if previous is not None else tuple(bar(item, PREVIOUS) for item in ids),
        trailing_results=liquidity if liquidity is not None else tuple(trailing(item) for item in ids),
        calculated_at=NOW,
    )


def test_complete_identity_base_keeps_type_exclusion_separate_from_quarantine() -> None:
    cs, adr, etf, missing, collision = (iid(index) for index in range(1, 6))
    ids = (cs, adr, etf, missing, collision)
    records = build(
        ids,
        source_evidence=(evidence(cs, "CS"), evidence(adr, "ADRC"), evidence(etf, "ETF")),
        source_quarantines={collision: ("provider_stable_id_collision",)},
    )
    by_key = {(item.policy_id, item.instrument_id): item for item in records}

    assert len(records) == len(ids) * 2
    assert by_key[(FULL_BASE_A_ID, cs)].disposition is FullBaseDisposition.INCLUDED
    assert by_key[(FULL_BASE_B_ID, cs)].disposition is FullBaseDisposition.INCLUDED
    assert by_key[(FULL_BASE_A_ID, adr)].disposition is FullBaseDisposition.TARGET_SECURITY_FORM
    assert by_key[(FULL_BASE_B_ID, adr)].disposition is FullBaseDisposition.INCLUDED
    assert by_key[(FULL_BASE_A_ID, etf)].disposition is FullBaseDisposition.TARGET_SECURITY_FORM
    assert by_key[(FULL_BASE_B_ID, etf)].disposition is FullBaseDisposition.TARGET_SECURITY_FORM
    for instrument_id in (missing, collision):
        assert by_key[(FULL_BASE_A_ID, instrument_id)].disposition is FullBaseDisposition.INVALID_INPUT
        assert by_key[(FULL_BASE_B_ID, instrument_id)].disposition is FullBaseDisposition.INVALID_INPUT


def test_risk_and_tradability_gates_do_not_become_false_membership() -> None:
    outlier, missing_current, low_price, illiquid = (iid(index) for index in range(11, 15))
    ids = (outlier, missing_current, low_price, illiquid)
    current = (
        bar(outlier, SESSION, close="20"),
        bar(low_price, SESSION, close="4"),
        bar(illiquid, SESSION),
    )
    previous = (
        bar(outlier, PREVIOUS, close="10"),
        bar(missing_current, PREVIOUS),
        bar(low_price, PREVIOUS, close="4"),
        bar(illiquid, PREVIOUS),
    )
    liquidity = tuple(
        trailing(
            item,
            TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD
            if item == illiquid
            else TrailingLiquidityEligibilityStatus.PASSED,
        )
        for item in ids
    )
    records = build(
        ids,
        source_evidence=tuple(evidence(item, "CS") for item in ids),
        current=current,
        previous=previous,
        liquidity=liquidity,
    )
    primary = {
        item.instrument_id: item
        for item in records
        if item.policy_id == FULL_BASE_A_ID
    }

    assert primary[outlier].disposition is FullBaseDisposition.OUTLIER_QUARANTINE
    assert primary[missing_current].disposition is FullBaseDisposition.MISSING_CURRENT_BAR
    assert primary[low_price].disposition is FullBaseDisposition.BELOW_PREVIOUS_CLOSE
    assert primary[illiquid].disposition is FullBaseDisposition.BELOW_TRAILING_LIQUIDITY


def test_trailing_ledger_must_exactly_cover_the_identity_base() -> None:
    first, second = iid(21), iid(22)
    with pytest.raises(ValueError, match="exactly cover"):
        build(
            (first, second),
            source_evidence=(evidence(first, "CS"), evidence(second, "CS")),
            liquidity=(trailing(first),),
        )


def test_conflicting_same_instrument_security_evidence_is_quarantined() -> None:
    instrument_id = iid(31)
    records = build(
        (instrument_id,),
        source_evidence=(
            evidence(instrument_id, "CS"),
            evidence(instrument_id, "ADRC"),
        ),
    )
    assert all(item.disposition is FullBaseDisposition.INVALID_INPUT for item in records)
    assert all(
        "conflicting_provider_security_evidence_for_instrument" in item.reason_codes
        for item in records
    )


def test_shadow_cli_path_and_network_boundaries() -> None:
    assert _paths_overlap(Path("/tmp/output"), Path("/tmp/output/source"))
    assert not _paths_overlap(Path("/tmp/output"), Path("/data/source"))
    with _network_disabled(), pytest.raises(RuntimeError, match="network access is disabled"):
        socket.socket()


def test_primary_must_remain_a_subset_of_secondary() -> None:
    instrument_id = iid(41)
    records = build(
        (instrument_id,),
        source_evidence=(evidence(instrument_id, "CS"),),
    )
    broken = tuple(
        item.model_copy(
            update={
                "disposition": FullBaseDisposition.TARGET_SECURITY_FORM,
                "included": False,
            }
        )
        if item.policy_id == FULL_BASE_B_ID
        else item
        for item in records
    )

    with pytest.raises(ValueError, match="not a subset"):
        _validate_policy_relationship(broken)
