"""Tests for the bounded Massive historical entitlement probe."""

from datetime import date

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.historical_entitlement_probe import (
    CONTRACT_VERSION,
    EntitlementProbeStatus,
    probe_massive_historical_entitlements,
    required_probe_acknowledgement,
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


def test_probe_is_bounded_non_retaining_and_deterministic() -> None:
    outcomes = [
        {"results": [{"T": "SPY"}]},
        {"results": []},
        {"results": [{"id": "split"}]},
        {"results": []},
    ]
    first_transport = FakeTransport(outcomes)
    second_transport = FakeTransport(outcomes)
    config = MassiveProviderConfig(api_key="fixture")

    first = probe_massive_historical_entitlements(
        config=config,
        transport=first_transport,  # type: ignore[arg-type]
        session_date=date(2026, 7, 16),
    )
    second = probe_massive_historical_entitlements(
        config=config,
        transport=second_transport,  # type: ignore[arg-type]
        session_date=date(2026, 7, 16),
    )

    assert first == second
    assert first.contract_version == CONTRACT_VERSION
    assert first.request_count == 4
    assert len(first_transport.calls) == 4
    assert not first.response_body_retained
    assert first.data_write_count == 0
    assert not first.permission_conclusion_authorized
    assert not first.pilot_authorized
    assert [line.result_count for line in first.lines] == [1, 0, 1, 0]
    assert all(line.status is EntitlementProbeStatus.ACCESSIBLE for line in first.lines)
    assert first.logical_content_fingerprint == second.logical_content_fingerprint


def test_probe_classifies_auth_entitlement_rate_and_http_errors() -> None:
    transport = FakeTransport(
        [
            MassiveTransportResponseError(401, "safe"),
            MassiveTransportResponseError(403, "safe"),
            MassiveTransportResponseError(429, "safe", retry_after_seconds=17),
            MassiveTransportResponseError(400, "safe"),
        ]
    )
    result = probe_massive_historical_entitlements(
        config=MassiveProviderConfig(api_key="fixture"),
        transport=transport,  # type: ignore[arg-type]
        session_date=date(2026, 7, 16),
    )

    assert [line.status for line in result.lines] == [
        EntitlementProbeStatus.AUTHENTICATION_FAILED,
        EntitlementProbeStatus.ENTITLEMENT_DENIED,
        EntitlementProbeStatus.RATE_LIMITED,
        EntitlementProbeStatus.HTTP_ERROR,
    ]
    assert result.lines[2].retry_after_seconds == 17
    assert all(line.result_count is None for line in result.lines)


def test_probe_rejects_success_payload_without_results_list() -> None:
    transport = FakeTransport([{}, {}, {}, {}])
    result = probe_massive_historical_entitlements(
        config=MassiveProviderConfig(api_key="fixture"),
        transport=transport,  # type: ignore[arg-type]
        session_date=date(2026, 7, 16),
    )

    assert all(
        line.status is EntitlementProbeStatus.MALFORMED_RESPONSE
        for line in result.lines
    )


def test_acknowledgement_is_exactly_bound() -> None:
    first = required_probe_acknowledgement(
        session_date=date(2026, 7, 16), revision="a" * 40
    )
    assert first.startswith("I_AUTHORIZE_MASSIVE_ENTITLEMENT_PROBE_")
    assert first != required_probe_acknowledgement(
        session_date=date(2026, 7, 15), revision="a" * 40
    )
    assert first != required_probe_acknowledgement(
        session_date=date(2026, 7, 16), revision="b" * 40
    )
