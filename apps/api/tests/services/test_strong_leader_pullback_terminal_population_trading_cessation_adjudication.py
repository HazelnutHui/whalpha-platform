from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import (
    strong_leader_pullback_terminal_population_trading_cessation_adjudication as service,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")
SESSIONS = (
    date(2025, 12, 8),
    date(2025, 12, 9),
    date(2025, 12, 10),
    date(2025, 12, 11),
)
ITEM_3_01 = (
    "Item 3.01 Notice of Delisting. In connection with the Mergers, on "
    "December 10, 2025, Steelcase requested that NYSE halt trading of "
    "Steelcase common stock prior to the opening of trading on December 10, "
    "2025. Trading of Steelcase common stock on NYSE halted prior to the "
    "opening of trading on December 10, 2025."
)


class _EodRepository:
    def __init__(self, *, next_present: bool = False) -> None:
        self.next_present = next_present

    def list_session_index(self) -> tuple[date, ...]:
        return SESSIONS

    def read_instrument_presence_sessions(
        self, session_dates: tuple[date, ...], instrument_ids: frozenset[UUID]
    ) -> tuple[object, ...]:
        assert instrument_ids == frozenset({INSTRUMENT_ID})
        reads = []
        for session in session_dates:
            fingerprint = f"{session.toordinal():064x}"
            present = session <= date(2025, 12, 9) or (
                self.next_present and session == date(2025, 12, 10)
            )
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
                    instrument_ids=(frozenset({INSTRUMENT_ID}) if present else frozenset()),
                )
            )
        return tuple(reads)


def _core(*, item_3_01_text: str = ITEM_3_01) -> object:
    return SimpleNamespace(
        report_sha256="1" * 64,
        report=SimpleNamespace(
            lifecycle_case_count=1,
            logical_fingerprint="2" * 64,
            source_case_fingerprint="3" * 64,
            cover_identity=SimpleNamespace(
                resolution_state="matched_in_source_lifecycle_window"
            ),
            transaction_event=SimpleNamespace(
                resolution_state="matched",
                instrument_id=INSTRUMENT_ID,
                selected_event_date=date(2025, 12, 10),
            ),
            termination_reason=SimpleNamespace(
                resolution_state="matched",
                instrument_id=INSTRUMENT_ID,
                item_3_01_text=item_3_01_text,
            ),
        ),
    )


def _report(*, next_present: bool = False, item_3_01_text: str = ITEM_3_01) -> object:
    return service._build_report(
        core=_core(item_3_01_text=item_3_01_text),
        eod_repository=_EodRepository(next_present=next_present),
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 10, tzinfo=UTC),
    )


def test_matches_realized_before_open_statement_to_stable_id_eod_presence() -> None:
    report = _report()

    assert report.decision.resolution_state == "matched"
    assert report.decision.source_stated_trading_stop_boundary_date == date(
        2025, 12, 10
    )
    assert report.decision.expected_last_eod_session == date(2025, 12, 9)
    assert report.decision.observed_last_eod_session == date(2025, 12, 9)
    assert report.decision.next_exchange_session == date(2025, 12, 10)
    assert report.matched_cessation_count == 1
    assert report.legal_delisting_effective_date_count == 0
    assert report.terminal_reference_value_count == 0
    assert report.terminal_outcome_count == 0


def test_preserves_next_session_presence_as_conflict() -> None:
    report = _report(next_present=True)

    assert report.decision.resolution_state == "conflicting"
    assert report.conflicting_cessation_count == 1


def test_missing_realized_timing_is_unsupported_without_eod_read() -> None:
    report = _report(item_3_01_text="Item 3.01. NYSE was asked to delist the stock.")

    assert report.decision.resolution_state == "unsupported"
    assert report.selected_eod_session_count == 0
    assert report.unsupported_cessation_count == 1


def test_report_is_owner_only_immutable_and_idempotent(tmp_path: Path) -> None:
    report = _report()
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
