"""Typed zero-outcome factor-space diagnostic contracts."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FACTOR_SPACE_DIAGNOSTIC_CONTRACT_VERSION = (
    "quant-research-factor-space-diagnostic/1.0"
)
FACTOR_SPACE_DIAGNOSTIC_PROTOCOL_VERSION = (
    "whalpha.us-factor-space-diagnostic/1.0.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FactorSpacePanelKind(StrEnum):
    SECURITY_CROSS_SECTION = "security_cross_section"
    MARKET_STATE_TIME_SERIES = "market_state_time_series"


class FactorSpaceVifStatus(StrEnum):
    AVAILABLE = "available"
    SINGULAR = "singular"


class FactorSpaceInputV1(FrozenModel):
    input_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    economic_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")


class FactorSpaceScaleV1(FrozenModel):
    input_id: str
    method: Literal[
        "same_session_midrank_then_development_scale",
        "development_median_mad",
        "development_median_std_fallback",
    ]
    available_count: int = Field(ge=0)
    location: str
    scale: str


class FactorSpacePairV1(FrozenModel):
    left_input_id: str
    right_input_id: str
    shared_count: int = Field(ge=0)
    both_missing_count: int = Field(ge=0)
    pearson: str
    rank_dependence: str


class FactorSpaceClusterMergeV1(FrozenModel):
    step: int = Field(ge=1)
    left_members: tuple[str, ...] = Field(min_length=1)
    right_members: tuple[str, ...] = Field(min_length=1)
    merged_members: tuple[str, ...] = Field(min_length=2)
    distance: str


class FactorSpaceVifV1(FrozenModel):
    input_id: str
    status: FactorSpaceVifStatus
    value: str | None = None

    @model_validator(mode="after")
    def value_matches_status(self) -> "FactorSpaceVifV1":
        if (self.status is FactorSpaceVifStatus.AVAILABLE) != (self.value is not None):
            raise ValueError("VIF value and status differ")
        return self


class FactorSpaceLoadingV1(FrozenModel):
    input_id: str
    loading: str


class FactorSpaceComponentV1(FrozenModel):
    component: int = Field(ge=1)
    eigenvalue: str
    explained_variance_ratio: str
    cumulative_explained_variance_ratio: str
    loadings: tuple[FactorSpaceLoadingV1, ...] = Field(min_length=1)


class FactorSpaceDimensionV1(FrozenModel):
    numerical_rank: int = Field(ge=0)
    participation_ratio: str
    kaiser_count: int = Field(ge=0)
    components_80: int = Field(ge=0)
    components_90: int = Field(ge=0)
    components_95: int = Field(ge=0)
    condition_status: Literal["available", "singular"]
    condition_number: str | None = None

    @model_validator(mode="after")
    def condition_matches_status(self) -> "FactorSpaceDimensionV1":
        if (self.condition_status == "available") != (
            self.condition_number is not None
        ):
            raise ValueError("condition value and status differ")
        return self


class FactorSpacePanelReportV1(FrozenModel):
    panel: FactorSpacePanelKind
    inputs: tuple[FactorSpaceInputV1, ...] = Field(min_length=2)
    row_count: int = Field(ge=1)
    complete_case_count: int = Field(ge=1)
    complete_case_share: str
    scales: tuple[FactorSpaceScaleV1, ...] = Field(min_length=2)
    pairs: tuple[FactorSpacePairV1, ...] = Field(min_length=1)
    cluster_merges: tuple[FactorSpaceClusterMergeV1, ...] = Field(min_length=1)
    vifs: tuple[FactorSpaceVifV1, ...] = Field(min_length=2)
    components: tuple[FactorSpaceComponentV1, ...] = Field(min_length=2)
    dimension: FactorSpaceDimensionV1

    @model_validator(mode="after")
    def panel_reconciles(self) -> "FactorSpacePanelReportV1":
        ids = tuple(item.input_id for item in self.inputs)
        count = len(ids)
        if (
            ids != tuple(dict.fromkeys(ids))
            or self.complete_case_count > self.row_count
            or tuple(item.input_id for item in self.scales) != ids
            or tuple(item.input_id for item in self.vifs) != ids
            or len(self.pairs) != count * (count - 1) // 2
            or len(self.cluster_merges) != count - 1
            or len(self.components) != count
            or any(tuple(item.input_id for item in component.loadings) != ids for component in self.components)
        ):
            raise ValueError("factor-space panel shape differs")
        return self


class FactorSpaceSourceBindingV1(FrozenModel):
    source_name: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class QuantResearchFactorSpaceDiagnosticV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[FACTOR_SPACE_DIAGNOSTIC_CONTRACT_VERSION] = (
        FACTOR_SPACE_DIAGNOSTIC_CONTRACT_VERSION
    )
    protocol_version: Literal[FACTOR_SPACE_DIAGNOSTIC_PROTOCOL_VERSION] = (
        FACTOR_SPACE_DIAGNOSTIC_PROTOCOL_VERSION
    )
    source_bindings: tuple[FactorSpaceSourceBindingV1, ...] = Field(min_length=1)
    panels: tuple[FactorSpacePanelReportV1, FactorSpacePanelReportV1]
    external_request_count: Literal[0] = 0
    development_outcome_read_count: Literal[0] = 0
    validation_read_count: Literal[0] = 0
    holdout_read_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    alpha_claim_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "QuantResearchFactorSpaceDiagnosticV1":
        if (
            tuple(item.panel for item in self.panels)
            != (
                FactorSpacePanelKind.SECURITY_CROSS_SECTION,
                FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
            )
            or tuple(item.source_name for item in self.source_bindings)
            != tuple(sorted({item.source_name for item in self.source_bindings}))
            or factor_space_diagnostic_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("factor-space report differs")
        return self


def factor_space_diagnostic_fingerprint(value: BaseModel | dict[str, object]) -> str:
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
        ).encode("utf-8")
    ).hexdigest()
