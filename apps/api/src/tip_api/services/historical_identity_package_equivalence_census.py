"""Read-only census of retained Identity packages against accepted snapshots."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import socket
import stat
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Literal

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.instrument_master import (
    InstrumentMasterSnapshotCorruptionError,
    InstrumentMasterSnapshotReadResult,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.same_day_catchup import (
    FetchPackageManifestV1,
    SameDayCatchupError,
)
from tip_api.services.historical_universe_membership_shadow import (
    HistoricalUniverseMembershipShadowError,
    inspect_historical_identity_package_equivalence,
)

CENSUS_CONTRACT_VERSION = "1.0"
MAXIMUM_CENSUS_WORKERS = 4

CandidateStatus = Literal[
    "exact_equivalent",
    "identity_snapshot_mismatch",
    "package_custody_failed",
]
CensusScope = Literal["full_canonical_index", "bounded_sample"]
SessionStatus = Literal[
    "missing_source",
    "package_custody_failed",
    "identity_snapshot_mismatch",
    "exact_equivalent",
    "duplicate_source_review_required",
    "canonical_identity_unavailable",
]


class HistoricalIdentityPackageEquivalenceCensusError(RuntimeError):
    """Fail-closed error at the census discovery or output boundary."""


@dataclass(frozen=True, slots=True)
class HistoricalIdentityPackageCandidateResult:
    source_locator_sha256: str
    package_manifest_sha256: str
    package_content_sha256: str
    fetched_at: str
    status: CandidateStatus
    rebuilt_instrument_fingerprint: str | None
    rebuilt_identity_fingerprint: str | None
    rebuilt_resolver_fingerprint: str | None
    instrument_match: bool | None
    identity_match: bool | None
    resolver_match: bool | None


@dataclass(frozen=True, slots=True)
class HistoricalIdentityPackageSessionResult:
    session_date: str
    status: SessionStatus
    candidate_count: int
    custody_valid_candidate_count: int
    exact_equivalent_candidate_count: int
    canonical_snapshot_fingerprint: str | None
    canonical_instrument_fingerprint: str | None
    canonical_identity_fingerprint: str | None
    canonical_resolver_fingerprint: str | None
    candidates: tuple[HistoricalIdentityPackageCandidateResult, ...]


@dataclass(frozen=True, slots=True)
class HistoricalIdentityPackageEquivalenceCensusResult:
    contract_version: str
    scope: CensusScope
    evaluated_at: str
    canonical_session_count: int
    evaluated_session_count: int
    worker_count: int
    canonical_session_index_fingerprint: str
    package_root_count: int
    discovered_identity_package_count: int
    ignored_non_identity_package_count: int
    unroutable_manifest_count: int
    outside_canonical_session_package_count: int
    discovered_package_inventory_fingerprint: str
    exact_equivalent_session_count: int
    duplicate_source_session_count: int
    status_counts: tuple[tuple[str, int], ...]
    sessions: tuple[HistoricalIdentityPackageSessionResult, ...]
    external_request_count: int = 0
    canonical_data_write_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _DiscoveredIdentityPackage:
    path: Path
    manifest: FetchPackageManifestV1
    manifest_sha256: str
    source_locator_sha256: str


@dataclass(frozen=True, slots=True)
class _PackageDiscovery:
    packages: tuple[_DiscoveredIdentityPackage, ...]
    ignored_non_identity_package_count: int
    unroutable_manifest_count: int
    inventory_fingerprint: str


def run_historical_identity_package_equivalence_census(
    *,
    data_root: Path,
    package_roots: tuple[Path, ...],
    evaluated_at: datetime,
    sample_sessions: tuple[date, ...] | None = None,
    workers: int = 1,
    progress: Callable[[int, int, date, SessionStatus], None] | None = None,
) -> HistoricalIdentityPackageEquivalenceCensusResult:
    """Formally compare every routed retained package with same-day Identity."""

    evaluated_at = normalize_utc_datetime(evaluated_at)
    if not 1 <= workers <= MAXIMUM_CENSUS_WORKERS:
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "census workers must be between one and four"
        )
    root = data_root.resolve(strict=True)
    resolved_package_roots = _validate_package_roots(package_roots)
    discovery = _discover_packages(resolved_package_roots)
    canonical_sessions = CanonicalEodReadRepository(root).list_session_index()
    if not canonical_sessions:
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "canonical EOD session index is empty"
        )
    canonical_session_set = set(canonical_sessions)
    evaluated_sessions = _evaluated_sessions(
        canonical_sessions=canonical_sessions,
        sample_sessions=sample_sessions,
    )
    packages_by_session: dict[date, list[_DiscoveredIdentityPackage]] = {}
    outside_canonical_count = 0
    for package in discovery.packages:
        session = package.manifest.session_date
        if session not in canonical_session_set:
            outside_canonical_count += 1
            continue
        packages_by_session.setdefault(session, []).append(package)

    jobs = tuple(
        (
            session,
            tuple(
                sorted(
                    packages_by_session.get(session, ()),
                    key=lambda item: (
                        item.manifest_sha256,
                        item.manifest.package_content_sha256,
                        item.source_locator_sha256,
                    ),
                )
            ),
        )
        for session in evaluated_sessions
    )
    results: list[HistoricalIdentityPackageSessionResult] = []
    total = len(evaluated_sessions)
    if workers == 1:
        for position, (session, candidates) in enumerate(jobs, 1):
            session_result = _inspect_session(
                data_root=root,
                session=session,
                candidates=candidates,
            )
            results.append(session_result)
            if progress is not None:
                progress(position, total, session, session_result.status)
    else:
        context = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_disable_network_in_worker,
        ) as executor:
            futures = {
                executor.submit(
                    _inspect_session,
                    data_root=root,
                    session=session,
                    candidates=candidates,
                ): session
                for session, candidates in jobs
            }
            for position, future in enumerate(as_completed(futures), 1):
                session = futures[future]
                session_result = future.result()
                results.append(session_result)
                if progress is not None:
                    progress(position, total, session, session_result.status)

    sessions = tuple(sorted(results, key=lambda item: item.session_date))
    status_counts = tuple(
        sorted(
            (status, sum(item.status == status for item in sessions))
            for status in {
                "missing_source",
                "package_custody_failed",
                "identity_snapshot_mismatch",
                "exact_equivalent",
                "duplicate_source_review_required",
                "canonical_identity_unavailable",
            }
        )
    )
    return HistoricalIdentityPackageEquivalenceCensusResult(
        contract_version=CENSUS_CONTRACT_VERSION,
        scope=(
            "bounded_sample" if sample_sessions is not None else "full_canonical_index"
        ),
        evaluated_at=evaluated_at.isoformat().replace("+00:00", "Z"),
        canonical_session_count=len(canonical_sessions),
        evaluated_session_count=len(evaluated_sessions),
        worker_count=workers,
        canonical_session_index_fingerprint=_json_fingerprint(
            [item.isoformat() for item in canonical_sessions]
        ),
        package_root_count=len(resolved_package_roots),
        discovered_identity_package_count=len(discovery.packages),
        ignored_non_identity_package_count=discovery.ignored_non_identity_package_count,
        unroutable_manifest_count=discovery.unroutable_manifest_count,
        outside_canonical_session_package_count=outside_canonical_count,
        discovered_package_inventory_fingerprint=discovery.inventory_fingerprint,
        exact_equivalent_session_count=sum(
            item.status == "exact_equivalent" for item in sessions
        ),
        duplicate_source_session_count=sum(
            item.status == "duplicate_source_review_required" for item in sessions
        ),
        status_counts=status_counts,
        sessions=sessions,
    )


def _inspect_session(
    *,
    data_root: Path,
    session: date,
    candidates: tuple[_DiscoveredIdentityPackage, ...],
) -> HistoricalIdentityPackageSessionResult:
    identity_repository = ParquetInstrumentMasterSnapshotRepository(data_root)
    try:
        identity = identity_repository.inspect_snapshot(session)
    except InstrumentMasterSnapshotCorruptionError:
        return HistoricalIdentityPackageSessionResult(
            session_date=session.isoformat(),
            status="canonical_identity_unavailable",
            candidate_count=len(candidates),
            custody_valid_candidate_count=0,
            exact_equivalent_candidate_count=0,
            canonical_snapshot_fingerprint=None,
            canonical_instrument_fingerprint=None,
            canonical_identity_fingerprint=None,
            canonical_resolver_fingerprint=None,
            candidates=(),
        )
    candidate_results = tuple(
        _inspect_candidate(
            data_root=data_root,
            session=session,
            identity=identity,
            candidate=candidate,
        )
        for candidate in candidates
    )
    custody_valid_count = sum(
        item.status != "package_custody_failed" for item in candidate_results
    )
    exact_count = sum(
        item.status == "exact_equivalent" for item in candidate_results
    )
    return HistoricalIdentityPackageSessionResult(
        session_date=session.isoformat(),
        status=_session_status(candidate_results),
        candidate_count=len(candidate_results),
        custody_valid_candidate_count=custody_valid_count,
        exact_equivalent_candidate_count=exact_count,
        canonical_snapshot_fingerprint=identity.snapshot_content_sha256,
        canonical_instrument_fingerprint=identity.instrument_content_sha256,
        canonical_identity_fingerprint=identity.identity_content_sha256,
        canonical_resolver_fingerprint=identity.resolver_content_sha256,
        candidates=candidate_results,
    )


def _disable_network_in_worker() -> None:
    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for Identity census worker")

    socket.socket = blocked_socket  # type: ignore[assignment]


def write_historical_identity_package_equivalence_census_report(
    *,
    report: HistoricalIdentityPackageEquivalenceCensusResult,
    report_path: Path,
) -> Path:
    """Atomically write one owner-only report below /tmp without replacement."""

    temporary_root = Path("/tmp").resolve(strict=True)
    parent = report_path.parent.resolve(strict=True)
    if parent != temporary_root and temporary_root not in parent.parents:
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "census report parent must be /tmp or a child of /tmp"
        )
    if parent.is_symlink() or not parent.is_dir():
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "census report parent must be a non-symlink directory"
        )
    target = parent / report_path.name
    if target.exists() or target.is_symlink():
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "census report path already exists"
        )
    staging = parent / f".{target.name}.staging"
    if staging.exists() or staging.is_symlink():
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "census report staging path already exists"
        )
    raw = (
        json.dumps(report.as_dict(), sort_keys=True, indent=2, ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        staging,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        staging.replace(target)
        directory_descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            staging.unlink()
        raise
    return target


def _inspect_candidate(
    *,
    data_root: Path,
    session: date,
    identity: InstrumentMasterSnapshotReadResult,
    candidate: _DiscoveredIdentityPackage,
) -> HistoricalIdentityPackageCandidateResult:
    common = {
        "source_locator_sha256": candidate.source_locator_sha256,
        "package_manifest_sha256": candidate.manifest_sha256,
        "package_content_sha256": candidate.manifest.package_content_sha256,
        "fetched_at": candidate.manifest.fetched_at.isoformat().replace(
            "+00:00", "Z"
        ),
    }
    try:
        result = inspect_historical_identity_package_equivalence(
            data_root=data_root,
            package_path=candidate.path,
            session_date=session,
            identity=identity,
        )
    except (SameDayCatchupError, HistoricalUniverseMembershipShadowError):
        return HistoricalIdentityPackageCandidateResult(
            **common,
            status="package_custody_failed",
            rebuilt_instrument_fingerprint=None,
            rebuilt_identity_fingerprint=None,
            rebuilt_resolver_fingerprint=None,
            instrument_match=None,
            identity_match=None,
            resolver_match=None,
        )
    return HistoricalIdentityPackageCandidateResult(
        **common,
        status=(
            "exact_equivalent"
            if result.exact_match
            else "identity_snapshot_mismatch"
        ),
        rebuilt_instrument_fingerprint=result.rebuilt_instrument_fingerprint,
        rebuilt_identity_fingerprint=result.rebuilt_identity_fingerprint,
        rebuilt_resolver_fingerprint=result.rebuilt_resolver_fingerprint,
        instrument_match=result.instrument_match,
        identity_match=result.identity_match,
        resolver_match=result.resolver_match,
    )


def _session_status(
    candidates: tuple[HistoricalIdentityPackageCandidateResult, ...],
) -> SessionStatus:
    if not candidates:
        return "missing_source"
    if len(candidates) > 1:
        return "duplicate_source_review_required"
    return candidates[0].status


def _validate_package_roots(package_roots: tuple[Path, ...]) -> tuple[Path, ...]:
    if not package_roots:
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "at least one explicit package root is required"
        )
    temporary_root = Path("/tmp").resolve(strict=True)
    resolved: list[Path] = []
    for raw in package_roots:
        if raw.is_symlink():
            raise HistoricalIdentityPackageEquivalenceCensusError(
                "package root must not be a symlink"
            )
        item = raw.resolve(strict=True)
        if temporary_root not in item.parents or not item.is_dir():
            raise HistoricalIdentityPackageEquivalenceCensusError(
                "package root must be an existing directory below /tmp"
            )
        if any(
            item == existing or item in existing.parents or existing in item.parents
            for existing in resolved
        ):
            raise HistoricalIdentityPackageEquivalenceCensusError(
                "package roots must be unique and non-overlapping"
            )
        resolved.append(item)
    return tuple(sorted(resolved))


def _evaluated_sessions(
    *,
    canonical_sessions: tuple[date, ...],
    sample_sessions: tuple[date, ...] | None,
) -> tuple[date, ...]:
    if sample_sessions is None:
        return canonical_sessions
    if (
        not sample_sessions
        or len(sample_sessions) != len(set(sample_sessions))
        or len(sample_sessions) > 10
    ):
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "bounded sample requires one to ten unique sessions"
        )
    canonical_set = set(canonical_sessions)
    if set(sample_sessions) - canonical_set:
        raise HistoricalIdentityPackageEquivalenceCensusError(
            "bounded sample contains a non-canonical EOD session"
        )
    return tuple(sorted(sample_sessions))


def _discover_packages(package_roots: tuple[Path, ...]) -> _PackageDiscovery:
    packages: list[_DiscoveredIdentityPackage] = []
    ignored_non_identity = 0
    unroutable = 0
    for root in package_roots:
        for manifest_path in _manifest_paths(root):
            try:
                metadata = manifest_path.lstat()
                if manifest_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                    unroutable += 1
                    continue
                raw = manifest_path.read_bytes()
                manifest = FetchPackageManifestV1.model_validate_json(raw)
            except Exception:
                unroutable += 1
                continue
            if manifest.package_type != "identity_reference":
                ignored_non_identity += 1
                continue
            packages.append(
                _DiscoveredIdentityPackage(
                    path=manifest_path.parent,
                    manifest=manifest,
                    manifest_sha256=hashlib.sha256(raw).hexdigest(),
                    source_locator_sha256=hashlib.sha256(
                        str(manifest_path.parent).encode("utf-8")
                    ).hexdigest(),
                )
            )
    packages.sort(
        key=lambda item: (
            item.manifest.session_date,
            item.manifest_sha256,
            item.manifest.package_content_sha256,
            item.source_locator_sha256,
        )
    )
    inventory = [
        {
            "session_date": item.manifest.session_date.isoformat(),
            "package_manifest_sha256": item.manifest_sha256,
            "package_content_sha256": item.manifest.package_content_sha256,
            "source_locator_sha256": item.source_locator_sha256,
        }
        for item in packages
    ]
    return _PackageDiscovery(
        packages=tuple(packages),
        ignored_non_identity_package_count=ignored_non_identity,
        unroutable_manifest_count=unroutable,
        inventory_fingerprint=_json_fingerprint(inventory),
    )


def _manifest_paths(root: Path) -> tuple[Path, ...]:
    manifests: list[Path] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            item
            for item in directories
            if not (current_path / item).is_symlink()
        )
        if "package.json" not in files:
            continue
        manifest_path = current_path / "package.json"
        manifests.append(manifest_path)
        directories[:] = []
    return tuple(sorted(manifests))


def _json_fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
