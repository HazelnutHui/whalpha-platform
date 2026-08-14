from __future__ import annotations

from datetime import date
from uuid import UUID

from tip_api.providers.market_data import InstrumentQuery, MarketDataProvider, ProviderCapability
from tests.providers.support.in_memory_market_data_provider import InMemoryMarketDataProvider


class IncompleteProvider:
    @property
    def provider_id(self) -> str:
        return "incomplete"


def test_in_memory_provider_satisfies_runtime_protocol() -> None:
    provider = InMemoryMarketDataProvider(
        provider_id="test_provider",
        capabilities=frozenset({ProviderCapability.INSTRUMENT_MASTER}),
    )

    assert isinstance(provider, MarketDataProvider)


def test_incomplete_object_does_not_satisfy_protocol() -> None:
    assert not isinstance(IncompleteProvider(), MarketDataProvider)


def test_provider_id_and_capabilities_are_exposed() -> None:
    capabilities = frozenset({ProviderCapability.INSTRUMENT_MASTER})
    provider = InMemoryMarketDataProvider(provider_id=" test_provider ", capabilities=capabilities)

    assert provider.provider_id == "test_provider"
    assert provider.capabilities == capabilities
    assert isinstance(provider.capabilities, frozenset)


def test_results_are_tuples() -> None:
    provider = InMemoryMarketDataProvider(
        provider_id="test_provider",
        capabilities=frozenset({ProviderCapability.INSTRUMENT_MASTER}),
    )

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert result == ()
    assert isinstance(result, tuple)


def test_canonical_result_model_type() -> None:
    from tests.providers.test_in_memory_market_data_provider import instrument_record

    record = instrument_record(instrument_id=UUID(int=1))
    provider = InMemoryMarketDataProvider(
        provider_id="test_provider",
        capabilities=frozenset({ProviderCapability.INSTRUMENT_MASTER}),
        instruments=(record,),
    )

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert result == (record,)
