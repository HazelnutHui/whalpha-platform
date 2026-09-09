"""CLI for the read-only canonical cash-dividend candidate diagnostic."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tip_api.services.canonical_cash_dividend_candidate_diagnostic import (
    diagnose_canonical_cash_dividend_candidates,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify bounded cash-dividend arithmetic candidates without "
            "writing canonical actions or adjustments."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--source-publication-path", required=True, type=Path)
    parser.add_argument("--eod-evidence-path", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--calculated-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--maximum-output-flags", type=int, default=100)
    args = parser.parse_args(argv)
    if not 0 <= args.maximum_output_flags <= 1_000:
        parser.error("--maximum-output-flags must be between 0 and 1000")
    try:
        report = diagnose_canonical_cash_dividend_candidates(
            data_root=args.data_root,
            source_publication_path=args.source_publication_path,
            eod_evidence_path=args.eod_evidence_path,
            source_revision=args.source_revision,
            calculated_at=args.calculated_at,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": (
                        "canonical_cash_dividend_candidate_diagnostic_rejected"
                    ),
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "filesystem_write_count": 0,
                    "canonical_data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    payload = report.as_dict(include_flags=False)
    payload["status"] = "completed"
    payload["review_flags"] = [
        item.as_dict()
        for item in report.review_flags[: args.maximum_output_flags]
    ]
    payload["output_flag_count"] = len(payload["review_flags"])
    payload["output_flags_truncated"] = (
        len(report.review_flags) > len(payload["review_flags"])
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
