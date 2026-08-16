"""Bounded Massive security-type evidence ingestion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
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
    ProviderInstrumentSecurityEvidenceV1,
    ProviderSecurityTypeCatalogV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    _identity_table_to_rows,
    _resolver_table_to_rows,
    records_fingerprint,
)
from tip_api.persistence.parquet.security_evidence import ParquetSecurityEvidenceRepository
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
MINIMUM_JOIN_RATIO = 0.99

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
EXCLUDED_CODES = frozenset(EXPLICIT_FORMS) - {"CS", "COMMON_STOCK", "ADRC"}
NAME_REVIEW_TERMS = ("ACQUISITION", "DEPOSITARY", "FUND", "PREFERRED", "RIGHT", "TRUST", "UNIT", "WARRANT")


@dataclass(frozen=True, slots=True)
class IdentityIndexes:
    stable: dict[tuple[str, str], frozenset[UUID]]
    ticker: dict[str, UUID]
    known_stable: frozenset[tuple[str, str]] = frozenset()
    known_tickers: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class EvidenceBuildResult:
    catalog: tuple[ProviderSecurityTypeCatalogV1, ...]
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...]
    request_count: int
    ticker_types_request_count: int
    all_tickers_request_count: int
    raw_record_count: int
    uniquely_mapped_count: int
    exact_duplicate_count: int
    ambiguous_count: int
    unjoined_count: int
    malformed_count: int
    identity_matched_count: int
    stable_identifier_collision_count: int
    mapped_business_key_duplicate_count: int
    join_ratio: float
    type_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    quality_gate_failures: tuple[str, ...]

    @property
    def publish_ready(self) -> bool:
        return not self.quality_gate_failures

    def safe_lines(self) -> tuple[str, ...]:
        values = (
            ("operation", "massive_security_type_evidence"),
            ("as_of_date", self.evidence[0].as_of_date.isoformat() if self.evidence else ""),
            ("ticker_types_endpoint", TICKER_TYPES_PATH),
            ("all_tickers_endpoint", ALL_TICKERS_PATH),
            ("request_count", self.request_count),
            ("retry_count", 0),
            ("catalog_count", len(self.catalog)),
            ("raw_record_count", self.raw_record_count),
            ("uniquely_mapped_count", self.uniquely_mapped_count),
            ("exact_duplicate_count", self.exact_duplicate_count),
            ("ambiguous_count", self.ambiguous_count),
            ("unjoined_count", self.unjoined_count),
            ("malformed_count", self.malformed_count),
            ("identity_matched_count", self.identity_matched_count),
            ("stable_identifier_collision_count", self.stable_identifier_collision_count),
            ("mapped_business_key_duplicate_count", self.mapped_business_key_duplicate_count),
            ("join_ratio", f"{self.join_ratio:.6f}"),
            ("publish_ready", str(self.publish_ready).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)),
        )
        return tuple(f"{key}={value}" for key, value in values)


@dataclass(frozen=True, slots=True)
class _MappedRaw:
    raw_index: int
    instrument_id: UUID
    payload: Mapping[str, object]
    join_flags: tuple[str, ...]


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
    mapped: list[_MappedRaw] = []
    malformed = 0
    ambiguous = 0
    unjoined = 0
    stable_collisions = 0
    exact_duplicate = 0
    raw_signatures: set[tuple[object, ...]] = set()
    identity_matched = 0
    type_counts: Counter[str] = Counter()
    for raw_index, payload in enumerate(payloads):
        raw_ticker = _optional_upper(payload.get("ticker"))
        raw_identity_keys = tuple(
            (kind, value)
            for kind, value in (
                ("share_class_figi", _optional_upper(payload.get("share_class_figi"))),
                ("composite_figi", _optional_upper(payload.get("composite_figi"))),
                ("provider_instrument_id", _optional_upper(payload.get("id"))),
            )
            if value is not None
        )
        if (raw_ticker is not None and raw_ticker in indexes.known_tickers) or any(
            key in indexes.known_stable for key in raw_identity_keys
        ):
            identity_matched += 1
        try:
            ticker = _required(payload.get("ticker"), "ticker").upper()
            type_code = _required(payload.get("type"), "type").upper()
            _required(payload.get("primary_exchange"), "primary_exchange")
        except RuntimeError:
            malformed += 1
            continue
        type_counts[type_code] += 1
        signature = (
            ticker,
            type_code,
            _optional_upper(payload.get("id")),
            _optional_upper(payload.get("composite_figi")),
            _optional_upper(payload.get("share_class_figi")),
        )
        if signature in raw_signatures:
            exact_duplicate += 1
            continue
        raw_signatures.add(signature)
        candidate_ids: set[UUID] = set()
        collision = False
        for identity_type, value in (
            ("share_class_figi", _optional_upper(payload.get("share_class_figi"))),
            ("composite_figi", _optional_upper(payload.get("composite_figi"))),
            ("provider_instrument_id", _optional_upper(payload.get("id"))),
        ):
            if value is None:
                continue
            matches = indexes.stable.get((identity_type, value), frozenset())
            if len(matches) > 1:
                collision = True
            candidate_ids.update(matches)
        if collision:
            stable_collisions += 1
            ambiguous += 1
            continue
        ticker_id = indexes.ticker.get(ticker)
        join_flags: list[str] = []
        if len(candidate_ids) > 1 or (len(candidate_ids) == 1 and ticker_id is not None and ticker_id not in candidate_ids):
            ambiguous += 1
            continue
        if candidate_ids:
            instrument_id = next(iter(candidate_ids))
            join_flags.append("stable_identifier_join")
        elif ticker_id is not None:
            instrument_id = ticker_id
            join_flags.append("point_in_time_ticker_resolver_join")
        else:
            unjoined += 1
            continue
        mapped.append(_MappedRaw(raw_index, instrument_id, payload, tuple(join_flags)))

    by_id: dict[UUID, list[_MappedRaw]] = {}
    for item in mapped:
        by_id.setdefault(item.instrument_id, []).append(item)
    business_duplicates = 0
    unique_mapped: list[_MappedRaw] = []
    for values in by_id.values():
        if len(values) == 1:
            unique_mapped.append(values[0])
            continue
        keys = {_mapped_signature(item.payload) for item in values}
        if len(keys) == 1:
            unique_mapped.append(values[0])
            exact_duplicate += len(values) - 1
        else:
            business_duplicates += len(values)
            ambiguous += len(values)

    evidence = tuple(
        sorted(
            (_to_evidence(item, catalog_by_code, as_of_date, observed_at) for item in unique_mapped),
            key=lambda item: (str(item.instrument_id), item.provider_ticker),
        )
    )
    raw_count = len(payloads)
    uniquely_mapped = len(evidence)
    reconciled = uniquely_mapped + exact_duplicate + ambiguous + unjoined + malformed
    failures = []
    if not catalog:
        failures.append("catalog_empty")
    if raw_count <= MINIMUM_RAW_RECORDS:
        failures.append("raw_record_count_below_gate")
    if request_count > MAX_TOTAL_REQUESTS or all_tickers_request_count > MAX_ALL_TICKER_PAGES:
        failures.append("request_count_above_gate")
    if stable_collisions:
        failures.append("stable_identifier_collision_nonzero")
    if business_duplicates:
        failures.append("mapped_business_key_duplicate_nonzero")
    if ambiguous:
        failures.append("ambiguous_mapping_nonzero")
    if reconciled != raw_count:
        failures.append("raw_reconciliation_failed")
    join_ratio = identity_matched / raw_count if raw_count else 0.0
    if join_ratio < MINIMUM_JOIN_RATIO:
        failures.append("identity_join_ratio_below_gate")
    categories = (
        ("ambiguous", ambiguous),
        ("exact_duplicate", exact_duplicate),
        ("malformed", malformed),
        ("uniquely_mapped", uniquely_mapped),
        ("unjoined", unjoined),
    )
    return EvidenceBuildResult(
        catalog=catalog,
        evidence=evidence,
        request_count=request_count,
        ticker_types_request_count=1,
        all_tickers_request_count=all_tickers_request_count,
        raw_record_count=raw_count,
        uniquely_mapped_count=uniquely_mapped,
        exact_duplicate_count=exact_duplicate,
        ambiguous_count=ambiguous,
        unjoined_count=unjoined,
        malformed_count=malformed,
        identity_matched_count=identity_matched,
        stable_identifier_collision_count=stable_collisions,
        mapped_business_key_duplicate_count=business_duplicates,
        join_ratio=join_ratio,
        type_counts=tuple(sorted(type_counts.items())),
        category_counts=categories,
        quality_gate_failures=tuple(failures),
    )


def _to_evidence(
    item: _MappedRaw,
    catalog: dict[str, ProviderSecurityTypeCatalogV1],
    as_of_date: date,
    observed_at: datetime,
) -> ProviderInstrumentSecurityEvidenceV1:
    payload = item.payload
    ticker = _required(payload.get("ticker"), "ticker").upper()
    code = _required(payload.get("type"), "type").upper()
    catalog_item = catalog.get(code)
    form = EXPLICIT_FORMS.get(code, SecurityForm.UNKNOWN)
    flags = list(item.join_flags)
    review_flags = list(_name_review_flags(_optional(payload.get("name"))))
    if catalog_item is None:
        description = "Unknown provider type code"
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
    return ProviderInstrumentSecurityEvidenceV1(
        as_of_date=as_of_date,
        instrument_id=item.instrument_id,
        provider=MASSIVE_PROVIDER_ID,
        provider_ticker=ticker,
        provider_type_code=code,
        provider_type_description=description,
        primary_exchange=_required(payload.get("primary_exchange"), "primary_exchange"),
        cik=_optional(payload.get("cik")),
        composite_figi=_optional_upper(payload.get("composite_figi")),
        share_class_figi=_optional_upper(payload.get("share_class_figi")),
        security_form_evidence=form,
        evidence_source=ALL_TICKERS_PATH,
        evidence_grade=grade,
        classification_status=status,
        universe_disposition=disposition,
        decision_flags=tuple(flags),
        review_flags=tuple(sorted(set(review_flags))),
        observed_at=observed_at,
        ingested_at=observed_at,
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
    stable_mutable: dict[tuple[str, str], set[UUID]] = {}
    known_stable: set[tuple[str, str]] = set()
    known_tickers: set[str] = set()
    for row in identity_table.to_pylist():
        known_tickers.add(str(row["provider_ticker"]).upper())
        for kind, field in (("share_class_figi", "share_class_figi"), ("composite_figi", "composite_figi"), ("provider_instrument_id", "provider_instrument_id")):
            value = _optional_upper(row.get(field))
            if value:
                known_stable.add((kind, value))
        canonical = row.get("canonical_instrument_id")
        if canonical is None:
            continue
        instrument_id = UUID(str(canonical))
        for kind, field in (("share_class_figi", "share_class_figi"), ("composite_figi", "composite_figi"), ("provider_instrument_id", "provider_instrument_id")):
            value = _optional_upper(row.get(field))
            if value:
                stable_mutable.setdefault((kind, value), set()).add(instrument_id)
    ticker = {str(row["provider_ticker"]).upper(): UUID(str(row["canonical_instrument_id"])) for row in resolver_table.to_pylist()}
    return IdentityIndexes(
        {key: frozenset(value) for key, value in stable_mutable.items()},
        ticker,
        frozenset(known_stable),
        frozenset(known_tickers),
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


def _mapped_signature(payload: Mapping[str, object]) -> tuple[object, ...]:
    return (_optional(payload.get("ticker")), _optional(payload.get("type")), _optional_upper(payload.get("id")), _optional_upper(payload.get("composite_figi")), _optional_upper(payload.get("share_class_figi")))


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


def target_partitions(root: Path, *, as_of_date: date, observed_date: date) -> tuple[Path, Path]:
    base = root / "market-data"
    return (
        base / "provider-security-type-catalog" / "schema_version=1" / f"provider={MASSIVE_PROVIDER_ID}" / f"observed_date={observed_date.isoformat()}",
        base / "provider-instrument-security-evidence" / "schema_version=1" / f"provider={MASSIVE_PROVIDER_ID}" / f"as_of_date={as_of_date.isoformat()}",
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
    catalog_target, evidence_target = target_partitions(root, as_of_date=as_of_date, observed_date=observed_at.date())
    if catalog_target.exists() or catalog_target.is_symlink() or evidence_target.exists() or evidence_target.is_symlink():
        print("error=security evidence target already exists", file=sys.stderr)
        return 1
    try:
        indexes = load_identity_indexes(root, as_of_date=as_of_date)
        config = load_massive_provider_config_from_file()
        result = fetch_security_evidence(
            config=config,
            transport=MassiveUrllibTransport(),
            as_of_date=as_of_date,
            indexes=indexes,
            rate_limiter=FixedIntervalRateLimiter(),
            observed_at=observed_at,
        )
        for line in result.safe_lines():
            print(line)
        if not result.publish_ready:
            return 1
        repository = ParquetSecurityEvidenceRepository(root)
        catalog_write = repository.publish_catalog(result.catalog, observed_date=observed_at.date(), provider_id=MASSIVE_PROVIDER_ID)
        quality = {
            "request_count": result.request_count,
            "retry_count": 0,
            "raw_record_count": result.raw_record_count,
            "uniquely_mapped_count": result.uniquely_mapped_count,
            "exact_duplicate_count": result.exact_duplicate_count,
            "ambiguous_count": result.ambiguous_count,
            "unjoined_count": result.unjoined_count,
            "malformed_count": result.malformed_count,
            "identity_matched_count": result.identity_matched_count,
            "stable_identifier_collision_count": result.stable_identifier_collision_count,
            "mapped_business_key_duplicate_count": result.mapped_business_key_duplicate_count,
            "identity_join_ratio": result.join_ratio,
            "type_counts": dict(result.type_counts),
        }
        evidence_write = repository.publish_instrument_evidence(
            result.evidence,
            as_of_date=as_of_date,
            provider_id=MASSIVE_PROVIDER_ID,
            catalog_content_sha256=catalog_write.content_sha256,
            quality_summary=quality,
        )
        print(f"catalog_status={catalog_write.status}")
        print(f"catalog_content_sha256={catalog_write.content_sha256}")
        print(f"evidence_status={evidence_write.status}")
        print(f"evidence_content_sha256={evidence_write.content_sha256}")
        return 0
    except (MassiveCredentialFileError, MassiveTransportError, SecurityEvidencePersistenceError, RuntimeError, ValueError) as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
