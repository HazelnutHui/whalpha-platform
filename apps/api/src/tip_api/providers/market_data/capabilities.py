"""Market-data provider capability declarations."""

from enum import StrEnum


class ProviderCapability(StrEnum):
    """Capabilities supported by a market-data provider implementation."""

    INSTRUMENT_MASTER = "instrument_master"
    EOD_PRICE_BARS = "eod_price_bars"
