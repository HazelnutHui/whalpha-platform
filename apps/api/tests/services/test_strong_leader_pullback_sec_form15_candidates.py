from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_form15_candidates as service


def _form15(index: int, *, signed: str = "January 7, 2026") -> bytes:
    return f"""
    <DOCUMENT><TYPE>15-12G<TEXT><html><body>
      <div>Commission File Number:</div><div>00</div><div>1-{index:05d}</div>
      <div>Issuer {index}</div>
      <div>(Address, including zip code, of registrant's principal executive offices)</div>
      <div>Common Stock, par value $0.01 per share</div>
      <div>(Title of each class of securities covered by this Form)</div>
      <div>Rule 12g-4(a)(1)</div><div>☒</div>
      <div>Rule 12h-3(b)(1)(i)</div><div>☑</div>
      <div>Rule 15d-6</div><div>☐</div>
      <div>Date: {signed}</div><div>By:</div><div>/s/ Signer</div>
    </body></html></TEXT></DOCUMENT>
    """.encode()


def _fixture(tmp_path: Path) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    items = []
    for index in range(219):
        sequence = index + 1
        if sequence <= 66:
            if sequence <= 62:
                instrument_number = sequence
            elif sequence == 63:
                instrument_number = 60
            elif sequence == 64:
                instrument_number = 61
            else:
                instrument_number = 62
            form = "15-12G" if sequence <= 63 else "15-15D"
            directory = source_root / f"request={sequence:06d}"
            directory.mkdir(mode=0o700)
            document = directory / "document.bin"
            document.write_bytes(
                _form15(
                    sequence,
                    signed=(
                        "January 6, 2026" if sequence == 1 else "January 7, 2026"
                    ),
                )
            )
            document.chmod(0o400)
        else:
            instrument_number = sequence
            form = "8-K"
        items.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=instrument_number),
                cik=f"{sequence:010d}",
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
        service, "read_strong_leader_pullback_sec_document_plan", lambda **_: plan
    )
    monkeypatch.setattr(
        service, "read_strong_leader_pullback_sec_document_source", lambda **_: source
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_content_census",
        lambda **_: census,
    )


def test_extracts_all_form15_fields_without_promoting_lifecycle_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    result = service.build_strong_leader_pullback_sec_form15_candidates(
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
    assert result.report.form_counts == (("15-12G", 63), ("15-15D", 3))
    assert result.report.instrument_count == 62
    assert result.report.duplicate_instrument_count == 3
    assert result.report.maximum_instrument_document_count == 3
    assert result.report.commission_file_number_state_counts == (
        ("single_candidate", 66),
    )
    assert result.report.certification_date_filing_relationship_counts == (
        ("before_filing_date", 1),
        ("same_as_filing_date", 65),
    )
    assert result.report.lifecycle_fact_count == 0
    first = result.report.candidates[0]
    assert first.commission_file_number_candidates == ("001-00001",)
    assert first.security_class_text_fragments == (
        "Common Stock, par value $0.01 per share",
    )
    assert first.selected_rule_provisions == (
        "17 CFR 240.12g-4(a)(1)",
        "17 CFR 240.12h-3(b)(1)(i)",
    )
    assert first.delisting_effective_date is None

    reread = service.read_strong_leader_pullback_sec_form15_candidates(
        output_root=target, output_custody_root=custody
    )
    assert reread.report == result.report
    assert (target / "candidates.json").stat().st_mode & 0o777 == 0o400


def test_unsupported_field_template_is_preserved_without_guessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    document = source.output_root / "request=000001" / "document.bin"
    document.chmod(0o600)
    document.write_bytes(
        document.read_bytes().replace(
            b"(Title of each class of securities covered by this Form)",
            b"(Nonstandard class label)",
        )
    )
    document.chmod(0o400)
    result = service.build_strong_leader_pullback_sec_form15_candidates(
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
    assert result.report.candidates[0].security_class_state == "unsupported_template"
    assert result.report.security_class_state_counts == (
        ("text_fragments_extracted", 65),
        ("unsupported_template", 1),
    )
    assert result.report.lifecycle_fact_count == 0


def test_tampered_report_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    service.build_strong_leader_pullback_sec_form15_candidates(
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
        report.read_bytes().replace(
            b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1'
        )
    )
    report.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecForm15CandidatesError):
        service.read_strong_leader_pullback_sec_form15_candidates(
            output_root=target, output_custody_root=custody
        )
