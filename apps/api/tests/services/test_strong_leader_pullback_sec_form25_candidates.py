from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_form25_candidates as service


def _form25(cik: str, index: int) -> bytes:
    return f"""
    <html><body><table>
      <tr><td>Commission File Number</td><td>001-{index:05d}</td></tr>
      <tr><td>Issuer:</td><td>
        <a href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK={cik}">
          Issuer {index}
        </a>
      </td></tr>
      <tr><td>Exchange:</td><td>Nasdaq Stock Market LLC</td></tr>
      <tr><td>Common Stock</td></tr>
      <tr><td>(Description of class of securities)</td></tr>
      <tr><td><input type="checkbox" disabled checked>17 CFR 240.12d2-2(a)(3)</td></tr>
      <tr><td>2026-01-07</td><td>Signer</td><td>Director</td></tr>
      <tr><td>Date</td><td>Name</td><td>Title</td></tr>
    </table></body></html>
    """.encode()


def _fixture(tmp_path: Path) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    items = []
    for index in range(219):
        sequence = index + 1
        if index < 64:
            instrument_number = sequence if sequence <= 62 else sequence - 62
            cik = f"{instrument_number:010d}"
            directory = source_root / f"request={sequence:06d}"
            directory.mkdir(mode=0o700)
            document = directory / "document.bin"
            document.write_bytes(_form25(cik, sequence))
            document.chmod(0o400)
            form = "25-NSE"
        else:
            instrument_number = sequence
            cik = f"{sequence:010d}"
            form = "15-12G"
        items.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=instrument_number),
                cik=cik,
                accession_number=f"9999999999-26-{sequence:06d}",
                form=form,
                filing_date=date(2026, 1, 7),
                acceptance_datetime=datetime(2026, 1, 7, 20, tzinfo=UTC)
                + timedelta(seconds=index),
            )
        )
    plan = SimpleNamespace(
        plan=SimpleNamespace(items=tuple(items), logical_fingerprint="1" * 64),
        plan_sha256="2" * 64,
    )
    source = SimpleNamespace(
        output_root=source_root,
        manifest=SimpleNamespace(logical_fingerprint="3" * 64),
        manifest_sha256="4" * 64,
    )
    census = SimpleNamespace(
        report=SimpleNamespace(
            source_manifest_sha256="4" * 64,
            source_logical_fingerprint="3" * 64,
            plan_sha256="2" * 64,
            plan_logical_fingerprint="1" * 64,
            parsed_document_count=219,
            logical_fingerprint="5" * 64,
        ),
        report_sha256="6" * 64,
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    return plan, source, census, custody


def _patch_inputs(
    monkeypatch: pytest.MonkeyPatch,
    plan: SimpleNamespace,
    source: SimpleNamespace,
    census: SimpleNamespace,
) -> None:
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_plan",
        lambda **_: plan,
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_source",
        lambda **_: source,
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_content_census",
        lambda **_: census,
    )


def test_extracts_all_form25_structured_candidates_without_fact_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    result = service.build_strong_leader_pullback_sec_form25_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.form25_document_count == 64
    assert result.report.instrument_count == 62
    assert result.report.duplicate_instrument_count == 2
    assert result.report.selected_rule_counts == (
        ("17 CFR 240.12d2-2(a)(3)", 64),
    )
    assert result.report.exchange_counts == (("Nasdaq Stock Market LLC", 64),)
    assert result.report.lifecycle_fact_count == 0
    assert result.report.complete_field_support_counts == tuple(
        (field, 0) for field in service.LIFECYCLE_REQUIRED_FIELDS
    )
    first = result.report.candidates[0]
    assert first.issuer_name == "Issuer 1"
    assert first.security_class_descriptions == ("Common Stock",)
    assert first.notice_signature_date == date(2026, 1, 7)
    assert first.last_tradable_date is None
    assert first.delisting_effective_date is None

    reread = service.read_strong_leader_pullback_sec_form25_candidates(
        output_root=target,
        output_custody_root=custody,
    )
    assert reread.report == result.report
    assert (target / "candidates.json").stat().st_mode & 0o777 == 0o400


def test_missing_checked_rule_stops_the_complete_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    document = source.output_root / "request=000001" / "document.bin"
    document.chmod(0o600)
    document.write_bytes(document.read_bytes().replace(b" checked", b""))
    document.chmod(0o400)
    with pytest.raises(
        service.StrongLeaderPullbackSecForm25CandidatesError,
        match="incomplete or ambiguous",
    ):
        service.build_strong_leader_pullback_sec_form25_candidates(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            content_census_root=Path("/unused/census"),
            content_census_custody_root=Path("/unused"),
            output_root=custody / "extraction=fixture",
            output_custody_root=custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
        )


def test_tampered_report_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    service.build_strong_leader_pullback_sec_form25_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
    )
    report = target / "candidates.json"
    report.chmod(0o600)
    report.write_bytes(
        report.read_bytes().replace(b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1')
    )
    report.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecForm25CandidatesError):
        service.read_strong_leader_pullback_sec_form25_candidates(
            output_root=target,
            output_custody_root=custody,
        )
