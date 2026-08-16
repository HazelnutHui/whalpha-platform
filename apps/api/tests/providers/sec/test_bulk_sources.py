import json
import zipfile
from pathlib import Path

import pytest

from tip_api.providers.sec.bulk_sources import (
    _extract_single_official_csv,
    iter_selected_submissions,
    parse_tabular_json,
    validate_submissions_zip,
)
from tip_api.providers.sec.transport import SecTransportError


def test_official_csv_link_is_same_host_allowlisted() -> None:
    landing = "https://www.sec.gov/data-research/example"
    assert _extract_single_official_csv(landing, '<a href="/files/current.csv">CSV</a>') == "https://www.sec.gov/files/current.csv"
    with pytest.raises(SecTransportError):
        _extract_single_official_csv(landing, '<a href="https://example.test/current.csv">CSV</a>')
    with pytest.raises(SecTransportError):
        _extract_single_official_csv(landing, '<a href="/a.csv">A</a><a href="/b.csv">B</a>')


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
