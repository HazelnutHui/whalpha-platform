from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source_plan as service,
)


def _submission_payload() -> dict[str, object]:
    return {
        "cik": "35527",
        "filings": {
            "recent": {
                "form": ["424B3"],
                "filingDate": ["2025-11-25"],
                "acceptanceDateTime": ["2025-11-25T21:05:53.000Z"],
                "accessionNumber": ["0001193125-25-297171"],
                "primaryDocument": ["d942117d424b3.htm"],
            }
        },
    }


def _inputs(*, changed_ratio: bool = False):
    plans = []
    identities = []
    considerations = []
    member_sha = "7" * 64
    for index, sequence in enumerate((158, 174, 184), start=1):
        spec = service._RESIDUAL_SPECS[sequence]
        target_id = UUID(int=index)
        consideration_id = UUID(int=100 + index)
        plan_fingerprint = f"{index + 1000:064x}"
        plan = SimpleNamespace(
            request_sequence=sequence,
            target_instrument_id=target_id,
            proposed_consideration_instrument_id=consideration_id,
            proposed_cik="0000035527" if sequence == 174 else f"{index:010d}",
            submissions_member_sha256=(
                member_sha if sequence == 174 else f"{index + 2000:064x}"
            ),
            logical_fingerprint=plan_fingerprint,
        )
        local = sequence in {158, 184}
        identity = SimpleNamespace(
            request_sequence=sequence,
            target_instrument_id=target_id,
            plan_decision_fingerprint=plan_fingerprint,
            resolution_state=spec.prior_resolution_state,
            expected_exchange_ratio=spec.expected_ratio,
            assigned_consideration_instrument_id=None,
            transaction_match=local,
            target_common_security_match=local,
            consideration_security_class_match=local,
            registered_exchange_ratio_match=False,
            source_artifact_fingerprint=f"{index + 3000:064x}",
            source_document_sha256=f"{index + 4000:064x}",
            logical_fingerprint=f"{index + 5000:064x}",
        )
        displayed_ratio = (
            "9.9999"
            if changed_ratio and sequence == 158
            else spec.expected_ratio.rstrip("0")
        )
        evidence = (
            f"Each {spec.target_security_term} was converted into "
            f"{displayed_ratio} shares of {spec.consideration_security_term}."
        )
        consideration = SimpleNamespace(
            request_sequence=sequence,
            instrument_id=target_id,
            resolution_state="matched",
            evidence_text=evidence,
            evidence_sha256=f"{index + 6000:064x}",
            accession_number=f"0001193125-26-{index:06d}",
            acceptance_datetime=datetime(2026, 1, index, tzinfo=UTC),
            document_sha256=f"{index + 7000:064x}",
            logical_fingerprint=f"{index + 8000:064x}",
        )
        plans.append(plan)
        identities.append(identity)
        considerations.append(consideration)
    original_plan = SimpleNamespace(
        report_sha256="1" * 64,
        report=SimpleNamespace(
            logical_fingerprint="2" * 64,
            submissions_manifest_sha256="3" * 64,
            submissions_source_fingerprint="4" * 64,
            submissions_archive_sha256="5" * 64,
            decisions=tuple(plans),
        ),
    )
    identity_result = SimpleNamespace(
        report_sha256="6" * 64,
        report=SimpleNamespace(
            plan_report_sha256=original_plan.report_sha256,
            plan_logical_fingerprint=original_plan.report.logical_fingerprint,
            logical_fingerprint="8" * 64,
            decisions=tuple(identities),
        ),
    )
    consideration_result = SimpleNamespace(
        report_sha256="9" * 64,
        report=SimpleNamespace(
            logical_fingerprint="a" * 64,
            decisions=tuple(considerations),
        ),
    )
    submissions = SimpleNamespace(
        logical_fingerprint="4" * 64,
        archive_sha256="5" * 64,
    )
    return (
        original_plan,
        identity_result,
        consideration_result,
        submissions,
        member_sha,
    )


def test_freezes_two_local_composites_and_one_exact_request() -> None:
    original, identities, consideration, submissions, member_sha = _inputs()

    report = service._build_report(
        original_plan=original,
        identities=identities,
        consideration=consideration,
        submissions=submissions,
        submissions_manifest_sha256="3" * 64,
        fifth_third_submission_payload=_submission_payload(),
        fifth_third_submission_member_sha256=member_sha,
        implementation_revision="b" * 40,
        evaluated_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
    )

    assert report.residual_case_count == 3
    assert report.local_composite_evidence_ready_count == 2
    assert report.replacement_registration_required_count == 1
    assert report.planned_source_document_count == 1
    assert report.consideration_security_identity_assignment_count == 0
    fifth_third = next(
        item for item in report.decisions if item.request_sequence == 174
    )
    assert fifth_third.replacement_registration_accession_number == (
        "0001193125-25-297171"
    )


def test_changed_completion_ratio_fails_closed() -> None:
    original, identities, consideration, submissions, member_sha = _inputs(
        changed_ratio=True
    )

    with pytest.raises(
        service.StrongLeaderPullbackListedConsiderationResidualSourcePlanError,
        match="decision evidence differs",
    ):
        service._build_report(
            original_plan=original,
            identities=identities,
            consideration=consideration,
            submissions=submissions,
            submissions_manifest_sha256="3" * 64,
            fifth_third_submission_payload=_submission_payload(),
            fifth_third_submission_member_sha256=member_sha,
            implementation_revision="b" * 40,
            evaluated_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
        )


def test_changed_replacement_row_fails_closed() -> None:
    payload = _submission_payload()
    payload["filings"]["recent"]["accessionNumber"] = [  # type: ignore[index]
        "0001193125-25-000001"
    ]

    with pytest.raises(
        service.StrongLeaderPullbackListedConsiderationResidualSourcePlanError,
        match="not unique",
    ):
        service._validate_replacement_registration_row(payload)


def test_report_is_owner_only_idempotent_and_network_disabled(
    tmp_path: Path,
) -> None:
    original, identities, consideration, submissions, member_sha = _inputs()
    report = service._build_report(
        original_plan=original,
        identities=identities,
        consideration=consideration,
        submissions=submissions,
        submissions_manifest_sha256="3" * 64,
        fifth_third_submission_payload=_submission_payload(),
        fifth_third_submission_member_sha256=member_sha,
        implementation_revision="b" * 40,
        evaluated_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
    )
    custody = tmp_path / "plans"
    custody.mkdir(mode=0o700)
    first = service._write_report(
        output_root=custody / "plan=fixture",
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=first.output_root,
        output_custody_root=custody,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert (first.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackListedConsiderationResidualSourcePlanError,
        match="network access is prohibited",
    ):
        socket.getaddrinfo("example.com", 443)
