from datetime import UTC, datetime
from decimal import Decimal

from pydantic import SecretStr

from tip_api.contracts.analytics.v1.quant_research_massive_starter_capability_sample import ProbeStatus
from tip_api.persistence.quant_research_massive_starter_capability_sample import (
    publish_massive_starter_capability_sample,
    read_massive_starter_capability_sample,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import MassiveTransportResponseError
from tip_api.services.quant_research_massive_starter_capability_sample import (
    execute_massive_starter_capability_sample,
    registered_massive_starter_capability_sample_plan_v1,
)


class FixtureTransport:
    def __init__(self, *, fail_at: int | None = None) -> None:
        self.calls = 0
        self.fail_at = fail_at

    def get_json(self, path, *, params, api_key, timeout_seconds, base_url):
        self.calls += 1
        if self.calls == self.fail_at:
            raise MassiveTransportResponseError(403, "denied")
        if path.endswith("/events"):
            return {
                "results": {
                    "events": (
                        [
                            {
                                "type": "ticker_change",
                                "date": "2024-09-09",
                                "ticker_change": {"ticker": "INVX"},
                            }
                        ]
                        if self.calls == 9
                        else []
                    )
                }
            }
        if path == "/v3/reference/tickers":
            ticker = params["ticker"]
            values = {
                "AGL": ("0001831097", "BBG00HCYVQQ4", "BBG00HCYVQR3"),
                "DRQ": ("0001042893", "BBG000BVDBY2", "BBG001SB9LK4"),
                "INVX": ("0001042893", "BBG000BVDBY2", "BBG001SB9LK4"),
                "URBN": ("0000912615", "BBG000BL79J3", "BBG001S7H9K1"),
            }
            cik, composite, share = values[ticker]
            return {
                "results": [
                    {
                        "ticker": ticker,
                        **({} if ticker == "INVX" else {"cik": cik}),
                        "composite_figi": composite,
                        "share_class_figi": share,
                        "type": "CS",
                    }
                ]
            }
        return {"results": {"ticker": path.rsplit("/", 1)[-1], "apiKey": api_key.get_secret_value()}}


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-secret"), request_timeout_seconds=Decimal("1"))


def test_complete_probe_is_bounded_sanitized_and_exactly_rereads(tmp_path) -> None:
    plan = registered_massive_starter_capability_sample_plan_v1()
    execution = execute_massive_starter_capability_sample(
        plan=plan,
        config=_config(),
        transport=FixtureTransport(),
        clock=lambda: datetime(2026, 9, 18, 12, tzinfo=UTC),
    )
    assert execution.result.status is ProbeStatus.COMPLETED
    assert execution.result.request_count == 10
    assert execution.result.historical_lane_admitted_count == 0
    dispositions = {
        item.lane.value: item.disposition
        for item in execution.result.lane_dispositions
    }
    assert dispositions == {
        "instrument_cik": "blocked",
        "security_form": "corroboration_only",
        "listing_aliases": "corroboration_only",
        "issuer_structure": "blocked",
    }
    assert "fixture-secret" not in str(execution.sanitized_responses)
    package = publish_massive_starter_capability_sample(
        custody_root=tmp_path / "custody",
        plan=plan,
        result=execution.result,
        sanitized_responses=dict(execution.sanitized_responses),
    )
    reread = read_massive_starter_capability_sample(package_path=package.package_path)
    assert reread.verification.exact_reread_status == "complete"


def test_entitlement_denial_stops_without_using_remaining_budget() -> None:
    execution = execute_massive_starter_capability_sample(
        plan=registered_massive_starter_capability_sample_plan_v1(),
        config=_config(),
        transport=FixtureTransport(fail_at=3),
        clock=lambda: datetime(2026, 9, 18, 12, tzinfo=UTC),
    )
    assert execution.result.status is ProbeStatus.STOPPED_ENTITLEMENT
    assert execution.result.request_count == 3
    assert execution.result.failed_request_sequence == 3
    assert len(execution.sanitized_responses) == 2


def test_registered_plan_has_three_cases_and_ten_requests() -> None:
    plan = registered_massive_starter_capability_sample_plan_v1()
    assert len(plan.samples) == 3
    assert len(plan.requests) == 10
    assert plan.maximum_request_count <= 12
    assert plan.outcome_selection_allowed is False
