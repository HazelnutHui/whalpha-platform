from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_terminal_payoff_terms as service


def _inputs(*, unsupported_sequence: int | None = None) -> tuple[object, object, object]:
    considerations = []
    parties = []
    cessation = []
    for sequence, spec in sorted(service._CASE_SPECS.items()):
        instrument_id = UUID(int=sequence)
        evidence = ". ".join(item.source_literal for item in spec.terms)
        consideration_fingerprint = f"{sequence + 100:064x}"
        party_fingerprint = f"{sequence + 200:064x}"
        considerations.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                resolution_state="matched",
                consideration_structure=spec.structure,
                fractional_share_cash_adjustment=False,
                evidence_text=evidence,
                evidence_sha256=hashlib.sha256(evidence.encode()).hexdigest(),
                logical_fingerprint=consideration_fingerprint,
            )
        )
        parties.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                resolution_state="matched",
                consideration_fingerprint=consideration_fingerprint,
                listed_equity_consideration=(
                    spec.listed_equity_issuer_locator is not None
                ),
                logical_fingerprint=party_fingerprint,
            )
        )
        cessation.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                resolution_state=(
                    "unsupported" if sequence == unsupported_sequence else "matched"
                ),
                party_relation_fingerprint=party_fingerprint,
                logical_fingerprint=f"{sequence + 300:064x}",
            )
        )
    consideration = SimpleNamespace(
        report=SimpleNamespace(
            matched_consideration_count=61,
            decisions=tuple(considerations),
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    party = SimpleNamespace(
        report=SimpleNamespace(
            consideration_report_sha256="2" * 64,
            consideration_logical_fingerprint="1" * 64,
            matched_relation_count=61,
            decisions=tuple(parties),
            logical_fingerprint="3" * 64,
        ),
        report_sha256="4" * 64,
    )
    cessation_result = SimpleNamespace(
        report=SimpleNamespace(
            party_relation_report_sha256="4" * 64,
            party_relation_logical_fingerprint="3" * 64,
            lifecycle_case_count=61,
            decisions=tuple(cessation),
            logical_fingerprint="5" * 64,
        ),
        report_sha256="6" * 64,
    )
    return consideration, party, cessation_result


def test_normalizes_registered_terms_without_opening_terminal_outcomes() -> None:
    consideration, parties, cessation = _inputs(unsupported_sequence=7)

    report = service._build_report(
        consideration=consideration,
        parties=parties,
        cessation=cessation,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 15, tzinfo=UTC),
    )

    assert report.source_numeric_term_count == 81
    assert report.fixed_cash_payoff_term_count == 37
    assert report.listed_equity_ratio_case_count == 16
    assert report.cvr_case_count == 7
    assert report.holder_election_case_count == 4
    assert report.unlisted_unit_case_count == 1
    assert report.fractional_share_cash_adjustment_count == 0
    assert report.fixed_cash_and_timing_ready_count == 36
    assert report.terminal_outcome_count == 0
    assert report.canonical_lifecycle_fact_count == 0


def test_cash_and_complex_terms_remain_distinct() -> None:
    consideration, parties, cessation = _inputs()
    report = service._build_report(
        consideration=consideration,
        parties=parties,
        cessation=cessation,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 15, tzinfo=UTC),
    )
    by_sequence = {item.request_sequence: item for item in report.decisions}

    assert by_sequence[7].terminal_candidate_state == "fixed_cash_and_timing_ready"
    assert by_sequence[1].listed_equity_issuer_locator == "Rayonier"
    assert by_sequence[49].terminal_candidate_state == (
        "contingent_value_realization_unresolved"
    )
    assert len(by_sequence[92].alternatives) == 3
    assert by_sequence[100].terminal_candidate_state == "unlisted_unit_value_unresolved"


def test_report_is_owner_only_immutable_and_idempotent(tmp_path: Path) -> None:
    consideration, parties, cessation = _inputs()
    report = service._build_report(
        consideration=consideration,
        parties=parties,
        cessation=cessation,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 15, tzinfo=UTC),
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
    assert (first.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackTerminalPayoffTermsError,
        match="network access is prohibited",
    ):
        socket.socket()
