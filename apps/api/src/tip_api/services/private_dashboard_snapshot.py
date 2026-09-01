"""Static private dashboard snapshot export boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelProductV1,
    MarketIntelligencePayloadV1_1,
    MarketIntelligencePayloadV1_2,
    MarketIntelligencePayloadV1_3,
    OpportunityCandidatePublicationV1,
    OpportunityCandidatePublicationV1_1,
    PreviewUniverseDefinitionV1,
    SectorEtfRotationDashboardSnapshotV1,
    sector_rotation_dashboard_snapshot_fingerprint,
)
from tip_api.contracts.analytics.v1.review_deployment import review_acknowledgement_for_contract
from tip_api.contracts.analytics.v1.opportunity_candidate_snapshot import (
    DETAIL_FILE_RE,
    DETAIL_SHARD_CONTRACT_VERSION,
    DETAIL_SHARD_CONTRACT_VERSION_V1_1,
    SUMMARY_ANALYTICS_CONTRACT_VERSION,
    SUMMARY_SNAPSHOT_CONTRACT_VERSION,
    OpportunityCandidateDetailShardV1,
    OpportunityCandidateDetailShardV1_1,
    OpportunityCandidateSummarySnapshotV1,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.schemas.private_market import DashboardOverviewResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService
from tip_api.services.dashboard_overview import DashboardOverviewService
from tip_api.persistence.parquet.dashboard_universe_activation_active import ActiveDashboardUniverseActivation, read_active_dashboard_universe_activation
from tip_api.persistence.parquet.market_intelligence_active import CompletedMarketIntelligence
from tip_api.services.market_regime_preview import MarketRegimePreviewService
from tip_api.services.opportunity_candidate_snapshot_split import (
    build_split_candidate_snapshot,
    reconstruct_full_candidate_publication,
)
from tip_api.services.candidate_strategy_channel_product import (
    build_candidate_strategy_channel_product,
)
from tip_api.services.candidate_visual_context_audit import (
    VISUAL_CONTEXT_AUDIT_MANIFEST,
    read_candidate_visual_context_batches,
)

SNAPSHOT_CONTRACT_VERSION = "1.8"
SNAPSHOT_FILES = {
    "overview_file": "market-overview.json",
    "summary_file": "market-summary.json",
    "movers_file": "movers.json",
    "liquidity_map_file": "liquidity-map.json",
}
MARKET_INTELLIGENCE_FILE = "market-regime-overviews.json"
OPPORTUNITY_CANDIDATES_FILE = "opportunity-candidates.json"
OPPORTUNITY_CANDIDATE_SUMMARY_FILE = "opportunity-candidates-summary.json"
CANDIDATE_STRATEGY_CHANNELS_FILE = "candidate-strategy-channels.json"
SECTOR_ETF_ROTATION_FILE = "sector-etf-rotation.json"
_RELEASE_ID_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$")


class DashboardSnapshotError(RuntimeError):
    """Raised when a private dashboard snapshot cannot be safely produced."""


class DashboardSnapshotManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_contract_version: str = Field(pattern=r"^1(?:\.(?:[1-9]|1[01]))?$")
    release_id: str
    generated_at: str
    current_session_date: str
    previous_session_date: str
    expected_latest_completed_session: str | None = None
    actual_latest_completed_session: str | None = None
    session_lag: int | None = None
    freshness_status: str | None = None
    calendar_id: str | None = None
    freshness_checked_at: str | None = None
    data_status: str
    overview_file: str
    summary_file: str
    movers_file: str
    liquidity_map_file: str
    file_sha256: dict[str, str]
    summary_node_count: int
    mover_gainer_count: int
    mover_loser_count: int
    liquidity_node_count: int
    warning_count: int
    default_universe_id: str = "tradable_us_listed_equities_v1"
    dashboard_contract_version: str = "1.2"
    universe_definition_id: str = "legacy_liquid_screen_provisional"
    universe_version: str = "1.0"
    governance_status: str = "provisional_classification"
    classification_as_of_date: str | None = None
    evidence_coverage_status: str = "incomplete"
    selected_universe_id: str | None = None
    available_universe_ids: tuple[str, ...] = ()
    activation_fingerprint: str | None = None
    membership_evidence_as_of: str | None = None
    funnel_stage_count: int | None = None
    funnel_source_fingerprint: str | None = None
    market_intelligence_file: str | None = None
    market_intelligence_publication_id: str | None = None
    market_intelligence_payload_sha256: str | None = None
    market_intelligence_logical_fingerprint: str | None = None
    analytics_payload_logical_fingerprint: str | None = None
    opportunity_candidates_file: str | None = None
    candidate_contract_version: Literal["opportunity-candidate/1.1"] | None = None
    candidate_analytics_logical_fingerprint: str | None = None
    candidate_audit_logical_fingerprint: str | None = None
    candidate_parameter_fingerprint: str | None = None
    candidate_state_parameter_fingerprint: str | None = None
    candidate_primary_display_count: int | None = None
    candidate_secondary_display_count: int | None = None
    candidate_publication_contract_version: str | None = None
    entry_geometry_contract_version: str | None = None
    entry_geometry_audit_logical_fingerprint: str | None = None
    entry_geometry_parameter_fingerprint: str | None = None
    entry_lane_consumer_parameter_fingerprint: str | None = None
    candidate_summary_contract_version: str | None = None
    candidate_summary_logical_fingerprint: str | None = None
    candidate_detail_contract_version: str | None = None
    candidate_detail_files: tuple[str, ...] = ()
    candidate_strategy_file: str | None = None
    candidate_strategy_contract_version: str | None = None
    candidate_strategy_audit_manifest_sha256: str | None = None
    candidate_strategy_audit_logical_fingerprint: str | None = None
    candidate_strategy_parameter_fingerprint: str | None = None
    candidate_strategy_logical_fingerprint: str | None = None
    candidate_visual_context_contract_version: str | None = None
    candidate_visual_context_audit_manifest_sha256: str | None = None
    candidate_visual_context_audit_logical_fingerprint: str | None = None
    candidate_visual_context_batch_fingerprints: tuple[str, ...] = ()
    sector_rotation_file: str | None = None
    sector_rotation_snapshot_contract_version: str | None = None
    sector_rotation_snapshot_logical_fingerprint: str | None = None
    sector_rotation_audit_manifest_sha256: str | None = None
    sector_rotation_audit_logical_fingerprint: str | None = None
    sector_rotation_parameter_fingerprint: str | None = None
    sector_rotation_history_source_fingerprint: str | None = None
    sector_rotation_product_logical_fingerprint: str | None = None
    review_mode: bool = False
    review_contract_version: str | None = None
    review_approved_as_of_session: str | None = None
    review_expected_latest_session: str | None = None
    review_expected_lag_sessions: int | None = None
    is_real_provider_backed: bool
    access_classification: str
    contains_raw_provider_data: bool
    contains_credentials: bool

    @field_validator("release_id")
    @classmethod
    def release_id_is_safe(cls, value: str) -> str:
        validate_release_id(value)
        return value

    @field_validator(
        "candidate_visual_context_audit_manifest_sha256",
        "candidate_visual_context_audit_logical_fingerprint",
    )
    @classmethod
    def optional_visual_digests(cls, value: str | None) -> str | None:
        if value is not None and (
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("Candidate visual-context fingerprint must be SHA-256")
        return value

    @field_validator("candidate_visual_context_batch_fingerprints")
    @classmethod
    def visual_batch_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in values
        ):
            raise ValueError("Candidate visual-context batch fingerprint must be SHA-256")
        return values

    @field_validator(
        "sector_rotation_snapshot_logical_fingerprint",
        "sector_rotation_audit_manifest_sha256",
        "sector_rotation_audit_logical_fingerprint",
        "sector_rotation_parameter_fingerprint",
        "sector_rotation_history_source_fingerprint",
        "sector_rotation_product_logical_fingerprint",
    )
    @classmethod
    def optional_sector_rotation_digests(cls, value: str | None) -> str | None:
        if value is not None and (
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("Sector Rotation fingerprint must be SHA-256")
        return value

    @model_validator(mode="after")
    def freshness_contract_is_complete(self) -> DashboardSnapshotManifest:
        if self.snapshot_contract_version in {"1.1", "1.2"} and any(
            value is None
            for value in (
                self.expected_latest_completed_session,
                self.actual_latest_completed_session,
                self.session_lag,
                self.freshness_status,
                self.calendar_id,
                self.freshness_checked_at,
            )
        ):
            raise ValueError("snapshot freshness fields are required for contract 1.1")
        if self.snapshot_contract_version == "1.2" and self.classification_as_of_date is None:
            raise ValueError("snapshot governance fields are required for contract 1.2")
        if self.snapshot_contract_version in {"1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"} and (
            self.classification_as_of_date is None or self.selected_universe_id is None or
            len(self.available_universe_ids) != 2 or self.activation_fingerprint is None or
            self.membership_evidence_as_of is None
        ):
            raise ValueError("snapshot activation fields are required for contract 1.3+")
        if self.snapshot_contract_version in {"1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"} and (
            self.funnel_stage_count != 20 or self.funnel_source_fingerprint is None
        ):
            raise ValueError("snapshot Funnel fields are required for contract 1.4")
        if self.snapshot_contract_version in {"1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"} and any(
            value is None
            for value in (
                self.market_intelligence_file,
                self.market_intelligence_publication_id,
                self.market_intelligence_payload_sha256,
                self.market_intelligence_logical_fingerprint,
                self.analytics_payload_logical_fingerprint,
            )
        ):
            raise ValueError("snapshot Market Intelligence fields are required for contract 1.5")
        candidate_values = (
            self.opportunity_candidates_file,
            self.candidate_contract_version,
            self.candidate_analytics_logical_fingerprint,
            self.candidate_audit_logical_fingerprint,
            self.candidate_parameter_fingerprint,
            self.candidate_state_parameter_fingerprint,
            self.candidate_primary_display_count,
            self.candidate_secondary_display_count,
        )
        if self.snapshot_contract_version in {"1.6", "1.7", "1.8", "1.9", "1.10", "1.11"}:
            expected_dashboard = {
                "1.6": "2.3",
                "1.7": "2.4",
                "1.8": "2.5",
                "1.9": "2.6",
                "1.10": "2.7",
                "1.11": "2.8",
            }[self.snapshot_contract_version]
            if self.dashboard_contract_version != expected_dashboard or any(
                value is None for value in candidate_values
            ):
                raise ValueError(
                    f"Snapshot {self.snapshot_contract_version} requires Dashboard {expected_dashboard} Candidate bindings"
                )
        elif any(value is not None for value in candidate_values):
            raise ValueError("Snapshot before 1.6 cannot carry Candidate bindings")
        entry_values = (
            self.candidate_publication_contract_version,
            self.entry_geometry_contract_version,
            self.entry_geometry_audit_logical_fingerprint,
            self.entry_geometry_parameter_fingerprint,
            self.entry_lane_consumer_parameter_fingerprint,
        )
        if self.snapshot_contract_version in {"1.7", "1.8", "1.9", "1.10", "1.11"}:
            if (
                any(value is None for value in entry_values)
                or self.candidate_publication_contract_version
                != "opportunity-candidate-publication/1.1"
                or self.entry_geometry_contract_version != "candidate-entry-geometry/1.0"
            ):
                raise ValueError("Snapshot 1.7 requires complete entry-geometry bindings")
        elif any(value is not None for value in entry_values):
            raise ValueError("Snapshot before 1.7 cannot carry entry-geometry bindings")
        split_values = (
            self.candidate_summary_contract_version,
            self.candidate_summary_logical_fingerprint,
            self.candidate_detail_contract_version,
        )
        if self.snapshot_contract_version in {"1.8", "1.9", "1.10", "1.11"}:
            if (
                self.opportunity_candidates_file != OPPORTUNITY_CANDIDATE_SUMMARY_FILE
                or self.candidate_summary_contract_version
                != SUMMARY_ANALYTICS_CONTRACT_VERSION
                or self.candidate_detail_contract_version
                != (
                    DETAIL_SHARD_CONTRACT_VERSION_V1_1
                    if self.snapshot_contract_version in {"1.10", "1.11"}
                    else DETAIL_SHARD_CONTRACT_VERSION
                )
                or self.candidate_summary_logical_fingerprint is None
                or not self.candidate_detail_files
                or tuple(self.candidate_detail_files)
                != tuple(sorted(self.candidate_detail_files))
                or len(self.candidate_detail_files) != len(set(self.candidate_detail_files))
                or any(
                    DETAIL_FILE_RE.fullmatch(value) is None
                    for value in self.candidate_detail_files
                )
            ):
                raise ValueError("Snapshot 1.8+ requires split Candidate bindings")
        elif any(value is not None for value in split_values) or self.candidate_detail_files:
            raise ValueError("Snapshot before 1.8 cannot carry split Candidate bindings")
        strategy_values = (
            self.candidate_strategy_file,
            self.candidate_strategy_contract_version,
            self.candidate_strategy_audit_manifest_sha256,
            self.candidate_strategy_audit_logical_fingerprint,
            self.candidate_strategy_parameter_fingerprint,
            self.candidate_strategy_logical_fingerprint,
        )
        if self.snapshot_contract_version in {"1.9", "1.10", "1.11"}:
            if (
                any(value is None for value in strategy_values)
                or self.candidate_strategy_file != CANDIDATE_STRATEGY_CHANNELS_FILE
                or self.candidate_strategy_contract_version
                != "candidate-strategy-channel-product/1.0"
            ):
                raise ValueError(
                    "Snapshot 1.9 requires complete strategy-channel bindings"
                )
        elif any(value is not None for value in strategy_values):
            raise ValueError(
                "Snapshot before 1.9 cannot carry strategy-channel bindings"
            )
        visual_values = (
            self.candidate_visual_context_contract_version,
            self.candidate_visual_context_audit_manifest_sha256,
            self.candidate_visual_context_audit_logical_fingerprint,
        )
        if self.snapshot_contract_version in {"1.10", "1.11"}:
            if (
                any(value is None for value in visual_values)
                or self.candidate_visual_context_contract_version
                != "candidate-visual-context/1.0"
                or len(self.candidate_visual_context_batch_fingerprints) != 2
            ):
                raise ValueError(
                    "Snapshot 1.10+ requires complete Candidate visual-context bindings"
                )
        elif any(value is not None for value in visual_values) or self.candidate_visual_context_batch_fingerprints:
            raise ValueError(
                "Snapshot before 1.10 cannot carry Candidate visual-context bindings"
            )
        sector_values = (
            self.sector_rotation_file,
            self.sector_rotation_snapshot_contract_version,
            self.sector_rotation_snapshot_logical_fingerprint,
            self.sector_rotation_audit_manifest_sha256,
            self.sector_rotation_audit_logical_fingerprint,
            self.sector_rotation_parameter_fingerprint,
            self.sector_rotation_history_source_fingerprint,
            self.sector_rotation_product_logical_fingerprint,
        )
        if self.snapshot_contract_version == "1.11":
            if (
                any(value is None for value in sector_values)
                or self.sector_rotation_file != SECTOR_ETF_ROTATION_FILE
                or self.sector_rotation_snapshot_contract_version
                != "sector-etf-rotation-dashboard-snapshot/1.0"
            ):
                raise ValueError(
                    "Snapshot 1.11 requires complete Sector Rotation bindings"
                )
        elif any(value is not None for value in sector_values):
            raise ValueError(
                "Snapshot before 1.11 cannot carry Sector Rotation bindings"
            )
        review_values = (
            self.review_contract_version,
            self.review_approved_as_of_session,
            self.review_expected_latest_session,
            self.review_expected_lag_sessions,
        )
        if self.review_mode:
            if any(value is None for value in review_values) or self.data_status != "stale_review":
                raise ValueError("snapshot review deployment metadata is incomplete")
            if (
                self.current_session_date != self.review_approved_as_of_session
                or self.actual_latest_completed_session != self.review_approved_as_of_session
                or self.expected_latest_completed_session != self.review_expected_latest_session
                or self.session_lag != self.review_expected_lag_sessions
                or self.freshness_status != "stale"
            ):
                raise ValueError("snapshot review freshness differs from authorization")
        elif any(value is not None for value in review_values):
            raise ValueError("normal snapshot cannot carry review deployment metadata")
        return self


@dataclass(frozen=True, slots=True)
class DashboardSnapshotResult:
    release_id: str
    output_dir: Path
    manifest: DashboardSnapshotManifest


def validate_release_id(value: str) -> str:
    if not _RELEASE_ID_RE.fullmatch(value):
        raise ValueError("release_id must be UTC timestamp plus git commit, for example 2026-08-13T120000Z-abcdef0")
    return value


def make_release_id(*, session_date: str, generated_at: datetime | None = None, git_commit: str | None = None) -> str:
    generated = generated_at or datetime.now(UTC)
    commit = git_commit or _git_commit()
    safe_commit = commit.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{7,40}", safe_commit):
        raise DashboardSnapshotError("git commit is not a safe hexadecimal value")
    value = f"{session_date}T{generated.strftime('%H%M%S')}Z-{safe_commit[:12]}"
    validate_release_id(value)
    return value


def build_private_dashboard_snapshot(
    *,
    data_root: Path,
    output_root: Path,
    release_id: str | None = None,
    generated_at: datetime | None = None,
    git_commit: str | None = None,
    allowed_output_root: Path | None = None,
    dashboard_activation: ActiveDashboardUniverseActivation | None = None,
    market_intelligence: CompletedMarketIntelligence | None = None,
    candidate_strategy_audit_path: Path | None = None,
    candidate_visual_context_audit_path: Path | None = None,
) -> DashboardSnapshotResult:
    safe_data_root = _validate_existing_root(data_root, label="data_root")
    safe_output_root = _validate_output_root(output_root, allowed_output_root=allowed_output_root)

    query_service = EodMarketDataQueryService(CanonicalEodReadRepository(safe_data_root))
    analytics = EodReturnAnalyticsService(query_service)
    generated = generated_at or datetime.now(UTC)
    activation = dashboard_activation or read_active_dashboard_universe_activation(safe_data_root, analysis_session=query_service.list_sessions()[-1].session_date, validate_sources=True)
    overview = DashboardOverviewResponse.from_model(
        DashboardOverviewService(query_service, activation).get_latest_overview(checked_at=generated)
    ).model_copy(
        update={"snapshot_generated_at": generated.astimezone(UTC).isoformat().replace("+00:00", "Z")}
    )
    review = market_intelligence.payload.review_deployment if market_intelligence else None
    candidate_mi_payload = (
        market_intelligence.payload
        if market_intelligence is not None
        and isinstance(market_intelligence.payload, MarketIntelligencePayloadV1_1)
        else None
    )
    if review is not None:
        if (
            overview.current_session_date != review.approved_as_of_session
            or overview.actual_latest_completed_session != review.approved_as_of_session
            or overview.expected_latest_completed_session != review.expected_latest_session
            or overview.session_lag != review.expected_lag_sessions
            or overview.freshness_status != "stale"
        ):
            raise DashboardSnapshotError(
                "Dashboard freshness no longer matches Market Intelligence review authorization"
            )
        overview = overview.model_copy(
            update={
                "data_status": "stale_review",
                "review_mode": True,
                "review_contract_version": review.contract_version,
                "review_approved_as_of_session": review.approved_as_of_session,
                "review_expected_latest_session": review.expected_latest_session,
                "review_expected_lag_sessions": review.expected_lag_sessions,
            }
        )
    default_universe = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    summary = default_universe.summary
    movers = default_universe.movers
    liquidity_map = default_universe.trading_activity_map

    if not (
        summary.current_session_date == movers.current_session_date == liquidity_map.current_session_date
        and summary.previous_session_date == movers.previous_session_date == liquidity_map.previous_session_date
    ):
        raise DashboardSnapshotError("market summary snapshot session dates are inconsistent")

    rid = release_id or make_release_id(
        session_date=summary.current_session_date.isoformat(), generated_at=generated, git_commit=git_commit
    )
    validate_release_id(rid)

    final_dir = _contained_child(safe_output_root, rid)
    if final_dir.exists():
        raise DashboardSnapshotError("snapshot release already exists")
    staging_dir = _contained_child(safe_output_root, f".{rid}.staging")
    if staging_dir.exists():
        raise DashboardSnapshotError("snapshot staging directory already exists")

    staging_private = staging_dir / "private-data" / "v1"
    staging_private.mkdir(parents=True, exist_ok=False)
    try:
        payloads: dict[str, BaseModel | Mapping[str, Any]] = {
            SNAPSHOT_FILES["overview_file"]: overview,
            SNAPSHOT_FILES["summary_file"]: summary,
            SNAPSHOT_FILES["movers_file"]: movers,
            SNAPSHOT_FILES["liquidity_map_file"]: liquidity_map,
        }
        market_payload: Mapping[str, Any] | None = None
        candidate_payload: Mapping[str, Any] | None = None
        candidate_summary: OpportunityCandidateSummarySnapshotV1 | None = None
        candidate_detail_shards: tuple[
            OpportunityCandidateDetailShardV1 | OpportunityCandidateDetailShardV1_1, ...
        ] = ()
        candidate_strategy: CandidateStrategyChannelProductV1 | None = None
        sector_rotation_snapshot: SectorEtfRotationDashboardSnapshotV1 | None = None
        visual_manifest: dict[str, Any] | None = None
        visual_batches = None
        if candidate_visual_context_audit_path is not None:
            if candidate_strategy_audit_path is None:
                raise DashboardSnapshotError(
                    "visual-context Snapshot requires strategy-channel binding"
                )
            visual_manifest, visual_batches = read_candidate_visual_context_batches(
                candidate_visual_context_audit_path
            )
        if candidate_strategy_audit_path is not None and not isinstance(
            candidate_mi_payload, MarketIntelligencePayloadV1_2
        ):
            raise DashboardSnapshotError(
                "strategy-channel Snapshot requires Candidate publication 1.1"
            )
        if market_intelligence is not None:
            if (
                market_intelligence.payload.analysis_session != summary.current_session_date
                or market_intelligence.payload.source.activation.logical_fingerprint
                != overview.activation_fingerprint
                or market_intelligence.payload.source.activation.universes
                != tuple(
                    PreviewUniverseDefinitionV1(
                        universe_id=item.definition.universe_id,
                        display_name=item.definition.display_name,
                        catalog_order=index,
                        is_default=item.definition.universe_id == overview.default_universe_id,
                        member_count=item.definition.member_count,
                        membership_fingerprint=item.definition.membership_fingerprint,
                    )
                    for index, item in enumerate(overview.universes)
                )
            ):
                raise DashboardSnapshotError(
                    "Market Intelligence source does not match Dashboard Snapshot sources"
                )
            market_service = MarketRegimePreviewService.from_payload(
                market_intelligence.payload.analytics,
                market_intelligence.payload.source.preview_generated_at,
                market_intelligence.payload.review_deployment,
            )
            market_payload = {
                "schema_version": "1.0",
                "contract_version": "market-regime-snapshot/1.0",
                "publication_id": market_intelligence.payload.publication_id,
                "payload_sha256": market_intelligence.manifest.payload_sha256,
                "payload_logical_fingerprint": market_intelligence.payload.logical_fingerprint,
                "analytics_logical_fingerprint": (
                    market_intelligence.payload.analytics.logical_fingerprint
                ),
                "review_deployment": (
                    review.model_dump(mode="json") if review is not None else None
                ),
                "default_universe_id": overview.default_universe_id,
                "universe_order": [item.definition.universe_id for item in overview.universes],
                "records": [
                    market_service.overview(item.definition.universe_id).model_dump(mode="json")
                    for item in overview.universes
                ],
            }
            payloads[MARKET_INTELLIGENCE_FILE] = market_payload
            if candidate_mi_payload is not None:
                has_entry_geometry = isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                if has_entry_geometry:
                    candidate_summary, candidate_detail_shards = build_split_candidate_snapshot(
                        candidate_analytics=candidate_mi_payload.candidate_analytics,
                        publication_id=market_intelligence.payload.publication_id,
                        payload_sha256=market_intelligence.manifest.payload_sha256,
                        payload_logical_fingerprint=(
                            market_intelligence.payload.logical_fingerprint
                        ),
                        visual_context_batches=visual_batches,
                        visual_context_audit_logical_fingerprint=(
                            visual_manifest["logical_content_fingerprint"]
                            if visual_manifest is not None
                            else None
                        ),
                    )
                    candidate_payload = candidate_summary.model_dump(mode="json")
                    payloads[OPPORTUNITY_CANDIDATE_SUMMARY_FILE] = candidate_summary
                    for shard in candidate_detail_shards:
                        payloads[
                            f"opportunity-candidate-details-{shard.shard_id}.json"
                        ] = shard
                    if candidate_strategy_audit_path is not None:
                        candidate_strategy = build_candidate_strategy_channel_product(
                            strategy_audit_dir=candidate_strategy_audit_path,
                            candidate_analytics=candidate_mi_payload.candidate_analytics,
                        )
                        payloads[CANDIDATE_STRATEGY_CHANNELS_FILE] = (
                            candidate_strategy
                        )
                else:
                    candidate_payload = {
                        "schema_version": "1.0",
                        "contract_version": "opportunity-candidate-snapshot/1.0",
                        "publication_id": market_intelligence.payload.publication_id,
                        "payload_sha256": market_intelligence.manifest.payload_sha256,
                        "payload_logical_fingerprint": market_intelligence.payload.logical_fingerprint,
                        "candidate_analytics_logical_fingerprint": (
                            candidate_mi_payload.candidate_analytics.logical_fingerprint
                        ),
                        "default_universe_id": overview.default_universe_id,
                        "universe_order": [item.definition.universe_id for item in overview.universes],
                        "analytics": candidate_mi_payload.candidate_analytics.model_dump(
                            mode="json"
                        ),
                    }
                    payloads[OPPORTUNITY_CANDIDATES_FILE] = candidate_payload
        if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_3):
            if visual_manifest is None or candidate_strategy is None:
                raise DashboardSnapshotError(
                    "Snapshot 1.11 requires the complete Snapshot 1.10 consumer chain"
                )
            sector_rotation_fields = {
                "publication_id": market_intelligence.payload.publication_id,
                "payload_sha256": market_intelligence.manifest.payload_sha256,
                "payload_logical_fingerprint": (
                    market_intelligence.payload.logical_fingerprint
                ),
                "source": candidate_mi_payload.sector_rotation_source,
                "product": candidate_mi_payload.sector_rotation,
            }
            sector_rotation_snapshot = SectorEtfRotationDashboardSnapshotV1(
                **sector_rotation_fields,
                logical_fingerprint=sector_rotation_dashboard_snapshot_fingerprint(
                    sector_rotation_fields
                ),
            )
            payloads[SECTOR_ETF_ROTATION_FILE] = sector_rotation_snapshot
        hashes: dict[str, str] = {}
        for filename, payload in payloads.items():
            path = staging_private / filename
            value = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
            _write_json(path, value)
            hashes[filename] = sha256_file(path)

        funnel_stage_count = sum(len(item.funnel) for item in overview.universes)
        snapshot_contract_version = (
            "1.11"
            if sector_rotation_snapshot is not None
            else "1.10"
            if visual_manifest is not None
            else "1.9"
            if candidate_strategy is not None
            else SNAPSHOT_CONTRACT_VERSION
            if funnel_stage_count == 20
            and isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
            else (
                "1.6"
                if funnel_stage_count == 20 and candidate_payload is not None
                else (
                "1.5"
                if funnel_stage_count == 20 and market_intelligence is not None
                else ("1.4" if funnel_stage_count == 20 else "1.3")
                )
            )
        )
        manifest = DashboardSnapshotManifest(
            snapshot_contract_version=snapshot_contract_version,
            release_id=rid,
            generated_at=generated.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            current_session_date=summary.current_session_date.isoformat(),
            previous_session_date=summary.previous_session_date.isoformat(),
            expected_latest_completed_session=(overview.expected_latest_completed_session.isoformat() if overview.expected_latest_completed_session else None),
            actual_latest_completed_session=(overview.actual_latest_completed_session.isoformat() if overview.actual_latest_completed_session else None),
            session_lag=overview.session_lag,
            freshness_status=overview.freshness_status,
            calendar_id=overview.calendar_id,
            freshness_checked_at=overview.freshness_checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            data_status="stale_review" if review is not None else summary.data_status,
            overview_file=SNAPSHOT_FILES["overview_file"],
            summary_file=SNAPSHOT_FILES["summary_file"],
            movers_file=SNAPSHOT_FILES["movers_file"],
            liquidity_map_file=SNAPSHOT_FILES["liquidity_map_file"],
            file_sha256=hashes,
            summary_node_count=1,
            mover_gainer_count=len(movers.top_gainers),
            mover_loser_count=len(movers.top_losers),
            liquidity_node_count=len(liquidity_map.nodes),
            warning_count=summary.quality_warning_count,
            default_universe_id=overview.default_universe_id,
            dashboard_contract_version=(
                "2.8"
                if snapshot_contract_version == "1.11"
                else "2.7"
                if snapshot_contract_version == "1.10"
                else "2.6"
                if snapshot_contract_version == "1.9"
                else "2.5"
                if snapshot_contract_version == "1.8"
                else "2.4"
                if snapshot_contract_version == "1.7"
                else "2.3"
                if snapshot_contract_version == "1.6"
                else ("2.2" if snapshot_contract_version == "1.5" else overview.contract_version)
            ),
            universe_definition_id=overview.universe_definition_id,
            universe_version=overview.universe_version,
            governance_status=overview.governance_status,
            classification_as_of_date=overview.classification_as_of_date.isoformat(),
            evidence_coverage_status=overview.evidence_coverage_status,
            selected_universe_id=overview.selected_universe_id,
            available_universe_ids=tuple(item.definition.universe_id for item in overview.universes),
            activation_fingerprint=overview.activation_fingerprint,
            membership_evidence_as_of=overview.classification_as_of_date.isoformat(),
            funnel_stage_count=(
                funnel_stage_count
                if snapshot_contract_version in {"1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"}
                else None
            ),
            funnel_source_fingerprint=(
                next(item.funnel[0].source_fingerprint for item in overview.universes if item.funnel)
                if snapshot_contract_version in {"1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"} else None
            ),
            market_intelligence_file=(
                MARKET_INTELLIGENCE_FILE if market_intelligence is not None else None
            ),
            market_intelligence_publication_id=(
                market_intelligence.payload.publication_id
                if market_intelligence is not None
                else None
            ),
            market_intelligence_payload_sha256=(
                market_intelligence.manifest.payload_sha256
                if market_intelligence is not None
                else None
            ),
            market_intelligence_logical_fingerprint=(
                market_intelligence.payload.logical_fingerprint
                if market_intelligence is not None
                else None
            ),
            analytics_payload_logical_fingerprint=(
                market_intelligence.payload.analytics.logical_fingerprint
                if market_intelligence is not None
                else None
            ),
            opportunity_candidates_file=(
                OPPORTUNITY_CANDIDATE_SUMMARY_FILE
                if candidate_summary is not None
                else OPPORTUNITY_CANDIDATES_FILE
                if candidate_payload is not None
                else None
            ),
            candidate_contract_version=(
                candidate_mi_payload.candidate_source.candidate_contract_version
                if candidate_mi_payload is not None
                else None
            ),
            candidate_analytics_logical_fingerprint=(
                candidate_mi_payload.candidate_analytics.logical_fingerprint
                if candidate_mi_payload is not None
                else None
            ),
            candidate_audit_logical_fingerprint=(
                candidate_mi_payload.candidate_source.candidate_audit_logical_fingerprint
                if candidate_mi_payload is not None
                else None
            ),
            candidate_parameter_fingerprint=(
                candidate_mi_payload.candidate_source.candidate_parameter_fingerprint
                if candidate_mi_payload is not None
                else None
            ),
            candidate_state_parameter_fingerprint=(
                candidate_mi_payload.candidate_source.candidate_state_parameter_fingerprint
                if candidate_mi_payload is not None
                else None
            ),
            candidate_primary_display_count=(
                len(candidate_mi_payload.candidate_analytics.universes[0].candidates)
                if candidate_mi_payload is not None
                else None
            ),
            candidate_secondary_display_count=(
                len(candidate_mi_payload.candidate_analytics.universes[1].candidates)
                if candidate_mi_payload is not None
                else None
            ),
            candidate_publication_contract_version=(
                candidate_mi_payload.candidate_analytics.contract_version
                if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                else None
            ),
            entry_geometry_contract_version=(
                candidate_mi_payload.candidate_source.entry_geometry_contract_version
                if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                else None
            ),
            entry_geometry_audit_logical_fingerprint=(
                candidate_mi_payload.candidate_source.entry_geometry_audit_logical_fingerprint
                if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                else None
            ),
            entry_geometry_parameter_fingerprint=(
                candidate_mi_payload.candidate_source.entry_geometry_parameter_fingerprint
                if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                else None
            ),
            entry_lane_consumer_parameter_fingerprint=(
                candidate_mi_payload.candidate_source.entry_lane_consumer_parameter_fingerprint
                if isinstance(candidate_mi_payload, MarketIntelligencePayloadV1_2)
                else None
            ),
            candidate_summary_contract_version=(
                candidate_summary.analytics.contract_version
                if candidate_summary is not None
                else None
            ),
            candidate_summary_logical_fingerprint=(
                candidate_summary.analytics.logical_fingerprint
                if candidate_summary is not None
                else None
            ),
            candidate_detail_contract_version=(
                candidate_detail_shards[0].contract_version
                if candidate_detail_shards
                else None
            ),
            candidate_detail_files=tuple(
                sorted(
                    f"opportunity-candidate-details-{item.shard_id}.json"
                    for item in candidate_detail_shards
                )
            ),
            candidate_strategy_file=(
                CANDIDATE_STRATEGY_CHANNELS_FILE
                if candidate_strategy is not None
                else None
            ),
            candidate_strategy_contract_version=(
                candidate_strategy.contract_version
                if candidate_strategy is not None
                else None
            ),
            candidate_strategy_audit_manifest_sha256=(
                candidate_strategy.source.strategy_audit_manifest_sha256
                if candidate_strategy is not None
                else None
            ),
            candidate_strategy_audit_logical_fingerprint=(
                candidate_strategy.source.strategy_audit_logical_fingerprint
                if candidate_strategy is not None
                else None
            ),
            candidate_strategy_parameter_fingerprint=(
                candidate_strategy.source.strategy_parameter_fingerprint
                if candidate_strategy is not None
                else None
            ),
            candidate_strategy_logical_fingerprint=(
                candidate_strategy.logical_fingerprint
                if candidate_strategy is not None
                else None
            ),
            candidate_visual_context_contract_version=(
                visual_manifest["contract_version"]
                if visual_manifest is not None
                else None
            ),
            candidate_visual_context_audit_manifest_sha256=(
                sha256_file(
                    candidate_visual_context_audit_path
                    / VISUAL_CONTEXT_AUDIT_MANIFEST
                )
                if candidate_visual_context_audit_path is not None
                else None
            ),
            candidate_visual_context_audit_logical_fingerprint=(
                visual_manifest["logical_content_fingerprint"]
                if visual_manifest is not None
                else None
            ),
            candidate_visual_context_batch_fingerprints=(
                tuple(visual_manifest["batch_fingerprints"])
                if visual_manifest is not None
                else ()
            ),
            sector_rotation_file=(
                SECTOR_ETF_ROTATION_FILE
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_snapshot_contract_version=(
                sector_rotation_snapshot.contract_version
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_snapshot_logical_fingerprint=(
                sector_rotation_snapshot.logical_fingerprint
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_audit_manifest_sha256=(
                sector_rotation_snapshot.source.audit_manifest_sha256
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_audit_logical_fingerprint=(
                sector_rotation_snapshot.source.audit_logical_fingerprint
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_parameter_fingerprint=(
                sector_rotation_snapshot.source.parameter_fingerprint
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_history_source_fingerprint=(
                sector_rotation_snapshot.source.history_source_fingerprint
                if sector_rotation_snapshot is not None
                else None
            ),
            sector_rotation_product_logical_fingerprint=(
                sector_rotation_snapshot.source.product_logical_fingerprint
                if sector_rotation_snapshot is not None
                else None
            ),
            review_mode=review is not None,
            review_contract_version=(review.contract_version if review is not None else None),
            review_approved_as_of_session=(
                review.approved_as_of_session.isoformat() if review is not None else None
            ),
            review_expected_latest_session=(
                review.expected_latest_session.isoformat() if review is not None else None
            ),
            review_expected_lag_sessions=(
                review.expected_lag_sessions if review is not None else None
            ),
            is_real_provider_backed=True,
            access_classification="private",
            contains_raw_provider_data=False,
            contains_credentials=False,
        )
        _write_json(staging_private / "manifest.json", manifest.model_dump(mode="json"))
        _validate_snapshot_dir(staging_private)
        (staging_dir / ".complete").write_text("completed\n", encoding="utf-8")
        os.replace(staging_dir, final_dir)
    except Exception:
        _cleanup_staging(staging_dir)
        raise

    completed_private = final_dir / "private-data" / "v1"
    manifest = _validate_snapshot_dir(completed_private)
    return DashboardSnapshotResult(release_id=rid, output_dir=final_dir, manifest=manifest)


def validate_snapshot_release(path: Path) -> DashboardSnapshotManifest:
    private_dir = path / "private-data" / "v1"
    return _validate_snapshot_dir(private_dir)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_json_bytes(payload: Mapping[str, Any]) -> bytes:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(deterministic_json_bytes(payload))
    os.replace(tmp, path)


def _validate_json_file(path: Path, filename: str) -> Any:
    """Validate one snapshot artifact and return its decoded contract value.

    Callers that need the payload for cross-file binding checks must reuse this
    return value.  Re-reading a multi-megabyte Candidate artifact immediately
    after contract validation adds no custody evidence and used to double the
    parsing cost of every full snapshot validation.
    """

    try:
        raw = path.read_bytes()
        decoded = json.loads(raw.decode("utf-8"))
        if filename == SNAPSHOT_FILES["summary_file"]:
            return MarketSummaryResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["overview_file"]:
            return DashboardOverviewResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["movers_file"]:
            return MoversResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["liquidity_map_file"]:
            return LiquidityMapResponse.model_validate(decoded)
        elif filename == MARKET_INTELLIGENCE_FILE:
            _validate_market_intelligence_snapshot(decoded)
            return decoded
        elif filename == OPPORTUNITY_CANDIDATES_FILE:
            _validate_opportunity_candidate_snapshot(decoded)
            return decoded
        elif filename == OPPORTUNITY_CANDIDATE_SUMMARY_FILE:
            return OpportunityCandidateSummarySnapshotV1.model_validate(decoded)
        elif filename == CANDIDATE_STRATEGY_CHANNELS_FILE:
            return CandidateStrategyChannelProductV1.model_validate(decoded)
        elif filename == SECTOR_ETF_ROTATION_FILE:
            return SectorEtfRotationDashboardSnapshotV1.model_validate(decoded)
        elif DETAIL_FILE_RE.fullmatch(filename):
            if decoded.get("contract_version") == DETAIL_SHARD_CONTRACT_VERSION_V1_1:
                return OpportunityCandidateDetailShardV1_1.model_validate(decoded)
            return OpportunityCandidateDetailShardV1.model_validate(decoded)
        else:
            raise DashboardSnapshotError(f"unexpected snapshot file {filename}")
    except DashboardSnapshotError:
        raise
    except Exception as exc:
        raise DashboardSnapshotError(f"invalid snapshot file {filename}") from exc


def _validate_snapshot_dir(private_dir: Path) -> DashboardSnapshotManifest:
    if not private_dir.is_dir() or private_dir.is_symlink():
        raise DashboardSnapshotError("snapshot private-data directory is invalid")
    manifest_path = private_dir / "manifest.json"
    manifest = DashboardSnapshotManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    expected_files = {
        *SNAPSHOT_FILES.values(),
        "manifest.json",
        *( {MARKET_INTELLIGENCE_FILE} if manifest.snapshot_contract_version in {"1.5", "1.6", "1.7"} else set() ),
        *( {OPPORTUNITY_CANDIDATES_FILE} if manifest.snapshot_contract_version in {"1.6", "1.7"} else set() ),
        *( {MARKET_INTELLIGENCE_FILE, OPPORTUNITY_CANDIDATE_SUMMARY_FILE, *manifest.candidate_detail_files}
            if manifest.snapshot_contract_version in {"1.8", "1.9", "1.10", "1.11"} else set() ),
        *( {CANDIDATE_STRATEGY_CHANNELS_FILE}
            if manifest.snapshot_contract_version in {"1.9", "1.10", "1.11"} else set() ),
        *( {SECTOR_ETF_ROTATION_FILE}
            if manifest.snapshot_contract_version == "1.11" else set() ),
    }
    actual_files = {item.name for item in private_dir.iterdir()}
    if actual_files != expected_files:
        raise DashboardSnapshotError("snapshot private-data file set is incomplete or has extras")
    validated_files: dict[str, Any] = {}
    for field, filename in SNAPSHOT_FILES.items():
        expected = getattr(manifest, field)
        if expected != filename:
            raise DashboardSnapshotError("snapshot manifest filename mismatch")
        file_path = private_dir / filename
        if file_path.is_symlink() or not file_path.is_file():
            raise DashboardSnapshotError("snapshot file is missing or unsafe")
        validated_files[filename] = _validate_json_file(file_path, filename)
        if sha256_file(file_path) != manifest.file_sha256[filename]:
            raise DashboardSnapshotError("snapshot file checksum mismatch")
    if manifest.access_classification != "private" or manifest.contains_credentials or manifest.contains_raw_provider_data:
        raise DashboardSnapshotError("snapshot manifest violates access boundary")
    if manifest.snapshot_contract_version in {"1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"}:
        overview = validated_files[manifest.overview_file]
        if overview.contract_version != "2.1" or sum(len(item.funnel) for item in overview.universes) != 20:
            raise DashboardSnapshotError("snapshot formal Funnel contract mismatch")
        fingerprints = {stage.source_fingerprint for item in overview.universes for stage in item.funnel}
        if fingerprints != {manifest.funnel_source_fingerprint}:
            raise DashboardSnapshotError("snapshot Funnel source fingerprint mismatch")
    if manifest.snapshot_contract_version in {"1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"}:
        expected_dashboard = (
            "2.8" if manifest.snapshot_contract_version == "1.11"
            else "2.7" if manifest.snapshot_contract_version == "1.10"
            else "2.6" if manifest.snapshot_contract_version == "1.9"
            else "2.5" if manifest.snapshot_contract_version == "1.8"
            else "2.4" if manifest.snapshot_contract_version == "1.7"
            else "2.3" if manifest.snapshot_contract_version == "1.6"
            else "2.2"
        )
        if manifest.dashboard_contract_version != expected_dashboard:
            raise DashboardSnapshotError(
                f"snapshot Dashboard contract {expected_dashboard} is required"
            )
        analytics_path = private_dir / MARKET_INTELLIGENCE_FILE
        if analytics_path.is_symlink() or not analytics_path.is_file():
            raise DashboardSnapshotError("snapshot Market Intelligence file is missing")
        analytics = _validate_json_file(analytics_path, MARKET_INTELLIGENCE_FILE)
        if sha256_file(analytics_path) != manifest.file_sha256.get(MARKET_INTELLIGENCE_FILE):
            raise DashboardSnapshotError("snapshot Market Intelligence checksum mismatch")
        if (
            analytics["publication_id"] != manifest.market_intelligence_publication_id
            or analytics["payload_sha256"] != manifest.market_intelligence_payload_sha256
            or analytics["payload_logical_fingerprint"]
            != manifest.market_intelligence_logical_fingerprint
            or analytics["analytics_logical_fingerprint"]
            != manifest.analytics_payload_logical_fingerprint
        ):
            raise DashboardSnapshotError("snapshot Market Intelligence reference mismatch")
        if analytics.get("review_deployment") != (
            {
                "contract_version": manifest.review_contract_version,
                "review_mode": True,
                "normal_freshness": False,
                "data_status": "stale_review",
                "approved_as_of_session": manifest.review_approved_as_of_session,
                "expected_latest_session": manifest.review_expected_latest_session,
                "expected_lag_sessions": manifest.review_expected_lag_sessions,
                "explicit_user_acknowledgement": review_acknowledgement_for_contract(
                    manifest.review_contract_version or ""
                ),
            }
            if manifest.review_mode
            else None
        ):
            raise DashboardSnapshotError("snapshot Market Intelligence review binding mismatch")
    if manifest.snapshot_contract_version in {"1.6", "1.7"}:
        candidate_path = private_dir / OPPORTUNITY_CANDIDATES_FILE
        if candidate_path.is_symlink() or not candidate_path.is_file():
            raise DashboardSnapshotError("snapshot Candidate file is missing")
        candidate = _validate_json_file(candidate_path, OPPORTUNITY_CANDIDATES_FILE)
        if sha256_file(candidate_path) != manifest.file_sha256.get(OPPORTUNITY_CANDIDATES_FILE):
            raise DashboardSnapshotError("snapshot Candidate checksum mismatch")
        analytics_type = (
            OpportunityCandidatePublicationV1_1
            if manifest.snapshot_contract_version == "1.7"
            else OpportunityCandidatePublicationV1
        )
        analytics = analytics_type.model_validate(candidate["analytics"])
        if (
            candidate["publication_id"] != manifest.market_intelligence_publication_id
            or candidate["payload_sha256"] != manifest.market_intelligence_payload_sha256
            or candidate["payload_logical_fingerprint"]
            != manifest.market_intelligence_logical_fingerprint
            or candidate["candidate_analytics_logical_fingerprint"]
            != manifest.candidate_analytics_logical_fingerprint
            or analytics.logical_fingerprint != manifest.candidate_analytics_logical_fingerprint
            or analytics.source.candidate_audit_logical_fingerprint
            != manifest.candidate_audit_logical_fingerprint
            or analytics.source.candidate_parameter_fingerprint
            != manifest.candidate_parameter_fingerprint
            or analytics.source.candidate_state_parameter_fingerprint
            != manifest.candidate_state_parameter_fingerprint
            or len(analytics.universes[0].candidates)
            != manifest.candidate_primary_display_count
            or len(analytics.universes[1].candidates)
            != manifest.candidate_secondary_display_count
        ):
            raise DashboardSnapshotError("snapshot Candidate reference mismatch")
        if manifest.snapshot_contract_version == "1.7" and (
            candidate.get("contract_version") != "opportunity-candidate-snapshot/1.1"
            or analytics.contract_version != manifest.candidate_publication_contract_version
            or analytics.source.entry_geometry_contract_version
            != manifest.entry_geometry_contract_version
            or analytics.source.entry_geometry_audit_logical_fingerprint
            != manifest.entry_geometry_audit_logical_fingerprint
            or analytics.source.entry_geometry_parameter_fingerprint
            != manifest.entry_geometry_parameter_fingerprint
            or analytics.source.entry_lane_consumer_parameter_fingerprint
            != manifest.entry_lane_consumer_parameter_fingerprint
        ):
            raise DashboardSnapshotError("snapshot entry-geometry reference mismatch")
    if manifest.snapshot_contract_version in {"1.8", "1.9", "1.10", "1.11"}:
        summary_path = private_dir / OPPORTUNITY_CANDIDATE_SUMMARY_FILE
        if summary_path.is_symlink() or not summary_path.is_file():
            raise DashboardSnapshotError("snapshot Candidate summary file is missing")
        summary = _validate_json_file(
            summary_path, OPPORTUNITY_CANDIDATE_SUMMARY_FILE
        )
        if sha256_file(summary_path) != manifest.file_sha256.get(
            OPPORTUNITY_CANDIDATE_SUMMARY_FILE
        ):
            raise DashboardSnapshotError("snapshot Candidate summary checksum mismatch")
        shards: list[
            OpportunityCandidateDetailShardV1 | OpportunityCandidateDetailShardV1_1
        ] = []
        for filename in manifest.candidate_detail_files:
            path = private_dir / filename
            if path.is_symlink() or not path.is_file():
                raise DashboardSnapshotError("snapshot Candidate detail shard is missing")
            shard = _validate_json_file(path, filename)
            if sha256_file(path) != manifest.file_sha256.get(filename):
                raise DashboardSnapshotError("snapshot Candidate detail checksum mismatch")
            shard_type = (
                OpportunityCandidateDetailShardV1_1
                if manifest.snapshot_contract_version in {"1.10", "1.11"}
                else OpportunityCandidateDetailShardV1
            )
            if not isinstance(shard, shard_type):
                raise DashboardSnapshotError(
                    "snapshot Candidate detail contract version mismatch"
                )
            shards.append(shard)
        analytics = reconstruct_full_candidate_publication(summary, tuple(shards))
        if (
            summary.publication_id != manifest.market_intelligence_publication_id
            or summary.payload_sha256 != manifest.market_intelligence_payload_sha256
            or summary.payload_logical_fingerprint
            != manifest.market_intelligence_logical_fingerprint
            or summary.candidate_analytics_logical_fingerprint
            != manifest.candidate_analytics_logical_fingerprint
            or summary.analytics.logical_fingerprint
            != manifest.candidate_summary_logical_fingerprint
            or summary.analytics.contract_version
            != manifest.candidate_summary_contract_version
            or analytics.contract_version
            != manifest.candidate_publication_contract_version
            or analytics.source.candidate_audit_logical_fingerprint
            != manifest.candidate_audit_logical_fingerprint
            or analytics.source.candidate_parameter_fingerprint
            != manifest.candidate_parameter_fingerprint
            or analytics.source.candidate_state_parameter_fingerprint
            != manifest.candidate_state_parameter_fingerprint
            or analytics.source.entry_geometry_contract_version
            != manifest.entry_geometry_contract_version
            or analytics.source.entry_geometry_audit_logical_fingerprint
            != manifest.entry_geometry_audit_logical_fingerprint
            or analytics.source.entry_geometry_parameter_fingerprint
            != manifest.entry_geometry_parameter_fingerprint
            or analytics.source.entry_lane_consumer_parameter_fingerprint
            != manifest.entry_lane_consumer_parameter_fingerprint
            or len(analytics.universes[0].candidates)
            != manifest.candidate_primary_display_count
            or len(analytics.universes[1].candidates)
            != manifest.candidate_secondary_display_count
        ):
            raise DashboardSnapshotError("snapshot split Candidate binding differs")
        if manifest.snapshot_contract_version in {"1.10", "1.11"} and any(
            not isinstance(shard, OpportunityCandidateDetailShardV1_1)
            or shard.visual_context_contract_version
            != manifest.candidate_visual_context_contract_version
            or shard.visual_context_audit_logical_fingerprint
            != manifest.candidate_visual_context_audit_logical_fingerprint
            for shard in shards
        ):
            raise DashboardSnapshotError(
                "snapshot Candidate visual-context binding differs"
            )
    if manifest.snapshot_contract_version in {"1.9", "1.10", "1.11"}:
        strategy_path = private_dir / CANDIDATE_STRATEGY_CHANNELS_FILE
        if strategy_path.is_symlink() or not strategy_path.is_file():
            raise DashboardSnapshotError(
                "snapshot Candidate strategy-channel file is missing"
            )
        strategy = _validate_json_file(
            strategy_path, CANDIDATE_STRATEGY_CHANNELS_FILE
        )
        if sha256_file(strategy_path) != manifest.file_sha256.get(
            CANDIDATE_STRATEGY_CHANNELS_FILE
        ):
            raise DashboardSnapshotError(
                "snapshot Candidate strategy-channel checksum mismatch"
            )
        if (
            strategy.contract_version
            != manifest.candidate_strategy_contract_version
            or strategy.logical_fingerprint
            != manifest.candidate_strategy_logical_fingerprint
            or strategy.source.strategy_audit_manifest_sha256
            != manifest.candidate_strategy_audit_manifest_sha256
            or strategy.source.strategy_audit_logical_fingerprint
            != manifest.candidate_strategy_audit_logical_fingerprint
            or strategy.source.strategy_parameter_fingerprint
            != manifest.candidate_strategy_parameter_fingerprint
            or strategy.source.candidate_analytics_logical_fingerprint
            != manifest.candidate_analytics_logical_fingerprint
            or strategy.source.candidate_audit_logical_fingerprint
            != manifest.candidate_audit_logical_fingerprint
            or strategy.source.entry_geometry_audit_logical_fingerprint
            != manifest.entry_geometry_audit_logical_fingerprint
            or strategy.default_universe_id != manifest.default_universe_id
            or strategy.universe_order != manifest.available_universe_ids
            or strategy.as_of_session.isoformat() != manifest.current_session_date
        ):
            raise DashboardSnapshotError(
                "snapshot Candidate strategy-channel binding differs"
            )
    if manifest.snapshot_contract_version == "1.11":
        rotation_path = private_dir / SECTOR_ETF_ROTATION_FILE
        if rotation_path.is_symlink() or not rotation_path.is_file():
            raise DashboardSnapshotError(
                "snapshot Sector Rotation file is missing"
            )
        rotation = _validate_json_file(rotation_path, SECTOR_ETF_ROTATION_FILE)
        if sha256_file(rotation_path) != manifest.file_sha256.get(
            SECTOR_ETF_ROTATION_FILE
        ):
            raise DashboardSnapshotError(
                "snapshot Sector Rotation checksum mismatch"
            )
        if (
            rotation.contract_version
            != manifest.sector_rotation_snapshot_contract_version
            or rotation.logical_fingerprint
            != manifest.sector_rotation_snapshot_logical_fingerprint
            or rotation.publication_id
            != manifest.market_intelligence_publication_id
            or rotation.payload_sha256
            != manifest.market_intelligence_payload_sha256
            or rotation.payload_logical_fingerprint
            != manifest.market_intelligence_logical_fingerprint
            or rotation.source.audit_manifest_sha256
            != manifest.sector_rotation_audit_manifest_sha256
            or rotation.source.audit_logical_fingerprint
            != manifest.sector_rotation_audit_logical_fingerprint
            or rotation.source.parameter_fingerprint
            != manifest.sector_rotation_parameter_fingerprint
            or rotation.source.history_source_fingerprint
            != manifest.sector_rotation_history_source_fingerprint
            or rotation.source.product_logical_fingerprint
            != manifest.sector_rotation_product_logical_fingerprint
            or rotation.product.as_of_session.isoformat()
            != manifest.current_session_date
        ):
            raise DashboardSnapshotError(
                "snapshot Sector Rotation binding differs"
            )
    return manifest


def _validate_market_intelligence_snapshot(value: object) -> None:
    if not isinstance(value, dict):
        raise DashboardSnapshotError("Market Intelligence snapshot is not an object")
    if (
        value.get("schema_version") != "1.0"
        or value.get("contract_version") != "market-regime-snapshot/1.0"
        or not isinstance(value.get("records"), list)
        or len(value["records"]) != 2
        or value.get("universe_order")
        != [
            "provider_classified_common_shares_v1",
            "provider_classified_common_shares_plus_adrs_v1",
        ]
    ):
        raise DashboardSnapshotError("Market Intelligence snapshot contract is invalid")
    from tip_api.contracts.analytics.v1 import MarketRegimeOpportunityMapResponseV1

    records = tuple(
        MarketRegimeOpportunityMapResponseV1.model_validate(item) for item in value["records"]
    )
    if tuple(item.selected_universe_id for item in records) != tuple(value["universe_order"]):
        raise DashboardSnapshotError("Market Intelligence snapshot Universe order differs")
    if any(len(item.relationships) != 16 for item in records):
        raise DashboardSnapshotError("Market Intelligence snapshot pair registry is incomplete")


def _validate_opportunity_candidate_snapshot(value: object) -> None:
    if not isinstance(value, dict):
        raise DashboardSnapshotError("Candidate snapshot is not an object")
    if (
        value.get("schema_version") != "1.0"
        or value.get("contract_version") not in {
            "opportunity-candidate-snapshot/1.0",
            "opportunity-candidate-snapshot/1.1",
        }
        or value.get("universe_order")
        != [
            "provider_classified_common_shares_v1",
            "provider_classified_common_shares_plus_adrs_v1",
        ]
    ):
        raise DashboardSnapshotError("Candidate snapshot contract is invalid")
    analytics_type = (
        OpportunityCandidatePublicationV1_1
        if value.get("contract_version") == "opportunity-candidate-snapshot/1.1"
        else OpportunityCandidatePublicationV1
    )
    analytics = analytics_type.model_validate(value.get("analytics"))
    if (
        analytics.universe_order != tuple(value["universe_order"])
        or analytics.default_universe_id != value.get("default_universe_id")
        or analytics.logical_fingerprint
        != value.get("candidate_analytics_logical_fingerprint")
    ):
        raise DashboardSnapshotError("Candidate snapshot analytics binding differs")


def _validate_existing_root(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_absolute() or resolved.is_symlink() or not resolved.is_dir():
        raise DashboardSnapshotError(f"{label} must be an existing absolute non-symlink directory")
    return resolved


def _validate_output_root(path: Path, *, allowed_output_root: Path | None) -> Path:
    if not path.is_absolute():
        raise DashboardSnapshotError("output_root must be absolute")
    if path.exists() and path.is_symlink():
        raise DashboardSnapshotError("output_root must not be a symlink")
    allowed = allowed_output_root or path
    if not allowed.is_absolute():
        raise DashboardSnapshotError("allowed_output_root must be absolute")
    if allowed.exists() and allowed.is_symlink():
        raise DashboardSnapshotError("allowed_output_root must not be a symlink")
    allowed.mkdir(parents=True, exist_ok=True)
    resolved_allowed = allowed.resolve(strict=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = path.parent.resolve(strict=True)
    resolved = resolved_parent / path.name
    if not str(resolved).startswith(str(resolved_allowed)):
        raise DashboardSnapshotError("output_root is outside the approved build directory")
    resolved.mkdir(parents=True, exist_ok=True)
    if resolved.is_symlink():
        raise DashboardSnapshotError("output_root must not be a symlink")
    return resolved

def _contained_child(parent: Path, child_name: str) -> Path:
    if "/" in child_name or ".." in child_name:
        raise DashboardSnapshotError("unsafe child path")
    child = parent / child_name
    if not str(child.resolve(strict=False)).startswith(str(parent.resolve(strict=True))):
        raise DashboardSnapshotError("child path escapes output root")
    return child


def _cleanup_staging(path: Path) -> None:
    if not path.exists() or path.is_symlink():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_symlink():
            child.unlink()
        elif child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as exc:  # pragma: no cover - operational fallback
        raise DashboardSnapshotError("unable to determine git commit") from exc
