from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from tip_api.services import reconciled_eod_source_coverage_cli as cli


def test_cli_writes_bounded_coverage_summary(monkeypatch, capsys) -> None:
    observed: dict[str, object] = {}
    coverage = SimpleNamespace(
        status="incomplete",
        logical_fingerprint="a" * 64,
        evaluation_first_session=date(2021, 9, 9),
        evaluation_last_session=date(2026, 9, 9),
        warmup_first_session=date(2021, 8, 11),
        warmup_last_session=date(2021, 9, 8),
        target_session_count=1275,
        retained_original_session_count=900,
        later_reacquisition_session_count=0,
        missing_session_count=353,
        invalid_session_count=2,
        conflict_session_count=0,
        external_request_count=0,
        canonical_data_write_count=0,
        candidate_session_write_count=0,
        source_selection_authorized=False,
        production_authority=False,
    )

    def assess(**values):
        observed.update(values)
        return coverage

    monkeypatch.setattr(cli, "assess_reconciled_eod_source_coverage", assess)
    monkeypatch.setattr(
        cli,
        "write_reconciled_eod_source_coverage",
        lambda **_values: SimpleNamespace(
            path=Path("/tmp/source-coverage.json"),
            file_sha256="b" * 64,
        ),
    )

    assert (
        cli.main(
            [
                "--data-root",
                "/data/trading-intelligence-platform",
                "--first-session",
                "2021-09-09",
                "--last-session",
                "2026-09-09",
                "--warmup-first-session",
                "2021-08-11",
                "--warmup-last-session",
                "2021-09-08",
                "--created-at",
                "2026-09-11T01:00:00+00:00",
                "--coverage-path",
                "/tmp/source-coverage.json",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert observed["evaluation_first_session"] == date(2021, 9, 9)
    assert observed["warmup_first_session"] == date(2021, 8, 11)
    assert observed["warmup_last_session"] == date(2021, 9, 8)
    assert observed["workers"] == 4
    assert '"missing_session_count": 353' in output
    assert '"canonical_data_write_count": 0' in output
    assert '"source_selection_authorized": false' in output
