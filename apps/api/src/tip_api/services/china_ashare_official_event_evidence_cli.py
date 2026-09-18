"""Restartable bounded CLI for partition-0 official-event evidence."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_official_event_evidence import (
    completed_official_event_query_ids,
    publish_official_event_capture,
    publish_official_event_evidence_plan,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    read_china_ashare_source_expansion_partition,
    read_china_ashare_source_expansion_plan,
)
from tip_api.services.china_ashare_official_event_evidence import (
    capture_official_event_query,
    plan_partition0_official_event_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-plan-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--maximum-new-queries", type=int, default=1)
    parser.add_argument("--minimum-request-interval-milliseconds", type=int, default=1000)
    args = parser.parse_args()
    if not 0 <= args.maximum_new_queries <= 251:
        parser.error("--maximum-new-queries must be from 0 through 251")
    source_plan = read_china_ashare_source_expansion_plan(plan_root=args.source_plan_root)
    source_partition = read_china_ashare_source_expansion_partition(
        plan_result=source_plan, partition_index=0
    )
    plan = plan_partition0_official_event_evidence(
        source_plan=source_plan,
        source_partition=source_partition,
        minimum_request_interval_milliseconds=(
            args.minimum_request_interval_milliseconds
        ),
    )
    plan_root = publish_official_event_evidence_plan(
        custody_root=args.custody_root, plan=plan
    )
    completed_before = set(completed_official_event_query_ids(plan_root=plan_root))
    pending = tuple(item for item in plan.queries if item.query_id not in completed_before)
    selected = pending if args.maximum_new_queries == 0 else pending[: args.maximum_new_queries]
    captured = 0
    blocked = 0
    announcements = 0
    for index, query in enumerate(selected):
        if index:
            time.sleep(plan.minimum_request_interval_milliseconds / 1000)
        capture, raw = capture_official_event_query(
            plan=plan, query=query, retrieved_at=datetime.now(UTC)
        )
        publish_official_event_capture(
            plan_root=plan_root, capture=capture, raw_bytes=raw
        )
        captured += raw is not None
        blocked += capture.blocker_code is not None
        announcements += len(capture.announcements)
        print(
            json.dumps(
                {
                    "event": "official_event_query_checkpoint",
                    "query_id": query.query_id,
                    "parse_status": capture.parse_status.value,
                    "raw_sha256": capture.raw_sha256,
                    "announcement_count": len(capture.announcements),
                    "blocker_code": capture.blocker_code,
                    "capture_fingerprint": capture.logical_fingerprint,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    completed_after = completed_official_event_query_ids(plan_root=plan_root)
    print(
        json.dumps(
            {
                "event": "official_event_evidence_checkpoint",
                "plan_fingerprint": plan.logical_fingerprint,
                "plan_root": str(plan_root),
                "target_count": len(plan.target_source_security_ids),
                "query_count": len(plan.queries),
                "completed_query_count": len(completed_after),
                "remaining_query_count": len(plan.queries) - len(completed_after),
                "new_raw_capture_count": captured,
                "new_blocker_count": blocked,
                "new_announcement_count": announcements,
                "outcome_read_count": 0,
                "as_operated_claim_authorized": False,
                "research_backtest_authorized": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
