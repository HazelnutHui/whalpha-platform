"""Resumable temporary acquisition and private reread of inactive listings."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
    MassiveParams,
)


CONTRACT_VERSION = "historical-inactive-lifecycle-source-package/1.0"
PAGE_CONTRACT_VERSION = "historical-inactive-lifecycle-source-page/1.0"
CHECKPOINT_CONTRACT_VERSION = "historical-inactive-lifecycle-source-checkpoint/1.0"
ALL_TICKERS_PATH = "/v3/reference/tickers"
PAGE_LIMIT = 1_000
MAXIMUM_PAGE_COUNT = 100
MAXIMUM_RECORD_COUNT = 100_000
MAXIMUM_PAGE_BYTES = 8 * 1024 * 1024
MAXIMUM_PACKAGE_BYTES = 512 * 1024 * 1024
MINIMUM_REQUEST_INTERVAL_SECONDS = 15
_PAGE_FILE_PREFIX = "response-"
_PAGE_FILE_SUFFIX = ".json"
_CHECKPOINT_FILE = "checkpoint.json"
_MANIFEST_FILE = "package.json"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_LIFECYCLE_FIELDS = (
    "delisted_utc",
    "last_updated_utc",
    "cik",
    "composite_figi",
    "share_class_figi",
)
_FORBIDDEN_KEYS = {"authorization", "api_key", "apikey", "access_token", "request_id"}


class HistoricalInactiveLifecycleSourceError(RuntimeError):
    """Raised when inactive lifecycle source custody cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class ValidatedInactiveLifecycleSourcePackage:
    """Formally reread manifest and source pages for downstream normalization."""

    package_path: Path
    manifest: InactiveLifecycleSourcePackageManifestV1
    pages: tuple[InactiveLifecycleSourcePageV1, ...]
    manifest_sha256: str


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class InactiveLifecycleSourcePageV1(FrozenModel):
    contract_version: Literal[
        "historical-inactive-lifecycle-source-page/1.0"
    ] = PAGE_CONTRACT_VERSION
    sequence: int = Field(ge=1)
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
    def next_request_reconciles(self) -> "InactiveLifecycleSourcePageV1":
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


class InactiveLifecycleSourceArtifactV1(FrozenModel):
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
    def file_identity_reconciles(self) -> "InactiveLifecycleSourceArtifactV1":
        if self.file_name != _page_file_name(self.sequence):
            raise ValueError("source page file identity differs")
        return self


ProgressCallback = Callable[[InactiveLifecycleSourceArtifactV1, int, int], None]


class InactiveLifecycleSourceCheckpointV1(FrozenModel):
    contract_version: Literal[
        "historical-inactive-lifecycle-source-checkpoint/1.0"
    ] = CHECKPOINT_CONTRACT_VERSION
    state: Literal["in_progress", "complete"]
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    anchor_date: date
    started_at: datetime
    last_observed_at: datetime | None = None
    artifacts: tuple[InactiveLifecycleSourceArtifactV1, ...] = ()
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
    def checkpoint_reconciles(self) -> "InactiveLifecycleSourceCheckpointV1":
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


class InactiveLifecycleSourcePackageManifestV1(FrozenModel):
    contract_version: Literal[
        "historical-inactive-lifecycle-source-package/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    anchor_date: date
    endpoint: Literal["/v3/reference/tickers"] = ALL_TICKERS_PATH
    active_filter: Literal[False] = False
    page_limit: Literal[1000] = PAGE_LIMIT
    maximum_page_count: Literal[100] = MAXIMUM_PAGE_COUNT
    maximum_record_count: Literal[100000] = MAXIMUM_RECORD_COUNT
    minimum_request_interval_seconds: Literal[15] = (
        MINIMUM_REQUEST_INTERVAL_SECONDS
    )
    zero_automatic_retry: Literal[True] = True
    started_at: datetime
    completed_at: datetime
    artifacts: tuple[InactiveLifecycleSourceArtifactV1, ...] = Field(min_length=1)
    request_count: int = Field(ge=1, le=MAXIMUM_PAGE_COUNT)
    record_count: int = Field(ge=1, le=MAXIMUM_RECORD_COUNT)
    package_bytes: int = Field(ge=1, le=MAXIMUM_PACKAGE_BYTES)
    active_false_count: int = Field(ge=0)
    active_true_conflict_count: Literal[0] = 0
    active_missing_count: Literal[0] = 0
    duplicate_ticker_count: int = Field(ge=0)
    field_presence_counts: tuple[tuple[str, int], ...]
    pagination_complete: Literal[True] = True
    source_payload_retention: Literal["temporary_package_only"] = (
        "temporary_package_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    request_id_retained: Literal[False] = False
    credential_material_retained: Literal[False] = False
    pagination_url_retained: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
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
    def manifest_reconciles(self) -> "InactiveLifecycleSourcePackageManifestV1":
        if self.completed_at < self.started_at:
            raise ValueError("package completion precedes start")
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
        if self.active_false_count != self.record_count:
            raise ValueError("package contains non-inactive source rows")
        if self.field_presence_counts != tuple(
            (field, dict(self.field_presence_counts).get(field, -1))
            for field in _LIFECYCLE_FIELDS
        ):
            raise ValueError("lifecycle field-presence contract differs")
        if any(
            count < 0 or count > self.record_count
            for _, count in self.field_presence_counts
        ):
            raise ValueError("lifecycle field-presence count is invalid")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("package fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class InactiveLifecycleSourcePackageResult:
    manifest: InactiveLifecycleSourcePackageManifestV1
    package_path: Path
    manifest_sha256: str
    status: Literal["published", "already_present", "recovered_and_published"]


def fetch_historical_inactive_lifecycle_source_package(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    anchor_date: date,
    package_path: Path,
    rate_limiter: FixedIntervalRateLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    progress: ProgressCallback | None = None,
) -> InactiveLifecycleSourcePackageResult:
    """Fetch or resume one inactive source package and formally reread it."""

    if anchor_date >= date.today():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle anchor must be historical"
        )
    _validate_config(config)
    target = _validate_package_target(package_path, anchor_date)
    now = clock or (lambda: datetime.now(UTC))
    limiter = rate_limiter or FixedIntervalRateLimiter()
    with _package_lock(target):
        partial = target.parent / f".{target.name}.partial"
        if target.exists():
            if partial.exists() or partial.is_symlink():
                raise HistoricalInactiveLifecycleSourceError(
                    "completed and partial lifecycle packages coexist"
                )
            manifest = read_historical_inactive_lifecycle_source_package(
                package_path=target,
                expected_anchor_date=anchor_date,
            )
            return _result(manifest, target, "already_present")

        recovered = partial.exists()
        checkpoint = _load_or_create_checkpoint(
            partial=partial,
            anchor_date=anchor_date,
            now=now,
        )
        checkpoint = _adopt_exact_orphan_if_present(partial, checkpoint)
        if checkpoint.state == "complete":
            manifest = _finalize_partial(partial, target, checkpoint)
            return _result(manifest, target, "recovered_and_published")

        while checkpoint.state == "in_progress":
            if len(checkpoint.artifacts) >= MAXIMUM_PAGE_COUNT:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle pagination exceeds page ceiling"
                )
            limiter.wait_before_request()
            path = checkpoint.next_request_path
            if path is None:
                raise HistoricalInactiveLifecycleSourceError(
                    "in-progress checkpoint has no request path"
                )
            params = dict(checkpoint.next_request_params)
            request_fingerprint = _request_locator_fingerprint(path, params)
            if request_fingerprint in {
                item.request_locator_sha256 for item in checkpoint.artifacts
            }:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle pagination loop detected"
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
                anchor_date=anchor_date,
                request_locator_sha256=request_fingerprint,
                source_observed_at=observed_at,
            )
            page_bytes = _json_bytes(page.model_dump(mode="json"))
            if len(page_bytes) > MAXIMUM_PAGE_BYTES:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle page exceeds byte ceiling"
                )
            rows = _results(page.sanitized_response)
            if checkpoint.record_count + len(rows) > MAXIMUM_RECORD_COUNT:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle package exceeds record ceiling"
                )
            if checkpoint.package_bytes + len(page_bytes) > MAXIMUM_PACKAGE_BYTES:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle package exceeds byte ceiling"
                )
            artifact = _write_page(partial, page, page_bytes)
            checkpoint = _advance_checkpoint(checkpoint, page, artifact)
            _write_checkpoint(partial, checkpoint)
            if progress is not None:
                progress(
                    artifact,
                    checkpoint.record_count,
                    checkpoint.package_bytes,
                )

        manifest = _finalize_partial(partial, target, checkpoint)
        return _result(
            manifest,
            target,
            "recovered_and_published" if recovered else "published",
        )


def read_historical_inactive_lifecycle_source_package(
    *,
    package_path: Path,
    expected_anchor_date: date,
    approved_custody_root: Path | None = None,
) -> InactiveLifecycleSourcePackageManifestV1:
    """Reread every package byte and validate pagination plus aggregate facts."""

    package = _validate_completed_package_path(
        package_path,
        expected_anchor_date,
        approved_custody_root=approved_custody_root,
    )
    manifest_path = package / _MANIFEST_FILE
    manifest = _read_model(manifest_path, InactiveLifecycleSourcePackageManifestV1)
    if manifest.anchor_date != expected_anchor_date:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle package anchor differs"
        )
    checkpoint = _read_model(
        package / _CHECKPOINT_FILE, InactiveLifecycleSourceCheckpointV1
    )
    if (
        checkpoint.state != "complete"
        or checkpoint.anchor_date != manifest.anchor_date
        or checkpoint.artifacts != manifest.artifacts
        or checkpoint.record_count != manifest.record_count
        or checkpoint.package_bytes != manifest.package_bytes
    ):
        raise HistoricalInactiveLifecycleSourceError(
            "completed checkpoint differs from package manifest"
        )
    expected_files = {_MANIFEST_FILE, _CHECKPOINT_FILE} | {
        item.file_name for item in manifest.artifacts
    }
    _validate_file_set(package, expected_files, completed=True)
    summary, pages = _reread_artifacts(package, manifest.artifacts, expected_anchor_date)
    if pages[-1].next_request_path is not None:
        raise HistoricalInactiveLifecycleSourceError(
            "completed package pagination continues"
        )
    expected_summary = _summary_manifest_values(summary)
    for key, value in expected_summary.items():
        if getattr(manifest, key) != value:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package aggregate differs"
            )
    return manifest


def read_historical_inactive_lifecycle_source_payloads(
    *,
    package_path: Path,
    expected_anchor_date: date,
    approved_custody_root: Path | None = None,
) -> ValidatedInactiveLifecycleSourcePackage:
    """Return source pages only after the complete package passes formal reread."""

    manifest = read_historical_inactive_lifecycle_source_package(
        package_path=package_path,
        expected_anchor_date=expected_anchor_date,
        approved_custody_root=approved_custody_root,
    )
    package = _validate_completed_package_path(
        package_path,
        expected_anchor_date,
        approved_custody_root=approved_custody_root,
    )
    _, pages = _reread_artifacts(
        package,
        manifest.artifacts,
        expected_anchor_date,
    )
    return ValidatedInactiveLifecycleSourcePackage(
        package_path=package,
        manifest=manifest,
        pages=pages,
        manifest_sha256=_sha256(
            _read_regular_file(
                package / _MANIFEST_FILE,
                maximum_bytes=MAXIMUM_PAGE_BYTES,
            )
        ),
    )


def _load_or_create_checkpoint(
    *,
    partial: Path,
    anchor_date: date,
    now: Callable[[], datetime],
) -> InactiveLifecycleSourceCheckpointV1:
    if partial.exists():
        if partial.is_symlink() or not partial.is_dir():
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle partial path is unsafe"
            )
        _require_mode(partial, 0o700)
        _remove_known_temporary_files(partial)
        checkpoint = _read_model(
            partial / _CHECKPOINT_FILE, InactiveLifecycleSourceCheckpointV1
        )
        if checkpoint.anchor_date != anchor_date:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle checkpoint anchor differs"
            )
        _reread_artifacts(partial, checkpoint.artifacts, anchor_date)
        return checkpoint

    partial.mkdir(mode=0o700)
    started_at = normalize_utc_datetime(now())
    path, params = _initial_request(anchor_date)
    checkpoint = _make_checkpoint(
        state="in_progress",
        anchor_date=anchor_date,
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
    checkpoint: InactiveLifecycleSourceCheckpointV1,
) -> InactiveLifecycleSourceCheckpointV1:
    expected = {item.file_name for item in checkpoint.artifacts}
    actual = {
        path.name
        for path in partial.iterdir()
        if path.name.startswith(_PAGE_FILE_PREFIX) and path.name.endswith(_PAGE_FILE_SUFFIX)
    }
    extras = actual - expected
    if not extras:
        return checkpoint
    expected_name = _page_file_name(len(checkpoint.artifacts) + 1)
    if extras != {expected_name} or checkpoint.state != "in_progress":
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle partial package has unexpected pages"
        )
    page_path = partial / expected_name
    page = _read_model(page_path, InactiveLifecycleSourcePageV1)
    expected_request = _request_locator_fingerprint(
        checkpoint.next_request_path or "", dict(checkpoint.next_request_params)
    )
    if page.request_locator_sha256 != expected_request:
        raise HistoricalInactiveLifecycleSourceError(
            "orphan source page request binding differs"
        )
    raw = _read_regular_file(page_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
    artifact = _artifact_from_page(page, raw)
    updated = _advance_checkpoint(checkpoint, page, artifact)
    _write_checkpoint(partial, updated)
    return updated


def _advance_checkpoint(
    checkpoint: InactiveLifecycleSourceCheckpointV1,
    page: InactiveLifecycleSourcePageV1,
    artifact: InactiveLifecycleSourceArtifactV1,
) -> InactiveLifecycleSourceCheckpointV1:
    if artifact.sequence != len(checkpoint.artifacts) + 1:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle artifact sequence differs"
        )
    complete = page.next_request_path is None
    return _make_checkpoint(
        state="complete" if complete else "in_progress",
        anchor_date=checkpoint.anchor_date,
        started_at=checkpoint.started_at,
        last_observed_at=page.source_observed_at,
        artifacts=checkpoint.artifacts + (artifact,),
        next_request_path=page.next_request_path,
        next_request_params=page.next_request_params,
    )


def _make_checkpoint(
    *,
    state: Literal["in_progress", "complete"],
    anchor_date: date,
    started_at: datetime,
    last_observed_at: datetime | None,
    artifacts: tuple[InactiveLifecycleSourceArtifactV1, ...],
    next_request_path: str | None,
    next_request_params: tuple[tuple[str, str], ...],
) -> InactiveLifecycleSourceCheckpointV1:
    values = {
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "state": state,
        "provider_id": MASSIVE_PROVIDER_ID,
        "anchor_date": anchor_date,
        "started_at": started_at,
        "last_observed_at": last_observed_at,
        "artifacts": artifacts,
        "next_request_path": next_request_path,
        "next_request_params": next_request_params,
        "record_count": sum(item.row_count for item in artifacts),
        "package_bytes": sum(item.byte_size for item in artifacts),
    }
    return InactiveLifecycleSourceCheckpointV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(_json_ready(values))}
    )


def _build_page(
    *,
    response: MassiveJson,
    sequence: int,
    anchor_date: date,
    request_locator_sha256: str,
    source_observed_at: datetime,
) -> InactiveLifecycleSourcePageV1:
    safe = _sanitize_response(response)
    rows = _results(safe)
    if len(rows) > PAGE_LIMIT or any(row.get("active") is not False for row in rows):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle page contains out-of-scope rows"
        )
    next_url = response.get("next_url")
    if next_url is None:
        next_path = None
        next_params: tuple[tuple[str, str], ...] = ()
        next_fingerprint = None
    else:
        path, params = _next_request(next_url, anchor_date=anchor_date)
        next_path = path
        next_params = tuple(sorted(params.items()))
        next_fingerprint = _request_locator_fingerprint(path, params)
    return InactiveLifecycleSourcePageV1(
        sequence=sequence,
        source_observed_at=source_observed_at,
        request_locator_sha256=request_locator_sha256,
        next_request_path=next_path,
        next_request_params=next_params,
        next_request_locator_sha256=next_fingerprint,
        sanitized_response=safe,
    )


def _sanitize_response(response: Mapping[str, object]) -> dict[str, object]:
    safe = {
        key: value
        for key, value in response.items()
        if str(key).strip().lower() not in {"request_id", "next_url"}
    }
    _assert_no_secret_material(safe)
    return safe


def _results(response: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = response.get("results")
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle results are malformed"
        )
    return tuple(value)


def _initial_request(anchor_date: date) -> tuple[str, dict[str, str]]:
    return ALL_TICKERS_PATH, {
        "market": "stocks",
        "active": "false",
        "date": anchor_date.isoformat(),
        "limit": str(PAGE_LIMIT),
        "sort": "ticker",
        "order": "asc",
    }


def _next_request(value: object, *, anchor_date: date) -> tuple[str, dict[str, str]]:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle next URL is invalid"
        )
    parsed = urlparse(value)
    if parsed.scheme not in {"", "https"} or (
        parsed.netloc and parsed.netloc != "api.massive.com"
    ):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle pagination host changed"
        )
    if parsed.path != ALL_TICKERS_PATH:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle pagination path changed"
        )
    params = {
        key: item
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if key.strip().lower() not in {"apikey", "api_key", "access_token"}
    }
    required = _initial_request(anchor_date)[1]
    for key, expected in required.items():
        actual = params.get(key)
        if actual is not None and actual.lower() != expected:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle pagination scope changed"
            )
        params[key] = expected
    if not any(key not in required for key in params):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle pagination cursor is absent"
        )
    return parsed.path, params


def _finalize_partial(
    partial: Path,
    target: Path,
    checkpoint: InactiveLifecycleSourceCheckpointV1,
) -> InactiveLifecycleSourcePackageManifestV1:
    if checkpoint.state != "complete" or checkpoint.last_observed_at is None:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle source package is incomplete"
        )
    summary, pages = _reread_artifacts(
        partial, checkpoint.artifacts, checkpoint.anchor_date
    )
    if not pages or pages[-1].next_request_path is not None:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle source pagination is incomplete"
        )
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": MASSIVE_PROVIDER_ID,
        "anchor_date": checkpoint.anchor_date,
        "endpoint": ALL_TICKERS_PATH,
        "active_filter": False,
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
        "point_in_time_eligibility": "outcome_reconciliation_only",
        "request_id_retained": False,
        "credential_material_retained": False,
        "pagination_url_retained": False,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    manifest = InactiveLifecycleSourcePackageManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(_json_ready(values))}
    )
    manifest_path = partial / _MANIFEST_FILE
    if manifest_path.exists():
        existing = _read_model(
            manifest_path, InactiveLifecycleSourcePackageManifestV1
        )
        if existing != manifest:
            raise HistoricalInactiveLifecycleSourceError(
                "recovered lifecycle package manifest differs"
            )
    else:
        _write_immutable_json(manifest_path, manifest.model_dump(mode="json"))
    (partial / _CHECKPOINT_FILE).chmod(0o400)
    _fsync_directory(partial)
    if target.exists() or target.is_symlink():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle package target appeared"
        )
    partial.replace(target)
    _fsync_directory(target.parent)
    return read_historical_inactive_lifecycle_source_package(
        package_path=target,
        expected_anchor_date=checkpoint.anchor_date,
    )


@dataclass(frozen=True, slots=True)
class _SourceSummary:
    record_count: int
    active_false_count: int
    duplicate_ticker_count: int
    field_presence_counts: tuple[tuple[str, int], ...]


def _reread_artifacts(
    root: Path,
    artifacts: tuple[InactiveLifecycleSourceArtifactV1, ...],
    anchor_date: date,
) -> tuple[_SourceSummary, tuple[InactiveLifecycleSourcePageV1, ...]]:
    path, params = _initial_request(anchor_date)
    rows_total = 0
    tickers: list[str] = []
    field_counts = {field: 0 for field in _LIFECYCLE_FIELDS}
    pages: list[InactiveLifecycleSourcePageV1] = []
    for artifact in artifacts:
        expected_request = _request_locator_fingerprint(path, params)
        if artifact.request_locator_sha256 != expected_request:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle request chain differs"
            )
        page_path = root / artifact.file_name
        raw = _read_regular_file(page_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
        if len(raw) != artifact.byte_size or _sha256(raw) != artifact.physical_sha256:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle page custody differs"
            )
        page = _parse_model(raw, InactiveLifecycleSourcePageV1)
        if (
            page.sequence != artifact.sequence
            or page.request_locator_sha256 != artifact.request_locator_sha256
            or page.next_request_locator_sha256
            != artifact.next_request_locator_sha256
            or page.source_observed_at != artifact.source_observed_at
        ):
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle page manifest binding differs"
            )
        _assert_no_secret_material(page.sanitized_response)
        rows = _results(page.sanitized_response)
        if len(rows) != artifact.row_count or any(
            row.get("active") is not False for row in rows
        ):
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle page rows differ"
            )
        rows_total += len(rows)
        for row in rows:
            ticker = row.get("ticker")
            if isinstance(ticker, str) and ticker.strip():
                tickers.append(ticker.strip().upper())
            for field in _LIFECYCLE_FIELDS:
                if _present(row.get(field)):
                    field_counts[field] += 1
        pages.append(page)
        if page.next_request_path is None:
            if artifact.sequence != len(artifacts):
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle pages continue after natural completion"
                )
        else:
            path = page.next_request_path
            params = dict(page.next_request_params)
    return (
        _SourceSummary(
            record_count=rows_total,
            active_false_count=rows_total,
            duplicate_ticker_count=len(tickers) - len(set(tickers)),
            field_presence_counts=tuple(
                (field, field_counts[field]) for field in _LIFECYCLE_FIELDS
            ),
        ),
        tuple(pages),
    )


def _summary_manifest_values(summary: _SourceSummary) -> dict[str, object]:
    return {
        "active_false_count": summary.active_false_count,
        "active_true_conflict_count": 0,
        "active_missing_count": 0,
        "duplicate_ticker_count": summary.duplicate_ticker_count,
        "field_presence_counts": summary.field_presence_counts,
    }


def _write_page(
    partial: Path,
    page: InactiveLifecycleSourcePageV1,
    payload: bytes,
) -> InactiveLifecycleSourceArtifactV1:
    target = partial / _page_file_name(page.sequence)
    _write_immutable_bytes(target, payload)
    return _artifact_from_page(page, payload)


def _artifact_from_page(
    page: InactiveLifecycleSourcePageV1, payload: bytes
) -> InactiveLifecycleSourceArtifactV1:
    return InactiveLifecycleSourceArtifactV1(
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
    partial: Path, checkpoint: InactiveLifecycleSourceCheckpointV1
) -> None:
    target = partial / _CHECKPOINT_FILE
    temporary = partial / f".{_CHECKPOINT_FILE}.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle checkpoint staging exists"
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
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle immutable source target exists"
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
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle staging residue is unsafe"
            )
        path.unlink()
    _fsync_directory(partial)


def _validate_file_set(root: Path, expected: set[str], *, completed: bool) -> None:
    actual: set[str] = set()
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package contains an unsafe entry"
            )
        actual.add(path.name)
        expected_mode = 0o400 if completed else (
            0o600 if path.name == _CHECKPOINT_FILE else 0o400
        )
        _require_mode(path, expected_mode)
    if actual != expected:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle package file set differs"
        )


def _validate_package_target(path: Path, anchor_date: date) -> Path:
    target = path.absolute()
    if Path("/tmp") not in target.parents or target.name != (
        f"anchor={anchor_date.isoformat()}"
    ):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle package must use its exact /tmp anchor path"
        )
    parent = target.parent
    if parent.exists():
        if parent.is_symlink() or not parent.is_dir():
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package parent is unsafe"
            )
    else:
        if not parent.parent.exists() or parent.parent.is_symlink():
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package parent boundary is unavailable"
            )
        parent.mkdir(mode=0o700)
    _require_mode(parent, 0o700)
    return target


def _validate_completed_package_path(
    path: Path,
    anchor_date: date,
    *,
    approved_custody_root: Path | None = None,
) -> Path:
    package = path.absolute()
    if approved_custody_root is not None:
        root = approved_custody_root.absolute()
        if (
            root.is_symlink()
            or not root.is_dir()
            or root.resolve(strict=True) != root
            or package.parent != root
            or package.name != f"anchor={anchor_date.isoformat()}"
        ):
            raise HistoricalInactiveLifecycleSourceError(
                "persistent inactive lifecycle custody boundary differs"
            )
        _require_mode(root, 0o700)
        if (
            package.is_symlink()
            or not package.is_dir()
            or package.resolve(strict=True) != package
        ):
            raise HistoricalInactiveLifecycleSourceError(
                "persistent inactive lifecycle package is unavailable"
            )
        _require_mode(package, 0o700)
        return package
    if (
        Path("/tmp") not in package.parents
        or package.name != f"anchor={anchor_date.isoformat()}"
        or package.is_symlink()
        or not package.is_dir()
    ):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle completed package path is invalid"
        )
    _require_mode(package, 0o700)
    if package.parent.is_symlink() or not package.parent.is_dir():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle package parent is unsafe"
        )
    _require_mode(package.parent, 0o700)
    return package


@contextmanager
def _package_lock(target: Path) -> Iterator[None]:
    lock_path = target.parent / f".{target.name}.lock"
    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "r+b") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package lock is unsafe"
            )
        if stat.S_IMODE(os.fstat(handle.fileno()).st_mode) != 0o600:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle package lock mode differs"
            )
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def _validate_config(config: MassiveProviderConfig) -> None:
    parsed = urlparse(config.base_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.massive.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle source base URL is outside the allowlist"
        )


def _assert_no_secret_material(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).strip().lower().replace("-", "_") in _FORBIDDEN_KEYS:
                raise HistoricalInactiveLifecycleSourceError(
                    "inactive lifecycle source contains forbidden material"
                )
            _assert_no_secret_material(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_secret_material(item)
    elif isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        parsed = urlparse(value)
        query_keys = {
            key.strip().lower().replace("-", "_")
            for key, _ in parse_qsl(parsed.query)
        }
        if parsed.username or parsed.password or query_keys & _FORBIDDEN_KEYS:
            raise HistoricalInactiveLifecycleSourceError(
                "inactive lifecycle source contains a credential-bearing URL"
            )


def _read_model(path: Path, model: type[BaseModel]):
    return _parse_model(
        _read_regular_file(path, maximum_bytes=MAXIMUM_PAGE_BYTES), model
    )


def _parse_model(payload: bytes, model: type[BaseModel]):
    try:
        return model.model_validate_json(payload)
    except Exception as exc:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle custody document is invalid"
        ) from exc


def _read_regular_file(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle custody file is invalid"
        )
    size = path.stat().st_size
    if size < 1 or size > maximum_bytes:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle custody file size is invalid"
        )
    return path.read_bytes()


def _request_locator_fingerprint(path: str, params: Mapping[str, object]) -> str:
    return _fingerprint(
        {"path": path, "params": sorted((key, str(value)) for key, value in params.items())}
    )


def _page_file_name(sequence: int) -> str:
    return f"{_PAGE_FILE_PREFIX}{sequence:05d}{_PAGE_FILE_SUFFIX}"


def _present(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _json_ready(value: object) -> object:
    return to_jsonable_python(value)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _json_ready(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return _sha256(_json_bytes(value).rstrip(b"\n"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_mode(path: Path, expected: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != expected:
        raise HistoricalInactiveLifecycleSourceError(
            "inactive lifecycle custody ownership or mode differs"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _result(
    manifest: InactiveLifecycleSourcePackageManifestV1,
    package_path: Path,
    status: Literal["published", "already_present", "recovered_and_published"],
) -> InactiveLifecycleSourcePackageResult:
    return InactiveLifecycleSourcePackageResult(
        manifest=manifest,
        package_path=package_path,
        manifest_sha256=_sha256((package_path / _MANIFEST_FILE).read_bytes()),
        status=status,
    )
