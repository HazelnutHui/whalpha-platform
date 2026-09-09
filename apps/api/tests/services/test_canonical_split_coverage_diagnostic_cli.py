from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tip_api.services import canonical_split_coverage_diagnostic_cli as cli


def _report() -> SimpleNamespace:
    flags = tuple(
        SimpleNamespace(as_dict=lambda index=index: {"index": index})
        for index in range(3)
    )
    payload = {
        "contract_version": "canonical-split-coverage-diagnostic/1.0",
        "flag_count": 3,
    }
    return SimpleNamespace(
        flags=flags,
        as_dict=lambda *, include_flags: dict(payload),
    )


def test_cli_emits_bounded_flags(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "diagnose_canonical_split_coverage",
        lambda **_kwargs: _report(),
    )

    exit_code = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--canonical-action-publication-root",
            "/data/trading-intelligence-platform/action",
            "--eod-evidence-path",
            "/data/trading-intelligence-platform/eod/manifest.json",
            "--source-revision",
            "8" * 40,
            "--calculated-at",
            datetime(2026, 9, 9, tzinfo=UTC).isoformat(),
            "--maximum-output-flags",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["output_flag_count"] == 2
    assert payload["output_flags_truncated"] is True
    assert payload["flags"] == [{"index": 0}, {"index": 1}]


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    def reject(**_kwargs):
        raise RuntimeError("sensitive detail")

    monkeypatch.setattr(cli, "diagnose_canonical_split_coverage", reject)

    exit_code = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--canonical-action-publication-root",
            "/data/trading-intelligence-platform/action",
            "--eod-evidence-path",
            "/data/trading-intelligence-platform/eod/manifest.json",
            "--source-revision",
            "8" * 40,
            "--calculated-at",
            datetime(2026, 9, 9, tzinfo=UTC).isoformat(),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 1
    assert payload["status"] == "rejected"
    assert payload["external_request_count"] == 0
    assert payload["filesystem_write_count"] == 0
    assert "sensitive detail" not in output


def test_cli_rejects_unbounded_output() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--maximum-output-flags", "1001"])
