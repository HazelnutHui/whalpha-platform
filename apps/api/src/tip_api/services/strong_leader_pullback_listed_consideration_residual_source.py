"""One-document custody for the listed-consideration residual plan."""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import (
    BoundedSecTransport,
    SecRateLimiter,
    SecRetryPolicy,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source_plan as residual_plan,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_source as base,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-listed-consideration-residual-source/1.0"
)
MANIFEST_FILE = "manifest.json"
EXPECTED_REQUEST_SEQUENCE = 174
EXPECTED_DOCUMENT_COUNT = 1
MAXIMUM_MANIFEST_BYTES = 64 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SOURCE_NAME_PATTERN = r"^source=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackListedConsiderationResidualSourceError(RuntimeError):
    """Raised when the residual source package cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackListedConsiderationResidualSourceManifestV1(
    _FrozenModel
):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-residual-source/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    observed_at: datetime
    completed_at: datetime
    planned_document_count: Literal[1] = EXPECTED_DOCUMENT_COUNT
    completed_document_count: Literal[1] = EXPECTED_DOCUMENT_COUNT
    external_request_count: int = Field(ge=1)
    retry_count: int = Field(ge=0, le=base.MAXIMUM_RETRIES_PER_REQUEST)
    total_document_bytes: int = Field(ge=1, le=base.MAXIMUM_DOCUMENT_BYTES)
    content_type: str
    artifact_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    credential_material_retained: Literal[False] = False
    complete_source_custody: Literal[True] = True
    document_content_interpreted: Literal[False] = False
    consideration_security_identity_assignment_count: Literal[0] = 0
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("observed_at", "completed_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "StrongLeaderPullbackListedConsiderationResidualSourceManifestV1":
        if (
            self.observed_at > self.completed_at
            or self.external_request_count != 1 + self.retry_count
            or self.content_type not in base._ALLOWED_CONTENT_TYPES
            or self.logical_fingerprint
            != residual_plan._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual source manifest differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationResidualSourceResult:
    output_root: Path
    status: Literal["published", "already_present"]
    new_document_count: int
    network_request_count: int
    manifest: StrongLeaderPullbackListedConsiderationResidualSourceManifestV1
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class _DownloadDecision:
    request_sequence: int
    target_instrument_id: UUID
    proposed_consideration_instrument_id: UUID
    proposed_cik: str
    registration_accession_number: str
    registration_document_url: str
    logical_fingerprint: str


TransportFactory = base.TransportFactory
Clock = Callable[[], datetime]
ProgressCallback = Callable[[base.ListedConsiderationDocumentArtifactV1], None]


def acquire_strong_leader_pullback_listed_consideration_residual_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    config: SecProviderConfig,
    implementation_revision: str,
    transport_factory: TransportFactory | None = None,
    clock: Clock | None = None,
    progress: ProgressCallback | None = None,
) -> StrongLeaderPullbackListedConsiderationResidualSourceResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source revision is invalid"
        )
    if (
        config.max_requests_per_second > Decimal(base.MAXIMUM_REQUESTS_PER_SECOND)
        or config.max_retries > base.MAXIMUM_RETRIES_PER_REQUEST
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source configuration exceeds policy"
        )
    reader = (
        residual_plan.read_strong_leader_pullback_listed_consideration_residual_source_plan
    )
    plan = reader(
        output_root=plan_root,
        output_custody_root=plan_custody_root,
    )
    decision = _planned_download(plan)
    adapter = _download_adapter(decision)
    target = _validated_output_target(output_root, output_custody_root)
    partial = target.parent / f".{target.name}.partial"
    if target.exists() or target.is_symlink():
        if partial.exists() or partial.is_symlink():
            raise StrongLeaderPullbackListedConsiderationResidualSourceError(
                "completed and partial residual sources coexist"
            )
        existing = read_strong_leader_pullback_listed_consideration_residual_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=target,
            output_custody_root=output_custody_root,
        )
        return StrongLeaderPullbackListedConsiderationResidualSourceResult(
            output_root=target,
            status="already_present",
            new_document_count=0,
            network_request_count=0,
            manifest=existing.manifest,
            manifest_sha256=existing.manifest_sha256,
        )
    _prepare_partial(partial)
    if (partial / MANIFEST_FILE).exists() or (partial / MANIFEST_FILE).is_symlink():
        return _adopt_completed_partial(
            partial=partial,
            target=target,
            plan=plan,
            adapter=adapter,
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_custody_root=output_custody_root,
        )
    request = partial / f"request={EXPECTED_REQUEST_SEQUENCE:06d}"
    if request.exists() or request.is_symlink():
        artifact = base._read_artifact_directory(request, adapter)
        new_count = 0
        network_count = 0
    else:
        limiter = SecRateLimiter(
            max_requests_per_second=config.max_requests_per_second
        )
        factory = transport_factory or _default_transport_factory(config)
        now = clock or (lambda: datetime.now(UTC))
        artifact = base._download_decision(
            partial=partial,
            decision=adapter,
            config=config,
            implementation_revision=implementation_revision,
            transport=factory(limiter),
            observed_at=now(),
        )
        new_count = 1
        network_count = 1 + artifact.retry_count
        if progress is not None:
            progress(artifact)
    now = clock or (lambda: datetime.now(UTC))
    manifest = _build_manifest(
        plan=plan,
        artifact=artifact,
        completed_at=now(),
    )
    manifest_path = partial / MANIFEST_FILE
    if manifest_path.exists() or manifest_path.is_symlink():
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source manifest target exists"
        )
    base._write_exclusive(
        manifest_path,
        residual_plan._json_bytes(manifest.model_dump(mode="json")),
    )
    base._fsync_directory(partial)
    partial.replace(target)
    base._fsync_directory(target.parent)
    reread = read_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackListedConsiderationResidualSourceResult(
        output_root=target,
        status="published",
        new_document_count=new_count,
        network_request_count=network_count,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
    )


def read_strong_leader_pullback_listed_consideration_residual_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackListedConsiderationResidualSourceResult:
    reader = (
        residual_plan.read_strong_leader_pullback_listed_consideration_residual_source_plan
    )
    plan = reader(
        output_root=plan_root,
        output_custody_root=plan_custody_root,
    )
    adapter = _download_adapter(_planned_download(plan))
    root = _validated_completed_output(output_root, output_custody_root)
    expected = {MANIFEST_FILE, f"request={EXPECTED_REQUEST_SEQUENCE:06d}"}
    if {item.name for item in root.iterdir()} != expected:
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source package members differ"
        )
    manifest_path = root / MANIFEST_FILE
    base._require_regular_file(
        manifest_path, 0o400, MAXIMUM_MANIFEST_BYTES
    )
    raw = manifest_path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationResidualSourceManifestV1
        manifest = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source manifest is invalid"
        ) from exc
    artifact = base._read_artifact_directory(
        root / f"request={EXPECTED_REQUEST_SEQUENCE:06d}", adapter
    )
    if (
        manifest.plan_report_sha256 != plan.report_sha256
        or manifest.plan_logical_fingerprint != plan.report.logical_fingerprint
        or raw != residual_plan._json_bytes(manifest.model_dump(mode="json"))
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source plan binding differs"
        )
    _validate_manifest(manifest, artifact)
    return StrongLeaderPullbackListedConsiderationResidualSourceResult(
        output_root=root,
        status="already_present",
        new_document_count=0,
        network_request_count=0,
        manifest=manifest,
        manifest_sha256=residual_plan._sha256_bytes(raw),
    )


def _planned_download(
    plan: residual_plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanResult,
) -> residual_plan.ListedConsiderationResidualSourcePlanDecisionV1:
    matches = tuple(
        item
        for item in plan.report.decisions
        if item.new_source_request_count == 1
    )
    if (
        plan.report.planned_source_document_count != EXPECTED_DOCUMENT_COUNT
        or len(matches) != 1
        or matches[0].request_sequence != EXPECTED_REQUEST_SEQUENCE
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source plan population differs"
        )
    return matches[0]


def _download_adapter(
    decision: residual_plan.ListedConsiderationResidualSourcePlanDecisionV1,
) -> _DownloadDecision:
    if (
        decision.replacement_registration_accession_number is None
        or decision.replacement_registration_document_url is None
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source plan document differs"
        )
    return _DownloadDecision(
        request_sequence=decision.request_sequence,
        target_instrument_id=decision.target_instrument_id,
        proposed_consideration_instrument_id=(
            decision.proposed_consideration_instrument_id
        ),
        proposed_cik=decision.proposed_cik,
        registration_accession_number=(
            decision.replacement_registration_accession_number
        ),
        registration_document_url=decision.replacement_registration_document_url,
        logical_fingerprint=decision.logical_fingerprint,
    )


def _prepare_partial(partial: Path) -> None:
    if partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source partial custody is unsafe"
        )
    if not partial.exists():
        partial.mkdir(mode=0o700)
        base._fsync_directory(partial.parent)
        return
    if (
        not partial.is_dir()
        or partial.stat().st_uid != os.getuid()
        or stat.S_IMODE(partial.stat().st_mode) != 0o700
        or partial.resolve(strict=True) != partial
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source partial custody is unsafe"
        )
    allowed = {
        MANIFEST_FILE,
        f"request={EXPECTED_REQUEST_SEQUENCE:06d}",
        f".request={EXPECTED_REQUEST_SEQUENCE:06d}.partial",
    }
    for member in tuple(partial.iterdir()):
        if member.name not in allowed:
            raise StrongLeaderPullbackListedConsiderationResidualSourceError(
                "residual source partial members differ"
            )
        if member.name.startswith(".request="):
            if member.is_symlink() or not member.is_dir():
                raise StrongLeaderPullbackListedConsiderationResidualSourceError(
                    "residual source staging member is unsafe"
                )
            shutil.rmtree(member)
            base._fsync_directory(partial)


def _adopt_completed_partial(
    *,
    partial: Path,
    target: Path,
    plan: residual_plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanResult,
    adapter: _DownloadDecision,
    plan_root: Path,
    plan_custody_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackListedConsiderationResidualSourceResult:
    expected = {MANIFEST_FILE, f"request={EXPECTED_REQUEST_SEQUENCE:06d}"}
    if {item.name for item in partial.iterdir()} != expected:
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "completed residual partial members differ"
        )
    manifest_path = partial / MANIFEST_FILE
    base._require_regular_file(manifest_path, 0o400, MAXIMUM_MANIFEST_BYTES)
    raw = manifest_path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationResidualSourceManifestV1
        manifest = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "completed residual partial manifest is invalid"
        ) from exc
    artifact = base._read_artifact_directory(
        partial / f"request={EXPECTED_REQUEST_SEQUENCE:06d}", adapter
    )
    if (
        manifest.plan_report_sha256 != plan.report_sha256
        or manifest.plan_logical_fingerprint != plan.report.logical_fingerprint
        or raw != residual_plan._json_bytes(manifest.model_dump(mode="json"))
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "completed residual partial plan binding differs"
        )
    _validate_manifest(manifest, artifact)
    base._fsync_directory(partial)
    partial.replace(target)
    base._fsync_directory(target.parent)
    reread = read_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackListedConsiderationResidualSourceResult(
        output_root=target,
        status="published",
        new_document_count=0,
        network_request_count=0,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
    )


def _build_manifest(
    *,
    plan: residual_plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanResult,
    artifact: base.ListedConsiderationDocumentArtifactV1,
    completed_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualSourceManifestV1:
    values = {
        "plan_report_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "implementation_revision": artifact.implementation_revision,
        "observed_at": artifact.observed_at,
        "completed_at": normalize_utc_datetime(completed_at),
        "external_request_count": 1 + artifact.retry_count,
        "retry_count": artifact.retry_count,
        "total_document_bytes": artifact.byte_count,
        "content_type": artifact.content_type,
        "artifact_fingerprint": artifact.logical_fingerprint,
    }
    provisional = (
        StrongLeaderPullbackListedConsiderationResidualSourceManifestV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
    )
    model = StrongLeaderPullbackListedConsiderationResidualSourceManifestV1
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_manifest(
    manifest: StrongLeaderPullbackListedConsiderationResidualSourceManifestV1,
    artifact: base.ListedConsiderationDocumentArtifactV1,
) -> None:
    if (
        manifest.implementation_revision != artifact.implementation_revision
        or manifest.observed_at != artifact.observed_at
        or manifest.completed_at < artifact.observed_at
        or manifest.external_request_count != 1 + artifact.retry_count
        or manifest.retry_count != artifact.retry_count
        or manifest.total_document_bytes != artifact.byte_count
        or manifest.content_type != artifact.content_type
        or manifest.artifact_fingerprint != artifact.logical_fingerprint
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source manifest aggregates differ"
        )


def _default_transport_factory(config: SecProviderConfig) -> TransportFactory:
    def factory(limiter: SecRateLimiter) -> BoundedSecTransport:
        return BoundedSecTransport(
            request_ceiling=1 + config.max_retries,
            rate_limiter=limiter,
            retry_policy=SecRetryPolicy(max_retries=config.max_retries),
        )

    return factory


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source paths must be absolute"
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
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source custody or target is unsafe"
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
        raise StrongLeaderPullbackListedConsiderationResidualSourceError(
            "residual source output is unavailable or unsafe"
        )
    return target
