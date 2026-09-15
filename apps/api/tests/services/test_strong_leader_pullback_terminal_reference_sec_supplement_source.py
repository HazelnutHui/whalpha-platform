from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_supplement_source as service,
)


def test_supplement_source_uses_only_supplement_plan_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = SimpleNamespace(status="published")
    captured: dict[str, object] = {}

    def acquire(**arguments: object) -> object:
        captured.update(arguments)
        return sentinel

    monkeypatch.setattr(
        service.base,
        "acquire_strong_leader_pullback_terminal_population_sec_source",
        acquire,
    )
    result = (
        service.acquire_strong_leader_pullback_terminal_reference_sec_supplement_source(
            plan_root=Path("/plan"),
            plan_custody_root=Path("/plans"),
            output_root=Path("/source"),
            output_custody_root=Path("/sources"),
            config=SimpleNamespace(),  # type: ignore[arg-type]
            implementation_revision="a" * 40,
        )
    )

    assert result is sentinel
    assert captured["plan_reader"] is (
        service.plan.read_strong_leader_pullback_terminal_reference_sec_supplement_plan
    )
