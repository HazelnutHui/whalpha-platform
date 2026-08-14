"""Deterministic in-memory market-data provider for contract tests only."""

from __future__ import annotations

from collections import defaultdict

from tip_api.contracts.market_data.v1 import EodPriceBarV1, InstrumentMasterV1, InstrumentStatus
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    MarketDataProvider,
    ProviderCapability,
    ProviderDataError,
    RevisionSelection,
    UnsupportedCapabilityError,
)


class InMemoryMarketDataProvider:
    """In-memory implementation used only for deterministic boundary tests."""

    def __init__(
        self,
        provider_id: str,
        capabilities: frozenset[ProviderCapability],
        instruments: tuple[InstrumentMasterV1, ...] = (),
        eod_bars: tuple[EodPriceBarV1, ...] = (),
    ) -> None:
        normalized_provider_id = provider_id.strip()
        if not normalized_provider_id:
            raise ValueError("provider_id must not be empty")
        self._provider_id = normalized_provider_id
        self._capabilities = frozenset(capabilities)
        self._instruments = tuple(instruments)
        self._eod_bars = tuple(eod_bars)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def capabilities(self) -> frozenset[ProviderCapability]:
        return self._capabilities

    def get_instruments(self, query: InstrumentQuery) -> tuple[InstrumentMasterV1, ...]:
        self._require_capability(ProviderCapability.INSTRUMENT_MASTER)
        allowed_ids = set(query.instrument_ids) if query.instrument_ids is not None else None
        effective_records = tuple(
            record
            for record in self._instruments
            if (allowed_ids is None or record.instrument_id in allowed_ids)
            and record.valid_from <= query.as_of_date
            and (record.valid_to is None or query.as_of_date <= record.valid_to)
        )
        records_by_instrument: dict[object, list[InstrumentMasterV1]] = defaultdict(list)
        for record in effective_records:
            records_by_instrument[record.instrument_id].append(record)
        for instrument_id, records in records_by_instrument.items():
            if len(records) > 1:
                raise ProviderDataError(
                    self.provider_id,
                    f"multiple effective Instrument Master records for instrument_id={instrument_id}",
                )
        if query.active_only:
            effective_records = tuple(
                record for record in effective_records if record.status is InstrumentStatus.ACTIVE
            )
        return tuple(sorted(effective_records, key=lambda record: str(record.instrument_id)))

    def get_eod_bars(self, query: EodBarQuery) -> tuple[EodPriceBarV1, ...]:
        self._require_capability(ProviderCapability.EOD_PRICE_BARS)
        allowed_ids = set(query.instrument_ids)
        matching_records = tuple(
            record
            for record in self._eod_bars
            if record.instrument_id in allowed_ids
            and query.start_date <= record.session_date <= query.end_date
        )
        self._validate_eod_business_keys(matching_records)
        self._validate_eod_latest_state(matching_records, require_latest=query.revision_selection is RevisionSelection.LATEST)
        if query.revision_selection is RevisionSelection.LATEST:
            matching_records = tuple(record for record in matching_records if record.is_latest_revision)
        return tuple(
            sorted(
                matching_records,
                key=lambda record: (
                    str(record.instrument_id),
                    record.session_date,
                    record.source,
                    record.revision,
                ),
            )
        )

    def _require_capability(self, capability: ProviderCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapabilityError(self.provider_id, capability)

    def _validate_eod_business_keys(self, records: tuple[EodPriceBarV1, ...]) -> None:
        seen: set[tuple[object, object, str, int]] = set()
        for record in records:
            key = (record.instrument_id, record.session_date, record.source, record.revision)
            if key in seen:
                raise ProviderDataError(self.provider_id, "duplicate EOD Price Bar business key")
            seen.add(key)

    def _validate_eod_latest_state(
        self,
        records: tuple[EodPriceBarV1, ...],
        *,
        require_latest: bool,
    ) -> None:
        grouped: dict[tuple[object, object, str], list[EodPriceBarV1]] = defaultdict(list)
        for record in records:
            grouped[(record.instrument_id, record.session_date, record.source)].append(record)
        for group_records in grouped.values():
            latest_records = [record for record in group_records if record.is_latest_revision]
            if len(latest_records) > 1:
                raise ProviderDataError(self.provider_id, "multiple latest EOD revisions in one logical group")
            if require_latest and not latest_records:
                raise ProviderDataError(self.provider_id, "missing latest EOD revision in one logical group")
