from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_sec_document_content_census as service,
)


def _fixture(tmp_path: Path) -> tuple[SimpleNamespace, SimpleNamespace, Path, Path]:
    source_root = tmp_path / "source" / "source=fixture"
    source_root.mkdir(parents=True, mode=0o700)
    items = []
    for index in range(219):
        sequence = index + 1
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir(mode=0o700)
        if index == 0:
            raw = (
                b"\xef\xbb\xbf<html><body>Trading symbol. Last trading day. "
                b"The shares were delisted after the merger. The purchaser "
                b"paid cash consideration. Chapter 11. The filing was amended. "
                b"September 13, 2026.</body></html>"
            )
        elif index == 1:
            raw = b"<DOCUMENT><TYPE>8-K<TEXT><html><body>ordinary</body></html>"
        elif index == 2:
            raw = (
                b"<html xmlns:ix='http://www.xbrl.org/2013/inlineXBRL'>"
                b"<body>ordinary</body></html>"
            )
        elif index == 3:
            raw = b"<html><body>legacy \x96 text</body></html>"
        else:
            raw = b"<html><body>ordinary filing 2026-01-01</body></html>"
        document = directory / "document.bin"
        document.write_bytes(raw)
        document.chmod(0o400)
        items.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                cik=f"{sequence:010d}",
                accession_number=f"9999999999-26-{sequence:06d}",
                form="8-K",
                acceptance_datetime=datetime(2026, 9, 13, tzinfo=UTC)
                + timedelta(seconds=index),
            )
        )
    plan = SimpleNamespace(
        plan=SimpleNamespace(items=tuple(items), logical_fingerprint="1" * 64),
        plan_sha256="2" * 64,
    )
    source = SimpleNamespace(
        output_root=source_root,
        manifest=SimpleNamespace(
            logical_fingerprint="3" * 64,
            artifact_binding_fingerprint="4" * 64,
        ),
        manifest_sha256="5" * 64,
    )
    output_custody = tmp_path / "evidence"
    output_custody.mkdir(mode=0o700)
    return plan, source, source_root, output_custody


def test_builds_and_formally_rereads_complete_content_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, _, custody = _fixture(tmp_path)
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
    target = custody / "census=fixture"
    result = service.build_strong_leader_pullback_sec_document_content_census(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 15, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.document_count == 219
    assert result.report.parsed_document_count == 219
    assert result.report.decoding_counts == (
        ("utf-8", 217),
        ("utf-8-sig", 1),
        ("windows-1252", 1),
    )
    assert result.report.markup_profile_counts == (
        ("html", 217),
        ("sec-sgml-html", 1),
        ("xhtml-inline-xbrl", 1),
    )
    assert all(count == 1 for _, count in result.report.field_marker_document_counts)
    assert result.report.lifecycle_fact_count == 0
    assert result.report.terminal_outcome_count == 0
    assert (target / "census.json").stat().st_mode & 0o777 == 0o400
    assert target.stat().st_mode & 0o777 == 0o700

    reread = service.read_strong_leader_pullback_sec_document_content_census(
        output_root=target,
        output_custody_root=custody,
    )
    assert reread.report == result.report
    assert reread.report_sha256 == result.report_sha256


def test_marker_contexts_are_bounded_and_not_promoted_to_facts() -> None:
    marker = service._field_marker(
        field="termination_reason",
        pattern=dict(service._COMPILED_PATTERNS)["termination_reason"],
        normalized_text="merger merger merger merger merger",
    )
    assert marker.occurrence_count == 5
    assert len(marker.retained_contexts) == 3
    assert marker.contexts_truncated is True
    assert marker.fact_disposition == "unresolved_lexical_candidate_only"


def test_tampered_census_and_network_attempt_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, _, custody = _fixture(tmp_path)
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
    target = custody / "census=fixture"
    service.build_strong_leader_pullback_sec_document_content_census(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 15, tzinfo=UTC),
    )
    path = target / "census.json"
    path.chmod(0o600)
    path.write_bytes(
        path.read_bytes().replace(
            b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1'
        )
    )
    path.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecDocumentContentCensusError):
        service.read_strong_leader_pullback_sec_document_content_census(
            output_root=target,
            output_custody_root=custody,
        )

    def network_reader(**_: object) -> object:
        socket.create_connection(("example.com", 443))
        return source

    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_plan",
        network_reader,
    )
    with pytest.raises(
        service.StrongLeaderPullbackSecDocumentContentCensusError,
        match="network access is prohibited",
    ):
        service.build_strong_leader_pullback_sec_document_content_census(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            output_root=other / "census=fixture",
            output_custody_root=other,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 13, 15, tzinfo=UTC),
        )
