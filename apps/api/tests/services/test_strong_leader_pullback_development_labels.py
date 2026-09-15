from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    ReconstructedDevelopmentLabelState,
    TerminalReferenceLedgerState,
)
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
    StrongLeaderPullbackDevelopmentLabelError,
    build_reconstructed_development_label,
    build_terminal_reference_ledger_entry,
)


INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")
SESSIONS = (date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7))


def _bar(session: date, open_: str, high: str, low: str, close: str):
    return ReconstructedOutcomeBarV1(
        session=session,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _benchmark():
    return (
        _bar(SESSIONS[0], "500", "505", "498", "502"),
        _bar(SESSIONS[1], "502", "506", "500", "504"),
        _bar(SESSIONS[2], "504", "511", "503", "510"),
    )


def _values():
    return {
        "observation_fingerprint": "1" * 64,
        "signal_session": date(2026, 1, 2),
        "instrument_id": INSTRUMENT_ID,
        "ticker_locator": "TEST",
        "expected_path_sessions": SESSIONS,
        "split_basis_session": date(2026, 9, 9),
        "benchmark_bars": _benchmark(),
        "source_eod_fingerprint": "2" * 64,
        "source_adjustment_fingerprint": "3" * 64,
    }


def _terminal(
    state: TerminalReferenceLedgerState,
    lower: str,
    upper: str,
    *,
    last_observed: date = SESSIONS[0],
):
    return build_terminal_reference_ledger_entry(
        instrument_id=INSTRUMENT_ID,
        ticker_locator="TEST",
        last_observed_eod_session=last_observed,
        first_absent_exchange_session=SESSIONS[1],
        state=state,
        lower_reference_value_usd=Decimal(lower),
        upper_reference_value_usd=Decimal(upper),
        evidence_fingerprint="4" * 64,
    )


def test_observed_path_produces_exact_raw_stock_label() -> None:
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(
            _bar(SESSIONS[0], "100", "103", "98", "102"),
            _bar(SESSIONS[1], "102", "106", "101", "105"),
            _bar(SESSIONS[2], "105", "108", "104", "107"),
        ),
    )

    assert label.state is ReconstructedDevelopmentLabelState.OBSERVED_EOD_EXACT
    assert label.underlying_price_return_lower == "0.0700000000"
    assert label.underlying_price_return_upper == "0.0700000000"
    assert label.benchmark_price_return == "0.0200000000"
    assert label.relative_to_benchmark_return_lower == "0.0500000000"
    assert label.maximum_favorable_excursion == "0.0800000000"
    assert label.maximum_adverse_excursion == "-0.0200000000"
    assert label.transaction_costs_not_applied is True
    assert label.underlying_stock_result_not_option_return is True


def test_terminal_interval_preserves_both_endpoints_and_no_excursions() -> None:
    terminal = _terminal(TerminalReferenceLedgerState.FINITE_INTERVAL, "0", "120")
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(
            _bar(SESSIONS[0], "100", "103", "98", "102"),
            None,
            None,
        ),
        terminal_reference=terminal,
    )

    assert (
        label.state
        is ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL
    )
    assert label.underlying_price_return_lower == "-1.0000000000"
    assert label.underlying_price_return_upper == "0.2000000000"
    assert label.maximum_favorable_excursion is None
    assert label.maximum_adverse_excursion is None
    assert label.reason_codes == ("terminal_path_excursions_unavailable",)
    assert label.point_imputation_used is False


def test_terminal_exact_preserves_exact_return_without_inventing_path() -> None:
    terminal = _terminal(TerminalReferenceLedgerState.EXACT, "90", "90")
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(
            _bar(SESSIONS[0], "100", "103", "98", "102"),
            None,
            None,
        ),
        terminal_reference=terminal,
    )

    assert (
        label.state
        is ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_EXACT
    )
    assert label.underlying_price_return_lower == "-0.1000000000"
    assert label.underlying_price_return_upper == "-0.1000000000"
    assert label.maximum_favorable_excursion is None


def test_no_next_open_is_retained_as_unexecutable_without_return() -> None:
    terminal = _terminal(
        TerminalReferenceLedgerState.EXACT,
        "90",
        "90",
        last_observed=date(2026, 1, 2),
    )
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(None, None, None),
        terminal_reference=terminal,
    )

    assert (
        label.state
        is ReconstructedDevelopmentLabelState.UNEXECUTABLE_NO_NEXT_OPEN
    )
    assert label.entry_price_usd is None
    assert label.underlying_price_return_lower is None
    assert label.reason_codes == ("no_executable_next_session_open",)


def test_unproven_missing_next_open_is_unavailable_not_unexecutable() -> None:
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(
            None,
            _bar(SESSIONS[1], "102", "106", "101", "105"),
            _bar(SESSIONS[2], "105", "108", "104", "107"),
        ),
        unavailable_reason_codes=(
            "missing_next_session_eod_without_terminal_evidence",
        ),
    )

    assert label.state is ReconstructedDevelopmentLabelState.UNAVAILABLE_EVIDENCE
    assert label.entry_price_usd is None
    assert label.terminal_reference_fingerprint is None
    assert label.reason_codes == (
        "missing_next_session_eod_without_terminal_evidence",
    )


def test_missing_exit_without_terminal_evidence_fails_closed() -> None:
    with pytest.raises(
        StrongLeaderPullbackDevelopmentLabelError,
        match="terminal reference",
    ):
        build_reconstructed_development_label(
            **_values(),
            instrument_bars=(
                _bar(SESSIONS[0], "100", "103", "98", "102"),
                None,
                None,
            ),
        )


def test_unresolved_adjustment_is_retained_without_numeric_result() -> None:
    label = build_reconstructed_development_label(
        **_values(),
        instrument_bars=(
            _bar(SESSIONS[0], "100", "103", "98", "102"),
            _bar(SESSIONS[1], "102", "106", "101", "105"),
            _bar(SESSIONS[2], "105", "108", "104", "107"),
        ),
        unavailable_reason_codes=("split_adjustment_evidence_quarantined",),
    )

    assert label.state is ReconstructedDevelopmentLabelState.UNAVAILABLE_EVIDENCE
    assert label.underlying_price_return_lower is None
    assert label.reason_codes == ("split_adjustment_evidence_quarantined",)


def test_interval_reference_rejects_point_imputation() -> None:
    with pytest.raises(ValueError, match="terminal-reference ledger"):
        _terminal(TerminalReferenceLedgerState.FINITE_INTERVAL, "100", "100")


def test_split_adjusted_prices_freeze_contract_precision_before_return() -> None:
    label = build_reconstructed_development_label(
        **{
            **_values(),
            "expected_path_sessions": (SESSIONS[0],),
            "benchmark_bars": (_benchmark()[0],),
        },
        instrument_bars=(
            _bar(
                SESSIONS[0],
                "12.345678901234",
                "13.000000000001",
                "12.000000000001",
                "12.876543210987",
            ),
        ),
    )

    assert label.entry_price_usd == "12.3456789012"
    assert label.exit_price_lower_usd == "12.8765432110"
    assert label.underlying_price_return_lower == "0.0430000095"
