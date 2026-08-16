from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus,
    EvidenceGrade,
    IssuerStructure,
    ListingScope,
    SecurityForm,
    UniverseDisposition,
    ProviderInstrumentSecurityEvidenceV1,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.security_classification import (
    SecurityClassificationOverride,
    SecurityClassificationService,
    reviewed_overrides,
    safe_audit_summary,
    validate_override_registry,
)

NS = UUID("00000000-0000-4000-8000-000000000099")
VCX_ID = UUID("4acc30c6-9461-588d-a0cc-a66d4d23d0d0")
AKAN_ID = UUID("d8839d68-59a8-5525-a67d-676203ebea3a")


def bar(
    ticker: str,
    session: date,
    *,
    instrument_id: UUID | None = None,
    instrument_type: InstrumentType = InstrumentType.COMMON_STOCK,
    name: str | None = None,
    exchange: str = "XNYS",
    close: str = "20",
    volume: str = "2000000",
    quality_flags: tuple[str, ...] = (),
) -> EodMarketBarReadModel:
    return EodMarketBarReadModel(
        instrument_id=instrument_id or uuid5(NS, ticker),
        ticker=ticker,
        name=name or f"Fictional {ticker} Corporation",
        instrument_type=instrument_type,
        primary_exchange=exchange,
        session_date=session,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal(volume),
        vwap=None,
        trade_count=None,
        currency="USD",
        source="fictional-provider",
        quality_status=QualityStatus.VALID,
        quality_flags=quality_flags,
    )


def override(
    ticker: str,
    *,
    form: SecurityForm,
    structure: IssuerStructure,
    scope: ListingScope = ListingScope.US_DOMESTIC_PRIMARY,
    disposition: UniverseDisposition = UniverseDisposition.EXCLUDED,
    status: ClassificationStatus = ClassificationStatus.EXCLUDED_RESOLVED,
    is_us_domiciled: bool = True,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
) -> SecurityClassificationOverride:
    return SecurityClassificationOverride(
        instrument_id=uuid5(NS, ticker),
        effective_from=effective_from,
        effective_to=effective_to,
        source_url=f"https://www.sec.gov/Archives/edgar/data/1/{ticker.lower()}.htm",
        source_document_date=date(2026, 1, 1),
        reviewed_at=datetime(2026, 8, 15, tzinfo=UTC),
        reviewer="fixture-reviewer",
        reason="Fictional authoritative fixture.",
        security_form=form,
        issuer_structure=structure,
        listing_scope=scope,
        listing_country="US",
        issuer_domicile_country="US" if is_us_domiciled else "CA",
        incorporation_country="US" if is_us_domiciled else "CA",
        is_us_domiciled=is_us_domiciled,
        classification_status=status,
        universe_disposition=disposition,
    )


def run(tickers: list[str], overrides: tuple[SecurityClassificationOverride, ...] = ()):
    previous = tuple(bar(ticker, date(2026, 8, 13)) for ticker in tickers)
    current = tuple(bar(ticker, date(2026, 8, 14)) for ticker in reversed(tickers))
    return SecurityClassificationService(overrides=overrides).audit(current_bars=current, previous_bars=previous)


def test_provider_explicit_etf_is_excluded_and_unknown_common_is_quarantined() -> None:
    previous = (bar("SPY", date(2026, 8, 13), instrument_type=InstrumentType.ETF), bar("TEST", date(2026, 8, 13)))
    current = (bar("TEST", date(2026, 8, 14)), bar("SPY", date(2026, 8, 14), instrument_type=InstrumentType.ETF))
    audit = SecurityClassificationService().audit(current_bars=current, previous_bars=previous)
    by_id = {item.instrument_id: item for item in audit.classifications}
    assert by_id[uuid5(NS, "SPY")].issuer_structure is IssuerStructure.ETF
    assert by_id[uuid5(NS, "SPY")].universe_disposition is UniverseDisposition.EXCLUDED
    assert by_id[uuid5(NS, "TEST")].classification_status is ClassificationStatus.UNKNOWN
    assert by_id[uuid5(NS, "TEST")].universe_disposition is UniverseDisposition.QUARANTINE


@pytest.mark.parametrize("ticker", ["SPY", "QQQ", "IWM", "DIA", "XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLRE", "XLK", "XLU"])
def test_benchmark_etfs_never_enter_equity_candidates(ticker: str) -> None:
    previous = (bar(ticker, date(2026, 8, 13), instrument_type=InstrumentType.ETF),)
    current = (bar(ticker, date(2026, 8, 14), instrument_type=InstrumentType.ETF),)
    audit = SecurityClassificationService().audit(current_bars=current, previous_bars=previous)
    assert not audit.candidate_core_ids
    assert not audit.candidate_broad_ids


@pytest.mark.parametrize(
    ("ticker", "form", "structure"),
    [
        ("MREIT", SecurityForm.COMMON_SHARE, IssuerStructure.MORTGAGE_REIT),
        ("CEF", SecurityForm.FUND_SHARE, IssuerStructure.CLOSED_END_FUND),
        ("BDC", SecurityForm.COMMON_SHARE, IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY),
        ("OPEN", SecurityForm.FUND_SHARE, IssuerStructure.OPEN_END_FUND),
        ("PREF", SecurityForm.PREFERRED_SHARE, IssuerStructure.OPERATING_COMPANY),
        ("DPREF", SecurityForm.DEPOSITARY_PREFERRED, IssuerStructure.OPERATING_COMPANY),
        ("WARRANT", SecurityForm.WARRANT, IssuerStructure.OPERATING_COMPANY),
        ("RIGHT", SecurityForm.RIGHT, IssuerStructure.OPERATING_COMPANY),
        ("UNIT", SecurityForm.UNIT, IssuerStructure.SPAC_BLANK_CHECK),
        ("SPAC", SecurityForm.COMMON_SHARE, IssuerStructure.SPAC_BLANK_CHECK),
        ("MLP", SecurityForm.PARTNERSHIP_UNIT, IssuerStructure.PARTNERSHIP),
        ("TRUST", SecurityForm.TRUST_UNIT, IssuerStructure.ROYALTY_TRUST),
        ("STRUCT", SecurityForm.STRUCTURED_PRODUCT, IssuerStructure.STRUCTURED_PRODUCT_VEHICLE),
        ("ETN", SecurityForm.DEBT, IssuerStructure.ETN),
    ],
)
def test_resolved_non_operating_forms_are_excluded(ticker: str, form: SecurityForm, structure: IssuerStructure) -> None:
    audit = run([ticker], (override(ticker, form=form, structure=structure),))
    assert audit.classifications[0].universe_disposition is UniverseDisposition.EXCLUDED
    assert not audit.candidate_broad_ids


def test_domestic_common_and_equity_reit_enter_core_but_foreign_and_adr_only_enter_broad() -> None:
    overrides = (
        override("DOM", form=SecurityForm.COMMON_SHARE, structure=IssuerStructure.OPERATING_COMPANY, disposition=UniverseDisposition.CANDIDATE_CORE, status=ClassificationStatus.RESOLVED),
        override("REIT", form=SecurityForm.COMMON_SHARE, structure=IssuerStructure.EQUITY_REIT, disposition=UniverseDisposition.CANDIDATE_CORE, status=ClassificationStatus.RESOLVED),
        override("FOREIGN", form=SecurityForm.ORDINARY_SHARE, structure=IssuerStructure.OPERATING_COMPANY, scope=ListingScope.US_LISTED_FOREIGN, disposition=UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL, status=ClassificationStatus.RESOLVED, is_us_domiciled=False),
        override("ADR", form=SecurityForm.ADR_ADS, structure=IssuerStructure.OPERATING_COMPANY, scope=ListingScope.DEPOSITARY_RECEIPT, disposition=UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL, status=ClassificationStatus.RESOLVED, is_us_domiciled=False),
    )
    audit = run(["DOM", "REIT", "FOREIGN", "ADR"], overrides)
    assert len(audit.candidate_core_ids) == 2
    assert len(audit.candidate_broad_ids) == 4


def test_vcx_closed_end_fund_and_akan_foreign_issuer_regressions() -> None:
    previous = (bar("VCX", date(2026, 8, 13), instrument_id=VCX_ID), bar("AKAN", date(2026, 8, 13), instrument_id=AKAN_ID))
    current = (bar("AKAN", date(2026, 8, 14), instrument_id=AKAN_ID), bar("VCX", date(2026, 8, 14), instrument_id=VCX_ID))
    audit = SecurityClassificationService(overrides=reviewed_overrides()).audit(current_bars=current, previous_bars=previous)
    by_id = {item.instrument_id: item for item in audit.classifications}
    assert by_id[VCX_ID].issuer_structure is IssuerStructure.CLOSED_END_FUND
    assert by_id[VCX_ID].universe_disposition is UniverseDisposition.EXCLUDED
    assert by_id[AKAN_ID].listing_scope is ListingScope.US_LISTED_FOREIGN
    assert by_id[AKAN_ID].is_us_domiciled is False
    assert AKAN_ID in audit.candidate_broad_ids and AKAN_ID not in audit.candidate_core_ids


def test_name_heuristic_only_flags_review_and_never_includes() -> None:
    previous = (bar("FLAG", date(2026, 8, 13), name="Fictional Acquisition Fund"),)
    current = (bar("FLAG", date(2026, 8, 14), name="Fictional Acquisition Fund"),)
    item = SecurityClassificationService().audit(current_bars=current, previous_bars=previous).classifications[0]
    assert item.evidence_grade is EvidenceGrade.HEURISTIC_FLAG_ONLY
    assert item.universe_disposition is UniverseDisposition.QUARANTINE
    assert item.security_form is SecurityForm.UNKNOWN


def test_override_precedence_and_conflict_hard_fail() -> None:
    first = override("TEST", form=SecurityForm.COMMON_SHARE, structure=IssuerStructure.OPERATING_COMPANY, disposition=UniverseDisposition.CANDIDATE_CORE, status=ClassificationStatus.RESOLVED, effective_to=date(2026, 9, 1))
    overlap = override("TEST", form=SecurityForm.COMMON_SHARE, structure=IssuerStructure.OPERATING_COMPANY, disposition=UniverseDisposition.CANDIDATE_CORE, status=ClassificationStatus.RESOLVED, effective_from=date(2026, 8, 15))
    with pytest.raises(ValueError, match="overlap"):
        validate_override_registry((first, overlap))


def test_price_liquidity_exchange_and_material_quality_funnel_is_sequential() -> None:
    candidates = tuple(
        override(t, form=SecurityForm.COMMON_SHARE, structure=IssuerStructure.OPERATING_COMPANY, disposition=UniverseDisposition.CANDIDATE_CORE, status=ClassificationStatus.RESOLVED)
        for t in ("GOOD", "LOW", "ILLIQ", "OTC", "WARN")
    )
    previous = (
        bar("GOOD", date(2026, 8, 13)),
        bar("LOW", date(2026, 8, 13), close="4"),
        bar("ILLIQ", date(2026, 8, 13), volume="10"),
        bar("OTC", date(2026, 8, 13), exchange="OTCM"),
        bar("WARN", date(2026, 8, 13), quality_flags=("identity_conflict",)),
    )
    current = (
        bar("GOOD", date(2026, 8, 14)),
        bar("LOW", date(2026, 8, 14)),
        bar("ILLIQ", date(2026, 8, 14)),
        bar("OTC", date(2026, 8, 14), exchange="OTCM"),
        bar("WARN", date(2026, 8, 14)),
    )
    audit = SecurityClassificationService(overrides=candidates).audit(current_bars=current, previous_bars=previous)
    assert audit.core_funnel.classification_eligible == 5
    assert audit.core_funnel.supported_primary_exchange == 4
    assert audit.core_funnel.previous_price_gate_passed == 3
    assert audit.core_funnel.previous_dollar_volume_gate_passed == 2
    assert audit.core_funnel.final_candidate_universe == 1


def test_input_order_independence_fingerprint_and_exact_reconciliation() -> None:
    first = run(["A", "B", "C"])
    second = run(["C", "A", "B"])
    assert first.taxonomy_fingerprint == second.taxonomy_fingerprint
    status_total = sum(first.distribution("classification_status").values())
    disposition_total = sum(first.distribution("universe_disposition").values())
    assert status_total == disposition_total == first.raw_comparable_count == 3


def test_missing_bar_excluded_from_raw_and_ticker_rename_joins_by_id() -> None:
    identity = uuid5(NS, "stable")
    previous = (bar("OLD", date(2026, 8, 13), instrument_id=identity), bar("MISSING", date(2026, 8, 13)))
    current = (bar("NEW", date(2026, 8, 14), instrument_id=identity),)
    audit = SecurityClassificationService().audit(current_bars=current, previous_bars=previous)
    assert audit.raw_comparable_count == 1
    assert audit.classifications[0].instrument_id == identity


def test_duplicate_stable_identity_and_malformed_sessions_fail() -> None:
    duplicate = (bar("A", date(2026, 8, 14)), bar("A", date(2026, 8, 14)))
    with pytest.raises(ValueError, match="duplicate"):
        SecurityClassificationService().audit(current_bars=duplicate, previous_bars=(bar("A", date(2026, 8, 13)),))
    with pytest.raises(ValueError, match="one session"):
        SecurityClassificationService().audit(current_bars=(bar("A", date(2026, 8, 14)), bar("B", date(2026, 8, 13))), previous_bars=(bar("A", date(2026, 8, 13)),))


def test_unknown_ambiguous_malformed_dispositions_cannot_pollute_candidates() -> None:
    # Contract tests enforce all three statuses. The service defaults absent evidence to UNKNOWN/quarantine.
    audit = run(["UNKNOWN"])
    assert audit.distribution("classification_status") == {"unknown": 1}
    assert audit.distribution("universe_disposition") == {"quarantine": 1}
    assert not audit.candidate_core_ids and not audit.candidate_broad_ids


def test_safe_audit_report_has_no_raw_payload_or_filesystem_path() -> None:
    summary = safe_audit_summary(run(["TESTA", "TESTB"]))
    serialized = str(summary).lower()
    assert "raw_payload" not in serialized
    assert "filesystem" not in serialized
    assert "/data/" not in serialized
    assert "credential" not in serialized


def test_candidate_sets_are_mutually_safe_and_counts_reconcile() -> None:
    audit = run(["UNKNOWN"])
    dispositions = audit.distribution("universe_disposition")
    assert sum(dispositions.values()) == audit.raw_comparable_count
    assert audit.candidate_core_ids <= audit.candidate_broad_ids
    excluded_or_quarantine = {
        item.instrument_id
        for item in audit.classifications
        if item.universe_disposition in {UniverseDisposition.EXCLUDED, UniverseDisposition.QUARANTINE}
    }
    assert excluded_or_quarantine.isdisjoint(audit.candidate_broad_ids)


def test_provider_common_share_evidence_does_not_prove_operating_company() -> None:
    instrument_id = uuid5(NS, "PROVIDER")
    evidence = ProviderInstrumentSecurityEvidenceV1(
        as_of_date=date(2026, 8, 14), instrument_id=instrument_id, provider="fictional-provider",
        provider_ticker="PROVIDER", provider_type_code="CS", provider_type_description="Common Stock",
        primary_exchange="XNYS", security_form_evidence=SecurityForm.COMMON_SHARE,
        evidence_source="/v3/reference/tickers", evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,
        classification_status=ClassificationStatus.UNKNOWN, universe_disposition=UniverseDisposition.QUARANTINE,
        decision_flags=("provider_security_form_only",), review_flags=("issuer_structure_unresolved",),
        observed_at=datetime(2026, 8, 15, tzinfo=UTC), ingested_at=datetime(2026, 8, 15, tzinfo=UTC),
    )
    previous = (bar("PROVIDER", date(2026, 8, 13), instrument_id=instrument_id),)
    current = (bar("PROVIDER", date(2026, 8, 14), instrument_id=instrument_id),)
    audit = SecurityClassificationService(provider_evidence=(evidence,)).audit(current_bars=current, previous_bars=previous)
    item = audit.classifications[0]
    assert item.security_form is SecurityForm.COMMON_SHARE
    assert item.issuer_structure is IssuerStructure.UNKNOWN
    assert item.universe_disposition is UniverseDisposition.QUARANTINE
