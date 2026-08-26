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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.analytics.v1 import PreviewUniverseDefinitionV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.schemas.private_market import DashboardOverviewResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService
from tip_api.services.dashboard_overview import DashboardOverviewService
from tip_api.persistence.parquet.dashboard_universe_activation_active import ActiveDashboardUniverseActivation, read_active_dashboard_universe_activation
from tip_api.persistence.parquet.market_intelligence_active import CompletedMarketIntelligence
from tip_api.services.market_regime_preview import MarketRegimePreviewService

SNAPSHOT_CONTRACT_VERSION = "1.5"
SNAPSHOT_FILES = {
    "overview_file": "market-overview.json",
    "summary_file": "market-summary.json",
    "movers_file": "movers.json",
    "liquidity_map_file": "liquidity-map.json",
}
MARKET_INTELLIGENCE_FILE = "market-regime-overviews.json"
_RELEASE_ID_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$")


class DashboardSnapshotError(RuntimeError):
    """Raised when a private dashboard snapshot cannot be safely produced."""


class DashboardSnapshotManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_contract_version: str = Field(pattern=r"^1(?:\.[12345])?$")
    release_id: str
    generated_at: str
    current_session_date: str
    previous_session_date: str
    expected_latest_completed_session: str | None = None
    actual_latest_completed_session: str | None = None
    session_lag: int | None = None
    freshness_status: str | None = None
    calendar_id: str | None = None
    freshness_checked_at: str | None = None
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
    dashboard_contract_version: str = "1.2"
    universe_definition_id: str = "legacy_liquid_screen_provisional"
    universe_version: str = "1.0"
    governance_status: str = "provisional_classification"
    classification_as_of_date: str | None = None
    evidence_coverage_status: str = "incomplete"
    selected_universe_id: str | None = None
    available_universe_ids: tuple[str, ...] = ()
    activation_fingerprint: str | None = None
    membership_evidence_as_of: str | None = None
    funnel_stage_count: int | None = None
    funnel_source_fingerprint: str | None = None
    market_intelligence_file: str | None = None
    market_intelligence_publication_id: str | None = None
    market_intelligence_payload_sha256: str | None = None
    market_intelligence_logical_fingerprint: str | None = None
    analytics_payload_logical_fingerprint: str | None = None
    is_real_provider_backed: bool
    access_classification: str
    contains_raw_provider_data: bool
    contains_credentials: bool

    @field_validator("release_id")
    @classmethod
    def release_id_is_safe(cls, value: str) -> str:
        validate_release_id(value)
        return value

    @model_validator(mode="after")
    def freshness_contract_is_complete(self) -> DashboardSnapshotManifest:
        if self.snapshot_contract_version in {"1.1", "1.2"} and any(
            value is None
            for value in (
                self.expected_latest_completed_session,
                self.actual_latest_completed_session,
                self.session_lag,
                self.freshness_status,
                self.calendar_id,
                self.freshness_checked_at,
            )
        ):
            raise ValueError("snapshot freshness fields are required for contract 1.1")
        if self.snapshot_contract_version == "1.2" and self.classification_as_of_date is None:
            raise ValueError("snapshot governance fields are required for contract 1.2")
        if self.snapshot_contract_version in {"1.3", "1.4", "1.5"} and (
            self.classification_as_of_date is None or self.selected_universe_id is None or
            len(self.available_universe_ids) != 2 or self.activation_fingerprint is None or
            self.membership_evidence_as_of is None
        ):
            raise ValueError("snapshot activation fields are required for contract 1.3+")
        if self.snapshot_contract_version in {"1.4", "1.5"} and (
            self.funnel_stage_count != 20 or self.funnel_source_fingerprint is None
        ):
            raise ValueError("snapshot Funnel fields are required for contract 1.4")
        if self.snapshot_contract_version == "1.5" and any(
            value is None
            for value in (
                self.market_intelligence_file,
                self.market_intelligence_publication_id,
                self.market_intelligence_payload_sha256,
                self.market_intelligence_logical_fingerprint,
                self.analytics_payload_logical_fingerprint,
            )
        ):
            raise ValueError("snapshot Market Intelligence fields are required for contract 1.5")
        return self


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
    dashboard_activation: ActiveDashboardUniverseActivation | None = None,
    market_intelligence: CompletedMarketIntelligence | None = None,
) -> DashboardSnapshotResult:
    safe_data_root = _validate_existing_root(data_root, label="data_root")
    safe_output_root = _validate_output_root(output_root, allowed_output_root=allowed_output_root)

    query_service = EodMarketDataQueryService(CanonicalEodReadRepository(safe_data_root))
    analytics = EodReturnAnalyticsService(query_service)
    generated = generated_at or datetime.now(UTC)
    activation = dashboard_activation or read_active_dashboard_universe_activation(safe_data_root, analysis_session=query_service.list_sessions()[-1].session_date, validate_sources=True)
    overview = DashboardOverviewResponse.from_model(DashboardOverviewService(query_service, activation).get_latest_overview(checked_at=generated)).model_copy(
        update={"snapshot_generated_at": generated.astimezone(UTC).isoformat().replace("+00:00", "Z")}
    )
    default_universe = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    summary = default_universe.summary
    movers = default_universe.movers
    liquidity_map = default_universe.trading_activity_map

    if not (
        summary.current_session_date == movers.current_session_date == liquidity_map.current_session_date
        and summary.previous_session_date == movers.previous_session_date == liquidity_map.previous_session_date
    ):
        raise DashboardSnapshotError("market summary snapshot session dates are inconsistent")

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
        payloads: dict[str, BaseModel | Mapping[str, Any]] = {
            SNAPSHOT_FILES["overview_file"]: overview,
            SNAPSHOT_FILES["summary_file"]: summary,
            SNAPSHOT_FILES["movers_file"]: movers,
            SNAPSHOT_FILES["liquidity_map_file"]: liquidity_map,
        }
        market_payload: Mapping[str, Any] | None = None
        if market_intelligence is not None:
            if (
                market_intelligence.payload.analysis_session != summary.current_session_date
                or market_intelligence.payload.source.activation.logical_fingerprint
                != overview.activation_fingerprint
                or market_intelligence.payload.source.activation.universes
                != tuple(
                    PreviewUniverseDefinitionV1(
                        universe_id=item.definition.universe_id,
                        display_name=item.definition.display_name,
                        catalog_order=index,
                        is_default=item.definition.universe_id == overview.default_universe_id,
                        member_count=item.definition.member_count,
                        membership_fingerprint=item.definition.membership_fingerprint,
                    )
                    for index, item in enumerate(overview.universes)
                )
            ):
                raise DashboardSnapshotError(
                    "Market Intelligence source does not match Dashboard Snapshot sources"
                )
            market_service = MarketRegimePreviewService.from_payload(
                market_intelligence.payload.analytics,
                market_intelligence.payload.source.preview_generated_at,
            )
            market_payload = {
                "schema_version": "1.0",
                "contract_version": "market-regime-snapshot/1.0",
                "publication_id": market_intelligence.payload.publication_id,
                "payload_sha256": market_intelligence.manifest.payload_sha256,
                "payload_logical_fingerprint": market_intelligence.payload.logical_fingerprint,
                "analytics_logical_fingerprint": (
                    market_intelligence.payload.analytics.logical_fingerprint
                ),
                "default_universe_id": overview.default_universe_id,
                "universe_order": [item.definition.universe_id for item in overview.universes],
                "records": [
                    market_service.overview(item.definition.universe_id).model_dump(mode="json")
                    for item in overview.universes
                ],
            }
            payloads[MARKET_INTELLIGENCE_FILE] = market_payload
        hashes: dict[str, str] = {}
        for filename, payload in payloads.items():
            path = staging_private / filename
            value = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
            _write_json(path, value)
            _validate_json_file(path, filename)
            hashes[filename] = sha256_file(path)

        funnel_stage_count = sum(len(item.funnel) for item in overview.universes)
        snapshot_contract_version = (
            SNAPSHOT_CONTRACT_VERSION
            if funnel_stage_count == 20 and market_intelligence is not None
            else ("1.4" if funnel_stage_count == 20 else "1.3")
        )
        manifest = DashboardSnapshotManifest(
            snapshot_contract_version=snapshot_contract_version,
            release_id=rid,
            generated_at=generated.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            current_session_date=summary.current_session_date.isoformat(),
            previous_session_date=summary.previous_session_date.isoformat(),
            expected_latest_completed_session=(overview.expected_latest_completed_session.isoformat() if overview.expected_latest_completed_session else None),
            actual_latest_completed_session=(overview.actual_latest_completed_session.isoformat() if overview.actual_latest_completed_session else None),
            session_lag=overview.session_lag,
            freshness_status=overview.freshness_status,
            calendar_id=overview.calendar_id,
            freshness_checked_at=overview.freshness_checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
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
            dashboard_contract_version=(
                "2.2" if snapshot_contract_version == "1.5" else overview.contract_version
            ),
            universe_definition_id=overview.universe_definition_id,
            universe_version=overview.universe_version,
            governance_status=overview.governance_status,
            classification_as_of_date=overview.classification_as_of_date.isoformat(),
            evidence_coverage_status=overview.evidence_coverage_status,
            selected_universe_id=overview.selected_universe_id,
            available_universe_ids=tuple(item.definition.universe_id for item in overview.universes),
            activation_fingerprint=overview.activation_fingerprint,
            membership_evidence_as_of=overview.classification_as_of_date.isoformat(),
            funnel_stage_count=(
                funnel_stage_count
                if snapshot_contract_version in {"1.4", "1.5"}
                else None
            ),
            funnel_source_fingerprint=(
                next(item.funnel[0].source_fingerprint for item in overview.universes if item.funnel)
                if snapshot_contract_version in {"1.4", "1.5"} else None
            ),
            market_intelligence_file=(
                MARKET_INTELLIGENCE_FILE if market_intelligence is not None else None
            ),
            market_intelligence_publication_id=(
                market_intelligence.payload.publication_id
                if market_intelligence is not None
                else None
            ),
            market_intelligence_payload_sha256=(
                market_intelligence.manifest.payload_sha256
                if market_intelligence is not None
                else None
            ),
            market_intelligence_logical_fingerprint=(
                market_intelligence.payload.logical_fingerprint
                if market_intelligence is not None
                else None
            ),
            analytics_payload_logical_fingerprint=(
                market_intelligence.payload.analytics.logical_fingerprint
                if market_intelligence is not None
                else None
            ),
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
        elif filename == MARKET_INTELLIGENCE_FILE:
            _validate_market_intelligence_snapshot(decoded)
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
    if manifest.snapshot_contract_version in {"1.4", "1.5"}:
        overview = DashboardOverviewResponse.model_validate_json((private_dir / manifest.overview_file).read_text(encoding="utf-8"))
        if overview.contract_version != "2.1" or sum(len(item.funnel) for item in overview.universes) != 20:
            raise DashboardSnapshotError("snapshot formal Funnel contract mismatch")
        fingerprints = {stage.source_fingerprint for item in overview.universes for stage in item.funnel}
        if fingerprints != {manifest.funnel_source_fingerprint}:
            raise DashboardSnapshotError("snapshot Funnel source fingerprint mismatch")
    if manifest.snapshot_contract_version == "1.5":
        if manifest.dashboard_contract_version != "2.2":
            raise DashboardSnapshotError("snapshot Dashboard contract 2.2 is required")
        analytics_path = private_dir / MARKET_INTELLIGENCE_FILE
        if analytics_path.is_symlink() or not analytics_path.is_file():
            raise DashboardSnapshotError("snapshot Market Intelligence file is missing")
        _validate_json_file(analytics_path, MARKET_INTELLIGENCE_FILE)
        if sha256_file(analytics_path) != manifest.file_sha256.get(MARKET_INTELLIGENCE_FILE):
            raise DashboardSnapshotError("snapshot Market Intelligence checksum mismatch")
        analytics = json.loads(analytics_path.read_bytes())
        if (
            analytics["publication_id"] != manifest.market_intelligence_publication_id
            or analytics["payload_sha256"] != manifest.market_intelligence_payload_sha256
            or analytics["payload_logical_fingerprint"]
            != manifest.market_intelligence_logical_fingerprint
            or analytics["analytics_logical_fingerprint"]
            != manifest.analytics_payload_logical_fingerprint
        ):
            raise DashboardSnapshotError("snapshot Market Intelligence reference mismatch")
    return manifest


def _validate_market_intelligence_snapshot(value: object) -> None:
    if not isinstance(value, dict):
        raise DashboardSnapshotError("Market Intelligence snapshot is not an object")
    if (
        value.get("schema_version") != "1.0"
        or value.get("contract_version") != "market-regime-snapshot/1.0"
        or not isinstance(value.get("records"), list)
        or len(value["records"]) != 2
        or value.get("universe_order")
        != [
            "provider_classified_common_shares_v1",
            "provider_classified_common_shares_plus_adrs_v1",
        ]
    ):
        raise DashboardSnapshotError("Market Intelligence snapshot contract is invalid")
    from tip_api.contracts.analytics.v1 import MarketRegimeOpportunityMapResponseV1

    records = tuple(
        MarketRegimeOpportunityMapResponseV1.model_validate(item) for item in value["records"]
    )
    if tuple(item.selected_universe_id for item in records) != tuple(value["universe_order"]):
        raise DashboardSnapshotError("Market Intelligence snapshot Universe order differs")
    if any(len(item.relationships) != 16 for item in records):
        raise DashboardSnapshotError("Market Intelligence snapshot pair registry is incomplete")


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
