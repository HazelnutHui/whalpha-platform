"""Orthogonal record-governance classification shared across data families."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    normalize_required_string,
    normalize_utc_datetime,
)


_FAMILY_ID = re.compile(r"[a-z][a-z0-9_]{1,63}")


class DataLayer(StrEnum):
    SOURCE_OBSERVATION = "source_observation"
    CANONICAL_FACT = "canonical_fact"
    METHODOLOGY_DECISION = "methodology_decision"
    DERIVED_FACT = "derived_fact"
    ANALYTIC_RESULT = "analytic_result"
    RESEARCH_SIGNAL = "research_signal"
    FORWARD_OUTCOME = "forward_outcome"
    PRODUCT_PUBLICATION = "product_publication"
    COVERAGE_MANIFEST = "coverage_manifest"


class RecordDisposition(StrEnum):
    ACCEPTED = "accepted"
    EXCLUDED = "excluded"
    QUARANTINED = "quarantined"
    SUPERSEDED = "superseded"


class EvidenceStatus(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class CoverageStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_ASSESSED = "not_assessed"
    NOT_APPLICABLE = "not_applicable"


class PointInTimeEligibility(StrEnum):
    SIGNAL_ELIGIBLE = "signal_eligible"
    OUTCOME_RECONCILIATION_ONLY = "outcome_reconciliation_only"
    INELIGIBLE_UNKNOWN_AVAILABILITY = "ineligible_unknown_availability"
    NOT_APPLICABLE = "not_applicable"


class RetentionClass(StrEnum):
    CANONICAL_NO_AUTO_EXPIRY = "canonical_no_auto_expiry"
    APPEND_ONLY_EVENT_HISTORY = "append_only_event_history"
    SEALED_RESEARCH_EVIDENCE = "sealed_research_evidence"
    REBUILDABLE_CACHE_MINIMUM_90_DAYS = "rebuildable_cache_minimum_90_days"
    OPERATION_BOUNDED_STAGING = "operation_bounded_staging"
    DO_NOT_RETAIN_RAW_BODY = "do_not_retain_raw_body"


class ContentScope(StrEnum):
    SHARED_PRODUCT = "shared_product"
    INTERNAL_ONLY = "internal_only"
    USER_PRIVATE = "user_private"


class WebServingPolicy(StrEnum):
    NOT_ASSESSED = "not_assessed"
    ELIGIBLE_EQUAL_CAPABILITY = "eligible_equal_capability"
    BLOCKED_ALL_SHARED_SESSIONS = "blocked_all_shared_sessions"
    USER_IDENTITY_REQUIRED = "user_identity_required"


class StableKeyKind(StrEnum):
    INSTRUMENT_ID = "instrument_id"
    PROVIDER_STABLE_ID = "provider_stable_id"
    INSTRUMENT_SESSION = "instrument_session"
    INSTRUMENT_EFFECTIVE_INTERVAL = "instrument_effective_interval"
    UNIVERSE_INSTRUMENT_SESSION = "universe_instrument_session"
    EVENT_ID_REVISION = "event_id_revision"
    METHODOLOGY_SCOPE = "methodology_scope"
    PUBLICATION_ID = "publication_id"
    DATASET_SCOPE = "dataset_scope"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SharedContentAccessPolicyV1(FrozenContract):
    """Current product policy; shared analysis never branches by entry path."""

    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal["equal-capability-shared-content-v1"] = (
        "equal-capability-shared-content-v1"
    )
    guest_and_credential_content_identical: Literal[True] = True
    role_dependent_market_entitlements_allowed: Literal[False] = False
    incompatible_source_handling: Literal["block_for_all_shared_sessions"] = (
        "block_for_all_shared_sessions"
    )
    user_private_data_handling: Literal["identity_isolated_when_implemented"] = (
        "identity_isolated_when_implemented"
    )


class DataFamilyDefinitionV1(FrozenContract):
    """One registry definition; it describes grain and governance, not rows."""

    schema_version: Literal["1.0"] = "1.0"
    registry_version: Literal["standard-data-family-registry-v1"] = (
        "standard-data-family-registry-v1"
    )
    data_family_id: str
    layer: DataLayer
    stable_key_kind: StableKeyKind
    grain: str
    description: str
    retention_class: RetentionClass
    point_in_time_required: bool
    allowed_content_scopes: tuple[ContentScope, ...]

    @field_validator("data_family_id", mode="before")
    @classmethod
    def family_id(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="data_family_id")
        if not _FAMILY_ID.fullmatch(normalized):
            raise ValueError("data_family_id must be lower snake case")
        return normalized

    @field_validator("grain", "description", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("allowed_content_scopes")
    @classmethod
    def scopes_are_canonical(
        cls,
        value: tuple[ContentScope, ...],
    ) -> tuple[ContentScope, ...]:
        if not value:
            raise ValueError("a data family requires at least one content scope")
        keys = tuple(item.value for item in value)
        if len(keys) != len(set(keys)) or keys != tuple(sorted(keys)):
            raise ValueError("allowed content scopes must be sorted and unique")
        return value


class GovernedRecordClassificationV1(FrozenContract):
    """Cross-family governance state for one immutable record revision."""

    schema_version: Literal["1.0"] = "1.0"
    governance_policy_version: Literal["data-record-governance-v1"] = (
        "data-record-governance-v1"
    )
    data_family_id: str
    record_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    layer: DataLayer
    content_scope: ContentScope
    disposition: RecordDisposition
    evidence_status: EvidenceStatus
    quality_status: QualityStatus
    coverage_status: CoverageStatus
    point_in_time_eligibility: PointInTimeEligibility
    retention_class: RetentionClass
    web_serving_policy: WebServingPolicy
    source_available_at: datetime | None = None
    signal_cutoff_at: datetime | None = None
    ingested_at: datetime
    classified_at: datetime
    superseded_by_record_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    reason_codes: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...] = ()

    @field_validator("data_family_id", mode="before")
    @classmethod
    def family_id(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="data_family_id")
        if not _FAMILY_ID.fullmatch(normalized):
            raise ValueError("data_family_id must be lower snake case")
        return normalized

    @field_validator(
        "source_available_at",
        "signal_cutoff_at",
        "ingested_at",
        "classified_at",
    )
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalized_strings(value, field_name="reason_codes")

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def evidence_is_canonical(cls, value: Any) -> tuple[str, ...]:
        normalized = _normalized_strings(value, field_name="evidence_fingerprints")
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in normalized):
            raise ValueError("evidence_fingerprints must contain SHA-256 values")
        return normalized

    @model_validator(mode="after")
    def dimensions_reconcile(self) -> "GovernedRecordClassificationV1":
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot be later than ingestion")
        if self.classified_at < self.ingested_at:
            raise ValueError("classification cannot precede ingestion")

        if self.disposition is RecordDisposition.QUARANTINED:
            if not self.reason_codes:
                raise ValueError("quarantined records require reason codes")
            if self.evidence_status not in {
                EvidenceStatus.INSUFFICIENT,
                EvidenceStatus.CONFLICTING,
                EvidenceStatus.UNKNOWN,
            }:
                raise ValueError("quarantine requires unresolved evidence")
            if self.quality_status is QualityStatus.VALID:
                raise ValueError("quarantined records cannot be quality-valid")
        if self.disposition is RecordDisposition.ACCEPTED:
            if self.quality_status is QualityStatus.REJECTED:
                raise ValueError("accepted records cannot be quality-rejected")
            if self.evidence_status in {
                EvidenceStatus.INSUFFICIENT,
                EvidenceStatus.CONFLICTING,
                EvidenceStatus.UNKNOWN,
            }:
                raise ValueError("accepted records cannot carry unresolved evidence")
        if self.disposition is RecordDisposition.EXCLUDED:
            if self.evidence_status not in {
                EvidenceStatus.SUFFICIENT,
                EvidenceStatus.NOT_APPLICABLE,
            }:
                raise ValueError("exclusion requires sufficient or inapplicable evidence")
            if self.quality_status is QualityStatus.REJECTED:
                raise ValueError("excluded decisions cannot be quality-rejected")

        if self.disposition is RecordDisposition.SUPERSEDED:
            if self.superseded_by_record_fingerprint is None:
                raise ValueError("superseded records require the replacement fingerprint")
            if self.superseded_by_record_fingerprint == self.record_fingerprint:
                raise ValueError("a record cannot supersede itself")
        elif self.superseded_by_record_fingerprint is not None:
            raise ValueError("only superseded records may name a replacement")

        if self.point_in_time_eligibility is PointInTimeEligibility.SIGNAL_ELIGIBLE:
            if self.source_available_at is None or self.signal_cutoff_at is None:
                raise ValueError("signal eligibility requires availability and cutoff times")
            if self.source_available_at > self.signal_cutoff_at:
                raise ValueError("source availability cannot follow the signal cutoff")
            if self.disposition in {
                RecordDisposition.QUARANTINED,
                RecordDisposition.SUPERSEDED,
            }:
                raise ValueError("quarantined or superseded records are not signal eligible")
            if self.quality_status in {
                QualityStatus.REJECTED,
                QualityStatus.PENDING_REVIEW,
            }:
                raise ValueError("unresolved quality is not signal eligible")
        elif (
            self.point_in_time_eligibility
            is PointInTimeEligibility.INELIGIBLE_UNKNOWN_AVAILABILITY
        ):
            if self.source_available_at is not None or not self.reason_codes:
                raise ValueError("unknown availability must remain null with a reason")
        elif self.point_in_time_eligibility is PointInTimeEligibility.NOT_APPLICABLE:
            if self.signal_cutoff_at is not None:
                raise ValueError("inapplicable point-in-time state cannot carry a signal cutoff")

        if self.content_scope is ContentScope.SHARED_PRODUCT:
            if self.web_serving_policy is WebServingPolicy.USER_IDENTITY_REQUIRED:
                raise ValueError("shared content cannot require a user identity")
        elif self.content_scope is ContentScope.USER_PRIVATE:
            if self.web_serving_policy is not WebServingPolicy.USER_IDENTITY_REQUIRED:
                raise ValueError("user-private content requires future identity isolation")
        elif self.web_serving_policy is WebServingPolicy.ELIGIBLE_EQUAL_CAPABILITY:
            raise ValueError("internal-only records cannot be directly web eligible")

        if self.web_serving_policy is WebServingPolicy.ELIGIBLE_EQUAL_CAPABILITY:
            if self.content_scope is not ContentScope.SHARED_PRODUCT:
                raise ValueError("equal-capability serving applies only to shared content")
        return self


def validate_governance_registry(
    definitions: tuple[DataFamilyDefinitionV1, ...],
    classifications: tuple[GovernedRecordClassificationV1, ...] = (),
) -> None:
    """Reject duplicate, unordered, undefined, or cross-dimension drift."""

    family_ids = tuple(item.data_family_id for item in definitions)
    if not family_ids or family_ids != tuple(sorted(family_ids)):
        raise ValueError("data family definitions must be non-empty and ordered")
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("data family definitions must be unique")
    by_id = {item.data_family_id: item for item in definitions}

    keys = tuple(
        (item.data_family_id, item.record_fingerprint)
        for item in classifications
    )
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        raise ValueError("record classifications must be ordered and unique")
    for item in classifications:
        definition = by_id.get(item.data_family_id)
        if definition is None:
            raise ValueError("record classification references an undefined data family")
        if item.layer is not definition.layer:
            raise ValueError("record layer does not match its family registry")
        if item.retention_class is not definition.retention_class:
            raise ValueError("record retention does not match its family registry")
        if item.content_scope not in definition.allowed_content_scopes:
            raise ValueError("record content scope is not allowed by its family registry")


def _family(
    data_family_id: str,
    layer: DataLayer,
    stable_key_kind: StableKeyKind,
    grain: str,
    description: str,
    retention_class: RetentionClass,
    *,
    point_in_time_required: bool = True,
    scopes: tuple[ContentScope, ...] = (ContentScope.INTERNAL_ONLY,),
) -> DataFamilyDefinitionV1:
    return DataFamilyDefinitionV1(
        data_family_id=data_family_id,
        layer=layer,
        stable_key_kind=stable_key_kind,
        grain=grain,
        description=description,
        retention_class=retention_class,
        point_in_time_required=point_in_time_required,
        allowed_content_scopes=tuple(sorted(scopes, key=lambda item: item.value)),
    )


STANDARD_DATA_FAMILY_REGISTRY_V1 = tuple(
    sorted(
        (
            _family(
                "adjustment_ledger",
                DataLayer.DERIVED_FACT,
                StableKeyKind.METHODOLOGY_SCOPE,
                "instrument, source session, basis session, methodology revision",
                "Explicit split, volume, price-return, and total-return transformations.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "corporate_action",
                DataLayer.CANONICAL_FACT,
                StableKeyKind.EVENT_ID_REVISION,
                "canonical action ID and revision",
                "Resolved corporate-action fact with stable-ID lineage.",
                RetentionClass.APPEND_ONLY_EVENT_HISTORY,
            ),
            _family(
                "corporate_action_source_observation",
                DataLayer.SOURCE_OBSERVATION,
                StableKeyKind.EVENT_ID_REVISION,
                "provider action ID and source revision",
                "Normalized source evidence before canonical action resolution.",
                RetentionClass.APPEND_ONLY_EVENT_HISTORY,
            ),
            _family(
                "dashboard_snapshot",
                DataLayer.PRODUCT_PUBLICATION,
                StableKeyKind.PUBLICATION_ID,
                "immutable release and publication ID",
                "Serving-ready language-neutral product payload.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
                point_in_time_required=False,
                scopes=(ContentScope.SHARED_PRODUCT,),
            ),
            _family(
                "eod_price_bar",
                DataLayer.CANONICAL_FACT,
                StableKeyKind.INSTRUMENT_SESSION,
                "instrument, session, provider, revision",
                "Raw unadjusted canonical OHLCV fact.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "historical_coverage",
                DataLayer.COVERAGE_MANIFEST,
                StableKeyKind.DATASET_SCOPE,
                "family, bounded interval, methodology, revision",
                "Coverage and readiness evidence without duplicated facts.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "instrument_lifecycle",
                DataLayer.CANONICAL_FACT,
                StableKeyKind.INSTRUMENT_EFFECTIVE_INTERVAL,
                "instrument, effective interval, source, revision",
                "Active, terminal, ticker-history, and lineage facts.",
                RetentionClass.APPEND_ONLY_EVENT_HISTORY,
            ),
            _family(
                "instrument_master",
                DataLayer.CANONICAL_FACT,
                StableKeyKind.INSTRUMENT_ID,
                "stable instrument ID and canonical revision",
                "Provider-neutral listed-security identity.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "market_regime_state",
                DataLayer.ANALYTIC_RESULT,
                StableKeyKind.METHODOLOGY_SCOPE,
                "universe, session, methodology revision",
                "Explainable market-state analytics for product consumption.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
                scopes=(ContentScope.SHARED_PRODUCT,),
            ),
            _family(
                "matured_stock_outcome",
                DataLayer.FORWARD_OUTCOME,
                StableKeyKind.METHODOLOGY_SCOPE,
                "sealed signal ID, horizon, maturity session",
                "Later underlying-stock outcome, never an option-return label.",
                RetentionClass.SEALED_RESEARCH_EVIDENCE,
            ),
            _family(
                "opportunity_candidate",
                DataLayer.ANALYTIC_RESULT,
                StableKeyKind.METHODOLOGY_SCOPE,
                "universe, instrument, session, strategy channel",
                "Explainable candidate evidence and state, not a black-box conclusion.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
                scopes=(ContentScope.SHARED_PRODUCT,),
            ),
            _family(
                "point_in_time_identity",
                DataLayer.SOURCE_OBSERVATION,
                StableKeyKind.PROVIDER_STABLE_ID,
                "provider stable ID, as-of date, source revision",
                "Point-in-time source identity and listing-status observation.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "provider_ticker_resolver",
                DataLayer.DERIVED_FACT,
                StableKeyKind.INSTRUMENT_EFFECTIVE_INTERVAL,
                "provider, ticker, effective interval, instrument",
                "Effective-dated ticker-to-stable-ID resolution index.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "sealed_strategy_signal",
                DataLayer.RESEARCH_SIGNAL,
                StableKeyKind.METHODOLOGY_SCOPE,
                "universe, instrument, signal session, strategy channel",
                "Contemporaneous signal sealed before forward outcomes exist.",
                RetentionClass.SEALED_RESEARCH_EVIDENCE,
            ),
            _family(
                "security_classification",
                DataLayer.METHODOLOGY_DECISION,
                StableKeyKind.INSTRUMENT_EFFECTIVE_INTERVAL,
                "instrument, effective interval, taxonomy and ruleset",
                "Security form, issuer structure, listing scope, and evidence decision.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
            _family(
                "universe_membership",
                DataLayer.METHODOLOGY_DECISION,
                StableKeyKind.UNIVERSE_INSTRUMENT_SESSION,
                "universe, instrument, session, methodology revision",
                "Explicit included, excluded, or quarantined daily decision.",
                RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
            ),
        ),
        key=lambda item: item.data_family_id,
    )
)

SHARED_CONTENT_ACCESS_POLICY_V1 = SharedContentAccessPolicyV1()
validate_governance_registry(STANDARD_DATA_FAMILY_REGISTRY_V1)


def _normalized_strings(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError(f"{field_name} must be a collection")
    return tuple(
        sorted(
            {
                normalize_required_string(item, field_name=field_name)
                for item in value
            }
        )
    )
