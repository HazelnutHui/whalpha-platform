from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_daily_pipeline_administrator_scripts_use_worktree_safe_runner() -> None:
    expected_modules = {
        "ingest-massive-instrument-master.sh": (
            "tip_api.providers.massive.instrument_master_snapshot"
        ),
        "ingest-massive-grouped-daily.sh": "tip_api.providers.massive.grouped_daily_ingestion",
        "plan-daily-eod-automation.sh": "tip_api.services.daily_eod_automation_cli",
        "calculate-candidate-entry-geometry-offline.sh": (
            "tip_api.services.candidate_entry_geometry_cli"
        ),
        "execute-daily-eod-offline-action.sh": "tip_api.services.daily_eod_executor_cli",
        "plan-daily-eod-readiness.sh": "tip_api.services.daily_eod_readiness_cli",
    }
    for name, module in expected_modules.items():
        path = REPO_ROOT / "scripts" / "admin" / name
        source = path.read_text(encoding="utf-8")
        assert "scripts/dev/run-project-python.sh" in source
        assert module in source
        assert ".venv/bin/python" not in source
