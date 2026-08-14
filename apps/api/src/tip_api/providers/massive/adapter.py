"""Mock-testable Massive Stocks market-data provider adapter skeleton."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Callable, Iterable, Literal, Mapping
from urllib.parse import parse_qsl, urlparse
from uuid import UUID

from tip_api.contracts.market_data.v1 import EodPriceBarV1, InstrumentMasterV1, InstrumentStatus
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    ProviderAuthenticationError,
    ProviderCapability,
    ProviderDataError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    RevisionSelection,
    UnsupportedCapabilityError,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.mapping import (
    MASSIVE_PROVIDER_ID,
    map_custom_bar_payload,
    map_grouped_daily_bar_payload,
    map_ticker_payload,
)
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveParamValue,
    MassiveParams,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)

BarRequestStrategy = Literal["grouped_daily", "custom_bars"]
Clock = Callable[[], datetime]
InstrumentIdResolver = Mapping[UUID, str]


class MassiveMarketDataProvider:
    """Massive adapter skeleton using an injected transport.

    The class implements the provider-neutral Protocol while remaining unable
    to perform network I/O unless a caller deliberately supplies a transport.
    No production HTTP transport is implemented in this repository.
    """

    _capabilities = frozenset(
        {
            ProviderCapability.INSTRUMENT_MASTER,
            ProviderCapability.EOD_PRICE_BARS,
        }
    )

    def __init__(
        self,
        *,
        config: MassiveProviderConfig,
        transport: MassiveHttpTransport,
        instrument_tickers: InstrumentIdResolver | None = None,
        eod_bar_strategy: BarRequestStrategy = "grouped_daily",
        clock: Clock | None = None,
        max_pages: int = 20,
    ) -> None:
        if eod_bar_strategy not in {"grouped_daily", "custom_bars"}:
            raise ValueError("unsupported EOD bar request strategy")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than or equal to one")
        self._config = config
        self._transport = transport
        self._instrument_tickers = dict(instrument_tickers or {})
        self._eod_bar_strategy = eod_bar_strategy
        self._clock = clock or (lambda: datetime.now(UTC))
        self._max_pages = max_pages

    @property
    def provider_id(self) -> str:
        return MASSIVE_PROVIDER_ID

    @property
    def capabilities(self) -> frozenset[ProviderCapability]:
        return self._capabilities

    def get_instruments(self, query: InstrumentQuery) -> tuple[InstrumentMasterV1, ...]:
        self._require_capability(ProviderCapability.INSTRUMENT_MASTER)
        payloads = self._fetch_pages(
            "/v3/reference/tickers",
            {
                "date": query.as_of_date.isoformat(),
                "limit": 1000,
                **({"active": True} if query.active_only else {}),
            },
        )
        requested_ids = set(query.instrument_ids) if query.instrument_ids is not None else None
        records: list[InstrumentMasterV1] = []
        for payload in payloads:
            record = map_ticker_payload(
                payload,
                provider_id=self.provider_id,
                as_of_date=query.as_of_date,
                ingested_at=self._utc_now(),
            )
            if record is None:
                continue
            if requested_ids is not None and record.instrument_id not in requested_ids:
                continue
            if query.active_only and record.status is not InstrumentStatus.ACTIVE:
                continue
            records.append(record)
        self._validate_unique_instruments(records)
        return tuple(sorted(records, key=lambda record: str(record.instrument_id)))

    def get_eod_bars(self, query: EodBarQuery) -> tuple[EodPriceBarV1, ...]:
        self._require_capability(ProviderCapability.EOD_PRICE_BARS)
        if self._eod_bar_strategy == "custom_bars":
            records = self._get_custom_eod_bars(query)
        else:
            records = self._get_grouped_daily_bars(query)
        if query.revision_selection is RevisionSelection.LATEST:
            records = [record for record in records if record.is_latest_revision]
        return tuple(
            sorted(
                records,
                key=lambda record: (str(record.instrument_id), record.session_date, record.source, record.revision),
            )
        )

    def _require_capability(self, capability: ProviderCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapabilityError(self.provider_id, capability)

    def _get_grouped_daily_bars(self, query: EodBarQuery) -> list[EodPriceBarV1]:
        ticker_to_instrument = self._ticker_to_instrument_id(query.instrument_ids)
        records: list[EodPriceBarV1] = []
        for session_date in _date_range(query.start_date, query.end_date):
            response = self._request_json(
                f"/v2/aggs/grouped/locale/us/market/stocks/{session_date.isoformat()}",
                {"adjusted": False},
            )
            request_id = _optional_string(response.get("request_id"))
            for payload in _results(response, self.provider_id):
                ticker = _payload_ticker(payload)
                instrument_id = ticker_to_instrument.get(ticker)
                if instrument_id is None:
                    continue
                records.append(
                    map_grouped_daily_bar_payload(
                        payload,
                        provider_id=self.provider_id,
                        instrument_id=instrument_id,
                        session_date=session_date,
                        ingested_at=self._utc_now(),
                        request_id=request_id,
                    )
                )
        return records

    def _get_custom_eod_bars(self, query: EodBarQuery) -> list[EodPriceBarV1]:
        records: list[EodPriceBarV1] = []
        for instrument_id in query.instrument_ids:
            ticker = self._resolve_ticker(instrument_id)
            payloads = self._fetch_pages(
                f"/v2/aggs/ticker/{ticker}/range/1/day/{query.start_date.isoformat()}/{query.end_date.isoformat()}",
                {"adjusted": False, "sort": "asc", "limit": 50000},
            )
            for payload in payloads:
                session_date = _session_date_from_payload(payload)
                if query.start_date <= session_date <= query.end_date:
                    records.append(
                        map_custom_bar_payload(
                            payload,
                            provider_id=self.provider_id,
                            instrument_id=instrument_id,
                            session_date=session_date,
                            ingested_at=self._utc_now(),
                            request_id=None,
                        )
                    )
        return records

    def _fetch_pages(self, path: str, params: MassiveParams) -> tuple[Mapping[str, object], ...]:
        results: list[Mapping[str, object]] = []
        current_path = path
        current_params = dict(params)
        seen_pages: set[tuple[str, tuple[tuple[str, MassiveParamValue], ...]]] = set()
        for _ in range(self._max_pages):
            page_key = (current_path, tuple(sorted(current_params.items())))
            if page_key in seen_pages:
                raise ProviderDataError(self.provider_id, "Massive pagination loop detected")
            seen_pages.add(page_key)
            response = self._request_json(current_path, current_params)
            results.extend(_results(response, self.provider_id))
            next_url = response.get("next_url")
            if next_url is None:
                return tuple(results)
            current_path, current_params = self._next_page_request(next_url)
        raise ProviderDataError(self.provider_id, "Massive pagination exceeded page limit")

    def _request_json(self, path: str, params: MassiveParams) -> Mapping[str, object]:
        if any(key.lower() == "apikey" for key in params):
            raise ProviderDataError(self.provider_id, "Massive API key must not be sent as a query parameter")
        try:
            return self._transport.get_json(
                path,
                params=params,
                api_key=self._config.api_key,
                timeout_seconds=self._config.request_timeout_seconds,
                base_url=self._config.base_url,
            )
        except MassiveTransportResponseError as exc:
            if exc.status_code in {401, 403}:
                raise ProviderAuthenticationError(self.provider_id, "Massive authentication failed") from exc
            if exc.status_code == 429:
                raise ProviderRateLimitError(
                    self.provider_id,
                    "Massive rate limit exceeded",
                    retry_after_seconds=exc.retry_after_seconds,
                ) from exc
            raise ProviderUnavailableError(self.provider_id, "Massive HTTP request failed") from exc
        except MassiveTransportTimeoutError as exc:
            raise ProviderUnavailableError(self.provider_id, "Massive request timed out") from exc
        except MassiveTransportUnavailableError as exc:
            raise ProviderUnavailableError(self.provider_id, "Massive transport unavailable") from exc
        except MassiveTransportDataError as exc:
            raise ProviderDataError(self.provider_id, "Massive response payload was invalid") from exc

    def _next_page_request(self, next_url: object) -> tuple[str, dict[str, MassiveParamValue]]:
        if not isinstance(next_url, str) or not next_url.strip():
            raise ProviderDataError(self.provider_id, "Massive next_url is invalid")
        parsed = urlparse(next_url)
        if not parsed.path:
            raise ProviderDataError(self.provider_id, "Massive next_url has no path")
        base = urlparse(self._config.base_url)
        if parsed.netloc and parsed.netloc != base.netloc:
            raise ProviderDataError(self.provider_id, "Massive next_url host does not match configured base URL")
        params: dict[str, MassiveParamValue] = {}
        for key, value in parse_qsl(parsed.query, keep_blank_values=False):
            if key.lower() == "apikey":
                continue
            params[key] = value
        return parsed.path, params

    def _ticker_to_instrument_id(self, instrument_ids: Iterable[UUID]) -> dict[str, UUID]:
        return {self._resolve_ticker(instrument_id): instrument_id for instrument_id in instrument_ids}

    def _resolve_ticker(self, instrument_id: UUID) -> str:
        ticker = self._instrument_tickers.get(instrument_id)
        if ticker is None:
            raise ProviderDataError(self.provider_id, "Massive adapter cannot resolve instrument_id to ticker")
        normalized = ticker.strip().upper()
        if not normalized:
            raise ProviderDataError(self.provider_id, "Massive adapter resolved an empty ticker")
        return normalized

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProviderDataError(self.provider_id, "Massive adapter clock returned naive datetime")
        return value.astimezone(UTC)

    def _validate_unique_instruments(self, records: list[InstrumentMasterV1]) -> None:
        seen: set[UUID] = set()
        for record in records:
            if record.instrument_id in seen:
                raise ProviderDataError(self.provider_id, "Massive mapping produced duplicate instrument_id")
            seen.add(record.instrument_id)


def _results(response: Mapping[str, object], provider_id: str) -> tuple[Mapping[str, object], ...]:
    results = response.get("results", ())
    if not isinstance(results, list):
        raise ProviderDataError(provider_id, "Massive response results must be a list")
    normalized: list[Mapping[str, object]] = []
    for item in results:
        if not isinstance(item, Mapping):
            raise ProviderDataError(provider_id, "Massive response result item must be an object")
        normalized.append(item)
    return tuple(normalized)


def _payload_ticker(payload: Mapping[str, object]) -> str:
    ticker = payload.get("T") or payload.get("ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ProviderDataError(MASSIVE_PROVIDER_ID, "Massive aggregate payload missing ticker")
    return ticker.strip().upper()


def _session_date_from_payload(payload: Mapping[str, object]) -> date:
    timestamp = payload.get("t")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise ProviderDataError(MASSIVE_PROVIDER_ID, "Massive aggregate payload missing timestamp")
    return datetime.fromtimestamp(timestamp / 1000, tz=UTC).date()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
