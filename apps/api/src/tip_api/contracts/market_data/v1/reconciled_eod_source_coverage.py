"""Evidence contract for exact Reconciled EOD source-package selection."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
    reconciled_eod_fingerprint,
)


CONTRACT_VERSION = "reconciled-eod-source-coverage/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReconciledEodSourceOrigin(StrEnum):
    DAILY_AUTOMATION = "daily_automation"
    HISTORICAL_BACKFILL = "historical_backfill"
    HISTORICAL_WARMUP = "historical_warmup"
    LATER_REACQUISITION = "later_reacquisition"


class ReconciledEodSourceCoverageDisposition(StrEnum):
    SELECTED_RETAINED_ORIGINAL = "selected_retained_original"
    SELECTED_LATER_REACQUISITION = "selected_later_reacquisition"
    MISSING = "missing"
    INVALID = "invalid"
    CONFLICT = "conflict"


class ReconciledEodSourceCoverageSessionV1(FrozenModel):
    session_date: date
    disposition: ReconciledEodSourceCoverageDisposition
    observed_candidate_count: int = Field(ge=0, le=4)
    observed_candidate_origins: tuple[ReconciledEodSourceOrigin, ...] = ()
    canonical_eod_fingerprint: str | None = Field(default=None, pattern=_SHA256)
    canonical_identity_fingerprint: str | None = Field(default=None, pattern=_SHA256)
    selected_source_origin: ReconciledEodSourceOrigin | None = None
    selected_source_provenance: ReconciledEodSourceProvenance | None = None
    selected_source_observed_at: datetime | None = None
    selected_package_manifest_sha256: str | None = Field(default=None, pattern=_SHA256)
    selected_package_content_sha256: str | None = Field(default=None, pattern=_SHA256)
    selected_binding_plan_sha256: str | None = Field(default=None, pattern=_SHA256)
    reason_codes: tuple[str, ...] = ()

    @field_validator("selected_source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("observed_candidate_origins")
    @classmethod
    def candidate_origins_are_unique_and_ordered(
        cls,
        value: tuple[ReconciledEodSourceOrigin, ...],
    ) -> tuple[ReconciledEodSourceOrigin, ...]:
        if value != tuple(sorted(set(value), key=lambda item: item.value)):
            raise ValueError("source candidate origins must be unique and ordered")
        return value

    @field_validator("reason_codes")
    @classmethod
    def reasons_are_unique_and_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item for item in value):
            raise ValueError("source coverage reasons must be present, unique, and ordered")
        return value

    @model_validator(mode="after")
    def session_binding_reconciles(self) -> "ReconciledEodSourceCoverageSessionV1":
        if self.observed_candidate_count != len(self.observed_candidate_origins):
            raise ValueError("source candidate count differs from origins")
        selected = self.disposition in {
            ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL,
            ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION,
        }
        selected_values = (
            self.selected_source_origin,
            self.selected_source_provenance,
            self.selected_source_observed_at,
            self.selected_package_manifest_sha256,
            self.selected_package_content_sha256,
        )
        if selected:
            if (
                any(item is None for item in selected_values)
                or self.canonical_eod_fingerprint is None
                or self.canonical_identity_fingerprint is None
                or self.reason_codes
            ):
                raise ValueError("selected source coverage binding is incomplete")
            if self.selected_source_origin not in self.observed_candidate_origins:
                raise ValueError("selected source origin was not observed")
            if (
                self.disposition
                == ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
            ):
                if (
                    self.selected_source_provenance
                    != ReconciledEodSourceProvenance.RETAINED_ORIGINAL
                    or self.selected_source_origin
                    == ReconciledEodSourceOrigin.LATER_REACQUISITION
                    or self.selected_binding_plan_sha256 is None
                ):
                    raise ValueError("retained-original source binding differs")
            elif (
                self.selected_source_provenance
                != ReconciledEodSourceProvenance.LATER_REACQUISITION
                or self.selected_source_origin
                != ReconciledEodSourceOrigin.LATER_REACQUISITION
                or self.selected_binding_plan_sha256 is not None
            ):
                raise ValueError("later-reacquisition source binding differs")
            return self
        if any(item is not None for item in selected_values) or (
            self.selected_binding_plan_sha256 is not None
        ):
            raise ValueError("unselected source coverage contains a selection")
        if not self.reason_codes:
            raise ValueError("unselected source coverage lacks a reason")
        return self


class ReconciledEodSourceCoverageV1(FrozenModel):
    contract_version: Literal["reconciled-eod-source-coverage/1.0"] = (
        CONTRACT_VERSION
    )
    status: Literal["ready_for_candidate_build", "incomplete"]
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    calendar_id: Literal["XNYS"] = "XNYS"
    evaluation_first_session: date
    evaluation_last_session: date
    warmup_first_session: date | None = None
    warmup_last_session: date | None = None
    sessions: tuple[ReconciledEodSourceCoverageSessionV1, ...]
    target_session_count: int = Field(ge=1)
    retained_original_session_count: int = Field(ge=0)
    later_reacquisition_session_count: int = Field(ge=0)
    missing_session_count: int = Field(ge=0)
    invalid_session_count: int = Field(ge=0)
    conflict_session_count: int = Field(ge=0)
    created_at: datetime
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    candidate_session_write_count: Literal[0] = 0
    source_selection_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    production_authority: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def coverage_reconciles(
        self,
        info: ValidationInfo,
    ) -> "ReconciledEodSourceCoverageV1":
        dates = tuple(item.session_date for item in self.sessions)
        if not dates or dates != tuple(sorted(set(dates))):
            raise ValueError("source coverage sessions must be unique and ordered")
        if self.evaluation_first_session > self.evaluation_last_session:
            raise ValueError("source coverage evaluation interval is reversed")
        if (self.warmup_first_session is None) != (
            self.warmup_last_session is None
        ):
            raise ValueError("source coverage warmup bounds must both be present")
        if self.warmup_first_session is not None and not (
            self.warmup_first_session
            <= self.warmup_last_session
            < self.evaluation_first_session
        ):
            raise ValueError("source coverage warmup interval is invalid")
        expected_first = self.warmup_first_session or self.evaluation_first_session
        if (
            dates[0] != expected_first
            or dates[-1] != self.evaluation_last_session
            or self.evaluation_first_session not in dates
            or self.target_session_count != len(dates)
        ):
            raise ValueError("source coverage evaluation interval differs")
        dispositions = tuple(item.disposition for item in self.sessions)
        expected_counts = {
            ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL: (
                self.retained_original_session_count
            ),
            ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION: (
                self.later_reacquisition_session_count
            ),
            ReconciledEodSourceCoverageDisposition.MISSING: self.missing_session_count,
            ReconciledEodSourceCoverageDisposition.INVALID: self.invalid_session_count,
            ReconciledEodSourceCoverageDisposition.CONFLICT: self.conflict_session_count,
        }
        if any(dispositions.count(key) != value for key, value in expected_counts.items()):
            raise ValueError("source coverage disposition counts differ")
        incomplete = (
            self.missing_session_count
            + self.invalid_session_count
            + self.conflict_session_count
        )
        expected_status = "incomplete" if incomplete else "ready_for_candidate_build"
        if self.status != expected_status:
            raise ValueError("source coverage status differs from session evidence")
        if info.context and info.context.get("allow_unsealed_manifest"):
            return self
        expected = reconciled_eod_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("source coverage fingerprint mismatch")
        return self


def seal_reconciled_eod_source_coverage(
    values: Mapping[str, object],
) -> ReconciledEodSourceCoverageV1:
    if "logical_fingerprint" in values:
        raise ValueError("logical_fingerprint is computed, not supplied")
    draft = ReconciledEodSourceCoverageV1.model_validate(
        {**dict(values), "logical_fingerprint": "0" * 64},
        context={"allow_unsealed_manifest": True},
    )
    payload = draft.model_dump(mode="json", exclude={"logical_fingerprint"})
    payload["logical_fingerprint"] = reconciled_eod_fingerprint(payload)
    return ReconciledEodSourceCoverageV1.model_validate(payload)
