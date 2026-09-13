from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_case_adjudication as service


class _Case(SimpleNamespace):
    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "instrument_id": str(self.instrument_id),
            "provider_ticker_locators": self.provider_ticker_locators,
            "cik_locators": self.cik_locators,
            "primary_exchange_locators": self.primary_exchange_locators,
            "selected_identity_types": self.selected_identity_types,
            "selected_identity_values": self.selected_identity_values,
            "canonical_first_observed_date": self.canonical_first_observed_date,
            "canonical_last_observed_date": self.canonical_last_observed_date,
            "provider_delist_date_candidate": self.provider_delist_date_candidate,
        }


def _html(
    *, cik: str, ticker: str, extra_row: bool, incomplete_right: bool
) -> bytes:
    rows = [
        (
            "target",
            "Common Stock, par value $0.01 per share",
            ticker,
            "The Nasdaq Stock Market LLC",
        )
    ]
    if extra_row:
        rows.append(("debt", "3.5% Senior Notes", f"N{ticker}", "NASDAQ"))
    values = [
        '<ix:nonNumeric name="dei:DocumentPeriodEndDate" '
        'contextRef="report">January 2, 2026</ix:nonNumeric>',
        '<ix:nonNumeric name="dei:EntityCentralIndexKey" '
        f'contextRef="report">{cik}</ix:nonNumeric>',
        '<ix:nonNumeric name="dei:EntityRegistrantName" '
        f'contextRef="report">Issuer {ticker}</ix:nonNumeric>',
    ]
    for context, title, symbol, exchange in rows:
        values.extend(
            (
                f'<ix:nonNumeric name="dei:Security12bTitle" contextRef="{context}">'
                f"{title}</ix:nonNumeric>",
                f'<ix:nonNumeric name="dei:TradingSymbol" contextRef="{context}">'
                f"{symbol}</ix:nonNumeric>",
                '<ix:nonNumeric name="dei:SecurityExchangeName" '
                f'contextRef="{context}">{exchange}</ix:nonNumeric>',
            )
        )
    if incomplete_right:
        values.extend(
            (
                '<ix:nonNumeric name="dei:Security12bTitle" '
                'contextRef="right">Purchase rights</ix:nonNumeric>',
                '<ix:nonNumeric name="dei:SecurityExchangeName" '
                'contextRef="right">NASDAQ</ix:nonNumeric>',
            )
        )
    return ("<html><body>" + "".join(values) + "</body></html>").encode()


def _fixture(tmp_path: Path) -> tuple[object, object, object, object, object]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    cases = tuple(
        _Case(
            instrument_id=UUID(int=index),
            provider_ticker_locators=(f"T{index}",),
            cik_locators=(f"{index:010d}",),
            primary_exchange_locators=("XNAS",),
            selected_identity_types=("share_class_figi",),
            selected_identity_values=(f"BBG{index:09d}",),
            canonical_first_observed_date=date(2020, 1, 1),
            canonical_last_observed_date=date(2026, 1, 1),
            provider_delist_date_candidate=date(2026, 1, 2),
        )
        for index in range(1, 65)
    )
    candidates = []
    for sequence in range(1, 62):
        raw = _html(
            cik=f"{sequence:010d}",
            ticker=f"T{sequence}",
            extra_row=sequence <= 8,
            incomplete_right=sequence == 1,
        )
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        (directory / "document.bin").write_bytes(raw)
        candidates.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                accession_number=f"{sequence:010d}-26-{sequence:06d}",
                filing_date=date(2026, 1, 2),
                acceptance_datetime=datetime(2026, 1, 2, 20, tzinfo=UTC),
                document_sha256=hashlib.sha256(raw).hexdigest(),
                structure_state="8k_item_2_01_candidate_scope",
                form="8-K",
            )
        )
    sequence = 62
    raw = _html(cik="0000000001", ticker="T1", extra_row=False, incomplete_right=False)
    raw = raw.replace(b"January 2, 2026", b"January 3, 2026")
    directory = source_root / f"request={sequence:06d}"
    directory.mkdir()
    (directory / "document.bin").write_bytes(raw)
    candidates.append(
        SimpleNamespace(
            request_sequence=sequence,
            instrument_id=UUID(int=1),
            accession_number="0000000001-26-000062",
            filing_date=date(2026, 1, 3),
            acceptance_datetime=datetime(2026, 1, 3, 20, tzinfo=UTC),
            document_sha256=hashlib.sha256(raw).hexdigest(),
            structure_state="8k_without_item_2_01_scope",
            form="8-K",
        )
    )
    sample = SimpleNamespace(
        report=SimpleNamespace(
            lifecycle_cases=cases,
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    plan = SimpleNamespace(plan_sha256="3" * 64)
    source = SimpleNamespace(
        output_root=source_root,
        manifest=SimpleNamespace(),
        manifest_sha256="4" * 64,
    )
    transaction = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="3" * 64,
            source_manifest_sha256="4" * 64,
            logical_fingerprint="5" * 64,
            candidates=tuple(candidates),
        ),
        report_sha256="6" * 64,
    )
    coverage_cases = tuple(
        SimpleNamespace(
            instrument_id=item.instrument_id,
            logical_fingerprint=f"{index:064x}",
            evidence_profile=(
                "structured_transaction_scope"
                if index <= 61
                else "notice_only_no_transaction_document"
            ),
        )
        for index, item in enumerate(cases, start=1)
    )
    coverage = SimpleNamespace(
        report=SimpleNamespace(
            source_sample_sha256="2" * 64,
            transaction_report_sha256="6" * 64,
            lifecycle_case_count=64,
            logical_fingerprint="7" * 64,
            cases=coverage_cases,
        ),
        report_sha256="8" * 64,
    )
    return sample, plan, source, transaction, coverage


def _patch_inputs(
    monkeypatch: pytest.MonkeyPatch,
    sample: object,
    plan: object,
    source: object,
    transaction: object,
    coverage: object,
) -> None:
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_source_acceptance_sample",
        lambda **_: sample,
    )
    monkeypatch.setattr(
        service, "read_strong_leader_pullback_sec_document_plan", lambda **_: plan
    )
    monkeypatch.setattr(
        service, "read_strong_leader_pullback_sec_document_source", lambda **_: source
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_transaction_candidates",
        lambda **_: transaction,
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_case_coverage_census",
        lambda **_: coverage,
    )


def _build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> service.StrongLeaderPullbackSecCaseAdjudicationResult:
    values = _fixture(tmp_path)
    _patch_inputs(monkeypatch, *values)
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    return service.build_strong_leader_pullback_sec_case_adjudication(
        source_sample_root=Path("/unused/sample"),
        source_sample_custody_root=Path("/unused"),
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        transaction_root=Path("/unused/transaction"),
        transaction_custody_root=Path("/unused"),
        coverage_root=Path("/unused/coverage"),
        coverage_custody_root=Path("/unused"),
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 19, tzinfo=UTC),
    )


def test_adjudicates_point_in_time_cover_identity_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _build(tmp_path, monkeypatch)

    assert result.status == "published"
    assert result.report.cover_8k_document_count == 62
    assert result.report.cover_security_row_count == 70
    assert result.report.incomplete_security_context_count == 1
    assert result.report.matched_cover_document_count == 61
    assert result.report.outside_lifecycle_window_document_count == 1
    assert result.report.matched_identity_case_count == 61
    assert result.report.result_state_counts == (("matched", 61), ("unsupported", 451))
    assert result.report.cover_documents[-1].resolution_state == (
        "outside_source_lifecycle_window"
    )
    assert result.report.cover_documents[-1].matched_row_fingerprint is None
    assert (result.output_root / "adjudication.json").stat().st_mode & 0o777 == 0o400


def test_exact_rerun_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _build(tmp_path, monkeypatch)
    reread = service.read_strong_leader_pullback_sec_case_adjudication(
        output_root=result.output_root,
        output_custody_root=result.output_root.parent,
    )
    assert reread.status == "already_present"
    assert reread.report == result.report


def test_tampered_adjudication_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _build(tmp_path, monkeypatch)
    path = result.output_root / "adjudication.json"
    path.chmod(0o600)
    path.write_bytes(
        path.read_bytes().replace(
            b'"canonical_identity_write_count":0',
            b'"canonical_identity_write_count":1',
        )
    )
    path.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecCaseAdjudicationError):
        service.read_strong_leader_pullback_sec_case_adjudication(
            output_root=result.output_root,
            output_custody_root=result.output_root.parent,
        )
