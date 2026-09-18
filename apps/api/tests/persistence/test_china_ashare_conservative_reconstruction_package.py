from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
    build_conservative_partition_census,
    build_conservative_reconstruction_plan,
    build_price_limit_smoke,
    candidate_set_fingerprint,
)
from tip_api.contracts.china_ashare.v1.conservative_reconstructed_universe import (
    ChinaAshareConservativeUniverseDisposition,
    ChinaAshareConservativeUniverseRowV1,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.persistence.china_ashare_conservative_reconstruction_package import (
    ChinaAshareConservativeReconstructionPackageError,
    publish_china_ashare_conservative_reconstruction_package,
    read_china_ashare_conservative_reconstruction_package,
)
from tip_api.services.china_ashare_conservative_reconstruction_census import (
    merge_conservative_reconstruction_census,
)


def test_partitioned_package_is_atomic_closed_set_and_byte_replayable(tmp_path: Path) -> None:
    plan = _plan()
    partitions = tuple(_partition(plan, index, state_count=index == 0) for index in range(109))
    census = merge_conservative_reconstruction_census(plan=plan, partitions=partitions)
    smoke = build_price_limit_smoke(
        instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
        cninfo_plan_fingerprint="7" * 64,
        cninfo_replay_set_fingerprint="6" * 64,
        normalized_partition_manifest_fingerprint=plan.normalized_partition_manifest_fingerprints[0],
        price_limit_resolver_plan_fingerprint="5" * 64,
        state_count=1,
        resolved_count=1,
        quarantined_count=0,
        resolution_set_fingerprint="9" * 64,
        official_zero_event_evidence=True,
        as_operated=False,
        outcome_read_count=0,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
    )
    row = ChinaAshareConservativeUniverseRowV1(
        partition_index=0,
        instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_security_id="sh.600001",
        session_date=date(2024, 1, 3),
        knowledge_session_date=None,
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        trading_status=ChinaAshareTradingStatus.TRADING,
        risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
        disposition=ChinaAshareConservativeUniverseDisposition.QUARANTINE,
        reason_codes=(
            "provider_reconstructed_not_as_operated",
            "source_available_at_unobserved",
            "next_session_knowledge_clock_unavailable",
        ),
        input_partition_manifest_fingerprint=plan.normalized_partition_manifest_fingerprints[0],
        as_operated=False,
        research_authorized=False,
        return_construction_authorized=False,
        research_backtest_authorized=False,
    )
    payloads = tuple(
        (partition, (row,) if partition.partition_index == 0 else ())
        for partition in partitions
    )
    primary = publish_china_ashare_conservative_reconstruction_package(
        custody_root=tmp_path / "primary", plan=plan, census=census, smoke=smoke,
        partition_payloads=payloads,
    )
    replay = publish_china_ashare_conservative_reconstruction_package(
        custody_root=tmp_path / "replay", plan=plan, census=census, smoke=smoke,
        partition_payloads=payloads,
    )

    assert primary.manifest == replay.manifest
    assert primary.file_count == 331
    assert primary.census.maximum_official_request_count == 0
    assert primary.manifest.as_operated is False
    assert primary.manifest.research_authorized is False
    assert primary.manifest.return_construction_authorized is False
    assert primary.manifest.research_backtest_authorized is False
    assert _files(primary.package_path) == _files(replay.package_path)
    assert all((item.stat().st_mode & 0o777) == 0o400 for item in primary.package_path.rglob("*") if item.is_file())
    assert all((item.stat().st_mode & 0o777) == 0o700 for item in primary.package_path.rglob("*") if item.is_dir())

    extra = primary.package_path / "unexpected"
    extra.write_bytes(b"x")
    extra.chmod(0o400)
    with pytest.raises(ChinaAshareConservativeReconstructionPackageError, match="closed file set"):
        read_china_ashare_conservative_reconstruction_package(package_path=primary.package_path)


def _plan():
    return build_conservative_reconstruction_plan(
        source_expansion_plan_fingerprint="1" * 64,
        population_package_fingerprint="2" * 64,
        normalized_run_fingerprint="3" * 64,
        normalized_partition_manifest_fingerprints=tuple(f"{index + 1000:064x}" for index in range(109)),
        market_mechanics_package_fingerprint="4" * 64,
        price_limit_resolver_plan_fingerprint="5" * 64,
        cninfo_sample_plan_fingerprint="7" * 64,
        cninfo_sample_replay_set_fingerprint="6" * 64,
        interval_start=date(2021, 9, 16), interval_end=date(2024, 1, 3),
        target_sessions=(date(2021, 9, 16), date(2024, 1, 3)),
        official_evidence_priority=(
            ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
            ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
            ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
        ),
        official_confirmed_requires_all_families=True,
        provider_provisional_as_operated=False,
        provider_provisional_excludes_warning_windows=True,
        provider_provisional_quarantines_action_windows=True,
        provider_provisional_quarantines_terminal_boundaries=True,
        provider_provisional_quarantines_unknown_states=True,
        provider_provisional_reconstructs_normal_limits_from_official_mechanics=True,
        provider_provisional_personal_research_candidate_only=True,
        maximum_requests_per_warning_candidate=1,
        maximum_requests_per_lifecycle_candidate=4,
        maximum_requests_per_listing_candidate=1,
        maximum_requests_per_action_candidate=0,
        action_candidates_remain_isolated_without_official_requests=True,
        outcome_read_count=0,
        return_construction_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        factor_discovery_authorized=False,
        product_publication_authorized=False,
    )


def _partition(plan, index: int, state_count: bool):
    count = int(state_count)
    return build_conservative_partition_census(
        plan_fingerprint=plan.logical_fingerprint,
        partition_index=index,
        normalized_partition_manifest_fingerprint=plan.normalized_partition_manifest_fingerprints[index],
        target_count=1, resolved_target_count=1, isolated_target_count=0,
        state_count=count,
        provisional_candidate_included_state_count=0,
        provisional_candidate_excluded_state_count=0,
        provisional_quarantined_state_count=count,
        warning_present_state_count=0, warning_unknown_state_count=0,
        trading_status_unknown_state_count=0, factor_change_candidate_window_count=0,
        terminal_boundary_candidate_security_count=0,
        resolved_empty_state_target_count=0, warning_candidate_security_count=0,
        lifecycle_candidate_security_count=0, listing_stage_candidate_security_count=0,
        action_candidate_security_count=0, candidate_records=(),
        candidate_set_fingerprint=candidate_set_fingerprint(()),
        maximum_official_request_count=0, outcome_read_count=0,
        research_backtest_authorized=False,
    )


def _files(root: Path):
    return tuple(
        (item.relative_to(root).as_posix(), item.read_bytes())
        for item in sorted(root.rglob("*")) if item.is_file()
    )
