from __future__ import annotations

import json
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_plan as service,
)


def _package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    first_accession: str | None = None,
) -> Path:
    package = tmp_path / "source" / "snapshot=2026-09-10"
    package.mkdir(parents=True)
    with zipfile.ZipFile(package / "submissions.zip", "w") as archive:
        for index, registered in enumerate(service._REQUESTS):
            accession = (
                first_accession
                if index == 0 and first_accession is not None
                else registered["accession_number"]
            )
            archive.writestr(
                f"CIK{registered['source_cik']}.json",
                json.dumps(
                    {
                        "filings": {
                            "recent": {
                                "accessionNumber": [accession],
                                "form": [registered["form"]],
                                "filingDate": [registered["filing_date"]],
                                "acceptanceDateTime": [
                                    registered["acceptance_datetime"].replace(
                                        "Z", ".000Z"
                                    )
                                ],
                                "primaryDocument": [
                                    registered["submissions_primary_document"]
                                ],
                            }
                        }
                    }
                ),
            )
    monkeypatch.setattr(
        service,
        "read_sec_submissions_source_package",
        lambda **_: SimpleNamespace(
            logical_fingerprint="1" * 64,
            archive_sha256="2" * 64,
            completed_at=datetime(2026, 9, 10, 15, tzinfo=UTC),
        ),
    )
    return package


def test_builds_exact_five_document_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path, monkeypatch)
    result = service.build_strong_leader_pullback_terminal_reference_sec_plan(
        submissions_package_path=package,
        submissions_custody_root=package.parent,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 15, 12, tzinfo=UTC),
    )

    assert result.completion_status == "planned_not_executed"
    assert tuple(item.ticker_locator for item in result.items) == (
        "LNW",
        "MTSR",
        "REVG",
        "SAND",
        "SKX",
    )
    assert result.planned_request_count == 5
    assert result.external_request_count == 0
    assert result.source_field_adjudication_count == 0
    assert result.outcome_count == 0
    assert all(
        item.request_url.startswith("https://www.sec.gov/")
        for item in result.items
    )


def test_rejects_accession_metadata_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(
        tmp_path,
        monkeypatch,
        first_accession="0000000000-00-000000",
    )

    with pytest.raises(service.TerminalReferenceSecPlanError):
        service.build_strong_leader_pullback_terminal_reference_sec_plan(
            submissions_package_path=package,
            submissions_custody_root=package.parent,
            implementation_revision="a" * 40,
            planned_at=datetime(2026, 9, 15, 12, tzinfo=UTC),
        )


def test_publishes_and_rereads_owner_only_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path, monkeypatch)
    custody = tmp_path / "plans"
    custody.mkdir(mode=0o700)
    output = custody / "plan=test"
    arguments = {
        "submissions_package_path": package,
        "submissions_custody_root": package.parent,
        "output_root": output,
        "output_custody_root": custody,
        "implementation_revision": "a" * 40,
        "planned_at": datetime(2026, 9, 15, 12, tzinfo=UTC),
    }

    result = service.publish_strong_leader_pullback_terminal_reference_sec_plan(
        **arguments
    )
    repeated = service.publish_strong_leader_pullback_terminal_reference_sec_plan(
        **arguments
    )

    assert result.status == "published"
    assert repeated.status == "already_present"
    assert repeated.report == result.report
    assert repeated.report_sha256 == result.report_sha256
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / service.REPORT_FILE).stat().st_mode) == 0o400


def test_plan_item_rejects_request_url_drift() -> None:
    registered = service._REQUESTS[0]
    with pytest.raises(ValidationError, match="request URL differs"):
        service.TerminalReferenceSecPlanItemV1.model_validate(
            {
                **registered,
                "request_sequence": 1,
                "request_url": "https://www.sec.gov/wrong",
            }
        )
