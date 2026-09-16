"""Registered reusable artifacts after market-state qualification."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_reusable_artifacts import (
    QuantResearchArtifactKind,
    QuantResearchReusableArtifactDescriptorV1,
    QuantResearchReusableArtifactIdentityV1,
    quant_research_reusable_artifact_registry_v1,
    reusable_artifact_identity_fingerprint,
)


QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_CONTRACT_VERSION = (
    "quant-research-reusable-artifact-registry/2.0"
)
QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_VERSION = (
    "whalpha.quant-research-reusable-artifacts/2.0.0"
)
MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT = (
    "20b496eb76ba6597b6937bf2e79924a65491631767e7e1c4ac186281bba04ee3"
)
MARKET_STATE_QUALIFICATION_REPORT_SHA256 = (
    "8f3ec454b2626b3a2feab79e8f38e3ae014c0d853e7698d9266a32dca224b02a"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchReusableArtifactRegistryV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_CONTRACT_VERSION
    registry_version: Literal[
        QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_VERSION
    ] = QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_V2_VERSION
    accepted_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    implementation_status: Literal[
        "market_state_registered_outcomes_closed"
    ] = "market_state_registered_outcomes_closed"
    prior_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_market_state_qualification_report_fingerprint: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    ] = MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    source_market_state_qualification_report_sha256: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_SHA256
    ] = MARKET_STATE_QUALIFICATION_REPORT_SHA256
    materialized_artifacts: tuple[
        QuantResearchReusableArtifactDescriptorV1, ...
    ] = Field(min_length=1, max_length=1)
    materialized_artifact_count: Literal[1] = 1
    materialized_market_state_artifact_count: Literal[1] = 1
    materialized_population_artifact_count: Literal[0] = 0
    materialized_feature_matrix_artifact_count: Literal[0] = 0
    materialized_nuisance_control_artifact_count: Literal[0] = 0
    materialized_outcome_label_artifact_count: Literal[0] = 0
    active_campaign_id: None = None
    next_campaign_registered: Literal[False] = False
    new_outcome_access_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    cleanup_or_deletion_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def registry_reconciles(self) -> "QuantResearchReusableArtifactRegistryV2":
        prior = quant_research_reusable_artifact_registry_v1()
        expected = _registered_market_state_artifact()
        if (
            self.prior_registry_fingerprint != prior.logical_fingerprint
            or self.materialized_artifacts != (expected,)
            or self.materialized_artifact_count != len(self.materialized_artifacts)
            or reusable_artifact_registry_v2_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("registered reusable-artifact state differs")
        return self


def reusable_artifact_registry_v2_fingerprint(
    value: BaseModel | dict[str, object],
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


@lru_cache(maxsize=1)
def quant_research_reusable_artifact_registry_v2() -> (
    QuantResearchReusableArtifactRegistryV2
):
    payload: dict[str, object] = {
        "prior_registry_fingerprint": (
            quant_research_reusable_artifact_registry_v1().logical_fingerprint
        ),
        "materialized_artifacts": (_registered_market_state_artifact(),),
    }
    provisional = QuantResearchReusableArtifactRegistryV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchReusableArtifactRegistryV2.model_validate(
        {
            **payload,
            "logical_fingerprint": reusable_artifact_registry_v2_fingerprint(
                provisional
            ),
        }
    )


@lru_cache(maxsize=1)
def _registered_market_state_artifact() -> (
    QuantResearchReusableArtifactDescriptorV1
):
    identity = QuantResearchReusableArtifactIdentityV1(
        artifact_kind=QuantResearchArtifactKind.MARKET_STATE,
        source_logical_fingerprints=(
            "09ffe4edc38aeaccb3f101f5b1b784eb0769af0de9fde0c28fafbc18fe32388f",
            "233c9661f96d133d096daa404df07a67e0b9a5fc3de86f5b935f1a227531ce5c",
            "477b45a7013918eb926d62a2c96dc66417fb7775f4ed692ea9b46210350c724d",
            "e1b562cb384e33badc9ec193322e5c3a4894d20f1323066bac72044c66a93b93",
        ),
        source_contract_versions=(
            "quant-research-historical-split-extension/1.0",
            "quant-research-market-state-vector/1.1",
            "reconciled-eod-price-bar-edition-session/1.2",
            "strong-leader-pullback-development-coverage-census/1.0",
            "universe-membership-partition-manifest/1.1",
        ),
        stable_universe_fingerprint=(
            "4c4a15f1ff78d43a05d2b074627d3777ea0391a7fa4ff1490c59ba3c511b44dc"
        ),
        knowledge_time_cutoff=(
            "completed_session_close_each_row_earliest_next_open"
        ),
        session_partition_fingerprint=(
            "1d2151281b6ed45c352294529d544d58bb5e41c19798a73a0ef5d72fc54c1eff"
        ),
        calculation_code_sha256=(
            "ebe4ae3d31b241917554252f6a4be56245213833159042ac68dc11b9d3ebb82f"
        ),
        parameter_fingerprint=(
            "c74831d225a87f7b5389e15f2f78b35a358ad6d9aedcfccf5464b3182a51bd9a"
        ),
        upstream_artifact_fingerprints=(
            "28148726fa8bf6f91358b0d1470b24573d88f0590241e85050b509f5db360c88",
        ),
    )
    return QuantResearchReusableArtifactDescriptorV1(
        identity=identity,
        identity_fingerprint=reusable_artifact_identity_fingerprint(identity),
        content_sha256=(
            "a670fb106b559a3b363da8aae0d3c85a8076fd8b0b5952c52537a859e0b1e537"
        ),
        record_count=287,
        first_session=date(2025, 6, 23),
        last_session=date(2026, 8, 12),
    )
