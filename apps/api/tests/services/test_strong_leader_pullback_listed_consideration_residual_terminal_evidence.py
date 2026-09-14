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
    strong_leader_pullback_listed_consideration_residual_terminal_evidence as service,
)


VALUATION_SESSION = date(2026, 2, 3)
OBSERVED_LAST_SESSION = date(2026, 2, 2)
SEQUENCES = (158, 174, 184)


class _Repository:
    missing_sequence: int | None = None

    def __init__(self, _: Path) -> None:
        pass

    def read_history_sessions(
        self, sessions: tuple[date, ...]
    ) -> tuple[EodHistorySessionRead, ...]:
        assert sessions == (VALUATION_SESSION,)
        count = len(SEQUENCES) - int(self.missing_sequence is not None)
        return (
            EodHistorySessionRead(
                _integrity(count),
                (),
                datetime(2026, 2, 3, 22, tzinfo=UTC),
            ),
        )

    def read_canonical_records(self, session: date) -> tuple[EodPriceBarV1, ...]:
        assert session == VALUATION_SESSION
        return tuple(
            _bar(index, sequence)
            for index, sequence in enumerate(SEQUENCES, start=1)
            if sequence != self.missing_sequence
        )


def _integrity(count: int) -> EodSessionIntegrityV1:
    return EodSessionIntegrityV1(
        session_date=VALUATION_SESSION,
        record_count=count,
        content_fingerprint="1" * 64,
        parquet_sha256="2" * 64,
        identity_snapshot_date=VALUATION_SESSION,
        identity_snapshot_fingerprint="3" * 64,
        duplicate_instrument_session_count=0,
        multiple_latest_revision_count=0,
        future_identity_reference_count=0,
    )


def _bar(index: int, sequence: int) -> EodPriceBarV1:
    close = Decimal(f"{20 + index}.0000000000")
    volume = Decimal("100000")
    return EodPriceBarV1(
        instrument_id=UUID(int=1000 + sequence),
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
        ingested_at=datetime(2026, 2, 3, 21, tzinfo=UTC),
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.VALID,
        quality_flags=("adjustment_factors_unverified",),
    )


def _inputs():
    identity_decisions = []
    consideration_decisions = []
    cessation_decisions = []
    payoff_decisions = []
    ratios = {158: "0.488300", 174: "1.866300", 184: "0.195500"}
    for sequence in SEQUENCES:
        target = UUID(int=sequence)
        assigned = UUID(int=1000 + sequence)
        consideration_fingerprint = f"{sequence + 1000:064x}"
        cessation_fingerprint = f"{sequence + 2000:064x}"
        identity_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                target_instrument_id=target,
                assigned_consideration_instrument_id=assigned,
                composite_evidence_match=True,
                logical_fingerprint=f"{sequence + 3000:064x}",
            )
        )
        consideration_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target,
                logical_fingerprint=consideration_fingerprint,
                acceptance_datetime=datetime(2026, 2, 2, 12, tzinfo=UTC),
                transaction_completion_date=VALUATION_SESSION,
            )
        )
        cessation_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target,
                logical_fingerprint=cessation_fingerprint,
                transaction_completion_date=VALUATION_SESSION,
                resolution_state="matched",
                timing_profile="before_open",
                sec_stated_trading_stop_boundary_date=VALUATION_SESSION,
                expected_last_eod_session=OBSERVED_LAST_SESSION,
                observed_last_eod_session=OBSERVED_LAST_SESSION,
                next_exchange_session=VALUATION_SESSION,
            )
        )
        terms = [
            SimpleNamespace(
                term_kind="listed_equity_shares_per_target_share",
                normalized_value=ratios[sequence],
                logical_fingerprint=f"{sequence + 4000:064x}",
            )
        ]
        if sequence == 158:
            terms.append(
                SimpleNamespace(
                    term_kind="cash_usd_per_target_share",
                    normalized_value="15.00",
                    logical_fingerprint=f"{sequence + 5000:064x}",
                )
            )
        payoff_decisions.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target,
                consideration_fingerprint=consideration_fingerprint,
                cessation_fingerprint=cessation_fingerprint,
                logical_fingerprint=f"{sequence + 6000:064x}",
                consideration_structure=(
                    "fixed_cash_and_stock" if sequence == 158 else "stock_only"
                ),
                terms=tuple(terms),
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
    prior_values = SimpleNamespace(
        report_sha256="a" * 64,
        report=SimpleNamespace(
            terminal_reference_value_count=9,
            identity_adjudication_report_sha256="b" * 64,
            consideration_report_sha256=consideration.report_sha256,
            cessation_report_sha256=cessation.report_sha256,
            payoff_terms_report_sha256=payoff.report_sha256,
            logical_fingerprint="c" * 64,
        ),
    )
    identities = SimpleNamespace(
        report_sha256="d" * 64,
        report=SimpleNamespace(
            prior_identity_report_sha256=(
                prior_values.report.identity_adjudication_report_sha256
            ),
            consideration_report_sha256=consideration.report_sha256,
            consideration_logical_fingerprint=(
                consideration.report.logical_fingerprint
            ),
            residual_matched_identity_count=3,
            cumulative_matched_identity_count=12,
            logical_fingerprint="e" * 64,
            decisions=tuple(identity_decisions),
        ),
    )
    return prior_values, identities, consideration, cessation, payoff


def test_documents_three_residual_reference_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.base, "CanonicalEodReadRepository", _Repository)
    inputs = _inputs()

    report = service._build_report(
        prior_values=inputs[0],
        identities=inputs[1],
        consideration=inputs[2],
        cessation=inputs[3],
        payoff=inputs[4],
        canonical_eod_root=Path("/fixture"),
        implementation_revision="f" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
    )

    assert report.residual_terminal_reference_value_count == 3
    assert report.cumulative_terminal_reference_value_count == 12
    assert report.canonical_terminal_outcome_count == 0
    assert report.strategy_outcome_label_count == 0
    first = report.decisions[0]
    assert first.gross_reference_terminal_value_usd == "25.2543000000000000"
    assert "consideration_security_identity_passed_residual_composite_gate" in (
        first.decision_reasons
    )


def test_missing_consideration_bar_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingRepository(_Repository):
        missing_sequence = 158

    monkeypatch.setattr(
        service.base, "CanonicalEodReadRepository", MissingRepository
    )
    inputs = _inputs()

    with pytest.raises(
        service.StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError,
        match="residual terminal decision differs",
    ):
        service._build_report(
            prior_values=inputs[0],
            identities=inputs[1],
            consideration=inputs[2],
            cessation=inputs[3],
            payoff=inputs[4],
            canonical_eod_root=Path("/fixture"),
            implementation_revision="f" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
        )


def test_changed_identity_binding_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.base, "CanonicalEodReadRepository", _Repository)
    inputs = _inputs()
    inputs[1].report.prior_identity_report_sha256 = "0" * 64

    with pytest.raises(
        service.StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError,
        match="input bindings differ",
    ):
        service._build_report(
            prior_values=inputs[0],
            identities=inputs[1],
            consideration=inputs[2],
            cessation=inputs[3],
            payoff=inputs[4],
            canonical_eod_root=Path("/fixture"),
            implementation_revision="f" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
        )


def test_report_is_owner_only_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(service.base, "CanonicalEodReadRepository", _Repository)
    inputs = _inputs()
    report = service._build_report(
        prior_values=inputs[0],
        identities=inputs[1],
        consideration=inputs[2],
        cessation=inputs[3],
        payoff=inputs[4],
        canonical_eod_root=Path("/fixture"),
        implementation_revision="f" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=UTC),
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    target = custody / "adjudication=fixture"

    first = service._write_report(
        output_root=target, output_custody_root=custody, report=report
    )
    second = service._write_report(
        output_root=target, output_custody_root=custody, report=report
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400
