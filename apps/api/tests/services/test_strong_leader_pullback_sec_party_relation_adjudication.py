from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_sec_party_relation_adjudication as service,
)


def _document() -> bytes:
    return (
        "<html><body><div>Introductory Note</div>"
        "<p>On January 3, 2026, Example Target Inc. (the Company) completed "
        "the Agreement and Plan of Merger (the Merger Agreement) entered into "
        "with Example Parent LLC (Parent) and Example Merger Sub Inc. "
        "(Merger Sub). Merger Sub merged with and into the Company, with the "
        "Company surviving as a wholly owned subsidiary of Parent.</p>"
        "<div>Item 2.01</div><p>Completion of Acquisition.</p>"
        "<p>Each share of common stock was converted into the right to receive "
        "$25.00 per share in cash.</p>"
        "<div>Item 3.01</div><p>Notice of Delisting.</p>"
        "</body></html>"
    ).encode()


def _fixture(tmp_path: Path) -> tuple[object, object, object, object, object, object]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    cover_documents = []
    event_decisions = []
    reason_decisions = []
    consideration_decisions = []
    raw = _document()
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    for sequence in sorted(service._REGISTERED_SEQUENCES):
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        (directory / "document.bin").write_bytes(raw)
        parser = service._DocumentParser()
        parser.feed(raw.decode())
        parser.close()
        introduction, item_two, _ = service._transaction_scope(tuple(parser.nodes))
        scope = service._normalized_text(f"{introduction} {item_two}")
        instrument_id = UUID(int=sequence)
        cover_documents.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                document_sha256=raw_sha256,
                resolution_state="matched_in_source_lifecycle_window",
                transaction_structure_state="8k_item_2_01_candidate_scope",
                logical_fingerprint=f"{sequence:064x}",
            )
        )
        event_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                accession_number=f"{sequence:010d}-26-{sequence:06d}",
                filing_date=date(2026, 1, 4),
                acceptance_datetime=datetime(2026, 1, 4, 20, tzinfo=UTC),
                document_sha256=raw_sha256,
                selected_event_date=date(2026, 1, 3),
                scope_character_count=len(scope),
                scope_sha256=hashlib.sha256(scope.encode()).hexdigest(),
                logical_fingerprint=f"{sequence + 300:064x}",
            )
        )
        reason_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                document_sha256=raw_sha256,
                transaction_event_fingerprint=f"{sequence + 300:064x}",
                resolution_state="matched",
                logical_fingerprint=f"{sequence + 400:064x}",
            )
        )
        consideration_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                document_sha256=raw_sha256,
                transaction_event_fingerprint=f"{sequence + 300:064x}",
                termination_reason_fingerprint=f"{sequence + 400:064x}",
                resolution_state="matched",
                consideration_components=("cash",),
                logical_fingerprint=f"{sequence + 500:064x}",
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
    reasons = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            cover_adjudication_report_sha256="4" * 64,
            transaction_event_report_sha256="6" * 64,
            matched_reason_count=61,
            logical_fingerprint="7" * 64,
            decisions=tuple(reason_decisions),
        ),
        report_sha256="8" * 64,
    )
    consideration = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            cover_adjudication_report_sha256="4" * 64,
            transaction_event_report_sha256="6" * 64,
            termination_reason_report_sha256="8" * 64,
            matched_consideration_count=61,
            logical_fingerprint="9" * 64,
            decisions=tuple(consideration_decisions),
        ),
        report_sha256="a" * 64,
    )
    return plan, source, cover, events, reasons, consideration


def test_builds_finite_source_relation_adjudication_without_identity_authority(
    tmp_path: Path,
) -> None:
    plan, source, cover, events, reasons, consideration = _fixture(tmp_path)

    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        reasons=reasons,
        consideration=consideration,
        implementation_revision="b" * 40,
        evaluated_at=datetime(2026, 9, 14, 1, tzinfo=UTC),
    )

    assert report.matched_relation_count == 61
    assert report.relation_topology_counts == (
        ("target_absorbed_into_other_survivor", 11),
        ("target_and_peer_absorbed_into_new_holding_company", 1),
        ("target_survives_as_owned_subsidiary", 49),
    )
    assert report.counterparty_stable_id_assignment_count == 0
    assert report.canonical_party_identity_count == 0
    assert report.lifecycle_fact_count == 0
    assert report.terminal_outcome_count == 0


def test_party_and_relation_clauses_are_bounded() -> None:
    raw = _document()
    parser = service._DocumentParser()
    parser.feed(raw.decode())
    parser.close()
    introduction, item_two, _ = service._transaction_scope(tuple(parser.nodes))
    scope = service._normalized_text(f"{introduction} {item_two}")

    party = service._primary_party_definition_candidate(scope)
    relation = service._primary_relation_candidate(scope)

    assert party is not None
    assert relation is not None
    assert "Agreement and Plan of Merger" in party[2]
    assert "surviving" in relation[2]


def test_report_is_immutable_and_idempotent(tmp_path: Path) -> None:
    plan, source, cover, events, reasons, consideration = _fixture(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        reasons=reasons,
        consideration=consideration,
        implementation_revision="b" * 40,
        evaluated_at=datetime(2026, 9, 14, 1, tzinfo=UTC),
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
    assert (first.output_root / "party-relations.json").stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackSecPartyRelationAdjudicationError,
        match="network access is prohibited",
    ):
        socket.socket()
