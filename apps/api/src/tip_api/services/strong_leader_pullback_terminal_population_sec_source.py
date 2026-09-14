"""Atomic private custody for corrected-population SEC documents."""

from __future__ import annotations

import os
import re
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import (
    BoundedSecTransport,
    SecDownloadResult,
    SecRateLimiter,
    SecRetryPolicy,
)
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_source,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-population-sec-source/1.0"
ARTIFACT_VERSION = (
    "strong-leader-pullback-terminal-population-sec-document-artifact/1.0"
)
MANIFEST_FILE = "manifest.json"
ARTIFACT_FILE = "artifact.json"
DOCUMENT_FILE = "document.bin"
MAXIMUM_MANIFEST_BYTES = 64 * 1024
MAXIMUM_ARTIFACT_BYTES = 32 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_SOURCE_NAME_PATTERN = r"^source=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackTerminalPopulationSecSourceError(RuntimeError):
    """Raised when corrected-population SEC custody cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalPopulationSecDocumentArtifactV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-document-artifact/1.0"
    ] = ARTIFACT_VERSION
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    request_sequence: int = Field(ge=1)
    plan_item_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    form: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    observed_at: datetime
    content_type: str = Field(min_length=1)
    byte_count: int = Field(ge=1, le=plan_source.MAXIMUM_DOCUMENT_BYTES)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    retry_count: int = Field(ge=0, le=plan_source.MAXIMUM_RETRIES_PER_REQUEST)
    source_content_retained: Literal[True] = True
    credential_material_retained: Literal[False] = False
    document_content_interpreted: Literal[False] = False
    listed_security_fact_authority: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def artifact_reconciles(self) -> "TerminalPopulationSecDocumentArtifactV1":
        if (
            self.content_type not in source_base._ALLOWED_CONTENT_TYPES
            or self.logical_fingerprint
            != source_base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC artifact differs")
        return self


class StrongLeaderPullbackTerminalPopulationSecSourceManifestV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-source/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    first_observed_at: datetime
    completed_at: datetime
    planned_request_count: int = Field(ge=1)
    completed_document_count: int = Field(ge=1)
    external_request_count: int = Field(ge=1)
    retry_count: int = Field(ge=0)
    total_document_bytes: int = Field(ge=1)
    content_type_counts: tuple[tuple[str, int], ...]
    artifact_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    credential_material_retained: Literal[False] = False
    complete_source_custody: Literal[True] = True
    document_content_interpreted: Literal[False] = False
    listed_security_identity_assignment_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("first_observed_at", "completed_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationSecSourceManifestV1":
        if (
            self.completed_at < self.first_observed_at
            or self.completed_document_count != self.planned_request_count
            or self.external_request_count
            != self.completed_document_count + self.retry_count
            or sum(count for _, count in self.content_type_counts)
            != self.completed_document_count
            or self.content_type_counts != tuple(sorted(self.content_type_counts))
            or self.logical_fingerprint
            != source_base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC manifest differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationSecSourceResult:
    output_root: Path
    status: Literal["published", "already_present"]
    completed_document_count: int
    new_document_count: int
    network_request_count: int
    manifest: StrongLeaderPullbackTerminalPopulationSecSourceManifestV1
    manifest_sha256: str


class _DocumentTransport(Protocol):
    request_count: int

    def download(
        self,
        url: str,
        target: Path,
        *,
        user_agent: SecretStr,
        timeout_seconds: Decimal,
        max_bytes: int,
    ) -> SecDownloadResult: ...


TransportFactory = Callable[[SecRateLimiter], _DocumentTransport]
Clock = Callable[[], datetime]


def acquire_strong_leader_pullback_terminal_population_sec_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    config: SecProviderConfig,
    implementation_revision: str,
    transport_factory: TransportFactory | None = None,
    clock: Clock | None = None,
) -> StrongLeaderPullbackTerminalPopulationSecSourceResult:
    """Acquire the complete small plan into one atomic source package."""

    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source revision is invalid"
        )
    plan = plan_source.read_strong_leader_pullback_terminal_population_sec_source_plan(
        output_root=plan_root, output_custody_root=plan_custody_root
    )
    if (
        config.max_requests_per_second
        > Decimal(plan.report.maximum_requests_per_second)
        or config.max_retries > plan.report.maximum_retries_per_request
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source configuration exceeds the plan"
        )
    target = _validated_output_target(output_root, output_custody_root)
    staging = target.parent / f".{target.name}.partial"
    if target.exists() or target.is_symlink():
        if staging.exists() or staging.is_symlink():
            raise StrongLeaderPullbackTerminalPopulationSecSourceError(
                "completed and partial terminal-population SEC sources coexist"
            )
        existing = read_strong_leader_pullback_terminal_population_sec_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=target,
            output_custody_root=output_custody_root,
        )
        return StrongLeaderPullbackTerminalPopulationSecSourceResult(
            output_root=target,
            status="already_present",
            completed_document_count=existing.completed_document_count,
            new_document_count=0,
            network_request_count=0,
            manifest=existing.manifest,
            manifest_sha256=existing.manifest_sha256,
        )
    _remove_owned_staging(staging=staging, target=target)
    staging.mkdir(mode=0o700)
    limiter = SecRateLimiter(max_requests_per_second=config.max_requests_per_second)
    factory = transport_factory or _default_transport_factory(config)
    now = clock or (lambda: datetime.now(UTC))
    artifacts: list[TerminalPopulationSecDocumentArtifactV1] = []
    network_count = 0
    try:
        for item in plan.report.items:
            artifact = _download_item(
                staging=staging,
                item=item,
                config=config,
                implementation_revision=implementation_revision,
                transport=factory(limiter),
                observed_at=now(),
            )
            artifacts.append(artifact)
            network_count += 1 + artifact.retry_count
        manifest = _build_manifest(
            plan=plan,
            artifacts=tuple(artifacts),
            implementation_revision=implementation_revision,
            completed_at=now(),
        )
        source_base._write_exclusive(
            staging / MANIFEST_FILE,
            source_base._json_bytes(manifest.model_dump(mode="json")),
        )
        source_base._fsync_directory(staging)
        staging.replace(target)
        source_base._fsync_directory(target.parent)
    except Exception:
        if (
            staging.exists()
            and not staging.is_symlink()
            and staging.parent == target.parent
        ):
            shutil.rmtree(staging)
            source_base._fsync_directory(staging.parent)
        raise
    reread = read_strong_leader_pullback_terminal_population_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackTerminalPopulationSecSourceResult(
        output_root=target,
        status="published",
        completed_document_count=len(artifacts),
        new_document_count=len(artifacts),
        network_request_count=network_count,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
    )


def read_strong_leader_pullback_terminal_population_sec_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackTerminalPopulationSecSourceResult:
    """Formally reread a complete source package and every retained document."""

    plan = plan_source.read_strong_leader_pullback_terminal_population_sec_source_plan(
        output_root=plan_root, output_custody_root=plan_custody_root
    )
    root = _validated_completed_output(output_root, output_custody_root)
    expected_names = {
        MANIFEST_FILE,
        *(f"request={item.request_sequence:06d}" for item in plan.report.items),
    }
    if {item.name for item in root.iterdir()} != expected_names:
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source members differ"
        )
    manifest_path = root / MANIFEST_FILE
    source_base._require_regular_file(
        manifest_path, 0o400, MAXIMUM_MANIFEST_BYTES
    )
    raw = manifest_path.read_bytes()
    try:
        manifest = StrongLeaderPullbackTerminalPopulationSecSourceManifestV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source manifest is invalid"
        ) from exc
    if (
        raw != source_base._json_bytes(manifest.model_dump(mode="json"))
        or manifest.plan_sha256 != plan.report_sha256
        or manifest.plan_logical_fingerprint != plan.report.logical_fingerprint
        or manifest.planned_request_count != plan.report.planned_request_count
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source plan binding differs"
        )
    artifacts = tuple(
        _read_artifact_directory(
            directory=root / f"request={item.request_sequence:06d}", item=item
        )
        for item in plan.report.items
    )
    _validate_manifest(manifest=manifest, artifacts=artifacts)
    return StrongLeaderPullbackTerminalPopulationSecSourceResult(
        output_root=root,
        status="already_present",
        completed_document_count=len(artifacts),
        new_document_count=0,
        network_request_count=0,
        manifest=manifest,
        manifest_sha256=source_base._sha256_file(manifest_path),
    )


def _default_transport_factory(config: SecProviderConfig) -> TransportFactory:
    def factory(limiter: SecRateLimiter) -> BoundedSecTransport:
        return BoundedSecTransport(
            request_ceiling=1 + config.max_retries,
            rate_limiter=limiter,
            retry_policy=SecRetryPolicy(max_retries=config.max_retries),
        )

    return factory


def _download_item(
    *, staging: Path, item: object, config: SecProviderConfig,
    implementation_revision: str, transport: _DocumentTransport,
    observed_at: datetime,
) -> TerminalPopulationSecDocumentArtifactV1:
    request_root = staging / f"request={item.request_sequence:06d}"
    request_root.mkdir(mode=0o700)
    document_path = request_root / DOCUMENT_FILE
    result = transport.download(
        item.request_url,
        document_path,
        user_agent=config.user_agent,
        timeout_seconds=config.request_timeout_seconds,
        max_bytes=item.maximum_response_bytes,
    )
    if (
        result.url != item.request_url
        or result.byte_count < 1
        or result.byte_count > item.maximum_response_bytes
        or result.content_type not in source_base._ALLOWED_CONTENT_TYPES
        or result.retry_count > plan_source.MAXIMUM_RETRIES_PER_REQUEST
        or document_path.stat().st_size != result.byte_count
        or source_base._sha256_file(document_path) != result.sha256
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC response differs from the plan"
        )
    document_path.chmod(0o400)
    values = {
        "implementation_revision": implementation_revision,
        "request_sequence": item.request_sequence,
        "plan_item_fingerprint": source_base._fingerprint(
            item.model_dump(mode="json")
        ),
        "instrument_id": item.instrument_id,
        "cik": item.cik,
        "accession_number": item.accession_number,
        "form": item.form,
        "request_url": item.request_url,
        "observed_at": normalize_utc_datetime(observed_at),
        "content_type": result.content_type,
        "byte_count": result.byte_count,
        "physical_sha256": result.sha256,
        "retry_count": result.retry_count,
    }
    provisional = TerminalPopulationSecDocumentArtifactV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    artifact = TerminalPopulationSecDocumentArtifactV1.model_validate(
        {
            **values,
            "logical_fingerprint": source_base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )
    source_base._write_exclusive(
        request_root / ARTIFACT_FILE,
        source_base._json_bytes(artifact.model_dump(mode="json")),
    )
    source_base._fsync_directory(request_root)
    return artifact


def _read_artifact_directory(
    *, directory: Path, item: object
) -> TerminalPopulationSecDocumentArtifactV1:
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or directory.stat().st_uid != os.getuid()
        or stat.S_IMODE(directory.stat().st_mode) != 0o700
        or directory.resolve(strict=True) != directory
        or directory.name != f"request={item.request_sequence:06d}"
        or {member.name for member in directory.iterdir()}
        != {ARTIFACT_FILE, DOCUMENT_FILE}
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC artifact directory differs"
        )
    artifact_path = directory / ARTIFACT_FILE
    document_path = directory / DOCUMENT_FILE
    source_base._require_regular_file(artifact_path, 0o400, MAXIMUM_ARTIFACT_BYTES)
    source_base._require_regular_file(
        document_path, 0o400, plan_source.MAXIMUM_DOCUMENT_BYTES
    )
    try:
        artifact = TerminalPopulationSecDocumentArtifactV1.model_validate_json(
            artifact_path.read_bytes()
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC artifact is invalid"
        ) from exc
    if (
        artifact_path.read_bytes()
        != source_base._json_bytes(artifact.model_dump(mode="json"))
        or artifact.request_sequence != item.request_sequence
        or artifact.plan_item_fingerprint
        != source_base._fingerprint(item.model_dump(mode="json"))
        or artifact.instrument_id != item.instrument_id
        or artifact.cik != item.cik
        or artifact.accession_number != item.accession_number
        or artifact.form != item.form
        or artifact.request_url != item.request_url
        or document_path.stat().st_size != artifact.byte_count
        or source_base._sha256_file(document_path) != artifact.physical_sha256
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC artifact binding differs"
        )
    return artifact


def _build_manifest(
    *, plan: object, artifacts: tuple[TerminalPopulationSecDocumentArtifactV1, ...],
    implementation_revision: str, completed_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecSourceManifestV1:
    if len(artifacts) != plan.report.planned_request_count:
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC completion count differs"
        )
    counts = Counter(item.content_type for item in artifacts)
    values = {
        "plan_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "implementation_revision": implementation_revision,
        "first_observed_at": min(item.observed_at for item in artifacts),
        "completed_at": normalize_utc_datetime(completed_at),
        "planned_request_count": plan.report.planned_request_count,
        "completed_document_count": len(artifacts),
        "external_request_count": sum(1 + item.retry_count for item in artifacts),
        "retry_count": sum(item.retry_count for item in artifacts),
        "total_document_bytes": sum(item.byte_count for item in artifacts),
        "content_type_counts": source_base._ordered(counts),
        "artifact_binding_fingerprint": source_base._fingerprint(
            tuple(item.model_dump(mode="json") for item in artifacts)
        ),
    }
    provisional = StrongLeaderPullbackTerminalPopulationSecSourceManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationSecSourceManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": source_base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_manifest(
    *, manifest: StrongLeaderPullbackTerminalPopulationSecSourceManifestV1,
    artifacts: tuple[TerminalPopulationSecDocumentArtifactV1, ...],
) -> None:
    if (
        tuple(item.request_sequence for item in artifacts)
        != tuple(range(1, len(artifacts) + 1))
        or manifest.implementation_revision
        not in {item.implementation_revision for item in artifacts}
        or manifest.first_observed_at != min(item.observed_at for item in artifacts)
        or manifest.external_request_count
        != sum(1 + item.retry_count for item in artifacts)
        or manifest.retry_count != sum(item.retry_count for item in artifacts)
        or manifest.total_document_bytes != sum(item.byte_count for item in artifacts)
        or manifest.content_type_counts
        != source_base._ordered(Counter(item.content_type for item in artifacts))
        or manifest.artifact_binding_fingerprint
        != source_base._fingerprint(
            tuple(item.model_dump(mode="json") for item in artifacts)
        )
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC manifest aggregates differ"
        )


def _remove_owned_staging(*, staging: Path, target: Path) -> None:
    if not staging.exists() and not staging.is_symlink():
        return
    if (
        staging.is_symlink()
        or not staging.is_dir()
        or staging.parent != target.parent
        or staging.name != f".{target.name}.partial"
        or staging.stat().st_uid != os.getuid()
        or stat.S_IMODE(staging.stat().st_mode) != 0o700
        or staging.resolve(strict=True) != staging
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC staging is unsafe"
        )
    shutil.rmtree(staging)
    source_base._fsync_directory(staging.parent)


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_SOURCE_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source target is unsafe"
        )
    return path


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or target.resolve(strict=True) != target
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourceError(
            "terminal-population SEC source output is unsafe"
        )
    return target
