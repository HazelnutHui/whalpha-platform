from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import (
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)
from tip_api.services import historical_backfill_batch_runner as module
from tip_api.services.historical_backfill_batch_runner import (
    HistoricalBackfillBatchRunnerError,
    HistoricalBackfillBatchStoppedError,
    HistoricalBackfillSessionResultV1,
    run_historical_backfill_batch,
)
from tip_api.services.market_calendar import ExchangeCalendar


def _sessions_ending(end: date, count: int) -> tuple[date, ...]:
    calendar = ExchangeCalendar()
    sessions = [end]
    while len(sessions) < count:
        sessions.append(calendar.previous_session(sessions[-1]))
    return tuple(reversed(sessions))


def _session_result(
    session: date,
    canonical_count: int,
    *,
    provider_request_attempt_count: int = 15,
) -> HistoricalBackfillSessionResultV1:
    return HistoricalBackfillSessionResultV1(
        session_date=session.isoformat(),
        identity_canonical_reused=False,
        identity_package_reused=False,
        identity_request_count=14,
        identity_plan_sha256="a" * 64,
        identity_status="published_and_verified",
        eod_canonical_reused=False,
        eod_package_reused=False,
        eod_request_count=1,
        eod_plan_sha256="b" * 64,
        eod_status="published_and_verified",
        canonical_session_count_after=canonical_count,
        canonical_first_session_after=session.isoformat(),
        provider_request_attempt_count=provider_request_attempt_count,
        transient_retry_count=0,
        transient_failure_codes=(),
    )


def _provider_get(transport: object) -> object:
    return transport.get_json(  # type: ignore[attr-defined]
        "/fixture",
        params={},
        api_key=SecretStr("fixture-key"),
        timeout_seconds=Decimal("1"),
        base_url="https://api.massive.com",
    )


def test_runner_selects_each_adjacent_left_session_and_reports_no_product_work(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state = {"sessions": _sessions_ending(date(2026, 8, 31), 35)}

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            del root

        def list_session_index(self) -> tuple[date, ...]:
            return state["sessions"]

    def fake_process_session(**kwargs) -> HistoricalBackfillSessionResultV1:
        session = kwargs["session_date"]
        state["sessions"] = (session,) + state["sessions"]
        return _session_result(session, len(state["sessions"]))

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(module, "_process_session", fake_process_session)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)

    package_root = tmp_path / "packages"
    result = run_historical_backfill_batch(
        config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
        transport=object(),
        data_root=tmp_path / "data",
        package_root=package_root,
        maximum_sessions=3,
    )

    assert tuple(item.session_date for item in result.completed_sessions) == (
        "2026-07-13",
        "2026-07-10",
        "2026-07-09",
    )
    assert result.external_request_count == 45
    assert result.transient_retry_count == 0
    assert result.transient_retry_delays_seconds == (30, 90)
    assert result.production_session_count == 3
    assert result.next_session == "2026-07-08"
    assert result.analytics_execution_count == 0
    assert result.publication_count == 0
    assert result.deployment_count == 0
    assert package_root.is_dir()


def test_runner_uses_frozen_interval_without_legacy_count_ceiling(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state = {"sessions": _sessions_ending(date(2026, 9, 9), 306)}

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            del root

        def list_session_index(self) -> tuple[date, ...]:
            return state["sessions"]

    def fake_process_session(**kwargs) -> HistoricalBackfillSessionResultV1:
        session = kwargs["session_date"]
        state["sessions"] = (session,) + state["sessions"]
        return _session_result(session, len(state["sessions"]))

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(module, "_process_session", fake_process_session)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)

    result = run_historical_backfill_batch(
        config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
        transport=object(),
        data_root=tmp_path / "data",
        package_root=tmp_path / "packages",
        maximum_sessions=1,
        target_first_session=date(2021, 9, 9),
        target_last_session=date(2026, 9, 9),
        request_interval_seconds=Decimal("0.25"),
    )

    assert result.target_session_count == 1_255
    assert result.completed_sessions[0].session_date == "2025-06-20"


def test_runner_rejects_unbounded_session_count(tmp_path: Path) -> None:
    try:
        run_historical_backfill_batch(
            config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
            transport=object(),
            data_root=tmp_path,
            package_root=tmp_path / "packages",
            maximum_sessions=21,
        )
    except RuntimeError as exc:
        assert "between one and twenty" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unbounded batch was accepted")


def test_package_root_accepts_one_owner_only_persistent_child(
    monkeypatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "state"
    parent.mkdir(mode=0o700)
    base = parent / "historical-backfill"
    monkeypatch.setattr(module, "APPROVED_PERSISTENT_PACKAGE_BASE", base)

    prepared = module._prepare_package_root(base / "five-year-fixture")

    assert prepared == (base / "five-year-fixture").resolve()
    assert base.stat().st_mode & 0o777 == 0o700
    assert prepared.stat().st_mode & 0o777 == 0o700
    assert (prepared / "sessions").stat().st_mode & 0o777 == 0o700


def test_package_root_rejects_nested_persistent_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "state"
    parent.mkdir(mode=0o700)
    base = parent / "historical-backfill"
    monkeypatch.setattr(module, "APPROVED_PERSISTENT_PACKAGE_BASE", base)

    with pytest.raises(HistoricalBackfillBatchRunnerError, match="direct child"):
        module._prepare_package_root(base / "outer" / "nested")


@pytest.mark.parametrize(
    ("transient_error", "expected_code"),
    (
        (MassiveTransportTimeoutError("fixture timeout"), "transport_timeout"),
        (
            MassiveTransportUnavailableError("fixture unavailable"),
            "transport_unavailable",
        ),
    ),
)
def test_runner_retries_one_transient_failure_and_counts_every_provider_attempt(
    monkeypatch,
    tmp_path: Path,
    transient_error: Exception,
    expected_code: str,
) -> None:
    state = {"sessions": _sessions_ending(date(2026, 8, 31), 35)}
    attempted_sessions: list[date] = []

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            del root

        def list_session_index(self) -> tuple[date, ...]:
            return state["sessions"]

    class FlakyTransport:
        calls = 0

        def get_json(self, *args, **kwargs) -> dict[str, object]:
            del args, kwargs
            self.calls += 1
            if self.calls == 1:
                raise transient_error
            return {}

    def fake_process_session(**kwargs) -> HistoricalBackfillSessionResultV1:
        attempted_sessions.append(kwargs["session_date"])
        _provider_get(kwargs["transport"])
        session = kwargs["session_date"]
        state["sessions"] = (session,) + state["sessions"]
        return _session_result(
            session,
            len(state["sessions"]),
            provider_request_attempt_count=1,
        )

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(module, "_process_session", fake_process_session)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)
    sleeps: list[float] = []

    result = run_historical_backfill_batch(
        config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
        transport=FlakyTransport(),
        data_root=tmp_path / "data",
        package_root=tmp_path / "packages",
        maximum_sessions=1,
        transient_retry_delays_seconds=(1, 2),
        sleep=sleeps.append,
    )

    assert result.external_request_count == 2
    assert result.transient_retry_count == 1
    assert result.completed_sessions[0].provider_request_attempt_count == 2
    assert result.completed_sessions[0].transient_failure_codes == (expected_code,)
    assert attempted_sessions == [date(2026, 7, 13), date(2026, 7, 13)]
    assert sleeps == [1]


def test_runner_stops_with_resumable_evidence_after_retry_budget_exhaustion(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state = {"sessions": _sessions_ending(date(2026, 8, 31), 35)}

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            del root

        def list_session_index(self) -> tuple[date, ...]:
            return state["sessions"]

    class TimeoutTransport:
        def get_json(self, *args, **kwargs) -> dict[str, object]:
            del args, kwargs
            raise MassiveTransportTimeoutError("fixture timeout")

    def fake_process_session(**kwargs) -> HistoricalBackfillSessionResultV1:
        _provider_get(kwargs["transport"])
        raise AssertionError("unreachable")

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(module, "_process_session", fake_process_session)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)
    sleeps: list[float] = []

    try:
        run_historical_backfill_batch(
            config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
            transport=TimeoutTransport(),
            data_root=tmp_path / "data",
            package_root=tmp_path / "packages",
            maximum_sessions=1,
            transient_retry_delays_seconds=(1, 2),
            sleep=sleeps.append,
        )
    except HistoricalBackfillBatchStoppedError as exc:
        assert exc.failed_session == date(2026, 7, 13)
        assert exc.failure_code == "transport_timeout"
        assert exc.completed_sessions == ()
        assert exc.external_request_count == 3
        assert exc.transient_retry_count == 2
        assert exc.transient_failure_count == 3
    else:  # pragma: no cover
        raise AssertionError("exhausted transient retries did not stop the batch")
    assert sleeps == [1, 2]


def test_runner_does_not_retry_provider_response_errors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state = {"sessions": _sessions_ending(date(2026, 8, 31), 35)}

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            del root

        def list_session_index(self) -> tuple[date, ...]:
            return state["sessions"]

    class ResponseErrorTransport:
        def get_json(self, *args, **kwargs) -> dict[str, object]:
            del args, kwargs
            raise MassiveTransportResponseError(429, "fixture rate limit")

    def fake_process_session(**kwargs) -> HistoricalBackfillSessionResultV1:
        _provider_get(kwargs["transport"])
        raise AssertionError("unreachable")

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(module, "_process_session", fake_process_session)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)
    sleeps: list[float] = []

    try:
        run_historical_backfill_batch(
            config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
            transport=ResponseErrorTransport(),
            data_root=tmp_path / "data",
            package_root=tmp_path / "packages",
            maximum_sessions=1,
            transient_retry_delays_seconds=(1, 2),
            sleep=sleeps.append,
        )
    except MassiveTransportResponseError as exc:
        assert exc.status_code == 429
    else:  # pragma: no cover
        raise AssertionError("provider response error was retried or suppressed")
    assert sleeps == []


def test_runner_rejects_retry_policy_outside_fixed_bounds(tmp_path: Path) -> None:
    for retry_delays in ((1, 2, 3), (0,), (301,)):
        try:
            run_historical_backfill_batch(
                config=MassiveProviderConfig(api_key=SecretStr("fixture-key")),
                transport=object(),
                data_root=tmp_path,
                package_root=tmp_path / "packages",
                maximum_sessions=1,
                transient_retry_delays_seconds=retry_delays,
            )
        except HistoricalBackfillBatchRunnerError as exc:
            assert "bounded policy" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("unbounded retry policy was accepted")
