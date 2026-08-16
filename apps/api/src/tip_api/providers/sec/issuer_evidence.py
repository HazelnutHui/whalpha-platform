"""Deterministic SEC fixture interpretation and identity reconciliation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Iterable, Mapping
from uuid import UUID

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.security_classification.v1 import IssuerStructure, ListingScope, SecurityForm, UniverseDisposition
from tip_api.contracts.security_classification.v1.sec_evidence import (
    SecEvidenceGrade,
    SecEvidenceResolutionStatus,
    SecEvidenceSubject,
    SecIssuerEvidenceObservationV1,
    SecIssuerStructureEvidenceV1,
)


@dataclass(frozen=True, slots=True)
class SecIdentityRecord:
    instrument_id: UUID
    effective_from: date
    effective_to: date | None = None
    cik: str | None = None
    ticker: str | None = None
    exchange: str | None = None
    share_class_figi: str | None = None
    composite_figi: str | None = None
    provider_stable_identifier: str | None = None

    def active_on(self, as_of_date: date) -> bool:
        return self.effective_from <= as_of_date and (
            self.effective_to is None or as_of_date < self.effective_to
        )


@dataclass(frozen=True, slots=True)
class SecIdentityResolution:
    instrument_id: UUID | None
    status: SecEvidenceResolutionStatus
    method: str
    reasons: tuple[str, ...]


class SecIdentityResolver:
    """Resolve SEC records without permitting ticker-only permanent identity."""

    def __init__(self, records: tuple[SecIdentityRecord, ...]) -> None:
        self._records = records

    def resolve(self, raw: Mapping[str, Any], *, as_of_date: date) -> SecIdentityResolution:
        active = tuple(item for item in self._records if item.active_on(as_of_date))
        stages = (
            ("stable_instrument_id", "instrument_id"),
            ("share_class_figi", "share_class_figi"),
            ("composite_figi", "composite_figi"),
            ("provider_stable_identifier", "provider_stable_identifier"),
        )
        selected: tuple[SecIdentityRecord, ...] = ()
        method = "unresolved"
        for method_name, field in stages:
            value = _optional_text(raw.get(field), uppercase=field in {"share_class_figi", "composite_figi"})
            if value is None:
                continue
            if field == "instrument_id":
                matches = tuple(item for item in active if str(item.instrument_id) == value)
            else:
                matches = tuple(item for item in active if getattr(item, field) == value)
            if len({item.instrument_id for item in matches}) > 1:
                return SecIdentityResolution(None, SecEvidenceResolutionStatus.COLLISION, method_name, ("stable_identifier_collision",))
            if matches:
                selected, method = matches, method_name
                break

        cover_matches: tuple[SecIdentityRecord, ...] = ()
        if raw.get("source_dataset") == "inline_xbrl_cover" or raw.get("allow_cik_ticker_exchange") is True:
            cik = _normalize_cik(_raw_value(raw, "cik", "cik_str"))
            ticker = _optional_text(_raw_value(raw, "TradingSymbol", "trading_symbol", "ticker"), uppercase=True)
            exchange = _optional_text(_raw_value(raw, "SecurityExchangeName", "security_exchange_name", "exchange"), uppercase=True)
            if cik and ticker and exchange:
                cover_matches = tuple(
                    item for item in active
                    if _normalize_cik(item.cik) == cik and item.ticker == ticker and item.exchange == exchange
                )
                if not selected and len({item.instrument_id for item in cover_matches}) == 1:
                    selected, method = cover_matches, "cik_cover_ticker_exchange"
                elif not selected and len({item.instrument_id for item in cover_matches}) > 1:
                    return SecIdentityResolution(None, SecEvidenceResolutionStatus.AMBIGUOUS, "cik_cover_ticker_exchange", ("multiple_cik_ticker_exchange_candidates",))

        if not selected:
            reason = "ticker_only_identity_forbidden" if _optional_text(raw.get("ticker"), uppercase=True) else "identity_evidence_missing"
            return SecIdentityResolution(None, SecEvidenceResolutionStatus.EXPECTED_UNJOINED, "unresolved", (reason,))

        instrument_id = selected[0].instrument_id
        conflicts: set[UUID] = set()
        for _, field in stages[1:]:
            value = _optional_text(raw.get(field), uppercase=field in {"share_class_figi", "composite_figi"})
            if value:
                conflicts.update(item.instrument_id for item in active if getattr(item, field) == value)
        conflicts.discard(instrument_id)
        conflicts.update(item.instrument_id for item in cover_matches if item.instrument_id != instrument_id)
        if conflicts:
            return SecIdentityResolution(None, SecEvidenceResolutionStatus.AMBIGUOUS, method, ("identifier_evidence_conflict",))
        return SecIdentityResolution(instrument_id, SecEvidenceResolutionStatus.CANONICAL_MAPPED, method, (f"{method}_join",))


def interpret_sec_fixture(
    raw: Mapping[str, Any],
    *,
    filing_cutoff: date,
    resolver: SecIdentityResolver,
    source_observed_at: datetime,
) -> SecIssuerEvidenceObservationV1 | None:
    """Interpret one tiny official-shape fixture without retaining the raw mapping."""

    filing_date = _required_date(_raw_value(raw, "filing_date", "filingDate"))
    if filing_date > filing_cutoff:
        return None
    dataset = _required_text(raw.get("source_dataset"))
    resolution = resolver.resolve(raw, as_of_date=filing_cutoff)
    assertion = _interpret_assertion(raw, dataset)
    reasons = tuple(sorted(set(resolution.reasons) | set(assertion[5])))
    flags = tuple(sorted(set(assertion[6])))
    identity = {
        "instrument_id": str(resolution.instrument_id) if resolution.instrument_id else None,
        "cik": _normalize_cik(_raw_value(raw, "cik", "cik_str")),
        "dataset": dataset,
        "document": _required_text(raw.get("source_document_type", dataset)),
        "form": _optional_text(raw.get("form"), uppercase=True),
        "accession": _optional_text(_raw_value(raw, "accession_number", "accessionNumber")),
        "filing_date": filing_date.isoformat(),
        "ticker": _optional_text(_raw_value(raw, "ticker", "TradingSymbol", "trading_symbol"), uppercase=True),
        "exchange": _optional_text(_raw_value(raw, "exchange", "SecurityExchangeName", "security_exchange_name"), uppercase=True),
        "assertions": [item.value if item is not None else None for item in assertion[:3]],
        "subject": assertion[3].value,
        "grade": assertion[4].value,
        "reasons": reasons,
    }
    observation_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return SecIssuerEvidenceObservationV1(
        observation_id=observation_id,
        instrument_id=resolution.instrument_id,
        cik=identity["cik"],
        source_dataset=dataset,
        source_document_type=identity["document"],
        form_type=identity["form"],
        accession_number=identity["accession"],
        filing_date=filing_date,
        effective_from=filing_date,
        ticker=identity["ticker"],
        exchange=identity["exchange"],
        share_class_figi=_optional_text(raw.get("share_class_figi"), uppercase=True),
        composite_figi=_optional_text(raw.get("composite_figi"), uppercase=True),
        provider_stable_identifier=_optional_text(raw.get("provider_stable_identifier")),
        evidence_subject=assertion[3],
        asserted_security_form=assertion[0],
        asserted_issuer_structure=assertion[1],
        asserted_listing_scope=assertion[2],
        evidence_grade=assertion[4],
        resolution_status=resolution.status,
        decision_reasons=reasons,
        source_observed_at=source_observed_at,
        quality_status=QualityStatus.WARNING if flags or resolution.status is not SecEvidenceResolutionStatus.CANONICAL_MAPPED else QualityStatus.VALID,
        quality_flags=flags,
    )


def build_bdc_state_observation(
    filings: Iterable[Mapping[str, Any]],
    *,
    filing_cutoff: date,
    resolver: SecIdentityResolver,
    source_observed_at: datetime,
) -> SecIssuerEvidenceObservationV1 | None:
    eligible = [item for item in filings if _required_date(_raw_value(item, "filing_date", "filingDate")) <= filing_cutoff]
    if not eligible:
        return None
    latest = max(eligible, key=lambda item: (_required_date(_raw_value(item, "filing_date", "filingDate")), str(_raw_value(item, "accession_number", "accessionNumber") or "")))
    return interpret_sec_fixture(latest, filing_cutoff=filing_cutoff, resolver=resolver, source_observed_at=source_observed_at)


def reconcile_sec_evidence(
    observations: tuple[SecIssuerEvidenceObservationV1, ...],
    *,
    as_of_date: date,
) -> tuple[SecIssuerStructureEvidenceV1, ...]:
    by_instrument: dict[UUID, list[SecIssuerEvidenceObservationV1]] = {}
    for item in observations:
        if item.resolution_status is SecEvidenceResolutionStatus.CANONICAL_MAPPED and item.is_effective_on(as_of_date):
            assert item.instrument_id is not None
            by_instrument.setdefault(item.instrument_id, []).append(item)
    result: list[SecIssuerStructureEvidenceV1] = []
    for instrument_id, records in by_instrument.items():
        unique = {item.observation_id: item for item in records}
        ordered = tuple(sorted(unique.values(), key=lambda item: item.observation_id))
        forms = {item.asserted_security_form for item in ordered if item.asserted_security_form is not None}
        structures = {item.asserted_issuer_structure for item in ordered if item.asserted_issuer_structure is not None}
        scopes = {item.asserted_listing_scope for item in ordered if item.asserted_listing_scope is not None}
        conflict = any(len(values) > 1 for values in (forms, structures, scopes))
        form = next(iter(forms)) if len(forms) == 1 and not conflict else None
        structure = next(iter(structures)) if len(structures) == 1 and not conflict else None
        scope = next(iter(scopes)) if len(scopes) == 1 and not conflict else None
        best_grade = min((item.evidence_grade for item in ordered), key=_grade_rank)
        disposition = UniverseDisposition.QUARANTINE if conflict else decide_universe_disposition(
            security_form=form,
            issuer_structure=structure,
            listing_scope=scope,
            evidence_grade=best_grade,
        )
        result.append(SecIssuerStructureEvidenceV1(
            as_of_date=as_of_date,
            instrument_id=instrument_id,
            cik=ordered[0].cik,
            asserted_security_form=form,
            asserted_issuer_structure=structure,
            asserted_listing_scope=scope,
            evidence_grade=best_grade,
            universe_disposition=disposition,
            source_observation_ids=tuple(item.observation_id for item in ordered),
            decision_reasons=("conflicting_authoritative_evidence",) if conflict else (f"disposition:{disposition.value}",),
            quality_status=QualityStatus.PENDING_REVIEW if conflict or disposition is UniverseDisposition.QUARANTINE else QualityStatus.VALID,
            quality_flags=("evidence_conflict",) if conflict else (),
            source_observed_at=max(item.source_observed_at for item in ordered),
        ))
    return tuple(sorted(result, key=lambda item: (str(item.instrument_id), item.as_of_date)))


def decide_universe_disposition(
    *,
    security_form: SecurityForm | None,
    issuer_structure: IssuerStructure | None,
    listing_scope: ListingScope | None,
    evidence_grade: SecEvidenceGrade,
) -> UniverseDisposition:
    high_confidence = evidence_grade in {
        SecEvidenceGrade.AUTHORITATIVE_EXPLICIT,
        SecEvidenceGrade.AUTHORITATIVE_FILING_COVER,
        SecEvidenceGrade.AUTHORITATIVE_STATE_MACHINE,
    }
    excluded_forms = {
        SecurityForm.PREFERRED_SHARE, SecurityForm.DEPOSITARY_PREFERRED, SecurityForm.FUND_SHARE,
        SecurityForm.TRUST_UNIT, SecurityForm.PARTNERSHIP_UNIT, SecurityForm.UNIT, SecurityForm.WARRANT,
        SecurityForm.RIGHT, SecurityForm.DEBT, SecurityForm.STRUCTURED_PRODUCT,
    }
    excluded_structures = {
        IssuerStructure.MORTGAGE_REIT, IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY,
        IssuerStructure.SPAC_BLANK_CHECK, IssuerStructure.ETF, IssuerStructure.ETN,
        IssuerStructure.CLOSED_END_FUND, IssuerStructure.OPEN_END_FUND, IssuerStructure.PARTNERSHIP,
        IssuerStructure.ROYALTY_TRUST, IssuerStructure.STRUCTURED_PRODUCT_VEHICLE,
    }
    if security_form in excluded_forms or issuer_structure in excluded_structures:
        return UniverseDisposition.EXCLUDED
    if not high_confidence:
        return UniverseDisposition.QUARANTINE
    if (
        security_form in {SecurityForm.COMMON_SHARE, SecurityForm.ORDINARY_SHARE}
        and issuer_structure in {IssuerStructure.OPERATING_COMPANY, IssuerStructure.EQUITY_REIT}
        and listing_scope is ListingScope.US_DOMESTIC_PRIMARY
    ):
        return UniverseDisposition.CANDIDATE_CORE
    if (
        security_form in {SecurityForm.ORDINARY_SHARE, SecurityForm.ADR_ADS}
        and issuer_structure is IssuerStructure.OPERATING_COMPANY
        and listing_scope in {ListingScope.US_LISTED_FOREIGN, ListingScope.DEPOSITARY_RECEIPT}
    ):
        return UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL
    return UniverseDisposition.QUARANTINE


def _interpret_assertion(raw: Mapping[str, Any], dataset: str) -> tuple[
    SecurityForm | None, IssuerStructure | None, ListingScope | None,
    SecEvidenceSubject, SecEvidenceGrade, tuple[str, ...], tuple[str, ...],
]:
    form = _optional_text(raw.get("form"), uppercase=True)
    if dataset == "company_tickers_exchange":
        flags = ("sic_review_signal",) if raw.get("sic") else ()
        return None, None, None, SecEvidenceSubject.IDENTITY_REFERENCE, SecEvidenceGrade.CORROBORATING_REFERENCE, ("join_seed_only",), flags
    if raw.get("historical_cutoff_supported") is False:
        return None, None, None, SecEvidenceSubject.IDENTITY_REFERENCE, SecEvidenceGrade.INSUFFICIENT, ("current_reference_not_backfilled",), ("historical_effective_date_unavailable",)
    if dataset == "company_tickers_mf":
        return SecurityForm.FUND_SHARE, None, None, SecEvidenceSubject.FUND_STATUS, SecEvidenceGrade.AUTHORITATIVE_EXPLICIT, ("mutual_fund_dataset_presence",), ()
    if dataset == "n_cen":
        return SecurityForm.FUND_SHARE, None, None, SecEvidenceSubject.FUND_STATUS, SecEvidenceGrade.AUTHORITATIVE_EXPLICIT, ("n_cen_registered_investment_company",), ()
    if dataset == "investment_company_series_class":
        kind = _optional_text(raw.get("fund_kind"))
        structure = IssuerStructure.ETF if kind == "etf" else IssuerStructure.OPEN_END_FUND if kind == "open_end_fund" else None
        return SecurityForm.FUND_SHARE, structure, None, SecEvidenceSubject.FUND_STATUS, SecEvidenceGrade.AUTHORITATIVE_EXPLICIT, ("investment_company_series_class",), () if structure else ("fund_kind_unresolved",)
    if dataset == "closed_end_fund":
        return SecurityForm.FUND_SHARE, IssuerStructure.CLOSED_END_FUND, None, SecEvidenceSubject.FUND_STATUS, SecEvidenceGrade.AUTHORITATIVE_EXPLICIT, ("official_closed_end_fund_dataset",), ()
    if dataset == "business_development_company":
        return None, IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY, None, SecEvidenceSubject.BDC_STATUS, SecEvidenceGrade.AUTHORITATIVE_EXPLICIT, ("official_bdc_dataset",), ()
    if dataset == "filing" and form == "N-54A":
        return None, IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY, None, SecEvidenceSubject.BDC_STATUS, SecEvidenceGrade.AUTHORITATIVE_STATE_MACHINE, ("bdc_election_active",), ()
    if dataset == "filing" and form == "N-54C":
        return None, None, None, SecEvidenceSubject.BDC_STATUS, SecEvidenceGrade.AUTHORITATIVE_STATE_MACHINE, ("bdc_election_terminated",), ("issuer_structure_requires_post_termination_evidence",)
    if dataset == "filing" and form == "N-2":
        return None, None, None, SecEvidenceSubject.FUND_STATUS, SecEvidenceGrade.INSUFFICIENT, ("n2_does_not_distinguish_cef_from_bdc",), ("fund_structure_ambiguous",)
    if dataset == "filing" and form == "10-K":
        return None, None, None, SecEvidenceSubject.REPORTING_STATUS, SecEvidenceGrade.INSUFFICIENT, ("10k_alone_does_not_prove_operating_domestic_equity",), ()
    if dataset == "filing" and form in {"20-F", "40-F"}:
        return None, None, None, SecEvidenceSubject.REPORTING_STATUS, SecEvidenceGrade.CORROBORATING_REFERENCE, ("foreign_private_reporting_evidence_not_adr_proof",), ()
    if dataset == "inline_xbrl_cover":
        title = _optional_text(_raw_value(raw, "Security12bTitle", "security_12b_title"))
        ticker = _optional_text(_raw_value(raw, "TradingSymbol", "trading_symbol"), uppercase=True)
        exchange = _optional_text(_raw_value(raw, "SecurityExchangeName", "security_exchange_name"), uppercase=True)
        if title and ticker and exchange:
            mapped = {
                "Common Stock": SecurityForm.COMMON_SHARE,
                "Ordinary Shares": SecurityForm.ORDINARY_SHARE,
                "American Depositary Shares": SecurityForm.ADR_ADS,
                "Preferred Stock": SecurityForm.PREFERRED_SHARE,
                "Warrants": SecurityForm.WARRANT,
                "Units": SecurityForm.UNIT,
            }.get(title)
            if mapped:
                return mapped, None, None, SecEvidenceSubject.SECURITY, SecEvidenceGrade.AUTHORITATIVE_FILING_COVER, ("cover_page_security_mapping",), ()
        return None, None, None, SecEvidenceSubject.SECURITY, SecEvidenceGrade.INSUFFICIENT, ("cover_page_triad_incomplete_or_unsupported",), ("cover_page_review_required",)
    return None, None, None, SecEvidenceSubject.ISSUER_STRUCTURE, SecEvidenceGrade.INSUFFICIENT, ("unsupported_sec_evidence",), ("unsupported_source_dataset",)


def _grade_rank(value: SecEvidenceGrade) -> int:
    return list(SecEvidenceGrade).index(value)


def _required_text(value: Any, default: str | None = None) -> str:
    candidate = default if value is None else value
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("SEC fixture text field is required")
    return candidate.strip()


def _raw_value(raw: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _optional_text(value: Any, *, uppercase: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    result = value.strip()
    return result.upper() if uppercase else result


def _normalize_cik(value: Any) -> str:
    text = _required_text(str(value) if value is not None else None)
    if not text.isdigit() or len(text) > 10:
        raise ValueError("SEC fixture CIK is invalid")
    return text.zfill(10)


def _required_date(value: Any) -> date:
    if isinstance(value, datetime):
        raise ValueError("SEC fixture filing_date must be a date")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("SEC fixture filing_date is invalid")


def utc_now_for_tests() -> datetime:
    """Explicit helper only for callers that deliberately choose wall time."""
    return datetime.now(UTC)
