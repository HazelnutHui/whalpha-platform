from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SHARED_CONTENT_ACCESS_POLICY_FINGERPRINT_V1,
    SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
    STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1,
    SourcePermissionConclusion,
    SourcePermissionReviewV1,
    SourceUseAssessmentStatus,
    SourceUsePermissionV1,
    assess_source_uses,
    source_permission_review_fingerprint,
)
from tip_api.services.historical_pilot_approval import (
    EXTERNAL_GATE_ORDER,
    REQUIRED_PILOT_SOURCE_FAMILY_IDS,
    HistoricalPilotApprovalError,
    HistoricalPilotRepositoryEvidenceV1,
    PilotApprovalGateEvidenceV1,
    PilotApprovalGateId,
    PilotApprovalGateState,
    PilotApprovalNextAction,
    PilotApprovalReviewStatus,
    build_historical_pilot_approval_review,
)
from tip_api.services.historical_pilot_planner import (
    HistoricalPilotInventoryV1,
    HistoricalPilotRequestV1,
    PilotRequestKind,
    plan_historical_research_pilot,
)


INVENTORY = "a" * 64
SOURCE_EVIDENCE = "b" * 64
ENTITLEMENT_EVIDENCE = "c" * 64
LIFECYCLE_EVIDENCE = "d" * 64
MAPPING_EVIDENCE = "e" * 64
ADJUSTMENT_EVIDENCE = "f" * 64
REVISION = "1" * 40
NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)
TARGETS = (date(2026, 7, 14), date(2026, 7, 15), date(2026, 7, 16))


def _plan():
    return plan_historical_research_pilot(
        inventory=HistoricalPilotInventoryV1(
            source_report_id="current-context-report-v1",
            inventory_fingerprint=INVENTORY,
            completed_eod_sessions=(),
            completed_identity_sessions=(),
        ),
        request=HistoricalPilotRequestV1(
            target_sessions=TARGETS,
            inactive_identity_anchor_dates=TARGETS,
            targeted_ticker_event_scopes=(),
            provider_id="example_historical_source",
        ),
    )


def _repository_evidence() -> HistoricalPilotRepositoryEvidenceV1:
    return HistoricalPilotRepositoryEvidenceV1(
        implementation_revision=REVISION,
        synthetic_action_mapping_fingerprint=MAPPING_EVIDENCE,
        adjustment_invariants_fingerprint=ADJUSTMENT_EVIDENCE,
    )


def _gate(
    gate_id: PilotApprovalGateId,
    state: PilotApprovalGateState,
    evidence: str | None,
    *reasons: str,
    observed_at: datetime | None = None,
    valid_until: datetime | None = None,
) -> PilotApprovalGateEvidenceV1:
    return PilotApprovalGateEvidenceV1(
        gate_id=gate_id,
        state=state,
        evidence_fingerprint=evidence,
        reason_codes=tuple(sorted(reasons)),
        observed_at=observed_at,
        valid_until=valid_until,
    )


def _blocked_gates() -> tuple[PilotApprovalGateEvidenceV1, ...]:
    return (
        _gate(
            PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
            PilotApprovalGateState.UNVERIFIED,
            None,
            "live_entitlement_not_verified",
            observed_at=NOW,
            valid_until=NOW + timedelta(hours=1),
        ),
        _gate(
            PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
            PilotApprovalGateState.SATISFIED,
            INVENTORY,
            observed_at=NOW,
            valid_until=NOW + timedelta(hours=1),
        ),
        _gate(
            PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE,
            PilotApprovalGateState.UNSATISFIED,
            LIFECYCLE_EVIDENCE,
            "terminal_source_incomplete",
            observed_at=NOW,
            valid_until=NOW + timedelta(days=7),
        ),
    )


def _ready_gates() -> tuple[PilotApprovalGateEvidenceV1, ...]:
    evidence = {
        PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT: ENTITLEMENT_EVIDENCE,
        PilotApprovalGateId.EXACT_CURRENT_INVENTORY: INVENTORY,
        PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE: LIFECYCLE_EVIDENCE,
    }
    return tuple(
        _gate(
            gate_id,
            PilotApprovalGateState.SATISFIED,
            evidence[gate_id],
            observed_at=NOW,
            valid_until=(
                NOW + timedelta(hours=1)
                if gate_id
                in {
                    PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
                    PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
                }
                else NOW + timedelta(days=7)
            ),
        )
        for gate_id in EXTERNAL_GATE_ORDER
    )


def _source_package(
    conclusion: SourcePermissionConclusion,
    *,
    assessed_at: datetime = NOW,
):
    permissions = tuple(
        SourceUsePermissionV1(
            use_case=use_case,
            conclusion=conclusion,
            reason_codes=("terms_gate",)
            if conclusion is not SourcePermissionConclusion.CLEARED
            else (),
            evidence_fingerprints=(SOURCE_EVIDENCE,),
        )
        for use_case in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
    )
    review = SourcePermissionReviewV1(
        source_id="example_historical_source",
        source_display_name="Example Historical Source",
        reviewed_at=NOW,
        valid_until=NOW + timedelta(days=30),
        supported_data_family_ids=REQUIRED_PILOT_SOURCE_FAMILY_IDS,
        official_evidence_urls=("https://example.com/official-terms",),
        permissions=permissions,
    )
    assessments = tuple(
        assess_source_uses(
            review,
            data_family_id=family_id,
            required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
            assessed_at=assessed_at,
        )
        for family_id in REQUIRED_PILOT_SOURCE_FAMILY_IDS
    )
    return review, assessments


def _review(gates=None, plan=None, permission_package=None):
    review, assessments = permission_package or _source_package(
        SourcePermissionConclusion.BLOCKED
    )
    return build_historical_pilot_approval_review(
        plan=plan or _plan(),
        repository_evidence=_repository_evidence(),
        external_gate_evidence=gates or _blocked_gates(),
        source_permission_review=review,
        source_permission_assessments=assessments,
        reviewed_at=NOW,
    )


def test_current_preliminary_review_is_blocked_and_performs_nothing() -> None:
    review = _review()
    by_kind = {item.kind: item for item in review.request_summary}

    assert review.target_sessions == ("2026-07-14", "2026-07-15", "2026-07-16")
    assert review.planned_request_ceiling == 75
    assert review.estimated_transport_seconds_at_ceiling == 1_125
    assert by_kind[PilotRequestKind.GROUPED_DAILY.value].request_ceiling == 3
    assert by_kind[PilotRequestKind.ACTIVE_ALL_TICKERS.value].request_ceiling == 60
    assert by_kind[PilotRequestKind.TICKER_EVENTS_EXPERIMENTAL.value].request_ceiling == 0
    assert review.review_status is PilotApprovalReviewStatus.BLOCKED
    assert review.next_action is PilotApprovalNextAction.RESOLVE_REVIEW_GATES
    assert review.unresolved_gate_ids == (
        "account_endpoint_entitlement",
        "equal_capability_source_permission",
        "lifecycle_source_coverage",
    )
    assert review.required_user_acknowledgement is None
    assert not any(
        (
            review.acquisition_authorized,
            review.apply_authorized,
            review.publication_authorized,
            review.deployment_authorized,
            review.scheduler_authorized,
        )
    )
    assert review.external_request_count == 0
    assert review.data_write_count == 0


def test_all_external_gates_only_make_review_ready_for_separate_user_authorization() -> None:
    review = _review(
        _ready_gates(),
        permission_package=_source_package(SourcePermissionConclusion.CLEARED),
    )

    assert review.review_status is (
        PilotApprovalReviewStatus.READY_FOR_EXACT_USER_AUTHORIZATION_REVIEW
    )
    assert review.next_action is PilotApprovalNextAction.REQUEST_EXACT_USER_AUTHORIZATION
    assert review.unresolved_gate_ids == ()
    assert review.required_user_acknowledgement == (
        "I_AUTHORIZE_HISTORICAL_PILOT_"
        f"{review.authorization_binding_fingerprint}"
    )
    assert review.acquisition_authorized is False
    assert review.external_request_count == 0
    assert review.data_write_count == 0


def test_review_binds_unified_registry_access_policy_inventory_and_revision() -> None:
    review = _review()

    assert review.inventory_fingerprint == INVENTORY
    assert review.implementation_revision == REVISION
    assert (
        review.standard_data_family_registry_fingerprint
        == STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1
    )
    assert (
        review.shared_content_access_policy_fingerprint
        == SHARED_CONTENT_ACCESS_POLICY_FINGERPRINT_V1
    )
    assert review.source_permission_policy_fingerprint == (
        SOURCE_PERMISSION_POLICY_FINGERPRINT_V1
    )
    assert review.source_permission_family_ids == REQUIRED_PILOT_SOURCE_FAMILY_IDS
    assert review.source_permission_assessment_statuses == (
        SourceUseAssessmentStatus.BLOCKED_BY_PERMISSION.value,
    ) * 3
    assert review.source_permission_source_id == "example_historical_source"
    assert review.as_dict()["review_status"] == "blocked"
    assert review.as_dict()["gate_results"][0]["observed_at"].endswith("+00:00")
    assert len(review.logical_content_fingerprint) == 64


def test_review_is_deterministic_for_identical_evidence() -> None:
    assert _review() == _review()


def test_external_gates_must_be_exact_ordered_and_inventory_bound() -> None:
    gates = _blocked_gates()
    with pytest.raises(HistoricalPilotApprovalError, match="exact and ordered"):
        _review(tuple(reversed(gates)))

    wrong_inventory = list(gates)
    wrong_inventory[1] = _gate(
        PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
        PilotApprovalGateState.SATISFIED,
        "9" * 64,
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=1),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="bind the pilot inventory"):
        _review(tuple(wrong_inventory))


def test_unresolved_gate_needs_reason_and_satisfied_gate_needs_evidence() -> None:
    gates = list(_blocked_gates())
    gates[0] = _gate(
        PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
        PilotApprovalGateState.UNVERIFIED,
        None,
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=1),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="requires a reason"):
        _review(tuple(gates))

    gates = list(_ready_gates())
    gates[0] = _gate(
        PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
        PilotApprovalGateState.SATISFIED,
        None,
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=1),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="requires evidence"):
        _review(tuple(gates))


def test_malformed_repository_evidence_and_naive_review_time_fail_closed() -> None:
    with pytest.raises(HistoricalPilotApprovalError, match="revision"):
        build_historical_pilot_approval_review(
            plan=_plan(),
            repository_evidence=replace(
                _repository_evidence(),
                implementation_revision="not-a-revision",
            ),
            external_gate_evidence=_blocked_gates(),
            source_permission_review=_source_package(
                SourcePermissionConclusion.BLOCKED
            )[0],
            source_permission_assessments=_source_package(
                SourcePermissionConclusion.BLOCKED
            )[1],
            reviewed_at=NOW,
        )


def test_satisfied_external_gate_must_be_current_and_bounded() -> None:
    stale = list(_ready_gates())
    stale[0] = _gate(
        PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
        PilotApprovalGateState.SATISFIED,
        ENTITLEMENT_EVIDENCE,
        observed_at=NOW - timedelta(hours=2),
        valid_until=NOW - timedelta(hours=1),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="stale"):
        _review(tuple(stale))

    too_long = list(_ready_gates())
    too_long[1] = _gate(
        PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
        PilotApprovalGateState.SATISFIED,
        INVENTORY,
        observed_at=NOW,
        valid_until=NOW + timedelta(days=2),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="validity"):
        _review(tuple(too_long))
    with pytest.raises(HistoricalPilotApprovalError, match="timezone-aware"):
        build_historical_pilot_approval_review(
            plan=_plan(),
            repository_evidence=_repository_evidence(),
            external_gate_evidence=_blocked_gates(),
            source_permission_review=_source_package(
                SourcePermissionConclusion.BLOCKED
            )[0],
            source_permission_assessments=_source_package(
                SourcePermissionConclusion.BLOCKED
            )[1],
            reviewed_at=NOW.replace(tzinfo=None),
        )


def test_plan_count_or_tmp_path_tampering_is_rejected() -> None:
    with pytest.raises(HistoricalPilotApprovalError, match="default-deny and bounded"):
        _review(plan=replace(_plan(), planned_request_ceiling=74))
    with pytest.raises(HistoricalPilotApprovalError, match="paths are unsafe"):
        _review(
            plan=replace(
                _plan(),
                temporary_package_relative_paths=("/tmp/escaped",) * 78,
            )
        )


def test_source_permission_must_bind_exact_families_uses_review_and_time() -> None:
    review, ready = _source_package(SourcePermissionConclusion.CLEARED)
    with pytest.raises(HistoricalPilotApprovalError, match="exact pilot families"):
        _review(permission_package=(review, tuple(reversed(ready))))

    wrong_source = list(ready)
    wrong_source[1] = wrong_source[1].model_copy(
        update={"source_id": "different_source"}
    )
    with pytest.raises(HistoricalPilotApprovalError, match="one source"):
        _review(permission_package=(review, tuple(wrong_source)))

    partial_uses = list(ready)
    partial_uses[1] = partial_uses[1].model_copy(
        update={
            "required_use_cases": (
                EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1[0],
            )
        }
    )
    with pytest.raises(HistoricalPilotApprovalError, match="every equal-capability use"):
        _review(permission_package=(review, tuple(partial_uses)))

    stale_time = _source_package(
        SourcePermissionConclusion.CLEARED,
        assessed_at=NOW + timedelta(seconds=1),
    )
    with pytest.raises(HistoricalPilotApprovalError, match="fresh at review time"):
        _review(permission_package=stale_time)


def test_source_permission_review_must_match_plan_provider() -> None:
    mismatched = _plan()
    mismatched = replace(mismatched, provider_id="different_source")

    with pytest.raises(HistoricalPilotApprovalError, match="match the pilot provider"):
        _review(plan=mismatched)


def test_cleared_assessments_cannot_override_a_blocked_bound_review() -> None:
    blocked_review, _ = _source_package(SourcePermissionConclusion.BLOCKED)
    _, cleared_assessments = _source_package(SourcePermissionConclusion.CLEARED)
    forged = tuple(
        item.model_copy(
            update={
                "source_id": blocked_review.source_id,
                "permission_review_fingerprint": source_permission_review_fingerprint(
                    blocked_review
                ),
                "permission_review_valid_until": blocked_review.valid_until,
            }
        )
        for item in cleared_assessments
    )
    with pytest.raises(HistoricalPilotApprovalError, match="not derived"):
        _review(permission_package=(blocked_review, forged))
