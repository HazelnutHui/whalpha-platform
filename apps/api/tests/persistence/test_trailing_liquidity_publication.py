from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import (
    ShadowEligibilityStatus,
    TrailingLiquidityCandidateSummaryV1,
    TrailingLiquidityMetricStatus,
    TrailingLiquidityMetricV1,
    TrailingLiquidityShadowDecisionV1,
    TrailingLiquiditySourceSessionV1,
)
from tip_api.persistence.parquet.trailing_liquidity import (
    DECISION_SCHEMA,
    METRIC_SCHEMA,
    ParquetTrailingLiquidityRepository,
    read_completed_trailing_liquidity_publication,
)
from tip_api.persistence.trailing_liquidity import (
    TrailingLiquidityConflictError,
    TrailingLiquidityCorruptionError,
    TrailingLiquidityPersistenceError,
)
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.trailing_liquidity_publication import _validate_security_form_gates

ANALYSIS = date(2026, 8, 19)
START = date(2026, 7, 22)
END = date(2026, 8, 18)
NOW = datetime(2026, 8, 20, 5, 0, tzinfo=UTC)
IID = UUID("00000000-0000-4000-8000-000000000001")
HASH_A = "a" * 64
HASH_B = "b" * 64


def metric(*, median: Decimal | None = Decimal("20000000"), status=TrailingLiquidityMetricStatus.AVAILABLE):
    return TrailingLiquidityMetricV1(
        analysis_session=ANALYSIS,
        window_start=START,
        window_end=END,
        instrument_id=IID,
        display_ticker="AAA",
        provider_type_code="CS",
        observation_count=20 if median is not None else 19,
        previous_session=END,
        previous_close=Decimal("5"),
        median_dollar_volume_proxy_20s=median,
        metric_status=status,
        quality_flags=("adjustment_factors_unverified",),
        source_window_fingerprint=HASH_A,
        calculated_at=NOW,
    )


def decision(*, status=ShadowEligibilityStatus.PASSED, universe="provider_classified_common_shares_v1"):
    return TrailingLiquidityShadowDecisionV1(
        analysis_session=ANALYSIS,
        universe_id=universe,
        membership_evidence_as_of_date=date(2026, 8, 14),
        instrument_id=IID,
        provider_type_code="CS",
        eligibility_status=status,
        price_gate_passed=True,
        liquidity_gate_passed=True if status is ShadowEligibilityStatus.PASSED else False,
        included=status is ShadowEligibilityStatus.PASSED,
        primary_reason=status.value,
        quality_flags=("adjustment_factors_unverified",),
        decision_reasons=(status.value,),
        calculated_at=NOW,
    )


def summary():
    return TrailingLiquidityCandidateSummaryV1(
        universe_id="provider_classified_common_shares_v1",
        requested_count=1,
        passed_count=1,
        below_liquidity_count=0,
        below_price_count=0,
        missing_previous_bar_count=0,
        insufficient_history_count=0,
        full_history_count=1,
        non_null_median_count=1,
        audit_fingerprint=HASH_B,
    )


def sources():
    days = tuple(date(2026, 7, 22 + index) for index in range(10)) + tuple(date(2026, 8, 1 + index) for index in range(10))
    return tuple(
        TrailingLiquiditySourceSessionV1(
            session_date=day,
            dataset_path=f"market-data/eod-price-bars/schema_version=1/session_date={day}",
            record_count=1,
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=day,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, day in enumerate(days)
    )


def publish(root: Path):
    src = sources()
    return ParquetTrailingLiquidityRepository(root).publish(
        analysis_session=ANALYSIS,
        metrics=(metric(),),
        decisions=(decision(),),
        calendar_name="XNYS",
        calendar_version="4.13.2",
        window_sessions=tuple(item.session_date for item in src),
        source_sessions=src,
        source_descriptor_fingerprint=HASH_A,
        membership_evidence_path="market-data/provider-instrument-security-evidence/schema_version=1/as_of_date=2026-08-14",
        membership_evidence_as_of_date=date(2026, 8, 14),
        membership_evidence_fingerprint=HASH_B,
        candidates=(summary(),),
        previous_close_threshold=Decimal("5"),
        median_dollar_volume_threshold=Decimal("20000000"),
        policy_version="20-session-median-dollar-volume-proxy-v1",
        created_at=NOW,
    )


def test_explicit_arrow_schema_and_atomic_logical_publication(tmp_path: Path) -> None:
    result = publish(tmp_path)
    assert result.status == "published"
    completed = read_completed_trailing_liquidity_publication(tmp_path, analysis_session=ANALYSIS, validate_sources=False)
    assert completed.metric_record_count == 1 and completed.decision_record_count == 1
    assert METRIC_SCHEMA.field("previous_close").type.precision == 38
    assert METRIC_SCHEMA.field("previous_close").type.scale == 10
    assert DECISION_SCHEMA.field("included").type.__class__.__name__ == "DataType"
    assert completed.manifest.metric_dataset.parquet_sha256 == result.metric_parquet_sha256


def test_existing_identical_is_idempotent_and_conflict_fails(tmp_path: Path) -> None:
    publish(tmp_path)
    assert publish(tmp_path).status == "already_present"
    logical = tmp_path / "market-data/snapshots/trailing-liquidity-shadow/analysis_session=2026-08-19/manifest.json"
    logical.write_text(logical.read_text().replace(HASH_A, "c" * 64, 1))
    with pytest.raises((TrailingLiquidityConflictError, TrailingLiquidityCorruptionError)):
        publish(tmp_path)


def test_partial_target_and_symlink_fail_closed(tmp_path: Path) -> None:
    partial = tmp_path / "market-data/derived/trailing-liquidity-metrics/schema_version=1/analysis_session=2026-08-19"
    partial.mkdir(parents=True)
    with pytest.raises(TrailingLiquidityCorruptionError):
        publish(tmp_path)

    other = tmp_path / "other"
    other.mkdir()
    root = tmp_path / "linked"
    root.symlink_to(other, target_is_directory=True)
    with pytest.raises(TrailingLiquidityPersistenceError):
        publish(root)


def test_second_component_failure_cleans_staging_and_new_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tip_api.persistence.parquet.trailing_liquidity as module

    original = module.pq.write_table
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic decision write failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(module.pq, "write_table", fail_second)
    with pytest.raises(RuntimeError, match="synthetic"):
        publish(tmp_path)
    assert not list(tmp_path.rglob("*.staging.*"))
    assert not list(tmp_path.rglob("analysis_session=2026-08-19"))


def test_duplicate_or_orphan_business_keys_rejected(tmp_path: Path) -> None:
    src = sources()
    kwargs = dict(
        analysis_session=ANALYSIS, calendar_name="XNYS", calendar_version="4.13.2",
        window_sessions=tuple(item.session_date for item in src), source_sessions=src,
        source_descriptor_fingerprint=HASH_A,
        membership_evidence_path="market-data/evidence", membership_evidence_as_of_date=date(2026, 8, 14),
        membership_evidence_fingerprint=HASH_B, candidates=(summary(),),
        previous_close_threshold=Decimal(5), median_dollar_volume_threshold=Decimal(20000000),
        policy_version="v1", created_at=NOW,
    )
    with pytest.raises(TrailingLiquidityPersistenceError):
        ParquetTrailingLiquidityRepository(tmp_path).publish(metrics=(metric(), metric()), decisions=(decision(),), **kwargs)
    orphan = decision().model_copy(update={"instrument_id": UUID("00000000-0000-4000-8000-000000000002")})
    with pytest.raises(TrailingLiquidityPersistenceError):
        ParquetTrailingLiquidityRepository(tmp_path).publish(metrics=(metric(),), decisions=(orphan,), **kwargs)


def test_decimal_scale_overflow_rejected_without_rounding(tmp_path: Path) -> None:
    bad = metric(median=Decimal("20000000.00000000001"))
    src = sources()
    with pytest.raises(TrailingLiquidityPersistenceError, match="scale"):
        ParquetTrailingLiquidityRepository(tmp_path).publish(
            analysis_session=ANALYSIS, metrics=(bad,), decisions=(decision(),), calendar_name="XNYS",
            calendar_version="4.13.2", window_sessions=tuple(item.session_date for item in src), source_sessions=src,
            source_descriptor_fingerprint=HASH_A, membership_evidence_path="market-data/evidence",
            membership_evidence_as_of_date=date(2026, 8, 14), membership_evidence_fingerprint=HASH_B,
            candidates=(summary(),), previous_close_threshold=Decimal(5),
            median_dollar_volume_threshold=Decimal(20000000), policy_version="v1", created_at=NOW,
        )


@pytest.mark.parametrize("status", list(ShadowEligibilityStatus))
def test_primary_status_is_mutually_exclusive(status: ShadowEligibilityStatus) -> None:
    record = decision(status=status)
    assert record.primary_reason == status.value
    assert record.included is (status is ShadowEligibilityStatus.PASSED)


def test_candidate_a_and_b_security_form_hard_gates() -> None:
    a = decision(universe=CANDIDATE_A_ID)
    b_adrc = decision(universe=CANDIDATE_B_ID).model_copy(update={"provider_type_code": "ADRC"})
    _validate_security_form_gates((a, b_adrc))
    with pytest.raises(ValueError, match="disallowed"):
        _validate_security_form_gates((a.model_copy(update={"provider_type_code": "ETF"}),))
    with pytest.raises(ValueError, match="disallowed"):
        _validate_security_form_gates((b_adrc.model_copy(update={"provider_type_code": "WARRANT"}),))


def test_production_reconciliation_contract_counts() -> None:
    candidate_a = TrailingLiquidityCandidateSummaryV1(
        universe_id=CANDIDATE_A_ID, requested_count=1751, passed_count=1641,
        below_liquidity_count=97, below_price_count=4, missing_previous_bar_count=1,
        insufficient_history_count=8, full_history_count=1742, non_null_median_count=1738,
        audit_fingerprint=HASH_A,
    )
    candidate_b = TrailingLiquidityCandidateSummaryV1(
        universe_id=CANDIDATE_B_ID, requested_count=1864, passed_count=1747,
        below_liquidity_count=103, below_price_count=4, missing_previous_bar_count=1,
        insufficient_history_count=9, full_history_count=1854, non_null_median_count=1850,
        audit_fingerprint=HASH_B,
    )
    assert candidate_a.requested_count == sum((1641, 97, 4, 1, 8))
    assert candidate_b.requested_count == sum((1747, 103, 4, 1, 9))


def test_contract_rejects_wrong_window_future_and_incomplete_median() -> None:
    with pytest.raises(ValueError):
        metric().model_copy(update={"analysis_session": END}).model_validate(metric().model_dump() | {"analysis_session": END})
    with pytest.raises(ValueError):
        metric(median=Decimal(1)).model_copy(update={"observation_count": 19}).model_validate(
            metric(median=Decimal(1)).model_dump() | {"observation_count": 19}
        )


def test_cli_argument_contract_without_touching_data() -> None:
    from tip_api.services.trailing_liquidity_shadow_cli import main

    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        main(["--unknown"])
    assert error.value.code == 2
