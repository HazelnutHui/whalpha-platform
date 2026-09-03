"""Bounded Massive security-type evidence ingestion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qsl, urlparse
from uuid import UUID

import pyarrow.parquet as pq

from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus,
    EvidenceGrade,
    FailedSecurityEvidenceDiagnosticV1,
    ProviderInstrumentSecurityEvidenceV1,
    ProviderObservationStatus,
    ProviderSecurityObservationV1,
    ProviderSecurityTypeCatalogV1,
    SanitizedObservationSummaryV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.persistence.parquet.instrument_master_snapshot import (
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    _identity_table_to_rows,
    _resolver_table_to_rows,
    records_fingerprint,
)
from tip_api.persistence.parquet.security_evidence import (
    ParquetSecurityEvidenceRepository,
    write_failed_diagnostic,
)
from tip_api.persistence.security_evidence import SecurityEvidencePersistenceError
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.credential import MassiveCredentialFileError, load_massive_provider_config_from_file
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveParamValue,
    MassiveTransportError,
    MassiveUrllibTransport,
)

APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
TICKER_TYPES_PATH = "/v3/reference/tickers/types"
ALL_TICKERS_PATH = "/v3/reference/tickers"
MAX_ALL_TICKER_PAGES = 15
MAX_TOTAL_REQUESTS = 16
MINIMUM_RAW_RECORDS = 5000
MINIMUM_JOIN_RATIO = 0.999

EXPLICIT_FORMS: dict[str, SecurityForm] = {
    "CS": SecurityForm.COMMON_SHARE,
    "COMMON_STOCK": SecurityForm.COMMON_SHARE,
    "ADRC": SecurityForm.ADR_ADS,
    "ADRP": SecurityForm.DEPOSITARY_PREFERRED,
    "ADRR": SecurityForm.RIGHT,
    "PFD": SecurityForm.PREFERRED_SHARE,
    "PREF": SecurityForm.PREFERRED_SHARE,
    "PREFERRED": SecurityForm.PREFERRED_SHARE,
    "WARRANT": SecurityForm.WARRANT,
    "WRT": SecurityForm.WARRANT,
    "RIGHT": SecurityForm.RIGHT,
    "RIGHTS": SecurityForm.RIGHT,
    "UNIT": SecurityForm.UNIT,
    "ETF": SecurityForm.FUND_SHARE,
    "ETN": SecurityForm.DEBT,
    "ETS": SecurityForm.DEBT,
    "FUND": SecurityForm.FUND_SHARE,
    "CEF": SecurityForm.FUND_SHARE,
    "MF": SecurityForm.FUND_SHARE,
    "MMF": SecurityForm.FUND_SHARE,
    "BOND": SecurityForm.DEBT,
    "STRUCT": SecurityForm.STRUCTURED_PRODUCT,
    "SP": SecurityForm.STRUCTURED_PRODUCT,
}
# Catalog-known codes that are outside the supported equity Universe but whose
# provider label is not specific enough to infer a canonical SecurityForm.
KNOWN_UNSUPPORTED_CODES = frozenset({"ETV"})
EXCLUDED_CODES = (frozenset(EXPLICIT_FORMS) | KNOWN_UNSUPPORTED_CODES) - {
    "CS",
    "COMMON_STOCK",
    "ADRC",
}
NAME_REVIEW_TERMS = ("ACQUISITION", "DEPOSITARY", "FUND", "PREFERRED", "RIGHT", "TRUST", "UNIT", "WARRANT")


@dataclass(frozen=True, slots=True)
class IdentityReference:
    provider_ticker: str
    canonical_instrument_id: UUID | None
    resolution_status: ResolutionStatus
    share_class_figi: str | None = None
    composite_figi: str | None = None
    provider_instrument_id: str | None = None


@dataclass(frozen=True, slots=True)
class IdentityIndexes:
    share_class_figi: dict[str, tuple[IdentityReference, ...]]
    composite_figi: dict[str, tuple[IdentityReference, ...]]
    provider_instrument_id: dict[str, tuple[IdentityReference, ...]]
    ticker_observations: dict[str, tuple[IdentityReference, ...]]
    ticker_resolver: dict[str, UUID]


@dataclass(frozen=True, slots=True)
class EvidenceBuildResult:
    catalog: tuple[ProviderSecurityTypeCatalogV1, ...]
    observations: tuple[ProviderSecurityObservationV1, ...]
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...]
    request_count: int
    ticker_types_request_count: int
    all_tickers_request_count: int
    raw_record_count: int
    canonical_mapped_count: int
    expected_unjoined_count: int
    exact_duplicate_count: int
    ambiguous_count: int
    collision_count: int
    malformed_count: int
    linkage_numerator: int
    linkage_denominator: int
    business_key_conflict_count: int
    linkage_ratio: float
    type_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    quality_gate_failures: tuple[str, ...]

    @property
    def publish_ready(self) -> bool:
        return not self.quality_gate_failures

    def safe_lines(self) -> tuple[str, ...]:
        values = (
            ("operation", "massive_security_type_evidence"),
            ("as_of_date", self.observations[0].as_of_date.isoformat() if self.observations else ""),
            ("ticker_types_endpoint", TICKER_TYPES_PATH),
            ("all_tickers_endpoint", ALL_TICKERS_PATH),
            ("request_count", self.request_count),
            ("retry_count", 0),
            ("catalog_count", len(self.catalog)),
            ("raw_record_count", self.raw_record_count),
            ("canonical_mapped_count", self.canonical_mapped_count),
            ("expected_unjoined_count", self.expected_unjoined_count),
            ("exact_duplicate_count", self.exact_duplicate_count),
            ("ambiguous_count", self.ambiguous_count),
            ("collision_count", self.collision_count),
            ("malformed_count", self.malformed_count),
            ("linkage_numerator", self.linkage_numerator),
            ("linkage_denominator", self.linkage_denominator),
            ("business_key_conflict_count", self.business_key_conflict_count),
            ("linkage_ratio", f"{self.linkage_ratio:.6f}"),
            ("publish_ready", str(self.publish_ready).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)),
        )
        return tuple(f"{key}={value}" for key, value in values)


@dataclass(frozen=True, slots=True)
class _Resolution:
    status: ProviderObservationStatus
    instrument_id: UUID | None
    method: str
    reasons: tuple[str, ...]


@dataclass(slots=True)
class CountingMassiveTransport:
    """Count bounded request attempts without retaining request secrets or bodies."""

    transport: MassiveHttpTransport
    request_count: int = 0
    ticker_types_request_count: int = 0
    all_tickers_request_count: int = 0

    def get_json(self, path: str, **kwargs: object) -> Mapping[str, object]:
        self.request_count += 1
        if path == TICKER_TYPES_PATH:
            self.ticker_types_request_count += 1
        elif path == ALL_TICKERS_PATH:
            self.all_tickers_request_count += 1
        else:
            raise RuntimeError("Massive security evidence requested an unapproved endpoint")
        if (
            self.request_count > MAX_TOTAL_REQUESTS
            or self.ticker_types_request_count > 1
            or self.all_tickers_request_count > MAX_ALL_TICKER_PAGES
        ):
            raise RuntimeError("Massive security evidence request ceiling exceeded")
        return self.transport.get_json(path, **kwargs)  # type: ignore[arg-type]


def fetch_security_evidence(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    as_of_date: date,
    indexes: IdentityIndexes,
    rate_limiter: FixedIntervalRateLimiter,
    observed_at: datetime,
) -> EvidenceBuildResult:
    rate_limiter.wait_before_request()
    type_response = transport.get_json(
        TICKER_TYPES_PATH,
        params={},
        api_key=config.api_key,
        timeout_seconds=config.request_timeout_seconds,
        base_url=config.base_url,
    )
    catalog = parse_ticker_type_catalog(type_response, observed_at=observed_at)
    pages = _fetch_all_tickers(
        config=config,
        transport=transport,
        as_of_date=as_of_date,
        rate_limiter=rate_limiter,
    )
    payloads = tuple(item for page in pages for item in _results(page))
    return build_instrument_evidence(
        catalog=catalog,
        payloads=payloads,
        indexes=indexes,
        as_of_date=as_of_date,
        observed_at=observed_at,
        request_count=1 + len(pages),
        all_tickers_request_count=len(pages),
    )


def parse_ticker_type_catalog(
    response: Mapping[str, object], *, observed_at: datetime
) -> tuple[ProviderSecurityTypeCatalogV1, ...]:
    raw = response.get("results")
    items = [raw] if isinstance(raw, Mapping) else raw
    if not isinstance(items, list) or not items:
        raise RuntimeError("Massive ticker type catalog is empty or malformed")
    records = []
    for item in items:
        if not isinstance(item, Mapping):
            raise RuntimeError("Massive ticker type catalog item is malformed")
        code = _required(item.get("code"), "catalog code").upper()
        description = _required(item.get("description"), "catalog description")
        asset_class = _required(item.get("asset_class"), "catalog asset_class")
        locale = _required(item.get("locale"), "catalog locale")
        fingerprint = _fingerprint({"provider": MASSIVE_PROVIDER_ID, "code": code, "description": description, "asset_class": asset_class, "locale": locale, "endpoint": TICKER_TYPES_PATH})
        records.append(
            ProviderSecurityTypeCatalogV1(
                provider=MASSIVE_PROVIDER_ID,
                provider_type_code=code,
                provider_type_description=description,
                provider_asset_class=asset_class,
                provider_locale=locale,
                observed_at=observed_at,
                source_endpoint=TICKER_TYPES_PATH,
                evidence_fingerprint=fingerprint,
            )
        )
    if len({item.provider_type_code for item in records}) != len(records):
        raise RuntimeError("Massive ticker type catalog contains duplicate codes")
    return tuple(sorted(records, key=lambda item: item.provider_type_code))


def build_instrument_evidence(
    *,
    catalog: tuple[ProviderSecurityTypeCatalogV1, ...],
    payloads: tuple[Mapping[str, object], ...],
    indexes: IdentityIndexes,
    as_of_date: date,
    observed_at: datetime,
    request_count: int,
    all_tickers_request_count: int,
) -> EvidenceBuildResult:
    catalog_by_code = {item.provider_type_code: item for item in catalog}
    grouped_payloads: dict[tuple[object, ...], tuple[Mapping[str, object], int]] = {}
    type_counts: Counter[str] = Counter()
    for payload in payloads:
        signature = _provider_observation_signature(payload)
        current = grouped_payloads.get(signature)
        grouped_payloads[signature] = (payload, 1 if current is None else current[1] + 1)

    observations: list[ProviderSecurityObservationV1] = []
    exact_duplicate = 0
    for signature in sorted(grouped_payloads, key=lambda value: json.dumps(value, separators=(",", ":"))):
        payload, occurrence_count = grouped_payloads[signature]
        exact_duplicate += occurrence_count - 1
        type_code = _optional_upper(payload.get("type"))
        if type_code:
            type_counts[type_code] += occurrence_count
        resolution = _resolve_observation(payload, indexes)
        observations.append(
            _to_observation(
                payload,
                resolution,
                catalog_by_code,
                as_of_date,
                observed_at,
                occurrence_count,
            )
        )

    evidence_by_key: dict[tuple[UUID, date, str, str, str], list[ProviderInstrumentSecurityEvidenceV1]] = defaultdict(list)
    for observation in observations:
        if observation.observation_status is ProviderObservationStatus.CANONICAL_MAPPED:
            candidate = _observation_to_evidence(observation)
            evidence_by_key[candidate.business_key].append(candidate)

    conflict_observation_ids: set[str] = set()
    business_conflicts = 0
    evidence: list[ProviderInstrumentSecurityEvidenceV1] = []
    for key in sorted(evidence_by_key, key=lambda item: tuple(str(value) for value in item)):
        values = evidence_by_key[key]
        signatures = {_canonical_evidence_signature(item) for item in values}
        if len(signatures) > 1:
            business_conflicts += len(values)
            conflict_observation_ids.update(
                observation_id for value in values for observation_id in value.provider_observation_ids
            )
            continue
        selected = min(values, key=lambda item: (item.provider_ticker, item.provider_observation_ids))
        evidence.append(
            selected.model_copy(
                update={
                    "provider_observation_ids": tuple(
                        sorted({item for value in values for item in value.provider_observation_ids})
                    )
                }
            )
        )

    if conflict_observation_ids:
        observations = [
            observation.model_copy(
                update={
                    "instrument_id": None,
                    "observation_status": ProviderObservationStatus.AMBIGUOUS,
                    "resolution_method": "unresolved",
                    "reason_codes": tuple(sorted(set(observation.reason_codes) | {"canonical_evidence_conflict"})),
                }
            )
            if observation.provider_observation_id in conflict_observation_ids
            else observation
            for observation in observations
        ]

    observations_tuple = tuple(sorted(observations, key=lambda item: item.provider_observation_id))
    evidence_tuple = tuple(sorted(evidence, key=lambda item: (str(item.instrument_id), item.provider_ticker)))
    status_counts = Counter(item.observation_status for item in observations_tuple)
    raw_count = len(payloads)
    canonical_mapped = status_counts[ProviderObservationStatus.CANONICAL_MAPPED]
    expected_unjoined = status_counts[ProviderObservationStatus.EXPECTED_UNJOINED]
    ambiguous = status_counts[ProviderObservationStatus.AMBIGUOUS]
    collisions = status_counts[ProviderObservationStatus.COLLISION]
    malformed = status_counts[ProviderObservationStatus.MALFORMED]
    reconciled = canonical_mapped + expected_unjoined + ambiguous + collisions + malformed + exact_duplicate
    linkage_denominator = canonical_mapped + ambiguous + collisions
    linkage_ratio = canonical_mapped / linkage_denominator if linkage_denominator else 0.0
    failures = []
    if not catalog:
        failures.append("catalog_empty")
    if raw_count <= MINIMUM_RAW_RECORDS:
        failures.append("raw_record_count_below_gate")
    if request_count > MAX_TOTAL_REQUESTS or all_tickers_request_count > MAX_ALL_TICKER_PAGES:
        failures.append("request_count_above_gate")
    if collisions:
        failures.append("stable_identifier_collision_nonzero")
    if business_conflicts:
        failures.append("canonical_business_key_conflict_nonzero")
    if ambiguous:
        failures.append("ambiguous_mapping_nonzero")
    if reconciled != raw_count:
        failures.append("raw_reconciliation_failed")
    if linkage_denominator == 0 or linkage_ratio < MINIMUM_JOIN_RATIO:
        failures.append("identity_join_ratio_below_gate")
    categories = (
        ("ambiguous", ambiguous),
        ("canonical_mapped", canonical_mapped),
        ("collision", collisions),
        ("exact_duplicate", exact_duplicate),
        ("expected_unjoined", expected_unjoined),
        ("malformed", malformed),
    )
    return EvidenceBuildResult(
        catalog=catalog,
        observations=observations_tuple,
        evidence=evidence_tuple,
        request_count=request_count,
        ticker_types_request_count=1,
        all_tickers_request_count=all_tickers_request_count,
        raw_record_count=raw_count,
        canonical_mapped_count=canonical_mapped,
        expected_unjoined_count=expected_unjoined,
        exact_duplicate_count=exact_duplicate,
        ambiguous_count=ambiguous,
        collision_count=collisions,
        malformed_count=malformed,
        linkage_numerator=canonical_mapped,
        linkage_denominator=linkage_denominator,
        business_key_conflict_count=business_conflicts,
        linkage_ratio=linkage_ratio,
        type_counts=tuple(sorted(type_counts.items())),
        category_counts=categories,
        quality_gate_failures=tuple(failures),
    )


def build_failed_diagnostic(
    result: EvidenceBuildResult,
    *,
    run_id: str,
    created_at: datetime,
) -> FailedSecurityEvidenceDiagnosticV1:
    status_counts = Counter(item.observation_status.value for item in result.observations)
    conflicts = tuple(
        SanitizedObservationSummaryV1(
            provider_ticker=item.provider_ticker,
            provider_type_code=item.provider_type_code,
            observation_status=item.observation_status,
            identifier_types=tuple(
                name
                for name, value in (
                    ("share_class_figi", item.share_class_figi),
                    ("composite_figi", item.composite_figi),
                    ("provider_stable_id", item.provider_instrument_id),
                )
                if value is not None
            ),
            instrument_id=item.instrument_id,
            reason_codes=item.reason_codes,
        )
        for item in result.observations
        if item.observation_status in {ProviderObservationStatus.AMBIGUOUS, ProviderObservationStatus.COLLISION}
    )
    reconciled = sum(dict(result.category_counts).values()) == result.raw_record_count
    return FailedSecurityEvidenceDiagnosticV1(
        run_id=run_id,
        as_of_date=(result.observations[0].as_of_date if result.observations else date(2026, 8, 14)),
        provider=MASSIVE_PROVIDER_ID,
        endpoint_names=(TICKER_TYPES_PATH, ALL_TICKERS_PATH),
        request_count=result.request_count,
        ticker_types_request_count=result.ticker_types_request_count,
        all_tickers_request_count=result.all_tickers_request_count,
        statistics_complete=True,
        raw_observation_count=result.raw_record_count,
        status_counts=dict(sorted(status_counts.items())),
        linkage_numerator=result.linkage_numerator,
        linkage_denominator=result.linkage_denominator,
        linkage_ratio=f"{result.linkage_ratio:.6f}",
        exact_duplicate_count=result.exact_duplicate_count,
        ambiguous_count=result.ambiguous_count,
        collision_count=result.collision_count,
        business_key_conflict_count=result.business_key_conflict_count,
        reconciliation_status="passed" if reconciled else "failed",
        failure_reasons=result.quality_gate_failures,
        conflicting_observations=conflicts,
        created_at=created_at,
    )


def build_runtime_failed_diagnostic(
    *,
    as_of_date: date,
    run_id: str,
    created_at: datetime,
    transport: CountingMassiveTransport,
    failure_reason: str,
) -> FailedSecurityEvidenceDiagnosticV1:
    """Build a safe diagnostic when a request fails before reconciliation exists."""

    return FailedSecurityEvidenceDiagnosticV1(
        run_id=run_id,
        as_of_date=as_of_date,
        provider=MASSIVE_PROVIDER_ID,
        endpoint_names=(TICKER_TYPES_PATH, ALL_TICKERS_PATH),
        request_count=transport.request_count,
        ticker_types_request_count=transport.ticker_types_request_count,
        all_tickers_request_count=transport.all_tickers_request_count,
        statistics_complete=False,
        raw_observation_count=None,
        status_counts={},
        linkage_numerator=None,
        linkage_denominator=None,
        linkage_ratio=None,
        exact_duplicate_count=None,
        ambiguous_count=None,
        collision_count=None,
        business_key_conflict_count=None,
        reconciliation_status="unavailable",
        failure_reasons=(failure_reason,),
        conflicting_observations=(),
        created_at=created_at,
    )


def _to_observation(
    payload: Mapping[str, object],
    resolution: _Resolution,
    catalog: dict[str, ProviderSecurityTypeCatalogV1],
    as_of_date: date,
    observed_at: datetime,
    occurrence_count: int,
) -> ProviderSecurityObservationV1:
    ticker = _optional_upper(payload.get("ticker"))
    code = _optional_upper(payload.get("type"))
    catalog_item = catalog.get(code)
    form = EXPLICIT_FORMS.get(code or "", SecurityForm.UNKNOWN)
    flags = list(resolution.reasons)
    review_flags = list(_name_review_flags(_optional(payload.get("name"))))
    if resolution.status is ProviderObservationStatus.MALFORMED:
        description = catalog_item.provider_type_description if catalog_item else None
        grade = EvidenceGrade.INSUFFICIENT
    elif catalog_item is None:
        description = "Unknown provider type code" if code else None
        status = ClassificationStatus.UNKNOWN
        disposition = UniverseDisposition.QUARANTINE
        flags.append("provider_type_code_not_in_catalog")
        grade = EvidenceGrade.INSUFFICIENT
    elif code in EXCLUDED_CODES:
        description = catalog_item.provider_type_description
        status = ClassificationStatus.EXCLUDED_RESOLVED
        disposition = UniverseDisposition.EXCLUDED
        flags.append("provider_security_form_excluded")
        grade = EvidenceGrade.PROVIDER_EXPLICIT
        if code in {"FUND", "CEF", "MF", "MMF"}:
            review_flags.append("fund_form_does_not_resolve_fund_subtype")
    else:
        description = catalog_item.provider_type_description
        status = ClassificationStatus.UNKNOWN
        disposition = UniverseDisposition.QUARANTINE
        grade = EvidenceGrade.PROVIDER_EXPLICIT
        flags.append("provider_security_form_only")
        if code in {"CS", "COMMON_STOCK"}:
            review_flags.extend(("issuer_structure_unresolved", "issuer_domicile_unresolved"))
        elif code == "ADRC":
            review_flags.append("foreign_operating_status_unresolved")
        elif form is SecurityForm.UNKNOWN:
            review_flags.append("provider_type_requires_review")
    return ProviderSecurityObservationV1(
        provider_observation_id=_observation_id(payload, as_of_date),
        as_of_date=as_of_date,
        instrument_id=resolution.instrument_id,
        provider=MASSIVE_PROVIDER_ID,
        provider_ticker=ticker,
        provider_type_code=code,
        provider_type_description=description,
        primary_exchange=_optional_upper(payload.get("primary_exchange")),
        provider_instrument_id=_optional_upper(payload.get("id")),
        cik=_optional(payload.get("cik")),
        composite_figi=_optional_upper(payload.get("composite_figi")),
        share_class_figi=_optional_upper(payload.get("share_class_figi")),
        security_form_evidence=form,
        evidence_source=ALL_TICKERS_PATH,
        evidence_grade=grade,
        observation_status=resolution.status,
        resolution_method=resolution.method,
        reason_codes=tuple(flags),
        review_flags=tuple(sorted(set(review_flags))),
        occurrence_count=occurrence_count,
        observed_at=observed_at,
        ingested_at=observed_at,
    )


def _observation_to_evidence(observation: ProviderSecurityObservationV1) -> ProviderInstrumentSecurityEvidenceV1:
    if observation.instrument_id is None or observation.provider_ticker is None or observation.provider_type_code is None or observation.provider_type_description is None or observation.primary_exchange is None:
        raise RuntimeError("mapped observation is missing canonical evidence fields")
    code = observation.provider_type_code
    if code in EXCLUDED_CODES:
        status = ClassificationStatus.EXCLUDED_RESOLVED
        disposition = UniverseDisposition.EXCLUDED
    else:
        status = ClassificationStatus.UNKNOWN
        disposition = UniverseDisposition.QUARANTINE
    return ProviderInstrumentSecurityEvidenceV1(
        as_of_date=observation.as_of_date,
        instrument_id=observation.instrument_id,
        provider=observation.provider,
        provider_ticker=observation.provider_ticker,
        provider_type_code=code,
        provider_type_description=observation.provider_type_description,
        primary_exchange=observation.primary_exchange,
        provider_instrument_id=observation.provider_instrument_id,
        cik=observation.cik,
        composite_figi=observation.composite_figi,
        share_class_figi=observation.share_class_figi,
        security_form_evidence=observation.security_form_evidence,
        evidence_source=observation.evidence_source,
        evidence_grade=observation.evidence_grade,
        classification_status=status,
        universe_disposition=disposition,
        decision_flags=observation.reason_codes,
        review_flags=observation.review_flags,
        provider_observation_ids=(observation.provider_observation_id,),
        observed_at=observation.observed_at,
        ingested_at=observation.ingested_at,
    )


def _resolve_observation(payload: Mapping[str, object], indexes: IdentityIndexes) -> _Resolution:
    ticker = _optional_upper(payload.get("ticker"))
    type_code = _optional_upper(payload.get("type"))
    exchange = _optional_upper(payload.get("primary_exchange"))
    if ticker is None or type_code is None or exchange is None:
        return _Resolution(ProviderObservationStatus.MALFORMED, None, "unresolved", ("required_field_missing",))

    identifier_values = (
        ("share_class_figi", _optional_upper(payload.get("share_class_figi")), indexes.share_class_figi),
        ("composite_figi", _optional_upper(payload.get("composite_figi")), indexes.composite_figi),
        ("provider_stable_id", _optional_upper(payload.get("id")), indexes.provider_instrument_id),
    )
    supplied_identifier = False
    for method, value, index in identifier_values:
        if value is None:
            continue
        supplied_identifier = True
        references = index.get(value, ())
        if not references:
            continue
        canonical_ids = {
            item.canonical_instrument_id
            for item in references
            if item.resolution_status is ResolutionStatus.RESOLVED and item.canonical_instrument_id is not None
        }
        if len(canonical_ids) > 1:
            return _Resolution(ProviderObservationStatus.COLLISION, None, "unresolved", (f"{method}_collision",))
        if len(references) > 1:
            return _Resolution(ProviderObservationStatus.COLLISION, None, "unresolved", (f"{method}_not_unique",))
        if len(canonical_ids) == 1:
            return _Resolution(
                ProviderObservationStatus.CANONICAL_MAPPED,
                next(iter(canonical_ids)),
                method,
                (f"{method}_join",),
            )
        return _Resolution(
            ProviderObservationStatus.EXPECTED_UNJOINED,
            None,
            "unresolved",
            (f"{method}_belongs_to_noncanonical_identity",),
        )

    ticker_references = indexes.ticker_observations.get(ticker, ())
    resolved_ids = {
        item.canonical_instrument_id
        for item in ticker_references
        if item.resolution_status is ResolutionStatus.RESOLVED and item.canonical_instrument_id is not None
    }
    if len(resolved_ids) > 1:
        return _Resolution(ProviderObservationStatus.AMBIGUOUS, None, "unresolved", ("ticker_maps_multiple_canonical_instruments",))
    if not ticker_references:
        return _Resolution(ProviderObservationStatus.AMBIGUOUS, None, "unresolved", ("identity_snapshot_no_match",))
    if len(ticker_references) != 1:
        return _Resolution(ProviderObservationStatus.EXPECTED_UNJOINED, None, "unresolved", ("duplicate_ticker_requires_stable_identifier",))
    reference = ticker_references[0]
    resolver_id = indexes.ticker_resolver.get(ticker)
    if reference.resolution_status is not ResolutionStatus.RESOLVED or reference.canonical_instrument_id is None:
        return _Resolution(ProviderObservationStatus.EXPECTED_UNJOINED, None, "unresolved", ("identity_not_canonical_eligible",))
    if resolver_id is None or resolver_id != reference.canonical_instrument_id:
        return _Resolution(ProviderObservationStatus.AMBIGUOUS, None, "unresolved", ("ticker_resolver_conflict",))
    reason = "point_in_time_ticker_resolver_join"
    if supplied_identifier:
        reason = "unmatched_identifier_then_unique_ticker_resolver_join"
    return _Resolution(ProviderObservationStatus.CANONICAL_MAPPED, resolver_id, "point_in_time_ticker_resolver", (reason,))


def _provider_observation_signature(payload: Mapping[str, object]) -> tuple[object, ...]:
    return (
        _optional_upper(payload.get("ticker")),
        _optional_upper(payload.get("type")),
        _optional_upper(payload.get("primary_exchange")),
        _optional_upper(payload.get("id")),
        _optional_upper(payload.get("share_class_figi")),
        _optional_upper(payload.get("composite_figi")),
        _optional(payload.get("cik")),
        _optional(payload.get("name")),
    )


def _observation_id(payload: Mapping[str, object], as_of_date: date) -> str:
    return _fingerprint(
        {
            "provider": MASSIVE_PROVIDER_ID,
            "as_of_date": as_of_date.isoformat(),
            "observation": _provider_observation_signature(payload),
        }
    )


def _canonical_evidence_signature(value: ProviderInstrumentSecurityEvidenceV1) -> tuple[object, ...]:
    return (
        value.provider_type_code,
        value.provider_type_description,
        value.security_form_evidence.value,
        value.classification_status.value,
        value.universe_disposition.value,
    )


def load_identity_indexes(root: Path, *, as_of_date: date) -> IdentityIndexes:
    provider = MASSIVE_PROVIDER_ID
    snapshot_path = root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={as_of_date.isoformat()}" / "manifest.json"
    snapshot = _read_json(snapshot_path)
    if snapshot.get("completion_status") != "completed" or snapshot.get("as_of_date") != as_of_date.isoformat() or snapshot.get("provider_id") != provider:
        raise RuntimeError("accepted identity snapshot is unavailable")
    identity_path = root / "market-data" / "provider-instrument-identity" / "schema_version=1" / f"provider={provider}" / f"as_of_date={as_of_date.isoformat()}"
    resolver_path = root / "market-data" / "provider-ticker-resolver" / "schema_version=1" / f"provider={provider}" / f"as_of_date={as_of_date.isoformat()}"
    identity_table = _validated_snapshot_table(
        identity_path,
        PROVIDER_IDENTITY_ARROW_SCHEMA,
        int(snapshot["identity_count"]),
        str(snapshot["identity_content_sha256"]),
        _identity_table_to_rows,
    )
    resolver_table = _validated_snapshot_table(
        resolver_path,
        PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
        int(snapshot["resolver_count"]),
        str(snapshot["resolver_content_sha256"]),
        _resolver_table_to_rows,
    )
    share_class_figi: dict[str, list[IdentityReference]] = defaultdict(list)
    composite_figi: dict[str, list[IdentityReference]] = defaultdict(list)
    provider_instrument_id: dict[str, list[IdentityReference]] = defaultdict(list)
    ticker_observations: dict[str, list[IdentityReference]] = defaultdict(list)
    for row in identity_table.to_pylist():
        canonical = row.get("canonical_instrument_id")
        reference = IdentityReference(
            provider_ticker=str(row["provider_ticker"]).upper(),
            canonical_instrument_id=UUID(str(canonical)) if canonical is not None else None,
            resolution_status=ResolutionStatus(str(row["resolution_status"])),
            share_class_figi=_optional_upper(row.get("share_class_figi")),
            composite_figi=_optional_upper(row.get("composite_figi")),
            provider_instrument_id=_optional_upper(row.get("provider_instrument_id")),
        )
        ticker_observations[reference.provider_ticker].append(reference)
        for value, index in (
            (reference.share_class_figi, share_class_figi),
            (reference.composite_figi, composite_figi),
            (reference.provider_instrument_id, provider_instrument_id),
        ):
            if value:
                index[value].append(reference)
    ticker_resolver = {
        str(row["provider_ticker"]).upper(): UUID(str(row["canonical_instrument_id"]))
        for row in resolver_table.to_pylist()
    }
    sort_key = lambda item: (
        item.provider_ticker,
        item.resolution_status.value,
        str(item.canonical_instrument_id or ""),
        item.share_class_figi or "",
        item.composite_figi or "",
        item.provider_instrument_id or "",
    )
    return IdentityIndexes(
        {key: tuple(sorted(value, key=sort_key)) for key, value in share_class_figi.items()},
        {key: tuple(sorted(value, key=sort_key)) for key, value in composite_figi.items()},
        {key: tuple(sorted(value, key=sort_key)) for key, value in provider_instrument_id.items()},
        {key: tuple(sorted(value, key=sort_key)) for key, value in ticker_observations.items()},
        ticker_resolver,
    )


def _validated_snapshot_table(path: Path, schema: object, count: int, fingerprint: str, converter: object):
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("accepted identity partition is unavailable")
    table = pq.ParquetFile(path / "part-00000.parquet").read()
    if not table.schema.equals(schema, check_metadata=False) or table.num_rows != count:
        raise RuntimeError("accepted identity partition schema/count mismatch")
    if records_fingerprint(converter(table)) != fingerprint:
        raise RuntimeError("accepted identity partition fingerprint mismatch")
    return table


def _fetch_all_tickers(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    as_of_date: date,
    rate_limiter: FixedIntervalRateLimiter,
) -> tuple[Mapping[str, object], ...]:
    path = ALL_TICKERS_PATH
    params: dict[str, MassiveParamValue] = {"market": "stocks", "active": True, "date": as_of_date.isoformat(), "limit": 1000, "sort": "ticker", "order": "asc"}
    pages = []
    seen = set()
    for _ in range(MAX_ALL_TICKER_PAGES):
        key = (path, tuple(sorted(params.items())))
        if key in seen:
            raise RuntimeError("Massive All Tickers pagination loop detected")
        seen.add(key)
        rate_limiter.wait_before_request()
        page = transport.get_json(path, params=params, api_key=config.api_key, timeout_seconds=config.request_timeout_seconds, base_url=config.base_url)
        _results(page)
        pages.append(page)
        next_url = page.get("next_url")
        if next_url is None:
            return tuple(pages)
        path, params = _next_page(next_url, config.base_url)
    raise RuntimeError("Massive All Tickers page limit exceeded")


def _next_page(value: object, base_url: str) -> tuple[str, dict[str, MassiveParamValue]]:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("Massive All Tickers next_url is invalid")
    parsed, base = urlparse(value), urlparse(base_url)
    if parsed.netloc and parsed.netloc != base.netloc:
        raise RuntimeError("Massive All Tickers pagination host changed")
    if parsed.path != ALL_TICKERS_PATH:
        raise RuntimeError("Massive All Tickers pagination path changed")
    params = {key: item for key, item in parse_qsl(parsed.query) if key.lower() != "apikey"}
    return parsed.path, params


def _results(page: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = page.get("results")
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise RuntimeError("Massive All Tickers results are malformed")
    return tuple(value)


def _name_review_flags(name: str | None) -> tuple[str, ...]:
    upper = (name or "").upper()
    return tuple(f"name_review_flag:{term.lower()}" for term in NAME_REVIEW_TERMS if term in upper)


def _required(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Massive evidence missing {label}")
    return value.strip()


def _optional(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_upper(value: object) -> str | None:
    result = _optional(value)
    return result.upper() if result else None


def _fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("accepted identity manifest is unavailable")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("accepted identity manifest is malformed")
    return value


def target_partitions(root: Path, *, as_of_date: date, observed_date: date) -> tuple[Path, Path, Path, Path]:
    base = root / "market-data"
    return (
        base / "provider-security-type-catalog" / "schema_version=1" / f"provider={MASSIVE_PROVIDER_ID}" / f"observed_date={observed_date.isoformat()}",
        base / "provider-security-observation" / "schema_version=1" / f"provider={MASSIVE_PROVIDER_ID}" / f"as_of_date={as_of_date.isoformat()}",
        base / "provider-instrument-security-evidence" / "schema_version=1" / f"provider={MASSIVE_PROVIDER_ID}" / f"as_of_date={as_of_date.isoformat()}",
        base / "snapshots" / "provider-security-evidence" / f"as_of_date={as_of_date.isoformat()}",
    )


def parse_args(argv: list[str]) -> tuple[date, Path]:
    parser = argparse.ArgumentParser(prog="ingest-massive-security-type-evidence.sh")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args(argv)
    parsed = date.fromisoformat(args.as_of_date)
    root = Path(args.data_root)
    if parsed != date(2026, 8, 14):
        raise ValueError("Phase B1 permits only as-of-date 2026-08-14")
    if root != APPROVED_DATA_ROOT:
        raise ValueError("data root is not approved")
    return parsed, root


def main(argv: list[str] | None = None) -> int:
    try:
        as_of_date, root = parse_args(sys.argv[1:] if argv is None else argv)
    except (SystemExit, ValueError) as exc:
        if not isinstance(exc, SystemExit):
            print(f"error={exc}", file=sys.stderr)
            return 2
        return int(exc.code) if isinstance(exc.code, int) else 2
    observed_at = datetime.now(UTC)
    targets = target_partitions(root, as_of_date=as_of_date, observed_date=observed_at.date())
    if any(path.exists() or path.is_symlink() for path in targets):
        print("error=security evidence target already exists", file=sys.stderr)
        return 1
    run_id = f"phase-b1-{as_of_date.isoformat()}-{observed_at.strftime('%Y%m%dT%H%M%SZ')}"
    counting_transport = CountingMassiveTransport(MassiveUrllibTransport())
    diagnostic_written = False
    try:
        indexes = load_identity_indexes(root, as_of_date=as_of_date)
        config = load_massive_provider_config_from_file()
        result = fetch_security_evidence(
            config=config,
            transport=counting_transport,
            as_of_date=as_of_date,
            indexes=indexes,
            rate_limiter=FixedIntervalRateLimiter(),
            observed_at=observed_at,
        )
        for line in result.safe_lines():
            print(line)
        if not result.publish_ready:
            diagnostic = build_failed_diagnostic(result, run_id=run_id, created_at=observed_at)
            diagnostic_write = write_failed_diagnostic(root, diagnostic)
            diagnostic_written = True
            print(f"failed_diagnostic_status={diagnostic_write.status}")
            print(f"failed_diagnostic_run_id={diagnostic_write.run_id}")
            return 1
        repository = ParquetSecurityEvidenceRepository(root)
        catalog_write = repository.publish_catalog(result.catalog, observed_date=observed_at.date(), provider_id=MASSIVE_PROVIDER_ID)
        quality = {
            "request_count": result.request_count,
            "retry_count": 0,
            "raw_record_count": result.raw_record_count,
            "canonical_mapped_count": result.canonical_mapped_count,
            "expected_unjoined_count": result.expected_unjoined_count,
            "exact_duplicate_count": result.exact_duplicate_count,
            "ambiguous_count": result.ambiguous_count,
            "collision_count": result.collision_count,
            "malformed_count": result.malformed_count,
            "linkage_numerator": result.linkage_numerator,
            "linkage_denominator": result.linkage_denominator,
            "canonical_business_key_conflict_count": result.business_key_conflict_count,
            "identity_join_ratio": result.linkage_ratio,
            "type_counts": dict(result.type_counts),
        }
        observation_write = repository.publish_observations(
            result.observations,
            as_of_date=as_of_date,
            provider_id=MASSIVE_PROVIDER_ID,
            catalog_content_sha256=catalog_write.content_sha256,
            quality_summary=quality,
        )
        evidence_write = repository.publish_instrument_evidence(
            result.evidence,
            as_of_date=as_of_date,
            provider_id=MASSIVE_PROVIDER_ID,
            catalog_content_sha256=catalog_write.content_sha256,
            quality_summary=quality,
        )
        snapshot_write = repository.publish_logical_snapshot(
            as_of_date=as_of_date,
            observed_date=observed_at.date(),
            provider_id=MASSIVE_PROVIDER_ID,
            created_at=observed_at,
            request_count=result.request_count,
            catalog=catalog_write,
            observations=observation_write,
            evidence=evidence_write,
        )
        print(f"catalog_status={catalog_write.status}")
        print(f"catalog_content_sha256={catalog_write.content_sha256}")
        print(f"observation_status={observation_write.status}")
        print(f"observation_content_sha256={observation_write.content_sha256}")
        print(f"evidence_status={evidence_write.status}")
        print(f"evidence_content_sha256={evidence_write.content_sha256}")
        print(f"logical_snapshot_status={snapshot_write.status}")
        print(f"logical_snapshot_content_sha256={snapshot_write.logical_content_sha256}")
        return 0
    except (MassiveCredentialFileError, MassiveTransportError, SecurityEvidencePersistenceError, RuntimeError, ValueError) as exc:
        failure_reason = _safe_failure_reason(exc)
        if not diagnostic_written:
            try:
                diagnostic = build_runtime_failed_diagnostic(
                    as_of_date=as_of_date,
                    run_id=run_id,
                    created_at=observed_at,
                    transport=counting_transport,
                    failure_reason=failure_reason,
                )
                diagnostic_write = write_failed_diagnostic(root, diagnostic)
                print(f"failed_diagnostic_status={diagnostic_write.status}")
                print(f"failed_diagnostic_run_id={diagnostic_write.run_id}")
            except SecurityEvidencePersistenceError:
                print("failed_diagnostic_status=write_failed", file=sys.stderr)
        print(f"error={failure_reason}", file=sys.stderr)
        return 1


def _safe_failure_reason(exc: Exception) -> str:
    if isinstance(exc, MassiveCredentialFileError):
        return "credential_boundary_failure"
    if isinstance(exc, MassiveTransportError):
        status = getattr(exc, "status_code", None)
        return f"provider_http_{status}" if isinstance(status, int) else "provider_transport_failure"
    if isinstance(exc, SecurityEvidencePersistenceError):
        return "evidence_persistence_failure"
    message = str(exc).lower()
    if "pagination" in message:
        return "pagination_validation_failure"
    if "request ceiling" in message or "page limit" in message:
        return "request_ceiling_failure"
    return "evidence_runtime_failure"


if __name__ == "__main__":
    raise SystemExit(main())
