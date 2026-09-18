"""Pure construction of the full-market official-evidence priority plan."""

from __future__ import annotations

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
    OFFICIAL_EVIDENCE_PRIORITY,
)
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    EXPECTED_FIELDS_BY_PURPOSE,
    PURPOSE_BY_FAMILY,
    ChinaAshareOfficialEvidenceAuthority,
    ChinaAshareOfficialEvidenceAuthoritySpecV1,
    ChinaAshareOfficialEvidencePriorityRequestV1,
    ChinaAshareOfficialEvidencePriorityTierV1,
    build_official_evidence_priority_plan,
    official_evidence_request_id,
)


class ChinaAshareOfficialEvidencePriorityPlanError(RuntimeError):
    pass


def plan_china_ashare_official_evidence_priority(
    *, reconstruction_package, reverse_candidate_input: bool = False
):
    """Use only one exact-reread conservative package; perform no acquisition."""

    manifest = reconstruction_package.manifest
    source_plan = reconstruction_package.plan
    census = reconstruction_package.census
    if (
        manifest.plan_fingerprint != source_plan.logical_fingerprint
        or manifest.global_census_fingerprint != census.logical_fingerprint
        or manifest.candidate_set_fingerprint != census.candidate_set_fingerprint
    ):
        raise ChinaAshareOfficialEvidencePriorityPlanError(
            "conservative reconstruction input binding differs"
        )
    candidates = [
        candidate
        for partition in reconstruction_package.partition_censuses
        for candidate in partition.candidate_records
    ]
    if reverse_candidate_input:
        candidates.reverse()
    by_source_security_id = {}
    for candidate in candidates:
        existing = by_source_security_id.setdefault(
            candidate.source_security_id, candidate
        )
        if existing != candidate:
            raise ChinaAshareOfficialEvidencePriorityPlanError(
                "candidate stable security IDs differ"
            )
    requests = []
    for family in OFFICIAL_EVIDENCE_PRIORITY:
        family_candidates = sorted(
            (
                item
                for item in by_source_security_id.values()
                if family in item.requested_families
            ),
            key=lambda item: item.source_security_id,
        )
        for candidate in family_candidates:
            authorities = _authorities(candidate.source_security_id)
            stable_subject_id = (
                f"instrument:{candidate.instrument_id}"
                if candidate.instrument_id is not None
                else (
                    "quarantined-source-security:"
                    f"{candidate.source_security_id}"
                )
            )
            for purpose in PURPOSE_BY_FAMILY[family]:
                requests.append(
                    ChinaAshareOfficialEvidencePriorityRequestV1(
                        request_id=official_evidence_request_id(
                            stable_subject_id=stable_subject_id,
                            family=family,
                            purpose=purpose,
                            effective_from=source_plan.interval_start,
                            effective_to=source_plan.interval_end,
                        ),
                        stable_subject_id=stable_subject_id,
                        source_security_id=candidate.source_security_id,
                        instrument_id=candidate.instrument_id,
                        partition_index=candidate.partition_index,
                        family=family,
                        purpose=purpose,
                        effective_from=source_plan.interval_start,
                        effective_to=source_plan.interval_end,
                        candidate_authorities=authorities,
                        expected_fields=EXPECTED_FIELDS_BY_PURPOSE[purpose],
                        maximum_acquisition_attempt_count=1,
                        failure_disposition="quarantine_unchanged",
                        source_available_at_must_be_observed=True,
                        evidence_may_be_reused_by_bound_adjudications=True,
                    )
                )
    expected_security_counts = {
        ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING: (
            census.warning_candidate_security_count
        ),
        ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE: (
            census.lifecycle_candidate_security_count
        ),
        ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE: (
            census.listing_stage_candidate_security_count
        ),
    }
    tier_by_family = {
        item.family: item for item in census.official_request_budget_by_priority
    }
    tiers = tuple(
        ChinaAshareOfficialEvidencePriorityTierV1(
            priority=priority,
            family=family,
            deduplicated_security_count=expected_security_counts[family],
            requests_per_security=tier_by_family[family].maximum_requests_per_security,
            maximum_request_count=tier_by_family[family].maximum_request_count,
        )
        for priority, family in enumerate(OFFICIAL_EVIDENCE_PRIORITY, start=1)
    )
    return build_official_evidence_priority_plan(
        input_package_fingerprint=manifest.logical_fingerprint,
        input_manifest_physical_sha256=(
            reconstruction_package.manifest_physical_sha256
        ),
        input_plan_fingerprint=source_plan.logical_fingerprint,
        input_global_census_fingerprint=census.logical_fingerprint,
        input_candidate_set_fingerprint=census.candidate_set_fingerprint,
        interval_start=source_plan.interval_start,
        interval_end=source_plan.interval_end,
        authority_registry=(
            ChinaAshareOfficialEvidenceAuthoritySpecV1(
                authority=ChinaAshareOfficialEvidenceAuthority.SSE,
                official_base_url="https://www.sse.com.cn/",
                credentials_required=False,
                aggregate_source=False,
            ),
            ChinaAshareOfficialEvidenceAuthoritySpecV1(
                authority=ChinaAshareOfficialEvidenceAuthority.SZSE,
                official_base_url="https://www.szse.cn/",
                credentials_required=False,
                aggregate_source=False,
            ),
            ChinaAshareOfficialEvidenceAuthoritySpecV1(
                authority=ChinaAshareOfficialEvidenceAuthority.CNINFO,
                official_base_url="https://www.cninfo.com.cn/",
                credentials_required=False,
                aggregate_source=False,
            ),
        ),
        tiers=tiers,
        requests=tuple(requests),
        maximum_official_request_count=census.maximum_official_request_count,
        corporate_action_candidate_security_count=census.action_candidate_security_count,
        corporate_action_candidate_window_count=(
            census.factor_change_candidate_window_count
        ),
        corporate_action_request_count=0,
        corporate_action_disposition="quarantine_unchanged",
        network_execution_authorized=False,
        outcome_read_count=0,
        return_construction_authorized=False,
        historical_coverage_authorized=False,
        factor_discovery_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
    )


def _authorities(source_security_id):
    if source_security_id.startswith("sh."):
        return (
            ChinaAshareOfficialEvidenceAuthority.SSE,
            ChinaAshareOfficialEvidenceAuthority.CNINFO,
        )
    if source_security_id.startswith("sz."):
        return (
            ChinaAshareOfficialEvidenceAuthority.SZSE,
            ChinaAshareOfficialEvidenceAuthority.CNINFO,
        )
    raise ChinaAshareOfficialEvidencePriorityPlanError(
        "official evidence route is outside frozen SSE/SZSE scope"
    )
