from __future__ import annotations

from fastapi import FastAPI

from tip_api.api.v1.private_eod import router as private_eod_router
from tip_api.api.v1.private_market import router as private_market_router
from tip_api.api.v1.router import router as api_v1_router
from tip_api.config import AppConfig, config
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService
from tip_api.services.dashboard_overview import DashboardOverviewService


def create_app(
    app_config: AppConfig | None = None,
    *,
    eod_query_service: EodMarketDataQueryService | None = None,
) -> FastAPI:
    cfg = app_config or config
    app = FastAPI(
        title=cfg.name,
        version=cfg.version,
    )
    app.include_router(api_v1_router, prefix=cfg.api_v1_prefix)
    if cfg.enable_private_market_data_routes:
        service = eod_query_service or EodMarketDataQueryService(
            CanonicalEodReadRepository(cfg.market_data_root)
        )
        app.state.eod_query_service = service
        app.state.eod_return_analytics_service = EodReturnAnalyticsService(service)
        app.state.dashboard_overview_service = DashboardOverviewService(service)
        app.include_router(private_eod_router, prefix=cfg.api_v1_prefix)
        app.include_router(private_market_router, prefix=cfg.api_v1_prefix)
    return app


app = create_app()
