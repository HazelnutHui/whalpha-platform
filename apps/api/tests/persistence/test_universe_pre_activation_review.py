from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tip_api.contracts.security_classification.v1 import EvidenceGrade, IssuerStructure, SecurityForm
from tip_api.contracts.security_classification.v1.universe_review import ReviewedEligibilityDecision, ReviewedEligibilityOverrideV1, validate_override_intervals
from tip_api.persistence.parquet.universe_review import ParquetUniverseReviewRepository, read_completed_universe_review
from tip_api.persistence.universe_review import UniverseReviewConflictError, UniverseReviewCorruptionError
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.universe_pre_activation import build_universe_review, compare_stable_sets, membership_fingerprint, repository_reviewed_overrides
from tip_api.services.universe_pre_activation_cli import main

NOW=datetime(2026,8,20,6,tzinfo=UTC); SESSION=date(2026,8,19); SHA="a"*64
CS1=UUID("00000000-0000-0000-0000-000000000001"); CS2=UUID("00000000-0000-0000-0000-000000000002"); ADR=UUID("00000000-0000-0000-0000-000000000003")

def override(i=CS1, decision=ReviewedEligibilityDecision.EXCLUDE, start=date(2026,8,1), end=None, grade=EvidenceGrade.AUTHORITATIVE):
    return ReviewedEligibilityOverrideV1(override_id=uuid4(),instrument_id=i,effective_from=start,effective_to=end,decision=decision,
        asserted_security_form=SecurityForm.COMMON_SHARE,asserted_issuer_structure=IssuerStructure.CLOSED_END_FUND,
        evidence_grade=grade,source_reference="repo:audit",source_document_date=date(2026,7,1),reviewer_identifier="reviewer",
        reason_code="reviewed_exclusion",reason="reviewed evidence",created_at=NOW)

def bundle(records=(override(),), order=False):
    passed={CANDIDATE_A_ID:frozenset({CS1,CS2}),CANDIDATE_B_ID:frozenset({CS1,CS2,ADR})}
    if order: passed={CANDIDATE_B_ID:frozenset({ADR,CS2,CS1}),CANDIDATE_A_ID:frozenset({CS2,CS1})}
    return build_universe_review(analysis_session=SESSION,passed_by_universe=passed,provider_type_by_id={CS1:"CS",CS2:"CS",ADR:"ADRC"},trailing_decision_fingerprint=SHA,overrides=records,created_at=NOW)

def test_reviewed_exclusion_and_adr_boundary():
    b=bundle(); assert b.final_memberships[CANDIDATE_A_ID]=={CS2}; assert b.final_memberships[CANDIDATE_B_ID]=={CS2,ADR}
    assert all(x.provider_type_code=="CS" for x in b.decisions if x.universe_id==CANDIDATE_A_ID)
    assert {x.provider_type_code for x in b.decisions if x.universe_id==CANDIDATE_B_ID}<={"CS","ADRC"}

def test_point_in_time_half_open():
    record=override(start=date(2026,8,1),end=SESSION)
    assert not record.is_effective_on(SESSION); assert bundle((record,)).summaries[0].reviewed_exclusion_count==0

def test_overlap_and_conflict_rejected():
    with pytest.raises(ValueError,match="overlap"): validate_override_intervals((override(end=date(2026,9,1)),override(start=date(2026,8,15),decision=ReviewedEligibilityDecision.ALLOW)))

def test_unknown_evidence_cannot_form_override():
    with pytest.raises(ValueError,match="authoritative"): override(grade=EvidenceGrade.INSUFFICIENT)

def test_future_evidence_cannot_backfill_history():
    with pytest.raises(ValueError,match="future evidence"):
        ReviewedEligibilityOverrideV1(override_id=uuid4(),instrument_id=CS1,effective_from=date(2026,7,1),decision=ReviewedEligibilityDecision.EXCLUDE,asserted_security_form=SecurityForm.COMMON_SHARE,asserted_issuer_structure=IssuerStructure.CLOSED_END_FUND,evidence_grade=EvidenceGrade.AUTHORITATIVE,source_reference="repo:audit",source_document_date=date(2026,7,2),reviewer_identifier="reviewer",reason_code="reviewed_exclusion",reason="reviewed",created_at=NOW)

def test_duplicate_override_key_and_id_rejected():
    first=override(); duplicate=first.model_copy(update={"decision":ReviewedEligibilityDecision.ALLOW})
    with pytest.raises(ValueError,match="duplicate override_id"):
        validate_override_intervals((first,duplicate))
    with pytest.raises(ValueError,match="business key"):
        validate_override_intervals((first,override(decision=ReviewedEligibilityDecision.ALLOW)))

def test_quarantine_is_separate_and_allow_does_not_add_failed_members():
    quarantine=override(decision=ReviewedEligibilityDecision.QUARANTINE)
    result=bundle((quarantine,))
    assert result.summaries[0].reviewed_quarantine_count==1
    allow=override(i=UUID(int=99),decision=ReviewedEligibilityDecision.ALLOW)
    allowed=bundle((allow,))
    assert UUID(int=99) not in set().union(*allowed.final_memberships.values())

def test_ticker_not_in_identity_or_join_contract():
    assert "ticker" not in ReviewedEligibilityOverrideV1.model_fields

def test_equal_count_different_membership_is_not_equal():
    other=UUID("00000000-0000-0000-0000-000000000004"); c=compare_stable_sets({CS1,CS2},{CS1,other}); assert c.left_count==c.right_count==2 and (c.removed,c.added)==(1,1) and c.left_fingerprint!=c.right_fingerprint

def test_input_order_and_fingerprint_deterministic():
    a,b=bundle(),bundle(order=True); assert a.final_memberships==b.final_memberships; assert a.summaries==b.summaries

@pytest.mark.parametrize("bad_types",[{CS1:"ETF",CS2:"CS",ADR:"ADRC"},{CS1:"CS",CS2:"CS",ADR:"WARRANT"}])
def test_disallowed_type_rejected(bad_types):
    with pytest.raises(ValueError,match="disallowed"): build_universe_review(analysis_session=SESSION,passed_by_universe={CANDIDATE_A_ID:frozenset({CS1,CS2}),CANDIDATE_B_ID:frozenset({CS1,CS2,ADR})},provider_type_by_id=bad_types,trailing_decision_fingerprint=SHA,overrides=(),created_at=NOW)

def test_orphan_type_reference_rejected():
    with pytest.raises(ValueError,match="no provider type"): build_universe_review(analysis_session=SESSION,passed_by_universe={CANDIDATE_A_ID:frozenset({CS1}),CANDIDATE_B_ID:frozenset({CS1})},provider_type_by_id={},trailing_decision_fingerprint=SHA,overrides=(),created_at=NOW)

def test_historical_gap_records_are_not_hand_added():
    excluded={UUID(int=i) for i in range(20,30)}; b=bundle(); assert not excluded & set().union(*b.final_memberships.values())

def test_repository_reviewed_registry_is_stable_id_based():
    rows=repository_reviewed_overrides(created_at=NOW); assert len(rows)==2; assert {x.decision for x in rows}=={ReviewedEligibilityDecision.EXCLUDE,ReviewedEligibilityDecision.ALLOW}; assert all(x.evidence_grade is EvidenceGrade.AUTHORITATIVE for x in rows)

def publish(root: Path):
    root.mkdir(exist_ok=True); b=bundle(); return ParquetUniverseReviewRepository(root).publish(analysis_session=SESSION,overrides=b.overrides,decisions=b.decisions,summaries=b.summaries,membership_evidence_as_of_date=date(2026,8,14),trailing_logical_fingerprint="b"*64,trailing_decision_fingerprint=SHA,legacy_count=3,legacy_membership_fingerprint=membership_fingerprint({CS1,CS2,ADR}),legacy_analysis_session=date(2026,8,14),legacy_previous_session=date(2026,8,13),legacy_current_eod_fingerprint="c"*64,legacy_previous_eod_fingerprint="d"*64,created_at=NOW)

def test_atomic_publish_schema_hash_fingerprint_and_formal_reread(tmp_path):
    result=publish(tmp_path/"data"); completed=read_completed_universe_review(tmp_path/"data",analysis_session=SESSION,validate_source=False)
    assert completed.override_record_count==1 and completed.review_record_count==5; assert len(result.override_parquet_sha256)==64; assert completed.manifest.logical_content_fingerprint==result.logical_content_fingerprint

def test_existing_target_rejected(tmp_path):
    root=tmp_path/"data"; publish(root)
    with pytest.raises(UniverseReviewConflictError): publish(root)

def test_symlink_root_rejected(tmp_path):
    real=tmp_path/"real"; real.mkdir(); link=tmp_path/"link"; link.symlink_to(real,target_is_directory=True)
    with pytest.raises(UniverseReviewCorruptionError,match="root"): ParquetUniverseReviewRepository(link).publish(analysis_session=SESSION,overrides=(),decisions=(),summaries=(),membership_evidence_as_of_date=date(2026,8,14),trailing_logical_fingerprint=SHA,trailing_decision_fingerprint=SHA,legacy_count=0,legacy_membership_fingerprint=SHA,legacy_analysis_session=date(2026,8,14),legacy_previous_session=date(2026,8,13),legacy_current_eod_fingerprint=SHA,legacy_previous_eod_fingerprint=SHA,created_at=NOW)

def test_no_staging_residue_after_success(tmp_path):
    root=tmp_path/"data"; publish(root); assert not list(root.rglob("*.staging-*")) and not [x for x in root.rglob("*") if ".staging-" in x.name]

def test_cli_unknown_returns_2(monkeypatch):
    with pytest.raises(SystemExit) as unknown: main(["--unknown"])
    assert unknown.value.code==2
