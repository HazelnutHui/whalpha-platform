"""Reconcile A-share cash/share distributions against adjustment-factor steps."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable
from uuid import UUID

from tip_api.contracts.china_ashare.v1.corporate_actions import (
    ChinaAshareAdjustmentActionReconciliationV1,
    ChinaAshareAdjustmentReconciliationStatus,
    ChinaAshareCorporateActionObservationV1,
    ChinaAshareCorporateActionReconciliationReportV1,
    build_corporate_action_reconciliation_report,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
)


ADJUSTMENT_STEP_RELATIVE_TOLERANCE = Decimal("0.000005")
EASTMONEY_DISTRIBUTION_CROSSCHECK_SOURCE = "eastmoney_stock_fhps_detail_em"
THS_DISTRIBUTION_CROSSCHECK_SOURCE = "tonghuashun_stock_fhps_detail_ths"


@dataclass(frozen=True, slots=True)
class ChinaAshareDistributionCrosscheckV1:
    """Independent normalized distribution terms used only for reconciliation."""

    source_security_id: str
    ex_date: date
    record_date: date
    cash_dividend_per_share_cny: Decimal
    bonus_share_ratio: Decimal
    capitalization_ratio: Decimal
    source: str = EASTMONEY_DISTRIBUTION_CROSSCHECK_SOURCE


def capture_eastmoney_distribution_crosschecks(
    *,
    source_security_ids: tuple[str, ...],
    start_date: date,
    end_date: date,
) -> tuple[ChinaAshareDistributionCrosscheckV1, ...]:
    """Capture implemented Eastmoney rows through AKShare for independent checking.

    This function performs network work only when explicitly called. The returned
    normalized rows are supporting observations, not canonical corporate actions.
    """

    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - environment boundary
        raise RuntimeError("AKShare is required for Eastmoney cross-check capture") from exc
    rows: list[ChinaAshareDistributionCrosscheckV1] = []
    seen: set[tuple[str, date]] = set()
    for source_security_id in tuple(sorted(set(source_security_ids))):
        symbol = _source_symbol(source_security_id)
        frame = ak.stock_fhps_detail_em(symbol=symbol)
        required = {
            "股权登记日",
            "除权除息日",
            "方案进度",
            "送转股份-送股比例",
            "送转股份-转股比例",
            "现金分红-现金分红比例",
        }
        if not required.issubset(set(frame.columns)):
            raise ValueError("Eastmoney distribution schema differs")
        for raw in frame.to_dict(orient="records"):
            if str(raw.get("方案进度") or "").strip() != "实施分配":
                continue
            ex_date = _optional_frame_date(raw.get("除权除息日"))
            record_date = _optional_frame_date(raw.get("股权登记日"))
            if ex_date is None or not start_date <= ex_date <= end_date:
                continue
            if record_date is None:
                raise ValueError("Eastmoney implemented distribution lacks record date")
            key = (source_security_id, ex_date)
            if key in seen:
                raise ValueError("Eastmoney distribution cross-check has duplicate ex-date")
            seen.add(key)
            rows.append(
                ChinaAshareDistributionCrosscheckV1(
                    source_security_id=source_security_id,
                    ex_date=ex_date,
                    record_date=record_date,
                    cash_dividend_per_share_cny=(
                        _frame_decimal(raw.get("现金分红-现金分红比例")) / Decimal("10")
                    ),
                    bonus_share_ratio=(
                        _frame_decimal(raw.get("送转股份-送股比例")) / Decimal("10")
                    ),
                    capitalization_ratio=(
                        _frame_decimal(raw.get("送转股份-转股比例")) / Decimal("10")
                    ),
                )
            )
    return tuple(sorted(rows, key=lambda item: (item.source_security_id, item.ex_date)))


def capture_ths_distribution_crosschecks(
    *,
    source_security_ids: tuple[str, ...],
    start_date: date,
    end_date: date,
) -> tuple[ChinaAshareDistributionCrosscheckV1, ...]:
    """Capture implemented Tonghuashun rows through AKShare for cross-checking."""

    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - environment boundary
        raise RuntimeError("AKShare is required for Tonghuashun cross-check capture") from exc
    rows: list[ChinaAshareDistributionCrosscheckV1] = []
    seen: set[tuple[str, date]] = set()
    for source_security_id in tuple(sorted(set(source_security_ids))):
        frame = ak.stock_fhps_detail_ths(symbol=_source_symbol(source_security_id))
        required = {
            "分红方案说明",
            "A股股权登记日",
            "A股除权除息日",
            "方案进度",
        }
        if not required.issubset(set(frame.columns)):
            raise ValueError("Tonghuashun distribution schema differs")
        for raw in frame.to_dict(orient="records"):
            if str(raw.get("方案进度") or "").strip() != "实施方案":
                continue
            ex_date = _optional_frame_date(raw.get("A股除权除息日"))
            record_date = _optional_frame_date(raw.get("A股股权登记日"))
            if ex_date is None or not start_date <= ex_date <= end_date:
                continue
            if record_date is None:
                raise ValueError("Tonghuashun implemented distribution lacks record date")
            key = (source_security_id, ex_date)
            if key in seen:
                raise ValueError("Tonghuashun distribution cross-check has duplicate ex-date")
            seen.add(key)
            cash, bonus, capitalization = _parse_ths_distribution_terms(
                str(raw.get("分红方案说明") or "")
            )
            rows.append(
                ChinaAshareDistributionCrosscheckV1(
                    source_security_id=source_security_id,
                    ex_date=ex_date,
                    record_date=record_date,
                    cash_dividend_per_share_cny=cash,
                    bonus_share_ratio=bonus,
                    capitalization_ratio=capitalization,
                    source=THS_DISTRIBUTION_CROSSCHECK_SOURCE,
                )
            )
    return tuple(sorted(rows, key=lambda item: (item.source_security_id, item.ex_date)))


def build_corporate_action_reconciliation_for_pilot(
    *,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    actions: tuple[ChinaAshareCorporateActionObservationV1, ...],
    full_adjustments: tuple[ChinaAshareAdjustmentFactorObservationV1, ...],
    crosschecks: tuple[ChinaAshareDistributionCrosscheckV1, ...],
    raw_upstream_payload_retained: bool,
    evaluated_at: datetime,
    tolerance: Decimal = ADJUSTMENT_STEP_RELATIVE_TOLERANCE,
) -> ChinaAshareCorporateActionReconciliationReportV1:
    """Build a deterministic reconciliation report for the bounded daily pilot."""

    if tolerance <= 0:
        raise ValueError("adjustment reconciliation tolerance must be positive")
    start_date = daily_package.plan.history_start_date
    end_date = daily_package.plan.history_end_date
    source_by_instrument = {
        item.pilot_instrument_id: item.source_security_id
        for item in daily_package.captured.identity_decisions
        if item.pilot_instrument_id is not None
    }
    if not source_by_instrument:
        raise ValueError("daily package has no bound pilot instruments")
    expected_instruments = frozenset(source_by_instrument)
    if any(item.instrument_id not in expected_instruments for item in actions):
        raise ValueError("corporate action falls outside pilot instruments")
    if any(item.instrument_id not in expected_instruments for item in full_adjustments):
        raise ValueError("adjustment observation falls outside pilot instruments")
    action_keys = [(item.instrument_id, item.ex_date) for item in actions]
    if len(action_keys) != len(set(action_keys)):
        raise ValueError("corporate actions must be unique by instrument and ex-date")
    adjustment_keys = [(item.instrument_id, item.session_date) for item in full_adjustments]
    if len(adjustment_keys) != len(set(adjustment_keys)):
        raise ValueError("adjustments must be unique by instrument and session")
    if any(not start_date <= item.ex_date <= end_date for item in actions):
        raise ValueError("corporate action falls outside daily package interval")

    cross_source_reconciled = _crosschecks_reconcile(actions, crosschecks)
    actions_by_key = {(item.instrument_id, item.ex_date): item for item in actions}
    adjustments_by_instrument = _adjustments_by_instrument(full_adjustments)
    bars_by_instrument = _bars_by_instrument(daily_package.captured.daily_batch.bars)
    decisions: list[ChinaAshareAdjustmentActionReconciliationV1] = []

    for instrument_id in sorted(expected_instruments, key=str):
        source_security_id = source_by_instrument[instrument_id]
        adjustments = adjustments_by_instrument.get(instrument_id, ())
        bars = bars_by_instrument.get(instrument_id, ())
        action_dates = {
            item.ex_date
            for item in actions
            if item.instrument_id == instrument_id
        }
        for index, adjustment in enumerate(adjustments):
            if not start_date <= adjustment.session_date <= end_date:
                continue
            action = actions_by_key.get((instrument_id, adjustment.session_date))
            previous_adjustment = adjustments[index - 1] if index > 0 else None
            if action is None:
                decisions.append(
                    _unmatched_adjustment_decision(
                        adjustment=adjustment,
                        previous_adjustment=previous_adjustment,
                        source_security_id=source_security_id,
                    )
                )
                continue
            decisions.append(
                _action_decision(
                    action=action,
                    adjustment=adjustment,
                    previous_adjustment=previous_adjustment,
                    bars=bars,
                    tolerance=tolerance,
                )
            )
        adjustment_dates = {
            item.session_date
            for item in adjustments
            if start_date <= item.session_date <= end_date
        }
        for action_date in sorted(action_dates - adjustment_dates):
            action = actions_by_key[(instrument_id, action_date)]
            decisions.append(
                ChinaAshareAdjustmentActionReconciliationV1(
                    instrument_id=instrument_id,
                    source_security_id=source_security_id,
                    session_date=action_date,
                    action_fingerprint=action.logical_fingerprint,
                    status=ChinaAshareAdjustmentReconciliationStatus.ACTION_WITHOUT_ADJUSTMENT,
                    quality_status=QualityStatus.REJECTED,
                    reason_codes=("implemented_action_lacks_adjustment_observation",),
                )
            )

    ordered = tuple(
        sorted(
            decisions,
            key=lambda item: (str(item.instrument_id), item.session_date, item.status.value),
        )
    )
    counts = {
        status: sum(item.status is status for item in ordered)
        for status in ChinaAshareAdjustmentReconciliationStatus
    }
    blockers = any(
        counts[status]
        for status in (
            ChinaAshareAdjustmentReconciliationStatus.LEFT_BOUNDARY_ACTION,
            ChinaAshareAdjustmentReconciliationStatus.ACTION_WITHOUT_ADJUSTMENT,
            ChinaAshareAdjustmentReconciliationStatus.ADJUSTMENT_WITHOUT_ACTION,
            ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT,
        )
    )
    semantics_reconciled = raw_upstream_payload_retained and not blockers
    family_complete = semantics_reconciled and cross_source_reconciled
    reasons = {
        "pilot_scope_only",
        "canonical_apply_not_authorized",
        "research_backtest_not_authorized",
    }
    if family_complete:
        reasons.add("corporate_action_family_reconciled_for_pilot")
    if not cross_source_reconciled:
        reasons.add("independent_cross_source_terms_differ")
    if blockers:
        reasons.add("adjustment_semantics_have_unresolved_rows")
    return build_corporate_action_reconciliation_report(
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        evaluated_at=evaluated_at,
        start_date=start_date,
        end_date=end_date,
        instrument_count=len(expected_instruments),
        corporate_action_count=len(actions),
        adjustment_observation_count=sum(
            start_date <= item.session_date <= end_date for item in full_adjustments
        ),
        matched_action_count=counts[ChinaAshareAdjustmentReconciliationStatus.MATCHED_ACTION],
        left_boundary_action_count=counts[
            ChinaAshareAdjustmentReconciliationStatus.LEFT_BOUNDARY_ACTION
        ],
        provider_noop_correction_count=counts[
            ChinaAshareAdjustmentReconciliationStatus.PROVIDER_NOOP_CORRECTION
        ],
        action_without_adjustment_count=counts[
            ChinaAshareAdjustmentReconciliationStatus.ACTION_WITHOUT_ADJUSTMENT
        ],
        adjustment_without_action_count=counts[
            ChinaAshareAdjustmentReconciliationStatus.ADJUSTMENT_WITHOUT_ACTION
        ],
        factor_conflict_count=counts[
            ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT
        ],
        raw_upstream_payload_retained=raw_upstream_payload_retained,
        cross_source_action_reconciled=cross_source_reconciled,
        adjustment_semantics_reconciled=semantics_reconciled,
        corporate_action_family_complete=family_complete,
        gross_total_return_authorized=family_complete,
        decisions=ordered,
        reason_codes=tuple(sorted(reasons)),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def _action_decision(
    *,
    action: ChinaAshareCorporateActionObservationV1,
    adjustment: ChinaAshareAdjustmentFactorObservationV1,
    previous_adjustment: ChinaAshareAdjustmentFactorObservationV1 | None,
    bars: tuple[ChinaAshareDailyBarV1, ...],
    tolerance: Decimal,
) -> ChinaAshareAdjustmentActionReconciliationV1:
    if previous_adjustment is None:
        return ChinaAshareAdjustmentActionReconciliationV1(
            instrument_id=action.instrument_id,
            source_security_id=action.source_security_id,
            session_date=action.ex_date,
            action_fingerprint=action.logical_fingerprint,
            provider_factor=adjustment.provider_factor,
            status=ChinaAshareAdjustmentReconciliationStatus.LEFT_BOUNDARY_ACTION,
            quality_status=QualityStatus.REJECTED,
            reason_codes=("predecessor_adjustment_factor_absent",),
        )
    previous_bar, current_bar = _surrounding_bars(bars, action.ex_date)
    if previous_bar is None or current_bar is None or current_bar.pre_close is None:
        return ChinaAshareAdjustmentActionReconciliationV1(
            instrument_id=action.instrument_id,
            source_security_id=action.source_security_id,
            session_date=action.ex_date,
            action_fingerprint=action.logical_fingerprint,
            provider_factor=adjustment.provider_factor,
            status=ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT,
            quality_status=QualityStatus.REJECTED,
            reason_codes=("exchange_reference_price_evidence_absent",),
        )
    total_ratio = (
        action.bonus_share_ratio
        + action.capitalization_ratio
        + action.rights_issue_ratio
    )
    rights_price = action.rights_issue_price_per_share_cny or Decimal("0")
    theoretical = (
        previous_bar.close
        - action.cash_dividend_per_share_cny
        + rights_price * action.rights_issue_ratio
    ) / (Decimal("1") + total_ratio)
    expected = previous_bar.close / current_bar.pre_close
    observed_fore = adjustment.fore_adjust_factor / previous_adjustment.fore_adjust_factor
    observed_back = adjustment.back_adjust_factor / previous_adjustment.back_adjust_factor
    fore_error = abs(observed_fore - expected) / expected
    back_error = abs(observed_back - expected) / expected
    matched = fore_error <= tolerance and back_error <= tolerance
    reasons = {
        "exchange_reference_preclose_used",
        "unrounded_formula_retained_for_audit",
    }
    if current_bar.pre_close != theoretical:
        reasons.add("exchange_rounding_observed")
    if adjustment.provider_factor != adjustment.back_adjust_factor:
        reasons.add("provider_factor_differs_from_back_cumulative")
    if matched:
        reasons.add("fore_and_back_factor_steps_match")
    else:
        reasons.add("factor_step_outside_relative_tolerance")
    return ChinaAshareAdjustmentActionReconciliationV1(
        instrument_id=action.instrument_id,
        source_security_id=action.source_security_id,
        session_date=action.ex_date,
        action_fingerprint=action.logical_fingerprint,
        previous_close_cny=previous_bar.close,
        exchange_reference_pre_close_cny=current_bar.pre_close,
        theoretical_unrounded_reference_cny=theoretical,
        expected_adjustment_step=expected,
        observed_fore_step=observed_fore,
        observed_back_step=observed_back,
        fore_relative_error=fore_error,
        back_relative_error=back_error,
        provider_factor=adjustment.provider_factor,
        status=(
            ChinaAshareAdjustmentReconciliationStatus.MATCHED_ACTION
            if matched
            else ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT
        ),
        quality_status=QualityStatus.VALID if matched else QualityStatus.REJECTED,
        reason_codes=tuple(sorted(reasons)),
    )


def _unmatched_adjustment_decision(
    *,
    adjustment: ChinaAshareAdjustmentFactorObservationV1,
    previous_adjustment: ChinaAshareAdjustmentFactorObservationV1 | None,
    source_security_id: str,
) -> ChinaAshareAdjustmentActionReconciliationV1:
    if previous_adjustment is None:
        return ChinaAshareAdjustmentActionReconciliationV1(
            instrument_id=adjustment.instrument_id,
            source_security_id=source_security_id,
            session_date=adjustment.session_date,
            provider_factor=adjustment.provider_factor,
            status=ChinaAshareAdjustmentReconciliationStatus.ADJUSTMENT_WITHOUT_ACTION,
            quality_status=QualityStatus.REJECTED,
            reason_codes=("adjustment_predecessor_and_action_absent",),
        )
    observed_fore = adjustment.fore_adjust_factor / previous_adjustment.fore_adjust_factor
    observed_back = adjustment.back_adjust_factor / previous_adjustment.back_adjust_factor
    noop = observed_fore == Decimal("1") and observed_back == Decimal("1")
    return ChinaAshareAdjustmentActionReconciliationV1(
        instrument_id=adjustment.instrument_id,
        source_security_id=source_security_id,
        session_date=adjustment.session_date,
        observed_fore_step=observed_fore,
        observed_back_step=observed_back,
        provider_factor=adjustment.provider_factor,
        status=(
            ChinaAshareAdjustmentReconciliationStatus.PROVIDER_NOOP_CORRECTION
            if noop
            else ChinaAshareAdjustmentReconciliationStatus.ADJUSTMENT_WITHOUT_ACTION
        ),
        quality_status=QualityStatus.VALID if noop else QualityStatus.REJECTED,
        reason_codes=(
            ("provider_factor_correction_without_economic_action",)
            if noop
            else ("factor_step_has_no_implemented_action",)
        ),
    )


def _crosschecks_reconcile(
    actions: tuple[ChinaAshareCorporateActionObservationV1, ...],
    crosschecks: tuple[ChinaAshareDistributionCrosscheckV1, ...],
) -> bool:
    rights_actions = tuple(item for item in actions if item.rights_issue_ratio > 0)
    distribution_actions = tuple(item for item in actions if item.rights_issue_ratio == 0)
    if rights_actions:
        return False
    expected = {
        (
            item.source_security_id,
            item.ex_date,
            item.record_date,
            item.cash_dividend_per_share_cny,
            item.bonus_share_ratio,
            item.capitalization_ratio,
        )
        for item in distribution_actions
    }
    observed = {
        (
            item.source_security_id,
            item.ex_date,
            item.record_date,
            item.cash_dividend_per_share_cny,
            item.bonus_share_ratio,
            item.capitalization_ratio,
        )
        for item in crosschecks
    }
    return bool(expected) and expected == observed


def _adjustments_by_instrument(
    observations: Iterable[ChinaAshareAdjustmentFactorObservationV1],
) -> dict[UUID, tuple[ChinaAshareAdjustmentFactorObservationV1, ...]]:
    grouped: dict[UUID, list[ChinaAshareAdjustmentFactorObservationV1]] = {}
    for item in observations:
        grouped.setdefault(item.instrument_id, []).append(item)
    return {
        key: tuple(sorted(values, key=lambda item: item.session_date))
        for key, values in grouped.items()
    }


def _bars_by_instrument(
    observations: Iterable[ChinaAshareDailyBarV1],
) -> dict[UUID, tuple[ChinaAshareDailyBarV1, ...]]:
    grouped: dict[UUID, list[ChinaAshareDailyBarV1]] = {}
    for item in observations:
        grouped.setdefault(item.instrument_id, []).append(item)
    return {
        key: tuple(sorted(values, key=lambda item: item.session_date))
        for key, values in grouped.items()
    }


def _surrounding_bars(
    bars: tuple[ChinaAshareDailyBarV1, ...],
    session_date: date,
) -> tuple[ChinaAshareDailyBarV1 | None, ChinaAshareDailyBarV1 | None]:
    previous: ChinaAshareDailyBarV1 | None = None
    current: ChinaAshareDailyBarV1 | None = None
    for item in bars:
        if item.session_date < session_date:
            previous = item
        elif item.session_date == session_date:
            current = item
            break
        else:
            break
    return previous, current


def _source_symbol(source_security_id: str) -> str:
    parts = str(source_security_id).strip().lower().split(".", 1)
    if len(parts) != 2 or parts[0] not in {"sh", "sz"}:
        raise ValueError("Eastmoney cross-check supports only SSE/SZSE source IDs")
    if len(parts[1]) != 6 or not parts[1].isdigit():
        raise ValueError("source security ID is malformed")
    return parts[1]


def _optional_frame_date(value: object) -> date | None:
    if value is None:
        return None
    text = str(value).strip()[:10]
    if not text or text.lower() in {"nat", "nan", "none"}:
        return None
    return date.fromisoformat(text)


def _frame_decimal(value: object) -> Decimal:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return Decimal("0")
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return Decimal("0")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("cross-check distribution term is not decimal") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("cross-check distribution term is invalid")
    return result


def _parse_ths_distribution_terms(value: str) -> tuple[Decimal, Decimal, Decimal]:
    normalized = value.replace(" ", "")
    cash = _ths_term(normalized, r"派([0-9]+(?:\.[0-9]+)?)元")
    bonus = _ths_term(normalized, r"送([0-9]+(?:\.[0-9]+)?)股")
    capitalization = _ths_term(normalized, r"转(?:增)?([0-9]+(?:\.[0-9]+)?)股")
    if not any(item > 0 for item in (cash, bonus, capitalization)):
        raise ValueError("Tonghuashun distribution description has no economic terms")
    divisor = Decimal("10")
    return cash / divisor, bonus / divisor, capitalization / divisor


def _ths_term(value: str, pattern: str) -> Decimal:
    matched = re.search(pattern, value)
    return Decimal(matched.group(1)) if matched is not None else Decimal("0")
