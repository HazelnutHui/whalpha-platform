from __future__ import annotations

import stat
from datetime import datetime, timezone

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessError,
    CampaignThreeDevelopmentExecutionKind,
    build_campaign_three_development_access_request,
    expected_campaign_three_authorization_phrase,
    grant_campaign_three_development_access,
)
from tip_api.persistence.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessPersistenceError,
    complete_campaign_three_development_execution,
    read_campaign_three_development_access_grant,
    read_campaign_three_development_access_request,
    read_campaign_three_development_execution_state,
    reserve_campaign_three_development_execution,
    write_campaign_three_development_access_grant,
    write_campaign_three_development_access_request,
)


REVISION = "1" * 40


def _custody(tmp_path, name):
    path = tmp_path / name
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _access():
    request = build_campaign_three_development_access_request(
        implementation_revision=REVISION,
        implementation_tree_clean=True,
    )
    grant = grant_campaign_three_development_access(
        request=request,
        authorization_phrase=expected_campaign_three_authorization_phrase(request),
        granted_at=datetime(2026, 9, 16, 1, tzinfo=timezone.utc),
    )
    return request, grant


def test_access_records_are_owner_only_canonical_and_round_trip(tmp_path) -> None:
    request, grant = _access()
    request_custody = _custody(tmp_path, "requests")
    grant_custody = _custody(tmp_path, "grants")
    request_root = request_custody / "request=test"
    grant_root = grant_custody / "grant=test"

    request_path, request_sha, request_status = (
        write_campaign_three_development_access_request(
            output_root=request_root,
            output_custody_root=request_custody,
            request=request,
        )
    )
    grant_path, grant_sha, grant_status = (
        write_campaign_three_development_access_grant(
            output_root=grant_root,
            output_custody_root=grant_custody,
            request=request,
            grant=grant,
        )
    )

    assert request_status == grant_status == "published"
    assert stat.S_IMODE(request_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(request_path.stat().st_mode) == 0o400
    assert stat.S_IMODE(grant_path.stat().st_mode) == 0o400
    assert read_campaign_three_development_access_request(
        output_root=request_root,
        output_custody_root=request_custody,
    ) == (request, request_sha)
    assert read_campaign_three_development_access_grant(
        output_root=grant_root,
        output_custody_root=grant_custody,
    ) == (grant, grant_sha)


def test_execution_custody_enforces_formal_then_distinct_exact_replay(tmp_path) -> None:
    request, grant = _access()
    custody = _custody(tmp_path, "executions")
    root = custody / "execution=test"
    formal_output = tmp_path / "formal-report"
    replay_output = tmp_path / "replay-report"
    run_created_at = datetime(2026, 9, 16, 2, tzinfo=timezone.utc)

    formal = reserve_campaign_three_development_execution(
        execution_root=root,
        execution_custody_root=custody,
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.FORMAL,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        report_output_root=formal_output,
    )
    assert stat.S_IMODE(root.stat().st_mode) == 0o700

    with pytest.raises(
        CampaignThreeDevelopmentAccessPersistenceError,
        match="completed formal",
    ):
        reserve_campaign_three_development_execution(
            execution_root=root,
            execution_custody_root=custody,
            request=request,
            grant=grant,
            execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
            run_created_at=run_created_at,
            reserved_at=run_created_at,
            report_output_root=replay_output,
        )

    formal_completion = complete_campaign_three_development_execution(
        execution_root=root,
        execution_custody_root=custody,
        execution_kind=CampaignThreeDevelopmentExecutionKind.FORMAL,
        report_sha256="3" * 64,
        report_fingerprint="4" * 64,
        completed_at=run_created_at,
    )
    assert formal_completion.reservation_fingerprint == formal.logical_fingerprint

    with pytest.raises(
        CampaignThreeDevelopmentAccessPersistenceError,
        match="output root differs",
    ):
        reserve_campaign_three_development_execution(
            execution_root=root,
            execution_custody_root=custody,
            request=request,
            grant=grant,
            execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
            run_created_at=run_created_at,
            reserved_at=run_created_at,
            report_output_root=formal_output,
        )

    replay = reserve_campaign_three_development_execution(
        execution_root=root,
        execution_custody_root=custody,
        request=request,
        grant=grant,
        execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
        run_created_at=run_created_at,
        reserved_at=run_created_at,
        report_output_root=replay_output,
    )

    with pytest.raises(CampaignThreeDevelopmentAccessError, match="differs from formal"):
        complete_campaign_three_development_execution(
            execution_root=root,
            execution_custody_root=custody,
            execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
            report_sha256="5" * 64,
            report_fingerprint="4" * 64,
            completed_at=run_created_at,
        )

    replay_completion = complete_campaign_three_development_execution(
        execution_root=root,
        execution_custody_root=custody,
        execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
        report_sha256="3" * 64,
        report_fingerprint="4" * 64,
        completed_at=run_created_at,
    )
    assert replay_completion.reservation_fingerprint == replay.logical_fingerprint
    state = read_campaign_three_development_execution_state(
        execution_root=root,
        execution_custody_root=custody,
    )
    assert all(item is not None for item in state)

    with pytest.raises(
        CampaignThreeDevelopmentAccessPersistenceError,
        match="completed formal",
    ):
        reserve_campaign_three_development_execution(
            execution_root=root,
            execution_custody_root=custody,
            request=request,
            grant=grant,
            execution_kind=CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY,
            run_created_at=run_created_at,
            reserved_at=run_created_at,
            report_output_root=tmp_path / "third-report",
        )


def test_access_custody_rejects_symlink_parent(tmp_path) -> None:
    request, _ = _access()
    real = _custody(tmp_path, "real")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)

    with pytest.raises(
        CampaignThreeDevelopmentAccessPersistenceError,
        match="custody differs",
    ):
        write_campaign_three_development_access_request(
            output_root=alias / "request=test",
            output_custody_root=alias,
            request=request,
        )
