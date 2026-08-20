"""Persistence boundary for trailing-liquidity shadow results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from tip_api.contracts.market_data.v1 import TrailingLiquidityShadowManifestV1


class TrailingLiquidityPersistenceError(Exception):
    pass


class TrailingLiquidityConflictError(TrailingLiquidityPersistenceError):
    pass


class TrailingLiquidityCorruptionError(TrailingLiquidityPersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class TrailingLiquidityPublicationResult:
    metric_path: Path
    decision_path: Path
    logical_manifest_path: Path
    metric_record_count: int
    decision_record_count: int
    metric_content_fingerprint: str
    decision_content_fingerprint: str
    metric_parquet_sha256: str
    decision_parquet_sha256: str
    logical_content_fingerprint: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class CompletedTrailingLiquidityPublication:
    manifest: TrailingLiquidityShadowManifestV1
    metric_record_count: int
    decision_record_count: int


class TrailingLiquidityRepository(Protocol):
    def publish(self, *args: object, **kwargs: object) -> TrailingLiquidityPublicationResult: ...
