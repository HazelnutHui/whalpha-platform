from datetime import UTC, date, datetime
import hashlib
import json
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.contracts.security_classification.v1 import (
    ProviderObservationStatus,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.security_type_evidence import (
    IdentityIndexes,
    IdentityReference,
    build_failed_diagnostic,
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


def payload(ticker="TEST", type="CS", share="SHARE1", composite="COMP1", id=None, **changes):
    value = {"ticker": ticker, "name": f"{ticker} Company", "type": type, "primary_exchange": "XNYS", "share_class_figi": share, "composite_figi": composite, "id": id, "cik": "0001"}
    value.update(changes)
    return value


def reference(ticker="TEST", instrument_id=ID1, status=ResolutionStatus.RESOLVED, share="SHARE1", composite="COMP1", provider_id=None):
    return IdentityReference(ticker, instrument_id, status, share, composite, provider_id)


def make_indexes(*references: IdentityReference, resolver=None) -> IdentityIndexes:
    share, composite, provider, tickers = {}, {}, {}, {}
    for item in references:
        tickers.setdefault(item.provider_ticker, []).append(item)
        for value, target in ((item.share_class_figi, share), (item.composite_figi, composite), (item.provider_instrument_id, provider)):
            if value:
                target.setdefault(value, []).append(item)
    return IdentityIndexes(
        {key: tuple(value) for key, value in share.items()},
        {key: tuple(value) for key, value in composite.items()},
        {key: tuple(value) for key, value in provider.items()},
        {key: tuple(value) for key, value in tickers.items()},
        resolver if resolver is not None else {item.provider_ticker: item.canonical_instrument_id for item in references if item.resolution_status is ResolutionStatus.RESOLVED and item.canonical_instrument_id is not None},
    )


def indexes() -> IdentityIndexes:
    return make_indexes(reference(), reference("TEST2", ID2, share="SHARE2", composite="COMP2"))


def build(values, *, identity_indexes=None, codes=(("CS", "Common Stock"),)):
    catalog = parse_ticker_type_catalog(catalog_response(*codes), observed_at=NOW)
    return build_instrument_evidence(catalog=catalog, payloads=tuple(values), indexes=identity_indexes or indexes(), as_of_date=AS_OF, observed_at=NOW, request_count=2, all_tickers_request_count=1)


def test_catalog_parsing_and_duplicate_code_rejected() -> None:
    records = parse_ticker_type_catalog(catalog_response(("CS", "Common Stock"), ("ETF", "Exchange Traded Fund")), observed_at=NOW)
    assert [item.provider_type_code for item in records] == ["CS", "ETF"]
    with pytest.raises(RuntimeError, match="duplicate"):
        parse_ticker_type_catalog(catalog_response(("CS", "One"), ("CS", "Two")), observed_at=NOW)


def test_resolved_and_excluded_shared_ticker_reconcile_without_ambiguity() -> None:
    resolved = reference("DUP", ID1, share="DUPSHARE", composite="DUPCOMP")
    excluded = reference("DUP", None, ResolutionStatus.EXCLUDED, share=None, composite=None)
    result = build(
        [payload("DUP", share="DUPSHARE", composite="DUPCOMP"), payload("DUP", type="PFD", share=None, composite=None)],
        identity_indexes=make_indexes(resolved, excluded, resolver={"DUP": ID1}),
        codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")),
    )
    assert result.canonical_mapped_count == 1
    assert result.expected_unjoined_count == 1
    assert result.ambiguous_count == 0
    assert result.business_key_conflict_count == 0
    assert result.linkage_numerator == result.linkage_denominator == 1


def test_ticker_only_two_resolved_canonical_ids_is_ambiguous() -> None:
    values = (reference("DUP", ID1, share="S1", composite="C1"), reference("DUP", ID2, share="S2", composite="C2"))
    result = build([payload("DUP", share=None, composite=None)], identity_indexes=make_indexes(*values, resolver={}))
    assert result.ambiguous_count == 1
    assert "ambiguous_mapping_nonzero" in result.quality_gate_failures


def test_share_class_figi_precedes_conflicting_ticker() -> None:
    result = build([payload("OTHER", share="SHARE1", composite=None)], identity_indexes=make_indexes(reference(), reference("OTHER", ID2, share="SHARE2", composite="COMP2")))
    assert result.evidence[0].instrument_id == ID1
    assert "share_class_figi_join" in result.evidence[0].decision_flags


def test_composite_figi_requires_unique_match() -> None:
    unique = build([payload(share=None)], identity_indexes=indexes())
    assert unique.evidence[0].instrument_id == ID1
    duplicate = make_indexes(reference(share=None), reference("OTHER", ID2, share=None, composite="COMP1"), resolver={})
    collision = build([payload(share=None)], identity_indexes=duplicate)
    assert collision.collision_count == 1


def test_provider_stable_id_join() -> None:
    idx = make_indexes(reference(share=None, composite=None, provider_id="PID1"))
    result = build([payload(share=None, composite=None, id="PID1")], identity_indexes=idx)
    assert result.evidence[0].instrument_id == ID1
    assert "provider_stable_id_join" in result.evidence[0].decision_flags


def test_ticker_fallback_requires_unique_point_in_time_identity() -> None:
    idx = make_indexes(reference(share=None, composite=None), resolver={"TEST": ID1})
    result = build([payload(share=None, composite=None)], identity_indexes=idx)
    assert result.evidence[0].instrument_id == ID1
    assert result.observations[0].resolution_method == "point_in_time_ticker_resolver"


def test_observation_absent_from_identity_snapshot_is_not_silently_expected() -> None:
    result = build([payload("UNKNOWN", share=None, composite=None)], identity_indexes=make_indexes(resolver={}))
    assert result.ambiguous_count == 1
    assert result.expected_unjoined_count == 0
    assert "identity_snapshot_no_match" in result.observations[0].reason_codes


def test_unresolved_and_excluded_are_expected_unjoined_and_not_denominator() -> None:
    values = (
        reference("UNRES", None, ResolutionStatus.UNRESOLVED, share=None, composite=None),
        reference("EXCL", None, ResolutionStatus.EXCLUDED, share=None, composite=None),
    )
    result = build([payload("UNRES", share=None, composite=None), payload("EXCL", type="PFD", share=None, composite=None)], identity_indexes=make_indexes(*values, resolver={}), codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")))
    assert result.expected_unjoined_count == 2
    assert result.linkage_denominator == 0
    assert not result.evidence


def test_linkage_ratio_uses_only_canonical_eligible_observations() -> None:
    values = (reference(), reference("EXCL", None, ResolutionStatus.EXCLUDED, share=None, composite=None))
    result = build([payload(), payload("EXCL", type="PFD", share=None, composite=None)], identity_indexes=make_indexes(*values), codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")))
    assert (result.linkage_numerator, result.linkage_denominator, result.linkage_ratio) == (1, 1, 1.0)
    assert sum(dict(result.category_counts).values()) == result.raw_record_count


def test_same_ticker_distinct_observations_coexist_and_ids_are_deterministic() -> None:
    values = [payload("DUP", share="S1", composite="C1"), payload("DUP", type="PFD", share=None, composite=None)]
    idx = make_indexes(reference("DUP", ID1, share="S1", composite="C1"), reference("DUP", None, ResolutionStatus.EXCLUDED, share=None, composite=None))
    first = build(values, identity_indexes=idx, codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")))
    second = build(list(reversed(values)), identity_indexes=idx, codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")))
    assert len({item.provider_observation_id for item in first.observations}) == 2
    assert first.observations == second.observations
    first_fingerprint = hashlib.sha256(json.dumps([item.model_dump(mode="json") for item in first.observations], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    second_fingerprint = hashlib.sha256(json.dumps([item.model_dump(mode="json") for item in second.observations], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert first_fingerprint == second_fingerprint


def test_observation_business_key_distinguishes_stable_identifiers_and_type() -> None:
    values = [
        payload("DUP", share="S1", composite="C1", id="P1"),
        payload("DUP", share="S2", composite="C1", id="P1"),
        payload("DUP", share="S1", composite="C2", id="P1"),
        payload("DUP", share="S1", composite="C1", id="P2"),
        payload("DUP", type="PFD", share="S1", composite="C1", id="P1"),
    ]
    result = build(values, identity_indexes=make_indexes(resolver={}), codes=(("CS", "Common Stock"), ("PFD", "Preferred Stock")))
    assert len(result.observations) == 5
    assert len({item.provider_observation_id for item in result.observations}) == 5


def test_identical_canonical_evidence_dedupes_and_conflicting_evidence_fails() -> None:
    same = build([payload(), payload(name="Renamed Display")])
    assert len(same.observations) == 2 and len(same.evidence) == 1
    assert len(same.evidence[0].provider_observation_ids) == 2
    conflict = build([payload(), payload(type="ADRC", name="Different")], codes=(("CS", "Common Stock"), ("ADRC", "Depositary Receipt")))
    assert conflict.business_key_conflict_count == 2
    assert conflict.ambiguous_count == 2
    assert "canonical_business_key_conflict_nonzero" in conflict.quality_gate_failures


def test_exact_duplicate_and_malformed_reconcile_without_silent_drop() -> None:
    result = build([payload(), payload(), {"ticker": "MISSING"}])
    assert result.canonical_mapped_count == 1
    assert result.exact_duplicate_count == 1
    assert result.malformed_count == 1
    assert sum(dict(result.category_counts).values()) == 3


def test_cs_form_only_unknown_code_and_name_heuristic_remain_quarantine() -> None:
    cs = build([payload()]).evidence[0]
    unknown = build([payload(type="NEW", name="Fictional Acquisition Fund")]).evidence[0]
    assert cs.security_form_evidence is SecurityForm.COMMON_SHARE
    assert cs.universe_disposition is UniverseDisposition.QUARANTINE
    assert unknown.security_form_evidence is SecurityForm.UNKNOWN
    assert any(flag.startswith("name_review_flag") for flag in unknown.review_flags)


@pytest.mark.parametrize(
    ("code", "form"),
    (("ETF", SecurityForm.FUND_SHARE), ("ETN", SecurityForm.DEBT), ("PFD", SecurityForm.PREFERRED_SHARE),
     ("WARRANT", SecurityForm.WARRANT), ("UNIT", SecurityForm.UNIT), ("RIGHT", SecurityForm.RIGHT)),
)
def test_explicit_special_security_codes_are_excluded(code: str, form: SecurityForm) -> None:
    item = build([payload(type=code)], codes=((code, f"{code} description"),)).evidence[0]
    assert item.security_form_evidence is form
    assert item.universe_disposition is UniverseDisposition.EXCLUDED


def test_adr_and_generic_fund_remain_conservative() -> None:
    adr = build([payload(type="ADRC")], codes=(("ADRC", "Depositary Receipt"),)).evidence[0]
    fund = build([payload(type="FUND")], codes=(("FUND", "Fund"),)).evidence[0]
    assert adr.universe_disposition is UniverseDisposition.QUARANTINE
    assert fund.security_form_evidence is SecurityForm.FUND_SHARE
    assert "fund_form_does_not_resolve_fund_subtype" in fund.review_flags


def test_failed_diagnostic_is_sanitized() -> None:
    idx = make_indexes(reference(), reference("TEST", ID2, share="SHARE2", composite="COMP2"), resolver={})
    result = build([payload(share=None, composite=None)], identity_indexes=idx)
    diagnostic = build_failed_diagnostic(result, run_id="phase-b1-test", created_at=NOW)
    rendered = json.dumps(diagnostic.model_dump(mode="json"), sort_keys=True)
    assert diagnostic.diagnostic_status == "failed"
    assert "api_key" not in rendered.lower()
    assert "authorization" not in rendered.lower()
    assert "raw_payload" not in rendered.lower()
    assert "http_headers" not in rendered.lower()


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
