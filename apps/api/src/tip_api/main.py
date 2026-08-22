from __future__ import annotations

from fastapi import FastAPI

from tip_api.api.v1.private_eod import router as private_eod_router
from tip_api.api.v1.private_market import router as private_market_router
from tip_api.api.v1.router import router as api_v1_router
from tip_api.config import AppConfig, config
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.dashboard_universe_activation import DashboardUniverseActivationError
from tip_api.persistence.parquet.dashboard_universe_activation_active import ActiveDashboardUniverseActivation, read_active_dashboard_universe_activation
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService
from tip_api.services.dashboard_overview import DashboardOverviewService


def create_app(
    app_config: AppConfig | None = None,
    *,
    eod_query_service: EodMarketDataQueryService | None = None,
    dashboard_activation: ActiveDashboardUniverseActivation | None = None,
) -> FastAPI:
    cfg = app_config or config
    app = FastAPI(title=cfg.name, version=cfg.version)
    app.include_router(api_v1_router, prefix=cfg.api_v1_prefix)
    if cfg.enable_private_market_data_routes:
        service = eod_query_service or EodMarketDataQueryService(CanonicalEodReadRepository(cfg.market_data_root))
        activation = dashboard_activation
        if activation is None:
            sessions=service.list_sessions()
            if sessions:
                try:
                    activation=read_active_dashboard_universe_activation(cfg.market_data_root,analysis_session=sessions[-1].session_date,validate_sources=True)
                except DashboardUniverseActivationError:
                    activation=None
        app.state.eod_query_service = service
        app.state.eod_return_analytics_service = EodReturnAnalyticsService(service)
        if activation is not None:
            app.state.dashboard_overview_service = DashboardOverviewService(service,activation)
        app.include_router(private_eod_router, prefix=cfg.api_v1_prefix)
        app.include_router(private_market_router, prefix=cfg.api_v1_prefix)
    return app


app = create_app()
