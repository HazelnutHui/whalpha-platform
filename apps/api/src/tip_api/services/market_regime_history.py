"""In-memory chronological Phase 1a Composite replay for Phase 1b."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from typing import Sequence

from tip_api.contracts.analytics.v1 import MarketRegimeCompositeV1
from tip_api.services.market_regime import calculate_market_regime
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


MINIMUM_PHASE1A_PANEL_SESSIONS = 21
FROZEN_CURRENT_SCORES = {
    "provider_classified_common_shares_v1": {
        "regime_score": "63.9102",
        "dimensions": ("70.9143", "53.5499", "74.6935", "41.1743", "81.3355"),
    },
    "provider_classified_common_shares_plus_adrs_v1": {
        "regime_score": "64.8167",
        "dimensions": ("70.9143", "56.4037", "75.1777", "41.6198", "81.6300"),
    },
}


class MarketRegimeHistoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MarketRegimeCompositeHistory:
    first_calculable_session: date
    last_session: date
    session_count: int
    composites_by_universe: dict[str, tuple[MarketRegimeCompositeV1, ...]]


def calculate_phase1a_composite_history(
    *,
    panel: MarketRegimeInputPanel,
    universe_ids: Sequence[str],
) -> MarketRegimeCompositeHistory:
    """Load sources once, then replay compatible Phase 1a prefixes in memory."""

    if len(panel.sessions) < MINIMUM_PHASE1A_PANEL_SESSIONS:
        raise MarketRegimeHistoryError("Phase 1b needs at least 21 completed XNYS sessions")
    ordered_ids = tuple(universe_ids)
    expected_order = tuple(item.universe_id for item in panel.universes if item.universe_id in ordered_ids)
    if ordered_ids != expected_order or len(set(ordered_ids)) != len(ordered_ids):
        raise MarketRegimeHistoryError("Universe replay order must match the active Primary-first catalog")
    result: dict[str, list[MarketRegimeCompositeV1]] = {item: [] for item in ordered_ids}
    for end_index in range(MINIMUM_PHASE1A_PANEL_SESSIONS - 1, len(panel.sessions)):
        prefix = _prefix_panel(panel, end_index)
        for universe_id in ordered_ids:
            composite, _ = calculate_market_regime(panel=prefix, universe_id=universe_id)
            result[universe_id].append(composite)
    frozen = {key: tuple(value) for key, value in result.items()}
    _validate_current_anchor(panel, frozen)
    first = panel.sessions[MINIMUM_PHASE1A_PANEL_SESSIONS - 1]
    return MarketRegimeCompositeHistory(
        first_calculable_session=first,
        last_session=panel.sessions[-1],
        session_count=len(panel.sessions) - MINIMUM_PHASE1A_PANEL_SESSIONS + 1,
        composites_by_universe=frozen,
    )


def _prefix_panel(panel: MarketRegimeInputPanel, end_index: int) -> MarketRegimeInputPanel:
    start_index = max(0, end_index - 25)
    sessions = panel.sessions[start_index : end_index + 1]
    source_sessions = panel.source_sessions[start_index : end_index + 1]
    allowed = set(sessions)
    current_source = source_sessions[-1]
    return replace(
        panel,
        as_of_session=sessions[-1],
        sessions=sessions,
        source_sessions=source_sessions,
        bars=tuple(item for item in panel.bars if item.session_date in allowed),
        identity_logical_fingerprint=current_source.identity_snapshot_fingerprint,
        eod_content_fingerprint=current_source.content_fingerprint,
        # The business-key anchor is consumed only by the formal final-session source gate.
        # Phase 1a calculation/fingerprinting does not read this field for prefix views.
        eod_business_key_fingerprint=panel.eod_business_key_fingerprint,
        history_source_fingerprint=_source_fingerprint(source_sessions),
    )


def _validate_current_anchor(
    panel: MarketRegimeInputPanel,
    histories: dict[str, tuple[MarketRegimeCompositeV1, ...]],
) -> None:
    if panel.as_of_session != date(2026, 8, 21):
        return
    for universe_id, expected in FROZEN_CURRENT_SCORES.items():
        if universe_id not in histories:
            continue
        current = histories[universe_id][-1]
        dimensions = tuple(item.score for item in current.dimensions)
        if current.regime_score != expected["regime_score"] or dimensions != expected["dimensions"]:
            raise MarketRegimeHistoryError("frozen Phase 1a current Composite anchor mismatch")


def _source_fingerprint(source_sessions: Sequence[object]) -> str:
    rows = [
        {
            "session_date": item.session_date.isoformat(),
            "dataset_path": item.dataset_path,
            "record_count": item.record_count,
            "content_fingerprint": item.content_fingerprint,
            "parquet_sha256": item.parquet_sha256,
            "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
            "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint,
        }
        for item in source_sessions
    ]
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
