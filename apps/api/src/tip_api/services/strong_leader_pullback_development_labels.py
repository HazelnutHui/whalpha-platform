"""Pure label mechanics for reconstructed Strong-Leader Pullback development."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tip_api.contracts.analytics.v1.strong_leader_pullback_development_dataset import (
    ReconstructedDevelopmentLabelState,
    StrongLeaderPullbackReconstructedDevelopmentLabelV1,
    StrongLeaderPullbackTerminalReferenceLedgerEntryV1,
    TerminalReferenceLedgerState,
    development_dataset_fingerprint,
)


_QUANTUM = Decimal("0.0000000001")


class StrongLeaderPullbackDevelopmentLabelError(ValueError):
    """Raised when one development label cannot be constructed safely."""


@dataclass(frozen=True, slots=True)
class ReconstructedOutcomeBarV1:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


def build_terminal_reference_ledger_entry(
    *,
    instrument_id,
    ticker_locator: str,
    last_observed_eod_session: date,
    first_absent_exchange_session: date,
    state: TerminalReferenceLedgerState,
    lower_reference_value_usd: Decimal,
    upper_reference_value_usd: Decimal,
    evidence_fingerprint: str,
) -> StrongLeaderPullbackTerminalReferenceLedgerEntryV1:
    values = {
        "instrument_id": instrument_id,
        "ticker_locator": ticker_locator,
        "last_observed_eod_session": last_observed_eod_session,
        "first_absent_exchange_session": first_absent_exchange_session,
        "state": state,
        "lower_reference_value_usd": _string(lower_reference_value_usd),
        "upper_reference_value_usd": _string(upper_reference_value_usd),
        "evidence_fingerprint": evidence_fingerprint,
        "point_imputation_used": False,
    }
    provisional = StrongLeaderPullbackTerminalReferenceLedgerEntryV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalReferenceLedgerEntryV1.model_validate(
        {
            **values,
            "logical_fingerprint": development_dataset_fingerprint(provisional),
        }
    )


def build_reconstructed_development_label(
    *,
    observation_fingerprint: str,
    signal_session: date,
    instrument_id,
    ticker_locator: str,
    expected_path_sessions: tuple[date, ...],
    split_basis_session: date,
    instrument_bars: tuple[ReconstructedOutcomeBarV1 | None, ...],
    benchmark_bars: tuple[ReconstructedOutcomeBarV1, ...],
    source_eod_fingerprint: str,
    source_adjustment_fingerprint: str,
    terminal_reference: StrongLeaderPullbackTerminalReferenceLedgerEntryV1 | None = None,
    unavailable_reason_codes: tuple[str, ...] = (),
) -> StrongLeaderPullbackReconstructedDevelopmentLabelV1:
    """Build one raw development label without selecting a parameter."""

    horizon = len(expected_path_sessions)
    if horizon not in {1, 3, 5}:
        raise StrongLeaderPullbackDevelopmentLabelError(
            "development label horizon must be 1, 3, or 5 sessions"
        )
    if len(instrument_bars) != horizon or len(benchmark_bars) != horizon:
        raise StrongLeaderPullbackDevelopmentLabelError(
            "development label bars must cover the declared horizon"
        )
    actual_instrument_sessions = tuple(
        item.session if item is not None else expected_path_sessions[index]
        for index, item in enumerate(instrument_bars)
    )
    if actual_instrument_sessions != expected_path_sessions:
        raise StrongLeaderPullbackDevelopmentLabelError(
            "instrument bars differ from the expected path"
        )
    if tuple(item.session for item in benchmark_bars) != expected_path_sessions:
        raise StrongLeaderPullbackDevelopmentLabelError(
            "benchmark bars differ from the expected path"
        )
    for bar in (
        *tuple(item for item in instrument_bars if item is not None),
        *benchmark_bars,
    ):
        _validate_bar(bar)
    if unavailable_reason_codes:
        reasons = tuple(sorted(set(unavailable_reason_codes)))
        return _build_label(
            observation_fingerprint=observation_fingerprint,
            signal_session=signal_session,
            instrument_id=instrument_id,
            ticker_locator=ticker_locator,
            expected_path_sessions=expected_path_sessions,
            split_basis_session=split_basis_session,
            state=ReconstructedDevelopmentLabelState.UNAVAILABLE_EVIDENCE,
            source_eod_fingerprint=source_eod_fingerprint,
            source_adjustment_fingerprint=source_adjustment_fingerprint,
            terminal_reference_fingerprint=(
                terminal_reference.logical_fingerprint
                if terminal_reference is not None
                else None
            ),
            reason_codes=reasons,
        )
    entry_bar = instrument_bars[0]
    if entry_bar is None:
        if (
            terminal_reference is None
            or terminal_reference.instrument_id != instrument_id
            or terminal_reference.last_observed_eod_session >= expected_path_sessions[0]
        ):
            raise StrongLeaderPullbackDevelopmentLabelError(
                "missing next-session open lacks a matching terminal boundary"
            )
        return _build_label(
            observation_fingerprint=observation_fingerprint,
            signal_session=signal_session,
            instrument_id=instrument_id,
            ticker_locator=ticker_locator,
            expected_path_sessions=expected_path_sessions,
            split_basis_session=split_basis_session,
            state=ReconstructedDevelopmentLabelState.UNEXECUTABLE_NO_NEXT_OPEN,
            source_eod_fingerprint=source_eod_fingerprint,
            source_adjustment_fingerprint=source_adjustment_fingerprint,
            terminal_reference_fingerprint=terminal_reference.logical_fingerprint,
            reason_codes=("no_executable_next_session_open",),
        )

    benchmark_return = _return(benchmark_bars[-1].close, benchmark_bars[0].open)
    exit_bar = instrument_bars[-1]
    if exit_bar is not None:
        lower_exit = upper_exit = exit_bar.close
        state = ReconstructedDevelopmentLabelState.OBSERVED_EOD_EXACT
        terminal_fingerprint = None
        complete_path = all(item is not None for item in instrument_bars)
        if complete_path:
            path = tuple(item for item in instrument_bars if item is not None)
            favorable = max(
                Decimal("0"), *(_return(item.high, entry_bar.open) for item in path)
            )
            adverse = min(
                Decimal("0"), *(_return(item.low, entry_bar.open) for item in path)
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
            or expected_path_sessions[0] > terminal_reference.last_observed_eod_session
        ):
            raise StrongLeaderPullbackDevelopmentLabelError(
                "missing horizon close lacks a matching terminal reference"
            )
        lower_exit = Decimal(terminal_reference.lower_reference_value_usd)
        upper_exit = Decimal(terminal_reference.upper_reference_value_usd)
        state = (
            ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_EXACT
            if terminal_reference.state is TerminalReferenceLedgerState.EXACT
            else ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL
        )
        terminal_fingerprint = terminal_reference.logical_fingerprint
        favorable = adverse = None
        reasons = ("terminal_path_excursions_unavailable",)

    entry_price = _quantize(entry_bar.open)
    lower_exit_price = _quantize(lower_exit)
    upper_exit_price = _quantize(upper_exit)
    lower_return = _return(lower_exit_price, entry_price)
    upper_return = _return(upper_exit_price, entry_price)
    return _build_label(
        observation_fingerprint=observation_fingerprint,
        signal_session=signal_session,
        instrument_id=instrument_id,
        ticker_locator=ticker_locator,
        expected_path_sessions=expected_path_sessions,
        split_basis_session=split_basis_session,
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
        source_eod_fingerprint=source_eod_fingerprint,
        source_adjustment_fingerprint=source_adjustment_fingerprint,
        terminal_reference_fingerprint=terminal_fingerprint,
        reason_codes=reasons,
    )


def _build_label(**values: object) -> StrongLeaderPullbackReconstructedDevelopmentLabelV1:
    values = {
        **values,
        "horizon_sessions": len(values["expected_path_sessions"]),  # type: ignore[arg-type]
        "expected_entry_session": values["expected_path_sessions"][0],  # type: ignore[index]
        "expected_exit_session": values["expected_path_sessions"][-1],  # type: ignore[index]
    }
    provisional = StrongLeaderPullbackReconstructedDevelopmentLabelV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackReconstructedDevelopmentLabelV1.model_validate(
        {
            **values,
            "logical_fingerprint": development_dataset_fingerprint(provisional),
        }
    )


def _validate_bar(bar: ReconstructedOutcomeBarV1) -> None:
    values = (bar.open, bar.high, bar.low, bar.close)
    if (
        any(not value.is_finite() or value <= 0 for value in values)
        or bar.high < max(bar.open, bar.close)
        or bar.low > min(bar.open, bar.close)
    ):
        raise StrongLeaderPullbackDevelopmentLabelError(
            "development label bar is invalid"
        )


def _return(exit_price: Decimal, entry_price: Decimal) -> Decimal:
    return (exit_price / entry_price - Decimal("1")).quantize(_QUANTUM)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM)


def _string(value: Decimal) -> str:
    return format(_quantize(value), "f")
