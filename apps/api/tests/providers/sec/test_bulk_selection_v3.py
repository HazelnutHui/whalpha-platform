import hashlib
import json
import socket
import zipfile
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tip_api.providers.sec.bulk_sources import (
    CSV_PATH_TEMPLATES,
    LANDING_PAGES,
    SERIES_CLASS_2023_UNDERSCORE_PATH,
    SERIES_CLASS_2024_LEGACY_PATH,
    SecLandingDiscoveryError,
    download_selected_csv,
    iter_selected_submissions,
    parse_tabular_json,
    read_landing_discovery_diagnostic,
    select_dated_official_csv,
    validate_selected_csv_response,
    validate_submissions_zip,
)
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult, SecTransportError

CUTOFF = date(2026, 8, 14)
FIXTURES = Path(__file__).parents[2] / "fixtures/sec"
SERIES = "investment_company_series_class"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def href(dataset_id: str, year: int, *, extension: str = "csv") -> str:
    path = CSV_PATH_TEMPLATES[dataset_id].format(year=year)
    return path[:-3] + extension


def unknown_series_href(year: int) -> str:
    return (
        "/files/investment/data/other/investment-company-series-and-class-information/"
        f"investment_company_series_class_{year}.csv"
    )


def page(rows: list[str], *, headers=("File", "Format", "Size"), extra="") -> str:
    heading = "".join(f"<th>{value}</th>" for value in headers)
    return f"<html><body>{extra}<table><tr>{heading}</tr>{''.join(rows)}</table></body></html>"


def row(
    dataset_id: str,
    year: int,
    updated: str | None,
    *,
    format: str = "CSV",
    custom_href: str | None = None,
    size: str = "1 MB",
    anchor_text: str | None = None,
) -> str:
    value = custom_href if custom_href is not None else href(
        dataset_id, year, extension=format.lower()
    )
    tail = f" Updated {updated}" if updated is not None else ""
    label = anchor_text if anchor_text is not None else str(year)
    return (
        f'<tr><td><a href="{value}">{label}</a>{tail}</td>'
        f"<td>{format}</td><td>{size}</td></tr>"
    )


def five_rows() -> list[str]:
    return [
        row(SERIES, 2026, "6/1/2026", size="7.68 MB"),
        row(SERIES, 2025, "6/2/2025", size="7.25 MB"),
        row(
            SERIES, 2024, "6/5/2024",
            custom_href=SERIES_CLASS_2024_LEGACY_PATH, size="7.21 MB",
        ),
        row(
            SERIES, 2023, "6/8/2023",
            custom_href=SERIES_CLASS_2023_UNDERSCORE_PATH, size="7.4 MB",
        ),
        row(
            SERIES, 2022, "6/9/2022",
            custom_href=unknown_series_href(2022), size="7.1 MB",
        ),
    ]


def select(html: str, *, dataset: str = SERIES, cutoff: date = CUTOFF):
    return select_dated_official_csv(
        dataset, LANDING_PAGES[dataset], html, evidence_cutoff=cutoff
    )


def failure(html: str, *, dataset: str = SERIES) -> SecLandingDiscoveryError:
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select(html, dataset=dataset)
    return caught.value


class FakeDownloadTransport:
    def __init__(self, payload: bytes = b"CIK,Series ID\n1,S000001\n") -> None:
        self.payload = payload
        self.urls: list[str] = []
        self.request_count = 0
        self.retry_count = 0

    def download(self, url, target, **kwargs):
        self.urls.append(url)
        self.request_count += 1
        target.write_bytes(self.payload)
        return SecDownloadResult(
            url=url,
            content_type="text/csv",
            byte_count=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
            retry_count=0,
        )


def test_observed_2026_through_2022_fixture_selects_latest_and_warns() -> None:
    result = select(fixture("series_class_2022_history_landing.html"))
    diagnostic = result.diagnostic
    assert result.dataset_year == 2026
    assert result.effective_date == date(2026, 6, 1)
    assert result.url == f"https://www.sec.gov{href(SERIES, 2026)}"
    assert diagnostic.schema_version == "3.0"
    assert diagnostic.csv_candidate_count == 5
    assert diagnostic.baseline_safe_count == 5
    assert diagnostic.exact_allowlisted_count == 4
    assert diagnostic.blocking_rejection_count == 0
    assert diagnostic.historical_path_warning_count == 1
    assert diagnostic.undated_historical_warning_count == 0
    assert diagnostic.cutoff_eligible_count == 5
    assert diagnostic.selected_count == 1
    candidate = next(item for item in diagnostic.candidate_diagnostics if item.file_year == 2022)
    assert (
        candidate.baseline_url_status,
        candidate.template_status,
        candidate.temporal_relation,
        candidate.action,
        candidate.reason_code,
    ) == (
        "passed",
        "failed",
        "older",
        "ignored_warning",
        "historical_path_template_mismatch_ignored",
    )


def test_multiple_unknown_older_paths_do_not_change_selection() -> None:
    result = select(
        page(
            five_rows()
            + [
                row(SERIES, 2021, "6/10/2021", custom_href=unknown_series_href(2021)),
                row(SERIES, 2020, "6/11/2020", custom_href=unknown_series_href(2020)),
            ]
        )
    )
    assert result.dataset_year == 2026
    assert result.diagnostic.historical_path_warning_count == 3
    assert result.diagnostic.blocking_rejection_count == 0


def test_row_order_does_not_change_selection_warnings_or_fingerprint() -> None:
    first = select(page(five_rows()))
    second = select(page(list(reversed(five_rows()))))
    assert (first.url, first.dataset_year, first.effective_date) == (
        second.url, second.dataset_year, second.effective_date
    )
    assert first.selection_fingerprint == second.selection_fingerprint
    assert first.diagnostic.warning_codes == second.diagnostic.warning_codes


def test_csv_xml_order_does_not_change_selection() -> None:
    xml = row(SERIES, 2026, "6/1/2026", format="XML")
    first = select(page([xml, *five_rows()]))
    second = select(page([*five_rows(), xml]))
    assert first.url == second.url == f"https://www.sec.gov{href(SERIES, 2026)}"


def test_parser_scans_rows_after_first_historical_mismatch() -> None:
    rows = [
        row(SERIES, 2022, "6/9/2022", custom_href=unknown_series_href(2022)),
        row(SERIES, 2026, "6/1/2026"),
        row(SERIES, 2025, "6/2/2025"),
    ]
    result = select(page(rows))
    assert result.dataset_year == 2026
    assert result.diagnostic.rows_scanned == 3
    assert result.diagnostic.csv_candidate_count == 3


@pytest.mark.parametrize(
    ("year", "updated", "bad_href", "expected"),
    [
        (2026, "6/1/2026", unknown_series_href(2026), "selected_path_template_mismatch"),
        (2027, "6/1/2027", unknown_series_href(2027), "same_or_newer_href_rejected"),
    ],
)
def test_selected_or_future_template_mismatch_hard_fails(
    year: int, updated: str, bad_href: str, expected: str
) -> None:
    rows = [row(SERIES, year, updated, custom_href=bad_href)]
    if year == 2027:
        rows.append(row(SERIES, 2026, "6/1/2026"))
    caught = failure(page(rows))
    assert caught.reason_code == expected
    assert caught.diagnostic.blocking_rejection_count >= 1
    assert caught.diagnostic.selected_count == 0


def test_same_max_date_unallowlisted_distinct_url_hard_fails() -> None:
    caught = failure(
        page(
            [
                row(SERIES, 2026, "6/1/2026"),
                row(SERIES, 2026, "6/1/2026", custom_href=unknown_series_href(2026)),
            ]
        )
    )
    assert caught.reason_code == "max_date_distinct_url_tie"


def test_newer_cutoff_unallowlisted_does_not_fall_back() -> None:
    caught = failure(
        page(
            [
                row(SERIES, 2026, "6/1/2026"),
                row(SERIES, 2025, "7/1/2026", custom_href=unknown_series_href(2025)),
            ]
        )
    )
    assert caught.reason_code in {
        "selected_path_template_mismatch",
        "file_year_date_mismatch",
        "same_or_newer_href_rejected",
    }
    assert caught.diagnostic.selected_count == 0


def test_duplicate_same_date_same_url_dedupes() -> None:
    selected = select(page([row(SERIES, 2026, "6/1/2026")] * 2))
    assert selected.dataset_year == 2026
    assert selected.diagnostic.max_date_candidate_count == 1
    assert selected.diagnostic.selected_count == 1
    assert sum(
        item.reason_code == "duplicate_candidate_ignored"
        for item in selected.diagnostic.candidate_diagnostics
    ) == 1


def test_same_max_date_distinct_url_tie_is_deterministic() -> None:
    rows = [
        row(SERIES, 2026, "6/1/2026"),
        row(SERIES, 2026, "6/1/2026", custom_href=unknown_series_href(2026)),
    ]
    assert failure(page(rows)).reason_code == "max_date_distinct_url_tie"
    assert failure(page(list(reversed(rows)))).reason_code == "max_date_distinct_url_tie"


def test_cutoff_is_inclusive() -> None:
    selected = select(
        page([row(SERIES, 2026, "8/14/2026")]), cutoff=date(2026, 8, 14)
    )
    assert selected.effective_date == date(2026, 8, 14)


def test_legal_future_candidate_is_excluded_and_recorded() -> None:
    result = select(
        page([row(SERIES, 2027, "9/1/2027"), row(SERIES, 2026, "6/1/2026")])
    )
    assert result.dataset_year == 2026
    assert result.diagnostic.future_candidate_count == 1
    future = next(item for item in result.diagnostic.candidate_diagnostics if item.file_year == 2027)
    assert future.temporal_relation == "future"
    assert future.reason_code == "future_candidate_excluded"


def test_only_future_candidates_preserve_future_diagnostic_state() -> None:
    caught = failure(page([row(SERIES, 2027, "9/1/2027")]))
    assert caught.reason_code == "no_cutoff_eligible_candidate"
    assert caught.diagnostic.future_candidate_count == 1
    assert caught.diagnostic.candidate_diagnostics[0].temporal_relation == "future"


def test_undated_strictly_older_candidate_is_warning() -> None:
    result = select(
        page(
            [
                row(SERIES, 2026, "6/1/2026"),
                row(SERIES, 2021, None, custom_href=unknown_series_href(2021)),
            ]
        )
    )
    assert result.diagnostic.undated_historical_warning_count == 1
    old = next(item for item in result.diagnostic.candidate_diagnostics if item.file_year == 2021)
    assert old.reason_code == "undated_historical_ignored"
    assert old.action == "ignored_warning"


def test_dated_and_undated_rows_for_same_old_year_fingerprint_stably() -> None:
    rows = [
        row(SERIES, 2026, "6/1/2026"),
        row(SERIES, 2021, "6/10/2021", custom_href=unknown_series_href(2021)),
        row(SERIES, 2021, None, custom_href=unknown_series_href(2021)),
    ]
    first = select(page(rows))
    second = select(page(list(reversed(rows))))
    assert first.selection_fingerprint == second.selection_fingerprint


def test_selected_or_newer_year_undated_hard_fails() -> None:
    caught = failure(
        page([row(SERIES, 2025, "6/2/2025"), row(SERIES, 2026, None)])
    )
    assert caught.reason_code == "current_candidate_date_missing"


def test_only_undated_candidate_is_a_blocking_record() -> None:
    caught = failure(page([row(SERIES, 2026, None)]))
    assert caught.reason_code == "current_candidate_date_missing"
    assert caught.diagnostic.blocking_rejection_count == 1
    assert caught.diagnostic.candidate_diagnostics[0].action == "hard_fail"


@pytest.mark.parametrize(
    ("updated", "reason"),
    [
        ("not-a-date", "updated_date_parse_failed"),
        ("6/1/2026 Updated 6/2/2026", "multiple_dates_in_row"),
        ("6/1/2025", "file_year_date_mismatch"),
    ],
)
def test_date_integrity_failures_are_blocking(updated: str, reason: str) -> None:
    caught = failure(page([row(SERIES, 2026, updated)]))
    assert caught.reason_code == reason


@pytest.mark.parametrize(
    ("bad_href", "candidate_reason"),
    [
        ("http://www.sec.gov" + unknown_series_href(2022), "scheme_not_https"),
        ("//www.sec.gov" + unknown_series_href(2022), "scheme_not_https"),
        ("https://www.sec.gov.evil.example" + unknown_series_href(2022), "host_not_allowed"),
        ("https://user@www.sec.gov" + unknown_series_href(2022), "userinfo_present"),
        ("https://www.sec.gov:8443" + unknown_series_href(2022), "nonstandard_port"),
        (unknown_series_href(2022) + "?download=1", "query_present"),
        (unknown_series_href(2022) + "#section", "fragment_present"),
        (unknown_series_href(2022).replace("/investment_", "/../investment_"), "traversal_present"),
        (unknown_series_href(2022).replace("/investment_", "/%2e%2e/investment_"), "encoded_traversal_present"),
        (unknown_series_href(2022).replace("/", "\\", 1), "backslash_present"),
        ("/other-root/file.csv", "path_root_not_allowed"),
        (unknown_series_href(2022) + "%00", "malformed_url"),
    ],
)
def test_historical_baseline_url_failures_never_become_warnings(
    bad_href: str, candidate_reason: str
) -> None:
    caught = failure(
        page(
            [
                row(SERIES, 2022, "6/9/2022", custom_href=bad_href),
                row(SERIES, 2026, "6/1/2026"),
            ]
        )
    )
    assert caught.reason_code == "baseline_url_safety_failure"
    candidate = caught.diagnostic.candidate_diagnostics[0]
    assert candidate.action == "hard_fail"
    assert candidate.reason_code == candidate_reason
    assert candidate.normalized_path is None


def test_latest_baseline_failure_uses_selected_href_rejected() -> None:
    caught = failure(
        page(
            [
                row(SERIES, 2026, "6/1/2026", custom_href="http://www.sec.gov" + href(SERIES, 2026)),
                row(SERIES, 2025, "6/2/2025"),
            ]
        )
    )
    assert caught.reason_code == "selected_href_rejected"
    assert caught.diagnostic.selected_count == 0


@pytest.mark.parametrize(
    ("dataset", "foreign_path"),
    [
        ("closed_end_fund", href(SERIES, 2026)),
        ("business_development_company", href("closed_end_fund", 2026)),
    ],
)
def test_dataset_templates_cannot_be_reused(dataset: str, foreign_path: str) -> None:
    caught = failure(
        page([row(dataset, 2026, "6/1/2026", custom_href=foreign_path)]),
        dataset=dataset,
    )
    assert caught.reason_code == "selected_path_template_mismatch"


@pytest.mark.parametrize(
    ("year", "special_path"),
    [
        (2024, SERIES_CLASS_2024_LEGACY_PATH),
        (2023, SERIES_CLASS_2023_UNDERSCORE_PATH),
    ],
)
def test_existing_exact_historical_rules_remain_valid(
    year: int, special_path: str
) -> None:
    result = select(page([row(SERIES, year, f"6/1/{year}", custom_href=special_path)]))
    assert result.dataset_year == year
    assert result.diagnostic.selected_template_id is not None


def test_download_boundary_requests_only_selected_object(tmp_path: Path) -> None:
    selection = select(fixture("series_class_2022_history_landing.html"))
    transport = FakeDownloadTransport()
    output = []
    target = tmp_path / "selected.csv"
    config = SecProviderConfig(
        user_agent="trading-intelligence-platform test-contact@example.invalid",
        request_timeout_seconds=Decimal("1"),
        max_retries=0,
    )
    download_selected_csv(
        transport, config, selection, target, SERIES,
        datetime(2026, 8, 16, tzinfo=UTC), output,
    )
    assert transport.urls == [selection.url]
    assert unknown_series_href(2022) not in transport.urls
    assert len(output) == 1


def test_invalid_selected_object_causes_zero_download_requests(tmp_path: Path) -> None:
    selection = select(page([row(SERIES, 2026, "6/1/2026")]))
    forged = replace(selection, url=f"https://www.sec.gov{unknown_series_href(2026)}")
    transport = FakeDownloadTransport()
    config = SecProviderConfig(
        user_agent="trading-intelligence-platform test-contact@example.invalid"
    )
    with pytest.raises(SecTransportError, match="selected CSV"):
        download_selected_csv(
            transport, config, forged, tmp_path / "never.csv", SERIES,
            datetime(2026, 8, 16, tzinfo=UTC), [],
        )
    assert transport.urls == []
    assert transport.request_count == 0


def test_schema_three_counts_actions_and_fingerprint_are_stable() -> None:
    first = select(page(five_rows()))
    second = select(page(five_rows()))
    diagnostic = first.diagnostic
    assert diagnostic.status == "selected"
    assert diagnostic.failure_code is None
    assert diagnostic.warning_codes == ("historical_path_template_mismatch_ignored",)
    assert diagnostic.blocking_rejection_count == sum(
        item.action == "hard_fail" for item in diagnostic.candidate_diagnostics
    )
    assert first.selection_fingerprint == second.selection_fingerprint
    assert diagnostic.selection_fingerprint == first.selection_fingerprint


def test_schema_two_diagnostic_remains_audit_readable() -> None:
    legacy = {
        "schema_version": "2.0",
        "dataset_id": SERIES,
        "candidate_diagnostics": [{"selection_state": "rejected"}],
    }
    assert read_landing_discovery_diagnostic(legacy) == legacy
    with pytest.raises(ValueError):
        read_landing_discovery_diagnostic({"schema_version": "1.0"})


def test_diagnostic_never_contains_unsafe_href_html_or_sentinel(capsys) -> None:
    sentinel = "FIXTURE-CREDENTIAL-SENTINEL"
    html = page(
        [
            row(
                SERIES, 2022, "6/9/2022",
                custom_href=unknown_series_href(2022) + f"?secret={sentinel}",
            ),
            row(SERIES, 2026, "6/1/2026"),
        ],
        extra=f"<script>{sentinel}</script>",
    )
    caught = failure(html)
    rendered = json.dumps(caught.diagnostic.to_safe_dict(), sort_keys=True)
    captured = capsys.readouterr()
    assert sentinel not in rendered + str(caught) + repr(caught)
    assert "secret=" not in rendered
    assert "<script>" not in rendered
    assert sentinel not in captured.out + captured.err


@pytest.mark.parametrize(
    "content_type",
    ["text/csv", "text/csv; charset=utf-8", "application/octet-stream"],
)
def test_verified_selection_accepts_bounded_csv_content_types(
    content_type: str, tmp_path: Path
) -> None:
    selection = select(page([row(SERIES, 2026, "6/1/2026")]))
    source = tmp_path / "source.csv"
    source.write_text("CIK,Series ID\n1,S000001\n", encoding="utf-8")
    validate_selected_csv_response(selection, content_type, source)


def test_octet_stream_still_requires_matching_csv_schema(tmp_path: Path) -> None:
    selection = select(page([row(SERIES, 2026, "6/1/2026")]))
    source = tmp_path / "source.csv"
    source.write_text("unexpected,fields\n1,2\n", encoding="utf-8")
    with pytest.raises(SecTransportError, match="header"):
        validate_selected_csv_response(selection, "application/octet-stream", source)


def test_parser_has_explicit_network_prohibition(monkeypatch) -> None:
    monkeypatch.setattr(
        socket, "create_connection",
        lambda *args, **kwargs: pytest.fail("network attempted"),
    )
    assert select(fixture("series_class_2022_history_landing.html")).dataset_year == 2026


def test_tabular_json_requires_exact_field_row_shape(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text(json.dumps({"fields": ["cik", "ticker"], "data": [[1, "AAA"]]}))
    assert parse_tabular_json(path) == ({"cik": 1, "ticker": "AAA"},)
    path.write_text(json.dumps({"fields": ["cik", "ticker"], "data": [[1]]}))
    with pytest.raises(SecTransportError):
        parse_tabular_json(path)


def test_submissions_zip_rejects_traversal_and_reads_selected_cik(tmp_path: Path) -> None:
    safe = tmp_path / "safe.zip"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("CIK0000000001.json", json.dumps({"cik": "1"}))
        archive.writestr("CIK0000000002.json", json.dumps({"cik": "2"}))
    validate_submissions_zip(safe)
    assert tuple(iter_selected_submissions(safe, {"0000000002"}))[0][0] == "0000000002"
    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../escape.json", "{}")
    with pytest.raises(SecTransportError):
        validate_submissions_zip(unsafe)
