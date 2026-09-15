"""Compose the admitted terminal evidence into one deterministic value ledger."""

from __future__ import annotations

from decimal import Decimal

from tip_api.contracts.analytics.v1 import (
    StrongLeaderPullbackTerminalReferenceLedgerEntryV1,
    TerminalReferenceLedgerState,
    development_dataset_fingerprint,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.strong_leader_pullback_development_labels import (
    build_terminal_reference_ledger_entry,
)
from tip_api.services.strong_leader_pullback_terminal_reference_bounds import (
    TerminalReferenceBoundState,
)


class StrongLeaderPullbackTerminalReferenceLedgerError(ValueError):
    """Raised when admitted terminal evidence cannot form one complete ledger."""


def build_strong_leader_pullback_terminal_reference_ledger(
    *,
    terminal_boundary: object,
    terminal_gap_v3: object,
    fixed_cash: object,
    listed_consideration: object,
    residual_listed_consideration: object,
    terminal_population_listed_reference: object,
    terminal_gap_v4: object,
    final_terminal_bounds: object,
    calendar: ExchangeCalendar | None = None,
) -> tuple[StrongLeaderPullbackTerminalReferenceLedgerEntryV1, ...]:
    """Unify every terminal-crossing instrument without constructing a return."""

    session_calendar = calendar or ExchangeCalendar()
    population = tuple(terminal_gap_v3.decisions)
    if len(population) != 65:
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "terminal-reference population must contain 65 instruments"
        )
    population_by_id = {item.instrument_id: item for item in population}
    if len(population_by_id) != len(population):
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "terminal-reference population contains duplicate instruments"
        )
    boundary_by_id = {item.instrument_id: item for item in terminal_boundary.decisions}
    if not set(population_by_id).issubset(boundary_by_id):
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "terminal-reference population lacks boundary evidence"
        )

    values: dict[object, tuple[TerminalReferenceLedgerState, Decimal, Decimal, str]] = {}
    for item in fixed_cash.decisions:
        if item.evidence_state == "nominal_fixed_cash_terminal_evidence":
            _add_value(
                values,
                item.instrument_id,
                TerminalReferenceLedgerState.EXACT,
                Decimal(item.nominal_terminal_cash_amount_usd),
                Decimal(item.nominal_terminal_cash_amount_usd),
                item.logical_fingerprint,
            )
    for report in (listed_consideration, residual_listed_consideration):
        for item in report.decisions:
            if item.evidence_state == "gross_listed_consideration_reference_value":
                value = Decimal(item.gross_reference_terminal_value_usd)
                _add_value(
                    values,
                    item.target_instrument_id,
                    TerminalReferenceLedgerState.EXACT,
                    value,
                    value,
                    item.logical_fingerprint,
                )
    scs_value = Decimal(
        terminal_population_listed_reference.primary_gross_reference_value_usd
    )
    _add_value(
        values,
        terminal_population_listed_reference.identity.source_target_instrument_id,
        TerminalReferenceLedgerState.EXACT,
        scs_value,
        scs_value,
        terminal_population_listed_reference.logical_fingerprint,
    )
    for item in terminal_gap_v4.references:
        value = Decimal(item.gross_reference_value_usd)
        _add_value(
            values,
            item.instrument_id,
            TerminalReferenceLedgerState.EXACT,
            value,
            value,
            item.logical_fingerprint,
        )
    if len(values) != 47:
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "prior exact terminal-reference count differs"
        )

    for item in final_terminal_bounds.cases:
        if item.bound_state is TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING:
            raise StrongLeaderPullbackTerminalReferenceLedgerError(
                "unbounded terminal reference remains"
            )
        evidence_fingerprint = development_dataset_fingerprint(
            {
                "final_terminal_bounds": final_terminal_bounds.logical_fingerprint,
                "case": item.model_dump(mode="json"),
            },
            exclude=set(),
        )
        _add_value(
            values,
            item.instrument_id,
            (
                TerminalReferenceLedgerState.EXACT
                if item.bound_state
                is TerminalReferenceBoundState.EXACT_REFERENCE_READY
                else TerminalReferenceLedgerState.FINITE_INTERVAL
            ),
            Decimal(item.lower_reference_value_usd),
            Decimal(item.upper_reference_value_usd),
            evidence_fingerprint,
        )
    if set(values) != set(population_by_id):
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "terminal-reference ledger does not cover the exact population"
        )

    entries = []
    for instrument_id, decision in population_by_id.items():
        tickers = tuple(decision.provider_ticker_locators)
        if len(tickers) != 1:
            raise StrongLeaderPullbackTerminalReferenceLedgerError(
                "terminal-reference ticker locator is ambiguous"
            )
        boundary = boundary_by_id[instrument_id]
        state, lower, upper, evidence_fingerprint = values[instrument_id]
        entries.append(
            build_terminal_reference_ledger_entry(
                instrument_id=instrument_id,
                ticker_locator=tickers[0],
                last_observed_eod_session=(
                    boundary.strategy_window_last_eod_observed_date
                ),
                first_absent_exchange_session=session_calendar.next_session(
                    boundary.strategy_window_last_eod_observed_date
                ),
                state=state,
                lower_reference_value_usd=lower,
                upper_reference_value_usd=upper,
                evidence_fingerprint=evidence_fingerprint,
            )
        )
    ordered = tuple(
        sorted(entries, key=lambda item: (item.ticker_locator, str(item.instrument_id)))
    )
    exact_paths = sum(
        population_by_id[item.instrument_id].horizon_5_crossing_path_count
        for item in ordered
        if item.state is TerminalReferenceLedgerState.EXACT
    )
    interval_paths = sum(
        population_by_id[item.instrument_id].horizon_5_crossing_path_count
        for item in ordered
        if item.state is TerminalReferenceLedgerState.FINITE_INTERVAL
    )
    if (
        exact_paths != final_terminal_bounds.total_exact_reference_path_count
        or interval_paths
        != final_terminal_bounds.finite_interval_reference_path_count
        or exact_paths + interval_paths != final_terminal_bounds.total_terminal_path_count
    ):
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "terminal-reference path counts do not reconcile"
        )
    return ordered


def _add_value(
    values: dict[object, tuple[TerminalReferenceLedgerState, Decimal, Decimal, str]],
    instrument_id: object,
    state: TerminalReferenceLedgerState,
    lower: Decimal,
    upper: Decimal,
    evidence_fingerprint: str,
) -> None:
    if instrument_id in values:
        raise StrongLeaderPullbackTerminalReferenceLedgerError(
            "duplicate terminal-reference value"
        )
    values[instrument_id] = (state, lower, upper, evidence_fingerprint)

