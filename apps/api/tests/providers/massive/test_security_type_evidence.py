from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.security_classification.v1 import SecurityForm, UniverseDisposition
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.security_type_evidence import (
    ALL_TICKERS_PATH,
    TICKER_TYPES_PATH,
    IdentityIndexes,
    build_instrument_evidence,
    fetch_security_evidence,
    parse_args,
    parse_ticker_type_catalog,
)

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)
AS_OF = date(2026, 8, 14)
ID1 = UUID("00000000-0000-4000-8000-000000000001")
ID2 = UUID("00000000-0000-4000-8000-000000000002")


def catalog_response(*codes: tuple[str, str]):
    return {"results": [{"code": code, "description": description, "asset_class": "stocks", "locale": "us"} for code, description in codes]}


def payload(ticker="TEST", type="CS", share="SHARE1", composite="COMP1", **changes):
    value = {"ticker": ticker, "name": f"{ticker} Company", "type": type, "primary_exchange": "XNYS", "share_class_figi": share, "composite_figi": composite, "cik": "0001"}
    value.update(changes)
    return value


def indexes() -> IdentityIndexes:
    return IdentityIndexes(
        stable={("share_class_figi", "SHARE1"): frozenset({ID1}), ("share_class_figi", "SHARE2"): frozenset({ID2})},
        ticker={"TEST": ID1, "TEST2": ID2},
        known_stable=frozenset({("share_class_figi", "SHARE1"), ("share_class_figi", "SHARE2")}),
        known_tickers=frozenset({"TEST", "TEST2"}),
    )


def build(payloads, codes=(("CS", "Common Stock"),)):
    catalog = parse_ticker_type_catalog(catalog_response(*codes), observed_at=NOW)
    return build_instrument_evidence(catalog=catalog, payloads=tuple(payloads), indexes=indexes(), as_of_date=AS_OF, observed_at=NOW, request_count=2, all_tickers_request_count=1)


def test_catalog_parsing_and_duplicate_code_rejected() -> None:
    records = parse_ticker_type_catalog(catalog_response(("CS", "Common Stock"), ("ETF", "Exchange Traded Fund")), observed_at=NOW)
    assert [item.provider_type_code for item in records] == ["CS", "ETF"]
    with pytest.raises(RuntimeError, match="duplicate"):
        parse_ticker_type_catalog(catalog_response(("CS", "One"), ("CS", "Two")), observed_at=NOW)


def test_cs_proves_form_only_not_operating_company_or_domicile() -> None:
    result = build([payload()])
    item = result.evidence[0]
    assert item.security_form_evidence is SecurityForm.COMMON_SHARE
    assert item.universe_disposition is UniverseDisposition.QUARANTINE
    assert "issuer_structure_unresolved" in item.review_flags
    assert "issuer_domicile_unresolved" in item.review_flags


@pytest.mark.parametrize(
    ("code", "form"),
    [("ETF", SecurityForm.FUND_SHARE), ("ETN", SecurityForm.DEBT), ("PFD", SecurityForm.PREFERRED_SHARE),
     ("WARRANT", SecurityForm.WARRANT), ("UNIT", SecurityForm.UNIT), ("RIGHT", SecurityForm.RIGHT)],
)
def test_explicit_special_security_codes_are_excluded(code: str, form: SecurityForm) -> None:
    result = build([payload(type=code)], ((code, f"{code} description"),))
    assert result.evidence[0].security_form_evidence is form
    assert result.evidence[0].universe_disposition is UniverseDisposition.EXCLUDED


def test_adr_and_fund_are_conservative() -> None:
    adr = build([payload(type="ADRC")], (("ADRC", "American Depositary Receipt Common"),)).evidence[0]
    fund = build([payload(type="FUND")], (("FUND", "Fund"),)).evidence[0]
    assert adr.security_form_evidence is SecurityForm.ADR_ADS
    assert adr.universe_disposition is UniverseDisposition.QUARANTINE
    assert fund.security_form_evidence is SecurityForm.FUND_SHARE
    assert "fund_form_does_not_resolve_fund_subtype" in fund.review_flags


def test_unknown_code_and_name_heuristic_only_quarantine() -> None:
    item = build([payload(type="NEW", name="Fictional Acquisition Fund")]).evidence[0]
    assert item.provider_type_code == "NEW"
    assert item.security_form_evidence is SecurityForm.UNKNOWN
    assert item.universe_disposition is UniverseDisposition.QUARANTINE
    assert any(flag.startswith("name_review_flag") for flag in item.review_flags)


def test_stable_identifier_join_precedes_ticker_and_ticker_fallback_is_point_in_time() -> None:
    stable = build([payload(ticker="RENAMED")]).evidence[0]
    fallback = build([payload(share=None, composite=None)]).evidence[0]
    assert stable.instrument_id == ID1 and "stable_identifier_join" in stable.decision_flags
    assert fallback.instrument_id == ID1 and "point_in_time_ticker_resolver_join" in fallback.decision_flags


def test_conflicting_identity_is_ambiguous_and_reconciles() -> None:
    conflict_indexes = IdentityIndexes(stable={("share_class_figi", "SHARE1"): frozenset({ID1})}, ticker={"TEST": ID2})
    catalog = parse_ticker_type_catalog(catalog_response(("CS", "Common Stock")), observed_at=NOW)
    result = build_instrument_evidence(catalog=catalog, payloads=(payload(),), indexes=conflict_indexes, as_of_date=AS_OF, observed_at=NOW, request_count=2, all_tickers_request_count=1)
    assert result.ambiguous_count == 1
    assert sum(dict(result.category_counts).values()) == result.raw_record_count
    assert "ambiguous_mapping_nonzero" in result.quality_gate_failures


def test_exact_duplicate_malformed_and_unjoined_reconcile_without_silent_drop() -> None:
    values = [payload(), payload(), payload(ticker="BAD", share=None, composite=None), {"ticker": "MISSING"}]
    result = build(values)
    assert result.uniquely_mapped_count == 1
    assert result.exact_duplicate_count == 1
    assert result.unjoined_count == 1
    assert result.malformed_count == 1
    assert sum(dict(result.category_counts).values()) == 4


def test_identity_join_ratio_counts_known_excluded_identity_without_canonical_id() -> None:
    known = IdentityIndexes(stable={}, ticker={}, known_tickers=frozenset({"PREFERRED"}))
    catalog = parse_ticker_type_catalog(catalog_response(("PFD", "Preferred Stock")), observed_at=NOW)
    result = build_instrument_evidence(
        catalog=catalog, payloads=(payload(ticker="PREFERRED", type="PFD", share=None, composite=None),),
        indexes=known, as_of_date=AS_OF, observed_at=NOW, request_count=2, all_tickers_request_count=1,
    )
    assert result.identity_matched_count == 1
    assert result.join_ratio == 1.0
    assert result.unjoined_count == 1


def test_input_order_deterministic() -> None:
    first = build([payload(), payload("TEST2", share="SHARE2", composite="COMP2")])
    second = build([payload("TEST2", share="SHARE2", composite="COMP2"), payload()])
    assert first.evidence == second.evidence


class FakeTransport:
    def __init__(self, responses): self.responses=list(responses); self.calls=[]
    def get_json(self, path, *, params, api_key, timeout_seconds, base_url):
        self.calls.append((path, dict(params)))
        return self.responses.pop(0)


def test_fake_pagination_rate_limit_and_api_key_absent_from_params() -> None:
    responses = [catalog_response(("CS", "Common Stock")), {"results": [payload()], "next_url": "https://api.massive.com/v3/reference/tickers?cursor=x&apiKey=removed"}, {"results": []}]
    now=[0.0]; sleeps=[]
    def clock(): return now[0]
    def sleeper(delay): sleeps.append(delay); now[0]+=delay
    transport=FakeTransport(responses)
    result=fetch_security_evidence(config=MassiveProviderConfig(api_key="fake"), transport=transport, as_of_date=AS_OF, indexes=indexes(), rate_limiter=FixedIntervalRateLimiter(clock=clock,sleeper=sleeper), observed_at=NOW)
    assert result.request_count == 3
    assert sleeps == [15.0, 15.0]
    assert all("apiKey" not in params for _, params in transport.calls)


def test_pagination_foreign_host_rejected() -> None:
    transport=FakeTransport([catalog_response(("CS", "Common Stock")), {"results": [], "next_url": "https://evil.example/v3/reference/tickers?cursor=x"}])
    with pytest.raises(RuntimeError, match="host"):
        fetch_security_evidence(config=MassiveProviderConfig(api_key="fake"), transport=transport, as_of_date=AS_OF, indexes=indexes(), rate_limiter=FixedIntervalRateLimiter(sleeper=lambda _:None), observed_at=NOW)


def test_cli_scope_is_fixed() -> None:
    assert parse_args(["--as-of-date", "2026-08-14", "--data-root", "/data/trading-intelligence-platform"])[0] == AS_OF
    with pytest.raises(ValueError): parse_args(["--as-of-date", "2026-08-13", "--data-root", "/data/trading-intelligence-platform"])
    with pytest.raises(ValueError): parse_args(["--as-of-date", "2026-08-14", "--data-root", "/tmp/data"])
