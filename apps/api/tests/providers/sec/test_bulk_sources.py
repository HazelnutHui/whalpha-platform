import json
import socket
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
import tip_api.providers.sec.bulk_sources as bulk_sources

from tip_api.providers.sec.bulk_sources import (
    LANDING_PAGES,
    CSV_PATH_TEMPLATES,
    SERIES_CLASS_2023_UNDERSCORE_PATH,
    SERIES_CLASS_2024_LEGACY_PATH,
    SecCsvUrlFailureCode,
    SecLandingDiscoveryError,
    iter_selected_submissions,
    parse_tabular_json,
    select_dated_official_csv,
    validate_selected_csv_response,
    validate_submissions_zip,
)
from tip_api.providers.sec.transport import SecTransportError

CUTOFF = date(2026, 8, 14)
FIXTURES = Path(__file__).parents[2] / "fixtures/sec"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def href(dataset_id: str, year: int, *, extension: str = "csv") -> str:
    path = CSV_PATH_TEMPLATES[dataset_id].format(year=year)
    return path[:-3] + extension


def legacy_series_href(year: int, *, extension: str = "csv") -> str:
    directory = SERIES_CLASS_2024_LEGACY_PATH.rsplit("/", 1)[0]
    return f"{directory}/investment-company-series-class-{year}.{extension}"


def underscore_series_href(year: int, *, extension: str = "csv") -> str:
    directory = SERIES_CLASS_2023_UNDERSCORE_PATH.rsplit("/", 1)[0]
    return f"{directory}/investment_company_series_class_{year}.{extension}"


def page(dataset_id: str, rows: list[str], *, headers=("File", "Format", "Size"), extra="") -> str:
    heading = "".join(f"<th>{value}</th>" for value in headers)
    return f"<html><body>{extra}<table><tr>{heading}</tr>{''.join(rows)}</table></body></html>"


def row(dataset_id: str, year: int, updated: str | None, *, format="CSV", custom_href=None, size="1 MB") -> str:
    value = custom_href if custom_href is not None else href(dataset_id, year, extension=format.lower())
    tail = f" Updated {updated}" if updated is not None else ""
    return f'<tr><td><a href="{value}">{year}</a>{tail}</td><td>{format}</td><td>{size}</td></tr>'


@pytest.mark.parametrize(("dataset_id", "fixture_name", "effective"), [
    ("investment_company_series_class", "series_class_landing.html", "2026-06-01"),
    ("closed_end_fund", "closed_end_fund_landing.html", "2026-06-01"),
    ("business_development_company", "business_development_company_landing.html", "2026-06-01"),
])
def test_real_structure_fixtures_select_dated_csv(dataset_id: str, fixture_name: str, effective: str) -> None:
    result = select_dated_official_csv(dataset_id, LANDING_PAGES[dataset_id], fixture(fixture_name), evidence_cutoff=CUTOFF)
    assert result.dataset_year == 2026
    assert result.effective_date.isoformat() == effective
    assert result.url == f"https://www.sec.gov{href(dataset_id, 2026)}"
    assert result.selection_reason_code == "selected"
    assert result.diagnostic.table_count == 2
    assert result.diagnostic.normalized_header_signature == ("file", "format", "size")
    assert result.diagnostic.undated_historical_count >= 1


def test_observed_three_candidate_fixture_selects_2026_and_counts_all_eligible() -> None:
    dataset = "investment_company_series_class"
    result = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        fixture("series_class_2024_legacy_landing.html"),
        evidence_cutoff=CUTOFF,
    )
    diagnostic = result.diagnostic
    assert result.dataset_year == 2026
    assert result.effective_date == date(2026, 6, 1)
    assert result.url == f"https://www.sec.gov{href(dataset, 2026)}"
    assert result.eligible_count == 3
    assert diagnostic.csv_candidate_count == 3
    assert diagnostic.allowlisted_count == 3
    assert diagnostic.cutoff_eligible_count == 3
    assert diagnostic.rejected_count == 0
    assert diagnostic.selected_count == 1
    assert [item.selection_state for item in diagnostic.candidate_diagnostics] == [
        "selected", "eligible_not_selected", "eligible_not_selected",
    ]
    assert all(item.path_template_match is True for item in diagnostic.candidate_diagnostics)


def test_observed_three_candidate_selection_is_independent_of_row_order() -> None:
    dataset = "investment_company_series_class"
    rows = [
        row(dataset, 2026, "6/1/2026", size="7.68 MB"),
        row(dataset, 2025, "6/2/2025", size="7.25 MB"),
        row(dataset, 2024, "6/5/2024", custom_href=SERIES_CLASS_2024_LEGACY_PATH, size="7.21 MB"),
    ]
    first = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    reversed_result = select_dated_official_csv(
        dataset, LANDING_PAGES[dataset], page(dataset, list(reversed(rows))), evidence_cutoff=CUTOFF,
    )
    assert (first.url, first.dataset_year, first.effective_date, first.eligible_count) == (
        reversed_result.url, reversed_result.dataset_year, reversed_result.effective_date, reversed_result.eligible_count,
    )
    assert first.dataset_year == 2026 and first.eligible_count == 3


def test_observed_four_candidate_fixture_selects_only_2026_and_counts_all_eligible() -> None:
    dataset = "investment_company_series_class"
    result = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        fixture("series_class_2023_underscore_landing.html"),
        evidence_cutoff=CUTOFF,
    )
    diagnostic = result.diagnostic
    assert result.url == f"https://www.sec.gov{href(dataset, 2026)}"
    assert result.dataset_year == 2026
    assert result.effective_date == date(2026, 6, 1)
    assert result.eligible_count == 4
    assert diagnostic.csv_candidate_count == 4
    assert diagnostic.allowlisted_count == 4
    assert diagnostic.rejected_count == 0
    assert diagnostic.cutoff_eligible_count == 4
    assert diagnostic.selected_count == 1
    assert [item.selection_state for item in diagnostic.candidate_diagnostics] == [
        "selected", "eligible_not_selected", "eligible_not_selected", "eligible_not_selected",
    ]
    assert [item.parsed_file_year for item in diagnostic.candidate_diagnostics] == [2026, 2025, 2024, 2023]
    assert all(item.path_template_match is True for item in diagnostic.candidate_diagnostics)


def test_observed_four_candidate_selection_is_independent_of_row_order() -> None:
    dataset = "investment_company_series_class"
    rows = [
        row(dataset, 2026, "6/1/2026", size="7.68 MB"),
        row(dataset, 2025, "6/2/2025", size="7.25 MB"),
        row(dataset, 2024, "6/5/2024", custom_href=SERIES_CLASS_2024_LEGACY_PATH, size="7.21 MB"),
        row(dataset, 2023, "6/8/2023", custom_href=SERIES_CLASS_2023_UNDERSCORE_PATH, size="7.4 MB"),
    ]
    first = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    reversed_result = select_dated_official_csv(
        dataset, LANDING_PAGES[dataset], page(dataset, list(reversed(rows))), evidence_cutoff=CUTOFF,
    )
    assert (first.url, first.dataset_year, first.effective_date, first.eligible_count) == (
        reversed_result.url, reversed_result.dataset_year, reversed_result.effective_date, reversed_result.eligible_count,
    )
    assert first.url == f"https://www.sec.gov{href(dataset, 2026)}"
    assert first.eligible_count == 4


@pytest.mark.parametrize("value", [
    SERIES_CLASS_2023_UNDERSCORE_PATH,
    f"https://www.sec.gov{SERIES_CLASS_2023_UNDERSCORE_PATH}",
])
def test_exact_2023_underscore_series_path_accepts_relative_and_absolute_https(
    value: str,
    tmp_path: Path,
) -> None:
    dataset = "investment_company_series_class"
    result = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        page(dataset, [row(dataset, 2023, "6/8/2023", custom_href=value)]),
        evidence_cutoff=CUTOFF,
    )
    candidate = result.diagnostic.candidate_diagnostics[0]
    assert result.url == f"https://www.sec.gov{SERIES_CLASS_2023_UNDERSCORE_PATH}"
    assert result.dataset_year == 2023
    assert candidate.url_validation_state == "accepted"
    assert candidate.path_template_match is True
    source = tmp_path / "series.csv"
    source.write_text("CIK,Series ID\n1,S000001\n", encoding="utf-8")
    validate_selected_csv_response(result, "text/csv", source)


@pytest.mark.parametrize(("year", "value", "failure_code"), [
    (2022, underscore_series_href(2022), "path_template_mismatch"),
    (2024, underscore_series_href(2024), "path_template_mismatch"),
    (2025, underscore_series_href(2025), "path_template_mismatch"),
    (2026, underscore_series_href(2026), "path_template_mismatch"),
    (2023, underscore_series_href(2022), "path_template_mismatch"),
    (2023, SERIES_CLASS_2023_UNDERSCORE_PATH.replace("series-class-information", "series-classes-information"), "path_template_mismatch"),
    (2023, SERIES_CLASS_2023_UNDERSCORE_PATH.replace("investment_company", "investment-company"), "path_template_mismatch"),
    (2023, SERIES_CLASS_2023_UNDERSCORE_PATH.removesuffix(".csv") + ".CSV", "path_template_mismatch"),
    (2023, underscore_series_href(2023, extension="xml"), "extension_not_csv"),
    (2023, f"{SERIES_CLASS_2023_UNDERSCORE_PATH}?download=PRIVATE-QUERY", "query_present"),
    (2023, f"{SERIES_CLASS_2023_UNDERSCORE_PATH}#PRIVATE-FRAGMENT", "fragment_present"),
    (2023, f"https://PRIVATE-USER@www.sec.gov{SERIES_CLASS_2023_UNDERSCORE_PATH}", "userinfo_present"),
    (2023, f"https://www.sec.gov:8443{SERIES_CLASS_2023_UNDERSCORE_PATH}", "nonstandard_port"),
    (2023, f"https://www.sec.gov.evil.example{SERIES_CLASS_2023_UNDERSCORE_PATH}", "host_not_allowed"),
    (2023, SERIES_CLASS_2023_UNDERSCORE_PATH.replace("/investment_company_series_class_2023.csv", "/../investment-company-series-class-information/investment_company_series_class_2023.csv"), "traversal_present"),
    (2023, SERIES_CLASS_2023_UNDERSCORE_PATH.replace("/investment_company_series_class_2023.csv", "/%2e%2e/investment-company-series-class-information/investment_company_series_class_2023.csv"), "encoded_traversal_present"),
])
def test_2023_underscore_series_path_is_an_exact_exception(
    year: int,
    value: str,
    failure_code: str,
) -> None:
    dataset = "investment_company_series_class"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(dataset, year, f"6/1/{year}", custom_href=value)]),
            evidence_cutoff=CUTOFF,
        )
    candidate = caught.value.diagnostic.candidate_diagnostics[0]
    assert caught.value.reason_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else "selected_href_rejected"
    )
    assert candidate.failure_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else failure_code
    )
    assert candidate.url_validation_state == "rejected"
    rendered = json.dumps(caught.value.diagnostic.to_safe_dict(), sort_keys=True)
    assert "PRIVATE-QUERY" not in rendered
    assert "PRIVATE-FRAGMENT" not in rendered
    assert "PRIVATE-USER" not in rendered


@pytest.mark.parametrize("value", [
    SERIES_CLASS_2024_LEGACY_PATH,
    f"https://www.sec.gov{SERIES_CLASS_2024_LEGACY_PATH}",
])
def test_exact_2024_legacy_series_path_accepts_relative_and_absolute_https(
    value: str,
    tmp_path: Path,
) -> None:
    dataset = "investment_company_series_class"
    result = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        page(dataset, [row(dataset, 2024, "6/5/2024", custom_href=value)]),
        evidence_cutoff=CUTOFF,
    )
    candidate = result.diagnostic.candidate_diagnostics[0]
    assert result.url == f"https://www.sec.gov{SERIES_CLASS_2024_LEGACY_PATH}"
    assert result.dataset_year == 2024
    assert candidate.url_validation_state == "accepted"
    assert candidate.path_template_match is True
    source = tmp_path / "series.csv"
    source.write_text("CIK,Series ID\n1,S000001\n", encoding="utf-8")
    validate_selected_csv_response(result, "text/csv", source)


@pytest.mark.parametrize(("year", "value", "failure_code"), [
    (2025, legacy_series_href(2025), "path_template_mismatch"),
    (2026, legacy_series_href(2026), "path_template_mismatch"),
    (2023, legacy_series_href(2023), "path_template_mismatch"),
    (2024, legacy_series_href(2023), "path_template_mismatch"),
    (2024, SERIES_CLASS_2024_LEGACY_PATH.replace("series-and-class", "series-and-classes"), "path_template_mismatch"),
    (2024, f"{SERIES_CLASS_2024_LEGACY_PATH}?download=PRIVATE-QUERY", "query_present"),
    (2024, f"{SERIES_CLASS_2024_LEGACY_PATH}#PRIVATE-FRAGMENT", "fragment_present"),
    (2024, f"https://PRIVATE-USER@www.sec.gov{SERIES_CLASS_2024_LEGACY_PATH}", "userinfo_present"),
    (2024, f"https://www.sec.gov:8443{SERIES_CLASS_2024_LEGACY_PATH}", "nonstandard_port"),
    (2024, SERIES_CLASS_2024_LEGACY_PATH.replace("/investment-company-series-class-2024.csv", "/../investment-company-series-and-class-information/investment-company-series-class-2024.csv"), "traversal_present"),
    (2024, SERIES_CLASS_2024_LEGACY_PATH.replace("/investment-company-series-class-2024.csv", "/%2e%2e/investment-company-series-and-class-information/investment-company-series-class-2024.csv"), "encoded_traversal_present"),
    (2024, f"https://www.sec.gov.evil.example{SERIES_CLASS_2024_LEGACY_PATH}", "host_not_allowed"),
    (2024, legacy_series_href(2024, extension="xml"), "extension_not_csv"),
])
def test_2024_legacy_series_path_is_an_exact_exception(
    year: int,
    value: str,
    failure_code: str,
) -> None:
    dataset = "investment_company_series_class"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(dataset, year, f"6/1/{year}", custom_href=value)]),
            evidence_cutoff=CUTOFF,
        )
    diagnostic = caught.value.diagnostic
    candidate = diagnostic.candidate_diagnostics[0]
    assert caught.value.reason_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else "selected_href_rejected"
    )
    assert candidate.failure_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else failure_code
    )
    assert candidate.url_validation_state == "rejected"
    rendered = json.dumps(diagnostic.to_safe_dict(), sort_keys=True)
    assert "PRIVATE-QUERY" not in rendered
    assert "PRIVATE-FRAGMENT" not in rendered
    assert "PRIVATE-USER" not in rendered


@pytest.mark.parametrize("dataset", ["closed_end_fund", "business_development_company"])
@pytest.mark.parametrize("series_path", [SERIES_CLASS_2024_LEGACY_PATH, SERIES_CLASS_2023_UNDERSCORE_PATH])
def test_series_historical_exceptions_do_not_change_other_dataset_paths(dataset: str, series_path: str) -> None:
    modern = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        page(dataset, [row(dataset, 2024, "6/1/2024")]),
        evidence_cutoff=CUTOFF,
    )
    assert modern.dataset_year == 2024
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(dataset, 2024, "6/1/2024", custom_href=series_path)]),
            evidence_cutoff=CUTOFF,
        )
    assert caught.value.reason_code == "selected_path_template_mismatch"
    assert caught.value.diagnostic.candidate_diagnostics[0].failure_code == "selected_path_template_mismatch"


def test_anchor_tail_two_and_four_digit_dates_and_cutoff_are_supported() -> None:
    dataset = "investment_company_series_class"
    for value in ("8/14/26", "08/14/26", "8/14/2026", "08/14/2026"):
        result = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, value)]), evidence_cutoff=CUTOFF)
        assert result.effective_date == CUTOFF


def test_unique_download_table_ignores_unrelated_tables_and_normalizes_headers() -> None:
    dataset = "closed_end_fund"
    unrelated = "<table><tr><th>Field</th><th>Description</th></tr><tr><td>CSV</td><td>x</td></tr></table>"
    html = page(dataset, [row(dataset, 2026, "6/1/2026")], headers=("\u00a0FILE ", " format", "SIZE\u00a0"), extra=unrelated)
    assert select_dated_official_csv(dataset, LANDING_PAGES[dataset], html, evidence_cutoff=CUTOFF).dataset_year == 2026


def test_csv_xml_order_and_row_order_do_not_change_selection() -> None:
    dataset = "business_development_company"
    rows = [row(dataset, 2016, None, format="XML"), row(dataset, 2026, "6/1/2026"), row(dataset, 2026, "6/1/2026", format="XML"), row(dataset, 2016, None)]
    first = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    second = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, list(reversed(rows))), evidence_cutoff=CUTOFF)
    assert (first.url, first.dataset_year, first.effective_date) == (second.url, second.dataset_year, second.effective_date)


def test_many_historical_rows_select_by_date_not_dom_order() -> None:
    dataset = "investment_company_series_class"
    rows = [row(dataset, year, f"6/1/{year}") for year in range(2010, 2027)]
    first = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    second = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, list(reversed(rows))), evidence_cutoff=CUTOFF)
    assert (first.url, first.dataset_year, first.effective_date) == (second.url, second.dataset_year, second.effective_date)
    assert first.dataset_year == 2026


def test_future_candidate_is_counted_and_previous_eligible_selected() -> None:
    dataset = "closed_end_fund"
    result = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2025, "12/1/2025"), row(dataset, 2026, "8/15/2026")]), evidence_cutoff=CUTOFF)
    assert result.dataset_year == 2025 and result.future_dated_count == 1


def test_duplicate_same_url_and_date_is_deduplicated() -> None:
    dataset = "closed_end_fund"
    item = row(dataset, 2026, "6/1/2026")
    result = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [item, item]), evidence_cutoff=CUTOFF)
    assert result.eligible_count == 1 and result.diagnostic.max_date_candidate_count == 1
    assert result.diagnostic.selected_count == 1
    assert [item.selection_state for item in result.diagnostic.candidate_diagnostics] == [
        "selected", "duplicate_excluded",
    ]


@pytest.mark.parametrize(("html", "reason"), [
    ("<html></html>", "download_table_not_found"),
    ("<table><tr><th>Year</th><th>Format</th><th>URL</th></tr></table>", "download_table_not_found"),
])
def test_table_discovery_failures_have_exact_reason(html: str, reason: str) -> None:
    dataset = "closed_end_fund"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], html, evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == reason


def test_multiple_download_tables_are_rejected() -> None:
    dataset = "closed_end_fund"
    table = page(dataset, [row(dataset, 2026, "6/1/2026")]).removeprefix("<html><body>").removesuffix("</body></html>")
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], f"<html>{table}{table}</html>", evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == "download_table_ambiguous"


@pytest.mark.parametrize(("rows", "reason"), [
    (['<tr><td><a href="x">2026</a></td><td>CSV</td></tr>'], "row_shape_invalid"),
    (['<tr><td>2026 Updated 6/1/2026</td><td>CSV</td><td>1</td></tr>'], "anchor_cardinality_invalid"),
    (['<tr><td><a href="x">latest</a> Updated 6/1/2026</td><td>CSV</td><td>1</td></tr>'], "file_year_missing"),
])
def test_row_shape_anchor_and_year_failures(rows: list[str], reason: str) -> None:
    dataset = "closed_end_fund"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == reason


@pytest.mark.parametrize(("updated", "reason"), [
    ("not-a-date", "updated_date_parse_failed"),
    ("13/40/2026", "updated_date_parse_failed"),
    ("6/1/2025", "file_year_date_mismatch"),
    ("6/1/2026 Updated 6/2/2026", "multiple_dates_in_row"),
])
def test_date_failures_are_not_ignored(updated: str, reason: str) -> None:
    dataset = "closed_end_fund"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, updated)]), evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == reason


def test_undated_current_or_only_candidate_hard_fails_but_old_archive_does_not() -> None:
    dataset = "closed_end_fund"
    valid = row(dataset, 2025, "12/1/2025")
    old = row(dataset, 2016, None)
    assert select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [old, valid]), evidence_cutoff=CUTOFF).dataset_year == 2025
    for rows in ([row(dataset, 2026, None), valid], [old]):
        with pytest.raises(SecLandingDiscoveryError) as caught:
            select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, list(rows)), evidence_cutoff=CUTOFF)
        assert caught.value.reason_code == "current_candidate_date_missing"


def test_no_csv_and_no_cutoff_candidate_are_distinct() -> None:
    dataset = "closed_end_fund"
    with pytest.raises(SecLandingDiscoveryError) as no_csv:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, "6/1/2026", format="XML")]), evidence_cutoff=CUTOFF)
    assert no_csv.value.reason_code == "no_csv_candidate"
    with pytest.raises(SecLandingDiscoveryError) as future:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, "8/15/2026")]), evidence_cutoff=CUTOFF)
    assert future.value.reason_code == "no_cutoff_eligible_candidate"


def test_same_max_date_distinct_urls_hard_fails() -> None:
    dataset = "closed_end_fund"
    rows = [
        row(dataset, 2026, "6/1/2026"),
        row(
            dataset,
            2026,
            "6/1/2026",
            custom_href="/files/investment/data/other/closed-end-fund-information/other-2026.csv",
        ),
    ]
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, rows), evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == "max_date_distinct_url_tie"


@pytest.mark.parametrize(("bad", "failure_code"), [
    ("http://www.sec.gov{path}", "scheme_not_https"),
    ("https://example.test{path}", "host_not_allowed"),
    ("https://www.sec.gov.evil.example{path}", "host_not_allowed"),
    ("https://user@www.sec.gov{path}", "userinfo_present"),
    ("{path}\\evil.csv", "backslash_present"),
    ("/files/../private/file.csv", "traversal_present"),
    ("/files/%2e%2e/private/file.csv", "encoded_traversal_present"),
    ("/files/%2E%2E/private/file.csv", "encoded_traversal_present"),
    ("/files/%252e%252e/private/file.csv", "encoded_traversal_present"),
    ("https://www.sec.gov{path}?download=PRIVATE-QUERY", "query_present"),
    ("https://www.sec.gov{path}#PRIVATE-FRAGMENT", "fragment_present"),
    ("https://www.sec.gov:8443{path}", "nonstandard_port"),
    ("/files/other-dataset/file.csv", "path_root_not_allowed"),
    ("{path_without_extension}", "extension_not_csv"),
    ("javascript:data.csv", "scheme_not_https"),
    ("https://[broken", "malformed_url"),
])
def test_url_policy_rejects_with_specific_safe_code(bad: str, failure_code: str) -> None:
    dataset = "closed_end_fund"
    value = bad.format(path=href(dataset, 2026), path_without_extension=href(dataset, 2026)[:-4])
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, "6/1/2026", custom_href=value)]), evidence_cutoff=CUTOFF)
    assert caught.value.reason_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else "selected_href_rejected"
    )
    candidate = caught.value.diagnostic.candidate_diagnostics[0]
    assert caught.value.diagnostic.schema_version == "3.0"
    assert candidate.failure_code == (
        "selected_path_template_mismatch"
        if failure_code == "path_template_mismatch"
        else failure_code
    )
    assert candidate.url_validation_state == "rejected"
    rendered = json.dumps(caught.value.diagnostic.to_safe_dict(), sort_keys=True)
    assert "PRIVATE-QUERY" not in rendered
    assert "PRIVATE-FRAGMENT" not in rendered


def test_url_failure_code_contract_is_finite_and_complete() -> None:
    assert {item.value for item in SecCsvUrlFailureCode} == {
        "scheme_not_https", "userinfo_present", "host_not_allowed", "nonstandard_port",
        "backslash_present", "traversal_present", "encoded_traversal_present",
        "query_present", "fragment_present", "path_template_mismatch", "extension_not_csv",
        "file_year_mismatch", "malformed_url", "path_root_not_allowed",
    }


def test_url_path_year_mismatch_has_distinct_code() -> None:
    dataset = "closed_end_fund"
    wrong_year_path = href(dataset, 2025)
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(dataset, 2026, "6/1/2026", custom_href=wrong_year_path)]),
            evidence_cutoff=CUTOFF,
        )
    candidate = caught.value.diagnostic.candidate_diagnostics[0]
    assert caught.value.reason_code == "file_year_mismatch"
    assert candidate.failure_code == "file_year_mismatch"
    assert candidate.parsed_file_year == 2026
    assert candidate.path_template_match is False


def test_three_candidate_failure_records_actionable_candidate_context() -> None:
    dataset = "investment_company_series_class"
    unrelated = "<table><tr><th>Field</th><th>Description</th></tr><tr><td>CSV</td><td>not a download</td></tr></table>"
    rows = [
        row(dataset, 2025, "6/1/2025", size="900 KB"),
        row(dataset, 2026, "6/1/26", size="1\u00a0MB"),
        row(dataset, 2024, "6/1/2024", custom_href="/files/investment/data/other/unrelated/report-2024.csv", size="2 MB"),
    ]
    result = select_dated_official_csv(
        dataset, LANDING_PAGES[dataset], page(dataset, rows, extra=unrelated), evidence_cutoff=CUTOFF,
    )
    diagnostic = result.diagnostic
    assert diagnostic.csv_candidate_count == 3
    assert diagnostic.allowlisted_count == 2
    assert diagnostic.cutoff_eligible_count == 3
    assert diagnostic.rejected_count == 0
    assert diagnostic.selected_count == 1
    assert [item.selection_state for item in diagnostic.candidate_diagnostics] == [
        "eligible_not_selected", "selected", "ignored_warning",
    ]
    assert diagnostic.allowlisted_count == sum(
        item.url_validation_state == "accepted" for item in diagnostic.candidate_diagnostics
    )
    assert diagnostic.cutoff_eligible_count == sum(
        item.baseline_url_status == "passed"
        and item.updated_date is not None
        and item.temporal_relation != "future"
        for item in diagnostic.candidate_diagnostics
    )
    assert diagnostic.historical_path_warning_count == 1
    assert diagnostic.selected_count == sum(
        item.selection_state == "selected" for item in diagnostic.candidate_diagnostics
    )
    assert diagnostic.table_count == 2
    assert len(diagnostic.candidate_diagnostics) == 3
    rejected = diagnostic.candidate_diagnostics[2]
    assert rejected.candidate_ordinal == 3
    assert rejected.download_table_ordinal == 2
    assert rejected.table_row_index == 4
    assert rejected.normalized_format == "csv"
    assert rejected.normalized_size_text == "2 MB"
    assert rejected.parsed_file_year == 2024
    assert rejected.parsed_updated_date == "2024-06-01"
    assert rejected.anchor_count == 1
    assert rejected.selection_state == "ignored_warning"
    assert rejected.url_validation_state == "rejected"
    assert rejected.failure_code == "historical_path_template_mismatch_ignored"
    assert rejected.normalized_path == "/files/investment/data/other/unrelated/report-2024.csv"
    assert rejected.path_basename == "report-2024.csv"
    assert rejected.path_template_match is False


def test_legal_relative_and_absolute_paths_keep_selection_behavior() -> None:
    dataset = "closed_end_fund"
    relative = href(dataset, 2025)
    absolute = f"https://www.sec.gov{href(dataset, 2026)}"
    result = select_dated_official_csv(
        dataset,
        LANDING_PAGES[dataset],
        page(dataset, [
            row(dataset, 2025, "6/1/2025", custom_href=relative),
            row(dataset, 2026, "6/1/2026", custom_href=absolute),
        ]),
        evidence_cutoff=CUTOFF,
    )
    assert result.url == absolute
    assert [item.url_validation_state for item in result.diagnostic.candidate_diagnostics] == ["accepted", "accepted"]
    assert result.diagnostic.candidate_diagnostics[1].selection_state == "selected"


def test_missing_size_and_date_are_null_not_raw_content() -> None:
    dataset = "closed_end_fund"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(dataset, 2026, None, size="")]),
            evidence_cutoff=CUTOFF,
        )
    candidate = caught.value.diagnostic.candidate_diagnostics[0]
    assert candidate.normalized_size_text is None
    assert candidate.parsed_updated_date is None
    assert caught.value.reason_code == "current_candidate_date_missing"


def test_diagnostic_serialization_is_deterministic_and_does_not_leak_url_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = "closed_end_fund"
    sentinel = "PRIVATE-CONTACT-SENTINEL@invalid.example"
    malicious = f"https://{sentinel}@www.sec.gov{href(dataset, 2026)}?secret={sentinel}#{sentinel}"
    rendered: list[str] = []
    for _ in range(2):
        with pytest.raises(SecLandingDiscoveryError) as caught:
            select_dated_official_csv(
                dataset,
                LANDING_PAGES[dataset],
                page(dataset, [row(dataset, 2026, "6/1/2026", custom_href=malicious)]),
                evidence_cutoff=CUTOFF,
            )
        rendered.append(json.dumps(caught.value.diagnostic.to_safe_dict(), sort_keys=True))
        assert caught.value.reason_code == "selected_href_rejected"
        assert caught.value.diagnostic.candidate_diagnostics[0].failure_code == "userinfo_present"
    assert rendered[0] == rendered[1]
    assert sentinel not in rendered[0]
    captured = capsys.readouterr()
    assert sentinel not in captured.out and sentinel not in captured.err


def test_diagnostic_and_error_do_not_expose_raw_html_or_sentinel() -> None:
    dataset = "closed_end_fund"
    sentinel = "PRIVATE-CONTACT-SENTINEL@invalid.example"
    html = page(dataset, [row(dataset, 2026, "bad-date")], extra=f"<p>{sentinel}</p>")
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(dataset, LANDING_PAGES[dataset], html, evidence_cutoff=CUTOFF)
    rendered = json.dumps(caught.value.diagnostic.to_safe_dict(), sort_keys=True) + repr(caught.value) + str(caught.value)
    assert sentinel not in rendered and "bad-date" not in rendered
    assert caught.value.reason_code == "updated_date_parse_failed"


def test_2023_path_rejection_does_not_expose_credential_sentinel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = "investment_company_series_class"
    sentinel = "PRIVATE-CREDENTIAL-SENTINEL"
    with pytest.raises(SecLandingDiscoveryError) as caught:
        select_dated_official_csv(
            dataset,
            LANDING_PAGES[dataset],
            page(dataset, [row(
                dataset,
                2023,
                "6/8/2023",
                custom_href=f"{SERIES_CLASS_2023_UNDERSCORE_PATH}?credential={sentinel}",
            )]),
            evidence_cutoff=CUTOFF,
        )
    rendered = json.dumps(caught.value.diagnostic.to_safe_dict(), sort_keys=True) + repr(caught.value) + str(caught.value)
    captured = capsys.readouterr()
    assert sentinel not in rendered
    assert sentinel not in captured.out and sentinel not in captured.err


@pytest.mark.parametrize("content_type", ["text/csv", "text/csv; charset=utf-8", "application/octet-stream"])
def test_verified_selection_accepts_bounded_csv_content_types(content_type: str, tmp_path: Path) -> None:
    dataset = "closed_end_fund"
    selection = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, "6/1/2026")]), evidence_cutoff=CUTOFF)
    source = tmp_path / "source.csv"
    source.write_text("CIK,Company Name\n1,Fixture\n", encoding="utf-8")
    validate_selected_csv_response(selection, content_type, source)


def test_octet_stream_still_requires_matching_csv_schema(tmp_path: Path) -> None:
    dataset = "closed_end_fund"
    selection = select_dated_official_csv(dataset, LANDING_PAGES[dataset], page(dataset, [row(dataset, 2026, "6/1/2026")]), evidence_cutoff=CUTOFF)
    source = tmp_path / "source.csv"
    source.write_text("unexpected,fields\n1,2\n", encoding="utf-8")
    with pytest.raises(SecTransportError, match="header"):
        validate_selected_csv_response(selection, "application/octet-stream", source)


def test_parser_has_explicit_network_prohibition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network attempted"))
    dataset = "investment_company_series_class"
    result = select_dated_official_csv(dataset, LANDING_PAGES[dataset], fixture("series_class_landing.html"), evidence_cutoff=CUTOFF)
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


def test_submissions_zip_accepts_historical_shards_but_requires_cik_root(
    tmp_path: Path,
) -> None:
    payload = json.dumps(
        {
            "cik": "1",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000001-26-000001"],
                    "filingDate": ["2026-09-09"],
                    "acceptanceDateTime": ["20260909163000"],
                    "form": ["10-K"],
                },
                "files": [],
            },
        }
    )
    shard = json.dumps(
        {
            "accessionNumber": ["0000000001-20-000001"],
            "filingDate": ["2020-03-01"],
            "acceptanceDateTime": ["20200301163000"],
            "form": ["10-K"],
        }
    )
    safe = tmp_path / "safe-shard.zip"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("CIK0000000001.json", payload)
        archive.writestr("CIK0000000001-submissions-001.json", shard)
        archive.writestr("placeholder.txt", "fixture marker")
    validate_submissions_zip(safe)

    missing_root = tmp_path / "missing-root.zip"
    with zipfile.ZipFile(missing_root, "w") as archive:
        archive.writestr("CIK0000000001-submissions-001.json", shard)
    with pytest.raises(SecTransportError, match="root coverage is incomplete"):
        validate_submissions_zip(missing_root)
