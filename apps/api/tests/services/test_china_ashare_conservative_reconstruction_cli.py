from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from tip_api.services import china_ashare_conservative_reconstruction_cli as cli


def test_reread_cli_reports_all_authority_closed(monkeypatch, capsys) -> None:
    census = SimpleNamespace(
        logical_fingerprint="2" * 64,
        candidate_set_fingerprint="3" * 64,
        state_count=5,
        provisional_candidate_included_state_count=2,
        provisional_candidate_excluded_state_count=1,
        provisional_quarantined_state_count=2,
        official_request_budget_by_priority=(),
        maximum_official_request_count=0,
        avoided_request_count=25,
    )
    result = SimpleNamespace(
        status="exact_reread_complete",
        package_path=Path("/tmp/package"),
        manifest=SimpleNamespace(logical_fingerprint="1" * 64),
        manifest_physical_sha256="4" * 64,
        plan=SimpleNamespace(logical_fingerprint="5" * 64),
        census=census,
        partition_manifests=tuple(range(109)),
    )
    monkeypatch.setattr(
        cli, "read_china_ashare_conservative_reconstruction_package",
        lambda **_: result,
    )
    monkeypatch.setattr(
        sys, "argv", ["conservative-reconstruction", "reread", "--package", "/tmp/package"]
    )

    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["partition_count"] == 109
    assert payload["as_operated"] is False
    assert payload["research_authorized"] is False
    assert payload["return_construction_authorized"] is False
    assert payload["historical_coverage_authorized"] is False
    assert payload["research_backtest_authorized"] is False
