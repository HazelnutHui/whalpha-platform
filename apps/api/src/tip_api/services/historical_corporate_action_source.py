"""Resumable tmp-only custody for Massive split and dividend source pages."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterator, Literal, Mapping
from urllib.parse import parse_qsl, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveJson,
)


CONTRACT_VERSION = "historical-corporate-action-source-package/1.0"
PAGE_CONTRACT_VERSION = "historical-corporate-action-source-page/1.0"
CHECKPOINT_CONTRACT_VERSION = "historical-corporate-action-source-checkpoint/1.0"
PAGE_LIMIT = 5_000
MAXIMUM_PAGE_COUNT = 16
MAXIMUM_RECORD_COUNT = 80_000
MAXIMUM_PAGE_BYTES = 32 * 1024 * 1024
MAXIMUM_PACKAGE_BYTES = 512 * 1024 * 1024
MINIMUM_REQUEST_INTERVAL_SECONDS = 15
_PAGE_FILE_PREFIX = "response-"
_PAGE_FILE_SUFFIX = ".json"
_CHECKPOINT_FILE = "checkpoint.json"
_MANIFEST_FILE = "package.json"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_FORBIDDEN_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "request_id",
}


class CorporateActionSourceKind(StrEnum):
    SPLIT = "split"
    DIVIDEND = "dividend"


_ENDPOINTS = {
    CorporateActionSourceKind.SPLIT: "/stocks/v1/splits",
    CorporateActionSourceKind.DIVIDEND: "/stocks/v1/dividends",
}
_DATE_FIELDS = {
    CorporateActionSourceKind.SPLIT: "execution_date",
    CorporateActionSourceKind.DIVIDEND: "ex_dividend_date",
}
_KNOWN_FIELDS = {
    CorporateActionSourceKind.SPLIT: (
        "adjustment_type",
        "execution_date",
        "historical_adjustment_factor",
        "id",
        "split_from",
        "split_to",
        "ticker",
    ),
    CorporateActionSourceKind.DIVIDEND: (
        "cash_amount",
        "currency",
        "declaration_date",
        "distribution_type",
        "ex_dividend_date",
        "frequency",
        "historical_adjustment_factor",
        "id",
        "pay_date",
        "record_date",
        "split_adjusted_cash_amount",
        "ticker",
    ),
}


class HistoricalCorporateActionSourceError(RuntimeError):
    """Raised when corporate-action source custody cannot proceed safely."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorporateActionSourcePageV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-source-page/1.0"
    ] = PAGE_CONTRACT_VERSION
    sequence: int = Field(ge=1)
    action_kind: CorporateActionSourceKind
    source_observed_at: datetime
    request_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    next_request_path: str | None = None
    next_request_params: tuple[tuple[str, str], ...] = ()
    next_request_locator_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    sanitized_response: dict[str, object]

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def next_request_reconciles(self) -> "CorporateActionSourcePageV1":
        has_next = self.next_request_path is not None
        if has_next != bool(self.next_request_params) or has_next != (
            self.next_request_locator_sha256 is not None
        ):
            raise ValueError("next request fields are incomplete")
        if has_next:
            expected = _request_locator_fingerprint(
                self.next_request_path or "", dict(self.next_request_params)
            )
            if expected != self.next_request_locator_sha256:
                raise ValueError("next request locator fingerprint differs")
        return self


class CorporateActionSourceArtifactV1(FrozenModel):
    sequence: int = Field(ge=1)
    file_name: str
    request_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    next_request_locator_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    source_observed_at: datetime
    row_count: int = Field(ge=0, le=PAGE_LIMIT)
    byte_size: int = Field(ge=1, le=MAXIMUM_PAGE_BYTES)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def file_identity_reconciles(self) -> "CorporateActionSourceArtifactV1":
        if self.file_name != _page_file_name(self.sequence):
            raise ValueError("source page file identity differs")
        return self


ProgressCallback = Callable[[CorporateActionSourceArtifactV1, int, int], None]


class CorporateActionSourceCheckpointV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-source-checkpoint/1.0"
    ] = CHECKPOINT_CONTRACT_VERSION
    state: Literal["in_progress", "complete"]
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    action_kind: CorporateActionSourceKind
    start_date: date
    end_date: date
    started_at: datetime
    last_observed_at: datetime | None = None
    artifacts: tuple[CorporateActionSourceArtifactV1, ...] = ()
    next_request_path: str | None
    next_request_params: tuple[tuple[str, str], ...]
    record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    package_bytes: int = Field(ge=0, le=MAXIMUM_PACKAGE_BYTES)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("started_at", "last_observed_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def checkpoint_reconciles(self) -> "CorporateActionSourceCheckpointV1":
        if self.end_date < self.start_date:
            raise ValueError("corporate-action range is reversed")
        sequences = tuple(item.sequence for item in self.artifacts)
        if sequences != tuple(range(1, len(self.artifacts) + 1)):
            raise ValueError("checkpoint page sequence is not contiguous")
        if len(self.artifacts) > MAXIMUM_PAGE_COUNT:
            raise ValueError("checkpoint page count exceeds its ceiling")
        if self.record_count != sum(item.row_count for item in self.artifacts):
            raise ValueError("checkpoint record count differs")
        if self.package_bytes != sum(item.byte_size for item in self.artifacts):
            raise ValueError("checkpoint byte count differs")
        if self.state == "complete":
            if self.next_request_path is not None or self.next_request_params:
                raise ValueError("complete checkpoint retains a next request")
        elif self.next_request_path is None or not self.next_request_params:
            raise ValueError("in-progress checkpoint lacks a next request")
        if self.artifacts:
            if self.last_observed_at != self.artifacts[-1].source_observed_at:
                raise ValueError("checkpoint last-observed time differs")
        elif self.last_observed_at is not None:
            raise ValueError("empty checkpoint has a last-observed time")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("checkpoint fingerprint differs")
        return self


class CorporateActionSourcePackageManifestV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-source-package/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    action_kind: CorporateActionSourceKind
    start_date: date
    end_date: date
    endpoint: str
    date_field: str
    page_limit: Literal[5000] = PAGE_LIMIT
    maximum_page_count: Literal[16] = MAXIMUM_PAGE_COUNT
    maximum_record_count: Literal[80000] = MAXIMUM_RECORD_COUNT
    minimum_request_interval_seconds: Literal[15] = (
        MINIMUM_REQUEST_INTERVAL_SECONDS
    )
    zero_automatic_retry: Literal[True] = True
    started_at: datetime
    completed_at: datetime
    artifacts: tuple[CorporateActionSourceArtifactV1, ...] = Field(min_length=1)
    request_count: int = Field(ge=1, le=MAXIMUM_PAGE_COUNT)
    record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    package_bytes: int = Field(ge=1, le=MAXIMUM_PACKAGE_BYTES)
    valid_effective_date_count: int = Field(ge=0)
    invalid_effective_date_count: int = Field(ge=0)
    out_of_scope_effective_date_count: Literal[0] = 0
    duplicate_source_action_id_count: int = Field(ge=0)
    field_presence_counts: tuple[tuple[str, int], ...]
    unexpected_field_counts: tuple[tuple[str, int], ...]
    pagination_complete: Literal[True] = True
    source_payload_retention: Literal["temporary_package_only"] = (
        "temporary_package_only"
    )
    identity_resolution_status: Literal["not_attempted"] = "not_attempted"
    research_eligibility: Literal["source_observation_only"] = (
        "source_observation_only"
    )
    request_id_retained: Literal[False] = False
    credential_material_retained: Literal[False] = False
    pagination_url_retained: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("started_at", "completed_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "CorporateActionSourcePackageManifestV1":
        if self.end_date < self.start_date:
            raise ValueError("corporate-action range is reversed")
        if self.completed_at < self.started_at:
            raise ValueError("package completion precedes start")
        if self.endpoint != _ENDPOINTS[self.action_kind]:
            raise ValueError("corporate-action endpoint differs")
        if self.date_field != _DATE_FIELDS[self.action_kind]:
            raise ValueError("corporate-action date field differs")
        sequences = tuple(item.sequence for item in self.artifacts)
        if sequences != tuple(range(1, len(self.artifacts) + 1)):
            raise ValueError("package page sequence is not contiguous")
        if self.request_count != len(self.artifacts):
            raise ValueError("package request count differs")
        if len({item.request_locator_sha256 for item in self.artifacts}) != len(
            self.artifacts
        ):
            raise ValueError("package request chain contains a loop")
        observation_times = tuple(item.source_observed_at for item in self.artifacts)
        if observation_times != tuple(sorted(observation_times)) or any(
            value < self.started_at or value > self.completed_at
            for value in observation_times
        ):
            raise ValueError("package observation times differ")
        if self.record_count != sum(item.row_count for item in self.artifacts):
            raise ValueError("package record count differs")
        if self.package_bytes != sum(item.byte_size for item in self.artifacts):
            raise ValueError("package byte count differs")
        if self.valid_effective_date_count + self.invalid_effective_date_count != (
            self.record_count
        ):
            raise ValueError("effective-date counts differ")
        known = _KNOWN_FIELDS[self.action_kind]
        if self.field_presence_counts != tuple(
            (field, dict(self.field_presence_counts).get(field, -1))
            for field in known
        ):
            raise ValueError("field-presence contract differs")
        if any(
            count < 0 or count > self.record_count
            for _, count in self.field_presence_counts
        ):
            raise ValueError("field-presence count is invalid")
        if tuple(sorted(self.unexpected_field_counts)) != (
            self.unexpected_field_counts
        ):
            raise ValueError("unexpected-field counts are not ordered")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("package fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class ValidatedCorporateActionSourcePackage:
    package_path: Path
    manifest: CorporateActionSourcePackageManifestV1
    pages: tuple[CorporateActionSourcePageV1, ...]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class CorporateActionSourcePackageResult:
    manifest: CorporateActionSourcePackageManifestV1
    package_path: Path
    manifest_sha256: str
    status: Literal["published", "already_present", "recovered_and_published"]


def fetch_historical_corporate_action_source_package(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    package_path: Path,
    rate_limiter: FixedIntervalRateLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    progress: ProgressCallback | None = None,
) -> CorporateActionSourcePackageResult:
    """Fetch or resume one split or dividend source package and reread it."""

    kind = CorporateActionSourceKind(action_kind)
    _validate_range(start_date, end_date)
    _validate_config(config)
    target = _validate_package_target(package_path, kind, start_date, end_date)
    now = clock or (lambda: datetime.now(UTC))
    limiter = rate_limiter or FixedIntervalRateLimiter()
    with _package_lock(target):
        partial = target.parent / f".{target.name}.partial"
        if target.exists():
            if partial.exists() or partial.is_symlink():
                raise HistoricalCorporateActionSourceError(
                    "completed and partial corporate-action packages coexist"
                )
            validated = read_historical_corporate_action_source_package(
                package_path=target,
                expected_action_kind=kind,
                expected_start_date=start_date,
                expected_end_date=end_date,
            )
            return _result(validated.manifest, target, "already_present")

        recovered = partial.exists()
        checkpoint = _load_or_create_checkpoint(
            partial=partial,
            action_kind=kind,
            start_date=start_date,
            end_date=end_date,
            now=now,
        )
        checkpoint = _adopt_exact_orphan_if_present(partial, checkpoint)
        if checkpoint.state == "complete":
            manifest = _finalize_partial(partial, target, checkpoint)
            return _result(manifest, target, "recovered_and_published")

        while checkpoint.state == "in_progress":
            if len(checkpoint.artifacts) >= MAXIMUM_PAGE_COUNT:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action pagination exceeds page ceiling"
                )
            limiter.wait_before_request()
            path = checkpoint.next_request_path
            if path is None:
                raise HistoricalCorporateActionSourceError(
                    "in-progress checkpoint has no request path"
                )
            params = dict(checkpoint.next_request_params)
            request_fingerprint = _request_locator_fingerprint(path, params)
            if request_fingerprint in {
                item.request_locator_sha256 for item in checkpoint.artifacts
            }:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action pagination loop detected"
                )
            response = transport.get_json(
                path,
                params=params,
                api_key=config.api_key,
                timeout_seconds=config.request_timeout_seconds,
                base_url=config.base_url,
            )
            observed_at = normalize_utc_datetime(now())
            page = _build_page(
                response=response,
                sequence=len(checkpoint.artifacts) + 1,
                action_kind=kind,
                start_date=start_date,
                end_date=end_date,
                request_locator_sha256=request_fingerprint,
                source_observed_at=observed_at,
            )
            page_bytes = _json_bytes(page.model_dump(mode="json"))
            if len(page_bytes) > MAXIMUM_PAGE_BYTES:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action page exceeds byte ceiling"
                )
            rows = _results(page.sanitized_response)
            if checkpoint.record_count + len(rows) > MAXIMUM_RECORD_COUNT:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action package exceeds record ceiling"
                )
            if checkpoint.package_bytes + len(page_bytes) > MAXIMUM_PACKAGE_BYTES:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action package exceeds byte ceiling"
                )
            artifact = _write_page(partial, page, page_bytes)
            checkpoint = _advance_checkpoint(checkpoint, page, artifact)
            _write_checkpoint(partial, checkpoint)
            if progress is not None:
                progress(artifact, checkpoint.record_count, checkpoint.package_bytes)

        manifest = _finalize_partial(partial, target, checkpoint)
        return _result(
            manifest,
            target,
            "recovered_and_published" if recovered else "published",
        )


def read_historical_corporate_action_source_package(
    *,
    package_path: Path,
    expected_action_kind: CorporateActionSourceKind,
    expected_start_date: date,
    expected_end_date: date,
) -> ValidatedCorporateActionSourcePackage:
    """Reread every package byte and validate pagination and aggregate facts."""

    kind = CorporateActionSourceKind(expected_action_kind)
    package = _validate_completed_package_path(
        package_path, kind, expected_start_date, expected_end_date
    )
    manifest_path = package / _MANIFEST_FILE
    manifest = _read_model(manifest_path, CorporateActionSourcePackageManifestV1)
    if (
        manifest.action_kind != kind
        or manifest.start_date != expected_start_date
        or manifest.end_date != expected_end_date
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action package scope differs"
        )
    checkpoint = _read_model(
        package / _CHECKPOINT_FILE, CorporateActionSourceCheckpointV1
    )
    if (
        checkpoint.state != "complete"
        or checkpoint.action_kind != manifest.action_kind
        or checkpoint.start_date != manifest.start_date
        or checkpoint.end_date != manifest.end_date
        or checkpoint.artifacts != manifest.artifacts
        or checkpoint.record_count != manifest.record_count
        or checkpoint.package_bytes != manifest.package_bytes
    ):
        raise HistoricalCorporateActionSourceError(
            "completed checkpoint differs from package manifest"
        )
    expected_files = {_MANIFEST_FILE, _CHECKPOINT_FILE} | {
        item.file_name for item in manifest.artifacts
    }
    _validate_file_set(package, expected_files, completed=True)
    summary, pages = _reread_artifacts(
        package,
        manifest.artifacts,
        kind,
        expected_start_date,
        expected_end_date,
    )
    if not pages or pages[-1].next_request_path is not None:
        raise HistoricalCorporateActionSourceError(
            "completed corporate-action pagination continues"
        )
    expected_summary = _summary_manifest_values(summary)
    for key, value in expected_summary.items():
        if getattr(manifest, key) != value:
            raise HistoricalCorporateActionSourceError(
                "corporate-action package aggregate differs"
            )
    return ValidatedCorporateActionSourcePackage(
        package_path=package,
        manifest=manifest,
        pages=pages,
        manifest_sha256=_sha256(
            _read_regular_file(manifest_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
        ),
    )


def _load_or_create_checkpoint(
    *,
    partial: Path,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    now: Callable[[], datetime],
) -> CorporateActionSourceCheckpointV1:
    if partial.exists():
        if partial.is_symlink() or not partial.is_dir():
            raise HistoricalCorporateActionSourceError(
                "corporate-action partial path is unsafe"
            )
        _require_mode(partial, 0o700)
        _remove_known_temporary_files(partial)
        checkpoint = _read_model(
            partial / _CHECKPOINT_FILE, CorporateActionSourceCheckpointV1
        )
        if (
            checkpoint.action_kind != action_kind
            or checkpoint.start_date != start_date
            or checkpoint.end_date != end_date
        ):
            raise HistoricalCorporateActionSourceError(
                "corporate-action checkpoint scope differs"
            )
        _reread_artifacts(
            partial, checkpoint.artifacts, action_kind, start_date, end_date
        )
        return checkpoint

    partial.mkdir(mode=0o700)
    started_at = normalize_utc_datetime(now())
    path, params = _initial_request(action_kind, start_date, end_date)
    checkpoint = _make_checkpoint(
        state="in_progress",
        action_kind=action_kind,
        start_date=start_date,
        end_date=end_date,
        started_at=started_at,
        last_observed_at=None,
        artifacts=(),
        next_request_path=path,
        next_request_params=tuple(sorted(params.items())),
    )
    _write_checkpoint(partial, checkpoint)
    return checkpoint


def _adopt_exact_orphan_if_present(
    partial: Path,
    checkpoint: CorporateActionSourceCheckpointV1,
) -> CorporateActionSourceCheckpointV1:
    expected = {item.file_name for item in checkpoint.artifacts}
    actual = {
        path.name
        for path in partial.iterdir()
        if path.name.startswith(_PAGE_FILE_PREFIX)
        and path.name.endswith(_PAGE_FILE_SUFFIX)
    }
    extras = actual - expected
    if not extras:
        return checkpoint
    expected_name = _page_file_name(len(checkpoint.artifacts) + 1)
    if extras != {expected_name} or checkpoint.state != "in_progress":
        raise HistoricalCorporateActionSourceError(
            "corporate-action partial package has unexpected pages"
        )
    page_path = partial / expected_name
    page = _read_model(page_path, CorporateActionSourcePageV1)
    expected_request = _request_locator_fingerprint(
        checkpoint.next_request_path or "", dict(checkpoint.next_request_params)
    )
    if (
        page.action_kind != checkpoint.action_kind
        or page.request_locator_sha256 != expected_request
    ):
        raise HistoricalCorporateActionSourceError(
            "orphan corporate-action page request binding differs"
        )
    raw = _read_regular_file(page_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
    artifact = _artifact_from_page(page, raw)
    updated = _advance_checkpoint(checkpoint, page, artifact)
    _write_checkpoint(partial, updated)
    return updated


def _advance_checkpoint(
    checkpoint: CorporateActionSourceCheckpointV1,
    page: CorporateActionSourcePageV1,
    artifact: CorporateActionSourceArtifactV1,
) -> CorporateActionSourceCheckpointV1:
    if artifact.sequence != len(checkpoint.artifacts) + 1:
        raise HistoricalCorporateActionSourceError(
            "corporate-action artifact sequence differs"
        )
    complete = page.next_request_path is None
    return _make_checkpoint(
        state="complete" if complete else "in_progress",
        action_kind=checkpoint.action_kind,
        start_date=checkpoint.start_date,
        end_date=checkpoint.end_date,
        started_at=checkpoint.started_at,
        last_observed_at=page.source_observed_at,
        artifacts=checkpoint.artifacts + (artifact,),
        next_request_path=page.next_request_path,
        next_request_params=page.next_request_params,
    )


def _make_checkpoint(
    *,
    state: Literal["in_progress", "complete"],
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    started_at: datetime,
    last_observed_at: datetime | None,
    artifacts: tuple[CorporateActionSourceArtifactV1, ...],
    next_request_path: str | None,
    next_request_params: tuple[tuple[str, str], ...],
) -> CorporateActionSourceCheckpointV1:
    values = {
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "state": state,
        "provider_id": MASSIVE_PROVIDER_ID,
        "action_kind": action_kind,
        "start_date": start_date,
        "end_date": end_date,
        "started_at": started_at,
        "last_observed_at": last_observed_at,
        "artifacts": artifacts,
        "next_request_path": next_request_path,
        "next_request_params": next_request_params,
        "record_count": sum(item.row_count for item in artifacts),
        "package_bytes": sum(item.byte_size for item in artifacts),
    }
    return CorporateActionSourceCheckpointV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(_json_ready(values))}
    )


def _build_page(
    *,
    response: MassiveJson,
    sequence: int,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    request_locator_sha256: str,
    source_observed_at: datetime,
) -> CorporateActionSourcePageV1:
    safe = _sanitize_response(response)
    rows = _results(safe)
    if len(rows) > PAGE_LIMIT:
        raise HistoricalCorporateActionSourceError(
            "corporate-action page exceeds row ceiling"
        )
    _validate_row_scope(rows, action_kind, start_date, end_date)
    next_url = response.get("next_url")
    if next_url is None:
        next_path = None
        next_params: tuple[tuple[str, str], ...] = ()
        next_fingerprint = None
    else:
        path, params = _next_request(
            next_url,
            action_kind=action_kind,
            start_date=start_date,
            end_date=end_date,
        )
        next_path = path
        next_params = tuple(sorted(params.items()))
        next_fingerprint = _request_locator_fingerprint(path, params)
    return CorporateActionSourcePageV1(
        sequence=sequence,
        action_kind=action_kind,
        source_observed_at=source_observed_at,
        request_locator_sha256=request_locator_sha256,
        next_request_path=next_path,
        next_request_params=next_params,
        next_request_locator_sha256=next_fingerprint,
        sanitized_response=safe,
    )


def _sanitize_response(response: Mapping[str, object]) -> dict[str, object]:
    status_value = response.get("status")
    if not isinstance(status_value, str) or status_value.upper() != "OK":
        raise HistoricalCorporateActionSourceError(
            "corporate-action response status is not OK"
        )
    safe = {
        str(key): value
        for key, value in response.items()
        if str(key).strip().lower() not in {"request_id", "next_url"}
    }
    _assert_no_secret_material(safe)
    return safe


def _results(response: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = response.get("results")
    if not isinstance(value, list) or any(
        not isinstance(item, Mapping) for item in value
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action results are malformed"
        )
    return tuple(value)


def _validate_row_scope(
    rows: tuple[Mapping[str, object], ...],
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> None:
    valid_dates: list[date] = []
    date_field = _DATE_FIELDS[action_kind]
    for row in rows:
        parsed = _parse_date(row.get(date_field))
        if parsed is None:
            continue
        if parsed < start_date or parsed > end_date:
            raise HistoricalCorporateActionSourceError(
                "corporate-action page contains an out-of-scope date"
            )
        valid_dates.append(parsed)
    if valid_dates != sorted(valid_dates):
        raise HistoricalCorporateActionSourceError(
            "corporate-action page date ordering differs"
        )


def _initial_request(
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> tuple[str, dict[str, str]]:
    date_field = _DATE_FIELDS[action_kind]
    return _ENDPOINTS[action_kind], {
        f"{date_field}.gte": start_date.isoformat(),
        f"{date_field}.lte": end_date.isoformat(),
        "limit": str(PAGE_LIMIT),
        "sort": f"{date_field}.asc",
    }


def _next_request(
    value: object,
    *,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> tuple[str, dict[str, str]]:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalCorporateActionSourceError(
            "corporate-action next URL is invalid"
        )
    parsed = urlparse(value)
    if parsed.scheme not in {"", "https"} or (
        parsed.netloc and parsed.netloc != "api.massive.com"
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action pagination host changed"
        )
    endpoint, required = _initial_request(action_kind, start_date, end_date)
    if parsed.path != endpoint:
        raise HistoricalCorporateActionSourceError(
            "corporate-action pagination path changed"
        )
    params = {
        key: item
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if key.strip().lower() not in {"apikey", "api_key", "access_token"}
    }
    for key, expected in required.items():
        actual = params.get(key)
        if actual is not None and actual != expected:
            raise HistoricalCorporateActionSourceError(
                "corporate-action pagination scope changed"
            )
        params[key] = expected
    if not any(key not in required for key in params):
        raise HistoricalCorporateActionSourceError(
            "corporate-action pagination cursor is absent"
        )
    return parsed.path, params


def _finalize_partial(
    partial: Path,
    target: Path,
    checkpoint: CorporateActionSourceCheckpointV1,
) -> CorporateActionSourcePackageManifestV1:
    if checkpoint.state != "complete" or checkpoint.last_observed_at is None:
        raise HistoricalCorporateActionSourceError(
            "corporate-action source package is incomplete"
        )
    summary, pages = _reread_artifacts(
        partial,
        checkpoint.artifacts,
        checkpoint.action_kind,
        checkpoint.start_date,
        checkpoint.end_date,
    )
    if not pages or pages[-1].next_request_path is not None:
        raise HistoricalCorporateActionSourceError(
            "corporate-action source pagination is incomplete"
        )
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": MASSIVE_PROVIDER_ID,
        "action_kind": checkpoint.action_kind,
        "start_date": checkpoint.start_date,
        "end_date": checkpoint.end_date,
        "endpoint": _ENDPOINTS[checkpoint.action_kind],
        "date_field": _DATE_FIELDS[checkpoint.action_kind],
        "page_limit": PAGE_LIMIT,
        "maximum_page_count": MAXIMUM_PAGE_COUNT,
        "maximum_record_count": MAXIMUM_RECORD_COUNT,
        "minimum_request_interval_seconds": MINIMUM_REQUEST_INTERVAL_SECONDS,
        "zero_automatic_retry": True,
        "started_at": checkpoint.started_at,
        "completed_at": checkpoint.last_observed_at,
        "artifacts": checkpoint.artifacts,
        "request_count": len(checkpoint.artifacts),
        "record_count": checkpoint.record_count,
        "package_bytes": checkpoint.package_bytes,
        **_summary_manifest_values(summary),
        "pagination_complete": True,
        "source_payload_retention": "temporary_package_only",
        "identity_resolution_status": "not_attempted",
        "research_eligibility": "source_observation_only",
        "request_id_retained": False,
        "credential_material_retained": False,
        "pagination_url_retained": False,
        "canonical_data_write_count": 0,
        "adjustment_ledger_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    manifest = CorporateActionSourcePackageManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(_json_ready(values))}
    )
    manifest_path = partial / _MANIFEST_FILE
    if manifest_path.exists():
        existing = _read_model(
            manifest_path, CorporateActionSourcePackageManifestV1
        )
        if existing != manifest:
            raise HistoricalCorporateActionSourceError(
                "recovered corporate-action package manifest differs"
            )
    else:
        _write_immutable_json(manifest_path, manifest.model_dump(mode="json"))
    (partial / _CHECKPOINT_FILE).chmod(0o400)
    _fsync_directory(partial)
    if target.exists() or target.is_symlink():
        raise HistoricalCorporateActionSourceError(
            "corporate-action package target appeared"
        )
    partial.replace(target)
    _fsync_directory(target.parent)
    return read_historical_corporate_action_source_package(
        package_path=target,
        expected_action_kind=checkpoint.action_kind,
        expected_start_date=checkpoint.start_date,
        expected_end_date=checkpoint.end_date,
    ).manifest


@dataclass(frozen=True, slots=True)
class _SourceSummary:
    record_count: int
    valid_effective_date_count: int
    invalid_effective_date_count: int
    duplicate_source_action_id_count: int
    field_presence_counts: tuple[tuple[str, int], ...]
    unexpected_field_counts: tuple[tuple[str, int], ...]


def _reread_artifacts(
    root: Path,
    artifacts: tuple[CorporateActionSourceArtifactV1, ...],
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> tuple[_SourceSummary, tuple[CorporateActionSourcePageV1, ...]]:
    path, params = _initial_request(action_kind, start_date, end_date)
    rows_total = 0
    source_action_ids: list[str] = []
    valid_dates: list[date] = []
    invalid_date_count = 0
    known = _KNOWN_FIELDS[action_kind]
    field_counts = {field: 0 for field in known}
    unexpected_counts: dict[str, int] = {}
    pages: list[CorporateActionSourcePageV1] = []
    for artifact in artifacts:
        expected_request = _request_locator_fingerprint(path, params)
        if artifact.request_locator_sha256 != expected_request:
            raise HistoricalCorporateActionSourceError(
                "corporate-action request chain differs"
            )
        page_path = root / artifact.file_name
        raw = _read_regular_file(page_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
        if len(raw) != artifact.byte_size or _sha256(raw) != artifact.physical_sha256:
            raise HistoricalCorporateActionSourceError(
                "corporate-action page custody differs"
            )
        page = _parse_model(raw, CorporateActionSourcePageV1)
        if (
            page.sequence != artifact.sequence
            or page.action_kind != action_kind
            or page.request_locator_sha256 != artifact.request_locator_sha256
            or page.next_request_locator_sha256
            != artifact.next_request_locator_sha256
            or page.source_observed_at != artifact.source_observed_at
        ):
            raise HistoricalCorporateActionSourceError(
                "corporate-action page manifest binding differs"
            )
        _assert_no_secret_material(page.sanitized_response)
        rows = _results(page.sanitized_response)
        if len(rows) != artifact.row_count:
            raise HistoricalCorporateActionSourceError(
                "corporate-action page row count differs"
            )
        _validate_row_scope(rows, action_kind, start_date, end_date)
        rows_total += len(rows)
        for row in rows:
            source_action_id = row.get("id")
            if isinstance(source_action_id, str) and source_action_id.strip():
                source_action_ids.append(source_action_id.strip())
            parsed_date = _parse_date(row.get(_DATE_FIELDS[action_kind]))
            if parsed_date is None:
                invalid_date_count += 1
            else:
                valid_dates.append(parsed_date)
            for field in known:
                if _present(row.get(field)):
                    field_counts[field] += 1
            for field in row:
                field_name = str(field)
                if field_name not in field_counts:
                    unexpected_counts[field_name] = (
                        unexpected_counts.get(field_name, 0) + 1
                    )
        pages.append(page)
        if page.next_request_path is None:
            if artifact.sequence != len(artifacts):
                raise HistoricalCorporateActionSourceError(
                    "corporate-action pages continue after natural completion"
                )
        else:
            path = page.next_request_path
            params = dict(page.next_request_params)
    if valid_dates != sorted(valid_dates):
        raise HistoricalCorporateActionSourceError(
            "corporate-action package date ordering differs"
        )
    return (
        _SourceSummary(
            record_count=rows_total,
            valid_effective_date_count=len(valid_dates),
            invalid_effective_date_count=invalid_date_count,
            duplicate_source_action_id_count=(
                len(source_action_ids) - len(set(source_action_ids))
            ),
            field_presence_counts=tuple(
                (field, field_counts[field]) for field in known
            ),
            unexpected_field_counts=tuple(sorted(unexpected_counts.items())),
        ),
        tuple(pages),
    )


def _summary_manifest_values(summary: _SourceSummary) -> dict[str, object]:
    return {
        "valid_effective_date_count": summary.valid_effective_date_count,
        "invalid_effective_date_count": summary.invalid_effective_date_count,
        "out_of_scope_effective_date_count": 0,
        "duplicate_source_action_id_count": (
            summary.duplicate_source_action_id_count
        ),
        "field_presence_counts": summary.field_presence_counts,
        "unexpected_field_counts": summary.unexpected_field_counts,
    }


def _write_page(
    partial: Path,
    page: CorporateActionSourcePageV1,
    payload: bytes,
) -> CorporateActionSourceArtifactV1:
    target = partial / _page_file_name(page.sequence)
    _write_immutable_bytes(target, payload)
    return _artifact_from_page(page, payload)


def _artifact_from_page(
    page: CorporateActionSourcePageV1,
    payload: bytes,
) -> CorporateActionSourceArtifactV1:
    return CorporateActionSourceArtifactV1(
        sequence=page.sequence,
        file_name=_page_file_name(page.sequence),
        request_locator_sha256=page.request_locator_sha256,
        next_request_locator_sha256=page.next_request_locator_sha256,
        source_observed_at=page.source_observed_at,
        row_count=len(_results(page.sanitized_response)),
        byte_size=len(payload),
        physical_sha256=_sha256(payload),
    )


def _write_checkpoint(
    partial: Path,
    checkpoint: CorporateActionSourceCheckpointV1,
) -> None:
    target = partial / _CHECKPOINT_FILE
    temporary = partial / f".{_CHECKPOINT_FILE}.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise HistoricalCorporateActionSourceError(
            "corporate-action checkpoint staging exists"
        )
    payload = _json_bytes(checkpoint.model_dump(mode="json"))
    _write_new_bytes(temporary, payload, 0o600)
    temporary.replace(target)
    target.chmod(0o600)
    _fsync_directory(partial)


def _write_immutable_json(path: Path, value: object) -> None:
    _write_immutable_bytes(path, _json_bytes(value))


def _write_immutable_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    if (
        path.exists()
        or path.is_symlink()
        or temporary.exists()
        or temporary.is_symlink()
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action immutable source target exists"
        )
    _write_new_bytes(temporary, payload, 0o400)
    temporary.replace(path)
    _fsync_directory(path.parent)


def _write_new_bytes(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(mode)


def _remove_known_temporary_files(partial: Path) -> None:
    allowed = {f".{_CHECKPOINT_FILE}.tmp"}
    allowed.update(
        f".{_page_file_name(sequence)}.tmp"
        for sequence in range(1, MAXIMUM_PAGE_COUNT + 1)
    )
    for path in partial.iterdir():
        if path.name not in allowed:
            continue
        if path.is_symlink() or not path.is_file():
            raise HistoricalCorporateActionSourceError(
                "corporate-action staging residue is unsafe"
            )
        path.unlink()
    _fsync_directory(partial)


def _validate_file_set(root: Path, expected: set[str], *, completed: bool) -> None:
    actual: set[str] = set()
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise HistoricalCorporateActionSourceError(
                "corporate-action package contains an unsafe entry"
            )
        actual.add(path.name)
        expected_mode = 0o400 if completed else (
            0o600 if path.name == _CHECKPOINT_FILE else 0o400
        )
        _require_mode(path, expected_mode)
    if actual != expected:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package file set differs"
        )


def _validate_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HistoricalCorporateActionSourceError(
            "corporate-action range is reversed"
        )
    if end_date >= date.today():
        raise HistoricalCorporateActionSourceError(
            "corporate-action range end must be historical"
        )


def _expected_target_name(
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> str:
    return f"{action_kind.value}={start_date.isoformat()}_{end_date.isoformat()}"


def _validate_package_target(
    path: Path,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> Path:
    target = path.absolute()
    if Path("/tmp") not in target.parents or target.name != _expected_target_name(
        action_kind, start_date, end_date
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action package must use its exact /tmp range path"
        )
    parent = target.parent
    if parent.exists():
        if parent.is_symlink() or not parent.is_dir():
            raise HistoricalCorporateActionSourceError(
                "corporate-action package parent is unsafe"
            )
    else:
        if not parent.parent.exists() or parent.parent.is_symlink():
            raise HistoricalCorporateActionSourceError(
                "corporate-action package parent boundary is unavailable"
            )
        parent.mkdir(mode=0o700)
    _require_mode(parent, 0o700)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise HistoricalCorporateActionSourceError(
                "corporate-action package target is unsafe"
            )
    partial = parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        if partial.is_symlink() or not partial.is_dir():
            raise HistoricalCorporateActionSourceError(
                "corporate-action partial target is unsafe"
            )
    return target


def _validate_completed_package_path(
    path: Path,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> Path:
    target = _validate_package_target(path, action_kind, start_date, end_date)
    if target.is_symlink() or not target.is_dir():
        raise HistoricalCorporateActionSourceError(
            "corporate-action completed package is unavailable"
        )
    _require_mode(target, 0o700)
    return target


def _validate_config(config: MassiveProviderConfig) -> None:
    if urlparse(config.base_url).scheme != "https" or (
        urlparse(config.base_url).netloc.lower() != "api.massive.com"
    ):
        raise HistoricalCorporateActionSourceError(
            "corporate-action source requires the approved Massive HTTPS host"
        )


@contextmanager
def _package_lock(target: Path) -> Iterator[None]:
    lock_path = target.parent / f".{target.name}.lock"
    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package is already locked"
        ) from exc
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def _read_model(path: Path, model: type[BaseModel]):
    raw = _read_regular_file(path, maximum_bytes=MAXIMUM_PAGE_BYTES)
    return _parse_model(raw, model)


def _parse_model(raw: bytes, model: type[BaseModel]):
    try:
        value = json.loads(raw.decode("utf-8"))
        return model.model_validate(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package document is invalid"
        ) from exc


def _read_regular_file(path: Path, *, maximum_bytes: int) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package file is missing"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise HistoricalCorporateActionSourceError(
            "corporate-action package file is unsafe"
        )
    if metadata.st_size < 1 or metadata.st_size > maximum_bytes:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package file size is invalid"
        )
    return path.read_bytes()


def _assert_no_secret_material(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_KEYS:
                raise HistoricalCorporateActionSourceError(
                    "corporate-action source contains forbidden metadata"
                )
            _assert_no_secret_material(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_secret_material(item)


def _present(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _request_locator_fingerprint(path: str, params: Mapping[str, object]) -> str:
    return _fingerprint(
        {
            "path": path,
            "params": tuple(sorted((str(key), str(value)) for key, value in params.items())),
        }
    )


def _fingerprint(value: object) -> str:
    return _sha256(_json_bytes(value))


def _json_ready(value: object) -> object:
    return to_jsonable_python(value)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _page_file_name(sequence: int) -> str:
    return f"{_PAGE_FILE_PREFIX}{sequence:05d}{_PAGE_FILE_SUFFIX}"


def _require_mode(path: Path, expected: int) -> None:
    actual = stat.S_IMODE(path.lstat().st_mode)
    if actual != expected:
        raise HistoricalCorporateActionSourceError(
            "corporate-action package permissions differ"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _result(
    manifest: CorporateActionSourcePackageManifestV1,
    package_path: Path,
    status: Literal["published", "already_present", "recovered_and_published"],
) -> CorporateActionSourcePackageResult:
    manifest_sha256 = _sha256(
        _read_regular_file(
            package_path / _MANIFEST_FILE,
            maximum_bytes=MAXIMUM_PAGE_BYTES,
        )
    )
    return CorporateActionSourcePackageResult(
        manifest=manifest,
        package_path=package_path,
        manifest_sha256=manifest_sha256,
        status=status,
    )
