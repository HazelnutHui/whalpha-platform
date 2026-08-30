"""Lazy Dashboard projection of the Market Intelligence Sector ETF product."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .market_intelligence import SectorEtfRotationPublicationSourceV1
from .sector_etf_rotation import SectorEtfRotationSnapshotV1


SECTOR_ROTATION_DASHBOARD_SNAPSHOT_CONTRACT_VERSION = (
    "sector-etf-rotation-dashboard-snapshot/1.0"
)


class SectorEtfRotationDashboardSnapshotV1(BaseModel):
    """Self-contained lazy file with exact MI and audit lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        "sector-etf-rotation-dashboard-snapshot/1.0"
    ] = SECTOR_ROTATION_DASHBOARD_SNAPSHOT_CONTRACT_VERSION
    market_intelligence_contract_version: Literal[
        "market-intelligence-publication/1.3"
    ] = "market-intelligence-publication/1.3"
    publication_id: str
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: SectorEtfRotationPublicationSourceV1
    product: SectorEtfRotationSnapshotV1
    language_neutral: Literal[True] = True
    fixed_sector_etf_proxy_only: Literal[True] = True
    constituent_breadth_unavailable: Literal[True] = True
    fund_flow_claim_prohibited: Literal[True] = True
    theme_membership_unavailable: Literal[True] = True
    guest_and_credential_capability_identical: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def lineage_reconciles(self) -> "SectorEtfRotationDashboardSnapshotV1":
        if (
            self.source.product_contract_version != self.product.contract_version
            or self.source.calculation_version != self.product.calculation_version
            or self.source.parameter_fingerprint != self.product.parameter_fingerprint
            or self.source.history_source_fingerprint
            != self.product.source_history_fingerprint
            or self.source.product_logical_fingerprint
            != self.product.logical_fingerprint
            or self.source.record_count != len(self.product.records)
            or self.source.theme_status != self.product.theme_status
            or sector_rotation_dashboard_snapshot_fingerprint(
                self, exclude={"logical_fingerprint"}
            )
            != self.logical_fingerprint
        ):
            raise ValueError("Sector Rotation Dashboard snapshot lineage differs")
        return self


def sector_rotation_dashboard_snapshot_fingerprint(
    value: BaseModel | dict[str, object], *, exclude: set[str] | None = None
) -> str:
    excluded = exclude or set()
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude=excluded)
    else:
        payload = {
            "schema_version": "1.0",
            "contract_version": (
                SECTOR_ROTATION_DASHBOARD_SNAPSHOT_CONTRACT_VERSION
            ),
            "market_intelligence_contract_version": (
                "market-intelligence-publication/1.3"
            ),
            "language_neutral": True,
            "fixed_sector_etf_proxy_only": True,
            "constituent_breadth_unavailable": True,
            "fund_flow_claim_prohibited": True,
            "theme_membership_unavailable": True,
            "guest_and_credential_capability_identical": True,
            **{
                key: (
                    item.model_dump(mode="json")
                    if isinstance(item, BaseModel)
                    else item
                )
                for key, item in value.items()
                if key not in excluded
            },
        }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
