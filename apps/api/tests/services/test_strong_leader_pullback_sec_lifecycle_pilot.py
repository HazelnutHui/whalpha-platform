from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_sec_lifecycle_pilot as service


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _write_fixture(tmp_path: Path, *, omit_last_root: bool = False) -> dict[str, object]:
    sample_cases = []
    archive_names = []
    source_parent = tmp_path / "source"
    source_parent.mkdir(mode=0o700)
    package = source_parent / "snapshot=2026-09-10"
    package.mkdir(mode=0o700)
    archive_path = package / "submissions.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index in range(64):
            cik = f"{index + 1:010d}"
            instrument_id = UUID(int=index + 1)
            sample_cases.append(
                SimpleNamespace(
                    instrument_id=instrument_id,
                    cik_locators=(cik,),
                    canonical_last_observed_date=date(2026, 6, 1),
                    provider_delist_date_candidate=date(2026, 6, 2),
                )
            )
            if omit_last_root and index == 63:
                continue
            name = f"CIK{cik}.json"
            archive_names.append(name)
            # The accession prefix is a filing-system identifier and is not
            # required to equal the entity CIK owning the Submissions member.
            accession = f"9999999999-26-{index + 1:06d}"
            archive.writestr(
                name,
                _json_bytes(
                    {
                        "cik": int(cik),
                        "filings": {
                            "files": [],
                            "recent": {
                                "accessionNumber": [accession],
                                "acceptanceDateTime": [
                                    "2026-06-01T20:00:00.000Z"
                                ],
                                "filingDate": ["2026-06-01"],
                                "form": ["25-NSE"],
                                "items": [""],
                                "primaryDocDescription": ["Notification"],
                                "primaryDocument": [f"form25-{index}.htm"],
                            },
                        },
                    }
                ),
            )
    archive_path.chmod(0o400)
    package_manifest = package / "package.json"
    package_manifest.write_bytes(b"{}")
    package_manifest.chmod(0o400)
    census_root = tmp_path / "census"
    census_root.mkdir(mode=0o700)
    census_file = census_root / (
        "census=snapshot-2026-09-10--range-2021-08-11--2026-09-09.json"
    )
    census_file.write_bytes(b"{}")
    census_file.chmod(0o400)
    output_parent = tmp_path / "output"
    output_parent.mkdir(mode=0o700)
    sample = SimpleNamespace(
        report=SimpleNamespace(
            lifecycle_cases=tuple(sample_cases),
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    source = SimpleNamespace(
        remote=SimpleNamespace(last_modified=datetime(2026, 9, 10, tzinfo=UTC)),
        archive_bytes=archive_path.stat().st_size,
        archive_sha256="3" * 64,
        member_count=len(archive_names),
        member_name_fingerprint=service._fingerprint(tuple(sorted(archive_names))),
        logical_fingerprint="4" * 64,
    )
    census = SimpleNamespace(
        submissions_snapshot_date=date(2026, 9, 10),
        range_start=date(2021, 8, 11),
        range_end=date(2026, 9, 9),
        submissions_manifest_sha256=hashlib.sha256(b"{}").hexdigest(),
        submissions_source_fingerprint="4" * 64,
        submissions_archive_sha256="3" * 64,
        payload_read_member_count=len(archive_names),
        quarantined_member_count=0,
        payload_validation_status="complete",
        logical_fingerprint="5" * 64,
    )
    return {
        "sample": sample,
        "source": source,
        "census": census,
        "source_parent": source_parent,
        "package": package,
        "census_root": census_root,
        "output_parent": output_parent,
    }


def _build(monkeypatch: pytest.MonkeyPatch, fixture: dict[str, object]):
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_source_acceptance_sample",
        lambda **_: fixture["sample"],
    )
    monkeypatch.setattr(
        service,
        "read_sec_submissions_source_package",
        lambda **_: fixture["source"],
    )
    monkeypatch.setattr(
        service,
        "read_sealed_sec_submissions_payload_census",
        lambda **_: fixture["census"],
    )
    output_parent = fixture["output_parent"]
    assert isinstance(output_parent, Path)
    return service.build_strong_leader_pullback_sec_lifecycle_pilot(
        sample_root=Path("/unused/sample"),
        sample_custody_root=Path("/unused"),
        submissions_package_path=fixture["package"],
        submissions_custody_root=fixture["source_parent"],
        submissions_census_root=fixture["census_root"],
        source_snapshot_date=date(2026, 9, 10),
        range_start=date(2021, 8, 11),
        range_end=date(2026, 9, 9),
        output_root=output_parent / "build=test",
        output_custody_root=output_parent,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, tzinfo=UTC),
    )


def test_builds_and_formally_rereads_bounded_sec_lifecycle_pilot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_fixture(tmp_path)
    result = _build(monkeypatch, fixture)

    assert result.status == "published"
    assert result.report.lifecycle_case_count == 64
    assert result.report.candidate_filing_count == 64
    assert result.report.on_or_after_last_observation_candidate_count == 64
    assert result.report.candidate_form_counts == (("25-NSE", 64),)
    assert result.report.required_field_result_counts == (("unsupported", 512),)
    assert result.report.document_request_count == 0
    assert result.report.terminal_outcome_count == 0
    assert all(
        item.relation_to_last_observation == "on_last_observation"
        for case in result.report.cases
        for item in case.candidate_filings
    )

    output_parent = fixture["output_parent"]
    assert isinstance(output_parent, Path)
    reread = service.read_strong_leader_pullback_sec_lifecycle_pilot(
        output_root=output_parent / "build=test",
        output_custody_root=output_parent,
    )
    assert reread.report == result.report
    assert (output_parent / "build=test").stat().st_mode & 0o777 == 0o700
    assert (output_parent / "build=test" / "pilot.json").stat().st_mode & 0o777 == 0o400


def test_missing_frozen_sample_cik_root_stops_whole_pilot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_fixture(tmp_path, omit_last_root=True)
    with pytest.raises(service.StrongLeaderPullbackSecLifecyclePilotError):
        _build(monkeypatch, fixture)


def test_report_rejects_authority_or_fingerprint_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _build(monkeypatch, _write_fixture(tmp_path))
    values = result.report.model_dump(mode="json")
    values["terminal_outcome_count"] = 1
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackSecLifecyclePilotV1.model_validate(values)
    values = result.report.model_dump(mode="json")
    values["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackSecLifecyclePilotV1.model_validate(values)


def test_candidate_classifier_is_narrow_and_outcome_free() -> None:
    assert service._locator_categories(
        form="25-NSE",
        items=(),
        filing_date=date(2026, 1, 2),
        last_observed=date(2026, 1, 2),
    ) == ("direct_lifecycle_form",)
    assert service._locator_categories(
        form="8-K",
        items=("3.01", "9.01"),
        filing_date=date(2026, 1, 2),
        last_observed=date(2026, 1, 2),
    ) == ("structured_8k_lifecycle_item",)
    assert service._locator_categories(
        form="10-K",
        items=(),
        filing_date=date(2026, 1, 2),
        last_observed=date(2026, 1, 2),
    ) == ()
