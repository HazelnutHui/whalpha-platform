from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_sec_transaction_event_adjudication as service,
)


def _document(body: str) -> bytes:
    return (
        "<html><body><div>Introductory Note</div>"
        f"<p>{body}</p>"
        "<div>Item 1.01.</div><p>Unrelated financing dated January 1, 2020.</p>"
        "<div>Item 2.01.</div><p>Completion of Acquisition or Disposition of Assets.</p>"
        "<div>Item 3.01.</div><p>Notice of Delisting.</p></body></html>"
    ).encode()


@pytest.mark.parametrize(
    ("introduction", "scope", "rule", "expected"),
    (
        (
            "On January 3, 2026 (the Closing Date), Merger Sub merged with and into Issuer.",
            "On January 3, 2026 (the Closing Date), Merger Sub merged with and "
            "into Issuer. Item 2.01 Completion.",
            "named_closing_date_in_introduction",
            date(2026, 1, 3),
        ),
        (
            "This report concerns the closing on January 4, 2026 "
            "(the Effective Time) of the merger.",
            "This report concerns the closing on January 4, 2026 "
            "(the Effective Time) of the merger. Item 2.01 Completion.",
            "closing_of_merger_date_in_introduction",
            date(2026, 1, 4),
        ),
        (
            "On January 5, 2026, Parent completed the acquisition of Issuer.",
            "On January 5, 2026, Parent completed the acquisition of Issuer. Item 2.01 Completion.",
            "dated_transaction_completion_statement",
            date(2026, 1, 5),
        ),
        (
            "On January 6, 2026, Purchaser accepted for payment all shares. "
            "Accordingly, Purchaser effected the Merger.",
            "On January 6, 2026, Purchaser accepted for payment all shares. "
            "Accordingly, Purchaser effected the Merger. Item 2.01 Completion.",
            "tender_acceptance_followed_by_effected_merger",
            date(2026, 1, 6),
        ),
    ),
)
def test_registered_rules_are_typed(
    introduction: str, scope: str, rule: str, expected: date
) -> None:
    evidence = service._completion_evidence(
        scope=scope, introduction=introduction
    )

    assert len(evidence) == 1
    assert evidence[0].decision_rule == rule
    assert evidence[0].event_date == expected


def test_scope_excludes_intervening_items_and_supports_implicit_introduction() -> None:
    parser = service._DocumentParser()
    parser.feed(
        "<html><body>"
        "<p>On June 1, 2026 (the Closing Date), the Mergers and related "
        "transactions were consummated.</p>"
        "<div>Item 1.02.</div><p>Unrelated.</p>"
        "<div>Item 2.01.</div><p>On the Closing Date, the Company consummated the Mergers.</p>"
        "<div>Item 3.01.</div><p>Excluded.</p>"
        "</body></html>"
    )
    parser.close()

    introduction, item_two, profile = service._transaction_scope(tuple(parser.nodes))

    assert profile == "implicit_pre_item_completion_and_item_2_01"
    assert "June 1, 2026" in introduction
    assert "Unrelated" not in introduction
    assert "Excluded" not in item_two


def _fixture(tmp_path: Path) -> tuple[object, object, object, object]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    candidates = []
    cover_documents = []
    for sequence in range(1, 62):
        event_day = 3 if sequence == 1 else 2
        raw = _document(
            f"On January {event_day}, 2026 (the Closing Date), "
            "Merger Sub merged with and into Issuer."
        )
        parser = service._DocumentParser()
        parser.feed(raw.decode())
        parser.close()
        normalized = service._normalized_text(" ".join(parser.raw_parts))
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        (directory / "document.bin").write_bytes(raw)
        candidates.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                accession_number=f"{sequence:010d}-26-{sequence:06d}",
                filing_date=date(2026, 1, 4),
                acceptance_datetime=datetime(2026, 1, 4, 20, tzinfo=UTC),
                document_sha256=hashlib.sha256(raw).hexdigest(),
                normalized_text_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
                normalized_text_character_count=len(normalized),
            )
        )
        cover_documents.append(
            SimpleNamespace(
                request_sequence=sequence,
                transaction_structure_state="8k_item_2_01_candidate_scope",
                resolution_state="matched_in_source_lifecycle_window",
                report_date=date(2026, 1, 2),
                logical_fingerprint=f"{sequence:064x}",
            )
        )
    plan = SimpleNamespace(plan_sha256="1" * 64)
    source = SimpleNamespace(
        output_root=source_root,
        manifest=SimpleNamespace(),
        manifest_sha256="2" * 64,
    )
    transaction = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            logical_fingerprint="3" * 64,
            candidates=tuple(candidates),
        ),
        report_sha256="4" * 64,
    )
    cover = SimpleNamespace(
        report=SimpleNamespace(
            plan_sha256="1" * 64,
            source_manifest_sha256="2" * 64,
            transaction_report_sha256="4" * 64,
            logical_fingerprint="5" * 64,
            cover_documents=tuple(cover_documents),
        ),
        report_sha256="6" * 64,
    )
    return plan, source, transaction, cover


def test_builds_immutable_event_evidence_without_using_cover_date(
    tmp_path: Path,
) -> None:
    plan, source, transaction, cover = _fixture(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        transaction=transaction,
        cover=cover,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 21, tzinfo=UTC),
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)

    result = service._write_report(
        output_root=custody / "adjudication=fixture",
        output_custody_root=custody,
        report=report,
    )
    reread = service.read_strong_leader_pullback_sec_transaction_event_adjudication(
        output_root=result.output_root, output_custody_root=custody
    )

    assert report.matched_event_count == 61
    assert report.report_date_relation_counts == (
        ("after_report_date", 1),
        ("same_as_report_date", 60),
    )
    assert report.decisions[0].selected_event_date == date(2026, 1, 3)
    assert report.decisions[0].report_date == date(2026, 1, 2)
    assert report.termination_reason_adjudication_count == 0
    assert report.lifecycle_fact_count == 0
    assert result.status == "published"
    assert reread.status == "already_present"
    assert (result.output_root / "transaction-events.json").stat().st_mode & 0o777 == 0o400


def test_ambiguous_same_priority_dates_are_not_selected() -> None:
    scope = (
        "On January 3, 2026, Parent completed the acquisition. "
        "On January 4, 2026, Merger Sub merged with and into Issuer."
    )

    evidence = service._completion_evidence(scope=scope, introduction=scope)

    assert {item.event_date for item in evidence} == {
        date(2026, 1, 3),
        date(2026, 1, 4),
    }


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackSecTransactionEventAdjudicationError,
        match="network access is prohibited",
    ):
        socket.socket()
