"""Resumable owner-only custody for bounded official SEC ZIP archives."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import zipfile
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from time import monotonic, sleep
from typing import BinaryIO, Callable, Iterator, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import _SafeRedirectHandler, validate_sec_url


COMPANYFACTS_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
)
CONTRACT_VERSION = "sec-companyfacts-source-package/1.0"
CHECKPOINT_VERSION = "sec-companyfacts-source-checkpoint/1.0"
ARCHIVE_FILE = "companyfacts.zip"
CHECKPOINT_FILE = "checkpoint.json"
MANIFEST_FILE = "package.json"
DEFAULT_CHUNK_BYTES = 128 * 1024 * 1024
MAXIMUM_ARCHIVE_BYTES = 8 * 1024 * 1024 * 1024
MAXIMUM_CHUNK_COUNT = 64
MAXIMUM_HEAD_REQUEST_COUNT = 16
MAXIMUM_REQUEST_COUNT = MAXIMUM_CHUNK_COUNT + MAXIMUM_HEAD_REQUEST_COUNT
MAXIMUM_MEMBER_COUNT = 1_000_000
MAXIMUM_MEMBER_BYTES = 512 * 1024 * 1024
MAXIMUM_TOTAL_UNCOMPRESSED_BYTES = 128 * 1024 * 1024 * 1024
MAXIMUM_COMPRESSION_RATIO = 500
MAXIMUM_JSON_BYTES = 4 * 1024 * 1024
_CIK_MEMBER = re.compile(r"CIK(?P<cik>[0-9]{10})\.json\Z")
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class SecCompanyfactsSourceError(RuntimeError):
    """Raised when a governed SEC archive package cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class SecArchiveSourceProfile:
    source_label: str
    contract_version: str
    checkpoint_version: str
    source_family: str
    url: str
    archive_file: str
    member_pattern: re.Pattern[str]
    allowed_non_cik_members: frozenset[str]
    require_unique_cik_per_member: bool
    require_root_member_per_cik: bool
    maximum_member_count: int
    maximum_member_bytes: int
    maximum_total_uncompressed_bytes: int
    maximum_compression_ratio: int
    source_availability_semantics: str

    def __post_init__(self) -> None:
        validate_sec_url(self.url)
        if (
            not self.source_label
            or len(self.source_label) > 128
            or not self.contract_version
            or len(self.contract_version) > 128
            or not self.checkpoint_version
            or len(self.checkpoint_version) > 128
            or not self.source_family
            or len(self.source_family) > 128
            or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*\.zip", self.archive_file)
            or "cik" not in self.member_pattern.groupindex
            or any(
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name)
                for name in self.allowed_non_cik_members
            )
            or self.maximum_member_count < 1
            or self.maximum_member_count > MAXIMUM_MEMBER_COUNT
            or self.maximum_member_bytes < 1
            or self.maximum_member_bytes > MAXIMUM_MEMBER_BYTES
            or self.maximum_total_uncompressed_bytes < 1
            or self.maximum_total_uncompressed_bytes
            > MAXIMUM_TOTAL_UNCOMPRESSED_BYTES
            or self.maximum_compression_ratio < 1
            or self.maximum_compression_ratio > MAXIMUM_COMPRESSION_RATIO
            or not self.source_availability_semantics
            or len(self.source_availability_semantics) > 256
        ):
            raise ValueError("SEC archive source profile is invalid")


COMPANYFACTS_PROFILE = SecArchiveSourceProfile(
    source_label="Company Facts",
    contract_version=CONTRACT_VERSION,
    checkpoint_version=CHECKPOINT_VERSION,
    source_family="companyfacts_bulk_archive",
    url=COMPANYFACTS_URL,
    archive_file=ARCHIVE_FILE,
    member_pattern=_CIK_MEMBER,
    allowed_non_cik_members=frozenset(),
    require_unique_cik_per_member=True,
    require_root_member_per_cik=True,
    maximum_member_count=100_000,
    maximum_member_bytes=MAXIMUM_MEMBER_BYTES,
    maximum_total_uncompressed_bytes=MAXIMUM_TOTAL_UNCOMPRESSED_BYTES,
    maximum_compression_ratio=MAXIMUM_COMPRESSION_RATIO,
    source_availability_semantics=(
        "snapshot_observed_now_filing_dates_preserved_downstream"
    ),
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCompanyfactsRemoteMetadataV1(_FrozenModel):
    url: str = Field(default=COMPANYFACTS_URL, min_length=1, max_length=2048)
    content_type: Literal["application/zip"] = "application/zip"
    content_length: int = Field(ge=1, le=MAXIMUM_ARCHIVE_BYTES)
    last_modified: datetime
    etag: str = Field(min_length=1, max_length=512)
    accept_ranges: Literal["bytes"] = "bytes"
    observed_at: datetime

    @field_validator("last_modified", "observed_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("etag")
    @classmethod
    def etag_is_safe(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(char) < 32 or ord(char) > 126 for char in normalized):
            raise ValueError("SEC Company Facts ETag is invalid")
        return normalized

    @field_validator("url")
    @classmethod
    def url_is_approved_sec_https(cls, value: str) -> str:
        return validate_sec_url(value)


class SecCompanyfactsChunkV1(_FrozenModel):
    sequence: int = Field(ge=1, le=MAXIMUM_CHUNK_COUNT)
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    byte_count: int = Field(ge=1, le=DEFAULT_CHUNK_BYTES)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def range_reconciles(self) -> "SecCompanyfactsChunkV1":
        if self.byte_end < self.byte_start or self.byte_count != self.byte_end - self.byte_start + 1:
            raise ValueError("SEC Company Facts chunk range differs")
        return self


class SecCompanyfactsCheckpointV1(_FrozenModel):
    contract_version: str = Field(
        default=CHECKPOINT_VERSION, min_length=1, max_length=128
    )
    state: Literal["in_progress", "complete"]
    remote: SecCompanyfactsRemoteMetadataV1
    started_at: datetime
    last_observed_at: datetime
    chunk_bytes: Literal[DEFAULT_CHUNK_BYTES] = DEFAULT_CHUNK_BYTES
    chunks: tuple[SecCompanyfactsChunkV1, ...]
    committed_bytes: int = Field(ge=0, le=MAXIMUM_ARCHIVE_BYTES)
    head_request_count: int = Field(ge=1, le=MAXIMUM_HEAD_REQUEST_COUNT)
    request_count: int = Field(ge=1, le=MAXIMUM_REQUEST_COUNT)
    credential_material_retained: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("started_at", "last_observed_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def checkpoint_reconciles(self) -> "SecCompanyfactsCheckpointV1":
        if self.last_observed_at < self.started_at:
            raise ValueError("SEC Company Facts checkpoint time differs")
        if self.request_count != len(self.chunks) + self.head_request_count:
            raise ValueError("SEC Company Facts request count differs")
        cursor = 0
        for expected_sequence, chunk in enumerate(self.chunks, 1):
            if chunk.sequence != expected_sequence or chunk.byte_start != cursor:
                raise ValueError("SEC Company Facts chunk chain differs")
            cursor = chunk.byte_end + 1
        if self.committed_bytes != cursor:
            raise ValueError("SEC Company Facts committed byte count differs")
        expected_state = (
            "complete"
            if self.committed_bytes == self.remote.content_length
            else "in_progress"
        )
        if self.state != expected_state:
            raise ValueError("SEC Company Facts checkpoint state differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC Company Facts checkpoint fingerprint differs")
        return self


class SecCompanyfactsSourceManifestV1(_FrozenModel):
    contract_version: str = Field(
        default=CONTRACT_VERSION, min_length=1, max_length=128
    )
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    source_family: str = Field(
        default="companyfacts_bulk_archive", min_length=1, max_length=128
    )
    remote: SecCompanyfactsRemoteMetadataV1
    started_at: datetime
    completed_at: datetime
    chunks: tuple[SecCompanyfactsChunkV1, ...] = Field(min_length=1)
    head_request_count: int = Field(ge=1, le=MAXIMUM_HEAD_REQUEST_COUNT)
    request_count: int = Field(ge=2, le=MAXIMUM_REQUEST_COUNT)
    archive_bytes: int = Field(ge=1, le=MAXIMUM_ARCHIVE_BYTES)
    archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    member_count: int = Field(ge=1, le=MAXIMUM_MEMBER_COUNT)
    unique_cik_count: int = Field(ge=1, le=MAXIMUM_MEMBER_COUNT)
    member_name_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    total_compressed_bytes: int = Field(ge=1, le=MAXIMUM_ARCHIVE_BYTES)
    total_uncompressed_bytes: int = Field(
        ge=1, le=MAXIMUM_TOTAL_UNCOMPRESSED_BYTES
    )
    archive_validation_status: Literal["central_directory_validated"] = (
        "central_directory_validated"
    )
    member_payload_validation_status: Literal["deferred_to_normalization"] = (
        "deferred_to_normalization"
    )
    source_availability_semantics: str = Field(min_length=1, max_length=256)
    external_request_count: int = Field(ge=2, le=MAXIMUM_REQUEST_COUNT)
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    credential_material_retained: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "SecCompanyfactsSourceManifestV1":
        if self.completed_at < self.started_at:
            raise ValueError("SEC Company Facts completion time differs")
        if self.archive_bytes != self.remote.content_length:
            raise ValueError("SEC Company Facts archive length differs")
        if (
            self.request_count != len(self.chunks) + self.head_request_count
            or self.external_request_count != self.request_count
        ):
            raise ValueError("SEC Company Facts manifest request count differs")
        if sum(item.byte_count for item in self.chunks) != self.archive_bytes:
            raise ValueError("SEC Company Facts chunk byte total differs")
        if self.unique_cik_count > self.member_count:
            raise ValueError("SEC archive CIK population differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC Company Facts manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecCompanyfactsRangeResult:
    byte_count: int
    physical_sha256: str


@dataclass(frozen=True, slots=True)
class SecCompanyfactsPackageResult:
    package_path: Path
    manifest: SecCompanyfactsSourceManifestV1
    manifest_sha256: str
    status: Literal["published", "already_present", "recovered_and_published"]


class SecCompanyfactsTransport(Protocol):
    def head(
        self,
        *,
        url: str,
        user_agent: SecretStr,
        timeout_seconds: float,
        observed_at: datetime,
    ) -> SecCompanyfactsRemoteMetadataV1: ...

    def download_range(
        self,
        *,
        url: str,
        target: BinaryIO,
        byte_start: int,
        byte_end: int,
        expected: SecCompanyfactsRemoteMetadataV1,
        user_agent: SecretStr,
        timeout_seconds: float,
    ) -> SecCompanyfactsRangeResult: ...


ProgressCallback = Callable[[SecCompanyfactsChunkV1, int, int], None]


class SecCompanyfactsFixedIntervalLimiter:
    def __init__(
        self,
        *,
        requests_per_second: float = 2.0,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if requests_per_second <= 0 or requests_per_second > 2:
            raise ValueError("SEC request rate must be in (0, 2]")
        self._interval = 1.0 / requests_per_second
        self._clock = clock
        self._sleeper = sleeper
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            remaining = self._interval - (now - self._last)
            if remaining > 0:
                self._sleeper(remaining)
                now = self._clock()
        self._last = now


class SecCompanyfactsUrllibTransport:
    def __init__(self, *, opener: object | None = None) -> None:
        self._opener = opener or build_opener(_SafeRedirectHandler())

    def head(
        self,
        *,
        url: str,
        user_agent: SecretStr,
        timeout_seconds: float,
        observed_at: datetime,
    ) -> SecCompanyfactsRemoteMetadataV1:
        validate_sec_url(url)
        request = Request(
            url,
            headers={
                "User-Agent": user_agent.get_secret_value(),
                "Accept-Encoding": "identity",
            },
            method="HEAD",
        )
        try:
            response = self._opener.open(request, timeout=timeout_seconds)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise SecCompanyfactsSourceError("SEC Company Facts HEAD failed") from exc
        with response:
            if int(getattr(response, "status", 200)) != 200:
                raise SecCompanyfactsSourceError("SEC Company Facts HEAD status differs")
            return _remote_metadata(response.headers, observed_at, url)

    def download_range(
        self,
        *,
        url: str,
        target: BinaryIO,
        byte_start: int,
        byte_end: int,
        expected: SecCompanyfactsRemoteMetadataV1,
        user_agent: SecretStr,
        timeout_seconds: float,
    ) -> SecCompanyfactsRangeResult:
        validate_sec_url(url)
        request = Request(
            url,
            headers={
                "User-Agent": user_agent.get_secret_value(),
                "Accept-Encoding": "identity",
                "Range": f"bytes={byte_start}-{byte_end}",
                "If-Match": expected.etag,
            },
            method="GET",
        )
        try:
            response = self._opener.open(request, timeout=timeout_seconds)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise SecCompanyfactsSourceError("SEC Company Facts range request failed") from exc
        expected_count = byte_end - byte_start + 1
        digest = hashlib.sha256()
        count = 0
        with response:
            headers = response.headers
            if int(getattr(response, "status", 200)) != 206:
                raise SecCompanyfactsSourceError("SEC Company Facts range status differs")
            if str(headers.get_content_type()).lower() != expected.content_type:
                raise SecCompanyfactsSourceError("SEC Company Facts range content type differs")
            if headers.get("Content-Range") != f"bytes {byte_start}-{byte_end}/{expected.content_length}":
                raise SecCompanyfactsSourceError("SEC Company Facts content range differs")
            if headers.get("ETag", "").strip() != expected.etag:
                raise SecCompanyfactsSourceError("SEC Company Facts ETag changed")
            modified = _http_datetime(headers.get("Last-Modified"))
            if modified != expected.last_modified:
                raise SecCompanyfactsSourceError("SEC Company Facts object changed")
            declared = headers.get("Content-Length")
            if declared is None or int(declared) != expected_count:
                raise SecCompanyfactsSourceError("SEC Company Facts range length differs")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > expected_count:
                    raise SecCompanyfactsSourceError("SEC Company Facts range exceeded")
                digest.update(chunk)
                target.write(chunk)
        if count != expected_count:
            raise SecCompanyfactsSourceError("SEC Company Facts range is incomplete")
        return SecCompanyfactsRangeResult(count, digest.hexdigest())


def acquire_sec_companyfacts_source_package(
    *,
    config: SecProviderConfig,
    package_path: Path,
    approved_custody_root: Path,
    transport: SecCompanyfactsTransport | None = None,
    rate_limiter: SecCompanyfactsFixedIntervalLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    progress: ProgressCallback | None = None,
) -> SecCompanyfactsPackageResult:
    """Acquire or resume one exact remote Company Facts archive snapshot."""

    return acquire_sec_resumable_zip_source_package(
        profile=COMPANYFACTS_PROFILE,
        config=config,
        package_path=package_path,
        approved_custody_root=approved_custody_root,
        transport=transport,
        rate_limiter=rate_limiter,
        clock=clock,
        progress=progress,
    )


def acquire_sec_resumable_zip_source_package(
    *,
    profile: SecArchiveSourceProfile,
    config: SecProviderConfig,
    package_path: Path,
    approved_custody_root: Path,
    transport: SecCompanyfactsTransport | None = None,
    rate_limiter: SecCompanyfactsFixedIntervalLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    progress: ProgressCallback | None = None,
) -> SecCompanyfactsPackageResult:
    """Acquire or resume one exact profile-bound official SEC ZIP snapshot."""

    target = _validate_target(package_path, approved_custody_root)
    with _package_lock(target):
        return _acquire_sec_resumable_zip_source_package_locked(
            profile=profile,
            config=config,
            package_path=target,
            approved_custody_root=approved_custody_root,
            transport=transport,
            rate_limiter=rate_limiter,
            clock=clock,
            progress=progress,
        )


def _acquire_sec_resumable_zip_source_package_locked(
    *,
    profile: SecArchiveSourceProfile,
    config: SecProviderConfig,
    package_path: Path,
    approved_custody_root: Path,
    transport: SecCompanyfactsTransport | None,
    rate_limiter: SecCompanyfactsFixedIntervalLimiter | None,
    clock: Callable[[], datetime] | None,
    progress: ProgressCallback | None,
) -> SecCompanyfactsPackageResult:
    target = _validate_target(package_path, approved_custody_root)
    if target.exists():
        result = read_sec_resumable_zip_source_package(
            profile=profile,
            package_path=target,
            approved_custody_root=approved_custody_root,
        )
        return SecCompanyfactsPackageResult(
            target, result, _sha256_file(target / MANIFEST_FILE), "already_present"
        )
    client = transport or SecCompanyfactsUrllibTransport()
    limiter = rate_limiter or SecCompanyfactsFixedIntervalLimiter()
    now = clock or (lambda: datetime.now(UTC))
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() and (partial / MANIFEST_FILE).exists():
        manifest = _read_completed_tree(partial, profile)
        if target.name != f"snapshot={manifest.remote.last_modified.date().isoformat()}":
            raise SecCompanyfactsSourceError("SEC Company Facts orphan date differs")
        partial.replace(target)
        _fsync_directory(target.parent)
        reread = read_sec_resumable_zip_source_package(
            profile=profile,
            package_path=target, approved_custody_root=approved_custody_root
        )
        return SecCompanyfactsPackageResult(
            target,
            reread,
            _sha256_file(target / MANIFEST_FILE),
            "recovered_and_published",
        )
    recovered = partial.exists()
    if recovered:
        checkpoint = _read_partial_checkpoint(partial, profile)
        _truncate_to_checkpoint(partial / profile.archive_file, checkpoint)
        if checkpoint.head_request_count >= MAXIMUM_HEAD_REQUEST_COUNT:
            raise SecCompanyfactsSourceError("SEC Company Facts HEAD ceiling exceeded")
        limiter.wait()
        observed = client.head(
            url=profile.url,
            user_agent=config.user_agent,
            timeout_seconds=float(config.request_timeout_seconds),
            observed_at=normalize_utc_datetime(now()),
        )
        if _object_identity(observed) != _object_identity(checkpoint.remote):
            raise SecCompanyfactsSourceError("SEC Company Facts remote object changed")
        checkpoint = _checkpoint(
            contract_version=profile.checkpoint_version,
            state=checkpoint.state,
            remote=checkpoint.remote,
            started_at=checkpoint.started_at,
            last_observed_at=normalize_utc_datetime(now()),
            chunks=checkpoint.chunks,
            head_request_count=checkpoint.head_request_count + 1,
        )
        _write_checkpoint(partial, checkpoint)
    else:
        limiter.wait()
        observed = client.head(
            url=profile.url,
            user_agent=config.user_agent,
            timeout_seconds=float(config.request_timeout_seconds),
            observed_at=normalize_utc_datetime(now()),
        )
        if target.name != f"snapshot={observed.last_modified.date().isoformat()}":
            raise SecCompanyfactsSourceError("SEC Company Facts target date differs")
        partial.mkdir(mode=0o700)
        archive = partial / profile.archive_file
        descriptor = os.open(archive, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(descriptor)
        checkpoint = _checkpoint(
            contract_version=profile.checkpoint_version,
            state="in_progress",
            remote=observed,
            started_at=normalize_utc_datetime(now()),
            last_observed_at=normalize_utc_datetime(now()),
            chunks=(),
            head_request_count=1,
        )
        _write_checkpoint(partial, checkpoint)

    archive = partial / profile.archive_file
    while checkpoint.state == "in_progress":
        if len(checkpoint.chunks) >= MAXIMUM_CHUNK_COUNT:
            raise SecCompanyfactsSourceError("SEC Company Facts chunk ceiling exceeded")
        byte_start = checkpoint.committed_bytes
        byte_end = min(
            byte_start + DEFAULT_CHUNK_BYTES - 1,
            checkpoint.remote.content_length - 1,
        )
        with archive.open("r+b") as handle:
            handle.seek(byte_start)
            limiter.wait()
            result = client.download_range(
                url=profile.url,
                target=handle,
                byte_start=byte_start,
                byte_end=byte_end,
                expected=checkpoint.remote,
                user_agent=config.user_agent,
                timeout_seconds=float(config.request_timeout_seconds),
            )
            handle.flush()
            os.fsync(handle.fileno())
        chunk = SecCompanyfactsChunkV1(
            sequence=len(checkpoint.chunks) + 1,
            byte_start=byte_start,
            byte_end=byte_end,
            byte_count=result.byte_count,
            physical_sha256=result.physical_sha256,
        )
        state = "complete" if byte_end + 1 == checkpoint.remote.content_length else "in_progress"
        checkpoint = _checkpoint(
            contract_version=profile.checkpoint_version,
            state=state,
            remote=checkpoint.remote,
            started_at=checkpoint.started_at,
            last_observed_at=normalize_utc_datetime(now()),
            chunks=checkpoint.chunks + (chunk,),
            head_request_count=checkpoint.head_request_count,
        )
        _write_checkpoint(partial, checkpoint)
        if progress is not None:
            progress(
                chunk,
                checkpoint.committed_bytes,
                checkpoint.remote.content_length,
            )

    manifest = _finalize(partial, target, checkpoint, profile)
    reread = read_sec_resumable_zip_source_package(
        profile=profile,
        package_path=target, approved_custody_root=approved_custody_root
    )
    if reread != manifest:
        raise SecCompanyfactsSourceError("SEC Company Facts formal reread differs")
    return SecCompanyfactsPackageResult(
        target,
        reread,
        _sha256_file(target / MANIFEST_FILE),
        "recovered_and_published" if recovered else "published",
    )


def read_sec_companyfacts_source_package(
    *, package_path: Path, approved_custody_root: Path
) -> SecCompanyfactsSourceManifestV1:
    return read_sec_resumable_zip_source_package(
        profile=COMPANYFACTS_PROFILE,
        package_path=package_path,
        approved_custody_root=approved_custody_root,
    )


def read_sec_resumable_zip_source_package(
    *,
    profile: SecArchiveSourceProfile,
    package_path: Path,
    approved_custody_root: Path,
) -> SecCompanyfactsSourceManifestV1:
    root = _validate_completed(package_path, approved_custody_root)
    return _read_completed_tree(root, profile)


def _read_completed_tree(
    root: Path, profile: SecArchiveSourceProfile
) -> SecCompanyfactsSourceManifestV1:
    if root.is_symlink() or not root.is_dir():
        raise SecCompanyfactsSourceError("SEC Company Facts completed tree is unsafe")
    _require_mode(root, 0o700)
    manifest = _read_model(root / MANIFEST_FILE, SecCompanyfactsSourceManifestV1)
    checkpoint = _read_model(root / CHECKPOINT_FILE, SecCompanyfactsCheckpointV1)
    if (
        checkpoint.state != "complete"
        or checkpoint.remote != manifest.remote
        or checkpoint.started_at != manifest.started_at
        or checkpoint.last_observed_at != manifest.completed_at
        or checkpoint.chunks != manifest.chunks
        or checkpoint.head_request_count != manifest.head_request_count
        or checkpoint.request_count != manifest.request_count
        or checkpoint.committed_bytes != manifest.archive_bytes
    ):
        raise SecCompanyfactsSourceError("SEC Company Facts checkpoint differs")
    if (
        manifest.contract_version != profile.contract_version
        or manifest.source_family != profile.source_family
        or manifest.remote.url != profile.url
        or manifest.source_availability_semantics
        != profile.source_availability_semantics
        or checkpoint.contract_version != profile.checkpoint_version
    ):
        raise SecCompanyfactsSourceError("SEC archive source profile differs")
    expected = {profile.archive_file, CHECKPOINT_FILE, MANIFEST_FILE}
    actual = {item.name for item in root.iterdir()}
    if actual != expected:
        raise SecCompanyfactsSourceError("SEC Company Facts package file set differs")
    for item in root.iterdir():
        _require_file(item, 0o400)
    archive = root / profile.archive_file
    if archive.stat().st_size != manifest.archive_bytes or _sha256_file(archive) != manifest.archive_sha256:
        raise SecCompanyfactsSourceError("SEC Company Facts archive hash differs")
    zip_values = _zip_census(archive, profile)
    for key, value in zip_values.items():
        if getattr(manifest, key) != value:
            raise SecCompanyfactsSourceError("SEC Company Facts ZIP census differs")
    _verify_chunk_hashes(archive, manifest.chunks)
    return manifest


def _finalize(
    partial: Path,
    target: Path,
    checkpoint: SecCompanyfactsCheckpointV1,
    profile: SecArchiveSourceProfile,
) -> SecCompanyfactsSourceManifestV1:
    archive = partial / profile.archive_file
    if checkpoint.state != "complete" or archive.stat().st_size != checkpoint.committed_bytes:
        raise SecCompanyfactsSourceError("SEC Company Facts partial is incomplete")
    _verify_chunk_hashes(archive, checkpoint.chunks)
    zip_values = _zip_census(archive, profile)
    values = {
        "contract_version": profile.contract_version,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "source_family": profile.source_family,
        "remote": checkpoint.remote,
        "started_at": checkpoint.started_at,
        "completed_at": checkpoint.last_observed_at,
        "chunks": checkpoint.chunks,
        "head_request_count": checkpoint.head_request_count,
        "request_count": checkpoint.request_count,
        "archive_bytes": checkpoint.committed_bytes,
        "archive_sha256": _sha256_file(archive),
        **zip_values,
        "archive_validation_status": "central_directory_validated",
        "member_payload_validation_status": "deferred_to_normalization",
        "source_availability_semantics": profile.source_availability_semantics,
        "external_request_count": checkpoint.request_count,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
        "credential_material_retained": False,
    }
    manifest = SecCompanyfactsSourceManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )
    _write_manifest(partial, manifest)
    for item in partial.iterdir():
        item.chmod(0o400)
    partial.chmod(0o700)
    _fsync_directory(partial)
    partial.replace(target)
    _fsync_directory(target.parent)
    return manifest


def _zip_census(
    path: Path, profile: SecArchiveSourceProfile
) -> dict[str, object]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SecCompanyfactsSourceError("SEC Company Facts ZIP is invalid") from exc
    with archive:
        members = archive.infolist()
        if not members or len(members) > profile.maximum_member_count:
            raise SecCompanyfactsSourceError("SEC Company Facts member count differs")
        names: list[str] = []
        seen_names: set[str] = set()
        ciks: set[str] = set()
        root_ciks: set[str] = set()
        total_compressed = 0
        total_uncompressed = 0
        for member in members:
            match = profile.member_pattern.fullmatch(member.filename)
            allowed_non_cik = member.filename in profile.allowed_non_cik_members
            if (
                (match is None and not allowed_non_cik)
                or member.is_dir()
                or member.flag_bits & 0x1
                or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                or member.file_size < 1
                or member.file_size > profile.maximum_member_bytes
                or member.compress_size < 1
            ):
                raise SecCompanyfactsSourceError("SEC Company Facts member is unsafe")
            normalized = member.filename.casefold()
            if normalized in seen_names:
                raise SecCompanyfactsSourceError("SEC Company Facts member is duplicated")
            ratio = member.file_size / member.compress_size
            if ratio > profile.maximum_compression_ratio:
                raise SecCompanyfactsSourceError("SEC Company Facts member ratio differs")
            names.append(member.filename)
            seen_names.add(normalized)
            if match is not None:
                cik = match.group("cik")
                ciks.add(cik)
                if match.groupdict().get("shard") is None:
                    root_ciks.add(cik)
            total_compressed += member.compress_size
            total_uncompressed += member.file_size
            if total_uncompressed > profile.maximum_total_uncompressed_bytes:
                raise SecCompanyfactsSourceError("SEC Company Facts expansion exceeds ceiling")
        if profile.require_unique_cik_per_member and len(ciks) != len(names):
            raise SecCompanyfactsSourceError("SEC Company Facts CIK members collide")
        if profile.require_root_member_per_cik and root_ciks != ciks:
            raise SecCompanyfactsSourceError("SEC archive CIK root coverage differs")
        return {
            "member_count": len(names),
            "unique_cik_count": len(ciks),
            "member_name_fingerprint": _fingerprint(tuple(sorted(names))),
            "total_compressed_bytes": total_compressed,
            "total_uncompressed_bytes": total_uncompressed,
        }


def _remote_metadata(
    headers: object, observed_at: datetime, url: str
) -> SecCompanyfactsRemoteMetadataV1:
    try:
        content_type = str(headers.get_content_type()).lower()  # type: ignore[attr-defined]
        content_length = int(headers.get("Content-Length"))  # type: ignore[attr-defined]
        last_modified = _http_datetime(headers.get("Last-Modified"))  # type: ignore[attr-defined]
        etag = str(headers.get("ETag") or "")  # type: ignore[attr-defined]
        accept_ranges = str(headers.get("Accept-Ranges") or "").lower()  # type: ignore[attr-defined]
    except (TypeError, ValueError, AttributeError) as exc:
        raise SecCompanyfactsSourceError("SEC Company Facts metadata is malformed") from exc
    return SecCompanyfactsRemoteMetadataV1(
        url=url,
        content_type=content_type,
        content_length=content_length,
        last_modified=last_modified,
        etag=etag,
        accept_ranges=accept_ranges,
        observed_at=observed_at,
    )


def _http_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SecCompanyfactsSourceError("SEC Company Facts timestamp is absent")
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as exc:
        raise SecCompanyfactsSourceError("SEC Company Facts timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise SecCompanyfactsSourceError("SEC Company Facts timestamp has no timezone")
    return normalize_utc_datetime(parsed)


def _object_identity(remote: SecCompanyfactsRemoteMetadataV1) -> tuple[object, ...]:
    return (
        remote.url,
        remote.content_type,
        remote.content_length,
        remote.last_modified,
        remote.etag,
        remote.accept_ranges,
    )


def _checkpoint(
    *,
    contract_version: str,
    state: Literal["in_progress", "complete"],
    remote: SecCompanyfactsRemoteMetadataV1,
    started_at: datetime,
    last_observed_at: datetime,
    chunks: tuple[SecCompanyfactsChunkV1, ...],
    head_request_count: int,
) -> SecCompanyfactsCheckpointV1:
    values = {
        "contract_version": contract_version,
        "state": state,
        "remote": remote,
        "started_at": started_at,
        "last_observed_at": last_observed_at,
        "chunk_bytes": DEFAULT_CHUNK_BYTES,
        "chunks": chunks,
        "committed_bytes": sum(item.byte_count for item in chunks),
        "head_request_count": head_request_count,
        "request_count": len(chunks) + head_request_count,
        "credential_material_retained": False,
    }
    return SecCompanyfactsCheckpointV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _read_partial_checkpoint(
    partial: Path, profile: SecArchiveSourceProfile
) -> SecCompanyfactsCheckpointV1:
    if partial.is_symlink() or not partial.is_dir():
        raise SecCompanyfactsSourceError("SEC Company Facts partial is unsafe")
    _require_mode(partial, 0o700)
    actual = {item.name for item in partial.iterdir()}
    if actual != {profile.archive_file, CHECKPOINT_FILE}:
        raise SecCompanyfactsSourceError("SEC Company Facts partial file set differs")
    _require_file(partial / profile.archive_file, 0o600)
    _require_file(partial / CHECKPOINT_FILE, 0o600)
    checkpoint = _read_model(partial / CHECKPOINT_FILE, SecCompanyfactsCheckpointV1)
    if (
        checkpoint.contract_version != profile.checkpoint_version
        or checkpoint.remote.url != profile.url
    ):
        raise SecCompanyfactsSourceError("SEC archive partial profile differs")
    _verify_chunk_hashes(partial / profile.archive_file, checkpoint.chunks)
    return checkpoint


def _truncate_to_checkpoint(path: Path, checkpoint: SecCompanyfactsCheckpointV1) -> None:
    if path.stat().st_size < checkpoint.committed_bytes:
        raise SecCompanyfactsSourceError("SEC Company Facts partial archive is short")
    with path.open("r+b") as handle:
        handle.truncate(checkpoint.committed_bytes)
        handle.flush()
        os.fsync(handle.fileno())


def _verify_chunk_hashes(path: Path, chunks: tuple[SecCompanyfactsChunkV1, ...]) -> None:
    with path.open("rb") as handle:
        for chunk in chunks:
            handle.seek(chunk.byte_start)
            remaining = chunk.byte_count
            digest = hashlib.sha256()
            while remaining:
                payload = handle.read(min(1024 * 1024, remaining))
                if not payload:
                    raise SecCompanyfactsSourceError("SEC Company Facts chunk is incomplete")
                digest.update(payload)
                remaining -= len(payload)
            if digest.hexdigest() != chunk.physical_sha256:
                raise SecCompanyfactsSourceError("SEC Company Facts chunk hash differs")


def _write_checkpoint(partial: Path, checkpoint: SecCompanyfactsCheckpointV1) -> None:
    target = partial / CHECKPOINT_FILE
    temporary = partial / f".{CHECKPOINT_FILE}.tmp"
    if temporary.exists() or temporary.is_symlink():
        if temporary.is_symlink() or not temporary.is_file():
            raise SecCompanyfactsSourceError("SEC Company Facts checkpoint residue is unsafe")
        temporary.unlink()
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(_json_bytes(checkpoint.model_dump(mode="json")) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    temporary.replace(target)
    target.chmod(0o600)
    _fsync_directory(partial)


def _write_manifest(
    partial: Path, manifest: SecCompanyfactsSourceManifestV1
) -> None:
    target = partial / MANIFEST_FILE
    temporary = partial / f".{MANIFEST_FILE}.tmp"
    if target.exists() or target.is_symlink():
        raise SecCompanyfactsSourceError("SEC Company Facts manifest already exists")
    if temporary.exists() or temporary.is_symlink():
        if temporary.is_symlink() or not temporary.is_file():
            raise SecCompanyfactsSourceError("SEC Company Facts manifest residue is unsafe")
        metadata = temporary.stat()
        if metadata.st_uid != os.getuid():
            raise SecCompanyfactsSourceError("SEC Company Facts manifest residue differs")
        temporary.unlink()
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(_json_bytes(manifest.model_dump(mode="json")) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    temporary.replace(target)
    _fsync_directory(partial)


def _validate_target(path: Path, approved_root: Path) -> Path:
    root = approved_root.absolute()
    target = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecCompanyfactsSourceError("SEC Company Facts custody root is unsafe")
    _require_mode(root, 0o700)
    if target.parent != root or not re.fullmatch(r"snapshot=20[0-9]{2}-[0-9]{2}-[0-9]{2}", target.name):
        raise SecCompanyfactsSourceError("SEC Company Facts target path differs")
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise SecCompanyfactsSourceError("SEC Company Facts target is unsafe")
    partial = target.parent / f".{target.name}.partial"
    if partial.is_symlink() or (partial.exists() and not partial.is_dir()):
        raise SecCompanyfactsSourceError("SEC Company Facts partial target is unsafe")
    return target


@contextmanager
def _package_lock(target: Path) -> Iterator[None]:
    lock_path = target.parent / f".{target.name}.lock"
    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "r+b") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise SecCompanyfactsSourceError("SEC Company Facts lock is unsafe")
        os.fchmod(handle.fileno(), 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def _validate_completed(path: Path, approved_root: Path) -> Path:
    target = _validate_target(path, approved_root)
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise SecCompanyfactsSourceError("SEC Company Facts completed and partial coexist")
    if not target.is_dir() or target.resolve(strict=True) != target:
        raise SecCompanyfactsSourceError("SEC Company Facts package is unavailable")
    _require_mode(target, 0o700)
    return target


def _read_model(path: Path, model: type[BaseModel]):
    _require_file(path, 0o400 if path.name == MANIFEST_FILE else stat.S_IMODE(path.stat().st_mode))
    if path.stat().st_size < 1 or path.stat().st_size > MAXIMUM_JSON_BYTES:
        raise SecCompanyfactsSourceError("SEC Company Facts JSON size differs")
    try:
        return model.model_validate_json(path.read_bytes())
    except Exception as exc:
        raise SecCompanyfactsSourceError("SEC Company Facts JSON is invalid") from exc


def _require_file(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise SecCompanyfactsSourceError("SEC Company Facts file is unsafe")
    _require_mode(path, mode)


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecCompanyfactsSourceError("SEC Company Facts ownership or mode differs")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
