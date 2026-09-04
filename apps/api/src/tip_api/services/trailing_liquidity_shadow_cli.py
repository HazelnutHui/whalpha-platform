"""Offline administrator CLI for trailing-liquidity shadow publication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.market_data.v1 import TrailingLiquiditySourceSessionV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.trailing_liquidity import (
    ParquetTrailingLiquidityRepository,
    read_completed_trailing_liquidity_publication,
)
from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
from tip_api.services.eod_history import (
    MEDIAN_DOLLAR_VOLUME_THRESHOLD,
    PREVIOUS_CLOSE_THRESHOLD,
    TRAILING_LIQUIDITY_POLICY_VERSION,
    plan_eod_history_window,
)
from tip_api.services.market_calendar import ExchangeCalendar, evaluate_market_data_freshness
from tip_api.services.provider_classified_universe import audit_provider_classified_universes
from tip_api.services.trailing_liquidity_publication import build_trailing_liquidity_publication


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or publish versioned trailing-liquidity shadow results.")
    parser.add_argument("--analysis-session", type=date.fromisoformat, required=True)
    parser.add_argument("--membership-evidence-as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--expected-descriptor-fingerprint", required=True)
    parser.add_argument("--expected-candidate-a-fingerprint", required=True)
    parser.add_argument("--expected-candidate-b-fingerprint", required=True)
    parser.add_argument("--calculated-at", type=_utc_datetime, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root.is_absolute():
        parser.error("--data-root must be absolute")

    root = args.data_root
    repository = CanonicalEodReadRepository(root)
    calendar = ExchangeCalendar()
    session_dates = repository.list_session_index()
    if not session_dates:
        raise RuntimeError("no completed canonical EOD session exists")
    actual = session_dates[-1]
    freshness = evaluate_market_data_freshness(
        calendar=calendar,
        actual_latest_completed_session=actual,
        checked_at=datetime.now(UTC),
    )
    if actual != args.analysis_session or freshness.expected_latest_completed_session != args.analysis_session:
        raise RuntimeError("analysis session is not the expected latest completed XNYS session")
    descriptor, integrity = plan_eod_history_window(
        analysis_session=args.analysis_session,
        calendar=calendar,
        repository=repository,
    )
    if descriptor.fingerprint != args.expected_descriptor_fingerprint:
        raise RuntimeError("history descriptor fingerprint mismatch")
    if descriptor.readiness_status.value != "ready":
        raise RuntimeError("trailing-liquidity source window is not ready")

    security = read_completed_security_evidence_snapshot(root, as_of_date=args.membership_evidence_as_of_date)
    validated_root = repository._validated_root()
    instruments = repository._read_instruments(validated_root, as_of_date=args.membership_evidence_as_of_date)
    previous_membership_session = calendar.sessions_before(args.membership_evidence_as_of_date, 1)[0]
    provider_audit = audit_provider_classified_universes(
        analysis_date=args.membership_evidence_as_of_date,
        identity_instrument_ids=frozenset(instruments),
        catalog_type_codes=frozenset(item.provider_type_code for item in security.catalog),
        observations=security.observations,
        evidence=security.evidence,
        current_bars=repository.read_bars(args.membership_evidence_as_of_date),
        previous_bars=repository.read_bars(previous_membership_session),
    )
    identity_presence = {
        item.identity_snapshot_date: frozenset(
            repository._read_instruments(validated_root, as_of_date=item.identity_snapshot_date)
        )
        for item in integrity
    }
    bundle = build_trailing_liquidity_publication(
        descriptor=descriptor,
        repository=repository,
        provider_audit=provider_audit,
        evidence=security.evidence,
        membership_evidence_as_of_date=args.membership_evidence_as_of_date,
        calculated_at=args.calculated_at,
        identity_presence=identity_presence,
    )
    if bundle.candidate_a_audit_fingerprint != args.expected_candidate_a_fingerprint:
        raise RuntimeError("Candidate A audit fingerprint mismatch")
    if bundle.candidate_b_audit_fingerprint != args.expected_candidate_b_fingerprint:
        raise RuntimeError("Candidate B audit fingerprint mismatch")

    source_sessions = tuple(
        TrailingLiquiditySourceSessionV1(
            session_date=item.session_date,
            dataset_path=(
                "market-data/eod-price-bars/schema_version=1/"
                f"session_date={item.session_date.isoformat()}"
            ),
            record_count=item.record_count,
            content_fingerprint=item.content_fingerprint,
            parquet_sha256=item.parquet_sha256,
            identity_snapshot_date=item.identity_snapshot_date,
            identity_snapshot_fingerprint=item.identity_snapshot_fingerprint,
        )
        for item in integrity
    )
    plan = {
        "status": "publish_ready" if args.apply else "dry_run_ready",
        "analysis_session": args.analysis_session.isoformat(),
        "window_start": descriptor.window_start.isoformat(),
        "window_end": descriptor.window_end.isoformat(),
        "window_sessions": [item.isoformat() for item in descriptor.expected_sessions],
        "source_descriptor_fingerprint": descriptor.fingerprint,
        "metric_record_count": len(bundle.metrics),
        "decision_record_count": len(bundle.decisions),
        "candidate_summaries": [item.model_dump(mode="json") for item in bundle.candidates],
        "decision_distribution": dict(sorted(Counter(item.eligibility_status.value for item in bundle.decisions).items())),
        "gap_audits": [_safe_gap(item) for item in bundle.gap_audits],
        "external_request_count": 0,
    }
    if not args.apply:
        print(json.dumps(plan, sort_keys=True))
        return 0

    result = ParquetTrailingLiquidityRepository(root).publish(
        analysis_session=args.analysis_session,
        metrics=bundle.metrics,
        decisions=bundle.decisions,
        calendar_name=calendar.calendar_id,
        calendar_version=calendar.calendar_version,
        window_sessions=descriptor.expected_sessions,
        source_sessions=source_sessions,
        source_descriptor_fingerprint=descriptor.fingerprint,
        membership_evidence_path=security.manifest.evidence_path,
        membership_evidence_as_of_date=args.membership_evidence_as_of_date,
        membership_evidence_fingerprint=security.manifest.logical_content_sha256,
        candidates=bundle.candidates,
        previous_close_threshold=PREVIOUS_CLOSE_THRESHOLD,
        median_dollar_volume_threshold=MEDIAN_DOLLAR_VOLUME_THRESHOLD,
        policy_version=TRAILING_LIQUIDITY_POLICY_VERSION,
        created_at=args.calculated_at,
    )
    completed = read_completed_trailing_liquidity_publication(
        root, analysis_session=args.analysis_session, validate_sources=True
    )
    if completed.manifest.logical_content_fingerprint != result.logical_content_fingerprint:
        raise RuntimeError("formal production reader did not reproduce the publication")
    plan.update(
        {
            "status": result.status,
            "metric_dataset_path": result.metric_path.relative_to(root).as_posix(),
            "decision_dataset_path": result.decision_path.relative_to(root).as_posix(),
            "logical_manifest_path": result.logical_manifest_path.relative_to(root).as_posix(),
            "metric_content_fingerprint": result.metric_content_fingerprint,
            "decision_content_fingerprint": result.decision_content_fingerprint,
            "metric_parquet_sha256": result.metric_parquet_sha256,
            "decision_parquet_sha256": result.decision_parquet_sha256,
            "logical_content_fingerprint": result.logical_content_fingerprint,
        }
    )
    print(json.dumps(plan, sort_keys=True))
    return 0


def _utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("calculated-at must include a UTC offset")
    normalized = parsed.astimezone(UTC)
    if normalized.utcoffset().total_seconds() != 0:
        raise argparse.ArgumentTypeError("calculated-at must be UTC")
    return normalized


def _safe_gap(item: object) -> dict[str, object]:
    return {
        "universe_id": item.universe_id,
        "instrument_id": str(item.instrument_id),
        "display_ticker": item.display_ticker,
        "provider_type_code": item.provider_type_code,
        "first_bar_session": item.first_bar_session.isoformat() if item.first_bar_session else None,
        "last_bar_session": item.last_bar_session.isoformat() if item.last_bar_session else None,
        "observation_count": item.observation_count,
        "missing_sessions": [value.isoformat() for value in item.missing_sessions],
        "same_day_identity_present": [[value.isoformat(), present] for value, present in item.same_day_identity_present],
        "previous_bar_present": item.previous_bar_present,
        "primary_reason": item.primary_reason,
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
