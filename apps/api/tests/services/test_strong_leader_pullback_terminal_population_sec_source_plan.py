from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")


def _source_inputs(tmp_path: Path) -> tuple[Path, Path]:
    package = tmp_path / "source" / "snapshot=2026-09-10"
    package.mkdir(parents=True, mode=0o700)
    (package / "package.json").write_text("{}\n")
    (package / "package.json").chmod(0o400)
    filing_dates = ["2025-12-10", "2025-12-11", "2025-12-22", "2025-12-12"]
    payload = {
        "cik": 1050825,
        "filings": {
            "files": [],
            "recent": {
                "acceptanceDateTime": [
                    "2025-12-10T10:07:48.000Z",
                    "2025-12-11T16:00:16.000Z",
                    "2025-12-22T08:00:07.000Z",
                    "2025-12-12T15:00:00.000Z",
                ],
                "accessionNumber": [
                    "0000876661-25-000952",
                    "0001193125-25-315864",
                    "0001193125-25-327599",
                    "0000000001-25-000001",
                ],
                "filingDate": filing_dates,
                "form": ["25-NSE", "8-K", "15-12G", "4"],
                "items": ["", "2.01,3.01", "", ""],
                "primaryDocDescription": ["", "8-K", "15-12G", "FORM 4"],
                "primaryDocument": [
                    "xslF25X02/primary_doc.xml",
                    "d77540d8k.htm",
                    "d45344d1512g.htm",
                    "form4.xml",
                ],
            },
        },
    }
    archive = package / "submissions.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("CIK0001050825.json", json.dumps(payload))
    archive.chmod(0o400)
    census = tmp_path / "census"
    census.mkdir(mode=0o700)
    census_file = census / (
        "census=snapshot-2026-09-10--range-2021-08-11--2026-09-09.json"
    )
    census_file.write_text("{}\n")
    census_file.chmod(0o400)
    return package, census


def _patch_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, ambiguous_cik: bool = False
) -> tuple[Path, Path]:
    package, census_root = _source_inputs(tmp_path)
    gap_case = SimpleNamespace(
        instrument_id=INSTRUMENT_ID,
        gap_state="newly_in_scope_primary_source_unadjudicated",
        canonical_identity_last_observed_date=date(2025, 12, 10),
        strategy_window_last_eod_observed_date=date(2025, 12, 9),
        horizon_5_crossing_path_count=1,
    )
    gap = SimpleNamespace(
        report=SimpleNamespace(
            decisions=(gap_case,),
            new_primary_source_case_count=1,
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    monkeypatch.setattr(
        service.gap_source,
        "read_strong_leader_pullback_terminal_gap_census_v2",
        lambda **_: gap,
    )
    source_observation = SimpleNamespace(
        source_observation_fingerprint="3" * 64,
        cik="0001050825",
        primary_exchange="XNYS",
        ticker="SCS",
    )
    decision = SimpleNamespace(
        disposition=InactiveLifecycleDisposition.REVIEW_CANDIDATE,
        canonical_instrument_id=INSTRUMENT_ID,
        canonical_last_observed_date=date(2025, 12, 10),
        source_observation_fingerprint="3" * 64,
        selected_identity_type=SimpleNamespace(value="share_class_figi"),
        selected_identity_value="BBG001S89FD2",
        effective_date_candidate=date(2025, 12, 11),
        anchor_date=date(2026, 9, 3),
    )
    observations = [source_observation]
    decisions = [decision]
    if ambiguous_cik:
        observations.append(
            SimpleNamespace(
                source_observation_fingerprint="9" * 64,
                cik="0009999999",
                primary_exchange="XNYS",
                ticker="SCS",
            )
        )
        decisions.append(
            SimpleNamespace(
                **{
                    **decision.__dict__,
                    "source_observation_fingerprint": "9" * 64,
                }
            )
        )
    lifecycle = SimpleNamespace(
        manifest=SimpleNamespace(
            anchor_date=date(2026, 9, 3),
            contract_version="historical-inactive-lifecycle-resolution-shadow/1.0",
            logical_fingerprint="4" * 64,
        ),
        manifest_sha256="5" * 64,
        source_observations=tuple(observations),
        decisions=tuple(decisions),
    )
    monkeypatch.setattr(
        service,
        "read_historical_inactive_lifecycle_resolution_shadow",
        lambda **_: lifecycle,
    )
    archive = package / "submissions.zip"
    names = ("CIK0001050825.json",)
    source = SimpleNamespace(
        archive_bytes=archive.stat().st_size,
        member_count=1,
        member_name_fingerprint=service._fingerprint(names),
        logical_fingerprint="6" * 64,
        archive_sha256="7" * 64,
        completed_at=datetime(2026, 9, 10, 1, tzinfo=UTC),
    )
    monkeypatch.setattr(
        service,
        "read_sec_submissions_source_package",
        lambda **_: source,
    )
    census = SimpleNamespace(
        submissions_snapshot_date=date(2026, 9, 10),
        range_start=date(2021, 8, 11),
        range_end=date(2026, 9, 9),
        logical_fingerprint="8" * 64,
    )
    monkeypatch.setattr(
        service,
        "read_sealed_sec_submissions_payload_census",
        lambda **_: census,
    )
    monkeypatch.setattr(
        service.lifecycle_pilot,
        "validate_sec_lifecycle_submissions_binding",
        lambda **_: None,
    )
    return package, census_root


def test_builds_three_item_plan_and_formally_rereads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, census_root = _patch_inputs(tmp_path, monkeypatch)
    output = tmp_path / "plans"
    output.mkdir(mode=0o700)
    result = service.build_strong_leader_pullback_terminal_population_sec_source_plan(
        terminal_gap_v2_root=Path("/unused/gap"),
        terminal_gap_v2_custody_root=Path("/unused"),
        lifecycle_shadow_root=Path("/unused/lifecycle"),
        lifecycle_shadow_custody_root=Path("/unused"),
        lifecycle_anchor_dates=(date(2026, 9, 3),),
        submissions_package_path=package,
        submissions_custody_root=package.parent,
        submissions_census_root=census_root,
        source_snapshot_date=date(2026, 9, 10),
        range_start=date(2021, 8, 11),
        range_end=date(2026, 9, 9),
        output_root=output / "plan=test",
        output_custody_root=output,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.planned_request_count == 3
    assert result.report.form_counts == (("15-12G", 1), ("25-NSE", 1), ("8-K", 1))
    assert result.report.cases[0].provider_ticker_locators == ("SCS",)
    assert result.report.relation_counts == (
        ("after_last_eod_before_provider_delist_candidate", 1),
        ("after_provider_delist_candidate", 1),
        ("on_provider_delist_candidate", 1),
    )
    reread = service.read_strong_leader_pullback_terminal_population_sec_source_plan(
        output_root=output / "plan=test", output_custody_root=output
    )
    assert reread.report == result.report
    assert (output / "plan=test").stat().st_mode & 0o777 == 0o700
    assert (output / "plan=test" / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_ambiguous_lifecycle_cik_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, census_root = _patch_inputs(tmp_path, monkeypatch, ambiguous_cik=True)
    output = tmp_path / "plans"
    output.mkdir(mode=0o700)
    with pytest.raises(service.StrongLeaderPullbackTerminalPopulationSecSourcePlanError):
        service.build_strong_leader_pullback_terminal_population_sec_source_plan(
            terminal_gap_v2_root=Path("/unused/gap"),
            terminal_gap_v2_custody_root=Path("/unused"),
            lifecycle_shadow_root=Path("/unused/lifecycle"),
            lifecycle_shadow_custody_root=Path("/unused"),
            lifecycle_anchor_dates=(date(2026, 9, 3),),
            submissions_package_path=package,
            submissions_custody_root=package.parent,
            submissions_census_root=census_root,
            source_snapshot_date=date(2026, 9, 10),
            range_start=date(2021, 8, 11),
            range_end=date(2026, 9, 9),
            output_root=output / "plan=test",
            output_custody_root=output,
            implementation_revision="a" * 40,
            planned_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
        )


def test_model_rejects_fingerprint_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, census_root = _patch_inputs(tmp_path, monkeypatch)
    output = tmp_path / "plans"
    output.mkdir(mode=0o700)
    result = service.build_strong_leader_pullback_terminal_population_sec_source_plan(
        terminal_gap_v2_root=Path("/unused/gap"),
        terminal_gap_v2_custody_root=Path("/unused"),
        lifecycle_shadow_root=Path("/unused/lifecycle"),
        lifecycle_shadow_custody_root=Path("/unused"),
        lifecycle_anchor_dates=(date(2026, 9, 3),),
        submissions_package_path=package,
        submissions_custody_root=package.parent,
        submissions_census_root=census_root,
        source_snapshot_date=date(2026, 9, 10),
        range_start=date(2021, 8, 11),
        range_end=date(2026, 9, 9),
        output_root=output / "plan=test",
        output_custody_root=output,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 14, 5, tzinfo=UTC),
    )
    values = result.report.model_dump(mode="json")
    values["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackTerminalPopulationSecSourcePlanV1.model_validate(
            values
        )


def test_boundary_relation_rejects_pre_boundary_filing() -> None:
    with pytest.raises(service.StrongLeaderPullbackTerminalPopulationSecSourcePlanError):
        service._boundary_relation(
            filing_date=date(2025, 12, 8),
            last_eod=date(2025, 12, 9),
            delist_candidate=date(2025, 12, 11),
        )
