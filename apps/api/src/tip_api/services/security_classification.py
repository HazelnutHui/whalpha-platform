"""Security classification and candidate-universe audit services."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.contracts.security_classification.v1 import (
    ClassificationMethod,
    ClassificationStatus,
    EvidenceGrade,
    IssuerStructure,
    ListingScope,
    ProviderInstrumentSecurityEvidenceV1,
    SecurityClassificationV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.read_models.eod import EodMarketBarReadModel

TAXONOMY_VERSION = "security-type-taxonomy-v1"
RULESET_VERSION = "security-type-governance-phase-a-v1"
SUPPORTED_EXCHANGES = frozenset({"XNYS", "XNAS", "ARCX", "BATS"})
MINIMUM_PREVIOUS_CLOSE = Decimal("5")
MINIMUM_PREVIOUS_DOLLAR_VOLUME = Decimal("20000000")
MATERIAL_QUALITY_FLAGS = frozenset({
    "identity_conflict",
    "price_continuity_review",
    "canonical_validation_failure",
})
REVIEW_NAME_TERMS = (
    "ACQUISITION",
    "DEPOSITARY",
    "FUND",
    "PREFERRED",
    "RIGHT",
    "TRUST",
    "UNIT",
    "WARRANT",
)


class SecurityClassificationOverride(BaseModel):
    """Reviewed, effective-dated decision keyed by canonical identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    effective_from: date
    effective_to: date | None = None
    source_url: str
    source_document_date: date
    reviewed_at: datetime
    reviewer: str
    reason: str
    security_form: SecurityForm
    issuer_structure: IssuerStructure
    listing_scope: ListingScope
    listing_country: str
    issuer_domicile_country: str
    incorporation_country: str
    is_us_domiciled: bool
    classification_status: ClassificationStatus
    universe_disposition: UniverseDisposition

    @field_validator("source_url", "reviewer", "reason", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: object) -> str:
        return normalize_required_string(value, field_name=getattr(info, "field_name", "value"))

    @field_validator("reviewed_at")
    @classmethod
    def normalize_reviewed_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_period(self) -> SecurityClassificationOverride:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("override effective_to must be later than effective_from")
        return self

    def is_effective_on(self, session_date: date) -> bool:
        return self.effective_from <= session_date and (
            self.effective_to is None or session_date < self.effective_to
        )


def validate_override_registry(overrides: tuple[SecurityClassificationOverride, ...]) -> None:
    by_instrument: dict[UUID, list[SecurityClassificationOverride]] = {}
    for override in overrides:
        by_instrument.setdefault(override.instrument_id, []).append(override)
    for records in by_instrument.values():
        ordered = sorted(records, key=lambda item: item.effective_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.effective_to is None or current.effective_from < previous.effective_to:
                raise ValueError("manual override effective periods overlap")


@dataclass(frozen=True, slots=True)
class EligibilityFunnel:
    classification_eligible: int
    supported_primary_exchange: int
    both_sessions_available: int
    previous_price_gate_passed: int
    previous_dollar_volume_gate_passed: int
    data_quality_checks_passed: int
    final_candidate_universe: int


@dataclass(frozen=True, slots=True)
class SecurityClassificationAudit:
    as_of_date: date
    previous_session_date: date
    raw_comparable_count: int
    legacy_default_count: int
    classifications: tuple[SecurityClassificationV1, ...]
    candidate_core_ids: frozenset[UUID]
    candidate_broad_ids: frozenset[UUID]
    core_funnel: EligibilityFunnel
    broad_funnel: EligibilityFunnel
    taxonomy_fingerprint: str
    ruleset_fingerprint: str

    def distribution(self, field_name: str) -> dict[str, int]:
        values = Counter(str(getattr(item, field_name)) for item in self.classifications)
        return dict(sorted(values.items()))


def reviewed_overrides() -> tuple[SecurityClassificationOverride, ...]:
    """Small authoritative registry; ticker is intentionally not a key."""

    reviewed_at = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)
    overrides = (
        SecurityClassificationOverride(
            instrument_id=UUID("4acc30c6-9461-588d-a0cc-a66d4d23d0d0"),
            effective_from=date(2026, 8, 12),
            source_url="https://www.sec.gov/Archives/edgar/data/1867090/000199937126011950/fundrise-ncsra_033126.htm",
            source_document_date=date(2026, 8, 13),
            reviewed_at=reviewed_at,
            reviewer="security-governance-phase-a",
            reason="SEC filing identifies the issuer as a registered closed-end management investment company.",
            security_form=SecurityForm.COMMON_SHARE,
            issuer_structure=IssuerStructure.CLOSED_END_FUND,
            listing_scope=ListingScope.US_DOMESTIC_PRIMARY,
            listing_country="US",
            issuer_domicile_country="US",
            incorporation_country="US",
            is_us_domiciled=True,
            classification_status=ClassificationStatus.EXCLUDED_RESOLVED,
            universe_disposition=UniverseDisposition.EXCLUDED,
        ),
        SecurityClassificationOverride(
            instrument_id=UUID("d8839d68-59a8-5525-a67d-676203ebea3a"),
            effective_from=date(2026, 8, 12),
            source_url="https://www.sec.gov/Archives/edgar/data/1888014/000110465922034560/tm2129724-11_424b4.htm",
            source_document_date=date(2022, 3, 14),
            reviewed_at=reviewed_at,
            reviewer="security-governance-phase-a",
            reason="SEC prospectus identifies an Ontario operating issuer and Nasdaq-listed common shares.",
            security_form=SecurityForm.ORDINARY_SHARE,
            issuer_structure=IssuerStructure.OPERATING_COMPANY,
            listing_scope=ListingScope.US_LISTED_FOREIGN,
            listing_country="US",
            issuer_domicile_country="CA",
            incorporation_country="CA",
            is_us_domiciled=False,
            classification_status=ClassificationStatus.RESOLVED,
            universe_disposition=UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL,
        ),
    )
    validate_override_registry(overrides)
    return overrides


class SecurityClassificationService:
    """Classify comparable bars without changing canonical Instrument Master semantics."""

    def __init__(
        self,
        *,
        overrides: tuple[SecurityClassificationOverride, ...] = (),
        provider_evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...] = (),
    ) -> None:
        validate_override_registry(overrides)
        self._overrides = overrides
        if len({item.instrument_id for item in provider_evidence}) != len(provider_evidence):
            raise ValueError("provider evidence instrument_id must be unique")
        self._provider_evidence = {item.instrument_id: item for item in provider_evidence}

    def audit(
        self,
        *,
        current_bars: tuple[EodMarketBarReadModel, ...],
        previous_bars: tuple[EodMarketBarReadModel, ...],
    ) -> SecurityClassificationAudit:
        if not current_bars or not previous_bars:
            raise ValueError("both sessions are required")
        current_date = _single_session_date(current_bars)
        previous_date = _single_session_date(previous_bars)
        if previous_date >= current_date:
            raise ValueError("previous session must precede current session")
        current = _unique_by_id(current_bars)
        previous = _unique_by_id(previous_bars)
        comparable_ids = frozenset(current) & frozenset(previous)
        classifications = tuple(
            sorted(
                (self._classify(current[instrument_id], current_date) for instrument_id in comparable_ids),
                key=lambda item: str(item.instrument_id),
            )
        )
        if len(classifications) != len(comparable_ids):
            raise ValueError("classification reconciliation failed")

        class_by_id = {item.instrument_id: item for item in classifications}
        core_eligible = {
            instrument_id
            for instrument_id in comparable_ids
            if class_by_id[instrument_id].universe_disposition is UniverseDisposition.CANDIDATE_CORE
        }
        broad_eligible = core_eligible | {
            instrument_id
            for instrument_id in comparable_ids
            if class_by_id[instrument_id].universe_disposition
            is UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL
        }
        core_ids, core_funnel = _apply_eligibility_funnel(core_eligible, current, previous)
        broad_ids, broad_funnel = _apply_eligibility_funnel(broad_eligible, current, previous)
        legacy = {
            instrument_id
            for instrument_id in comparable_ids
            if _passes_legacy_default(current[instrument_id], previous[instrument_id])
        }
        taxonomy_fingerprint = _sha256_json(
            {
                "taxonomy_version": TAXONOMY_VERSION,
                "security_form": [item.value for item in SecurityForm],
                "issuer_structure": [item.value for item in IssuerStructure],
                "listing_scope": [item.value for item in ListingScope],
                "classification_status": [item.value for item in ClassificationStatus],
                "universe_disposition": [item.value for item in UniverseDisposition],
                "evidence_grade": [item.value for item in EvidenceGrade],
            }
        )
        ruleset_fingerprint = _sha256_json(
            {
                "ruleset_version": RULESET_VERSION,
                "supported_exchanges": sorted(SUPPORTED_EXCHANGES),
                "minimum_previous_close": str(MINIMUM_PREVIOUS_CLOSE),
                "minimum_previous_dollar_volume": str(MINIMUM_PREVIOUS_DOLLAR_VOLUME),
            }
        )
        return SecurityClassificationAudit(
            as_of_date=current_date,
            previous_session_date=previous_date,
            raw_comparable_count=len(comparable_ids),
            legacy_default_count=len(legacy),
            classifications=classifications,
            candidate_core_ids=frozenset(core_ids),
            candidate_broad_ids=frozenset(broad_ids),
            core_funnel=core_funnel,
            broad_funnel=broad_funnel,
            taxonomy_fingerprint=taxonomy_fingerprint,
            ruleset_fingerprint=ruleset_fingerprint,
        )

    def _classify(self, bar: EodMarketBarReadModel, as_of_date: date) -> SecurityClassificationV1:
        active = [
            item for item in self._overrides if item.instrument_id == bar.instrument_id and item.is_effective_on(as_of_date)
        ]
        if len(active) > 1:
            raise ValueError("multiple active manual overrides")
        now = datetime(as_of_date.year, as_of_date.month, as_of_date.day, tzinfo=UTC)
        if active:
            override = active[0]
            return SecurityClassificationV1(
                taxonomy_version=TAXONOMY_VERSION,
                ruleset_version=RULESET_VERSION,
                instrument_id=bar.instrument_id,
                provider=bar.source,
                as_of_date=as_of_date,
                effective_from=override.effective_from,
                effective_to=override.effective_to,
                security_form=override.security_form,
                issuer_structure=override.issuer_structure,
                listing_scope=override.listing_scope,
                primary_exchange=bar.primary_exchange,
                listing_country=override.listing_country,
                issuer_domicile_country=override.issuer_domicile_country,
                incorporation_country=override.incorporation_country,
                is_us_listed=True,
                is_us_domiciled=override.is_us_domiciled,
                classification_status=override.classification_status,
                universe_disposition=override.universe_disposition,
                decision_reason_codes=("authoritative_manual_review",),
                classification_method=ClassificationMethod.AUTHORITATIVE_OVERRIDE,
                evidence_grade=EvidenceGrade.AUTHORITATIVE,
                evidence_ids=(override.source_url,),
                quality_flags=(),
                observed_at=override.reviewed_at,
                reviewed_at=override.reviewed_at,
                ingested_at=override.reviewed_at,
            )
        provider_evidence = self._provider_evidence.get(bar.instrument_id)
        if provider_evidence is not None:
            if provider_evidence.as_of_date != as_of_date:
                raise ValueError("provider evidence as_of_date mismatch")
            issuer_structure = {
                "ETF": IssuerStructure.ETF,
                "ETN": IssuerStructure.ETN,
                "ETS": IssuerStructure.ETN,
            }.get(provider_evidence.provider_type_code, IssuerStructure.UNKNOWN)
            listing_scope = (
                ListingScope.DEPOSITARY_RECEIPT
                if provider_evidence.security_form_evidence is SecurityForm.ADR_ADS
                else ListingScope.OTHER
                if issuer_structure in {IssuerStructure.ETF, IssuerStructure.ETN}
                else ListingScope.UNKNOWN
            )
            return SecurityClassificationV1(
                taxonomy_version=TAXONOMY_VERSION,
                ruleset_version=RULESET_VERSION,
                instrument_id=bar.instrument_id,
                provider=bar.source,
                as_of_date=as_of_date,
                effective_from=as_of_date,
                security_form=provider_evidence.security_form_evidence,
                issuer_structure=issuer_structure,
                listing_scope=listing_scope,
                primary_exchange=bar.primary_exchange,
                listing_country="US",
                issuer_domicile_country="UNKNOWN",
                incorporation_country="UNKNOWN",
                is_us_listed=True,
                is_us_domiciled=None,
                classification_status=provider_evidence.classification_status,
                universe_disposition=provider_evidence.universe_disposition,
                decision_reason_codes=provider_evidence.decision_flags,
                classification_method=ClassificationMethod.PROVIDER_EXPLICIT,
                evidence_grade=provider_evidence.evidence_grade,
                evidence_ids=(f"{provider_evidence.provider}:{provider_evidence.provider_type_code}",),
                quality_flags=provider_evidence.review_flags,
                observed_at=provider_evidence.observed_at,
                reviewed_at=provider_evidence.observed_at,
                ingested_at=provider_evidence.ingested_at,
            )
        if bar.instrument_type is InstrumentType.ETF:
            return SecurityClassificationV1(
                taxonomy_version=TAXONOMY_VERSION,
                ruleset_version=RULESET_VERSION,
                instrument_id=bar.instrument_id,
                provider=bar.source,
                as_of_date=as_of_date,
                effective_from=as_of_date,
                security_form=SecurityForm.FUND_SHARE,
                issuer_structure=IssuerStructure.ETF,
                listing_scope=ListingScope.OTHER,
                primary_exchange=bar.primary_exchange,
                listing_country="US",
                issuer_domicile_country="UNKNOWN",
                incorporation_country="UNKNOWN",
                is_us_listed=True,
                is_us_domiciled=None,
                classification_status=ClassificationStatus.EXCLUDED_RESOLVED,
                universe_disposition=UniverseDisposition.EXCLUDED,
                decision_reason_codes=("canonical_etf_type",),
                classification_method=ClassificationMethod.PROVIDER_EXPLICIT,
                evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,
                evidence_ids=("canonical:instrument_type=etf",),
                quality_flags=(),
                observed_at=now,
                reviewed_at=now,
                ingested_at=now,
            )
        review_flags = _name_review_flags(bar.name)
        heuristic = bool(review_flags)
        return SecurityClassificationV1(
            taxonomy_version=TAXONOMY_VERSION,
            ruleset_version=RULESET_VERSION,
            instrument_id=bar.instrument_id,
            provider=bar.source,
            as_of_date=as_of_date,
            effective_from=as_of_date,
            security_form=SecurityForm.UNKNOWN,
            issuer_structure=IssuerStructure.UNKNOWN,
            listing_scope=ListingScope.UNKNOWN,
            primary_exchange=bar.primary_exchange,
            listing_country="US",
            issuer_domicile_country="UNKNOWN",
            incorporation_country="UNKNOWN",
            is_us_listed=True,
            is_us_domiciled=None,
            classification_status=ClassificationStatus.UNKNOWN,
            universe_disposition=UniverseDisposition.QUARANTINE,
            decision_reason_codes=("insufficient_persisted_classification_evidence",),
            classification_method=(
                ClassificationMethod.HEURISTIC_REVIEW_FLAG if heuristic else ClassificationMethod.INSUFFICIENT_EVIDENCE
            ),
            evidence_grade=EvidenceGrade.HEURISTIC_FLAG_ONLY if heuristic else EvidenceGrade.INSUFFICIENT,
            evidence_ids=(),
            quality_flags=review_flags,
            observed_at=now,
            reviewed_at=now,
            ingested_at=now,
        )


def _apply_eligibility_funnel(
    classification_eligible: set[UUID],
    current: dict[UUID, EodMarketBarReadModel],
    previous: dict[UUID, EodMarketBarReadModel],
) -> tuple[set[UUID], EligibilityFunnel]:
    exchange = {item for item in classification_eligible if current[item].primary_exchange in SUPPORTED_EXCHANGES}
    both = exchange & set(current) & set(previous)
    price = {item for item in both if previous[item].close >= MINIMUM_PREVIOUS_CLOSE}
    liquid = {
        item
        for item in price
        if previous[item].close * previous[item].volume >= MINIMUM_PREVIOUS_DOLLAR_VOLUME
    }
    quality = {
        item
        for item in liquid
        if not MATERIAL_QUALITY_FLAGS.intersection(current[item].quality_flags)
        and not MATERIAL_QUALITY_FLAGS.intersection(previous[item].quality_flags)
    }
    counts = [len(classification_eligible), len(exchange), len(both), len(price), len(liquid), len(quality), len(quality)]
    if counts != sorted(counts, reverse=True):
        raise ValueError("eligibility funnel must be non-increasing")
    return quality, EligibilityFunnel(*counts)


def _passes_legacy_default(current: EodMarketBarReadModel, previous: EodMarketBarReadModel) -> bool:
    return (
        current.instrument_type is InstrumentType.COMMON_STOCK
        and current.primary_exchange in SUPPORTED_EXCHANGES
        and previous.close >= MINIMUM_PREVIOUS_CLOSE
        and previous.close * previous.volume >= MINIMUM_PREVIOUS_DOLLAR_VOLUME
    )


def _name_review_flags(name: str) -> tuple[str, ...]:
    upper = name.upper()
    return tuple(f"name_review_flag:{term.lower()}" for term in REVIEW_NAME_TERMS if term in upper)


def _unique_by_id(rows: Iterable[EodMarketBarReadModel]) -> dict[UUID, EodMarketBarReadModel]:
    result: dict[UUID, EodMarketBarReadModel] = {}
    for row in rows:
        if row.instrument_id in result:
            raise ValueError("duplicate instrument_id")
        result[row.instrument_id] = row
    return result


def _single_session_date(rows: tuple[EodMarketBarReadModel, ...]) -> date:
    values = {row.session_date for row in rows}
    if len(values) != 1:
        raise ValueError("rows must contain one session date")
    return next(iter(values))


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_audit_summary(audit: SecurityClassificationAudit) -> dict[str, object]:
    """Return aggregate-only output suitable for a non-sensitive audit report."""

    return {
        "as_of_date": audit.as_of_date.isoformat(),
        "previous_session_date": audit.previous_session_date.isoformat(),
        "raw_comparable_count": audit.raw_comparable_count,
        "legacy_default_count": audit.legacy_default_count,
        "candidate_core_count": len(audit.candidate_core_ids),
        "candidate_broad_count": len(audit.candidate_broad_ids),
        "security_form": audit.distribution("security_form"),
        "issuer_structure": audit.distribution("issuer_structure"),
        "listing_scope": audit.distribution("listing_scope"),
        "classification_status": audit.distribution("classification_status"),
        "evidence_grade": audit.distribution("evidence_grade"),
        "universe_disposition": audit.distribution("universe_disposition"),
        "core_funnel": asdict(audit.core_funnel),
        "broad_funnel": asdict(audit.broad_funnel),
        "taxonomy_fingerprint": audit.taxonomy_fingerprint,
        "ruleset_fingerprint": audit.ruleset_fingerprint,
    }
