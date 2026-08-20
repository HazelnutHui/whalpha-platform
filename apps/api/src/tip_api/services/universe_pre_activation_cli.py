"""Offline administrator CLI for Universe pre-activation review publication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import ShadowEligibilityStatus, TrailingLiquidityShadowDecisionV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
from tip_api.persistence.parquet.trailing_liquidity import read_completed_trailing_liquidity_publication
from tip_api.persistence.parquet.universe_review import ParquetUniverseReviewRepository, read_completed_universe_review
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.security_classification import (
    MATERIAL_QUALITY_FLAGS,
    MINIMUM_PREVIOUS_CLOSE,
    MINIMUM_PREVIOUS_DOLLAR_VOLUME,
    SUPPORTED_EXCHANGES,
)
from tip_api.services.universe_pre_activation import (
    build_universe_review,
    compare_stable_sets,
    membership_fingerprint,
    repository_reviewed_overrides,
)

DATA_ROOT = Path("/data/trading-intelligence-platform")
ANALYSIS_SESSION = date(2026, 8, 19)
MEMBERSHIP_DATE = date(2026, 8, 14)
LEGACY_PREVIOUS_SESSION = date(2026, 8, 13)
EXPECTED_DESCRIPTOR = "705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a"
EXPECTED_METRIC = "8abe29f4deb064acea974590fe965ecb166405381e7632762eb2ecba783ea7fc"
EXPECTED_DECISION = "9f27f7babaf347cab590386d9229d97f1f4348e32e483a35deffddc25d0a3254"
EXPECTED_LOGICAL = "89b58983f8c51680d77662dee7e2bfbf25406e160039d1a842d624396b08e65a"
EXPECTED_A_AUDIT = "1b8b9757054130c04ac21266d3660107c0b38d37db0ba8e510a0dcb2ed9583fd"
EXPECTED_B_AUDIT = "2404a29b818ac365db19dff9734eea10cbda7b88f16b93610ea49297bb03aa95"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review and optionally publish reviewed Universe eligibility shadows."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    created_at = datetime.now(UTC)

    _require_targets_absent(DATA_ROOT)
    trailing = read_completed_trailing_liquidity_publication(
        DATA_ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True
    )
    tm = trailing.manifest
    observed = (
        tm.source_descriptor_fingerprint,
        tm.metric_dataset.content_fingerprint,
        tm.decision_dataset.content_fingerprint,
        tm.logical_content_fingerprint,
    )
    if observed != (EXPECTED_DESCRIPTOR, EXPECTED_METRIC, EXPECTED_DECISION, EXPECTED_LOGICAL):
        raise RuntimeError("published trailing-liquidity input fingerprint mismatch")
    if tm.membership_evidence_as_of_date != MEMBERSHIP_DATE:
        raise RuntimeError("membership evidence date mismatch")
    if len(tm.window_sessions) != 20 or ANALYSIS_SESSION in tm.window_sessions:
        raise RuntimeError("trailing source window is invalid")
    candidate_a, candidate_b = tm.candidates
    if (
        candidate_a.universe_id != CANDIDATE_A_ID
        or candidate_b.universe_id != CANDIDATE_B_ID
        or candidate_a.audit_fingerprint != EXPECTED_A_AUDIT
        or candidate_b.audit_fingerprint != EXPECTED_B_AUDIT
    ):
        raise RuntimeError("Candidate A/B source audit mismatch")

    decision_path = DATA_ROOT / tm.decision_dataset.dataset_path / "part-00000.parquet"
    records = tuple(
        TrailingLiquidityShadowDecisionV1.model_validate(row)
        for row in pq.ParquetFile(decision_path).read().to_pylist()
    )
    passed = {
        universe_id: frozenset(
            item.instrument_id
            for item in records
            if item.universe_id == universe_id and item.included
        )
        for universe_id in (CANDIDATE_A_ID, CANDIDATE_B_ID)
    }
    requested = {
        universe_id: frozenset(item.instrument_id for item in records if item.universe_id == universe_id)
        for universe_id in (CANDIDATE_A_ID, CANDIDATE_B_ID)
    }
    status_by_id = {
        item.instrument_id: item.eligibility_status.value
        for item in records
        if item.universe_id == CANDIDATE_B_ID
    }

    security = read_completed_security_evidence_snapshot(DATA_ROOT, as_of_date=MEMBERSHIP_DATE)
    type_by_id = {item.instrument_id: item.provider_type_code for item in security.evidence}
    ticker_by_id = {item.instrument_id: item.provider_ticker for item in security.evidence}
    repository = CanonicalEodReadRepository(DATA_ROOT)
    legacy, legacy_current, legacy_previous = _legacy_ids(repository)
    overrides = repository_reviewed_overrides(created_at=created_at)
    bundle = build_universe_review(
        analysis_session=ANALYSIS_SESSION,
        passed_by_universe=passed,
        provider_type_by_id=type_by_id,
        trailing_decision_fingerprint=tm.decision_dataset.content_fingerprint,
        overrides=overrides,
        created_at=created_at,
    )
    adrc_ids = frozenset(instrument_id for instrument_id, code in type_by_id.items() if code == "ADRC")
    gap_audit = _audit_gaps(repository, tm.window_sessions, records, ticker_by_id, type_by_id)
    edge = _edge_audit(
        security=security,
        ticker_by_id=ticker_by_id,
        type_by_id=type_by_id,
        legacy=legacy,
        requested=requested,
        passed=passed,
        status_by_id=status_by_id,
        overrides=overrides,
        final=bundle.final_memberships,
    )
    comparisons = {
        "candidate_a_passed_vs_legacy": asdict(compare_stable_sets(passed[CANDIDATE_A_ID], legacy)),
        "candidate_b_passed_vs_legacy": asdict(compare_stable_sets(passed[CANDIDATE_B_ID], legacy)),
        "candidate_a_passed_vs_candidate_b_passed": asdict(
            compare_stable_sets(passed[CANDIDATE_A_ID], passed[CANDIDATE_B_ID])
        ),
    }
    plan = {
        "status": "publish_ready" if args.apply else "dry_run_ready",
        "analysis_session": ANALYSIS_SESSION.isoformat(),
        "membership_evidence_as_of_date": MEMBERSHIP_DATE.isoformat(),
        "trailing_input": {
            "metric": EXPECTED_METRIC,
            "decision": EXPECTED_DECISION,
            "logical": EXPECTED_LOGICAL,
            "descriptor": EXPECTED_DESCRIPTOR,
            "window_sessions": [item.isoformat() for item in tm.window_sessions],
        },
        "set_counts": {
            "legacy": len(legacy),
            "candidate_a_requested": len(requested[CANDIDATE_A_ID]),
            "candidate_b_requested": len(requested[CANDIDATE_B_ID]),
            "candidate_a_passed": len(passed[CANDIDATE_A_ID]),
            "candidate_b_passed": len(passed[CANDIDATE_B_ID]),
        },
        "set_fingerprints": {
            "legacy": membership_fingerprint(legacy),
            "candidate_a_passed": membership_fingerprint(passed[CANDIDATE_A_ID]),
            "candidate_b_passed": membership_fingerprint(passed[CANDIDATE_B_ID]),
            "candidate_b_requested": membership_fingerprint(requested[CANDIDATE_B_ID]),
        },
        "candidate_b_requested_equals_legacy": requested[CANDIDATE_B_ID] == legacy,
        "comparisons": comparisons,
        "difference_reasons": {
            "candidate_a_removed_from_legacy": _removed_reasons(
                legacy - passed[CANDIDATE_A_ID], status_by_id, adrc_ids
            ),
            "candidate_b_removed_from_legacy": _removed_reasons(
                legacy - passed[CANDIDATE_B_ID], status_by_id, frozenset()
            ),
        },
        "override_count": len(overrides),
        "override_fingerprint": bundle.override_fingerprint,
        "overrides": [
            {
                "override_id": str(item.override_id),
                "instrument_id": str(item.instrument_id),
                "decision": item.decision.value,
                "effective_from": item.effective_from.isoformat(),
                "effective_to": None if item.effective_to is None else item.effective_to.isoformat(),
                "reason_code": item.reason_code,
            }
            for item in overrides
        ],
        "final_summaries": [item.model_dump(mode="json") for item in bundle.summaries],
        "final_composition": {
            universe_id: dict(
                sorted(Counter(type_by_id[item] for item in members).items())
            )
            for universe_id, members in bundle.final_memberships.items()
        },
        "historical_gap_audit": gap_audit,
        "edge": edge,
        "external_request_count": 0,
    }
    if not args.apply:
        print(json.dumps(plan, sort_keys=True))
        return 0

    result = ParquetUniverseReviewRepository(DATA_ROOT).publish(
        analysis_session=ANALYSIS_SESSION,
        overrides=overrides,
        decisions=bundle.decisions,
        summaries=bundle.summaries,
        membership_evidence_as_of_date=MEMBERSHIP_DATE,
        trailing_logical_fingerprint=tm.logical_content_fingerprint,
        trailing_decision_fingerprint=tm.decision_dataset.content_fingerprint,
        legacy_count=len(legacy),
        legacy_membership_fingerprint=membership_fingerprint(legacy),
        legacy_analysis_session=MEMBERSHIP_DATE,
        legacy_previous_session=LEGACY_PREVIOUS_SESSION,
        legacy_current_eod_fingerprint=legacy_current.content_fingerprint,
        legacy_previous_eod_fingerprint=legacy_previous.content_fingerprint,
        created_at=created_at,
    )
    completed = read_completed_universe_review(
        DATA_ROOT, analysis_session=ANALYSIS_SESSION, validate_source=True
    )
    if completed.manifest.logical_content_fingerprint != result.logical_content_fingerprint:
        raise RuntimeError("formal production reader did not reproduce the publication")
    plan.update(
        {
            "status": "published",
            "override_dataset_path": result.override_path.relative_to(DATA_ROOT).as_posix(),
            "review_dataset_path": result.review_path.relative_to(DATA_ROOT).as_posix(),
            "logical_manifest_path": result.logical_manifest_path.relative_to(DATA_ROOT).as_posix(),
            "override_content_fingerprint": result.override_content_fingerprint,
            "review_content_fingerprint": result.review_content_fingerprint,
            "override_parquet_sha256": result.override_parquet_sha256,
            "review_parquet_sha256": result.review_parquet_sha256,
            "logical_content_fingerprint": result.logical_content_fingerprint,
        }
    )
    print(json.dumps(plan, sort_keys=True))
    return 0


def _require_targets_absent(root: Path) -> None:
    suffix = f"schema_version=1/analysis_session={ANALYSIS_SESSION.isoformat()}"
    targets = (
        root / f"market-data/derived/reviewed-universe-eligibility-overrides/{suffix}",
        root / f"market-data/derived/universe-pre-activation-review/{suffix}",
        root / f"market-data/snapshots/universe-pre-activation-review/analysis_session={ANALYSIS_SESSION.isoformat()}",
    )
    if any(item.exists() or item.is_symlink() for item in targets):
        raise RuntimeError("Universe review target already exists or is a symlink")
    for target in targets:
        if target.parent.exists() and any(target.parent.glob(f".{target.name}.staging-*")):
            raise RuntimeError("Universe review staging residue exists")


def _legacy_ids(repository: CanonicalEodReadRepository):
    current_integrity = repository.inspect_session(MEMBERSHIP_DATE)
    previous_integrity = repository.inspect_session(LEGACY_PREVIOUS_SESSION)
    current = {item.instrument_id: item for item in repository.read_bars(MEMBERSHIP_DATE)}
    previous = {item.instrument_id: item for item in repository.read_bars(LEGACY_PREVIOUS_SESSION)}
    members = frozenset(
        instrument_id
        for instrument_id in current.keys() & previous.keys()
        if current[instrument_id].instrument_type.value == "common_stock"
        and current[instrument_id].primary_exchange in SUPPORTED_EXCHANGES
        and not (set(current[instrument_id].quality_flags) & MATERIAL_QUALITY_FLAGS)
        and previous[instrument_id].close >= MINIMUM_PREVIOUS_CLOSE
        and previous[instrument_id].close * previous[instrument_id].volume
        >= MINIMUM_PREVIOUS_DOLLAR_VOLUME
    )
    return members, current_integrity, previous_integrity


def _removed_reasons(
    ids: frozenset[UUID], status: dict[UUID, str], adrc_ids: frozenset[UUID]
) -> dict[str, int]:
    mapping = {
        "below_liquidity": "below_trailing_liquidity",
        "below_price": "below_previous_close",
        "missing_previous_bar": "missing_previous_bar",
        "insufficient_history": "insufficient_history",
        "quarantined_or_invalid_input": "missing_or_invalid_evidence",
    }
    counts = Counter(
        "adrc_not_in_common_share_universe"
        if item in adrc_ids
        else mapping.get(status.get(item, ""), "other")
        for item in ids
    )
    return dict(sorted(counts.items()))


def _audit_gaps(repository, sessions, records, ticker_by_id, type_by_id):
    gap_records = {
        item.instrument_id: item
        for item in records
        if item.universe_id == CANDIDATE_B_ID
        and item.eligibility_status
        in {ShadowEligibilityStatus.INSUFFICIENT_HISTORY, ShadowEligibilityStatus.MISSING_PREVIOUS_BAR}
    }
    bars_by_id = {instrument_id: set() for instrument_id in gap_records}
    identity_by_session = {}
    root = repository._validated_root()
    for source in sessions:
        for bar in repository.read_bars(source):
            if bar.instrument_id in bars_by_id:
                bars_by_id[bar.instrument_id].add(source)
        identity_by_session[source] = frozenset(
            repository._read_instruments(root, as_of_date=source)
        )
    output = []
    for instrument_id, decision in sorted(gap_records.items(), key=lambda item: str(item[0])):
        observed = bars_by_id[instrument_id]
        missing = tuple(session for session in sessions if session not in observed)
        if decision.eligibility_status is ShadowEligibilityStatus.MISSING_PREVIOUS_BAR:
            reason = "no_previous_session_bar"
        elif any(instrument_id in identity_by_session[session] for session in missing):
            reason = "missing_canonical_bar"
        elif missing and any(instrument_id not in identity_by_session[session] for session in missing):
            reason = "identity_not_resolved_for_session"
        else:
            reason = "insufficient_local_evidence"
        output.append(
            {
                "instrument_id": str(instrument_id),
                "display_ticker": ticker_by_id[instrument_id],
                "provider_type_code": type_by_id[instrument_id],
                "eligibility_status": decision.eligibility_status.value,
                "observation_count": len(observed),
                "missing_sessions": [item.isoformat() for item in missing],
                "reason_code": reason,
            }
        )
    if Counter(item["eligibility_status"] for item in output) != {
        "insufficient_history": 9,
        "missing_previous_bar": 1,
    }:
        raise RuntimeError("historical-gap reconciliation mismatch")
    return output


def _edge_audit(*, security, ticker_by_id, type_by_id, legacy, requested, passed, status_by_id, overrides, final):
    observations = {}
    for item in security.observations:
        if item.provider_ticker in {"VCX", "AKAN", "BCPC", "TPC", "VXT", "AZ"}:
            observations.setdefault(item.provider_ticker, []).append(
                [item.provider_type_code, item.observation_status.value]
            )
    by_ticker = {
        ticker: instrument_id
        for instrument_id, ticker in ticker_by_id.items()
        if ticker in {"VCX", "AKAN", "BCPC", "TPC", "VXT", "AZ"}
    }
    output = {}
    for ticker in ("VCX", "AKAN", "BCPC", "TPC", "VXT", "AZ"):
        instrument_id = by_ticker.get(ticker)
        active = next(
            (
                item
                for item in overrides
                if item.instrument_id == instrument_id and item.is_effective_on(ANALYSIS_SESSION)
            ),
            None,
        )
        output[ticker] = {
            "canonical_instrument": instrument_id is not None,
            "instrument_id": None if instrument_id is None else str(instrument_id),
            "provider_type_code": None if instrument_id is None else type_by_id[instrument_id],
            "provider_observations": sorted(observations.get(ticker, [])),
            "legacy": instrument_id in legacy if instrument_id else False,
            "candidate_a_requested": instrument_id in requested[CANDIDATE_A_ID] if instrument_id else False,
            "candidate_a_passed": instrument_id in passed[CANDIDATE_A_ID] if instrument_id else False,
            "candidate_b_requested": instrument_id in requested[CANDIDATE_B_ID] if instrument_id else False,
            "candidate_b_passed": instrument_id in passed[CANDIDATE_B_ID] if instrument_id else False,
            "trailing_status": status_by_id.get(instrument_id),
            "override_decision": None if active is None else active.decision.value,
            "override_reason": None if active is None else active.reason_code,
            "primary_final": instrument_id in final[CANDIDATE_A_ID] if instrument_id else False,
            "secondary_final": instrument_id in final[CANDIDATE_B_ID] if instrument_id else False,
        }
    return output


if __name__ == "__main__":
    raise SystemExit(main())
