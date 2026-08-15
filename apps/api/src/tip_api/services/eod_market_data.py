"""Query service for canonical EOD market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.persistence.eod_read import EodReadRepository, EodSessionNotFoundError
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor, EodSessionPage, EodSessionSummary


class EodQueryValidationError(ValueError):
    """Raised when an EOD query request is outside the supported boundary."""


@dataclass(frozen=True, slots=True)
class EodMarketDataQueryService:
    repository: EodReadRepository

    def list_sessions(self) -> tuple[EodSessionDescriptor, ...]:
        return self.repository.list_sessions()

    def get_latest_session(self) -> EodSessionDescriptor:
        sessions = self.list_sessions()
        if not sessions:
            raise EodSessionNotFoundError("no completed EOD sessions are available")
        return sessions[-1]

    def get_session_summary(self, session_date: date) -> EodSessionSummary:
        bars = self.repository.read_bars(session_date)
        if not bars:
            raise EodSessionNotFoundError("EOD session is not available")
        first = bars[0]
        return EodSessionSummary(
            session_date=session_date,
            total_records=len(bars),
            common_stock_count=sum(1 for bar in bars if bar.instrument_type is InstrumentType.COMMON_STOCK),
            etf_count=sum(1 for bar in bars if bar.instrument_type is InstrumentType.ETF),
            other_supported_count=sum(1 for bar in bars if bar.instrument_type not in {InstrumentType.COMMON_STOCK, InstrumentType.ETF}),
            missing_vwap_count=sum(1 for bar in bars if bar.vwap is None),
            missing_trade_count_count=sum(1 for bar in bars if bar.trade_count is None),
            zero_volume_count=sum(1 for bar in bars if bar.volume == 0),
            quality_warning_count=sum(1 for bar in bars if bar.quality_flags),
            source=first.source,
            identity_as_of_date=self._descriptor(session_date).identity_as_of_date,
        )

    def get_bars_page(
        self,
        *,
        session_date: date,
        limit: int = 100,
        offset: int = 0,
        ticker: str | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> EodSessionPage:
        if limit < 1 or limit > 200:
            raise EodQueryValidationError("limit must be between 1 and 200")
        if offset < 0:
            raise EodQueryValidationError("offset must be greater than or equal to zero")
        normalized_ticker = _normalize_ticker(ticker) if ticker is not None else None
        bars = self.repository.read_bars(session_date)
        filtered: list[EodMarketBarReadModel] = []
        for bar in bars:
            if normalized_ticker is not None and bar.ticker != normalized_ticker:
                continue
            if instrument_type is not None and bar.instrument_type is not instrument_type:
                continue
            filtered.append(bar)
        total = len(filtered)
        items = tuple(filtered[offset : offset + limit])
        return EodSessionPage(session_date=session_date, total_count=total, limit=limit, offset=offset, items=items)

    def _descriptor(self, session_date: date) -> EodSessionDescriptor:
        for descriptor in self.list_sessions():
            if descriptor.session_date == session_date:
                return descriptor
        raise EodSessionNotFoundError("EOD session is not available")


def _normalize_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not ticker:
        raise EodQueryValidationError("ticker must not be empty")
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if any(char not in allowed for char in ticker):
        raise EodQueryValidationError("ticker contains unsupported characters")
    return ticker
