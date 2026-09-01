from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.services import daily_eod_scheduler_runtime_plan as runtime


REVISION = "a" * 40
PYTHON = Path("/usr/bin/python3.12")


def test_plan_is_exact_deterministic_and_grants_no_authority() -> None:
    first = runtime.build_daily_eod_scheduler_runtime_plan(
        implementation_revision=REVISION,
        expected_python_executable=PYTHON,
    )
    second = runtime.build_daily_eod_scheduler_runtime_plan(
        implementation_revision=REVISION,
        expected_python_executable=PYTHON,
    )

    assert first == second
    assert first.runtime_root.endswith(f"revision={REVISION}")
    assert first.checkout_mode == "detached_git_worktree"
    assert first.creation_command[-2:] == (first.runtime_root, REVISION)
    assert first.network_authorized is False
    assert first.credential_access_authorized is False
    assert first.data_read_authorized is False
    assert first.filesystem_write_authorized is False
    assert first.production_write_authorized is False
    assert first.systemd_change_authorized is False
    assert first.creation_performed is False
    assert first.installation_performed is False


@pytest.mark.parametrize(
    "revision",
    ["a" * 39, "A" * 40, "g" * 40, "main", "a" * 41],
)
def test_plan_rejects_non_exact_revision(revision: str) -> None:
    with pytest.raises(runtime.DailyEodSchedulerRuntimePlanError):
        runtime.build_daily_eod_scheduler_runtime_plan(
            implementation_revision=revision,
            expected_python_executable=PYTHON,
        )


def test_plan_rejects_relative_python_executable() -> None:
    with pytest.raises(runtime.DailyEodSchedulerRuntimePlanError):
        runtime.build_daily_eod_scheduler_runtime_plan(
            implementation_revision=REVISION,
            expected_python_executable=Path("python"),
        )


def test_tampered_plan_fails_closed() -> None:
    plan = runtime.build_daily_eod_scheduler_runtime_plan(
        implementation_revision=REVISION,
        expected_python_executable=PYTHON,
    )
    payload = plan.model_dump(mode="json")
    payload["runtime_root"] = "/tmp/runtime"

    with pytest.raises(ValueError, match="boundary is invalid"):
        runtime.DailyEodSchedulerRuntimePlanV1.model_validate(payload)
