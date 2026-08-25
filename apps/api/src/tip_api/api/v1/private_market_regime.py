"""Explicitly enabled, read-only Market Regime local preview routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tip_api.contracts.analytics.v1 import (
    MarketRegimeOpportunityMapResponseV1,
    MarketRegimeRelationshipDetailResponseV1,
)
from tip_api.services.market_regime_preview import MarketRegimePreviewService


router = APIRouter(prefix="/private/market-regime", tags=["private-market-regime-preview"])


def _service(request: Request) -> MarketRegimePreviewService:
    service = getattr(request.app.state, "market_regime_preview_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Market Regime preview unavailable")
    return service


@router.get("/overview", response_model=MarketRegimeOpportunityMapResponseV1)
def market_regime_overview(
    request: Request, universe_id: str | None = None
) -> MarketRegimeOpportunityMapResponseV1:
    try:
        return _service(request).overview(universe_id)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="unknown Universe") from exc


@router.get(
    "/relationships/{pair_id}", response_model=MarketRegimeRelationshipDetailResponseV1
)
def market_regime_relationship_detail(
    pair_id: str, request: Request, universe_id: str | None = None
) -> MarketRegimeRelationshipDetailResponseV1:
    try:
        return _service(request).relationship_detail(pair_id, universe_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown Universe or ETF pair") from exc
