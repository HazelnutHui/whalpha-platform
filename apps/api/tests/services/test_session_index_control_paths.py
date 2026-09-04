from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from tip_api.services import (
    daily_eod_dashboard_snapshot_apply_custody as snapshot_custody,
)
from tip_api.services import (
    daily_eod_market_intelligence_apply_custody as mi_custody,
)
from tip_api.services import market_intelligence_publication_cli as mi_cli
from tip_api.services import opportunity_candidate_cli as candidate_cli


TARGET = date(2026, 8, 28)
CHECKED_AT = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)


class IndexOnlyRepository:
    def list_session_index(self):
        return (TARGET,)

    def list_sessions(self):
        raise AssertionError("date-only control path must use the completion index")


def test_market_intelligence_freshness_uses_completion_index(monkeypatch) -> None:
    repository = IndexOnlyRepository()
    monkeypatch.setattr(mi_cli, "CanonicalEodReadRepository", lambda _root: repository)

    freshness = mi_cli._freshness(SimpleNamespace(), CHECKED_AT)

    assert freshness.actual_latest_completed_session == TARGET
    assert freshness.expected_latest_completed_session == TARGET
    assert freshness.session_lag == 0


def test_market_intelligence_apply_freshness_uses_completion_index(
    monkeypatch,
) -> None:
    repository = IndexOnlyRepository()
    monkeypatch.setattr(
        mi_custody, "CanonicalEodReadRepository", lambda _root: repository
    )
    plan = SimpleNamespace(
        activation_allowed=True,
        actual_latest_completed_session=TARGET,
        expected_latest_completed_session=TARGET,
    )

    mi_custody.validate_approved_market_intelligence_freshness(
        root=SimpleNamespace(),
        plan=plan,
        checked_at=CHECKED_AT,
        review_acknowledgement=None,
    )


def test_snapshot_apply_freshness_uses_completion_index(monkeypatch) -> None:
    repository = IndexOnlyRepository()
    monkeypatch.setattr(
        snapshot_custody, "CanonicalEodReadRepository", lambda _root: repository
    )
    plan = SimpleNamespace(
        normal_freshness=True,
        actual_latest_completed_session=TARGET,
        expected_latest_completed_session=TARGET,
    )

    snapshot_custody.validate_approved_dashboard_snapshot_freshness(
        root=SimpleNamespace(),
        plan=plan,
        checked_at=CHECKED_AT,
        review_acknowledgement=None,
    )


def test_candidate_session_discovery_uses_completion_index(monkeypatch) -> None:
    repository = IndexOnlyRepository()
    monkeypatch.setattr(
        candidate_cli, "CanonicalEodReadRepository", lambda _root: repository
    )

    assert candidate_cli._list_available_eod_sessions(SimpleNamespace()) == (TARGET,)
