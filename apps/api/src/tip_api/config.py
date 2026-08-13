from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppConfig:
    name: str = "Trading Intelligence API"
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"


config = AppConfig()
