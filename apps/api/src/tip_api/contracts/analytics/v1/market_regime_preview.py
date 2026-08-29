"""Versioned read-only local preview contract for Market Regime analytics."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .etf_relationship import (
    EtfRelationshipExplanationV1,
    EtfRelationshipRecordV1,
    MarketRegimeRelationshipComparisonV1,
)
from .market_regime import ExplanationLedgerEntryV1, MarketRegimeCompositeV1
from .market_regime_state import MarketRegimeStateExplanationV1, MarketRegimeStateRecordV1
from .review_deployment import ReviewDeploymentAuthorization


PREVIEW_SCHEMA_VERSION = "1.0"
PREVIEW_CONTRACT_VERSION = "market-regime-opportunity-map-preview/1.0"
PREVIEW_API_CONTRACT_VERSION = "market-regime-opportunity-map-api/1.0"
PREVIEW_PAYLOAD_FILE = "market-regime-opportunity-map.json"
PREVIEW_MANIFEST_FILE = "preview-manifest.json"


class PreviewUniverseDefinitionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    universe_id: str
    display_name: str
    catalog_order: int = Field(ge=0)
    is_default: bool
    member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreviewUniverseAnalyticsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    definition: PreviewUniverseDefinitionV1
    composite: MarketRegimeCompositeV1
    current_state: MarketRegimeStateRecordV1
    current_state_explanation: MarketRegimeStateExplanationV1
    state_history: tuple[MarketRegimeStateRecordV1, ...]
    dimension_explanations: tuple[ExplanationLedgerEntryV1, ...]

    @model_validator(mode="after")
    def identity_reconciles(self) -> "PreviewUniverseAnalyticsV1":
        universe_id = self.definition.universe_id
        if self.composite.universe_id != universe_id or self.current_state.universe_id != universe_id:
            raise ValueError("preview Universe analytics are cross-wired")
        if self.current_state_explanation.universe_id != universe_id:
            raise ValueError("preview state explanation is cross-wired")
        if any(item.universe_id != universe_id for item in self.state_history):
            raise ValueError("preview state history is cross-wired")
        if any(item.universe_id != universe_id for item in self.dimension_explanations):
            raise ValueError("preview dimension explanation is cross-wired")
        if self.composite.as_of_session != self.current_state.as_of_session:
            raise ValueError("preview current regime sessions differ")
        if self.current_state.source_composite_fingerprint != self.composite.logical_fingerprint:
            raise ValueError("preview state does not reference its composite")
        if not self.state_history or self.state_history[-1].logical_fingerprint != self.current_state.logical_fingerprint:
            raise ValueError("preview current state is not the history tail")
        return self


class PreviewEtfBasketEntryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str
    family: str
    role: str


class PreviewEtfPairDefinitionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pair_id: str
    registry_order: int = Field(ge=0)
    left_ticker: str
    right_ticker: str
    relationship_family: str
    economic_rationale: str
    expected_interpretation: str
    forbidden_interpretation: str
    applicable_windows: tuple[Literal[5, 10, 20], ...]
    availability_requirement: str
    regime_orientation: str


class PreviewEtfRelationshipWindowChangeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_sessions: Literal[5, 10, 20]
    current_relative_return: str | None
    prior_1_session_relative_return: str | None
    change_1_session: str | None
    prior_5_session_relative_return: str | None
    change_5_sessions: str | None
    leadership_change_1: Literal[
        "strengthening", "weakening", "reversed", "new_leadership",
        "leadership_faded", "unchanged", "unavailable",
    ]
    leadership_change_5: Literal[
        "strengthening", "weakening", "reversed", "new_leadership",
        "leadership_faded", "unchanged", "unavailable",
    ]


class PreviewEtfRelationshipChangeSummaryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["relationship-change-summary/1.0"] = (
        "relationship-change-summary/1.0"
    )
    pair_id: str
    as_of_session: date
    current_state_run_started_session: date
    current_state_run_session_count: int = Field(ge=1)
    state_run_reaches_history_start: bool
    state_changed_this_session: bool
    current_5_session_leader: Literal["left", "right", "tied", "unavailable"]
    windows: tuple[PreviewEtfRelationshipWindowChangeV1, ...]
    reason_codes: tuple[str, ...]
    disclaimer: Literal["descriptive_change_not_predictive_signal"] = (
        "descriptive_change_not_predictive_signal"
    )

    @model_validator(mode="after")
    def fixed_windows(self) -> "PreviewEtfRelationshipChangeSummaryV1":
        if tuple(item.window_sessions for item in self.windows) != (5, 10, 20):
            raise ValueError("relationship change summary requires fixed window order")
        return self


class PreviewEtfRelationshipV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    definition: PreviewEtfPairDefinitionV1
    current: EtfRelationshipRecordV1
    explanation: EtfRelationshipExplanationV1

    @model_validator(mode="after")
    def current_reconciles(self) -> "PreviewEtfRelationshipV1":
        pair_id = self.definition.pair_id
        if self.current.pair_id != pair_id or self.explanation.pair_id != pair_id:
            raise ValueError("preview ETF relationship is cross-wired")
        if self.current.left_ticker != self.definition.left_ticker:
            raise ValueError("preview ETF left ticker differs from registry")
        if self.current.right_ticker != self.definition.right_ticker:
            raise ValueError("preview ETF right ticker differs from registry")
        if self.current.relationship_family != self.definition.relationship_family:
            raise ValueError("preview ETF family differs from registry")
        return self


class PreviewEtfRelationshipViewV1(PreviewEtfRelationshipV1):
    """Additive API/Snapshot view; immutable source payload remains unchanged."""

    change_summary: PreviewEtfRelationshipChangeSummaryV1


class PreviewSourceLogicalFingerprintsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase1a: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase1b: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase2: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreviewCalculationVersionsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase1a: str
    phase1b: str
    phase2: str


class PreviewParameterFingerprintsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase1a: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase1b: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase2: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreviewQualityGateV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    status: Literal["passed", "degraded"]
    reason_codes: tuple[str, ...]


class MarketRegimePreviewPayloadV1(BaseModel):
    """Immutable logical payload stored in a tmp-only preview bundle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-opportunity-map-preview/1.0"] = (
        "market-regime-opportunity-map-preview/1.0"
    )
    api_contract_version: Literal["market-regime-opportunity-map-api/1.0"] = (
        "market-regime-opportunity-map-api/1.0"
    )
    as_of_session: date
    data_status: Literal["degraded_short_history"] = "degraded_short_history"
    input_first_session: date
    input_last_session: date
    input_session_count: int = Field(gt=0)
    default_universe_id: str
    universe_order: tuple[str, ...]
    calculation_versions: PreviewCalculationVersionsV1
    parameter_fingerprints: PreviewParameterFingerprintsV1
    source_logical_fingerprints: PreviewSourceLogicalFingerprintsV1
    universes: tuple[PreviewUniverseAnalyticsV1, ...]
    etf_basket: tuple[PreviewEtfBasketEntryV1, ...]
    relationships: tuple[PreviewEtfRelationshipV1, ...]
    relationship_history: tuple[EtfRelationshipRecordV1, ...]
    relationship_comparisons: tuple[MarketRegimeRelationshipComparisonV1, ...]
    warnings: tuple[str, ...]
    quality_gates: tuple[PreviewQualityGateV1, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def complete_and_ordered(self) -> "MarketRegimePreviewPayloadV1":
        universe_ids = tuple(item.definition.universe_id for item in self.universes)
        if universe_ids != self.universe_order or len(universe_ids) != 2:
            raise ValueError("preview requires exactly two Universes in catalog order")
        if not self.universes[0].definition.is_default or any(
            item.definition.is_default for item in self.universes[1:]
        ):
            raise ValueError("preview requires exactly the first Universe as default")
        if self.default_universe_id != universe_ids[0]:
            raise ValueError("preview default Universe differs from catalog")
        if self.as_of_session != self.input_last_session:
            raise ValueError("preview as-of session differs from input tail")
        pair_ids = tuple(item.definition.pair_id for item in self.relationships)
        if len(pair_ids) != 16 or len(set(pair_ids)) != 16:
            raise ValueError("preview requires all 16 registered ETF pairs")
        if tuple(item.definition.registry_order for item in self.relationships) != tuple(range(16)):
            raise ValueError("preview ETF pair registry order is invalid")
        expected_pairs = set(pair_ids)
        if {item.pair_id for item in self.relationship_history} != expected_pairs:
            raise ValueError("preview ETF history does not cover the registry")
        expected_comparisons = {
            (universe_id, pair_id) for universe_id in universe_ids for pair_id in pair_ids
        }
        if {
            (item.universe_id, item.pair_id) for item in self.relationship_comparisons
        } != expected_comparisons:
            raise ValueError("preview regime/relationship comparison coverage is incomplete")
        return self


class MarketRegimePreviewManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-opportunity-map-preview/1.0"] = (
        "market-regime-opportunity-map-preview/1.0"
    )
    completion_status: Literal["completed"] = "completed"
    generated_at: datetime
    as_of_session: date
    payload_file: Literal["market-regime-opportunity-map.json"] = (
        "market-regime-opportunity-map.json"
    )
    payload_bytes: int = Field(gt=0)
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_logical_fingerprints: PreviewSourceLogicalFingerprintsV1
    external_request_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    manifest_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class MarketRegimeOpportunityMapResponseV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-opportunity-map-api/1.0"] = (
        "market-regime-opportunity-map-api/1.0"
    )
    preview_contract_version: Literal["market-regime-opportunity-map-preview/1.0"] = (
        "market-regime-opportunity-map-preview/1.0"
    )
    bundle_generated_at: datetime
    bundle_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    data_status: Literal["degraded_short_history", "stale_review"]
    review_deployment: ReviewDeploymentAuthorization | None = None
    input_first_session: date
    input_last_session: date
    input_session_count: int
    default_universe_id: str
    selected_universe_id: str
    available_universes: tuple[PreviewUniverseDefinitionV1, ...]
    calculation_versions: PreviewCalculationVersionsV1
    parameter_fingerprints: PreviewParameterFingerprintsV1
    source_logical_fingerprints: PreviewSourceLogicalFingerprintsV1
    regime: PreviewUniverseAnalyticsV1
    relationships: tuple[PreviewEtfRelationshipViewV1, ...]
    relationship_comparisons: tuple[MarketRegimeRelationshipComparisonV1, ...]
    warnings: tuple[str, ...]
    quality_gates: tuple[PreviewQualityGateV1, ...]

    @model_validator(mode="after")
    def review_status_reconciles(self) -> "MarketRegimeOpportunityMapResponseV1":
        if (self.data_status == "stale_review") != (self.review_deployment is not None):
            raise ValueError("Market Regime review status and authorization differ")
        if self.review_deployment is not None and (
            self.as_of_session != self.review_deployment.approved_as_of_session
        ):
            raise ValueError("Market Regime review session differs from authorization")
        return self


class MarketRegimeRelationshipDetailResponseV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-opportunity-map-api/1.0"] = (
        "market-regime-opportunity-map-api/1.0"
    )
    as_of_session: date
    selected_universe_id: str
    source_logical_fingerprints: PreviewSourceLogicalFingerprintsV1
    relationship: PreviewEtfRelationshipViewV1
    comparison: MarketRegimeRelationshipComparisonV1
    history: tuple[EtfRelationshipRecordV1, ...]
