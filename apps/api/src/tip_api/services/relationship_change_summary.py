"""Descriptive, threshold-free change facts for registered ETF relationships."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Sequence

from tip_api.contracts.analytics.v1.etf_relationship import EtfRelationshipRecordV1
from tip_api.contracts.analytics.v1.market_regime_preview import (
    PreviewEtfRelationshipChangeSummaryV1,
    PreviewEtfRelationshipWindowChangeV1,
)


class RelationshipChangeSummaryError(RuntimeError):
    """Raised when relationship history cannot support an exact summary."""


LeadershipChange = Literal[
    "strengthening",
    "weakening",
    "reversed",
    "new_leadership",
    "leadership_faded",
    "unchanged",
    "unavailable",
]


def build_relationship_change_summary(
    *,
    current: EtfRelationshipRecordV1,
    history: Sequence[EtfRelationshipRecordV1],
) -> PreviewEtfRelationshipChangeSummaryV1:
    supplied = tuple(history)
    if not supplied or any(item.pair_id != current.pair_id for item in supplied):
        raise RelationshipChangeSummaryError("relationship history identity mismatch")
    by_session: dict[date, EtfRelationshipRecordV1] = {}
    for item in supplied:
        existing = by_session.get(item.as_of_session)
        if existing is not None and existing.logical_fingerprint != item.logical_fingerprint:
            raise RelationshipChangeSummaryError(
                "relationship history contains conflicting duplicate sessions"
            )
        by_session[item.as_of_session] = item
    ordered = tuple(sorted(by_session.values(), key=lambda item: item.as_of_session))
    if ordered[-1].logical_fingerprint != current.logical_fingerprint:
        raise RelationshipChangeSummaryError("relationship history tail differs from current")

    run_count = 0
    for item in reversed(ordered):
        if item.relationship_state != current.relationship_state:
            break
        run_count += 1
    run_start = ordered[-run_count].as_of_session
    previous = ordered[-2] if len(ordered) >= 2 else None
    prior_five = ordered[-6] if len(ordered) >= 6 else None
    current_windows = _windows(current)
    previous_windows = _windows(previous) if previous is not None else {}
    prior_five_windows = _windows(prior_five) if prior_five is not None else {}
    window_changes = tuple(
        _window_change(
            window=window,
            current=current_windows[window],
            prior_one=previous_windows.get(window),
            prior_five=prior_five_windows.get(window),
        )
        for window in (5, 10, 20)
    )
    relative_five = current_windows[5]
    return PreviewEtfRelationshipChangeSummaryV1(
        pair_id=current.pair_id,
        as_of_session=current.as_of_session,
        current_state_run_started_session=run_start,
        current_state_run_session_count=run_count,
        state_run_reaches_history_start=run_count == len(ordered),
        state_changed_this_session=(
            previous is not None
            and previous.relationship_state != current.relationship_state
        ),
        current_5_session_leader=_leader(relative_five),
        windows=window_changes,
        reason_codes=(
            "state_run_derived_from_retained_relationship_history",
            "rolling_relative_return_changes_are_descriptive",
            "history_start_boundary_explicit"
            if run_count == len(ordered)
            else "state_run_start_observed",
        ),
    )


def _windows(record: EtfRelationshipRecordV1 | None) -> dict[int, str | None]:
    if record is None:
        return {}
    return {item.window_sessions: item.relative_return for item in record.windows}


def _window_change(
    *, window: int, current: str | None, prior_one: str | None, prior_five: str | None,
) -> PreviewEtfRelationshipWindowChangeV1:
    return PreviewEtfRelationshipWindowChangeV1(
        window_sessions=window,
        current_relative_return=current,
        prior_1_session_relative_return=prior_one,
        change_1_session=_difference(current, prior_one),
        prior_5_session_relative_return=prior_five,
        change_5_sessions=_difference(current, prior_five),
        leadership_change_1=_leadership_change(current, prior_one),
        leadership_change_5=_leadership_change(current, prior_five),
    )


def _difference(current: str | None, prior: str | None) -> str | None:
    if current is None or prior is None:
        return None
    return format(Decimal(current) - Decimal(prior), "f")


def _leader(value: str | None) -> Literal["left", "right", "tied", "unavailable"]:
    if value is None:
        return "unavailable"
    decimal = Decimal(value)
    return "left" if decimal > 0 else "right" if decimal < 0 else "tied"


def _leadership_change(current: str | None, prior: str | None) -> LeadershipChange:
    if current is None or prior is None:
        return "unavailable"
    current_value, prior_value = Decimal(current), Decimal(prior)
    if current_value == prior_value:
        return "unchanged"
    if prior_value == 0:
        return "new_leadership" if current_value != 0 else "unchanged"
    if current_value == 0:
        return "leadership_faded"
    if (current_value > 0) != (prior_value > 0):
        return "reversed"
    return "strengthening" if abs(current_value) > abs(prior_value) else "weakening"
