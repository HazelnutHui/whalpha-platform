from datetime import UTC, date, datetime
from uuid import UUID

from tip_api.contracts.security_classification.v1 import (
    IssuerStructure,
    ListingScope,
    SecEvidenceGrade,
    SecEvidenceResolutionStatus,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.providers.sec.issuer_evidence import (
    SecIdentityRecord,
    SecIdentityResolver,
    build_bdc_state_observation,
    decide_universe_disposition,
    interpret_sec_fixture,
    reconcile_sec_evidence,
)

AS_OF = date(2026, 8, 14)
NOW = datetime(2026, 8, 15, tzinfo=UTC)
ID_A = UUID("00000000-0000-4000-8000-000000000001")
ID_B = UUID("00000000-0000-4000-8000-000000000002")


def identity(
    instrument_id=ID_A, *, ticker="TEST", exchange="XNYS", cik="1",
    share="BBG000000001", composite="BBG000000002", provider_id="provider-1",
    effective_from=date(2020, 1, 1), effective_to=None,
):
    return SecIdentityRecord(
        instrument_id=instrument_id, effective_from=effective_from, effective_to=effective_to,
        cik=cik.zfill(10), ticker=ticker, exchange=exchange, share_class_figi=share,
        composite_figi=composite, provider_stable_identifier=provider_id,
    )


def fixture(dataset: str, **values):
    result = {
        "source_dataset": dataset,
        "source_document_type": dataset,
        "cik": "1",
        "filing_date": "2026-08-14",
        "share_class_figi": "BBG000000001",
        "ticker": "TEST",
        "exchange": "XNYS",
    }
    result.update(values)
    return result


def parse(raw, records=(identity(),)):
    return interpret_sec_fixture(raw, filing_cutoff=AS_OF, resolver=SecIdentityResolver(records), source_observed_at=NOW)


def test_identity_priority_and_ticker_only_prohibition() -> None:
    resolver = SecIdentityResolver((identity(),))
    assert resolver.resolve({"share_class_figi": "BBG000000001"}, as_of_date=AS_OF).method == "share_class_figi"
    assert resolver.resolve({"composite_figi": "BBG000000002"}, as_of_date=AS_OF).method == "composite_figi"
    assert resolver.resolve({"provider_stable_identifier": "provider-1"}, as_of_date=AS_OF).method == "provider_stable_identifier"
    unresolved = resolver.resolve({"ticker": "TEST"}, as_of_date=AS_OF)
    assert unresolved.status is SecEvidenceResolutionStatus.EXPECTED_UNJOINED
    assert unresolved.reasons == ("ticker_only_identity_forbidden",)
    cik_only = resolver.resolve({"cik": "1"}, as_of_date=AS_OF)
    assert cik_only.status is SecEvidenceResolutionStatus.EXPECTED_UNJOINED


def test_stable_instrument_id_precedes_other_identifiers_and_conflict_quarantines() -> None:
    records = (identity(), identity(ID_B, ticker="OTHER", share="BBG000000003", composite="BBG000000004", provider_id="provider-2"))
    resolved = SecIdentityResolver(records).resolve({"instrument_id": str(ID_A)}, as_of_date=AS_OF)
    assert resolved.instrument_id == ID_A and resolved.method == "stable_instrument_id"
    conflicted = SecIdentityResolver(records).resolve(
        {"instrument_id": str(ID_A), "share_class_figi": "BBG000000003"}, as_of_date=AS_OF
    )
    assert conflicted.status is SecEvidenceResolutionStatus.AMBIGUOUS


def test_composite_figi_must_be_unique() -> None:
    records = (identity(), identity(ID_B, ticker="OTHER", share="BBG000000003", composite="BBG000000002", provider_id="provider-2"))
    result = SecIdentityResolver(records).resolve({"composite_figi": "BBG000000002"}, as_of_date=AS_OF)
    assert result.status is SecEvidenceResolutionStatus.COLLISION


def test_cik_cover_page_join_handles_multiple_securities_without_merging() -> None:
    records = (
        identity(ticker="AAA", cik="9", share=None, composite=None, provider_id=None),
        identity(ID_B, ticker="AAB", cik="9", share=None, composite=None, provider_id=None),
    )
    raw = fixture(
        "inline_xbrl_cover", cik="9", share_class_figi=None, ticker=None,
        TradingSymbol="AAB", SecurityExchangeName="XNYS", Security12bTitle="Common Stock",
    )
    value = parse(raw, records)
    assert value is not None and value.instrument_id == ID_B


def test_approved_cik_ticker_exchange_seed_resolves_without_ticker_only_join() -> None:
    raw = fixture(
        "company_tickers_exchange", share_class_figi=None,
        allow_cik_ticker_exchange=True,
    )
    value = parse(raw, (identity(share=None, composite=None, provider_id=None),))
    assert value is not None and value.instrument_id == ID_A
    assert "cik_cover_ticker_exchange_join" in value.decision_reasons


def test_current_reference_without_historical_date_never_backfills_classification() -> None:
    value = parse(fixture("company_tickers_mf", historical_cutoff_supported=False))
    assert value is not None and value.asserted_security_form is None
    assert value.evidence_grade is SecEvidenceGrade.INSUFFICIENT
    assert "historical_effective_date_unavailable" in value.quality_flags


def test_ticker_reuse_is_point_in_time() -> None:
    records = (
        identity(effective_to=date(2025, 1, 1), share=None, composite=None, provider_id=None),
        identity(ID_B, effective_from=date(2025, 1, 1), share=None, composite=None, provider_id=None),
    )
    raw = fixture(
        "inline_xbrl_cover", share_class_figi=None, ticker=None,
        TradingSymbol="TEST", SecurityExchangeName="XNYS", Security12bTitle="Common Stock",
    )
    value = parse(raw, records)
    assert value is not None and value.instrument_id == ID_B


def test_company_tickers_exchange_is_join_seed_and_sic_only_review_signal() -> None:
    value = parse(fixture("company_tickers_exchange", sic="9999"))
    assert value is not None
    assert value.asserted_security_form is None and value.asserted_issuer_structure is None
    assert value.evidence_grade is SecEvidenceGrade.CORROBORATING_REFERENCE
    assert value.quality_flags == ("sic_review_signal",)


def test_mutual_fund_presence_excludes_but_absence_is_not_proof() -> None:
    present = parse(fixture("company_tickers_mf"))
    absent = parse(fixture("company_tickers_exchange"))
    assert present is not None and present.asserted_security_form is SecurityForm.FUND_SHARE
    assert absent is not None and absent.asserted_security_form is None
    evidence = reconcile_sec_evidence((present,), as_of_date=AS_OF)
    assert evidence[0].universe_disposition is UniverseDisposition.EXCLUDED


def test_n_cen_is_fund_exclusion_evidence_without_overstating_fund_subtype() -> None:
    value = parse(fixture("n_cen"))
    assert value is not None and value.asserted_security_form is SecurityForm.FUND_SHARE
    assert value.asserted_issuer_structure is None


def test_fund_cef_and_bdc_official_datasets_create_exclusion_evidence() -> None:
    etf = parse(fixture("investment_company_series_class", fund_kind="etf"))
    cef = parse(fixture("closed_end_fund"))
    bdc = parse(fixture("business_development_company"))
    assert etf and etf.asserted_issuer_structure is IssuerStructure.ETF
    assert cef and cef.asserted_issuer_structure is IssuerStructure.CLOSED_END_FUND
    assert bdc and bdc.asserted_issuer_structure is IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY


def test_bdc_n54_state_machine_uses_latest_filing_before_cutoff() -> None:
    filings = (
        fixture("filing", form="N-54A", filing_date="2026-01-01"),
        fixture("filing", form="N-54C", filing_date="2026-06-01"),
        fixture("filing", form="N-54A", filing_date="2026-09-01"),
    )
    value = build_bdc_state_observation(filings, filing_cutoff=AS_OF, resolver=SecIdentityResolver((identity(),)), source_observed_at=NOW)
    assert value is not None and value.asserted_issuer_structure is None
    assert "bdc_election_terminated" in value.decision_reasons


def test_n2_10k_and_foreign_reports_do_not_overclaim() -> None:
    n2 = parse(fixture("filing", form="N-2"))
    ten_k = parse(fixture("filing", form="10-K"))
    twenty_f = parse(fixture("filing", form="20-F"))
    forty_f = parse(fixture("filing", form="40-F"))
    assert n2 and n2.asserted_issuer_structure is None and "fund_structure_ambiguous" in n2.quality_flags
    assert ten_k and ten_k.evidence_grade is SecEvidenceGrade.INSUFFICIENT
    assert twenty_f and forty_f and twenty_f.asserted_security_form is None
    assert twenty_f.asserted_listing_scope is None


def test_inline_xbrl_cover_triad_is_strong_security_form_evidence_not_issuer_proof() -> None:
    value = parse(fixture(
        "inline_xbrl_cover", ticker=None, TradingSymbol="TEST",
        SecurityExchangeName="XNYS", Security12bTitle="Common Stock",
    ))
    assert value is not None and value.asserted_security_form is SecurityForm.COMMON_SHARE
    assert value.asserted_issuer_structure is None
    assert value.evidence_grade is SecEvidenceGrade.AUTHORITATIVE_FILING_COVER


def test_future_filing_is_not_backfilled() -> None:
    assert parse(fixture("filing", form="10-K", filing_date="2026-08-15")) is None


def test_company_name_never_creates_positive_assertion() -> None:
    value = parse(fixture("company_tickers_exchange", name="Example Operating Company"))
    assert value is not None
    assert value.asserted_security_form is None and value.asserted_issuer_structure is None


def test_conflicting_authoritative_evidence_is_quarantined() -> None:
    common = parse(fixture(
        "inline_xbrl_cover", ticker=None, TradingSymbol="TEST",
        SecurityExchangeName="XNYS", Security12bTitle="Common Stock",
        accessionNumber="a",
    ))
    preferred = parse(fixture(
        "inline_xbrl_cover", ticker=None, TradingSymbol="TEST",
        SecurityExchangeName="XNYS", Security12bTitle="Preferred Stock",
        accessionNumber="b",
    ))
    assert common and preferred
    result = reconcile_sec_evidence((common, preferred), as_of_date=AS_OF)
    assert result[0].universe_disposition is UniverseDisposition.QUARANTINE
    assert result[0].quality_flags == ("evidence_conflict",)


def test_identical_evidence_dedupes_and_input_order_is_deterministic() -> None:
    value = parse(fixture("company_tickers_mf"))
    assert value
    first = reconcile_sec_evidence((value, value), as_of_date=AS_OF)
    second = reconcile_sec_evidence((value,), as_of_date=AS_OF)
    assert first == second


def test_core_and_broad_rules_are_deterministic_and_exclude_unknown() -> None:
    grade = SecEvidenceGrade.AUTHORITATIVE_EXPLICIT
    core = decide_universe_disposition(
        security_form=SecurityForm.COMMON_SHARE,
        issuer_structure=IssuerStructure.OPERATING_COMPANY,
        listing_scope=ListingScope.US_DOMESTIC_PRIMARY,
        evidence_grade=grade,
    )
    broad = decide_universe_disposition(
        security_form=SecurityForm.ADR_ADS,
        issuer_structure=IssuerStructure.OPERATING_COMPANY,
        listing_scope=ListingScope.DEPOSITARY_RECEIPT,
        evidence_grade=grade,
    )
    assert core is UniverseDisposition.CANDIDATE_CORE
    assert broad is UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL
    assert decide_universe_disposition(
        security_form=SecurityForm.COMMON_SHARE,
        issuer_structure=IssuerStructure.EQUITY_REIT,
        listing_scope=ListingScope.US_DOMESTIC_PRIMARY,
        evidence_grade=grade,
    ) is UniverseDisposition.CANDIDATE_CORE
    for structure in (
        IssuerStructure.ETF, IssuerStructure.ETN, IssuerStructure.CLOSED_END_FUND,
        IssuerStructure.OPEN_END_FUND, IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY,
        IssuerStructure.MORTGAGE_REIT, IssuerStructure.SPAC_BLANK_CHECK,
        IssuerStructure.PARTNERSHIP, IssuerStructure.ROYALTY_TRUST,
    ):
        assert decide_universe_disposition(
            security_form=SecurityForm.COMMON_SHARE, issuer_structure=structure,
            listing_scope=ListingScope.US_DOMESTIC_PRIMARY, evidence_grade=grade,
        ) is UniverseDisposition.EXCLUDED
    assert decide_universe_disposition(
        security_form=None, issuer_structure=None, listing_scope=None,
        evidence_grade=SecEvidenceGrade.INSUFFICIENT,
    ) is UniverseDisposition.QUARANTINE


def test_special_security_forms_are_excluded_from_core_and_broad() -> None:
    for form in (
        SecurityForm.PREFERRED_SHARE, SecurityForm.DEPOSITARY_PREFERRED, SecurityForm.FUND_SHARE,
        SecurityForm.TRUST_UNIT, SecurityForm.PARTNERSHIP_UNIT, SecurityForm.UNIT,
        SecurityForm.WARRANT, SecurityForm.RIGHT, SecurityForm.DEBT, SecurityForm.STRUCTURED_PRODUCT,
    ):
        assert decide_universe_disposition(
            security_form=form,
            issuer_structure=IssuerStructure.OPERATING_COMPANY,
            listing_scope=ListingScope.US_DOMESTIC_PRIMARY,
            evidence_grade=SecEvidenceGrade.AUTHORITATIVE_EXPLICIT,
        ) is UniverseDisposition.EXCLUDED
