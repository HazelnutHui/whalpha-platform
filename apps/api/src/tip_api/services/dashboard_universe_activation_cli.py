"""Default-dry-run Dashboard Universe Activation V1 publisher."""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationRecordV1, SecurityTypeCountV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.trailing_liquidity import read_completed_trailing_liquidity_publication
from tip_api.persistence.parquet.dashboard_universe_activation import PUBLIC_SECONDARY_ID, ParquetDashboardUniverseActivationRepository, _read_review_members, _read_review_records, read_completed_dashboard_universe_activation
from tip_api.persistence.parquet.universe_review import read_completed_universe_review
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID

ROOT=Path("/data/trading-intelligence-platform"); SESSION=date(2026,8,19)

@dataclass(frozen=True, slots=True)
class ActivationInputs:
    records: tuple[DashboardUniverseActivationRecordV1, ...]
    legacy_count: int
    legacy_fingerprint: str
    trailing_window_start: date
    trailing_window_end: date
    trailing_window_session_count: int
    reviewed_override_count: int
    activated_at: datetime

def main(argv:list[str]|None=None)->int:
    args=list(sys.argv[1:] if argv is None else argv)
    if args in (["--help"],["-h"]): print("Usage: publish-dashboard-universe-activation.sh [--apply]"); return 0
    if args not in ([],["--apply"]): print("only --apply is accepted",file=sys.stderr); return 2
    apply=args==["--apply"]
    inputs=_prepare_inputs()
    records=inputs.records
    result={"mode":"apply" if apply else "dry-run","analysis_session":SESSION.isoformat(),"default_universe_id":CANDIDATE_A_ID,"universes":[{"universe_id":x.universe_id,"member_count":x.member_count,"composition":{y.provider_type_code:y.count for y in x.security_type_composition},"membership_fingerprint":x.membership_fingerprint} for x in records],"legacy_count":inputs.legacy_count,"legacy_fingerprint":inputs.legacy_fingerprint}
    if not apply: print(json.dumps(result,sort_keys=True)); return 0
    published=ParquetDashboardUniverseActivationRepository(ROOT).publish(records=records,legacy_count=inputs.legacy_count,legacy_fingerprint=inputs.legacy_fingerprint,trailing_window_start=inputs.trailing_window_start,trailing_window_end=inputs.trailing_window_end,trailing_window_session_count=inputs.trailing_window_session_count,reviewed_override_count=inputs.reviewed_override_count,activated_at=inputs.activated_at)
    completed=read_completed_dashboard_universe_activation(ROOT,analysis_session=SESSION,validate_sources=True)
    if len(completed.universes)!=2: raise RuntimeError("activation final formal reread failed")
    result.update({"status":"completed","content_fingerprint":published.content_fingerprint,"parquet_sha256":published.parquet_sha256,"logical_content_fingerprint":published.logical_content_fingerprint})
    print(json.dumps(result,sort_keys=True)); return 0

def _prepare_inputs()->ActivationInputs:
    review=read_completed_universe_review(ROOT,analysis_session=SESSION,validate_source=True)
    trailing=read_completed_trailing_liquidity_publication(ROOT,analysis_session=SESSION,validate_sources=True)
    members=_read_review_members(ROOT,review.manifest.review_dataset.dataset_path)
    review_records=_read_review_records(ROOT,review.manifest.review_dataset.dataset_path)
    summaries={x.universe_id:x for x in review.manifest.universes}
    eod=CanonicalEodReadRepository(ROOT); current=eod.inspect_session(SESSION); previous=eod.inspect_session(date(2026,8,18))
    rows=[]; activated=datetime.now(UTC)
    definitions=((CANDIDATE_A_ID,CANDIDATE_A_ID,"Common Shares","Provider-Classified Common Shares (Provisional)","Provider-classified common shares passing price, 20-session median dollar-volume, history, and reviewed eligibility rules.",True),(PUBLIC_SECONDARY_ID,CANDIDATE_B_ID,"Common Shares + ADRs","Provider-Classified Common Shares + ADRs","Adds qualifying American Depositary Receipts to the same screened common-share universe.",False))
    for public_id,source_id,short,long,description,is_default in definitions:
        ids=members[source_id]
        counts=Counter(item.provider_type_code for item in review_records if item.universe_id==source_id and item.final_included)
        summary=summaries[source_id]
        if len(ids)!=summary.final_count: raise RuntimeError("review membership count mismatch")
        rows.append(DashboardUniverseActivationRecordV1(activation_id=uuid5(NAMESPACE_URL,f"tip:dashboard-universe-activation:{SESSION}:{public_id}"),analysis_session=SESSION,membership_evidence_as_of=review.manifest.membership_evidence_as_of_date,activated_at=activated,universe_id=public_id,display_name=short,long_display_name=long,description=description,is_default=is_default,member_count=len(ids),security_type_composition=tuple(SecurityTypeCountV1(provider_type_code=k,count=v) for k,v in sorted(counts.items())),membership_fingerprint=summary.membership_fingerprint,trailing_liquidity_source_fingerprint=review.manifest.trailing_decision_fingerprint,reviewed_override_source_fingerprint=review.manifest.override_dataset.content_fingerprint,pre_activation_review_fingerprint=review.manifest.logical_content_fingerprint,current_eod_fingerprint=current.content_fingerprint,previous_eod_fingerprint=previous.content_fingerprint,legacy_rollback_reference=f"market-data/snapshots/universe-pre-activation-review/analysis_session={SESSION.isoformat()}",limitations=("provider security form does not prove issuer domicile","issuer structure remains incompletely verified","adjustment factors unverified","close times volume is a proxy, not fund flow")))
    records=tuple(rows)
    if records[0].member_count!=1641 or dict((x.provider_type_code,x.count) for x in records[0].security_type_composition)!={"CS":1641}: raise RuntimeError("Primary hard gate failed")
    if records[1].member_count!=1747 or dict((x.provider_type_code,x.count) for x in records[1].security_type_composition)!={"ADRC":106,"CS":1641}: raise RuntimeError("Secondary hard gate failed")
    return ActivationInputs(records,review.manifest.legacy_count,review.manifest.legacy_membership_fingerprint,trailing.manifest.window_sessions[0],trailing.manifest.window_sessions[-1],len(trailing.manifest.window_sessions),review.manifest.override_dataset.record_count,activated)

if __name__=="__main__": raise SystemExit(main())
