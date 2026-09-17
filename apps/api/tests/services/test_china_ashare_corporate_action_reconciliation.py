from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
    build_corporate_action_observation,
)
from tip_api.contracts.common import QualityStatus
from tip_api.services.china_ashare_corporate_action_reconciliation import (
    ChinaAshareDistributionCrosscheckV1,
    _parse_ths_distribution_terms,
    build_corporate_action_reconciliation_for_pilot,
)


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "10派191.06元(含税)",
            (Decimal("19.106"), Decimal("0"), Decimal("0")),
        ),
        (
            "10送1股转增2股派3.5元(含税)",
            (Decimal("0.35"), Decimal("0.1"), Decimal("0.2")),
        ),
    ],
)
def test_ths_distribution_terms_are_normalized_per_share(description, expected) -> None:
    assert _parse_ths_distribution_terms(description) == expected


def test_reconciliation_matches_action_against_both_factor_directions() -> None:
    now = datetime(2026, 9, 17, tzinfo=UTC)
    instrument_id = UUID("00000000-0000-0000-0000-000000600519")
    action = build_corporate_action_observation(
        instrument_id=instrument_id,
        source_security_id="sh.600519",
        action_type="cash_dividend",
        implementation_announcement_date=date(2023, 12, 14),
        record_date=date(2023, 12, 19),
        ex_date=date(2023, 12, 20),
        payment_date=date(2023, 12, 20),
        cash_dividend_per_share_cny=Decimal("0.2"),
        bonus_share_ratio=Decimal("0"),
        capitalization_ratio=Decimal("0"),
        action_description="10派2元",
        source="test_cninfo",
        source_retrieved_at=now,
        raw_payload_sha256="a" * 64,
        quality_status=QualityStatus.WARNING,
        reason_codes=("implementation_terms_observed",),
        normalized_return_authorized=False,
    )
    factor_step = Decimal("10") / Decimal("9.8")
    adjustments = (
        ChinaAshareAdjustmentFactorObservationV1(
            instrument_id=instrument_id,
            session_date=date(2020, 1, 2),
            provider_factor=Decimal("1"),
            fore_adjust_factor=Decimal("1"),
            back_adjust_factor=Decimal("1"),
            provider_semantics="test",
            source="test",
            ingested_at=now,
            quality_status=QualityStatus.WARNING,
        ),
        ChinaAshareAdjustmentFactorObservationV1(
            instrument_id=instrument_id,
            session_date=date(2023, 12, 20),
            provider_factor=factor_step,
            fore_adjust_factor=factor_step,
            back_adjust_factor=factor_step,
            provider_semantics="test",
            source="test",
            ingested_at=now,
            quality_status=QualityStatus.WARNING,
        ),
    )
    bars = tuple(
        ChinaAshareDailyBarV1(
            instrument_id=instrument_id,
            session_date=session_date,
            open=close,
            high=close,
            low=close,
            close=close,
            pre_close=pre_close,
            volume_shares=Decimal("100"),
            turnover_amount_cny=Decimal("1000"),
            source="test",
            ingested_at=now,
            revision=1,
            quality_status=QualityStatus.VALID,
        )
        for session_date, close, pre_close in (
            (date(2023, 12, 19), Decimal("10"), Decimal("10")),
            (date(2023, 12, 20), Decimal("9.8"), Decimal("9.8")),
        )
    )
    package = SimpleNamespace(
        plan=SimpleNamespace(
            history_start_date=date(2021, 9, 16),
            history_end_date=date(2026, 9, 16),
        ),
        manifest=SimpleNamespace(logical_fingerprint="b" * 64),
        captured=SimpleNamespace(
            identity_decisions=(
                SimpleNamespace(
                    pilot_instrument_id=instrument_id,
                    source_security_id="sh.600519",
                ),
            ),
            daily_batch=SimpleNamespace(bars=bars),
        ),
    )
    report = build_corporate_action_reconciliation_for_pilot(
        daily_package=package,
        actions=(action,),
        full_adjustments=adjustments,
        crosschecks=(
            ChinaAshareDistributionCrosscheckV1(
                source_security_id="sh.600519",
                ex_date=action.ex_date,
                record_date=action.record_date,
                cash_dividend_per_share_cny=Decimal("0.2"),
                bonus_share_ratio=Decimal("0"),
                capitalization_ratio=Decimal("0"),
            ),
        ),
        raw_upstream_payload_retained=True,
        evaluated_at=now,
    )

    assert report.matched_action_count == 1
    assert report.factor_conflict_count == 0
    assert report.corporate_action_family_complete is True
    assert report.research_backtest_authorized is False
