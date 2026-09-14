from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_adjudication as service,
)


def _fixture(sequence: int, tmp_path: Path):
    spec = service.residual_plan._RESIDUAL_SPECS[sequence]
    target = UUID(int=sequence)
    proposed = UUID(int=1000 + sequence)
    plan_fingerprint = f"{sequence:064x}"
    original_artifact_fingerprint = f"{sequence + 1:064x}"
    original_document_sha = f"{sequence + 2:064x}"
    identity_fingerprint = f"{sequence + 3:064x}"
    completion_fingerprint = f"{sequence + 4:064x}"
    completion_document_sha = f"{sequence + 5:064x}"
    completion_text = (
        "At completion of the merger, each "
        f"{spec.target_security_term} was converted into "
        f"{spec.expected_ratio.rstrip('0')} shares of "
        f"{spec.consideration_security_term}."
    )
    completion_evidence_sha = service.residual_plan._sha256_bytes(
        completion_text.encode()
    )
    plan = SimpleNamespace(
        request_sequence=sequence,
        target_instrument_id=target,
        proposed_consideration_instrument_id=proposed,
        proposed_cik=f"{sequence:010d}",
        canonical_cik=f"{sequence:010d}",
        canonical_source_instrument_id=f"share_class_figi:fixture-{sequence}",
        logical_fingerprint=plan_fingerprint,
    )
    original_artifact = SimpleNamespace(
        logical_fingerprint=original_artifact_fingerprint,
        physical_sha256=original_document_sha,
        plan_decision_fingerprint=plan_fingerprint,
    )
    prior_text = (
        f"In the merger, {spec.target_security_term} is exchanged for "
        f"{spec.consideration_security_term} under a variable formula."
    )
    prior_evidence = service.prior._evidence_span(
        prior_text,
        0,
        len(prior_text),
        (
            "non_transaction_offering_scope"
            if sequence == 174
            else "variable_exchange_formula_clause"
        ),
    )
    identity = SimpleNamespace(
        request_sequence=sequence,
        target_instrument_id=target,
        proposed_consideration_instrument_id=proposed,
        proposed_cik=plan.proposed_cik,
        plan_decision_fingerprint=plan_fingerprint,
        logical_fingerprint=identity_fingerprint,
        resolution_state=spec.prior_resolution_state,
        expected_exchange_ratio=spec.expected_ratio,
        sec_filer_cik_to_canonical_common_security_match=True,
        transaction_match=sequence != 174,
        target_common_security_match=sequence != 174,
        consideration_security_class_match=sequence != 174,
        registered_exchange_ratio_match=False,
        exact_ratio_occurrence_count=0,
        evidence=prior_evidence,
    )
    planned = SimpleNamespace(
        request_sequence=sequence,
        target_instrument_id=target,
        proposed_consideration_instrument_id=proposed,
        proposed_cik=plan.proposed_cik,
        resolution_path=spec.resolution_path,
        original_plan_decision_fingerprint=plan_fingerprint,
        prior_identity_decision_fingerprint=identity_fingerprint,
        prior_identity_resolution_state=spec.prior_resolution_state,
        original_registration_artifact_fingerprint=(
            original_artifact_fingerprint
        ),
        original_registration_document_sha256=original_document_sha,
        completion_consideration_fingerprint=completion_fingerprint,
        completion_disclosure_accession_number=(
            f"0000000001-26-{sequence:06d}"
        ),
        completion_disclosure_acceptance_datetime=datetime(
            2026, 9, 14, 5, tzinfo=UTC
        ),
        completion_disclosure_document_sha256=completion_document_sha,
        completion_consideration_evidence_sha256=completion_evidence_sha,
        expected_exchange_ratio=spec.expected_ratio,
        logical_fingerprint=f"{sequence + 6:064x}",
    )
    consideration = SimpleNamespace(
        request_sequence=sequence,
        instrument_id=target,
        resolution_state="matched",
        evidence_text=completion_text,
        evidence_sha256=completion_evidence_sha,
        logical_fingerprint=completion_fingerprint,
        accession_number=planned.completion_disclosure_accession_number,
        acceptance_datetime=planned.completion_disclosure_acceptance_datetime,
        document_sha256=completion_document_sha,
    )
    replacement_artifact = None
    replacement_path = None
    if sequence == 174:
        replacement_text = (
            "<html><body>In the merger, each "
            f"{spec.target_security_term} will be converted into the right "
            f"to receive {spec.expected_ratio.rstrip('0')} shares of "
            f"{spec.consideration_security_term}.</body></html>"
        )
        raw = replacement_text.encode()
        replacement_path = tmp_path / "replacement.htm"
        replacement_path.write_bytes(raw)
        replacement_artifact = SimpleNamespace(
            logical_fingerprint=f"{sequence + 7:064x}",
            physical_sha256=service.residual_plan._sha256_bytes(raw),
        )
    return SimpleNamespace(
        plan=plan,
        original_artifact=original_artifact,
        identity=identity,
        planned=planned,
        consideration=consideration,
        replacement_artifact=replacement_artifact,
        replacement_path=replacement_path,
    )


def _decision(fixture: SimpleNamespace):
    return service._adjudicate_decision(
        plan=fixture.plan,
        original_artifact=fixture.original_artifact,
        identity=fixture.identity,
        planned=fixture.planned,
        consideration=fixture.consideration,
        replacement_artifact=fixture.replacement_artifact,
        replacement_document_path=fixture.replacement_path,
    )


def test_three_complementary_evidence_paths_assign_exact_candidates(
    tmp_path: Path,
) -> None:
    decisions = tuple(
        _decision(_fixture(sequence, tmp_path))
        for sequence in sorted(service.residual_plan._RESIDUAL_SPECS)
    )

    assert {item.request_sequence for item in decisions} == {158, 174, 184}
    assert all(item.composite_evidence_match for item in decisions)
    assert all(
        item.consideration_security_identity_assignment_count == 1
        for item in decisions
    )
    assert next(
        item for item in decisions if item.request_sequence == 174
    ).registration_direct_final_ratio_match
    assert all(
        not item.registration_direct_final_ratio_match
        for item in decisions
        if item.request_sequence in {158, 184}
    )


def test_changed_completion_ratio_remains_unassigned(tmp_path: Path) -> None:
    fixture = _fixture(158, tmp_path)
    fixture.consideration.evidence_text = fixture.consideration.evidence_text.replace(
        "0.4883", "0.4999"
    )

    decision = _decision(fixture)

    assert decision.resolution_state == "required_evidence_not_matched"
    assert decision.assigned_consideration_instrument_id is None
    assert not decision.completion_final_ratio_match


def test_changed_replacement_ratio_remains_unassigned(tmp_path: Path) -> None:
    fixture = _fixture(174, tmp_path)
    raw = fixture.replacement_path.read_bytes().replace(b"1.8663", b"1.9000")
    fixture.replacement_path.write_bytes(raw)
    fixture.replacement_artifact.physical_sha256 = service.residual_plan._sha256_bytes(
        raw
    )

    decision = _decision(fixture)

    assert decision.resolution_state == "required_evidence_not_matched"
    assert decision.assigned_consideration_instrument_id is None
    assert not decision.registration_direct_final_ratio_match


def test_report_is_owner_only_and_idempotent(tmp_path: Path) -> None:
    decisions = tuple(
        _decision(_fixture(sequence, tmp_path))
        for sequence in sorted(service.residual_plan._RESIDUAL_SPECS)
    )
    states = service.Counter(item.resolution_state for item in decisions)
    values = {
        "implementation_revision": "a" * 40,
        "evaluated_at": datetime(2026, 9, 14, 6, tzinfo=UTC),
        "ruleset_fingerprint": service._ruleset_fingerprint(),
        "original_plan_report_sha256": "1" * 64,
        "original_plan_logical_fingerprint": "2" * 64,
        "original_source_manifest_sha256": "3" * 64,
        "original_source_logical_fingerprint": "4" * 64,
        "prior_identity_report_sha256": "5" * 64,
        "prior_identity_logical_fingerprint": "6" * 64,
        "residual_plan_report_sha256": "7" * 64,
        "residual_plan_logical_fingerprint": "8" * 64,
        "residual_source_manifest_sha256": "9" * 64,
        "residual_source_logical_fingerprint": "a" * 64,
        "consideration_report_sha256": "b" * 64,
        "consideration_logical_fingerprint": "c" * 64,
        "residual_matched_identity_count": 3,
        "cumulative_matched_identity_count": 12,
        "required_evidence_not_matched_count": 0,
        "resolution_state_counts": service._ordered(states),
        "decisions": decisions,
        "consideration_security_identity_assignment_count": 3,
    }
    model = service.StrongLeaderPullbackListedConsiderationResidualAdjudicationV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    report = model.model_validate(
        {
            **values,
            "logical_fingerprint": service.residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )
    custody = tmp_path / "reports"
    custody.mkdir(mode=0o700)
    target = custody / "adjudication=fixture"

    first = service._write_report(
        output_root=target, output_custody_root=custody, report=report
    )
    second = service._write_report(
        output_root=target, output_custody_root=custody, report=report
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400
