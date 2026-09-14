from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services import strong_leader_pullback_source_acceptance_sample as sample_source
from tip_api.services import strong_leader_pullback_terminal_gap_census_v2 as service
from tip_api.services import strong_leader_pullback_terminal_gap_census_v2_cli as cli


SHA_A = "a" * 64
SHA_B = "b" * 64
SOURCE_TIME = datetime(2026, 9, 14, 9, tzinfo=timezone.utc)


def test_terminal_gap_v2_adds_corrected_population_and_recounts_paths() -> None:
    report = service._build_report(
        **_inputs(),
        implementation_revision="1" * 40,
        evaluated_at=SOURCE_TIME,
    )

    assert report.population_instrument_count == 2
    assert report.legacy_population_instrument_count == 1
    assert report.newly_in_scope_instrument_count == 1
    assert report.reference_documented_instrument_count == 1
    assert report.remaining_gap_instrument_count == 1
    assert report.horizon_5_crossing_path_count == 4
    assert report.documented_horizon_5_crossing_path_count == 3
    assert report.remaining_horizon_5_crossing_path_count == 1
    assert report.new_primary_source_case_count == 1
    assert report.terminal_outcome_count == 0


def test_terminal_gap_v2_rejects_prior_path_lineage_difference() -> None:
    inputs = _inputs()
    inputs["prior"].report.decisions[0].horizon_5_crossing_path_count = 99

    with pytest.raises(
        service.StrongLeaderPullbackTerminalGapCensusV2Error,
        match="legacy path lineage differs",
    ):
        service._build_report(
            **inputs,
            implementation_revision="1" * 40,
            evaluated_at=SOURCE_TIME,
        )


def test_terminal_gap_v2_write_is_immutable(tmp_path: Path) -> None:
    report = service._build_report(
        **_inputs(),
        implementation_revision="1" * 40,
        evaluated_at=SOURCE_TIME,
    )
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    output = custody / "census=v2"

    first = service._write_report(
        output_root=output, output_custody_root=custody, report=report
    )
    second = service._write_report(
        output_root=output, output_custody_root=custody, report=report
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert (output / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_terminal_gap_v2_cli_fails_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "1" * 40)

    def stopped(**_kwargs: object) -> object:
        raise service.StrongLeaderPullbackTerminalGapCensusV2Error("stopped")

    monkeypatch.setattr(
        service, "build_strong_leader_pullback_terminal_gap_census_v2", stopped
    )
    assert cli.main(_cli_args()) == 1
    assert '"status":"stopped"' in capsys.readouterr().err


def _inputs() -> dict[str, object]:
    legacy_id = UUID(int=1)
    new_id = UUID(int=2)
    legacy_date = date(2026, 1, 8)
    new_identity_date = date(2026, 1, 9)
    new_eod_date = date(2026, 1, 8)
    legacy_case = sample_source.LifecycleSourceAcceptanceCaseV1(
        instrument_id=legacy_id,
        source_anchor_dates=(date(2026, 7, 16),),
        source_observation_fingerprints=(SHA_A,),
        source_occurrence_count=1,
        selected_identity_types=("share_class_figi",),
        selected_identity_values=("BBGLEGACY",),
        provider_ticker_locators=("LEG",),
        provider_name_locators=("Legacy Inc.",),
        cik_locators=("0000000001",),
        primary_exchange_locators=("XNYS",),
        source_type_codes=("CS",),
        canonical_first_observed_date=date(2021, 9, 10),
        canonical_last_observed_date=legacy_date,
        provider_delist_date_candidate=date(2026, 1, 9),
        included_path_count=10,
        horizon_1_crossing_path_count=0,
        horizon_3_crossing_path_count=1,
        horizon_5_crossing_path_count=2,
    )
    boundary_decisions = (
        SimpleNamespace(
            instrument_id=legacy_id,
            canonical_identity_first_observed_date=date(2021, 9, 10),
            canonical_identity_last_observed_date=legacy_date,
            strategy_window_last_eod_observed_date=date(2026, 1, 7),
            provider_delist_date_candidate=date(2026, 1, 9),
            included_path_count=10,
            legacy_horizon_1_crossing_path_count=0,
            legacy_horizon_3_crossing_path_count=1,
            legacy_horizon_5_crossing_path_count=2,
            corrected_horizon_1_crossing_path_count=1,
            corrected_horizon_3_crossing_path_count=2,
            corrected_horizon_5_crossing_path_count=3,
        ),
        SimpleNamespace(
            instrument_id=new_id,
            canonical_identity_first_observed_date=date(2021, 9, 10),
            canonical_identity_last_observed_date=new_identity_date,
            strategy_window_last_eod_observed_date=new_eod_date,
            provider_delist_date_candidate=date(2026, 1, 12),
            included_path_count=8,
            legacy_horizon_1_crossing_path_count=0,
            legacy_horizon_3_crossing_path_count=0,
            legacy_horizon_5_crossing_path_count=0,
            corrected_horizon_1_crossing_path_count=0,
            corrected_horizon_3_crossing_path_count=0,
            corrected_horizon_5_crossing_path_count=1,
        ),
    )
    boundary = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="boundary/1.0",
            logical_fingerprint=SHA_A,
            lifecycle_instrument_count=2,
            corrected_horizon_5_crossing_instrument_count=2,
            newly_horizon_5_in_scope_instrument_count=1,
            decisions=boundary_decisions,
        ),
        report_sha256=SHA_B,
    )
    prior = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="gap/1.0",
            logical_fingerprint=SHA_A,
            population_instrument_count=1,
            source_bindings=(
                *(
                    SimpleNamespace(
                        name=name,
                        report_sha256=SHA_B,
                        logical_fingerprint=SHA_A,
                    )
                    for name in (
                        "source_acceptance_sample",
                        "terminal_payoff_terms",
                        "fixed_cash_terminal_evidence",
                        "listed_consideration_terminal_evidence",
                        "residual_listed_consideration_terminal_evidence",
                    )
                ),
            ),
            decisions=[
                SimpleNamespace(
                    instrument_id=legacy_id,
                    gap_state="nominal_fixed_cash_reference_documented",
                    horizon_1_crossing_path_count=0,
                    horizon_3_crossing_path_count=1,
                    horizon_5_crossing_path_count=2,
                )
            ],
        ),
        report_sha256=SHA_B,
    )
    sample = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="sample/1.0",
            logical_fingerprint=SHA_A,
            lifecycle_case_count=1,
            lifecycle_cases=(legacy_case,),
        ),
        report_sha256=SHA_B,
    )
    lifecycle_decision = SimpleNamespace(
        disposition=InactiveLifecycleDisposition.REVIEW_CANDIDATE,
        canonical_instrument_id=new_id,
        canonical_first_observed_date=date(2021, 9, 10),
        canonical_last_observed_date=new_identity_date,
        effective_date_candidate=date(2026, 1, 12),
        source_observation_fingerprint=SHA_A,
        anchor_date=date(2026, 7, 16),
        selected_identity_type=SimpleNamespace(value="share_class_figi"),
        selected_identity_value="BBGNEW",
    )
    lifecycle_source = SimpleNamespace(
        source_observation_fingerprint=SHA_A,
        ticker="NEW",
        name="New Inc.",
        cik="0000000002",
        primary_exchange="XNYS",
        type="CS",
    )
    lifecycle = (
        SimpleNamespace(
            manifest=SimpleNamespace(
                anchor_date=date(2026, 7, 16),
                contract_version="lifecycle/1.0",
                logical_fingerprint=SHA_A,
            ),
            manifest_sha256=SHA_B,
            decisions=(lifecycle_decision,),
            source_observations=(lifecycle_source,),
        ),
    )
    payoff = _report_source(
        "payoff/1.0",
        (
            SimpleNamespace(
                instrument_id=legacy_id,
                request_sequence=1,
                terminal_candidate_state="cessation_timing_not_matched",
            ),
        ),
    )
    cash = _report_source(
        "cash/1.0",
        (
            SimpleNamespace(
                instrument_id=legacy_id,
                evidence_state="nominal_fixed_cash_terminal_evidence",
                source_available_at=SOURCE_TIME,
            ),
        ),
    )
    listed = _report_source("listed/1.0", ())
    residual = _report_source("residual/1.0", ())
    return {
        "boundary": boundary,
        "prior": prior,
        "sample": sample,
        "lifecycle": lifecycle,
        "payoff": payoff,
        "cash": cash,
        "listed": listed,
        "residual": residual,
    }


def _report_source(contract: str, decisions: tuple[object, ...]) -> object:
    return SimpleNamespace(
        report=SimpleNamespace(
            contract_version=contract,
            logical_fingerprint=SHA_A,
            decisions=decisions,
        ),
        report_sha256=SHA_B,
    )


def _cli_args() -> list[str]:
    names = (
        "boundary-census",
        "boundary-census-custody-root",
        "prior-gap-census",
        "prior-gap-census-custody-root",
        "source-sample",
        "source-sample-custody-root",
        "lifecycle-shadow",
        "lifecycle-shadow-custody-root",
        "payoff-terms",
        "payoff-terms-custody-root",
        "fixed-cash",
        "fixed-cash-custody-root",
        "listed-terminal",
        "listed-terminal-custody-root",
        "residual-terminal",
        "residual-terminal-custody-root",
        "output-root",
        "output-custody-root",
    )
    result = [value for name in names for value in (f"--{name}", "/tmp/value")]
    return result + [
        "--lifecycle-anchor",
        "2026-07-16",
        "--evaluated-at",
        "2026-09-14T09:00:00Z",
        "--execute",
    ]
