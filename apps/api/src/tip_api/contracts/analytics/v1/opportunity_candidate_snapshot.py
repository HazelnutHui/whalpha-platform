"""Split static-snapshot contracts for Candidate list and on-demand detail."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .opportunity_candidate import (
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateOpportunityStage,
    CandidateRiskMode,
)
from .opportunity_candidate_publication import (
    CandidateRiskDispositionV1,
    CandidateRiskModeEntryPublicationV1,
    CandidateRiskModePublicationV1,
    OpportunityCandidatePublicationItemV1_1,
    OpportunityCandidatePublicationSourceV1_1,
)
from .candidate_entry_geometry import (
    CandidateEntryReviewPosture,
    CandidateExtensionRisk,
    CandidateTechnicalSetup,
)
from .candidate_visual_context import (
    VISUAL_CONTEXT_CONTRACT_VERSION,
    CandidateVisualContextV1,
)


SUMMARY_SNAPSHOT_CONTRACT_VERSION = "opportunity-candidate-summary-snapshot/1.0"
SUMMARY_ANALYTICS_CONTRACT_VERSION = "opportunity-candidate-summary/1.0"
DETAIL_SHARD_CONTRACT_VERSION = "opportunity-candidate-detail-shard/1.0"
DETAIL_SHARD_CONTRACT_VERSION_V1_1 = "opportunity-candidate-detail-shard/1.1"
DETAIL_FILE_RE = re.compile(r"^opportunity-candidate-details-u[01]-[0-9a-f]\.json$")


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def logical_fingerprint(value: dict[str, object]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class CandidateEntrySummaryV1(FrozenModel):
    review_posture: CandidateEntryReviewPosture
    technical_setup: CandidateTechnicalSetup
    extension_risk: CandidateExtensionRisk
    reference_support_distance_pct: str | None


class CandidateSummaryItemV1(FrozenModel):
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    base_score: str | None
    confidence: CandidateConfidenceV1
    latest_price: str
    median_dollar_volume_20: str | None
    data_quality_status: CandidateDataQualityStatus
    final_stage: CandidateOpportunityStage | None
    risk_dispositions: tuple[CandidateRiskDispositionV1, ...]
    entry_summary: CandidateEntrySummaryV1
    score_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_geometry_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    detail_shard_id: str = Field(pattern=r"^u[01]-[0-9a-f]$")

    @model_validator(mode="after")
    def item_reconciles(self) -> "CandidateSummaryItemV1":
        if tuple(row.risk_mode for row in self.risk_dispositions) != tuple(
            CandidateRiskMode
        ):
            raise ValueError("Candidate summary risk dispositions differ")
        if str(self.instrument_id)[0] != self.detail_shard_id[-1]:
            raise ValueError("Candidate summary stable-ID shard differs")
        return self


class CandidateSummaryUniverseV1(FrozenModel):
    universe_id: str
    universe_member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    bar_covered_member_count: int = Field(ge=0)
    missing_member_count: int = Field(ge=0)
    quality_counts: dict[CandidateDataQualityStatus, int]
    stage_counts: dict[str, int]
    risk_modes: tuple[CandidateRiskModePublicationV1, ...]
    entry_risk_modes: tuple[CandidateRiskModeEntryPublicationV1, ...]
    candidates: tuple[CandidateSummaryItemV1, ...]
    candidate_batch_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def universe_reconciles(self) -> "CandidateSummaryUniverseV1":
        if self.bar_covered_member_count + self.missing_member_count != self.universe_member_count:
            raise ValueError("Candidate summary coverage does not reconcile")
        if sum(self.quality_counts.values()) != self.bar_covered_member_count:
            raise ValueError("Candidate summary quality counts do not reconcile")
        if sum(self.stage_counts.values()) != self.universe_member_count:
            raise ValueError("Candidate summary stage counts do not reconcile")
        if tuple(row.risk_mode for row in self.risk_modes) != tuple(CandidateRiskMode):
            raise ValueError("Candidate summary risk mode order differs")
        if tuple(row.risk_mode for row in self.entry_risk_modes) != tuple(CandidateRiskMode):
            raise ValueError("Candidate summary entry mode order differs")
        ids = tuple(str(row.instrument_id) for row in self.candidates)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("Candidate summaries must be unique and stable-ID ordered")
        available = {row.instrument_id for row in self.candidates}
        referenced = {
            instrument_id
            for risk in self.risk_modes
            for instrument_id in risk.displayed_instrument_ids
        } | {
            instrument_id
            for risk in self.entry_risk_modes
            for lane in risk.lanes
            for instrument_id in lane.displayed_instrument_ids
        }
        if not referenced.issubset(available):
            raise ValueError("Candidate summary selection references absent rows")
        return self


class CandidateDetailShardDescriptorV1(FrozenModel):
    shard_id: str = Field(pattern=r"^u[01]-[0-9a-f]$")
    universe_id: str
    stable_id_prefix: str = Field(pattern=r"^[0-9a-f]$")
    filename: str
    item_count: int = Field(gt=0)
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def descriptor_reconciles(self) -> "CandidateDetailShardDescriptorV1":
        if (
            not DETAIL_FILE_RE.fullmatch(self.filename)
            or self.shard_id[-1] != self.stable_id_prefix
            or self.filename != f"opportunity-candidate-details-{self.shard_id}.json"
        ):
            raise ValueError("Candidate detail shard descriptor differs")
        return self


class OpportunityCandidateSummaryAnalyticsV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[SUMMARY_ANALYTICS_CONTRACT_VERSION] = (
        SUMMARY_ANALYTICS_CONTRACT_VERSION
    )
    full_publication_contract_version: Literal["opportunity-candidate-publication/1.1"]
    full_candidate_analytics_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    default_universe_id: str
    universe_order: tuple[str, str]
    risk_mode_order: tuple[CandidateRiskMode, CandidateRiskMode, CandidateRiskMode]
    source: OpportunityCandidatePublicationSourceV1_1
    universes: tuple[CandidateSummaryUniverseV1, CandidateSummaryUniverseV1]
    detail_shards: tuple[CandidateDetailShardDescriptorV1, ...]
    language_neutral: Literal[True] = True
    research_priority_only: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    price_volume_not_fund_flow: Literal[True] = True
    leadership_rank_preserved: Literal[True] = True
    entry_location_separate_from_leadership: Literal[True] = True
    reference_support_not_stop_price: Literal[True] = True
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def analytics_reconciles(self) -> "OpportunityCandidateSummaryAnalyticsV1":
        if tuple(row.universe_id for row in self.universes) != self.universe_order:
            raise ValueError("Candidate summary Universe order differs")
        if self.default_universe_id != self.universe_order[0]:
            raise ValueError("Candidate summary default Universe differs")
        if self.risk_mode_order != tuple(CandidateRiskMode):
            raise ValueError("Candidate summary risk mode order differs")
        ids = tuple(row.shard_id for row in self.detail_shards)
        expected = tuple(sorted(ids, key=lambda value: (int(value[1]), value[-1])))
        if ids != expected or len(ids) != len(set(ids)):
            raise ValueError("Candidate detail descriptors are duplicated or unordered")
        referenced = {
            row.detail_shard_id
            for universe in self.universes
            for row in universe.candidates
        }
        if referenced != set(ids):
            raise ValueError("Candidate detail descriptor coverage differs")
        raw = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if logical_fingerprint(raw) != self.logical_fingerprint:
            raise ValueError("Candidate summary logical fingerprint mismatch")
        return self


class OpportunityCandidateSummarySnapshotV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[SUMMARY_SNAPSHOT_CONTRACT_VERSION] = (
        SUMMARY_SNAPSHOT_CONTRACT_VERSION
    )
    publication_id: str
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_analytics_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    default_universe_id: str
    universe_order: tuple[str, str]
    analytics: OpportunityCandidateSummaryAnalyticsV1

    @model_validator(mode="after")
    def snapshot_reconciles(self) -> "OpportunityCandidateSummarySnapshotV1":
        if (
            self.analytics.full_candidate_analytics_logical_fingerprint
            != self.candidate_analytics_logical_fingerprint
            or self.analytics.default_universe_id != self.default_universe_id
            or self.analytics.universe_order != self.universe_order
        ):
            raise ValueError("Candidate summary snapshot binding differs")
        return self


class OpportunityCandidateDetailShardV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[DETAIL_SHARD_CONTRACT_VERSION] = DETAIL_SHARD_CONTRACT_VERSION
    publication_id: str
    candidate_analytics_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    shard_id: str = Field(pattern=r"^u[01]-[0-9a-f]$")
    universe_id: str
    stable_id_prefix: str = Field(pattern=r"^[0-9a-f]$")
    candidates: tuple[OpportunityCandidatePublicationItemV1_1, ...]
    item_count: int = Field(gt=0)
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def shard_reconciles(self) -> "OpportunityCandidateDetailShardV1":
        ids = tuple(str(row.instrument_id) for row in self.candidates)
        if (
            self.shard_id[-1] != self.stable_id_prefix
            or self.item_count != len(self.candidates)
            or ids != tuple(sorted(ids))
            or len(ids) != len(set(ids))
            or any(value[0] != self.stable_id_prefix for value in ids)
            or any(row.entry_geometry.universe_id != self.universe_id for row in self.candidates)
        ):
            raise ValueError("Candidate detail shard contents differ")
        raw = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if logical_fingerprint(raw) != self.logical_fingerprint:
            raise ValueError("Candidate detail shard logical fingerprint mismatch")
        return self


class OpportunityCandidateDetailShardV1_1(FrozenModel):
    """Candidate detail shard with exact source-bound visual context."""

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[DETAIL_SHARD_CONTRACT_VERSION_V1_1] = (
        DETAIL_SHARD_CONTRACT_VERSION_V1_1
    )
    publication_id: str
    candidate_analytics_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    visual_context_contract_version: Literal[VISUAL_CONTEXT_CONTRACT_VERSION] = (
        VISUAL_CONTEXT_CONTRACT_VERSION
    )
    visual_context_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    shard_id: str = Field(pattern=r"^u[01]-[0-9a-f]$")
    universe_id: str
    stable_id_prefix: str = Field(pattern=r"^[0-9a-f]$")
    candidates: tuple[OpportunityCandidatePublicationItemV1_1, ...]
    visual_contexts: tuple[CandidateVisualContextV1, ...]
    item_count: int = Field(gt=0)
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def shard_reconciles(self) -> "OpportunityCandidateDetailShardV1_1":
        candidate_ids = tuple(str(row.instrument_id) for row in self.candidates)
        visual_ids = tuple(str(row.instrument_id) for row in self.visual_contexts)
        if (
            self.shard_id[-1] != self.stable_id_prefix
            or self.item_count != len(self.candidates)
            or candidate_ids != tuple(sorted(candidate_ids))
            or candidate_ids != visual_ids
            or len(candidate_ids) != len(set(candidate_ids))
            or any(value[0] != self.stable_id_prefix for value in candidate_ids)
            or any(row.entry_geometry.universe_id != self.universe_id for row in self.candidates)
            or any(row.universe_id != self.universe_id for row in self.visual_contexts)
            or any(
                visual.source_candidate_fingerprint != candidate.score_logical_fingerprint
                or visual.source_entry_geometry_fingerprint
                != candidate.entry_geometry.logical_fingerprint
                for candidate, visual in zip(
                    self.candidates,
                    self.visual_contexts,
                    strict=True,
                )
            )
        ):
            raise ValueError("Candidate visual detail shard contents differ")
        raw = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if logical_fingerprint(raw) != self.logical_fingerprint:
            raise ValueError("Candidate visual detail shard logical fingerprint mismatch")
        return self
