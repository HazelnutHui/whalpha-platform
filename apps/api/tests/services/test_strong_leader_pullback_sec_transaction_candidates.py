from __future__ import annotations

import unicodedata
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_transaction_candidates as service


def _document(form: str, sequence: int) -> bytes:
    if form == "8-K" and sequence <= 61:
        body = """
        <div>EXPLANATORY NOTE</div>
        <div>On January 7, 2026 (the Closing Date), Merger Sub merged with and
        into the Company, with the Company surviving the merger. At the
        Effective Time each share was converted into the right to receive
        $10.00 per share.</div>
        <div>Item 2.01. Completion of Acquisition or Disposition of Assets.</div>
        <div>The merger was consummated on the Closing Date.</div>
        <div>Item 3.01. Notice of Delisting.</div>
        <div>Trading will be suspended and the shares delisted.</div>
        """
    elif form == "8-K":
        body = """
        <div>Item 8.01. Other Events.</div>
        <div>The issuer completed an exchange offer for notes at a purchase
        price per share equivalent.</div><div>Item 9.01. Exhibits.</div>
        """
    elif form in {"SC TO-T/A", "SC 14D9/A"}:
        body = """
        <div>The tender offer expired on January 7, 2026 and shares were
        accepted for payment. The merger was consummated at the Effective
        Time for $10.00 per share.</div>
        """
    elif form == "6-K":
        body = "<div>Exhibit 99.1 — Issuer Closes Arrangement</div>"
    else:
        body = "<div>Annual meeting voting instructions.</div>"
    return (
        f"<DOCUMENT><TYPE>{form}<TEXT><html><body>{body}</body></html>"
        "</TEXT></DOCUMENT>"
    ).encode()


def _normalized(raw: bytes) -> tuple[int, str]:
    parser = service._DocumentParser()
    parser.feed(raw.decode())
    parser.close()
    value = " ".join(
        unicodedata.normalize("NFKC", " ".join(parser.raw_parts)).split()
    )
    return len(value), service._sha256_bytes(value.encode())


def _fixture(tmp_path: Path) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    forms = (
        ["8-K"] * 62
        + ["SC TO-T/A"] * 12
        + ["SC 14D9/A"] * 12
        + ["DEFA14A"] * 2
        + ["6-K"]
    )
    items = []
    census_records = []
    for sequence in range(1, 220):
        if sequence <= 89:
            if sequence <= 63:
                instrument_number = sequence
            elif sequence <= 87:
                instrument_number = ((sequence - 64) % 12) + 1
            else:
                instrument_number = sequence - 75
            form = forms[sequence - 1]
            directory = source_root / f"request={sequence:06d}"
            directory.mkdir(mode=0o700)
            raw = _document(form, sequence)
            document = directory / "document.bin"
            document.write_bytes(raw)
            document.chmod(0o400)
            character_count, normalized_sha = _normalized(raw)
            census_records.append(
                SimpleNamespace(
                    request_sequence=sequence,
                    document_sha256=service._sha256_bytes(raw),
                    normalized_text_sha256=normalized_sha,
                    normalized_text_character_count=character_count,
                )
            )
        else:
            instrument_number = sequence
            form = "25-NSE"
        items.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=instrument_number),
                cik=f"{sequence:010d}",
                accession_number=f"9999999999-26-{sequence:06d}",
                form=form,
                filing_date=date(2026, 1, 7),
                acceptance_datetime=datetime(2026, 1, 7, 20, tzinfo=UTC)
                + timedelta(seconds=sequence),
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
            records=tuple(census_records),
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


def test_extracts_form_aware_transaction_candidates_without_fact_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    result = service.build_strong_leader_pullback_sec_transaction_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 17, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.transaction_document_count == 89
    assert result.report.instrument_count == 63
    assert result.report.structure_state_counts == (
        ("8k_item_2_01_candidate_scope", 61),
        ("8k_without_item_2_01_scope", 1),
        ("foreign_report_referenced_exhibit_only", 1),
        ("proxy_material_no_registered_completion_scope", 2),
        ("tender_amendment_primary_document", 24),
    )
    assert result.report.referenced_completion_exhibit_count == 1
    assert result.report.transaction_completion_fact_count == 0
    first = result.report.candidates[0]
    assert first.scope_profile == "explanatory_through_item_2_01"
    assert first.field_candidates[0].scan_profile == "transaction_scope"
    assert first.field_candidates[0].primary_document_state == "candidate_present"
    assert first.terminal_outcome_count == 0

    reread = service.read_strong_leader_pullback_sec_transaction_candidates(
        output_root=target, output_custody_root=custody
    )
    assert reread.report == result.report
    assert (target / "candidates.json").stat().st_mode & 0o777 == 0o400


def test_duplicate_item_2_01_scope_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    document = source.output_root / "request=000001" / "document.bin"
    document.chmod(0o600)
    raw = document.read_bytes().replace(
        b"Item 3.01. Notice of Delisting.",
        b"Item 2.01. Duplicate. Item 3.01. Notice of Delisting.",
    )
    document.write_bytes(raw)
    document.chmod(0o400)
    character_count, normalized_sha = _normalized(raw)
    census.report.records[0].document_sha256 = service._sha256_bytes(raw)
    census.report.records[0].normalized_text_sha256 = normalized_sha
    census.report.records[0].normalized_text_character_count = character_count
    with pytest.raises(
        service.StrongLeaderPullbackSecTransactionCandidatesError,
        match="Item 2.01 structure is ambiguous",
    ):
        service.build_strong_leader_pullback_sec_transaction_candidates(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            content_census_root=Path("/unused/census"),
            content_census_custody_root=Path("/unused"),
            output_root=custody / "extraction=fixture",
            output_custody_root=custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 13, 17, tzinfo=UTC),
        )


def test_tampered_report_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, census, custody = _fixture(tmp_path)
    _patch_inputs(monkeypatch, plan, source, census)
    target = custody / "extraction=fixture"
    service.build_strong_leader_pullback_sec_transaction_candidates(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        content_census_root=Path("/unused/census"),
        content_census_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 17, tzinfo=UTC),
    )
    report = target / "candidates.json"
    report.chmod(0o600)
    report.write_bytes(
        report.read_bytes().replace(b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1')
    )
    report.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecTransactionCandidatesError):
        service.read_strong_leader_pullback_sec_transaction_candidates(
            output_root=target, output_custody_root=custody
        )
