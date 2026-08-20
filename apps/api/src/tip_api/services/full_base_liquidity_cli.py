"""Offline CLI for the full-classified-base trailing-liquidity scope review."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import TrailingLiquidityMetricV1, TrailingLiquidityShadowDecisionV1, TrailingLiquiditySourceSessionV1
from tip_api.contracts.security_classification.v1.universe_review import ReviewedEligibilityOverrideV1
from tip_api.persistence.parquet.dashboard_universe_activation import read_completed_dashboard_universe_activation
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.full_base_liquidity import (
    ParquetFullBaseScopeReviewRepository,
    read_completed_full_base_scope_review,
    validate_full_base_physical_round_trip,
)
from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
from tip_api.persistence.parquet.trailing_liquidity import DECISION_SCHEMA as V1_DECISION_SCHEMA, METRIC_SCHEMA as V1_METRIC_SCHEMA, read_completed_trailing_liquidity_publication
from tip_api.persistence.parquet.universe_review import OVERRIDE_SCHEMA, read_completed_universe_review
from tip_api.services.eod_history import MEDIAN_DOLLAR_VOLUME_THRESHOLD, PREVIOUS_CLOSE_THRESHOLD, plan_eod_history_window
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID, build_full_base_scope_review, calculate_membership_analytics
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID, audit_provider_classified_universes
from tip_api.services.trailing_liquidity_publication import build_trailing_liquidity_publication
from tip_api.services.universe_pre_activation import records_fingerprint

ROOT = Path("/data/trading-intelligence-platform")
ANALYSIS_SESSION = date(2026, 8, 19)
EVIDENCE_DATE = date(2026, 8, 14)
PUBLIC_SECONDARY_ID = "provider_classified_common_shares_plus_adrs_v1"
EXPECTED_DESCRIPTOR = "705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a"
EXPECTED_V1_LOGICAL = "89b58983f8c51680d77662dee7e2bfbf25406e160039d1a842d624396b08e65a"


def _freeze_metric_records(rows):
    """Compare Decimal metrics by numeric value, independent of persisted scale."""
    return [
        item.model_dump(mode="python", exclude={"calculated_at"})
        for item in sorted(rows, key=lambda item: str(item.instrument_id))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the versioned full-base trailing-liquidity scope review.")
    parser.add_argument("--apply", action="store_true", help="atomically publish the completed shadow review")
    args = parser.parse_args(argv)
    created_at = datetime.now(UTC)
    repo = CanonicalEodReadRepository(ROOT)
    sessions = repo.list_sessions()
    if max(item.session_date for item in sessions) != ANALYSIS_SESSION:
        raise RuntimeError("latest canonical EOD is not the frozen analysis session")
    descriptor, integrity = plan_eod_history_window(analysis_session=ANALYSIS_SESSION, calendar=ExchangeCalendar(), repository=repo)
    if descriptor.fingerprint != EXPECTED_DESCRIPTOR or descriptor.readiness_status.value != "ready":
        raise RuntimeError("20-session descriptor does not match the reviewed source")
    if descriptor.analysis_session in descriptor.expected_sessions:
        raise RuntimeError("analysis session entered its own trailing window")
    security = read_completed_security_evidence_snapshot(ROOT, as_of_date=EVIDENCE_DATE)
    trailing = read_completed_trailing_liquidity_publication(ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True)
    review = read_completed_universe_review(ROOT, analysis_session=ANALYSIS_SESSION, validate_source=True)
    activation = read_completed_dashboard_universe_activation(ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True)
    if (
        len(security.catalog), len(security.observations), len(security.evidence),
        trailing.metric_record_count, trailing.decision_record_count,
        review.review_record_count, len(activation.universes), review.override_record_count,
    ) != (25, 13110, 9939, 1864, 3615, 3388, 2, 2):
        raise RuntimeError("formal input counts differ from the reviewed baseline")
    if trailing.manifest.logical_content_fingerprint != EXPECTED_V1_LOGICAL:
        raise RuntimeError("Trailing Liquidity V1 logical fingerprint mismatch")
    type_counts = Counter(item.provider_type_code for item in security.evidence)
    if type_counts != Counter({"ETF": 5374, "CS": 4193, "ADRC": 372}):
        raise RuntimeError("canonical provider type distribution mismatch")

    validated_root = repo._validated_root()
    instruments = repo._read_instruments(validated_root, as_of_date=EVIDENCE_DATE)
    overrides = _read_overrides(review)
    if records_fingerprint(overrides) != review.manifest.override_dataset.content_fingerprint:
        # Content rows include created_at; the reviewed semantic fingerprint is stored in decisions.
        semantic_override_fingerprint = records_fingerprint(overrides)
    else:
        semantic_override_fingerprint = review.manifest.override_dataset.content_fingerprint
    reproduction = _reproduce_v1(repo, security, trailing, descriptor, integrity, instruments, created_at)
    if not reproduction["decision_exact"] or not reproduction["metric_exact"]:
        raise RuntimeError("frozen Legacy/V1 metrics or decisions could not be reproduced")
    old_memberships = {
        CANDIDATE_A_ID: activation.member_ids_by_universe[CANDIDATE_A_ID],
        PUBLIC_SECONDARY_ID: activation.member_ids_by_universe[PUBLIC_SECONDARY_ID],
    }
    bundle = build_full_base_scope_review(
        descriptor=descriptor, repository=repo, evidence=security.evidence, instruments=instruments,
        current_bars=repo.read_bars(ANALYSIS_SESSION), membership_evidence_as_of_date=EVIDENCE_DATE,
        reviewed_overrides=overrides, old_memberships=old_memberships, calculated_at=created_at,
    )
    a, b = bundle.final_memberships[FULL_BASE_A_ID], bundle.final_memberships[FULL_BASE_B_ID]
    if not old_memberships[CANDIDATE_A_ID] <= a or not old_memberships[PUBLIC_SECONDARY_ID] <= b:
        raise RuntimeError("corrected shadow does not contain every current production member")
    if not a <= b:
        raise RuntimeError("corrected Primary is not a subset of Secondary")
    evidence_by_id = {item.instrument_id: item for item in security.evidence}
    if any(evidence_by_id[item].provider_type_code != "ADRC" for item in b - a):
        raise RuntimeError("corrected Secondary minus Primary contains non-ADRC")

    current_by_id = {item.instrument_id: item for item in repo.read_bars(ANALYSIS_SESSION)}
    previous_by_id = {item.instrument_id: item for item in repo.read_bars(descriptor.previous_session)}
    current_analytics = {
        CANDIDATE_A_ID: calculate_membership_analytics(old_memberships[CANDIDATE_A_ID], current_by_id, previous_by_id),
        PUBLIC_SECONDARY_ID: calculate_membership_analytics(old_memberships[PUBLIC_SECONDARY_ID], current_by_id, previous_by_id),
    }
    physical_round_trip = validate_full_base_physical_round_trip(
        metrics=bundle.metrics,
        decisions=bundle.decisions,
        memberships=bundle.memberships,
        diffs=bundle.diffs,
        funnels=bundle.funnels,
    )
    plan = {
        "status": "publish_ready" if args.apply else "dry_run_ready",
        "analysis_session": ANALYSIS_SESSION.isoformat(), "membership_evidence_as_of_date": EVIDENCE_DATE.isoformat(),
        "security_type_distribution": dict(sorted(type_counts.items())),
        "source_descriptor_fingerprint": descriptor.fingerprint,
        "v1_reproduction": reproduction,
        "metric_rows": len(bundle.metrics), "decision_rows": len(bundle.decisions),
        "membership_rows": len(bundle.memberships), "diff_rows": len(bundle.diffs), "funnel_rows": len(bundle.funnels),
        "policies": [item.model_dump(mode="json") for item in bundle.summaries],
        "funnels": [item.model_dump(mode="json") for item in bundle.funnels],
        "overlapping_exclusions": bundle.overlapping_exclusions,
        "analytics": {"current_production": current_analytics, "corrected_shadow": bundle.analytics},
        "edge_tickers": _edge_audit(evidence_by_id, bundle, old_memberships, overrides),
        "physical_round_trip": physical_round_trip,
        "external_network_requests": 0,
    }
    if not args.apply:
        print(json.dumps(plan, sort_keys=True))
        return 0
    result = ParquetFullBaseScopeReviewRepository(ROOT).publish(
        analysis_session=ANALYSIS_SESSION, metrics=bundle.metrics, decisions=bundle.decisions,
        memberships=bundle.memberships, diffs=bundle.diffs, funnels=bundle.funnels,
        membership_evidence_as_of_date=EVIDENCE_DATE, calendar_name=descriptor.calendar_name,
        calendar_version=descriptor.calendar_version, window_sessions=descriptor.expected_sessions,
        source_sessions=tuple(TrailingLiquiditySourceSessionV1(
            session_date=item.session_date,
            dataset_path=f"market-data/eod-price-bars/schema_version=1/session_date={item.session_date.isoformat()}",
            record_count=item.record_count, content_fingerprint=item.content_fingerprint,
            parquet_sha256=item.parquet_sha256, identity_snapshot_date=item.identity_snapshot_date,
            identity_snapshot_fingerprint=item.identity_snapshot_fingerprint,
        ) for item in integrity),
        source_descriptor_fingerprint=descriptor.fingerprint, security_evidence_path=security.manifest.evidence_path,
        security_evidence_fingerprint=security.manifest.logical_content_sha256,
        legacy_v1_logical_path=f"market-data/snapshots/trailing-liquidity-shadow/analysis_session={ANALYSIS_SESSION}",
        legacy_v1_logical_fingerprint=trailing.manifest.logical_content_fingerprint,
        reviewed_override_logical_path=f"market-data/snapshots/universe-pre-activation-review/analysis_session={ANALYSIS_SESSION}",
        reviewed_override_fingerprint=semantic_override_fingerprint, policies=bundle.summaries,
        previous_close_threshold=PREVIOUS_CLOSE_THRESHOLD, median_dollar_volume_threshold=MEDIAN_DOLLAR_VOLUME_THRESHOLD,
        created_at=created_at,
    )
    completed = read_completed_full_base_scope_review(ROOT, analysis_session=ANALYSIS_SESSION)
    if completed.manifest.logical_content_fingerprint != result.logical_fingerprint:
        raise RuntimeError("final formal reader did not reproduce the full-base publication")
    plan.update({
        "status": result.status,
        "logical_manifest_path": result.logical_manifest_path.relative_to(ROOT).as_posix(),
        "logical_content_fingerprint": result.logical_fingerprint,
        "datasets": {key: value.model_dump(mode="json") for key, value in result.references.items()},
    })
    print(json.dumps(plan, sort_keys=True))
    return 0


def _read_overrides(review):
    path = ROOT / review.manifest.override_dataset.dataset_path / "part-00000.parquet"
    table = pq.ParquetFile(path).read()
    if table.schema != OVERRIDE_SCHEMA:
        raise RuntimeError("reviewed override schema mismatch")
    return tuple(ReviewedEligibilityOverrideV1.model_validate(row) for row in table.to_pylist())


def _reproduce_v1(repo, security, trailing, descriptor, integrity, instruments, calculated_at):
    calendar = ExchangeCalendar()
    previous_membership_session = calendar.sessions_before(EVIDENCE_DATE, 1)[0]
    provider_audit = audit_provider_classified_universes(
        analysis_date=EVIDENCE_DATE, identity_instrument_ids=frozenset(instruments),
        catalog_type_codes=frozenset(item.provider_type_code for item in security.catalog),
        observations=security.observations, evidence=security.evidence,
        current_bars=repo.read_bars(EVIDENCE_DATE), previous_bars=repo.read_bars(previous_membership_session),
    )
    identity_presence = {
        item.identity_snapshot_date: frozenset(repo._read_instruments(repo._validated_root(), as_of_date=item.identity_snapshot_date))
        for item in integrity
    }
    rebuilt = build_trailing_liquidity_publication(
        descriptor=descriptor, repository=repo, provider_audit=provider_audit, evidence=security.evidence,
        membership_evidence_as_of_date=EVIDENCE_DATE, calculated_at=calculated_at, identity_presence=identity_presence,
    )
    path = ROOT / trailing.manifest.decision_dataset.dataset_path / "part-00000.parquet"
    table = pq.ParquetFile(path).read()
    if table.schema != V1_DECISION_SCHEMA:
        raise RuntimeError("Trailing Liquidity V1 decision schema mismatch")
    persisted = tuple(TrailingLiquidityShadowDecisionV1.model_validate(row) for row in table.to_pylist())
    metric_path = ROOT / trailing.manifest.metric_dataset.dataset_path / "part-00000.parquet"
    metric_table = pq.ParquetFile(metric_path).read()
    if metric_table.schema != V1_METRIC_SCHEMA:
        raise RuntimeError("Trailing Liquidity V1 metric schema mismatch")
    persisted_metrics = tuple(TrailingLiquidityMetricV1.model_validate(row) for row in metric_table.to_pylist())
    freeze = lambda rows: [item.model_dump(mode="json", exclude={"calculated_at"}) for item in sorted(rows, key=lambda item: (item.universe_id, str(item.instrument_id)))]
    return {
        "decision_exact": freeze(rebuilt.decisions) == freeze(persisted),
        "metric_exact": _freeze_metric_records(rebuilt.metrics) == _freeze_metric_records(persisted_metrics),
        "candidate_a_fingerprint": rebuilt.candidate_a_audit_fingerprint,
        "candidate_b_fingerprint": rebuilt.candidate_b_audit_fingerprint,
        "requested_a": len(provider_audit.candidate_a.member_ids), "requested_b": len(provider_audit.candidate_b.member_ids),
    }


def _edge_audit(evidence_by_id, bundle, old_memberships, overrides):
    wanted = {"VCX", "AKAN", "BCPC", "TPC", "VXT", "AZ", "YXT"}
    active = {item.instrument_id:item for item in overrides if item.is_effective_on(ANALYSIS_SESSION)}
    decisions = {(item.policy_id,item.instrument_id):item for item in bundle.decisions}
    output = []
    for item in sorted((value for value in evidence_by_id.values() if value.provider_ticker in wanted), key=lambda value:(value.provider_ticker,str(value.instrument_id))):
        a = decisions.get((FULL_BASE_A_ID,item.instrument_id)); b = decisions.get((FULL_BASE_B_ID,item.instrument_id))
        override = active.get(item.instrument_id)
        output.append({
            "ticker": item.provider_ticker, "instrument_id": str(item.instrument_id), "provider_type_code": item.provider_type_code,
            "current_primary": item.instrument_id in old_memberships[CANDIDATE_A_ID],
            "current_secondary": item.instrument_id in old_memberships[PUBLIC_SECONDARY_ID],
            "corrected_primary_disposition": None if a is None else a.disposition.value,
            "corrected_secondary_disposition": None if b is None else b.disposition.value,
            "reviewed_override": None if override is None else override.decision.value,
        })
    return output


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
