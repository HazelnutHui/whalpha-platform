"""Atomic temporary custody for provider-neutral historical source responses."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping
from urllib.parse import parse_qsl, urlsplit

from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import (
    HistoricalSourceArtifactV1,
    HistoricalSourcePackageManifestV1,
    HistoricalSourceRequestKind,
    HistoricalSourceScopeReceiptV1,
    build_historical_source_package_manifest,
)
from tip_api.services.historical_pilot_planner import HistoricalPilotPlanV1


MANIFEST_DIRECTORY = "manifests"
PACKAGE_MANIFEST_FILE = "source-package.json"
REQUEST_PLAN_FILE = "request-plan.json"
INVENTORY_FILE = "inventory-source.json"
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "password",
        "private_key",
        "secret",
        "set-cookie",
        "token",
    }
)


class HistoricalSourcePackageError(RuntimeError):
    """Base failure for a temporary historical source package."""


class HistoricalSourcePackageConflictError(HistoricalSourcePackageError):
    """Raised when an immutable target differs from the requested package."""


class HistoricalSourcePackageCorruptionError(HistoricalSourcePackageError):
    """Raised when formal reread finds changed or unsafe package bytes."""


@dataclass(frozen=True, slots=True)
class CapturedHistoricalSourceScopeV1:
    request_kind: HistoricalSourceRequestKind
    logical_endpoint: str
    scope: str
    responses: tuple[Mapping[str, object], ...]
    completed: bool = True


@dataclass(frozen=True, slots=True)
class HistoricalSourcePackageResultV1:
    manifest: HistoricalSourcePackageManifestV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_historical_source_package(
    *,
    package_path: Path,
    plan: HistoricalPilotPlanV1,
    captured_scopes: tuple[CapturedHistoricalSourceScopeV1, ...],
    acquired_at: datetime,
    source_permission_review_fingerprint: str,
    account_entitlement_evidence_fingerprint: str,
    lifecycle_coverage_review_fingerprint: str,
    exact_authorization_acknowledgement_fingerprint: str,
) -> HistoricalSourcePackageResultV1:
    """Publish already captured, sanitized responses without any provider call."""

    target = _validate_new_package_path(package_path, plan.logical_content_fingerprint)
    plan_bytes = _canonical_json_bytes(plan.as_dict())
    inventory_bytes = _canonical_json_bytes(plan.as_dict()["inventory"])
    artifact_payloads, receipts = _prepare_captured_scopes(plan, captured_scopes)
    manifest = build_historical_source_package_manifest(
        provider_id=plan.provider_id,
        pilot_plan_fingerprint=plan.logical_content_fingerprint,
        source_permission_review_fingerprint=source_permission_review_fingerprint,
        account_entitlement_evidence_fingerprint=(
            account_entitlement_evidence_fingerprint
        ),
        lifecycle_coverage_review_fingerprint=lifecycle_coverage_review_fingerprint,
        exact_authorization_acknowledgement_fingerprint=(
            exact_authorization_acknowledgement_fingerprint
        ),
        acquired_at=acquired_at,
        serial_pace_seconds=plan.serial_pace_seconds,
        zero_automatic_retry=True,
        request_plan_document_sha256=_sha256(plan_bytes),
        inventory_document_sha256=_sha256(inventory_bytes),
        scope_receipts=receipts,
        total_request_count=sum(item.request_count for item in receipts),
        planned_request_ceiling=plan.planned_request_ceiling,
        source_payload_retention="temporary_package_only",
        canonical_apply_authorized=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))

    if target.exists() or target.is_symlink():
        existing = read_historical_source_package(
            package_path=target,
            expected_plan_fingerprint=plan.logical_content_fingerprint,
        )
        if existing.manifest != manifest:
            raise HistoricalSourcePackageConflictError(
                "immutable historical source package differs"
            )
        return replace(existing, status="already_present")

    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise HistoricalSourcePackageConflictError("source package staging path exists")
    staging.mkdir(mode=0o700)
    try:
        manifests = staging / MANIFEST_DIRECTORY
        manifests.mkdir(mode=0o700)
        _write_file(manifests / REQUEST_PLAN_FILE, plan_bytes)
        _write_file(manifests / INVENTORY_FILE, inventory_bytes)
        for relative_path, payload in artifact_payloads:
            destination = staging / PurePosixPath(relative_path)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _write_file(destination, payload)
        _write_file(manifests / PACKAGE_MANIFEST_FILE, manifest_bytes)
        _make_directories_owner_only(staging)
        _fsync_tree(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
        result = read_historical_source_package(
            package_path=target,
            expected_plan_fingerprint=plan.logical_content_fingerprint,
        )
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    if result.manifest != manifest:
        raise HistoricalSourcePackageCorruptionError(
            "source package changed after publication"
        )
    return replace(result, status="published")


def read_historical_source_package(
    *,
    package_path: Path,
    expected_plan_fingerprint: str | None = None,
) -> HistoricalSourcePackageResultV1:
    """Formally reread every package byte and return bounded custody evidence."""

    package = _validate_existing_package_path(package_path)
    manifest_path = package / MANIFEST_DIRECTORY / PACKAGE_MANIFEST_FILE
    raw_manifest = _read_regular_file(manifest_path)
    try:
        manifest = HistoricalSourcePackageManifestV1.model_validate_json(raw_manifest)
    except (ValidationError, ValueError, TypeError) as exc:
        raise HistoricalSourcePackageCorruptionError(
            "historical source package manifest is invalid"
        ) from exc
    if expected_plan_fingerprint is not None and (
        manifest.pilot_plan_fingerprint != expected_plan_fingerprint
    ):
        raise HistoricalSourcePackageCorruptionError("source package plan differs")
    if package.name != f"plan={manifest.pilot_plan_fingerprint}":
        raise HistoricalSourcePackageCorruptionError("source package path identity differs")

    plan_path = package / MANIFEST_DIRECTORY / REQUEST_PLAN_FILE
    inventory_path = package / MANIFEST_DIRECTORY / INVENTORY_FILE
    plan_bytes = _read_regular_file(plan_path)
    inventory_bytes = _read_regular_file(inventory_path)
    if _sha256(plan_bytes) != manifest.request_plan_document_sha256:
        raise HistoricalSourcePackageCorruptionError("request plan bytes changed")
    if _sha256(inventory_bytes) != manifest.inventory_document_sha256:
        raise HistoricalSourcePackageCorruptionError("inventory bytes changed")
    plan_document = _read_json_bytes(plan_bytes)
    inventory_document = _read_json_bytes(inventory_bytes)
    if (
        plan_document.get("logical_content_fingerprint")
        != manifest.pilot_plan_fingerprint
        or plan_document.get("provider_id") != manifest.provider_id
        or plan_document.get("serial_pace_seconds") != manifest.serial_pace_seconds
        or plan_document.get("planned_request_ceiling")
        != manifest.planned_request_ceiling
        or plan_document.get("inventory") != inventory_document
    ):
        raise HistoricalSourcePackageCorruptionError(
            "source package plan and inventory binding differs"
        )

    expected_files = {
        f"{MANIFEST_DIRECTORY}/{PACKAGE_MANIFEST_FILE}",
        f"{MANIFEST_DIRECTORY}/{REQUEST_PLAN_FILE}",
        f"{MANIFEST_DIRECTORY}/{INVENTORY_FILE}",
    }
    total_requests = 0
    for receipt in manifest.scope_receipts:
        total_requests += receipt.request_count
        for artifact in receipt.artifacts:
            expected_files.add(artifact.relative_path)
            payload = _read_regular_file(package / PurePosixPath(artifact.relative_path))
            if len(payload) != artifact.byte_size or _sha256(payload) != artifact.physical_sha256:
                raise HistoricalSourcePackageCorruptionError(
                    "historical source artifact custody differs"
                )
            _validate_payload_security(_read_json_bytes(payload))
    if total_requests != manifest.total_request_count:
        raise HistoricalSourcePackageCorruptionError("source package request count differs")

    actual_files: set[str] = set()
    total_bytes = 0
    if stat.S_IMODE(package.stat().st_mode) != 0o700:
        raise HistoricalSourcePackageCorruptionError(
            "source package directory custody differs"
        )
    for path in package.rglob("*"):
        if path.is_symlink():
            raise HistoricalSourcePackageCorruptionError("source package contains a symlink")
        if path.is_dir() and stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise HistoricalSourcePackageCorruptionError(
                "source package directory custody differs"
            )
        if path.is_file():
            relative = path.relative_to(package).as_posix()
            actual_files.add(relative)
            total_bytes += path.stat().st_size
            if stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise HistoricalSourcePackageCorruptionError(
                    "source package file custody differs"
                )
    if actual_files != expected_files:
        raise HistoricalSourcePackageCorruptionError("source package file set differs")
    return HistoricalSourcePackageResultV1(
        manifest=manifest,
        package_path=package,
        manifest_path=manifest_path,
        manifest_physical_sha256=_sha256(raw_manifest),
        file_count=len(actual_files),
        total_bytes=total_bytes,
        status="reread",
    )


def _prepare_captured_scopes(
    plan: HistoricalPilotPlanV1,
    captured_scopes: tuple[CapturedHistoricalSourceScopeV1, ...],
) -> tuple[tuple[tuple[str, bytes], ...], tuple[HistoricalSourceScopeReceiptV1, ...]]:
    planned = {
        (line.kind.value, line.logical_endpoint, scope): line
        for line in plan.request_lines
        for scope in line.scopes
    }
    captured = {
        (item.request_kind.value, item.logical_endpoint, item.scope): item
        for item in captured_scopes
    }
    if len(captured) != len(captured_scopes):
        raise HistoricalSourcePackageConflictError("captured source scopes are duplicated")
    if set(captured) != set(planned):
        raise HistoricalSourcePackageConflictError(
            "captured source scopes differ from the exact pilot plan"
        )
    payloads: list[tuple[str, bytes]] = []
    receipts: list[HistoricalSourceScopeReceiptV1] = []
    planned_paths = set(plan.temporary_package_relative_paths)
    prefix = f"historical-research-pilot/plan={plan.logical_content_fingerprint}/"
    for key in sorted(captured):
        item = captured[key]
        line = planned[key]
        if not item.completed or not item.responses:
            raise HistoricalSourcePackageConflictError(
                "every planned source scope must be explicitly complete"
            )
        ceiling = line.page_ceiling_per_scope or 1
        if len(item.responses) > ceiling:
            raise HistoricalSourcePackageConflictError(
                "captured scope exceeds the planned request ceiling"
            )
        artifacts: list[HistoricalSourceArtifactV1] = []
        for sequence, response in enumerate(item.responses, start=1):
            _validate_payload_security(response)
            payload = _canonical_json_bytes(response)
            relative = _artifact_relative_path(item, sequence)
            if f"{prefix}{relative}" not in planned_paths:
                raise HistoricalSourcePackageConflictError(
                    "captured artifact path is outside the exact pilot plan"
                )
            artifact = HistoricalSourceArtifactV1(
                request_kind=item.request_kind,
                logical_endpoint=item.logical_endpoint,
                scope=item.scope,
                sequence=sequence,
                relative_path=relative,
                byte_size=len(payload),
                physical_sha256=_sha256(payload),
            )
            artifacts.append(artifact)
            payloads.append((relative, payload))
        receipts.append(
            HistoricalSourceScopeReceiptV1(
                request_kind=item.request_kind,
                logical_endpoint=item.logical_endpoint,
                scope=item.scope,
                completed=True,
                request_count=len(artifacts),
                request_ceiling=ceiling,
                artifacts=tuple(artifacts),
            )
        )
    if sum(item.request_count for item in receipts) > plan.planned_request_ceiling:
        raise HistoricalSourcePackageConflictError(
            "captured package exceeds the plan-wide request ceiling"
        )
    return tuple(payloads), tuple(receipts)


def _artifact_relative_path(
    captured: CapturedHistoricalSourceScopeV1,
    sequence: int,
) -> str:
    if any(character in captured.scope for character in "/\\"):
        raise HistoricalSourcePackageConflictError("captured scope is unsafe")
    if captured.request_kind is HistoricalSourceRequestKind.GROUPED_DAILY:
        return f"staged/grouped-daily/session={captured.scope}/request={sequence:03d}.json"
    if captured.request_kind is HistoricalSourceRequestKind.ACTIVE_ALL_TICKERS:
        return f"staged/active-all-tickers/session={captured.scope}/page={sequence:03d}.json"
    if captured.request_kind is HistoricalSourceRequestKind.INACTIVE_ALL_TICKERS:
        return f"staged/inactive-all-tickers/anchor={captured.scope}/page={sequence:03d}.json"
    if captured.request_kind is HistoricalSourceRequestKind.SPLITS:
        return f"staged/splits/page={sequence:03d}.json"
    if captured.request_kind is HistoricalSourceRequestKind.DIVIDENDS:
        return f"staged/dividends/page={sequence:03d}.json"
    if sequence != 1:
        raise HistoricalSourcePackageConflictError(
            "each targeted ticker-event scope permits one request"
        )
    return f"staged/ticker-events/request-scope={captured.scope}.json"


def _validate_payload_security(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in {item.replace("-", "_") for item in _SENSITIVE_KEYS}:
                raise HistoricalSourcePackageConflictError(
                    "source response contains credential-bearing fields"
                )
            _validate_payload_security(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_payload_security(item)
        return
    if isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        parsed = urlsplit(value)
        sensitive = {item.replace("-", "_") for item in _SENSITIVE_KEYS}
        query_keys = {
            key.strip().lower().replace("-", "_") for key, _ in parse_qsl(parsed.query)
        }
        if parsed.username or parsed.password or query_keys & sensitive:
            raise HistoricalSourcePackageConflictError(
                "source response contains a credential-bearing URL"
            )


def _validate_new_package_path(path: Path, plan_fingerprint: str) -> Path:
    target = path.absolute()
    if (
        target.parent.name != "historical-research-pilot"
        or target.name != f"plan={plan_fingerprint}"
        or Path("/tmp") not in target.parents
    ):
        raise HistoricalSourcePackageConflictError(
            "source package must use the exact /tmp historical pilot path"
        )
    if not target.parent.exists() or not target.parent.is_dir() or target.parent.is_symlink():
        raise HistoricalSourcePackageConflictError(
            "source package parent must be an existing non-symlink directory"
        )
    return target


def _validate_existing_package_path(path: Path) -> Path:
    package = path.absolute()
    if (
        Path("/tmp") not in package.parents
        or package.parent.name != "historical-research-pilot"
        or not package.is_dir()
        or package.is_symlink()
    ):
        raise HistoricalSourcePackageCorruptionError(
            "historical source package path is invalid"
        )
    return package


def _read_regular_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise HistoricalSourcePackageCorruptionError("source package file is invalid")
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise HistoricalSourcePackageCorruptionError("source package file size is invalid")
    return path.read_bytes()


def _read_json_bytes(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HistoricalSourcePackageCorruptionError("source package JSON is invalid") from exc
    if not isinstance(value, dict):
        raise HistoricalSourcePackageCorruptionError("source package JSON must be an object")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    try:
        payload = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HistoricalSourcePackageConflictError(
            "source response is not canonical JSON"
        ) from exc
    if len(payload) > MAXIMUM_JSON_BYTES:
        raise HistoricalSourcePackageConflictError("source response exceeds size ceiling")
    return payload


def _write_file(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o400)


def _make_directories_owner_only(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o700)
    root.chmod(0o700)


def _fsync_tree(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        _fsync_directory(path)
    _fsync_directory(root)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
