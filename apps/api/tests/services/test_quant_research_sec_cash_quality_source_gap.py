import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_gap import (
    EvidenceLane,
    LocalQualification,
    SourceCapabilityV1,
    SourceClass,
)
from tip_api.services.quant_research_sec_cash_quality_source_gap import (
    evaluate_source_gap_plan,
    registered_source_gap_plan_v1,
)


def test_registered_source_gap_stays_zero_and_prioritizes_positive_denominator() -> None:
    plan = registered_source_gap_plan_v1()
    result = evaluate_source_gap_plan(plan)

    assert result.historical_admitted_count == 0
    assert plan.logical_fingerprint == (
        "0958b66c9b69dc031e6e71a64e9ab394559779fe52655ed9210a77aa388bb32e"
    )
    assert result.logical_fingerprint == (
        "3b35e9a0e46756e94f03cb23ee1fddc212015a64c2baf36711422d4065791858"
    )
    assert result.qualified_lanes == ()
    assert set(result.blocked_lanes) == set(EvidenceLane)
    assert result.prioritized_gaps[0] == (
        EvidenceLane.INSTRUMENT_CIK,
        75_391,
    )
    assert plan.prospective_policy.selection_may_use_outcomes is False
    assert plan.prospective_policy.multi_common_disposition == "quarantine"
    assert plan.forbidden_positive_proxies == (
        "current_provider_snapshot_backcast",
        "sec_filer_identity_only",
        "ticker_or_name",
    )


def test_registered_plan_is_deterministic() -> None:
    first = registered_source_gap_plan_v1()
    second = registered_source_gap_plan_v1()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.logical_fingerprint == second.logical_fingerprint


def test_ticker_or_partial_source_cannot_claim_positive_admission() -> None:
    with pytest.raises(ValidationError, match="positive admission requires"):
        SourceCapabilityV1(
            source_id="ticker_only",
            source_class=SourceClass.FREE_OFFICIAL,
            lane=EvidenceLane.INSTRUMENT_CIK,
            local_qualification=LocalQualification.QUALIFIED,
            stable_key_supported=False,
            effective_interval_supported=True,
            source_knowledge_time_supported=True,
            positive_admission_supported=True,
            additional_acquisition_requires_network=False,
            additional_acquisition_requires_credentials_or_agreement=False,
            evidence_references=("evidence",),
            limitations=("ticker_is_not_stable",),
        )


def test_current_snapshot_cannot_claim_historical_admission() -> None:
    with pytest.raises(ValidationError, match="positive admission requires"):
        SourceCapabilityV1(
            source_id="current_snapshot",
            source_class=SourceClass.MASSIVE_STARTER,
            lane=EvidenceLane.SECURITY_FORM,
            local_qualification=LocalQualification.QUALIFIED,
            stable_key_supported=True,
            effective_interval_supported=False,
            source_knowledge_time_supported=True,
            positive_admission_supported=True,
            additional_acquisition_requires_network=False,
            additional_acquisition_requires_credentials_or_agreement=False,
            evidence_references=("evidence",),
            limitations=("not_effective_dated",),
        )
