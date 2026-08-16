"""Bounded SEC bulk-source acquisition and safe offline parsing."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
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


@dataclass(frozen=True, slots=True)
class SecCachedSource:
    source_name: str
    url: str
    file_name: str
    observed_at: str
    content_type: str
    compressed_size: int
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
    parsed_file_year: int | None
    parsed_updated_date: str | None
    anchor_count: int
    selection_state: str
    url_validation_state: str
    failure_code: str | None
    normalized_path: str | None
    path_basename: str | None
    path_template_match: bool | None
    query_present: bool
    fragment_present: bool
    userinfo_present: bool


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
    allowlisted_count: int
    parsed_date_count: int
    future_count: int
    undated_historical_count: int
    malformed_count: int
    rejected_count: int
    rejection_reason_counts: tuple[tuple[str, int], ...]
    cutoff_eligible_count: int
    max_date_candidate_count: int
    selected_year: int | None = None
    selected_date: str | None = None
    selected_host: str | None = None
    selected_path_pattern: str | None = None
    candidate_diagnostics: tuple[SecCsvCandidateDiagnostic, ...] = ()

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


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
    path_template_match: bool | None
    query_present: bool
    fragment_present: bool
    userinfo_present: bool


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
        _download(transport, config, COMPANY_EXCHANGE_URL, staging / "company_tickers_exchange.json", "company_tickers_exchange", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_exchange.json")
        _download(transport, config, COMPANY_MF_URL, staging / "company_tickers_mf.json", "company_tickers_mf", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_mf.json")
        for source_name, landing_url in LANDING_PAGES.items():
            landing_file = staging / f"{source_name}.landing.html"
            _download(transport, config, landing_url, landing_file, f"{source_name}_landing", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
            selection = select_dated_official_csv(
                source_name,
                landing_url,
                landing_file.read_text(encoding="utf-8", errors="strict"),
                evidence_cutoff=as_of_date,
            )
            selections[source_name] = selection
            csv_file = staging / f"{source_name}.csv"
            downloaded = _download(
                transport, config, selection.url, csv_file, source_name, observed_at,
                MAX_CSV_BYTES, sources, dataset_year=selection.dataset_year,
                effective_date=selection.effective_date,
            )
            validate_selected_csv_response(selection, downloaded.content_type, csv_file)
        submissions = staging / "submissions.zip"
        _download(transport, config, SUBMISSIONS_URL, submissions, "submissions", observed_at, MAX_SUBMISSIONS_ZIP_BYTES, sources)
        validate_submissions_zip(submissions)
        manifest = {
            "schema_version": "1.0",
            "dataset_name": "sec-security-classification-source-cache",
            "completion_status": "completed",
            "as_of_date": as_of_date.isoformat(),
            "observed_at": observed_at.astimezone(UTC).isoformat(),
            "request_count": transport.request_count,
            "retry_count": transport.retry_count,
            "csv_selections": {
                name: {
                    "selected_url": selection.url,
                    "selected_dataset_year": selection.dataset_year,
                    "selected_effective_date": selection.effective_date.isoformat(),
                    "total_csv_candidate_count": selection.total_csv_candidate_count,
                    "eligible_count": selection.eligible_count,
                    "future_dated_count": selection.future_dated_count,
                    "discovery_diagnostic": selection.diagnostic.to_safe_dict(),
                }
                for name, selection in sorted(selections.items())
            },
            "sources": [asdict(item) for item in sorted(sources, key=lambda item: item.source_name)],
        }
        _write_json(staging / "manifest.json", manifest)
        if json.loads((staging / "manifest.json").read_text(encoding="utf-8")) != manifest:
            raise SecTransportError("SEC source cache manifest reread mismatch")
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
    observed_at: datetime,
    max_bytes: int,
    output: list[SecCachedSource],
    dataset_year: int | None = None,
    effective_date: date | None = None,
) -> SecCachedSource:
    result = transport.download(url, target, user_agent=config.user_agent, timeout_seconds=config.request_timeout_seconds, max_bytes=max_bytes)
    cached = SecCachedSource(
        source_name, result.url, target.name, observed_at.astimezone(UTC).isoformat(),
        result.content_type, result.byte_count, result.sha256, dataset_year,
        effective_date.isoformat() if effective_date else None,
    )
    output.append(cached)
    return cached


def select_dated_official_csv(
    dataset_id: str,
    landing_url: str,
    html: str,
    *,
    evidence_cutoff: date,
) -> SecCsvSelection:
    """Select one cutoff-eligible SEC CSV from the unique download table."""

    if dataset_id not in LANDING_PAGES or landing_url != LANDING_PAGES[dataset_id]:
        raise ValueError("unknown SEC landing dataset")
    parser = _LandingTableParser()
    parser.feed(html)
    stats: dict[str, int] = {
        "rows_scanned": 0, "rows_with_anchors": 0, "csv_candidate_count": 0,
        "allowlisted_count": 0, "parsed_date_count": 0, "future_count": 0,
        "undated_historical_count": 0, "malformed_count": 0,
        "rejected_count": 0, "cutoff_eligible_count": 0,
        "max_date_candidate_count": 0,
    }
    reasons: dict[str, int] = {}
    signatures = [_table_header_signature(table) for table in parser.tables]
    matches = [
        (ordinal, table, signature)
        for ordinal, (table, signature) in enumerate(zip(parser.tables, signatures, strict=True), start=1)
        if signature == ("file", "format", "size")
    ]
    candidate_diagnostics: list[SecCsvCandidateDiagnostic] = []
    if not parser.tables:
        _fail_discovery("download_table_not_found", dataset_id, landing_url, parser.tables, (), stats, reasons, candidate_diagnostics)
    if not matches:
        _fail_discovery("download_table_header_mismatch", dataset_id, landing_url, parser.tables, (), stats, reasons, candidate_diagnostics)
    if len(matches) != 1:
        _fail_discovery("download_table_ambiguous", dataset_id, landing_url, parser.tables, ("file", "format", "size"), stats, reasons, candidate_diagnostics)
    table_ordinal, table, signature = matches[0]
    candidates: list[_CsvCandidate] = []
    undated: list[_CsvCandidate] = []
    for row_index, row in enumerate(table, start=1):
        if any(cell.is_header for cell in row):
            continue
        stats["rows_scanned"] += 1
        anchor_count = sum(len(cell.links) for cell in row)
        if anchor_count:
            stats["rows_with_anchors"] += 1
        if len(row) != 3:
            _reject_or_fail("row_shape_invalid", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        file_cell, format_cell, size_cell = row
        normalized_format = _normalized_header(format_cell.text)
        if normalized_format != "csv":
            continue
        stats["csv_candidate_count"] += 1
        candidate_ordinal = stats["csv_candidate_count"]
        diagnostic = SecCsvCandidateDiagnostic(
            dataset_id=dataset_id,
            candidate_ordinal=candidate_ordinal,
            download_table_ordinal=table_ordinal,
            table_row_index=row_index,
            normalized_format=normalized_format,
            normalized_size_text=_safe_size_text(size_cell.text),
            parsed_file_year=None,
            parsed_updated_date=None,
            anchor_count=len(file_cell.links),
            selection_state="candidate",
            url_validation_state="not_evaluated",
            failure_code=None,
            normalized_path=None,
            path_basename=None,
            path_template_match=None,
            query_present=False,
            fragment_present=False,
            userinfo_present=False,
        )
        if len(file_cell.links) != 1:
            candidate_diagnostics.append(replace(diagnostic, selection_state="rejected", failure_code="anchor_cardinality_invalid"))
            _reject_or_fail("anchor_cardinality_invalid", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        href, anchor_text = file_cell.links[0]
        year = _file_year(anchor_text)
        if year is None:
            candidate_diagnostics.append(replace(diagnostic, selection_state="rejected", failure_code="file_year_missing"))
            _reject_or_fail("file_year_missing", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        diagnostic = replace(diagnostic, parsed_file_year=year)
        effective_date: date | None = None
        updated_date_error: _UpdatedDateError | None = None
        try:
            effective_date = _updated_date(file_cell.text)
        except _UpdatedDateError as exc:
            updated_date_error = exc
        diagnostic = replace(diagnostic, parsed_updated_date=effective_date.isoformat() if effective_date else None)
        analysis = _analyze_csv_url(dataset_id, landing_url, href, year)
        diagnostic = replace(
            diagnostic,
            url_validation_state="accepted" if analysis.failure_code is None else "rejected",
            failure_code=str(analysis.failure_code) if analysis.failure_code is not None else None,
            normalized_path=analysis.normalized_path,
            path_basename=analysis.path_basename,
            path_template_match=analysis.path_template_match,
            query_present=analysis.query_present,
            fragment_present=analysis.fragment_present,
            userinfo_present=analysis.userinfo_present,
        )
        if analysis.failure_code is not None or analysis.canonical_url is None:
            candidate_diagnostics.append(replace(diagnostic, selection_state="rejected"))
            detail = str(analysis.failure_code or SecCsvUrlFailureCode.MALFORMED_URL)
            reasons[detail] = reasons.get(detail, 0) + 1
            _reject_or_fail("href_rejected", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        url = analysis.canonical_url
        stats["allowlisted_count"] += 1
        if updated_date_error is not None:
            candidate_diagnostics.append(replace(diagnostic, selection_state="rejected", failure_code=updated_date_error.reason_code))
            _reject_or_fail(updated_date_error.reason_code, dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        diagnostic_index = len(candidate_diagnostics)
        candidate_diagnostics.append(diagnostic)
        candidate = _CsvCandidate(year, effective_date, url, diagnostic_index)
        if effective_date is None:
            candidate_diagnostics[diagnostic_index] = replace(diagnostic, selection_state="undated_pending")
            undated.append(candidate)
            continue
        if effective_date.year != year:
            candidate_diagnostics[diagnostic_index] = replace(diagnostic, selection_state="rejected", failure_code="file_year_date_mismatch")
            _reject_or_fail("file_year_date_mismatch", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        stats["parsed_date_count"] += 1
        if effective_date > evidence_cutoff:
            stats["future_count"] += 1
            candidate_diagnostics[diagnostic_index] = replace(diagnostic, selection_state="future_excluded")
        else:
            candidate_diagnostics[diagnostic_index] = replace(diagnostic, selection_state="cutoff_eligible")
            candidates.append(candidate)
    if stats["csv_candidate_count"] == 0:
        _fail_discovery("no_csv_candidate", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
    unique_by_key: dict[tuple[int, date | None, str], _CsvCandidate] = {}
    for candidate in candidates:
        unique_by_key.setdefault((candidate.dataset_year, candidate.effective_date, candidate.url), candidate)
    unique = sorted(unique_by_key.values(), key=lambda item: (item.effective_date or date.min, item.dataset_year, item.url))
    stats["cutoff_eligible_count"] = len(unique)
    if not unique:
        reason = "updated_date_missing_current_candidate" if undated else "no_cutoff_eligible_candidate"
        _fail_discovery(reason, dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
    latest_date = max(item.effective_date for item in unique if item.effective_date is not None)
    latest = [item for item in unique if item.effective_date == latest_date]
    distinct_urls = {item.url for item in latest}
    stats["max_date_candidate_count"] = len(distinct_urls)
    if len(distinct_urls) != 1:
        _fail_discovery("max_date_distinct_url_tie", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
    selected = min(latest, key=lambda item: (item.dataset_year, item.url))
    selected_key = (selected.dataset_year, selected.effective_date, selected.url)
    for candidate in candidates:
        state = "selected" if (candidate.dataset_year, candidate.effective_date, candidate.url) == selected_key else "eligible_not_selected"
        candidate_diagnostics[candidate.diagnostic_index] = replace(candidate_diagnostics[candidate.diagnostic_index], selection_state=state)
    for candidate in undated:
        if candidate.dataset_year >= selected.dataset_year:
            _fail_discovery("updated_date_missing_current_candidate", dataset_id, landing_url, parser.tables, signature, stats, reasons, candidate_diagnostics)
        stats["undated_historical_count"] += 1
        reasons["undated_historical_excluded"] = reasons.get("undated_historical_excluded", 0) + 1
        candidate_diagnostics[candidate.diagnostic_index] = replace(
            candidate_diagnostics[candidate.diagnostic_index], selection_state="undated_historical_excluded"
        )
    reasons["selected"] = 1
    diagnostic = _make_diagnostic(
        dataset_id, landing_url, parser.tables, signature, stats, reasons,
        selected_year=selected.dataset_year, selected_date=latest_date.isoformat(),
        selected_host="www.sec.gov", selected_path_pattern=Path(urlparse(selected.url).path).name,
        candidate_diagnostics=candidate_diagnostics,
    )
    return SecCsvSelection(
        dataset_id=dataset_id, url=selected.url, dataset_year=selected.dataset_year,
        effective_date=latest_date, selection_reason_code="selected",
        total_csv_candidate_count=stats["csv_candidate_count"],
        eligible_count=stats["cutoff_eligible_count"],
        future_dated_count=stats["future_count"], diagnostic=diagnostic,
    )


def _table_header_signature(table: list[list[_LandingCell]]) -> tuple[str, ...]:
    signatures = [tuple(_normalized_header(cell.text) for cell in row) for row in table if row and all(cell.is_header for cell in row)]
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
    values = re.findall(r"(?i)\bupdated\s+(\d{1,2}/\d{1,2}/(?:\d{2}|\d{4}))\b", normalized)
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
    analysis = _analyze_csv_url(dataset_id, landing_url, href, year)
    if analysis.failure_code is not None or analysis.canonical_url is None:
        raise _SecCsvUrlValidationError(analysis.failure_code or SecCsvUrlFailureCode.MALFORMED_URL)
    return analysis.canonical_url


def _analyze_csv_url(dataset_id: str, landing_url: str, href: str, year: int) -> _CsvUrlAnalysis:
    query_present = False
    fragment_present = False
    userinfo_present = False
    normalized_path: str | None = None
    path_basename: str | None = None
    template_match: bool | None = None

    def rejected(code: SecCsvUrlFailureCode) -> _CsvUrlAnalysis:
        return _CsvUrlAnalysis(
            None, code, normalized_path, path_basename, template_match,
            query_present, fragment_present, userinfo_present,
        )

    if not isinstance(href, str) or not href or any(ord(char) < 32 or ord(char) == 127 for char in href):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    if "\\" in href:
        return rejected(SecCsvUrlFailureCode.BACKSLASH_PRESENT)
    try:
        raw = urlparse(href)
        query_present = "?" in href.split("#", maxsplit=1)[0]
        fragment_present = "#" in href
        userinfo_present = raw.username is not None or raw.password is not None
        port = raw.port
        raw_hostname = raw.hostname
    except (TypeError, ValueError):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    normalized_path = _safe_public_path(raw.path)
    path_basename = PurePosixPath(normalized_path).name if normalized_path else None
    if raw.scheme.casefold() not in {"", "https"}:
        return rejected(SecCsvUrlFailureCode.SCHEME_NOT_HTTPS)
    if userinfo_present:
        return rejected(SecCsvUrlFailureCode.USERINFO_PRESENT)
    if raw_hostname is not None and raw_hostname.casefold() != "www.sec.gov":
        return rejected(SecCsvUrlFailureCode.HOST_NOT_ALLOWED)
    if port not in {None, 443}:
        return rejected(SecCsvUrlFailureCode.NONSTANDARD_PORT)
    if query_present:
        return rejected(SecCsvUrlFailureCode.QUERY_PRESENT)
    if fragment_present:
        return rejected(SecCsvUrlFailureCode.FRAGMENT_PRESENT)
    if _has_literal_traversal(raw.path):
        return rejected(SecCsvUrlFailureCode.TRAVERSAL_PRESENT)
    decoded_once = unquote(raw.path)
    if "\\" in decoded_once:
        return rejected(SecCsvUrlFailureCode.BACKSLASH_PRESENT)
    decoded_twice = unquote(decoded_once)
    if decoded_once != raw.path and (
        _has_literal_traversal(decoded_once)
        or _has_literal_traversal(decoded_twice)
        or "\\" in decoded_twice
    ):
        return rejected(SecCsvUrlFailureCode.ENCODED_TRAVERSAL_PRESENT)
    try:
        resolved = urljoin(landing_url, href)
        parsed = urlparse(resolved)
        resolved_port = parsed.port
    except (TypeError, ValueError):
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    normalized_path = _safe_public_path(parsed.path)
    path_basename = PurePosixPath(normalized_path).name if normalized_path else None
    if parsed.scheme != "https":
        return rejected(SecCsvUrlFailureCode.SCHEME_NOT_HTTPS)
    if parsed.username is not None or parsed.password is not None:
        userinfo_present = True
        return rejected(SecCsvUrlFailureCode.USERINFO_PRESENT)
    if parsed.hostname != "www.sec.gov":
        return rejected(SecCsvUrlFailureCode.HOST_NOT_ALLOWED)
    if resolved_port not in {None, 443}:
        return rejected(SecCsvUrlFailureCode.NONSTANDARD_PORT)
    if not parsed.path.casefold().endswith(".csv"):
        template_match = False
        return rejected(SecCsvUrlFailureCode.EXTENSION_NOT_CSV)
    template = CSV_PATH_TEMPLATES[dataset_id]
    prefix, suffix = template.split("{year}", maxsplit=1)
    path_match = re.fullmatch(f"{re.escape(prefix)}((?:19|20)\\d{{2}}){re.escape(suffix)}", parsed.path)
    if path_match is not None and int(path_match.group(1)) != year:
        template_match = False
        return rejected(SecCsvUrlFailureCode.FILE_YEAR_MISMATCH)
    expected_path = template.format(year=year)
    template_match = parsed.path == expected_path
    if not template_match:
        return rejected(SecCsvUrlFailureCode.PATH_TEMPLATE_MISMATCH)
    try:
        validate_sec_url(resolved)
    except SecTransportError:
        return rejected(SecCsvUrlFailureCode.MALFORMED_URL)
    return _CsvUrlAnalysis(
        f"https://www.sec.gov{parsed.path}", None, normalized_path, path_basename,
        True, query_present, fragment_present, userinfo_present,
    )


def _safe_public_path(value: str) -> str | None:
    if not value or len(value) > 512 or any(ord(char) < 32 or ord(char) == 127 for char in value):
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


def _reject_or_fail(
    reason: str,
    dataset_id: str,
    landing_url: str,
    tables: list[list[list[_LandingCell]]],
    signature: tuple[str, ...],
    stats: dict[str, int],
    reasons: dict[str, int],
    candidate_diagnostics: list[SecCsvCandidateDiagnostic],
) -> None:
    stats["malformed_count"] += 1
    stats["rejected_count"] += 1
    reasons[reason] = reasons.get(reason, 0) + 1
    _fail_discovery(reason, dataset_id, landing_url, tables, signature, stats, reasons, candidate_diagnostics)


def _fail_discovery(
    reason: str,
    dataset_id: str,
    landing_url: str,
    tables: list[list[list[_LandingCell]]],
    signature: tuple[str, ...],
    stats: dict[str, int],
    reasons: dict[str, int],
    candidate_diagnostics: list[SecCsvCandidateDiagnostic],
) -> None:
    reasons[reason] = reasons.get(reason, 0) + (0 if reason in reasons else 1)
    raise SecLandingDiscoveryError(
        reason,
        _make_diagnostic(
            dataset_id, landing_url, tables, signature, stats, reasons,
            candidate_diagnostics=candidate_diagnostics,
        ),
    )


def _make_diagnostic(
    dataset_id: str,
    landing_url: str,
    tables: list[list[list[_LandingCell]]],
    signature: tuple[str, ...],
    stats: dict[str, int],
    reasons: dict[str, int],
    *,
    selected_year: int | None = None,
    selected_date: str | None = None,
    selected_host: str | None = None,
    selected_path_pattern: str | None = None,
    candidate_diagnostics: Iterable[SecCsvCandidateDiagnostic] = (),
) -> SecLandingDiscoveryDiagnostic:
    return SecLandingDiscoveryDiagnostic(
        schema_version="2.0", dataset_id=dataset_id, page_id=Path(urlparse(landing_url).path).name,
        table_count=len(tables), normalized_header_signature=signature,
        rows_scanned=stats["rows_scanned"], rows_with_anchors=stats["rows_with_anchors"],
        csv_candidate_count=stats["csv_candidate_count"], allowlisted_count=stats["allowlisted_count"],
        parsed_date_count=stats["parsed_date_count"], future_count=stats["future_count"],
        undated_historical_count=stats["undated_historical_count"],
        malformed_count=stats["malformed_count"], rejected_count=stats["rejected_count"],
        rejection_reason_counts=tuple(sorted(reasons.items())),
        cutoff_eligible_count=stats["cutoff_eligible_count"], max_date_candidate_count=stats["max_date_candidate_count"],
        selected_year=selected_year, selected_date=selected_date, selected_host=selected_host,
        selected_path_pattern=selected_path_pattern,
        candidate_diagnostics=tuple(candidate_diagnostics),
    )


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

    if (
        selection.dataset_id not in LANDING_PAGES
        or selection.dataset_id not in CSV_REQUIRED_HEADER_GROUPS
        or selection.selection_reason_code != "selected"
        or _canonical_csv_url(
            selection.dataset_id,
            LANDING_PAGES[selection.dataset_id],
            selection.url,
            selection.dataset_year,
        ) != selection.url
    ):
        raise SecTransportError("SEC selected CSV URL is invalid")
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


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple({str(key).strip(): (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle))


def validate_submissions_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not members or len(members) > MAX_ZIP_MEMBERS:
            raise SecTransportError("SEC submissions ZIP member count is invalid")
        total = 0
        for member in members:
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts or member.is_dir() or member.external_attr >> 16 & 0o170000 == 0o120000:
                raise SecTransportError("SEC submissions ZIP contains an unsafe member")
            if len(name.parts) != 1 or not name.name.startswith("CIK") or not name.name.endswith(".json"):
                raise SecTransportError("SEC submissions ZIP member name is invalid")
            if member.file_size > MAX_ZIP_MEMBER_BYTES:
                raise SecTransportError("SEC submissions ZIP member exceeds size limit")
            total += member.file_size
            if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
                raise SecTransportError("SEC submissions ZIP exceeds expansion limit")


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
