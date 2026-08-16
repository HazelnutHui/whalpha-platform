"""Bounded SEC bulk-source acquisition and safe offline parsing."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import stat
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urljoin, urlparse

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import BoundedSecTransport, SecTransportError, validate_sec_url

COMPANY_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COMPANY_MF_URL = "https://www.sec.gov/files/company_tickers_mf.json"
SUBMISSIONS_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
LANDING_PAGES = {
    "investment_company_series_class": "https://www.sec.gov/data-research/sec-markets-data/investment-company-series-class-information",
    "closed_end_fund": "https://www.sec.gov/data-research/sec-markets-data/closed-end-fund-information",
    "business_development_company": "https://www.sec.gov/data-research/sec-markets-data/opendatasetsshtmlbdc",
}
CSV_PATH_TEMPLATES = {
    "investment_company_series_class": "/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-{year}.csv",
    "closed_end_fund": "/files/investment/data/other/closed-end-fund-information/closed-end-investment-company-{year}.csv",
    "business_development_company": "/files/investment/data/other/business-development-company-report/business-development-company-{year}.csv",
}
SERIES_CLASS_2024_LEGACY_PATH = (
    "/files/investment/data/other/investment-company-series-and-class-information/"
    "investment-company-series-class-2024.csv"
)
SERIES_CLASS_2023_UNDERSCORE_PATH = (
    "/files/investment/data/other/investment-company-series-class-information/"
    "investment_company_series_class_2023.csv"
)
CSV_REQUIRED_HEADER_GROUPS = {
    "investment_company_series_class": (
        frozenset({"cik", "cik number", "registrant cik"}),
        frozenset({"series id", "seriesid"}),
    ),
    "closed_end_fund": (
        frozenset({"cik", "cik number", "registrant cik"}),
        frozenset({"registrant name", "fund name", "company name", "name"}),
    ),
    "business_development_company": (
        frozenset({"cik", "cik number", "registrant cik"}),
        frozenset({"registrant name", "company name", "name"}),
    ),
}
SOURCE_CACHE_RELATIVE_ROOT = Path("source-cache/sec/security-classification")
MAX_SMALL_SOURCE_BYTES = 128 * 1024 * 1024
MAX_CSV_BYTES = 512 * 1024 * 1024
MAX_SUBMISSIONS_ZIP_BYTES = 8 * 1024 * 1024 * 1024
MAX_ZIP_MEMBERS = 1_000_000
MAX_ZIP_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ZIP_TOTAL_UNCOMPRESSED = 64 * 1024 * 1024 * 1024
MAX_ZIP_COMPRESSION_RATIO = 200
ZIP_READ_CHUNK_BYTES = 1024 * 1024
SOURCE_CACHE_ARTIFACTS = {
    "company_tickers_exchange.json": "official_ticker_json",
    "company_tickers_mf.json": "official_ticker_json",
    "investment_company_series_class.landing.html": "official_landing_html",
    "investment_company_series_class.csv": "selected_csv",
    "closed_end_fund.landing.html": "official_landing_html",
    "closed_end_fund.csv": "selected_csv",
    "business_development_company.landing.html": "official_landing_html",
    "business_development_company.csv": "selected_csv",
    "submissions.zip": "submissions_zip",
}
SUBMISSIONS_MEMBER_PATTERN = re.compile(r"CIK(?P<cik>[0-9]{10})\.json\Z")


@dataclass(frozen=True, slots=True)
class SecCachedSource:
    source_name: str
    artifact_role: str
    url: str
    file_name: str
    observed_at: str
    content_type: str
    byte_size: int
    sha256: str
    dataset_year: int | None = None
    effective_date: str | None = None


@dataclass(frozen=True, slots=True)
class SecSourceCacheResult:
    path: Path
    sources: tuple[SecCachedSource, ...]
    request_count: int
    retry_count: int
    status: str
    csv_selections: tuple[tuple[str, SecCsvSelection], ...]


@dataclass(frozen=True, slots=True)
class SecCsvSelection:
    dataset_id: str
    url: str
    dataset_year: int
    effective_date: date
    selection_reason_code: str
    total_csv_candidate_count: int
    eligible_count: int
    future_dated_count: int
    selection_fingerprint: str
    diagnostic: SecLandingDiscoveryDiagnostic


class SecCsvUrlFailureCode(StrEnum):
    """Finite, non-content reasons for rejecting a landing-page CSV URL."""

    SCHEME_NOT_HTTPS = "scheme_not_https"
    USERINFO_PRESENT = "userinfo_present"
    HOST_NOT_ALLOWED = "host_not_allowed"
    NONSTANDARD_PORT = "nonstandard_port"
    BACKSLASH_PRESENT = "backslash_present"
    TRAVERSAL_PRESENT = "traversal_present"
    ENCODED_TRAVERSAL_PRESENT = "encoded_traversal_present"
    QUERY_PRESENT = "query_present"
    FRAGMENT_PRESENT = "fragment_present"
    PATH_ROOT_NOT_ALLOWED = "path_root_not_allowed"
    PATH_TEMPLATE_MISMATCH = "path_template_mismatch"
    EXTENSION_NOT_CSV = "extension_not_csv"
    FILE_YEAR_MISMATCH = "file_year_mismatch"
    MALFORMED_URL = "malformed_url"


@dataclass(frozen=True, slots=True)
class SecCsvCandidateDiagnostic:
    dataset_id: str
    candidate_ordinal: int
    download_table_ordinal: int
    table_row_index: int
    normalized_format: str
    normalized_size_text: str | None
    file_year: int | None
    updated_date: str | None
    anchor_count: int
    temporal_relation: str
    baseline_url_status: str
    template_status: str
    reason_code: str | None
    action: str
    normalized_path: str | None
    path_basename: str | None

    @property
    def parsed_file_year(self) -> int | None:
        return self.file_year

    @property
    def parsed_updated_date(self) -> str | None:
        return self.updated_date

    @property
    def selection_state(self) -> str:
        if self.action == "selected":
            return "selected"
        if self.reason_code == "eligible_not_selected":
            return "eligible_not_selected"
        if self.reason_code == "future_candidate_excluded":
            return "future_excluded"
        if self.reason_code == "undated_historical_ignored":
            return "undated_historical_excluded"
        if self.reason_code == "duplicate_candidate_ignored":
            return "duplicate_excluded"
        return "rejected" if self.action == "hard_fail" else "ignored_warning"

    @property
    def url_validation_state(self) -> str:
        return (
            "accepted"
            if self.baseline_url_status == "passed" and self.template_status == "matched"
            else "rejected"
        )

    @property
    def failure_code(self) -> str | None:
        return self.reason_code

    @property
    def path_template_match(self) -> bool | None:
        if self.template_status == "not_evaluated":
            return None
        return self.template_status == "matched"

    @property
    def query_present(self) -> bool:
        return False

    @property
    def fragment_present(self) -> bool:
        return False

    @property
    def userinfo_present(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class SecLandingDiscoveryDiagnostic:
    schema_version: str
    dataset_id: str
    page_id: str
    table_count: int
    normalized_header_signature: tuple[str, ...]
    rows_scanned: int
    rows_with_anchors: int
    csv_candidate_count: int
    baseline_safe_count: int
    exact_allowlisted_count: int
    blocking_rejection_count: int
    historical_path_warning_count: int
    undated_historical_warning_count: int
    cutoff_eligible_count: int
    future_candidate_count: int
    max_date_candidate_count: int
    selected_count: int
    selected_year: int | None = None
    selected_date: str | None = None
    selected_template_id: str | None = None
    status: str = "failed"
    failure_code: str | None = None
    warning_codes: tuple[str, ...] = ()
    selection_fingerprint: str | None = None
    candidate_diagnostics: tuple[SecCsvCandidateDiagnostic, ...] = ()

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def allowlisted_count(self) -> int:
        return self.exact_allowlisted_count

    @property
    def rejected_count(self) -> int:
        return self.blocking_rejection_count

    @property
    def future_count(self) -> int:
        return self.future_candidate_count

    @property
    def undated_historical_count(self) -> int:
        return self.undated_historical_warning_count


class SecLandingDiscoveryError(SecTransportError):
    """Discovery failure with only bounded, non-content diagnostics."""

    def __init__(self, reason_code: str, diagnostic: SecLandingDiscoveryDiagnostic) -> None:
        super().__init__(f"SEC landing discovery failed: {reason_code}")
        self.reason_code = reason_code
        self.diagnostic = diagnostic


@dataclass(frozen=True, slots=True)
class _CsvUrlAnalysis:
    canonical_url: str | None
    failure_code: SecCsvUrlFailureCode | None
    normalized_path: str | None
    path_basename: str | None


@dataclass(frozen=True, slots=True)
class _CsvTemplateAnalysis:
    status: str
    template_id: str | None
    failure_code: SecCsvUrlFailureCode | None


class _SecCsvUrlValidationError(SecTransportError):
    def __init__(self, failure_code: SecCsvUrlFailureCode) -> None:
        super().__init__("SEC CSV URL rejected")
        self.failure_code = failure_code


@dataclass(frozen=True, slots=True)
class _LandingCell:
    text: str
    links: tuple[tuple[str, str], ...]
    is_header: bool


class _LandingTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[_LandingCell]]] = []
        self._table: list[list[_LandingCell]] | None = None
        self._row: list[_LandingCell] | None = None
        self._cell_text: list[str] | None = None
        self._cell_links: list[tuple[str, str]] | None = None
        self._cell_is_header = False
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            if self._table is not None:
                return
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_text, self._cell_links = [], []
            self._cell_is_header = tag == "th"
        elif tag == "a" and self._cell_text is not None:
            self._link_href = dict(attrs).get("href")
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._cell_text is not None:
            self._cell_text.append(data)
        if self._link_href is not None:
            self._link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._link_href is not None and self._cell_links is not None:
            self._cell_links.append((self._link_href, _collapse(" ".join(self._link_text))))
            self._link_href, self._link_text = None, []
        elif tag in {"td", "th"} and self._cell_text is not None and self._row is not None:
            self._row.append(_LandingCell(_collapse(" ".join(self._cell_text)), tuple(self._cell_links or ()), self._cell_is_header))
            self._cell_text, self._cell_links = None, None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


@dataclass(frozen=True, slots=True)
class _CsvCandidate:
    dataset_year: int
    effective_date: date | None
    url: str
    template: _CsvTemplateAnalysis
    diagnostic_index: int


def acquire_sec_source_cache(
    root: Path,
    *,
    as_of_date: date,
    observed_at: datetime,
    config: SecProviderConfig,
    transport: BoundedSecTransport,
) -> SecSourceCacheResult:
    """Download the approved source set once and atomically publish the verified cache."""

    validated_root = _validated_root(root)
    partition = validated_root / SOURCE_CACHE_RELATIVE_ROOT / f"as_of_date={as_of_date.isoformat()}"
    if partition.exists() or partition.is_symlink():
        raise SecTransportError("SEC source cache target already exists")
    partition.parent.mkdir(parents=True, exist_ok=True)
    staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise SecTransportError("SEC source cache staging path already exists")
    sources: list[SecCachedSource] = []
    selections: dict[str, SecCsvSelection] = {}
    try:
        staging.mkdir(mode=0o750)
        _download(transport, config, COMPANY_EXCHANGE_URL, staging / "company_tickers_exchange.json", "company_tickers_exchange", "official_ticker_json", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_exchange.json")
        _download(transport, config, COMPANY_MF_URL, staging / "company_tickers_mf.json", "company_tickers_mf", "official_ticker_json", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_mf.json")
        for source_name, landing_url in LANDING_PAGES.items():
            landing_file = staging / f"{source_name}.landing.html"
            landing = _download(transport, config, landing_url, landing_file, f"{source_name}_landing", "official_landing_html", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
            _validate_landing_response(landing)
            selection = select_dated_official_csv(
                source_name,
                landing_url,
                landing_file.read_text(encoding="utf-8", errors="strict"),
                evidence_cutoff=as_of_date,
            )
            _validate_landing_selection(selection)
            selections[source_name] = selection
            csv_file = staging / f"{source_name}.csv"
            downloaded = download_selected_csv(
                transport, config, selection, csv_file, source_name, observed_at, sources,
            )
            validate_selected_csv_response(selection, downloaded.content_type, csv_file)
        submissions = staging / "submissions.zip"
        _download(transport, config, SUBMISSIONS_URL, submissions, "submissions", "submissions_zip", observed_at, MAX_SUBMISSIONS_ZIP_BYTES, sources)
        validate_submissions_zip(submissions)
        _validate_source_cache_artifacts(staging, sources)
        manifest = json.loads(json.dumps({
            "schema_version": "1.0",
            "dataset_name": "sec-security-classification-source-cache",
            "completion_status": "completed",
            "as_of_date": as_of_date.isoformat(),
            "observed_at": observed_at.astimezone(UTC).isoformat(),
            "request_count": transport.request_count,
            "retry_count": transport.retry_count,
            "artifact_count": len(SOURCE_CACHE_ARTIFACTS),
            "csv_selections": {
                name: {
                    "selected_url": selection.url,
                    "selected_dataset_year": selection.dataset_year,
                    "selected_effective_date": selection.effective_date.isoformat(),
                    "total_csv_candidate_count": selection.total_csv_candidate_count,
                    "eligible_count": selection.eligible_count,
                    "future_dated_count": selection.future_dated_count,
                    "selection_fingerprint": selection.selection_fingerprint,
                    "discovery_diagnostic": selection.diagnostic.to_safe_dict(),
                }
                for name, selection in sorted(selections.items())
            },
            "sources": [asdict(item) for item in sorted(sources, key=lambda item: item.source_name)],
        }, sort_keys=True))
        _write_json(staging / "manifest.json", manifest)
        if json.loads((staging / "manifest.json").read_text(encoding="utf-8")) != manifest:
            raise SecTransportError("SEC source cache manifest reread mismatch")
        _validate_completed_source_cache_staging(staging, manifest)
        staging.replace(partition)
        return SecSourceCacheResult(
            partition, tuple(sorted(sources, key=lambda item: item.source_name)),
            transport.request_count, transport.retry_count, "published",
            tuple(sorted(selections.items())),
        )
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise


def _download(
    transport: BoundedSecTransport,
    config: SecProviderConfig,
    url: str,
    target: Path,
    source_name: str,
    artifact_role: str,
    observed_at: datetime,
    max_bytes: int,
    output: list[SecCachedSource],
    dataset_year: int | None = None,
    effective_date: date | None = None,
) -> SecCachedSource:
    result = transport.download(url, target, user_agent=config.user_agent, timeout_seconds=config.request_timeout_seconds, max_bytes=max_bytes)
    if result.url != url:
        raise SecTransportError("SEC download result URL mismatch")
    cached = SecCachedSource(
        source_name, artifact_role, result.url, target.name, observed_at.astimezone(UTC).isoformat(),
        result.content_type, result.byte_count, result.sha256, dataset_year,
        effective_date.isoformat() if effective_date else None,
    )
    output.append(cached)
    return cached


def _validate_landing_response(source: SecCachedSource) -> None:
    if source.content_type not in {"text/html", "application/xhtml+xml"}:
        raise SecTransportError("SEC landing response content type is invalid")
    if source.byte_size <= 0 or source.byte_size > MAX_SMALL_SOURCE_BYTES:
        raise SecTransportError("SEC landing response size is invalid")


def _validate_landing_selection(selection: SecCsvSelection) -> None:
    diagnostic = selection.diagnostic
    if (
        diagnostic.normalized_header_signature != ("file", "format", "size")
        or diagnostic.table_count < 1
        or diagnostic.rows_scanned < 1
        or diagnostic.csv_candidate_count < 1
    ):
        raise SecTransportError("SEC landing response table signature is invalid")


def _validate_source_cache_artifacts(
    staging: Path,
    sources: list[SecCachedSource],
) -> None:
    if len(sources) != len(SOURCE_CACHE_ARTIFACTS):
        raise SecTransportError("SEC source cache artifact count is invalid")
    by_file = {source.file_name: source for source in sources}
    if len(by_file) != len(sources) or set(by_file) != set(SOURCE_CACHE_ARTIFACTS):
        raise SecTransportError("SEC source cache artifact inventory is invalid")
    entries = {entry.name for entry in staging.iterdir()}
    if entries != set(SOURCE_CACHE_ARTIFACTS):
        raise SecTransportError("SEC source cache staging inventory is invalid")
    for file_name, expected_role in SOURCE_CACHE_ARTIFACTS.items():
        source = by_file[file_name]
        artifact = staging / file_name
        if (
            source.artifact_role != expected_role
            or artifact.is_symlink()
            or not artifact.is_file()
            or source.byte_size <= 0
            or artifact.stat().st_size != source.byte_size
            or source_file_hash(artifact) != source.sha256
            or validate_sec_url(source.url) != source.url
        ):
            raise SecTransportError("SEC source cache artifact validation failed")


def _validate_completed_source_cache_staging(
    staging: Path,
    manifest: dict[str, object],
) -> None:
    manifest_path = staging / "manifest.json"
    expected_entries = set(SOURCE_CACHE_ARTIFACTS) | {"manifest.json"}
    if (
        {entry.name for entry in staging.iterdir()} != expected_entries
        or manifest_path.is_symlink()
        or not manifest_path.is_file()
        or manifest.get("completion_status") != "completed"
        or manifest.get("artifact_count") != len(SOURCE_CACHE_ARTIFACTS)
    ):
        raise SecTransportError("SEC source cache completion marker is invalid")
    manifest_sources = manifest.get("sources")
    if not isinstance(manifest_sources, list) or len(manifest_sources) != len(SOURCE_CACHE_ARTIFACTS):
        raise SecTransportError("SEC source cache manifest artifact count is invalid")


def download_selected_csv(
    transport: BoundedSecTransport,
    config: SecProviderConfig,
    selection: SecCsvSelection,
    target: Path,
    source_name: str,
    observed_at: datetime,
    output: list[SecCachedSource],
) -> SecCachedSource:
    """Download only a selection object whose full discovery contract revalidates."""

    _validate_selected_selection(selection)
    return _download(
        transport,
        config,
        selection.url,
        target,
        source_name,
        "selected_csv",
        observed_at,
        MAX_CSV_BYTES,
        output,
        dataset_year=selection.dataset_year,
        effective_date=selection.effective_date,
    )


def select_dated_official_csv(
    dataset_id: str,
    landing_url: str,
    html: str,
    *,
    evidence_cutoff: date,
) -> SecCsvSelection:
    """Select the unique latest cutoff candidate, then require its exact template."""

    if dataset_id not in LANDING_PAGES or landing_url != LANDING_PAGES[dataset_id]:
        raise ValueError("unknown SEC landing dataset")
    parser = _LandingTableParser()
    parser.feed(html)
    signatures = [_table_header_signature(table) for table in parser.tables]
    matches = [
        (ordinal, table, signature)
        for ordinal, (table, signature) in enumerate(
            zip(parser.tables, signatures, strict=True), start=1
        )
        if signature == ("file", "format", "size")
    ]
    if not parser.tables:
        _raise_discovery(
            "download_table_not_found", dataset_id, landing_url, parser.tables, (), 0, 0, ()
        )
    if not matches:
        _raise_discovery(
            "download_table_not_found", dataset_id, landing_url, parser.tables, (), 0, 0, ()
        )
    if len(matches) != 1:
        _raise_discovery(
            "download_table_ambiguous", dataset_id, landing_url, parser.tables,
            ("file", "format", "size"), 0, 0, (),
        )

    table_ordinal, table, signature = matches[0]
    rows_scanned = 0
    rows_with_anchors = 0
    diagnostics: list[SecCsvCandidateDiagnostic] = []
    candidates: list[_CsvCandidate] = []
    blocker_codes: list[str] = []

    for row_index, row in enumerate(table, start=1):
        if any(cell.is_header for cell in row):
            continue
        rows_scanned += 1
        anchor_count = sum(len(cell.links) for cell in row)
        rows_with_anchors += bool(anchor_count)
        if len(row) != 3:
            blocker_codes.append("row_shape_invalid")
            continue
        file_cell, format_cell, size_cell = row
        normalized_format = _normalized_header(format_cell.text)
        if normalized_format != "csv":
            continue
        diagnostic = SecCsvCandidateDiagnostic(
            dataset_id=dataset_id,
            candidate_ordinal=len(diagnostics) + 1,
            download_table_ordinal=table_ordinal,
            table_row_index=row_index,
            normalized_format=normalized_format,
            normalized_size_text=_safe_size_text(size_cell.text),
            file_year=None,
            updated_date=None,
            anchor_count=len(file_cell.links),
            temporal_relation="unknown",
            baseline_url_status="not_evaluated",
            template_status="not_evaluated",
            reason_code=None,
            action="hard_fail",
            normalized_path=None,
            path_basename=None,
        )
        if len(file_cell.links) != 1:
            diagnostics.append(replace(diagnostic, reason_code="anchor_cardinality_invalid"))
            blocker_codes.append("anchor_cardinality_invalid")
            continue
        href, anchor_text = file_cell.links[0]
        year = _file_year(anchor_text)
        if year is None:
            diagnostics.append(replace(diagnostic, reason_code="file_year_missing"))
            blocker_codes.append("file_year_missing")
            continue
        diagnostic = replace(diagnostic, file_year=year)

        updated: date | None = None
        date_failure: str | None = None
        try:
            updated = _updated_date(file_cell.text)
        except _UpdatedDateError as exc:
            date_failure = exc.reason_code
        diagnostic = replace(
            diagnostic, updated_date=updated.isoformat() if updated is not None else None
        )

        baseline = _analyze_baseline_url(landing_url, href)
        if baseline.failure_code is not None or baseline.canonical_url is None:
            diagnostics.append(
                replace(
                    diagnostic,
                    baseline_url_status="failed",
                    reason_code=str(
                        baseline.failure_code or SecCsvUrlFailureCode.MALFORMED_URL
                    ),
                )
            )
            blocker_codes.append("baseline_url_safety_failure")
            continue
        template = _analyze_exact_template(dataset_id, baseline.canonical_url, year)
        diagnostic = replace(
            diagnostic,
            baseline_url_status="passed",
            template_status=template.status,
            normalized_path=baseline.normalized_path,
            path_basename=baseline.path_basename,
        )
        if date_failure is not None:
            diagnostics.append(replace(diagnostic, reason_code=date_failure))
            blocker_codes.append(date_failure)
            continue
        if updated is not None and updated.year != year:
            diagnostics.append(replace(diagnostic, reason_code="file_year_date_mismatch"))
            blocker_codes.append("file_year_date_mismatch")
            continue
        if (
            template.failure_code is not None
            and template.failure_code is not SecCsvUrlFailureCode.PATH_TEMPLATE_MISMATCH
        ):
            diagnostics.append(replace(diagnostic, reason_code=str(template.failure_code)))
            blocker_codes.append(str(template.failure_code))
            continue
        diagnostic_index = len(diagnostics)
        diagnostics.append(replace(diagnostic, action="ignored_warning"))
        candidates.append(
            _CsvCandidate(year, updated, baseline.canonical_url, template, diagnostic_index)
        )

    observed_cutoff_dates = [
        date.fromisoformat(item.updated_date)
        for item in diagnostics
        if item.file_year is not None
        and item.updated_date is not None
        and date.fromisoformat(item.updated_date).year == item.file_year
        and date.fromisoformat(item.updated_date) <= evidence_cutoff
    ]
    if observed_cutoff_dates:
        observed_latest = max(observed_cutoff_dates)
        if any(
            item.updated_date == observed_latest.isoformat()
            and item.baseline_url_status == "failed"
            for item in diagnostics
        ):
            blocker_codes.append("selected_href_rejected")

    if not diagnostics:
        reason = _preferred_failure(blocker_codes) or "no_csv_candidate"
        diagnostic = _make_diagnostic_v3(
            dataset_id, landing_url, parser.tables, signature,
            rows_scanned, rows_with_anchors, (), status="failed",
            failure_code=reason,
            global_blocking_count=sum(
                code == "row_shape_invalid" for code in blocker_codes
            ),
        )
        raise SecLandingDiscoveryError(reason, diagnostic)

    dated_cutoff = [
        candidate for candidate in candidates
        if candidate.effective_date is not None
        and candidate.effective_date <= evidence_cutoff
    ]
    if not dated_cutoff:
        for candidate in candidates:
            item = diagnostics[candidate.diagnostic_index]
            if candidate.effective_date is None:
                diagnostics[candidate.diagnostic_index] = replace(
                    item,
                    temporal_relation="unknown",
                    reason_code="current_candidate_date_missing",
                    action="hard_fail",
                )
                blocker_codes.append("current_candidate_date_missing")
            elif candidate.effective_date > evidence_cutoff:
                if candidate.template.status == "matched":
                    diagnostics[candidate.diagnostic_index] = replace(
                        item,
                        temporal_relation="future",
                        reason_code="future_candidate_excluded",
                        action="ignored_warning",
                    )
                else:
                    diagnostics[candidate.diagnostic_index] = replace(
                        item,
                        temporal_relation="future",
                        reason_code="same_or_newer_href_rejected",
                        action="hard_fail",
                    )
                    blocker_codes.append("same_or_newer_href_rejected")
        reason = _preferred_failure(blocker_codes) or (
            "current_candidate_date_missing"
            if any(candidate.effective_date is None for candidate in candidates)
            else "no_cutoff_eligible_candidate"
        )
        diagnostic = _make_diagnostic_v3(
            dataset_id, landing_url, parser.tables, signature,
            rows_scanned, rows_with_anchors, diagnostics,
            status="failed", failure_code=reason,
        )
        raise SecLandingDiscoveryError(reason, diagnostic)

    latest_date = max(
        candidate.effective_date for candidate in dated_cutoff
        if candidate.effective_date is not None
    )
    latest = [candidate for candidate in dated_cutoff if candidate.effective_date == latest_date]
    distinct_latest_urls = {candidate.url for candidate in latest}
    if len(distinct_latest_urls) != 1:
        for candidate in latest:
            diagnostics[candidate.diagnostic_index] = replace(
                diagnostics[candidate.diagnostic_index],
                temporal_relation="same",
                reason_code="max_date_distinct_url_tie",
                action="hard_fail",
            )
        blocker_codes.append("max_date_distinct_url_tie")

    selected_url = min(distinct_latest_urls)
    selected_group = sorted(
        (candidate for candidate in latest if candidate.url == selected_url),
        key=lambda candidate: candidate.diagnostic_index,
    )
    selected = selected_group[0]

    for candidate in candidates:
        item = diagnostics[candidate.diagnostic_index]
        if candidate.effective_date is None:
            if candidate.dataset_year < selected.dataset_year:
                diagnostics[candidate.diagnostic_index] = replace(
                    item, temporal_relation="older",
                    reason_code="undated_historical_ignored", action="ignored_warning",
                )
            else:
                diagnostics[candidate.diagnostic_index] = replace(
                    item,
                    temporal_relation=(
                        "same" if candidate.dataset_year == selected.dataset_year else "newer"
                    ),
                    reason_code="current_candidate_date_missing", action="hard_fail",
                )
                blocker_codes.append("current_candidate_date_missing")
            continue
        if candidate.effective_date > evidence_cutoff:
            if candidate.template.status != "matched":
                diagnostics[candidate.diagnostic_index] = replace(
                    item, temporal_relation="future",
                    reason_code="same_or_newer_href_rejected", action="hard_fail",
                )
                blocker_codes.append("same_or_newer_href_rejected")
            else:
                diagnostics[candidate.diagnostic_index] = replace(
                    item, temporal_relation="future",
                    reason_code="future_candidate_excluded", action="ignored_warning",
                )
            continue

        relation = "older" if candidate.effective_date < latest_date else "same"
        if candidate.effective_date < latest_date:
            reason = (
                "eligible_not_selected"
                if candidate.template.status == "matched"
                else "historical_path_template_mismatch_ignored"
            )
            diagnostics[candidate.diagnostic_index] = replace(
                item, temporal_relation=relation, reason_code=reason,
                action="ignored_warning",
            )
            continue
        if candidate.url != selected.url:
            diagnostics[candidate.diagnostic_index] = replace(
                item, temporal_relation="same",
                reason_code="max_date_distinct_url_tie", action="hard_fail",
            )
            continue
        if candidate.diagnostic_index != selected.diagnostic_index:
            diagnostics[candidate.diagnostic_index] = replace(
                item, temporal_relation="same",
                reason_code="duplicate_candidate_ignored", action="ignored_warning",
            )
            continue
        if candidate.template.status != "matched":
            diagnostics[candidate.diagnostic_index] = replace(
                item, temporal_relation="same",
                reason_code="selected_path_template_mismatch", action="hard_fail",
            )
            blocker_codes.append("selected_path_template_mismatch")
        else:
            diagnostics[candidate.diagnostic_index] = replace(
                item, temporal_relation="same", reason_code="selected", action="selected",
            )

    failure = _preferred_failure(blocker_codes)
    if failure is not None:
        diagnostics = [
            replace(item, action="ignored_warning", reason_code="selection_blocked")
            if item.action == "selected" else item
            for item in diagnostics
        ]
        diagnostic = _make_diagnostic_v3(
            dataset_id, landing_url, parser.tables, signature,
            rows_scanned, rows_with_anchors, diagnostics,
            status="failed", failure_code=failure,
            max_date_candidate_count=len(distinct_latest_urls),
            global_blocking_count=sum(
                code == "row_shape_invalid" for code in blocker_codes
            ),
        )
        raise SecLandingDiscoveryError(failure, diagnostic)

    fingerprint = _selection_fingerprint(
        dataset_id, selected.dataset_year, latest_date, selected.url,
        selected.template.template_id, diagnostics,
    )
    diagnostic = _make_diagnostic_v3(
        dataset_id, landing_url, parser.tables, signature,
        rows_scanned, rows_with_anchors, diagnostics,
        status="selected", selected_year=selected.dataset_year,
        selected_date=latest_date.isoformat(),
        selected_template_id=selected.template.template_id,
        selection_fingerprint=fingerprint,
        max_date_candidate_count=len(distinct_latest_urls),
    )
    if diagnostic.selected_count != 1:
        raise SecTransportError("SEC selected CSV discovery invariant failed")
    return SecCsvSelection(
        dataset_id=dataset_id, url=selected.url,
        dataset_year=selected.dataset_year, effective_date=latest_date,
        selection_reason_code="selected",
        total_csv_candidate_count=diagnostic.csv_candidate_count,
        eligible_count=diagnostic.cutoff_eligible_count,
        future_dated_count=diagnostic.future_candidate_count,
        selection_fingerprint=fingerprint, diagnostic=diagnostic,
    )


def _table_header_signature(table: list[list[_LandingCell]]) -> tuple[str, ...]:
    signatures = [
        tuple(_normalized_header(cell.text) for cell in row)
        for row in table if row and all(cell.is_header for cell in row)
    ]
    return signatures[0] if len(signatures) == 1 else ()


def _normalized_header(value: str) -> str:
    return _collapse(value.replace("\xa0", " ")).casefold()


def _file_year(anchor_text: str) -> int | None:
    match = re.fullmatch(r"\s*((?:19|20)\d{2})\s*", anchor_text)
    return int(match.group(1)) if match else None


class _UpdatedDateError(ValueError):
    def __init__(self, reason_code: str) -> None:
        super().__init__("SEC landing-page updated date is invalid")
        self.reason_code = reason_code


def _updated_date(text: str) -> date | None:
    normalized = _collapse(text.replace("\xa0", " "))
    if "updated" not in normalized.casefold():
        return None
    values = re.findall(
        r"(?i)\bupdated\s+(\d{1,2}/\d{1,2}/(?:\d{2}|\d{4}))\b", normalized
    )
    if not values:
        raise _UpdatedDateError("updated_date_parse_failed")
    parsed: set[date] = set()
    for value in values:
        try:
            month, day, year = (int(part) for part in value.split("/"))
            year = 2000 + year if year < 100 else year
            parsed.add(date(year, month, day))
        except ValueError:
            raise _UpdatedDateError("updated_date_parse_failed") from None
    if len(parsed) != 1:
        raise _UpdatedDateError("multiple_dates_in_row")
    return next(iter(parsed))


def _canonical_csv_url(dataset_id: str, landing_url: str, href: str, year: int) -> str:
    baseline = _analyze_baseline_url(landing_url, href)
    if baseline.failure_code is not None or baseline.canonical_url is None:
        raise _SecCsvUrlValidationError(
            baseline.failure_code or SecCsvUrlFailureCode.MALFORMED_URL
        )
    template = _analyze_exact_template(dataset_id, baseline.canonical_url, year)
    if template.failure_code is not None:
        raise _SecCsvUrlValidationError(template.failure_code)
    return baseline.canonical_url


def _analyze_baseline_url(landing_url: str, href: str) -> _CsvUrlAnalysis:
    def rejected(code: SecCsvUrlFailureCode) -> _CsvUrlAnalysis:
        return _CsvUrlAnalysis(None, code, None, None)

    if (
        not isinstance(href, str) or not href
        or any(ord(char) < 32 or ord(char) == 127 for char in href)
    ):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    if "\\" in href:
        return rejected(SecCsvUrlFailureCode.BACKSLASH_PRESENT)
    try:
        raw = urlparse(href)
        raw_port = raw.port
    except (TypeError, ValueError):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    if raw.scheme not in {"", "https"} or (raw.netloc and raw.scheme != "https"):
        return rejected(SecCsvUrlFailureCode.SCHEME_NOT_HTTPS)
    if raw.username is not None or raw.password is not None:
        return rejected(SecCsvUrlFailureCode.USERINFO_PRESENT)
    if raw.hostname is not None and raw.hostname != "www.sec.gov":
        return rejected(SecCsvUrlFailureCode.HOST_NOT_ALLOWED)
    if raw_port not in {None, 443}:
        return rejected(SecCsvUrlFailureCode.NONSTANDARD_PORT)
    if raw.query:
        return rejected(SecCsvUrlFailureCode.QUERY_PRESENT)
    if raw.fragment:
        return rejected(SecCsvUrlFailureCode.FRAGMENT_PRESENT)
    if _has_literal_traversal(raw.path):
        return rejected(SecCsvUrlFailureCode.TRAVERSAL_PRESENT)
    decoded_once = unquote(raw.path)
    decoded_twice = unquote(decoded_once)
    if any(
        any(ord(char) < 32 or ord(char) == 127 for char in value)
        for value in (decoded_once, decoded_twice)
    ):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    if "\\" in decoded_once or "\\" in decoded_twice:
        return rejected(SecCsvUrlFailureCode.ENCODED_TRAVERSAL_PRESENT)
    if _has_literal_traversal(decoded_once) or _has_literal_traversal(decoded_twice):
        return rejected(SecCsvUrlFailureCode.ENCODED_TRAVERSAL_PRESENT)
    if decoded_once != raw.path:
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    try:
        resolved = urljoin(landing_url, href)
        parsed = urlparse(resolved)
        resolved_port = parsed.port
    except (TypeError, ValueError):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    if parsed.scheme != "https":
        return rejected(SecCsvUrlFailureCode.SCHEME_NOT_HTTPS)
    if parsed.username is not None or parsed.password is not None:
        return rejected(SecCsvUrlFailureCode.USERINFO_PRESENT)
    if parsed.hostname != "www.sec.gov":
        return rejected(SecCsvUrlFailureCode.HOST_NOT_ALLOWED)
    if resolved_port not in {None, 443}:
        return rejected(SecCsvUrlFailureCode.NONSTANDARD_PORT)
    if parsed.query:
        return rejected(SecCsvUrlFailureCode.QUERY_PRESENT)
    if parsed.fragment:
        return rejected(SecCsvUrlFailureCode.FRAGMENT_PRESENT)
    if not parsed.path.startswith("/files/investment/data/other/"):
        return rejected(SecCsvUrlFailureCode.PATH_ROOT_NOT_ALLOWED)
    if not parsed.path.casefold().endswith(".csv"):
        return rejected(SecCsvUrlFailureCode.EXTENSION_NOT_CSV)
    try:
        validate_sec_url(resolved)
    except SecTransportError:
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    public_path = _safe_public_path(parsed.path)
    if public_path is None:
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    return _CsvUrlAnalysis(
        f"https://www.sec.gov{parsed.path}", None, public_path,
        PurePosixPath(public_path).name,
    )


def _analyze_exact_template(
    dataset_id: str, canonical_url: str, year: int
) -> _CsvTemplateAnalysis:
    if dataset_id not in CSV_PATH_TEMPLATES:
        return _CsvTemplateAnalysis(
            "failed", None, SecCsvUrlFailureCode.PATH_TEMPLATE_MISMATCH
        )
    path = urlparse(canonical_url).path
    template = CSV_PATH_TEMPLATES[dataset_id]
    prefix, suffix = template.split("{year}", maxsplit=1)
    match = re.fullmatch(
        f"{re.escape(prefix)}((?:19|20)\\d{{2}}){re.escape(suffix)}", path
    )
    if match is not None and int(match.group(1)) != year:
        return _CsvTemplateAnalysis(
            "failed", None, SecCsvUrlFailureCode.FILE_YEAR_MISMATCH
        )
    if path == template.format(year=year):
        return _CsvTemplateAnalysis("matched", "modern_year_template", None)
    if (
        dataset_id == "investment_company_series_class" and year == 2024
        and path == SERIES_CLASS_2024_LEGACY_PATH
    ):
        return _CsvTemplateAnalysis("matched", "series_class_2024_legacy", None)
    if (
        dataset_id == "investment_company_series_class" and year == 2023
        and path == SERIES_CLASS_2023_UNDERSCORE_PATH
    ):
        return _CsvTemplateAnalysis("matched", "series_class_2023_underscore", None)
    return _CsvTemplateAnalysis(
        "failed", None, SecCsvUrlFailureCode.PATH_TEMPLATE_MISMATCH
    )


def _safe_public_path(value: str) -> str | None:
    if (
        not value or len(value) > 512
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        return None
    return value if value.startswith("/") else None


def _has_literal_traversal(value: str) -> bool:
    return ".." in PurePosixPath(value).parts


def _safe_size_text(value: str) -> str | None:
    normalized = _collapse(value.replace("\xa0", " ")).upper()
    if not normalized:
        return None
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|BYTE|BYTES)", normalized)
    return f"{match.group(1)} {match.group(2)}" if match else None


def _preferred_failure(codes: Iterable[str]) -> str | None:
    values = set(codes)
    priority = (
        "max_date_distinct_url_tie", "selected_href_rejected",
        "baseline_url_safety_failure",
        "selected_path_template_mismatch", "same_or_newer_href_rejected",
        "updated_date_parse_failed", "multiple_dates_in_row",
        "file_year_date_mismatch", "file_year_mismatch",
        "current_candidate_date_missing",
        "anchor_cardinality_invalid", "file_year_missing", "row_shape_invalid",
    )
    return next((code for code in priority if code in values), None)


def _selection_fingerprint(
    dataset_id: str,
    selected_year: int,
    selected_date: date,
    selected_url: str,
    selected_template_id: str | None,
    candidates: Iterable[SecCsvCandidateDiagnostic],
) -> str:
    safe_candidates = sorted(
        (
            item.file_year if item.file_year is not None else -1,
            item.updated_date or "",
            item.normalized_path or "",
            item.baseline_url_status, item.template_status,
            item.temporal_relation, item.reason_code or "", item.action,
        )
        for item in candidates
    )
    payload = {
        "dataset_id": dataset_id, "selected_year": selected_year,
        "selected_date": selected_date.isoformat(),
        "selected_path": urlparse(selected_url).path,
        "selected_template_id": selected_template_id,
        "candidates": safe_candidates,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _make_diagnostic_v3(
    dataset_id: str,
    landing_url: str,
    tables: list[list[list[_LandingCell]]],
    signature: tuple[str, ...],
    rows_scanned: int,
    rows_with_anchors: int,
    candidate_diagnostics: Iterable[SecCsvCandidateDiagnostic],
    *,
    status: str,
    failure_code: str | None = None,
    selected_year: int | None = None,
    selected_date: str | None = None,
    selected_template_id: str | None = None,
    selection_fingerprint: str | None = None,
    max_date_candidate_count: int = 0,
    global_blocking_count: int = 0,
) -> SecLandingDiscoveryDiagnostic:
    candidates = tuple(candidate_diagnostics)
    warning_codes = tuple(sorted({
        item.reason_code for item in candidates
        if item.action == "ignored_warning"
        and item.reason_code in {
            "historical_path_template_mismatch_ignored",
            "undated_historical_ignored",
        }
    }))
    return SecLandingDiscoveryDiagnostic(
        schema_version="3.0", dataset_id=dataset_id,
        page_id=Path(urlparse(landing_url).path).name,
        table_count=len(tables), normalized_header_signature=signature,
        rows_scanned=rows_scanned, rows_with_anchors=rows_with_anchors,
        csv_candidate_count=len(candidates),
        baseline_safe_count=sum(
            item.baseline_url_status == "passed" for item in candidates
        ),
        exact_allowlisted_count=sum(
            item.template_status == "matched" for item in candidates
        ),
        blocking_rejection_count=(
            sum(item.action == "hard_fail" for item in candidates)
            + global_blocking_count
        ),
        historical_path_warning_count=sum(
            item.reason_code == "historical_path_template_mismatch_ignored"
            and item.action == "ignored_warning" for item in candidates
        ),
        undated_historical_warning_count=sum(
            item.reason_code == "undated_historical_ignored"
            and item.action == "ignored_warning" for item in candidates
        ),
        cutoff_eligible_count=sum(
            item.baseline_url_status == "passed"
            and item.updated_date is not None
            and item.temporal_relation != "future" for item in candidates
            if item.reason_code != "duplicate_candidate_ignored"
        ),
        future_candidate_count=sum(
            item.temporal_relation == "future" for item in candidates
        ),
        max_date_candidate_count=max_date_candidate_count,
        selected_count=sum(item.action == "selected" for item in candidates),
        selected_year=selected_year, selected_date=selected_date,
        selected_template_id=selected_template_id, status=status,
        failure_code=failure_code, warning_codes=warning_codes,
        selection_fingerprint=selection_fingerprint,
        candidate_diagnostics=candidates,
    )


def _raise_discovery(
    reason: str,
    dataset_id: str,
    landing_url: str,
    tables: list[list[list[_LandingCell]]],
    signature: tuple[str, ...],
    rows_scanned: int,
    rows_with_anchors: int,
    candidates: Iterable[SecCsvCandidateDiagnostic],
) -> None:
    diagnostic = _make_diagnostic_v3(
        dataset_id, landing_url, tables, signature,
        rows_scanned, rows_with_anchors, candidates,
        status="failed", failure_code=reason, global_blocking_count=1,
    )
    raise SecLandingDiscoveryError(reason, diagnostic)


def read_landing_discovery_diagnostic(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return an audit-safe copy of historical schema 2.0 or current schema 3.0."""

    copy = json.loads(json.dumps(dict(value)))
    if copy.get("schema_version") not in {"2.0", "3.0"}:
        raise ValueError("unsupported SEC landing diagnostic schema")
    return copy


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _validate_tabular_json(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), list) or not isinstance(payload.get("data"), list):
        raise SecTransportError("SEC JSON source has an unexpected format")
    if not payload["fields"] or len(set(map(str, payload["fields"]))) != len(payload["fields"]):
        raise SecTransportError("SEC JSON source fields are invalid")


def parse_tabular_json(path: Path) -> tuple[dict[str, Any], ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = tuple(str(item) for item in payload["fields"])
    rows: list[dict[str, Any]] = []
    for values in payload["data"]:
        if not isinstance(values, list) or len(values) != len(fields):
            raise SecTransportError("SEC JSON source row has an unexpected format")
        rows.append(dict(zip(fields, values, strict=True)))
    return tuple(rows)


def validate_selected_csv_response(selection: SecCsvSelection, content_type: str, path: Path) -> None:
    """Validate a downloaded CSV only after strict landing-page selection."""

    _validate_selected_selection(selection)
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise SecTransportError("SEC selected CSV content type is invalid")
    if path.stat().st_size <= 0 or selection.dataset_id not in CSV_REQUIRED_HEADER_GROUPS:
        raise SecTransportError("SEC selected CSV source is invalid")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise SecTransportError("SEC CSV source is empty") from exc
    normalized = tuple(_normalized_header(item) for item in header)
    if not normalized or len(set(normalized)) != len(normalized):
        raise SecTransportError("SEC CSV source header is invalid")
    fields = set(normalized)
    if any(not (fields & alternatives) for alternatives in CSV_REQUIRED_HEADER_GROUPS[selection.dataset_id]):
        raise SecTransportError("SEC CSV source header does not match selected dataset")


def _validate_selected_selection(selection: SecCsvSelection) -> None:
    diagnostic = selection.diagnostic
    if (
        selection.dataset_id not in LANDING_PAGES
        or selection.dataset_id not in CSV_REQUIRED_HEADER_GROUPS
        or selection.selection_reason_code != "selected"
        or diagnostic.schema_version != "3.0"
        or diagnostic.status != "selected"
        or diagnostic.failure_code is not None
        or diagnostic.selected_count != 1
        or diagnostic.selected_year != selection.dataset_year
        or diagnostic.selected_date != selection.effective_date.isoformat()
        or diagnostic.selection_fingerprint != selection.selection_fingerprint
        or diagnostic.csv_candidate_count != selection.total_csv_candidate_count
        or diagnostic.cutoff_eligible_count != selection.eligible_count
        or diagnostic.future_candidate_count != selection.future_dated_count
    ):
        raise SecTransportError("SEC selected CSV object is invalid")
    baseline = _analyze_baseline_url(LANDING_PAGES[selection.dataset_id], selection.url)
    if baseline.failure_code is not None or baseline.canonical_url != selection.url:
        raise SecTransportError("SEC selected CSV URL is invalid")
    template = _analyze_exact_template(
        selection.dataset_id, selection.url, selection.dataset_year
    )
    if (
        template.status != "matched"
        or template.failure_code is not None
        or template.template_id != diagnostic.selected_template_id
    ):
        raise SecTransportError("SEC selected CSV template is invalid")
    selected = [item for item in diagnostic.candidate_diagnostics if item.action == "selected"]
    if (
        len(selected) != 1
        or selected[0].file_year != selection.dataset_year
        or selected[0].updated_date != selection.effective_date.isoformat()
        or selected[0].normalized_path != urlparse(selection.url).path
        or selected[0].baseline_url_status != "passed"
        or selected[0].template_status != "matched"
    ):
        raise SecTransportError("SEC selected CSV diagnostic is invalid")
    expected_fingerprint = _selection_fingerprint(
        selection.dataset_id,
        selection.dataset_year,
        selection.effective_date,
        selection.url,
        diagnostic.selected_template_id,
        diagnostic.candidate_diagnostics,
    )
    if expected_fingerprint != selection.selection_fingerprint:
        raise SecTransportError("SEC selected CSV fingerprint is invalid")


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple({str(key).strip(): (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle))


def validate_submissions_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_ZIP_MEMBERS:
                raise SecTransportError("SEC submissions ZIP member count is invalid")
            total = 0
            normalized_names: set[str] = set()
            for member in members:
                match = _validate_submissions_member(member, normalized_names)
                if member.file_size > MAX_ZIP_MEMBER_BYTES:
                    raise SecTransportError("SEC submissions ZIP member exceeds size limit")
                total += member.file_size
                if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
                    raise SecTransportError("SEC submissions ZIP exceeds expansion limit")
                payload = _read_bounded_zip_member(archive, member)
                _validate_submission_payload(payload, match.group("cik"))
    except SecTransportError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, UnicodeError, ValueError) as exc:
        raise SecTransportError("SEC submissions ZIP is invalid") from exc


def _validate_submissions_member(
    member: zipfile.ZipInfo,
    normalized_names: set[str],
) -> re.Match[str]:
    raw_name = member.filename
    if member.flag_bits & 0x1:
        raise SecTransportError("SEC submissions ZIP contains an encrypted member")
    if "\\" in raw_name:
        raise SecTransportError("SEC submissions ZIP contains an unsafe member path")
    decoded_name = raw_name
    for _ in range(3):
        next_name = unquote(decoded_name)
        if next_name == decoded_name:
            break
        decoded_name = next_name
    raw_path = PurePosixPath(raw_name)
    decoded_path = PurePosixPath(decoded_name)
    if (
        raw_path.is_absolute()
        or decoded_path.is_absolute()
        or ".." in raw_path.parts
        or ".." in decoded_path.parts
    ):
        raise SecTransportError("SEC submissions ZIP contains an unsafe member path")
    normalized_name = unicodedata.normalize("NFC", decoded_name).casefold()
    if normalized_name in normalized_names:
        raise SecTransportError("SEC submissions ZIP contains duplicate members")
    normalized_names.add(normalized_name)
    mode = member.external_attr >> 16
    member_type = stat.S_IFMT(mode)
    if member.is_dir() or member_type not in {0, stat.S_IFREG}:
        raise SecTransportError("SEC submissions ZIP contains a non-regular member")
    if len(decoded_path.parts) != 1:
        raise SecTransportError("SEC submissions ZIP member name is invalid")
    match = SUBMISSIONS_MEMBER_PATTERN.fullmatch(decoded_path.name)
    if match is None or decoded_name != raw_name:
        raise SecTransportError("SEC submissions ZIP member name is invalid")
    if member.compress_size == 0:
        if member.file_size != 0:
            raise SecTransportError("SEC submissions ZIP compression metadata is invalid")
    elif member.file_size / member.compress_size > MAX_ZIP_COMPRESSION_RATIO:
        raise SecTransportError("SEC submissions ZIP compression ratio exceeds limit")
    return match


def _read_bounded_zip_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> bytes:
    chunks: list[bytes] = []
    total = 0
    with archive.open(member) as handle:
        while True:
            chunk = handle.read(ZIP_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ZIP_MEMBER_BYTES or total > member.file_size:
                raise SecTransportError("SEC submissions ZIP member exceeds bounded size")
            chunks.append(chunk)
    if total != member.file_size:
        raise SecTransportError("SEC submissions ZIP member size mismatch")
    return b"".join(chunks)


def _validate_submission_payload(payload: bytes, expected_cik: str) -> None:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecTransportError("SEC submissions member JSON is invalid") from exc
    if not isinstance(value, dict):
        raise SecTransportError("SEC submissions member root is invalid")
    cik = value.get("cik")
    filings = value.get("filings")
    cik_text = str(cik) if isinstance(cik, (str, int)) and not isinstance(cik, bool) else ""
    if not cik_text.isdigit() or cik_text.zfill(10) != expected_cik or not isinstance(filings, dict):
        raise SecTransportError("SEC submissions member schema is invalid")
    recent = filings.get("recent")
    files = filings.get("files")
    if recent is not None and not isinstance(recent, dict):
        raise SecTransportError("SEC submissions recent filings schema is invalid")
    if files is not None and not isinstance(files, list):
        raise SecTransportError("SEC submissions historical files schema is invalid")


def iter_selected_submissions(path: Path, ciks: set[str]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    wanted = {f"CIK{str(cik).zfill(10)}.json" for cik in ciks}
    with zipfile.ZipFile(path) as archive:
        for name in sorted(wanted & set(archive.namelist())):
            info = archive.getinfo(name)
            if info.file_size > MAX_ZIP_MEMBER_BYTES:
                raise SecTransportError("SEC submissions member exceeds size limit")
            with archive.open(info) as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise SecTransportError("SEC submissions member has an unexpected format")
            yield name[3:-5], payload


def source_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise SecTransportError("SEC source cache root is unavailable")
    return root.resolve()


def _write_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
