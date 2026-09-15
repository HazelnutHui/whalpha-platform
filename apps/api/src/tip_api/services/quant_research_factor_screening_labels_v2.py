"""Outcome-label builder for the registered Factor Catalog V2 Development screen."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningLabelState,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result_v2 import (
    QuantResearchFactorScreeningLabelV2,
    build_factor_screening_label_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    quant_research_factor_screening_protocol_v2,
)
from tip_api.contracts.analytics.v1.strong_leader_pullback_development_dataset import (
    StrongLeaderPullbackTerminalReferenceLedgerEntryV1,
    TerminalReferenceLedgerState,
)
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
)


_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorScreeningLabelV2Error(ValueError):
    """Raised when one V2 factor-screening label cannot be built safely."""


def build_quant_research_factor_screening_label_v2(
    *,
    observation_fingerprint: str,
    signal_session: date,
    instrument_id,
    display_ticker: str | None,
    expected_path_sessions: tuple[date, ...],
    split_basis_session: date,
    instrument_bars: tuple[ReconstructedOutcomeBarV1 | None, ...],
    benchmark_bars: tuple[ReconstructedOutcomeBarV1, ...],
    source_eod_fingerprint: str,
    source_action_fingerprint: str,
    source_adjustment_fingerprint: str,
    terminal_reference: StrongLeaderPullbackTerminalReferenceLedgerEntryV1 | None = None,
    unavailable_reason_codes: tuple[str, ...] = (),
) -> QuantResearchFactorScreeningLabelV2:
    """Build one factor-bound V2 label without reusing a strategy outcome."""

    horizon = len(expected_path_sessions)
    if horizon not in {1, 3, 5}:
        raise QuantResearchFactorScreeningLabelV2Error(
            "V2 factor-screening horizon must be 1, 3, or 5 sessions"
        )
    if len(instrument_bars) != horizon or len(benchmark_bars) != horizon:
        raise QuantResearchFactorScreeningLabelV2Error(
            "V2 factor-screening bars must cover the declared horizon"
        )
    actual_instrument_sessions = tuple(
        item.session if item is not None else expected_path_sessions[index]
        for index, item in enumerate(instrument_bars)
    )
    if actual_instrument_sessions != expected_path_sessions:
        raise QuantResearchFactorScreeningLabelV2Error(
            "V2 instrument bars differ from the expected path"
        )
    if tuple(item.session for item in benchmark_bars) != expected_path_sessions:
        raise QuantResearchFactorScreeningLabelV2Error(
            "V2 benchmark bars differ from the expected path"
        )
    for bar in (
        *tuple(item for item in instrument_bars if item is not None),
        *benchmark_bars,
    ):
        _validate_bar(bar)
    protocol = quant_research_factor_screening_protocol_v2()
    common = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "catalog_fingerprint": protocol.catalog_fingerprint,
        "observation_fingerprint": observation_fingerprint,
        "signal_session": signal_session,
        "instrument_id": instrument_id,
        "display_ticker": display_ticker,
        "horizon_sessions": horizon,
        "expected_entry_session": expected_path_sessions[0],
        "expected_exit_session": expected_path_sessions[-1],
        "expected_path_sessions": expected_path_sessions,
        "split_basis_session": split_basis_session,
        "source_eod_fingerprint": source_eod_fingerprint,
        "source_action_fingerprint": source_action_fingerprint,
        "source_adjustment_fingerprint": source_adjustment_fingerprint,
    }
    if unavailable_reason_codes:
        return build_factor_screening_label_v2(
            **common,
            state=QuantResearchFactorScreeningLabelState.UNAVAILABLE_EVIDENCE,
            terminal_reference_fingerprint=(
                terminal_reference.logical_fingerprint
                if terminal_reference is not None
                else None
            ),
            reason_codes=tuple(sorted(set(unavailable_reason_codes))),
        )
    entry_bar = instrument_bars[0]
    if entry_bar is None:
        if (
            terminal_reference is None
            or terminal_reference.instrument_id != instrument_id
            or terminal_reference.last_observed_eod_session
            >= expected_path_sessions[0]
        ):
            raise QuantResearchFactorScreeningLabelV2Error(
                "missing V2 next-session open lacks a matching terminal boundary"
            )
        return build_factor_screening_label_v2(
            **common,
            state=QuantResearchFactorScreeningLabelState.UNEXECUTABLE_NO_NEXT_OPEN,
            terminal_reference_fingerprint=terminal_reference.logical_fingerprint,
            reason_codes=("no_executable_next_session_open",),
        )

    benchmark_return = _return(benchmark_bars[-1].close, benchmark_bars[0].open)
    exit_bar = instrument_bars[-1]
    if exit_bar is not None:
        lower_exit = upper_exit = exit_bar.close
        state = QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT
        terminal_fingerprint = None
        complete_path = all(item is not None for item in instrument_bars)
        if complete_path:
            path = tuple(item for item in instrument_bars if item is not None)
            favorable = max(
                Decimal("0"),
                *(_return(item.high, entry_bar.open) for item in path),
            )
            adverse = min(
                Decimal("0"),
                *(_return(item.low, entry_bar.open) for item in path),
            )
            reasons: tuple[str, ...] = ()
        else:
            favorable = adverse = None
            reasons = ("incomplete_intraperiod_path_excursions_unavailable",)
    else:
        if (
            terminal_reference is None
            or terminal_reference.instrument_id != instrument_id
            or expected_path_sessions[-1]
            < terminal_reference.first_absent_exchange_session
            or expected_path_sessions[0]
            > terminal_reference.last_observed_eod_session
        ):
            raise QuantResearchFactorScreeningLabelV2Error(
                "missing V2 horizon close lacks a matching terminal reference"
            )
        lower_exit = Decimal(terminal_reference.lower_reference_value_usd)
        upper_exit = Decimal(terminal_reference.upper_reference_value_usd)
        state = (
            QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_EXACT
            if terminal_reference.state is TerminalReferenceLedgerState.EXACT
            else QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL
        )
        terminal_fingerprint = terminal_reference.logical_fingerprint
        favorable = adverse = None
        reasons = ("terminal_path_excursions_unavailable",)

    entry_price = _quantize(entry_bar.open)
    lower_exit_price = _quantize(lower_exit)
    upper_exit_price = _quantize(upper_exit)
    lower_return = _return(lower_exit_price, entry_price)
    upper_return = _return(upper_exit_price, entry_price)
    return build_factor_screening_label_v2(
        **common,
        state=state,
        entry_price_usd=_string(entry_price),
        exit_price_lower_usd=_string(lower_exit_price),
        exit_price_upper_usd=_string(upper_exit_price),
        underlying_price_return_lower=_string(lower_return),
        underlying_price_return_upper=_string(upper_return),
        benchmark_price_return=_string(benchmark_return),
        relative_to_benchmark_return_lower=_string(lower_return - benchmark_return),
        relative_to_benchmark_return_upper=_string(upper_return - benchmark_return),
        maximum_favorable_excursion=(
            _string(favorable) if favorable is not None else None
        ),
        maximum_adverse_excursion=(
            _string(adverse) if adverse is not None else None
        ),
        terminal_reference_fingerprint=terminal_fingerprint,
        reason_codes=reasons,
    )


def _validate_bar(bar: ReconstructedOutcomeBarV1) -> None:
    values = (bar.open, bar.high, bar.low, bar.close)
    if (
        any(not value.is_finite() or value <= 0 for value in values)
        or bar.high < max(bar.open, bar.close)
        or bar.low > min(bar.open, bar.close)
    ):
        raise QuantResearchFactorScreeningLabelV2Error(
            "V2 factor-screening label bar is invalid"
        )


def _return(exit_price: Decimal, entry_price: Decimal) -> Decimal:
    return (exit_price / entry_price - Decimal("1")).quantize(_QUANTUM)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM)


def _string(value: Decimal) -> str:
    return format(_quantize(value), "f")
