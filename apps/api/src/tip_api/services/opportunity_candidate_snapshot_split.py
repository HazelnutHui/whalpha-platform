"""Lossless summary/detail projection for static Candidate snapshots."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from tip_api.contracts.analytics.v1.opportunity_candidate_publication import (
    OpportunityCandidatePublicationItemV1_1,
    OpportunityCandidatePublicationV1_1,
)
from tip_api.contracts.analytics.v1.opportunity_candidate_snapshot import (
    CandidateDetailShardDescriptorV1,
    CandidateEntrySummaryV1,
    CandidateSummaryItemV1,
    CandidateSummaryUniverseV1,
    OpportunityCandidateDetailShardV1,
    OpportunityCandidateDetailShardV1_1,
    OpportunityCandidateSummaryAnalyticsV1,
    OpportunityCandidateSummarySnapshotV1,
    logical_fingerprint,
)
from tip_api.contracts.analytics.v1.candidate_visual_context import (
    CandidateVisualContextBatchV1,
    CandidateVisualContextV1,
)


class OpportunityCandidateSnapshotSplitError(RuntimeError):
    """Raised when the split projection cannot reproduce its full source."""


def build_split_candidate_snapshot(
    *,
    candidate_analytics: OpportunityCandidatePublicationV1_1,
    publication_id: str,
    payload_sha256: str,
    payload_logical_fingerprint: str,
    visual_context_batches: tuple[CandidateVisualContextBatchV1, ...] | None = None,
    visual_context_audit_logical_fingerprint: str | None = None,
) -> tuple[
    OpportunityCandidateSummarySnapshotV1,
    tuple[OpportunityCandidateDetailShardV1 | OpportunityCandidateDetailShardV1_1, ...],
]:
    if (visual_context_batches is None) != (
        visual_context_audit_logical_fingerprint is None
    ):
        raise OpportunityCandidateSnapshotSplitError(
            "Candidate visual-context batches and audit binding must be supplied together"
        )
    visual_by_universe: dict[str, dict[str, CandidateVisualContextV1]] = {}
    if visual_context_batches is not None:
        if (
            tuple(batch.universe_id for batch in visual_context_batches)
            != candidate_analytics.universe_order
            or tuple(
                batch.source_candidate_batch_fingerprint
                for batch in visual_context_batches
            )
            != candidate_analytics.source.current_candidate_batch_fingerprints
            or tuple(
                batch.source_entry_geometry_batch_fingerprint
                for batch in visual_context_batches
            )
            != candidate_analytics.source.entry_geometry_batch_fingerprints
            or any(
                batch.as_of_session != candidate_analytics.as_of_session
                for batch in visual_context_batches
            )
        ):
            raise OpportunityCandidateSnapshotSplitError(
                "Candidate visual-context batch lineage differs from publication"
            )
        for batch in visual_context_batches:
            mapping = {str(row.instrument_id): row for row in batch.records}
            if len(mapping) != len(batch.records):
                raise OpportunityCandidateSnapshotSplitError(
                    "Candidate visual-context stable IDs are duplicated"
                )
            visual_by_universe[batch.universe_id] = mapping

    shards: list[
        OpportunityCandidateDetailShardV1 | OpportunityCandidateDetailShardV1_1
    ] = []
    descriptors: list[CandidateDetailShardDescriptorV1] = []
    summary_universes: list[CandidateSummaryUniverseV1] = []

    for universe_index, universe in enumerate(candidate_analytics.universes):
        grouped: dict[str, list[OpportunityCandidatePublicationItemV1_1]] = defaultdict(list)
        for item in universe.candidates:
            grouped[str(item.instrument_id)[0]].append(item)
        for prefix in sorted(grouped):
            shard_id = f"u{universe_index}-{prefix}"
            base: dict[str, object] = {
                "schema_version": "1.0",
                "contract_version": (
                    "opportunity-candidate-detail-shard/1.1"
                    if visual_context_batches is not None
                    else "opportunity-candidate-detail-shard/1.0"
                ),
                "publication_id": publication_id,
                "candidate_analytics_logical_fingerprint": (
                    candidate_analytics.logical_fingerprint
                ),
                "shard_id": shard_id,
                "universe_id": universe.universe_id,
                "stable_id_prefix": prefix,
                "candidates": tuple(grouped[prefix]),
                "item_count": len(grouped[prefix]),
            }
            if visual_context_batches is not None:
                visual_mapping = visual_by_universe[universe.universe_id]
                visual_contexts = tuple(
                    visual_mapping.get(str(item.instrument_id))
                    for item in grouped[prefix]
                )
                if any(item is None for item in visual_contexts):
                    raise OpportunityCandidateSnapshotSplitError(
                        "Candidate visual context does not cover every published detail"
                    )
                base.update(
                    {
                        "visual_context_contract_version": "candidate-visual-context/1.0",
                        "visual_context_audit_logical_fingerprint": (
                            visual_context_audit_logical_fingerprint
                        ),
                        "visual_contexts": visual_contexts,
                    }
                )
                shard = OpportunityCandidateDetailShardV1_1(
                    **base,
                    logical_fingerprint=logical_fingerprint(_jsonable(base)),
                )
            else:
                shard = OpportunityCandidateDetailShardV1(
                    **base,
                    logical_fingerprint=logical_fingerprint(_jsonable(base)),
                )
            shards.append(shard)
            descriptors.append(
                CandidateDetailShardDescriptorV1(
                    shard_id=shard_id,
                    universe_id=universe.universe_id,
                    stable_id_prefix=prefix,
                    filename=f"opportunity-candidate-details-{shard_id}.json",
                    item_count=shard.item_count,
                    logical_fingerprint=shard.logical_fingerprint,
                )
            )
        summary_universes.append(
            CandidateSummaryUniverseV1(
                universe_id=universe.universe_id,
                universe_member_count=universe.universe_member_count,
                membership_fingerprint=universe.membership_fingerprint,
                bar_covered_member_count=universe.bar_covered_member_count,
                missing_member_count=universe.missing_member_count,
                quality_counts=universe.quality_counts,
                stage_counts=universe.stage_counts,
                risk_modes=universe.risk_modes,
                entry_risk_modes=universe.entry_risk_modes,
                candidates=tuple(
                    _summary_item(item, universe_index=universe_index)
                    for item in universe.candidates
                ),
                candidate_batch_logical_fingerprint=(
                    universe.candidate_batch_logical_fingerprint
                ),
            )
        )

    analytics_base = {
        "schema_version": "1.0",
        "contract_version": "opportunity-candidate-summary/1.0",
        "full_publication_contract_version": candidate_analytics.contract_version,
        "full_candidate_analytics_logical_fingerprint": (
            candidate_analytics.logical_fingerprint
        ),
        "as_of_session": candidate_analytics.as_of_session,
        "default_universe_id": candidate_analytics.default_universe_id,
        "universe_order": candidate_analytics.universe_order,
        "risk_mode_order": candidate_analytics.risk_mode_order,
        "source": candidate_analytics.source,
        "universes": tuple(summary_universes),
        "detail_shards": tuple(descriptors),
        "language_neutral": True,
        "research_priority_only": True,
        "underlying_stock_result_not_option_return": True,
        "price_volume_not_fund_flow": True,
        "leadership_rank_preserved": True,
        "entry_location_separate_from_leadership": True,
        "reference_support_not_stop_price": True,
        "warnings": candidate_analytics.warnings,
    }
    analytics = OpportunityCandidateSummaryAnalyticsV1(
        **analytics_base,
        logical_fingerprint=logical_fingerprint(
            _jsonable(analytics_base)
        ),
    )
    summary = OpportunityCandidateSummarySnapshotV1(
        publication_id=publication_id,
        payload_sha256=payload_sha256,
        payload_logical_fingerprint=payload_logical_fingerprint,
        candidate_analytics_logical_fingerprint=candidate_analytics.logical_fingerprint,
        default_universe_id=candidate_analytics.default_universe_id,
        universe_order=candidate_analytics.universe_order,
        analytics=analytics,
    )
    reconstructed = reconstruct_full_candidate_publication(summary, tuple(shards))
    if reconstructed != candidate_analytics:
        raise OpportunityCandidateSnapshotSplitError(
            "split Candidate projection does not reproduce its full source"
        )
    return summary, tuple(shards)


def reconstruct_full_candidate_publication(
    summary: OpportunityCandidateSummarySnapshotV1,
    shards: Iterable[
        OpportunityCandidateDetailShardV1 | OpportunityCandidateDetailShardV1_1
    ],
) -> OpportunityCandidatePublicationV1_1:
    shard_by_id = {item.shard_id: item for item in shards}
    descriptors = {item.shard_id: item for item in summary.analytics.detail_shards}
    if set(shard_by_id) != set(descriptors):
        raise OpportunityCandidateSnapshotSplitError(
            "Candidate detail shard set differs from summary descriptors"
        )
    for shard_id, shard in shard_by_id.items():
        descriptor = descriptors[shard_id]
        if (
            shard.publication_id != summary.publication_id
            or shard.candidate_analytics_logical_fingerprint
            != summary.candidate_analytics_logical_fingerprint
            or shard.universe_id != descriptor.universe_id
            or shard.stable_id_prefix != descriptor.stable_id_prefix
            or shard.item_count != descriptor.item_count
            or shard.logical_fingerprint != descriptor.logical_fingerprint
        ):
            raise OpportunityCandidateSnapshotSplitError(
                "Candidate detail shard binding differs"
            )

    full_universes: list[dict[str, object]] = []
    for universe in summary.analytics.universes:
        full_items = tuple(
            sorted(
                (
                    item
                    for shard in shard_by_id.values()
                    if shard.universe_id == universe.universe_id
                    for item in shard.candidates
                ),
                key=lambda item: str(item.instrument_id),
            )
        )
        expected_summaries = tuple(
            _summary_item(
                item,
                universe_index=summary.analytics.universe_order.index(
                    universe.universe_id
                ),
            )
            for item in full_items
        )
        if expected_summaries != universe.candidates:
            raise OpportunityCandidateSnapshotSplitError(
                "Candidate summaries differ from detail rows"
            )
        full_universes.append(
            {
                "universe_id": universe.universe_id,
                "universe_member_count": universe.universe_member_count,
                "membership_fingerprint": universe.membership_fingerprint,
                "bar_covered_member_count": universe.bar_covered_member_count,
                "missing_member_count": universe.missing_member_count,
                "quality_counts": universe.quality_counts,
                "stage_counts": universe.stage_counts,
                "risk_modes": universe.risk_modes,
                "entry_risk_modes": universe.entry_risk_modes,
                "candidates": full_items,
                "candidate_batch_logical_fingerprint": (
                    universe.candidate_batch_logical_fingerprint
                ),
            }
        )
    analytics = summary.analytics
    return OpportunityCandidatePublicationV1_1(
        schema_version="1.0",
        contract_version=analytics.full_publication_contract_version,
        as_of_session=analytics.as_of_session,
        default_universe_id=analytics.default_universe_id,
        universe_order=analytics.universe_order,
        risk_mode_order=analytics.risk_mode_order,
        source=analytics.source,
        universes=tuple(full_universes),  # type: ignore[arg-type]
        language_neutral=True,
        research_priority_only=True,
        underlying_stock_result_not_option_return=True,
        price_volume_not_fund_flow=True,
        warnings=analytics.warnings,
        logical_fingerprint=analytics.full_candidate_analytics_logical_fingerprint,
        leadership_rank_preserved=True,
        entry_location_separate_from_leadership=True,
        reference_support_not_stop_price=True,
    )


def _summary_item(
    item: OpportunityCandidatePublicationItemV1_1,
    *,
    universe_index: int,
) -> CandidateSummaryItemV1:
    entry = item.entry_geometry
    return CandidateSummaryItemV1(
        instrument_id=item.instrument_id,
        ticker=item.ticker,
        security_type=item.security_type,
        base_score=item.base_score,
        confidence=item.confidence,
        latest_price=item.latest_price,
        median_dollar_volume_20=item.median_dollar_volume_20,
        data_quality_status=item.data_quality_status,
        final_stage=item.state.final_stage,
        risk_dispositions=item.risk_dispositions,
        entry_summary=CandidateEntrySummaryV1(
            review_posture=entry.review_posture.value,
            technical_setup=entry.technical_setup.value,
            extension_risk=entry.extension_risk.value,
            reference_support_distance_pct=(
                entry.metrics.reference_support_distance_pct
            ),
        ),
        score_logical_fingerprint=item.score_logical_fingerprint,
        entry_geometry_logical_fingerprint=entry.logical_fingerprint,
        detail_shard_id=f"u{universe_index}-{str(item.instrument_id)[0]}",
    )


def _jsonable(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
