from __future__ import annotations

from decimal import Decimal

import pytest

from tip_api.services import strong_leader_pullback_terminal_reference_final_review as service


def test_registered_population_matches_frozen_residual_scope() -> None:
    assert len(service._CASES) == 18
    assert sum(item.crossing_path_count for item in service._CASES) == 88
    assert tuple(item.ticker for item in service._CASES) == tuple(
        sorted(item.ticker for item in service._CASES)
    )
    assert len({item.instrument_id for item in service._CASES}) == 18


@pytest.mark.parametrize(
    ("calculation", "terms", "fields", "close_key", "legacy_text", "expected"),
    (
        (
            "fixed_cash",
            {"guaranteed_cash": Decimal("101")},
            {},
            None,
            "",
            "101.0000000000",
        ),
        (
            "cash_plus_cvr",
            {
                "guaranteed_cash": Decimal("54"),
                "cvr_max_cash": Decimal("6"),
            },
            {},
            None,
            "",
            "60.0000000000",
        ),
        (
            "aclx_source",
            {},
            {},
            None,
            "price per Share of (x) $115.00 and a payment of $5.00 per CVR",
            "120.0000000000",
        ),
        (
            "holx_source",
            {},
            {},
            None,
            "$76.00 per Share with CVR payment (up to $3.00)",
            "79.0000000000",
        ),
        (
            "bld_election",
            {
                "cash_election_cash": Decimal("505"),
                "stock_election_ratio": Decimal("20.2"),
            },
            {},
            "QXO",
            "",
            "505.0000000000",
        ),
        (
            "snv_stock",
            {"listed_equity_ratio": Decimal("0.5237")},
            {},
            "PNFP",
            "",
            "49.8038700000",
        ),
        (
            "thr_election",
            {
                "cash_election_cash": Decimal("63.89"),
                "mixed_election_cash": Decimal("10"),
                "mixed_election_ratio": Decimal("0.684"),
                "stock_election_ratio": Decimal("0.811"),
            },
            {},
            "CECO",
            "",
            "64.0933300000",
        ),
        (
            "lnw_exact",
            {},
            {
                "foreign_sole_listing_date": Decimal("20251114"),
                "last_us_trading_date": Decimal("20251112"),
            },
            "LNW",
            "",
            "86.2200000000",
        ),
        (
            "mtsr_source",
            {},
            {"cash_usd": Decimal("65.60"), "cvr_cap_usd": Decimal("20.65")},
            None,
            "",
            "86.2500000000",
        ),
        (
            "revg_source",
            {},
            {
                "cash_usd": Decimal("8.71"),
                "listed_equity_ratio": Decimal("0.9809"),
            },
            "TEX",
            "",
            "66.5732910000",
        ),
        (
            "sand_source",
            {},
            {"listed_equity_ratio": Decimal("0.0625")},
            "RGLD",
            "",
            "12.1325000000",
        ),
        (
            "skx_source",
            {},
            {
                "cash_election_usd": Decimal("63"),
                "mixed_cash_usd": Decimal("57"),
                "unlisted_unit_count": Decimal("1"),
                "unlisted_unit_value_usd": Decimal("29"),
            },
            None,
            "",
            "86.0000000000",
        ),
    ),
)
def test_frozen_calculations_are_exact_and_outcome_independent(
    calculation: str,
    terms: dict[str, Decimal],
    fields: dict[str, Decimal],
    close_key: str | None,
    legacy_text: str,
    expected: str,
) -> None:
    value = service._calculate_upper(
        calculation=calculation,
        terms=terms,
        fields=fields,
        close=service._CLOSES.get(close_key or ""),
        legacy_text=legacy_text,
    )
    assert service._money(value) == expected


def test_missing_registered_term_fails_closed() -> None:
    with pytest.raises(
        service.StrongLeaderPullbackTerminalReferenceFinalReviewError,
        match="required terminal-reference term is absent",
    ):
        service._calculate_upper(
            calculation="cash_plus_cvr",
            terms={"guaranteed_cash": Decimal("10")},
            fields={},
            close=None,
            legacy_text="",
        )
