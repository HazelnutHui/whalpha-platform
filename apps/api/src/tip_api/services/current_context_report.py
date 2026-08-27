"""Credential-free, network-prohibited report for the authoritative local context."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import socket
import subprocess
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from tip_api.persistence.parquet.dashboard_snapshot_active import (
    read_active_dashboard_snapshot,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    read_active_dashboard_universe_activation,
    read_dashboard_universe_activation_pointer,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.market_intelligence_active import (
    read_active_market_intelligence,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.private_dashboard_snapshot import validate_snapshot_release


DATA_ROOT = Path("/data/trading-intelligence-platform")
REPOSITORY_ROOT = Path("/home/hui/projects/trading-intelligence-platform")
EXPECTED_HOST = "dell5820"
EXPECTED_USER = "hui"


class CurrentContextReportError(RuntimeError):
    """Raised when an authoritative read-only context cannot be produced."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read the fixed repository and /data roots and emit a credential-free "
            "local context report. No network or write operation is available."
        )
    )
    parser.add_argument(
        "--full-source-validation",
        action="store_true",
        help=(
            "also reread latest EOD rows and the active Activation and "
            "Market Intelligence sources"
        ),
    )
    parser.add_argument(
        "--skip-inventory",
        action="store_true",
        help="skip the full /data content-and-metadata inventory fingerprint",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with _network_guard():
        report = build_report(
            full_source_validation=args.full_source_validation,
            include_inventory=not args.skip_inventory,
        )
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
    return 0


def build_report(
    *, full_source_validation: bool = False, include_inventory: bool = True
) -> dict[str, Any]:
    """Build one report from exact fixed roots without changing either root."""

    repo = _validated_directory(REPOSITORY_ROOT, "source-of-truth repository")
    data = _validated_directory(DATA_ROOT, "formal data root")
    repository = _repository_state(repo)

    eod_repository = CanonicalEodReadRepository(data)
    sessions = eod_repository.list_sessions()
    if not sessions:
        raise CurrentContextReportError("no completed canonical EOD session exists")
    latest_descriptor = sessions[-1]
    latest_integrity = eod_repository.inspect_session(latest_descriptor.session_date)
    if full_source_validation:
        latest_rows = len(eod_repository.read_bars(latest_descriptor.session_date))
        if latest_rows != latest_descriptor.record_count:
            raise CurrentContextReportError("latest EOD row count changed during full reread")

    identity = _latest_identity_state(data)
    identity_eod_alignment = _identity_eod_alignment(
        latest_identity_date=date.fromisoformat(identity["as_of_date"]),
        latest_eod_session=latest_descriptor.session_date,
        eod_bound_identity_date=latest_integrity.identity_snapshot_date,
    )
    activation_pointer = read_dashboard_universe_activation_pointer(data)
    if activation_pointer is None:
        raise CurrentContextReportError("Activation V2 pointer is absent")
    activation_session = activation_pointer.active.analysis_session
    activation = read_active_dashboard_universe_activation(
        data,
        analysis_session=activation_session,
        validate_sources=full_source_validation,
    )
    market_intelligence = read_active_market_intelligence(
        data, validate_sources=full_source_validation
    )
    snapshot = read_active_dashboard_snapshot(data, repo / "build/private-dashboard")

    inventory = _inventory_state(data, include_fingerprint=include_inventory)
    publication_residue = _publication_residue(data)
    analytics = market_intelligence.payload.analytics
    candidate_analytics = getattr(market_intelligence.payload, "candidate_analytics", None)
    universe_analytics = []
    for item in analytics.universes:
        universe_analytics.append(
            {
                "universe_id": item.definition.universe_id,
                "member_count": item.definition.member_count,
                "regime_score": _decimal_text(item.composite.regime_score),
                "candidate_state": item.current_state.instantaneous_candidate_state,
                "confirmed_state": item.current_state.confirmed_state,
            }
        )

    report = {
        "report_contract": "tip-current-context-report/1.1",
        "read_only": True,
        "network_allowed": False,
        "validation_level": (
            "active_sources_reread"
            if full_source_validation
            else "active_custody_and_contracts"
        ),
        "host": {
            "hostname": socket.gethostname(),
            "expected_hostname": EXPECTED_HOST,
            "hostname_matches": socket.gethostname() == EXPECTED_HOST,
            "user": getpass.getuser(),
            "expected_user": EXPECTED_USER,
            "user_matches": getpass.getuser() == EXPECTED_USER,
        },
        "repository": repository,
        "inventory": inventory,
        "publication_residue": publication_residue,
        "eod": {
            "session_count": len(sessions),
            "first_session": sessions[0].session_date.isoformat(),
            "latest_session": latest_descriptor.session_date.isoformat(),
            "latest_record_count": latest_descriptor.record_count,
            "latest_content_fingerprint": latest_integrity.content_fingerprint,
            "latest_parquet_sha256": latest_integrity.parquet_sha256,
            "identity_snapshot_date": latest_integrity.identity_snapshot_date.isoformat(),
            "bound_identity_snapshot_date": (
                latest_integrity.identity_snapshot_date.isoformat()
            ),
        },
        "identity": identity,
        "identity_eod_alignment": identity_eod_alignment,
        "activation": {
            "analysis_session": activation.manifest.analysis_session.isoformat(),
            "pointer_fingerprint": activation_pointer.pointer_content_fingerprint,
            "logical_fingerprint": activation.manifest.logical_content_fingerprint,
            "default_universe_id": activation.manifest.default_universe_id,
            "universes": [
                {
                    "universe_id": item.universe_id,
                    "member_count": item.member_count,
                    "membership_fingerprint": item.membership_fingerprint,
                    "security_type_composition": {
                        value.provider_type_code: value.count
                        for value in item.security_type_composition
                    },
                }
                for item in activation.universes
            ],
        },
        "market_intelligence": {
            "publication_id": market_intelligence.manifest.publication_id,
            "analysis_session": market_intelligence.manifest.analysis_session.isoformat(),
            "contract_version": market_intelligence.manifest.contract_version,
            "payload_sha256": market_intelligence.manifest.payload_sha256,
            "payload_logical_fingerprint": (
                market_intelligence.manifest.payload_logical_fingerprint
            ),
            "analytics_logical_fingerprint": (
                market_intelligence.manifest.analytics_logical_fingerprint
            ),
            "etf_count": market_intelligence.manifest.etf_count,
            "relationship_count": market_intelligence.manifest.relationship_count,
            "relationship_history_count": (
                market_intelligence.manifest.relationship_history_count
            ),
            "input_session_count": analytics.input_session_count,
            "analytics_data_status": analytics.data_status,
            "review_deployment": (
                market_intelligence.manifest.review_deployment.model_dump(mode="json")
                if market_intelligence.manifest.review_deployment is not None
                else None
            ),
            "candidate": (
                {
                    "contract_version": candidate_analytics.contract_version,
                    "logical_fingerprint": candidate_analytics.logical_fingerprint,
                    "audit_logical_fingerprint": (
                        candidate_analytics.source.candidate_audit_logical_fingerprint
                    ),
                    "parameter_fingerprint": (
                        candidate_analytics.source.candidate_parameter_fingerprint
                    ),
                    "state_parameter_fingerprint": (
                        candidate_analytics.source.candidate_state_parameter_fingerprint
                    ),
                    "display_counts": {
                        item.universe_id: len(item.candidates)
                        for item in candidate_analytics.universes
                    },
                }
                if candidate_analytics is not None
                else None
            ),
            "universes": universe_analytics,
        },
        "snapshot": {
            "release_id": snapshot.manifest.release_id,
            "snapshot_contract_version": snapshot.manifest.snapshot_contract_version,
            "dashboard_contract_version": snapshot.manifest.dashboard_contract_version,
            "data_status": snapshot.manifest.data_status,
            "current_session": snapshot.manifest.current_session_date,
            "previous_session": snapshot.manifest.previous_session_date,
            "expected_session": snapshot.manifest.expected_latest_completed_session,
            "session_lag": snapshot.manifest.session_lag,
            "review_mode": snapshot.manifest.review_mode,
            "market_intelligence_publication_id": (
                snapshot.manifest.market_intelligence_publication_id
            ),
            "candidate_contract_version": snapshot.manifest.candidate_contract_version,
            "candidate_analytics_logical_fingerprint": (
                snapshot.manifest.candidate_analytics_logical_fingerprint
            ),
            "pointer_fingerprint": (
                snapshot.pointer.pointer_content_fingerprint
                if snapshot.pointer is not None
                else None
            ),
        },
    }
    report["local_bundles"] = _matching_local_bundles(
        repo,
        current_git_head=repository["head"],
        snapshot_release=snapshot.manifest.release_id,
        market_intelligence_publication=market_intelligence.manifest.publication_id,
    )
    return report


def _validated_directory(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
        raise CurrentContextReportError(f"{label} is unavailable or unsafe")
    return path


def _repository_state(repo: Path) -> dict[str, Any]:
    head = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "branch", "--show-current") or None
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "path": str(repo),
        "head": head,
        "branch": branch,
        "clean": status == "",
        "change_count": 0 if status == "" else len(status.splitlines()),
        "source_of_truth_shape": branch == "main",
    }


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repo), *arguments),
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    return result.stdout.strip()


def _identity_state(root: Path, as_of_date: date) -> dict[str, Any]:
    path = (
        root
        / "market-data/snapshots/instrument-master"
        / f"as_of_date={as_of_date.isoformat()}"
        / "manifest.json"
    )
    if path.is_symlink() or not path.is_file():
        raise CurrentContextReportError("same-day Identity manifest is unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentContextReportError("same-day Identity manifest is malformed") from exc
    expected = {
        "completion_status": "completed",
        "as_of_date": as_of_date.isoformat(),
    }
    if any(value.get(key) != item for key, item in expected.items()):
        raise CurrentContextReportError("same-day Identity manifest identity differs")
    fields = ("instrument_count", "identity_count", "resolver_count")
    if any(not isinstance(value.get(field), int) or value[field] <= 0 for field in fields):
        raise CurrentContextReportError("same-day Identity counts are invalid")
    fingerprint = value.get("snapshot_content_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise CurrentContextReportError("same-day Identity fingerprint is invalid")
    return {
        "as_of_date": value["as_of_date"],
        "completion_status": value["completion_status"],
        "instrument_count": value["instrument_count"],
        "provider_identity_count": value["identity_count"],
        "resolver_count": value["resolver_count"],
        "logical_fingerprint": fingerprint,
    }


def _latest_identity_state(root: Path) -> dict[str, Any]:
    snapshot_root = root / "market-data/snapshots/instrument-master"
    if (
        snapshot_root.is_symlink()
        or not snapshot_root.is_dir()
        or snapshot_root.resolve(strict=True) != snapshot_root
    ):
        raise CurrentContextReportError("Identity snapshot root is unavailable")
    candidates: list[date] = []
    for path in snapshot_root.iterdir():
        if not path.name.startswith("as_of_date="):
            continue
        if path.is_symlink() or not path.is_dir():
            raise CurrentContextReportError("Identity snapshot path is unsafe")
        try:
            candidates.append(date.fromisoformat(path.name.removeprefix("as_of_date=")))
        except ValueError as exc:
            raise CurrentContextReportError(
                "Identity snapshot date is malformed"
            ) from exc
    if not candidates:
        raise CurrentContextReportError("no completed Identity snapshot exists")
    return _identity_state(root, max(candidates))


def _identity_eod_alignment(
    *,
    latest_identity_date: date,
    latest_eod_session: date,
    eod_bound_identity_date: date,
) -> dict[str, str]:
    if eod_bound_identity_date != latest_eod_session:
        raise CurrentContextReportError("latest EOD Identity binding is inconsistent")
    status = (
        "aligned"
        if latest_identity_date == latest_eod_session
        else "identity_ahead_of_eod"
        if latest_identity_date > latest_eod_session
        else "identity_behind_eod"
    )
    return {
        "status": status,
        "latest_identity_date": latest_identity_date.isoformat(),
        "latest_eod_session": latest_eod_session.isoformat(),
        "eod_bound_identity_date": eod_bound_identity_date.isoformat(),
    }


def _inventory_state(root: Path, *, include_fingerprint: bool) -> dict[str, Any]:
    paths = tuple(root.rglob("*"))
    files = tuple(path for path in paths if path.is_file() and not path.is_symlink())
    symlinks = tuple(
        path.relative_to(root).as_posix() for path in paths if path.is_symlink()
    )
    return {
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "fingerprint": inventory_fingerprint(root) if include_fingerprint else None,
        "fingerprint_skipped": not include_fingerprint,
        "symlink_count": len(symlinks),
        "symlink_paths": symlinks,
    }


def _publication_residue(root: Path) -> dict[str, Any]:
    residue = []
    for path in root.rglob("*"):
        name = path.name.lower()
        if "staging" in name or "partial" in name:
            residue.append(path.relative_to(root).as_posix())
    return {"count": len(residue), "paths": tuple(sorted(residue))}


def _matching_local_bundles(
    repo: Path,
    *,
    current_git_head: str,
    snapshot_release: str,
    market_intelligence_publication: str,
) -> tuple[dict[str, Any], ...]:
    base = repo / "build/oci-dashboard"
    if base.is_symlink() or not base.is_dir():
        return ()
    matches = []
    for manifest_path in sorted(base.glob("*/deployment-manifest.json")):
        bundle = manifest_path.parent
        if bundle.is_symlink() or manifest_path.is_symlink():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            manifest.get("market_intelligence_publication_id")
            != market_intelligence_publication
        ):
            continue
        snapshot = validate_snapshot_release(bundle)
        if snapshot.release_id != snapshot_release:
            continue
        checksums = _validate_bundle_checksums(bundle)
        matches.append(
            {
                "release_id": manifest.get("release_id"),
                "path": str(bundle),
                "bundle_source_commit": manifest.get("git_commit"),
                "matches_current_repository_head": (
                    manifest.get("git_commit") == current_git_head
                ),
                "snapshot_release_id": snapshot.release_id,
                "market_intelligence_publication_id": (
                    manifest.get("market_intelligence_publication_id")
                ),
                "default_locale": manifest.get("default_locale"),
                "supported_locales": manifest.get("supported_locales"),
                "checksum_file_count": checksums,
                "contains_credentials": manifest.get("contains_credentials"),
                "contains_raw_provider_data": manifest.get("contains_raw_provider_data"),
                "contains_parquet": manifest.get("contains_parquet"),
            }
        )
    return tuple(matches)


def _validate_bundle_checksums(bundle: Path) -> int:
    checksum_path = bundle / "checksums.sha256"
    if checksum_path.is_symlink() or not checksum_path.is_file():
        raise CurrentContextReportError("local bundle checksum inventory is unavailable")
    count = 0
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if separator != "  " or len(digest) != 64:
            raise CurrentContextReportError("local bundle checksum inventory is malformed")
        relative_path = Path(relative.removeprefix("./"))
        target = bundle / relative_path
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or target.is_symlink()
            or not target.is_file()
            or _file_sha256(target) != digest
        ):
            raise CurrentContextReportError("local bundle checksum validation failed")
        count += 1
    if count == 0:
        raise CurrentContextReportError("local bundle checksum inventory is empty")
    return count


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: object) -> str | None:
    return None if value is None else str(value)


@contextmanager
def _network_guard() -> Iterator[None]:
    original_socket = socket.socket

    def blocked_socket(*args: object, **kwargs: object) -> socket.socket:
        raise CurrentContextReportError("network access is prohibited for context reports")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())
