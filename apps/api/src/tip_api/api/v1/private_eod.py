"""Default-disabled private canonical EOD market-data routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request

from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.persistence.eod_read import EodDatasetUnavailableError, EodSessionNotFoundError
from tip_api.schemas.private_eod import (
    EodSessionDescriptorResponse,
    EodSessionListResponse,
    EodSessionPageResponse,
    EodSessionSummaryResponse,
)
from tip_api.services.eod_market_data import EodMarketDataQueryService, EodQueryValidationError

router = APIRouter(prefix="/private/market-data/eod", tags=["private-market-data-eod"])


def _service(request: Request) -> EodMarketDataQueryService:
    service = getattr(request.app.state, "eod_query_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="market data unavailable")
    return service


def _safe_call(func):
    try:
        return func()
    except EodSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="EOD session not found") from exc
    except EodDatasetUnavailableError as exc:
        raise HTTPException(status_code=503, detail="market data unavailable") from exc
    except EodQueryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sessions", response_model=EodSessionListResponse)
def list_sessions(request: Request) -> EodSessionListResponse:
    sessions = _safe_call(lambda: _service(request).list_sessions())
    return EodSessionListResponse(sessions=tuple(EodSessionDescriptorResponse.from_read_model(item) for item in sessions))


@router.get("/sessions/latest", response_model=EodSessionDescriptorResponse)
def latest_session(request: Request) -> EodSessionDescriptorResponse:
    descriptor = _safe_call(lambda: _service(request).get_latest_session())
    return EodSessionDescriptorResponse.from_read_model(descriptor)


@router.get("/sessions/{session_date}/summary", response_model=EodSessionSummaryResponse)
def session_summary(session_date: date, request: Request) -> EodSessionSummaryResponse:
    summary = _safe_call(lambda: _service(request).get_session_summary(session_date))
    return EodSessionSummaryResponse.from_read_model(summary)


@router.get("/sessions/{session_date}/bars", response_model=EodSessionPageResponse)
def session_bars(
    session_date: date,
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ticker: str | None = None,
    instrument_type: InstrumentType | None = None,
) -> EodSessionPageResponse:
    page = _safe_call(
        lambda: _service(request).get_bars_page(
            session_date=session_date,
            limit=limit,
            offset=offset,
            ticker=ticker,
            instrument_type=instrument_type,
        )
    )
    return EodSessionPageResponse.from_read_model(page)
