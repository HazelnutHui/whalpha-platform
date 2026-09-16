from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessError,
    build_campaign_three_development_access_request,
    expected_campaign_three_authorization_phrase,
    grant_campaign_three_development_access,
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
