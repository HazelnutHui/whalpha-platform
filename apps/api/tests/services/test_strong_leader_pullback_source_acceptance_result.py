from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_source_acceptance_result as module
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    ACTION_REQUIRED_FIELDS,
    LIFECYCLE_REQUIRED_FIELDS,
    REQUIRED_PROVIDER_RESULT_STATES,
    ActionSourceAcceptanceCaseV1,
    LifecycleSourceAcceptanceCaseV1,
    SourceBindingV1,
    StrongLeaderPullbackSourceAcceptanceSampleV1,
)


NOW = datetime(2026, 9, 15, 12, tzinfo=UTC)
REVISION = "a" * 40
SAMPLE_SHA = "b" * 64


def _instrument(number: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{number:012d}")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _sample() -> StrongLeaderPullbackSourceAcceptanceSampleV1:
    action_instruments = tuple(_instrument(index + 1) for index in range(4))
    action_cases = tuple(
        ActionSourceAcceptanceCaseV1(
            source_action_id=f"action-{index:02d}",
            source_revision=1,
            provider_ticker_locator=f"A{index:02d}",
            effective_date=date(2026, 7, 1),
            action_type="reverse_split" if index == 19 else "cash_dividend",
            candidate_instrument_id=action_instruments[index % 4],
            candidate_classification="one_historical_candidate",
            exact_date_failure_reason="unresolved_ticker",
            feature_path_count=1,
            horizon_1_path_count=1,
            horizon_3_path_count=1,
            horizon_5_path_count=1,
            inactive_source_state="candidate_only",
            inactive_source_type_codes=("CS",),
            finra_exact_date_symbol_occurrence_count=1,
            finra_exact_numeric_occurrence_count=0,
            finra_flag_codes=("A",),
        )
        for index in range(20)
    )
    lifecycle_cases = tuple(
        LifecycleSourceAcceptanceCaseV1(
            instrument_id=_instrument(index + 100),
            source_anchor_dates=(date(2026, 7, 16), date(2026, 9, 3)),
            source_observation_fingerprints=(
                (f"{index + 1:064x}", f"{index + 1001:064x}")
                if index < 58
                else (f"{index + 1:064x}",)
            ),
            source_occurrence_count=2 if index < 58 else 1,
            selected_identity_types=("composite_figi",),
            selected_identity_values=(f"BBG{index:09d}",),
            provider_ticker_locators=(f"L{index:02d}",),
            provider_name_locators=(f"Lifecycle {index:02d}",),
            cik_locators=(f"{index + 1:010d}",),
            primary_exchange_locators=("XNYS",),
            source_type_codes=("CS",),
            canonical_first_observed_date=date(2025, 6, 23),
            canonical_last_observed_date=date(2026, 8, 12),
            provider_delist_date_candidate=date(2026, 8, 13),
            included_path_count=2,
            horizon_1_crossing_path_count=0,
            horizon_3_crossing_path_count=1,
            horizon_5_crossing_path_count=2,
        )
        for index in range(64)
    )
    values = {
        "implementation_revision": REVISION,
        "evaluated_at": NOW,
        "source_bindings": tuple(
            SourceBindingV1(
                name=name,
                manifest_sha256=str(index) * 64,
                logical_fingerprint=str(index + 3) * 64,
                record_count=1,
            )
            for index, name in enumerate(("action", "blocker", "lifecycle"), start=1)
        ),
        "action_required_fields": ACTION_REQUIRED_FIELDS,
        "lifecycle_required_fields": LIFECYCLE_REQUIRED_FIELDS,
        "required_provider_result_states": REQUIRED_PROVIDER_RESULT_STATES,
        "action_cases": action_cases,
        "lifecycle_cases": lifecycle_cases,
    }
    provisional = StrongLeaderPullbackSourceAcceptanceSampleV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    payload = provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
    return StrongLeaderPullbackSourceAcceptanceSampleV1.model_validate(
        {**payload, "logical_fingerprint": _fingerprint(payload)}
    )


def _field_assessments(
    required_fields: tuple[str, ...],
    *,
    state: module.SourceFieldState = module.SourceFieldState.PROVIDED,
) -> tuple[module.SourceFieldAssessmentV1, ...]:
    return tuple(
        module.SourceFieldAssessmentV1(
            field_name=field_name,
            state=state,
            evidence_fingerprint=(
                "c" * 64 if state is module.SourceFieldState.PROVIDED else None
            ),
            reason_codes=(f"field_{state.value}",),
        )
        for field_name in required_fields
    )


def _permission(
    *, public_display: bool = True, private_research: bool = True
) -> module.SourcePermissionAssessmentV1:
    return module.SourcePermissionAssessmentV1(
        permission_review_fingerprint="d" * 64,
        production_representative_sample=True,
        private_research_permitted=private_research,
        local_evidence_retention_permitted=True,
        stable_identifier_use_permitted=True,
        public_derived_metric_display_permitted=public_display,
        termination_obligations_documented=True,
        reason_codes=("permission_reviewed",),
    )


def _assessment(
    sample: StrongLeaderPullbackSourceAcceptanceSampleV1,
    *,
    partial_lifecycle: bool = False,
    public_display: bool = True,
    private_research: bool = True,
) -> module.ProviderSampleAssessmentV1:
    actions = tuple(
        module.ActionCaseAssessmentV1(
            source_action_id=item.source_action_id,
            source_revision=item.source_revision,
            candidate_instrument_id=item.candidate_instrument_id,
            result_state=module.SourceResultState.MATCHED,
            result_evidence_fingerprint="e" * 64,
            stable_identity_state=module.StableIdentityState.VERIFIED,
            field_assessments=_field_assessments(ACTION_REQUIRED_FIELDS),
            reason_codes=("action_matched",),
        )
        for item in sample.action_cases
    )
    lifecycles = []
    for item in sample.lifecycle_cases:
        fields = list(_field_assessments(LIFECYCLE_REQUIRED_FIELDS))
        identity_state = module.StableIdentityState.VERIFIED
        if partial_lifecycle:
            identity_state = module.StableIdentityState.AMBIGUOUS
            fields = [
                module.SourceFieldAssessmentV1(
                    field_name=field_name,
                    state=(
                        module.SourceFieldState.PROVIDED
                        if field_name
                        in {
                            "first_and_last_tradable_dates",
                            "suspension_and_delisting_status_effective_dates",
                        }
                        else module.SourceFieldState.MISSING
                    ),
                    evidence_fingerprint=(
                        "f" * 64
                        if field_name
                        in {
                            "first_and_last_tradable_dates",
                            "suspension_and_delisting_status_effective_dates",
                        }
                        else None
                    ),
                    reason_codes=("partial_lifecycle_field",),
                )
                for field_name in LIFECYCLE_REQUIRED_FIELDS
            ]
        lifecycles.append(
            module.LifecycleCaseAssessmentV1(
                instrument_id=item.instrument_id,
                result_state=module.SourceResultState.MATCHED,
                result_evidence_fingerprint="1" * 64,
                stable_identity_state=identity_state,
                field_assessments=tuple(fields),
                reason_codes=("lifecycle_matched",),
            )
        )
    return module.build_provider_sample_assessment(
        provider_id="fixture-provider",
        product_id="fixture-product",
        sample_id="fixture-sample",
        assessed_at=NOW,
        source_schema_fingerprint="2" * 64,
        source_sample_fingerprint="3" * 64,
        acceptance_sample_sha256=SAMPLE_SHA,
        acceptance_sample_logical_fingerprint=sample.logical_fingerprint,
        permission=_permission(
            public_display=public_display,
            private_research=private_research,
        ),
        action_cases=actions,
        lifecycle_cases=tuple(lifecycles),
    )


def _evaluate(
    sample: StrongLeaderPullbackSourceAcceptanceSampleV1,
    assessment: module.ProviderSampleAssessmentV1,
) -> module.StrongLeaderPullbackSourceAcceptanceResultV1:
    return module.evaluate_strong_leader_pullback_source_sample(
        sample=sample,
        sample_sha256=SAMPLE_SHA,
        assessment=assessment,
        implementation_revision=REVISION,
        evaluated_at=NOW,
    )


def test_complete_synthetic_source_is_only_a_sole_primary_candidate() -> None:
    sample = _sample()
    result = _evaluate(sample, _assessment(sample))
    assert result.qualification is module.SourceQualification.SOLE_PRIMARY_CANDIDATE
    assert result.action_complete_count == 20
    assert result.lifecycle_complete_count == 64
    assert result.stable_identity_verified_case_count == 84
    assert result.provided_field_count == result.assessed_field_count == 672
    assert result.blocker_codes == ()
    assert result.sole_primary_source_selected is False
    assert result.performance_admission_authorized is False
    assert result.true_return_labels_authorized is False
    assert result.canonical_data_write_count == 0
    assert result.production_write_count == 0


def test_partial_fields_remain_corroboration_without_becoming_primary() -> None:
    sample = _sample()
    result = _evaluate(
        sample,
        _assessment(sample, partial_lifecycle=True, public_display=False),
    )
    assert result.qualification is module.SourceQualification.CORROBORATOR_ONLY
    assert result.action_complete_count == 20
    assert result.lifecycle_complete_count == 0
    assert result.provided_field_count == 288
    assert result.permission_gate_passed is False
    assert result.complete_semantic_gate_passed is False
    assert result.blocker_codes == (
        "lifecycle_cases_incomplete",
        "public_derived_metric_display_permission_absent",
        "stable_identity_cases_incomplete",
    )


def test_exact_ratio_cannot_be_marked_not_applicable() -> None:
    sample = _sample()
    assessment = _assessment(sample)
    action = assessment.action_cases[0]
    fields = tuple(
        module.SourceFieldAssessmentV1(
            field_name=field.field_name,
            state=(
                module.SourceFieldState.EXPLICIT_NOT_APPLICABLE
                if field.field_name == "exact_ratio_or_consideration"
                else field.state
            ),
            evidence_fingerprint=field.evidence_fingerprint,
            reason_codes=field.reason_codes,
        )
        for field in action.field_assessments
    )
    altered = module.build_provider_sample_assessment(
        **{
            **assessment.model_dump(
                mode="python", exclude={"logical_fingerprint", "action_cases"}
            ),
            "action_cases": (action.model_copy(update={"field_assessments": fields}),)
            + assessment.action_cases[1:],
        }
    )
    result = _evaluate(sample, altered)
    assert result.action_complete_count == 19
    assert result.qualification is module.SourceQualification.CORROBORATOR_ONLY
    assert "action_cases_incomplete" in result.blocker_codes


def test_unusable_permission_rejects_even_complete_source_content() -> None:
    sample = _sample()
    result = _evaluate(sample, _assessment(sample, private_research=False))
    assert result.qualification is module.SourceQualification.REJECTED
    assert result.complete_semantic_gate_passed is True
    assert result.permission_gate_passed is False
    assert result.blocker_codes == ("private_research_permission_absent",)


def test_missing_or_reordered_case_population_is_rejected() -> None:
    sample = _sample()
    assessment = _assessment(sample)
    altered = module.build_provider_sample_assessment(
        **{
            **assessment.model_dump(
                mode="python", exclude={"logical_fingerprint", "action_cases"}
            ),
            "action_cases": tuple(reversed(assessment.action_cases)),
        }
    )
    with pytest.raises(ValueError, match="action assessment population differs"):
        _evaluate(sample, altered)


def test_tampered_assessment_fingerprint_and_conflict_cannot_pass() -> None:
    sample = _sample()
    assessment = _assessment(sample)
    payload = assessment.model_dump(mode="json")
    payload["source_sample_fingerprint"] = "9" * 64
    with pytest.raises(ValidationError, match="assessment fingerprint differs"):
        module.ProviderSampleAssessmentV1.model_validate(payload)

    lifecycle = assessment.lifecycle_cases[0]
    conflict_fields = list(lifecycle.field_assessments)
    conflict_fields[0] = module.SourceFieldAssessmentV1(
        field_name=conflict_fields[0].field_name,
        state=module.SourceFieldState.CONFLICTING,
        evidence_fingerprint="8" * 64,
        reason_codes=("source_conflict",),
    )
    altered = module.build_provider_sample_assessment(
        **{
            **assessment.model_dump(
                mode="python", exclude={"logical_fingerprint", "lifecycle_cases"}
            ),
            "lifecycle_cases": (
                lifecycle.model_copy(
                    update={
                        "result_state": module.SourceResultState.CONFLICTING,
                        "field_assessments": tuple(conflict_fields),
                    }
                ),
            )
            + assessment.lifecycle_cases[1:],
        }
    )
    result = _evaluate(sample, altered)
    assert result.conflicting_case_count == 1
    assert result.lifecycle_complete_count == 63
    assert result.qualification is module.SourceQualification.CORROBORATOR_ONLY
    assert "source_conflicts_present" in result.blocker_codes
