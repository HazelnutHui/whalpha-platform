from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from tip_api.services import (
    strong_leader_pullback_listed_consideration_adjudication as service,
)
from tip_api.services.strong_leader_pullback_listed_consideration_source import (
    ListedConsiderationDocumentArtifactV1,
)


def _document_text(sequence: int) -> str:
    spec = service._CASE_SPECS[sequence]
    target = spec.target_security_terms[0]
    issuer = spec.consideration_security_terms[0]
    if spec.expected_source_state == "direct":
        ratio = spec.expected_ratio.rstrip("0").rstrip(".")
        return (
            "<html><body>In the merger, each "
            f"{target} will be converted into the right to receive {ratio} "
            f"{issuer}. The exchange ratio is fixed.</body></html>"
        )
    if spec.expected_source_state == "formula_only":
        return (
            "<html><body>In the merger, each "
            f"{target} will be converted into the right to receive {issuer}. "
            "The exchange ratio is the quotient obtained by dividing "
            f"{spec.formula_terms[0]} by the {spec.formula_terms[1]} according "
            f"to the registered {spec.formula_terms[2]} formula.</body></html>"
        )
    return (
        "<html><body>Filed Pursuant to Rule 424(b)(3). "
        f"{spec.wrong_scope_terms[0]} fixed rate {spec.wrong_scope_terms[1]} "
        f"and {spec.wrong_scope_terms[2]}.</body></html>"
    )


def _artifact(
    *, sequence: int, raw: bytes, plan: SimpleNamespace
) -> ListedConsiderationDocumentArtifactV1:
    values = {
        "implementation_revision": "a" * 40,
        "request_sequence": sequence,
        "plan_decision_fingerprint": plan.logical_fingerprint,
        "target_instrument_id": plan.target_instrument_id,
        "proposed_consideration_instrument_id": (
            plan.proposed_consideration_instrument_id
        ),
        "proposed_cik": plan.proposed_cik,
        "registration_accession_number": plan.registration_accession_number,
        "request_url": plan.registration_document_url,
        "observed_at": datetime(2026, 9, 14, 2, tzinfo=UTC),
        "content_type": "text/html",
        "byte_count": len(raw),
        "physical_sha256": service._sha256_bytes(raw),
        "retry_count": 0,
    }
    provisional = ListedConsiderationDocumentArtifactV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ListedConsiderationDocumentArtifactV1.model_validate(
        {
            **values,
            "logical_fingerprint": service._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _inputs(tmp_path: Path):
    source_root = tmp_path / "source"
    source_root.mkdir(mode=0o700)
    plan_decisions = []
    payoff_decisions = []
    for index, sequence in enumerate(sorted(service._CASE_SPECS), start=1):
        target_id = UUID(int=index)
        consideration_id = UUID(int=100 + index)
        plan = SimpleNamespace(
            request_sequence=sequence,
            target_instrument_id=target_id,
            proposed_consideration_instrument_id=consideration_id,
            proposed_cik=f"{index:010d}",
            canonical_cik=f"{index:010d}",
            canonical_source_instrument_id=f"share_class_figi:fixture-{index}",
            registration_accession_number=f"9999999999-26-{index:06d}",
            registration_document_url=(
                "https://www.sec.gov/Archives/edgar/data/"
                f"{index}/999999999926{index:06d}/filing-{index}.htm"
            ),
            logical_fingerprint=f"{sequence:064x}",
        )
        raw = _document_text(sequence).encode()
        artifact = _artifact(sequence=sequence, raw=raw, plan=plan)
        request = source_root / f"request={sequence:06d}"
        request.mkdir(mode=0o700)
        document = request / "document.bin"
        document.write_bytes(raw)
        document.chmod(0o400)
        artifact_path = request / "artifact.json"
        artifact_path.write_bytes(
            service._json_bytes(artifact.model_dump(mode="json"))
        )
        artifact_path.chmod(0o400)
        plan_decisions.append(plan)
        payoff_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                terminal_candidate_state=(
                    "listed_security_identity_and_market_value_required"
                ),
                terms=(
                    SimpleNamespace(
                        term_kind="listed_equity_shares_per_target_share",
                        normalized_value=service._CASE_SPECS[sequence].expected_ratio,
                    ),
                ),
            )
        )
    payoff = SimpleNamespace(
        report_sha256="1" * 64,
        report=SimpleNamespace(
            logical_fingerprint="2" * 64,
            decisions=tuple(payoff_decisions),
        ),
    )
    plan = SimpleNamespace(
        report_sha256="3" * 64,
        report=SimpleNamespace(
            logical_fingerprint="4" * 64,
            payoff_terms_report_sha256=payoff.report_sha256,
            payoff_terms_logical_fingerprint=payoff.report.logical_fingerprint,
            decisions=tuple(plan_decisions),
        ),
    )
    source = SimpleNamespace(
        output_root=source_root,
        manifest_sha256="5" * 64,
        manifest=SimpleNamespace(
            plan_report_sha256=plan.report_sha256,
            plan_logical_fingerprint=plan.report.logical_fingerprint,
            logical_fingerprint="6" * 64,
            artifact_binding_fingerprint="7" * 64,
        ),
    )
    return plan, source, payoff


def test_full_population_assigns_only_four_element_matches(tmp_path: Path) -> None:
    plan, source, payoff = _inputs(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        payoff=payoff,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 3, tzinfo=UTC),
    )
    assert report.matched_identity_count == 9
    assert report.final_ratio_absent_count == 2
    assert report.transaction_scope_absent_count == 1
    assert report.required_evidence_not_matched_count == 0
    assert report.consideration_security_identity_assignment_count == 9
    assert report.terminal_value_count == 0
    assert {
        item.request_sequence
        for item in report.decisions
        if item.resolution_state
        == "final_exchange_ratio_absent_from_registration_source"
    } == {158, 184}
    assert next(
        item for item in report.decisions if item.request_sequence == 174
    ).resolution_state == "transaction_registration_scope_absent"
    assert all(
        item.evidence is not None and len(item.evidence.text) <= 2600
        for item in report.decisions
    )


def test_integer_ratio_does_not_match_a_different_decimal() -> None:
    pattern = service._ratio_pattern("11.000000")
    assert [match.group() for match in pattern.finditer("11 11.0 11.00")] == [
        "11",
        "11.0",
        "11.00",
    ]
    assert pattern.search("11.5 111 0.11") is None


def test_changed_direct_ratio_remains_unassigned(tmp_path: Path) -> None:
    plan, source, payoff = _inputs(tmp_path)
    first_plan = plan.report.decisions[0]
    path = source.output_root / "request=000001" / "document.bin"
    raw = path.read_bytes().replace(b"1.8185", b"1.9000")
    path.chmod(0o600)
    path.write_bytes(raw)
    path.chmod(0o400)
    artifact = _artifact(sequence=1, raw=raw, plan=first_plan)
    artifact_path = path.parent / "artifact.json"
    artifact_path.chmod(0o600)
    artifact_path.write_bytes(
        service._json_bytes(artifact.model_dump(mode="json"))
    )
    artifact_path.chmod(0o400)

    report = service._build_report(
        plan=plan,
        source=source,
        payoff=payoff,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 3, tzinfo=UTC),
    )
    decision = report.decisions[0]
    assert decision.resolution_state == "required_evidence_not_matched"
    assert decision.assigned_consideration_instrument_id is None
    assert report.matched_identity_count == 8


def test_report_publish_is_owner_only_and_idempotent(tmp_path: Path) -> None:
    plan, source, payoff = _inputs(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        payoff=payoff,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 3, tzinfo=UTC),
    )
    custody = tmp_path / "reports"
    custody.mkdir(mode=0o700)
    target = custody / "adjudication=test"
    first = service._write_report(
        output_root=target,
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=target,
        output_custody_root=custody,
        report=report,
    )
    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400
