"""Pure evaluator and registered offline source-gap disposition."""

from __future__ import annotations

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_gap import (
    ConservativeFirstBatchPolicyV1,
    EvidenceLane,
    LocalQualification,
    SecCashQualitySourceGapEvaluationV1,
    SecCashQualitySourceGapPlanV1,
    SourceCapabilityV1,
    SourceClass,
    SourceGapV1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


def registered_source_gap_plan_v1() -> SecCashQualitySourceGapPlanV1:
    """Return the repository-evidenced plan without I/O or external claims."""

    gaps = (
        SourceGapV1(
            lane=EvidenceLane.INSTRUMENT_CIK,
            blocked_observation_count=75_391,
            denominator_name="all_ttm_ready_issuer_observations",
            required_proof=(
                "effective_dated_instrument_to_cik_relation",
                "evidence_known_by_signal_open",
                "stable_instrument_id",
            ),
        ),
        SourceGapV1(
            lane=EvidenceLane.SECURITY_FORM,
            blocked_observation_count=56_542,
            denominator_name="unique_common_same_session_observations",
            required_proof=(
                "effective_dated_security_form",
                "form_evidence_known_by_signal_open",
                "stable_instrument_id",
            ),
        ),
        SourceGapV1(
            lane=EvidenceLane.LISTING_AND_ALIASES,
            blocked_observation_count=56_542,
            denominator_name="unique_common_same_session_observations",
            required_proof=(
                "effective_listing_interval",
                "stable_id_ticker_alias_history",
                "venue_and_source_knowledge_time",
            ),
        ),
        SourceGapV1(
            lane=EvidenceLane.ISSUER_SECURITY_STRUCTURE,
            blocked_observation_count=56_542,
            denominator_name="unique_common_same_session_observations",
            required_proof=(
                "effective_issuer_security_relationship",
                "issuer_structure_positive_evidence",
                "structure_evidence_known_by_signal_open",
            ),
        ),
        SourceGapV1(
            lane=EvidenceLane.MULTI_COMMON,
            blocked_observation_count=577,
            denominator_name="same_session_multiple_common_observations",
            required_proof=(
                "complete_share_class_cardinality",
                "deterministic_quarantine_or_class_policy",
                "effective_issuer_security_relationship",
            ),
        ),
    )
    capabilities = tuple(
        sorted(
            _registered_capabilities(), key=lambda item: (item.lane.value, item.source_id)
        )
    )
    values = {
        "gaps": gaps,
        "capabilities": capabilities,
        "prospective_policy": ConservativeFirstBatchPolicyV1(),
    }
    provisional = SecCashQualitySourceGapPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualitySourceGapPlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def evaluate_source_gap_plan(
    plan: SecCashQualitySourceGapPlanV1,
) -> SecCashQualitySourceGapEvaluationV1:
    qualified = tuple(
        lane
        for lane in EvidenceLane
        if any(
            item.lane is lane and item.positive_admission_supported
            for item in plan.capabilities
        )
    )
    blocked = tuple(lane for lane in EvidenceLane if lane not in qualified)
    prioritized = tuple(
        (gap.lane, gap.blocked_observation_count)
        for gap in sorted(
            plan.gaps,
            key=lambda item: (-item.blocked_observation_count, item.lane.value),
        )
    )
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "qualified_lanes": qualified,
        "blocked_lanes": blocked,
        "prioritized_gaps": prioritized,
    }
    provisional = SecCashQualitySourceGapEvaluationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualitySourceGapEvaluationV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def _registered_capabilities() -> tuple[SourceCapabilityV1, ...]:
    common_refs = (
        "docs/decisions/0308-census-listed-security-applicability-before-cash-quality-projection.md",
    )
    massive_refs = tuple(
        sorted(
            (
                *common_refs,
                "docs/audits/massive-starter-five-year-depth-probe-2026-09-10.md",
                "docs/audits/massive-starter-lifecycle-capability-2026-09-10.md",
            )
        )
    )
    free_refs = (
        "docs/audits/free-performance-evidence-source-review-2026-09-15.md",
        "docs/decisions/0196-build-a-five-year-point-in-time-research-foundation-on-dell.md",
    )
    commercial_refs = (
        "docs/providers/lifecycle-corroboration-source-review-2026-09-08.md",
    )
    rows: list[SourceCapabilityV1] = []

    def add(
        source_id: str,
        source_class: SourceClass,
        lane: EvidenceLane,
        qualification: LocalQualification,
        *,
        stable: bool,
        effective: bool,
        clock: bool,
        network: bool,
        credentials: bool,
        refs: tuple[str, ...],
        limitations: tuple[str, ...],
    ) -> None:
        rows.append(
            SourceCapabilityV1(
                source_id=source_id,
                source_class=source_class,
                lane=lane,
                local_qualification=qualification,
                stable_key_supported=stable,
                effective_interval_supported=effective,
                source_knowledge_time_supported=clock,
                positive_admission_supported=(
                    qualification is LocalQualification.QUALIFIED
                    and stable
                    and effective
                    and clock
                ),
                additional_acquisition_requires_network=network,
                additional_acquisition_requires_credentials_or_agreement=credentials,
                evidence_references=tuple(sorted(refs)),
                limitations=tuple(sorted(limitations)),
            )
        )

    for lane in (
        EvidenceLane.INSTRUMENT_CIK,
        EvidenceLane.SECURITY_FORM,
        EvidenceLane.LISTING_AND_ALIASES,
        EvidenceLane.MULTI_COMMON,
    ):
        add(
            "massive_starter_dated_reference",
            SourceClass.MASSIVE_STARTER,
            lane,
            LocalQualification.VERIFIED_INSUFFICIENT,
            stable=True,
            effective=False,
            clock=False,
            network=True,
            credentials=True,
            refs=massive_refs,
            limitations=(
                "existing_history_was_observed_after_historical_signal_cutoffs",
                "no_complete_effective_dated_security_master_is_retained",
                "provider_form_does_not_prove_issuer_structure",
            ),
        )
    add(
        "massive_starter_dated_reference",
        SourceClass.MASSIVE_STARTER,
        EvidenceLane.ISSUER_SECURITY_STRUCTURE,
        LocalQualification.VERIFIED_INSUFFICIENT,
        stable=True,
        effective=False,
        clock=False,
        network=True,
        credentials=True,
        refs=massive_refs,
        limitations=(
            "cik_and_figi_connect_identity_but_do_not_classify_issuer_structure",
            "provider_common_stock_type_is_not_operating_structure_or_domicile",
        ),
    )
    add(
        "sec_edgar_filings_and_form25",
        SourceClass.FREE_OFFICIAL,
        EvidenceLane.INSTRUMENT_CIK,
        LocalQualification.CORROBORATOR_ONLY,
        stable=False,
        effective=False,
        clock=True,
        network=True,
        credentials=False,
        refs=free_refs,
        limitations=(
            "cik_is_a_filer_not_a_listed_security_key",
            "cover_page_ticker_exchange_and_title_are_filing_context_only",
        ),
    )
    add(
        "sec_edgar_filings_and_form25",
        SourceClass.FREE_OFFICIAL,
        EvidenceLane.ISSUER_SECURITY_STRUCTURE,
        LocalQualification.CORROBORATOR_ONLY,
        stable=False,
        effective=False,
        clock=True,
        network=True,
        credentials=False,
        refs=free_refs,
        limitations=(
            "filings_can_support_named_structure_facts_but_not_complete_population_positives",
            "filing_acceptance_does_not_prove_exchange_listing_interval",
        ),
    )
    add(
        "gleif_legal_entity_data",
        SourceClass.OPEN_IDENTIFIER,
        EvidenceLane.ISSUER_SECURITY_STRUCTURE,
        LocalQualification.CORROBORATOR_ONLY,
        stable=False,
        effective=True,
        clock=False,
        network=True,
        credentials=False,
        refs=free_refs,
        limitations=(
            "lei_identifies_a_legal_entity_not_an_exchange_listed_security",
            "legal_entity_relationships_do_not_prove_security_form_or_listing",
        ),
    )
    add(
        "official_venue_directories_and_notices",
        SourceClass.FREE_OFFICIAL,
        EvidenceLane.LISTING_AND_ALIASES,
        LocalQualification.REQUIRES_BOUNDED_SAMPLE,
        stable=False,
        effective=False,
        clock=False,
        network=True,
        credentials=False,
        refs=free_refs,
        limitations=(
            "current_directories_are_not_complete_historical_ledgers",
            "venue_fragments_need_stable_id_resolution_and_retained_observation_clocks",
        ),
    )
    add(
        "openfigi_mapping",
        SourceClass.OPEN_IDENTIFIER,
        EvidenceLane.INSTRUMENT_CIK,
        LocalQualification.CORROBORATOR_ONLY,
        stable=True,
        effective=False,
        clock=False,
        network=True,
        credentials=False,
        refs=free_refs,
        limitations=(
            "identifier_mapping_is_not_a_cik_relationship_ledger",
            "mapping_is_not_listing_or_knowledge_time_evidence",
        ),
    )
    add(
        "finra_otc_daily_list",
        SourceClass.LOCAL_RETAINED,
        EvidenceLane.LISTING_AND_ALIASES,
        LocalQualification.CORROBORATOR_ONLY,
        stable=False,
        effective=True,
        clock=False,
        network=False,
        credentials=False,
        refs=free_refs,
        limitations=(
            "otc_scope_does_not_cover_major_exchange_history",
            "ticker_never_creates_stable_identity",
        ),
    )
    add(
        "paid_official_venue_listing_feeds",
        SourceClass.OPTIONAL_COMMERCIAL,
        EvidenceLane.LISTING_AND_ALIASES,
        LocalQualification.REQUIRES_BOUNDED_SAMPLE,
        stable=False,
        effective=False,
        clock=False,
        network=True,
        credentials=True,
        refs=commercial_refs,
        limitations=(
            "each_feed_is_venue_specific_and_not_cross_venue_identity_truth",
            "schema_identifiers_revision_clocks_and_permissions_require_a_sample",
        ),
    )
    for lane in EvidenceLane:
        add(
            "commercial_point_in_time_security_master_sample",
            SourceClass.OPTIONAL_COMMERCIAL,
            lane,
            LocalQualification.REQUIRES_BOUNDED_SAMPLE,
            stable=False,
            effective=False,
            clock=False,
            network=True,
            credentials=True,
            refs=commercial_refs,
            limitations=(
                "marketing_material_does_not_prove_required_fields_or_history",
                "sample_schema_revision_clocks_permissions_and_coverage_are_unverified",
            ),
        )
    return tuple(rows)
