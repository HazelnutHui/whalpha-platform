from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_terminal_reference_bounds as service


def _case(
    index: int,
    *,
    state: service.TerminalReferenceBoundState,
    path_count: int = 5,
) -> service.TerminalReferenceBoundCaseV1:
    base: dict[str, object] = {
        "instrument_id": UUID(int=index + 1),
        "ticker_locator": f"T{index:02d}",
        "prior_gap_state": "reviewed_residual",
        "crossing_path_count": path_count,
        "bound_state": state,
    }
    if state is service.TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING:
        base["missing_source_roles"] = ("final_cvr_cap",)
    else:
        exact = state is service.TerminalReferenceBoundState.EXACT_REFERENCE_READY
        base.update(
            {
                "policy": (
                    "forced_last_us_close"
                    if exact
                    else "zero_to_fixed_cash"
                ),
                "lower_reference_value_usd": (
                    "10.0000000000" if exact else "0.0000000000"
                ),
                "upper_reference_value_usd": "10.0000000000",
                "evidence": (
                    {
                        "evidence_role": "retained_sec_document",
                        "evidence_fingerprint": f"{index + 1:064x}",
                    },
                ),
            }
        )
    return service.TerminalReferenceBoundCaseV1.model_validate(base)


def _partial_cases() -> tuple[service.TerminalReferenceBoundCaseV1, ...]:
    cases = []
    for index in range(18):
        state = (
            service.TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING
            if index < 5
            else service.TerminalReferenceBoundState.FINITE_INTERVAL_READY
        )
        cases.append(
            _case(index, state=state, path_count=3 if index == 17 else 5)
        )
    return tuple(cases)


def test_partial_review_preserves_63_finite_and_25_unbounded_paths() -> None:
    result = service.build_strong_leader_pullback_terminal_reference_bounds(
        terminal_population_fingerprint="a" * 64,
        cases=_partial_cases(),
    )

    assert result.completion_status == "source_evidence_pending"
    assert result.finite_interval_reference_path_count == 63
    assert result.unbounded_reference_path_count == 25
    admission = result.to_admission_evidence()
    assert admission.exact_terminal_reference_path_count == 214
    assert admission.interval_terminal_reference_path_count == 63
    assert admission.unbounded_terminal_reference_path_count == 25


def test_complete_review_can_add_exact_forced_exit_reference() -> None:
    cases = list(_partial_cases())
    cases[0] = _case(
        0,
        state=service.TerminalReferenceBoundState.EXACT_REFERENCE_READY,
    )
    for index in range(1, 5):
        cases[index] = _case(
            index,
            state=service.TerminalReferenceBoundState.FINITE_INTERVAL_READY,
        )
    result = service.build_strong_leader_pullback_terminal_reference_bounds(
        terminal_population_fingerprint="a" * 64,
        cases=tuple(cases),
    )

    assert result.completion_status == "complete"
    assert result.total_exact_reference_path_count == 219
    assert result.finite_interval_reference_path_count == 83
    assert result.unbounded_reference_path_count == 0
    assert result.to_admission_evidence().crossing_path_count == 302


def test_pending_and_ready_states_fail_closed() -> None:
    with pytest.raises(ValidationError, match="not fail closed"):
        service.TerminalReferenceBoundCaseV1.model_validate(
            {
                **_case(
                    0,
                    state=service.TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING,
                ).model_dump(mode="json"),
                "lower_reference_value_usd": "0.0000000000",
                "upper_reference_value_usd": "10.0000000000",
            }
        )
    with pytest.raises(ValidationError, match="must be zero"):
        service.TerminalReferenceBoundCaseV1.model_validate(
            {
                **_case(
                    0,
                    state=service.TerminalReferenceBoundState.FINITE_INTERVAL_READY,
                ).model_dump(mode="json"),
                "lower_reference_value_usd": "1.0000000000",
            }
        )


def test_report_rejects_missing_case_or_path() -> None:
    with pytest.raises(ValidationError):
        service.build_strong_leader_pullback_terminal_reference_bounds(
            terminal_population_fingerprint="a" * 64,
            cases=_partial_cases()[:-1],
        )
