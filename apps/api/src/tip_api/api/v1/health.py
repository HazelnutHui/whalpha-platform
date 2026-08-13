from fastapi import APIRouter

from tip_api.config import config
from tip_api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="trading-intelligence-api",
        version=config.version,
    )
