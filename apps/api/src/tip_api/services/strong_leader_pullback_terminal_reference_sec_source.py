"""Private SEC custody wrapper for the five terminal-reference documents."""

from __future__ import annotations

from pathlib import Path

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source as base,
)
from tip_api.services import strong_leader_pullback_terminal_reference_sec_plan as plan


def acquire_strong_leader_pullback_terminal_reference_sec_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    config: SecProviderConfig,
    implementation_revision: str,
    transport_factory: base.TransportFactory | None = None,
    clock: base.Clock | None = None,
) -> base.StrongLeaderPullbackTerminalPopulationSecSourceResult:
    """Acquire only the frozen five-document plan into atomic custody."""

    return base.acquire_strong_leader_pullback_terminal_population_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=output_root,
        output_custody_root=output_custody_root,
        config=config,
        implementation_revision=implementation_revision,
        transport_factory=transport_factory,
        clock=clock,
        plan_reader=plan.read_strong_leader_pullback_terminal_reference_sec_plan,
    )


def read_strong_leader_pullback_terminal_reference_sec_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> base.StrongLeaderPullbackTerminalPopulationSecSourceResult:
    """Reread all five documents and their hashes without network access."""

    return base.read_strong_leader_pullback_terminal_population_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=output_root,
        output_custody_root=output_custody_root,
        plan_reader=plan.read_strong_leader_pullback_terminal_reference_sec_plan,
    )
