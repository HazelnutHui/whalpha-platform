"""Approval-bound same-day Massive Identity and canonical EOD publication.

Only fetch mode can use a provider transport.  Planning and approved apply are
strictly offline.  Provider JSON is held in a caller-selected private /tmp
package; production receives only the existing canonical Parquet contracts.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import socket
import stat
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from tip_api.ingestion.instrument_master_snapshot import InstrumentMasterSnapshotIngestionService
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    MANIFEST_FILE_NAME as IDENTITY_MANIFEST_FILE,
    PARQUET_FILE_NAME as IDENTITY_PARQUET_FILE,
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.credential import load_massive_provider_config_from_file
from tip_api.providers.massive.grouped_daily_ingestion import (
    ENDPOINT_TEMPLATE,
    load_identity_snapshot,
    process_grouped_daily_payload,
)
from tip_api.providers.massive.instrument_master_snapshot import (
    MAX_PAGES,
    MAX_RECORDS,
    REFERENCE_TICKERS_PATH,
    FixedIntervalRateLimiter,
    _fetch_reference_pages,
    build_snapshot_from_payloads,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.transport import MassiveHttpTransport, MassiveUrllibTransport

APPROVED_PRODUCTION_ROOT = Path("/data/trading-intelligence-platform")
PACKAGE_SCHEMA_VERSION = "1.0"
PLAN_SCHEMA_VERSION = "1.1"
LOCK_ROOT = Path("/tmp")


class SameDayCatchupError(RuntimeError):
    """Fail-closed boundary error with no provider payload or credential."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FetchArtifactV1(FrozenModel):
    sequence: int = Field(ge=1)
    file_name: str
    canonical_response_sha256: str
    response_bytes: int = Field(ge=1)


class FetchPackageManifestV1(FrozenModel):
    schema_version: Literal["1.0"] = PACKAGE_SCHEMA_VERSION
    package_type: Literal["identity_reference", "grouped_daily"]
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    session_date: date
    endpoint_class: str
    adjusted: bool | None
    request_count: int = Field(ge=1)
    pagination_complete: bool
    fetched_at: datetime
    artifacts: tuple[FetchArtifactV1, ...]
    package_content_sha256: str


class PlannedArtifactV1(FrozenModel):
    dataset_name: str
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str


class CatchupApprovalPlanV1(FrozenModel):
    schema_version: Literal["1.0", "1.1"] = PLAN_SCHEMA_VERSION
    operation: Literal["identity", "identity_source", "eod"]
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    session_date: date
    created_at: datetime
    data_root: str
    fetch_package_path: str
    fetch_package_manifest_sha256: str
    fetch_package_content_sha256: str
    expected_current_state_fingerprint: str
    same_day_identity_snapshot_fingerprint: str | None
    publication_order: tuple[str, ...]
    artifacts: tuple[PlannedArtifactV1, ...]
    counts: dict[str, int]
    content_fingerprints: dict[str, str]
    inventory_change_file_count: int
    inventory_change_bytes: int
    recovery_boundary: str
    rollback_boundary: str
    plan_content_sha256: str


class FetchPackageEvidenceV1(FrozenModel):
    operation: Literal["identity", "identity_source", "eod"]
    session_date: date
    package_path: str
    package_type: Literal["identity_reference", "grouped_daily"]
    request_count: int = Field(ge=1)
    fetched_at: datetime
    package_manifest_sha256: str
    package_content_sha256: str


@dataclass(frozen=True, slots=True)
class ValidatedIdentityReferencePackage:
    """In-memory view of one fully custody-validated, credential-free package."""

    manifest: FetchPackageManifestV1
    pages: tuple[Mapping[str, object], ...]
    package_manifest_sha256: str


class CatchupApprovalPlanEvidenceV1(FrozenModel):
    operation: Literal["identity", "identity_source", "eod"]
    session_date: date
    plan_path: str
    plan_file_sha256: str
    plan_content_sha256: str
    data_root: str
    fetch_package_path: str
    fetch_package_manifest_sha256: str
    fetch_package_content_sha256: str
    expected_current_state_fingerprint: str
    publication_order: tuple[str, ...]
    inventory_change_file_count: int = Field(ge=1)
    inventory_change_bytes: int = Field(ge=1)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_fingerprint(
    root: Path, *, exclude_prefixes: tuple[Path, ...] = ()
) -> str:
    root = _validate_data_root(root)
    excluded = tuple(path.relative_to(root) for path in exclude_prefixes)
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        relative_path = Path(relative)
        if any(relative_path == prefix or prefix in relative_path.parents for prefix in excluded):
            continue
        stat = path.lstat()
        if path.is_symlink():
            rows.append(
                {
                    "path": relative,
                    "type": "symlink",
                    "owner": stat.st_uid,
                    "group": stat.st_gid,
                    "mode": oct(stat.st_mode & 0o7777),
                    "size": stat.st_size,
                    "sha256": None,
                    "symlink": True,
                }
            )
        elif path.is_file():
            rows.append(
                {
                    "path": relative,
                    "type": "file",
                    "owner": stat.st_uid,
                    "group": stat.st_gid,
                    "mode": oct(stat.st_mode & 0o7777),
                    "size": stat.st_size,
                    "sha256": file_sha256(path),
                    "symlink": False,
                }
            )
    return sha256_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def fetch_identity_package(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    session_date: date,
    package_path: Path,
    fetched_at: datetime | None = None,
    rate_limiter: FixedIntervalRateLimiter | None = None,
) -> FetchPackageManifestV1:
    _validate_fetch_config(config)
    package_path = _new_tmp_directory_path(package_path)
    pages, request_count, complete = _fetch_reference_pages(
        config=config,
        transport=transport,
        as_of_date=session_date,
        rate_limiter=rate_limiter or FixedIntervalRateLimiter(),
    )
    if not complete:
        raise SameDayCatchupError("reference pagination is incomplete")
    safe_pages = tuple(_sanitize_reference_page(page) for page in pages)
    page_hashes = [sha256_bytes(canonical_json_bytes(_results(page))) for page in safe_pages]
    if len(page_hashes) != len(set(page_hashes)):
        raise SameDayCatchupError("duplicate reference page response")
    if request_count > MAX_PAGES or sum(len(_results(page)) for page in pages) > MAX_RECORDS:
        raise SameDayCatchupError("reference package exceeds bounded limits")
    return _publish_fetch_package(
        package_path=package_path,
        package_type="identity_reference",
        session_date=session_date,
        endpoint_class=REFERENCE_TICKERS_PATH,
        adjusted=None,
        responses=safe_pages,
        request_count=request_count,
        pagination_complete=True,
        fetched_at=fetched_at or datetime.now(UTC),
    )


def fetch_eod_package(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    session_date: date,
    package_path: Path,
    fetched_at: datetime | None = None,
) -> FetchPackageManifestV1:
    _validate_fetch_config(config)
    package_path = _new_tmp_directory_path(package_path)
    endpoint = ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())
    payload = transport.get_json(
        endpoint,
        params={"adjusted": False},
        api_key=config.api_key,
        timeout_seconds=config.request_timeout_seconds,
        base_url=config.base_url,
    )
    _validate_grouped_session(payload, session_date)
    return _publish_fetch_package(
        package_path=package_path,
        package_type="grouped_daily",
        session_date=session_date,
        endpoint_class="/v2/aggs/grouped/locale/us/market/stocks/{session_date}",
        adjusted=False,
        responses=(payload,),
        request_count=1,
        pagination_complete=True,
        fetched_at=fetched_at or datetime.now(UTC),
    )


def read_fetch_package_evidence(
    *,
    package_path: Path,
    operation: Literal["identity", "identity_source", "eod"],
    expected_session: date,
) -> FetchPackageEvidenceV1:
    """Formally reread a frozen package and expose only non-sensitive custody."""

    expected_type: Literal["identity_reference", "grouped_daily"] = (
        "identity_reference"
        if operation in {"identity", "identity_source"}
        else "grouped_daily"
    )
    manifest, _ = _read_fetch_package(package_path, expected_type=expected_type)
    if manifest.session_date != expected_session:
        raise SameDayCatchupError("fetch package session mismatch")
    return FetchPackageEvidenceV1(
        operation=operation,
        session_date=manifest.session_date,
        package_path=str(package_path),
        package_type=manifest.package_type,
        request_count=manifest.request_count,
        fetched_at=manifest.fetched_at,
        package_manifest_sha256=file_sha256(package_path / "package.json"),
        package_content_sha256=manifest.package_content_sha256,
    )


def read_identity_reference_package(
    *,
    package_path: Path,
    expected_session: date,
) -> ValidatedIdentityReferencePackage:
    """Read sanitized Identity payloads after complete package custody validation.

    The payloads are intentionally returned only in memory.  Callers must not
    log them or copy them into canonical storage.
    """

    manifest, pages = _read_fetch_package(
        package_path,
        expected_type="identity_reference",
    )
    if manifest.session_date != expected_session:
        raise SameDayCatchupError("fetch package session mismatch")
    return ValidatedIdentityReferencePackage(
        manifest=manifest,
        pages=pages,
        package_manifest_sha256=file_sha256(package_path / "package.json"),
    )


def read_catchup_approval_plan_evidence(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_operation: Literal["identity", "identity_source", "eod"],
    expected_session: date,
    expected_data_root: Path,
) -> CatchupApprovalPlanEvidenceV1:
    """Formally reread a frozen apply plan and expose bounded custody evidence."""

    plan = _read_plan(plan_path, approved_plan_sha256)
    data_root = _validate_data_root(expected_data_root)
    if (
        plan.operation != expected_operation
        or plan.session_date != expected_session
        or plan.data_root != str(data_root)
    ):
        raise SameDayCatchupError("approval plan identity mismatch")
    _verify_package_custody(plan)
    return CatchupApprovalPlanEvidenceV1(
        operation=plan.operation,
        session_date=plan.session_date,
        plan_path=str(plan_path),
        plan_file_sha256=file_sha256(plan_path),
        plan_content_sha256=plan.plan_content_sha256,
        data_root=plan.data_root,
        fetch_package_path=plan.fetch_package_path,
        fetch_package_manifest_sha256=plan.fetch_package_manifest_sha256,
        fetch_package_content_sha256=plan.fetch_package_content_sha256,
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        publication_order=plan.publication_order,
        inventory_change_file_count=plan.inventory_change_file_count,
        inventory_change_bytes=plan.inventory_change_bytes,
    )


def build_identity_plan(*, package_path: Path, plan_path: Path, data_root: Path) -> CatchupApprovalPlanV1:
    package, pages = _read_fetch_package(package_path, expected_type="identity_reference")
    data_root = _validate_data_root(data_root)
    plan_path, artifact_root = _new_plan_paths(plan_path)
    raw_records: list[Mapping[str, object]] = []
    for page in pages:
        raw_records.extend(_results(page))
    build = build_snapshot_from_payloads(
        payloads=tuple(raw_records),
        as_of_date=package.session_date,
        ingested_at=package.fetched_at,
        request_count=package.request_count,
        pagination_complete=package.pagination_complete,
    )
    service = InstrumentMasterSnapshotIngestionService(
        repository=ParquetInstrumentMasterSnapshotRepository(root=artifact_root, created_at=package.fetched_at)
    )
    result = service.publish_snapshot(
        as_of_date=package.session_date,
        provider_id=MASSIVE_PROVIDER_ID,
        instruments=build.instruments,
        identities=build.identities,
        resolvers=build.resolvers,
        request_count=build.request_count,
        raw_record_count=build.raw_record_count,
        eligible_record_count=build.eligible_record_count,
        expected_exclusion_count=build.expected_exclusion_count,
        malformed_rejected_count=build.malformed_rejected_count,
        resolved_eligible_count=build.resolved_eligible_count,
        unresolved_eligible_count=build.unresolved_eligible_count,
        ambiguous_ticker_record_count=build.ambiguous_ticker_record_count,
        stable_identifier_collision_count=build.stable_identifier_collision_count,
        unique_provider_ticker_count=build.unique_provider_ticker_count,
        duplicate_provider_ticker_count=build.duplicate_provider_ticker_count,
    )
    if not result.quality_gate_passed or result.status != "published":
        shutil.rmtree(artifact_root, ignore_errors=True)
        raise SameDayCatchupError("identity quality gates did not pass")
    logical = artifact_root / "market-data" / "snapshots" / "instrument-master" / (
        f"as_of_date={package.session_date.isoformat()}"
    ) / IDENTITY_MANIFEST_FILE
    payload = json.loads(logical.read_text(encoding="utf-8"))
    for field in (
        "instrument_partition_path",
        "identity_partition_path",
        "resolver_partition_path",
    ):
        value = Path(str(payload[field]))
        payload[field] = str(data_root / value.relative_to(artifact_root))
    logical.write_bytes(_pretty_json_bytes(payload))
    _fsync_file(logical)
    artifact_root.chmod(0o700)
    (artifact_root / "market-data").chmod(0o700)
    from tip_api.services.historical_identity_source_custody import (
        build_same_day_identity_source_custody_candidate,
    )

    source = build_same_day_identity_source_custody_candidate(
        package=ValidatedIdentityReferencePackage(
            manifest=package,
            pages=pages,
            package_manifest_sha256=file_sha256(package_path / "package.json"),
        ),
        package_path=package_path,
        output_root=artifact_root,
        canonical_snapshot_fingerprint=result.snapshot_content_sha256 or "",
        canonical_instrument_fingerprint=result.instrument_content_sha256 or "",
        canonical_identity_fingerprint=result.identity_content_sha256 or "",
        canonical_resolver_fingerprint=result.resolver_content_sha256 or "",
    )
    order = _identity_target_directories(
        data_root,
        package.session_date,
        include_source=True,
    )
    artifacts = _collect_planned_artifacts(artifact_root, data_root, order)
    counts = {
        "raw_records": result.raw_record_count,
        "instrument_rows": result.canonical_instrument_count,
        "identity_rows": len(build.identities),
        "resolver_rows": result.resolver_entry_count,
        "source_observation_rows": source.manifest.record_count,
        "requests": result.request_count,
    }
    fingerprints = {
        "instrument": result.instrument_content_sha256 or "",
        "identity": result.identity_content_sha256 or "",
        "resolver": result.resolver_content_sha256 or "",
        "logical": result.snapshot_content_sha256 or "",
        "source_observation": source.manifest.content_fingerprint,
        "source_custody": source.manifest.logical_fingerprint,
    }
    return _write_plan(
        plan_path=plan_path,
        operation="identity",
        package=package,
        package_path=package_path,
        data_root=data_root,
        publication_order=order,
        artifacts=artifacts,
        counts=counts,
        fingerprints=fingerprints,
        same_day_identity=None,
    )


def build_identity_source_plan(
    *,
    package_path: Path,
    plan_path: Path,
    data_root: Path,
) -> CatchupApprovalPlanV1:
    """Plan an append-only source repair for an already completed Identity."""

    package, pages = _read_fetch_package(
        package_path,
        expected_type="identity_reference",
    )
    data_root = _validate_data_root(data_root)
    plan_path, artifact_root = _new_plan_paths(plan_path)
    try:
        identity = load_identity_snapshot(
            data_root,
            provider_id=MASSIVE_PROVIDER_ID,
            as_of_date=package.session_date,
        )
    except Exception as exc:
        raise SameDayCatchupError(
            "completed Identity is unavailable for source repair"
        ) from exc
    artifact_root.mkdir(mode=0o700)
    from tip_api.services.historical_identity_source_custody import (
        build_same_day_identity_source_custody_candidate,
    )

    source = build_same_day_identity_source_custody_candidate(
        package=ValidatedIdentityReferencePackage(
            manifest=package,
            pages=pages,
            package_manifest_sha256=file_sha256(package_path / "package.json"),
        ),
        package_path=package_path,
        output_root=artifact_root,
        canonical_snapshot_fingerprint=str(
            identity.manifest["snapshot_content_sha256"]
        ),
        canonical_instrument_fingerprint=str(
            identity.manifest["instrument_content_sha256"]
        ),
        canonical_identity_fingerprint=str(
            identity.manifest["identity_content_sha256"]
        ),
        canonical_resolver_fingerprint=str(
            identity.manifest["resolver_content_sha256"]
        ),
    )
    order = (_identity_source_target_directory(data_root, package.session_date),)
    artifacts = _collect_planned_artifacts(artifact_root, data_root, order)
    return _write_plan(
        plan_path=plan_path,
        operation="identity_source",
        package=package,
        package_path=package_path,
        data_root=data_root,
        publication_order=order,
        artifacts=artifacts,
        counts={
            "source_observation_rows": source.manifest.record_count,
            "requests": source.manifest.source_request_count,
        },
        fingerprints={
            "identity_logical": str(
                identity.manifest["snapshot_content_sha256"]
            ),
            "source_observation": source.manifest.content_fingerprint,
            "source_custody": source.manifest.logical_fingerprint,
        },
        same_day_identity=str(identity.manifest["snapshot_content_sha256"]),
    )


def build_eod_plan(*, package_path: Path, plan_path: Path, data_root: Path) -> CatchupApprovalPlanV1:
    package, pages = _read_fetch_package(package_path, expected_type="grouped_daily")
    data_root = _validate_data_root(data_root)
    plan_path, artifact_root = _new_plan_paths(plan_path)
    try:
        identity = load_identity_snapshot(
            data_root, provider_id=MASSIVE_PROVIDER_ID, as_of_date=package.session_date
        )
    except Exception as exc:
        raise SameDayCatchupError("same-day completed Identity is unavailable") from exc
    payload = pages[0]
    _validate_grouped_session(payload, package.session_date)
    result = process_grouped_daily_payload(
        payload,
        identity=identity,
        session_date=package.session_date,
        endpoint=ENDPOINT_TEMPLATE.format(session_date=package.session_date.isoformat()),
        data_root=artifact_root,
        ingested_at=package.fetched_at,
        publish=True,
    )
    if not result.quality_gate_passed or result.status != "published":
        shutil.rmtree(artifact_root, ignore_errors=True)
        raise SameDayCatchupError("EOD quality gates did not pass")
    order = (_eod_target_directory(data_root, package.session_date),)
    artifacts = _collect_planned_artifacts(artifact_root, data_root, order)
    counts = {
        "raw_records": result.raw_result_count,
        "canonical_rows": result.canonical_bar_count,
        "requests": result.request_count,
        "duplicate_business_keys": 0,
        "orphan_references": 0,
    }
    fingerprints = {
        "eod": result.content_sha256 or "",
        "identity_logical": str(identity.manifest["snapshot_content_sha256"]),
    }
    return _write_plan(
        plan_path=plan_path,
        operation="eod",
        package=package,
        package_path=package_path,
        data_root=data_root,
        publication_order=order,
        artifacts=artifacts,
        counts=counts,
        fingerprints=fingerprints,
        same_day_identity=str(identity.manifest["snapshot_content_sha256"]),
    )


def apply_approved_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    fail_after_target_count: int | None = None,
    expected_operation: Literal["identity", "identity_source", "eod"] | None = None,
    expected_session: date | None = None,
) -> CatchupApprovalPlanV1:
    plan = _read_plan(plan_path, approved_plan_sha256)
    if expected_operation is not None and plan.operation != expected_operation:
        raise SameDayCatchupError("approved plan operation mismatch")
    if expected_session is not None and plan.session_date != expected_session:
        raise SameDayCatchupError("approved plan session mismatch")
    data_root = _validate_data_root(data_root)
    if plan.data_root != str(data_root):
        raise SameDayCatchupError("approved data root mismatch")
    if plan.expected_current_state_fingerprint != expected_current_state_fingerprint:
        raise SameDayCatchupError("expected current-state fingerprint disagrees with plan")
    _verify_package_custody(plan)
    lock_path = LOCK_ROOT / ("tip-same-day-catchup-" + sha256_bytes(str(data_root).encode())[:16] + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise SameDayCatchupError("publication lock is unavailable") from exc
    with os.fdopen(lock_fd, "r+b") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise SameDayCatchupError("publication lock is not a regular file")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked_plan = _read_plan(plan_path, approved_plan_sha256)
        if locked_plan != plan:
            raise SameDayCatchupError("approved plan changed before lock validation")
        _verify_package_custody(plan)
        if verify_then_complete:
            if plan.operation == "identity":
                _validate_recovery_state(plan, data_root)
            elif plan.operation == "identity_source":
                _validate_atomic_target_recovery_state(plan, data_root)
            else:
                raise SameDayCatchupError(
                    "verify-then-complete is not valid for EOD"
                )
        elif inventory_fingerprint(data_root) != expected_current_state_fingerprint:
            raise SameDayCatchupError("approved current state changed")
        else:
            _assert_targets_absent(plan)
        if plan.operation == "eod":
            identity = load_identity_snapshot(
                data_root, provider_id=MASSIVE_PROVIDER_ID, as_of_date=plan.session_date
            )
            if (
                identity.as_of_date != plan.session_date
                or identity.manifest.get("snapshot_content_sha256")
                != plan.same_day_identity_snapshot_fingerprint
            ):
                raise SameDayCatchupError("same-day completed Identity fingerprint mismatch")
        with _network_prohibited():
            published = 0
            for target_text in plan.publication_order:
                target = Path(target_text)
                refs = tuple(item for item in plan.artifacts if Path(item.target_path).parent == target)
                if target.exists():
                    if not verify_then_complete:
                        raise SameDayCatchupError("completed target already exists")
                    _verify_target_files(target, refs)
                    continue
                _publish_target_directory(target, refs, plan.plan_content_sha256)
                published += 1
                if fail_after_target_count is not None and published == fail_after_target_count:
                    raise SameDayCatchupError("injected failure after completed target")
            for target_text in plan.publication_order:
                target = Path(target_text)
                refs = tuple(
                    item for item in plan.artifacts if Path(item.target_path).parent == target
                )
                _verify_target_files(target, refs)
            _formal_reread(plan, data_root)
    return plan


def _publish_fetch_package(
    *,
    package_path: Path,
    package_type: Literal["identity_reference", "grouped_daily"],
    session_date: date,
    endpoint_class: str,
    adjusted: bool | None,
    responses: tuple[Mapping[str, object], ...],
    request_count: int,
    pagination_complete: bool,
    fetched_at: datetime,
) -> FetchPackageManifestV1:
    fetched_at = _aware_utc(fetched_at)
    staging = package_path.with_name("." + package_path.name + ".staging")
    if staging.exists() or staging.is_symlink():
        raise SameDayCatchupError("fetch package staging already exists")
    staging.mkdir(mode=0o700)
    artifacts: list[FetchArtifactV1] = []
    try:
        for index, response in enumerate(responses, 1):
            _assert_no_secret_material(response)
            raw = canonical_json_bytes(response)
            file_name = f"response-{index:02d}.json"
            path = staging / file_name
            path.write_bytes(raw)
            path.chmod(0o400)
            _fsync_file(path)
            artifacts.append(
                FetchArtifactV1(
                    sequence=index,
                    file_name=file_name,
                    canonical_response_sha256=sha256_bytes(raw),
                    response_bytes=len(raw),
                )
            )
        provisional = FetchPackageManifestV1(
            package_type=package_type,
            session_date=session_date,
            endpoint_class=endpoint_class,
            adjusted=adjusted,
            request_count=request_count,
            pagination_complete=pagination_complete,
            fetched_at=fetched_at,
            artifacts=tuple(artifacts),
            package_content_sha256="0" * 64,
        )
        base = provisional.model_dump(mode="json", exclude={"package_content_sha256"})
        manifest = provisional.model_copy(
            update={"package_content_sha256": sha256_bytes(canonical_json_bytes(base))}
        )
        manifest_path = staging / "package.json"
        manifest_path.write_bytes(_pretty_json_bytes(manifest.model_dump(mode="json")))
        manifest_path.chmod(0o400)
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.replace(package_path)
        _fsync_directory(package_path.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    return manifest


def _read_fetch_package(
    path: Path, *, expected_type: Literal["identity_reference", "grouped_daily"]
) -> tuple[FetchPackageManifestV1, tuple[Mapping[str, object], ...]]:
    path = _existing_tmp_directory(path)
    manifest_path = path / "package.json"
    _regular_nonsymlink(manifest_path)
    try:
        manifest = FetchPackageManifestV1.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SameDayCatchupError("fetch package manifest is invalid") from exc
    base = manifest.model_dump(mode="json", exclude={"package_content_sha256"})
    if sha256_bytes(canonical_json_bytes(base)) != manifest.package_content_sha256:
        raise SameDayCatchupError("fetch package content fingerprint mismatch")
    if manifest.package_type != expected_type:
        raise SameDayCatchupError("fetch package type mismatch")
    expected_endpoint = (
        REFERENCE_TICKERS_PATH
        if expected_type == "identity_reference"
        else "/v2/aggs/grouped/locale/us/market/stocks/{session_date}"
    )
    if manifest.endpoint_class != expected_endpoint:
        raise SameDayCatchupError("fetch package endpoint class mismatch")
    if tuple(item.sequence for item in manifest.artifacts) != tuple(range(1, len(manifest.artifacts) + 1)):
        raise SameDayCatchupError("fetch package page order is invalid")
    if manifest.request_count != len(manifest.artifacts):
        raise SameDayCatchupError("fetch package request count mismatch")
    pages: list[Mapping[str, object]] = []
    seen: set[str] = set()
    for item in manifest.artifacts:
        file_path = path / item.file_name
        if file_path.parent != path or "/" in item.file_name or "\\" in item.file_name:
            raise SameDayCatchupError("fetch package path traversal")
        _regular_nonsymlink(file_path)
        raw = file_path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != item.canonical_response_sha256 or len(raw) != item.response_bytes:
            raise SameDayCatchupError("fetch package response custody mismatch")
        if digest in seen:
            raise SameDayCatchupError("fetch package contains a duplicate page")
        seen.add(digest)
        value = json.loads(raw)
        if not isinstance(value, Mapping):
            raise SameDayCatchupError("fetch response must be a JSON object")
        _assert_no_secret_material(value)
        pages.append(value)
    if expected_type == "grouped_daily":
        if manifest.adjusted is not False or len(pages) != 1:
            raise SameDayCatchupError("Grouped Daily package contract mismatch")
        _validate_grouped_session(pages[0], manifest.session_date)
    elif manifest.adjusted is not None or not manifest.pagination_complete:
        raise SameDayCatchupError("reference package contract mismatch")
    return manifest, tuple(pages)


def _write_plan(
    *,
    plan_path: Path,
    operation: Literal["identity", "identity_source", "eod"],
    package: FetchPackageManifestV1,
    package_path: Path,
    data_root: Path,
    publication_order: tuple[Path, ...],
    artifacts: tuple[PlannedArtifactV1, ...],
    counts: dict[str, int],
    fingerprints: dict[str, str],
    same_day_identity: str | None,
) -> CatchupApprovalPlanV1:
    package_manifest_sha = file_sha256(package_path / "package.json")
    values: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "operation": operation,
        "provider_id": MASSIVE_PROVIDER_ID,
        "session_date": package.session_date,
        "created_at": package.fetched_at,
        "data_root": str(data_root),
        "fetch_package_path": str(package_path),
        "fetch_package_manifest_sha256": package_manifest_sha,
        "fetch_package_content_sha256": package.package_content_sha256,
        "expected_current_state_fingerprint": inventory_fingerprint(data_root),
        "same_day_identity_snapshot_fingerprint": same_day_identity,
        "publication_order": tuple(str(item) for item in publication_order),
        "artifacts": artifacts,
        "counts": counts,
        "content_fingerprints": fingerprints,
        "inventory_change_file_count": len(artifacts),
        "inventory_change_bytes": sum(item.size for item in artifacts),
        "recovery_boundary": (
            "verify_matching_completed_components_then_publish_missing_components_and_logical_marker"
            if operation == "identity"
            else (
                "verify_matching_atomic_source_target_without_overwrite"
                if operation == "identity_source"
                else "formal_reread_completed_target_without_replay"
            )
        ),
        "rollback_boundary": "immutable_completed_datasets_are_never_deleted_or_overwritten",
    }
    fingerprint_value = _plan_content_fingerprint(values)
    plan = CatchupApprovalPlanV1(**values, plan_content_sha256=fingerprint_value)
    plan_path.write_bytes(_pretty_json_bytes(plan.model_dump(mode="json")))
    plan_path.chmod(0o444)
    _fsync_file(plan_path)
    _fsync_directory(plan_path.parent)
    return plan


def _read_plan(path: Path, approved_sha: str) -> CatchupApprovalPlanV1:
    path = _existing_tmp_file(path)
    if file_sha256(path) != approved_sha:
        raise SameDayCatchupError("approved plan SHA-256 mismatch")
    try:
        plan = CatchupApprovalPlanV1.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SameDayCatchupError("approved plan is invalid") from exc
    values = plan.model_dump(mode="json", exclude={"plan_content_sha256"})
    if _plan_content_fingerprint(values) != plan.plan_content_sha256:
        raise SameDayCatchupError("approved plan content fingerprint mismatch")
    _validate_plan_contract(plan)
    for artifact in plan.artifacts:
        source = _existing_tmp_file(Path(artifact.source_path))
        if file_sha256(source) != artifact.sha256 or source.stat().st_size != artifact.size:
            raise SameDayCatchupError("planned artifact custody mismatch")
    return plan



def _validate_plan_contract(plan: CatchupApprovalPlanV1) -> None:
    root = _validate_data_root(Path(plan.data_root))
    order = tuple(Path(item) for item in plan.publication_order)
    if plan.schema_version == "1.0":
        if plan.operation == "identity_source":
            raise SameDayCatchupError(
                "source-only operation requires approval-plan schema 1.1"
            )
        expected_order = (
            _identity_target_directories(
                root,
                plan.session_date,
                include_source=False,
            )
            if plan.operation == "identity"
            else (_eod_target_directory(root, plan.session_date),)
        )
        expected_files = 7 if plan.operation == "identity" else 2
    elif plan.operation == "identity":
        expected_order = _identity_target_directories(
            root,
            plan.session_date,
            include_source=True,
        )
        expected_files = 9
    elif plan.operation == "identity_source":
        expected_order = (
            _identity_source_target_directory(root, plan.session_date),
        )
        expected_files = 2
    else:
        expected_order = (_eod_target_directory(root, plan.session_date),)
        expected_files = 2
    if order != expected_order:
        raise SameDayCatchupError("approved publication order mismatch")
    targets = set(order)
    if len(plan.artifacts) != plan.inventory_change_file_count:
        raise SameDayCatchupError("approved inventory file count mismatch")
    if sum(item.size for item in plan.artifacts) != plan.inventory_change_bytes:
        raise SameDayCatchupError("approved inventory byte count mismatch")
    for artifact in plan.artifacts:
        target = Path(artifact.target_path)
        if target.parent not in targets or target.name not in {
            "part-00000.parquet", "manifest.json"
        }:
            raise SameDayCatchupError("approved artifact target is invalid")
        _reject_symlink_chain(root, target)
    if len(plan.artifacts) != expected_files:
        raise SameDayCatchupError("approved artifact cardinality mismatch")

def _verify_package_custody(plan: CatchupApprovalPlanV1) -> None:
    package_path = _existing_tmp_directory(Path(plan.fetch_package_path))
    if file_sha256(package_path / "package.json") != plan.fetch_package_manifest_sha256:
        raise SameDayCatchupError("fetch package manifest changed after approval")
    package, _ = _read_fetch_package(
        package_path,
        expected_type=(
            "identity_reference"
            if plan.operation in {"identity", "identity_source"}
            else "grouped_daily"
        ),
    )
    if (
        package.package_content_sha256 != plan.fetch_package_content_sha256
        or package.session_date != plan.session_date
    ):
        raise SameDayCatchupError("fetch package changed after approval")


def _collect_planned_artifacts(
    artifact_root: Path, data_root: Path, order: tuple[Path, ...]
) -> tuple[PlannedArtifactV1, ...]:
    refs: list[PlannedArtifactV1] = []
    for target in order:
        relative = target.relative_to(data_root)
        source_dir = artifact_root / relative
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise SameDayCatchupError("planned target artifact directory is incomplete")
        for source in sorted(source_dir.iterdir()):
            _regular_nonsymlink(source)
            refs.append(
                PlannedArtifactV1(
                    dataset_name=relative.parts[-2] if len(relative.parts) >= 2 else relative.name,
                    source_path=str(source),
                    target_path=str(target / source.name),
                    size=source.stat().st_size,
                    sha256=file_sha256(source),
                )
            )
    return tuple(refs)


def _assert_targets_absent(plan: CatchupApprovalPlanV1) -> None:
    for target_text in plan.publication_order:
        target = Path(target_text)
        _reject_symlink_chain(Path(plan.data_root), target)
        if target.exists() or target.is_symlink():
            raise SameDayCatchupError("approved target is no longer absent")


def _validate_recovery_state(plan: CatchupApprovalPlanV1, data_root: Path) -> None:
    logical = Path(plan.publication_order[-1])
    if logical.exists() or logical.is_symlink():
        raise SameDayCatchupError("logical completion marker already exists")
    for target_text in plan.publication_order[:-1]:
        target = Path(target_text)
        _reject_symlink_chain(data_root, target)
        refs = tuple(item for item in plan.artifacts if Path(item.target_path).parent == target)
        if target.exists():
            _verify_target_files(target, refs)
        elif target.is_symlink():
            raise SameDayCatchupError("recovery target is a symlink")
    recovery_base = inventory_fingerprint(
        data_root,
        exclude_prefixes=tuple(Path(item) for item in plan.publication_order),
    )
    if recovery_base != plan.expected_current_state_fingerprint:
        raise SameDayCatchupError("approved recovery base state changed")


def _validate_atomic_target_recovery_state(
    plan: CatchupApprovalPlanV1,
    data_root: Path,
) -> None:
    if len(plan.publication_order) != 1:
        raise SameDayCatchupError("atomic recovery target count differs")
    target = Path(plan.publication_order[0])
    _reject_symlink_chain(data_root, target)
    refs = tuple(
        item for item in plan.artifacts if Path(item.target_path).parent == target
    )
    if target.exists():
        _verify_target_files(target, refs)
    elif target.is_symlink():
        raise SameDayCatchupError("atomic recovery target is a symlink")
    recovery_base = inventory_fingerprint(
        data_root,
        exclude_prefixes=(target,),
    )
    if recovery_base != plan.expected_current_state_fingerprint:
        raise SameDayCatchupError("approved recovery base state changed")


def _publish_target_directory(
    target: Path, refs: tuple[PlannedArtifactV1, ...], plan_fingerprint: str
) -> None:
    if not refs:
        raise SameDayCatchupError("approved target has no artifacts")
    _mkdirs_durable(target.parent)
    staging = target.parent / f".{target.name}.staging.{plan_fingerprint[:16]}"
    if staging.exists() or staging.is_symlink():
        raise SameDayCatchupError("approved staging path already exists")
    staging.mkdir(mode=0o755)
    try:
        for ref in refs:
            source = _existing_tmp_file(Path(ref.source_path))
            destination = staging / Path(ref.target_path).name
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            _fsync_file(destination)
            if file_sha256(destination) != ref.sha256:
                raise SameDayCatchupError("staged artifact hash mismatch")
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise


def _verify_target_files(target: Path, refs: tuple[PlannedArtifactV1, ...]) -> None:
    if target.is_symlink() or not target.is_dir():
        raise SameDayCatchupError("completed target is unavailable")
    expected = {Path(item.target_path).name: item for item in refs}
    actual = {item.name for item in target.iterdir()}
    if actual != set(expected):
        raise SameDayCatchupError("completed target file set mismatch")
    for name, ref in expected.items():
        path = target / name
        _regular_nonsymlink(path)
        if path.stat().st_size != ref.size or file_sha256(path) != ref.sha256:
            raise SameDayCatchupError("completed target artifact mismatch")


def _formal_reread(plan: CatchupApprovalPlanV1, data_root: Path) -> None:
    if plan.operation == "identity":
        value = load_identity_snapshot(
            data_root, provider_id=MASSIVE_PROVIDER_ID, as_of_date=plan.session_date
        )
        if (
            value.manifest.get("snapshot_content_sha256")
            != plan.content_fingerprints.get("logical")
            or len(value.resolver) != plan.counts["resolver_rows"]
        ):
            raise SameDayCatchupError("formal Identity reread mismatch")
        if plan.schema_version == "1.1":
            _formal_source_reread(plan, data_root)
    elif plan.operation == "identity_source":
        identity = load_identity_snapshot(
            data_root,
            provider_id=MASSIVE_PROVIDER_ID,
            as_of_date=plan.session_date,
        )
        if (
            identity.manifest.get("snapshot_content_sha256")
            != plan.same_day_identity_snapshot_fingerprint
        ):
            raise SameDayCatchupError(
                "source repair canonical Identity fingerprint mismatch"
            )
        _formal_source_reread(plan, data_root)
    else:
        value = CanonicalEodReadRepository(data_root).inspect_session(plan.session_date)
        if (
            value.record_count != plan.counts["canonical_rows"]
            or value.content_fingerprint != plan.content_fingerprints["eod"]
            or value.identity_snapshot_date != plan.session_date
            or value.identity_snapshot_fingerprint != plan.same_day_identity_snapshot_fingerprint
        ):
            raise SameDayCatchupError("formal EOD reread mismatch")


def _formal_source_reread(plan: CatchupApprovalPlanV1, data_root: Path) -> None:
    from tip_api.services.historical_identity_source_custody import (
        HistoricalIdentitySourceCustodyError,
        read_identity_source_custody_at_data_root,
    )

    try:
        value = read_identity_source_custody_at_data_root(
            data_root=data_root,
            provider=MASSIVE_PROVIDER_ID,
            session_date=plan.session_date,
        )
    except HistoricalIdentitySourceCustodyError as exc:
        raise SameDayCatchupError(
            "formal Identity source-custody reread failed"
        ) from exc
    if (
        value.manifest.record_count != plan.counts["source_observation_rows"]
        or value.manifest.content_fingerprint
        != plan.content_fingerprints["source_observation"]
        or value.manifest.logical_fingerprint
        != plan.content_fingerprints["source_custody"]
    ):
        raise SameDayCatchupError("formal Identity source-custody reread mismatch")


def _identity_target_directories(
    root: Path,
    session: date,
    *,
    include_source: bool,
) -> tuple[Path, ...]:
    day = session.isoformat()
    physical = (
        root / "market-data" / "instrument-master" / "schema_version=1" / f"as_of_date={day}",
        root
        / "market-data"
        / "provider-instrument-identity"
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
        / f"as_of_date={day}",
        root
        / "market-data"
        / "provider-ticker-resolver"
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
        / f"as_of_date={day}",
    )
    logical = (
        root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={day}"
    )
    if include_source:
        return (*physical, _identity_source_target_directory(root, session), logical)
    return (*physical, logical)


def _identity_source_target_directory(root: Path, session: date) -> Path:
    return (
        root
        / "market-data"
        / "provider-identity-reference-observation"
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
        / f"as_of_date={session.isoformat()}"
    )


def _eod_target_directory(root: Path, session: date) -> Path:
    return (
        root
        / "market-data"
        / "eod-price-bars"
        / "schema_version=1"
        / f"session_date={session.isoformat()}"
    )


def _validate_grouped_session(payload: Mapping[str, object], session: date) -> None:
    results = payload.get("results")
    if not isinstance(results, list):
        raise SameDayCatchupError("Grouped Daily results must be a list")
    from tip_api.providers.massive.grouped_daily_ingestion import (
        _parse_massive_integral,
        _session_date_from_timestamp_ms,
    )

    for item in results:
        if not isinstance(item, Mapping):
            raise SameDayCatchupError("Grouped Daily result must be an object")
        try:
            timestamp = _parse_massive_integral(item.get("t"), required=True, allow_negative=False)
        except Exception as exc:
            raise SameDayCatchupError("Grouped Daily timestamp is invalid") from exc
        if timestamp is None or _session_date_from_timestamp_ms(timestamp) != session:
            raise SameDayCatchupError("Grouped Daily response session mismatch")


def _validate_fetch_config(config: MassiveProviderConfig) -> None:
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
        raise SameDayCatchupError("fetch-only base URL is outside the Massive allowlist")


def _assert_no_secret_material(value: object) -> None:
    forbidden = {"authorization", "api_key", "apikey", "access_token"}
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).strip().lower() in forbidden:
                raise SameDayCatchupError("provider package contains forbidden credential material")
            _assert_no_secret_material(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_secret_material(item)
    elif isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.username or parsed.password:
            raise SameDayCatchupError("provider package contains credentialed URL")
        query_keys = {key.strip().lower() for key, _ in parse_qsl(parsed.query)}
        if query_keys & forbidden:
            raise SameDayCatchupError("provider package URL contains forbidden credential material")


def _sanitize_reference_page(page: Mapping[str, object]) -> Mapping[str, object]:
    """Return the provider page with credential query material removed in memory."""

    sanitized = dict(page)
    next_url = sanitized.get("next_url")
    if isinstance(next_url, str):
        parsed = urlparse(next_url)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if key.strip().lower() not in {"apikey", "api_key", "access_token"}
        ]
        sanitized["next_url"] = urlunparse(parsed._replace(query=urlencode(query)))
    _assert_no_secret_material(sanitized)
    return sanitized


def _results(page: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    results = page.get("results")
    if not isinstance(results, list):
        raise SameDayCatchupError("reference page results must be a list")
    if not all(isinstance(item, Mapping) for item in results):
        raise SameDayCatchupError("reference page contains a non-object result")
    return tuple(results)


def _plan_content_fingerprint(values: Mapping[str, object]) -> str:
    normalized = dict(values)
    created = normalized.get("created_at")
    if isinstance(created, datetime):
        normalized["created_at"] = created.astimezone(UTC).isoformat()
    elif isinstance(created, str) and created.endswith("Z"):
        normalized["created_at"] = created[:-1] + "+00:00"
    normalized["session_date"] = (
        normalized["session_date"].isoformat()
        if isinstance(normalized.get("session_date"), date)
        else normalized.get("session_date")
    )
    normalized["artifacts"] = [
        item.model_dump(mode="json") if isinstance(item, PlannedArtifactV1) else item
        for item in normalized["artifacts"]
    ]
    return sha256_bytes(canonical_json_bytes(normalized))


def _new_plan_paths(plan_path: Path) -> tuple[Path, Path]:
    if not plan_path.is_absolute() or not plan_path.resolve(strict=False).is_relative_to(Path("/tmp")):
        raise SameDayCatchupError("approval plan must be under /tmp")
    _reject_tmp_symlink_chain(plan_path)
    if plan_path.exists() or plan_path.is_symlink():
        raise SameDayCatchupError("approval plan already exists")
    if not plan_path.parent.is_dir() or plan_path.parent.is_symlink():
        raise SameDayCatchupError("approval plan parent is invalid")
    artifact_root = plan_path.with_suffix(".artifacts")
    if artifact_root.exists() or artifact_root.is_symlink():
        raise SameDayCatchupError("approval artifact root already exists")
    return plan_path, artifact_root


def _new_tmp_directory_path(path: Path) -> Path:
    if not path.is_absolute() or not path.resolve(strict=False).is_relative_to(Path("/tmp")):
        raise SameDayCatchupError("fetch package must be under /tmp")
    _reject_tmp_symlink_chain(path)
    if path.exists() or path.is_symlink():
        raise SameDayCatchupError("fetch package target already exists")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise SameDayCatchupError("fetch package parent is invalid")
    return path


def _existing_tmp_directory(path: Path) -> Path:
    if (
        not path.is_absolute()
        or not path.resolve(strict=True).is_relative_to(Path("/tmp"))
        or path.is_symlink()
        or not path.is_dir()
    ):
        raise SameDayCatchupError("package directory is invalid")
    _reject_tmp_symlink_chain(path)
    return path


def _existing_tmp_file(path: Path) -> Path:
    if (
        not path.is_absolute()
        or not path.resolve(strict=True).is_relative_to(Path("/tmp"))
        or path.is_symlink()
        or not path.is_file()
    ):
        raise SameDayCatchupError("approved temporary file is invalid")
    _reject_tmp_symlink_chain(path)
    return path


def _reject_tmp_symlink_chain(path: Path) -> None:
    current = path
    while current != Path("/tmp"):
        if current.exists() and current.is_symlink():
            raise SameDayCatchupError("symlink in temporary custody path")
        current = current.parent


def _regular_nonsymlink(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SameDayCatchupError("artifact must be a regular non-symlink file")


def _validate_data_root(root: Path) -> Path:
    if not root.is_absolute():
        raise SameDayCatchupError("data root must be absolute")
    if root != APPROVED_PRODUCTION_ROOT and not root.resolve(strict=False).is_relative_to(Path("/tmp")):
        raise SameDayCatchupError("data root is outside approved boundaries")
    if root.is_symlink() or not root.is_dir():
        raise SameDayCatchupError("data root must be an existing non-symlink directory")
    resolved = root.resolve()
    _reject_symlink_chain(resolved, resolved)
    return resolved


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if not target.is_absolute() or not target.resolve(strict=False).is_relative_to(root):
        raise SameDayCatchupError("target path escapes data root")
    current = target
    while current != root:
        if current.exists() and current.is_symlink():
            raise SameDayCatchupError("symlink in publication path")
        current = current.parent


def _mkdirs_durable(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise SameDayCatchupError("publication parent is invalid")
    for item in reversed(missing):
        item.mkdir()
        _fsync_directory(item)
        _fsync_directory(item.parent)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SameDayCatchupError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _pretty_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _network_prohibited():
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def denied(*_args, **_kwargs):
        raise SameDayCatchupError("network access is prohibited during approved apply")

    socket.socket.connect = denied
    socket.create_connection = denied
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.create_connection = original_create


def _parser(
    operation: Literal["identity", "identity_source", "eod"],
) -> argparse.ArgumentParser:
    label = {
        "identity": "instrument-master",
        "identity_source": "identity-source-repair",
        "eod": "grouped-daily",
    }[operation]
    parser = argparse.ArgumentParser(prog=f"ingest-massive-{label}.sh")
    modes = parser.add_mutually_exclusive_group(required=True)
    if operation != "identity_source":
        modes.add_argument("--fetch-only", action="store_true")
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--apply", action="store_true")
    if operation in {"identity", "identity_source"}:
        modes.add_argument("--verify-then-complete", action="store_true")
    parser.add_argument("--session-date", required=True)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--approval-plan", type=Path)
    parser.add_argument("--approved-plan", type=Path)
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--expected-current-state-fingerprint")
    parser.add_argument("--data-root", type=Path)
    return parser


def cli_main(
    operation: Literal["identity", "identity_source", "eod"],
    argv: list[str] | None = None,
) -> int:
    parser = _parser(operation)
    args = parser.parse_args(argv)
    try:
        session = date.fromisoformat(args.session_date)
        if getattr(args, "fetch_only", False):
            if args.package is None or any(
                (args.approval_plan, args.approved_plan, args.approved_plan_sha256,
                 args.expected_current_state_fingerprint, args.data_root)
            ):
                parser.error("fetch-only requires only --session-date and --package")
            config = load_massive_provider_config_from_file()
            value = (
                fetch_identity_package(config=config, transport=MassiveUrllibTransport(),
                                       session_date=session, package_path=args.package)
                if operation in {"identity", "identity_source"}
                else fetch_eod_package(config=config, transport=MassiveUrllibTransport(),
                                       session_date=session, package_path=args.package)
            )
            print(json.dumps({"status": "fetched", **value.model_dump(mode="json")}, sort_keys=True))
            return 0
        if args.plan:
            if not all((args.package, args.approval_plan, args.data_root)) or any(
                (args.approved_plan, args.approved_plan_sha256, args.expected_current_state_fingerprint)
            ):
                parser.error("plan requires package, approval-plan, and data-root")
            if operation == "identity":
                value = build_identity_plan(
                    package_path=args.package,
                    plan_path=args.approval_plan,
                    data_root=args.data_root,
                )
            elif operation == "identity_source":
                value = build_identity_source_plan(
                    package_path=args.package,
                    plan_path=args.approval_plan,
                    data_root=args.data_root,
                )
            else:
                value = build_eod_plan(
                    package_path=args.package,
                    plan_path=args.approval_plan,
                    data_root=args.data_root,
                )
            if value.session_date != session:
                raise SameDayCatchupError("fetch package session disagrees with CLI")
            print(json.dumps({
                "status": "dry_run_ready", "operation": operation,
                "session_date": session.isoformat(), "plan_path": str(args.approval_plan),
                "plan_sha256": file_sha256(args.approval_plan),
                "expected_current_state_fingerprint": value.expected_current_state_fingerprint,
                "counts": value.counts, "content_fingerprints": value.content_fingerprints,
                "production_writes": 0,
            }, sort_keys=True))
            return 0
        approved_mode = args.apply or getattr(args, "verify_then_complete", False)
        if approved_mode:
            if not all((args.approved_plan, args.approved_plan_sha256,
                        args.expected_current_state_fingerprint, args.data_root)) or args.package or args.approval_plan:
                parser.error("approved apply requires plan, plan SHA-256, expected state, and data-root")
            apply_approved_plan(
                plan_path=args.approved_plan,
                approved_plan_sha256=args.approved_plan_sha256,
                expected_current_state_fingerprint=args.expected_current_state_fingerprint,
                data_root=args.data_root,
                verify_then_complete=getattr(args, "verify_then_complete", False),
                expected_operation=operation,
                expected_session=session,
            )
            print(json.dumps({"status": "published_and_verified", "operation": operation,
                              "session_date": session.isoformat()}, sort_keys=True))
            return 0
        parser.error("operation mode is required")
    except (SameDayCatchupError, ValueError) as exc:
        print(f"status=failed\nfailure={exc}", file=sys.stderr)
        return 1
    return 2


def identity_main(argv: list[str] | None = None) -> int:
    return cli_main("identity", argv)


def identity_source_main(argv: list[str] | None = None) -> int:
    return cli_main("identity_source", argv)


def eod_main(argv: list[str] | None = None) -> int:
    return cli_main("eod", argv)
