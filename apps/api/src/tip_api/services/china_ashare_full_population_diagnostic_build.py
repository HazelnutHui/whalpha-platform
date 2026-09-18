"""Build and independently replay the bounded A-share population diagnostic."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationPartitionAggregateV1,
)
from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    ChinaAshareNormalizedExpansionPartitionManifestV1,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    ChinaAshareFullPopulationDiagnosticAggregateResultV1,
    ChinaAshareFullPopulationDiagnosticPlanResultV1,
    publish_china_ashare_full_population_diagnostic_aggregate,
    publish_china_ashare_full_population_diagnostic_plan,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    read_china_ashare_normalized_expansion_partition,
)
from tip_api.persistence.china_ashare_population_package import (
    read_china_ashare_population_package,
)
from tip_api.persistence.china_ashare_source_expansion_completion import (
    read_china_ashare_source_expansion_completion,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    read_china_ashare_source_expansion_partition,
    read_china_ashare_source_expansion_plan,
)
from tip_api.services.china_ashare_full_population_coverage import (
    aggregate_china_ashare_normalized_partition,
    merge_china_ashare_partition_aggregates,
    plan_china_ashare_full_population_diagnostic,
)


class ChinaAshareFullPopulationDiagnosticBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationDiagnosticBuildResultV1:
    plan_result: ChinaAshareFullPopulationDiagnosticPlanResultV1
    aggregate_result: ChinaAshareFullPopulationDiagnosticAggregateResultV1
    target_session_count: int
    partition_count: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationDiagnosticReplayResultV1:
    primary: ChinaAshareFullPopulationDiagnosticBuildResultV1
    replay: ChinaAshareFullPopulationDiagnosticBuildResultV1
    byte_identical: bool
    physical_hashes_identical: bool
    primary_file_sha256s: tuple[tuple[str, str], ...]
    replay_file_sha256s: tuple[tuple[str, str], ...]


def build_china_ashare_full_population_diagnostic(
    *,
    population_package_path: Path,
    source_plan_root: Path,
    source_completion_package: Path,
    normalized_custody_root: Path,
    output_custody_root: Path,
) -> ChinaAshareFullPopulationDiagnosticBuildResultV1:
    """Exact-read one partition at a time and publish only bounded documents."""

    population = read_china_ashare_population_package(
        package_path=population_package_path
    )
    source_plan = read_china_ashare_source_expansion_plan(plan_root=source_plan_root)
    completion = read_china_ashare_source_expansion_completion(
        package_path=source_completion_package
    )
    if completion.report.partition_count != len(source_plan.plan.partitions):
        raise ChinaAshareFullPopulationDiagnosticBuildError(
            "source completion partition count differs from source plan"
        )

    manifests: list[ChinaAshareNormalizedExpansionPartitionManifestV1] = []
    aggregates: list[ChinaAshareFullPopulationPartitionAggregateV1] = []
    observed_sessions: set[date] = set()
    for partition_index in range(completion.report.partition_count):
        manifest, aggregate, sessions = _read_and_aggregate_partition(
            partition_index=partition_index,
            normalized_custody_root=normalized_custody_root,
            population=population,
            source_plan=source_plan,
        )
        manifests.append(manifest)
        aggregates.append(aggregate)
        observed_sessions.update(sessions)
    if not observed_sessions:
        raise ChinaAshareFullPopulationDiagnosticBuildError(
            "normalized diagnostic contains no observed sessions"
        )

    plan = plan_china_ashare_full_population_diagnostic(
        population_package=population,
        source_plan=source_plan,
        source_completion=completion,
        normalized_manifests=tuple(manifests),
        target_session_count=len(observed_sessions),
        registered_at=completion.report.evaluated_at,
    )
    partition_aggregates = tuple(aggregates)
    streaming = merge_china_ashare_partition_aggregates(
        plan=plan,
        partitions=partition_aggregates,
    )
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=output_custody_root,
        plan=plan,
    )
    aggregate_result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=output_custody_root,
        plan_result=plan_result,
        partitions=partition_aggregates,
        streaming=streaming,
    )
    return ChinaAshareFullPopulationDiagnosticBuildResultV1(
        plan_result=plan_result,
        aggregate_result=aggregate_result,
        target_session_count=len(observed_sessions),
        partition_count=len(partition_aggregates),
        total_bytes=plan_result.total_bytes + aggregate_result.total_bytes,
    )


def build_and_replay_china_ashare_full_population_diagnostic(
    *,
    population_package_path: Path,
    source_plan_root: Path,
    source_completion_package: Path,
    normalized_custody_root: Path,
    output_custody_root: Path,
    replay_custody_root: Path,
) -> ChinaAshareFullPopulationDiagnosticReplayResultV1:
    primary_root = output_custody_root.expanduser().resolve()
    replay_root = replay_custody_root.expanduser().resolve()
    if primary_root == replay_root:
        raise ChinaAshareFullPopulationDiagnosticBuildError(
            "replay custody must be independent from primary custody"
        )
    inputs = {
        "population_package_path": population_package_path,
        "source_plan_root": source_plan_root,
        "source_completion_package": source_completion_package,
        "normalized_custody_root": normalized_custody_root,
    }
    primary = build_china_ashare_full_population_diagnostic(
        **inputs,
        output_custody_root=output_custody_root,
    )
    replay = build_china_ashare_full_population_diagnostic(
        **inputs,
        output_custody_root=replay_custody_root,
    )
    primary_files = _package_files(primary)
    replay_files = _package_files(replay)
    primary_hashes = _physical_hashes(primary_files)
    replay_hashes = _physical_hashes(replay_files)
    if primary_files != replay_files or primary_hashes != replay_hashes:
        raise ChinaAshareFullPopulationDiagnosticBuildError(
            "independent diagnostic replay differs from primary custody"
        )
    return ChinaAshareFullPopulationDiagnosticReplayResultV1(
        primary=primary,
        replay=replay,
        byte_identical=True,
        physical_hashes_identical=True,
        primary_file_sha256s=primary_hashes,
        replay_file_sha256s=replay_hashes,
    )


def _read_and_aggregate_partition(
    *, partition_index: int, normalized_custody_root: Path, population, source_plan
) -> tuple[
    ChinaAshareNormalizedExpansionPartitionManifestV1,
    ChinaAshareFullPopulationPartitionAggregateV1,
    frozenset[date],
]:
    """Keep raw and normalized row objects inside one partition-local frame."""

    source_partition = read_china_ashare_source_expansion_partition(
        plan_result=source_plan,
        partition_index=partition_index,
    )
    normalized_partition = read_china_ashare_normalized_expansion_partition(
        custody_root=normalized_custody_root,
        population_package=population,
        plan_result=source_plan,
        source_partition=source_partition,
    )
    aggregate = aggregate_china_ashare_normalized_partition(
        partition=normalized_partition
    )
    sessions = frozenset(
        item.session_date for item in normalized_partition.normalized.states
    )
    return normalized_partition.manifest, aggregate, sessions


def _package_files(
    result: ChinaAshareFullPopulationDiagnosticBuildResultV1,
) -> tuple[tuple[str, bytes], ...]:
    roots = (
        ("plan", result.plan_result.package_path),
        ("aggregate", result.aggregate_result.package_path),
    )
    return tuple(
        (f"{label}/{item.relative_to(root).as_posix()}", item.read_bytes())
        for label, root in roots
        for item in sorted(root.rglob("*"))
        if item.is_file() and not item.is_symlink()
    )


def _physical_hashes(
    files: tuple[tuple[str, bytes], ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (relative_path, hashlib.sha256(payload).hexdigest())
        for relative_path, payload in files
    )
