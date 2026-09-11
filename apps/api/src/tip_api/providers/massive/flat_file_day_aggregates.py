"""Massive S3 Day Aggregates acquisition with transitive raw custody."""

from __future__ import annotations

import csv
import gzip
import io
import os
import stat
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from tip_api.providers.massive.same_day_catchup import (
    FLAT_FILE_DAY_AGGREGATES_ENDPOINT_CLASS,
    FetchPackageManifestV1,
    SameDayCatchupError,
    _new_fetch_package_path,
    _publish_fetch_package,
    sha256_bytes,
)


FLAT_FILE_ENDPOINT = "https://files.massive.com"
FLAT_FILE_BUCKET = "flatfiles"
FLAT_FILE_PREFIX = "us_stocks_sip/day_aggs_v1"
SOURCE_FILE_NAME = "source.csv.gz"
EXPECTED_HEADER = (
    "ticker",
    "volume",
    "open",
    "close",
    "high",
    "low",
    "window_start",
    "transactions",
)
MAXIMUM_COMPRESSED_BYTES = 5 * 1024 * 1024
MAXIMUM_DECOMPRESSED_BYTES = 32 * 1024 * 1024
MAXIMUM_RECORDS = 30_000

ACCESS_KEY_ENV = "TIP_MASSIVE_FLAT_FILES_ACCESS_KEY_ID"
SECRET_KEY_ENV = "TIP_MASSIVE_FLAT_FILES_SECRET_ACCESS_KEY"
FLAT_FILE_ENV_FILE_ENV = "TIP_MASSIVE_FLAT_FILES_ENV_FILE"
DEFAULT_FLAT_FILE_ENV_FILE = Path(
    "~/.config/trading-intelligence-platform/massive-flat-files.env"
)


class MassiveFlatFileError(RuntimeError):
    """Raised when Flat File access or source custody cannot be validated."""


class MassiveFlatFileAccessDeniedError(MassiveFlatFileError):
    """Raised when S3 rejects authentication or object entitlement."""


class MassiveFlatFileObjectNotFoundError(MassiveFlatFileError):
    """Raised when the exact allowlisted S3 object is unavailable."""


class MassiveFlatFileTransportError(MassiveFlatFileError):
    """Raised when S3 transport fails without a classified provider response."""


class MassiveFlatFileCredentialError(ValueError):
    """Raised when the private S3 credential boundary is unavailable."""


class MassiveFlatFileConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    access_key_id: SecretStr
    secret_access_key: SecretStr
    endpoint_url: str = FLAT_FILE_ENDPOINT
    bucket: str = FLAT_FILE_BUCKET

    @field_validator("access_key_id", "secret_access_key", mode="before")
    @classmethod
    def normalize_secret(cls, value: object) -> SecretStr:
        if isinstance(value, SecretStr):
            secret = value.get_secret_value().strip()
        elif isinstance(value, str):
            secret = value.strip()
        else:
            raise ValueError("Massive Flat File credential must be text")
        if not secret:
            raise ValueError("Massive Flat File credential is required")
        return SecretStr(secret)

    @field_validator("endpoint_url")
    @classmethod
    def fixed_endpoint(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        parsed = urlparse(normalized)
        if (
            normalized != FLAT_FILE_ENDPOINT
            or parsed.scheme != "https"
            or parsed.hostname != "files.massive.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Massive Flat File endpoint differs from allowlist")
        return normalized

    @field_validator("bucket")
    @classmethod
    def fixed_bucket(cls, value: str) -> str:
        if value.strip() != FLAT_FILE_BUCKET:
            raise ValueError("Massive Flat File bucket differs from allowlist")
        return FLAT_FILE_BUCKET


@dataclass(frozen=True, slots=True)
class MassiveFlatFileObject:
    body: bytes
    etag: str | None
    last_modified: datetime | None
    request_count: int = 1


class MassiveFlatFileTransport(Protocol):
    def get_object(self, *, bucket: str, object_key: str) -> MassiveFlatFileObject: ...


class Boto3MassiveFlatFileTransport:
    """Lazily constructed S3-compatible transport; secrets never enter output."""

    def __init__(self, config: MassiveFlatFileConfig) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise MassiveFlatFileError(
                "boto3 Flat File dependency is not installed"
            ) from exc
        session = boto3.Session(
            aws_access_key_id=config.access_key_id.get_secret_value(),
            aws_secret_access_key=config.secret_access_key.get_secret_value(),
        )
        self._client = session.client(
            "s3",
            endpoint_url=config.endpoint_url,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 0},
                connect_timeout=15,
                read_timeout=30,
            ),
        )

    def get_object(self, *, bucket: str, object_key: str) -> MassiveFlatFileObject:
        try:
            response = self._client.get_object(Bucket=bucket, Key=object_key)
            stream = response["Body"]
            body = stream.read(MAXIMUM_COMPRESSED_BYTES + 1)
            stream.close()
        except Exception as exc:  # pragma: no cover - exercised with fake S3 errors
            raise _classify_s3_failure(exc) from exc
        if len(body) > MAXIMUM_COMPRESSED_BYTES:
            raise MassiveFlatFileError("Massive Flat File exceeds byte ceiling")
        last_modified = response.get("LastModified")
        if isinstance(last_modified, datetime):
            if last_modified.tzinfo is None:
                raise MassiveFlatFileError("Flat File last-modified clock is naive")
            last_modified = last_modified.astimezone(UTC)
        elif last_modified is not None:
            raise MassiveFlatFileError("Flat File last-modified clock is malformed")
        etag = response.get("ETag")
        return MassiveFlatFileObject(
            body=body,
            etag=str(etag).strip('"') if etag is not None else None,
            last_modified=last_modified,
        )


def _classify_s3_failure(exc: Exception) -> MassiveFlatFileError:
    """Map only non-sensitive S3 code/status fields to stable local errors."""

    response = getattr(exc, "response", None)
    if not isinstance(response, Mapping):
        return MassiveFlatFileTransportError("Massive Flat File transport failed")
    error = response.get("Error")
    metadata = response.get("ResponseMetadata")
    code = error.get("Code") if isinstance(error, Mapping) else None
    status = (
        metadata.get("HTTPStatusCode") if isinstance(metadata, Mapping) else None
    )
    normalized_code = str(code).strip() if code is not None else ""
    if status in {401, 403} or normalized_code in {
        "AccessDenied",
        "ExpiredToken",
        "InvalidAccessKeyId",
        "InvalidToken",
        "SignatureDoesNotMatch",
    }:
        return MassiveFlatFileAccessDeniedError(
            "Massive Flat File authentication or entitlement was denied"
        )
    if status == 404 or normalized_code in {"NoSuchKey", "NotFound"}:
        return MassiveFlatFileObjectNotFoundError(
            "Massive Flat File object was not found"
        )
    return MassiveFlatFileTransportError("Massive Flat File transport failed")


def load_massive_flat_file_config_from_file(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> MassiveFlatFileConfig:
    env = os.environ if environ is None else environ
    raw_path = path or env.get(
        FLAT_FILE_ENV_FILE_ENV, str(DEFAULT_FLAT_FILE_ENV_FILE)
    )
    target = Path(str(raw_path).strip()).expanduser()
    if not str(raw_path).strip():
        raise MassiveFlatFileCredentialError(
            "Massive Flat File credential path is empty"
        )
    try:
        metadata = target.lstat()
    except FileNotFoundError as exc:
        raise MassiveFlatFileCredentialError(
            "Massive Flat File credential file does not exist"
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o077
    ):
        raise MassiveFlatFileCredentialError(
            "Massive Flat File credential custody is invalid"
        )
    values: dict[str, str] = {}
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise MassiveFlatFileCredentialError(
            "Massive Flat File credential file is not UTF-8"
        ) from exc
    allowed = {ACCESS_KEY_ENV, SECRET_KEY_ENV}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export ") or "=" not in stripped:
            raise MassiveFlatFileCredentialError(
                f"Malformed Flat File credential line: {line_number}"
            )
        key, value = (item.strip() for item in stripped.split("=", 1))
        if key not in allowed or key in values:
            raise MassiveFlatFileCredentialError(
                f"Unsupported or duplicate Flat File credential line: {line_number}"
            )
        if any(token in value for token in ("$(", "`", ";", "&&", "||")):
            raise MassiveFlatFileCredentialError(
                f"Unsupported Flat File credential syntax: {line_number}"
            )
        values[key] = value
    return MassiveFlatFileConfig(
        access_key_id=values.get(ACCESS_KEY_ENV, ""),
        secret_access_key=values.get(SECRET_KEY_ENV, ""),
    )


def day_aggregate_object_key(session_date: date) -> str:
    return (
        f"{FLAT_FILE_PREFIX}/{session_date.year:04d}/"
        f"{session_date.month:02d}/{session_date.isoformat()}.csv.gz"
    )


def fetch_flat_file_day_aggregate_package(
    *,
    config: MassiveFlatFileConfig,
    transport: MassiveFlatFileTransport,
    session_date: date,
    package_path: Path,
    fetched_at: datetime | None = None,
) -> FetchPackageManifestV1:
    validate_flat_file_package_target(
        package_path=package_path,
        session_date=session_date,
    )
    object_key = day_aggregate_object_key(session_date)
    source = transport.get_object(bucket=config.bucket, object_key=object_key)
    if source.request_count != 1:
        raise MassiveFlatFileError("Flat File fetch must use exactly one request")
    if not source.body or len(source.body) > MAXIMUM_COMPRESSED_BYTES:
        raise MassiveFlatFileError("Flat File body is absent or exceeds ceiling")
    if source.last_modified is not None and (
        source.last_modified.tzinfo is None
        or source.last_modified.utcoffset() is None
    ):
        raise MassiveFlatFileError("Flat File last-modified clock is naive")
    results = parse_flat_file_day_aggregate(source.body, session_date=session_date)
    source_sha = sha256_bytes(source.body)
    page: dict[str, Any] = {
        "adjusted": False,
        "queryCount": 1,
        "resultsCount": len(results),
        "status": "OK",
        "results": list(results),
        "source_artifact": {
            "transport": "massive_s3_flat_file",
            "bucket": config.bucket,
            "object_key": object_key,
            "file_name": SOURCE_FILE_NAME,
            "sha256": source_sha,
            "bytes": len(source.body),
            "etag": source.etag,
            "last_modified": (
                source.last_modified.astimezone(UTC).isoformat()
                if source.last_modified is not None
                else None
            ),
            "unadjusted": True,
        },
    }
    try:
        return _publish_fetch_package(
            package_path=package_path,
            package_type="grouped_daily",
            session_date=session_date,
            endpoint_class=FLAT_FILE_DAY_AGGREGATES_ENDPOINT_CLASS,
            adjusted=False,
            responses=(page,),
            request_count=1,
            pagination_complete=True,
            fetched_at=fetched_at or datetime.now(UTC),
            source_files=((SOURCE_FILE_NAME, source.body),),
        )
    except SameDayCatchupError as exc:
        raise MassiveFlatFileError("Flat File package publication failed") from exc


def parse_flat_file_day_aggregate(
    raw_gzip: bytes,
    *,
    session_date: date,
) -> tuple[dict[str, object], ...]:
    if not raw_gzip.startswith(b"\x1f\x8b"):
        raise MassiveFlatFileError("Flat File is not gzip encoded")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw_gzip)) as handle:
            raw_csv = handle.read(MAXIMUM_DECOMPRESSED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise MassiveFlatFileError("Flat File gzip payload is invalid") from exc
    if len(raw_csv) > MAXIMUM_DECOMPRESSED_BYTES:
        raise MassiveFlatFileError("Flat File decompressed content exceeds ceiling")
    try:
        text = raw_csv.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MassiveFlatFileError("Flat File CSV is not UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != EXPECTED_HEADER:
        raise MassiveFlatFileError("Flat File CSV header differs")
    from tip_api.providers.massive.grouped_daily_ingestion import (
        _session_date_from_timestamp_ms,
    )

    results: list[dict[str, object]] = []
    seen_tickers: set[str] = set()
    for row in reader:
        if len(results) >= MAXIMUM_RECORDS:
            raise MassiveFlatFileError("Flat File row count exceeds ceiling")
        if None in row or any(value is None for value in row.values()):
            raise MassiveFlatFileError("Flat File CSV row has malformed columns")
        ticker = row["ticker"].strip()
        if not ticker or ticker in seen_tickers:
            raise MassiveFlatFileError("Flat File ticker is absent or duplicated")
        seen_tickers.add(ticker)
        try:
            window_start_ns = int(row["window_start"])
        except ValueError as exc:
            raise MassiveFlatFileError("Flat File window_start is invalid") from exc
        if window_start_ns < 0 or window_start_ns % 1_000_000 != 0:
            raise MassiveFlatFileError(
                "Flat File window_start cannot convert exactly to milliseconds"
            )
        if _session_date_from_timestamp_ms(window_start_ns // 1_000_000) != session_date:
            raise MassiveFlatFileError("Flat File row belongs to another session")
        transactions = row["transactions"].strip()
        results.append(
            {
                "T": ticker,
                "v": row["volume"].strip(),
                "o": row["open"].strip(),
                "c": row["close"].strip(),
                "h": row["high"].strip(),
                "l": row["low"].strip(),
                "t": window_start_ns // 1_000_000,
                "n": transactions if transactions else None,
            }
        )
    if not results:
        raise MassiveFlatFileError("Flat File contains no aggregate rows")
    return tuple(results)


def validate_flat_file_grouped_payload(
    *,
    payload: Mapping[str, object],
    package_path: Path,
    session_date: date,
) -> None:
    source = payload.get("source_artifact")
    if not isinstance(source, Mapping):
        raise SameDayCatchupError("Flat File source custody is absent")
    expected_key = day_aggregate_object_key(session_date)
    expected = {
        "transport": "massive_s3_flat_file",
        "bucket": FLAT_FILE_BUCKET,
        "object_key": expected_key,
        "file_name": SOURCE_FILE_NAME,
        "unadjusted": True,
    }
    if any(source.get(key) != value for key, value in expected.items()):
        raise SameDayCatchupError("Flat File source identity differs")
    source_path = package_path / SOURCE_FILE_NAME
    if source_path.is_symlink() or not source_path.is_file():
        raise SameDayCatchupError("Flat File source artifact is unavailable")
    if source_path.stat().st_size > MAXIMUM_COMPRESSED_BYTES:
        raise SameDayCatchupError("Flat File source artifact exceeds byte ceiling")
    raw = source_path.read_bytes()
    if (
        source.get("bytes") != len(raw)
        or source.get("sha256") != sha256_bytes(raw)
    ):
        raise SameDayCatchupError("Flat File source artifact custody differs")
    try:
        expected_results = parse_flat_file_day_aggregate(
            raw, session_date=session_date
        )
    except MassiveFlatFileError as exc:
        raise SameDayCatchupError("Flat File source artifact is invalid") from exc
    if payload.get("results") != list(expected_results):
        raise SameDayCatchupError("Flat File normalized results differ from source")
    if (
        payload.get("adjusted") is not False
        or payload.get("resultsCount") != len(expected_results)
        or payload.get("queryCount") != 1
    ):
        raise SameDayCatchupError("Flat File normalized envelope differs")


def safe_flat_file_evidence(
    manifest: FetchPackageManifestV1,
) -> dict[str, object]:
    return {
        "package_type": manifest.package_type,
        "session_date": manifest.session_date.isoformat(),
        "endpoint_class": manifest.endpoint_class,
        "request_count": manifest.request_count,
        "fetched_at": manifest.fetched_at.isoformat(),
        "package_content_sha256": manifest.package_content_sha256,
    }


def validate_flat_file_package_target(
    *,
    package_path: Path,
    session_date: date,
) -> None:
    try:
        _new_fetch_package_path(package_path, session_date=session_date)
    except SameDayCatchupError as exc:
        raise MassiveFlatFileError("Flat File package target is invalid") from exc
