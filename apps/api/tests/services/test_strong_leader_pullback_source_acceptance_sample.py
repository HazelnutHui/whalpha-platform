from __future__ import annotations

import json
import stat
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
    InactiveLifecycleIdentityType,
)
from tip_api.services import strong_leader_pullback_source_acceptance_sample as module


NOW = datetime(2026, 9, 13, 14, tzinfo=UTC)
REVISION = "a" * 40
SHA = "b" * 64
FIRST = date(2025, 6, 23)
LAST = date(2026, 8, 12)
DELIST = date(2026, 8, 13)


def _instrument(number: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{number:012d}")


def _blocker() -> SimpleNamespace:
    action_ids = tuple(_instrument(index + 1) for index in range(4))
    actions = tuple(
        SimpleNamespace(
            source_action_id=f"action-{index:02d}",
            source_revision=1,
            provider_ticker=f"T{index:02d}",
            effective_date=date(2026, 7, 1),
            action_type="reverse_split" if index == 19 else "cash_dividend",
            candidate_instrument_id=action_ids[index % len(action_ids)],
            historical_candidate_classification=(
                "one_historical_candidate"
                if index < 12
                else "multiple_historical_candidates"
            ),
            exact_date_failure_reason="unresolved_ticker",
            feature_path_count=1,
            horizon_1_path_count=1,
            horizon_3_path_count=1,
            horizon_5_path_count=1,
            inactive_source_state="candidate_only",
            inactive_source_type_codes=("CS",),
            finra_exact_date_symbol_occurrence_count=1,
            finra_exact_numeric_occurrence_count=0,
            finra_flag_codes=("A",),
            identity_evidence_kind="history_candidate_unassigned",
        )
        for index in range(20)
    )
    lifecycles = tuple(
        SimpleNamespace(
            instrument_id=_instrument(index + 100),
            source_anchor_dates=(
                module.FIXED_LIFECYCLE_ANCHORS
                if index < 58
                else (module.FIXED_LIFECYCLE_ANCHORS[1],)
            ),
            canonical_first_observed_date=FIRST,
            canonical_last_observed_date=LAST,
            provider_delist_date_candidate=DELIST,
            included_path_count=2,
            horizon_1_crosses_last_observed_path_count=0,
            horizon_3_crosses_last_observed_path_count=1,
            horizon_5_crosses_last_observed_path_count=2,
        )
        for index in range(64)
    )
    return SimpleNamespace(
        action_records=actions,
        lifecycle_records=lifecycles,
        manifest_sha256="c" * 64,
        manifest=SimpleNamespace(
            logical_fingerprint="d" * 64,
            action_exposure_record_count=4_643,
            lifecycle_exposure_record_count=89,
        ),
    )


def _lifecycle_results() -> tuple[SimpleNamespace, ...]:
    results = []
    for anchor_index, anchor in enumerate(module.FIXED_LIFECYCLE_ANCHORS):
        observations = []
        decisions = []
        for index in range(64):
            if anchor_index == 0 and index >= 58:
                continue
            fingerprint = f"{anchor_index * 1000 + index + 1:064x}"
            instrument_id = _instrument(index + 100)
            observations.append(
                SimpleNamespace(
                    source_observation_fingerprint=fingerprint,
                    ticker=f"L{index:02d}",
                    name=f"Lifecycle {index:02d}",
                    cik=f"{index + 1:010d}",
                    primary_exchange="XNYS",
                    type="CS",
                )
            )
            decisions.append(
                SimpleNamespace(
                    disposition=InactiveLifecycleDisposition.REVIEW_CANDIDATE,
                    canonical_instrument_id=instrument_id,
                    canonical_first_observed_date=FIRST,
                    canonical_last_observed_date=LAST,
                    effective_date_candidate=DELIST,
                    source_observation_fingerprint=fingerprint,
                    anchor_date=anchor,
                    selected_identity_type=(
                        InactiveLifecycleIdentityType.SHARE_CLASS_FIGI
                    ),
                    selected_identity_value=f"BBG{index:09d}",
                )
            )
        results.append(
            SimpleNamespace(
                source_observations=tuple(observations),
                decisions=tuple(decisions),
                manifest_sha256=f"{anchor_index + 10:064x}",
                manifest=SimpleNamespace(
                    anchor_date=anchor,
                    logical_fingerprint=f"{anchor_index + 20:064x}",
                    decision_artifact=SimpleNamespace(record_count=len(decisions)),
                ),
            )
        )
    return tuple(results)


def test_compose_freezes_complete_outcome_blind_population() -> None:
    report = module._compose_report(
        blocker=_blocker(),
        lifecycle=_lifecycle_results(),
        implementation_revision=REVISION,
        evaluated_at=NOW,
    )
    assert report.action_case_count == 20
    assert report.action_instrument_count == 4
    assert report.lifecycle_case_count == 64
    assert report.lifecycle_source_occurrence_count == 122
    assert report.combined_instrument_count == 68
    assert report.overlapping_instrument_count == 0
    assert report.provider_request_count == 0
    assert report.stable_identity_assignment_count == 0
    assert report.terminal_outcome_count == 0
    assert report.forward_outcome_count == 0
    assert report.performance_metric_count == 0
    assert report.research_admission_count == 0


def test_build_persists_and_formally_rereads_exact_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    blocker = _blocker()
    lifecycle = _lifecycle_results()
    monkeypatch.setattr(
        module,
        "read_strong_leader_pullback_evidence_blocker_census",
        lambda **_: blocker,
    )
    calls = []

    def lifecycle_reader(*, anchor_date: date, **_: object) -> SimpleNamespace:
        calls.append(anchor_date)
        return lifecycle[module.FIXED_LIFECYCLE_ANCHORS.index(anchor_date)]

    monkeypatch.setattr(
        module,
        "read_historical_inactive_lifecycle_resolution_shadow",
        lifecycle_reader,
    )
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    custody.chmod(0o700)
    output = custody / "build=fixture"
    result = module.build_strong_leader_pullback_source_acceptance_sample(
        blocker_census_root=tmp_path,
        blocker_census_custody_root=tmp_path,
        lifecycle_shadow_root=tmp_path,
        lifecycle_shadow_custody_root=tmp_path,
        output_root=output,
        output_custody_root=custody,
        implementation_revision=REVISION,
        evaluated_at=NOW,
    )
    assert result.status == "published"
    assert calls == list(module.FIXED_LIFECYCLE_ANCHORS)
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    report_path = output / module.REPORT_FILE
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o400
    reread = module.read_strong_leader_pullback_source_acceptance_sample(
        output_root=output,
        output_custody_root=custody,
    )
    assert reread.report == result.report
    assert reread.report_sha256 == result.report_sha256

    report_path.chmod(0o600)
    payload = json.loads(report_path.read_text())
    payload["action_case_count"] = 19
    report_path.write_text(json.dumps(payload))
    report_path.chmod(0o400)
    with pytest.raises(module.StrongLeaderPullbackSourceAcceptanceSampleError):
        module.read_strong_leader_pullback_source_acceptance_sample(
            output_root=output,
            output_custody_root=custody,
        )


def test_missing_lifecycle_source_occurrence_rejects_whole_sample() -> None:
    lifecycle = list(_lifecycle_results())
    lifecycle[1] = SimpleNamespace(
        **{
            **lifecycle[1].__dict__,
            "source_observations": lifecycle[1].source_observations[:-1],
        }
    )
    with pytest.raises(
        module.StrongLeaderPullbackSourceAcceptanceSampleError,
        match="lacks its source occurrence",
    ):
        module._compose_report(
            blocker=_blocker(),
            lifecycle=tuple(lifecycle),
            implementation_revision=REVISION,
            evaluated_at=NOW,
        )
