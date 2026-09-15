from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    StrategyMembershipMode,
    TerminalReferenceLedgerState,
)
from tip_api.persistence.strong_leader_pullback_development_dataset import (
    StrongLeaderPullbackDevelopmentDatasetPersistenceError,
    read_strong_leader_pullback_development_dataset,
    write_strong_leader_pullback_development_dataset,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_strong_leader_pullback_observation,
)
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
    build_reconstructed_development_label,
    build_terminal_reference_ledger_entry,
)


INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")
SIGNAL = date(2026, 1, 2)
SESSIONS = (date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8), date(2026, 1, 9))


def _bar(session: date, value: str) -> ReconstructedOutcomeBarV1:
    close = Decimal(value)
    return ReconstructedOutcomeBarV1(
        session=session,
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
    )


def _observation():
    return build_strong_leader_pullback_observation(
        as_of_session=SIGNAL,
        universe_id="primary",
        instrument_id=INSTRUMENT_ID,
        ticker="TEST",
        membership_mode=StrategyMembershipMode.POINT_IN_TIME,
        membership_session=SIGNAL,
        membership_included=True,
        relative_strength_20s_percentile="0.9000",
        trend_quality_score="80.0000",
        pullback_depth_atr="1.0000",
        close_above_prior_close=True,
        close_above_prior_high=False,
        pullback_volume_ratio="0.7000",
        market_regime="Balanced",
        source_max_session=SIGNAL,
        source_fingerprint="1" * 64,
    )


def _package_values():
    observation = _observation()
    target = tuple(_bar(session, str(100 + index)) for index, session in enumerate(SESSIONS))
    benchmark = tuple(_bar(session, str(500 + index)) for index, session in enumerate(SESSIONS))
    labels = tuple(
        build_reconstructed_development_label(
            observation_fingerprint=observation.logical_fingerprint,
            signal_session=SIGNAL,
            instrument_id=INSTRUMENT_ID,
            ticker_locator="TEST",
            expected_path_sessions=SESSIONS[:horizon],
            split_basis_session=date(2026, 9, 9),
            instrument_bars=target[:horizon],
            benchmark_bars=benchmark[:horizon],
            source_eod_fingerprint="2" * 64,
            source_adjustment_fingerprint="3" * 64,
        )
        for horizon in (1, 3, 5)
    )
    terminal = build_terminal_reference_ledger_entry(
        instrument_id=UUID("00000000-0000-4000-8000-000000000002"),
        ticker_locator="TERM",
        last_observed_eod_session=date(2026, 1, 7),
        first_absent_exchange_session=date(2026, 1, 8),
        state=TerminalReferenceLedgerState.EXACT,
        lower_reference_value_usd=Decimal("25"),
        upper_reference_value_usd=Decimal("25"),
        evidence_fingerprint="4" * 64,
    )
    return observation, labels, terminal


def _manifest_values():
    return {
        "implementation_revision": "a" * 40,
        "created_at": datetime(2026, 9, 15, tzinfo=UTC),
        "admission_report_sha256": "5" * 64,
        "admission_logical_fingerprint": "6" * 64,
        "diagnostics_report_sha256": "7" * 64,
        "diagnostics_logical_fingerprint": "8" * 64,
        "chronological_plan_fingerprint": "9" * 64,
        "source_eod_fingerprint": "2" * 64,
        "source_adjustment_fingerprint": "3" * 64,
        "split_basis_session": date(2026, 9, 9),
        "first_development_signal_session": SIGNAL,
        "last_development_signal_session": SIGNAL,
        "development_signal_session_count": 1,
    }


def test_owner_only_dataset_round_trip_and_immutable_replay(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "dataset=fixture"
    observation, labels, terminal = _package_values()

    first = write_strong_leader_pullback_development_dataset(
        output_root=target,
        output_custody_root=custody,
        observations=(observation,),
        labels=labels,
        terminal_references=(terminal,),
        manifest_values=_manifest_values(),
    )
    second = write_strong_leader_pullback_development_dataset(
        output_root=target,
        output_custody_root=custody,
        observations=(observation,),
        labels=labels,
        terminal_references=(terminal,),
        manifest_values=_manifest_values(),
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert second.observations == (observation,)
    assert second.labels == labels
    assert second.manifest.observation_count == 1
    assert second.manifest.label_count == 3
    assert second.manifest.validation_label_count == 0
    assert second.manifest.holdout_label_count == 0
    assert {item.stat().st_mode & 0o777 for item in target.iterdir()} == {0o400}


def test_dataset_rejects_non_owner_only_custody(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o755)
    observation, labels, terminal = _package_values()

    with pytest.raises(
        StrongLeaderPullbackDevelopmentDatasetPersistenceError,
        match="custody",
    ):
        write_strong_leader_pullback_development_dataset(
            output_root=custody / "dataset=fixture",
            output_custody_root=custody,
            observations=(observation,),
            labels=labels,
            terminal_references=(terminal,),
            manifest_values=_manifest_values(),
        )


def test_dataset_detects_manifest_tampering(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "dataset=fixture"
    observation, labels, terminal = _package_values()
    write_strong_leader_pullback_development_dataset(
        output_root=target,
        output_custody_root=custody,
        observations=(observation,),
        labels=labels,
        terminal_references=(terminal,),
        manifest_values=_manifest_values(),
    )
    manifest = target / "manifest.json"
    manifest.chmod(0o600)

    with pytest.raises(
        StrongLeaderPullbackDevelopmentDatasetPersistenceError,
        match="custody",
    ):
        read_strong_leader_pullback_development_dataset(
            output_root=target, output_custody_root=custody
        )


def test_immutable_replay_rejects_different_source_binding(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "dataset=fixture"
    observation, labels, terminal = _package_values()
    write_strong_leader_pullback_development_dataset(
        output_root=target,
        output_custody_root=custody,
        observations=(observation,),
        labels=labels,
        terminal_references=(terminal,),
        manifest_values=_manifest_values(),
    )
    changed = {**_manifest_values(), "implementation_revision": "b" * 40}

    with pytest.raises(
        StrongLeaderPullbackDevelopmentDatasetPersistenceError,
        match="differs",
    ):
        write_strong_leader_pullback_development_dataset(
            output_root=target,
            output_custody_root=custody,
            observations=(observation,),
            labels=labels,
            terminal_references=(terminal,),
            manifest_values=changed,
        )
