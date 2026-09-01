from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services import historical_backfill_batch_runner as module
from tip_api.services.historical_backfill_batch_runner import (
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
            canonical_session_count_after=len(state["sessions"]),
            canonical_first_session_after=session.isoformat(),
        )

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
    assert result.production_session_count == 3
    assert result.next_session == "2026-07-08"
    assert result.analytics_execution_count == 0
    assert result.publication_count == 0
    assert result.deployment_count == 0
    assert package_root.is_dir()


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
