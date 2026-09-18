from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareConservativeEvidenceCandidateV1,
    ChinaAshareOfficialEvidenceBudgetFamily,
    ChinaAshareOfficialEvidenceBudgetTierV1,
)
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
    ChinaAshareOfficialEvidenceRequestPurpose,
)
from tip_api.persistence.china_ashare_official_evidence_priority_plan import (
    ChinaAshareOfficialEvidencePriorityPackageError,
    publish_china_ashare_official_evidence_priority_plan,
    read_china_ashare_official_evidence_priority_plan,
)
from tip_api.services.china_ashare_official_evidence_priority_plan import (
    plan_china_ashare_official_evidence_priority,
)


def test_priority_plan_is_deduplicated_budgeted_and_order_independent() -> None:
    source = _source_package()
    forward = plan_china_ashare_official_evidence_priority(
        reconstruction_package=source
    )
    reverse = plan_china_ashare_official_evidence_priority(
        reconstruction_package=source,
        reverse_candidate_input=True,
    )

    assert forward == reverse
    assert len(forward.requests) == 6
    assert [item.maximum_request_count for item in forward.tiers] == [1, 4, 1]
    assert [item.deduplicated_security_count for item in forward.tiers] == [1, 1, 1]
    assert len({item.request_id for item in forward.requests}) == 6
    assert all(item.effective_from == date(2021, 9, 16) for item in forward.requests)
    assert all(item.effective_to == date(2026, 9, 16) for item in forward.requests)
    assert all(item.failure_disposition == "quarantine_unchanged" for item in forward.requests)
    assert all(item.maximum_acquisition_attempt_count == 1 for item in forward.requests)
    assert not any(item.source_security_id == "sz.000004" for item in forward.requests)
    assert forward.corporate_action_candidate_security_count == 4
    assert forward.corporate_action_candidate_window_count == 7
    assert forward.corporate_action_request_count == 0
    assert forward.network_execution_authorized is False
    warning = forward.requests[0]
    assert warning.purpose is ChinaAshareOfficialEvidenceRequestPurpose.RISK_WARNING_TRANSITION_HISTORY
    assert warning.candidate_authorities == (
        ChinaAshareOfficialEvidenceAuthority.SSE,
        ChinaAshareOfficialEvidenceAuthority.CNINFO,
    )
    lifecycle = next(
        item for item in forward.requests if item.family.value == "lifecycle"
    )
    assert lifecycle.candidate_authorities == (
        ChinaAshareOfficialEvidenceAuthority.SZSE,
        ChinaAshareOfficialEvidenceAuthority.CNINFO,
    )


def test_priority_plan_persistence_is_owner_only_atomic_and_closed(tmp_path: Path) -> None:
    plan = plan_china_ashare_official_evidence_priority(
        reconstruction_package=_source_package()
    )
    primary = publish_china_ashare_official_evidence_priority_plan(
        custody_root=tmp_path / "primary", plan=plan
    )
    replay = publish_china_ashare_official_evidence_priority_plan(
        custody_root=tmp_path / "replay", plan=plan
    )

    assert primary.plan == replay.plan
    assert primary.manifest == replay.manifest
    assert primary.file_count == 2
    assert _files(primary.package_path) == _files(replay.package_path)
    assert all(
        (item.stat().st_mode & 0o777) == 0o400
        for item in primary.package_path.rglob("*")
        if item.is_file()
    )
    assert all(
        (item.stat().st_mode & 0o777) == 0o700
        for item in primary.package_path.rglob("*")
        if item.is_dir()
    )

    unexpected = primary.package_path / "unexpected.json"
    unexpected.write_text("{}")
    unexpected.chmod(0o400)
    with pytest.raises(
        ChinaAshareOfficialEvidencePriorityPackageError,
        match="closed file set",
    ):
        read_china_ashare_official_evidence_priority_plan(
            package_path=primary.package_path
        )


def _source_package():
    candidates = (
        _candidate(
            "sh.600001",
            1,
            (
                ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
                ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION,
            ),
        ),
        _candidate(
            "sz.000002",
            2,
            (
                ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
                ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION,
            ),
        ),
        _candidate(
            "sh.600003",
            3,
            (
                ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
                ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION,
            ),
        ),
        _candidate(
            "sz.000004",
            4,
            (ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION,),
        ),
    )
    tiers = (
        ChinaAshareOfficialEvidenceBudgetTierV1(
            priority=1,
            family=ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
            deduplicated_security_count=1,
            maximum_requests_per_security=1,
            maximum_request_count=1,
        ),
        ChinaAshareOfficialEvidenceBudgetTierV1(
            priority=2,
            family=ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
            deduplicated_security_count=1,
            maximum_requests_per_security=4,
            maximum_request_count=4,
        ),
        ChinaAshareOfficialEvidenceBudgetTierV1(
            priority=3,
            family=ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
            deduplicated_security_count=1,
            maximum_requests_per_security=1,
            maximum_request_count=1,
        ),
    )
    return SimpleNamespace(
        manifest=SimpleNamespace(
            logical_fingerprint="a" * 64,
            plan_fingerprint="b" * 64,
            global_census_fingerprint="c" * 64,
            candidate_set_fingerprint="d" * 64,
        ),
        plan=SimpleNamespace(
            logical_fingerprint="b" * 64,
            interval_start=date(2021, 9, 16),
            interval_end=date(2026, 9, 16),
        ),
        census=SimpleNamespace(
            logical_fingerprint="c" * 64,
            candidate_set_fingerprint="d" * 64,
            warning_candidate_security_count=1,
            lifecycle_candidate_security_count=1,
            listing_stage_candidate_security_count=1,
            action_candidate_security_count=4,
            factor_change_candidate_window_count=7,
            official_request_budget_by_priority=tiers,
            maximum_official_request_count=6,
        ),
        partition_censuses=(SimpleNamespace(candidate_records=candidates),),
        manifest_physical_sha256="e" * 64,
    )


def _candidate(source_security_id, value, families):
    return ChinaAshareConservativeEvidenceCandidateV1(
        source_security_id=source_security_id,
        instrument_id=UUID(f"00000000-0000-0000-0000-{value:012d}"),
        partition_index=value,
        source_target_quarantined=False,
        observed_state_count=1,
        warning_present_state_count=int(
            ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING in families
        ),
        warning_unknown_state_count=0,
        trading_status_unknown_state_count=0,
        factor_change_candidate_count=1,
        terminal_boundary_candidate=(
            ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE in families
        ),
        listing_stage_uncertain=(
            ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE in families
        ),
        requested_families=tuple(sorted(families, key=str)),
        maximum_official_request_count=sum(
            {
                ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING: 1,
                ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE: 4,
                ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE: 1,
                ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION: 0,
            }[item]
            for item in families
        ),
    )


def _files(root: Path):
    return tuple(
        (item.relative_to(root).as_posix(), item.read_bytes())
        for item in sorted(root.rglob("*"))
        if item.is_file()
    )
