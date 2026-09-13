from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_sec_consideration_adjudication as service,
)


def _document(*, clause: str | None = None) -> bytes:
    consideration = clause or (
        "At the Effective Time, each share of common stock issued and outstanding "
        "immediately prior to the Effective Time was converted into the right to "
        "receive $25.00 per share in cash (the Merger Consideration)."
    )
    return (
        "<html><body><div>Introductory Note</div>"
        "<p>On January 3, 2026, the merger was completed.</p>"
        "<div>Item 2.01</div><p>Completion of Acquisition.</p>"
        f"<p>{consideration}</p>"
        "<div>Item 3.01</div><p>Notice of Delisting.</p>"
        "</body></html>"
    ).encode()


def _fixture(tmp_path: Path) -> tuple[object, object, object, object, object]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    cover_documents = []
    event_decisions = []
    reason_decisions = []
    for sequence in range(1, 62):
        raw = _document()
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        (directory / "document.bin").write_bytes(raw)
        parser = service._DocumentParser()
        parser.feed(raw.decode())
        parser.close()
        introduction, item_two, _ = service._transaction_scope(tuple(parser.nodes))
        scope = service._normalized_text(f"{introduction} {item_two}")
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
                scope_character_count=len(scope),
                scope_sha256=hashlib.sha256(scope.encode()).hexdigest(),
                logical_fingerprint=f"{sequence + 100:064x}",
            )
        )
        reason_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=UUID(int=sequence),
                document_sha256=hashlib.sha256(raw).hexdigest(),
                transaction_event_fingerprint=f"{sequence + 100:064x}",
                resolution_state="matched",
                logical_fingerprint=f"{sequence + 200:064x}",
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
    return plan, source, cover, events, reasons


def test_builds_bounded_cash_consideration_without_terminal_authority(
    tmp_path: Path,
) -> None:
    plan, source, cover, events, reasons = _fixture(tmp_path)

    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        reasons=reasons,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 23, tzinfo=UTC),
    )

    assert report.matched_consideration_count == 61
    assert report.consideration_structure_counts == (("cash_only", 61),)
    assert report.consideration_component_counts == (("cash", 61),)
    assert report.normalized_payoff_term_count == 0
    assert report.lifecycle_fact_count == 0
    assert report.terminal_outcome_count == 0


@pytest.mark.parametrize(
    ("evidence", "expected"),
    (
        (
            "Each share was converted into the right to receive 1.5 shares of "
            "Buyer common stock and cash in lieu of fractional shares.",
            "stock_only",
        ),
        (
            "Each share was converted into the right to receive $10.00 in cash "
            "and 0.5 shares of Buyer common stock.",
            "fixed_cash_and_stock",
        ),
        (
            "Each share was converted into the right to receive $10.00 in cash "
            "plus one contingent value right (CVR).",
            "cash_plus_contingent_value_right",
        ),
        (
            "Each share was converted into the right to receive, at the election "
            "of the holder, $20.00 in cash or 0.5 shares of Buyer common stock.",
            "holder_election_cash_or_stock",
        ),
        (
            "Each share was converted into the right to receive, subject to the "
            "election mechanics, $63.00 in cash or $57.00 in cash and one "
            "unlisted limited liability company unit.",
            "holder_election_cash_or_cash_plus_unlisted_unit",
        ),
    ),
)
def test_classifies_registered_structures(evidence: str, expected: str) -> None:
    result = service._classify_consideration(evidence)

    assert result is not None
    assert result[0] == expected


def test_primary_clause_excludes_award_bullet() -> None:
    scope = service._normalized_text(
        "Introductory Note. On January 3, 2026, the merger was completed. "
        "Item 2.01 Completion. • Each outstanding share of common stock was "
        "converted into the right to receive $25.00 in cash. • Each option was "
        "converted into an award of Buyer shares."
    )

    candidate = service._primary_consideration_candidate(scope)

    assert candidate is not None
    assert "Each option" not in candidate[2]


def test_report_is_immutable_and_idempotent(tmp_path: Path) -> None:
    plan, source, cover, events, reasons = _fixture(tmp_path)
    report = service._build_report(
        plan=plan,
        source=source,
        cover=cover,
        events=events,
        reasons=reasons,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 23, tzinfo=UTC),
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
    assert (first.output_root / "consideration.json").stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackSecConsiderationAdjudicationError,
        match="network access is prohibited",
    ):
        socket.socket()
