"""Typed one-run-plus-replay access boundary for Campaign Three Development."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
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
AUTHORIZATION_PREFIX = "I_AUTHORIZE_CAMPAIGN_THREE_DEVELOPMENT_SCREEN_"


class CampaignThreeDevelopmentAccessError(ValueError):
    pass


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


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
        if self.granted_at.tzinfo is None or self.granted_at.utcoffset() != timezone.utc.utcoffset(
            self.granted_at
        ):
            raise ValueError("Campaign Three Development grant must use UTC")
        if development_access_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Campaign Three Development access grant differs")
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
