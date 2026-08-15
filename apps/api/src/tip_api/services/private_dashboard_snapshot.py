"""Static private dashboard snapshot export boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.schemas.private_market import DashboardOverviewResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService
from tip_api.services.dashboard_overview import DashboardOverviewService

SNAPSHOT_CONTRACT_VERSION = "1"
SNAPSHOT_FILES = {
    "overview_file": "market-overview.json",
    "summary_file": "market-summary.json",
    "movers_file": "movers.json",
    "liquidity_map_file": "liquidity-map.json",
}
_RELEASE_ID_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$")


class DashboardSnapshotError(RuntimeError):
    """Raised when a private dashboard snapshot cannot be safely produced."""


class DashboardSnapshotManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_contract_version: str = Field(pattern=r"^1$")
    release_id: str
    generated_at: str
    current_session_date: str
    previous_session_date: str
    data_status: str
    overview_file: str
    summary_file: str
    movers_file: str
    liquidity_map_file: str
    file_sha256: dict[str, str]
    summary_node_count: int
    mover_gainer_count: int
    mover_loser_count: int
    liquidity_node_count: int
    warning_count: int
    default_universe_id: str = "tradable_us_listed_equities_v1"
    dashboard_contract_version: str = "1.1"
    is_real_provider_backed: bool
    access_classification: str
    contains_raw_provider_data: bool
    contains_credentials: bool

    @field_validator("release_id")
    @classmethod
    def release_id_is_safe(cls, value: str) -> str:
        validate_release_id(value)
        return value


@dataclass(frozen=True, slots=True)
class DashboardSnapshotResult:
    release_id: str
    output_dir: Path
    manifest: DashboardSnapshotManifest


def validate_release_id(value: str) -> str:
    if not _RELEASE_ID_RE.fullmatch(value):
        raise ValueError("release_id must be UTC timestamp plus git commit, for example 2026-08-13T120000Z-abcdef0")
    return value


def make_release_id(*, session_date: str, generated_at: datetime | None = None, git_commit: str | None = None) -> str:
    generated = generated_at or datetime.now(UTC)
    commit = git_commit or _git_commit()
    safe_commit = commit.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{7,40}", safe_commit):
        raise DashboardSnapshotError("git commit is not a safe hexadecimal value")
    value = f"{session_date}T{generated.strftime('%H%M%S')}Z-{safe_commit[:12]}"
    validate_release_id(value)
    return value


def build_private_dashboard_snapshot(
    *,
    data_root: Path,
    output_root: Path,
    release_id: str | None = None,
    generated_at: datetime | None = None,
    git_commit: str | None = None,
    allowed_output_root: Path | None = None,
) -> DashboardSnapshotResult:
    safe_data_root = _validate_existing_root(data_root, label="data_root")
    safe_output_root = _validate_output_root(output_root, allowed_output_root=allowed_output_root)

    query_service = EodMarketDataQueryService(CanonicalEodReadRepository(safe_data_root))
    analytics = EodReturnAnalyticsService(query_service)
    overview = DashboardOverviewResponse.from_model(DashboardOverviewService(query_service).get_latest_overview())
    default_universe = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    summary = default_universe.summary
    movers = default_universe.movers
    liquidity_map = default_universe.trading_activity_map

    if not (
        summary.current_session_date == movers.current_session_date == liquidity_map.current_session_date
        and summary.previous_session_date == movers.previous_session_date == liquidity_map.previous_session_date
    ):
        raise DashboardSnapshotError("market summary snapshot session dates are inconsistent")

    generated = generated_at or datetime.now(UTC)
    rid = release_id or make_release_id(
        session_date=summary.current_session_date.isoformat(), generated_at=generated, git_commit=git_commit
    )
    validate_release_id(rid)

    final_dir = _contained_child(safe_output_root, rid)
    if final_dir.exists():
        raise DashboardSnapshotError("snapshot release already exists")
    staging_dir = _contained_child(safe_output_root, f".{rid}.staging")
    if staging_dir.exists():
        raise DashboardSnapshotError("snapshot staging directory already exists")

    staging_private = staging_dir / "private-data" / "v1"
    staging_private.mkdir(parents=True, exist_ok=False)
    try:
        payloads: Mapping[str, BaseModel] = {
            SNAPSHOT_FILES["overview_file"]: overview,
            SNAPSHOT_FILES["summary_file"]: summary,
            SNAPSHOT_FILES["movers_file"]: movers,
            SNAPSHOT_FILES["liquidity_map_file"]: liquidity_map,
        }
        hashes: dict[str, str] = {}
        for filename, payload in payloads.items():
            path = staging_private / filename
            _write_json(path, payload.model_dump(mode="json"))
            _validate_json_file(path, filename)
            hashes[filename] = sha256_file(path)

        manifest = DashboardSnapshotManifest(
            snapshot_contract_version=SNAPSHOT_CONTRACT_VERSION,
            release_id=rid,
            generated_at=generated.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            current_session_date=summary.current_session_date.isoformat(),
            previous_session_date=summary.previous_session_date.isoformat(),
            data_status=summary.data_status,
            overview_file=SNAPSHOT_FILES["overview_file"],
            summary_file=SNAPSHOT_FILES["summary_file"],
            movers_file=SNAPSHOT_FILES["movers_file"],
            liquidity_map_file=SNAPSHOT_FILES["liquidity_map_file"],
            file_sha256=hashes,
            summary_node_count=1,
            mover_gainer_count=len(movers.top_gainers),
            mover_loser_count=len(movers.top_losers),
            liquidity_node_count=len(liquidity_map.nodes),
            warning_count=summary.quality_warning_count,
            default_universe_id=overview.default_universe_id,
            dashboard_contract_version=overview.contract_version,
            is_real_provider_backed=True,
            access_classification="private",
            contains_raw_provider_data=False,
            contains_credentials=False,
        )
        _write_json(staging_private / "manifest.json", manifest.model_dump(mode="json"))
        _validate_snapshot_dir(staging_private)
        (staging_dir / ".complete").write_text("completed\n", encoding="utf-8")
        os.replace(staging_dir, final_dir)
    except Exception:
        _cleanup_staging(staging_dir)
        raise

    completed_private = final_dir / "private-data" / "v1"
    manifest = _validate_snapshot_dir(completed_private)
    return DashboardSnapshotResult(release_id=rid, output_dir=final_dir, manifest=manifest)


def validate_snapshot_release(path: Path) -> DashboardSnapshotManifest:
    private_dir = path / "private-data" / "v1"
    return _validate_snapshot_dir(private_dir)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_json_bytes(payload: Mapping[str, Any]) -> bytes:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(deterministic_json_bytes(payload))
    os.replace(tmp, path)


def _validate_json_file(path: Path, filename: str) -> None:
    try:
        raw = path.read_bytes()
        decoded = json.loads(raw.decode("utf-8"))
        if filename == SNAPSHOT_FILES["summary_file"]:
            MarketSummaryResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["overview_file"]:
            DashboardOverviewResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["movers_file"]:
            MoversResponse.model_validate(decoded)
        elif filename == SNAPSHOT_FILES["liquidity_map_file"]:
            LiquidityMapResponse.model_validate(decoded)
        else:
            raise DashboardSnapshotError(f"unexpected snapshot file {filename}")
    except DashboardSnapshotError:
        raise
    except Exception as exc:
        raise DashboardSnapshotError(f"invalid snapshot file {filename}") from exc


def _validate_snapshot_dir(private_dir: Path) -> DashboardSnapshotManifest:
    if not private_dir.is_dir() or private_dir.is_symlink():
        raise DashboardSnapshotError("snapshot private-data directory is invalid")
    manifest_path = private_dir / "manifest.json"
    manifest = DashboardSnapshotManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    for field, filename in SNAPSHOT_FILES.items():
        expected = getattr(manifest, field)
        if expected != filename:
            raise DashboardSnapshotError("snapshot manifest filename mismatch")
        file_path = private_dir / filename
        if file_path.is_symlink() or not file_path.is_file():
            raise DashboardSnapshotError("snapshot file is missing or unsafe")
        _validate_json_file(file_path, filename)
        if sha256_file(file_path) != manifest.file_sha256[filename]:
            raise DashboardSnapshotError("snapshot file checksum mismatch")
    if manifest.access_classification != "private" or manifest.contains_credentials or manifest.contains_raw_provider_data:
        raise DashboardSnapshotError("snapshot manifest violates access boundary")
    return manifest


def _validate_existing_root(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_absolute() or resolved.is_symlink() or not resolved.is_dir():
        raise DashboardSnapshotError(f"{label} must be an existing absolute non-symlink directory")
    return resolved


def _validate_output_root(path: Path, *, allowed_output_root: Path | None) -> Path:
    if not path.is_absolute():
        raise DashboardSnapshotError("output_root must be absolute")
    if path.exists() and path.is_symlink():
        raise DashboardSnapshotError("output_root must not be a symlink")
    allowed = allowed_output_root or path
    if not allowed.is_absolute():
        raise DashboardSnapshotError("allowed_output_root must be absolute")
    if allowed.exists() and allowed.is_symlink():
        raise DashboardSnapshotError("allowed_output_root must not be a symlink")
    allowed.mkdir(parents=True, exist_ok=True)
    resolved_allowed = allowed.resolve(strict=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = path.parent.resolve(strict=True)
    resolved = resolved_parent / path.name
    if not str(resolved).startswith(str(resolved_allowed)):
        raise DashboardSnapshotError("output_root is outside the approved build directory")
    resolved.mkdir(parents=True, exist_ok=True)
    if resolved.is_symlink():
        raise DashboardSnapshotError("output_root must not be a symlink")
    return resolved

def _contained_child(parent: Path, child_name: str) -> Path:
    if "/" in child_name or ".." in child_name:
        raise DashboardSnapshotError("unsafe child path")
    child = parent / child_name
    if not str(child.resolve(strict=False)).startswith(str(parent.resolve(strict=True))):
        raise DashboardSnapshotError("child path escapes output root")
    return child


def _cleanup_staging(path: Path) -> None:
    if not path.exists() or path.is_symlink():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_symlink():
            child.unlink()
        elif child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as exc:  # pragma: no cover - operational fallback
        raise DashboardSnapshotError("unable to determine git commit") from exc
