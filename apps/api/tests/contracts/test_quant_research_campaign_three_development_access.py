from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessError,
    CampaignThreeDevelopmentExecutionKind,
    build_campaign_three_development_access_request,
    build_campaign_three_execution_completion,
    build_campaign_three_execution_reservation,
    expected_campaign_three_authorization_phrase,
    grant_campaign_three_development_access,
    validate_campaign_three_development_grant,
)


REVISION = "1" * 40


def test_development_access_request_is_closed_and_revision_bound() -> None:
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )

    assert request.implementation_revision == REVISION
    assert request.authorized_trial_count_if_granted == 3
    assert request.formal_execution_count_if_granted == 1
    assert request.exact_replay_execution_count_if_granted == 1
    assert request.development_outcome_access_authorized is False
    assert request.validation_access_authorized is False
    assert request.holdout_access_authorized is False
    assert expected_campaign_three_authorization_phrase(request).endswith(
        request.logical_fingerprint
    )


def test_development_access_request_rejects_dirty_tree() -> None:
    with pytest.raises(CampaignThreeDevelopmentAccessError, match="clean committed"):
        build_campaign_three_development_access_request(
            implementation_revision=REVISION,
            implementation_tree_clean=False,
        )


def test_development_access_grant_requires_exact_phrase_and_stays_bounded() -> None:
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )
    with pytest.raises(CampaignThreeDevelopmentAccessError, match="phrase differs"):
        grant_campaign_three_development_access(
            request=request,
            authorization_phrase="I_AUTHORIZE_SOMETHING_ELSE",
            granted_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

    grant = grant_campaign_three_development_access(
        request=request,
        authorization_phrase=expected_campaign_three_authorization_phrase(request),
        granted_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    assert grant.development_outcome_access_authorized is True
    assert grant.total_execution_count == 2
    assert grant.formal_execution_count == 1
    assert grant.exact_replay_execution_count == 1
    assert grant.validation_access_authorized is False
    assert grant.holdout_access_authorized is False
    assert grant.canonical_data_write_authorized is False
    assert grant.production_write_authorized is False
    validate_campaign_three_development_grant(request=request, grant=grant)


def test_development_access_grant_cannot_be_rebound_to_another_request() -> None:
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )
    grant = grant_campaign_three_development_access(
        request=request,
        authorization_phrase=expected_campaign_three_authorization_phrase(request),
        granted_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    other_request = build_campaign_three_development_access_request(
        implementation_revision="2" * 40,
        implementation_tree_clean=True,
    )

    with pytest.raises(
        CampaignThreeDevelopmentAccessError,
        match="does not match",
    ):
        validate_campaign_three_development_grant(
            request=other_request,
            grant=grant,
        )


def test_execution_contract_requires_formal_before_exact_replay() -> None:
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )
    granted_at = datetime(2026, 9, 16, 1, tzinfo=timezone.utc)
    grant = grant_campaign_three_development_access(
        request=request,
        authorization_phrase=expected_campaign_three_authorization_phrase(request),
        granted_at=granted_at,
    )
    run_created_at = datetime(2026, 9, 16, 2, tzinfo=timezone.utc)

    with pytest.raises(CampaignThreeDevelopmentAccessError, match="requires a completed"):
        build_campaign_three_execution_reservation(
            request=request,
            grant=grant,
            execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
            run_created_at=run_created_at,
            reserved_at=run_created_at,
            output_root_fingerprint="2" * 64,
        )

    formal = build_campaign_three_execution_reservation(
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.FORMAL,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        output_root_fingerprint="1" * 64,
    )
    completion = build_campaign_three_execution_completion(
        reservation=formal,
        report_sha256="3" * 64,
        report_fingerprint="4" * 64,
        completed_at=run_created_at,
    )
    replay = build_campaign_three_execution_reservation(
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        output_root_fingerprint="2" * 64,
        formal_completion=completion,
    )

    assert replay.expected_formal_report_sha256 == completion.report_sha256
    assert replay.expected_formal_report_fingerprint == completion.report_fingerprint


def test_replay_completion_must_match_formal_result() -> None:
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )
    run_created_at = datetime(2026, 9, 16, 2, tzinfo=timezone.utc)
    grant = grant_campaign_three_development_access(
        request=request,
        authorization_phrase=expected_campaign_three_authorization_phrase(request),
        granted_at=datetime(2026, 9, 16, 1, tzinfo=timezone.utc),
    )
    formal = build_campaign_three_execution_reservation(
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.FORMAL,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        output_root_fingerprint="1" * 64,
    )
    formal_completion = build_campaign_three_execution_completion(
        reservation=formal,
        report_sha256="3" * 64,
        report_fingerprint="4" * 64,
        completed_at=run_created_at,
    )
    replay = build_campaign_three_execution_reservation(
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        output_root_fingerprint="2" * 64,
        formal_completion=formal_completion,
    )

    with pytest.raises(CampaignThreeDevelopmentAccessError, match="differs from formal"):
        build_campaign_three_execution_completion(
            reservation=replay,
            report_sha256="5" * 64,
            report_fingerprint="4" * 64,
            completed_at=run_created_at,
        )
