from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import (
    EodPriceBarV1,
    EodSessionIntegrityV1,
    QualityStatus,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.services import (
    strong_leader_pullback_listed_consideration_terminal_evidence as service,
)


VALUATION_SESSION = date(2026, 1, 6)
OBSERVED_LAST_SESSION = date(2026, 1, 5)


class _Repository:
    def __init__(self, _: Path, *, missing_sequence: int | None = None) -> None:
        self.missing_sequence = missing_sequence

    def read_history_sessions(
        self, sessions: tuple[date, ...]
    ) -> tuple[EodHistorySessionRead, ...]:
        assert sessions == (VALUATION_SESSION,)
        return (
            EodHistorySessionRead(
                _integrity(),
                (),
                datetime(2026, 1, 6, 22, tzinfo=UTC),
            ),
        )

    def read_canonical_records(
        self, session: date
    ) -> tuple[EodPriceBarV1, ...]:
        assert session == VALUATION_SESSION
        return tuple(
            _bar(sequence)
            for sequence in range(1, 10)
            if sequence != self.missing_sequence
        )


def _integrity(*, record_count: int = 9) -> EodSessionIntegrityV1:
    return EodSessionIntegrityV1(
        session_date=VALUATION_SESSION,
        record_count=record_count,
        content_fingerprint="1" * 64,
        parquet_sha256="2" * 64,
        identity_snapshot_date=VALUATION_SESSION,
        identity_snapshot_fingerprint="3" * 64,
        duplicate_instrument_session_count=0,
        multiple_latest_revision_count=0,
        future_identity_reference_count=0,
    )


def _bar(sequence: int) -> EodPriceBarV1:
    close = Decimal(f"{20 + sequence}.0000000000")
    volume = Decimal("100000")
    return EodPriceBarV1(
        instrument_id=UUID(int=100 + sequence),
        session_date=VALUATION_SESSION,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=volume,
        vwap=close,
        trade_count=1000,
        notional=close * volume,
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=close,
        source="fixture",
        source_record_id=f"fixture-{sequence}",
        ingested_at=datetime(2026, 1, 6, 21, tzinfo=UTC),
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.VALID,
        quality_flags=("adjustment_factors_unverified",),
    )


def _inputs() -> tuple[object, object, object, object]:
    identity_decisions = []
    consideration_decisions = []
    cessation_decisions = []
    payoff_decisions = []
    for sequence in range(1, 13):
        target_id = UUID(int=sequence)
        consideration_id = UUID(int=100 + sequence)
        matched = sequence <= 9
        consideration_fingerprint = f"{sequence + 1000:064x}"
        cessation_fingerprint = f"{sequence + 2000:064x}"
        identity_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                target_instrument_id=target_id,
                resolution_state=(
                    "matched"
                    if matched
                    else "final_exchange_ratio_absent_from_registration_source"
                ),
                assigned_consideration_instrument_id=(
                    consideration_id if matched else None
                ),
                logical_fingerprint=f"{sequence + 3000:064x}",
            )
        )
        consideration_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                logical_fingerprint=consideration_fingerprint,
                acceptance_datetime=datetime(2026, 1, 5, 12, tzinfo=UTC),
                transaction_completion_date=VALUATION_SESSION,
            )
        )
        cessation_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                logical_fingerprint=cessation_fingerprint,
                transaction_completion_date=VALUATION_SESSION,
                resolution_state="matched" if matched else "unsupported",
                timing_profile="before_open" if matched else "unresolved",
                sec_stated_trading_stop_boundary_date=(
                    VALUATION_SESSION if matched else None
                ),
                expected_last_eod_session=(
                    OBSERVED_LAST_SESSION if matched else None
                ),
                observed_last_eod_session=(
                    OBSERVED_LAST_SESSION if matched else None
                ),
                next_exchange_session=VALUATION_SESSION if matched else None,
            )
        )
        term = SimpleNamespace(
            term_kind="listed_equity_shares_per_target_share",
            normalized_value="1.500000",
            logical_fingerprint=f"{sequence + 4000:064x}",
        )
        payoff_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                consideration_fingerprint=consideration_fingerprint,
                cessation_fingerprint=cessation_fingerprint,
                logical_fingerprint=f"{sequence + 5000:064x}",
                consideration_structure="stock_only",
                terms=(term,),
                alternatives=(),
            )
        )
    consideration = SimpleNamespace(
        report_sha256="4" * 64,
        report=SimpleNamespace(
            logical_fingerprint="5" * 64,
            decisions=tuple(consideration_decisions),
        ),
    )
    cessation = SimpleNamespace(
        report_sha256="6" * 64,
        report=SimpleNamespace(
            logical_fingerprint="7" * 64,
            decisions=tuple(cessation_decisions),
        ),
    )
    payoff = SimpleNamespace(
        report_sha256="8" * 64,
        report=SimpleNamespace(
            consideration_report_sha256=consideration.report_sha256,
            consideration_logical_fingerprint=(
                consideration.report.logical_fingerprint
            ),
            cessation_report_sha256=cessation.report_sha256,
            cessation_logical_fingerprint=cessation.report.logical_fingerprint,
            logical_fingerprint="9" * 64,
            decisions=tuple(payoff_decisions),
        ),
    )
    identities = SimpleNamespace(
        report_sha256="a" * 64,
        report=SimpleNamespace(
            payoff_terms_report_sha256=payoff.report_sha256,
            payoff_terms_logical_fingerprint=payoff.report.logical_fingerprint,
            matched_identity_count=9,
            logical_fingerprint="b" * 64,
            decisions=tuple(identity_decisions),
        ),
    )
    return identities, consideration, cessation, payoff


def test_documents_nine_reference_values_without_outcome_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "CanonicalEodReadRepository", _Repository)
    identities, consideration, cessation, payoff = _inputs()

    report = service._build_report(
        identities=identities,
        consideration=consideration,
        cessation=cessation,
        payoff=payoff,
        canonical_eod_root=Path("/fixture"),
        implementation_revision="c" * 40,
        evaluated_at=datetime(2026, 9, 14, 4, tzinfo=UTC),
    )

    assert report.terminal_reference_value_count == 9
    assert report.excluded_case_count == 3
    assert report.valuation_session_count == 1
    assert report.canonical_terminal_outcome_count == 0
    assert report.strategy_outcome_label_count == 0
    assert report.decisions[0].listed_equity_component_value_usd == (
        "31.5000000000000000"
    )
    assert report.decisions[0].gross_reference_terminal_value_usd == (
        "31.5000000000000000"
    )
    assert report.decisions[-1].gross_reference_terminal_value_usd is None


def test_missing_consideration_bar_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingRepository(_Repository):
        def __init__(self, root: Path) -> None:
            super().__init__(root, missing_sequence=1)

        def read_history_sessions(
            self, sessions: tuple[date, ...]
        ) -> tuple[EodHistorySessionRead, ...]:
            return (
                EodHistorySessionRead(
                    _integrity(record_count=8),
                    (),
                    datetime(2026, 1, 6, 22, tzinfo=UTC),
                ),
            )

    monkeypatch.setattr(service, "CanonicalEodReadRepository", MissingRepository)
    identities, consideration, cessation, payoff = _inputs()

    with pytest.raises(
        service.StrongLeaderPullbackListedConsiderationTerminalEvidenceError,
        match="consideration bar differs",
    ):
        service._build_report(
            identities=identities,
            consideration=consideration,
            cessation=cessation,
            payoff=payoff,
            canonical_eod_root=Path("/fixture"),
            implementation_revision="c" * 40,
            evaluated_at=datetime(2026, 9, 14, 4, tzinfo=UTC),
        )


def test_report_is_owner_only_immutable_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(service, "CanonicalEodReadRepository", _Repository)
    identities, consideration, cessation, payoff = _inputs()
    report = service._build_report(
        identities=identities,
        consideration=consideration,
        cessation=cessation,
        payoff=payoff,
        canonical_eod_root=Path("/fixture"),
        implementation_revision="c" * 40,
        evaluated_at=datetime(2026, 9, 14, 4, tzinfo=UTC),
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


def test_network_and_name_resolution_are_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackListedConsiderationTerminalEvidenceError,
        match="network access is prohibited",
    ):
        socket.getaddrinfo("example.com", 443)
