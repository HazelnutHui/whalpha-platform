"""Bounded SEC bulk-source acquisition and safe offline parsing."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin, urlparse

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


@dataclass(frozen=True, slots=True)
class SecSourceCacheResult:
    path: Path
    sources: tuple[SecCachedSource, ...]
    request_count: int
    retry_count: int
    status: str


class _CsvLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and ".csv" in href.lower():
            self.hrefs.append(href)


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
    try:
        staging.mkdir(mode=0o750)
        _download(transport, config, COMPANY_EXCHANGE_URL, staging / "company_tickers_exchange.json", "company_tickers_exchange", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_exchange.json")
        _download(transport, config, COMPANY_MF_URL, staging / "company_tickers_mf.json", "company_tickers_mf", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
        _validate_tabular_json(staging / "company_tickers_mf.json")
        for source_name, landing_url in LANDING_PAGES.items():
            landing_file = staging / f"{source_name}.landing.html"
            _download(transport, config, landing_url, landing_file, f"{source_name}_landing", observed_at, MAX_SMALL_SOURCE_BYTES, sources)
            csv_url = _extract_single_official_csv(landing_url, landing_file.read_text(encoding="utf-8", errors="strict"))
            csv_file = staging / f"{source_name}.csv"
            _download(transport, config, csv_url, csv_file, source_name, observed_at, MAX_CSV_BYTES, sources)
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
            "sources": [asdict(item) for item in sorted(sources, key=lambda item: item.source_name)],
        }
        _write_json(staging / "manifest.json", manifest)
        if json.loads((staging / "manifest.json").read_text(encoding="utf-8")) != manifest:
            raise SecTransportError("SEC source cache manifest reread mismatch")
        staging.replace(partition)
        return SecSourceCacheResult(partition, tuple(sorted(sources, key=lambda item: item.source_name)), transport.request_count, transport.retry_count, "published")
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
) -> None:
    result = transport.download(url, target, user_agent=config.user_agent, timeout_seconds=config.request_timeout_seconds, max_bytes=max_bytes)
    output.append(SecCachedSource(source_name, result.url, target.name, observed_at.astimezone(UTC).isoformat(), result.content_type, result.byte_count, result.sha256))


def _extract_single_official_csv(landing_url: str, html: str) -> str:
    parser = _CsvLinkParser()
    parser.feed(html)
    candidates = []
    for href in parser.hrefs:
        resolved = urljoin(landing_url, href)
        validate_sec_url(resolved)
        if urlparse(resolved).path.lower().endswith(".csv"):
            candidates.append(resolved)
    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise SecTransportError("SEC landing page did not identify exactly one official CSV")
    return unique[0]


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
