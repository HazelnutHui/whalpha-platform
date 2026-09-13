"""Cross-census unresolved corporate actions without assigning identity."""

from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
import shutil
import socket
import stat
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, Literal, Mapping

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services.finra_otc_daily_list_range_census import (
    read_sealed_finra_otc_daily_list_range_census,
)
from tip_api.services.finra_otc_daily_list_source import (
    read_finra_otc_daily_list_source_payloads,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    read_historical_corporate_action_resolution_shadow,
)
from tip_api.services.historical_corporate_action_unresolved_census import (
    read_historical_corporate_action_unresolved_census,
)
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    read_historical_inactive_lifecycle_resolution_shadow,
)


CONTRACT_VERSION = "historical-corporate-action-residual-evidence-census/1.0"
RECORD_CONTRACT_VERSION = (
    "historical-corporate-action-residual-evidence-census-record/1.0"
)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
RECORDS_FILE = "records.parquet"
MANIFEST_FILE = "manifest.json"
MAXIMUM_RECORDS_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"
_LIFECYCLE_STATES = (
    "after_delist_candidate",
    "before_canonical_first_observed",
    "inside_canonical_observed_span",
    "mixed_anchor_boundary",
    "no_lifecycle_evidence",
    "unverified_terminal_gap",
)
_INACTIVE_SOURCE_STATES = (
    "matched_multiple_stable_identities",
    "matched_no_stable_identity",
    "matched_one_stable_identity",
    "no_ticker_match",
)
_FINRA_FLAGS = (
    "bankruptcy",
    "security_add",
    "security_delete",
    "symbol_change",
)


RECORDS_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("source_action_id", pa.string(), nullable=False),
        pa.field("source_revision", pa.int32(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field("action_type", pa.string(), nullable=False),
        pa.field("exact_date_failure_reason", pa.string(), nullable=False),
        pa.field("historical_candidate_classification", pa.string(), nullable=False),
        pa.field("historical_candidate_count", pa.int32(), nullable=False),
        *[
            pa.field(f"lifecycle_{state}_count", pa.int32(), nullable=False)
            for state in _LIFECYCLE_STATES
        ],
        pa.field("inactive_source_state", pa.string(), nullable=False),
        pa.field("inactive_source_type_codes", pa.list_(pa.string()), nullable=False),
        pa.field("finra_exact_date_symbol_occurrence_count", pa.int32(), nullable=False),
        pa.field("finra_exact_numeric_occurrence_count", pa.int32(), nullable=False),
        pa.field("finra_flag_codes", pa.list_(pa.string()), nullable=False),
    ]
)


class HistoricalCorporateActionResidualEvidenceCensusError(RuntimeError):
    """Raised when residual evidence cannot be reconciled conservatively."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResidualEvidenceRecordV1(_FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-residual-evidence-census-record/1.0"
    ] = RECORD_CONTRACT_VERSION
    source_action_id: str
    source_revision: int = Field(ge=1)
    provider_ticker: str
    effective_date: date
    action_type: Literal[
        "cash_dividend", "reverse_split", "stock_dividend", "stock_split"
    ]
    exact_date_failure_reason: Literal[
        "event_date_identity_unavailable", "unresolved_ticker"
    ]
    historical_candidate_classification: Literal[
        "zero_historical_candidates",
        "one_historical_candidate",
        "multiple_historical_candidates",
    ]
    historical_candidate_count: int = Field(ge=0)
    lifecycle_after_delist_candidate_count: int = Field(ge=0)
    lifecycle_before_canonical_first_observed_count: int = Field(ge=0)
    lifecycle_inside_canonical_observed_span_count: int = Field(ge=0)
    lifecycle_mixed_anchor_boundary_count: int = Field(ge=0)
    lifecycle_no_lifecycle_evidence_count: int = Field(ge=0)
    lifecycle_unverified_terminal_gap_count: int = Field(ge=0)
    inactive_source_state: Literal[
        "matched_multiple_stable_identities",
        "matched_no_stable_identity",
        "matched_one_stable_identity",
        "no_ticker_match",
    ]
    inactive_source_type_codes: tuple[str, ...]
    finra_exact_date_symbol_occurrence_count: int = Field(ge=0)
    finra_exact_numeric_occurrence_count: int = Field(ge=0)
    finra_flag_codes: tuple[
        Literal["bankruptcy", "security_add", "security_delete", "symbol_change"],
        ...,
    ]

    @field_validator("source_action_id")
    @classmethod
    def action_id_is_trimmed(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("source action ID is invalid")
        return value

    @field_validator("provider_ticker")
    @classmethod
    def ticker_is_normalized(cls, value: str) -> str:
        if not value or value != value.strip().upper():
            raise ValueError("provider ticker is not normalized")
        return value

    @field_validator("inactive_source_type_codes", "finra_flag_codes", mode="before")
    @classmethod
    def tuple_is_ordered_unique(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("residual evidence values are not ordered and unique")
        return values

    @model_validator(mode="after")
    def counts_reconcile(self) -> "ResidualEvidenceRecordV1":
        expected_count = {
            "zero_historical_candidates": 0,
            "one_historical_candidate": 1,
        }.get(self.historical_candidate_classification)
        if expected_count is not None and self.historical_candidate_count != expected_count:
            raise ValueError("historical candidate count differs from classification")
        if (
            self.historical_candidate_classification
            == "multiple_historical_candidates"
            and self.historical_candidate_count < 2
        ):
            raise ValueError("multiple-candidate classification has fewer than two candidates")
        lifecycle_total = sum(
            getattr(self, f"lifecycle_{state}_count") for state in _LIFECYCLE_STATES
        )
        if lifecycle_total != self.historical_candidate_count:
            raise ValueError("lifecycle candidate accounting differs")
        if (
            self.finra_exact_numeric_occurrence_count
            > self.finra_exact_date_symbol_occurrence_count
        ):
            raise ValueError("FINRA numeric matches exceed date/symbol matches")
        if (
            self.inactive_source_state == "no_ticker_match"
            and self.inactive_source_type_codes
        ):
            raise ValueError("unmatched inactive source carries type codes")
        return self


class ResidualEvidenceLifecycleBindingV1(_FrozenModel):
    anchor_date: date
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_record_count: int = Field(ge=1)
    decision_record_count: int = Field(ge=1)


class HistoricalCorporateActionResidualEvidenceCensusManifestV1(_FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-residual-evidence-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "historical-corporate-action-residual-evidence-census"
    ] = "historical-corporate-action-residual-evidence-census"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    resolution_shadow_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_shadow_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    unresolved_census_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    unresolved_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_bindings: tuple[ResidualEvidenceLifecycleBindingV1, ...] = Field(
        min_length=1
    )
    finra_range_start: date
    finra_range_end: date
    finra_range_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    finra_range_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    finra_package_chain_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    finra_package_count: int = Field(ge=1)
    finra_source_record_count: int = Field(ge=1)
    unresolved_source_record_count: int = Field(ge=1)
    residual_record_count: int = Field(ge=1)
    residual_record_candidate_relation_counts: tuple[tuple[str, int], ...]
    inactive_source_state_counts: tuple[tuple[str, int], ...]
    finra_exact_date_symbol_record_count: int = Field(ge=0)
    finra_exact_numeric_record_count: int = Field(ge=0)
    records_file: Literal["records.parquet"] = RECORDS_FILE
    records_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    records_file_bytes: int = Field(ge=1, le=MAXIMUM_RECORDS_BYTES)
    records_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evidence_role: Literal["quarantine_diagnostic_only"] = (
        "quarantine_diagnostic_only"
    )
    stable_identity_assignment_count: Literal[0] = 0
    source_record_mutation_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "HistoricalCorporateActionResidualEvidenceCensusManifestV1":
        if self.finra_range_end < self.finra_range_start:
            raise ValueError("FINRA range is reversed")
        anchors = tuple(item.anchor_date for item in self.lifecycle_bindings)
        if anchors != tuple(sorted(set(anchors))):
            raise ValueError("lifecycle bindings are not ordered and unique")
        if self.unresolved_source_record_count != self.residual_record_count:
            raise ValueError("residual source accounting differs")
        if tuple(
            key for key, _ in self.residual_record_candidate_relation_counts
        ) != _LIFECYCLE_STATES:
            raise ValueError("lifecycle state matrix differs")
        if tuple(key for key, _ in self.inactive_source_state_counts) != (
            _INACTIVE_SOURCE_STATES
        ):
            raise ValueError("inactive source state matrix differs")
        values = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if self.logical_fingerprint != _fingerprint(values):
            raise ValueError("residual evidence manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class HistoricalCorporateActionResidualEvidenceCensusResult:
    output_root: Path
    manifest: HistoricalCorporateActionResidualEvidenceCensusManifestV1
    records: tuple[ResidualEvidenceRecordV1, ...]
    manifest_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _LifecycleWindow:
    first_observed: date
    last_observed: date
    delist_candidate: date


@dataclass(frozen=True, slots=True)
class _InactiveTickerEvidence:
    state: str
    type_codes: tuple[str, ...]


def build_historical_corporate_action_residual_evidence_census(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    unresolved_census_output_root: Path,
    unresolved_census_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
    finra_custody_root: Path,
    finra_range_start: date,
    finra_range_end: date,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> HistoricalCorporateActionResidualEvidenceCensusResult:
    """Build one immutable, network-free, assignment-free residual census."""

    with _network_prohibited():
        return _build_census(
            data_root=data_root,
            resolution_shadow_output_root=resolution_shadow_output_root,
            resolution_shadow_custody_root=resolution_shadow_custody_root,
            unresolved_census_output_root=unresolved_census_output_root,
            unresolved_census_custody_root=unresolved_census_custody_root,
            lifecycle_shadow_root=lifecycle_shadow_root,
            lifecycle_shadow_custody_root=lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=lifecycle_anchor_dates,
            finra_custody_root=finra_custody_root,
            finra_range_start=finra_range_start,
            finra_range_end=finra_range_end,
            output_root=output_root,
            output_custody_root=output_custody_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )


def _build_census(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    unresolved_census_output_root: Path,
    unresolved_census_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
    finra_custody_root: Path,
    finra_range_start: date,
    finra_range_end: date,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> HistoricalCorporateActionResidualEvidenceCensusResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "implementation revision is invalid"
        )
    if (
        not lifecycle_anchor_dates
        or lifecycle_anchor_dates != tuple(sorted(set(lifecycle_anchor_dates)))
    ):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "lifecycle anchors are empty, duplicated, or unordered"
        )
    evaluated_at = normalize_utc_datetime(evaluated_at)
    target = _validated_output_target(output_root, output_custody_root)
    shadow = read_historical_corporate_action_resolution_shadow(
        output_root=resolution_shadow_output_root,
        output_custody_root=resolution_shadow_custody_root,
    )
    unresolved = read_historical_corporate_action_unresolved_census(
        data_root=data_root,
        resolution_shadow_output_root=resolution_shadow_output_root,
        resolution_shadow_custody_root=resolution_shadow_custody_root,
        output_root=unresolved_census_output_root,
        output_custody_root=unresolved_census_custody_root,
    )
    lifecycle_results = tuple(
        read_historical_inactive_lifecycle_resolution_shadow(
            root=lifecycle_shadow_root,
            anchor_date=anchor,
            approved_custody_root=lifecycle_shadow_custody_root,
        )
        for anchor in lifecycle_anchor_dates
    )
    finra_rows, finra_range, finra_range_sha = _read_finra_range(
        custody_root=finra_custody_root,
        range_start=finra_range_start,
        range_end=finra_range_end,
    )
    source_rows = tuple(
        row
        for row in shadow.records
        if row.instrument_resolution_status is ResolutionStatus.UNRESOLVED
    )
    if len(source_rows) != unresolved.manifest.unresolved_typed_record_count:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "unresolved source denominator differs"
        )
    records = _build_records(
        source_rows=source_rows,
        unresolved_records=unresolved.records,
        lifecycle_results=lifecycle_results,
        finra_rows=finra_rows,
    )
    logical = _records_fingerprint(records)
    table = pa.Table.from_pylist(
        [item.model_dump(mode="python") for item in records], schema=RECORDS_SCHEMA
    )

    if target.exists() or target.is_symlink():
        existing = read_historical_corporate_action_residual_evidence_census(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.records != records:
            raise HistoricalCorporateActionResidualEvidenceCensusError(
                "existing residual evidence census differs"
            )
        return existing

    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_owner_directory(target.parent)
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        records_path = partial / RECORDS_FILE
        pq.write_table(table, records_path, compression="zstd", version="2.6")
        records_path.chmod(0o400)
        records_sha = _file_sha256(records_path)
        records_bytes = records_path.stat().st_size
        if records_bytes > MAXIMUM_RECORDS_BYTES:
            raise HistoricalCorporateActionResidualEvidenceCensusError(
                "residual evidence records exceed byte ceiling"
            )
        lifecycle_bindings = tuple(
            ResidualEvidenceLifecycleBindingV1(
                anchor_date=item.manifest.anchor_date,
                manifest_sha256=item.manifest_sha256,
                logical_fingerprint=item.manifest.logical_fingerprint,
                source_record_count=item.manifest.source_artifact.record_count,
                decision_record_count=item.manifest.decision_artifact.record_count,
            )
            for item in lifecycle_results
        )
        state_counts: Counter[str] = Counter()
        for item in records:
            for state in _LIFECYCLE_STATES:
                state_counts[state] += getattr(item, f"lifecycle_{state}_count")
        inactive_counts = Counter(item.inactive_source_state for item in records)
        manifest_values = {
            "contract_version": CONTRACT_VERSION,
            "completion_status": "completed",
            "dataset_name": "historical-corporate-action-residual-evidence-census",
            "implementation_revision": implementation_revision,
            "evaluated_at": evaluated_at,
            "resolution_shadow_manifest_sha256": shadow.manifest_sha256,
            "resolution_shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
            "unresolved_census_manifest_sha256": unresolved.manifest_sha256,
            "unresolved_census_logical_fingerprint": unresolved.manifest.logical_fingerprint,
            "lifecycle_bindings": lifecycle_bindings,
            "finra_range_start": finra_range_start,
            "finra_range_end": finra_range_end,
            "finra_range_census_sha256": finra_range_sha,
            "finra_range_census_logical_fingerprint": finra_range.logical_fingerprint,
            "finra_package_chain_fingerprint": finra_range.package_chain_fingerprint,
            "finra_package_count": finra_range.package_count,
            "finra_source_record_count": finra_range.record_count,
            "unresolved_source_record_count": len(source_rows),
            "residual_record_count": len(records),
            "residual_record_candidate_relation_counts": tuple(
                (state, state_counts[state]) for state in _LIFECYCLE_STATES
            ),
            "inactive_source_state_counts": tuple(
                (state, inactive_counts[state]) for state in _INACTIVE_SOURCE_STATES
            ),
            "finra_exact_date_symbol_record_count": sum(
                item.finra_exact_date_symbol_occurrence_count > 0 for item in records
            ),
            "finra_exact_numeric_record_count": sum(
                item.finra_exact_numeric_occurrence_count > 0 for item in records
            ),
            "records_file": RECORDS_FILE,
            "records_file_sha256": records_sha,
            "records_file_bytes": records_bytes,
            "records_logical_fingerprint": logical,
            "evidence_role": "quarantine_diagnostic_only",
            "stable_identity_assignment_count": 0,
            "source_record_mutation_count": 0,
            "canonical_data_write_count": 0,
            "adjustment_ledger_write_count": 0,
            "historical_coverage_write_count": 0,
            "analytics_execution_count": 0,
            "candidate_write_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
            "scheduler_change_count": 0,
            "external_request_count": 0,
        }
        manifest = HistoricalCorporateActionResidualEvidenceCensusManifestV1.model_validate(
            {**manifest_values, "logical_fingerprint": _fingerprint(manifest_values)}
        )
        manifest_path = partial / MANIFEST_FILE
        _write_exclusive(manifest_path, _json_bytes(manifest.model_dump(mode="json")))
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_historical_corporate_action_residual_evidence_census(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.records != records or reread.manifest != manifest:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence formal reread differs"
        )
    return HistoricalCorporateActionResidualEvidenceCensusResult(
        output_root=target,
        manifest=manifest,
        records=records,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_historical_corporate_action_residual_evidence_census(
    *, output_root: Path, output_custody_root: Path
) -> HistoricalCorporateActionResidualEvidenceCensusResult:
    """Reread one immutable residual census without recomputing upstream history."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {MANIFEST_FILE, RECORDS_FILE}:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence package members differ"
        )
    manifest_path, records_path = root / MANIFEST_FILE, root / RECORDS_FILE
    _require_regular_file(manifest_path, 0o400)
    _require_regular_file(records_path, 0o400)
    try:
        manifest = HistoricalCorporateActionResidualEvidenceCensusManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
        table = pq.ParquetFile(records_path).read()
    except Exception as exc:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence output is invalid"
        ) from exc
    if table.schema != RECORDS_SCHEMA:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence schema differs"
        )
    try:
        records = tuple(ResidualEvidenceRecordV1.model_validate(row) for row in table.to_pylist())
    except Exception as exc:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence records are invalid"
        ) from exc
    if (
        len(records) != manifest.residual_record_count
        or _file_sha256(records_path) != manifest.records_file_sha256
        or records_path.stat().st_size != manifest.records_file_bytes
        or _records_fingerprint(records) != manifest.records_logical_fingerprint
    ):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence records differ from manifest"
        )
    _verify_aggregates(manifest, records)
    return HistoricalCorporateActionResidualEvidenceCensusResult(
        output_root=root,
        manifest=manifest,
        records=records,
        manifest_sha256=_file_sha256(manifest_path),
        status="already_present",
    )


def _build_records(
    *, source_rows: tuple[object, ...], unresolved_records: tuple[object, ...],
    lifecycle_results: tuple[object, ...], finra_rows: tuple[dict[str, object], ...]
) -> tuple[ResidualEvidenceRecordV1, ...]:
    unresolved_by_ticker = {item.provider_ticker: item for item in unresolved_records}
    if set(unresolved_by_ticker) != {item.provider_ticker for item in source_rows}:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "unresolved ticker populations differ"
        )
    lifecycle_by_id: defaultdict[str, list[_LifecycleWindow]] = defaultdict(list)
    inactive_source_by_ticker: defaultdict[
        str, dict[str, tuple[object, object]]
    ] = defaultdict(dict)
    for result in lifecycle_results:
        for source, decision in zip(result.source_observations, result.decisions, strict=True):
            ticker = _symbol(source.ticker)
            if ticker is not None:
                inactive_source_by_ticker[ticker][source.source_payload_fingerprint] = (
                    source, decision
                )
            if decision.disposition is InactiveLifecycleDisposition.REVIEW_CANDIDATE:
                lifecycle_by_id[str(decision.canonical_instrument_id)].append(
                    _LifecycleWindow(
                        first_observed=decision.canonical_first_observed_date,
                        last_observed=decision.canonical_last_observed_date,
                        delist_candidate=decision.effective_date_candidate,
                    )
                )
    inactive = {
        ticker: _inactive_ticker_evidence(tuple(values.values()))
        for ticker, values in inactive_source_by_ticker.items()
    }
    finra_index = _finra_index(finra_rows)
    records = []
    for source in source_rows:
        census = unresolved_by_ticker[source.provider_ticker]
        counts = Counter(
            _lifecycle_state(
                event_date=source.effective_date,
                windows=tuple(lifecycle_by_id.get(str(candidate.instrument_id), ())),
            )
            for candidate in census.candidates
        )
        occurrences = finra_index.get((source.effective_date, source.provider_ticker), ())
        numeric_matches = sum(_finra_numeric_matches(source, item) for item in occurrences)
        flags = tuple(
            code
            for code, field in (
                ("bankruptcy", "bankruptcyFlag"),
                ("security_add", "securityAddFlag"),
                ("security_delete", "securityDeleteFlag"),
                ("symbol_change", "changeSymbolFlag"),
            )
            if any(_symbol(item.get(field)) == "Y" for item in occurrences)
        )
        failures = {
            item
            for item in source.quality_flags
            if item in {"event_date_identity_unavailable", "unresolved_ticker"}
        }
        if len(failures) != 1:
            raise HistoricalCorporateActionResidualEvidenceCensusError(
                "unresolved source failure reason differs"
            )
        failure = next(iter(failures))
        inactive_evidence = inactive.get(
            source.provider_ticker,
            _InactiveTickerEvidence(state="no_ticker_match", type_codes=()),
        )
        records.append(
            ResidualEvidenceRecordV1(
                source_action_id=source.source_action_id,
                source_revision=source.source_revision,
                provider_ticker=source.provider_ticker,
                effective_date=source.effective_date,
                action_type=source.action_type.value,
                exact_date_failure_reason=failure,
                historical_candidate_classification=census.classification,
                historical_candidate_count=len(census.candidates),
                **{
                    f"lifecycle_{state}_count": counts[state]
                    for state in _LIFECYCLE_STATES
                },
                inactive_source_state=inactive_evidence.state,
                inactive_source_type_codes=inactive_evidence.type_codes,
                finra_exact_date_symbol_occurrence_count=len(occurrences),
                finra_exact_numeric_occurrence_count=numeric_matches,
                finra_flag_codes=flags,
            )
        )
    ordered = tuple(sorted(records, key=lambda item: (item.source_action_id, item.source_revision)))
    if len({(item.source_action_id, item.source_revision) for item in ordered}) != len(ordered):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence business keys are duplicated"
        )
    return ordered


def _lifecycle_state(
    *, event_date: date, windows: tuple[_LifecycleWindow, ...]
) -> str:
    if not windows:
        return "no_lifecycle_evidence"
    if any(item.first_observed <= event_date <= item.last_observed for item in windows):
        return "inside_canonical_observed_span"
    if any(item.last_observed < event_date <= item.delist_candidate for item in windows):
        return "unverified_terminal_gap"
    if all(event_date < item.first_observed for item in windows):
        return "before_canonical_first_observed"
    if all(event_date > item.delist_candidate for item in windows):
        return "after_delist_candidate"
    return "mixed_anchor_boundary"


def _inactive_ticker_evidence(
    observations: tuple[tuple[object, object], ...]
) -> _InactiveTickerEvidence:
    identities = {
        (decision.selected_identity_type.value, decision.selected_identity_value)
        for _, decision in observations
        if decision.selected_identity_type is not None
        and decision.selected_identity_value is not None
    }
    state = (
        "matched_no_stable_identity"
        if not identities
        else "matched_one_stable_identity"
        if len(identities) == 1
        else "matched_multiple_stable_identities"
    )
    type_codes = tuple(
        sorted(
            {
                code
                for source, _ in observations
                if (code := _symbol(source.type)) is not None
            }
        )
    )
    return _InactiveTickerEvidence(state=state, type_codes=type_codes)


def _finra_index(
    rows: tuple[dict[str, object], ...]
) -> Mapping[tuple[date, str], tuple[dict[str, object], ...]]:
    mutable: defaultdict[tuple[date, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        effective = _date_value(row.get("exDate"))
        if effective is None:
            continue
        for symbol in {
            _symbol(row.get("oldSymbolCode")),
            _symbol(row.get("newSymbolCode")),
        } - {None}:
            mutable[(effective, symbol)].append(row)  # type: ignore[arg-type]
    return {key: tuple(items) for key, items in mutable.items()}


def _finra_numeric_matches(source: object, row: dict[str, object]) -> bool:
    if source.action_type.value == "cash_dividend":
        value = _decimal(row.get("cashAmountText"))
        return value is not None and value == source.cash_amount
    pair = (source.split_ratio_from, source.split_ratio_to)
    for field in ("forwardSplitRate", "reverseSplitRate"):
        value = row.get(field)
        if not isinstance(value, str) or ":" not in value:
            continue
        split_to_raw, split_from_raw = value.strip().split(":", 1)
        split_from, split_to = _decimal(split_from_raw), _decimal(split_to_raw)
        if split_from is not None and split_to is not None and pair == (split_from, split_to):
            return True
    return False


def _read_finra_range(
    *, custody_root: Path, range_start: date, range_end: date
) -> tuple[tuple[dict[str, object], ...], object, str]:
    sealed = read_sealed_finra_otc_daily_list_range_census(
        custody_root=custody_root, range_start=range_start, range_end=range_end
    )
    rows: list[dict[str, object]] = []
    chain = []
    for start, end in _monthly_partitions(range_start, range_end):
        name = f"period={start.isoformat()}--{end.isoformat()}"
        package = read_finra_otc_daily_list_source_payloads(
            package_path=custody_root / name,
            expected_partition_start=start,
            expected_partition_end=end,
            approved_custody_root=custody_root,
        )
        chain.append(
            (
                name,
                package.manifest_sha256,
                package.manifest.logical_fingerprint,
                package.manifest.record_count,
                package.manifest.request_count,
                package.manifest.data_version,
            )
        )
        rows.extend(dict(row) for page in package.pages for row in page.rows)
    if (
        len(rows) != sealed.record_count
        or _source_fingerprint(tuple(chain)) != sealed.package_chain_fingerprint
    ):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "FINRA source range differs from sealed census"
        )
    census_path = custody_root / (
        f"range-census={range_start.isoformat()}--{range_end.isoformat()}.json"
    )
    return tuple(rows), sealed, _file_sha256(census_path)


def _monthly_partitions(start: date, end: date) -> tuple[tuple[date, date], ...]:
    values = []
    cursor = start
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        partition_end = min(last, end)
        values.append((cursor, partition_end))
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    return tuple(values)


def _verify_aggregates(
    manifest: HistoricalCorporateActionResidualEvidenceCensusManifestV1,
    records: tuple[ResidualEvidenceRecordV1, ...],
) -> None:
    states: Counter[str] = Counter()
    for item in records:
        for state in _LIFECYCLE_STATES:
            states[state] += getattr(item, f"lifecycle_{state}_count")
    inactive = Counter(item.inactive_source_state for item in records)
    expected = {
        "residual_record_candidate_relation_counts": tuple(
            (state, states[state]) for state in _LIFECYCLE_STATES
        ),
        "inactive_source_state_counts": tuple(
            (state, inactive[state]) for state in _INACTIVE_SOURCE_STATES
        ),
        "finra_exact_date_symbol_record_count": sum(
            item.finra_exact_date_symbol_occurrence_count > 0 for item in records
        ),
        "finra_exact_numeric_record_count": sum(
            item.finra_exact_numeric_occurrence_count > 0 for item in records
        ),
    }
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence aggregates differ"
        )


def _records_fingerprint(records: tuple[ResidualEvidenceRecordV1, ...]) -> str:
    digest = hashlib.sha256()
    for item in records:
        digest.update(_json_bytes(item.model_dump(mode="json")))
    return digest.hexdigest()


def _date_value(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _symbol(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized or None


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _source_fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_exclusive(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    root = custody_root.absolute()
    target = path.absolute()
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or target.parent != root
        or re.fullmatch(_BUILD_NAME_PATTERN, target.name) is None
    ):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence output boundary is invalid"
        )
    _require_owner_directory(root)
    return target


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if target.is_symlink() or not target.is_dir() or target.resolve(strict=True) != target:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "completed residual evidence output is unavailable"
        )
    _require_owner_directory(target)
    return target


def _require_owner_directory(path: Path) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence directory custody differs"
        )


def _require_regular_file(path: Path, mode: int) -> None:
    metadata = path.stat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "residual evidence file custody differs"
        )


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket

    def denied(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise HistoricalCorporateActionResidualEvidenceCensusError(
            "network access is prohibited"
        )

    socket.socket = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
