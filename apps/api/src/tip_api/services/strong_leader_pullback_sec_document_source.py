"""Resumable private custody for the bounded SEC primary-document plan."""

from __future__ import annotations

import hashlib
import json
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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import (
    BoundedSecTransport,
    SecDownloadResult,
    SecRateLimiter,
    SecRetryPolicy,
)
from tip_api.services.strong_leader_pullback_sec_document_plan import (
    EXPECTED_BATCH_COUNT,
    EXPECTED_REQUEST_COUNT,
    MAXIMUM_DOCUMENT_BYTES,
    MAXIMUM_REQUESTS_PER_SECOND,
    MAXIMUM_RETRIES_PER_REQUEST,
    SecPrimaryDocumentPlanItemV1,
    StrongLeaderPullbackSecDocumentPlanResult,
    read_strong_leader_pullback_sec_document_plan,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-document-source/1.0"
ARTIFACT_VERSION = "strong-leader-pullback-sec-document-artifact/1.0"
MANIFEST_FILE = "manifest.json"
ARTIFACT_FILE = "artifact.json"
DOCUMENT_FILE = "document.bin"
MAXIMUM_MANIFEST_BYTES = 256 * 1024
MAXIMUM_ARTIFACT_BYTES = 32 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_SOURCE_NAME_PATTERN = r"^source=[A-Za-z0-9._-]+$"
_REQUEST_NAME_PATTERN = re.compile(r"request=(?P<sequence>[0-9]{6})\Z")
_STAGING_NAME_PATTERN = re.compile(r"\.request=(?P<sequence>[0-9]{6})\.partial\Z")
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/octet-stream",
        "application/xhtml+xml",
        "application/xml",
        "text/html",
        "text/plain",
        "text/xml",
    }
)


class StrongLeaderPullbackSecDocumentSourceError(RuntimeError):
    """Raised when SEC document custody cannot be acquired or proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecPrimaryDocumentArtifactV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-document-artifact/1.0"
    ] = ARTIFACT_VERSION
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    request_sequence: int = Field(ge=1, le=EXPECTED_REQUEST_COUNT)
    batch_number: int = Field(ge=1, le=EXPECTED_BATCH_COUNT)
    plan_item_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    form: str
    request_url: str
    observed_at: datetime
    content_type: str
    byte_count: int = Field(ge=1, le=MAXIMUM_DOCUMENT_BYTES)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    retry_count: int = Field(ge=0, le=MAXIMUM_RETRIES_PER_REQUEST)
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

    @field_validator("accession_number", "form", "request_url", "content_type")
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("SEC document artifact text is invalid")
        return value

    @model_validator(mode="after")
    def artifact_reconciles(self) -> "SecPrimaryDocumentArtifactV1":
        if self.content_type not in _ALLOWED_CONTENT_TYPES:
            raise ValueError("SEC document content type is unsupported")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC document artifact fingerprint differs")
        return self


class StrongLeaderPullbackSecDocumentSourceManifestV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-document-source/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    implementation_revisions: tuple[str, ...]
    first_observed_at: datetime
    completed_at: datetime
    planned_request_count: Literal[219] = EXPECTED_REQUEST_COUNT
    completed_document_count: Literal[219] = EXPECTED_REQUEST_COUNT
    completed_batch_count: Literal[22] = EXPECTED_BATCH_COUNT
    external_request_count: int = Field(ge=EXPECTED_REQUEST_COUNT)
    retry_count: int = Field(ge=0)
    total_document_bytes: int = Field(ge=EXPECTED_REQUEST_COUNT)
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

    @field_validator("implementation_revisions", mode="before")
    @classmethod
    def revisions_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if (
            not values
            or values != tuple(sorted(set(values)))
            or any(re.fullmatch(_REVISION_PATTERN, str(item)) is None for item in values)
        ):
            raise ValueError("SEC document source revisions are invalid")
        return values

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "StrongLeaderPullbackSecDocumentSourceManifestV1":
        if self.completed_at < self.first_observed_at:
            raise ValueError("SEC document source times are reversed")
        if self.external_request_count != self.completed_document_count + self.retry_count:
            raise ValueError("SEC document source request counts differ")
        if (
            sum(count for _, count in self.content_type_counts)
            != self.completed_document_count
            or self.content_type_counts != tuple(sorted(self.content_type_counts))
        ):
            raise ValueError("SEC document source content-type counts differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC document source fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecDocumentSourceResult:
    output_root: Path
    status: Literal["in_progress", "published", "already_present"]
    completed_document_count: int
    new_document_count: int
    network_request_count: int
    manifest: StrongLeaderPullbackSecDocumentSourceManifestV1 | None = None
    manifest_sha256: str | None = None


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
ProgressCallback = Callable[[SecPrimaryDocumentArtifactV1, int, int], None]
Clock = Callable[[], datetime]


def acquire_strong_leader_pullback_sec_document_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    config: SecProviderConfig,
    implementation_revision: str,
    maximum_new_documents: int | None = None,
    transport_factory: TransportFactory | None = None,
    clock: Clock | None = None,
    progress: ProgressCallback | None = None,
) -> StrongLeaderPullbackSecDocumentSourceResult:
    """Acquire or resume the exact plan into atomic per-document custody."""

    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source revision is invalid"
        )
    if maximum_new_documents is not None and not (
        1 <= maximum_new_documents <= EXPECTED_REQUEST_COUNT
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source run bound is invalid"
        )
    if (
        config.max_requests_per_second > Decimal(MAXIMUM_REQUESTS_PER_SECOND)
        or config.max_retries > MAXIMUM_RETRIES_PER_REQUEST
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source configuration exceeds the plan"
        )
    plan = read_strong_leader_pullback_sec_document_plan(
        output_root=plan_root,
        output_custody_root=plan_custody_root,
    )
    target = _validated_output_target(output_root, output_custody_root)
    partial = target.parent / f".{target.name}.partial"
    if target.exists() or target.is_symlink():
        if partial.exists() or partial.is_symlink():
            raise StrongLeaderPullbackSecDocumentSourceError(
                "completed and partial SEC document sources coexist"
            )
        completed = read_strong_leader_pullback_sec_document_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=target,
            output_custody_root=output_custody_root,
        )
        return StrongLeaderPullbackSecDocumentSourceResult(
            output_root=target,
            status="already_present",
            completed_document_count=EXPECTED_REQUEST_COUNT,
            new_document_count=0,
            network_request_count=0,
            manifest=completed.manifest,
            manifest_sha256=completed.manifest_sha256,
        )
    _prepare_partial(partial=partial, target=target, plan=plan)
    if (partial / MANIFEST_FILE).exists() or (partial / MANIFEST_FILE).is_symlink():
        return _adopt_completed_partial(
            partial=partial,
            target=target,
            plan=plan,
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_custody_root=output_custody_root,
        )
    artifacts = _read_completed_artifacts(partial=partial, plan=plan)
    limiter = SecRateLimiter(
        max_requests_per_second=config.max_requests_per_second
    )
    factory = transport_factory or _default_transport_factory(config)
    now = clock or (lambda: datetime.now(UTC))
    new_count = 0
    network_count = 0
    for batch_number in range(1, EXPECTED_BATCH_COUNT + 1):
        batch_items = tuple(
            item for item in plan.plan.items if item.batch_number == batch_number
        )
        for item in batch_items:
            if item.request_sequence in artifacts:
                continue
            if maximum_new_documents is not None and new_count >= maximum_new_documents:
                return StrongLeaderPullbackSecDocumentSourceResult(
                    output_root=partial,
                    status="in_progress",
                    completed_document_count=len(artifacts),
                    new_document_count=new_count,
                    network_request_count=network_count,
                )
            artifact = _download_item(
                partial=partial,
                item=item,
                config=config,
                implementation_revision=implementation_revision,
                transport=factory(limiter),
                observed_at=now(),
            )
            artifacts[item.request_sequence] = artifact
            new_count += 1
            network_count += 1 + artifact.retry_count
            if progress is not None:
                progress(artifact, len(artifacts), EXPECTED_REQUEST_COUNT)
    ordered = tuple(artifacts[index] for index in range(1, EXPECTED_REQUEST_COUNT + 1))
    manifest = _build_manifest(
        plan=plan,
        artifacts=ordered,
        completed_at=now(),
    )
    _write_exclusive(partial / MANIFEST_FILE, _json_bytes(manifest.model_dump(mode="json")))
    _fsync_directory(partial)
    partial.replace(target)
    _fsync_directory(target.parent)
    reread = read_strong_leader_pullback_sec_document_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackSecDocumentSourceResult(
        output_root=target,
        status="published",
        completed_document_count=EXPECTED_REQUEST_COUNT,
        new_document_count=new_count,
        network_request_count=network_count,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
    )


def read_strong_leader_pullback_sec_document_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackSecDocumentSourceResult:
    """Formally reread a completed source package and every document."""

    plan = read_strong_leader_pullback_sec_document_plan(
        output_root=plan_root,
        output_custody_root=plan_custody_root,
    )
    root = _validated_completed_output(output_root, output_custody_root)
    expected_names = {
        MANIFEST_FILE,
        *(f"request={index:06d}" for index in range(1, EXPECTED_REQUEST_COUNT + 1)),
    }
    if {item.name for item in root.iterdir()} != expected_names:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source package members differ"
        )
    path = root / MANIFEST_FILE
    _require_regular_file(path, 0o400, MAXIMUM_MANIFEST_BYTES)
    try:
        manifest = StrongLeaderPullbackSecDocumentSourceManifestV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source manifest is invalid"
        ) from exc
    if (
        manifest.plan_sha256 != plan.plan_sha256
        or manifest.plan_logical_fingerprint != plan.plan.logical_fingerprint
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source plan binding differs"
        )
    artifacts = tuple(
        _read_artifact_directory(
            directory=root / f"request={item.request_sequence:06d}",
            item=item,
        )
        for item in plan.plan.items
    )
    _validate_manifest_aggregates(manifest=manifest, artifacts=artifacts)
    raw = path.read_bytes()
    if raw != _json_bytes(manifest.model_dump(mode="json")):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source manifest bytes are not canonical"
        )
    return StrongLeaderPullbackSecDocumentSourceResult(
        output_root=root,
        status="already_present",
        completed_document_count=EXPECTED_REQUEST_COUNT,
        new_document_count=0,
        network_request_count=0,
        manifest=manifest,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _default_transport_factory(config: SecProviderConfig) -> TransportFactory:
    def factory(limiter: SecRateLimiter) -> BoundedSecTransport:
        return BoundedSecTransport(
            request_ceiling=1 + config.max_retries,
            rate_limiter=limiter,
            retry_policy=SecRetryPolicy(max_retries=config.max_retries),
        )

    return factory


def _prepare_partial(
    *, partial: Path, target: Path,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
) -> None:
    if partial.is_symlink():
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source partial is unsafe"
        )
    if not partial.exists():
        partial.mkdir(mode=0o700)
        _fsync_directory(partial.parent)
        return
    if (
        not partial.is_dir()
        or partial.resolve(strict=True) != partial
        or partial.parent != target.parent
        or partial.stat().st_uid != os.getuid()
        or stat.S_IMODE(partial.stat().st_mode) != 0o700
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source partial metadata differs"
        )
    valid_sequences = {item.request_sequence for item in plan.plan.items}
    for member in tuple(partial.iterdir()):
        request_match = _REQUEST_NAME_PATTERN.fullmatch(member.name)
        staging_match = _STAGING_NAME_PATTERN.fullmatch(member.name)
        if request_match is not None:
            if int(request_match.group("sequence")) not in valid_sequences:
                raise StrongLeaderPullbackSecDocumentSourceError(
                    "SEC document source partial contains an unknown request"
                )
            continue
        if member.name == MANIFEST_FILE:
            _require_regular_file(member, 0o400, MAXIMUM_MANIFEST_BYTES)
            continue
        if staging_match is not None:
            sequence = int(staging_match.group("sequence"))
            if (
                sequence not in valid_sequences
                or member.is_symlink()
                or not member.is_dir()
                or member.parent != partial
                or member.stat().st_uid != os.getuid()
                or stat.S_IMODE(member.stat().st_mode) != 0o700
                or member.resolve(strict=True) != member
            ):
                raise StrongLeaderPullbackSecDocumentSourceError(
                    "SEC document source staging member is unsafe"
                )
            shutil.rmtree(member)
            _fsync_directory(partial)
            continue
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source partial contains an unexpected member"
        )


def _adopt_completed_partial(
    *,
    partial: Path,
    target: Path,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    plan_root: Path,
    plan_custody_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackSecDocumentSourceResult:
    expected_names = {
        MANIFEST_FILE,
        *(f"request={index:06d}" for index in range(1, EXPECTED_REQUEST_COUNT + 1)),
    }
    if {item.name for item in partial.iterdir()} != expected_names:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "completed SEC document source partial members differ"
        )
    manifest_path = partial / MANIFEST_FILE
    try:
        manifest = StrongLeaderPullbackSecDocumentSourceManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "completed SEC document source partial manifest is invalid"
        ) from exc
    if (
        manifest.plan_sha256 != plan.plan_sha256
        or manifest.plan_logical_fingerprint != plan.plan.logical_fingerprint
        or manifest_path.read_bytes()
        != _json_bytes(manifest.model_dump(mode="json"))
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "completed SEC document source partial plan binding differs"
        )
    artifacts = tuple(
        _read_artifact_directory(
            directory=partial / f"request={item.request_sequence:06d}",
            item=item,
        )
        for item in plan.plan.items
    )
    _validate_manifest_aggregates(manifest=manifest, artifacts=artifacts)
    _fsync_directory(partial)
    partial.replace(target)
    _fsync_directory(target.parent)
    reread = read_strong_leader_pullback_sec_document_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackSecDocumentSourceResult(
        output_root=target,
        status="published",
        completed_document_count=EXPECTED_REQUEST_COUNT,
        new_document_count=0,
        network_request_count=0,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
    )


def _read_completed_artifacts(
    *, partial: Path, plan: StrongLeaderPullbackSecDocumentPlanResult
) -> dict[int, SecPrimaryDocumentArtifactV1]:
    items = {item.request_sequence: item for item in plan.plan.items}
    artifacts = {}
    for member in sorted(partial.iterdir(), key=lambda item: item.name):
        match = _REQUEST_NAME_PATTERN.fullmatch(member.name)
        if match is None:
            raise StrongLeaderPullbackSecDocumentSourceError(
                "SEC document source partial member differs"
            )
        sequence = int(match.group("sequence"))
        item = items.get(sequence)
        if item is None:
            raise StrongLeaderPullbackSecDocumentSourceError(
                "SEC document source partial sequence differs"
            )
        artifacts[sequence] = _read_artifact_directory(directory=member, item=item)
    return artifacts


def _download_item(
    *,
    partial: Path,
    item: SecPrimaryDocumentPlanItemV1,
    config: SecProviderConfig,
    implementation_revision: str,
    transport: _DocumentTransport,
    observed_at: datetime,
) -> SecPrimaryDocumentArtifactV1:
    final = partial / f"request={item.request_sequence:06d}"
    staging = partial / f".request={item.request_sequence:06d}.partial"
    if final.exists() or final.is_symlink() or staging.exists() or staging.is_symlink():
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source request target already exists"
        )
    staging.mkdir(mode=0o700)
    try:
        document = staging / DOCUMENT_FILE
        result = transport.download(
            item.request_url,
            document,
            user_agent=config.user_agent,
            timeout_seconds=config.request_timeout_seconds,
            max_bytes=item.maximum_response_bytes,
        )
        if (
            result.url != item.request_url
            or result.byte_count < 1
            or result.byte_count > item.maximum_response_bytes
            or result.content_type not in _ALLOWED_CONTENT_TYPES
            or result.retry_count > MAXIMUM_RETRIES_PER_REQUEST
            or document.stat().st_size != result.byte_count
            or _sha256_file(document) != result.sha256
        ):
            raise StrongLeaderPullbackSecDocumentSourceError(
                "SEC document source response differs from the plan"
            )
        document.chmod(0o400)
        values = {
            "implementation_revision": implementation_revision,
            "request_sequence": item.request_sequence,
            "batch_number": item.batch_number,
            "plan_item_fingerprint": _fingerprint(item.model_dump(mode="json")),
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
        provisional = SecPrimaryDocumentArtifactV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        artifact = SecPrimaryDocumentArtifactV1.model_validate(
            {
                **values,
                "logical_fingerprint": _fingerprint(
                    provisional.model_dump(
                        mode="json", exclude={"logical_fingerprint"}
                    )
                ),
            }
        )
        _write_exclusive(
            staging / ARTIFACT_FILE,
            _json_bytes(artifact.model_dump(mode="json")),
        )
        _fsync_directory(staging)
        staging.replace(final)
        _fsync_directory(partial)
        return artifact
    except Exception:
        if staging.exists() and not staging.is_symlink() and staging.parent == partial:
            shutil.rmtree(staging)
            _fsync_directory(partial)
        raise


def _read_artifact_directory(
    *, directory: Path, item: SecPrimaryDocumentPlanItemV1
) -> SecPrimaryDocumentArtifactV1:
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or directory.stat().st_uid != os.getuid()
        or stat.S_IMODE(directory.stat().st_mode) != 0o700
        or directory.resolve(strict=True) != directory
        or directory.name != f"request={item.request_sequence:06d}"
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document artifact directory differs"
        )
    if {member.name for member in directory.iterdir()} != {ARTIFACT_FILE, DOCUMENT_FILE}:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document artifact members differ"
        )
    artifact_path = directory / ARTIFACT_FILE
    document_path = directory / DOCUMENT_FILE
    _require_regular_file(artifact_path, 0o400, MAXIMUM_ARTIFACT_BYTES)
    _require_regular_file(document_path, 0o400, MAXIMUM_DOCUMENT_BYTES)
    try:
        artifact = SecPrimaryDocumentArtifactV1.model_validate_json(
            artifact_path.read_bytes()
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document artifact is invalid"
        ) from exc
    if (
        artifact.request_sequence != item.request_sequence
        or artifact.batch_number != item.batch_number
        or artifact.plan_item_fingerprint
        != _fingerprint(item.model_dump(mode="json"))
        or artifact.instrument_id != item.instrument_id
        or artifact.cik != item.cik
        or artifact.accession_number != item.accession_number
        or artifact.form != item.form
        or artifact.request_url != item.request_url
        or document_path.stat().st_size != artifact.byte_count
        or _sha256_file(document_path) != artifact.physical_sha256
        or artifact_path.read_bytes()
        != _json_bytes(artifact.model_dump(mode="json"))
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document artifact binding differs"
        )
    return artifact


def _build_manifest(
    *,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    artifacts: tuple[SecPrimaryDocumentArtifactV1, ...],
    completed_at: datetime,
) -> StrongLeaderPullbackSecDocumentSourceManifestV1:
    if len(artifacts) != EXPECTED_REQUEST_COUNT:
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source completion count differs"
        )
    types = Counter(item.content_type for item in artifacts)
    values = {
        "plan_sha256": plan.plan_sha256,
        "plan_logical_fingerprint": plan.plan.logical_fingerprint,
        "implementation_revisions": tuple(
            sorted({item.implementation_revision for item in artifacts})
        ),
        "first_observed_at": min(item.observed_at for item in artifacts),
        "completed_at": normalize_utc_datetime(completed_at),
        "external_request_count": sum(1 + item.retry_count for item in artifacts),
        "retry_count": sum(item.retry_count for item in artifacts),
        "total_document_bytes": sum(item.byte_count for item in artifacts),
        "content_type_counts": _ordered(types),
        "artifact_binding_fingerprint": _fingerprint(
            tuple(item.model_dump(mode="json") for item in artifacts)
        ),
    }
    provisional = StrongLeaderPullbackSecDocumentSourceManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecDocumentSourceManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_manifest_aggregates(
    *,
    manifest: StrongLeaderPullbackSecDocumentSourceManifestV1,
    artifacts: tuple[SecPrimaryDocumentArtifactV1, ...],
) -> None:
    if (
        tuple(item.request_sequence for item in artifacts)
        != tuple(range(1, EXPECTED_REQUEST_COUNT + 1))
        or manifest.implementation_revisions
        != tuple(sorted({item.implementation_revision for item in artifacts}))
        or manifest.first_observed_at != min(item.observed_at for item in artifacts)
        or manifest.external_request_count
        != sum(1 + item.retry_count for item in artifacts)
        or manifest.retry_count != sum(item.retry_count for item in artifacts)
        or manifest.total_document_bytes != sum(item.byte_count for item in artifacts)
        or manifest.content_type_counts
        != _ordered(Counter(item.content_type for item in artifacts))
        or manifest.artifact_binding_fingerprint
        != _fingerprint(tuple(item.model_dump(mode="json") for item in artifacts))
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source manifest aggregates differ"
        )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source paths must be absolute"
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
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source custody or target is unsafe"
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
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecDocumentSourceError(
            "SEC document source file metadata differs"
        )


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    return hashlib.sha256(_json_bytes(value).rstrip(b"\n")).hexdigest()
