"""Tests for bounded inactive-security lifecycle coverage probing."""

from datetime import date

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.historical_lifecycle_probe import (
    COMPLETION_CENSUS_CONTRACT_VERSION,
    COMPLETION_CENSUS_MAXIMUM_REQUEST_COUNT,
    CENSUS_CONTRACT_VERSION,
    LifecycleProbeStatus,
    census_complete_massive_historical_lifecycle_pagination,
    census_massive_historical_lifecycle_pagination,
    probe_massive_historical_lifecycle_coverage,
    required_lifecycle_census_acknowledgement,
    required_lifecycle_probe_acknowledgement,
)
from tip_api.providers.massive.transport import MassiveTransportResponseError


class FakeTransport:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[str, object]] = []

    def get_json(self, path: str, *, params: object, **_: object) -> object:
        self.calls.append((path, params))
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key="fixture")


def test_two_page_probe_summarizes_without_identifiers() -> None:
    first = {
        "results": [
            {
                "ticker": "OLD",
                "active": False,
                "delisted_utc": "2026-01-02",
                "last_updated_utc": "2026-01-03T00:00:00Z",
                "cik": "1",
            },
            {"ticker": "DUP", "active": False, "composite_figi": "BBG1"},
        ],
        "next_url": "https://api.massive.com/v3/reference/tickers?cursor=abc",
    }
    second = {
        "results": [
            {"ticker": "DUP", "active": True, "share_class_figi": "BBG2"},
            {"ticker": "NOACTIVE"},
        ]
    }
    transport = FakeTransport([first, second])

    result = probe_massive_historical_lifecycle_coverage(
        config=_config(),
        transport=transport,  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )

    assert result.status is LifecycleProbeStatus.COMPLETED
    assert result.request_count == 2
    assert result.page_count == 2
    assert result.result_count == 4
    assert result.pagination_complete
    assert result.active_false_count == 2
    assert result.active_true_conflict_count == 1
    assert result.active_missing_count == 1
    assert result.duplicate_ticker_count == 1
    assert dict(result.field_presence_counts) == {
        "delisted_utc": 1,
        "last_updated_utc": 1,
        "cik": 1,
        "composite_figi": 1,
        "share_class_figi": 1,
    }
    assert "OLD" not in str(result.as_dict())
    assert not result.response_body_retained
    assert result.data_write_count == 0
    assert not result.coverage_conclusion_authorized
    assert not result.pilot_authorized


def test_probe_stops_at_two_page_ceiling() -> None:
    page = {
        "results": [{"ticker": "OLD", "active": False}],
        "next_url": "https://api.massive.com/v3/reference/tickers?cursor=next",
    }
    result = probe_massive_historical_lifecycle_coverage(
        config=_config(),
        transport=FakeTransport([page, page]),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )
    assert result.status is LifecycleProbeStatus.TRUNCATED_AT_CEILING
    assert result.request_count == 2
    assert not result.pagination_complete


def test_foreign_pagination_host_fails_closed() -> None:
    page = {
        "results": [],
        "next_url": "https://example.com/v3/reference/tickers?cursor=bad",
    }
    result = probe_massive_historical_lifecycle_coverage(
        config=_config(),
        transport=FakeTransport([page]),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )
    assert result.status is LifecycleProbeStatus.MALFORMED_RESPONSE
    assert result.request_count == 1
    assert result.page_count == 1
    assert not result.pagination_complete


def test_entitlement_denial_is_safe() -> None:
    result = probe_massive_historical_lifecycle_coverage(
        config=_config(),
        transport=FakeTransport(  # type: ignore[arg-type]
            [MassiveTransportResponseError(403, "safe")]
        ),
        anchor_date=date(2026, 7, 16),
    )
    assert result.status is LifecycleProbeStatus.ENTITLEMENT_DENIED
    assert result.request_count == 1
    assert result.result_count == 0


def test_acknowledgement_binds_date_and_revision() -> None:
    first = required_lifecycle_probe_acknowledgement(
        anchor_date=date(2026, 7, 16), revision="a" * 40
    )
    assert first.startswith("I_AUTHORIZE_MASSIVE_LIFECYCLE_PROBE_")
    assert first != required_lifecycle_probe_acknowledgement(
        anchor_date=date(2026, 7, 15), revision="a" * 40
    )
    assert first != required_lifecycle_probe_acknowledgement(
        anchor_date=date(2026, 7, 16), revision="b" * 40
    )


def test_six_page_census_can_complete_without_changing_two_page_contract() -> None:
    pages = [
        {
            "results": [{"ticker": f"OLD{index}", "active": False}],
            "next_url": (
                "https://api.massive.com/v3/reference/tickers?"
                f"cursor={index + 1}"
            ),
        }
        for index in range(5)
    ]
    pages.append({"results": [{"ticker": "OLD5", "active": False}]})

    result = census_massive_historical_lifecycle_pagination(
        config=_config(),
        transport=FakeTransport(pages),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )

    assert result.contract_version == CENSUS_CONTRACT_VERSION
    assert result.status is LifecycleProbeStatus.COMPLETED
    assert result.request_count == 6
    assert result.page_count == 6
    assert result.pagination_complete
    assert result.result_count == 6


def test_six_page_census_reports_truncation_at_unchanged_ceiling() -> None:
    pages = [
        {
            "results": [{"ticker": f"OLD{index}", "active": False}],
            "next_url": (
                "https://api.massive.com/v3/reference/tickers?"
                f"cursor={index + 1}"
            ),
        }
        for index in range(6)
    ]
    result = census_massive_historical_lifecycle_pagination(
        config=_config(),
        transport=FakeTransport(pages),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )
    assert result.status is LifecycleProbeStatus.TRUNCATED_AT_CEILING
    assert result.request_count == 6
    assert not result.pagination_complete


def test_census_acknowledgement_differs_from_two_page_probe() -> None:
    census = required_lifecycle_census_acknowledgement(
        anchor_date=date(2026, 7, 16), revision="a" * 40
    )
    probe = required_lifecycle_probe_acknowledgement(
        anchor_date=date(2026, 7, 16), revision="a" * 40
    )
    assert census.startswith("I_AUTHORIZE_MASSIVE_LIFECYCLE_CENSUS_")
    assert census != probe


def test_completion_census_reaches_natural_end_beyond_old_six_page_ceiling() -> None:
    pages = [
        {
            "results": [{"ticker": f"OLD{index}", "active": False}],
            "next_url": (
                "https://api.massive.com/v3/reference/tickers?"
                f"cursor={index + 1}"
            ),
        }
        for index in range(8)
    ]
    pages.append({"results": [{"ticker": "OLD8", "active": False}]})

    result = census_complete_massive_historical_lifecycle_pagination(
        config=_config(),
        transport=FakeTransport(pages),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )

    assert result.contract_version == COMPLETION_CENSUS_CONTRACT_VERSION
    assert result.status is LifecycleProbeStatus.COMPLETED
    assert result.request_count == 9
    assert result.pagination_complete


def test_completion_census_remains_bounded_at_twenty_pages() -> None:
    pages = [
        {
            "results": [{"ticker": f"OLD{index}", "active": False}],
            "next_url": (
                "https://api.massive.com/v3/reference/tickers?"
                f"cursor={index + 1}"
            ),
        }
        for index in range(COMPLETION_CENSUS_MAXIMUM_REQUEST_COUNT)
    ]

    result = census_complete_massive_historical_lifecycle_pagination(
        config=_config(),
        transport=FakeTransport(pages),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )

    assert result.status is LifecycleProbeStatus.TRUNCATED_AT_CEILING
    assert result.request_count == COMPLETION_CENSUS_MAXIMUM_REQUEST_COUNT
    assert not result.pagination_complete


def test_completion_census_stops_if_record_ceiling_is_exceeded(monkeypatch) -> None:
    monkeypatch.setattr(
        "tip_api.providers.massive.historical_lifecycle_probe."
        "COMPLETION_CENSUS_MAXIMUM_RESULT_COUNT",
        1,
    )
    page = {
        "results": [
            {"ticker": "OLD1", "active": False},
            {"ticker": "OLD2", "active": False},
        ]
    }

    result = census_complete_massive_historical_lifecycle_pagination(
        config=_config(),
        transport=FakeTransport([page]),  # type: ignore[arg-type]
        anchor_date=date(2026, 7, 16),
    )

    assert result.status is LifecycleProbeStatus.RECORD_CEILING_EXCEEDED
    assert not result.pagination_complete
