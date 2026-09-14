from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_content_census as service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")


def _fixture(
    tmp_path: Path,
) -> tuple[SimpleNamespace, SimpleNamespace, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    specs = (
        (
            "0000876661-25-000952",
            "25-NSE",
            b"<html><body>Removal from listing. Trading symbol SCS.</body></html>",
        ),
        (
            "0001193125-25-315864",
            "8-K",
            (
                b"<html xmlns:ix='http://www.xbrl.org/2013/inlineXBRL'>"
                b"<body>The merger was completed. Cash consideration per share. "
                b"Trading has been suspended.</body></html>"
            ),
        ),
        (
            "0001193125-25-327599",
            "15-12G",
            (
                b"<DOCUMENT><TYPE>15-12G<TEXT><html><body>Withdrawal of "
                b"registration. Commission file number.</body></html>"
            ),
        ),
    )
    items = []
    for sequence, (accession, form, raw) in enumerate(specs, 1):
        request_root = source_root / f"request={sequence:06d}"
        request_root.mkdir(mode=0o700)
        document = request_root / "document.bin"
        document.write_bytes(raw)
        document.chmod(0o400)
        items.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=INSTRUMENT_ID,
                cik="0001050825",
                accession_number=accession,
                form=form,
                acceptance_datetime=datetime(2025, 12, 10, tzinfo=UTC)
                + timedelta(days=sequence),
            )
        )
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
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    return plan, source, custody


def _patch_readers(
    monkeypatch: pytest.MonkeyPatch,
    plan: SimpleNamespace,
    source: SimpleNamespace,
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


def test_builds_and_formally_rereads_three_document_content_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, custody = _fixture(tmp_path)
    _patch_readers(monkeypatch, plan, source)
    target = custody / "census=fixture"

    result = service.build_strong_leader_pullback_terminal_population_sec_content_census(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.document_count == 3
    assert result.report.parsed_document_count == 3
    assert result.report.form_counts == (
        ("15-12G", 1),
        ("25-NSE", 1),
        ("8-K", 1),
    )
    assert result.report.markup_profile_counts == (
        ("html", 1),
        ("sec-sgml-html", 1),
        ("xhtml-inline-xbrl", 1),
    )
    assert result.report.lifecycle_fact_count == 0
    assert result.report.terminal_outcome_count == 0
    assert result.report.network_request_count == 0
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400

    reread = service.read_strong_leader_pullback_terminal_population_sec_content_census(
        output_root=target, output_custody_root=custody
    )
    assert reread.report == result.report
    assert reread.report_sha256 == result.report_sha256


def test_source_count_mismatch_fails_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, custody = _fixture(tmp_path)
    source.completed_document_count = 2
    _patch_readers(monkeypatch, plan, source)

    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecContentCensusError,
        match="source count differs",
    ):
        service.build_strong_leader_pullback_terminal_population_sec_content_census(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            output_root=custody / "census=fixture",
            output_custody_root=custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
        )


def test_tampering_and_network_attempt_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, custody = _fixture(tmp_path)
    _patch_readers(monkeypatch, plan, source)
    target = custody / "census=fixture"
    service.build_strong_leader_pullback_terminal_population_sec_content_census(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
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
        service.StrongLeaderPullbackTerminalPopulationSecContentCensusError
    ):
        service.read_strong_leader_pullback_terminal_population_sec_content_census(
            output_root=target, output_custody_root=custody
        )

    def network_reader(**_: object) -> object:
        socket.create_connection(("example.com", 443))
        return plan

    other_custody = tmp_path / "other-evidence"
    other_custody.mkdir(mode=0o700)
    monkeypatch.setattr(
        service.plan_reader,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        network_reader,
    )
    with pytest.raises(RuntimeError, match="network access is prohibited"):
        service.build_strong_leader_pullback_terminal_population_sec_content_census(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            output_root=other_custody / "census=fixture",
            output_custody_root=other_custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
        )
