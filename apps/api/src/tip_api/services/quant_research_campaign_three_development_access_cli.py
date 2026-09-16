"""Network-disabled typed access workflow for Campaign Three Development."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    build_campaign_three_development_access_request,
    expected_campaign_three_authorization_phrase,
    grant_campaign_three_development_access,
)
from tip_api.persistence.quant_research_campaign_three_development_access import (
    read_campaign_three_development_access_request,
    write_campaign_three_development_access_grant,
    write_campaign_three_development_access_request,
)
from tip_api.services.quant_research_factor_screening_v2_cli import (
    _validate_repository_revision,
)
from tip_api.services.strong_leader_pullback_development_dataset_cli import (
    _safe_error_detail,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
)


class CampaignThreeDevelopmentAccessCliError(RuntimeError):
    """Raised when the typed Campaign Three access workflow differs."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create one Campaign Three Development request or exact grant."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    request_parser = subparsers.add_parser("request")
    request_parser.add_argument("--implementation-revision", required=True)
    request_parser.add_argument("--output-root", type=Path, required=True)
    request_parser.add_argument("--output-custody-root", type=Path, required=True)
    grant_parser = subparsers.add_parser("grant")
    grant_parser.add_argument("--implementation-revision", required=True)
    grant_parser.add_argument("--request-root", type=Path, required=True)
    grant_parser.add_argument("--request-custody-root", type=Path, required=True)
    grant_parser.add_argument("--output-root", type=Path, required=True)
    grant_parser.add_argument("--output-custody-root", type=Path, required=True)
    grant_parser.add_argument("--authorization-phrase", required=True)
    grant_parser.add_argument("--granted-at", type=_datetime, required=True)
    args = parser.parse_args(argv)
    try:
        with _network_disabled():
            _validate_repository_revision(args.implementation_revision)
            if args.command == "request":
                request = build_campaign_three_development_access_request(
                    implementation_revision=args.implementation_revision,
                    implementation_tree_clean=True,
                )
                path, sha256, status = (
                    write_campaign_three_development_access_request(
                        output_root=args.output_root,
                        output_custody_root=args.output_custody_root,
                        request=request,
                    )
                )
                output = {
                    "status": status,
                    "request_path": str(path),
                    "request_sha256": sha256,
                    "request_fingerprint": request.logical_fingerprint,
                    "exact_authorization_phrase": (
                        expected_campaign_three_authorization_phrase(request)
                    ),
                    "development_outcome_access_authorized": False,
                }
            else:
                request, _ = read_campaign_three_development_access_request(
                    output_root=args.request_root,
                    output_custody_root=args.request_custody_root,
                )
                if request.implementation_revision != args.implementation_revision:
                    raise CampaignThreeDevelopmentAccessCliError(
                        "Campaign Three access request revision differs"
                    )
                grant = grant_campaign_three_development_access(
                    request=request,
                    authorization_phrase=args.authorization_phrase,
                    granted_at=args.granted_at,
                )
                path, sha256, status = write_campaign_three_development_access_grant(
                    output_root=args.output_root,
                    output_custody_root=args.output_custody_root,
                    request=request,
                    grant=grant,
                )
                output = {
                    "status": status,
                    "grant_path": str(path),
                    "grant_sha256": sha256,
                    "grant_fingerprint": grant.logical_fingerprint,
                    "authorized_execution_count": grant.total_execution_count,
                    "validation_access_authorized": False,
                    "holdout_access_authorized": False,
                }
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "campaign_three_development_access_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": _safe_error_detail(exc),
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


def _datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware")
    return parsed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
