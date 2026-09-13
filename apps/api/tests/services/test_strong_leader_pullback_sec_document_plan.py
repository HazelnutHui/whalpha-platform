from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_sec_document_plan as service


def _pilot(*, duplicate_accession: bool = False) -> SimpleNamespace:
    cases = [
        SimpleNamespace(
            instrument_id=UUID(int=index + 1),
            cik=f"{index + 1:010d}",
            candidate_filings=[],
        )
        for index in range(64)
    ]
    for index in range(219):
        case = cases[index % 64]
        accession_index = 0 if duplicate_accession and index == 1 else index
        case.candidate_filings.append(
            SimpleNamespace(
                accession_number=f"9999999999-26-{accession_index + 1:06d}",
                form="25-NSE" if index < 64 else "15-12G",
                filing_date=date(2026, 6, 1) + timedelta(days=index // 64),
                acceptance_datetime=datetime(2026, 6, 1, 20, tzinfo=UTC)
                + timedelta(seconds=index),
                primary_document=f"documents/filing-{index}.htm",
                locator_categories=("direct_lifecycle_form",),
                items=(),
                relation_to_last_observation="on_last_observation",
            )
        )
    return SimpleNamespace(
        report=SimpleNamespace(
            completion_status=(
                "metadata_locator_complete_terminal_evidence_incomplete"
            ),
            document_request_count=0,
            terminal_outcome_count=0,
            research_admission_count=0,
            cases=tuple(cases),
            logical_fingerprint="1" * 64,
            evaluated_at=datetime(2026, 9, 13, 13, 42, 15, tzinfo=UTC),
        ),
        report_sha256="2" * 64,
    )


def test_builds_and_formally_rereads_exact_document_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pilot = _pilot()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_lifecycle_pilot",
        lambda **_: pilot,
    )
    root = tmp_path / "plans"
    root.mkdir(mode=0o700)
    result = service.build_strong_leader_pullback_sec_document_plan(
        pilot_root=Path("/unused/pilot"),
        pilot_custody_root=Path("/unused"),
        output_root=root / "build=test",
        output_custody_root=root,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 13, 14, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.plan.planned_request_count == 219
    assert result.plan.batch_count == 22
    assert result.plan.items[-1].batch_number == 22
    assert result.plan.items[-1].batch_position == 9
    assert result.plan.form_counts == (("15-12G", 155), ("25-NSE", 64))
    assert result.plan.external_request_count == 0
    assert result.plan.document_write_count == 0

    reread = service.read_strong_leader_pullback_sec_document_plan(
        output_root=root / "build=test",
        output_custody_root=root,
    )
    assert reread.plan == result.plan
    assert (root / "build=test").stat().st_mode & 0o777 == 0o700
    assert (root / "build=test" / "plan.json").stat().st_mode & 0o777 == 0o400


def test_duplicate_accession_stops_plan() -> None:
    with pytest.raises(service.StrongLeaderPullbackSecDocumentPlanError):
        service._compose_plan(
            pilot=_pilot(duplicate_accession=True),
            implementation_revision="a" * 40,
            planned_at=datetime(2026, 9, 13, tzinfo=UTC),
        )


def test_document_url_allows_safe_relative_path_and_separates_cik() -> None:
    assert service._document_url(
        cik="0000123456",
        accession="9999999999-26-000001",
        primary_document="xsl/form25/filing.xml",
    ) == (
        "https://www.sec.gov/Archives/edgar/data/123456/"
        "999999999926000001/xsl/form25/filing.xml"
    )
    with pytest.raises(ValueError):
        service._document_url(
            cik="0000123456",
            accession="9999999999-26-000001",
            primary_document="../secret.txt",
        )


def test_plan_rejects_aggregate_or_fingerprint_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pilot = _pilot()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_lifecycle_pilot",
        lambda **_: pilot,
    )
    root = tmp_path / "plans"
    root.mkdir(mode=0o700)
    result = service.build_strong_leader_pullback_sec_document_plan(
        pilot_root=Path("/unused/pilot"),
        pilot_custody_root=Path("/unused"),
        output_root=root / "build=test",
        output_custody_root=root,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 13, 14, tzinfo=UTC),
    )
    values = result.plan.model_dump(mode="json")
    values["form_counts"] = [["25-NSE", 219]]
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackSecDocumentPlanV1.model_validate(values)
    values = result.plan.model_dump(mode="json")
    values["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackSecDocumentPlanV1.model_validate(values)
