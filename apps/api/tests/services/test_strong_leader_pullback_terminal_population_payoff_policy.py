from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_transaction_event_adjudication as event
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff
from tip_api.services import (
    strong_leader_pullback_terminal_population_payoff_policy as service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")
CONSIDERATION = (
    "Pursuant to the Merger Agreement, each share was converted into, at the "
    "election of the holder thereof, subject to automatic adjustment, the "
    "right to receive: (i) 0.2192 shares of HNI common stock and $7.20 in cash "
    "(the mixed election consideration); (ii) $16.19 in cash and 0.0009 shares "
    "of HNI common stock (the cash election consideration); or (iii) 0.3940 "
    "shares of HNI common stock (the stock election consideration)."
)


def _document(*, add_proration: bool = False) -> bytes:
    proration = " Proration applies." if add_proration else ""
    return f"""
    <html><body>
      <div>Introductory Note</div>
      <p>This report concerns the completion on December 10, 2025 (the Closing
      Date) of the acquisition by HNI Corporation, an Iowa corporation (HNI),
      of Steelcase Inc. (Steelcase), pursuant to the Agreement and Plan of
      Merger by and among HNI, Steelcase, Geranium Merger Sub I, Inc. (Merger
      Sub Inc.), and Geranium Merger Sub II, LLC (Merger Sub LLC).</p>
      <p>Pursuant to the Merger Agreement, Merger Sub Inc. merged with and into
      Steelcase, and Steelcase survived as a wholly owned subsidiary of HNI.
      Immediately after, Steelcase merged with and into Merger Sub LLC, the
      separate existence of Steelcase ceased, and Merger Sub LLC continued as
      the surviving entity and a wholly owned subsidiary of HNI.</p>
      <div>Item 2.01. Completion of Acquisition or Disposition of Assets.</div>
      <p>{CONSIDERATION}</p>
      <p>The “Parent Common Stock Reference Price” used for calculating the
      cash election consideration and stock election consideration is $41.1991
      based on a volume-weighted average closing price.</p>
      <p>Shares of Steelcase common stock owned by holders who did not make an
      election were converted into the right to receive mixed election
      consideration.{proration}</p>
      <div>Item 3.01. Notice of Delisting.</div>
    </body></html>
    """.encode()


def _inputs(tmp_path: Path, *, add_proration: bool = False) -> tuple[object, ...]:
    raw = _document(add_proration=add_proration)
    source_root = tmp_path / "source" / "source=fixture"
    request_root = source_root / "request=000002"
    request_root.mkdir(parents=True, mode=0o700)
    document = request_root / "document.bin"
    document.write_bytes(raw)
    document.chmod(0o400)
    parser = event._DocumentParser()
    parser.feed(raw.decode())
    parser.close()
    introduction, item_two, _ = event._transaction_scope(tuple(parser.nodes))
    scope = payoff._normalized_text(f"{introduction} {item_two}")
    document_sha = base._sha256_bytes(raw)
    identity = SimpleNamespace(
        instrument_id=INSTRUMENT_ID,
        document_sha256=document_sha,
        logical_fingerprint="1" * 64,
        resolution_state="matched_in_source_lifecycle_window",
    )
    transaction = SimpleNamespace(
        request_sequence=2,
        instrument_id=INSTRUMENT_ID,
        accession_number="0001193125-25-315864",
        filing_date=date(2025, 12, 11),
        acceptance_datetime=datetime(2025, 12, 11, 16, tzinfo=UTC),
        document_sha256=document_sha,
        logical_fingerprint="2" * 64,
        selected_event_date=date(2025, 12, 10),
        scope_character_count=len(scope),
        scope_sha256=base._sha256_bytes(scope.encode()),
    )
    termination = SimpleNamespace(
        instrument_id=INSTRUMENT_ID,
        document_sha256=document_sha,
        transaction_event_fingerprint="2" * 64,
        logical_fingerprint="3" * 64,
    )
    consideration = SimpleNamespace(
        request_sequence=2,
        instrument_id=INSTRUMENT_ID,
        document_sha256=document_sha,
        transaction_event_fingerprint="2" * 64,
        termination_reason_fingerprint="3" * 64,
        logical_fingerprint="4" * 64,
        resolution_state="matched",
        consideration_structure="holder_election_cash_or_stock",
        evidence_text=CONSIDERATION,
    )
    plan = SimpleNamespace(
        report=SimpleNamespace(cases=(object(),)), report_sha256="5" * 64
    )
    source = SimpleNamespace(
        output_root=source_root,
        manifest_sha256="6" * 64,
        manifest=SimpleNamespace(logical_fingerprint="7" * 64),
    )
    core = SimpleNamespace(
        report_sha256="8" * 64,
        report=SimpleNamespace(
            plan_sha256="5" * 64,
            source_manifest_sha256="6" * 64,
            source_logical_fingerprint="7" * 64,
            logical_fingerprint="9" * 64,
            transaction_event=transaction,
            cover_identity=identity,
            termination_reason=termination,
            common_share_consideration=consideration,
        ),
    )
    cessation = SimpleNamespace(
        report_sha256="a" * 64,
        report=SimpleNamespace(
            core_adjudication_report_sha256="8" * 64,
            core_adjudication_logical_fingerprint="9" * 64,
            logical_fingerprint="b" * 64,
            decision=SimpleNamespace(resolution_state="matched"),
        ),
    )
    return plan, source, core, cessation


def _report(tmp_path: Path, *, add_proration: bool = False) -> object:
    plan, source, core, cessation = _inputs(
        tmp_path, add_proration=add_proration
    )
    return service._build_report(
        plan=plan,
        source=source,
        core=core,
        cessation=cessation,
        implementation_revision="c" * 40,
        evaluated_at=datetime(2026, 9, 14, 11, tzinfo=UTC),
    )


def test_normalizes_three_elections_and_source_default_without_valuation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)

    assert report.party_relation.resolution_state == "matched"
    assert report.party_relation.relation_topology == (
        "target_absorbed_into_other_survivor"
    )
    assert len(report.normalized_terms) == 5
    assert tuple(item.alternative_code for item in report.alternatives) == (
        "cash_election",
        "mixed_election",
        "stock_election",
    )
    assert report.default_no_valid_election_alternative == "mixed_election"
    assert report.actual_holder_election_known is False
    assert report.proration_state == "not_stated_in_retained_completion_scope"
    assert report.consideration_issuer_stable_id_assignment_count == 0
    assert report.terminal_reference_value_count == 0
    assert report.terminal_outcome_count == 0


def test_unadjudicated_proration_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationPayoffPolicyError,
        match="unadjudicated proration",
    ):
        _report(tmp_path, add_proration=True)


def test_report_is_owner_only_immutable_and_idempotent(tmp_path: Path) -> None:
    report = _report(tmp_path)
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
    assert (first.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service.base._network_prohibited(), pytest.raises(
        RuntimeError, match="network access is prohibited"
    ):
        socket.socket()
