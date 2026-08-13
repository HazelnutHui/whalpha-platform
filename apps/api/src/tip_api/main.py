from fastapi import FastAPI

from tip_api.api.v1.router import router as api_v1_router
from tip_api.config import config


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.name,
        version=config.version,
    )
    app.include_router(api_v1_router, prefix=config.api_v1_prefix)
    return app


app = create_app()
