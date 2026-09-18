"""Bounded Massive Starter capability-sample contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


CONTRACT_VERSION = "quant-research-massive-starter-capability-sample/1.0"
MAXIMUM_REQUEST_COUNT = 10
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SampleKind(StrEnum):
    SINGLE_COMMON = "single_common"
    TICKER_CHANGE = "ticker_change"
    MULTI_COMMON = "multi_common"


class RequestKind(StrEnum):
    CURRENT_TICKER_DETAILS = "current_ticker_details"
    HISTORICAL_TICKER_REFERENCE = "historical_ticker_reference"
    TICKER_EVENTS = "ticker_events"


class ProbeStatus(StrEnum):
    COMPLETED = "completed"
    STOPPED_ENTITLEMENT = "stopped_entitlement"
    STOPPED_AUTHENTICATION = "stopped_authentication"
    STOPPED_RATE_LIMIT = "stopped_rate_limit"
    STOPPED_UNAVAILABLE = "stopped_unavailable"
    STOPPED_MALFORMED = "stopped_malformed"


class HistoricalLane(StrEnum):
    INSTRUMENT_CIK = "instrument_cik"
    SECURITY_FORM = "security_form"
    LISTING_ALIASES = "listing_aliases"
    ISSUER_STRUCTURE = "issuer_structure"


class CapabilitySampleCaseV1(FrozenModel):
    kind: SampleKind
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    observed_tickers: tuple[str, ...] = Field(min_length=1)
    current_provider_ticker: str = Field(min_length=1)
    composite_figi: str = Field(pattern=r"^BBG[0-9A-Z]{9}$")
    share_class_figi: str = Field(pattern=r"^BBG[0-9A-Z]{9}$")
    representative_session: date
    multi_common_group: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def canonical(self) -> "CapabilitySampleCaseV1":
        if self.observed_tickers != tuple(sorted(set(self.observed_tickers))):
            raise ValueError("sample tickers must be unique and sorted")
        if self.kind is SampleKind.TICKER_CHANGE and len(self.observed_tickers) < 2:
            raise ValueError("ticker-change sample requires at least two tickers")
        if self.kind is SampleKind.MULTI_COMMON:
            if len(self.multi_common_group) < 2 or self.instrument_id not in self.multi_common_group:
                raise ValueError("multi-common sample requires its complete observed group")
        elif self.multi_common_group:
            raise ValueError("only multi-common sample can contain a security group")
        return self


class CapabilitySampleRequestV1(FrozenModel):
    sequence: int = Field(ge=1, le=MAXIMUM_REQUEST_COUNT)
    sample_kind: SampleKind
    request_kind: RequestKind
    path: str = Field(pattern=r"^/[^?]+$")
    params: tuple[tuple[str, str], ...] = ()
    response_body_limit_bytes: Literal[1_048_576] = 1_048_576
    automatic_retry_count: Literal[0] = 0

    @model_validator(mode="after")
    def canonical(self) -> "CapabilitySampleRequestV1":
        if self.params != tuple(sorted(set(self.params))):
            raise ValueError("request params must be unique and sorted")
        if any(key.lower() in {"apikey", "api_key", "authorization"} for key, _ in self.params):
            raise ValueError("request plan must not contain credentials")
        return self


class MassiveStarterCapabilitySamplePlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    applicability_result_fingerprint: Literal[
        "da67ce358fef0bb533875125d658ee6f2e365c435f17c08036d9b03d12fa578e"
    ] = "da67ce358fef0bb533875125d658ee6f2e365c435f17c08036d9b03d12fa578e"
    source_gap_plan_fingerprint: Literal[
        "0958b66c9b69dc031e6e71a64e9ab394559779fe52655ed9210a77aa388bb32e"
    ] = "0958b66c9b69dc031e6e71a64e9ab394559779fe52655ed9210a77aa388bb32e"
    selection_rule: Literal[
        "lexicographically_first_provider_locatable_case_per_registered_kind"
    ] = "lexicographically_first_provider_locatable_case_per_registered_kind"
    samples: tuple[CapabilitySampleCaseV1, ...]
    requests: tuple[CapabilitySampleRequestV1, ...]
    maximum_request_count: Literal[MAXIMUM_REQUEST_COUNT] = MAXIMUM_REQUEST_COUNT
    serial_request_interval_seconds: Literal["0.25"] = "0.25"
    raw_response_custody: Literal["owner_only_sanitized"] = "owner_only_sanitized"
    stop_on_first_failed_request: Literal[True] = True
    outcome_selection_allowed: Literal[False] = False
    issuer_structure_in_probe_scope: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "MassiveStarterCapabilitySamplePlanV1":
        if tuple(item.kind for item in self.samples) != tuple(SampleKind):
            raise ValueError("capability sample must cover three canonical kinds")
        sequences = tuple(item.sequence for item in self.requests)
        if sequences != tuple(range(1, len(self.requests) + 1)):
            raise ValueError("request sequence differs")
        if len(self.requests) != MAXIMUM_REQUEST_COUNT:
            raise ValueError("exact capability request budget differs")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("capability sample plan fingerprint differs")
        return self


class CapabilityRequestOutcomeV1(FrozenModel):
    sequence: int = Field(ge=1, le=MAXIMUM_REQUEST_COUNT)
    status: Literal["accessible"]
    captured_at_utc: datetime
    sanitized_response_sha256: str = Field(pattern=_SHA256)
    sanitized_response_byte_size: int = Field(ge=2, le=1_048_576)
    schema_paths: tuple[str, ...]
    result_count: int = Field(ge=0)


class HistoricalLaneDispositionV1(FrozenModel):
    lane: HistoricalLane
    disposition: Literal["blocked", "corroboration_only"]
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def canonical(self) -> "HistoricalLaneDispositionV1":
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("lane reason codes must be unique and sorted")
        return self


class MassiveStarterCapabilitySampleResultV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    status: ProbeStatus
    request_count: int = Field(ge=0, le=MAXIMUM_REQUEST_COUNT)
    failed_request_sequence: int | None = Field(default=None, ge=1, le=MAXIMUM_REQUEST_COUNT)
    request_outcomes: tuple[CapabilityRequestOutcomeV1, ...]
    lane_dispositions: tuple[HistoricalLaneDispositionV1, ...]
    credential_value_retained: Literal[False] = False
    credential_value_hashed: Literal[False] = False
    raw_responses_sanitized: Literal[True] = True
    historical_lane_admitted_count: Literal[0] = 0
    issuer_structure_proven: Literal[False] = False
    security_projection_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "MassiveStarterCapabilitySampleResultV1":
        if self.request_count != len(self.request_outcomes) + (self.failed_request_sequence is not None):
            raise ValueError("request count differs")
        if tuple(item.lane for item in self.lane_dispositions) != tuple(HistoricalLane):
            raise ValueError("lane dispositions differ")
        if self.status is ProbeStatus.COMPLETED:
            if self.request_count != MAXIMUM_REQUEST_COUNT or self.failed_request_sequence is not None:
                raise ValueError("completed probe did not use exact request budget")
        elif self.failed_request_sequence is None:
            raise ValueError("stopped probe lacks failed request sequence")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("capability sample result fingerprint differs")
        return self


class MassiveStarterCapabilitySampleVerificationV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    result_fingerprint: str = Field(pattern=_SHA256)
    retained_file_count: int = Field(ge=3)
    retained_byte_count: int = Field(ge=1)
    exact_reread_status: Literal["complete"] = "complete"
    downstream_authority_changed: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "MassiveStarterCapabilitySampleVerificationV1":
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("capability sample verification fingerprint differs")
        return self
