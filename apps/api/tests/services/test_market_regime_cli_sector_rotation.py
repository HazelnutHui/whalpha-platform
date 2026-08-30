from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from tip_api.contracts.market_data.v2.dashboard_universe_activation import (
    PUBLIC_UNIVERSE_ORDER,
)
from tip_api.services import market_regime_cli as cli


def test_phase1a_reuses_one_panel_for_sector_rotation(monkeypatch, capsys) -> None:
    panel = object()
    phase_output = Path("/tmp") / f"phase1a-cli-{uuid4().hex}"
    sector_output = Path("/tmp") / f"sector-cli-{uuid4().hex}"
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panel",
        lambda **_: calls.append(("load", panel)) or panel,
    )
    monkeypatch.setattr(
        cli,
        "calculate_market_regime",
        lambda *, panel, universe_id: (
            calls.append((f"phase1a:{universe_id}", panel))
            or (SimpleNamespace(), ())
        ),
    )
    monkeypatch.setattr(
        cli,
        "compare_with_independent_oracle",
        lambda *, panel, result: calls.append(("phase1a_oracle", panel))
        or SimpleNamespace(),
    )
    monkeypatch.setattr(
        cli,
        "write_market_regime_audit",
        lambda **_: {
            "as_of_session": "2026-08-28",
            "universe_ids": list(PUBLIC_UNIVERSE_ORDER),
            "logical_content_fingerprint": "1" * 64,
            "composite_fingerprints": ["2" * 64, "3" * 64],
            "oracle_mismatch_count": 0,
        },
    )
    sector_product = SimpleNamespace(logical_fingerprint="4" * 64)
    sector_oracle = SimpleNamespace(mismatch_count=0)
    monkeypatch.setattr(
        cli,
        "calculate_sector_etf_rotation",
        lambda *, panel: calls.append(("sector", panel)) or sector_product,
    )
    monkeypatch.setattr(
        cli,
        "compare_with_independent_sector_rotation_oracle",
        lambda *, panel, product: (
            calls.append(("sector_oracle", panel)) or sector_oracle
        ),
    )

    def write_sector(**kwargs):
        calls.append(("sector_audit", kwargs["panel"]))
        assert kwargs["phase1a_audit_dir"] == phase_output
        assert kwargs["output_dir"] == sector_output
        assert kwargs["product"] is sector_product
        assert kwargs["oracle_report"] is sector_oracle
        assert set(kwargs["timings"]) == {
            "calculation_seconds",
            "oracle_seconds",
        }
        return {
            "logical_content_fingerprint": "5" * 64,
            "product_logical_fingerprint": "4" * 64,
            "oracle_mismatch_count": 0,
        }

    monkeypatch.setattr(cli, "write_sector_etf_rotation_audit", write_sector)

    result = cli.main(
        [
            "--as-of-session",
            "2026-08-28",
            "--universe-id",
            PUBLIC_UNIVERSE_ORDER[0],
            "--universe-id",
            PUBLIC_UNIVERSE_ORDER[1],
            "--data-root",
            "/data/trading-intelligence-platform",
            "--output-dir",
            str(phase_output),
            "--sector-rotation-output-dir",
            str(sector_output),
        ]
    )

    assert result == 0
    assert [name for name, _ in calls].count("load") == 1
    assert all(value is panel for _, value in calls)
    assert "\"source_panel_load_count\":1" in capsys.readouterr().out
