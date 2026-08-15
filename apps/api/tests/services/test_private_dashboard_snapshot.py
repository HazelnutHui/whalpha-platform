from __future__ import annotations

import json
import subprocess
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1
from tip_api.services import private_dashboard_snapshot as snapshot

CURRENT = date(2026, 8, 13)
PREVIOUS = date(2026, 8, 12)
RID = "2026-08-13T120000Z-abcdef0"
ID_A = UUID("00000000-0000-5000-8000-200000000001")
ID_B = UUID("00000000-0000-5000-8000-200000000002")


def return_row(ticker="TESTA", ret=Decimal("0.05")):
    return EodReturnReadModel(
        instrument_id=ID_A,
        ticker=ticker,
        name=f"{ticker} Synthetic",
        instrument_type=InstrumentType.COMMON_STOCK,
        current_session_date=CURRENT,
        previous_session_date=PREVIOUS,
        previous_close=Decimal("100"),
        current_close=Decimal("105"),
        close_to_close_return=ret,
        current_volume=Decimal("100000.25"),
        current_vwap=None,
        current_dollar_volume_proxy=Decimal("10500026.25"),
        quality_status=QualityStatus.WARNING,
        quality_flags=("close_times_volume_proxy",),
    )


def fake_summary():
    return MarketSummaryV1(
        current_session_date=CURRENT,
        previous_session_date=PREVIOUS,
        comparable_instrument_count=2,
        current_only_count=0,
        previous_only_count=0,
        advancer_count=1,
        decliner_count=1,
        unchanged_count=0,
        advance_decline_ratio=Decimal("1"),
        advance_decline_net=0,
        advancer_volume=Decimal("100000.25"),
        decliner_volume=Decimal("200000.75"),
        up_down_volume_ratio=Decimal("0.5"),
        equal_weight_return=Decimal("0.01"),
        median_return=Decimal("0.01"),
        positive_return_share=Decimal("0.5"),
        negative_return_share=Decimal("0.5"),
        common_stock_comparable_count=1,
        etf_comparable_count=1,
        quality_warning_count=1,
        data_status="complete",
    )


def fake_movers():
    return MoversV1(current_session_date=CURRENT, previous_session_date=PREVIOUS, threshold=Decimal("5000000"), top_gainers=(return_row("TESTA"),), top_losers=(return_row("TESTB", Decimal("-0.03")),))


def fake_liquidity():
    node = LiquidityMapNodeV1(
        instrument_id=ID_A,
        ticker="TESTA",
        name="TESTA Synthetic",
        instrument_type=InstrumentType.COMMON_STOCK,
        size_value=Decimal("10500026.25"),
        color_value=Decimal("0.05"),
        current_close=Decimal("105"),
        current_volume=Decimal("100000.25"),
        rank=1,
        quality_flags=("close_times_volume_proxy",),
    )
    return LiquidityMapV1(
        map_type="liquidity",
        size_metric="close_times_volume_proxy",
        color_metric="close_to_close_return",
        is_market_cap_weighted=False,
        is_sector_grouped=False,
        threshold=Decimal("5000000"),
        current_session_date=CURRENT,
        previous_session_date=PREVIOUS,
        nodes=(node,),
    )


class FakeAnalytics:
    def __init__(self, query_service):
        self.query_service = query_service

    def get_latest_summary(self):
        return fake_summary()

    def get_latest_movers(self, per_side=10):
        return fake_movers()

    def get_latest_liquidity_map(self, limit=300):
        return fake_liquidity()


def test_release_id_validation():
    assert snapshot.validate_release_id(RID) == RID
    with pytest.raises(ValueError):
        snapshot.validate_release_id("../../bad")


def test_deterministic_json_rejects_nonfinite():
    assert snapshot.deterministic_json_bytes({"b": 2, "a": "1"}) == b'{"a":"1","b":2}\n'
    with pytest.raises(ValueError):
        snapshot.deterministic_json_bytes({"bad": float("nan")})


def test_build_snapshot_exports_contract_files(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    output_root = tmp_path / "build" / "private-dashboard"
    monkeypatch.setattr(snapshot, "EodReturnAnalyticsService", FakeAnalytics)
    result = snapshot.build_private_dashboard_snapshot(
        data_root=data_root,
        output_root=output_root,
        release_id=RID,
        generated_at=datetime(2026, 8, 15, 12, tzinfo=UTC),
        allowed_output_root=output_root,
    )
    private = result.output_dir / "private-data" / "v1"
    assert (private / "manifest.json").is_file()
    assert (private / "market-summary.json").is_file()
    assert (private / "movers.json").is_file()
    assert (private / "liquidity-map.json").is_file()
    manifest = json.loads((private / "manifest.json").read_text())
    assert manifest["access_classification"] == "private"
    assert manifest["contains_credentials"] is False
    assert manifest["contains_raw_provider_data"] is False
    assert manifest["current_session_date"] == "2026-08-13"
    assert manifest["file_sha256"]["market-summary.json"] == snapshot.sha256_file(private / "market-summary.json")
    assert '"equal_weight_return":"0.01"' in (private / "market-summary.json").read_text()


def test_corrupted_snapshot_file_detection(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    output_root = tmp_path / "build" / "private-dashboard"
    monkeypatch.setattr(snapshot, "EodReturnAnalyticsService", FakeAnalytics)
    result = snapshot.build_private_dashboard_snapshot(data_root=data_root, output_root=output_root, release_id=RID, allowed_output_root=output_root)
    (result.output_dir / "private-data" / "v1" / "movers.json").write_text("{}\n")
    with pytest.raises(snapshot.DashboardSnapshotError):
        snapshot.validate_snapshot_release(result.output_dir)


def test_output_symlink_and_traversal_rejected(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    link = tmp_path / "link"
    target = tmp_path / "target"
    target.mkdir()
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(snapshot.DashboardSnapshotError):
        snapshot.build_private_dashboard_snapshot(data_root=data_root, output_root=link, release_id=RID, allowed_output_root=link)
    with pytest.raises(ValueError):
        snapshot.validate_release_id("2026-08-13T120000Z-abcdef0/escape")


def test_scripts_default_dry_run_and_nginx_template(repo_root: Path = Path(__file__).resolve().parents[4]):
    deploy_script = repo_root / "scripts" / "admin" / "deploy-private-dashboard-oci.sh"
    build_script = repo_root / "scripts" / "admin" / "build-oci-dashboard-bundle.sh"
    nginx_template = repo_root / "deploy" / "oci" / "nginx" / "whalpha-private-dashboard.conf.template"
    assert "dry-run" in deploy_script.read_text()
    assert "--apply" in deploy_script.read_text()
    assert "VITE_MARKET_DATA_MODE=snapshot" in build_script.read_text()
    text = nginx_template.read_text()
    assert "location /dashboard/" in text and "auth_basic" in text
    assert "location /private-data/" in text and "no-store" in text
    assert "location / {" in text
    assert "Access-Control-Allow-Origin" not in text
    assert "Content-Security-Policy" in text
