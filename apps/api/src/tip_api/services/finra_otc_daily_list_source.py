"""Bounded, resumable custody for official FINRA OTC Daily List evidence."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable, Iterator, Literal, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime


CONTRACT_VERSION = "finra-otc-daily-list-source-package/1.0"
PAGE_CONTRACT_VERSION = "finra-otc-daily-list-source-page/1.0"
CHECKPOINT_CONTRACT_VERSION = "finra-otc-daily-list-source-checkpoint/1.0"
PROVIDER_ID = "finra_otc_daily_list"
ENDPOINT = "https://api.finra.org/data/group/otcMarket/name/OTCDAILYLIST"
PARTITION_FIELD = "calendarDay"
PAGE_LIMIT = 500
MAXIMUM_PAGE_COUNT = 100
MAXIMUM_RECORD_COUNT = PAGE_LIMIT * MAXIMUM_PAGE_COUNT
MAXIMUM_RESPONSE_BYTES = 3 * 1024 * 1024
MAXIMUM_PAGE_BYTES = 4 * 1024 * 1024
MAXIMUM_PACKAGE_BYTES = 256 * 1024 * 1024
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.0
_PAGE_PREFIX = "response-"
_PAGE_SUFFIX = ".json"
_CHECKPOINT_FILE = "checkpoint.json"
_MANIFEST_FILE = "package.json"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ALLOWED_RESPONSE_HEADERS = (
    "content-type",
    "data-version",
    "limit",
    "offset",
    "record-limit",
    "record-max-limit",
    "record-offset",
    "record-total",
    "response-payload-max-size",
)

# Complete field set returned by FINRA metadata on 2026-09-10.  The request is
# explicit so metadata drift cannot silently alter retained source semantics.
SOURCE_FIELDS = (
    "oldOATSReportableFlag",
    "newSymbolCode",
    "ADRWitholdingTaxPercentage",
    "oldADROrdinaryShareRate",
    "newSecurityDescription",
    "subjectCorporateActionCode",
    "oldRegFeeFlag",
    "dailyListReasonDescription",
    "changeRoundLotQuantityFlag",
    "bankruptcyFlag",
    "changeSecurityDescriptionFlag",
    "changeOATSReportableFlag",
    "stockPercentage",
    "newOATSReportableFlag",
    "newFinancialStatusCode",
    "qualifiedDividendDescription",
    "newClassText",
    "oldSecurityDescription",
    "offeringTypeDescription",
    "oldClassText",
    "dividendTypeDescription",
    "ADRNetRate",
    "newRegFeeFlag",
    "dailyListEventCode",
    "ADRFeeAmount",
    "OTCDailyListID",
    "paymentMethodCode",
    "ADRGrossRate",
    "newMarketCategoryCode",
    "oldMaturityExpirationDate",
    "dailyListDatetime",
    "oldMarketCategoryCode",
    "changeSymbolFlag",
    "oldRoundLotQuantity",
    "changeRegFeeFlag",
    "commentText",
    "ADRTaxReliefAmount",
    "securityDeleteFlag",
    "ADRIssuanceFeeAmount",
    "recordDate",
    "dividendTypeCode",
    "exDate",
    "changeFinancialStatusFlag",
    "dividendADRFlag",
    "dividendMasterID",
    "paymentDate",
    "declarationDate",
    "oldSymbolCode",
    "changeOTCBBQuoteFlag",
    "newRoundLotQuantity",
    "newADROrdnyShareRate",
    "oldFinancialStatusCode",
    "changeSecurityAttributeFlag",
    "forwardSplitRate",
    "reverseSplitRate",
    "newMaturityExpirationDate",
    "cashAmountText",
    "securityAddFlag",
    "dividendNonADRFlag",
    "calendarDay",
)
_SOURCE_FIELD_SET = frozenset(SOURCE_FIELDS)


class FinraOtcDailyListSourceError(RuntimeError):
    """Raised when official source custody cannot continue fail-closed."""


class FinraOtcDailyListTransport(Protocol):
    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> tuple[object, Mapping[str, str]]: ...


class FinraUrllibTransport:
    """Small no-credential transport with a fixed official-host allowlist."""

    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> tuple[object, Mapping[str, str]]:
        _validate_endpoint(endpoint)
        request = Request(
            endpoint,
            data=_json_bytes(payload).rstrip(b"\n"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "WH-Alpha-Research/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                final_url = response.geturl()
                _validate_endpoint(final_url)
                raw = response.read(maximum_response_bytes + 1)
                if len(raw) > maximum_response_bytes:
                    raise FinraOtcDailyListSourceError(
                        "FINRA response exceeds the documented payload ceiling"
                    )
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type.lower():
                    raise FinraOtcDailyListSourceError(
                        "FINRA response content type is not JSON"
                    )
                headers = {
                    name.lower(): value.strip()
                    for name, value in response.headers.items()
                    if name.lower() in _ALLOWED_RESPONSE_HEADERS
                }
        except HTTPError as exc:
            raise FinraOtcDailyListSourceError(
                f"FINRA request returned HTTP {exc.code}"
            ) from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise FinraOtcDailyListSourceError(
                "FINRA request was unavailable; resume from the sealed checkpoint"
            ) from exc
        try:
            return json.loads(raw), headers
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FinraOtcDailyListSourceError(
                "FINRA response body is not valid JSON"
            ) from exc


@dataclass(slots=True)
class FinraFixedIntervalLimiter:
    interval_seconds: float = MINIMUM_REQUEST_INTERVAL_SECONDS
    clock: Callable[[], float] = time.monotonic
    sleeper: Callable[[float], None] = time.sleep
    _last_request_at: float | None = field(default=None, init=False)

    def wait_before_request(self) -> None:
        current = self.clock()
        if self._last_request_at is not None:
            delay = self.interval_seconds - (current - self._last_request_at)
            if delay > 0:
                self.sleeper(delay)
                current = self.clock()
        self._last_request_at = current


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FinraOtcDailyListSourcePageV1(_FrozenModel):
    contract_version: Literal[
        "finra-otc-daily-list-source-page/1.0"
    ] = PAGE_CONTRACT_VERSION
    sequence: int = Field(ge=1)
    partition_start: date
    partition_end: date
    source_observed_at: datetime
    request_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    request_offset: int = Field(ge=0)
    data_version: int = Field(ge=1)
    record_total: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    record_limit: Literal[500] = PAGE_LIMIT
    record_max_limit: int = Field(ge=PAGE_LIMIT)
    record_offset: int = Field(ge=0)
    response_payload_maximum_bytes: Literal[3145728] = MAXIMUM_RESPONSE_BYTES
    rows: tuple[dict[str, object], ...]

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def page_reconciles(self) -> "FinraOtcDailyListSourcePageV1":
        if self.partition_end < self.partition_start:
            raise ValueError("FINRA partition range is reversed")
        if self.request_offset != self.record_offset:
            raise ValueError("FINRA request and response offsets differ")
        if len(self.rows) > self.record_limit:
            raise ValueError("FINRA page row count exceeds its limit")
        expected = _request_locator_fingerprint(
            self.partition_start, self.partition_end, self.request_offset
        )
        if self.request_locator_sha256 != expected:
            raise ValueError("FINRA request locator fingerprint differs")
        for row in self.rows:
            _validate_source_row(
                row,
                partition_start=self.partition_start,
                partition_end=self.partition_end,
            )
        return self


class FinraOtcDailyListSourceArtifactV1(_FrozenModel):
    sequence: int = Field(ge=1)
    file_name: str
    request_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_observed_at: datetime
    request_offset: int = Field(ge=0)
    row_count: int = Field(ge=0, le=PAGE_LIMIT)
    byte_size: int = Field(ge=1, le=MAXIMUM_PAGE_BYTES)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def file_name_reconciles(self) -> "FinraOtcDailyListSourceArtifactV1":
        if self.file_name != _page_file_name(self.sequence):
            raise ValueError("FINRA source page file name differs")
        return self


class FinraOtcDailyListSourceCheckpointV1(_FrozenModel):
    contract_version: Literal[
        "finra-otc-daily-list-source-checkpoint/1.0"
    ] = CHECKPOINT_CONTRACT_VERSION
    state: Literal["in_progress", "complete"]
    provider_id: Literal["finra_otc_daily_list"] = PROVIDER_ID
    partition_start: date
    partition_end: date
    started_at: datetime
    last_observed_at: datetime | None = None
    expected_data_version: int | None = Field(default=None, ge=1)
    expected_record_total: int | None = Field(
        default=None, ge=0, le=MAXIMUM_RECORD_COUNT
    )
    artifacts: tuple[FinraOtcDailyListSourceArtifactV1, ...] = ()
    next_offset: int | None = Field(default=0, ge=0)
    record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    package_bytes: int = Field(ge=0, le=MAXIMUM_PACKAGE_BYTES)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("started_at", "last_observed_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def checkpoint_reconciles(self) -> "FinraOtcDailyListSourceCheckpointV1":
        if self.partition_end < self.partition_start:
            raise ValueError("FINRA checkpoint range is reversed")
        if tuple(item.sequence for item in self.artifacts) != tuple(
            range(1, len(self.artifacts) + 1)
        ):
            raise ValueError("FINRA checkpoint sequence is not contiguous")
        if len(self.artifacts) > MAXIMUM_PAGE_COUNT:
            raise ValueError("FINRA checkpoint page ceiling exceeded")
        if self.record_count != sum(item.row_count for item in self.artifacts):
            raise ValueError("FINRA checkpoint record count differs")
        if self.package_bytes != sum(item.byte_size for item in self.artifacts):
            raise ValueError("FINRA checkpoint byte count differs")
        if self.artifacts:
            if self.last_observed_at != self.artifacts[-1].source_observed_at:
                raise ValueError("FINRA checkpoint observation time differs")
        elif self.last_observed_at is not None:
            raise ValueError("empty FINRA checkpoint has an observation time")
        if self.state == "complete":
            if self.next_offset is not None:
                raise ValueError("complete FINRA checkpoint retains an offset")
            if self.expected_record_total != self.record_count:
                raise ValueError("complete FINRA checkpoint total differs")
        elif self.next_offset is None or self.next_offset != self.record_count:
            raise ValueError("in-progress FINRA checkpoint offset differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("FINRA checkpoint fingerprint differs")
        return self


class FinraOtcDailyListSourcePackageManifestV1(_FrozenModel):
    contract_version: Literal[
        "finra-otc-daily-list-source-package/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["finra_otc_daily_list"] = PROVIDER_ID
    partition_start: date
    partition_end: date
    endpoint: Literal[
        "https://api.finra.org/data/group/otcMarket/name/OTCDAILYLIST"
    ] = ENDPOINT
    partition_field: Literal["calendarDay"] = PARTITION_FIELD
    selected_fields: tuple[str, ...]
    metadata_observed_date: Literal["2026-09-10"] = "2026-09-10"
    selected_fields_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    page_limit: Literal[500] = PAGE_LIMIT
    maximum_page_count: Literal[100] = MAXIMUM_PAGE_COUNT
    maximum_record_count: Literal[50000] = MAXIMUM_RECORD_COUNT
    minimum_request_interval_seconds: Literal["1.0"] = "1.0"
    zero_automatic_retry: Literal[True] = True
    started_at: datetime
    completed_at: datetime
    data_version: int = Field(ge=1)
    artifacts: tuple[FinraOtcDailyListSourceArtifactV1, ...] = Field(min_length=1)
    request_count: int = Field(ge=1, le=MAXIMUM_PAGE_COUNT)
    record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    unique_source_record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    duplicate_source_record_count: int = Field(ge=0, le=MAXIMUM_RECORD_COUNT)
    package_bytes: int = Field(ge=1, le=MAXIMUM_PACKAGE_BYTES)
    event_code_counts: tuple[tuple[str, int], ...]
    missing_event_code_count: int = Field(ge=0)
    field_presence_counts: tuple[tuple[str, int], ...]
    pagination_complete: Literal[True] = True
    source_payload_retention: Literal["complete_selected_fields"] = (
        "complete_selected_fields"
    )
    source_availability_clock: Literal["unverified"] = "unverified"
    research_eligibility: Literal["official_otc_corroboration_only"] = (
        "official_otc_corroboration_only"
    )
    major_exchange_lifecycle_authority: Literal[False] = False
    ticker_positive_identity_resolution: Literal[False] = False
    identity_resolution_status: Literal["not_attempted"] = "not_attempted"
    credential_material_retained: Literal[False] = False
    request_identifier_retained: Literal[False] = False
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
    def manifest_reconciles(self) -> "FinraOtcDailyListSourcePackageManifestV1":
        if self.completed_at < self.started_at:
            raise ValueError("FINRA package completion precedes its start")
        if self.selected_fields != SOURCE_FIELDS:
            raise ValueError("FINRA selected field set differs")
        if self.selected_fields_fingerprint != _fingerprint(SOURCE_FIELDS):
            raise ValueError("FINRA selected field fingerprint differs")
        if self.request_count != len(self.artifacts):
            raise ValueError("FINRA manifest request count differs")
        if self.record_count != sum(item.row_count for item in self.artifacts):
            raise ValueError("FINRA manifest record count differs")
        if self.package_bytes != sum(item.byte_size for item in self.artifacts):
            raise ValueError("FINRA manifest byte count differs")
        if self.unique_source_record_count + self.duplicate_source_record_count != self.record_count:
            raise ValueError("FINRA source record uniqueness counts differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("FINRA manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class FinraOtcDailyListSourcePackageResult:
    manifest: FinraOtcDailyListSourcePackageManifestV1
    package_path: Path
    manifest_sha256: str
    status: Literal["published", "already_present", "recovered_and_published"]


@dataclass(frozen=True, slots=True)
class ValidatedFinraOtcDailyListSourcePackage:
    """Source rows exposed only after the complete package passes readback."""

    package_path: Path
    manifest: FinraOtcDailyListSourcePackageManifestV1
    pages: tuple[FinraOtcDailyListSourcePageV1, ...]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class _SourceSummary:
    record_count: int
    unique_source_record_count: int
    duplicate_source_record_count: int
    event_code_counts: tuple[tuple[str, int], ...]
    missing_event_code_count: int
    field_presence_counts: tuple[tuple[str, int], ...]


ProgressCallback = Callable[[FinraOtcDailyListSourceArtifactV1, int, int], None]


def acquire_finra_otc_daily_list_source_package(
    *,
    partition_start: date,
    partition_end: date,
    package_path: Path,
    approved_custody_root: Path,
    transport: FinraOtcDailyListTransport | None = None,
    rate_limiter: FinraFixedIntervalLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    timeout_seconds: float = 30.0,
    progress: ProgressCallback | None = None,
) -> FinraOtcDailyListSourcePackageResult:
    """Acquire or resume one exact within-month official FINRA partition."""

    _validate_partition(partition_start, partition_end)
    target = _validate_package_target(
        package_path,
        partition_start=partition_start,
        partition_end=partition_end,
        approved_custody_root=approved_custody_root,
    )
    client = transport or FinraUrllibTransport()
    limiter = rate_limiter or FinraFixedIntervalLimiter()
    now = clock or (lambda: datetime.now(UTC))
    with _package_lock(target):
        partial = target.parent / f".{target.name}.partial"
        if target.exists():
            if partial.exists() or partial.is_symlink():
                raise FinraOtcDailyListSourceError(
                    "completed and partial FINRA packages coexist"
                )
            manifest = read_finra_otc_daily_list_source_package(
                package_path=target,
                expected_partition_start=partition_start,
                expected_partition_end=partition_end,
                approved_custody_root=approved_custody_root,
            )
            return _result(manifest, target, "already_present")

        recovered = partial.exists()
        checkpoint = _load_or_create_checkpoint(
            partial=partial,
            partition_start=partition_start,
            partition_end=partition_end,
            now=now,
        )
        checkpoint = _adopt_exact_orphan(partial, checkpoint)
        while checkpoint.state == "in_progress":
            if len(checkpoint.artifacts) >= MAXIMUM_PAGE_COUNT:
                raise FinraOtcDailyListSourceError(
                    "FINRA pagination exceeds the page ceiling"
                )
            request_offset = checkpoint.next_offset
            if request_offset is None:
                raise FinraOtcDailyListSourceError(
                    "in-progress FINRA checkpoint has no offset"
                )
            limiter.wait_before_request()
            payload = _request_payload(partition_start, partition_end, request_offset)
            response, headers = client.post_json(
                endpoint=ENDPOINT,
                payload=payload,
                timeout_seconds=timeout_seconds,
                maximum_response_bytes=MAXIMUM_RESPONSE_BYTES,
            )
            observed_at = normalize_utc_datetime(now())
            page = _build_page(
                response=response,
                headers=headers,
                sequence=len(checkpoint.artifacts) + 1,
                partition_start=partition_start,
                partition_end=partition_end,
                request_offset=request_offset,
                source_observed_at=observed_at,
            )
            _validate_page_against_checkpoint(page, checkpoint)
            raw = _json_bytes(page.model_dump(mode="json"))
            if len(raw) > MAXIMUM_PAGE_BYTES:
                raise FinraOtcDailyListSourceError(
                    "retained FINRA page exceeds the page ceiling"
                )
            if checkpoint.package_bytes + len(raw) > MAXIMUM_PACKAGE_BYTES:
                raise FinraOtcDailyListSourceError(
                    "FINRA package exceeds the byte ceiling"
                )
            artifact = _write_page(partial, page, raw)
            checkpoint = _advance_checkpoint(checkpoint, page, artifact)
            _write_checkpoint(partial, checkpoint)
            if progress is not None:
                progress(artifact, checkpoint.record_count, checkpoint.package_bytes)

        manifest = _finalize_partial(
            partial,
            target,
            checkpoint,
            approved_custody_root=approved_custody_root,
        )
        return _result(
            manifest,
            target,
            "recovered_and_published" if recovered else "published",
        )


def read_finra_otc_daily_list_source_package(
    *,
    package_path: Path,
    expected_partition_start: date,
    expected_partition_end: date,
    approved_custody_root: Path,
) -> FinraOtcDailyListSourcePackageManifestV1:
    """Formally reread every retained page and all pagination invariants."""

    package = _validate_completed_path(
        package_path,
        partition_start=expected_partition_start,
        partition_end=expected_partition_end,
        approved_custody_root=approved_custody_root,
    )
    manifest = _read_model(
        package / _MANIFEST_FILE, FinraOtcDailyListSourcePackageManifestV1
    )
    if (
        manifest.partition_start != expected_partition_start
        or manifest.partition_end != expected_partition_end
    ):
        raise FinraOtcDailyListSourceError("FINRA package partition differs")
    checkpoint = _read_model(
        package / _CHECKPOINT_FILE, FinraOtcDailyListSourceCheckpointV1
    )
    if (
        checkpoint.state != "complete"
        or checkpoint.artifacts != manifest.artifacts
        or checkpoint.expected_data_version != manifest.data_version
        or checkpoint.expected_record_total != manifest.record_count
        or checkpoint.record_count != manifest.record_count
        or checkpoint.package_bytes != manifest.package_bytes
    ):
        raise FinraOtcDailyListSourceError(
            "FINRA completed checkpoint differs from its manifest"
        )
    expected_files = {_CHECKPOINT_FILE, _MANIFEST_FILE} | {
        item.file_name for item in manifest.artifacts
    }
    _validate_file_set(package, expected_files, completed=True)
    summary, pages = _reread_artifacts(
        package,
        manifest.artifacts,
        partition_start=expected_partition_start,
        partition_end=expected_partition_end,
    )
    if not pages or sum(len(page.rows) for page in pages) != manifest.record_count:
        raise FinraOtcDailyListSourceError("FINRA package pagination is incomplete")
    for key, value in _summary_values(summary).items():
        if getattr(manifest, key) != value:
            raise FinraOtcDailyListSourceError("FINRA package aggregate differs")
    return manifest


def read_finra_otc_daily_list_source_payloads(
    *,
    package_path: Path,
    expected_partition_start: date,
    expected_partition_end: date,
    approved_custody_root: Path,
) -> ValidatedFinraOtcDailyListSourcePackage:
    """Return rows only after every package invariant has been reread."""

    manifest = read_finra_otc_daily_list_source_package(
        package_path=package_path,
        expected_partition_start=expected_partition_start,
        expected_partition_end=expected_partition_end,
        approved_custody_root=approved_custody_root,
    )
    package = _validate_completed_path(
        package_path,
        partition_start=expected_partition_start,
        partition_end=expected_partition_end,
        approved_custody_root=approved_custody_root,
    )
    _, pages = _reread_artifacts(
        package,
        manifest.artifacts,
        partition_start=expected_partition_start,
        partition_end=expected_partition_end,
    )
    return ValidatedFinraOtcDailyListSourcePackage(
        package_path=package,
        manifest=manifest,
        pages=pages,
        manifest_sha256=_sha256((package / _MANIFEST_FILE).read_bytes()),
    )


def _load_or_create_checkpoint(
    *,
    partial: Path,
    partition_start: date,
    partition_end: date,
    now: Callable[[], datetime],
) -> FinraOtcDailyListSourceCheckpointV1:
    if partial.exists():
        if partial.is_symlink() or not partial.is_dir():
            raise FinraOtcDailyListSourceError("FINRA partial path is unsafe")
        _require_mode(partial, 0o700)
        _remove_known_temporary_files(partial)
        checkpoint = _read_model(
            partial / _CHECKPOINT_FILE, FinraOtcDailyListSourceCheckpointV1
        )
        if (
            checkpoint.partition_start != partition_start
            or checkpoint.partition_end != partition_end
        ):
            raise FinraOtcDailyListSourceError("FINRA checkpoint range differs")
        _reread_artifacts(
            partial,
            checkpoint.artifacts,
            partition_start=partition_start,
            partition_end=partition_end,
        )
        return checkpoint
    partial.mkdir(mode=0o700)
    checkpoint = _make_checkpoint(
        state="in_progress",
        partition_start=partition_start,
        partition_end=partition_end,
        started_at=normalize_utc_datetime(now()),
        last_observed_at=None,
        expected_data_version=None,
        expected_record_total=None,
        artifacts=(),
        next_offset=0,
    )
    _write_checkpoint(partial, checkpoint)
    return checkpoint


def _adopt_exact_orphan(
    partial: Path,
    checkpoint: FinraOtcDailyListSourceCheckpointV1,
) -> FinraOtcDailyListSourceCheckpointV1:
    expected = {item.file_name for item in checkpoint.artifacts}
    actual = {
        path.name
        for path in partial.iterdir()
        if path.name.startswith(_PAGE_PREFIX) and path.name.endswith(_PAGE_SUFFIX)
    }
    extras = actual - expected
    if not extras:
        return checkpoint
    expected_name = _page_file_name(len(checkpoint.artifacts) + 1)
    if extras != {expected_name} or checkpoint.state != "in_progress":
        raise FinraOtcDailyListSourceError("FINRA partial has unexpected pages")
    page_path = partial / expected_name
    page = _read_model(page_path, FinraOtcDailyListSourcePageV1)
    _validate_page_against_checkpoint(page, checkpoint)
    raw = _read_regular_file(page_path, maximum_bytes=MAXIMUM_PAGE_BYTES)
    artifact = _artifact_from_page(page, raw)
    updated = _advance_checkpoint(checkpoint, page, artifact)
    _write_checkpoint(partial, updated)
    return updated


def _build_page(
    *,
    response: object,
    headers: Mapping[str, str],
    sequence: int,
    partition_start: date,
    partition_end: date,
    request_offset: int,
    source_observed_at: datetime,
) -> FinraOtcDailyListSourcePageV1:
    if not isinstance(response, list) or any(not isinstance(row, dict) for row in response):
        raise FinraOtcDailyListSourceError("FINRA JSON response is not a row list")
    normalized_headers = {str(key).lower(): str(value).strip() for key, value in headers.items()}
    content_type = normalized_headers.get("content-type", "application/json")
    if "application/json" not in content_type.lower():
        raise FinraOtcDailyListSourceError("FINRA response content type differs")
    record_total = _integer_header(normalized_headers, "record-total")
    record_limit = _integer_header(normalized_headers, "record-limit")
    record_max_limit = _integer_header(normalized_headers, "record-max-limit")
    record_offset = _integer_header(normalized_headers, "record-offset")
    data_version = _integer_header(normalized_headers, "data-version")
    payload_maximum = _payload_ceiling_header(normalized_headers)
    if record_limit != PAGE_LIMIT or payload_maximum != MAXIMUM_RESPONSE_BYTES:
        raise FinraOtcDailyListSourceError("FINRA documented response bounds changed")
    if record_offset != request_offset:
        raise FinraOtcDailyListSourceError(
            "FINRA request and response offsets differ"
        )
    return FinraOtcDailyListSourcePageV1(
        sequence=sequence,
        partition_start=partition_start,
        partition_end=partition_end,
        source_observed_at=source_observed_at,
        request_locator_sha256=_request_locator_fingerprint(
            partition_start, partition_end, request_offset
        ),
        request_offset=request_offset,
        data_version=data_version,
        record_total=record_total,
        record_limit=record_limit,
        record_max_limit=record_max_limit,
        record_offset=record_offset,
        response_payload_maximum_bytes=payload_maximum,
        rows=tuple(response),
    )


def _validate_page_against_checkpoint(
    page: FinraOtcDailyListSourcePageV1,
    checkpoint: FinraOtcDailyListSourceCheckpointV1,
) -> None:
    if page.sequence != len(checkpoint.artifacts) + 1:
        raise FinraOtcDailyListSourceError("FINRA page sequence differs")
    if page.request_offset != checkpoint.next_offset:
        raise FinraOtcDailyListSourceError("FINRA page offset differs")
    if checkpoint.expected_data_version not in {None, page.data_version}:
        raise FinraOtcDailyListSourceError("FINRA data version changed during paging")
    if checkpoint.expected_record_total not in {None, page.record_total}:
        raise FinraOtcDailyListSourceError("FINRA record total changed during paging")
    if page.record_total > MAXIMUM_RECORD_COUNT:
        raise FinraOtcDailyListSourceError("FINRA partition exceeds record ceiling")
    if page.request_offset + len(page.rows) > page.record_total:
        raise FinraOtcDailyListSourceError("FINRA page extends beyond record total")
    if not page.rows and page.request_offset < page.record_total:
        raise FinraOtcDailyListSourceError("FINRA pagination stopped before total")


def _advance_checkpoint(
    checkpoint: FinraOtcDailyListSourceCheckpointV1,
    page: FinraOtcDailyListSourcePageV1,
    artifact: FinraOtcDailyListSourceArtifactV1,
) -> FinraOtcDailyListSourceCheckpointV1:
    record_count = checkpoint.record_count + artifact.row_count
    complete = record_count == page.record_total
    return _make_checkpoint(
        state="complete" if complete else "in_progress",
        partition_start=checkpoint.partition_start,
        partition_end=checkpoint.partition_end,
        started_at=checkpoint.started_at,
        last_observed_at=page.source_observed_at,
        expected_data_version=page.data_version,
        expected_record_total=page.record_total,
        artifacts=checkpoint.artifacts + (artifact,),
        next_offset=None if complete else record_count,
    )


def _make_checkpoint(
    *,
    state: Literal["in_progress", "complete"],
    partition_start: date,
    partition_end: date,
    started_at: datetime,
    last_observed_at: datetime | None,
    expected_data_version: int | None,
    expected_record_total: int | None,
    artifacts: tuple[FinraOtcDailyListSourceArtifactV1, ...],
    next_offset: int | None,
) -> FinraOtcDailyListSourceCheckpointV1:
    values = {
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "state": state,
        "provider_id": PROVIDER_ID,
        "partition_start": partition_start,
        "partition_end": partition_end,
        "started_at": started_at,
        "last_observed_at": last_observed_at,
        "expected_data_version": expected_data_version,
        "expected_record_total": expected_record_total,
        "artifacts": artifacts,
        "next_offset": next_offset,
        "record_count": sum(item.row_count for item in artifacts),
        "package_bytes": sum(item.byte_size for item in artifacts),
    }
    return FinraOtcDailyListSourceCheckpointV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _finalize_partial(
    partial: Path,
    target: Path,
    checkpoint: FinraOtcDailyListSourceCheckpointV1,
    *,
    approved_custody_root: Path,
) -> FinraOtcDailyListSourcePackageManifestV1:
    if (
        checkpoint.state != "complete"
        or checkpoint.last_observed_at is None
        or checkpoint.expected_data_version is None
    ):
        raise FinraOtcDailyListSourceError("FINRA source package is incomplete")
    summary, _ = _reread_artifacts(
        partial,
        checkpoint.artifacts,
        partition_start=checkpoint.partition_start,
        partition_end=checkpoint.partition_end,
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": PROVIDER_ID,
        "partition_start": checkpoint.partition_start,
        "partition_end": checkpoint.partition_end,
        "endpoint": ENDPOINT,
        "partition_field": PARTITION_FIELD,
        "selected_fields": SOURCE_FIELDS,
        "metadata_observed_date": "2026-09-10",
        "selected_fields_fingerprint": _fingerprint(SOURCE_FIELDS),
        "page_limit": PAGE_LIMIT,
        "maximum_page_count": MAXIMUM_PAGE_COUNT,
        "maximum_record_count": MAXIMUM_RECORD_COUNT,
        "minimum_request_interval_seconds": "1.0",
        "zero_automatic_retry": True,
        "started_at": checkpoint.started_at,
        "completed_at": checkpoint.last_observed_at,
        "data_version": checkpoint.expected_data_version,
        "artifacts": checkpoint.artifacts,
        "request_count": len(checkpoint.artifacts),
        "record_count": checkpoint.record_count,
        "package_bytes": checkpoint.package_bytes,
        **_summary_values(summary),
        "pagination_complete": True,
        "source_payload_retention": "complete_selected_fields",
        "source_availability_clock": "unverified",
        "research_eligibility": "official_otc_corroboration_only",
        "major_exchange_lifecycle_authority": False,
        "ticker_positive_identity_resolution": False,
        "identity_resolution_status": "not_attempted",
        "credential_material_retained": False,
        "request_identifier_retained": False,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    manifest = FinraOtcDailyListSourcePackageManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )
    _write_immutable_json(partial / _MANIFEST_FILE, manifest.model_dump(mode="json"))
    (partial / _CHECKPOINT_FILE).chmod(0o400)
    _fsync_directory(partial)
    if target.exists() or target.is_symlink():
        raise FinraOtcDailyListSourceError("FINRA package target appeared")
    partial.replace(target)
    _fsync_directory(target.parent)
    return read_finra_otc_daily_list_source_package(
        package_path=target,
        expected_partition_start=checkpoint.partition_start,
        expected_partition_end=checkpoint.partition_end,
        approved_custody_root=approved_custody_root,
    )


def _reread_artifacts(
    root: Path,
    artifacts: tuple[FinraOtcDailyListSourceArtifactV1, ...],
    *,
    partition_start: date,
    partition_end: date,
) -> tuple[_SourceSummary, tuple[FinraOtcDailyListSourcePageV1, ...]]:
    rows: list[dict[str, object]] = []
    pages: list[FinraOtcDailyListSourcePageV1] = []
    expected_offset = 0
    expected_total: int | None = None
    expected_version: int | None = None
    for artifact in artifacts:
        if artifact.request_offset != expected_offset:
            raise FinraOtcDailyListSourceError("FINRA artifact offset chain differs")
        raw = _read_regular_file(root / artifact.file_name, maximum_bytes=MAXIMUM_PAGE_BYTES)
        if len(raw) != artifact.byte_size or _sha256(raw) != artifact.physical_sha256:
            raise FinraOtcDailyListSourceError("FINRA page custody differs")
        page = _parse_model(raw, FinraOtcDailyListSourcePageV1)
        if (
            page.sequence != artifact.sequence
            or page.request_locator_sha256 != artifact.request_locator_sha256
            or page.source_observed_at != artifact.source_observed_at
            or page.request_offset != artifact.request_offset
            or len(page.rows) != artifact.row_count
        ):
            raise FinraOtcDailyListSourceError("FINRA artifact binding differs")
        if expected_total not in {None, page.record_total} or expected_version not in {
            None,
            page.data_version,
        }:
            raise FinraOtcDailyListSourceError("FINRA page facts changed within package")
        expected_total = page.record_total
        expected_version = page.data_version
        expected_offset += len(page.rows)
        rows.extend(page.rows)
        pages.append(page)
    if artifacts and expected_total is not None and len(rows) > expected_total:
        raise FinraOtcDailyListSourceError("FINRA retained rows exceed record total")
    return _summarize_rows(rows), tuple(pages)


def _summarize_rows(rows: list[dict[str, object]]) -> _SourceSummary:
    identifiers: list[str] = []
    event_counts: dict[str, int] = {}
    missing_event = 0
    field_counts = {name: 0 for name in SOURCE_FIELDS}
    for row in rows:
        identifier = row.get("OTCDailyListID")
        identifiers.append(str(identifier))
        event = row.get("dailyListEventCode")
        if isinstance(event, str) and event.strip():
            code = event.strip().upper()
            event_counts[code] = event_counts.get(code, 0) + 1
        else:
            missing_event += 1
        for name in SOURCE_FIELDS:
            value = row.get(name)
            if value is not None and (not isinstance(value, str) or bool(value.strip())):
                field_counts[name] += 1
    unique = len(set(identifiers))
    return _SourceSummary(
        record_count=len(rows),
        unique_source_record_count=unique,
        duplicate_source_record_count=len(rows) - unique,
        event_code_counts=tuple(sorted(event_counts.items())),
        missing_event_code_count=missing_event,
        field_presence_counts=tuple((name, field_counts[name]) for name in SOURCE_FIELDS),
    )


def _summary_values(summary: _SourceSummary) -> dict[str, object]:
    return {
        "unique_source_record_count": summary.unique_source_record_count,
        "duplicate_source_record_count": summary.duplicate_source_record_count,
        "event_code_counts": summary.event_code_counts,
        "missing_event_code_count": summary.missing_event_code_count,
        "field_presence_counts": summary.field_presence_counts,
    }


def _request_payload(start: date, end: date, offset: int) -> dict[str, object]:
    return {
        "fields": list(SOURCE_FIELDS),
        "dateRangeFilters": [
            {
                "fieldName": PARTITION_FIELD,
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
            }
        ],
        "limit": PAGE_LIMIT,
        "offset": offset,
    }


def _request_locator_fingerprint(start: date, end: date, offset: int) -> str:
    return _fingerprint(_request_payload(start, end, offset))


def _validate_source_row(row: Mapping[str, object], *, partition_start: date, partition_end: date) -> None:
    unknown = set(row) - _SOURCE_FIELD_SET
    if unknown:
        raise FinraOtcDailyListSourceError("FINRA response added unrequested fields")
    identifier = row.get("OTCDailyListID")
    if not isinstance(identifier, int) or identifier < 1:
        raise FinraOtcDailyListSourceError("FINRA source record ID is invalid")
    calendar_day = row.get(PARTITION_FIELD)
    if not isinstance(calendar_day, str):
        raise FinraOtcDailyListSourceError("FINRA calendar day is absent")
    try:
        observed_date = date.fromisoformat(calendar_day)
    except ValueError as exc:
        raise FinraOtcDailyListSourceError("FINRA calendar day is malformed") from exc
    if not partition_start <= observed_date <= partition_end:
        raise FinraOtcDailyListSourceError("FINRA source row is outside its partition")


def _integer_header(headers: Mapping[str, str], name: str) -> int:
    value = headers.get(name)
    try:
        parsed = int(value or "")
    except ValueError as exc:
        raise FinraOtcDailyListSourceError(f"FINRA {name} header is invalid") from exc
    if parsed < 0:
        raise FinraOtcDailyListSourceError(f"FINRA {name} header is negative")
    return parsed


def _payload_ceiling_header(headers: Mapping[str, str]) -> int:
    value = headers.get("response-payload-max-size", "").strip().lower()
    if value == "3mb":
        return MAXIMUM_RESPONSE_BYTES
    raise FinraOtcDailyListSourceError("FINRA payload ceiling header changed")


def _validate_partition(start: date, end: date) -> None:
    if end < start or (start.year, start.month) != (end.year, end.month):
        raise FinraOtcDailyListSourceError(
            "FINRA source package must be one non-reversed calendar-month partition"
        )
    if end >= date.today():
        raise FinraOtcDailyListSourceError("FINRA partition must be historical")


def _package_name(start: date, end: date) -> str:
    return f"period={start.isoformat()}--{end.isoformat()}"


def _validate_package_target(
    path: Path,
    *,
    partition_start: date,
    partition_end: date,
    approved_custody_root: Path,
) -> Path:
    root = approved_custody_root.absolute()
    if root.exists():
        if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
            raise FinraOtcDailyListSourceError("FINRA custody root is unsafe")
    else:
        parent = root.parent
        if parent.is_symlink() or not parent.is_dir():
            raise FinraOtcDailyListSourceError("FINRA custody parent is unavailable")
        root.mkdir(mode=0o700)
    _require_mode(root, 0o700)
    target = path.absolute()
    if target.parent != root or target.name != _package_name(partition_start, partition_end):
        raise FinraOtcDailyListSourceError("FINRA package custody boundary differs")
    return target


def _validate_completed_path(
    path: Path,
    *,
    partition_start: date,
    partition_end: date,
    approved_custody_root: Path,
) -> Path:
    target = _validate_package_target(
        path,
        partition_start=partition_start,
        partition_end=partition_end,
        approved_custody_root=approved_custody_root,
    )
    if target.is_symlink() or not target.is_dir() or target.resolve(strict=True) != target:
        raise FinraOtcDailyListSourceError("FINRA completed package is unsafe")
    _require_mode(target, 0o700)
    return target


@contextmanager
def _package_lock(target: Path) -> Iterator[None]:
    lock_path = target.parent / f".{target.name}.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+b") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise FinraOtcDailyListSourceError("FINRA package lock is unsafe")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def _write_page(
    partial: Path,
    page: FinraOtcDailyListSourcePageV1,
    raw: bytes,
) -> FinraOtcDailyListSourceArtifactV1:
    path = partial / _page_file_name(page.sequence)
    _write_immutable_bytes(path, raw)
    return _artifact_from_page(page, raw)


def _artifact_from_page(
    page: FinraOtcDailyListSourcePageV1,
    raw: bytes,
) -> FinraOtcDailyListSourceArtifactV1:
    return FinraOtcDailyListSourceArtifactV1(
        sequence=page.sequence,
        file_name=_page_file_name(page.sequence),
        request_locator_sha256=page.request_locator_sha256,
        source_observed_at=page.source_observed_at,
        request_offset=page.request_offset,
        row_count=len(page.rows),
        byte_size=len(raw),
        physical_sha256=_sha256(raw),
    )


def _write_checkpoint(partial: Path, checkpoint: FinraOtcDailyListSourceCheckpointV1) -> None:
    path = partial / _CHECKPOINT_FILE
    temporary = partial / f".{_CHECKPOINT_FILE}.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise FinraOtcDailyListSourceError("FINRA checkpoint staging exists")
    _write_new_bytes(temporary, _json_bytes(checkpoint.model_dump(mode="json")), 0o600)
    temporary.replace(path)
    path.chmod(0o600)
    _fsync_directory(partial)


def _write_immutable_json(path: Path, value: object) -> None:
    _write_immutable_bytes(path, _json_bytes(value))


def _write_immutable_bytes(path: Path, raw: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise FinraOtcDailyListSourceError("FINRA immutable source target exists")
    _write_new_bytes(temporary, raw, 0o400)
    temporary.replace(path)
    _fsync_directory(path.parent)


def _write_new_bytes(path: Path, raw: bytes, mode: int) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(mode)


def _remove_known_temporary_files(partial: Path) -> None:
    allowed = {f".{_CHECKPOINT_FILE}.tmp"} | {
        f".{_page_file_name(sequence)}.tmp"
        for sequence in range(1, MAXIMUM_PAGE_COUNT + 1)
    }
    for path in partial.iterdir():
        if path.name in allowed:
            if path.is_symlink() or not path.is_file():
                raise FinraOtcDailyListSourceError("FINRA staging residue is unsafe")
            path.unlink()
    _fsync_directory(partial)


def _validate_file_set(root: Path, expected: set[str], *, completed: bool) -> None:
    actual: set[str] = set()
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise FinraOtcDailyListSourceError("FINRA package contains an unsafe entry")
        actual.add(path.name)
        expected_mode = 0o400 if completed else (0o600 if path.name == _CHECKPOINT_FILE else 0o400)
        _require_mode(path, expected_mode)
    if actual != expected:
        raise FinraOtcDailyListSourceError("FINRA package file set differs")


def _read_model(path: Path, model: type[BaseModel]):
    return _parse_model(_read_regular_file(path, maximum_bytes=MAXIMUM_PAGE_BYTES), model)


def _parse_model(raw: bytes, model: type[BaseModel]):
    try:
        return model.model_validate_json(raw)
    except Exception as exc:
        raise FinraOtcDailyListSourceError("FINRA custody document is invalid") from exc


def _read_regular_file(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise FinraOtcDailyListSourceError("FINRA custody file is invalid")
    size = path.stat().st_size
    if size < 1 or size > maximum_bytes:
        raise FinraOtcDailyListSourceError("FINRA custody file size is invalid")
    return path.read_bytes()


def _validate_endpoint(value: str) -> None:
    parsed = urlparse(value)
    expected = urlparse(ENDPOINT)
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != expected.path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise FinraOtcDailyListSourceError("FINRA endpoint is outside the allowlist")


def _page_file_name(sequence: int) -> str:
    return f"{_PAGE_PREFIX}{sequence:05d}{_PAGE_SUFFIX}"


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return _sha256(_json_bytes(value).rstrip(b"\n"))


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_mode(path: Path, expected: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != expected:
        raise FinraOtcDailyListSourceError("FINRA custody ownership or mode differs")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _result(
    manifest: FinraOtcDailyListSourcePackageManifestV1,
    package_path: Path,
    status: Literal["published", "already_present", "recovered_and_published"],
) -> FinraOtcDailyListSourcePackageResult:
    return FinraOtcDailyListSourcePackageResult(
        manifest=manifest,
        package_path=package_path,
        manifest_sha256=_sha256((package_path / _MANIFEST_FILE).read_bytes()),
        status=status,
    )
