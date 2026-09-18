"""One-partition-at-a-time build and independent replay of conservative candidates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from tip_api.persistence.china_ashare_cninfo_event_evidence import (
    read_cninfo_event_capture,
    read_cninfo_event_plan,
)
from tip_api.persistence.china_ashare_conservative_reconstruction_package import (
    ChinaAshareConservativeReconstructionPackageResultV1,
    publish_china_ashare_conservative_reconstruction_package,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    read_china_ashare_full_population_diagnostic_plan,
)
from tip_api.persistence.china_ashare_market_mechanics_package import (
    read_china_ashare_market_mechanics_package,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    read_china_ashare_normalized_expansion_partition,
)
from tip_api.persistence.china_ashare_population_package import (
    read_china_ashare_population_package,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    read_china_ashare_source_expansion_partition,
    read_china_ashare_source_expansion_plan,
)
from tip_api.services.china_ashare_conservative_reconstruction_census import (
    build_conservative_universe_partition_rows,
    build_sz000001_price_limit_smoke,
    merge_conservative_reconstruction_census,
    plan_conservative_reconstruction_census,
    scan_conservative_reconstruction_partition,
)
from tip_api.services.china_ashare_cninfo_event_evidence import replay_cninfo_capture
from tip_api.services.china_ashare_price_limit_resolver import (
    plan_china_ashare_price_limit_resolver,
)


class ChinaAshareConservativeReconstructionBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareConservativeReconstructionReplayResultV1:
    primary: ChinaAshareConservativeReconstructionPackageResultV1
    replay: ChinaAshareConservativeReconstructionPackageResultV1
    byte_identical: bool
    physical_hashes_identical: bool
    physical_sha256s: tuple[tuple[str, str], ...]


def build_china_ashare_conservative_reconstruction(
    *, population_package_path: Path, source_plan_root: Path,
    diagnostic_plan_package: Path, normalized_custody_root: Path,
    market_mechanics_package: Path, cninfo_plan_root: Path,
    output_custody_root: Path,
) -> ChinaAshareConservativeReconstructionPackageResultV1:
    population = read_china_ashare_population_package(
        package_path=population_package_path
    )
    source_plan = read_china_ashare_source_expansion_plan(plan_root=source_plan_root)
    diagnostic_plan = read_china_ashare_full_population_diagnostic_plan(
        package_path=diagnostic_plan_package
    )
    mechanics = read_china_ashare_market_mechanics_package(
        package_path=market_mechanics_package
    )
    cninfo_plan = read_cninfo_event_plan(plan_root=cninfo_plan_root)
    cninfo_captures = []
    for query in cninfo_plan.queries:
        capture, raw = read_cninfo_event_capture(
            plan_root=cninfo_plan_root, query_id=query.query_id
        )
        if raw is None:
            raise ChinaAshareConservativeReconstructionBuildError(
                "CNINFO exact replay requires captured official bytes"
            )
        cninfo_captures.append(replay_cninfo_capture(
            plan=cninfo_plan, query=query, capture=capture, raw=raw
        ))
    cninfo_captures = tuple(cninfo_captures)
    resolver_plan = plan_china_ashare_price_limit_resolver(mechanics=mechanics)
    occurrences = {
        item.logical_fingerprint: item for item in population.occurrences
    }
    source_zero, normalized_zero = _read_partition(
        index=0, source_plan=source_plan, population=population,
        normalized_custody_root=normalized_custody_root,
    )
    target_sessions = tuple(sorted({
        item.session_date for item in normalized_zero.normalized.states
    }))
    if len(target_sessions) != diagnostic_plan.plan.target_session_count:
        raise ChinaAshareConservativeReconstructionBuildError(
            "partition zero does not prove the diagnostic session set"
        )
    plan = plan_conservative_reconstruction_census(
        source_plan=source_plan,
        population=population,
        diagnostic_plan=diagnostic_plan,
        mechanics=mechanics,
        price_limit_resolver_plan=resolver_plan,
        cninfo_plan=cninfo_plan,
        cninfo_replay_captures=cninfo_captures,
        target_sessions=target_sessions,
    )
    source_smoke, normalized_smoke = _read_partition(
        index=47, source_plan=source_plan, population=population,
        normalized_custody_root=normalized_custody_root,
    )
    smoke = build_sz000001_price_limit_smoke(
        plan=plan,
        cninfo_plan=cninfo_plan,
        cninfo_replay_captures=cninfo_captures,
        source_partition=source_smoke,
        normalized_partition=normalized_smoke,
        mechanics=mechanics,
        price_limit_resolver_plan=resolver_plan,
    )
    partition_censuses = []
    for index in range(109):
        source_partition, normalized_partition = (
            (source_zero, normalized_zero)
            if index == 0
            else _read_partition(
                index=index, source_plan=source_plan, population=population,
                normalized_custody_root=normalized_custody_root,
            )
        )
        observed_sessions = {item.session_date for item in normalized_partition.normalized.states}
        if not observed_sessions <= set(target_sessions):
            raise ChinaAshareConservativeReconstructionBuildError(
                "normalized partition session set differs"
            )
        partition_censuses.append(scan_conservative_reconstruction_partition(
            plan=plan,
            source_partition=source_partition,
            normalized_partition=normalized_partition,
            population_occurrences_by_fingerprint=occurrences,
        ))
        del source_partition, normalized_partition
    census = merge_conservative_reconstruction_census(
        plan=plan, partitions=tuple(partition_censuses)
    )

    def payloads():
        for index, partition_census in enumerate(partition_censuses):
            source_partition, normalized_partition = _read_partition(
                index=index, source_plan=source_plan, population=population,
                normalized_custody_root=normalized_custody_root,
            )
            rows = build_conservative_universe_partition_rows(
                plan=plan,
                partition_census=partition_census,
                source_partition=source_partition,
                normalized_partition=normalized_partition,
                population_occurrences_by_fingerprint=occurrences,
            )
            yield partition_census, rows
            del source_partition, normalized_partition, rows

    return publish_china_ashare_conservative_reconstruction_package(
        custody_root=output_custody_root,
        plan=plan,
        census=census,
        smoke=smoke,
        partition_payloads=payloads(),
    )


def build_and_replay_china_ashare_conservative_reconstruction(
    *, replay_custody_root: Path, **values,
) -> ChinaAshareConservativeReconstructionReplayResultV1:
    primary_root = Path(values["output_custody_root"]).expanduser().resolve()
    replay_root = replay_custody_root.expanduser().resolve()
    if primary_root == replay_root:
        raise ChinaAshareConservativeReconstructionBuildError(
            "independent replay custody must differ"
        )
    primary = build_china_ashare_conservative_reconstruction(**values)
    replay = build_china_ashare_conservative_reconstruction(
        **{**values, "output_custody_root": replay_custody_root}
    )
    primary_files = _files(primary.package_path)
    replay_files = _files(replay.package_path)
    if primary_files != replay_files:
        raise ChinaAshareConservativeReconstructionBuildError(
            "independent conservative reconstruction replay differs"
        )
    hashes = tuple(
        (name, hashlib.sha256(payload).hexdigest())
        for name, payload in primary_files
    )
    return ChinaAshareConservativeReconstructionReplayResultV1(
        primary=primary,
        replay=replay,
        byte_identical=True,
        physical_hashes_identical=True,
        physical_sha256s=hashes,
    )


def _read_partition(*, index, source_plan, population, normalized_custody_root):
    source = read_china_ashare_source_expansion_partition(
        plan_result=source_plan, partition_index=index
    )
    normalized = read_china_ashare_normalized_expansion_partition(
        custody_root=normalized_custody_root,
        population_package=population,
        plan_result=source_plan,
        source_partition=source,
    )
    return source, normalized


def _files(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (item.relative_to(root).as_posix(), item.read_bytes())
        for item in sorted(root.rglob("*"))
        if item.is_file() and not item.is_symlink()
    )
