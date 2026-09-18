"""Exact-plan Massive Starter read-only capability sample."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Callable, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_massive_starter_capability_sample import (
    CapabilityRequestOutcomeV1,
    CapabilitySampleCaseV1,
    CapabilitySampleRequestV1,
    HistoricalLane,
    HistoricalLaneDispositionV1,
    MassiveStarterCapabilitySamplePlanV1,
    MassiveStarterCapabilitySampleResultV1,
    ProbeStatus,
    RequestKind,
    SampleKind,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import census_fingerprint
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)


Clock = Callable[[], datetime]
BeforeRequest = Callable[[int], None]


@dataclass(frozen=True)
class CapabilitySampleExecution:
    result: MassiveStarterCapabilitySampleResultV1
    sanitized_responses: Mapping[int, Mapping[str, object]]


def registered_massive_starter_capability_sample_plan_v1(
) -> MassiveStarterCapabilitySamplePlanV1:
    samples = (
        CapabilitySampleCaseV1(
            kind=SampleKind.SINGLE_COMMON,
            instrument_id=UUID("0009f17a-9e07-50b4-80b0-c99dde042549"),
            cik="0001831097",
            observed_tickers=("AGL",),
            current_provider_ticker="AGL",
            composite_figi="BBG00HCYVQQ4",
            share_class_figi="BBG00HCYVQR3",
            representative_session="2023-03-02",
        ),
        CapabilitySampleCaseV1(
            kind=SampleKind.TICKER_CHANGE,
            instrument_id=UUID("013f4751-d9cf-5e20-9ad2-a33b4e8f4f19"),
            cik="0001042893",
            observed_tickers=("DRQ", "INVX"),
            current_provider_ticker="INVX",
            composite_figi="BBG000BVDBY2",
            share_class_figi="BBG001SB9LK4",
            representative_session="2024-09-06",
        ),
        CapabilitySampleCaseV1(
            kind=SampleKind.MULTI_COMMON,
            instrument_id=UUID("053b0fba-1c72-5171-b97f-5c4596010895"),
            cik="0000912615",
            observed_tickers=("URBN",),
            current_provider_ticker="URBN",
            composite_figi="BBG000BL79J3",
            share_class_figi="BBG001S7H9K1",
            representative_session="2022-12-13",
            multi_common_group=(
                UUID("053b0fba-1c72-5171-b97f-5c4596010895"),
                UUID("1fa2428f-2f8a-5b64-96ca-c4587c9642e9"),
            ),
        ),
    )
    lines = (
        _request(1, SampleKind.SINGLE_COMMON, RequestKind.CURRENT_TICKER_DETAILS, "/v3/reference/tickers/AGL"),
        _request(2, SampleKind.TICKER_CHANGE, RequestKind.CURRENT_TICKER_DETAILS, "/v3/reference/tickers/INVX"),
        _request(3, SampleKind.MULTI_COMMON, RequestKind.CURRENT_TICKER_DETAILS, "/v3/reference/tickers/URBN"),
        _historical_request(4, SampleKind.SINGLE_COMMON, "AGL", "2023-03-02"),
        _historical_request(5, SampleKind.TICKER_CHANGE, "DRQ", "2024-09-06"),
        _historical_request(6, SampleKind.TICKER_CHANGE, "INVX", "2024-09-09"),
        _historical_request(7, SampleKind.MULTI_COMMON, "URBN", "2022-12-13"),
        _request(8, SampleKind.SINGLE_COMMON, RequestKind.TICKER_EVENTS, "/vX/reference/tickers/BBG00HCYVQQ4/events"),
        _request(9, SampleKind.TICKER_CHANGE, RequestKind.TICKER_EVENTS, "/vX/reference/tickers/BBG000BVDBY2/events"),
        _request(10, SampleKind.MULTI_COMMON, RequestKind.TICKER_EVENTS, "/vX/reference/tickers/BBG000BL79J3/events"),
    )
    values = {"samples": samples, "requests": lines}
    provisional = MassiveStarterCapabilitySamplePlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return MassiveStarterCapabilitySamplePlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def execute_massive_starter_capability_sample(
    *,
    plan: MassiveStarterCapabilitySamplePlanV1,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    clock: Clock | None = None,
    before_request: BeforeRequest | None = None,
) -> CapabilitySampleExecution:
    now = clock or (lambda: datetime.now(UTC))
    secret = config.api_key.get_secret_value()
    responses: dict[int, Mapping[str, object]] = {}
    outcomes: list[CapabilityRequestOutcomeV1] = []
    status = ProbeStatus.COMPLETED
    failed_sequence: int | None = None
    request_count = 0
    for line in plan.requests:
        if before_request is not None:
            before_request(line.sequence)
        request_count += 1
        try:
            raw = transport.get_json(
                line.path,
                params=dict(line.params),
                api_key=config.api_key,
                timeout_seconds=config.request_timeout_seconds,
                base_url=config.base_url,
            )
            sanitized = _sanitize_response(raw, secret=secret)
            encoded = _canonical_bytes(sanitized)
            if len(encoded) > line.response_body_limit_bytes:
                raise MassiveTransportDataError("capability sample response exceeded byte limit")
            captured = now()
            if captured.tzinfo is None or captured.utcoffset() is None:
                raise MassiveTransportDataError("capability sample clock was naive")
            responses[line.sequence] = sanitized
            outcomes.append(
                CapabilityRequestOutcomeV1(
                    sequence=line.sequence,
                    status="accessible",
                    captured_at_utc=captured.astimezone(UTC),
                    sanitized_response_sha256=hashlib.sha256(encoded).hexdigest(),
                    sanitized_response_byte_size=len(encoded),
                    schema_paths=_schema_paths(sanitized),
                    result_count=_result_count(sanitized),
                )
            )
        except MassiveTransportResponseError as exc:
            failed_sequence = line.sequence
            if exc.status_code == 401:
                status = ProbeStatus.STOPPED_AUTHENTICATION
            elif exc.status_code == 403:
                status = ProbeStatus.STOPPED_ENTITLEMENT
            elif exc.status_code == 429:
                status = ProbeStatus.STOPPED_RATE_LIMIT
            else:
                status = ProbeStatus.STOPPED_UNAVAILABLE
            break
        except (MassiveTransportTimeoutError, MassiveTransportUnavailableError):
            failed_sequence = line.sequence
            status = ProbeStatus.STOPPED_UNAVAILABLE
            break
        except MassiveTransportDataError:
            failed_sequence = line.sequence
            status = ProbeStatus.STOPPED_MALFORMED
            break
    result = evaluate_massive_starter_capability_sample(
        plan=plan,
        request_outcomes=tuple(outcomes),
        sanitized_responses=responses,
        status=status,
        failed_request_sequence=failed_sequence,
        request_count=request_count,
    )
    return CapabilitySampleExecution(result=result, sanitized_responses=responses)


def evaluate_massive_starter_capability_sample(
    *,
    plan: MassiveStarterCapabilitySamplePlanV1,
    request_outcomes: tuple[CapabilityRequestOutcomeV1, ...],
    sanitized_responses: Mapping[int, Mapping[str, object]],
    status: ProbeStatus,
    failed_request_sequence: int | None,
    request_count: int,
) -> MassiveStarterCapabilitySampleResultV1:
    """Evaluate retained sanitized responses without another provider request."""

    dispositions = _evaluate_lanes(
        plan=plan,
        responses=sanitized_responses,
        completed=status is ProbeStatus.COMPLETED,
    )
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "status": status,
        "request_count": request_count,
        "failed_request_sequence": failed_request_sequence,
        "request_outcomes": request_outcomes,
        "lane_dispositions": dispositions,
    }
    provisional = MassiveStarterCapabilitySampleResultV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return MassiveStarterCapabilitySampleResultV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def _request(sequence: int, sample: SampleKind, kind: RequestKind, path: str) -> CapabilitySampleRequestV1:
    return CapabilitySampleRequestV1(sequence=sequence, sample_kind=sample, request_kind=kind, path=path)


def _historical_request(sequence: int, sample: SampleKind, ticker: str, session: str) -> CapabilitySampleRequestV1:
    return CapabilitySampleRequestV1(
        sequence=sequence,
        sample_kind=sample,
        request_kind=RequestKind.HISTORICAL_TICKER_REFERENCE,
        path="/v3/reference/tickers",
        params=(("date", session), ("limit", "10"), ("ticker", ticker)),
    )


def _evaluate_lanes(
    *, plan: MassiveStarterCapabilitySamplePlanV1,
    responses: Mapping[int, Mapping[str, object]],
    completed: bool,
) -> tuple[HistoricalLaneDispositionV1, ...]:
    historical = [line for line in plan.requests if line.request_kind is RequestKind.HISTORICAL_TICKER_REFERENCE]
    identity_rows_ok = completed and all(_historical_line_matches(line, plan, responses.get(line.sequence)) for line in historical)
    form_rows_ok = completed and all(
        _historical_line_has_form(responses.get(line.sequence)) for line in historical
    )
    event = responses.get(9)
    ticker_change_lines = [
        line for line in historical if line.sample_kind is SampleKind.TICKER_CHANGE
    ]
    alias_ok = (
        completed
        and all(
            _historical_line_matches_stable_id(
                line, plan, responses.get(line.sequence)
            )
            for line in ticker_change_lines
        )
        and _has_ticker_change_event(event)
    )
    return (
        HistoricalLaneDispositionV1(
            lane=HistoricalLane.INSTRUMENT_CIK,
            disposition="corroboration_only" if identity_rows_ok else "blocked",
            reason_codes=tuple(sorted((
                "retrospective_provider_representation_only" if identity_rows_ok else "sample_identity_fields_incomplete_or_unavailable",
                "source_not_known_by_historical_signal_open",
            ))),
        ),
        HistoricalLaneDispositionV1(
            lane=HistoricalLane.SECURITY_FORM,
            disposition="corroboration_only" if form_rows_ok else "blocked",
            reason_codes=tuple(sorted((
                "provider_type_is_not_revision_aware_historical_ledger" if form_rows_ok else "sample_security_form_incomplete_or_unavailable",
                "source_not_known_by_historical_signal_open",
            ))),
        ),
        HistoricalLaneDispositionV1(
            lane=HistoricalLane.LISTING_ALIASES,
            disposition="corroboration_only" if alias_ok else "blocked",
            reason_codes=tuple(sorted((
                "ticker_event_is_not_complete_listing_interval" if alias_ok else "ticker_change_event_incomplete_or_unavailable",
                "source_availability_and_revision_history_missing",
            ))),
        ),
        HistoricalLaneDispositionV1(
            lane=HistoricalLane.ISSUER_STRUCTURE,
            disposition="blocked",
            reason_codes=("provider_reference_not_issuer_structure_evidence",),
        ),
    )


def _historical_line_matches(
    line: CapabilitySampleRequestV1,
    plan: MassiveStarterCapabilitySamplePlanV1,
    response: Mapping[str, object] | None,
) -> bool:
    if response is None or not isinstance(response.get("results"), list):
        return False
    sample = next(item for item in plan.samples if item.kind is line.sample_kind)
    expected_ticker = dict(line.params)["ticker"]
    for row in response["results"]:
        if not isinstance(row, Mapping):
            continue
        if (
            _upper(row.get("ticker")) == expected_ticker
            and _digits(row.get("cik")) == sample.cik
            and _upper(row.get("composite_figi")) == sample.composite_figi
            and _upper(row.get("share_class_figi")) == sample.share_class_figi
        ):
            return True
    return False


def _historical_line_has_form(response: Mapping[str, object] | None) -> bool:
    if response is None or not isinstance(response.get("results"), list):
        return False
    return any(isinstance(row, Mapping) and bool(_upper(row.get("type"))) for row in response["results"])


def _historical_line_matches_stable_id(
    line: CapabilitySampleRequestV1,
    plan: MassiveStarterCapabilitySamplePlanV1,
    response: Mapping[str, object] | None,
) -> bool:
    if response is None or not isinstance(response.get("results"), list):
        return False
    sample = next(item for item in plan.samples if item.kind is line.sample_kind)
    expected_ticker = dict(line.params)["ticker"]
    return any(
        isinstance(row, Mapping)
        and _upper(row.get("ticker")) == expected_ticker
        and _upper(row.get("composite_figi")) == sample.composite_figi
        and _upper(row.get("share_class_figi")) == sample.share_class_figi
        for row in response["results"]
    )


def _has_ticker_change_event(response: Mapping[str, object] | None) -> bool:
    if response is None:
        return False
    results = response.get("results")
    if isinstance(results, Mapping):
        events = results.get("events")
    else:
        events = results
    if not isinstance(events, list):
        return False
    return any(
        isinstance(row, Mapping) and _upper(row.get("type")) == "TICKER_CHANGE"
        for row in events
    )


def _sanitize_response(value: Mapping[str, object], *, secret: str) -> Mapping[str, object]:
    sanitized = _sanitize_value(value, secret=secret, key=None)
    if not isinstance(sanitized, Mapping):
        raise MassiveTransportDataError("sanitized response is not an object")
    return sanitized


def _sanitize_value(value: object, *, secret: str, key: str | None) -> object:
    if key is not None and key.lower() in {"apikey", "api_key", "authorization"}:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): _sanitize_value(v, secret=secret, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item, secret=secret, key=None) for item in value]
    if isinstance(value, str):
        text = _sanitize_url(value) if key == "next_url" else value
        return text.replace(secret, "[REDACTED]") if secret and secret in text else text
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise MassiveTransportDataError("provider response contains unsupported JSON value")


def _sanitize_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.query:
        return value
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in {"apikey", "api_key"}]
    return urlunparse(parsed._replace(query=urlencode(query)))


def _schema_paths(value: object, prefix: str = "$") -> tuple[str, ...]:
    found: set[str] = set()

    def visit(item: object, path: str) -> None:
        found.add(f"{path}:{_json_type(item)}")
        if isinstance(item, Mapping):
            for key, child in item.items():
                visit(child, f"{path}.{key}")
        elif isinstance(item, list):
            for child in item[:1]:
                visit(child, f"{path}[]")

    visit(value, prefix)
    return tuple(sorted(found))


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return "unsupported"


def _result_count(value: Mapping[str, object]) -> int:
    results = value.get("results")
    if isinstance(results, list):
        return len(results)
    return 1 if isinstance(results, Mapping) else 0


def _upper(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def _digits(value: object) -> str:
    return value.strip().zfill(10) if isinstance(value, str) and value.strip().isdigit() else ""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
