from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_terminal_gap_census_v2 as v2
from tip_api.services import strong_leader_pullback_terminal_gap_census_v3 as service
from tip_api.services import (
    strong_leader_pullback_terminal_population_listed_reference as reference,
)


def _decision(**overrides: object) -> v2.TerminalGapDecisionV2:
    values = {
        "instrument_id": UUID("11111111-1111-5111-8111-111111111111"),
        "population_origin": "legacy_identity_boundary_sample",
        "request_sequence": 1,
        "provider_ticker_locators": ("AAA",),
        "canonical_identity_last_observed_date": date(2025, 1, 2),
        "strategy_window_last_eod_observed_date": date(2025, 1, 2),
        "gap_state": "nominal_fixed_cash_reference_documented",
        "reference_kind": "nominal_fixed_cash",
        "reference_evidence_count": 1,
        "reference_source_available_at": datetime(2025, 1, 3, tzinfo=UTC),
        "reference_quality_flags": (),
        "horizon_1_crossing_path_count": 1,
        "horizon_3_crossing_path_count": 1,
        "horizon_5_crossing_path_count": 2,
        "next_required_gate": "lifecycle_fact_and_label_policy_required",
        **overrides,
    }
    provisional = v2.TerminalGapDecisionV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return v2.TerminalGapDecisionV2.model_validate(
        {
            **values,
            "logical_fingerprint": v2._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _inputs() -> dict[str, object]:
    scs = _decision(
        instrument_id=reference.TARGET_INSTRUMENT_ID,
        population_origin="corrected_eod_boundary",
        request_sequence=None,
        provider_ticker_locators=("SCS",),
        canonical_identity_last_observed_date=date(2025, 12, 10),
        strategy_window_last_eod_observed_date=date(2025, 12, 9),
        gap_state="newly_in_scope_primary_source_unadjudicated",
        reference_kind="none",
        reference_evidence_count=0,
        reference_source_available_at=None,
        horizon_1_crossing_path_count=0,
        horizon_3_crossing_path_count=0,
        horizon_5_crossing_path_count=1,
        next_required_gate="corrected_population_primary_source_adjudication_required",
    )
    prior = SimpleNamespace(
        report_sha256="1" * 64,
        report=SimpleNamespace(
            logical_fingerprint="2" * 64,
            decisions=tuple(sorted((_decision(), scs), key=lambda item: str(item.instrument_id))),
            population_instrument_count=2,
            legacy_population_instrument_count=1,
            newly_in_scope_instrument_count=1,
            structured_case_count=1,
            legacy_exception_case_count=0,
            new_primary_source_case_count=1,
        ),
    )
    listed = SimpleNamespace(
        report_sha256="3" * 64,
        report=SimpleNamespace(
            logical_fingerprint="4" * 64,
            payoff_policy_report_sha256="5" * 64,
            payoff_policy_logical_fingerprint="6" * 64,
            identity=SimpleNamespace(
                source_target_instrument_id=reference.TARGET_INSTRUMENT_ID
            ),
            terminal_reference_case_count=1,
            canonical_terminal_outcome_count=0,
            price_quality_flags=("adjustment_factors_unverified",),
        ),
    )
    policy = SimpleNamespace(
        report_sha256="5" * 64,
        report=SimpleNamespace(
            logical_fingerprint="6" * 64,
            party_relation=SimpleNamespace(
                instrument_id=reference.TARGET_INSTRUMENT_ID,
                acceptance_datetime=datetime(2025, 12, 11, 16, 0, 16, tzinfo=UTC),
            ),
        ),
    )
    return {
        "prior": prior,
        "reference": listed,
        "policy": policy,
        "implementation_revision": "7" * 40,
        "evaluated_at": datetime(2026, 9, 14, 10, tzinfo=UTC),
    }


def test_extends_only_scs_and_recomputes_impact() -> None:
    report = service._build_report(**_inputs())

    scs = next(
        item for item in report.decisions if item.instrument_id == reference.TARGET_INSTRUMENT_ID
    )
    assert scs.gap_state == "gross_listed_consideration_reference_documented"
    assert scs.reference_evidence_count == 1
    assert report.reference_documented_instrument_count == 2
    assert report.remaining_gap_instrument_count == 0
    assert report.documented_horizon_5_crossing_path_count == 3
    assert report.terminal_outcome_count == 0
    assert report.research_admission_count == 0


def test_unexpected_prior_scs_state_fails_closed() -> None:
    inputs = _inputs()
    prior = inputs["prior"]
    decisions = tuple(
        _decision(
            instrument_id=item.instrument_id,
            population_origin=item.population_origin,
            request_sequence=item.request_sequence,
            provider_ticker_locators=item.provider_ticker_locators,
            canonical_identity_last_observed_date=item.canonical_identity_last_observed_date,
            strategy_window_last_eod_observed_date=item.strategy_window_last_eod_observed_date,
            gap_state="holder_election_or_proration_unresolved",
            reference_kind="none",
            reference_evidence_count=0,
            reference_source_available_at=None,
            reference_quality_flags=(),
            horizon_1_crossing_path_count=item.horizon_1_crossing_path_count,
            horizon_3_crossing_path_count=item.horizon_3_crossing_path_count,
            horizon_5_crossing_path_count=item.horizon_5_crossing_path_count,
            next_required_gate="holder_election_or_proration_distribution_required",
        )
        if item.instrument_id == reference.TARGET_INSTRUMENT_ID
        else item
        for item in prior.report.decisions
    )
    inputs["prior"] = SimpleNamespace(
        report_sha256=prior.report_sha256,
        report=SimpleNamespace(**{**vars(prior.report), "decisions": decisions}),
    )

    with pytest.raises(
        service.StrongLeaderPullbackTerminalGapCensusV3Error,
        match="prior SCS decision differs",
    ):
        service._build_report(**inputs)
