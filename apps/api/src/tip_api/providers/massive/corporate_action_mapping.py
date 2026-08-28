"""Network-free Massive split and dividend response mapping."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Iterable, Mapping, TypeAlias
from uuid import UUID

from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    KnowledgeTimeStatus,
    ResolutionStatus,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.numeric import (
    InvalidMassiveNumericValue,
    MissingMassiveNumericValue,
    parse_massive_decimal,
    parse_massive_integral,
)

TickerResolution: TypeAlias = UUID | tuple[UUID, ...]


class MassiveCorporateActionPayloadKind(StrEnum):
    SPLIT = "split"
    DIVIDEND = "dividend"


@dataclass(frozen=True)
class MassiveCorporateActionMappingIssue:
    payload_kind: MassiveCorporateActionPayloadKind
    source_index: int
    reason_code: str
    provider_ticker: str | None
    source_action_id: str | None
    payload_fingerprint: str


@dataclass(frozen=True)
class MassiveCorporateActionMappingBatch:
    records: tuple[CorporateActionSourceObservationV1, ...]
    issues: tuple[MassiveCorporateActionMappingIssue, ...]
    input_count: int
    accepted_record_count: int
    quarantined_record_count: int
    quarantined_without_record_count: int


class _PayloadCannotBeRepresented(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def map_massive_corporate_action_payloads(
    *,
    split_payloads: Iterable[Mapping[str, object]],
    dividend_payloads: Iterable[Mapping[str, object]],
    ticker_resolutions: Mapping[str, TickerResolution],
    first_observed_at: datetime,
    ingested_at: datetime,
    source_revision: int = 1,
) -> MassiveCorporateActionMappingBatch:
    """Map already-loaded synthetic/provider-shaped rows without transport access."""

    first_observed_at = normalize_utc_datetime(first_observed_at)
    ingested_at = normalize_utc_datetime(ingested_at)
    if ingested_at < first_observed_at:
        raise ValueError("ingested_at must not precede first_observed_at")
    if source_revision < 1:
        raise ValueError("source_revision must be positive")
    resolutions = _normalize_resolutions(ticker_resolutions)
    records: list[CorporateActionSourceObservationV1] = []
    issues: list[MassiveCorporateActionMappingIssue] = []
    input_count = 0

    for kind, payloads in (
        (MassiveCorporateActionPayloadKind.SPLIT, split_payloads),
        (MassiveCorporateActionPayloadKind.DIVIDEND, dividend_payloads),
    ):
        for source_index, payload in enumerate(payloads):
            input_count += 1
            if not isinstance(payload, Mapping):
                issues.append(
                    MassiveCorporateActionMappingIssue(
                        payload_kind=kind,
                        source_index=source_index,
                        reason_code="payload_not_object",
                        provider_ticker=None,
                        source_action_id=None,
                        payload_fingerprint=_payload_fingerprint(kind, {}),
                    )
                )
                continue
            try:
                record = (
                    _map_split(
                        payload,
                        resolutions=resolutions,
                        first_observed_at=first_observed_at,
                        ingested_at=ingested_at,
                        source_revision=source_revision,
                    )
                    if kind is MassiveCorporateActionPayloadKind.SPLIT
                    else _map_dividend(
                        payload,
                        resolutions=resolutions,
                        first_observed_at=first_observed_at,
                        ingested_at=ingested_at,
                        source_revision=source_revision,
                    )
                )
            except _PayloadCannotBeRepresented as exc:
                issues.append(
                    MassiveCorporateActionMappingIssue(
                        payload_kind=kind,
                        source_index=source_index,
                        reason_code=exc.reason_code,
                        provider_ticker=_safe_issue_ticker(payload.get("ticker")),
                        source_action_id=_safe_provider_action_id(payload.get("id")),
                        payload_fingerprint=_payload_fingerprint(kind, payload),
                    )
                )
                continue
            records.append(record)

    ordered = tuple(
        sorted(
            records,
            key=lambda record: (
                record.provider,
                record.source_action_id,
                record.source_revision,
            ),
        )
    )
    quarantined_records = sum(
        record.record_status is CorporateActionRecordStatus.QUARANTINED
        for record in ordered
    )
    return MassiveCorporateActionMappingBatch(
        records=ordered,
        issues=tuple(issues),
        input_count=input_count,
        accepted_record_count=len(ordered) - quarantined_records,
        quarantined_record_count=quarantined_records,
        quarantined_without_record_count=len(issues),
    )


def _map_split(
    payload: Mapping[str, object],
    *,
    resolutions: Mapping[str, tuple[UUID, ...]],
    first_observed_at: datetime,
    ingested_at: datetime,
    source_revision: int,
) -> CorporateActionSourceObservationV1:
    ticker = _required_ticker(payload)
    effective_date = _required_date(payload.get("execution_date"), "missing_or_invalid_execution_date")
    adjustment_type = _safe_optional_text(payload.get("adjustment_type"))
    action_type = {
        "forward_split": CorporateActionType.STOCK_SPLIT,
        "reverse_split": CorporateActionType.REVERSE_SPLIT,
        "stock_dividend": CorporateActionType.STOCK_DIVIDEND,
    }.get((adjustment_type or "").lower())
    if action_type is None:
        raise _PayloadCannotBeRepresented("missing_or_unsupported_adjustment_type")
    flags = ["source_available_time_unavailable"]
    split_from = _optional_positive_decimal(payload.get("split_from"), "split_from", flags)
    split_to = _optional_positive_decimal(payload.get("split_to"), "split_to", flags)
    if split_from is None:
        flags.append("missing_split_from")
    if split_to is None:
        flags.append("missing_split_to")
    if split_from is not None and split_to is not None:
        direction_valid = {
            CorporateActionType.STOCK_SPLIT: split_to > split_from,
            CorporateActionType.REVERSE_SPLIT: split_from > split_to,
            CorporateActionType.STOCK_DIVIDEND: split_to > split_from,
        }[action_type]
        if not direction_valid:
            flags.append("split_direction_conflict")
    historical_factor = _optional_positive_decimal(
        payload.get("historical_adjustment_factor"),
        "historical_adjustment_factor",
        flags,
    )
    source_action_id, synthetic_id = _source_action_id(
        MassiveCorporateActionPayloadKind.SPLIT,
        payload,
        ticker=ticker,
        effective_date=effective_date,
    )
    if synthetic_id:
        flags.append("provider_action_id_missing")
    resolution_status, instrument_id, resolution_flags = _resolve_ticker(
        ticker,
        resolutions,
    )
    flags.extend(resolution_flags)
    return _build_record(
        source_action_id=source_action_id,
        source_revision=source_revision,
        action_type=action_type,
        provider_ticker=ticker,
        instrument_resolution_status=resolution_status,
        instrument_id=instrument_id,
        effective_date=effective_date,
        split_ratio_from=split_from,
        split_ratio_to=split_to,
        provider_historical_adjustment_factor=historical_factor,
        first_observed_at=first_observed_at,
        ingested_at=ingested_at,
        flags=flags,
    )


def _map_dividend(
    payload: Mapping[str, object],
    *,
    resolutions: Mapping[str, tuple[UUID, ...]],
    first_observed_at: datetime,
    ingested_at: datetime,
    source_revision: int,
) -> CorporateActionSourceObservationV1:
    ticker = _required_ticker(payload)
    ex_date = _required_date(payload.get("ex_dividend_date"), "missing_or_invalid_ex_dividend_date")
    flags = ["source_available_time_unavailable"]
    cash_amount = _optional_positive_decimal(payload.get("cash_amount"), "cash_amount", flags)
    if cash_amount is None:
        flags.append("missing_cash_amount")
    currency = _currency(payload.get("currency"), flags)
    if currency is None and "invalid_currency" not in flags:
        flags.append("missing_currency")
    announcement_date = _optional_date(payload.get("declaration_date"), "declaration_date", flags)
    record_date = _optional_date(payload.get("record_date"), "record_date", flags)
    pay_date = _optional_date(payload.get("pay_date"), "pay_date", flags)
    historical_factor = _optional_positive_decimal(
        payload.get("historical_adjustment_factor"),
        "historical_adjustment_factor",
        flags,
    )
    split_adjusted_cash = _optional_positive_decimal(
        payload.get("split_adjusted_cash_amount"),
        "split_adjusted_cash_amount",
        flags,
    )
    distribution_type = _distribution_type(payload.get("distribution_type"), flags)
    frequency = _optional_non_negative_integer(payload.get("frequency"), "frequency", flags)
    source_action_id, synthetic_id = _source_action_id(
        MassiveCorporateActionPayloadKind.DIVIDEND,
        payload,
        ticker=ticker,
        effective_date=ex_date,
    )
    if synthetic_id:
        flags.append("provider_action_id_missing")
    resolution_status, instrument_id, resolution_flags = _resolve_ticker(
        ticker,
        resolutions,
    )
    flags.extend(resolution_flags)
    return _build_record(
        source_action_id=source_action_id,
        source_revision=source_revision,
        action_type=CorporateActionType.CASH_DIVIDEND,
        provider_ticker=ticker,
        instrument_resolution_status=resolution_status,
        instrument_id=instrument_id,
        announcement_date=announcement_date,
        ex_date=ex_date,
        record_date=record_date,
        pay_date=pay_date,
        effective_date=ex_date,
        cash_amount=cash_amount,
        currency=currency,
        provider_historical_adjustment_factor=historical_factor,
        provider_split_adjusted_cash_amount=split_adjusted_cash,
        distribution_type=distribution_type,
        frequency=frequency,
        first_observed_at=first_observed_at,
        ingested_at=ingested_at,
        flags=flags,
    )


def _build_record(
    *,
    flags: list[str],
    **values: object,
) -> CorporateActionSourceObservationV1:
    material_flags = set(flags) - {"source_available_time_unavailable"}
    quarantined = bool(material_flags)
    try:
        return CorporateActionSourceObservationV1(
            provider=MASSIVE_PROVIDER_ID,
            record_status=(
                CorporateActionRecordStatus.QUARANTINED
                if quarantined
                else CorporateActionRecordStatus.ACTIVE
            ),
            knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
            source_available_at=None,
            quality_status=(
                QualityStatus.PENDING_REVIEW if quarantined else QualityStatus.VALID
            ),
            quality_flags=tuple(flags),
            **values,
        )
    except ValidationError as exc:
        raise _PayloadCannotBeRepresented("canonical_contract_validation_failed") from exc


def _normalize_resolutions(
    values: Mapping[str, TickerResolution],
) -> dict[str, tuple[UUID, ...]]:
    normalized: dict[str, tuple[UUID, ...]] = {}
    for raw_ticker, raw_resolution in values.items():
        ticker = _normalize_ticker(raw_ticker)
        candidates = (
            (raw_resolution,)
            if isinstance(raw_resolution, UUID)
            else tuple(raw_resolution)
        )
        if any(not isinstance(candidate, UUID) for candidate in candidates):
            raise ValueError("ticker resolution candidates must be UUID values")
        candidates = tuple(sorted(set(candidates), key=str))
        if ticker in normalized and normalized[ticker] != candidates:
            raise ValueError("ticker resolution has a normalized-key conflict")
        normalized[ticker] = candidates
    return normalized


def _resolve_ticker(
    ticker: str,
    resolutions: Mapping[str, tuple[UUID, ...]],
) -> tuple[ResolutionStatus, UUID | None, tuple[str, ...]]:
    candidates = resolutions.get(ticker, ())
    if len(candidates) == 1:
        return ResolutionStatus.RESOLVED, candidates[0], ()
    if len(candidates) > 1:
        return ResolutionStatus.AMBIGUOUS, None, ("ambiguous_ticker_resolution",)
    return ResolutionStatus.UNRESOLVED, None, ("unresolved_ticker",)


def _required_ticker(payload: Mapping[str, object]) -> str:
    value = _safe_optional_text(payload.get("ticker"), uppercase=True)
    if value is None:
        raise _PayloadCannotBeRepresented("missing_or_invalid_ticker")
    try:
        return _normalize_ticker(value)
    except ValueError as exc:
        raise _PayloadCannotBeRepresented("missing_or_invalid_ticker") from exc


def _normalize_ticker(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("ticker must be text")
    normalized = value.strip().upper()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if not normalized or any(character not in allowed for character in normalized):
        raise ValueError("ticker is invalid")
    return normalized


def _source_action_id(
    kind: MassiveCorporateActionPayloadKind,
    payload: Mapping[str, object],
    *,
    ticker: str,
    effective_date: date,
) -> tuple[str, bool]:
    source_id = _safe_provider_action_id(payload.get("id"))
    if source_id is not None:
        return source_id, False
    fingerprint = _payload_fingerprint(kind, payload)
    return f"synthetic-{ticker}-{effective_date.isoformat()}-{fingerprint}", True


def _required_date(value: object, reason_code: str) -> date:
    parsed = _parse_date(value)
    if parsed is None:
        raise _PayloadCannotBeRepresented(reason_code)
    return parsed


def _optional_date(value: object, field_name: str, flags: list[str]) -> date | None:
    if value is None:
        return None
    parsed = _parse_date(value)
    if parsed is None:
        flags.append(f"invalid_{field_name}")
    return parsed


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _optional_positive_decimal(
    value: object,
    field_name: str,
    flags: list[str],
) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = parse_massive_decimal(value, required=False)
    except (MissingMassiveNumericValue, InvalidMassiveNumericValue):
        flags.append(f"invalid_{field_name}")
        return None
    if parsed is None or parsed <= 0:
        flags.append(f"invalid_{field_name}")
        return None
    return parsed


def _optional_non_negative_integer(
    value: object,
    field_name: str,
    flags: list[str],
) -> int | None:
    if value is None:
        return None
    try:
        return parse_massive_integral(value, required=False, allow_negative=False)
    except (MissingMassiveNumericValue, InvalidMassiveNumericValue):
        flags.append(f"invalid_{field_name}")
        return None


def _safe_optional_text(value: object, *, uppercase: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized.upper() if uppercase else normalized


def _safe_provider_action_id(value: object) -> str | None:
    normalized = _safe_optional_text(value)
    if normalized is None or len(normalized) > 256:
        return None
    allowed = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:"
    )
    if any(character not in allowed for character in normalized):
        return None
    return normalized


def _safe_issue_ticker(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return _normalize_ticker(value)
    except ValueError:
        return None


def _currency(value: object, flags: list[str]) -> str | None:
    normalized = _safe_optional_text(value, uppercase=True)
    if normalized is None:
        return None
    if len(normalized) != 3 or not normalized.isalpha():
        flags.append("invalid_currency")
        return None
    return normalized


def _distribution_type(value: object, flags: list[str]) -> str | None:
    normalized = _safe_optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if normalized not in {
        "recurring",
        "special",
        "supplemental",
        "irregular",
        "unknown",
    }:
        flags.append("invalid_distribution_type")
        return None
    return normalized


_FINGERPRINT_FIELDS = {
    MassiveCorporateActionPayloadKind.SPLIT: (
        "adjustment_type",
        "execution_date",
        "historical_adjustment_factor",
        "id",
        "split_from",
        "split_to",
        "ticker",
    ),
    MassiveCorporateActionPayloadKind.DIVIDEND: (
        "cash_amount",
        "currency",
        "declaration_date",
        "distribution_type",
        "ex_dividend_date",
        "frequency",
        "historical_adjustment_factor",
        "id",
        "pay_date",
        "record_date",
        "split_adjusted_cash_amount",
        "ticker",
    ),
}


def _payload_fingerprint(
    kind: MassiveCorporateActionPayloadKind,
    payload: Mapping[str, object],
) -> str:
    safe_shape = {
        field_name: _json_safe(payload.get(field_name))
        for field_name in _FINGERPRINT_FIELDS[kind]
        if field_name in payload
    }
    rendered = json.dumps(
        safe_shape,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (float, Decimal)):
        return str(value)
    return type(value).__name__
