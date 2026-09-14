from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import (
    strong_leader_pullback_terminal_population_listed_reference as service,
)


def _named(value: str) -> object:
    return SimpleNamespace(value=value)


def _submission() -> dict[str, object]:
    return {
        "cik": "0000048287",
        "entityType": "operating",
        "name": "HNI CORP",
        "tickers": ["HNI"],
        "exchanges": ["NYSE"],
        "filings": {
            "recent": {
                "form": ["8-K"],
                "filingDate": ["2025-12-10"],
                "acceptanceDateTime": ["2025-12-10T21:49:32.000Z"],
                "accessionNumber": ["0000950103-25-015967"],
                "primaryDocument": ["dp238589_8k.htm"],
            }
        },
    }


def _term(key: str, kind: str, value: str, fingerprint: str) -> object:
    return SimpleNamespace(
        term_key=key,
        term_kind=kind,
        normalized_value=value,
        logical_fingerprint=fingerprint,
    )


def _inputs(*, canonical_cik: str = "0000048287") -> dict[str, object]:
    terms = (
        _term("cash_election_cash", "cash_usd_per_target_share", "16.19", "1" * 64),
        _term(
            "cash_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.000900",
            "2" * 64,
        ),
        _term("mixed_election_cash", "cash_usd_per_target_share", "7.20", "3" * 64),
        _term(
            "mixed_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.219200",
            "4" * 64,
        ),
        _term(
            "stock_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.394000",
            "5" * 64,
        ),
    )
    alternatives = tuple(
        SimpleNamespace(
            alternative_code=code,
            term_keys=tuple(sorted(keys)),
            default_if_no_valid_election=code == "mixed_election",
        )
        for code, keys in service._ALTERNATIVE_TERMS.items()
    )
    policy = SimpleNamespace(
        report_sha256="a" * 64,
        report=SimpleNamespace(
            core_adjudication_report_sha256="b" * 64,
            core_adjudication_logical_fingerprint="c" * 64,
            cessation_report_sha256="d" * 64,
            cessation_logical_fingerprint="e" * 64,
            listed_equity_issuer_locator="HNI",
            party_relation=SimpleNamespace(
                instrument_id=service.TARGET_INSTRUMENT_ID,
                party_definition_text="HNI Corporation, an Iowa corporation (HNI)",
            ),
            normalized_terms=terms,
            alternatives=alternatives,
            logical_fingerprint="f" * 64,
        ),
    )
    core = SimpleNamespace(
        report_sha256="b" * 64,
        report=SimpleNamespace(
            logical_fingerprint="c" * 64,
            common_share_consideration=SimpleNamespace(
                evidence_text="0.2192 shares of common stock of HNI (HNI common stock)",
            ),
        ),
    )
    cessation = SimpleNamespace(
        report_sha256="d" * 64,
        report=SimpleNamespace(
            logical_fingerprint="e" * 64,
            decision=SimpleNamespace(
                resolution_state="matched",
                next_exchange_session=date(2025, 12, 10),
                observed_last_eod_session=date(2025, 12, 9),
            ),
        ),
    )
    submissions = SimpleNamespace(
        logical_fingerprint="6" * 64,
        archive_sha256="7" * 64,
        completed_at=datetime(2026, 9, 10, 15, tzinfo=UTC),
    )
    integrity = SimpleNamespace(
        session_date=date(2025, 12, 10),
        record_count=1,
        content_fingerprint="8" * 64,
        parquet_sha256="9" * 64,
        identity_snapshot_fingerprint="0" * 64,
        duplicate_instrument_session_count=0,
        multiple_latest_revision_count=0,
        future_identity_reference_count=0,
    )
    instrument = SimpleNamespace(
        instrument_id=service.HNI_INSTRUMENT_ID,
        instrument_type=_named("common_stock"),
        status=_named("active"),
        ticker="HNI",
        name="HNI Corporation",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        cik=canonical_cik,
        figi="BBG000C7QK61",
        source="massive_stocks_basic",
        source_instrument_id="share_class_figi:BBG001S6Q6F5",
        quality_status=_named("valid"),
    )
    bar = SimpleNamespace(
        instrument_id=service.HNI_INSTRUMENT_ID,
        session_date=date(2025, 12, 10),
        close=Decimal("42.5400000000"),
        currency="USD",
        source="massive_stocks_basic",
        revision=1,
        is_latest_revision=True,
        quality_status=_named("valid"),
        quality_flags=("adjustment_factors_unverified",),
    )
    return {
        "policy": policy,
        "core": core,
        "cessation": cessation,
        "submissions": submissions,
        "submissions_manifest_sha256": "1" * 64,
        "submissions_member_sha256": "2" * 64,
        "submission_payload": _submission(),
        "integrity": integrity,
        "available_at": datetime(2026, 9, 2, 11, 39, tzinfo=UTC),
        "instruments": (instrument,),
        "records": (bar,),
        "implementation_revision": "3" * 40,
        "evaluated_at": datetime(2026, 9, 14, 9, tzinfo=UTC),
    }


def test_strict_identity_and_three_reference_values() -> None:
    report = service._build_report(**_inputs())

    assert report.identity.resolution_state == "strict_stable_security_match"
    assert report.identity.assigned_consideration_instrument_id == service.HNI_INSTRUMENT_ID
    assert report.consideration_close_usd == "42.5400000000"
    assert tuple(item.gross_reference_value_usd for item in report.alternatives) == (
        "16.2282860000000000",
        "16.5247680000000000",
        "16.7607600000000000",
    )
    assert report.primary_gross_reference_value_usd == "16.5247680000000000"
    assert report.sensitivity_range_usd == "0.5324740000000000"
    assert report.canonical_terminal_outcome_count == 0
    assert report.research_admission_count == 0


def test_cik_disagreement_fails_closed() -> None:
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationListedReferenceError,
        match="canonical evidence differs",
    ):
        service._build_report(**_inputs(canonical_cik="0000000000"))


def test_owner_only_write_is_immutable_and_idempotent(tmp_path: Path) -> None:
    report = service._build_report(**_inputs())
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
    assert (target / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service.base._network_prohibited(), pytest.raises(
        RuntimeError, match="network access is prohibited"
    ):
        socket.socket()
