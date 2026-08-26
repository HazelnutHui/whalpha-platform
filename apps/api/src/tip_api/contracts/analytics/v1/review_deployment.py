"""Exact, one-release authorization contract for a stale Production review."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


REVIEW_DEPLOYMENT_CONTRACT_VERSION = "production-review-deployment/1.0"
REVIEW_APPROVED_AS_OF_SESSION = date(2026, 8, 24)
REVIEW_EXPECTED_LATEST_SESSION = date(2026, 8, 25)
REVIEW_EXPECTED_LAG_SESSIONS = 1
REVIEW_ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1"


class ReviewDeploymentAuthorizationV1(BaseModel):
    """A deliberately non-general authorization for the approved 2026-08-24 review."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["production-review-deployment/1.0"] = (
        REVIEW_DEPLOYMENT_CONTRACT_VERSION
    )
    review_mode: Literal[True] = True
    normal_freshness: Literal[False] = False
    data_status: Literal["stale_review"] = "stale_review"
    approved_as_of_session: date
    expected_latest_session: date
    expected_lag_sessions: Literal[1]
    explicit_user_acknowledgement: str

    @model_validator(mode="after")
    def exact_authorization(self) -> "ReviewDeploymentAuthorizationV1":
        if (
            self.approved_as_of_session != REVIEW_APPROVED_AS_OF_SESSION
            or self.expected_latest_session != REVIEW_EXPECTED_LATEST_SESSION
            or self.expected_lag_sessions != REVIEW_EXPECTED_LAG_SESSIONS
            or self.explicit_user_acknowledgement != REVIEW_ACKNOWLEDGEMENT
        ):
            raise ValueError("review deployment authorization is not the approved exact binding")
        return self


def approved_review_authorization(
    *,
    approved_as_of_session: date,
    expected_latest_session: date,
    expected_lag_sessions: int,
    explicit_user_acknowledgement: str,
) -> ReviewDeploymentAuthorizationV1:
    return ReviewDeploymentAuthorizationV1(
        approved_as_of_session=approved_as_of_session,
        expected_latest_session=expected_latest_session,
        expected_lag_sessions=expected_lag_sessions,
        explicit_user_acknowledgement=explicit_user_acknowledgement,
    )
