from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import historical_inactive_lifecycle_resolution_shadow_cli as cli


def test_cli_passes_bounded_worker_count(monkeypatch, capsys) -> None:
    observed = {}
    manifest = SimpleNamespace(
        contract_version="historical-inactive-lifecycle-resolution-shadow/1.0",
        anchor_date=SimpleNamespace(isoformat=lambda: "2026-09-03"),
        source_package_record_count=23469,
        canonical_history_session_count=1249,
        canonical_history_unique_instrument_count=15000,
        disposition_counts=(("quarantined", 20000), ("review_candidate", 3469)),
        resolution_status_counts=(("resolved", 4000), ("unresolved", 19469)),
        reason_counts=(("missing_stable_security_identifier", 19000),),
        logical_fingerprint="a" * 64,
    )

    def build(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            manifest=manifest,
            manifest_sha256="b" * 64,
            status="published",
        )

    monkeypatch.setattr(cli, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        cli,
        "build_historical_inactive_lifecycle_resolution_shadow",
        build,
    )

    exit_code = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--source-package",
            "/source/anchor=2026-09-03",
            "--source-custody-root",
            "/source",
            "--output-root",
            "/tmp/output",
            "--anchor-date",
            "2026-09-03",
            "--materialized-at",
            "2026-09-12T23:15:00+00:00",
            "--workers",
            "6",
            "--execute",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert observed["max_workers"] == 6
    assert payload["canonical_history_session_count"] == 1249
    assert payload["canonical_data_write_count"] == 0
