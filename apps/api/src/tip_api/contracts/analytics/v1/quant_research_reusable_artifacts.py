"""Content-addressed reusable research-artifact boundaries for Factor Discovery."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_cycle import (
    QuantResearchDiscoveryStageId,
    quant_research_discovery_cycle_v1,
)


QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_CONTRACT_VERSION = (
    "quant-research-reusable-artifact-registry/1.0"
)
QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_VERSION = (
    "whalpha.quant-research-reusable-artifacts/1.0.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchArtifactKind(StrEnum):
    POPULATION = "population"
    MARKET_STATE = "market_state"
    FEATURE_MATRIX = "feature_matrix"
    NUISANCE_CONTROL = "nuisance_control"
    OUTCOME_LABEL = "outcome_label"


class QuantResearchArtifactCustody(StrEnum):
    OUTCOME_BLIND = "outcome_blind"
    OUTCOME_BEARING = "outcome_bearing"


class QuantResearchArtifactRetention(StrEnum):
    REUSABLE_DERIVED = "reusable_derived"
    RESTRICTED_REUSABLE_DERIVED = "restricted_reusable_derived"


class QuantResearchReusableArtifactIdentityV1(FrozenModel):
    """Every field that must match before an existing panel can be reused."""

    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: QuantResearchArtifactKind
    source_logical_fingerprints: tuple[str, ...] = Field(min_length=1)
    source_contract_versions: tuple[str, ...] = Field(min_length=1)
    stable_universe_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    knowledge_time_cutoff: str = Field(min_length=1, max_length=160)
    session_partition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    upstream_artifact_fingerprints: tuple[str, ...] = ()

    @model_validator(mode="after")
    def identity_is_canonical(self) -> "QuantResearchReusableArtifactIdentityV1":
        fingerprint_groups = (
            self.source_logical_fingerprints,
            self.upstream_artifact_fingerprints,
        )
        if any(
            tuple(values) != tuple(sorted(set(values)))
            or any(len(value) != 64 or set(value) - set("0123456789abcdef") for value in values)
            for values in fingerprint_groups
        ):
            raise ValueError("artifact fingerprint collections must be sorted and unique")
        if self.source_contract_versions != tuple(
            sorted(set(self.source_contract_versions))
        ):
            raise ValueError("source contract versions must be sorted and unique")
        return self


class QuantResearchReusableArtifactDescriptorV1(FrozenModel):
    identity: QuantResearchReusableArtifactIdentityV1
    identity_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=0)
    first_session: date | None = None
    last_session: date | None = None

    @model_validator(mode="after")
    def descriptor_reconciles(self) -> "QuantResearchReusableArtifactDescriptorV1":
        if self.identity_fingerprint != reusable_artifact_identity_fingerprint(
            self.identity
        ):
            raise ValueError("artifact identity fingerprint differs")
        if (self.first_session is None) != (self.last_session is None):
            raise ValueError("artifact session bounds must both be present or absent")
        if (
            self.first_session is not None
            and self.last_session is not None
            and self.first_session > self.last_session
        ):
            raise ValueError("artifact session bounds are reversed")
        return self


class QuantResearchArtifactFamilyPolicyV1(FrozenModel):
    artifact_kind: QuantResearchArtifactKind
    custody: QuantResearchArtifactCustody
    retention: QuantResearchArtifactRetention
    permitted_row_access_stages: tuple[QuantResearchDiscoveryStageId, ...] = Field(
        min_length=1
    )
    exact_identity_match_required: Literal[True] = True
    mismatch_action: Literal["build_new_immutable_version_never_mutate"] = (
        "build_new_immutable_version_never_mutate"
    )
    compact_summary_default: Literal[True] = True
    registered_campaign_required: bool


class QuantResearchReusableArtifactRegistryV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_CONTRACT_VERSION
    ] = QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_CONTRACT_VERSION
    registry_version: Literal[
        QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_VERSION
    ] = QUANT_RESEARCH_REUSABLE_ARTIFACT_REGISTRY_VERSION
    accepted_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    implementation_status: Literal["contract_ready_not_materialized"] = (
        "contract_ready_not_materialized"
    )
    source_cycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_completed_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_families: tuple[QuantResearchArtifactFamilyPolicyV1, ...] = Field(
        min_length=5, max_length=5
    )
    identity_dimensions: tuple[
        Literal[
            "source_logical_fingerprints",
            "source_contract_versions",
            "stable_universe_fingerprint",
            "knowledge_time_cutoff",
            "session_partition_fingerprint",
            "calculation_code_sha256",
            "parameter_fingerprint",
            "upstream_artifact_fingerprints",
        ],
        ...,
    ] = Field(min_length=8, max_length=8)
    materialized_artifact_count: Literal[0] = 0
    active_campaign_id: None = None
    next_campaign_registered: Literal[False] = False
    new_outcome_access_authorized: Literal[False] = False
    physical_data_write_authorized: Literal[False] = False
    cleanup_or_deletion_authorized: Literal[False] = False
    new_database_or_service_required: Literal[False] = False
    parallelism_rule: Literal[
        "profile_first_then_bounded_process_parallelism_with_stable_order"
    ] = "profile_first_then_bounded_process_parallelism_with_stable_order"
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def registry_reconciles(self) -> "QuantResearchReusableArtifactRegistryV1":
        cycle = quant_research_discovery_cycle_v1()
        if (
            self.source_cycle_fingerprint != cycle.logical_fingerprint
            or self.source_completed_ledger_fingerprint
            != cycle.source_completed_ledger_fingerprint
            or self.artifact_families != _artifact_family_policies()
            or tuple(item.artifact_kind for item in self.artifact_families)
            != tuple(QuantResearchArtifactKind)
            or len(set(self.identity_dimensions)) != 8
            or reusable_artifact_registry_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("reusable research-artifact registry differs from governed state")
        return self


def reusable_artifact_identity_fingerprint(
    value: QuantResearchReusableArtifactIdentityV1 | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return _fingerprint(payload)


def reusable_artifact_registry_fingerprint(
    value: BaseModel | dict[str, object],
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = {
            key: item for key, item in value.items() if key != "logical_fingerprint"
        }
    return _fingerprint(payload)


def reusable_artifact_exact_match(
    requested: QuantResearchReusableArtifactIdentityV1,
    existing: QuantResearchReusableArtifactDescriptorV1,
) -> bool:
    return reusable_artifact_identity_fingerprint(requested) == (
        existing.identity_fingerprint
    )


@lru_cache(maxsize=1)
def quant_research_reusable_artifact_registry_v1() -> (
    QuantResearchReusableArtifactRegistryV1
):
    cycle = quant_research_discovery_cycle_v1()
    payload: dict[str, object] = {
        "source_cycle_fingerprint": cycle.logical_fingerprint,
        "source_completed_ledger_fingerprint": (
            cycle.source_completed_ledger_fingerprint
        ),
        "artifact_families": _artifact_family_policies(),
        "identity_dimensions": (
            "source_logical_fingerprints",
            "source_contract_versions",
            "stable_universe_fingerprint",
            "knowledge_time_cutoff",
            "session_partition_fingerprint",
            "calculation_code_sha256",
            "parameter_fingerprint",
            "upstream_artifact_fingerprints",
        ),
    }
    provisional = QuantResearchReusableArtifactRegistryV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchReusableArtifactRegistryV1.model_validate(
        {
            **payload,
            "logical_fingerprint": reusable_artifact_registry_fingerprint(provisional),
        }
    )


def _artifact_family_policies() -> tuple[QuantResearchArtifactFamilyPolicyV1, ...]:
    blind_stages = (
        QuantResearchDiscoveryStageId.DATA_ADMISSION,
        QuantResearchDiscoveryStageId.OUTCOME_BLIND_QUALIFICATION,
        QuantResearchDiscoveryStageId.PROTOCOL_PREREGISTRATION,
        QuantResearchDiscoveryStageId.DEVELOPMENT_SCREEN,
        QuantResearchDiscoveryStageId.INDEPENDENT_REPLAY_AND_RED_TEAM,
    )
    feature_stages = blind_stages[1:]
    outcome_stages = (
        QuantResearchDiscoveryStageId.DEVELOPMENT_SCREEN,
        QuantResearchDiscoveryStageId.INDEPENDENT_REPLAY_AND_RED_TEAM,
    )
    return (
        QuantResearchArtifactFamilyPolicyV1(
            artifact_kind=QuantResearchArtifactKind.POPULATION,
            custody=QuantResearchArtifactCustody.OUTCOME_BLIND,
            retention=QuantResearchArtifactRetention.REUSABLE_DERIVED,
            permitted_row_access_stages=blind_stages,
            registered_campaign_required=False,
        ),
        QuantResearchArtifactFamilyPolicyV1(
            artifact_kind=QuantResearchArtifactKind.MARKET_STATE,
            custody=QuantResearchArtifactCustody.OUTCOME_BLIND,
            retention=QuantResearchArtifactRetention.REUSABLE_DERIVED,
            permitted_row_access_stages=feature_stages,
            registered_campaign_required=False,
        ),
        QuantResearchArtifactFamilyPolicyV1(
            artifact_kind=QuantResearchArtifactKind.FEATURE_MATRIX,
            custody=QuantResearchArtifactCustody.OUTCOME_BLIND,
            retention=QuantResearchArtifactRetention.REUSABLE_DERIVED,
            permitted_row_access_stages=feature_stages,
            registered_campaign_required=False,
        ),
        QuantResearchArtifactFamilyPolicyV1(
            artifact_kind=QuantResearchArtifactKind.NUISANCE_CONTROL,
            custody=QuantResearchArtifactCustody.OUTCOME_BEARING,
            retention=QuantResearchArtifactRetention.RESTRICTED_REUSABLE_DERIVED,
            permitted_row_access_stages=outcome_stages,
            registered_campaign_required=True,
        ),
        QuantResearchArtifactFamilyPolicyV1(
            artifact_kind=QuantResearchArtifactKind.OUTCOME_LABEL,
            custody=QuantResearchArtifactCustody.OUTCOME_BEARING,
            retention=QuantResearchArtifactRetention.RESTRICTED_REUSABLE_DERIVED,
            permitted_row_access_stages=outcome_stages,
            registered_campaign_required=True,
        ),
    )


def _fingerprint(payload: object) -> str:
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
