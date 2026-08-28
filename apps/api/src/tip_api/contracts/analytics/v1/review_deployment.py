"""Exact, one-release authorization contract for a stale Production review."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


REVIEW_DEPLOYMENT_CONTRACT_VERSION = "production-review-deployment/1.0"
REVIEW_APPROVED_AS_OF_SESSION = date(2026, 8, 24)
REVIEW_EXPECTED_LATEST_SESSION = date(2026, 8, 25)
REVIEW_EXPECTED_LAG_SESSIONS = 1
REVIEW_ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1"
REVIEW_DEPLOYMENT_CONTRACT_VERSION_V1_1 = "production-review-deployment/1.1"
REVIEW_APPROVED_AS_OF_SESSION_V1_1 = date(2026, 8, 26)
REVIEW_EXPECTED_LATEST_SESSION_V1_1 = date(2026, 8, 27)
REVIEW_EXPECTED_LAG_SESSIONS_V1_1 = 1
REVIEW_ACKNOWLEDGEMENT_V1_1 = "I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1"


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


class ReviewDeploymentAuthorizationV1_1(BaseModel):
    """A deliberately non-general authorization for the approved 2026-08-26 review."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["production-review-deployment/1.1"] = (
        REVIEW_DEPLOYMENT_CONTRACT_VERSION_V1_1
    )
    review_mode: Literal[True] = True
    normal_freshness: Literal[False] = False
    data_status: Literal["stale_review"] = "stale_review"
    approved_as_of_session: date
    expected_latest_session: date
    expected_lag_sessions: Literal[1]
    explicit_user_acknowledgement: str

    @model_validator(mode="after")
    def exact_authorization(self) -> "ReviewDeploymentAuthorizationV1_1":
        if (
            self.approved_as_of_session != REVIEW_APPROVED_AS_OF_SESSION_V1_1
            or self.expected_latest_session != REVIEW_EXPECTED_LATEST_SESSION_V1_1
            or self.expected_lag_sessions != REVIEW_EXPECTED_LAG_SESSIONS_V1_1
            or self.explicit_user_acknowledgement != REVIEW_ACKNOWLEDGEMENT_V1_1
        ):
            raise ValueError("review deployment authorization is not the approved exact binding")
        return self


ReviewDeploymentAuthorization: TypeAlias = Annotated[
    ReviewDeploymentAuthorizationV1 | ReviewDeploymentAuthorizationV1_1,
    Field(discriminator="contract_version"),
]


def approved_review_authorization(
    *,
    approved_as_of_session: date,
    expected_latest_session: date,
    expected_lag_sessions: int,
    explicit_user_acknowledgement: str,
) -> ReviewDeploymentAuthorization:
    values = {
        "approved_as_of_session": approved_as_of_session,
        "expected_latest_session": expected_latest_session,
        "expected_lag_sessions": expected_lag_sessions,
        "explicit_user_acknowledgement": explicit_user_acknowledgement,
    }
    if explicit_user_acknowledgement == REVIEW_ACKNOWLEDGEMENT:
        return ReviewDeploymentAuthorizationV1(**values)
    if explicit_user_acknowledgement == REVIEW_ACKNOWLEDGEMENT_V1_1:
        return ReviewDeploymentAuthorizationV1_1(**values)
    raise ValueError("review deployment authorization is not the approved exact binding")


def review_acknowledgement_for_contract(contract_version: str) -> str:
    """Return the exact acknowledgement bound to one supported review contract."""

    if contract_version == REVIEW_DEPLOYMENT_CONTRACT_VERSION:
        return REVIEW_ACKNOWLEDGEMENT
    if contract_version == REVIEW_DEPLOYMENT_CONTRACT_VERSION_V1_1:
        return REVIEW_ACKNOWLEDGEMENT_V1_1
    raise ValueError("unsupported review deployment contract")
