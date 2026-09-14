from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_document_content_census as content
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_field_candidates as service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")


def _form25() -> bytes:
    return b"""
    <html><body><table>
      <tr><td>Commission File Number</td><td>001-13873</td></tr>
      <tr><td>Issuer:</td><td>
        <a href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001050825">
          Steelcase Inc.
        </a>
      </td></tr>
      <tr><td>Exchange:</td><td>New York Stock Exchange LLC</td></tr>
      <tr><td>Class A Common Stock</td></tr>
      <tr><td>(Description of class of securities)</td></tr>
      <tr><td><input type="checkbox" disabled checked>17 CFR 240.12d2-2(a)(3)</td></tr>
      <tr><td>2025-12-10</td><td>Signer</td><td>Director</td></tr>
      <tr><td>Date</td><td>Name</td><td>Title</td></tr>
    </table></body></html>
    """


def _form8k() -> bytes:
    return b"""
    <html><body>
      <div>EXPLANATORY NOTE</div>
      <div>On December 10, 2025 (the Closing Date), Merger Sub merged with and
      into Steelcase, with Steelcase surviving. Each share of Class A Common
      Stock was converted into the right to receive cash.</div>
      <div>Item 2.01. Completion of Acquisition or Disposition of Assets.</div>
      <div>The merger was completed on the Closing Date.</div>
      <div>Item 3.01. Notice of Delisting.</div>
      <div>Trading was suspended and the shares were delisted.</div>
    </body></html>
    """


def _form15() -> bytes:
    return """
    <DOCUMENT><TYPE>15-12G<TEXT><html><body>
      <div>Commission File Number:</div><div>001-13873</div>
      <div>Steelcase Inc.</div>
      <div>(Address, including zip code, of registrant's principal executive offices)</div>
      <div>Class A Common Stock</div>
      <div>(Title of each class of securities covered by this Form)</div>
      <div>Rule 12g-4(a)(1)</div><div>☒</div>
      <div>Rule 12h-3(b)(1)(i)</div><div>☑</div>
      <div>Date: December 22, 2025</div><div>By:</div><div>/s/ Signer</div>
    </body></html></TEXT></DOCUMENT>
    """.encode()


def _fixture(
    tmp_path: Path,
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    specs = (
        ("25-NSE", date(2025, 12, 10), "0000876661-25-000952", _form25()),
        ("8-K", date(2025, 12, 11), "0001193125-25-315864", _form8k()),
        ("15-12G", date(2025, 12, 22), "0001193125-25-327599", _form15()),
    )
    items = []
    records = []
    for sequence, (form, filing_date, accession, raw) in enumerate(specs, 1):
        request_root = source_root / f"request={sequence:06d}"
        request_root.mkdir(mode=0o700)
        document = request_root / "document.bin"
        document.write_bytes(raw)
        document.chmod(0o400)
        item = SimpleNamespace(
            request_sequence=sequence,
            instrument_id=INSTRUMENT_ID,
            cik="0001050825",
            accession_number=accession,
            form=form,
            filing_date=filing_date,
            acceptance_datetime=datetime(2025, 12, 10, 16, tzinfo=UTC)
            + timedelta(days=sequence),
        )
        items.append(item)
        records.append(content._parse_document(path=document, item=item))
    plan = SimpleNamespace(
        report=SimpleNamespace(
            planned_request_count=3,
            items=tuple(items),
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    source = SimpleNamespace(
        output_root=source_root,
        completed_document_count=3,
        manifest=SimpleNamespace(
            completed_document_count=3,
            logical_fingerprint="3" * 64,
            artifact_binding_fingerprint="4" * 64,
        ),
        manifest_sha256="5" * 64,
    )
    census = SimpleNamespace(
        report=SimpleNamespace(
            document_count=3,
            plan_sha256="2" * 64,
            plan_logical_fingerprint="1" * 64,
            source_manifest_sha256="5" * 64,
            source_logical_fingerprint="3" * 64,
            source_artifact_binding_fingerprint="4" * 64,
            records=tuple(records),
            logical_fingerprint="6" * 64,
        ),
        report_sha256="7" * 64,
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    return plan, source, census, custody


def _patch_readers(
    monkeypatch: pytest.MonkeyPatch,
    plan: SimpleNamespace,
    source: SimpleNamespace,
    census: SimpleNamespace,
) -> None:
    monkeypatch.setattr(
        service.plan_reader,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        lambda **_: plan,
    )
    monkeypatch.setattr(
        service.source_reader,
        "read_strong_leader_pullback_terminal_population_sec_source",
        lambda **_: source,
    )
    monkeypatch.setattr(
        service.census_reader,
        "read_strong_leader_pullback_terminal_population_sec_content_census",
        lambda **_: census,
    )


def test_extracts_all_three_form_aware_candidates_without_fact_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_readers(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"

    result = service.build_strong_leader_pullback_terminal_population_sec_field_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 8, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.form_counts == (
        ("15-12G", 1),
        ("25-NSE", 1),
        ("8-K", 1),
    )
    assert result.report.form25_candidates[0].issuer_name == "Steelcase Inc."
    assert result.report.form15_candidates[0].commission_file_number_candidates == (
        "001-13873",
    )
    assert (
        result.report.transaction_candidates[0].structure_state
        == "8k_item_2_01_candidate_scope"
    )
    assert result.report.lifecycle_fact_count == 0
    assert result.report.terminal_outcome_count == 0
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400

    reread = service.read_strong_leader_pullback_terminal_population_sec_field_candidates(
        output_root=target, output_custody_root=custody
    )
    assert reread.report == result.report
    assert reread.report_sha256 == result.report_sha256


def test_changed_census_binding_and_tampered_report_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_readers(monkeypatch, plan, source, census)
    census.report.source_manifest_sha256 = "9" * 64
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError,
        match="input bindings differ",
    ):
        service.build_strong_leader_pullback_terminal_population_sec_field_candidates(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            content_census_root=Path("/unused/census"),
            content_census_custody_root=Path("/unused"),
            output_root=custody / "extraction=fixture",
            output_custody_root=custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 14, 8, tzinfo=UTC),
        )

    census.report.source_manifest_sha256 = "5" * 64
    target = custody / "extraction=fixture"
    service.build_strong_leader_pullback_terminal_population_sec_field_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 8, tzinfo=UTC),
    )
    report = target / service.REPORT_FILE
    report.chmod(0o600)
    report.write_bytes(
        report.read_bytes().replace(
            b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1'
        )
    )
    report.chmod(0o400)
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError
    ):
        service.read_strong_leader_pullback_terminal_population_sec_field_candidates(
            output_root=target, output_custody_root=custody
        )
