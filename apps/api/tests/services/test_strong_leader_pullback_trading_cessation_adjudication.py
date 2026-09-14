from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_trading_cessation_adjudication as service


_SESSIONS = (
    date(2026, 1, 2),
    date(2026, 1, 5),
    date(2026, 1, 6),
    date(2026, 1, 7),
)


class _EodRepository:
    def __init__(self, *, conflicting_sequence: int | None = None) -> None:
        self.conflicting_sequence = conflicting_sequence

    def list_session_index(self) -> tuple[date, ...]:
        return _SESSIONS

    def read_history_sessions(self, sessions: tuple[date, ...]) -> tuple[object, ...]:
        reads = []
        for session in sessions:
            bars = []
            for sequence in service._REGISTERED_SEQUENCES:
                timing = service._registered_timing(sequence)
                if timing == "unresolved":
                    continue
                last = date(2026, 1, 5) if timing == "before_open" else date(2026, 1, 6)
                if sequence == self.conflicting_sequence:
                    last = date(2026, 1, 5)
                if session <= last:
                    bars.append(SimpleNamespace(instrument_id=UUID(int=sequence)))
            fingerprint = f"{session.toordinal():064x}"
            reads.append(
                SimpleNamespace(
                    integrity=SimpleNamespace(
                        session_date=session,
                        record_count=100,
                        content_fingerprint=fingerprint,
                        parquet_sha256=fingerprint,
                        identity_snapshot_date=session,
                        identity_snapshot_fingerprint=fingerprint,
                    ),
                    bars=tuple(bars),
                )
            )
        return tuple(reads)


def _inputs() -> tuple[object, object, object, object]:
    lifecycle_cases = []
    form25_candidates = []
    reason_decisions = []
    party_decisions = []
    for sequence in sorted(service._REGISTERED_SEQUENCES):
        instrument_id = UUID(int=sequence)
        lifecycle_cases.append(
            SimpleNamespace(
                instrument_id=instrument_id,
                provider_delist_date_candidate=date(2026, 1, 6),
            )
        )
        form25_candidates.append(
            SimpleNamespace(
                instrument_id=instrument_id,
                security_class_descriptions=("Common Stock",),
            )
        )
        timing = service._registered_timing(sequence)
        if timing == "before_open":
            text = "Item 3.01. Trading was suspended before the market opens."
        elif timing == "after_close":
            text = "Item 3.01. Trading was halted after market close."
        else:
            text = "Item 3.01. The exchange was requested to suspend trading."
        reason_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                transaction_completion_date=date(2026, 1, 6),
                item_3_01_text=text,
                resolution_state="matched",
                logical_fingerprint=f"{sequence + 100:064x}",
            )
        )
        party_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=instrument_id,
                transaction_completion_date=date(2026, 1, 6),
                termination_reason_fingerprint=f"{sequence + 100:064x}",
                resolution_state="matched",
                logical_fingerprint=f"{sequence + 200:064x}",
            )
        )
    sample = SimpleNamespace(
        report=SimpleNamespace(
            lifecycle_case_count=64,
            lifecycle_cases=tuple(lifecycle_cases),
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    form25 = SimpleNamespace(
        report=SimpleNamespace(
            form25_document_count=64,
            candidates=tuple(form25_candidates),
            logical_fingerprint="3" * 64,
        ),
        report_sha256="4" * 64,
    )
    reasons = SimpleNamespace(
        report=SimpleNamespace(
            matched_reason_count=61,
            decisions=tuple(reason_decisions),
            logical_fingerprint="5" * 64,
        ),
        report_sha256="6" * 64,
    )
    parties = SimpleNamespace(
        report=SimpleNamespace(
            termination_reason_report_sha256="6" * 64,
            termination_reason_logical_fingerprint="5" * 64,
            matched_relation_count=61,
            decisions=tuple(party_decisions),
            logical_fingerprint="7" * 64,
        ),
        report_sha256="8" * 64,
    )
    return sample, form25, reasons, parties


def _report(monkeypatch: pytest.MonkeyPatch, *, conflict: int | None = None) -> object:
    monkeypatch.setattr(service, "_STOP_DATE_OVERRIDES", {})
    sample, form25, reasons, parties = _inputs()
    return service._build_report(
        sample=sample,
        form25=form25,
        reasons=reasons,
        parties=parties,
        eod_repository=_EodRepository(conflicting_sequence=conflict),
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 12, tzinfo=UTC),
    )


def test_builds_bounded_last_eod_evidence_without_lifecycle_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _report(monkeypatch, conflict=1)

    assert report.matched_cessation_count == 52
    assert report.conflicting_cessation_count == 1
    assert report.unsupported_cessation_count == 8
    assert report.selected_eod_session_count == 4
    assert report.last_eod_observation_evidence_count == 53
    assert report.first_tradable_date_count == 0
    assert report.legal_delisting_effective_date_count == 0
    assert report.canonical_lifecycle_fact_count == 0
    assert report.terminal_outcome_count == 0


def test_reviewed_cessation_phrase_variants_are_bounded() -> None:
    variants = (
        ("Trading was halted effective as of 8:00 p.m., Eastern Time.", "after_close"),
        ("Trading was suspended prior to Nasdaq’s opening.", "before_open"),
        ("The NYSE was asked to suspend trading before the market opens.", "before_open"),
    )

    for text, timing in variants:
        candidate = service._primary_cessation_candidate(text, timing)
        assert candidate is not None
        assert candidate[2] == text


def test_report_is_owner_only_immutable_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = _report(monkeypatch)
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
        service.StrongLeaderPullbackTradingCessationAdjudicationError,
        match="network access is prohibited",
    ):
        socket.socket()
