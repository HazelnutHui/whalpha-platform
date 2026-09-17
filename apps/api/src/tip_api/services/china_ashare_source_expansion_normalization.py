"""Normalize one resolved A-share raw-source expansion partition."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_population_package import (
    ChinaAsharePopulationPackageResultV1,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    ChinaAshareSourceExpansionPartitionResultV1,
    ChinaAshareSourceExpansionPlanResultV1,
)
from tip_api.providers.china_ashare.baostock_adapter import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
)


_PROVIDER_SEMANTICS = (
    "BaoStock adjustFactor, foreAdjustFactor, and backAdjustFactor source "
    "observation; direction and total-return semantics are not reconciled"
)


class ChinaAshareSourceExpansionNormalizationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedChinaAshareSourceExpansionPartitionV1:
    bars: tuple[ChinaAshareDailyBarV1, ...]
    states: tuple[ChinaAshareDailyTradingStateV1, ...]
    adjustments: tuple[ChinaAshareAdjustmentFactorObservationV1, ...]
    resolved_target_count: int
    quarantined_target_ids: tuple[str, ...]
    quarantined_daily_row_count: int
    quarantined_adjustment_row_count: int


def normalize_china_ashare_source_expansion_partition(
    *,
    population_package: ChinaAsharePopulationPackageResultV1,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    source_partition: ChinaAshareSourceExpansionPartitionResultV1,
) -> NormalizedChinaAshareSourceExpansionPartitionV1:
    plan = plan_result.plan
    partition = source_partition.partition
    if plan.population_package_fingerprint != (
        population_package.manifest.logical_fingerprint
    ):
        raise ChinaAshareSourceExpansionNormalizationError(
            "normalization population differs from source plan"
        )
    if source_partition.manifest.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAshareSourceExpansionNormalizationError(
            "normalization source partition differs from plan"
        )
    occurrences_by_fingerprint = {
        item.logical_fingerprint: item for item in population_package.occurrences
    }
    occurrences_by_source = {}
    quarantined_target_ids = []
    for target in partition.targets:
        occurrence = occurrences_by_fingerprint.get(
            target.population_occurrence_fingerprint
        )
        if occurrence is None or occurrence.source_security_id != (
            target.source_security_id
        ):
            raise ChinaAshareSourceExpansionNormalizationError(
                "normalization target differs from population occurrence"
            )
        if occurrence.disposition is not target.disposition:
            raise ChinaAshareSourceExpansionNormalizationError(
                "normalization target disposition differs"
            )
        occurrences_by_source[target.source_security_id] = occurrence
        if target.disposition is ChinaAsharePopulationDisposition.QUARANTINED:
            quarantined_target_ids.append(target.source_security_id)

    bars = []
    states = []
    adjustments = []
    quarantined_daily_row_count = 0
    quarantined_adjustment_row_count = 0
    for row in source_partition.captured.daily_rows:
        occurrence = occurrences_by_source[row.source_security_id]
        if occurrence.disposition is ChinaAsharePopulationDisposition.QUARANTINED:
            quarantined_daily_row_count += 1
            continue
        if occurrence.instrument_id is None:
            raise ChinaAshareSourceExpansionNormalizationError(
                "resolved normalization target lacks stable identity"
            )
        trading_status = _trading_status(row.provider_trade_status)
        risk_warning_status = _risk_warning_status(row.provider_risk_warning)
        state_reasons = [
            "price_limit_requires_official_rule_resolution",
            "source_available_time_unreported",
        ]
        if trading_status is ChinaAshareTradingStatus.UNKNOWN:
            state_reasons.append("trading_status_unavailable")
        if risk_warning_status is ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED:
            state_reasons.append("risk_warning_subtype_unavailable")
        elif risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN:
            state_reasons.append("risk_warning_state_unavailable")
        states.append(
            ChinaAshareDailyTradingStateV1(
                instrument_id=occurrence.instrument_id,
                session_date=row.session_date,
                exchange=occurrence.exchange,
                board=occurrence.board,
                trading_status=trading_status,
                risk_warning_status=risk_warning_status,
                price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
                pre_close=_optional_decimal(row.pre_close, field_name="pre_close"),
                up_limit=None,
                down_limit=None,
                exact_limit_prices_source_observed=False,
                source=BAOSTOCK_ASHARE_PROVIDER_ID,
                source_available_at=None,
                ingested_at=row.ingested_at,
                quality_status=QualityStatus.WARNING,
                reason_codes=tuple(state_reasons),
            )
        )
        if trading_status is ChinaAshareTradingStatus.SUSPENDED:
            continue
        bars.append(
            ChinaAshareDailyBarV1(
                instrument_id=occurrence.instrument_id,
                session_date=row.session_date,
                open=_required_decimal(row.open, field_name="open"),
                high=_required_decimal(row.high, field_name="high"),
                low=_required_decimal(row.low, field_name="low"),
                close=_required_decimal(row.close, field_name="close"),
                pre_close=_required_decimal(row.pre_close, field_name="pre_close"),
                volume_shares=_required_decimal(row.volume, field_name="volume"),
                turnover_amount_cny=_required_decimal(
                    row.amount, field_name="amount"
                ),
                source=BAOSTOCK_ASHARE_PROVIDER_ID,
                source_record_id=(
                    f"{row.source_security_id}:{row.session_date.isoformat()}"
                ),
                source_available_at=None,
                ingested_at=row.ingested_at,
                revision=1,
                quality_status=QualityStatus.WARNING,
                reason_codes=("source_available_time_unreported",),
            )
        )

    for row in source_partition.captured.adjustment_rows:
        occurrence = occurrences_by_source[row.source_security_id]
        if occurrence.disposition is ChinaAsharePopulationDisposition.QUARANTINED:
            quarantined_adjustment_row_count += 1
            continue
        if occurrence.instrument_id is None:
            raise ChinaAshareSourceExpansionNormalizationError(
                "resolved adjustment target lacks stable identity"
            )
        adjustments.append(
            ChinaAshareAdjustmentFactorObservationV1(
                instrument_id=occurrence.instrument_id,
                session_date=row.session_date,
                provider_factor=row.provider_factor,
                fore_adjust_factor=row.fore_adjust_factor,
                back_adjust_factor=row.back_adjust_factor,
                provider_semantics=_PROVIDER_SEMANTICS,
                source=BAOSTOCK_ASHARE_PROVIDER_ID,
                source_available_at=None,
                ingested_at=row.ingested_at,
                normalized_return_authorized=False,
                quality_status=QualityStatus.WARNING,
                reason_codes=(
                    "return_semantics_unreconciled",
                    "source_available_time_unreported",
                ),
            )
        )

    ordered_bars = tuple(
        sorted(bars, key=lambda item: (str(item.instrument_id), item.session_date))
    )
    ordered_states = tuple(
        sorted(states, key=lambda item: (str(item.instrument_id), item.session_date))
    )
    ordered_adjustments = tuple(
        sorted(
            adjustments,
            key=lambda item: (str(item.instrument_id), item.session_date),
        )
    )
    _unique_keys(ordered_bars, label="bar")
    _unique_keys(ordered_states, label="state")
    _unique_keys(ordered_adjustments, label="adjustment")
    return NormalizedChinaAshareSourceExpansionPartitionV1(
        bars=ordered_bars,
        states=ordered_states,
        adjustments=ordered_adjustments,
        resolved_target_count=(
            len(partition.targets) - len(quarantined_target_ids)
        ),
        quarantined_target_ids=tuple(sorted(quarantined_target_ids)),
        quarantined_daily_row_count=quarantined_daily_row_count,
        quarantined_adjustment_row_count=quarantined_adjustment_row_count,
    )


def _trading_status(value: str) -> ChinaAshareTradingStatus:
    normalized = str(value).strip()
    if normalized == "1":
        return ChinaAshareTradingStatus.TRADING
    if normalized == "0":
        return ChinaAshareTradingStatus.SUSPENDED
    return ChinaAshareTradingStatus.UNKNOWN


def _risk_warning_status(value: str) -> ChinaAshareRiskWarningStatus:
    normalized = str(value).strip()
    if normalized == "0":
        return ChinaAshareRiskWarningStatus.NONE
    if normalized == "1":
        return ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED
    return ChinaAshareRiskWarningStatus.UNKNOWN


def _required_decimal(value: str, *, field_name: str) -> Decimal:
    normalized = str(value).strip()
    if not normalized:
        raise ChinaAshareSourceExpansionNormalizationError(
            f"normalization {field_name} is missing"
        )
    try:
        result = Decimal(normalized)
    except InvalidOperation as exc:
        raise ChinaAshareSourceExpansionNormalizationError(
            f"normalization {field_name} is invalid"
        ) from exc
    if not result.is_finite():
        raise ChinaAshareSourceExpansionNormalizationError(
            f"normalization {field_name} is invalid"
        )
    return result


def _optional_decimal(value: str, *, field_name: str) -> Decimal | None:
    return None if not str(value).strip() else _required_decimal(
        value, field_name=field_name
    )


def _unique_keys(rows: tuple[object, ...], *, label: str) -> None:
    keys = tuple(
        (str(getattr(item, "instrument_id")), getattr(item, "session_date"))
        for item in rows
    )
    if keys != tuple(sorted(set(keys))):
        raise ChinaAshareSourceExpansionNormalizationError(
            f"normalized {label} keys differ"
        )
