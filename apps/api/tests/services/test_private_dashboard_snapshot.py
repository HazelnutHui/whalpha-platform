from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1
from tip_api.services import private_dashboard_snapshot as snapshot
from tip_api.services.dashboard_overview import (
    DashboardOverviewV11,
    DashboardUniverseAudit,
    DashboardUniverseDefinition,
    DashboardUniverseView,
    MarketBenchmark,
    SectorBenchmarkEtf,
)

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
        map_type="trading_activity",
        size_metric="close_times_volume_proxy",
        color_metric="close_to_close_return",
        is_market_cap_weighted=False,
        is_sector_grouped=False,
        threshold=Decimal("20000000"),
        current_session_date=CURRENT,
        previous_session_date=PREVIOUS,
        nodes=(node,),
    )


def fake_overview():
    definition = DashboardUniverseDefinition(
        universe_id="provider_classified_common_shares_v1",
        name="Provider-Classified Common Shares (Provisional)",
        display_name="Common Shares",
        description="Fixture universe",
        long_display_name="Provider-Classified Common Shares (Provisional)", provisional=True,
        member_count=2, security_type_composition={"CS":2}, membership_fingerprint="a"*64,
    )
    audit = DashboardUniverseAudit(
        raw_comparable_count=3,
        common_stock_count=2,
        adr_count=None,
        etf_count=1,
        other_excluded_type_count=0,
        major_exchange_count=2,
        price_gate_count=2,
        final_count=2,
        exclusion_counts={"excluded_instrument_type": 1},
    )
    universe = DashboardUniverseView(
        definition=definition,
        audit=audit,
        summary=fake_summary(),
        movers=fake_movers(),
        trading_activity_map=fake_liquidity(),
        outlier_review_count=1,
        quality_flag_counts={"close_times_volume_proxy": 2},
        equal_weight_benchmark=MarketBenchmark(benchmark_id="equal_weight_universe",label="Equal-Weight Universe",ticker=None,available=True,current_session_date=CURRENT,previous_session_date=PREVIOUS,previous_close=None,current_close=None,close_to_close_return=Decimal("0.01"),quality_flags=("equal_weight_not_index_return",)),
    )
    secondary=replace(universe,definition=replace(definition,universe_id="provider_classified_common_shares_plus_adrs_v1",display_name="Common Shares + ADRs",member_count=3,security_type_composition={"CS":2,"ADRC":1}))
    sectors = (
        SectorBenchmarkEtf(
            ticker="XLC",
            sector="Communication Services",
            available=False,
            current_session_date=CURRENT,
            previous_session_date=PREVIOUS,
            previous_close=None,
            current_close=None,
            close_to_close_return=None,
            relative_to_spy_return=None,
            quality_flags=("benchmark_unavailable",),
        ),
    )
    market_benchmarks = (
        MarketBenchmark(
            benchmark_id="spy",
            label="S&P 500 ETF",
            ticker="SPY",
            available=False,
            current_session_date=CURRENT,
            previous_session_date=PREVIOUS,
            previous_close=None,
            current_close=None,
            close_to_close_return=None,
            quality_flags=("benchmark_unavailable",),
        ),
        MarketBenchmark(
            benchmark_id="equal_weight_universe",
            label="Equal-Weight Universe",
            ticker=None,
            available=True,
            current_session_date=CURRENT,
            previous_session_date=PREVIOUS,
            previous_close=None,
            current_close=None,
            close_to_close_return=Decimal("0.01"),
            quality_flags=("equal_weight_not_index_return",),
        ),
    )
    return DashboardOverviewV11(
        contract_version="2.0",
        default_universe_id="provider_classified_common_shares_v1",
        selected_universe_id="provider_classified_common_shares_v1",
        universe_definition_id="dashboard_universe_activation_v1",
        universe_version="1.0",
        governance_status="provisional_classification",
        classification_as_of_date=CURRENT,
        trailing_window_start=date(2026,7,16),trailing_window_end=PREVIOUS,trailing_window_session_count=20,
        reviewed_override_count=2,activation_fingerprint="b"*64,legacy_rollback_available=True,
        evidence_coverage_status="provider_form_complete_issuer_structure_provisional",
        current_session_date=CURRENT,
        previous_session_date=PREVIOUS,
        data_as_of_label="Data as of 2026-08-13 EOD",
        snapshot_generated_at=None,
        snapshot_validation_status="file_schema_consistency_checks_passed",
        freshness_status="stale",
        expected_latest_completed_session=date(2026, 8, 14),
        actual_latest_completed_session=CURRENT,
        session_lag=1,
        calendar_id="XNYS",
        freshness_checked_at=datetime(2026, 8, 15, 12, tzinfo=UTC),
        universes=(universe,secondary),
        market_benchmarks=market_benchmarks,
        sector_benchmarks=sectors,
        data_status="file_schema_consistency_checks_passed",
    )


class FakeOverviewService:
    def __init__(self, query_service, activation):
        self.query_service = query_service

    def get_latest_overview(self, *, checked_at=None):
        return fake_overview()


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
    monkeypatch.setattr(snapshot, "DashboardOverviewService", FakeOverviewService)
    result = snapshot.build_private_dashboard_snapshot(
        data_root=data_root,
        output_root=output_root,
        release_id=RID,
        generated_at=datetime(2026, 8, 15, 12, tzinfo=UTC),
        allowed_output_root=output_root,
        dashboard_activation=object(),
    )
    private = result.output_dir / "private-data" / "v1"
    assert (private / "manifest.json").is_file()
    assert (private / "market-summary.json").is_file()
    assert (private / "movers.json").is_file()
    assert (private / "liquidity-map.json").is_file()
    assert (private / "market-overview.json").is_file()
    manifest = json.loads((private / "manifest.json").read_text())
    assert manifest["access_classification"] == "private"
    assert manifest["contains_credentials"] is False
    assert manifest["contains_raw_provider_data"] is False
    assert manifest["current_session_date"] == "2026-08-13"
    assert manifest["file_sha256"]["market-summary.json"] == snapshot.sha256_file(private / "market-summary.json")
    assert manifest["overview_file"] == "market-overview.json"
    assert manifest["snapshot_contract_version"] == "1.3"
    assert manifest["dashboard_contract_version"] == "2.0"
    assert manifest["governance_status"] == "provisional_classification"
    assert manifest["expected_latest_completed_session"] == "2026-08-14"
    assert manifest["actual_latest_completed_session"] == "2026-08-13"
    assert manifest["session_lag"] == 1
    assert manifest["freshness_status"] == "stale"
    assert manifest["calendar_id"] == "XNYS"
    assert '"equal_weight_return":"0.01"' in (private / "market-summary.json").read_text()
    assert '"default_universe_id":"provider_classified_common_shares_v1"' in (private / "market-overview.json").read_text()
    assert '"universe_definition_id":"dashboard_universe_activation_v1"' in (private / "market-overview.json").read_text()


def test_corrupted_snapshot_file_detection(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    output_root = tmp_path / "build" / "private-dashboard"
    monkeypatch.setattr(snapshot, "DashboardOverviewService", FakeOverviewService)
    result = snapshot.build_private_dashboard_snapshot(data_root=data_root, output_root=output_root, release_id=RID, allowed_output_root=output_root,dashboard_activation=object())
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
        snapshot.build_private_dashboard_snapshot(data_root=data_root, output_root=link, release_id=RID, allowed_output_root=link,dashboard_activation=object())
    with pytest.raises(ValueError):
        snapshot.validate_release_id("2026-08-13T120000Z-abcdef0/escape")


def test_scripts_default_dry_run_and_nginx_template(repo_root: Path = Path(__file__).resolve().parents[4]):
    deploy_script = repo_root / "scripts" / "admin" / "deploy-private-dashboard-oci.sh"
    inspect_script = repo_root / "scripts" / "admin" / "inspect-private-dashboard-oci.sh"
    review_script = repo_root / "scripts" / "admin" / "review-oci-dashboard-deployment-runtime.sh"
    build_script = repo_root / "scripts" / "admin" / "build-oci-dashboard-bundle.sh"
    nginx_template = repo_root / "deploy" / "oci" / "nginx" / "whalpha-private-dashboard.conf.template"
    assert "dry-run" in deploy_script.read_text()
    assert "--apply" in deploy_script.read_text()
    assert "datetime.timezone.utc" in inspect_script.read_text()
    assert "datetime.UTC" not in inspect_script.read_text()
    assert "VITE_MARKET_DATA_MODE=snapshot" in build_script.read_text()
    assert "--snapshot-path" in build_script.read_text()
    assert "--snapshot-release" not in build_script.read_text()
    assert "--bundle-root" in build_script.read_text()
    assert "offline_artifact_custody_cli" in build_script.read_text()
    assert "--build-timestamp" in build_script.read_text()
    assert "private-dashboard-v2/revision=universe-funnel-v2" in build_script.read_text()
    assert "release_id=*" in build_script.read_text()
    assert "--market-intelligence-publication" in build_script.read_text()
    assert "supported Snapshot 1.5-1.11 / Dashboard 2.2-2.8 pair" in build_script.read_text()
    assert "sector-etf-rotation.json" in build_script.read_text()
    assert "candidate-strategy-channel-product/1.0" in build_script.read_text()
    assert "guest_and_credential_capability_identical" in build_script.read_text()
    assert "login-i18n.js" in build_script.read_text()
    assert 'public/favicon.png" "${staging_dir}/favicon.png' in build_script.read_text()
    assert "'default_locale': 'en'" in build_script.read_text()
    assert "oci-dashboard-serving-bundle/1.0" in build_script.read_text()
    assert "guest_and_credential_capability_identical" in build_script.read_text()
    assert "npm_config_offline=true" in build_script.read_text()
    assert "trap cleanup_staging EXIT" in build_script.read_text()
    text = nginx_template.read_text()
    assert "location /dashboard/" in text and "auth_request /auth/internal-verify" in text
    assert "location = / {" in text and "try_files /login/index.html =404" in text
    assert "location = /favicon.png" in text and "try_files /favicon.png =404" in text
    assert "location = /login/" in text and "return 302 /$is_args$args" in text
    assert "location = /auth/status" in text
    assert "location /login/" in text and "root /srv/whalpha/current" in text and "location = /auth/login" in text
    assert "location = /auth/guest" in text and "proxy_pass http://127.0.0.1:8010/guest" in text
    assert "location /private-data/" in text and "no-store" in text
    assert "Access-Control-Allow-Origin" not in text
    assert "Content-Security-Policy" in text
    deploy_text = deploy_script.read_text()
    assert "candidate-strategy-channels.json" in deploy_text
    assert "guest Candidate strategy-channel binding is invalid" in deploy_text
    assert 'snapshot_contract_version\":\"1\\.(5|6|7|8|9|10|11)' in deploy_text
    assert "sector-etf-rotation.json" in deploy_text
    assert "guest Sector Rotation binding is invalid" in deploy_text
    assert "root route returned placeholder body" in deploy_text
    assert "public favicon status" in deploy_text
    assert "login compatibility redirect status" in deploy_text
    assert "auth status unauth status" in deploy_text
    assert "guest Dashboard status" in deploy_text and "guest private-data status" in deploy_text
    assert "remote_password_rotation_path" in deploy_text
    assert "--expected-current-release" in deploy_text
    assert "--bundle-path" in deploy_text
    assert "target staging path already exists" in deploy_text
    assert "remote failed-release residue appeared before mutation" in deploy_text
    assert "failed_units_before" in deploy_text
    assert "failed_units_after" in deploy_text
    assert "deployment introduced a new failed system unit" in deploy_text
    assert 'systemctl --failed --no-legend | wc -l' not in deploy_text
    inspect_text = inspect_script.read_text()
    assert "oci-dashboard-remote-state/1.0" in inspect_text
    assert "credential_login_tested" in inspect_text
    assert "guest_and_credential_route_policy_identical" in inspect_text
    assert "DEPLOY_FAILED" in inspect_text
    subprocess.run(["bash", "-n", str(deploy_script)], check=True)
    subprocess.run(["bash", "-n", str(inspect_script)], check=True)
    subprocess.run(["bash", "-n", str(review_script)], check=True)
    review_help = subprocess.run(
        [str(review_script), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--review-enabled-candidate" in review_help.stdout


def test_password_rotation_script_safety(tmp_path: Path, repo_root: Path = Path(__file__).resolve().parents[4]):
    script = repo_root / "scripts" / "admin" / "rotate-whalpha-dashboard-password.sh"
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    (auth_dir / "whalpha-dashboard.htpasswd").write_text("hui:$6$fixture$hash\n", encoding="utf-8")
    text = script.read_text()
    subprocess.run(["bash", "-n", str(script)], check=True)
    help_result = subprocess.run([str(script), "--help"], check=True, capture_output=True, text=True)
    assert "--apply" in help_result.stdout
    bad_result = subprocess.run([str(script), "--bad"], capture_output=True, text=True)
    assert bad_result.returncode == 2
    extra_result = subprocess.run([str(script), "--apply", "extra"], capture_output=True, text=True)
    assert extra_result.returncode == 2
    non_tty_result = subprocess.run(
        [str(script), "--apply"],
        env={
            "PATH": "/usr/bin:/bin",
            "WHALPHA_ROTATE_TEST_MODE": "1",
            "WHALPHA_ROTATE_EXPECTED_HOSTNAME": "dell5820",
            "WHALPHA_ROTATE_AUTH_DIR": str(auth_dir),
        },
        input="short\nshort\n",
        capture_output=True,
        text=True,
    )
    assert non_tty_result.returncode != 0
    assert "--apply requires an interactive terminal" in non_tty_result.stderr
    assert "openssl passwd -6 -stdin" in text
    assert "systemctl restart \"$AUTH_SERVICE\"" in text
    assert "MIN_PASSWORD_LENGTH=10" in text
    assert "wait_for_listener" in text
    assert "rollback_succeeded=true" in text
    assert "password_rotation=completed" in text
    assert "ROTATE_PASSWORD" in text
    assert "set -x" not in text
    assert "echo \"$ROTATE_PASSWORD\"" not in text
    assert "WHALPHA_PASSWORD" in text


def run_rotation_function(script: Path, body: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = {
        "PATH": "/usr/bin:/bin",
        "WHALPHA_ROTATE_SOURCE_ONLY": "1",
        "WHALPHA_ROTATE_TEST_MODE": "1",
        "WHALPHA_ROTATE_EXPECTED_HOSTNAME": "dell5820",
        "WHALPHA_ROTATE_SLEEP_SECONDS": "0",
        **(env or {}),
    }
    return subprocess.run(
        ["bash", "-c", f"source {script}; {body}"],
        capture_output=True,
        text=True,
        env=merged_env,
    )


def test_password_rotation_listener_parser(repo_root: Path = Path(__file__).resolve().parents[4]):
    script = repo_root / "scripts" / "admin" / "rotate-whalpha-dashboard-password.sh"
    good = "State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\nLISTEN 0 5 127.0.0.1:8010 0.0.0.0:* users:((\"python3\",pid=123,fd=3))\n"
    result = subprocess.run(
        ["bash", "-c", f"source {script}; listener_addresses_from_ss"],
        input=good,
        capture_output=True,
        text=True,
        env={"WHALPHA_ROTATE_SOURCE_ONLY": "1", "WHALPHA_ROTATE_TEST_MODE": "1"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "127.0.0.1:8010"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("LISTEN 0 5 127.0.0.1:8010 0.0.0.0:*\n", True),
        ("State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\nLISTEN 0 5 127.0.0.1:8010 0.0.0.0:*\n", True),
        ("LISTEN 0 5 0.0.0.0:8010 0.0.0.0:*\n", False),
        ("LISTEN 0 5 [::]:8010 [::]:*\n", False),
        ("LISTEN 0 5 127.0.0.1:8010 0.0.0.0:*\nLISTEN 0 5 0.0.0.0:8010 0.0.0.0:*\n", False),
        ("", False),
    ],
)
def test_password_rotation_listener_validation(tmp_path: Path, content: str, expected: bool, repo_root: Path = Path(__file__).resolve().parents[4]):
    script = repo_root / "scripts" / "admin" / "rotate-whalpha-dashboard-password.sh"
    listener_file = tmp_path / "ss.txt"
    listener_file.write_text(content, encoding="utf-8")
    result = run_rotation_function(script, "listener_is_localhost_only", env={"WHALPHA_ROTATE_LISTENER_FILE": str(listener_file)})
    assert (result.returncode == 0) is expected


def test_password_rotation_listener_wait_timeout(tmp_path: Path, repo_root: Path = Path(__file__).resolve().parents[4]):
    script = repo_root / "scripts" / "admin" / "rotate-whalpha-dashboard-password.sh"
    listener_file = tmp_path / "ss.txt"
    listener_file.write_text("", encoding="utf-8")
    result = run_rotation_function(
        script,
        "wait_for_listener",
        env={"WHALPHA_ROTATE_LISTENER_FILE": str(listener_file), "WHALPHA_ROTATE_LISTENER_WAIT_ATTEMPTS": "2"},
    )
    assert result.returncode != 0


def test_password_rotation_rollback_restores_fixture(tmp_path: Path, repo_root: Path = Path(__file__).resolve().parents[4]):
    script = repo_root / "scripts" / "admin" / "rotate-whalpha-dashboard-password.sh"
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    auth_file = auth_dir / "whalpha-dashboard.htpasswd"
    backup = auth_dir / "whalpha-dashboard.htpasswd.backup-fixture"
    auth_file.write_text("hui:$6$new$hash\n", encoding="utf-8")
    backup.write_text("hui:$6$old$hash\n", encoding="utf-8")
    listener_file = tmp_path / "ss.txt"
    listener_file.write_text("LISTEN 0 5 127.0.0.1:8010 0.0.0.0:*\n", encoding="utf-8")
    result = run_rotation_function(
        script,
        f"AUTH_DIR={auth_dir}; AUTH_FILE={auth_file}; restore_backup {backup}",
        env={"WHALPHA_ROTATE_LISTENER_FILE": str(listener_file)},
    )
    assert result.returncode == 0
    assert auth_file.read_text(encoding="utf-8") == "hui:$6$old$hash\n"
    assert oct(auth_file.stat().st_mode & 0o777) == "0o640"
    assert "old" not in result.stdout
    assert "hash" not in result.stdout
