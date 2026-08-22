"""Logical contract for an immutable reviewed security-form superseding shadow."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.full_base_liquidity import FullBaseDatasetReferenceV1, FullBasePolicySummaryV1


class SupersedingFullBaseManifestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    manifest_version: Literal["2.0"] = "2.0"
    completion_status: Literal["completed"] = "completed"
    revision_id: Literal["authoritative-security-form-v1"] = "authoritative-security-form-v1"
    analysis_session: date
    membership_evidence_as_of_date: date
    source_full_base_logical_path: str
    source_full_base_logical_fingerprint: str
    source_descriptor_fingerprint: str
    reviewed_security_form_dataset: FullBaseDatasetReferenceV1
    metric_dataset: FullBaseDatasetReferenceV1
    decision_dataset: FullBaseDatasetReferenceV1
    membership_dataset: FullBaseDatasetReferenceV1
    diff_dataset: FullBaseDatasetReferenceV1
    funnel_dataset: FullBaseDatasetReferenceV1
    policies: tuple[FullBasePolicySummaryV1, ...]
    created_at: datetime
    logical_content_fingerprint: str

    @field_validator("source_full_base_logical_path", mode="before")
    @classmethod
    def path(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="source_full_base_logical_path")
        if value.startswith("/") or ".." in value.split("/"):
            raise ValueError("source path must be normalized and relative")
        return value

    @field_validator("source_full_base_logical_fingerprint", "source_descriptor_fingerprint", "logical_content_fingerprint")
    @classmethod
    def sha(cls, value: str, info) -> str:
        value = normalize_required_string(value, field_name=info.field_name).lower()
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError(f"{info.field_name} must be SHA-256 hexadecimal")
        return value

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)
