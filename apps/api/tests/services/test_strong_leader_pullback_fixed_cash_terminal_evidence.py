from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_fixed_cash_terminal_evidence as service


def _inputs(
    *, invalid_completion_sequence: int | None = None
) -> tuple[object, object, object]:
    considerations = []
    cessations = []
    payoff_decisions = []
    for sequence in range(1, 62):
        instrument_id = UUID(int=sequence)
        consideration_fingerprint = f"{sequence + 100:064x}"
        cessation_fingerprint = f"{sequence + 200:064x}"
        ready = sequence <= 30
        stop = date(2026, 1, 6)
        completion = (
            date(2026, 1, 7)
            if sequence == invalid_completion_sequence
            else stop
        )
        considerations.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                logical_fingerprint=consideration_fingerprint,
                acceptance_datetime=datetime(2026, 1, 7, tzinfo=UTC),
                transaction_completion_date=completion,
            )
        )
        cessations.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                logical_fingerprint=cessation_fingerprint,
                transaction_completion_date=completion,
                resolution_state="matched" if ready else "unsupported",
                timing_profile="before_open" if ready else "unresolved",
                sec_stated_trading_stop_boundary_date=stop if ready else None,
                expected_last_eod_session=date(2026, 1, 5) if ready else None,
                observed_last_eod_session=date(2026, 1, 5) if ready else None,
                next_exchange_session=stop if ready else None,
            )
        )
        term = SimpleNamespace(
            term_key="guaranteed_cash",
            term_kind="cash_usd_per_target_share",
            normalized_value=f"{sequence}.00",
            logical_fingerprint=f"{sequence + 300:064x}",
        )
        payoff_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                consideration_fingerprint=consideration_fingerprint,
                cessation_fingerprint=cessation_fingerprint,
                logical_fingerprint=f"{sequence + 400:064x}",
                terminal_candidate_state=(
                    "fixed_cash_and_timing_ready"
                    if ready
                    else "cessation_timing_not_matched"
                ),
                single_deterministic_cash_term_complete=ready,
                terms=(term,),
                alternatives=(),
            )
        )
    consideration = SimpleNamespace(
        report=SimpleNamespace(
            decisions=tuple(considerations), logical_fingerprint="1" * 64
        ),
        report_sha256="2" * 64,
    )
    cessation = SimpleNamespace(
        report=SimpleNamespace(
            decisions=tuple(cessations), logical_fingerprint="3" * 64
        ),
        report_sha256="4" * 64,
    )
    payoff_terms = SimpleNamespace(
        report=SimpleNamespace(
            consideration_report_sha256="2" * 64,
            consideration_logical_fingerprint="1" * 64,
            cessation_report_sha256="4" * 64,
            cessation_logical_fingerprint="3" * 64,
            lifecycle_case_count=61,
            fixed_cash_and_timing_ready_count=30,
            decisions=tuple(payoff_decisions),
            logical_fingerprint="5" * 64,
        ),
        report_sha256="6" * 64,
    )
    return consideration, cessation, payoff_terms


def test_documents_only_safe_fixed_cash_terminal_evidence() -> None:
    consideration, cessation, payoff_terms = _inputs()

    report = service._build_report(
        consideration=consideration,
        cessation=cessation,
        payoff_terms=payoff_terms,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 18, tzinfo=UTC),
    )

    assert report.terminal_cash_evidence_count == 30
    assert report.excluded_case_count == 31
    assert report.completion_equals_stop_boundary_count == 30
    assert report.canonical_terminal_outcome_count == 0
    assert report.strategy_outcome_label_count == 0
    assert report.decisions[0].nominal_terminal_cash_amount_usd == "1.00"
    assert report.decisions[-1].nominal_terminal_cash_amount_usd is None


def test_rejects_completion_after_first_absent_session() -> None:
    consideration, cessation, payoff_terms = _inputs(invalid_completion_sequence=1)

    with pytest.raises(ValueError, match="daily terminal boundary differs"):
        service._build_report(
            consideration=consideration,
            cessation=cessation,
            payoff_terms=payoff_terms,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 14, 18, tzinfo=UTC),
        )


def test_report_is_owner_only_immutable_and_idempotent(tmp_path: Path) -> None:
    consideration, cessation, payoff_terms = _inputs()
    report = service._build_report(
        consideration=consideration,
        cessation=cessation,
        payoff_terms=payoff_terms,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 18, tzinfo=UTC),
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)

    first = service._write_report(
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=first.output_root,
        output_custody_root=custody,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert (first.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackFixedCashTerminalEvidenceError,
        match="network access is prohibited",
    ):
        socket.socket()
