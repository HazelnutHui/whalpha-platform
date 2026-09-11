"""Network-free census and exact source selection for Reconciled EOD Edition."""

from __future__ import annotations

import json
import multiprocessing
import os
import socket
import stat
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
)
from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageDisposition,
    ReconciledEodSourceCoverageSessionV1,
    ReconciledEodSourceCoverageV1,
    ReconciledEodSourceOrigin,
    seal_reconciled_eod_source_coverage,
)
from tip_api.persistence.parquet.eod_read import (
    CanonicalEodReadRepository,
    EodDatasetUnavailableError,
)
from tip_api.providers.massive.same_day_catchup import (
    SameDayCatchupError,
    canonical_json_bytes,
    file_sha256,
    read_catchup_approval_plan,
    read_grouped_daily_package,
)
from tip_api.services.historical_identity_source_custody import (
    HistoricalIdentitySourceCustodyError,
    read_identity_source_custody_at_data_root,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar
from tip_api.services.reconciled_eod_edition_batch import (
    MAXIMUM_SESSIONS_PER_BATCH,
    ReconciledEodEditionSourceV1,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
HISTORICAL_SESSIONS_ROOT = Path(
    "/home/hui/.local/state/trading-intelligence-platform/historical-backfill/"
    "five-year-2021-09-09--2026-09-09/sessions"
)
HISTORICAL_WARMUP_SESSIONS_ROOT = Path(
    "/home/hui/.local/state/trading-intelligence-platform/historical-backfill/"
    "warmup-2021-08-11--2021-09-08/sessions"
)
DAILY_SESSIONS_ROOT = Path(
    "/home/hui/.local/state/trading-intelligence-platform/automation/daily-eod/"
    "sessions"
)
LATER_REACQUISITION_SESSIONS_ROOT = Path(
    "/home/hui/.local/state/trading-intelligence-platform/"
    "reconciled-eod-source-reacquisition/sessions"
)
APPROVED_STATE_ROOT = Path(
    "/home/hui/.local/state/trading-intelligence-platform"
)
APPROVED_COVERAGE_BASE = APPROVED_STATE_ROOT / "reconciled-eod-source-coverage"
MAXIMUM_COVERAGE_WORKERS = 4


class ReconciledEodSourceCoverageError(RuntimeError):
    """Fail-closed error at the source-selection evidence boundary."""


@dataclass(frozen=True, slots=True)
class _SourceCandidateSpec:
    origin: ReconciledEodSourceOrigin
    package_path: Path
    plan_path: Path | None
    provenance: ReconciledEodSourceProvenance


@dataclass(frozen=True, slots=True)
class _ValidatedSourceCandidate:
    origin: ReconciledEodSourceOrigin
    provenance: ReconciledEodSourceProvenance
    source_observed_at: datetime
    package_manifest_sha256: str
    package_content_sha256: str
    binding_plan_sha256: str | None


@dataclass(frozen=True, slots=True)
class ReconciledEodSourceCoverageEvidence:
    coverage: ReconciledEodSourceCoverageV1
    path: Path
    file_sha256: str


@dataclass(frozen=True, slots=True)
class _CoverageJob:
    data_root: Path
    session_date: date


def assess_reconciled_eod_source_coverage(
    *,
    data_root: Path,
    evaluation_first_session: date,
    evaluation_last_session: date,
    warmup_first_session: date | None = None,
    warmup_last_session: date | None = None,
    created_at: datetime,
    calendar: MarketSessionCalendar | None = None,
    workers: int = 1,
) -> ReconciledEodSourceCoverageV1:
    """Formally select one exact source per XNYS session without any writes."""

    root = _validated_data_root(data_root)
    _validate_source_roots()
    if not 1 <= workers <= MAXIMUM_COVERAGE_WORKERS:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage workers must be between one and four"
        )
    session_calendar = calendar or ExchangeCalendar()
    if session_calendar.calendar_id != "XNYS":
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage requires XNYS"
        )
    if (warmup_first_session is None) != (warmup_last_session is None):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source warmup bounds must both be present"
        )
    if warmup_first_session is not None and not (
        warmup_first_session <= warmup_last_session < evaluation_first_session
    ):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source warmup interval is invalid"
        )
    coverage_first_session = warmup_first_session or evaluation_first_session
    sessions = session_calendar.sessions_in_range(
        coverage_first_session,
        evaluation_last_session,
    )
    if (
        not sessions
        or sessions[0] != coverage_first_session
        or sessions[-1] != evaluation_last_session
        or evaluation_first_session not in sessions
        or (
            warmup_last_session is not None
            and warmup_last_session not in sessions
        )
    ):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source interval is not an exact XNYS boundary"
        )
    jobs = tuple(_CoverageJob(data_root=root, session_date=item) for item in sessions)
    if workers == 1:
        with _network_prohibited():
            evidence = tuple(_assess_job(job) for job in jobs)
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_disable_network,
        ) as executor:
            evidence = tuple(executor.map(_assess_job, jobs))
    retained = sum(
        item.disposition
        == ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
        for item in evidence
    )
    later = sum(
        item.disposition
        == ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION
        for item in evidence
    )
    missing = sum(
        item.disposition == ReconciledEodSourceCoverageDisposition.MISSING
        for item in evidence
    )
    invalid = sum(
        item.disposition == ReconciledEodSourceCoverageDisposition.INVALID
        for item in evidence
    )
    conflict = sum(
        item.disposition == ReconciledEodSourceCoverageDisposition.CONFLICT
        for item in evidence
    )
    return seal_reconciled_eod_source_coverage(
        {
            "status": (
                "incomplete"
                if missing + invalid + conflict
                else "ready_for_candidate_build"
            ),
            "evaluation_first_session": evaluation_first_session,
            "evaluation_last_session": evaluation_last_session,
            "warmup_first_session": warmup_first_session,
            "warmup_last_session": warmup_last_session,
            "sessions": evidence,
            "target_session_count": len(sessions),
            "retained_original_session_count": retained,
            "later_reacquisition_session_count": later,
            "missing_session_count": missing,
            "invalid_session_count": invalid,
            "conflict_session_count": conflict,
            "created_at": created_at,
        }
    )


def _assess_job(job: _CoverageJob) -> ReconciledEodSourceCoverageSessionV1:
    _validate_source_roots()
    return _assess_session(
        data_root=job.data_root,
        repository=CanonicalEodReadRepository(job.data_root),
        session_date=job.session_date,
    )


def write_reconciled_eod_source_coverage(
    *,
    coverage: ReconciledEodSourceCoverageV1,
    path: Path,
) -> ReconciledEodSourceCoverageEvidence:
    """Write one immutable owner-read-only coverage artifact outside `/data`."""

    target = _validated_coverage_path(path, create_parent=True)
    if os.path.lexists(target):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage target already exists"
        )
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if os.path.lexists(staging):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage staging already exists"
        )
    payload = canonical_json_bytes(coverage.model_dump(mode="json"))
    created = False
    try:
        descriptor = os.open(
            staging,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
        )
        created = True
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        staging.chmod(0o400)
        try:
            os.link(staging, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise ReconciledEodSourceCoverageError(
                "reconciled EOD source coverage target already exists"
            ) from exc
        staging.unlink()
        _fsync_directory(target.parent)
    except Exception:
        if created and staging.exists() and not staging.is_symlink():
            staging.unlink()
        raise
    return read_reconciled_eod_source_coverage(
        path=target,
        expected_file_sha256=file_sha256(target),
    )


def read_reconciled_eod_source_coverage(
    *,
    path: Path,
    expected_file_sha256: str | None = None,
) -> ReconciledEodSourceCoverageEvidence:
    """Formally reread one immutable coverage artifact and optional byte hash."""

    target = _validated_coverage_path(path, create_parent=False)
    if target.is_symlink() or not target.is_file():
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage artifact is unavailable"
        )
    metadata = target.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage artifact custody differs"
        )
    observed_sha256 = file_sha256(target)
    if expected_file_sha256 is not None and observed_sha256 != expected_file_sha256:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage file hash differs"
        )
    try:
        coverage = ReconciledEodSourceCoverageV1.model_validate_json(
            target.read_bytes()
        )
    except Exception as exc:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage artifact is invalid"
        ) from exc
    return ReconciledEodSourceCoverageEvidence(
        coverage=coverage,
        path=target,
        file_sha256=observed_sha256,
    )


def resolve_reconciled_eod_batch_sources(
    *,
    coverage: ReconciledEodSourceCoverageV1,
    data_root: Path,
    session_dates: tuple[date, ...],
) -> tuple[ReconciledEodEditionSourceV1, ...]:
    """Reread exact selected packages for one bounded candidate-build batch."""

    root = _validated_data_root(data_root)
    _validate_source_roots()
    if coverage.status != "ready_for_candidate_build":
        raise ReconciledEodSourceCoverageError(
            "incomplete source coverage cannot feed candidate construction"
        )
    if (
        not 1 <= len(session_dates) <= MAXIMUM_SESSIONS_PER_BATCH
        or session_dates != tuple(sorted(set(session_dates)))
    ):
        raise ReconciledEodSourceCoverageError(
            "candidate source sessions must be 1–40 unique ordered dates"
        )
    evidence_by_date = {item.session_date: item for item in coverage.sessions}
    result: list[ReconciledEodEditionSourceV1] = []
    with _network_prohibited():
        for session_date in session_dates:
            evidence = evidence_by_date.get(session_date)
            if (
                evidence is None
                or evidence.selected_source_origin is None
                or evidence.selected_source_provenance is None
                or evidence.canonical_eod_fingerprint is None
                or evidence.canonical_identity_fingerprint is None
            ):
                raise ReconciledEodSourceCoverageError(
                    "candidate source session is absent from selected coverage"
                )
            spec = next(
                item
                for item in _candidate_specs(session_date)
                if item.origin == evidence.selected_source_origin
            )
            selected = _validate_candidate(
                spec=spec,
                data_root=root,
                session_date=session_date,
                canonical_eod_fingerprint=evidence.canonical_eod_fingerprint,
                canonical_identity_fingerprint=(
                    evidence.canonical_identity_fingerprint
                ),
            )
            if (
                selected.provenance != evidence.selected_source_provenance
                or selected.source_observed_at
                != evidence.selected_source_observed_at
                or selected.package_manifest_sha256
                != evidence.selected_package_manifest_sha256
                or selected.package_content_sha256
                != evidence.selected_package_content_sha256
                or selected.binding_plan_sha256
                != evidence.selected_binding_plan_sha256
            ):
                raise ReconciledEodSourceCoverageError(
                    "selected source package changed after coverage sealing"
                )
            result.append(
                ReconciledEodEditionSourceV1(
                    session_date=session_date,
                    package_path=spec.package_path,
                    source_provenance=selected.provenance,
                )
            )
    return tuple(result)


def _assess_session(
    *,
    data_root: Path,
    repository: CanonicalEodReadRepository,
    session_date: date,
) -> ReconciledEodSourceCoverageSessionV1:
    specs, discovery_reasons = _discover_candidates(session_date)
    origins = tuple(sorted({item.origin for item in specs}, key=lambda item: item.value))
    try:
        integrity = repository.inspect_session(session_date)
    except (OSError, ValueError, EodDatasetUnavailableError):
        return _unselected(
            session_date=session_date,
            disposition=ReconciledEodSourceCoverageDisposition.INVALID,
            origins=origins,
            reasons=(*discovery_reasons, "canonical_eod_unavailable"),
        )
    try:
        identity_source = read_identity_source_custody_at_data_root(
            data_root=data_root,
            provider="massive_stocks_basic",
            session_date=session_date,
        )
    except (OSError, ValueError, HistoricalIdentitySourceCustodyError):
        return _unselected(
            session_date=session_date,
            disposition=ReconciledEodSourceCoverageDisposition.INVALID,
            origins=origins,
            reasons=(*discovery_reasons, "identity_source_custody_unavailable"),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )
    if (
        identity_source.manifest.canonical_snapshot_fingerprint
        != integrity.identity_snapshot_fingerprint
    ):
        return _unselected(
            session_date=session_date,
            disposition=ReconciledEodSourceCoverageDisposition.INVALID,
            origins=origins,
            reasons=(*discovery_reasons, "identity_source_binding_differs"),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )

    valid: list[_ValidatedSourceCandidate] = []
    validation_reasons = list(discovery_reasons)
    for spec in specs:
        try:
            valid.append(
                _validate_candidate(
                    spec=spec,
                    data_root=data_root,
                    session_date=session_date,
                    canonical_eod_fingerprint=integrity.content_fingerprint,
                    canonical_identity_fingerprint=(
                        integrity.identity_snapshot_fingerprint
                    ),
                )
            )
        except (
            OSError,
            ValueError,
            SameDayCatchupError,
            ReconciledEodSourceCoverageError,
        ):
            validation_reasons.append(f"{spec.origin.value}_source_binding_invalid")

    if validation_reasons:
        return _unselected(
            session_date=session_date,
            disposition=(
                ReconciledEodSourceCoverageDisposition.CONFLICT
                if valid
                else ReconciledEodSourceCoverageDisposition.INVALID
            ),
            origins=origins,
            reasons=tuple(validation_reasons),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )
    retained = tuple(
        item
        for item in valid
        if item.provenance == ReconciledEodSourceProvenance.RETAINED_ORIGINAL
    )
    later = tuple(
        item
        for item in valid
        if item.provenance == ReconciledEodSourceProvenance.LATER_REACQUISITION
    )
    if len(retained) > 1 or (not retained and len(later) > 1):
        return _unselected(
            session_date=session_date,
            disposition=ReconciledEodSourceCoverageDisposition.CONFLICT,
            origins=origins,
            reasons=("multiple_eligible_source_packages",),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )
    if retained:
        return _selected(
            session_date=session_date,
            candidate=retained[0],
            origins=origins,
            disposition=(
                ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
            ),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )
    if later:
        return _selected(
            session_date=session_date,
            candidate=later[0],
            origins=origins,
            disposition=(
                ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION
            ),
            canonical_eod_fingerprint=integrity.content_fingerprint,
            canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
        )
    return _unselected(
        session_date=session_date,
        disposition=ReconciledEodSourceCoverageDisposition.MISSING,
        origins=origins,
        reasons=("grouped_daily_source_package_missing",),
        canonical_eod_fingerprint=integrity.content_fingerprint,
        canonical_identity_fingerprint=integrity.identity_snapshot_fingerprint,
    )


def _discover_candidates(
    session_date: date,
) -> tuple[tuple[_SourceCandidateSpec, ...], tuple[str, ...]]:
    possible = _candidate_specs(session_date)
    result: list[_SourceCandidateSpec] = []
    reasons: list[str] = []
    for spec in possible:
        if not os.path.lexists(spec.package_path):
            continue
        if spec.package_path.is_symlink() or not spec.package_path.is_dir():
            result.append(spec)
            reasons.append(f"{spec.origin.value}_source_package_path_invalid")
            continue
        package_type = _declared_package_type(spec.package_path)
        if (
            spec.origin == ReconciledEodSourceOrigin.DAILY_AUTOMATION
            and package_type not in {"grouped_daily", "invalid"}
        ):
            continue
        result.append(spec)
        if package_type != "grouped_daily":
            reasons.append(f"{spec.origin.value}_source_package_manifest_invalid")
    return tuple(result), tuple(sorted(set(reasons)))


def _candidate_specs(session_date: date) -> tuple[_SourceCandidateSpec, ...]:
    session_component = f"session_date={session_date.isoformat()}"
    return (
        _SourceCandidateSpec(
            origin=ReconciledEodSourceOrigin.HISTORICAL_BACKFILL,
            package_path=(
                HISTORICAL_SESSIONS_ROOT
                / session_component
                / "eod-acquisition-package"
            ),
            plan_path=(
                HISTORICAL_SESSIONS_ROOT
                / session_component
                / "eod-canonical-apply-plan.json"
            ),
            provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        ),
        _SourceCandidateSpec(
            origin=ReconciledEodSourceOrigin.HISTORICAL_WARMUP,
            package_path=(
                HISTORICAL_WARMUP_SESSIONS_ROOT
                / session_component
                / "eod-acquisition-package"
            ),
            plan_path=(
                HISTORICAL_WARMUP_SESSIONS_ROOT
                / session_component
                / "eod-canonical-apply-plan.json"
            ),
            provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        ),
        _SourceCandidateSpec(
            origin=ReconciledEodSourceOrigin.DAILY_AUTOMATION,
            package_path=(
                DAILY_SESSIONS_ROOT / session_component / "acquisition-package"
            ),
            plan_path=(
                DAILY_SESSIONS_ROOT / session_component / "canonical-apply-plan.json"
            ),
            provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        ),
        _SourceCandidateSpec(
            origin=ReconciledEodSourceOrigin.LATER_REACQUISITION,
            package_path=(
                LATER_REACQUISITION_SESSIONS_ROOT
                / session_component
                / "eod-acquisition-package"
            ),
            plan_path=None,
            provenance=ReconciledEodSourceProvenance.LATER_REACQUISITION,
        ),
    )


def _validate_candidate(
    *,
    spec: _SourceCandidateSpec,
    data_root: Path,
    session_date: date,
    canonical_eod_fingerprint: str,
    canonical_identity_fingerprint: str,
) -> _ValidatedSourceCandidate:
    package = read_grouped_daily_package(
        package_path=spec.package_path,
        expected_session=session_date,
    )
    if spec.provenance == ReconciledEodSourceProvenance.LATER_REACQUISITION:
        return _ValidatedSourceCandidate(
            origin=spec.origin,
            provenance=spec.provenance,
            source_observed_at=package.manifest.fetched_at,
            package_manifest_sha256=package.package_manifest_sha256,
            package_content_sha256=package.manifest.package_content_sha256,
            binding_plan_sha256=None,
        )
    if spec.plan_path is None or not spec.plan_path.is_file():
        raise ReconciledEodSourceCoverageError(
            "retained source canonical binding plan is unavailable"
        )
    plan_sha256 = file_sha256(spec.plan_path)
    plan = read_catchup_approval_plan(
        plan_path=spec.plan_path,
        approved_plan_sha256=plan_sha256,
        expected_operation="eod",
        expected_session=session_date,
        expected_data_root=data_root,
    )
    if (
        Path(plan.fetch_package_path) != spec.package_path
        or plan.fetch_package_manifest_sha256 != package.package_manifest_sha256
        or plan.fetch_package_content_sha256
        != package.manifest.package_content_sha256
        or plan.content_fingerprints.get("eod") != canonical_eod_fingerprint
        or plan.same_day_identity_snapshot_fingerprint
        != canonical_identity_fingerprint
    ):
        raise ReconciledEodSourceCoverageError(
            "retained source canonical binding differs"
        )
    return _ValidatedSourceCandidate(
        origin=spec.origin,
        provenance=spec.provenance,
        source_observed_at=package.manifest.fetched_at,
        package_manifest_sha256=package.package_manifest_sha256,
        package_content_sha256=package.manifest.package_content_sha256,
        binding_plan_sha256=plan_sha256,
    )


def _selected(
    *,
    session_date: date,
    candidate: _ValidatedSourceCandidate,
    origins: tuple[ReconciledEodSourceOrigin, ...],
    disposition: ReconciledEodSourceCoverageDisposition,
    canonical_eod_fingerprint: str,
    canonical_identity_fingerprint: str,
) -> ReconciledEodSourceCoverageSessionV1:
    return ReconciledEodSourceCoverageSessionV1(
        session_date=session_date,
        disposition=disposition,
        observed_candidate_count=len(origins),
        observed_candidate_origins=origins,
        canonical_eod_fingerprint=canonical_eod_fingerprint,
        canonical_identity_fingerprint=canonical_identity_fingerprint,
        selected_source_origin=candidate.origin,
        selected_source_provenance=candidate.provenance,
        selected_source_observed_at=candidate.source_observed_at,
        selected_package_manifest_sha256=candidate.package_manifest_sha256,
        selected_package_content_sha256=candidate.package_content_sha256,
        selected_binding_plan_sha256=candidate.binding_plan_sha256,
    )


def _unselected(
    *,
    session_date: date,
    disposition: ReconciledEodSourceCoverageDisposition,
    origins: tuple[ReconciledEodSourceOrigin, ...],
    reasons: tuple[str, ...],
    canonical_eod_fingerprint: str | None = None,
    canonical_identity_fingerprint: str | None = None,
) -> ReconciledEodSourceCoverageSessionV1:
    return ReconciledEodSourceCoverageSessionV1(
        session_date=session_date,
        disposition=disposition,
        observed_candidate_count=len(origins),
        observed_candidate_origins=origins,
        canonical_eod_fingerprint=canonical_eod_fingerprint,
        canonical_identity_fingerprint=canonical_identity_fingerprint,
        reason_codes=tuple(sorted(set(reasons))),
    )


def _declared_package_type(package_path: Path) -> str:
    manifest_path = package_path / "package.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return "invalid"
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "invalid"
    package_type = value.get("package_type") if isinstance(value, dict) else None
    return package_type if isinstance(package_type, str) else "invalid"


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD canonical data root is unavailable"
        )
    try:
        resolved = path.resolve(strict=True)
        approved = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD canonical data root is unavailable"
        ) from exc
    if resolved != path or resolved != approved:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD canonical data root is not approved"
        )
    return resolved


def _validate_source_roots() -> None:
    for root in (
        HISTORICAL_SESSIONS_ROOT,
        HISTORICAL_WARMUP_SESSIONS_ROOT,
        DAILY_SESSIONS_ROOT,
        LATER_REACQUISITION_SESSIONS_ROOT,
    ):
        if not os.path.lexists(root):
            continue
        metadata = root.lstat()
        if (
            not root.is_absolute()
            or root.is_symlink()
            or root.resolve(strict=True) != root
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise ReconciledEodSourceCoverageError(
                "reconciled EOD source root custody differs"
            )


def _validated_coverage_path(path: Path, *, create_parent: bool) -> Path:
    if (
        not path.is_absolute()
        or path.name in {"", ".", ".."}
        or path.suffix != ".json"
        or path.is_symlink()
    ):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage path is invalid"
        )
    temporary = Path("/tmp").resolve(strict=True)
    if path.parent == APPROVED_COVERAGE_BASE:
        _owner_only_directory(APPROVED_STATE_ROOT)
        if create_parent and not APPROVED_COVERAGE_BASE.exists():
            APPROVED_COVERAGE_BASE.mkdir(mode=0o700)
            _fsync_directory(APPROVED_COVERAGE_BASE.parent)
        parent = _owner_only_directory(APPROVED_COVERAGE_BASE)
    else:
        if not path.parent.is_dir() or path.parent.is_symlink():
            raise ReconciledEodSourceCoverageError(
                "reconciled EOD source coverage parent is unavailable"
            )
        parent = path.parent.resolve(strict=True)
        if temporary not in parent.parents:
            raise ReconciledEodSourceCoverageError(
                "reconciled EOD source coverage path is outside approved custody"
            )
        _owner_only_directory(parent)
    if path.parent.resolve(strict=True) != parent:
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage parent differs"
        )
    return parent / path.name


def _owner_only_directory(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage directory is unavailable"
        )
    resolved = path.resolve(strict=True)
    metadata = resolved.stat()
    if (
        resolved != path
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ReconciledEodSourceCoverageError(
            "reconciled EOD source coverage directory must be owner-only"
        )
    return resolved


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    _disable_network()
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]


def _disable_network() -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise ReconciledEodSourceCoverageError(
            "network is disabled during reconciled EOD source coverage"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
