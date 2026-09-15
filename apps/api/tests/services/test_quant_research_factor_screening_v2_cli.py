from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from tip_api.contracts.analytics.v1 import StrategyEvaluationSplit
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    quant_research_factor_screening_protocol_v2,
)
from tip_api.services import quant_research_factor_screening_v2_cli as service


def test_v2_runner_code_hashes_are_stable_and_domain_separated() -> None:
    hashes = (
        service._calculation_code_sha256(),
        service._control_code_sha256(),
        service._label_code_sha256(),
        service._screening_code_sha256(),
    )

    assert all(len(value) == 64 for value in hashes)
    assert len(set(hashes)) == len(hashes)
    assert hashes == (
        service._calculation_code_sha256(),
        service._control_code_sha256(),
        service._label_code_sha256(),
        service._screening_code_sha256(),
    )


def test_v2_runner_requires_an_exact_committed_revision() -> None:
    service._validate_run_identity(
        datetime(2026, 9, 15, tzinfo=UTC),
        "a" * 40,
    )

    with pytest.raises(service.QuantResearchFactorScreeningV2CliError):
        service._validate_run_identity(
            datetime(2026, 9, 15),
            "a" * 40,
        )
    with pytest.raises(service.QuantResearchFactorScreeningV2CliError):
        service._validate_run_identity(
            datetime(2026, 9, 15, tzinfo=UTC),
            "working-tree",
        )


def test_v2_runner_rejects_a_dirty_or_different_repository(monkeypatch) -> None:
    revision = "a" * 40
    responses = iter(
        (
            SimpleNamespace(returncode=0, stdout=f"{revision}\n"),
            SimpleNamespace(returncode=0, stdout=""),
        )
    )
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: next(responses),
    )

    service._validate_repository_revision(revision)

    dirty_responses = iter(
        (
            SimpleNamespace(returncode=0, stdout=f"{revision}\n"),
            SimpleNamespace(returncode=0, stdout="?? draft.py\n"),
        )
    )
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: next(dirty_responses),
    )
    with pytest.raises(
        service.QuantResearchFactorScreeningV2CliError,
        match="exact clean committed implementation",
    ):
        service._validate_repository_revision(revision)


def test_v2_runner_retains_only_the_preregistered_development_interval() -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    assignment = SimpleNamespace(
        raw_split=StrategyEvaluationSplit.DEVELOPMENT,
        usable_for_signal_evaluation=True,
    )
    declared = frozenset(
        (
            protocol.first_development_signal_session,
            protocol.last_development_signal_session,
        )
    )

    assert service._is_declared_development_session(
        assignment=assignment,
        source_session=protocol.first_development_signal_session,
        declared_development_sessions=declared,
    )
    assert service._is_declared_development_session(
        assignment=assignment,
        source_session=protocol.last_development_signal_session,
        declared_development_sessions=declared,
    )
    assert not service._is_declared_development_session(
        assignment=assignment,
        source_session=protocol.first_development_signal_session - timedelta(days=1),
        declared_development_sessions=declared,
    )
    assert not service._is_declared_development_session(
        assignment=assignment,
        source_session=protocol.last_development_signal_session + timedelta(days=1),
        declared_development_sessions=declared,
    )


def test_v2_runner_reconstructs_the_v1_complete_session_cohort(monkeypatch) -> None:
    sessions = tuple(date(2025, 1, day) for day in range(1, 5))
    monkeypatch.setattr(
        service,
        "quant_research_factor_screening_protocol_v2",
        lambda: SimpleNamespace(
            development_declared_session_count=2,
            first_development_signal_session=sessions[0],
            last_development_signal_session=sessions[-1],
        ),
    )
    diagnostics = SimpleNamespace(
        session_availability=tuple(
            SimpleNamespace(
                as_of_session=session,
                factor_id="relative_return_spy_20s",
                expected_count=10,
                available_count=10 if index in {0, 3} else 9,
            )
            for index, session in enumerate(sessions)
        )
    )
    plan = SimpleNamespace(
        ordered_sessions=sessions,
        assignments=tuple(
            SimpleNamespace(
                session=session,
                raw_split=StrategyEvaluationSplit.DEVELOPMENT,
                usable_for_signal_evaluation=True,
            )
            for session in sessions
        ),
    )

    assert service._declared_development_sessions(
        diagnostics=diagnostics,
        plan=plan,
    ) == frozenset((sessions[0], sessions[-1]))
