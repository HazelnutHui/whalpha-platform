"""Thin CLI for bounded A-share diagnostic plan and aggregate custody."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationDiagnosticPlanV1,
    ChinaAshareFullPopulationPartitionAggregateV1,
    ChinaAshareFullPopulationStreamingAggregateV1,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    MAXIMUM_FILE_BYTES,
    publish_china_ashare_full_population_diagnostic_aggregate,
    publish_china_ashare_full_population_diagnostic_plan,
    read_china_ashare_full_population_diagnostic_aggregate,
    read_china_ashare_full_population_diagnostic_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("publish-plan")
    plan.add_argument("--plan-json", type=Path, required=True)
    plan.add_argument("--custody-root", type=Path, required=True)

    aggregate = commands.add_parser("publish-aggregate")
    aggregate.add_argument("--plan-package", type=Path, required=True)
    aggregate.add_argument("--partition-aggregates-json", type=Path, required=True)
    aggregate.add_argument("--streaming-aggregate-json", type=Path, required=True)
    aggregate.add_argument("--custody-root", type=Path, required=True)

    reread = commands.add_parser("reread-aggregate")
    reread.add_argument("--plan-package", type=Path, required=True)
    reread.add_argument("--aggregate-package", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "publish-plan":
        typed_plan = ChinaAshareFullPopulationDiagnosticPlanV1.model_validate_json(
            _read(args.plan_json)
        )
        result = publish_china_ashare_full_population_diagnostic_plan(
            custody_root=args.custody_root,
            plan=typed_plan,
        )
        _emit(
            status=result.status,
            package_path=result.package_path,
            plan_fingerprint=result.plan.logical_fingerprint,
            partition_count=len(
                result.plan.normalized_partition_manifest_fingerprints
            ),
        )
        return 0

    plan_result = read_china_ashare_full_population_diagnostic_plan(
        package_path=args.plan_package
    )
    if args.command == "publish-aggregate":
        partitions = _partition_aggregates(args.partition_aggregates_json)
        streaming = ChinaAshareFullPopulationStreamingAggregateV1.model_validate_json(
            _read(args.streaming_aggregate_json)
        )
        result = publish_china_ashare_full_population_diagnostic_aggregate(
            custody_root=args.custody_root,
            plan_result=plan_result,
            partitions=partitions,
            streaming=streaming,
        )
    else:
        result = read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=args.aggregate_package,
        )
    _emit(
        status=result.status,
        package_path=result.package_path,
        plan_fingerprint=result.plan.logical_fingerprint,
        partition_count=len(result.partitions),
        streaming_aggregate_fingerprint=result.streaming.logical_fingerprint,
    )
    return 0


def _partition_aggregates(
    path: Path,
) -> tuple[ChinaAshareFullPopulationPartitionAggregateV1, ...]:
    try:
        document = json.loads(_read(path))
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != "1.0"
            or not isinstance(document.get("rows"), list)
        ):
            raise ValueError("partition aggregate document shape differs")
        return tuple(
            ChinaAshareFullPopulationPartitionAggregateV1.model_validate(item)
            for item in document["rows"]
        )
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("partition aggregate input is invalid") from exc


def _read(path: Path) -> bytes:
    candidate = path.expanduser()
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("diagnostic CLI input is absent or unsafe")
    size = candidate.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ValueError("diagnostic CLI input size is invalid")
    return candidate.read_bytes()


def _emit(**values: object) -> None:
    payload = {
        **{
            key: str(value) if isinstance(value, Path) else value
            for key, value in values.items()
        },
        "future_return_read_count": 0,
        "full_universe_rows_materialized": False,
        "research_backtest_authorized": False,
        "canonical_apply_authorized": False,
        "product_publication_authorized": False,
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
