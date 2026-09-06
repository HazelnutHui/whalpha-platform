"""Credential-free, network-prohibited report for the authoritative local context."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import socket
import stat
import subprocess
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterator

from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    DATASET_NAME as HISTORICAL_IDENTITY_SOURCE_DATASET,
    HistoricalIdentitySourceCustodyManifestV1,
)
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
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.market_calendar import (
    ExchangeCalendar,
    MarketDataFreshness,
    evaluate_market_data_freshness,
)
from tip_api.services.private_dashboard_snapshot import validate_snapshot_release


DATA_ROOT = Path("/data/trading-intelligence-platform")
REPOSITORY_ROOT = Path("/home/hui/projects/trading-intelligence-platform")
EXPECTED_HOST = "dell5820"
EXPECTED_USER = "hui"
RESEARCH_SESSION_FLOOR = 252

_RESEARCH_PHYSICAL_FAMILIES = (
    (
        "corporate_action_source_observation",
        "provider-corporate-action-observation",
        "schema_version=1/provider_id=*/event_year=*",
    ),
    (
        "corporate_action",
        "corporate-actions",
        "schema_version=1/event_year=*",
    ),
    (
        "universe_membership",
        "universe-membership",
        "schema_version=1/methodology_version=*/session_date=*",
    ),
    (
        "instrument_lifecycle",
        "instrument-lifecycle",
        "schema_version=1/as_of_date=*",
    ),
    (
        "adjustment_ledger",
        "adjustment-ledger",
        "schema_version=1/methodology_version=*/basis_session=*",
    ),
    (
        "historical_coverage_evidence",
        "historical-coverage-evidence",
        "schema_version=1/family=*/evidence_id=*",
    ),
    (
        "historical_coverage",
        "historical-coverage",
        "schema_version=1/coverage_id=*",
    ),
)


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
        "--full-history-validation",
        action="store_true",
        help=(
            "reconstruct every completed EOD partition instead of using the "
            "completion index plus a full latest-partition inspection"
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
            full_history_validation=args.full_history_validation,
            include_inventory=not args.skip_inventory,
        )
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
    return 0


def build_report(
    *,
    full_source_validation: bool = False,
    full_history_validation: bool = False,
    include_inventory: bool = True,
) -> dict[str, Any]:
    """Build one report from exact fixed roots without changing either root."""

    repo = _validated_directory(REPOSITORY_ROOT, "source-of-truth repository")
    data = _validated_directory(DATA_ROOT, "formal data root")
    repository = _repository_state(repo)

    eod_repository = CanonicalEodReadRepository(data)
    session_dates = _completed_session_dates(
        eod_repository,
        full_history_validation=full_history_validation,
    )
    if not session_dates:
        raise CurrentContextReportError("no completed canonical EOD session exists")
    latest_session = session_dates[-1]
    latest_integrity = eod_repository.inspect_session(latest_session)
    if full_source_validation:
        latest_rows = len(eod_repository.read_bars(latest_session))
        if latest_rows != latest_integrity.record_count:
            raise CurrentContextReportError("latest EOD row count changed during full reread")

    identity = _latest_identity_state(data)
    identity_eod_alignment = _identity_eod_alignment(
        latest_identity_date=date.fromisoformat(identity["as_of_date"]),
        latest_eod_session=latest_session,
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
    freshness = _freshness_state(
        latest_canonical_session=latest_session,
        snapshot_manifest=snapshot.manifest,
        checked_at=datetime.now(UTC),
    )

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
        "report_contract": "tip-current-context-report/1.5",
        "read_only": True,
        "network_allowed": False,
        "validation_level": (
            "full_history_and_active_sources_reread"
            if full_history_validation and full_source_validation
            else "full_history_custody_and_contracts"
            if full_history_validation
            else "active_sources_reread"
            if full_source_validation
            else "active_custody_and_contracts"
        ),
        "history_validation_scope": (
            "all_completed_partitions"
            if full_history_validation
            else "completion_index_plus_latest_partition"
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
        "freshness": freshness,
        "eod": {
            "session_count": len(session_dates),
            "first_session": session_dates[0].isoformat(),
            "latest_session": latest_session.isoformat(),
            "latest_record_count": latest_integrity.record_count,
            "latest_content_fingerprint": latest_integrity.content_fingerprint,
            "latest_parquet_sha256": latest_integrity.parquet_sha256,
            "identity_snapshot_date": latest_integrity.identity_snapshot_date.isoformat(),
            "bound_identity_snapshot_date": (
                latest_integrity.identity_snapshot_date.isoformat()
            ),
        },
        "identity": identity,
        "identity_eod_alignment": identity_eod_alignment,
        "research_readiness": _historical_research_readiness(
            data,
            session_dates=session_dates,
            history_validation_scope=(
                "all_completed_partitions"
                if full_history_validation
                else "completion_index_plus_latest_partition"
            ),
        ),
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


def _freshness_state(
    *,
    latest_canonical_session: date,
    snapshot_manifest: Any,
    checked_at: datetime,
) -> dict[str, Any]:
    """Separate live clock evaluation from the immutable Snapshot assertion."""

    calendar = ExchangeCalendar()
    canonical = evaluate_market_data_freshness(
        calendar=calendar,
        actual_latest_completed_session=latest_canonical_session,
        checked_at=checked_at,
    )
    try:
        snapshot_session = date.fromisoformat(snapshot_manifest.current_session_date)
    except (TypeError, ValueError) as exc:
        raise CurrentContextReportError(
            "active Snapshot current session is malformed"
        ) from exc
    active_snapshot = evaluate_market_data_freshness(
        calendar=calendar,
        actual_latest_completed_session=snapshot_session,
        checked_at=checked_at,
    )
    return {
        "canonical_operational": _runtime_freshness(canonical),
        "active_snapshot_operational": {
            **_runtime_freshness(active_snapshot),
            "release_id": snapshot_manifest.release_id,
        },
        "snapshot_publication_sealed": {
            "actual_latest_completed_session": (
                snapshot_manifest.actual_latest_completed_session
            ),
            "expected_latest_completed_session": (
                snapshot_manifest.expected_latest_completed_session
            ),
            "session_lag": snapshot_manifest.session_lag,
            "freshness_status": snapshot_manifest.freshness_status,
            "calendar_id": snapshot_manifest.calendar_id,
            "checked_at": snapshot_manifest.freshness_checked_at,
            "release_id": snapshot_manifest.release_id,
        },
    }


def _runtime_freshness(value: MarketDataFreshness) -> dict[str, Any]:
    return {
        "actual_latest_completed_session": (
            value.actual_latest_completed_session.isoformat()
            if value.actual_latest_completed_session is not None
            else None
        ),
        "expected_latest_completed_session": (
            value.expected_latest_completed_session.isoformat()
            if value.expected_latest_completed_session is not None
            else None
        ),
        "session_lag": value.session_lag,
        "freshness_status": value.freshness_status.value,
        "calendar_id": value.calendar_id,
        "checked_at": value.checked_at.isoformat().replace("+00:00", "Z"),
    }


def _completed_session_dates(
    repository: CanonicalEodReadRepository,
    *,
    full_history_validation: bool,
) -> tuple[date, ...]:
    dates = (
        tuple(item.session_date for item in repository.list_sessions())
        if full_history_validation
        else repository.list_session_index()
    )
    if dates != tuple(sorted(set(dates))):
        raise CurrentContextReportError(
            "completed canonical EOD sessions are not unique and ordered"
        )
    return dates


def _historical_research_readiness(
    root: Path,
    *,
    session_dates: tuple[date, ...],
    history_validation_scope: str,
) -> dict[str, Any]:
    """Report exact family progress without turning inventory into readiness."""

    if not session_dates or session_dates != tuple(sorted(set(session_dates))):
        raise CurrentContextReportError(
            "research-readiness EOD sessions must be unique and ordered"
        )
    identity_dates = _identity_completion_dates(root)
    eod_date_set = set(session_dates)
    identity_date_set = set(identity_dates)
    aligned_dates = tuple(
        session for session in session_dates if session in identity_date_set
    )
    missing_identity_dates = tuple(
        session.isoformat()
        for session in session_dates
        if session not in identity_date_set
    )
    identity_only_dates = tuple(
        session.isoformat()
        for session in identity_dates
        if session not in eod_date_set
    )
    identity_source_observation = _identity_source_observation_inventory(
        root,
        session_dates=session_dates,
    )

    physical = tuple(
        _research_family_inventory(root, family, directory, pattern)
        for family, directory, pattern in _RESEARCH_PHYSICAL_FAMILIES
    )
    by_family = {item["family"]: item for item in physical}
    blocker_codes = []
    if len(session_dates) < RESEARCH_SESSION_FLOOR:
        blocker_codes.append("canonical_price_session_floor_not_met")
    if missing_identity_dates:
        blocker_codes.append("same_session_identity_completion_incomplete")
    blocker_codes.extend(
        (
            "eod_price_bar_not_formally_coverage_validated",
            "point_in_time_identity_not_formally_coverage_validated",
        )
    )
    if identity_source_observation["partition_count"] == 0:
        blocker_codes.append("point_in_time_identity_source_observation_absent")
    elif (
        identity_source_observation["missing_eod_session_dates"]
        or identity_source_observation["source_only_session_dates"]
    ):
        blocker_codes.append("point_in_time_identity_source_observation_incomplete")
    else:
        blocker_codes.append(
            "point_in_time_identity_source_observation_not_formally_coverage_validated"
        )
    blocker_by_family = {
        "corporate_action_source_observation": (
            "corporate_action_source_observation_absent"
        ),
        "corporate_action": "canonical_corporate_action_coverage_absent",
        "universe_membership": "daily_point_in_time_membership_absent",
        "instrument_lifecycle": "instrument_lifecycle_coverage_absent",
        "adjustment_ledger": "adjustment_ledger_reconciliation_absent",
        "historical_coverage_evidence": (
            "historical_coverage_evidence_publication_absent"
        ),
        "historical_coverage": "historical_coverage_publication_absent",
    }
    for family, blocker in blocker_by_family.items():
        if by_family[family]["partition_count"] == 0:
            blocker_codes.append(blocker)
        else:
            blocker_codes.append(f"{family}_not_formally_coverage_validated")
    blocker_codes.extend(
        (
            "research_cost_and_liquidity_model_absent",
            "complete_source_availability_and_revision_lineage_absent",
            "real_chronological_evaluation_dataset_absent",
            "sealed_real_holdout_absent",
        )
    )

    return {
        "status": "data_blocked",
        "required_session_floor": RESEARCH_SESSION_FLOOR,
        "canonical_price_depth_satisfied": (
            len(session_dates) >= RESEARCH_SESSION_FLOOR
        ),
        "families": (
            {
                "family": "eod_price_bar",
                "custody_state": "canonical_acquired_coverage_unpublished",
                "partition_count": len(session_dates),
                "covered_session_count": len(session_dates),
                "first_session": session_dates[0].isoformat(),
                "last_session": session_dates[-1].isoformat(),
                "validation_scope": history_validation_scope,
                "research_ready": False,
            },
            {
                "family": "point_in_time_identity",
                "custody_state": "canonical_acquired_coverage_unpublished",
                "partition_count": len(identity_dates),
                "covered_session_count": len(aligned_dates),
                "first_session": (
                    identity_dates[0].isoformat() if identity_dates else None
                ),
                "last_session": (
                    identity_dates[-1].isoformat() if identity_dates else None
                ),
                "validation_scope": "completion_manifests",
                "missing_eod_session_dates": missing_identity_dates,
                "identity_only_dates": identity_only_dates,
                "research_ready": False,
            },
            identity_source_observation,
            *physical,
        ),
        "supporting_requirements": (
            {
                "requirement": "costs_and_liquidity",
                "state": "not_implemented",
                "note": "price_volume_proxies_do_not_establish_execution_costs",
            },
            {
                "requirement": "source_availability_and_revision_lineage",
                "state": "partial_family_specific",
                "note": "eod_identity_custody_does_not_complete_missing_families",
            },
            {
                "requirement": "chronological_evaluation",
                "state": "fixture_mechanics_only",
                "note": "no_real_performance_eligible_dataset_connected",
            },
            {
                "requirement": "holdout_custody",
                "state": "fixture_mechanics_only",
                "note": "no_real_holdout_reserved_or_consumed",
            },
        ),
        "blocker_codes": tuple(blocker_codes),
        "ready_for_strategy_development_review": False,
        "performance_claims_authorized": False,
    }


def _identity_source_observation_inventory(
    root: Path,
    *,
    session_dates: tuple[date, ...],
) -> dict[str, Any]:
    base = root / "market-data" / HISTORICAL_IDENTITY_SOURCE_DATASET
    provider_root = (
        base
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
    )
    absent = {
        "family": "point_in_time_identity_source_observation",
        "data_family_id": "point_in_time_identity",
        "record_layer": "source_observation",
        "custody_state": "absent",
        "partition_count": 0,
        "manifest_count": 0,
        "parquet_count": 0,
        "covered_session_count": 0,
        "record_count": 0,
        "source_artifact_count": 0,
        "first_session": None,
        "last_session": None,
        "missing_eod_session_dates": tuple(
            item.isoformat() for item in session_dates
        ),
        "source_only_session_dates": (),
        "validation_scope": "typed_partition_manifests_and_file_custody",
        "research_ready": False,
    }
    if not base.exists() and not base.is_symlink():
        return absent
    if (
        base.is_symlink()
        or not base.is_dir()
        or base.resolve(strict=True) != base
        or stat.S_IMODE(base.stat().st_mode) & 0o002
    ):
        raise CurrentContextReportError(
            "historical Identity source root is unsafe"
        )
    for path in (base / "schema_version=1", provider_root):
        if not path.exists() and not path.is_symlink():
            return {
                **absent,
                "custody_state": "root_present_without_partitions",
            }
        if (
            path.is_symlink()
            or not path.is_dir()
            or path.resolve(strict=True) != path
            or stat.S_IMODE(path.stat().st_mode) & 0o002
        ):
            raise CurrentContextReportError(
                "historical Identity source root is unsafe"
            )
    if any(
        not item.name.startswith("as_of_date=")
        for item in provider_root.iterdir()
    ):
        raise CurrentContextReportError(
            "historical Identity source provider inventory differs"
        )
    partitions = tuple(sorted(provider_root.glob("as_of_date=*")))
    dates: list[date] = []
    record_count = 0
    source_artifact_count = 0
    for partition in partitions:
        if (
            partition.is_symlink()
            or not partition.is_dir()
            or stat.S_IMODE(partition.stat().st_mode) != 0o755
        ):
            raise CurrentContextReportError(
                "historical Identity source partition is unsafe"
            )
        try:
            session_date = date.fromisoformat(
                partition.name.removeprefix("as_of_date=")
            )
        except ValueError as exc:
            raise CurrentContextReportError(
                "historical Identity source session is malformed"
            ) from exc
        entries = {item.name for item in partition.iterdir()}
        if entries != {"manifest.json", "part-00000.parquet"}:
            raise CurrentContextReportError(
                "historical Identity source partition file set differs"
            )
        manifest_path = partition / "manifest.json"
        parquet_path = partition / "part-00000.parquet"
        for path in (manifest_path, parquet_path):
            if (
                path.is_symlink()
                or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) != 0o644
            ):
                raise CurrentContextReportError(
                    "historical Identity source artifact is unsafe"
                )
        try:
            manifest = HistoricalIdentitySourceCustodyManifestV1.model_validate_json(
                manifest_path.read_bytes()
            )
        except Exception as exc:
            raise CurrentContextReportError(
                "historical Identity source manifest is invalid"
            ) from exc
        if (
            manifest.as_of_date != session_date
            or manifest.provider != MASSIVE_PROVIDER_ID
            or manifest.dataset_name != HISTORICAL_IDENTITY_SOURCE_DATASET
            or manifest.parquet_file != parquet_path.name
        ):
            raise CurrentContextReportError(
                "historical Identity source manifest identity differs"
            )
        dates.append(session_date)
        record_count += manifest.record_count
        source_artifact_count += len(manifest.source_artifacts)
    ordered_dates = tuple(sorted(dates))
    if tuple(dates) != ordered_dates or len(ordered_dates) != len(set(ordered_dates)):
        raise CurrentContextReportError(
            "historical Identity source sessions are not unique and ordered"
        )
    eod_dates = set(session_dates)
    source_dates = set(ordered_dates)
    missing_dates = tuple(
        item.isoformat() for item in session_dates if item not in source_dates
    )
    source_only_dates = tuple(
        item.isoformat() for item in ordered_dates if item not in eod_dates
    )
    if not ordered_dates:
        return {
            **absent,
            "custody_state": "root_present_without_partitions",
        }
    return {
        **absent,
        "custody_state": "canonical_partitions_observed_not_coverage_validated",
        "partition_count": len(ordered_dates),
        "manifest_count": len(ordered_dates),
        "parquet_count": len(ordered_dates),
        "covered_session_count": len(eod_dates & source_dates),
        "record_count": record_count,
        "source_artifact_count": source_artifact_count,
        "first_session": (
            ordered_dates[0].isoformat() if ordered_dates else None
        ),
        "last_session": (
            ordered_dates[-1].isoformat() if ordered_dates else None
        ),
        "missing_eod_session_dates": missing_dates,
        "source_only_session_dates": source_only_dates,
    }


def _identity_completion_dates(root: Path) -> tuple[date, ...]:
    snapshot_root = root / "market-data/snapshots/instrument-master"
    if (
        snapshot_root.is_symlink()
        or not snapshot_root.is_dir()
        or snapshot_root.resolve(strict=True) != snapshot_root
    ):
        raise CurrentContextReportError("Identity snapshot root is unavailable")
    dates = []
    for path in snapshot_root.iterdir():
        if not path.name.startswith("as_of_date="):
            continue
        if path.is_symlink() or not path.is_dir():
            raise CurrentContextReportError("Identity snapshot path is unsafe")
        try:
            as_of_date = date.fromisoformat(path.name.removeprefix("as_of_date="))
        except ValueError as exc:
            raise CurrentContextReportError(
                "Identity snapshot date is malformed"
            ) from exc
        _identity_state(root, as_of_date)
        dates.append(as_of_date)
    ordered = tuple(sorted(dates))
    if ordered != tuple(sorted(set(ordered))):
        raise CurrentContextReportError("Identity snapshot dates are duplicated")
    return ordered


def _research_family_inventory(
    root: Path,
    family: str,
    directory: str,
    pattern: str,
) -> dict[str, Any]:
    base = root / "market-data" / directory
    if base.is_symlink():
        raise CurrentContextReportError(f"{family} research root is unsafe")
    if not base.exists():
        return {
            "family": family,
            "custody_state": "absent",
            "partition_count": 0,
            "manifest_count": 0,
            "research_ready": False,
        }
    if not base.is_dir() or base.resolve(strict=True) != base:
        raise CurrentContextReportError(f"{family} research root is unsafe")
    if any(path.is_symlink() for path in base.rglob("*")):
        raise CurrentContextReportError(f"{family} research inventory is unsafe")
    partitions = tuple(sorted(base.glob(pattern)))
    if any(path.is_symlink() or not path.is_dir() for path in partitions):
        raise CurrentContextReportError(f"{family} research partition is unsafe")
    manifests = tuple(path for path in base.rglob("manifest.json") if path.is_file())
    state = (
        "root_present_without_partitions"
        if not partitions
        else "partitions_observed_not_coverage_validated"
    )
    return {
        "family": family,
        "custody_state": state,
        "partition_count": len(partitions),
        "manifest_count": len(manifests),
        "research_ready": False,
    }


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
