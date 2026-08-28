from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

from tip_api.contracts.analytics.v1.review_deployment import (
    REVIEW_ACKNOWLEDGEMENT,
    REVIEW_ACKNOWLEDGEMENT_V1_1,
    ReviewDeploymentAuthorization,
    ReviewDeploymentAuthorizationV1,
    ReviewDeploymentAuthorizationV1_1,
    approved_review_authorization,
)


def test_both_exact_review_authorizations_remain_readable() -> None:
    old = approved_review_authorization(
        approved_as_of_session=date(2026, 8, 24),
        expected_latest_session=date(2026, 8, 25),
        expected_lag_sessions=1,
        explicit_user_acknowledgement=REVIEW_ACKNOWLEDGEMENT,
    )
    current = approved_review_authorization(
        approved_as_of_session=date(2026, 8, 26),
        expected_latest_session=date(2026, 8, 27),
        expected_lag_sessions=1,
        explicit_user_acknowledgement=REVIEW_ACKNOWLEDGEMENT_V1_1,
    )
    assert isinstance(old, ReviewDeploymentAuthorizationV1)
    assert isinstance(current, ReviewDeploymentAuthorizationV1_1)
    adapter = TypeAdapter(ReviewDeploymentAuthorization)
    assert isinstance(adapter.validate_python(old.model_dump(mode="json")), ReviewDeploymentAuthorizationV1)
    assert isinstance(adapter.validate_python(current.model_dump(mode="json")), ReviewDeploymentAuthorizationV1_1)


@pytest.mark.parametrize(
    ("approved", "expected", "acknowledgement"),
    [
        (date(2026, 8, 26), date(2026, 8, 27), REVIEW_ACKNOWLEDGEMENT),
        (date(2026, 8, 24), date(2026, 8, 25), REVIEW_ACKNOWLEDGEMENT_V1_1),
        (date(2026, 8, 26), date(2026, 8, 28), REVIEW_ACKNOWLEDGEMENT_V1_1),
    ],
)
def test_review_authorization_rejects_cross_version_or_date_drift(
    approved: date, expected: date, acknowledgement: str,
) -> None:
    with pytest.raises((ValueError, ValidationError), match="approved exact binding"):
        approved_review_authorization(
            approved_as_of_session=approved,
            expected_latest_session=expected,
            expected_lag_sessions=1,
            explicit_user_acknowledgement=acknowledgement,
        )
