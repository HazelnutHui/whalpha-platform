"""Pure, offline Candidate strategy-channel preview calculation."""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_EVEN, Decimal

from tip_api.contracts.analytics.v1 import (
    CandidateDataQualityStatus,
    CandidateEntryGeometryBatchV1,
    CandidateExtensionRisk,
    CandidateMetricAvailability,
    CandidateOpportunityStage,
    CandidateStrategyChannelAssessmentV1,
    CandidateStrategyChannelBatchV1,
    CandidateStrategyChannelConsumerV1,
    CandidateStrategyChannelViewV1,
    CandidateTechnicalSetup,
    EntryGeometryAvailability,
    OpportunityCandidateBatchV1,
    STRATEGY_CHANNEL_CALCULATION_VERSION,
    STRATEGY_CHANNEL_CONTRACT_VERSION,
    STRATEGY_CHANNEL_ORDER,
    STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
    STRATEGY_CHANNEL_PARAMETER_SET_ID,
    StrategyChannel,
    StrategyChannelStatus,
    StrategyEvidenceAvailability,
    StrategyEvidenceKind,
    StrategyEvidenceRole,
    StrategyEvidenceSource,
    StrategyMarketFit,
    strategy_channel_logical_fingerprint,
)
from tip_api.parameters.market_regime.candidate_strategy_preview_v1_0_0 import (
    CHANNEL_GEOMETRY_SCORES,
    CHANNEL_SCORE_WEIGHTS,
    STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
    STRATEGY_CHANNEL_DISPLAY_CAP,
    TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR,
    TREND_CONTINUATION_WATCH_BASE_FLOOR,
    TREND_CONTINUATION_WATCH_COMPONENT_FLOOR,
)


TECHNICAL_CHANNELS = (
    StrategyChannel.MOMENTUM_BREAKOUT,
    StrategyChannel.STRONG_STOCK_PULLBACK,
    StrategyChannel.TREND_CONTINUATION,
)
UNAVAILABLE_CHANNEL_GAPS = {
    StrategyChannel.TECHNICAL_REVERSAL: (
        ("stabilization_reclaim_facts", StrategyEvidenceSource.PRICE_VOLUME),
    ),
    StrategyChannel.FUNDAMENTAL_VALUE_REVERSAL: (
        ("governed_fundamental_facts", StrategyEvidenceSource.FUNDAMENTALS),
        ("governed_valuation_facts", StrategyEvidenceSource.VALUATION),
        ("value_reversal_price_stabilization", StrategyEvidenceSource.PRICE_VOLUME),
    ),
    StrategyChannel.DEFENSIVE_ROTATION: (
        ("point_in_time_defensive_taxonomy", StrategyEvidenceSource.DATA_QUALITY),
        ("bound_market_regime_state", StrategyEvidenceSource.MARKET_REGIME),
        (
            "labelled_defensive_relationship_proxy",
            StrategyEvidenceSource.PRICE_DERIVED_RELATIONSHIP_PROXY,
        ),
    ),
}
SCORE_QUANTUM = Decimal("0.0001")


class CandidateStrategyChannelCalculationError(RuntimeError):
    """Raised when source custody cannot support a deterministic preview."""


def calculate_candidate_strategy_channels(
    *,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
) -> CandidateStrategyChannelBatchV1:
    """Build one explicit shadow result per security/channel without outcomes."""

    if (
        candidate_batch.as_of_session != entry_geometry_batch.as_of_session
        or candidate_batch.universe_id != entry_geometry_batch.universe_id
    ):
        raise CandidateStrategyChannelCalculationError(
            "strategy Candidate and entry-geometry batch identity differs"
        )
    if (
        entry_geometry_batch.source_candidate_batch_fingerprint
        != candidate_batch.logical_fingerprint
    ):
        raise CandidateStrategyChannelCalculationError(
            "strategy entry geometry is not bound to the Candidate batch"
        )
    candidate_by_id = {item.instrument_id: item for item in candidate_batch.candidates}
    entry_by_id = {item.instrument_id: item for item in entry_geometry_batch.records}
    if len(candidate_by_id) != len(candidate_batch.candidates):
        raise CandidateStrategyChannelCalculationError("duplicate strategy Candidate")
    if len(entry_by_id) != len(entry_geometry_batch.records):
        raise CandidateStrategyChannelCalculationError("duplicate strategy entry geometry")
    if set(candidate_by_id) != set(entry_by_id):
        raise CandidateStrategyChannelCalculationError(
            "strategy calculation requires exact Candidate/entry coverage"
        )

    drafts: list[dict[str, object]] = []
    for instrument_id in sorted(candidate_by_id, key=str):
        candidate = candidate_by_id[instrument_id]
        entry = entry_by_id[instrument_id]
        if (
            entry.source_candidate_fingerprint != candidate.logical_fingerprint
            or entry.ticker != candidate.ticker
            or entry.security_type != candidate.security_type
            or entry.candidate_base_score != candidate.base_score
        ):
            raise CandidateStrategyChannelCalculationError(
                "strategy Candidate and entry-geometry record differs"
            )
        for channel in StrategyChannel:
            if channel in TECHNICAL_CHANNELS:
                draft = _technical_draft(candidate=candidate, entry=entry, channel=channel)
            else:
                draft = _unavailable_draft(
                    candidate=candidate,
                    entry=entry,
                    channel=channel,
                )
            drafts.append(draft)

    _assign_within_channel_ranks(drafts)
    records = tuple(
        CandidateStrategyChannelAssessmentV1.model_validate(
            {
                **draft,
                "logical_fingerprint": strategy_channel_logical_fingerprint(draft),
            }
        )
        for draft in sorted(
            drafts,
            key=lambda item: (
                str(item["instrument_id"]),
                STRATEGY_CHANNEL_ORDER.index(str(item["channel"])),
            ),
        )
    )
    counts = {
        channel.value: {
            status.value: count
            for status, count in Counter(
                row.status for row in records if row.channel is channel
            ).items()
        }
        for channel in StrategyChannel
    }
    provisional = {
        "schema_version": "1.0",
        "contract_version": STRATEGY_CHANNEL_CONTRACT_VERSION,
        "calculation_version": STRATEGY_CHANNEL_CALCULATION_VERSION,
        "parameter_set_id": STRATEGY_CHANNEL_PARAMETER_SET_ID,
        "parameter_fingerprint": STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
        "as_of_session": candidate_batch.as_of_session.isoformat(),
        "universe_id": candidate_batch.universe_id,
        "source_candidate_batch_fingerprint": candidate_batch.logical_fingerprint,
        "source_entry_geometry_batch_fingerprint": entry_geometry_batch.logical_fingerprint,
        "channel_order": list(STRATEGY_CHANNEL_ORDER),
        "records": [row.model_dump(mode="json") for row in records],
        "status_counts": counts,
        "cross_channel_score_prohibited": True,
        "research_priority_only": True,
        "event_context_is_auxiliary": True,
        "underlying_stock_result_not_option_return": True,
        "price_volume_not_fund_flow": True,
        "warnings": (
            "shadow_only_not_publication_input",
            "fixed_baseline_not_chronologically_validated",
            "channel_score_not_success_probability_or_expected_return",
            "cross_channel_score_comparison_prohibited",
            "market_fit_not_yet_calibrated",
            "underlying_stock_result_not_option_return",
            "price_volume_not_fund_flow",
        )
    }
    provisional["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        provisional
    )
    return CandidateStrategyChannelBatchV1.model_validate(provisional)


def build_candidate_strategy_channel_consumer(
    batch: CandidateStrategyChannelBatchV1,
) -> CandidateStrategyChannelConsumerV1:
    """Bound the full shadow population to at most eight explanations per channel."""

    views = []
    for channel in StrategyChannel:
        ranked = tuple(
            sorted(
                (
                    row
                    for row in batch.records
                    if row.channel is channel and row.within_channel_rank is not None
                ),
                key=lambda row: row.within_channel_rank or 0,
            )
        )
        view_body = {
            "schema_version": "1.0",
            "channel": channel.value,
            "status_counts": {
                status.value: count
                for status, count in batch.status_counts[channel].items()
            },
            "qualifying_count": len(ranked),
            "display_cap": STRATEGY_CHANNEL_DISPLAY_CAP,
            "displayed_records": [
                row.model_dump(mode="json")
                for row in ranked[:STRATEGY_CHANNEL_DISPLAY_CAP]
            ],
        }
        view_body["logical_fingerprint"] = strategy_channel_logical_fingerprint(
            view_body
        )
        views.append(CandidateStrategyChannelViewV1.model_validate(view_body))

    body = {
        "schema_version": "1.0",
        "contract_version": STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
        "as_of_session": batch.as_of_session.isoformat(),
        "universe_id": batch.universe_id,
        "source_batch_logical_fingerprint": batch.logical_fingerprint,
        "channel_order": list(STRATEGY_CHANNEL_ORDER),
        "channels": [item.model_dump(mode="json") for item in views],
        "cross_channel_score_prohibited": True,
        "shadow_only": True,
        "warnings": (
            "shadow_only_not_publication_input",
            "display_cap_does_not_change_full_population_counts",
            "channel_score_not_success_probability_or_expected_return",
            "cross_channel_score_comparison_prohibited",
        ),
    }
    body["logical_fingerprint"] = strategy_channel_logical_fingerprint(body)
    return CandidateStrategyChannelConsumerV1.model_validate(body)


def _technical_draft(*, candidate, entry, channel: StrategyChannel) -> dict[str, object]:
    components = {item.component_id: item for item in candidate.components}
    weights = CHANNEL_SCORE_WEIGHTS[channel.value]
    missing = tuple(
        sorted(
            component_id
            for component_id in weights
            if component_id != "entry_geometry"
            and (
                component_id not in components
                or components[component_id].availability
                is not CandidateMetricAvailability.AVAILABLE
                or components[component_id].score is None
            )
        )
    )
    blocked_quality = candidate.data_quality_status in {
        CandidateDataQualityStatus.QUARANTINED,
        CandidateDataQualityStatus.FAILED,
    }
    if (
        missing
        or blocked_quality
        or entry.metrics.availability is EntryGeometryAvailability.UNAVAILABLE
        or entry.technical_setup is CandidateTechnicalSetup.UNAVAILABLE
    ):
        missing_codes = tuple(
            sorted(
                {
                    *(f"component_{item}_unavailable" for item in missing),
                    *(
                        ("candidate_source_quality_not_governed",)
                        if blocked_quality
                        else ()
                    ),
                    *(
                        ("entry_geometry_required_facts_unavailable",)
                        if entry.metrics.availability
                        is EntryGeometryAvailability.UNAVAILABLE
                        else ()
                    ),
                }
            )
        )
        return _base_draft(
            candidate=candidate,
            entry=entry,
            channel=channel,
            status=StrategyChannelStatus.UNAVAILABLE,
            score=None,
            evidence=tuple(
                _missing_evidence(
                    evidence_id=code,
                    source_kind=StrategyEvidenceSource.PRICE_VOLUME,
                    missing_reason_code=code,
                )
                for code in missing_codes
            ),
            missing_codes=missing_codes,
            why=(),
            rejection="required_technical_channel_evidence_unavailable",
            reviewable=("restore_complete_governed_technical_channel_evidence",),
        )

    score = _technical_score(
        channel=channel,
        components=components,
        setup=entry.technical_setup,
    )
    status, why, rejection, reviewable = _technical_status(
        candidate=candidate,
        entry=entry,
        components=components,
        channel=channel,
    )
    evidence = _technical_evidence(
        candidate=candidate,
        entry=entry,
        channel=channel,
        components=components,
    )
    return _base_draft(
        candidate=candidate,
        entry=entry,
        channel=channel,
        status=status,
        score=score,
        evidence=evidence,
        missing_codes=(),
        why=why,
        rejection=rejection,
        reviewable=reviewable,
    )


def _technical_score(*, channel, components, setup) -> str:
    total = Decimal("0")
    for component_id, weight in CHANNEL_SCORE_WEIGHTS[channel.value].items():
        value = (
            Decimal(CHANNEL_GEOMETRY_SCORES[channel.value][setup.value])
            if component_id == "entry_geometry"
            else Decimal(components[component_id].score)
        )
        total += Decimal(weight) * value
    return format(total.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_EVEN), "f")


def _technical_status(*, candidate, entry, components, channel):
    if entry.candidate_stage is CandidateOpportunityStage.INVALIDATED:
        return (
            StrategyChannelStatus.DEPRIORITIZED,
            (),
            "candidate_state_invalidated",
            ("candidate_state_must_requalify",),
        )
    setup = entry.technical_setup
    if channel is StrategyChannel.MOMENTUM_BREAKOUT:
        if setup is CandidateTechnicalSetup.BREAKOUT_CONFIRMED:
            return (
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                ("bounded_breakout_confirmed",),
                "breakout_may_fail_or_reverse",
                (),
            )
        if setup in {
            CandidateTechnicalSetup.BREAKOUT_WATCH,
            CandidateTechnicalSetup.STRONG_BUT_EXTENDED,
        }:
            review_condition = (
                "extension_must_reset_before_breakout_review"
                if setup is CandidateTechnicalSetup.STRONG_BUT_EXTENDED
                else "close_above_prior_high_with_volume_confirmation"
            )
            return (
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
                ("leadership_near_breakout_or_reset_trigger",),
                (
                    "chase_risk_high"
                    if setup is CandidateTechnicalSetup.STRONG_BUT_EXTENDED
                    else "breakout_not_confirmed"
                ),
                (review_condition,),
            )
        return (
            StrategyChannelStatus.DEPRIORITIZED,
            (),
            "bounded_breakout_structure_absent",
            ("bounded_breakout_or_near_trigger_structure_required",),
        )
    if channel is StrategyChannel.STRONG_STOCK_PULLBACK:
        if setup is CandidateTechnicalSetup.PULLBACK:
            return (
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                ("orderly_pullback_structure_present",),
                "pullback_may_break_support",
                (),
            )
        if setup is CandidateTechnicalSetup.STRONG_BUT_EXTENDED:
            return (
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
                ("leader_extended_before_possible_pullback",),
                "orderly_pullback_not_yet_formed",
                ("extension_reset_into_labelled_support_zone",),
            )
        return (
            StrategyChannelStatus.DEPRIORITIZED,
            (),
            "orderly_pullback_structure_absent",
            ("orderly_pullback_toward_support_required",),
        )

    relative = Decimal(components["stock_relative_strength"].score)
    trend = Decimal(components["trend_quality"].score)
    base = Decimal(candidate.base_score) if candidate.base_score is not None else Decimal("0")
    non_high_extension = entry.extension_risk in {
        CandidateExtensionRisk.LOW,
        CandidateExtensionRisk.MODERATE,
    }
    advanced_stage = entry.candidate_stage in {
        CandidateOpportunityStage.PREPARE,
        CandidateOpportunityStage.ENTER,
    }
    if (
        advanced_stage
        and non_high_extension
        and relative >= Decimal(TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR)
        and trend >= Decimal(TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR)
    ):
        return (
            StrategyChannelStatus.ADVANCE_TO_RESEARCH,
            ("candidate_state_and_trend_components_aligned",),
            "trend_may_be_late_cycle_or_crowded",
            (),
        )
    if (
        base >= Decimal(TREND_CONTINUATION_WATCH_BASE_FLOOR)
        and relative >= Decimal(TREND_CONTINUATION_WATCH_COMPONENT_FLOOR)
        and trend >= Decimal(TREND_CONTINUATION_WATCH_COMPONENT_FLOOR)
    ):
        review_condition = (
            "extension_must_reset_below_high_threshold"
            if not non_high_extension
            else "candidate_state_or_continuation_evidence_must_advance"
        )
        return (
            StrategyChannelStatus.WATCH_FOR_TRIGGER,
            ("leadership_and_trend_quality_remain_researchable",),
            (
                "extension_reset_required"
                if not non_high_extension
                else "continuation_state_not_fully_confirmed"
            ),
            (review_condition,),
        )
    return (
        StrategyChannelStatus.DEPRIORITIZED,
        (),
        "trend_continuation_gates_not_met",
        ("relative_strength_trend_and_state_must_align",),
    )


def _technical_evidence(*, candidate, entry, channel, components):
    rows = []
    for component_id in CHANNEL_SCORE_WEIGHTS[channel.value]:
        if component_id == "entry_geometry":
            continue
        component = components[component_id]
        source_kind = StrategyEvidenceSource.PRICE_VOLUME
        score = Decimal(component.score)
        rows.append(
            {
                "evidence_id": f"component_{component_id}",
                "evidence_kind": (
                    StrategyEvidenceKind.SUPPORTING
                    if score >= Decimal("50")
                    else StrategyEvidenceKind.COUNTEREVIDENCE
                ),
                "role": StrategyEvidenceRole.PRIMARY,
                "source_kind": source_kind,
                "evidence_type": (
                    "proxy"
                    if source_kind
                    is StrategyEvidenceSource.PRICE_DERIVED_RELATIONSHIP_PROXY
                    else "statistical_inference"
                ),
                "availability": StrategyEvidenceAvailability.AVAILABLE,
                "observed_value": component.score,
                "raw_unit": "component_score_0_100",
                "source_session": candidate.as_of_session.isoformat(),
                "missing_reason_code": None,
                "reason_codes": ("existing_candidate_component_reused",),
            }
        )
    rows.extend(
        (
            {
                "evidence_id": "entry_technical_setup",
                "evidence_kind": (
                    StrategyEvidenceKind.SUPPORTING
                    if entry.technical_setup
                    in {
                        CandidateTechnicalSetup.BREAKOUT_CONFIRMED,
                        CandidateTechnicalSetup.BREAKOUT_WATCH,
                        CandidateTechnicalSetup.PULLBACK,
                    }
                    else StrategyEvidenceKind.COUNTEREVIDENCE
                ),
                "role": StrategyEvidenceRole.PRIMARY,
                "source_kind": StrategyEvidenceSource.PRICE_VOLUME,
                "evidence_type": "statistical_inference",
                "availability": StrategyEvidenceAvailability.AVAILABLE,
                "observed_value": entry.technical_setup.value,
                "raw_unit": "technical_setup",
                "source_session": candidate.as_of_session.isoformat(),
                "missing_reason_code": None,
                "reason_codes": ("entry_geometry_reused_without_browser_reclassification",),
            },
            {
                "evidence_id": "entry_extension_risk",
                "evidence_kind": StrategyEvidenceKind.COUNTEREVIDENCE,
                "role": StrategyEvidenceRole.PRIMARY,
                "source_kind": StrategyEvidenceSource.PRICE_VOLUME,
                "evidence_type": "statistical_inference",
                "availability": StrategyEvidenceAvailability.AVAILABLE,
                "observed_value": entry.extension_risk.value,
                "raw_unit": "extension_risk",
                "source_session": candidate.as_of_session.isoformat(),
                "missing_reason_code": None,
                "reason_codes": ("chase_risk_review_dimension",),
            },
        )
    )
    return tuple(rows)


def _unavailable_draft(*, candidate, entry, channel):
    gaps = UNAVAILABLE_CHANNEL_GAPS[channel]
    missing_codes = tuple(sorted(item[0] for item in gaps))
    return _base_draft(
        candidate=candidate,
        entry=entry,
        channel=channel,
        status=StrategyChannelStatus.UNAVAILABLE,
        score=None,
        evidence=tuple(
            _missing_evidence(
                evidence_id=evidence_id,
                source_kind=source_kind,
                missing_reason_code=evidence_id,
            )
            for evidence_id, source_kind in gaps
        ),
        missing_codes=missing_codes,
        why=(),
        rejection=f"{channel.value}_required_evidence_unavailable",
        reviewable=(f"governed_{channel.value}_evidence_must_be_added",),
    )


def _missing_evidence(*, evidence_id, source_kind, missing_reason_code):
    return {
        "evidence_id": evidence_id,
        "evidence_kind": StrategyEvidenceKind.COUNTEREVIDENCE,
        "role": StrategyEvidenceRole.PRIMARY,
        "source_kind": source_kind,
        "evidence_type": (
            "proxy"
            if source_kind is StrategyEvidenceSource.PRICE_DERIVED_RELATIONSHIP_PROXY
            else "data_quality"
        ),
        "availability": StrategyEvidenceAvailability.UNAVAILABLE,
        "observed_value": None,
        "raw_unit": "unavailable",
        "source_session": None,
        "missing_reason_code": missing_reason_code,
        "reason_codes": ("required_channel_evidence_not_governed",),
    }


def _base_draft(
    *,
    candidate,
    entry,
    channel,
    status,
    score,
    evidence,
    missing_codes,
    why,
    rejection,
    reviewable,
):
    return {
        "schema_version": "1.0",
        "contract_version": STRATEGY_CHANNEL_CONTRACT_VERSION,
        "calculation_version": STRATEGY_CHANNEL_CALCULATION_VERSION,
        "parameter_set_id": STRATEGY_CHANNEL_PARAMETER_SET_ID,
        "parameter_fingerprint": STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
        "as_of_session": candidate.as_of_session.isoformat(),
        "universe_id": candidate.universe_id,
        "instrument_id": str(candidate.instrument_id),
        "ticker": candidate.ticker,
        "security_type": candidate.security_type,
        "channel": channel.value,
        "status": status.value,
        "channel_score": score,
        "within_channel_rank": None,
        "score_meaning": "within_channel_research_priority_not_return_probability",
        "market_fit": StrategyMarketFit.UNAVAILABLE.value,
        "market_fit_reason_codes": ("channel_specific_market_fit_not_validated",),
        "market_fit_separate_from_channel_score": True,
        "first_rejection_is_risk_not_status_reason": True,
        "source_candidate_fingerprint": candidate.logical_fingerprint,
        "source_entry_geometry_fingerprint": entry.logical_fingerprint,
        "evidence": evidence,
        "missing_required_evidence_codes": missing_codes,
        "why_surfaced_codes": why,
        "first_rejection_code": rejection,
        "what_would_make_researchable_codes": reviewable,
        "invalidation_codes": (
            "candidate_state_invalidated",
            "source_or_corporate_action_quarantine",
            "channel_primary_evidence_breaks",
        ),
        "required_manual_check_codes": (
            "company_event_and_earnings_timing",
            "news_and_thesis_evidence",
            "option_liquidity_iv_greeks_and_spread",
            "position_risk_and_execution_quality",
        ),
        "warning_codes": (
            "fixed_baseline_not_chronologically_validated",
            "research_priority_not_recommendation",
            "underlying_stock_result_not_option_return",
            "price_volume_not_fund_flow",
        ),
    }


def _assign_within_channel_ranks(drafts):
    priority = {
        StrategyChannelStatus.ADVANCE_TO_RESEARCH.value: 0,
        StrategyChannelStatus.WATCH_FOR_TRIGGER.value: 1,
    }
    for channel in StrategyChannel:
        rankable = [
            row
            for row in drafts
            if row["channel"] == channel.value and row["status"] in priority
        ]
        rankable.sort(
            key=lambda row: (
                priority[row["status"]],
                -Decimal(str(row["channel_score"])),
                str(row["ticker"]),
                str(row["instrument_id"]),
            )
        )
        for rank, row in enumerate(rankable, start=1):
            row["within_channel_rank"] = rank
