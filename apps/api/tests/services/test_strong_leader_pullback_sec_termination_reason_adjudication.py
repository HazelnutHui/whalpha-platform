from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_sec_termination_reason_adjudication as service,
)


def _document(*, transaction_marker: str = "Merger") -> bytes:
    return (
        "<html><body>"
        "<div>Item 2.01</div><p>Completion of Acquisition.</p>"
        "<p>Item 3.01, Item 5.01 are incorporated by reference.</p>"
        "<div>Item 3.01</div>"
        "<p>Notice of Delisting or Failure to Satisfy a Continued Listing Rule.</p>"
        f"<p>In connection with completion of the {transaction_marker}, Issuer "
        "requested that Nasdaq suspend trading and file Form 25 to delist the "
        "common stock.</p>"
        "<div>Item 5.01</div><p>Changes in Control.</p>"
        "</body></html>"
    ).encode()


def _fixture(tmp_path: Path) -> tuple[object, object, object, object]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    cover_documents = []
    event_decisions = []
    for sequence in range(1, 62):
        raw = _document()
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        (directory / "document.bin").write_bytes(raw)
        cover_documents.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                document_sha256=hashlib.sha256(raw).hexdigest(),
                resolution_state="matched_in_source_lifecycle_window",
                transaction_structure_state="8k_item_2_01_candidate_scope",
                logical_fingerprint=f"{sequence:064x}",
            )
        )
        event_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                accession_number=f"{sequence:010d}-26-{sequence:06d}",
                filing_date=date(2026, 1, 4),
                acceptance_datetime=datetime(2026, 1, 4, 20, tzinfo=UTC),
                document_sha256=hashlib.sha256(raw).hexdigest(),
                selected_event_date=date(2026, 1, 3),
                logical_fingerprint=f"{sequence + 100:064x}",
            )
        )
    plan = SimpleNamespace(plan_sha256="1" * 64)
    source = SimpleNamespace(
        output_root=source_root,
        manifest=SimpleNamespace(),
        manifest_sha256="2" * 64,
    )
    cover = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            logical_fingerprint="3" * 64,
            cover_documents=tuple(cover_documents),
        ),
        report_sha256="4" * 64,
    )
    events = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            cover_adjudication_report_sha256="4" * 64,
            matched_event_count=61,
            logical_fingerprint="5" * 64,
            decisions=tuple(event_decisions),
        ),
        report_sha256="6" * 64,
    )
    return plan, source, cover, events


def test_builds_bounded_termination_reasons_without_terminal_dates(
    tmp_path: Path,
) -> None:
    plan, source, cover, events = _fixture(tmp_path)

    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 22, tzinfo=UTC),
    )

    assert report.matched_reason_count == 61
    assert report.resolution_state_counts == (("matched", 61),)
    assert report.listing_action_counts == (
        ("delisting", 61),
        ("form_25_request", 61),
        ("trading_suspension", 61),
    )
    assert all(
        item.termination_reason == "merger_or_acquisition"
        for item in report.decisions
    )
    assert report.effective_delisting_date_count == 0
    assert report.first_or_last_tradable_date_count == 0
    assert report.lifecycle_fact_count == 0


def test_item_reference_is_not_misread_as_section_heading() -> None:
    parser = service._DocumentParser()
    parser.feed(_document().decode())
    parser.close()

    sections = service._item_sections(tuple(parser.nodes), "3.01")

    assert len(sections) == 1
    assert "Notice of Delisting" in sections[0][0]
    assert "Item 5.01" not in sections[0][1]


def test_missing_transaction_marker_stays_unsupported(tmp_path: Path) -> None:
    raw = _document(transaction_marker="refinancing")
    path = tmp_path / "document.bin"
    path.write_bytes(raw)
    event = SimpleNamespace(
        request_sequence=1,
        instrument_id=UUID(int=1),
        accession_number="0000000001-26-000001",
        filing_date=date(2026, 1, 4),
        acceptance_datetime=datetime(2026, 1, 4, 20, tzinfo=UTC),
        document_sha256=hashlib.sha256(raw).hexdigest(),
        selected_event_date=date(2026, 1, 3),
        logical_fingerprint="1" * 64,
    )
    identity = SimpleNamespace(
        instrument_id=UUID(int=1),
        document_sha256=hashlib.sha256(raw).hexdigest(),
        logical_fingerprint="2" * 64,
    )

    decision = service._document_decision(
        event=event, identity=identity, path=path
    )

    assert decision.resolution_state == "unsupported"
    assert decision.termination_reason is None


def test_report_is_immutable_and_idempotent(tmp_path: Path) -> None:
    plan, source, cover, events = _fixture(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 22, tzinfo=UTC),
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)

    first = service._write_report(
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=first.output_root,
        output_custody_root=custody,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert (first.output_root / "termination-reasons.json").stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackSecTerminationReasonAdjudicationError,
        match="network access is prohibited",
    ):
        socket.socket()
