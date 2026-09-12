from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import reconciled_eod_edition_batch_cli as cli


ARGS = [
    "--data-root",
    "/data/trading-intelligence-platform",
    "--coverage-path",
    "/tmp/source-coverage.json",
    "--coverage-file-sha256",
    "a" * 64,
    "--candidate-root",
    "/tmp/candidate",
    "--edition-id",
    "massive-exact-symbol-v1",
    "--implementation-revision",
    "b" * 40,
    "--created-at",
    "2026-09-11T01:00:00+00:00",
    "--session",
    "2026-09-09",
]


def test_cli_requires_explicit_execute(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "read_reconciled_eod_source_coverage",
        lambda **_values: pytest.fail("coverage must not be read"),
    )

    with pytest.raises(SystemExit):
        cli.main(ARGS)


def test_cli_binds_coverage_and_emits_noncanonical_result(
    monkeypatch,
    capsys,
) -> None:
    observed: dict[str, object] = {}
    coverage = object()
    sources = (object(),)
    monkeypatch.setattr(
        cli,
        "read_reconciled_eod_source_coverage",
        lambda **_values: SimpleNamespace(coverage=coverage),
    )

    def resolve(**values):
        observed["coverage"] = values["coverage"]
        observed["session_dates"] = values["session_dates"]
        return sources

    monkeypatch.setattr(cli, "resolve_reconciled_eod_batch_sources", resolve)
    result = SimpleNamespace(
        status="batch_complete",
        edition_id="massive-exact-symbol-v1",
        implementation_revision="b" * 40,
        requested_session_count=1,
        worker_count=1,
        published_session_count=1,
        reused_session_count=0,
        failed_session_count=0,
        record_count=10,
        added_record_count=1,
        absent_record_count=0,
        provenance_only_change_count=0,
        external_request_count=0,
        canonical_data_write_count=0,
        candidate_session_write_count=1,
        interval_manifest_write_count=0,
        candidate_authority=False,
        production_authority=False,
        research_performance_authorized=False,
        sessions=(
            SimpleNamespace(
                session_date="2026-09-09",
                status="published",
                failure_code="none",
                absent_record_count=0,
                provenance_only_change_count=0,
                manifest_fingerprint="c" * 64,
            ),
        ),
    )

    def run(**values):
        observed["sources"] = values["sources"]
        return result

    monkeypatch.setattr(cli, "run_reconciled_eod_edition_batch", run)

    assert cli.main([*ARGS, "--execute"]) == 0
    output = capsys.readouterr().out
    assert observed["coverage"] is coverage
    assert observed["sources"] is sources
    assert '"canonical_data_write_count": 0' in output
    assert '"interval_manifest_write_count": 0' in output
