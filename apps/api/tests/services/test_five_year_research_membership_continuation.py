from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services.five_year_research_membership_continuation import (
    CONTRACT_VERSION,
    FiveYearResearchMembershipBatchV1,
    FiveYearResearchMembershipContinuationError,
    FiveYearResearchMembershipContinuationPlanV1,
    _contiguous_batches,
    _fingerprint,
    _read_plan,
    _write_plan,
)


def test_contiguous_batches_do_not_bridge_missing_or_covered_sessions() -> None:
    first = date(2026, 9, 1)
    target = tuple(first + timedelta(days=index) for index in range(12))
    intended = target[:6] + target[7:10] + target[11:]

    batches = _contiguous_batches(target, intended)

    assert tuple(item.session_dates for item in batches) == (
        target[:5],
        target[5:6],
        target[7:10],
        target[11:],
    )
    assert tuple(item.batch_id for item in batches) == (
        "batch-0001",
        "batch-0002",
        "batch-0003",
        "batch-0004",
    )


def test_plan_round_trip_is_owner_read_only_and_fingerprint_bound(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir(mode=0o700)
    batch = FiveYearResearchMembershipBatchV1(
        batch_id="batch-0001",
        session_dates=(date(2026, 9, 10), date(2026, 9, 11)),
    )
    payload = {
        "contract_version": CONTRACT_VERSION,
        "data_root": "/data/trading-intelligence-platform",
        "candidate_root": str(candidate),
        "code_revision": "a" * 40,
        "methodology_version": "provider-form-complete-base-point-in-time-v3",
        "catalog_as_of_date": date(2026, 8, 14),
        "evaluated_at": datetime(2026, 9, 13, 9, tzinfo=UTC),
        "target_first_session": date(2021, 9, 13),
        "target_last_session": date(2026, 9, 11),
        "target_session_count": 1255,
        "target_session_fingerprint": hashlib.sha256(b"target").hexdigest(),
        "initial_research_session_count": 300,
        "initial_signal_session_count": 3,
        "initial_combined_session_count": 303,
        "unavailable_source_session_dates": (
            date(2026, 8, 13),
            date(2026, 8, 19),
        ),
        "intended_session_count": 2,
        "batches": (batch,),
        "performance_authorized": False,
        "production_authorized": False,
        "external_request_count": 0,
    }
    plan = FiveYearResearchMembershipContinuationPlanV1.model_validate(
        {**payload, "logical_fingerprint": _fingerprint(payload)}
    )
    path = candidate / "continuation-plan.json"

    _write_plan(path, plan)

    assert path.stat().st_mode & 0o777 == 0o400
    assert _read_plan(path) == plan
    changed = json.loads(path.read_text())
    changed["intended_session_count"] = 3
    path.chmod(0o600)
    path.write_text(json.dumps(changed))
    path.chmod(0o400)
    with pytest.raises(
        FiveYearResearchMembershipContinuationError,
        match="validation failed",
    ):
        _read_plan(path)


def test_batch_model_rejects_unordered_dates() -> None:
    with pytest.raises(ValueError, match="unique and ordered"):
        FiveYearResearchMembershipBatchV1(
            batch_id="batch-0001",
            session_dates=(date(2026, 9, 11), date(2026, 9, 10)),
        )
