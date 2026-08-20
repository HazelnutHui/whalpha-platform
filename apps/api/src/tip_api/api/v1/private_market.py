"""Default-disabled private market summary routes."""

from __future__ import annotations

from dataclasses import replace

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


def _selected_overview(request: Request, universe_id: str | None):
    overview = _safe_call(lambda: _overview_service(request).get_latest_overview(universe_id=universe_id))
    selected = next(item for item in overview.universes if item.definition.universe_id == overview.selected_universe_id)
    return overview, selected


@router.get("/summary/latest", response_model=MarketSummaryResponse)
def latest_summary(request: Request, universe_id: str | None = None) -> MarketSummaryResponse:
    _, selected = _selected_overview(request, universe_id)
    return MarketSummaryResponse.from_model(selected.summary).model_copy(update={"universe_id":selected.definition.universe_id,"universe_membership_fingerprint":selected.definition.membership_fingerprint,"universe_member_count":selected.definition.member_count})


@router.get("/overview/latest", response_model=DashboardOverviewResponse)
def latest_overview(request: Request, universe_id: str | None = None) -> DashboardOverviewResponse:
    return DashboardOverviewResponse.from_model(_safe_call(lambda: _overview_service(request).get_latest_overview(universe_id=universe_id)))


@router.get("/movers/latest", response_model=MoversResponse)
def latest_movers(request: Request, per_side: int = Query(default=10, ge=1, le=50), universe_id: str | None = None) -> MoversResponse:
    _, selected = _selected_overview(request, universe_id)
    movers=replace(selected.movers,top_gainers=selected.movers.top_gainers[:per_side],top_losers=selected.movers.top_losers[:per_side])
    return MoversResponse.from_model(movers).model_copy(update={"universe_id":selected.definition.universe_id,"universe_membership_fingerprint":selected.definition.membership_fingerprint,"universe_member_count":selected.definition.member_count})


@router.get("/liquidity-map/latest", response_model=LiquidityMapResponse)
def latest_liquidity_map(request: Request, limit: int = Query(default=300, ge=1, le=500), universe_id: str | None = None) -> LiquidityMapResponse:
    _, selected = _selected_overview(request, universe_id)
    projection=replace(selected.trading_activity_map,nodes=selected.trading_activity_map.nodes[:limit])
    return LiquidityMapResponse.from_model(projection).model_copy(update={"universe_id":selected.definition.universe_id,"universe_membership_fingerprint":selected.definition.membership_fingerprint,"universe_member_count":selected.definition.member_count})


@router.get("/returns/latest", response_model=EodReturnsPageResponse)
def latest_returns(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ticker: str | None = None,
    instrument_type: InstrumentType | None = None,
    universe_id: str | None = None,
) -> EodReturnsPageResponse:
    rows, record = _safe_call(lambda: _overview_service(request).get_latest_returns_for_universe(universe_id))
    if ticker is not None: rows=tuple(item for item in rows if item.ticker==ticker.strip().upper())
    if instrument_type is not None: rows=tuple(item for item in rows if item.instrument_type is instrument_type)
    total=len(rows); items=rows[offset:offset+limit]
    current_date,previous_date=_overview_service(request).get_latest_session_pair()
    return EodReturnsPageResponse(
        current_session_date=current_date,
        previous_session_date=previous_date,
        total_count=total,
        limit=limit,
        offset=offset,
        items=tuple(EodReturnResponse.from_model(item) for item in items),
        universe_id=record.universe_id,
        universe_membership_fingerprint=record.membership_fingerprint,
        universe_member_count=record.member_count,
    )
