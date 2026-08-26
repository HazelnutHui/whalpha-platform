"""Immutable Market Intelligence publication and approval contracts."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .market_regime_preview import (
    MarketRegimePreviewPayloadV1,
    PreviewSourceLogicalFingerprintsV1,
    PreviewUniverseDefinitionV1,
)
from .review_deployment import ReviewDeploymentAuthorizationV1
from .opportunity_candidate_publication import (
    OpportunityCandidatePublicationSourceV1,
    OpportunityCandidatePublicationV1,
)


MARKET_INTELLIGENCE_SCHEMA_VERSION = "1.0"
MARKET_INTELLIGENCE_CONTRACT_VERSION = "market-intelligence-publication/1.0"
MARKET_INTELLIGENCE_CONTRACT_VERSION_V1_1 = "market-intelligence-publication/1.1"
MARKET_INTELLIGENCE_POINTER_VERSION = "1.0"
MARKET_INTELLIGENCE_PLAN_VERSION = "1.0"
MARKET_INTELLIGENCE_REVISION = "market-regime-opportunity-map-v1"
MARKET_INTELLIGENCE_PAYLOAD_FILE = "market-intelligence.json"
MARKET_INTELLIGENCE_MANIFEST_FILE = "manifest.json"
_PUBLICATION_ID = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MarketIntelligenceEodSourceV1(FrozenModel):
    dataset_path: str
    session_date: date
    record_count: int = Field(gt=0)
    content_fingerprint: str
    business_key_fingerprint: str
    parquet_sha256: str
    manifest_sha256: str
    identity_logical_fingerprint: str
    history_first_session: date
    history_last_session: date
    history_session_count: int = Field(gt=0)
    history_source_fingerprint: str

    @field_validator(
        "content_fingerprint",
        "business_key_fingerprint",
        "parquet_sha256",
        "manifest_sha256",
        "identity_logical_fingerprint",
        "history_source_fingerprint",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)

    @field_validator("dataset_path")
    @classmethod
    def relative_dataset_path(cls, value: str) -> str:
        return _relative_path(value)


class MarketIntelligenceActivationSourceV1(FrozenModel):
    pointer_fingerprint: str
    logical_fingerprint: str
    universes: tuple[PreviewUniverseDefinitionV1, ...]

    @field_validator("pointer_fingerprint", "logical_fingerprint")
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)

    @model_validator(mode="after")
    def catalog_is_primary_first(self) -> "MarketIntelligenceActivationSourceV1":
        if len(self.universes) != 2:
            raise ValueError("Market Intelligence requires exactly two active Universes")
        if tuple(item.catalog_order for item in self.universes) != (0, 1):
            raise ValueError("Market Intelligence Universe order is invalid")
        if not self.universes[0].is_default or self.universes[1].is_default:
            raise ValueError("Market Intelligence Primary Universe must be the only default")
        return self


class MarketIntelligenceSourceBindingV1(FrozenModel):
    eod: MarketIntelligenceEodSourceV1
    activation: MarketIntelligenceActivationSourceV1
    phase_logical_fingerprints: PreviewSourceLogicalFingerprintsV1
    preview_payload_logical_fingerprint: str
    preview_payload_sha256: str
    preview_manifest_sha256: str
    preview_generated_at: datetime

    @field_validator(
        "preview_payload_logical_fingerprint",
        "preview_payload_sha256",
        "preview_manifest_sha256",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)


class MarketIntelligencePayloadV1(FrozenModel):
    schema_version: Literal["1.0"] = MARKET_INTELLIGENCE_SCHEMA_VERSION
    contract_version: Literal["market-intelligence-publication/1.0"] = (
        MARKET_INTELLIGENCE_CONTRACT_VERSION
    )
    revision: Literal["market-regime-opportunity-map-v1"] = MARKET_INTELLIGENCE_REVISION
    publication_id: str
    analysis_session: date
    generated_at: datetime
    source: MarketIntelligenceSourceBindingV1
    analytics: MarketRegimePreviewPayloadV1
    language_neutral: Literal[True] = True
    supported_interface_locales: tuple[Literal["en", "zh"], ...] = ("en", "zh")
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None
    logical_fingerprint: str

    @field_validator("publication_id")
    @classmethod
    def publication_id_is_safe(cls, value: str) -> str:
        if not _PUBLICATION_ID.fullmatch(value):
            raise ValueError("unsafe Market Intelligence publication ID")
        return value

    @field_validator("logical_fingerprint")
    @classmethod
    def digest(cls, value: str) -> str:
        return _sha(value)

    @model_validator(mode="after")
    def lineage_reconciles(self) -> "MarketIntelligencePayloadV1":
        if self.analysis_session != self.analytics.as_of_session:
            raise ValueError("Market Intelligence analysis session differs from analytics")
        if self.source.preview_payload_logical_fingerprint != self.analytics.logical_fingerprint:
            raise ValueError("Market Intelligence preview logical fingerprint differs")
        if self.source.phase_logical_fingerprints != self.analytics.source_logical_fingerprints:
            raise ValueError("Market Intelligence phase lineage differs")
        analytics_universes = tuple(item.definition for item in self.analytics.universes)
        if analytics_universes != self.source.activation.universes:
            raise ValueError("Market Intelligence Activation and analytics Universes differ")
        return self


class MarketIntelligencePayloadV1_1(MarketIntelligencePayloadV1):
    """Market Intelligence 1.1 adds the formally bound Candidate consumer view."""

    contract_version: Literal["market-intelligence-publication/1.1"] = (
        MARKET_INTELLIGENCE_CONTRACT_VERSION_V1_1
    )
    candidate_source: OpportunityCandidatePublicationSourceV1
    candidate_analytics: OpportunityCandidatePublicationV1

    @model_validator(mode="after")
    def candidate_lineage_reconciles(self) -> "MarketIntelligencePayloadV1_1":
        candidate = self.candidate_analytics
        if self.analysis_session != candidate.as_of_session:
            raise ValueError("Market Intelligence Candidate analysis session differs")
        if self.candidate_source != candidate.source:
            raise ValueError("Market Intelligence Candidate source binding differs")
        if candidate.universe_order != tuple(
            row.universe_id for row in self.source.activation.universes
        ):
            raise ValueError("Market Intelligence Candidate Universe order differs")
        if tuple(
            row.membership_fingerprint for row in candidate.universes
        ) != tuple(row.membership_fingerprint for row in self.source.activation.universes):
            raise ValueError("Market Intelligence Candidate memberships differ")
        if candidate.source.activation_pointer_fingerprint != self.source.activation.pointer_fingerprint:
            raise ValueError("Market Intelligence Candidate Activation pointer differs")
        eod = self.source.eod
        if (
            candidate.source.identity_logical_fingerprint != eod.identity_logical_fingerprint
            or candidate.source.eod_content_fingerprint != eod.content_fingerprint
            or candidate.source.eod_business_key_fingerprint != eod.business_key_fingerprint
            or candidate.source.history_source_fingerprint != eod.history_source_fingerprint
        ):
            raise ValueError("Market Intelligence Candidate EOD or Identity lineage differs")
        return self


class MarketIntelligenceManifestV1(FrozenModel):
    schema_version: Literal["1.0"] = MARKET_INTELLIGENCE_SCHEMA_VERSION
    contract_version: Literal["market-intelligence-publication/1.0"] = (
        MARKET_INTELLIGENCE_CONTRACT_VERSION
    )
    revision: Literal["market-regime-opportunity-map-v1"] = MARKET_INTELLIGENCE_REVISION
    completion_status: Literal["completed"] = "completed"
    publication_id: str
    analysis_session: date
    generated_at: datetime
    payload_file: Literal["market-intelligence.json"] = MARKET_INTELLIGENCE_PAYLOAD_FILE
    payload_bytes: int = Field(gt=0)
    payload_sha256: str
    payload_logical_fingerprint: str
    analytics_logical_fingerprint: str
    source: MarketIntelligenceSourceBindingV1
    primary_member_count: int = Field(gt=0)
    secondary_member_count: int = Field(gt=0)
    etf_count: Literal[30] = 30
    relationship_count: Literal[16] = 16
    relationship_history_count: Literal[336] = 336
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None
    external_request_count: Literal[0] = 0
    contains_credentials: Literal[False] = False
    contains_raw_provider_data: Literal[False] = False
    manifest_logical_fingerprint: str

    @field_validator("publication_id")
    @classmethod
    def publication_id_is_safe(cls, value: str) -> str:
        if not _PUBLICATION_ID.fullmatch(value):
            raise ValueError("unsafe Market Intelligence publication ID")
        return value

    @field_validator(
        "payload_sha256",
        "payload_logical_fingerprint",
        "analytics_logical_fingerprint",
        "manifest_logical_fingerprint",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)


class MarketIntelligenceManifestV1_1(MarketIntelligenceManifestV1):
    contract_version: Literal["market-intelligence-publication/1.1"] = (
        MARKET_INTELLIGENCE_CONTRACT_VERSION_V1_1
    )
    candidate_source: OpportunityCandidatePublicationSourceV1
    candidate_analytics_logical_fingerprint: str
    candidate_primary_display_count: int = Field(ge=0)
    candidate_secondary_display_count: int = Field(ge=0)

    @field_validator("candidate_analytics_logical_fingerprint")
    @classmethod
    def candidate_digest(cls, value: str) -> str:
        return _sha(value)


class MarketIntelligenceFileReferenceV1(FrozenModel):
    relative_path: str
    size: int = Field(gt=0)
    sha256: str

    @field_validator("relative_path")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        return _relative_path(value)

    @field_validator("sha256")
    @classmethod
    def digest(cls, value: str) -> str:
        return _sha(value)


class MarketIntelligenceTargetReferenceV1(FrozenModel):
    reference_version: Literal["1.0"] = "1.0"
    publication_id: str
    analysis_session: date
    revision: Literal["market-regime-opportunity-map-v1"] = MARKET_INTELLIGENCE_REVISION
    logical_path: str
    payload_sha256: str
    payload_logical_fingerprint: str
    analytics_logical_fingerprint: str
    manifest_sha256: str
    aggregate_sha256: str
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None

    @field_validator("publication_id")
    @classmethod
    def publication_id_is_safe(cls, value: str) -> str:
        if not _PUBLICATION_ID.fullmatch(value):
            raise ValueError("unsafe Market Intelligence publication ID")
        return value

    @field_validator("logical_path")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        return _relative_path(value)

    @field_validator(
        "payload_sha256",
        "payload_logical_fingerprint",
        "analytics_logical_fingerprint",
        "manifest_sha256",
        "aggregate_sha256",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)


class MarketIntelligenceActivePointerV1(FrozenModel):
    pointer_version: Literal["1.0"] = MARKET_INTELLIGENCE_POINTER_VERSION
    status: Literal["active"] = "active"
    active: MarketIntelligenceTargetReferenceV1
    rollback: MarketIntelligenceTargetReferenceV1 | None
    switched_at: datetime
    pointer_content_fingerprint: str

    @field_validator("pointer_content_fingerprint")
    @classmethod
    def digest(cls, value: str) -> str:
        return _sha(value)

    @model_validator(mode="after")
    def rollback_is_distinct(self) -> "MarketIntelligenceActivePointerV1":
        if self.rollback is not None and self.rollback == self.active:
            raise ValueError("active and rollback Market Intelligence references must differ")
        return self


class MarketIntelligenceApprovalPlanV1(FrozenModel):
    plan_version: Literal["1.0"] = MARKET_INTELLIGENCE_PLAN_VERSION
    operation: Literal["market_intelligence_publication"] = "market_intelligence_publication"
    revision: Literal["market-regime-opportunity-map-v1"] = MARKET_INTELLIGENCE_REVISION
    publication_id: str
    created_at: datetime
    analysis_session: date
    data_root: str
    preview_bundle_path: str
    phase1a_audit_path: str
    phase1b_audit_path: str
    phase2_audit_path: str
    source: MarketIntelligenceSourceBindingV1
    expected_current_state_fingerprint: str
    expected_consumer_state_fingerprint: str
    target_path: str
    target_logical_path: str
    pointer_path: str
    candidate_path: str
    files: tuple[MarketIntelligenceFileReferenceV1, ...]
    aggregate_sha256: str
    payload_sha256: str
    payload_logical_fingerprint: str
    analytics_logical_fingerprint: str
    manifest_sha256: str
    planned_pointer_sha256: str
    planned_pointer_fingerprint: str
    rollback_target: MarketIntelligenceTargetReferenceV1 | None
    rollback_authorization_digest: str
    expected_latest_completed_session: date | None
    actual_latest_completed_session: date
    freshness_status: Literal["fresh", "stale", "unavailable"]
    session_lag: int | None
    activation_allowed: bool
    review_mode: bool = False
    normal_freshness: bool = False
    activation_allowed_by_review_authorization: bool = False
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None
    inventory_change_file_count: Literal[3] = 3
    inventory_change_bytes: int = Field(gt=0)
    recovery_boundary: str
    rollback_boundary: str
    plan_content_fingerprint: str

    @field_validator("publication_id")
    @classmethod
    def publication_id_is_safe(cls, value: str) -> str:
        if not _PUBLICATION_ID.fullmatch(value):
            raise ValueError("unsafe Market Intelligence publication ID")
        return value

    @field_validator(
        "expected_current_state_fingerprint",
        "expected_consumer_state_fingerprint",
        "aggregate_sha256",
        "payload_sha256",
        "payload_logical_fingerprint",
        "analytics_logical_fingerprint",
        "manifest_sha256",
        "planned_pointer_sha256",
        "planned_pointer_fingerprint",
        "rollback_authorization_digest",
        "plan_content_fingerprint",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)

    @field_validator("target_logical_path")
    @classmethod
    def logical_path_is_safe(cls, value: str) -> str:
        return _relative_path(value)

    @field_validator("data_root", "target_path", "pointer_path", "candidate_path")
    @classmethod
    def absolute_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("approved paths must be normalized and absolute")
        return value

    @field_validator(
        "preview_bundle_path", "phase1a_audit_path", "phase1b_audit_path", "phase2_audit_path"
    )
    @classmethod
    def tmp_source_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not path.is_absolute()
            or not path.is_relative_to(PurePosixPath("/tmp"))
            or ".." in path.parts
        ):
            raise ValueError("approval source paths must be normalized absolute /tmp paths")
        return value

    @model_validator(mode="after")
    def freshness_authorization_reconciles(self) -> "MarketIntelligenceApprovalPlanV1":
        normal = (
            self.freshness_status == "fresh"
            and self.session_lag == 0
            and self.expected_latest_completed_session == self.actual_latest_completed_session
        )
        if self.activation_allowed != normal or self.normal_freshness != normal:
            raise ValueError("normal Market Intelligence freshness authorization differs")
        if self.review_mode != (self.review_deployment is not None):
            raise ValueError("review mode and review authorization differ")
        review_allowed = self.review_deployment is not None and (
            self.analysis_session == self.review_deployment.approved_as_of_session
            and self.actual_latest_completed_session == self.review_deployment.approved_as_of_session
            and self.expected_latest_completed_session
            == self.review_deployment.expected_latest_session
            and self.session_lag == self.review_deployment.expected_lag_sessions
            and self.freshness_status == "stale"
        )
        if self.activation_allowed_by_review_authorization != review_allowed:
            raise ValueError("review Market Intelligence freshness authorization differs")
        if normal and self.review_deployment is not None:
            raise ValueError("fresh publication must not carry stale-review authorization")
        return self


class MarketIntelligenceApprovalPlanV1_1(MarketIntelligenceApprovalPlanV1):
    """Approval plan that freezes the Candidate audit consumed by MI 1.1."""

    plan_version: Literal["1.1"] = "1.1"
    candidate_audit_path: str
    candidate_source: OpportunityCandidatePublicationSourceV1
    candidate_analytics_logical_fingerprint: str

    @field_validator("candidate_audit_path")
    @classmethod
    def candidate_tmp_source_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not path.is_absolute()
            or not path.is_relative_to(PurePosixPath("/tmp"))
            or ".." in path.parts
        ):
            raise ValueError("Candidate audit path must be a normalized absolute /tmp path")
        return value

    @field_validator("candidate_analytics_logical_fingerprint")
    @classmethod
    def candidate_fingerprint(cls, value: str) -> str:
        return _sha(value)


def _sha(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError("value must be SHA-256 hexadecimal")
    return normalized


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("path must be normalized and relative")
    return value
