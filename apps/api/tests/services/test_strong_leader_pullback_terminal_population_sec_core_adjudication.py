from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_document_content_census as content
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_core_adjudication as service,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_field_candidates as fields_service,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")


def _form25() -> bytes:
    return b"""
    <html><body><table>
      <tr><td>Commission File Number</td><td>001-13873</td></tr>
      <tr><td>Issuer:</td><td>
        <a href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001050825">
          STEELCASE INC
        </a>
      </td></tr>
      <tr><td>Exchange:</td><td>NEW YORK STOCK EXCHANGE LLC</td></tr>
      <tr><td>Class A Common Stock</td></tr>
      <tr><td>(Description of class of securities)</td></tr>
      <tr><td><input type="checkbox" disabled checked>17 CFR 240.12d2-2(a)(3)</td></tr>
      <tr><td>2025-12-10</td><td>Signer</td><td>Director</td></tr>
      <tr><td>Date</td><td>Name</td><td>Title</td></tr>
    </table></body></html>
    """


def _form8k() -> bytes:
    return """
    <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body>
      <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="report">
        December 10, 2025
      </ix:nonNumeric>
      <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="report">
        0001050825
      </ix:nonNumeric>
      <ix:nonNumeric name="dei:EntityRegistrantName" contextRef="report">
        Steelcase Inc.
      </ix:nonNumeric>
      <ix:nonNumeric name="dei:Security12bTitle" contextRef="target">
        Class A Common Stock
      </ix:nonNumeric>
      <ix:nonNumeric name="dei:TradingSymbol" contextRef="target">
        SCS
      </ix:nonNumeric>
      <ix:nonNumeric name="dei:SecurityExchangeName" contextRef="target">
        New York Stock Exchange
      </ix:nonNumeric>
      <div>Introductory Note</div>
      <p>In connection with the completion on December 10, 2025 (the Closing
      Date) of the acquisition, Merger Sub Inc. merged with and into Steelcase,
      with Steelcase surviving the merger.</p>
      <div>Item 2.01. Completion of Acquisition or Disposition of Assets.</div>
      <p>At the First Effective Time, each share of Class A Common Stock issued
      and outstanding was converted into the right to receive, at the election
      of the holder, $10.00 in cash or 0.5 shares of HNI common stock. Cash will
      be paid in lieu of fractional shares.</p>
      <div>Item 3.01. Notice of Delisting or Failure to Satisfy a Continued
      Listing Rule or Standard; Transfer of Listing.</div>
      <p>In connection with completion of the merger, NYSE halted trading and
      Steelcase requested that NYSE file Form 25 to delist the common stock,
      which will no longer be listed.</p>
      <div>Item 5.01. Changes in Control.</div><p>Control changed.</p>
    </body></html>
    """.encode()


def _form15() -> bytes:
    return """
    <DOCUMENT><TYPE>15-12G<TEXT><html><body>
      <div>Commission File Number:</div><div>001-13873</div>
      <div>Steelcase Inc.</div>
      <div>(Address, including zip code, of registrant's principal executive offices)</div>
      <div>Class A Common Stock</div>
      <div>5.125% Senior Notes due 2029</div>
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
            acceptance_datetime=datetime(2025, 12, filing_date.day, 16, tzinfo=UTC),
        )
        items.append(item)
        records.append(content._parse_document(path=document, item=item))
    case = plan_service.TerminalPopulationSecSourceCaseV1(
        instrument_id=INSTRUMENT_ID,
        provider_ticker_locators=("SCS",),
        cik="0001050825",
        primary_exchange="XNYS",
        selected_identity_type="share_class_figi",
        selected_identity_value="BBG001S89FD2",
        source_anchor_dates=(date(2026, 9, 3),),
        source_observation_fingerprints=("a" * 64,),
        canonical_identity_last_observed_date=date(2025, 12, 10),
        strategy_window_last_eod_observed_date=date(2025, 12, 9),
        provider_delist_date_candidate=date(2025, 12, 11),
        corrected_horizon_5_crossing_path_count=1,
        planned_request_count=3,
    )
    plan = SimpleNamespace(
        report=SimpleNamespace(
            cases=(case,),
            items=tuple(items),
            planned_request_count=3,
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
    field_report = fields_service._build_report(
        plan=plan,
        source=source,
        census=census,
        implementation_revision="b" * 40,
        evaluated_at=datetime(2026, 9, 14, 8, tzinfo=UTC),
    )
    fields = SimpleNamespace(report=field_report, report_sha256="8" * 64)
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    return plan, source, fields, custody


def test_adjudicates_four_core_evidence_fields_without_terminal_authority(
    tmp_path: Path,
) -> None:
    plan, source, fields, custody = _fixture(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        fields=fields,
        implementation_revision="c" * 40,
        evaluated_at=datetime(2026, 9, 14, 9, tzinfo=UTC),
    )
    result = service._write_report(
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        report=report,
    )

    assert report.cover_identity.resolution_state == (
        "matched_in_source_lifecycle_window"
    )
    assert report.transaction_event.selected_event_date == date(2025, 12, 10)
    assert report.termination_reason.termination_reason == "merger_or_acquisition"
    assert report.common_share_consideration.consideration_structure == (
        "holder_election_cash_or_stock"
    )
    assert report.common_share_consideration.fractional_share_cash_adjustment is True
    assert report.first_or_last_tradable_date_count == 0
    assert report.terminal_outcome_count == 0
    assert result.status == "published"
    assert (result.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400

    reread = service.read_strong_leader_pullback_terminal_population_sec_core_adjudication(
        output_root=result.output_root, output_custody_root=custody
    )
    assert reread.report == report
    assert reread.report_sha256 == result.report_sha256


def test_cross_form_conflict_and_report_tampering_fail_closed(
    tmp_path: Path,
) -> None:
    plan, source, fields, custody = _fixture(tmp_path)
    changed_form15 = fields.report.form15_candidates[0].model_copy(
        update={"security_class_text_fragments": ("Other Security",)}
    )
    changed_report = fields.report.model_copy(
        update={"form15_candidates": (changed_form15,)}
    )
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError,
        match="cross-form reconciliation differs",
    ):
        service._build_report(
            plan=plan,
            source=source,
            fields=SimpleNamespace(report=changed_report, report_sha256="8" * 64),
            implementation_revision="c" * 40,
            evaluated_at=datetime(2026, 9, 14, 9, tzinfo=UTC),
        )

    report = service._build_report(
        plan=plan,
        source=source,
        fields=fields,
        implementation_revision="c" * 40,
        evaluated_at=datetime(2026, 9, 14, 9, tzinfo=UTC),
    )
    result = service._write_report(
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        report=report,
    )
    path = result.output_root / service.REPORT_FILE
    path.chmod(0o600)
    path.write_bytes(
        path.read_bytes().replace(
            b'"terminal_outcome_count":0', b'"terminal_outcome_count":1'
        )
    )
    path.chmod(0o400)
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError
    ):
        service.read_strong_leader_pullback_terminal_population_sec_core_adjudication(
            output_root=result.output_root, output_custody_root=custody
        )
