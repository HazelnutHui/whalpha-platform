"""Fail-closed dynamic gap checklist for the A-share population diagnostic."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract


FULL_POPULATION_GAP_CHECKLIST_VERSION = (
    "china-ashare-full-population-gap-checklist/1.0"
)


class ChinaAshareDynamicGapFamily(StrEnum):
    PRICE_LIMIT_RULES = "price_limit_rules"
    WARNING_STATE = "warning_state"
    CORPORATE_ACTION = "corporate_action"
    INSTRUMENT_LIFECYCLE = "instrument_lifecycle"
    HISTORICAL_UNIVERSE = "historical_universe"


CHINA_ASHARE_DYNAMIC_GAP_FAMILY_ORDER = tuple(ChinaAshareDynamicGapFamily)


class ChinaAshareDynamicGapMeasureV1(FrozenContract):
    measure_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    count: int = Field(ge=0)
    unit: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class ChinaAshareDynamicGapEntryV1(FrozenContract):
    ordinal: int = Field(ge=1, le=5)
    family: ChinaAshareDynamicGapFamily
    disposition: Literal["blocked_missing_evidence"] = "blocked_missing_evidence"
    measures: tuple[ChinaAshareDynamicGapMeasureV1, ...] = Field(min_length=1)
    blocker_codes: tuple[str, ...] = Field(min_length=1)
    external_official_evidence_required: Literal[True] = True
    admission_authorized: Literal[False] = False

    @field_validator("blocker_codes", mode="before")
    @classmethod
    def blockers_are_sorted_unique(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))) or any(
            not item or not item.replace("_", "").isalnum() for item in normalized
        ):
            raise ValueError("dynamic gap blocker codes differ")
        return normalized

    @model_validator(mode="after")
    def measures_are_unique(self) -> "ChinaAshareDynamicGapEntryV1":
        identifiers = tuple(item.measure_id for item in self.measures)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("dynamic gap measures are duplicated")
        return self


class ChinaAshareFullPopulationGapChecklistV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    checklist_version: Literal[
        "china-ashare-full-population-gap-checklist/1.0"
    ] = FULL_POPULATION_GAP_CHECKLIST_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    diagnostic_plan_fingerprint: str
    diagnostic_package_fingerprint: str
    streaming_aggregate_fingerprint: str
    partition_aggregate_fingerprints: tuple[str, ...] = Field(min_length=1)
    entries: tuple[ChinaAshareDynamicGapEntryV1, ...] = Field(
        min_length=5, max_length=5
    )
    admitted_family_count: Literal[0] = 0
    future_return_read_count: Literal[0] = 0
    full_universe_rows_materialized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    adjusted_return_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "diagnostic_plan_fingerprint",
        "diagnostic_package_fingerprint",
        "streaming_aggregate_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def scalar_hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("partition_aggregate_fingerprints", mode="before")
    @classmethod
    def partition_hashes_are_ordered(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("partition aggregate fingerprints must be ordered")
        normalized = tuple(
            _sha(item, "partition_aggregate_fingerprint") for item in value
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError("partition aggregate fingerprints are duplicated")
        return normalized

    @model_validator(mode="after")
    def checklist_is_closed(self) -> "ChinaAshareFullPopulationGapChecklistV1":
        if tuple(item.ordinal for item in self.entries) != tuple(range(1, 6)):
            raise ValueError("dynamic gap ordinals differ")
        if tuple(item.family for item in self.entries) != (
            CHINA_ASHARE_DYNAMIC_GAP_FAMILY_ORDER
        ):
            raise ValueError("dynamic gap family order differs")
        if full_population_gap_checklist_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("dynamic gap checklist fingerprint differs")
        return self


def build_full_population_gap_checklist(
    **values: Any,
) -> ChinaAshareFullPopulationGapChecklistV1:
    provisional = ChinaAshareFullPopulationGapChecklistV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationGapChecklistV1.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": full_population_gap_checklist_fingerprint(
                provisional
            ),
        }
    )


def full_population_gap_checklist_fingerprint(
    value: ChinaAshareFullPopulationGapChecklistV1,
) -> str:
    payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
