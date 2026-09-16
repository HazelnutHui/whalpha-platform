"""Typed one-run-plus-replay access boundary for Campaign Three Development."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_campaign_three_screening import (
    quant_research_campaign_three_screening_protocol_v1,
)
from .quant_research_discovery_trial_ledger_v4 import (
    quant_research_discovery_trial_ledger_v4,
)


CAMPAIGN_THREE_DEVELOPMENT_ACCESS_REQUEST_CONTRACT_VERSION = (
    "quant-research-campaign-three-development-access-request/1.0"
)
CAMPAIGN_THREE_DEVELOPMENT_ACCESS_GRANT_CONTRACT_VERSION = (
    "quant-research-campaign-three-development-access-grant/1.0"
)
CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_RESERVATION_CONTRACT_VERSION = (
    "quant-research-campaign-three-development-execution-reservation/1.0"
)
CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_COMPLETION_CONTRACT_VERSION = (
    "quant-research-campaign-three-development-execution-completion/1.0"
)
AUTHORIZATION_PREFIX = "I_AUTHORIZE_CAMPAIGN_THREE_DEVELOPMENT_SCREEN_"


class CampaignThreeDevelopmentAccessError(ValueError):
    pass


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CampaignThreeDevelopmentExecutionKind(StrEnum):
    FORMAL = "formal"
    EXACT_REPLAY = "exact_replay"


class CampaignThreeDevelopmentAccessRequestV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        CAMPAIGN_THREE_DEVELOPMENT_ACCESS_REQUEST_CONTRACT_VERSION
    ] = CAMPAIGN_THREE_DEVELOPMENT_ACCESS_REQUEST_CONTRACT_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_tree_clean: Literal[True] = True
    outcome_partition: Literal["development"] = "development"
    authorized_trial_count_if_granted: Literal[3] = 3
    formal_execution_count_if_granted: Literal[1] = 1
    exact_replay_execution_count_if_granted: Literal[1] = 1
    created_at_must_match_across_run_and_replay: Literal[True] = True
    source_revision_must_match_across_run_and_replay: Literal[True] = True
    distinct_owner_only_output_roots_required: Literal[True] = True
    prior_result_access_prohibited: Literal[True] = True
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    broker_or_trading_authorized: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    status: Literal["awaiting_exact_user_authorization"] = (
        "awaiting_exact_user_authorization"
    )
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def request_reconciles(self) -> "CampaignThreeDevelopmentAccessRequestV1":
        protocol = quant_research_campaign_three_screening_protocol_v1()
        ledger = quant_research_discovery_trial_ledger_v4()
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.ledger_fingerprint != ledger.logical_fingerprint
            or development_access_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three Development access request differs")
        return self


class CampaignThreeDevelopmentAccessGrantV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        CAMPAIGN_THREE_DEVELOPMENT_ACCESS_GRANT_CONTRACT_VERSION
    ] = CAMPAIGN_THREE_DEVELOPMENT_ACCESS_GRANT_CONTRACT_VERSION
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    granted_at: datetime
    authorization_phrase_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_partition: Literal["development"] = "development"
    authorized_trial_count: Literal[3] = 3
    formal_execution_count: Literal[1] = 1
    exact_replay_execution_count: Literal[1] = 1
    total_execution_count: Literal[2] = 2
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    broker_or_trading_authorized: Literal[False] = False
    development_outcome_access_authorized: Literal[True] = True
    status: Literal["granted_once_for_formal_run_and_exact_replay"] = (
        "granted_once_for_formal_run_and_exact_replay"
    )
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def grant_reconciles(self) -> "CampaignThreeDevelopmentAccessGrantV1":
        protocol = quant_research_campaign_three_screening_protocol_v1()
        ledger = quant_research_discovery_trial_ledger_v4()
        if (
            not _is_utc(self.granted_at)
            or self.protocol_fingerprint != protocol.logical_fingerprint
            or self.ledger_fingerprint != ledger.logical_fingerprint
        ):
            raise ValueError("Campaign Three Development grant must use UTC")
        if development_access_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Campaign Three Development access grant differs")
        return self


class CampaignThreeDevelopmentExecutionReservationV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_RESERVATION_CONTRACT_VERSION
    ] = CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_RESERVATION_CONTRACT_VERSION
    execution_kind: CampaignThreeDevelopmentExecutionKind
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    grant_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    run_created_at: datetime
    reserved_at: datetime
    output_root_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_formal_report_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    expected_formal_report_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    status: Literal["reserved_and_consumed"] = "reserved_and_consumed"
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def reservation_reconciles(
        self,
    ) -> "CampaignThreeDevelopmentExecutionReservationV1":
        formal_bindings = (
            self.expected_formal_report_sha256,
            self.expected_formal_report_fingerprint,
        )
        if (
            not _is_utc(self.run_created_at)
            or not _is_utc(self.reserved_at)
            or (
                self.execution_kind
                is CampaignThreeDevelopmentExecutionKind.FORMAL
                and any(formal_bindings)
            )
            or (
                self.execution_kind
                is CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY
                and not all(formal_bindings)
            )
            or development_access_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three Development reservation differs")
        return self


class CampaignThreeDevelopmentExecutionCompletionV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_COMPLETION_CONTRACT_VERSION
    ] = CAMPAIGN_THREE_DEVELOPMENT_EXECUTION_COMPLETION_CONTRACT_VERSION
    execution_kind: CampaignThreeDevelopmentExecutionKind
    reservation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_at: datetime
    status: Literal["completed"] = "completed"
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def completion_reconciles(
        self,
    ) -> "CampaignThreeDevelopmentExecutionCompletionV1":
        if (
            not _is_utc(self.completed_at)
            or development_access_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three Development completion differs")
        return self


def build_campaign_three_development_access_request(
    *, implementation_revision: str, implementation_tree_clean: bool
) -> CampaignThreeDevelopmentAccessRequestV1:
    if not implementation_tree_clean:
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development access requires a clean committed tree"
        )
    payload: dict[str, object] = {
        "protocol_fingerprint": (
            quant_research_campaign_three_screening_protocol_v1().logical_fingerprint
        ),
        "ledger_fingerprint": quant_research_discovery_trial_ledger_v4().logical_fingerprint,
        "implementation_revision": implementation_revision,
        "implementation_tree_clean": True,
    }
    provisional = CampaignThreeDevelopmentAccessRequestV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeDevelopmentAccessRequestV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_access_fingerprint(provisional),
        }
    )


def expected_campaign_three_authorization_phrase(
    request: CampaignThreeDevelopmentAccessRequestV1,
) -> str:
    return f"{AUTHORIZATION_PREFIX}{request.logical_fingerprint}"


def grant_campaign_three_development_access(
    *,
    request: CampaignThreeDevelopmentAccessRequestV1,
    authorization_phrase: str,
    granted_at: datetime,
) -> CampaignThreeDevelopmentAccessGrantV1:
    expected = expected_campaign_three_authorization_phrase(request)
    if authorization_phrase != expected:
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development authorization phrase differs"
        )
    phrase_sha = hashlib.sha256(authorization_phrase.encode("utf-8")).hexdigest()
    payload: dict[str, object] = {
        "request_fingerprint": request.logical_fingerprint,
        "protocol_fingerprint": request.protocol_fingerprint,
        "ledger_fingerprint": request.ledger_fingerprint,
        "implementation_revision": request.implementation_revision,
        "granted_at": granted_at,
        "authorization_phrase_sha256": phrase_sha,
    }
    provisional = CampaignThreeDevelopmentAccessGrantV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeDevelopmentAccessGrantV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_access_fingerprint(provisional),
        }
    )


def validate_campaign_three_development_grant(
    *,
    request: CampaignThreeDevelopmentAccessRequestV1,
    grant: CampaignThreeDevelopmentAccessGrantV1,
) -> None:
    expected = expected_campaign_three_authorization_phrase(request)
    expected_phrase_sha = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    if (
        request.status != "awaiting_exact_user_authorization"
        or request.development_outcome_access_authorized
        or grant.request_fingerprint != request.logical_fingerprint
        or grant.protocol_fingerprint != request.protocol_fingerprint
        or grant.ledger_fingerprint != request.ledger_fingerprint
        or grant.implementation_revision != request.implementation_revision
        or grant.authorization_phrase_sha256 != expected_phrase_sha
        or not grant.development_outcome_access_authorized
    ):
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development grant does not match its request"
        )


def build_campaign_three_execution_reservation(
    *,
    request: CampaignThreeDevelopmentAccessRequestV1,
    grant: CampaignThreeDevelopmentAccessGrantV1,
    execution_kind: CampaignThreeDevelopmentExecutionKind,
    run_created_at: datetime,
    reserved_at: datetime,
    output_root_fingerprint: str,
    formal_completion: CampaignThreeDevelopmentExecutionCompletionV1 | None = None,
) -> CampaignThreeDevelopmentExecutionReservationV1:
    validate_campaign_three_development_grant(request=request, grant=grant)
    if not _is_utc(run_created_at) or not _is_utc(reserved_at):
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development execution timestamps must use UTC"
        )
    if reserved_at < grant.granted_at:
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development execution chronology differs"
        )
    if execution_kind is CampaignThreeDevelopmentExecutionKind.FORMAL:
        if formal_completion is not None:
            raise CampaignThreeDevelopmentAccessError(
                "Campaign Three formal execution cannot bind a prior result"
            )
        formal_sha = None
        formal_fingerprint = None
    else:
        if (
            formal_completion is None
            or formal_completion.execution_kind
            is not CampaignThreeDevelopmentExecutionKind.FORMAL
        ):
            raise CampaignThreeDevelopmentAccessError(
                "Campaign Three replay requires a completed formal execution"
            )
        formal_sha = formal_completion.report_sha256
        formal_fingerprint = formal_completion.report_fingerprint
    payload: dict[str, object] = {
        "execution_kind": execution_kind,
        "request_fingerprint": request.logical_fingerprint,
        "grant_fingerprint": grant.logical_fingerprint,
        "protocol_fingerprint": request.protocol_fingerprint,
        "ledger_fingerprint": request.ledger_fingerprint,
        "implementation_revision": request.implementation_revision,
        "run_created_at": run_created_at,
        "reserved_at": reserved_at,
        "output_root_fingerprint": output_root_fingerprint,
        "expected_formal_report_sha256": formal_sha,
        "expected_formal_report_fingerprint": formal_fingerprint,
    }
    provisional = CampaignThreeDevelopmentExecutionReservationV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeDevelopmentExecutionReservationV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_access_fingerprint(provisional),
        }
    )


def build_campaign_three_execution_completion(
    *,
    reservation: CampaignThreeDevelopmentExecutionReservationV1,
    report_sha256: str,
    report_fingerprint: str,
    completed_at: datetime,
) -> CampaignThreeDevelopmentExecutionCompletionV1:
    if not _is_utc(completed_at) or completed_at < reservation.reserved_at:
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development completion chronology differs"
        )
    if (
        reservation.execution_kind
        is CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY
        and (
            report_sha256 != reservation.expected_formal_report_sha256
            or report_fingerprint
            != reservation.expected_formal_report_fingerprint
        )
    ):
        raise CampaignThreeDevelopmentAccessError(
            "Campaign Three Development replay result differs from formal result"
        )
    payload: dict[str, object] = {
        "execution_kind": reservation.execution_kind,
        "reservation_fingerprint": reservation.logical_fingerprint,
        "report_sha256": report_sha256,
        "report_fingerprint": report_fingerprint,
        "completed_at": completed_at,
    }
    provisional = CampaignThreeDevelopmentExecutionCompletionV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeDevelopmentExecutionCompletionV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_access_fingerprint(provisional),
        }
    )


def development_access_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _is_utc(value: datetime) -> bool:
    return (
        value.tzinfo is not None
        and value.utcoffset() is not None
        and value.utcoffset().total_seconds() == 0
    )
