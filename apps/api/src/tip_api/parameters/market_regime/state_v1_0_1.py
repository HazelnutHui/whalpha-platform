"""Stable-prefix Phase 1b parameters; transition thresholds remain unchanged."""

from __future__ import annotations

import hashlib
import json

from tip_api.parameters.market_regime.state_v1_0_0 import *  # noqa: F403
from tip_api.parameters.market_regime.state_v1_0_0 import state_parameter_payload as _prior_payload


STATE_CALCULATION_VERSION = "market-regime-opportunity-map-state-v1.0.1"
STATE_PARAMETER_SET_ID = "mrom-regime-state-v1-stable-prefix-2"


def _payload() -> dict[str, object]:
    payload = _prior_payload()
    payload.update(
        state_calculation_version=STATE_CALCULATION_VERSION,
        state_parameter_set_id=STATE_PARAMETER_SET_ID,
        history_replay_start_policy="first_contiguous_canonical_session",
        phase1a_composite_source_window_sessions=26,
        cross_as_of_future_prefix_required=True,
    )
    return payload


STATE_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
).hexdigest()


def state_parameter_payload() -> dict[str, object]:
    return json.loads(json.dumps(_payload(), sort_keys=True, separators=(",", ":")))
