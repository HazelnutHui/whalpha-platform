"""Outcome-blind full-population A-share cross-family coverage diagnostic."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from functools import lru_cache
from typing import Any, Literal, Mapping

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    CHINA_ASHARE_FOUNDATION_FAMILY_ORDER,
    MARKET_ID,
    ChinaAshareFoundationFamily,
    FrozenContract,
)
from tip_api.contracts.common import normalize_utc_datetime


FULL_POPULATION_COVERAGE_VERSION = "china-ashare-full-population-coverage/1.0"
FULL_POPULATION_DIAGNOSTIC_PLAN_VERSION = (
    "china-ashare-full-population-diagnostic-plan/1.0"
)
FULL_POPULATION_PARTITION_AGGREGATE_VERSION = (
    "china-ashare-full-population-partition-aggregate/1.0"
)
FULL_POPULATION_STREAMING_AGGREGATE_VERSION = (
    "china-ashare-full-population-streaming-aggregate/1.0"
)
FULL_POPULATION_DIAGNOSTIC_PACKAGE_VERSION = (
    "china-ashare-full-population-diagnostic-package/1.0"
)
POPULATION_PACKAGE_FINGERPRINT = (
    "13595c0645aa36acc5fea8d818509b484582ad13d7def53d377b984d549c02c0"
)
SOURCE_COMPLETION_FINGERPRINT = (
    "833f79859b411f0422c4c1e9c0cbf2898dbe59df52c005ff17d546b56af7aab2"
)
NORMALIZED_RUN_FINGERPRINT = (
    "a7d24928a464b20632c44d6c92ac7aea3b99bfc22e077ced13073781c63682b4"
)


class CoverageDisposition(StrEnum):
    SOURCE_COMPLETE = "source_complete"
    PROVISIONAL_RECONSTRUCTION_ONLY = "provisional_reconstruction_only"
    BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"


class ChinaAshareFullPopulationDiagnosticPlanV1(FrozenContract):
    """Frozen input bindings for an outcome-blind, offline coverage pass."""

    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-full-population-diagnostic-plan/1.0"
    ] = FULL_POPULATION_DIAGNOSTIC_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    registered_at: datetime
    interval_start: date
    interval_end: date
    target_session_count: int = Field(ge=1)
    target_count: int = Field(ge=1)
    population_package_fingerprint: str
    source_plan_fingerprint: str
    source_completion_fingerprint: str
    normalized_run_fingerprint: str
    source_partition_manifest_fingerprints: tuple[str, ...] = Field(min_length=1)
    normalized_partition_manifest_fingerprints: tuple[str, ...] = Field(min_length=1)
    required_families: tuple[ChinaAshareFoundationFamily, ...] = (
        CHINA_ASHARE_FOUNDATION_FAMILY_ORDER
    )
    future_return_read_count: Literal[0] = 0
    full_universe_rows_materialized: Literal[False] = False
    adjusted_return_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("registered_at")
    @classmethod
    def registered_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "population_package_fingerprint",
        "source_plan_fingerprint",
        "source_completion_fingerprint",
        "normalized_run_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def scalar_fingerprints_are_sha256(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)

    @field_validator(
        "source_partition_manifest_fingerprints",
        "normalized_partition_manifest_fingerprints",
        mode="before",
    )
    @classmethod
    def partition_fingerprints_are_ordered(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("partition fingerprints must be an ordered collection")
        normalized = tuple(_sha256(item, "partition_fingerprint") for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError("partition fingerprints must be unique")
        return normalized

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareFullPopulationDiagnosticPlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("diagnostic interval is reversed")
        if len(self.source_partition_manifest_fingerprints) != len(
            self.normalized_partition_manifest_fingerprints
        ):
            raise ValueError("source and normalized partition sets differ")
        if self.required_families != CHINA_ASHARE_FOUNDATION_FAMILY_ORDER:
            raise ValueError("diagnostic foundation family order differs")
        if full_population_diagnostic_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("full-population diagnostic plan fingerprint differs")
        return self


class ChinaAshareFullPopulationPartitionAggregateV1(FrozenContract):
    """Bounded counters derived from exactly one normalized partition."""

    schema_version: Literal["1.0"] = "1.0"
    aggregate_version: Literal[
        "china-ashare-full-population-partition-aggregate/1.0"
    ] = FULL_POPULATION_PARTITION_AGGREGATE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    partition_index: int = Field(ge=0)
    source_partition_manifest_fingerprint: str
    normalized_partition_manifest_fingerprint: str
    target_count: int = Field(ge=1)
    resolved_target_count: int = Field(ge=0)
    quarantined_target_count: int = Field(ge=0)
    bar_count: int = Field(ge=0)
    state_count: int = Field(ge=0)
    adjustment_count: int = Field(ge=0)
    trading_state_count: int = Field(ge=0)
    suspended_state_count: int = Field(ge=0)
    resumed_state_count: int = Field(ge=0)
    not_listed_state_count: int = Field(ge=0)
    unknown_trading_state_count: int = Field(ge=0)
    risk_warning_none_count: int = Field(ge=0)
    risk_warning_present_unspecified_count: int = Field(ge=0)
    risk_warning_detailed_count: int = Field(ge=0)
    risk_warning_unknown_count: int = Field(ge=0)
    price_limit_unknown_count: int = Field(ge=0)
    source_available_at_null_state_count: int = Field(ge=0)
    adjustment_first_observation_count: int = Field(ge=0)
    adjustment_changed_observation_count: int = Field(ge=0)
    adjustment_noop_observation_count: int = Field(ge=0)
    first_state_session: date | None = None
    last_state_session: date | None = None
    full_universe_rows_materialized: Literal[False] = False
    future_return_read_count: Literal[0] = 0
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "source_partition_manifest_fingerprint",
        "normalized_partition_manifest_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def fingerprints_are_sha256(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def aggregate_reconciles(
        self,
    ) -> "ChinaAshareFullPopulationPartitionAggregateV1":
        if self.resolved_target_count + self.quarantined_target_count != self.target_count:
            raise ValueError("partition aggregate target counts differ")
        if sum(
            (
                self.trading_state_count,
                self.suspended_state_count,
                self.resumed_state_count,
                self.not_listed_state_count,
                self.unknown_trading_state_count,
            )
        ) != self.state_count:
            raise ValueError("partition aggregate trading-state counts differ")
        if sum(
            (
                self.risk_warning_none_count,
                self.risk_warning_present_unspecified_count,
                self.risk_warning_detailed_count,
                self.risk_warning_unknown_count,
            )
        ) != self.state_count:
            raise ValueError("partition aggregate risk-warning counts differ")
        if sum(
            (
                self.adjustment_first_observation_count,
                self.adjustment_changed_observation_count,
                self.adjustment_noop_observation_count,
            )
        ) != self.adjustment_count:
            raise ValueError("partition aggregate adjustment counts differ")
        if self.source_available_at_null_state_count > self.state_count:
            raise ValueError("partition aggregate null source times exceed states")
        if self.price_limit_unknown_count > self.state_count:
            raise ValueError("partition aggregate unknown limits exceed states")
        if (self.first_state_session is None) != (self.last_state_session is None):
            raise ValueError("partition aggregate state-date bounds differ")
        if (
            self.first_state_session is not None
            and self.last_state_session is not None
            and self.last_state_session < self.first_state_session
        ):
            raise ValueError("partition aggregate state-date bounds are reversed")
        if full_population_partition_aggregate_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("full-population partition aggregate fingerprint differs")
        return self


class ChinaAshareFullPopulationStreamingAggregateV1(FrozenContract):
    """Deterministic merge of ordered, independently bounded partitions."""

    schema_version: Literal["1.0"] = "1.0"
    aggregate_version: Literal[
        "china-ashare-full-population-streaming-aggregate/1.0"
    ] = FULL_POPULATION_STREAMING_AGGREGATE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    partition_aggregate_fingerprints: tuple[str, ...] = Field(min_length=1)
    target_count: int = Field(ge=1)
    resolved_target_count: int = Field(ge=0)
    quarantined_target_count: int = Field(ge=0)
    bar_count: int = Field(ge=0)
    state_count: int = Field(ge=0)
    adjustment_count: int = Field(ge=0)
    suspended_state_count: int = Field(ge=0)
    risk_warning_present_unspecified_count: int = Field(ge=0)
    price_limit_unknown_count: int = Field(ge=0)
    source_available_at_null_state_count: int = Field(ge=0)
    adjustment_first_observation_count: int = Field(ge=0)
    adjustment_changed_observation_count: int = Field(ge=0)
    adjustment_noop_observation_count: int = Field(ge=0)
    full_universe_rows_materialized: Literal[False] = False
    future_return_read_count: Literal[0] = 0
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "logical_fingerprint")
    @classmethod
    def aggregate_fingerprints_are_sha256(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)

    @field_validator("partition_aggregate_fingerprints", mode="before")
    @classmethod
    def aggregate_partition_fingerprints_are_ordered(
        cls, value: Any
    ) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("partition aggregate fingerprints must be ordered")
        normalized = tuple(_sha256(item, "partition_aggregate_fingerprint") for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError("partition aggregate fingerprints must be unique")
        return normalized

    @model_validator(mode="after")
    def streaming_aggregate_reconciles(
        self,
    ) -> "ChinaAshareFullPopulationStreamingAggregateV1":
        if self.resolved_target_count + self.quarantined_target_count != self.target_count:
            raise ValueError("streaming aggregate target counts differ")
        if sum(
            (
                self.adjustment_first_observation_count,
                self.adjustment_changed_observation_count,
                self.adjustment_noop_observation_count,
            )
        ) != self.adjustment_count:
            raise ValueError("streaming aggregate adjustment counts differ")
        if full_population_streaming_aggregate_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("full-population streaming aggregate fingerprint differs")
        return self


class ChinaAshareFullPopulationDiagnosticPackageManifestV1(FrozenContract):
    """Closed-set physical custody binding for one plan's small aggregates."""

    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-full-population-diagnostic-package/1.0"
    ] = FULL_POPULATION_DIAGNOSTIC_PACKAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    created_at: datetime
    partition_count: int = Field(ge=1)
    partition_document_bytes: int = Field(ge=1)
    partition_document_sha256: str
    streaming_aggregate_fingerprint: str
    streaming_document_bytes: int = Field(ge=1)
    streaming_document_sha256: str
    full_universe_rows_materialized: Literal[False] = False
    future_return_read_count: Literal[0] = 0
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("created_at")
    @classmethod
    def created_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "plan_fingerprint",
        "partition_document_sha256",
        "streaming_aggregate_fingerprint",
        "streaming_document_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def manifest_fingerprints_are_sha256(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def package_manifest_reconciles(
        self,
    ) -> "ChinaAshareFullPopulationDiagnosticPackageManifestV1":
        if full_population_diagnostic_package_manifest_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("full-population diagnostic package fingerprint differs")
        return self


class ChinaAshareCoverageFamilyV1(FrozenContract):
    ordinal: int = Field(ge=1, le=13)
    family_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    disposition: CoverageDisposition
    current_evidence: str
    blocking_gap: str | None = None
    next_offline_action: str | None = None
    external_evidence_required: bool
    authorizes_backtest: Literal[False] = False


def build_full_population_diagnostic_plan(
    **values: Any,
) -> ChinaAshareFullPopulationDiagnosticPlanV1:
    provisional = ChinaAshareFullPopulationDiagnosticPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationDiagnosticPlanV1.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": full_population_diagnostic_plan_fingerprint(
                provisional
            ),
        }
    )


def build_full_population_partition_aggregate(
    **values: Any,
) -> ChinaAshareFullPopulationPartitionAggregateV1:
    provisional = ChinaAshareFullPopulationPartitionAggregateV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationPartitionAggregateV1.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": full_population_partition_aggregate_fingerprint(
                provisional
            ),
        }
    )


def build_full_population_streaming_aggregate(
    **values: Any,
) -> ChinaAshareFullPopulationStreamingAggregateV1:
    provisional = ChinaAshareFullPopulationStreamingAggregateV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationStreamingAggregateV1.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": full_population_streaming_aggregate_fingerprint(
                provisional
            ),
        }
    )


def build_full_population_diagnostic_package_manifest(
    **values: Any,
) -> ChinaAshareFullPopulationDiagnosticPackageManifestV1:
    provisional = ChinaAshareFullPopulationDiagnosticPackageManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationDiagnosticPackageManifestV1.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": (
                full_population_diagnostic_package_manifest_fingerprint(provisional)
            ),
        }
    )


def full_population_diagnostic_plan_fingerprint(
    value: ChinaAshareFullPopulationDiagnosticPlanV1 | Mapping[str, object],
) -> str:
    return _fingerprint(value, exclude={"logical_fingerprint"})


def full_population_partition_aggregate_fingerprint(
    value: ChinaAshareFullPopulationPartitionAggregateV1 | Mapping[str, object],
) -> str:
    return _fingerprint(value, exclude={"logical_fingerprint"})


def full_population_streaming_aggregate_fingerprint(
    value: ChinaAshareFullPopulationStreamingAggregateV1 | Mapping[str, object],
) -> str:
    return _fingerprint(value, exclude={"logical_fingerprint"})


def full_population_diagnostic_package_manifest_fingerprint(
    value: (
        ChinaAshareFullPopulationDiagnosticPackageManifestV1
        | Mapping[str, object]
    ),
) -> str:
    return _fingerprint(value, exclude={"logical_fingerprint"})


class ChinaAshareFullPopulationCoverageReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-full-population-coverage/1.0"
    ] = FULL_POPULATION_COVERAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    evaluated_date: date = date(2026, 9, 17)
    scope: Literal["sse_szse_frozen_five_year_acquisition_population"] = (
        "sse_szse_frozen_five_year_acquisition_population"
    )
    population_package_fingerprint: Literal[POPULATION_PACKAGE_FINGERPRINT] = (
        POPULATION_PACKAGE_FINGERPRINT
    )
    source_completion_fingerprint: Literal[SOURCE_COMPLETION_FINGERPRINT] = (
        SOURCE_COMPLETION_FINGERPRINT
    )
    normalized_run_fingerprint: Literal[NORMALIZED_RUN_FINGERPRINT] = (
        NORMALIZED_RUN_FINGERPRINT
    )
    partition_count: Literal[109] = 109
    target_count: Literal[5409] = 5409
    resolved_target_count: Literal[5296] = 5296
    quarantined_target_count: Literal[113] = 113
    normalized_state_count: Literal[5997301] = 5997301
    normalized_bar_count: Literal[5987288] = 5987288
    normalized_adjustment_observation_count: Literal[62272] = 62272
    suspended_state_count: Literal[10013] = 10013
    risk_warning_present_unspecified_count: Literal[160626] = 160626
    price_limit_regime_unknown_count: Literal[5997301] = 5997301
    source_available_at_null_count: Literal[5997301] = 5997301
    resolved_window_listing_count: Literal[930] = 930
    resolved_delisted_occurrence_count: Literal[76] = 76
    terminal_boundary_occurrence_gap_count: Literal[22] = 22
    terminal_boundary_session_gap_count: Literal[23] = 23
    families: tuple[ChinaAshareCoverageFamilyV1, ...] = Field(
        min_length=13, max_length=13
    )
    source_acquisition_complete: Literal[True] = True
    normalization_complete: Literal[True] = True
    full_market_claim_authorized: Literal[False] = False
    historical_coverage_admitted: Literal[False] = False
    adjusted_return_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("evaluated_date")
    @classmethod
    def evaluated_date_is_frozen(cls, value: date) -> date:
        if value != date(2026, 9, 17):
            raise ValueError("A-share coverage evaluation date differs")
        return value

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareFullPopulationCoverageReportV1":
        if (
            self.resolved_target_count + self.quarantined_target_count
            != self.target_count
            or self.normalized_bar_count + self.suspended_state_count
            != self.normalized_state_count
            or self.price_limit_regime_unknown_count != self.normalized_state_count
            or self.source_available_at_null_count != self.normalized_state_count
            or tuple(item.ordinal for item in self.families) != tuple(range(1, 14))
            or len({item.family_id for item in self.families}) != 13
            or self.families != _families()
            or full_population_coverage_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("A-share full-population coverage report differs")
        return self


def full_population_coverage_fingerprint(
    value: ChinaAshareFullPopulationCoverageReportV1 | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, ChinaAshareFullPopulationCoverageReportV1)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _fingerprint(
    value: FrozenContract | Mapping[str, object], *, exclude: set[str]
) -> str:
    payload = (
        value.model_dump(mode="json", exclude=exclude)
        if isinstance(value, FrozenContract)
        else {key: item for key, item in value.items() if key not in exclude}
    )
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sha256(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized


@lru_cache(maxsize=1)
def china_ashare_full_population_coverage_report_v1() -> (
    ChinaAshareFullPopulationCoverageReportV1
):
    payload = {"families": _families()}
    provisional = ChinaAshareFullPopulationCoverageReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationCoverageReportV1.model_validate(
        {**payload, "logical_fingerprint": full_population_coverage_fingerprint(provisional)}
    )


@lru_cache(maxsize=1)
def _families() -> tuple[ChinaAshareCoverageFamilyV1, ...]:
    values = (
        (1, "instrument_identity", "provisional_reconstruction_only", "5,296 stable listed-occurrence identities; 113 quarantined targets retained separately.", "113 historical SZSE occurrences lack sufficient official board evidence.", "Freeze a resolved identity census and a separate official-evidence request queue.", True),
        (2, "trading_calendar", "provisional_reconstruction_only", "1,211 observed SSE/SZSE sessions plus existing annual official closure evidence.", "Full-population lifecycle-by-calendar reconciliation has not been materialized.", "Reconcile every resolved occurrence against the frozen session set and listing interval.", False),
        (3, "raw_unadjusted_eod", "source_complete", "5,987,288 normalized unadjusted bars and explicit quarantine custody.", "The 113 quarantined targets prevent a claim of complete admitted-market coverage.", "Run uniqueness, OHLC, bar/state, and lifecycle-boundary checks on resolved scope.", False),
        (4, "daily_price_limits", "blocked_missing_evidence", "All 5,997,301 normalized states retain price_limit_regime=unknown.", "IPO no-limit windows, old main-board IPO rules, and STAR/ChiNext risk-warning rules are not covered by the pilot rule set.", "Generate a rule-applicability gap census; obtain effective-dated official rule evidence before evaluation.", True),
        (5, "suspension_state", "provisional_reconstruction_only", "10,013 resolved suspension states and zero normalized unknown trading states.", "Provider observation is not the same as point-in-time official suspension-notice evidence.", "Reconcile state continuity offline and preserve reconstructed-evidence status.", True),
        (6, "risk_warning_state", "blocked_missing_evidence", "160,626 states are only present_unspecified.", "Effective-dated ST/*ST/delisting-risk subtypes and historical source clocks are absent.", "Build an official status-change evidence queue; do not infer subtype from names.", True),
        (7, "adjustment_factors", "blocked_missing_evidence", "62,272 provider adjustment observations retained with normalized_return_authorized=false.", "Provider factor steps do not prove corporate-action terms or total-return semantics.", "Deduplicate factor transitions into a candidate evidence registry for independent reconciliation.", True),
        (8, "corporate_actions", "blocked_missing_evidence", "Pilot evidence exists for six instruments only; no full-population event family is admitted.", "Cash, stock, rights, merger, and terminal consideration terms are not reconciled for the population.", "Acquire and reconcile independent CNINFO or exchange event terms for candidate transitions.", True),
        (9, "instrument_lifecycle", "provisional_reconstruction_only", "5,220 current and 76 delisted resolved occurrences; 930 listed inside the window.", "113 identities and 22 terminal occurrences with 23 boundary sessions remain unresolved.", "Create a full-population lifecycle contract supporting within-window listing and delisting.", True),
        (10, "daily_universe_membership", "blocked_missing_evidence", "No full-population daily decision artifact has been admitted.", "Identity, warning-state, price-limit, and lifecycle gaps prevent complete membership decisions.", "Materialize provisional decisions with dependency-driven quarantine only after the offline census.", False),
        (11, "effective_dated_trading_rules", "blocked_missing_evidence", "Ten pilot rules cover normal regimes and selected main-board warning states.", "Full-scope IPO and special-board rule intervals are incomplete.", "Run full-population rule selection to expose exact uncovered intervals, without filling gaps heuristically.", True),
        (12, "effective_dated_fees", "provisional_reconstruction_only", "Fourteen official statutory fee rules exist in the pilot package.", "Actual Ping An commission history, minimum commission, and account-specific terms remain assumptions.", "Extend statutory interval coverage offline and keep broker commission as an explicit scenario.", True),
        (13, "historical_coverage", "blocked_missing_evidence", "Source acquisition and normalization are complete for the frozen SSE/SZSE target list.", "The preceding family gaps prevent Historical Coverage admission.", "Publish and exactly replay this ordered family census; keep admission closed until blockers are resolved.", False),
    )
    return tuple(
        ChinaAshareCoverageFamilyV1(
            ordinal=ordinal,
            family_id=family_id,
            disposition=CoverageDisposition(disposition),
            current_evidence=evidence,
            blocking_gap=gap,
            next_offline_action=action,
            external_evidence_required=external,
        )
        for ordinal, family_id, disposition, evidence, gap, action, external in values
    )
