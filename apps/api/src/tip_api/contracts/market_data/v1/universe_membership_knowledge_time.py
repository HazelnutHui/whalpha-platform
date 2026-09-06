"""Knowledge-time assessment for one immutable Universe Membership partition."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility


KNOWLEDGE_TIME_POLICY_VERSION = "universe-membership-next-open-knowledge-time/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class UniverseMembershipKnowledgeTimeAssessmentV1(FrozenContract):
    """Bind Membership evidence to the exact next-open usability boundary."""

    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal[KNOWLEDGE_TIME_POLICY_VERSION] = (
        KNOWLEDGE_TIME_POLICY_VERSION
    )
    membership_logical_fingerprint: str = Field(pattern=_SHA256)
    membership_manifest_sha256: str = Field(pattern=_SHA256)
    membership_parquet_sha256: str = Field(pattern=_SHA256)
    identity_source_logical_fingerprint: str = Field(pattern=_SHA256)
    identity_source_contract_version: Literal[
        "historical-identity-source-custody/1.0",
        "historical-identity-source-custody/1.1",
    ]
    identity_source_point_in_time_eligibility: Literal[
        "outcome_reconciliation_only",
        "eligible_at_source_observed_at",
    ]
    methodology_version: str
    session_date: date
    market_information_cutoff_at: datetime
    source_data_cutoff: datetime
    evaluated_at: datetime
    entry_session_date: date
    next_session_open_at: datetime
    assessed_at: datetime
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str
    point_in_time_eligibility: PointInTimeEligibility
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator(
        "market_information_cutoff_at",
        "source_data_cutoff",
        "evaluated_at",
        "next_session_open_at",
        "assessed_at",
    )
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("methodology_version", "calendar_version")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{info.field_name} is required")
        return value.strip()

    @field_validator("reason_codes", mode="before")
    @classmethod
    def canonical_reasons(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("reason_codes must be a collection")
        normalized = tuple(
            sorted(
                {
                    str(item).strip().lower().replace("-", "_").replace(" ", "_")
                    for item in value
                    if str(item).strip()
                }
            )
        )
        if not normalized:
            raise ValueError("knowledge-time assessment requires a reason code")
        return normalized

    @model_validator(mode="after")
    def assessment_reconciles(self) -> "UniverseMembershipKnowledgeTimeAssessmentV1":
        if self.entry_session_date <= self.session_date:
            raise ValueError("entry session must follow the represented session")
        if not (
            self.market_information_cutoff_at
            <= self.source_data_cutoff
            <= self.evaluated_at
            <= self.assessed_at
        ):
            raise ValueError("knowledge-time timestamps are not chronologically ordered")
        if self.next_session_open_at <= self.market_information_cutoff_at:
            raise ValueError("next-session open must follow the information cutoff")

        completed_before_open = self.evaluated_at < self.next_session_open_at
        source_is_contemporaneous = (
            self.identity_source_point_in_time_eligibility
            == "eligible_at_source_observed_at"
        )
        expected_eligibility = (
            PointInTimeEligibility.SIGNAL_ELIGIBLE
            if source_is_contemporaneous and completed_before_open
            else PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
        )
        if self.point_in_time_eligibility is not expected_eligibility:
            raise ValueError("point-in-time eligibility differs from the timing policy")
        if expected_eligibility is PointInTimeEligibility.SIGNAL_ELIGIBLE:
            if self.reason_codes != (
                "source_and_evaluation_completed_before_next_session_open",
            ):
                raise ValueError("signal-eligible timing reason differs")
        else:
            expected_reasons = set()
            if not source_is_contemporaneous:
                expected_reasons.add("identity_source_outcome_reconciliation_only")
            if not completed_before_open:
                expected_reasons.add("membership_evaluation_not_before_next_session_open")
            if set(self.reason_codes) != expected_reasons:
                raise ValueError("outcome-only timing reasons differ")

        expected_fingerprint = universe_membership_knowledge_time_fingerprint(self)
        if self.logical_fingerprint != expected_fingerprint:
            raise ValueError("knowledge-time assessment fingerprint mismatch")
        return self


def build_universe_membership_knowledge_time_assessment(
    **values: object,
) -> UniverseMembershipKnowledgeTimeAssessmentV1:
    provisional = UniverseMembershipKnowledgeTimeAssessmentV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return UniverseMembershipKnowledgeTimeAssessmentV1.model_validate(
        {
            **values,
            "logical_fingerprint": universe_membership_knowledge_time_fingerprint(
                provisional
            ),
        }
    )


def universe_membership_knowledge_time_fingerprint(
    assessment: UniverseMembershipKnowledgeTimeAssessmentV1,
) -> str:
    payload = assessment.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
