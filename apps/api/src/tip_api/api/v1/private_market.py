"""Default-disabled private market summary routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.persistence.eod_read import EodDatasetUnavailableError, EodSessionNotFoundError
from tip_api.schemas.private_market import DashboardOverviewResponse, EodReturnsPageResponse, EodReturnResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse
from tip_api.services.dashboard_overview import DashboardOverviewService
from tip_api.services.eod_market_data import EodQueryValidationError
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService

router = APIRouter(prefix="/private/market", tags=["private-market-summary"])


def _service(request: Request) -> EodReturnAnalyticsService:
    service = getattr(request.app.state, "eod_return_analytics_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="market data unavailable")
    return service


def _overview_service(request: Request) -> DashboardOverviewService:
    service = getattr(request.app.state, "dashboard_overview_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="market data unavailable")
    return service


def _safe_call(func):
    try:
        return func()
    except EodSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="completed session pair not found") from exc
    except EodDatasetUnavailableError as exc:
        raise HTTPException(status_code=503, detail="market data unavailable") from exc
    except EodQueryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/summary/latest", response_model=MarketSummaryResponse)
def latest_summary(request: Request) -> MarketSummaryResponse:
    return MarketSummaryResponse.from_model(_safe_call(lambda: _service(request).get_latest_summary()))


@router.get("/overview/latest", response_model=DashboardOverviewResponse)
def latest_overview(request: Request) -> DashboardOverviewResponse:
    return DashboardOverviewResponse.from_model(_safe_call(lambda: _overview_service(request).get_latest_overview()))


@router.get("/movers/latest", response_model=MoversResponse)
def latest_movers(request: Request, per_side: int = Query(default=10, ge=1, le=50)) -> MoversResponse:
    return MoversResponse.from_model(_safe_call(lambda: _service(request).get_latest_movers(per_side=per_side)))


@router.get("/liquidity-map/latest", response_model=LiquidityMapResponse)
def latest_liquidity_map(request: Request, limit: int = Query(default=300, ge=1, le=500)) -> LiquidityMapResponse:
    return LiquidityMapResponse.from_model(_safe_call(lambda: _service(request).get_latest_liquidity_map(limit=limit)))


@router.get("/returns/latest", response_model=EodReturnsPageResponse)
def latest_returns(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ticker: str | None = None,
    instrument_type: InstrumentType | None = None,
) -> EodReturnsPageResponse:
    items, total, current_date, previous_date = _safe_call(
        lambda: _service(request).get_latest_returns_page(
            limit=limit,
            offset=offset,
            ticker=ticker,
            instrument_type=instrument_type,
        )
    )
    return EodReturnsPageResponse(
        current_session_date=current_date,
        previous_session_date=previous_date,
        total_count=total,
        limit=limit,
        offset=offset,
        items=tuple(EodReturnResponse.from_model(item) for item in items),
    )
