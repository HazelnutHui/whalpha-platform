"""Bounded SEC bulk-source acquisition and safe offline parsing."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
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
    url: str
    dataset_year: int
    effective_date: date
    total_csv_candidate_count: int
    eligible_count: int
    future_dated_count: int


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
                landing_url,
                landing_file.read_text(encoding="utf-8", errors="strict"),
                evidence_cutoff=as_of_date,
            )
            selections[source_name] = selection
            csv_file = staging / f"{source_name}.csv"
            _download(
                transport, config, selection.url, csv_file, source_name, observed_at,
                MAX_CSV_BYTES, sources, dataset_year=selection.dataset_year,
                effective_date=selection.effective_date,
            )
            _validate_csv(csv_file)
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
) -> None:
    result = transport.download(url, target, user_agent=config.user_agent, timeout_seconds=config.request_timeout_seconds, max_bytes=max_bytes)
    output.append(SecCachedSource(
        source_name, result.url, target.name, observed_at.astimezone(UTC).isoformat(),
        result.content_type, result.byte_count, result.sha256, dataset_year,
        effective_date.isoformat() if effective_date else None,
    ))


def select_dated_official_csv(landing_url: str, html: str, *, evidence_cutoff: date) -> SecCsvSelection:
    """Select the latest non-future CSV from a semantically labelled SEC data table."""

    parser = _LandingTableParser()
    parser.feed(html)
    candidates: list[tuple[date, int, str]] = []
    for table in parser.tables:
        header_text = " ".join(cell.text.lower() for row in table for cell in row if cell.is_header)
        if not _is_download_table(header_text):
            continue
        for row in table:
            csv_links = [
                href
                for cell in row
                for href, link_text in cell.links
                if _explicit_csv_link(cell.text, link_text, href)
            ]
            if not csv_links:
                continue
            row_text = " ".join(cell.text for cell in row)
            dataset_year = _dataset_year(row_text)
            effective_date = _effective_date(row_text)
            if dataset_year is None:
                raise SecTransportError("SEC CSV candidate is missing dataset year")
            if effective_date is None:
                raise SecTransportError("SEC CSV candidate date is missing or invalid")
            for href in csv_links:
                candidates.append((effective_date, dataset_year, _canonical_csv_url(landing_url, href)))
    if not candidates:
        raise SecTransportError("SEC landing page contains no dated official CSV candidate")
    unique = sorted(set(candidates), key=lambda item: (item[0], item[1], item[2]))
    eligible = [item for item in unique if item[0] <= evidence_cutoff]
    if not eligible:
        raise SecTransportError("SEC landing page contains no CSV eligible for the evidence cutoff")
    latest_date = max(item[0] for item in eligible)
    latest = [item for item in eligible if item[0] == latest_date]
    latest_urls = {item[2] for item in latest}
    if len(latest_urls) != 1:
        raise SecTransportError("SEC landing page has conflicting latest CSV candidates")
    selected = min(latest, key=lambda item: (item[1], item[2]))
    return SecCsvSelection(
        url=selected[2],
        dataset_year=selected[1],
        effective_date=selected[0],
        total_csv_candidate_count=len(unique),
        eligible_count=len(eligible),
        future_dated_count=len(unique) - len(eligible),
    )


def _is_download_table(header_text: str) -> bool:
    return (
        "year" in header_text
        and any(token in header_text for token in ("updated", "effective", "date"))
        and any(token in header_text for token in ("format", "download", "file"))
    )


def _explicit_csv_link(cell_text: str, link_text: str, href: str) -> bool:
    label = f" {cell_text.upper()} {link_text.upper()} "
    explicit = bool(re.search(r"\bCSV\b", label))
    path = urlparse(href).path.lower()
    return explicit and path.endswith(".csv")


def _dataset_year(text: str) -> int | None:
    values = {int(value) for value in re.findall(r"(?<![\d/])((?:19|20)\d{2})(?![\d/])", text)}
    if len(values) != 1:
        return None
    return next(iter(values))


def _effective_date(text: str) -> date | None:
    raw_dates = re.findall(r"(?<!\d)(\d{1,2}/\d{1,2}/(?:\d{2}|\d{4}))(?!\d)", text)
    parsed: set[date] = set()
    for raw in raw_dates:
        try:
            month, day, year = (int(part) for part in raw.split("/"))
            if year < 100:
                year += 2000
            parsed.add(date(year, month, day))
        except ValueError as exc:
            raise SecTransportError("SEC CSV candidate date is invalid") from exc
    if len(parsed) != 1:
        return None
    return next(iter(parsed))


def _canonical_csv_url(landing_url: str, href: str) -> str:
    if any(ord(char) < 32 for char in href) or "\\" in href:
        raise SecTransportError("SEC CSV URL is unsafe")
    raw = urlparse(href)
    decoded_path = unquote(raw.path)
    if ".." in PurePosixPath(decoded_path).parts or raw.scheme.lower() not in {"", "https"}:
        raise SecTransportError("SEC CSV URL is unsafe")
    resolved = urljoin(landing_url, href)
    validate_sec_url(resolved)
    parsed = urlparse(resolved)
    if parsed.hostname != "www.sec.gov" or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise SecTransportError("SEC CSV URL is not an approved official file")
    if not parsed.path.startswith("/files/") or not parsed.path.lower().endswith(".csv"):
        raise SecTransportError("SEC CSV path is outside the approved file namespace")
    return parsed.geturl()


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


def _validate_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise SecTransportError("SEC CSV source is empty") from exc
    if not header or len(set(item.strip().lower() for item in header)) != len(header):
        raise SecTransportError("SEC CSV source header is invalid")


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
