"""Exact-plan CLI for the owner-only Massive Starter capability sample."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from tip_api.persistence.quant_research_massive_starter_capability_sample import (
    MassiveStarterCapabilitySampleCustodyError,
    publish_massive_starter_capability_sample,
)
from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport
from tip_api.services.quant_research_massive_starter_capability_sample import (
    execute_massive_starter_capability_sample,
    registered_massive_starter_capability_sample_plan_v1,
)


DEFAULT_CUSTODY_ROOT = Path(
    "~/.local/state/trading-intelligence-platform/quant-research/"
    "sec-cash-quality-source-engineering/build=20260918-v1/"
    "massive-starter-capability-sample-v1"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--acknowledgement")
    parser.add_argument("--custody-root", type=Path, default=DEFAULT_CUSTODY_ROOT)
    args = parser.parse_args(argv)
    if args.review == bool(args.acknowledgement):
        parser.error("choose exactly one of --review or --acknowledgement")
    plan = registered_massive_starter_capability_sample_plan_v1()
    required = f"I_AUTHORIZE_MASSIVE_STARTER_CAPABILITY_SAMPLE_{plan.logical_fingerprint}"
    if args.review:
        print(f"plan_fingerprint={plan.logical_fingerprint}")
        print(f"maximum_request_count={plan.maximum_request_count}")
        print("automatic_retry_count=0")
        print("raw_response_custody=owner_only_sanitized")
        print(f"required_acknowledgement={required}")
        return 0
    if args.acknowledgement != required:
        print("error=authorization-mismatch", file=sys.stderr)
        return 2
    try:
        execution = execute_massive_starter_capability_sample(
            plan=plan,
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            before_request=lambda sequence: time.sleep(0.25) if sequence > 1 else None,
        )
        package = publish_massive_starter_capability_sample(
            custody_root=args.custody_root,
            plan=plan,
            result=execution.result,
            sanitized_responses=dict(execution.sanitized_responses),
        )
    except (
        MassiveCredentialFileError,
        MassiveStarterCapabilitySampleCustodyError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error={type(exc).__name__}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": package.result.status.value,
                "request_count": package.result.request_count,
                "failed_request_sequence": package.result.failed_request_sequence,
                "plan_fingerprint": package.plan.logical_fingerprint,
                "result_fingerprint": package.result.logical_fingerprint,
                "verification_fingerprint": package.verification.logical_fingerprint,
                "package_path": str(package.package_path),
                "historical_lane_admitted_count": 0,
                "credential_value_retained": False,
                "credential_value_hashed": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
