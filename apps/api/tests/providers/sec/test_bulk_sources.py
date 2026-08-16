import json
import zipfile
from pathlib import Path

import pytest

from tip_api.providers.sec.bulk_sources import (
    iter_selected_submissions,
    parse_tabular_json,
    select_dated_official_csv,
    validate_submissions_zip,
)
from tip_api.providers.sec.transport import SecTransportError


LANDING = "https://www.sec.gov/data-research/sec-markets-data/example"
CUTOFF = __import__("datetime").date(2026, 8, 14)


def table(rows, headers=("Dataset Year", "Updated Date", "File Format")):
    heading = "".join(f"<th>{value}</th>" for value in headers)
    body = "".join(f"<tr>{row}</tr>" for row in rows)
    return f"<html><table><tr>{heading}</tr>{body}</table></html>"


def row(year, updated, href, *, label="CSV", extra=""):
    return f'<td>{year}</td><td>{updated}</td><td><a href="{href}">{label}</a>{extra}</td>'


def test_multiple_2010_through_2026_csvs_select_latest_eligible_deterministically() -> None:
    rows = [row(year, f"8/1/{str(year)[2:]}", f"/files/dataset-{year}.csv") for year in range(2010, 2027)]
    result = select_dated_official_csv(LANDING, table(rows), evidence_cutoff=CUTOFF)
    assert result.url == "https://www.sec.gov/files/dataset-2026.csv"
    assert result.dataset_year == 2026 and result.effective_date.isoformat() == "2026-08-01"
    assert (result.total_csv_candidate_count, result.eligible_count, result.future_dated_count) == (17, 17, 0)
    assert result == select_dated_official_csv(LANDING, table(reversed(rows)), evidence_cutoff=CUTOFF)


def test_xml_and_csv_share_row_but_only_explicit_csv_is_selected() -> None:
    html = table([row(2026, "08/01/2026", "/files/current.csv", extra='<a href="/files/current.xml">XML</a>')])
    assert select_dated_official_csv(LANDING, html, evidence_cutoff=CUTOFF).url.endswith("current.csv")


def test_future_latest_csv_is_skipped_for_cutoff() -> None:
    html = table([
        row(2025, "12/31/2025", "/files/previous.csv"),
        row(2026, "08/15/2026", "/files/future.csv"),
    ])
    result = select_dated_official_csv(LANDING, html, evidence_cutoff=CUTOFF)
    assert result.url.endswith("previous.csv") and result.future_dated_count == 1


@pytest.mark.parametrize("updated", ["8/1/26", "08/01/26", "8/1/2026", "08/01/2026"])
def test_supported_official_date_formats(updated: str) -> None:
    assert select_dated_official_csv(
        LANDING, table([row(2026, updated, "/files/current.csv")]), evidence_cutoff=CUTOFF,
    ).effective_date.isoformat() == "2026-08-01"


def test_same_latest_date_with_distinct_urls_hard_fails() -> None:
    html = table([
        row(2026, "8/1/2026", "/files/a.csv"),
        row(2026, "8/1/2026", "/files/b.csv"),
    ])
    with pytest.raises(SecTransportError, match="conflicting latest"):
        select_dated_official_csv(LANDING, html, evidence_cutoff=CUTOFF)


@pytest.mark.parametrize("updated", ["", "13/40/2026", "not-a-date"])
def test_missing_or_invalid_candidate_date_hard_fails(updated: str) -> None:
    with pytest.raises(SecTransportError, match="date"):
        select_dated_official_csv(
            LANDING, table([row(2026, updated, "/files/current.csv")]), evidence_cutoff=CUTOFF,
        )


@pytest.mark.parametrize("href", [
    "https://example.test/files/current.csv",
    "http://www.sec.gov/files/current.csv",
    "javascript:alert.csv",
    "data:text/csv,current.csv",
    "../files/current.csv",
    "/files/../private/current.csv",
])
def test_unsafe_csv_urls_hard_fail(href: str) -> None:
    with pytest.raises(SecTransportError):
        select_dated_official_csv(
            LANDING, table([row(2026, "8/1/2026", href)]), evidence_cutoff=CUTOFF,
        )


def test_landing_page_without_csv_hard_fails() -> None:
    with pytest.raises(SecTransportError, match="no dated official CSV"):
        select_dated_official_csv(
            LANDING,
            table(['<td>2026</td><td>8/1/2026</td><td><a href="/files/current.xml">XML</a></td>']),
            evidence_cutoff=CUTOFF,
        )


@pytest.mark.parametrize("headers", [
    ("Dataset Year", "Effective Date", "Download Format"),
    ("Year", "Last Updated", "File"),
    ("Data Year", "Date Posted", "Download"),
])
def test_series_cef_and_bdc_table_header_shapes(headers) -> None:
    result = select_dated_official_csv(
        LANDING, table([row(2026, "8/1/2026", "/files/current.csv")], headers), evidence_cutoff=CUTOFF,
    )
    assert result.dataset_year == 2026


def test_tabular_json_requires_exact_field_row_shape(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text(json.dumps({"fields": ["cik", "ticker"], "data": [[1, "AAA"]]}))
    assert parse_tabular_json(path) == ({"cik": 1, "ticker": "AAA"},)
    path.write_text(json.dumps({"fields": ["cik", "ticker"], "data": [[1]]}))
    with pytest.raises(SecTransportError):
        parse_tabular_json(path)


def test_submissions_zip_rejects_traversal_and_reads_only_selected_cik(tmp_path: Path) -> None:
    safe = tmp_path / "safe.zip"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("CIK0000000001.json", json.dumps({"cik": "1", "filings": {"recent": {}}}))
        archive.writestr("CIK0000000002.json", json.dumps({"cik": "2", "filings": {"recent": {}}}))
    validate_submissions_zip(safe)
    assert tuple(iter_selected_submissions(safe, {"0000000002"}))[0][0] == "0000000002"

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../escape.json", "{}")
    with pytest.raises(SecTransportError):
        validate_submissions_zip(unsafe)


def test_submissions_zip_rejects_unexpected_members(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("README.txt", "not a submission")
    with pytest.raises(SecTransportError):
        validate_submissions_zip(path)
