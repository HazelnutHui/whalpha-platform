from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_terminal_gap_census as service
from tip_api.services import strong_leader_pullback_terminal_gap_census_cli as cli


SHA_A = "a" * 64
SHA_B = "b" * 64


def test_terminal_gap_census_measures_reference_and_remaining_paths() -> None:
    inputs = _inputs()
    report = service._build_report(
        **inputs,
        implementation_revision="1" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=timezone.utc),
    )

    assert report.population_instrument_count == 7
    assert report.structured_case_count == 6
    assert report.exception_case_count == 1
    assert report.reference_documented_instrument_count == 2
    assert report.remaining_gap_instrument_count == 5
    assert report.documented_horizon_5_crossing_path_count == 5
    assert report.remaining_horizon_5_crossing_path_count == 30
    assert report.terminal_outcome_count == 0
    assert report.research_admission_count == 0


def test_terminal_gap_census_rejects_path_count_difference() -> None:
    inputs = _inputs()
    inputs["sample"].report.lifecycle_cases[0].horizon_5_crossing_path_count = 99

    with pytest.raises(
        service.StrongLeaderPullbackTerminalGapCensusError,
        match="path counts differ",
    ):
        service._build_report(
            **inputs,
            implementation_revision="1" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=timezone.utc),
        )


def test_terminal_gap_census_rejects_duplicate_reference_identity() -> None:
    inputs = _inputs()
    duplicate = inputs["cash"].report.decisions[0]
    inputs["listed"].report.decisions = (
        SimpleNamespace(
            target_instrument_id=duplicate.instrument_id,
            evidence_state="gross_listed_consideration_reference_value",
            source_available_at=duplicate.source_available_at,
            price_quality_flags=("adjustment_factors_unverified",),
        ),
    )

    with pytest.raises(
        service.StrongLeaderPullbackTerminalGapCensusError,
        match="duplicate listed reference evidence",
    ):
        service._build_report(
            **inputs,
            implementation_revision="1" * 40,
            evaluated_at=datetime(2026, 9, 14, 7, tzinfo=timezone.utc),
        )


def test_terminal_gap_census_write_is_immutable_and_formally_reread(
    tmp_path: Path,
) -> None:
    report = service._build_report(
        **_inputs(),
        implementation_revision="1" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=timezone.utc),
    )
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    output = custody / "census=v1"

    first = service._write_report(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert (output / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400
    (output / service.REPORT_FILE).chmod(0o600)
    with pytest.raises(service.StrongLeaderPullbackTerminalGapCensusError):
        service.read_strong_leader_pullback_terminal_gap_census(
            output_root=output,
            output_custody_root=custody,
        )


def test_terminal_gap_census_cli_reports_bounded_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = service._build_report(
        **_inputs(),
        implementation_revision="1" * 40,
        evaluated_at=datetime(2026, 9, 14, 7, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(cli, "_clean_revision", lambda: "1" * 40)
    monkeypatch.setattr(
        service,
        "build_strong_leader_pullback_terminal_gap_census",
        lambda **_kwargs: service.StrongLeaderPullbackTerminalGapCensusResult(
            output_root=Path("/tmp/census=v1"),
            report=report,
            report_sha256=SHA_B,
            status="published",
        ),
    )

    assert cli.main(_cli_args()) == 0
    output = capsys.readouterr().out
    assert '"population_instrument_count":7' in output
    assert '"remaining_gap_instrument_count":5' in output
    assert '"terminal_outcome_count":0' in output


def test_terminal_gap_census_cli_fails_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "1" * 40)

    def stopped(**_kwargs: object) -> object:
        raise service.StrongLeaderPullbackTerminalGapCensusError("stopped")

    monkeypatch.setattr(
        service,
        "build_strong_leader_pullback_terminal_gap_census",
        stopped,
    )

    assert cli.main(_cli_args()) == 1
    output = capsys.readouterr().err
    assert '"status":"stopped"' in output
    assert '"canonical_data_write_count":0' in output


def _inputs() -> dict[str, object]:
    ids = tuple(UUID(int=index) for index in range(1, 8))
    source_time = datetime(2026, 9, 14, 6, tzinfo=timezone.utc)
    lifecycle_records = tuple(
        SimpleNamespace(
            instrument_id=instrument_id,
            horizon_1_crosses_last_observed_path_count=index % 2,
            horizon_3_crosses_last_observed_path_count=index,
            horizon_5_crosses_last_observed_path_count=index + 1,
        )
        for index, instrument_id in enumerate(ids, start=1)
    )
    sample_cases = tuple(
        SimpleNamespace(
            instrument_id=item.instrument_id,
            provider_ticker_locators=(f"T{index}",),
            horizon_1_crossing_path_count=(
                item.horizon_1_crosses_last_observed_path_count
            ),
            horizon_3_crossing_path_count=(
                item.horizon_3_crosses_last_observed_path_count
            ),
            horizon_5_crossing_path_count=(
                item.horizon_5_crosses_last_observed_path_count
            ),
        )
        for index, item in enumerate(lifecycle_records, start=1)
    )
    blocker = SimpleNamespace(
        manifest=SimpleNamespace(
            contract_version="blocker/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
        ),
        manifest_sha256=SHA_B,
        lifecycle_records=lifecycle_records,
    )
    sample = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="sample/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
            lifecycle_cases=sample_cases,
            lifecycle_case_count=len(sample_cases),
            source_bindings=(
                SimpleNamespace(
                    name="strong_leader_pullback_evidence_blocker_census",
                    manifest_sha256=SHA_B,
                    logical_fingerprint=SHA_A,
                ),
            ),
        ),
        report_sha256=SHA_B,
    )
    states = (
        "fixed_cash_and_timing_ready",
        "listed_security_identity_and_market_value_required",
        "cessation_timing_not_matched",
        "contingent_value_realization_unresolved",
        "holder_election_or_proration_unresolved",
        "unlisted_unit_value_unresolved",
    )
    payoff = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="payoff/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
            decisions=tuple(
                SimpleNamespace(
                    instrument_id=instrument_id,
                    request_sequence=index,
                    terminal_candidate_state=state,
                )
                for index, (instrument_id, state) in enumerate(
                    zip(ids[:6], states, strict=True), start=1
                )
            ),
        ),
        report_sha256=SHA_B,
    )
    cash = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="cash/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
            payoff_terms_report_sha256=SHA_B,
            payoff_terms_logical_fingerprint=SHA_A,
            decisions=(
                SimpleNamespace(
                    instrument_id=ids[0],
                    evidence_state="nominal_fixed_cash_terminal_evidence",
                    source_available_at=source_time,
                ),
            ),
        ),
        report_sha256=SHA_B,
    )
    listed = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="listed/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
            payoff_terms_report_sha256=SHA_B,
            payoff_terms_logical_fingerprint=SHA_A,
            decisions=(
                SimpleNamespace(
                    target_instrument_id=ids[1],
                    evidence_state="gross_listed_consideration_reference_value",
                    source_available_at=source_time,
                    price_quality_flags=("adjustment_factors_unverified",),
                ),
            ),
        ),
        report_sha256=SHA_B,
    )
    residual = SimpleNamespace(
        report=SimpleNamespace(
            contract_version="residual/1.0",
            logical_fingerprint=SHA_A,
            evaluated_at=source_time,
            prior_terminal_evidence_report_sha256=SHA_B,
            prior_terminal_evidence_logical_fingerprint=SHA_A,
            payoff_terms_report_sha256=SHA_B,
            payoff_terms_logical_fingerprint=SHA_A,
            decisions=(),
        ),
        report_sha256=SHA_B,
    )
    return {
        "blocker": blocker,
        "sample": sample,
        "payoff": payoff,
        "cash": cash,
        "listed": listed,
        "residual": residual,
    }


def _cli_args() -> list[str]:
    values = []
    for name in (
        "blocker-census",
        "blocker-census-custody-root",
        "source-sample",
        "source-sample-custody-root",
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
    ):
        values.extend((f"--{name}", f"/tmp/{name}"))
    return [
        *values,
        "--evaluated-at",
        "2026-09-14T07:00:00+00:00",
        "--execute",
    ]
