"""Provider-neutral instrument identity resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from tip_api.contracts.market_data.v1 import ResolutionMethod

CANONICAL_INSTRUMENT_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "trading-intelligence-platform:canonical-instrument:v1",
)


class StableIdentityType(StrEnum):
    """Stable identifier types accepted for V1 canonical instrument IDs."""

    SHARE_CLASS_FIGI = "share_class_figi"
    COMPOSITE_FIGI = "composite_figi"
    PROVIDER_STABLE_ID = "provider_stable_id"


@dataclass(frozen=True)
class StableIdentityCandidate:
    """Selected stable identity candidate for UUIDv5 generation."""

    identity_type: StableIdentityType
    identity_value: str

    @property
    def resolution_method(self) -> ResolutionMethod:
        return ResolutionMethod(self.identity_type.value)

    @property
    def key(self) -> str:
        return f"{self.identity_type.value}:{self.identity_value}"


def normalize_identifier(value: str | None) -> str | None:
    """Normalize optional stable provider identifiers."""

    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def select_stable_identity(
    *,
    share_class_figi: str | None,
    composite_figi: str | None,
    provider_instrument_id: str | None,
) -> StableIdentityCandidate | None:
    """Select the V1 stable identity using the accepted priority order."""

    normalized_share_class_figi = normalize_identifier(share_class_figi)
    if normalized_share_class_figi is not None:
        return StableIdentityCandidate(StableIdentityType.SHARE_CLASS_FIGI, normalized_share_class_figi)
    normalized_composite_figi = normalize_identifier(composite_figi)
    if normalized_composite_figi is not None:
        return StableIdentityCandidate(StableIdentityType.COMPOSITE_FIGI, normalized_composite_figi)
    normalized_provider_id = normalize_identifier(provider_instrument_id)
    if normalized_provider_id is not None:
        return StableIdentityCandidate(StableIdentityType.PROVIDER_STABLE_ID, normalized_provider_id)
    return None


def canonical_instrument_id_for_identity(candidate: StableIdentityCandidate) -> UUID:
    """Return a deterministic UUIDv5 for a stable provider identity candidate."""

    return uuid5(CANONICAL_INSTRUMENT_NAMESPACE, candidate.key)

