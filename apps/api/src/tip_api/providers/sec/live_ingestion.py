"""Single-run SEC issuer-structure evidence ingestion for the approved Phase B2B scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import UUID

import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.contracts.security_classification.v1 import SecEvidenceResolutionStatus
from tip_api.persistence.parquet.instrument_master_snapshot import (
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    _identity_table_to_rows,
    _instrument_table_to_rows,
    records_fingerprint,
)
from tip_api.persistence.parquet.sec_issuer_evidence import ParquetSecIssuerEvidenceRepository
from tip_api.persistence.sec_issuer_evidence import SecIssuerEvidencePersistenceError
from tip_api.providers.sec.bulk_sources import (
    SOURCE_CACHE_RELATIVE_ROOT,
    SecLandingDiscoveryError,
    acquire_sec_source_cache,
    iter_selected_submissions,
    parse_tabular_json,
    read_csv_rows,
    source_file_hash,
)
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.credential import SecCredentialFileError, load_sec_provider_config_from_file
from tip_api.providers.sec.issuer_evidence import (
    SecIdentityRecord,
    SecIdentityResolver,
    build_bdc_state_observation,
    interpret_sec_fixture,
    reconcile_sec_evidence,
)
from tip_api.providers.sec.transport import BoundedSecTransport, SecTransportError

APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
APPROVED_AS_OF_DATE = date(2026, 8, 14)
INTERESTING_FORMS = frozenset({"N-54A", "N-54C", "N-2", "10-K", "20-F", "40-F"})
EXCHANGE_TO_MIC = {
    "NYSE": "XNYS", "NEW YORK STOCK EXCHANGE": "XNYS", "NASDAQ": "XNAS",
    "NASDAQ GLOBAL SELECT MARKET": "XNAS", "NASDAQ GLOBAL MARKET": "XNAS",
    "NASDAQ CAPITAL MARKET": "XNAS", "NYSE ARCA": "ARCX", "CBOE BZX": "BATS",
}


@dataclass(frozen=True, slots=True)
class SecLiveBuildResult:
    observations: tuple[Any, ...]
    evidence: tuple[Any, ...]
    raw_input_count: int
    emitted_observation_count: int
    not_applicable_count: int
    future_record_count: int
    malformed_count: int
    ambiguous_count: int
    collision_count: int
    mapped_count: int
    expected_unjoined_count: int
    canonical_conflict_count: int
    source_counts: tuple[tuple[str, int], ...]

    @property
    def publish_ready(self) -> bool:
        return (
            self.raw_input_count == self.emitted_observation_count + self.not_applicable_count + self.future_record_count + self.malformed_count
            and self.ambiguous_count == 0 and self.collision_count == 0 and self.canonical_conflict_count == 0
            and bool(self.observations) and bool(self.evidence)
        )

    def safe_summary(self) -> dict[str, int | float | str]:
        return {
            "raw_input_count": self.raw_input_count,
            "observation_count": len(self.observations),
            "canonical_evidence_count": len(self.evidence),
            "emitted_observation_input_count": self.emitted_observation_count,
            "not_applicable_count": self.not_applicable_count,
            "future_record_count": self.future_record_count,
            "malformed_count": self.malformed_count,
            "canonical_mapped_count": self.mapped_count,
            "expected_unjoined_count": self.expected_unjoined_count,
            "ambiguous_count": self.ambiguous_count,
            "collision_count": self.collision_count,
            "canonical_conflict_count": self.canonical_conflict_count,
            "reconciliation_status": "passed" if self.publish_ready else "failed",
        }


def load_sec_identity_records(root: Path, *, as_of_date: date) -> tuple[SecIdentityRecord, ...]:
    snapshot_path = root / "market-data/snapshots/instrument-master" / f"as_of_date={as_of_date.isoformat()}" / "manifest.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("completion_status") != "completed" or snapshot.get("as_of_date") != as_of_date.isoformat():
        raise RuntimeError("accepted identity snapshot is unavailable")
    instrument_path = _manifest_partition(root, snapshot.get("instrument_partition_path"))
    identity_path = _manifest_partition(root, snapshot.get("identity_partition_path"))
    instruments = _validated_table(instrument_path, INSTRUMENT_MASTER_ARROW_SCHEMA, int(snapshot["instrument_count"]), str(snapshot["instrument_content_sha256"]), _instrument_table_to_rows)
    identities = _validated_table(identity_path, PROVIDER_IDENTITY_ARROW_SCHEMA, int(snapshot["identity_count"]), str(snapshot["identity_content_sha256"]), _identity_table_to_rows)
    instrument_by_id = {str(row["instrument_id"]): row for row in instruments.to_pylist()}
    result: list[SecIdentityRecord] = []
    for row in identities.to_pylist():
        canonical = row.get("canonical_instrument_id")
        if row.get("resolution_status") != ResolutionStatus.RESOLVED.value or canonical is None:
            continue
        instrument = instrument_by_id.get(str(canonical))
        if instrument is None:
            raise RuntimeError("identity references a missing canonical instrument")
        result.append(SecIdentityRecord(
            instrument_id=UUID(str(canonical)), effective_from=row["valid_from"], effective_to=row.get("valid_to"),
            cik=_normalize_cik(row.get("cik") or instrument.get("cik")), ticker=str(row["provider_ticker"]).upper(),
            exchange=str(instrument["primary_exchange"]).upper(), share_class_figi=_upper(row.get("share_class_figi")),
            composite_figi=_upper(row.get("composite_figi")), provider_stable_identifier=_text(row.get("provider_instrument_id")),
        ))
    if len({item.instrument_id for item in result}) != len(result):
        raise RuntimeError("resolved identity snapshot contains duplicate canonical instruments")
    return tuple(sorted(result, key=lambda item: str(item.instrument_id)))


def build_live_evidence(cache: Path, *, as_of_date: date, observed_at: datetime, identities: tuple[SecIdentityRecord, ...]) -> SecLiveBuildResult:
    resolver = SecIdentityResolver(identities)
    observations: dict[str, Any] = {}
    raw_count = emitted_input = not_applicable = future = malformed = 0
    source_counts: Counter[str] = Counter()
    seed_rows = parse_tabular_json(cache / "company_tickers_exchange.json")
    seeds_by_cik: dict[str, list[dict[str, str]]] = defaultdict(list)

    def consume(raw: Mapping[str, Any], source_name: str, *, count_input: bool = True) -> None:
        nonlocal emitted_input, malformed
        try:
            value = interpret_sec_fixture(raw, filing_cutoff=as_of_date, resolver=resolver, source_observed_at=observed_at)
        except (ValueError, TypeError):
            malformed += 1
            return
        if value is not None:
            observations[value.observation_id] = value
            if count_input:
                emitted_input += 1

    for row in seed_rows:
        raw_count += 1
        source_counts["company_tickers_exchange"] += 1
        cik = _normalize_cik(_field(row, "cik", "cik_str"))
        ticker = _upper(_field(row, "ticker", "symbol"))
        exchange = _normalize_exchange(_field(row, "exchange", "exchange_name"))
        if not cik or not ticker or not exchange:
            malformed += 1
            continue
        seed = {"cik": cik, "ticker": ticker, "exchange": exchange}
        seeds_by_cik[cik].append(seed)
        consume({
            "source_dataset": "company_tickers_exchange", "source_document_type": "official_reference_json",
            "cik": cik, "ticker": ticker, "exchange": exchange, "filing_date": as_of_date.isoformat(),
            "allow_cik_ticker_exchange": True,
        }, "company_tickers_exchange")

    mf_rows = parse_tabular_json(cache / "company_tickers_mf.json")
    for row in mf_rows:
        raw_count += 1
        source_counts["company_tickers_mf"] += 1
        cik = _normalize_cik(_field(row, "cik", "cik_str"))
        ticker = _upper(_field(row, "ticker", "symbol", "class_ticker"))
        seeds = [seed for seed in seeds_by_cik.get(cik or "", ()) if seed["ticker"] == ticker]
        if not cik or not ticker or len(seeds) != 1:
            not_applicable += 1
            continue
        consume({
            "source_dataset": "company_tickers_mf", "source_document_type": "official_reference_json",
            **seeds[0], "filing_date": as_of_date.isoformat(), "allow_cik_ticker_exchange": True,
            "historical_cutoff_supported": False,
        }, "company_tickers_mf")

    for source_name in ("investment_company_series_class", "closed_end_fund", "business_development_company"):
        for row in read_csv_rows(cache / f"{source_name}.csv"):
            raw_count += 1
            source_counts[source_name] += 1
            cik = _normalize_cik(_field(row, "cik", "cik number", "cik_number", "registrant cik"))
            evidence_date = _date_field(row, "filing date", "filing_date", "report date", "report_date", "effective date", "effective_date")
            if evidence_date is not None and evidence_date > as_of_date:
                future += 1
                continue
            ticker = _upper(_field(row, "ticker", "symbol", "class ticker"))
            candidates = [seed for seed in seeds_by_cik.get(cik or "", ()) if ticker is None or seed["ticker"] == ticker]
            if not cik or evidence_date is None or len(candidates) != 1:
                not_applicable += 1
                continue
            consume({
                "source_dataset": source_name, "source_document_type": "official_csv", **candidates[0],
                "filing_date": evidence_date.isoformat(), "allow_cik_ticker_exchange": True,
                "fund_kind": _fund_kind(row),
            }, source_name)

    selected_ciks = {item.cik for item in identities if item.cik}
    for cik, payload in iter_selected_submissions(cache / "submissions.zip", selected_ciks):
        recent = payload.get("filings", {}).get("recent", {}) if isinstance(payload.get("filings"), dict) else {}
        forms = recent.get("form", []) if isinstance(recent, dict) else []
        filing_dates = recent.get("filingDate", []) if isinstance(recent, dict) else []
        accessions = recent.get("accessionNumber", []) if isinstance(recent, dict) else []
        if not isinstance(forms, list) or not isinstance(filing_dates, list) or len(forms) != len(filing_dates):
            malformed += 1
            continue
        bdc_filings: list[dict[str, Any]] = []
        seeds = seeds_by_cik.get(cik, [])
        for index, (form, filing_date_value) in enumerate(zip(forms, filing_dates, strict=True)):
            raw_count += 1
            source_counts["submissions_filing"] += 1
            normalized_form = str(form).upper()
            try:
                filing_date = date.fromisoformat(str(filing_date_value))
            except ValueError:
                malformed += 1
                continue
            if filing_date > as_of_date:
                future += 1
                continue
            if normalized_form not in INTERESTING_FORMS:
                not_applicable += 1
                continue
            accession = str(accessions[index]) if index < len(accessions) else None
            if normalized_form in {"N-54A", "N-54C"}:
                bdc_filings.append({"source_dataset": "filing", "source_document_type": "submissions_bulk", "cik": cik, "form": normalized_form, "filing_date": filing_date.isoformat(), "accession_number": accession})
                not_applicable += 1
                continue
            if not seeds:
                not_applicable += 1
                continue
            for seed_index, seed in enumerate(seeds):
                consume({"source_dataset": "filing", "source_document_type": "submissions_bulk", **seed, "form": normalized_form, "filing_date": filing_date.isoformat(), "accession_number": accession, "allow_cik_ticker_exchange": True}, "submissions_filing", count_input=seed_index == 0)
        if bdc_filings and seeds:
            for seed in seeds:
                records = tuple({**item, **seed, "allow_cik_ticker_exchange": True} for item in bdc_filings)
                value = build_bdc_state_observation(records, filing_cutoff=as_of_date, resolver=resolver, source_observed_at=observed_at)
                if value is not None:
                    observations[value.observation_id] = value

    ordered = tuple(sorted(observations.values(), key=lambda item: item.observation_id))
    status = Counter(item.resolution_status for item in ordered)
    evidence = reconcile_sec_evidence(ordered, as_of_date=as_of_date)
    business_keys = [item.business_key for item in evidence]
    conflicts = len(business_keys) - len(set(business_keys))
    return SecLiveBuildResult(
        ordered, evidence, raw_count, emitted_input, not_applicable, future, malformed,
        status[SecEvidenceResolutionStatus.AMBIGUOUS], status[SecEvidenceResolutionStatus.COLLISION],
        status[SecEvidenceResolutionStatus.CANONICAL_MAPPED], status[SecEvidenceResolutionStatus.EXPECTED_UNJOINED],
        conflicts, tuple(sorted(source_counts.items())),
    )


def target_paths(root: Path, as_of_date: date) -> tuple[Path, ...]:
    return (
        root / SOURCE_CACHE_RELATIVE_ROOT / f"as_of_date={as_of_date.isoformat()}",
        root / "market-data/sec-issuer-structure-observation/schema_version=1" / f"as_of_date={as_of_date.isoformat()}",
        root / "market-data/sec-issuer-structure-evidence/schema_version=1" / f"as_of_date={as_of_date.isoformat()}",
        root / "market-data/snapshots/sec-issuer-structure-evidence" / f"as_of_date={as_of_date.isoformat()}",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest-sec-issuer-structure-evidence.sh")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root, as_of_date = APPROVED_DATA_ROOT, APPROVED_AS_OF_DATE
    if any(path.exists() or path.is_symlink() for path in target_paths(root, as_of_date)):
        print("error=SEC evidence target already exists", file=sys.stderr)
        return 1
    identities = load_sec_identity_records(root, as_of_date=as_of_date)
    print(f"preflight_identity_count={len(identities)}")
    print(f"as_of_date={as_of_date.isoformat()}")
    if not args.apply:
        print("mode=dry-run")
        print("network_requests=0")
        return 0
    observed_at = datetime.now(UTC)
    transport = BoundedSecTransport(request_ceiling=12)
    try:
        config = load_sec_provider_config_from_file()
        config = SecProviderConfig(user_agent=config.user_agent, request_timeout_seconds="300", max_requests_per_second=config.max_requests_per_second, max_retries=2)
        cache = acquire_sec_source_cache(root, as_of_date=as_of_date, observed_at=observed_at, config=config, transport=transport)
        result = build_live_evidence(cache.path, as_of_date=as_of_date, observed_at=observed_at, identities=identities)
        if not result.publish_ready:
            diagnostic = _write_failed_diagnostic(root, as_of_date, observed_at, transport, result.safe_summary(), "quality_gate_failed")
            print(f"failed_diagnostic={diagnostic}")
            print("error=SEC evidence quality gate failed", file=sys.stderr)
            return 1
        cache_manifest_sha = source_file_hash(cache.path / "manifest.json")
        repository = ParquetSecIssuerEvidenceRepository(root, observed_at)
        observation_write = repository.publish_observations(result.observations, as_of_date=as_of_date, source_cache_manifest_sha256=cache_manifest_sha)
        evidence_write = repository.publish(result.evidence, source_datasets=tuple(name for name, _ in result.source_counts))
        snapshot_write = repository.publish_logical_snapshot(
            as_of_date=as_of_date, observed_at=observed_at, source_cache_manifest_sha256=cache_manifest_sha,
            observation=observation_write, canonical_evidence=evidence_write, quality_summary=result.safe_summary(),
        )
        print(f"request_count={transport.request_count}")
        print(f"retry_count={transport.retry_count}")
        for source_name, selection in cache.csv_selections:
            print(f"{source_name}_csv_dataset_year={selection.dataset_year}")
            print(f"{source_name}_csv_effective_date={selection.effective_date.isoformat()}")
            print(f"{source_name}_csv_total_candidates={selection.total_csv_candidate_count}")
            print(f"{source_name}_csv_eligible_candidates={selection.eligible_count}")
            print(f"{source_name}_csv_future_candidates={selection.future_dated_count}")
        for key, value in result.safe_summary().items():
            print(f"{key}={value}")
        print(f"source_cache_status={cache.status}")
        print(f"observation_status={observation_write.status}")
        print(f"observation_content_sha256={observation_write.content_sha256}")
        print(f"canonical_evidence_status={evidence_write.status}")
        print(f"canonical_evidence_content_sha256={evidence_write.content_sha256}")
        print(f"logical_snapshot_status={snapshot_write.status}")
        print(f"logical_content_sha256={snapshot_write.logical_content_sha256}")
        return 0
    except (SecCredentialFileError, SecTransportError, SecIssuerEvidencePersistenceError, RuntimeError, ValueError) as exc:
        reason = _safe_failure_reason(exc)
        quality = {"landing_discovery": exc.diagnostic.to_safe_dict()} if isinstance(exc, SecLandingDiscoveryError) else {}
        try:
            diagnostic = _write_failed_diagnostic(root, as_of_date, observed_at, transport, quality, reason)
            print(f"failed_diagnostic={diagnostic}")
        except Exception:
            print("failed_diagnostic=write_failed", file=sys.stderr)
        print(f"error={reason}", file=sys.stderr)
        return 1


def _write_failed_diagnostic(root: Path, as_of_date: date, created_at: datetime, transport: BoundedSecTransport, quality: Mapping[str, Any], reason: str) -> str:
    run_id = f"sec-b2b-{as_of_date.isoformat()}-{created_at.strftime('%Y%m%dT%H%M%SZ')}"
    directory = root / "operation-diagnostics/sec-issuer-structure-evidence" / f"as_of_date={as_of_date.isoformat()}" / f"run_id={run_id}"
    directory.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema_version": "1.0", "diagnostic_status": "failed", "run_id": run_id,
        "as_of_date": as_of_date.isoformat(), "created_at": created_at.astimezone(UTC).isoformat(),
        "request_count": transport.request_count, "retry_count": transport.retry_count,
        "failure_reason": reason, "quality_summary": dict(quality),
    }
    (directory / "diagnostic.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return directory.relative_to(root).as_posix()


def _validated_table(path: Path, schema: Any, count: int, fingerprint: str, converter: Any) -> Any:
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("accepted identity partition is unavailable")
    table = pq.ParquetFile(path / "part-00000.parquet").read()
    if not table.schema.equals(schema, check_metadata=False) or table.num_rows != count or records_fingerprint(converter(table)) != fingerprint:
        raise RuntimeError("accepted identity partition validation failed")
    return table


def _manifest_partition(root: Path, value: Any) -> Path:
    supplied = Path(str(value))
    if ".." in supplied.parts:
        raise RuntimeError("accepted identity manifest path is invalid")
    candidate = supplied if supplied.is_absolute() else root / supplied
    if candidate.resolve().is_relative_to(root.resolve()):
        return candidate
    raise RuntimeError("accepted identity manifest path escapes data root")


def _field(row: Mapping[str, Any], *aliases: str) -> Any:
    normalized = {str(key).strip().lower().replace("_", " "): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(alias.lower().replace("_", " "))
        if value not in (None, ""):
            return value
    return None


def _text(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _upper(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _normalize_cik(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    text = text.removeprefix("CIK").lstrip("0") or "0"
    return text.zfill(10) if text.isdigit() and len(text) <= 10 else None


def _normalize_exchange(value: Any) -> str | None:
    text = _upper(value)
    if text in {"XNYS", "XNAS", "ARCX", "BATS"}:
        return text
    return EXCHANGE_TO_MIC.get(text or "")


def _date_field(row: Mapping[str, Any], *aliases: str) -> date | None:
    value = _text(_field(row, *aliases))
    if value is None:
        return None
    for candidate in (value[:10], value):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _fund_kind(row: Mapping[str, Any]) -> str | None:
    text = " ".join(str(value).upper() for value in row.values())
    if "EXCHANGE TRADED" in text or "ETF" in text:
        return "etf"
    if "OPEN-END" in text or "OPEN END" in text:
        return "open_end_fund"
    return None


def _safe_failure_reason(exc: Exception) -> str:
    if isinstance(exc, SecCredentialFileError):
        return "credential_boundary_failure"
    if isinstance(exc, SecTransportError):
        status = getattr(exc, "status_code", None)
        if isinstance(exc, SecLandingDiscoveryError):
            return exc.reason_code
        return f"sec_http_{status}" if isinstance(status, int) else "sec_transport_or_source_validation_failure"
    if isinstance(exc, SecIssuerEvidencePersistenceError):
        return "evidence_persistence_failure"
    return "sec_evidence_runtime_failure"


if __name__ == "__main__":
    raise SystemExit(main())
