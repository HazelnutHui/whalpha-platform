"""Formal reader for one immutable Dell-local OCI Dashboard serving bundle."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.persistence.parquet.dashboard_snapshot_active import (
    aggregate_sha,
    file_references,
)
from tip_api.services.private_dashboard_snapshot import (
    DashboardSnapshotManifest,
    sha256_file,
    validate_snapshot_release,
)


CONTRACT_VERSION = "oci-dashboard-serving-bundle/1.0"
SUPPORTED_CONTRACTS = {("1.9", "2.6")}
EXPECTED_TOP_LEVEL = {
    "checksums.sha256",
    "dashboard",
    "deployment-manifest.json",
    "login",
    "private-data",
}
EXPECTED_LOGIN_FILES = {
    "index.html",
    "login-i18n.js",
    "login.css",
    "login.js",
}
FORBIDDEN_DEMO_MARKERS = (
    b"synthetic_demo_fixture",
    b"synthetic_demo",
    b"demoDashboardData",
)
PROHIBITED_FILE_NAMES = {".env", ".env.local", "credentials", "secrets"}
PROHIBITED_FILE_SUFFIXES = {".key", ".map", ".parquet", ".pem"}


class OciDashboardServingBundleError(RuntimeError):
    """Raised when a local serving bundle cannot prove its exact custody."""


class OciDashboardDeploymentManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_contract_version: str
    release_id: str
    git_commit: str
    source_tree_clean: bool
    build_timestamp: datetime
    frontend_mode: str
    dashboard_base: str
    default_locale: str
    supported_locales: tuple[str, ...]
    guest_and_credential_capability_identical: bool
    market_intelligence_publication_id: str
    market_intelligence_payload_sha256: str
    market_intelligence_logical_fingerprint: str
    snapshot_contract_version: str
    dashboard_contract_version: str
    snapshot_aggregate_sha256: str
    snapshot_manifest_sha256: str
    candidate_analytics_logical_fingerprint: str
    candidate_audit_logical_fingerprint: str
    candidate_strategy_logical_fingerprint: str
    candidate_strategy_audit_logical_fingerprint: str
    current_session_date: str
    previous_session_date: str
    file_count: int = Field(ge=1)
    contains_credentials: bool
    contains_raw_provider_data: bool
    contains_parquet: bool
    deployment_authorized: bool
    bundle_logical_fingerprint: str

    @field_validator(
        "market_intelligence_payload_sha256",
        "market_intelligence_logical_fingerprint",
        "snapshot_aggregate_sha256",
        "snapshot_manifest_sha256",
        "candidate_analytics_logical_fingerprint",
        "candidate_audit_logical_fingerprint",
        "candidate_strategy_logical_fingerprint",
        "candidate_strategy_audit_logical_fingerprint",
        "bundle_logical_fingerprint",
    )
    @classmethod
    def fingerprints(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("bundle fingerprint must be lowercase SHA-256")
        return value

    @field_validator("git_commit")
    @classmethod
    def source_revision(cls, value: str) -> str:
        if (
            len(value) not in {40, 64}
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("bundle Git revision must be lowercase SHA-1 or SHA-256")
        return value

    @model_validator(mode="after")
    def fixed_boundaries(self) -> "OciDashboardDeploymentManifest":
        if (
            self.bundle_contract_version != CONTRACT_VERSION
            or (self.snapshot_contract_version, self.dashboard_contract_version)
            not in SUPPORTED_CONTRACTS
            or self.frontend_mode != "snapshot"
            or self.dashboard_base != "/dashboard/"
            or self.default_locale != "en"
            or self.supported_locales != ("en", "zh")
            or not self.source_tree_clean
            or not self.guest_and_credential_capability_identical
            or self.contains_credentials
            or self.contains_raw_provider_data
            or self.contains_parquet
            or self.deployment_authorized
            or self.build_timestamp.tzinfo is None
            or self.build_timestamp.utcoffset() is None
            or self.build_timestamp.utcoffset().total_seconds() != 0
            or self.build_timestamp.microsecond != 0
        ):
            raise ValueError("serving bundle fixed boundary mismatch")
        suffix = self.release_id.rpartition("-")[2]
        if len(suffix) < 7 or not self.git_commit.startswith(suffix):
            raise ValueError("bundle release does not identify its source commit")
        return self


@dataclass(frozen=True, slots=True)
class CompletedOciDashboardServingBundle:
    path: Path
    deployment_manifest: OciDashboardDeploymentManifest
    snapshot_manifest: DashboardSnapshotManifest
    checksum_file_count: int
    bundle_logical_fingerprint: str


def read_oci_dashboard_serving_bundle(
    path: Path,
    *,
    expected_snapshot_path: Path | None = None,
) -> CompletedOciDashboardServingBundle:
    """Validate every local bundle byte and its exact source-Snapshot binding."""

    bundle = _safe_existing_directory(path)
    _validate_tree(bundle)
    if {item.name for item in bundle.iterdir()} != EXPECTED_TOP_LEVEL:
        raise OciDashboardServingBundleError("serving bundle top-level file set mismatch")
    if {item.name for item in (bundle / "login").iterdir()} != EXPECTED_LOGIN_FILES:
        raise OciDashboardServingBundleError("serving bundle login file set mismatch")
    if not (bundle / "dashboard" / "index.html").is_file():
        raise OciDashboardServingBundleError("serving bundle Dashboard entry is missing")
    for item in bundle.rglob("*"):
        if not item.is_file():
            continue
        if (
            item.name.lower() in PROHIBITED_FILE_NAMES
            or item.suffix.lower() in PROHIBITED_FILE_SUFFIXES
        ):
            raise OciDashboardServingBundleError(
                "serving bundle contains a prohibited file type"
            )
        if item.is_relative_to(bundle / "dashboard"):
            raw = item.read_bytes()
            if any(marker in raw for marker in FORBIDDEN_DEMO_MARKERS):
                raise OciDashboardServingBundleError(
                    "serving bundle contains prohibited demo data"
                )

    checksums = _read_checksum_inventory(bundle)
    actual_files = {
        item.relative_to(bundle).as_posix()
        for item in bundle.rglob("*")
        if item.is_file() and item.name != "checksums.sha256"
    }
    if set(checksums) != actual_files:
        raise OciDashboardServingBundleError(
            "serving bundle checksum inventory is incomplete or has extras"
        )
    for relative_path, expected_sha in checksums.items():
        if sha256_file(bundle / relative_path) != expected_sha:
            raise OciDashboardServingBundleError("serving bundle checksum mismatch")

    manifest_path = bundle / "deployment-manifest.json"
    try:
        deployment = OciDashboardDeploymentManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise OciDashboardServingBundleError(
            "serving bundle deployment manifest is invalid"
        ) from exc
    logical_payload = deployment.model_dump(
        mode="json", exclude={"bundle_logical_fingerprint"}
    )
    if _fingerprint(logical_payload) != deployment.bundle_logical_fingerprint:
        raise OciDashboardServingBundleError(
            "serving bundle logical fingerprint mismatch"
        )
    if deployment.file_count + 1 != len(checksums):
        raise OciDashboardServingBundleError("serving bundle file count mismatch")

    snapshot = validate_snapshot_release(bundle)
    if (
        snapshot.release_id != deployment.release_id
        or snapshot.snapshot_contract_version != deployment.snapshot_contract_version
        or snapshot.dashboard_contract_version != deployment.dashboard_contract_version
        or snapshot.market_intelligence_publication_id
        != deployment.market_intelligence_publication_id
        or snapshot.market_intelligence_payload_sha256
        != deployment.market_intelligence_payload_sha256
        or snapshot.market_intelligence_logical_fingerprint
        != deployment.market_intelligence_logical_fingerprint
        or snapshot.candidate_analytics_logical_fingerprint
        != deployment.candidate_analytics_logical_fingerprint
        or snapshot.candidate_audit_logical_fingerprint
        != deployment.candidate_audit_logical_fingerprint
        or snapshot.candidate_strategy_logical_fingerprint
        != deployment.candidate_strategy_logical_fingerprint
        or snapshot.candidate_strategy_audit_logical_fingerprint
        != deployment.candidate_strategy_audit_logical_fingerprint
        or snapshot.current_session_date != deployment.current_session_date
        or snapshot.previous_session_date != deployment.previous_session_date
        or sha256_file(bundle / "private-data" / "v1" / "manifest.json")
        != deployment.snapshot_manifest_sha256
    ):
        raise OciDashboardServingBundleError(
            "serving bundle Snapshot or analytics binding mismatch"
        )

    if expected_snapshot_path is not None:
        source = _safe_existing_directory(expected_snapshot_path)
        source_manifest = validate_snapshot_release(source)
        if source_manifest != snapshot:
            raise OciDashboardServingBundleError("source Snapshot manifest changed")
        if aggregate_sha(file_references(source)) != deployment.snapshot_aggregate_sha256:
            raise OciDashboardServingBundleError("source Snapshot aggregate changed")
        source_private = source / "private-data"
        copied_private = bundle / "private-data"
        source_files = _relative_file_hashes(source_private)
        copied_files = _relative_file_hashes(copied_private)
        if source_files != copied_files:
            raise OciDashboardServingBundleError(
                "serving bundle does not contain the exact source Snapshot bytes"
            )

    return CompletedOciDashboardServingBundle(
        path=bundle,
        deployment_manifest=deployment,
        snapshot_manifest=snapshot,
        checksum_file_count=len(checksums),
        bundle_logical_fingerprint=deployment.bundle_logical_fingerprint,
    )


def _safe_existing_directory(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise OciDashboardServingBundleError("serving bundle directory is unsafe")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise OciDashboardServingBundleError("serving bundle path contains a symlink")
    return resolved


def _validate_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise OciDashboardServingBundleError("serving bundle contains an unsafe entry")


def _read_checksum_inventory(root: Path) -> dict[str, str]:
    path = root / "checksums.sha256"
    if path.is_symlink() or not path.is_file():
        raise OciDashboardServingBundleError("serving bundle checksum inventory is missing")
    result: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        digest, separator, relative = line.partition("  ")
        normalized = relative.removeprefix("./")
        candidate = PurePosixPath(normalized)
        if (
            separator != "  "
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or candidate.is_absolute()
            or ".." in candidate.parts
            or candidate.as_posix() != normalized
            or normalized == "checksums.sha256"
            or normalized in result
        ):
            raise OciDashboardServingBundleError(
                "serving bundle checksum inventory is malformed"
            )
        result[normalized] = digest
    if not result:
        raise OciDashboardServingBundleError("serving bundle checksum inventory is empty")
    if tuple(result) != tuple(sorted(result)):
        raise OciDashboardServingBundleError("serving bundle checksums are not canonical")
    return result


def _relative_file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
