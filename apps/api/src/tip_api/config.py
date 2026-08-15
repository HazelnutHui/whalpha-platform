from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AppConfig:
    name: str = "Trading Intelligence API"
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    market_data_root: Path = Path("/data/trading-intelligence-platform")
    enable_private_market_data_routes: bool = False

    def __post_init__(self) -> None:
        if not self.market_data_root.is_absolute():
            raise ValueError("market_data_root must be an absolute path")


def load_app_config(env: Mapping[str, str] | None = None) -> AppConfig:
    source = os.environ if env is None else env
    return AppConfig(
        market_data_root=Path(source.get("TIP_MARKET_DATA_ROOT", "/data/trading-intelligence-platform")),
        enable_private_market_data_routes=_truthy(source.get("TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES")),
    )


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


config = load_app_config()
