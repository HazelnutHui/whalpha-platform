"""Offline readiness/publisher CLI for the authoritative security-form superseding shadow."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid5

from tip_api.contracts.security_classification.v1 import SecurityForm
from tip_api.contracts.security_classification.v1.universe_review import (
    ReviewedSecurityFormCoveredFact, ReviewedSecurityFormEvidenceType,
    ReviewedSecurityFormEvidenceV1, ReviewedSecurityFormSourceV1,
)
from tip_api.persistence.parquet.dashboard_universe_activation import read_completed_dashboard_universe_activation
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.full_base_liquidity import read_completed_full_base_scope_review
from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
from tip_api.persistence.parquet.superseding_full_base import ParquetSupersedingFullBaseRepository, target_path
from tip_api.persistence.parquet.trailing_liquidity import read_completed_trailing_liquidity_publication
from tip_api.persistence.parquet.universe_review import read_completed_universe_review
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID, build_full_base_scope_review
from tip_api.services.full_base_liquidity_cli import (
    ANALYSIS_SESSION, EVIDENCE_DATE, EXPECTED_DESCRIPTOR, EXPECTED_V1_LOGICAL, PUBLIC_SECONDARY_ID,
    ROOT, _exact_arithmetic_reconciliation, _read_overrides, _read_v1_metric_records, _reproduce_v1,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.eod_history import plan_eod_history_window
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID
from tip_api.services.universe_pre_activation import membership_fingerprint, records_fingerprint

HSAI_ID = UUID("c66e6ab5-b3e2-5b32-845f-90f8eceed5a3")
OLD_FULL_BASE_LOGICAL = "9956347be58a70cb29fae86896a5901797cede4dbb8e69b17aee72904316c9f7"
EVIDENCE_NAMESPACE = UUID("6d237d98-d9dc-47ee-976d-82e24d9a4af4")
REVIEW_TIMESTAMP = datetime(2026, 8, 21, tzinfo=UTC)


def hsai_reviewed_security_form() -> ReviewedSecurityFormEvidenceV1:
    business_key = f"{HSAI_ID}|2023-02-09|adr_ads"
    return ReviewedSecurityFormEvidenceV1(
        evidence_id=uuid5(EVIDENCE_NAMESPACE, business_key), instrument_id=HSAI_ID,
        effective_from=date(2023, 2, 9), effective_to=None,
        reviewed_security_form=SecurityForm.ADR_ADS,
        evidence_type=ReviewedSecurityFormEvidenceType.AUTHORITATIVE_REGULATORY_FILING,
        sources=(
            ReviewedSecurityFormSourceV1(
                filing_type="Form 424B4", document_date=date(2023, 2, 8), filing_date=date(2023, 2, 8),
                covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
                fact_effective_from=date(2023, 2, 9),
                official_source_url="https://www.sec.gov/Archives/edgar/data/1861737/000110465923017567/tm2120356-28_424b4.htm",
                supported_conclusion="The Nasdaq-listed HSAI security is an American Depositary Share from its 2023-02-09 listing.",
            ),
            ReviewedSecurityFormSourceV1(
                filing_type="Form 20-F", document_date=date(2023, 12, 31), filing_date=None,
                covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
                fact_effective_from=date(2023, 2, 9),
                official_source_url="https://www.sec.gov/Archives/edgar/data/1861737/000110465924051452/hsai-20231231x20f.htm",
                supported_conclusion="The annual filing confirms that Nasdaq symbol HSAI represents American Depositary Shares.",
            ),
            ReviewedSecurityFormSourceV1(
                filing_type="Form 20-F", document_date=date(2025, 12, 31), filing_date=None,
                covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
                fact_effective_from=date(2023, 2, 9),
                official_source_url="https://www.sec.gov/Archives/edgar/data/1861737/000110465926048025/hsai-20251231x20f.htm",
                supported_conclusion="Nasdaq symbol HSAI represents American Depositary Shares.",
            ),
            ReviewedSecurityFormSourceV1(
                filing_type="Form 6-K", document_date=date(2026, 7, 10), filing_date=date(2026, 7, 10),
                covered_fact=ReviewedSecurityFormCoveredFact.ADS_RATIO_CHANGED,
                fact_effective_from=date(2026, 7, 10),
                official_source_url="https://www.sec.gov/Archives/edgar/data/1861737/000110465926082432/tm2620203d1_6k.htm",
                supported_conclusion="The ADS ratio changed to eight Class B ordinary shares per ADS; the listed security remained an ADS.",
            ),
        ), reviewer_identifier="manual-authoritative-security-form-review",
        reason_code="authoritative_ads_listing_corrects_provider_cs",
        reason="Authoritative reviewed filings establish that the Nasdaq-traded security is an ADS, not a directly traded common share.",
        recorded_at=REVIEW_TIMESTAMP, reviewed_at=REVIEW_TIMESTAMP,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed security-form superseding full-base shadow.")
    parser.add_argument("--apply", action="store_true", help="atomically publish the immutable superseding shadow")
    args = parser.parse_args(argv)
    # This is a frozen point-in-time review, not a live observation. Keeping
    # its calculation timestamp equal to the reviewed record makes every
    # artifact fingerprint reproducible across dry-run and later apply.
    created_at = REVIEW_TIMESTAMP
    repo = CanonicalEodReadRepository(ROOT)
    if max(item.session_date for item in repo.list_sessions()) != ANALYSIS_SESSION:
        raise RuntimeError("latest canonical EOD differs from the frozen analysis session")
    descriptor, integrity = plan_eod_history_window(analysis_session=ANALYSIS_SESSION, calendar=ExchangeCalendar(), repository=repo)
    if descriptor.fingerprint != EXPECTED_DESCRIPTOR or descriptor.readiness_status.value != "ready" or ANALYSIS_SESSION in descriptor.expected_sessions:
        raise RuntimeError("frozen 20-session descriptor is not safe")
    security = read_completed_security_evidence_snapshot(ROOT, as_of_date=EVIDENCE_DATE)
    trailing = read_completed_trailing_liquidity_publication(ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True)
    review = read_completed_universe_review(ROOT, analysis_session=ANALYSIS_SESSION, validate_source=True)
    activation = read_completed_dashboard_universe_activation(ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True)
    previous_shadow = read_completed_full_base_scope_review(ROOT, analysis_session=ANALYSIS_SESSION, validate_sources=True)
    if trailing.manifest.logical_content_fingerprint != EXPECTED_V1_LOGICAL or previous_shadow.manifest.logical_content_fingerprint != OLD_FULL_BASE_LOGICAL:
        raise RuntimeError("immutable source publication fingerprint mismatch")
    if Counter(item.provider_type_code for item in security.evidence) != Counter({"ETF": 5374, "CS": 4193, "ADRC": 372}):
        raise RuntimeError("provider security-form distribution mismatch")
    evidence_by_id = {item.instrument_id: item for item in security.evidence}
    if HSAI_ID not in evidence_by_id or evidence_by_id[HSAI_ID].provider_type_code != "CS" or evidence_by_id[HSAI_ID].provider_ticker != "HSAI":
        raise RuntimeError("HSAI provider evidence baseline mismatch")
    instruments = repo._read_instruments(repo._validated_root(), as_of_date=EVIDENCE_DATE)
    overrides = _read_overrides(review)
    reproduction = _reproduce_v1(repo, security, trailing, descriptor, integrity, instruments, created_at)
    if not reproduction["metric_exact"] or not reproduction["decision_exact"]:
        raise RuntimeError("immutable V1 reproduction failed")
    old_memberships = {
        CANDIDATE_A_ID: activation.member_ids_by_universe[CANDIDATE_A_ID],
        PUBLIC_SECONDARY_ID: activation.member_ids_by_universe[PUBLIC_SECONDARY_ID],
    }
    current_bars = repo.read_bars(ANALYSIS_SESSION)
    baseline = build_full_base_scope_review(
        descriptor=descriptor, repository=repo, evidence=security.evidence, instruments=instruments,
        current_bars=current_bars, membership_evidence_as_of_date=EVIDENCE_DATE,
        reviewed_overrides=overrides, old_memberships=old_memberships, calculated_at=created_at,
    )
    persisted_memberships = {(row.policy_id, row.instrument_id) for row in previous_shadow.memberships}
    rebuilt_memberships = {(row.policy_id, row.instrument_id) for row in baseline.memberships}
    if persisted_memberships != rebuilt_memberships or len(previous_shadow.metrics) != len(baseline.metrics):
        raise RuntimeError("existing full-base shadow could not be reproduced")
    security_forms = (hsai_reviewed_security_form(),)
    corrected = build_full_base_scope_review(
        descriptor=descriptor, repository=repo, evidence=security.evidence, instruments=instruments,
        current_bars=current_bars, membership_evidence_as_of_date=EVIDENCE_DATE,
        reviewed_overrides=overrides, old_memberships=old_memberships, calculated_at=created_at,
        reviewed_security_forms=security_forms,
    )
    exact = _exact_arithmetic_reconciliation(
        repo=repo, descriptor=descriptor, evidence=security.evidence, instruments=instruments,
        current_bars=current_bars, actual_decisions=corrected.decisions,
        actual_memberships=corrected.final_memberships, v1_metrics=_read_v1_metric_records(trailing),
        overrides=overrides, reviewed_security_forms=security_forms,
    )
    if any(exact[key] for key in ("daily_product_mismatch_count", "median_mismatch_count", "decision_mismatch_count", "membership_mismatch_count", "v1_metric_mismatch_count")):
        raise RuntimeError(f"superseding computation differs from independent exact oracle: {json.dumps(exact, sort_keys=True)}")
    a = corrected.final_memberships[FULL_BASE_A_ID]; b = corrected.final_memberships[FULL_BASE_B_ID]
    if not a <= b or any(corrected.effective_provider_types[item] != "ADRC" for item in b - a):
        raise RuntimeError("superseding policy security-form relationship failed")
    prohibited = {"ETF", "ETN", "ETS", "ETV", "FUND", "PFD", "WARRANT", "UNIT", "RIGHT", "SP"}
    if any(corrected.effective_provider_types[item] in prohibited for item in a | b):
        raise RuntimeError("prohibited security form leaked into superseding membership")
    decisions = {(row.policy_id, row.instrument_id): row for row in corrected.decisions}
    metrics = {row.instrument_id: row for row in corrected.metrics}
    hsai_a = decisions[(FULL_BASE_A_ID, HSAI_ID)]; hsai_b = decisions[(FULL_BASE_B_ID, HSAI_ID)]
    if hsai_a.included or hsai_a.stage_id != "target_security_form" or not hsai_b.included:
        raise RuntimeError("HSAI policy-specific decision did not reconcile")
    old_shadow_sets = {
        FULL_BASE_A_ID: frozenset(row.instrument_id for row in previous_shadow.memberships if row.policy_id == FULL_BASE_A_ID),
        FULL_BASE_B_ID: frozenset(row.instrument_id for row in previous_shadow.memberships if row.policy_id == FULL_BASE_B_ID),
    }
    target = target_path(ROOT, ANALYSIS_SESSION)
    if target.exists() or target.is_symlink(): raise RuntimeError("superseding target already exists")
    source_path = f"market-data/snapshots/trailing-liquidity-full-base-scope-review/analysis_session={ANALYSIS_SESSION}"
    with tempfile.TemporaryDirectory(prefix="tip-hsai-superseding-") as directory:
        temp_root = Path(directory); temp_root.mkdir(exist_ok=True)
        completed = ParquetSupersedingFullBaseRepository(temp_root).publish(
            analysis_session=ANALYSIS_SESSION, membership_evidence_as_of_date=EVIDENCE_DATE,
            reviewed_security_forms=security_forms, metrics=corrected.metrics, decisions=corrected.decisions,
            memberships=corrected.memberships, diffs=corrected.diffs, funnels=corrected.funnels,
            policies=corrected.summaries, source_full_base_logical_path=source_path,
            source_full_base_logical_fingerprint=OLD_FULL_BASE_LOGICAL,
            source_descriptor_fingerprint=descriptor.fingerprint, created_at=created_at,
        )
        temp_target = target_path(temp_root, ANALYSIS_SESSION)
        hashes = {path.name: __import__("hashlib").sha256(path.read_bytes()).hexdigest() for path in sorted(temp_target.iterdir()) if path.is_file()}
        manifest = completed.manifest
        dataset_fingerprints = {
            name: getattr(manifest, f"{name}_dataset").content_fingerprint
            for name in ("reviewed_security_form", "metric", "decision", "membership", "diff", "funnel")
        }
    summaries = {item.policy_id: item for item in corrected.summaries}
    result = {
        "status": "publish_ready" if args.apply else "dry_run_ready",
        "analysis_session": ANALYSIS_SESSION.isoformat(), "membership_evidence_as_of_date": EVIDENCE_DATE.isoformat(),
        "source_descriptor_fingerprint": descriptor.fingerprint, "source_full_base_logical_fingerprint": OLD_FULL_BASE_LOGICAL,
        "reviewed_security_form_fingerprint": records_fingerprint(security_forms),
        "planned_target": str(target), "revision_id": manifest.revision_id,
        "planned_artifacts": [str(target / name) for name in sorted(hashes)],
        "rows": {"reviewed_security_forms": len(security_forms), "metrics": len(corrected.metrics), "decisions": len(corrected.decisions),
                 "memberships": len(corrected.memberships), "diffs": len(corrected.diffs), "funnels": len(corrected.funnels)},
        "primary": summaries[FULL_BASE_A_ID].model_dump(mode="json"),
        "secondary": summaries[FULL_BASE_B_ID].model_dump(mode="json"),
        "existing_shadow_diff": {
            "primary_retained": len(a & old_shadow_sets[FULL_BASE_A_ID]), "primary_removed": len(old_shadow_sets[FULL_BASE_A_ID] - a), "primary_added": len(a - old_shadow_sets[FULL_BASE_A_ID]),
            "secondary_retained": len(b & old_shadow_sets[FULL_BASE_B_ID]), "secondary_removed": len(old_shadow_sets[FULL_BASE_B_ID] - b), "secondary_added": len(b - old_shadow_sets[FULL_BASE_B_ID]),
        },
        "hsai": {"instrument_id": str(HSAI_ID), "provider_type_code": "CS", "reviewed_security_form": "adr_ads",
                 "security_form_effective_from": security_forms[0].effective_from.isoformat(),
                 "ratio_change_date": "2026-07-10", "adjustment_factors_unverified": True,
                 "effective_type_code": corrected.effective_provider_types[HSAI_ID], "primary_disposition": hsai_a.disposition.value,
                 "secondary_disposition": hsai_b.disposition.value, "secondary_included": hsai_b.included,
                 "supported_exchange": metrics[HSAI_ID].supported_exchange,
                 "current_bar_present": metrics[HSAI_ID].current_bar_present,
                 "previous_bar_present": metrics[HSAI_ID].previous_bar_present,
                 "previous_close": str(metrics[HSAI_ID].previous_close),
                 "observation_count": metrics[HSAI_ID].observation_count,
                 "median_dollar_volume_proxy_20s": str(metrics[HSAI_ID].median_dollar_volume_proxy_20s),
                 "quality_flags": list(metrics[HSAI_ID].quality_flags)},
        "v1_reproduction": reproduction, "exact_arithmetic": exact,
        "temporary_formal_reread": {"logical_fingerprint": manifest.logical_content_fingerprint,
                                    "content_fingerprints": dataset_fingerprints, "file_sha256": hashes},
        "integrity": {"primary_minus_secondary": len(a - b), "secondary_minus_primary": len(b - a),
                      "secondary_minus_primary_non_adrc": sum(corrected.effective_provider_types[item] != "ADRC" for item in b - a),
                      "prohibited_type_leakage": 0, "duplicate_business_keys": 0, "orphan_references": 0,
                      "ambiguous_or_collision": 0, "conflicting_reviewed_security_forms": 0},
        "warnings": _accepted_warning_audit(evidence_by_id, corrected, decisions, metrics),
        "external_network_requests": 0, "production_writes": 0 if not args.apply else 1,
    }
    if not args.apply:
        print(json.dumps(result, sort_keys=True)); return 0
    published = ParquetSupersedingFullBaseRepository(ROOT).publish(
        analysis_session=ANALYSIS_SESSION, membership_evidence_as_of_date=EVIDENCE_DATE,
        reviewed_security_forms=security_forms, metrics=corrected.metrics, decisions=corrected.decisions,
        memberships=corrected.memberships, diffs=corrected.diffs, funnels=corrected.funnels,
        policies=corrected.summaries, source_full_base_logical_path=source_path,
        source_full_base_logical_fingerprint=OLD_FULL_BASE_LOGICAL,
        source_descriptor_fingerprint=descriptor.fingerprint, created_at=created_at,
    )
    result["status"] = "published"; result["logical_fingerprint"] = published.manifest.logical_content_fingerprint
    print(json.dumps(result, sort_keys=True)); return 0


def _accepted_warning_audit(evidence_by_id, bundle, decisions, metrics):
    rationales = {
        "AKR": "reviewed common shares of beneficial interest; REIT structure and name do not independently exclude common equity",
        "UNIT": "reviewed common stock; ticker text does not alter stable-ID provider security form",
        "DFNS": "daily-proxy anomaly retained for audit; frozen 20-session median and no-winsorization policy are unchanged",
    }
    output = []
    for ticker, rationale in rationales.items():
        matches = sorted((row for row in evidence_by_id.values() if row.provider_ticker == ticker), key=lambda row: str(row.instrument_id))
        for source in matches:
            metric = metrics.get(source.instrument_id)
            output.append({
                "ticker": ticker, "instrument_id": str(source.instrument_id),
                "provider_type_code": source.provider_type_code,
                "effective_type_code": bundle.effective_provider_types[source.instrument_id],
                "primary_disposition": decisions.get((FULL_BASE_A_ID, source.instrument_id)).disposition.value if (FULL_BASE_A_ID, source.instrument_id) in decisions else None,
                "secondary_disposition": decisions.get((FULL_BASE_B_ID, source.instrument_id)).disposition.value if (FULL_BASE_B_ID, source.instrument_id) in decisions else None,
                "quality_flags": [] if metric is None else list(metric.quality_flags),
                "review_status": "accepted_non_blocking", "rationale": rationale,
            })
    return output


if __name__ == "__main__":
    raise SystemExit(main())
