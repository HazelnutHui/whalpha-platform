"""Build one exact, blocked historical-pilot review from current Dell evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SourcePermissionConclusion,
    SourcePermissionReviewV1,
    SourceUsePermissionV1,
    assess_source_uses,
    source_permission_review_fingerprint,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.current_historical_mechanics_evidence import (
    CurrentHistoricalMechanicsEvidenceReport,
    assess_current_historical_mechanics_evidence,
)
from tip_api.services.historical_pilot_approval import (
    EXTERNAL_GATE_ORDER,
    REQUIRED_PILOT_SOURCE_FAMILY_IDS,
    HistoricalPilotRepositoryEvidenceV1,
    PilotApprovalGateEvidenceV1,
    PilotApprovalGateId,
    PilotApprovalGateState,
    build_historical_pilot_approval_review,
)
from tip_api.services.historical_pilot_planner import (
    HistoricalPilotInventoryV1,
    HistoricalPilotRequestV1,
    plan_historical_research_pilot,
    select_preceding_historical_pilot_sessions,
)


CONTRACT_VERSION = "current-historical-pilot-baseline/1.0"
SOURCE_REPORT_ID = "current-historical-pilot-inventory-v1"
MASSIVE_PERMISSION_REVIEW_RECORDED_AT = datetime(
    2026, 8, 28, 8, 10, 57, tzinfo=UTC
)
MASSIVE_PERMISSION_REVIEW_VALID_DAYS = 90
MAPPING_EVIDENCE_FILES = (
    "apps/api/src/tip_api/providers/massive/corporate_action_mapping.py",
    "apps/api/tests/fixtures/massive/corporate_actions_v1.json",
    "apps/api/tests/providers/massive/test_corporate_action_mapping.py",
)
ADJUSTMENT_EVIDENCE_FILES = (
    "apps/api/src/tip_api/services/historical_adjustment_invariants.py",
    "apps/api/tests/services/test_historical_adjustment_invariants.py",
)
PERMISSION_EVIDENCE_FILES = (
    "docs/providers/equal-capability-historical-source-review-2026-08-28.md",
    "docs/providers/massive-historical-research-review-2026-08-28.md",
)
PERMISSION_EVIDENCE_FINGERPRINT = (
    "b01afdcf8973ba6a8e7193023bdb0f2e7a8cd1770d4231423238236bfae5dd46"
)


class CurrentHistoricalPilotBaselineError(RuntimeError):
    """Raised when current pilot evidence cannot be built without guessing."""


@dataclass(frozen=True, slots=True)
class CurrentHistoricalPilotRequestObservation:
    kind: str
    scopes: tuple[str, ...]
    request_ceiling: int
    retry_count: int
    serial_only: bool


@dataclass(frozen=True, slots=True)
class CurrentHistoricalPilotGateObservation:
    gate_id: str
    state: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrentHistoricalPilotBaselineReport:
    contract_version: str
    reviewed_at: str
    status: str
    implementation_revision: str
    mechanics_evidence_fingerprint: str
    inventory_fingerprint: str
    inventory_file_count: int
    inventory_total_bytes: int
    completed_eod_session_count: int
    completed_identity_session_count: int
    target_sessions: tuple[str, ...]
    plan_fingerprint: str
    planned_request_ceiling: int
    estimated_transport_seconds_at_ceiling: int
    requests: tuple[CurrentHistoricalPilotRequestObservation, ...]
    source_permission_review_fingerprint: str
    source_permission_assessment_statuses: tuple[str, ...]
    gates: tuple[CurrentHistoricalPilotGateObservation, ...]
    unresolved_gate_ids: tuple[str, ...]
    required_user_acknowledgement: None
    next_action: str
    acquisition_authorized: bool
    apply_authorized: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_authorized: bool
    external_request_count: int
    data_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_current_historical_pilot_baseline(
    *,
    data_root: Path,
    repository_root: Path,
    reviewed_at: datetime,
) -> CurrentHistoricalPilotBaselineReport:
    """Collect current local evidence and return a non-authorizing pilot review."""

    checked_at = _aware_utc(reviewed_at)
    root = _safe_root(data_root, "canonical data root")
    repository = _safe_root(repository_root, "repository root")
    revision = _clean_main_revision(repository)
    mechanics = assess_current_historical_mechanics_evidence(root)
    inventory_counts = _historical_partition_counts(root)
    eod_sessions, identity_sessions = _current_sessions(root, mechanics)
    inventory_size_before = _inventory_size(root)
    inventory_sha = inventory_fingerprint(root)
    inventory_size_after = _inventory_size(root)
    if inventory_size_after != inventory_size_before:
        raise CurrentHistoricalPilotBaselineError(
            "canonical inventory changed during pilot review"
        )
    inventory = HistoricalPilotInventoryV1(
        source_report_id=SOURCE_REPORT_ID,
        inventory_fingerprint=inventory_sha,
        completed_eod_sessions=eod_sessions,
        completed_identity_sessions=identity_sessions,
        provider_action_partition_count=inventory_counts[0],
        lifecycle_partition_count=inventory_counts[1],
        membership_partition_count=inventory_counts[2],
        adjustment_partition_count=inventory_counts[3],
        coverage_manifest_count=inventory_counts[4],
    )
    targets = select_preceding_historical_pilot_sessions(
        completed_eod_sessions=inventory.completed_eod_sessions
    )
    plan = plan_historical_research_pilot(
        inventory=inventory,
        request=HistoricalPilotRequestV1(
            target_sessions=targets,
            inactive_identity_anchor_dates=targets,
            targeted_ticker_event_scopes=(),
            provider_id="massive_stocks_basic",
        ),
    )
    repository_evidence = HistoricalPilotRepositoryEvidenceV1(
        implementation_revision=revision,
        synthetic_action_mapping_fingerprint=_file_set_fingerprint(
            repository, MAPPING_EVIDENCE_FILES
        ),
        adjustment_invariants_fingerprint=_file_set_fingerprint(
            repository, ADJUSTMENT_EVIDENCE_FILES
        ),
    )
    permission_review = _massive_permission_review(repository)
    permission_assessments = tuple(
        assess_source_uses(
            permission_review,
            data_family_id=family_id,
            required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
            assessed_at=checked_at,
        )
        for family_id in REQUIRED_PILOT_SOURCE_FAMILY_IDS
    )
    external_gates = tuple(
        {
            PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT: (
                PilotApprovalGateEvidenceV1(
                    gate_id=PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
                    state=PilotApprovalGateState.UNVERIFIED,
                    evidence_fingerprint=None,
                    reason_codes=(
                        "current_account_historical_endpoint_entitlement_unverified",
                    ),
                )
            ),
            PilotApprovalGateId.EXACT_CURRENT_INVENTORY: (
                PilotApprovalGateEvidenceV1(
                    gate_id=PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
                    state=PilotApprovalGateState.SATISFIED,
                    evidence_fingerprint=inventory_sha,
                    reason_codes=(),
                    observed_at=checked_at,
                    valid_until=checked_at + timedelta(hours=24),
                )
            ),
            PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE: (
                PilotApprovalGateEvidenceV1(
                    gate_id=PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE,
                    state=PilotApprovalGateState.UNSATISFIED,
                    evidence_fingerprint=None,
                    reason_codes=(
                        "complete_merger_successor_terminal_source_absent",
                    ),
                )
            ),
        }[gate_id]
        for gate_id in EXTERNAL_GATE_ORDER
    )
    approval = build_historical_pilot_approval_review(
        plan=plan,
        repository_evidence=repository_evidence,
        external_gate_evidence=external_gates,
        source_permission_review=permission_review,
        source_permission_assessments=permission_assessments,
        reviewed_at=checked_at,
    )
    if approval.required_user_acknowledgement is not None:
        raise CurrentHistoricalPilotBaselineError(
            "current blocked baseline unexpectedly produced authorization text"
        )
    requests = tuple(
        CurrentHistoricalPilotRequestObservation(
            kind=item.kind.value,
            scopes=item.scopes,
            request_ceiling=item.request_ceiling,
            retry_count=item.retry_count,
            serial_only=item.serial_only,
        )
        for item in plan.request_lines
    )
    gates = tuple(
        CurrentHistoricalPilotGateObservation(
            gate_id=item.gate_id.value,
            state=item.state.value,
            reason_codes=item.reason_codes,
        )
        for item in approval.gate_results
    )
    inventory_file_count, inventory_total_bytes = inventory_size_after
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "reviewed_at": checked_at.isoformat(),
        "status": approval.review_status.value,
        "implementation_revision": revision,
        "mechanics_evidence_fingerprint": mechanics.logical_content_fingerprint,
        "inventory_fingerprint": inventory_sha,
        "inventory_file_count": inventory_file_count,
        "inventory_total_bytes": inventory_total_bytes,
        "completed_eod_session_count": len(inventory.completed_eod_sessions),
        "completed_identity_session_count": len(
            inventory.completed_identity_sessions
        ),
        "target_sessions": plan.target_sessions,
        "plan_fingerprint": plan.logical_content_fingerprint,
        "planned_request_ceiling": plan.planned_request_ceiling,
        "estimated_transport_seconds_at_ceiling": (
            plan.estimated_transport_seconds_at_ceiling
        ),
        "requests": [asdict(item) for item in requests],
        "source_permission_review_fingerprint": (
            source_permission_review_fingerprint(permission_review)
        ),
        "source_permission_assessment_statuses": tuple(
            item.status.value for item in permission_assessments
        ),
        "gates": [asdict(item) for item in gates],
        "unresolved_gate_ids": approval.unresolved_gate_ids,
        "required_user_acknowledgement": None,
        "next_action": approval.next_action.value,
        "acquisition_authorized": False,
        "apply_authorized": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_authorized": False,
        "external_request_count": 0,
        "data_write_count": 0,
    }
    return CurrentHistoricalPilotBaselineReport(
        contract_version=CONTRACT_VERSION,
        reviewed_at=checked_at.isoformat(),
        status=approval.review_status.value,
        implementation_revision=revision,
        mechanics_evidence_fingerprint=mechanics.logical_content_fingerprint,
        inventory_fingerprint=inventory_sha,
        inventory_file_count=inventory_file_count,
        inventory_total_bytes=inventory_total_bytes,
        completed_eod_session_count=len(inventory.completed_eod_sessions),
        completed_identity_session_count=len(inventory.completed_identity_sessions),
        target_sessions=plan.target_sessions,
        plan_fingerprint=plan.logical_content_fingerprint,
        planned_request_ceiling=plan.planned_request_ceiling,
        estimated_transport_seconds_at_ceiling=(
            plan.estimated_transport_seconds_at_ceiling
        ),
        requests=requests,
        source_permission_review_fingerprint=(
            source_permission_review_fingerprint(permission_review)
        ),
        source_permission_assessment_statuses=tuple(
            item.status.value for item in permission_assessments
        ),
        gates=gates,
        unresolved_gate_ids=approval.unresolved_gate_ids,
        required_user_acknowledgement=None,
        next_action=approval.next_action.value,
        acquisition_authorized=False,
        apply_authorized=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_authorized=False,
        external_request_count=0,
        data_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def _current_sessions(
    root: Path,
    mechanics: CurrentHistoricalMechanicsEvidenceReport,
) -> tuple[tuple[date, ...], tuple[date, ...]]:
    if (
        mechanics.status != "mechanics_only"
        or len(mechanics.families) != 2
        or {item.family for item in mechanics.families}
        != {"eod_price_bar", "point_in_time_identity"}
        or any(
            item.session_count != mechanics.observed_session_count
            or item.validation_status not in {
                "validated_not_published",
                "already_present",
            }
            for item in mechanics.families
        )
    ):
        raise CurrentHistoricalPilotBaselineError(
            "current mechanics evidence is not suitable for pilot planning"
        )
    sessions = CanonicalEodReadRepository(root).list_session_index()
    if (
        len(sessions) != mechanics.observed_session_count
        or sessions[0].isoformat() != mechanics.first_session
        or sessions[-1].isoformat() != mechanics.last_session
    ):
        raise CurrentHistoricalPilotBaselineError(
            "mechanics report differs from canonical session index"
        )
    identity_dates = []
    for session in sessions:
        manifest_path = (
            root
            / "market-data"
            / "eod-price-bars"
            / "schema_version=1"
            / f"session_date={session.isoformat()}"
            / "manifest.json"
        )
        try:
            manifest = json.loads(manifest_path.read_bytes())
            identity = manifest["identity_snapshot"]
            identity_dates.append(datetime.fromisoformat(identity["as_of_date"]).date())
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise CurrentHistoricalPilotBaselineError(
                "EOD Identity binding cannot be reread"
            ) from exc
    unique_identity_dates = tuple(sorted(set(identity_dates)))
    identity_family = next(
        item
        for item in mechanics.families
        if item.family == "point_in_time_identity"
    )
    if len(unique_identity_dates) != identity_family.artifact_count:
        raise CurrentHistoricalPilotBaselineError(
            "mechanics Identity artifact count differs from EOD bindings"
        )
    return sessions, unique_identity_dates


def _historical_partition_counts(root: Path) -> tuple[int, int, int, int, int]:
    repository = ParquetHistoricalResearchRepository(root)
    coverage = ParquetHistoricalCoverageRepository(root)
    counts = (
        _discover_and_read(
            root / "market-data" / "provider-corporate-action-observation",
            "schema_version=1/provider_id=*/event_year=*",
            repository.read_corporate_action_observations,
        ),
        _discover_and_read(
            root / "market-data" / "instrument-lifecycle",
            "schema_version=1/as_of_date=*",
            repository.read_instrument_lifecycle,
        ),
        _discover_and_read(
            root / "market-data" / "universe-membership",
            "schema_version=1/methodology_version=*/session_date=*",
            repository.read_universe_membership,
        ),
        _discover_and_read(
            root / "market-data" / "adjustment-ledger",
            "schema_version=1/methodology_version=*/basis_session=*",
            repository.read_adjustment_ledger,
        ),
        _discover_coverage(root, coverage),
    )
    return counts


def _discover_and_read(
    base: Path,
    pattern: str,
    reader: Callable[[Path], object],
) -> int:
    if not base.exists():
        return 0
    if not base.is_dir() or base.is_symlink():
        raise CurrentHistoricalPilotBaselineError(
            "historical family root is missing or unsafe"
        )
    partitions = tuple(sorted(base.glob(pattern)))
    if any(not item.is_dir() or item.is_symlink() for item in partitions):
        raise CurrentHistoricalPilotBaselineError(
            "historical family partition is unsafe"
        )
    manifests = tuple(base.rglob("manifest.json"))
    if len(manifests) != len(partitions):
        raise CurrentHistoricalPilotBaselineError(
            "historical family inventory contains unrecognized manifests"
        )
    for partition in partitions:
        reader(partition)
    return len(partitions)


def _discover_coverage(
    root: Path,
    repository: ParquetHistoricalCoverageRepository,
) -> int:
    base = root / "market-data" / "historical-coverage" / "schema_version=1"
    if not base.exists():
        return 0
    if not base.is_dir() or base.is_symlink():
        raise CurrentHistoricalPilotBaselineError(
            "historical coverage root is unsafe"
        )
    partitions = tuple(sorted(base.glob("coverage_id=*")))
    if len(tuple(base.rglob("manifest.json"))) != len(partitions):
        raise CurrentHistoricalPilotBaselineError(
            "historical coverage inventory contains unrecognized manifests"
        )
    for partition in partitions:
        if not partition.is_dir() or partition.is_symlink():
            raise CurrentHistoricalPilotBaselineError(
                "historical coverage partition is unsafe"
            )
        repository.read_coverage(partition.name.removeprefix("coverage_id="))
    return len(partitions)


def _massive_permission_review(repository: Path) -> SourcePermissionReviewV1:
    evidence = _file_set_fingerprint(repository, PERMISSION_EVIDENCE_FILES)
    if evidence != PERMISSION_EVIDENCE_FINGERPRINT:
        raise CurrentHistoricalPilotBaselineError(
            "dated Massive permission evidence changed and requires a new review"
        )
    permissions = []
    for use_case in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1:
        shared_delivery = use_case.value.startswith("equal_capability_")
        reason = (
            "current_individual_plan_shared_use_blocked"
            if shared_delivery
            else "account_specific_permission_required"
        )
        permissions.append(
            SourceUsePermissionV1(
                use_case=use_case,
                conclusion=(
                    SourcePermissionConclusion.BLOCKED
                    if shared_delivery
                    else SourcePermissionConclusion.REQUIRES_SEPARATE_PERMISSION
                ),
                reason_codes=(reason,),
                evidence_fingerprints=(evidence,),
            )
        )
    return SourcePermissionReviewV1(
        source_id="massive_stocks_basic",
        source_display_name="Massive Stocks Basic",
        reviewed_at=MASSIVE_PERMISSION_REVIEW_RECORDED_AT,
        valid_until=(
            MASSIVE_PERMISSION_REVIEW_RECORDED_AT
            + timedelta(days=MASSIVE_PERMISSION_REVIEW_VALID_DAYS)
        ),
        supported_data_family_ids=REQUIRED_PILOT_SOURCE_FAMILY_IDS,
        official_evidence_urls=tuple(
            sorted(
                (
                    "https://massive.com/docs/rest/stocks/aggregates/daily-market-summary",
                    "https://massive.com/docs/rest/stocks/corporate-actions/dividends",
                    "https://massive.com/docs/rest/stocks/corporate-actions/splits",
                    "https://massive.com/docs/rest/stocks/tickers/all-tickers",
                    "https://massive.com/legal/market-data-terms-of-service",
                )
            )
        ),
        permissions=tuple(permissions),
    )


def _clean_main_revision(repository: Path) -> str:
    try:
        branch = subprocess.run(
            ["git", "-C", str(repository), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        revision = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CurrentHistoricalPilotBaselineError(
            "repository identity cannot be verified"
        ) from exc
    if branch != "main" or status or len(revision) != 40:
        raise CurrentHistoricalPilotBaselineError(
            "pilot baseline requires clean Dell main"
        )
    return revision


def _file_set_fingerprint(repository: Path, relative_paths: tuple[str, ...]) -> str:
    rows = []
    for relative in relative_paths:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise CurrentHistoricalPilotBaselineError(
                "repository evidence file is missing or unsafe"
            )
        rows.append({"path": relative, "sha256": _file_sha256(path)})
    return _fingerprint(rows)


def _inventory_size(root: Path) -> tuple[int, int]:
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise CurrentHistoricalPilotBaselineError(
                "canonical inventory contains a symlink"
            )
        if path.is_file():
            files.append(path)
    return len(files), sum(path.stat().st_size for path in files)


def _safe_root(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise CurrentHistoricalPilotBaselineError(f"{label} is missing or unsafe")
    return path.absolute()


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CurrentHistoricalPilotBaselineError(
            "pilot baseline review time must be timezone-aware"
        )
    return value.astimezone(UTC)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
