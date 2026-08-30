"""Frozen parameters for transparent Sector ETF Rotation V1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SectorEtfDefinition:
    ticker: str
    sector: str


SECTOR_ETFS = (
    SectorEtfDefinition("XLC", "Communication Services"),
    SectorEtfDefinition("XLY", "Consumer Discretionary"),
    SectorEtfDefinition("XLP", "Consumer Staples"),
    SectorEtfDefinition("XLE", "Energy"),
    SectorEtfDefinition("XLF", "Financials"),
    SectorEtfDefinition("XLV", "Health Care"),
    SectorEtfDefinition("XLI", "Industrials"),
    SectorEtfDefinition("XLB", "Materials"),
    SectorEtfDefinition("XLRE", "Real Estate"),
    SectorEtfDefinition("XLK", "Information Technology"),
    SectorEtfDefinition("XLU", "Utilities"),
)
WINDOWS = (5, 10, 20)
CALCULATION_VERSION = "sector-etf-rotation-v1.0.0"
PARAMETER_SET_ID = "sector-etf-rotation-fixed-registry-1"
PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        {
            "calculation_version": CALCULATION_VERSION,
            "parameter_set_id": PARAMETER_SET_ID,
            "benchmark": "SPY",
            "windows": WINDOWS,
            "registry": [asdict(item) for item in SECTOR_ETFS],
            "posture_axes": ("relative_return_20", "relative_return_5_acceleration"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()
