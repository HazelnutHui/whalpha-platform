from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tip_api.config import AppConfig
from tip_api.contracts.analytics.v1 import (
    EtfRelationshipExplanationV1,
    EtfRelationshipRecordV1,
    EtfRelationshipWindowMetricV1,
    ExplanationLedgerEntryV1,
    MarketRegimeCompositeV1,
    MarketRegimeDimensionV1,
    MarketRegimeMetricV1,
    MarketRegimePreviewPayloadV1,
    MarketRegimeRelationshipComparisonV1,
    MarketRegimeStateExplanationV1,
    MarketRegimeStateRecordV1,
    PreviewCalculationVersionsV1,
    PreviewEtfBasketEntryV1,
    PreviewEtfPairDefinitionV1,
    PreviewEtfRelationshipV1,
    PreviewParameterFingerprintsV1,
    PreviewQualityGateV1,
    PreviewSourceLogicalFingerprintsV1,
    PreviewUniverseAnalyticsV1,
    PreviewUniverseDefinitionV1,
)
from tip_api.main import create_app
from tip_api.services.market_regime_preview import (
    MarketRegimePreviewError,
    MarketRegimePreviewService,
    _fingerprint,
    _safe_new_output_dir,
    _write_and_read_bundle,
    read_market_regime_preview_bundle,
)
from tip_api.services.relationship_change_summary import (
    RelationshipChangeSummaryError,
    build_relationship_change_summary,
    build_relationship_state_timeline,
)
from tip_api.services.market_regime_preview_cli import main as preview_cli_main


PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
SESSION = date(2026, 8, 21)


def _metric(metric_id: str) -> MarketRegimeMetricV1:
    return MarketRegimeMetricV1(
        metric_id=metric_id, as_of_session=SESSION, lookback_sessions=20,
        raw_value="0.1000", raw_unit="ratio", direction="higher_supportive",
        normalization_method="piecewise_linear", normalization_parameters=(("floor", "0.0000"),),
        normalized_value="60.0000", configured_weight="1.0000", effective_weight="1.0000",
        weighted_contribution="60.0000", actual_observations=20, minimum_observations=20,
        coverage_ratio="1.0000", missing_count=0, availability="available", missing_reason=None,
        source_input_references=("fixture",), reason_codes=("metric_available",),
    )


def _composite(universe_id: str, count: int, score: str, fingerprint: str) -> MarketRegimeCompositeV1:
    dimension_ids = ("trend", "breadth", "volatility", "liquidity_participation", "leadership_dispersion")
    weights = ("0.3000", "0.2500", "0.2000", "0.1500", "0.1000")
    dimensions = tuple(MarketRegimeDimensionV1(
        universe_id=universe_id, dimension_id=dimension_id, as_of_session=SESSION,
        configured_weight=weight, effective_weight=weight, internal_configured_weight_available="1.0000",
        score="60.0000", score_contribution=format(60 * float(weight), ".4f"), minimum_observations=20,
        actual_observations=20, coverage_ratio="1.0000", missing_count=0, availability="available",
        support_status="supporting", explanation_template_id="fixture", rendered_explanation="Fixed fixture.",
        raw_metrics=(_metric(f"{dimension_id}_metric"),), warnings=(), reason_codes=("dimension_available",),
    ) for dimension_id, weight in zip(dimension_ids, weights, strict=True))
    return MarketRegimeCompositeV1(
        parameter_set_fingerprint="1" * 64, as_of_session=SESSION, universe_id=universe_id,
        universe_member_count=count, membership_fingerprint=("a" if universe_id == PRIMARY else "b") * 64,
        activation_pointer_fingerprint="c" * 64, identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64, history_source_fingerprint="f" * 64,
        history_sessions_used=(date(2026, 7, 17), SESSION), regime_score=score,
        configured_weight_available="1.0000", dimensions=dimensions, missing_metric_ids=(),
        unavailable_dimension_ids=(), warnings=(), reason_codes=("composite_available",),
        logical_fingerprint=fingerprint,
    )


def _state(universe_id: str, score: str, composite_fingerprint: str, state_fingerprint: str) -> MarketRegimeStateRecordV1:
    return MarketRegimeStateRecordV1(
        state_parameter_fingerprint="2" * 64, phase1a_parameter_fingerprint="1" * 64,
        as_of_session=SESSION, universe_id=universe_id, composite=score,
        instantaneous_candidate_state="balanced", confirmed_state="balanced", previous_confirmed_state="balanced",
        state_is_provisional=False, transition_status="held", transition_rule_id="state_hold",
        pending_target_state=None, consecutive_confirmation_sessions=0, required_confirmation_sessions=0,
        entry_threshold="70.0000", exit_threshold="65.0000", boundary_operator=">=",
        initialization_status="initialized", state_availability="available", stale_state=False,
        in_hysteresis_band=False, confirmation_sessions_remaining=0, threshold_distances=(),
        supporting_dimension_ids=("trend",), conflicting_dimension_ids=("liquidity_participation",),
        reason_codes=("confirmed_state_held",), source_composite_fingerprint=composite_fingerprint,
        logical_fingerprint=state_fingerprint,
    )


def _universe(universe_id: str, display_name: str, count: int, score: str, ordinal: int) -> PreviewUniverseAnalyticsV1:
    composite_fp = ("3" if ordinal == 0 else "4") * 64
    state_fp = ("5" if ordinal == 0 else "6") * 64
    composite = _composite(universe_id, count, score, composite_fp)
    state = _state(universe_id, score, composite_fp, state_fp)
    explanation = MarketRegimeStateExplanationV1(
        state_parameter_fingerprint="2" * 64, as_of_session=SESSION, universe_id=universe_id,
        composite=score, candidate_state="balanced", confirmed_state="balanced",
        candidate_band_text="Fixed Balanced band.", transition_text="State held.",
        supporting_dimension_ids=("trend",), conflicting_dimension_ids=("liquidity_participation",),
        threshold_distances=(), confirmation_sessions_remaining=0, in_hysteresis_band=False,
        source_input_references=("fixture",), reason_codes=("confirmed_state_held",),
        disclaimers=("Research context, not a recommendation.",),
    )
    return PreviewUniverseAnalyticsV1(
        definition=PreviewUniverseDefinitionV1(
            universe_id=universe_id, display_name=display_name, catalog_order=ordinal,
            is_default=ordinal == 0, member_count=count,
            membership_fingerprint=("a" if ordinal == 0 else "b") * 64,
        ), composite=composite, current_state=state, current_state_explanation=explanation,
        state_history=(state,), dimension_explanations=(),
    )


def _relationship(ordinal: int) -> PreviewEtfRelationshipV1:
    pair_id = f"pair_{ordinal:02d}"
    definition = PreviewEtfPairDefinitionV1(
        pair_id=pair_id, registry_order=ordinal, left_ticker=f"L{ordinal}", right_ticker=f"R{ordinal}",
        relationship_family="fixture_family", economic_rationale="Preregistered fixture relationship.",
        expected_interpretation="Relative performance only.", forbidden_interpretation="No causality.",
        applicable_windows=(5, 10, 20), availability_requirement="complete paired positive closes",
        regime_orientation="neutral",
    )
    windows = tuple(EtfRelationshipWindowMetricV1(
        window_sessions=window, start_session=date(2026, 7, 17), end_session=SESSION,
        left_start_close="100.0000", left_end_close="102.0000", right_start_close="100.0000",
        right_end_close="101.0000", left_return="0.0200000000", right_return="0.0100000000",
        relative_return="0.0100000000", daily_return_observation_count=window,
        rolling_correlation="0.5000000000", direction_combination="both_positive",
        availability="available", missing_reason=None, reason_codes=("window_available",),
    ) for window in (5, 10, 20))
    current = EtfRelationshipRecordV1(
        parameter_fingerprint="7" * 64, pair_id=pair_id, as_of_session=SESSION,
        left_ticker=definition.left_ticker, right_ticker=definition.right_ticker,
        relationship_family=definition.relationship_family, windows=windows, ratio_level="1.0099",
        ratio_robust_z=None, ratio_percentile=None, correlation_20_prior_5="0.6000",
        correlation_change_5="-0.1000", correlation_perturbations=((15, "0.5000"),),
        perturbation_state_consistent=True, relationship_state="synchronous_strengthening",
        previous_relationship_state="neutral", confidence="low", availability="available",
        missing_reason=None, paired_close_observation_count=26, source_first_session=date(2026, 7, 17),
        source_last_session=SESSION, source_history_fingerprint="8" * 64,
        reason_codes=("short_history_low_confidence",), warnings=("short_history",),
        logical_fingerprint=f"{ordinal + 10:064x}",
    )
    explanation = EtfRelationshipExplanationV1(
        parameter_fingerprint="7" * 64, pair_id=pair_id, as_of_session=SESSION,
        relationship_state="synchronous_strengthening", left_observation="Left rose.",
        right_observation="Right rose.", relative_strength_observation="Left led.",
        correlation_observation="Correlation is positive.", cross_window_observation="Windows agree.",
        supporting_evidence=("Both legs rose.",), counterevidence=("History is short.",),
        reason_codes=("short_history_low_confidence",), source_input_references=("fixture",),
        disclaimers=("statistical_relationship_not_causal",),
    )
    return PreviewEtfRelationshipV1(definition=definition, current=current, explanation=explanation)


def _payload() -> MarketRegimePreviewPayloadV1:
    universes = (_universe(PRIMARY, "Common Shares", 1718, "63.9102", 0), _universe(SECONDARY, "Common Shares + ADRs", 1831, "64.8167", 1))
    relationships = tuple(_relationship(index) for index in range(16))
    comparisons = tuple(MarketRegimeRelationshipComparisonV1(
        as_of_session=SESSION, universe_id=universe.definition.universe_id,
        regime_candidate_state="balanced", regime_confirmed_state="balanced",
        regime_composite=universe.current_state.composite or "0.0000",
        regime_state_record_fingerprint=universe.current_state.logical_fingerprint,
        pair_id=relationship.definition.pair_id, relationship_state=relationship.current.relationship_state,
        alignment="neutral", reason_codes=("contemporaneous_only",),
    ) for universe in universes for relationship in relationships)
    source = PreviewSourceLogicalFingerprintsV1(phase1a="9" * 64, phase1b="a" * 64, phase2="b" * 64)
    candidate = MarketRegimePreviewPayloadV1(
        as_of_session=SESSION, input_first_session=date(2026, 7, 17), input_last_session=SESSION,
        input_session_count=26, default_universe_id=PRIMARY, universe_order=(PRIMARY, SECONDARY),
        calculation_versions=PreviewCalculationVersionsV1(phase1a="a", phase1b="b", phase2="c"),
        parameter_fingerprints=PreviewParameterFingerprintsV1(phase1a="1" * 64, phase1b="2" * 64, phase2="7" * 64),
        source_logical_fingerprints=source, universes=universes,
        etf_basket=tuple(PreviewEtfBasketEntryV1(ticker=f"E{index}", family="fixture", role="fixture") for index in range(30)),
        relationships=relationships, relationship_history=tuple(item.current for item in relationships),
        relationship_comparisons=comparisons, warnings=("short history",),
        quality_gates=(PreviewQualityGateV1(gate_id="source", status="passed", reason_codes=("verified",)),),
        logical_fingerprint="0" * 64,
    )
    return candidate.model_copy(update={"logical_fingerprint": _fingerprint(candidate.model_dump(mode="json", exclude={"logical_fingerprint"}))})


def _new_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="mrom-preview-test-", dir="/tmp"))


def _cleanup(path: Path) -> None:
    if path.is_symlink():
        path.unlink(); return
    if not path.exists(): return
    for item in path.iterdir(): item.chmod(0o600); item.unlink()
    path.rmdir()


def test_preview_round_trip_is_deterministic_and_query_is_isolated():
    first, second = _new_dir(), _new_dir(); payload = _payload(); source = payload.source_logical_fingerprints
    try:
        one = _write_and_read_bundle(first, payload, datetime(2026, 8, 25, tzinfo=UTC), source)
        two = _write_and_read_bundle(second, payload, datetime(2026, 8, 25, tzinfo=UTC) + timedelta(seconds=1), source)
        assert (first / "market-regime-opportunity-map.json").read_bytes() == (second / "market-regime-opportunity-map.json").read_bytes()
        assert one.payload.logical_fingerprint == two.payload.logical_fingerprint
        service = MarketRegimePreviewService(one)
        primary, secondary = service.overview(), service.overview(SECONDARY)
        assert primary.selected_universe_id == PRIMARY and secondary.selected_universe_id == SECONDARY
        assert primary.regime.composite.regime_score == "63.9102" and secondary.regime.composite.regime_score == "64.8167"
        assert [item.current.logical_fingerprint for item in primary.relationships] == [item.current.logical_fingerprint for item in secondary.relationships]
        assert len(primary.relationships) == 16 and len(service.relationship_detail("pair_00").history) == 1
        assert primary.relationships[0].change_summary.current_state_run_session_count == 1
        assert primary.relationships[0].change_summary.state_run_reaches_history_start is True
        assert primary.relationships[0].state_timeline.displayed_session_count == 1
        assert primary.relationships[0].state_timeline.truncated_before is False
    finally:
        _cleanup(first); _cleanup(second)


def test_preview_reader_rejects_extra_corrupt_missing_and_unsafe_paths():
    source_dir = _new_dir(); payload = _payload()
    try:
        _write_and_read_bundle(source_dir, payload, datetime.now(UTC), payload.source_logical_fingerprints)
        (source_dir / "extra.json").write_text("{}")
        with pytest.raises(MarketRegimePreviewError, match="extras"):
            read_market_regime_preview_bundle(source_dir)
        (source_dir / "extra.json").unlink()
        manifest_path = source_dir / "preview-manifest.json"
        manifest_raw = manifest_path.read_bytes()
        manifest_path.unlink()
        with pytest.raises(MarketRegimePreviewError, match="incomplete"):
            read_market_regime_preview_bundle(source_dir)
        manifest_path.write_bytes(manifest_raw)
        manifest_path.chmod(0o400)
        payload_path = source_dir / "market-regime-opportunity-map.json"; payload_path.chmod(0o600)
        raw = payload_path.read_bytes(); payload_path.write_bytes(raw[:-2] + b"x\n"); payload_path.chmod(0o400)
        with pytest.raises(MarketRegimePreviewError, match="malformed|canonical|custody"):
            read_market_regime_preview_bundle(source_dir)
        nested = Path(tempfile.mkdtemp(prefix="nested-preview-", dir="/tmp")) / "child"
        nested.mkdir()
        with pytest.raises(MarketRegimePreviewError, match="direct child"):
            read_market_regime_preview_bundle(nested)
        nested.rmdir(); nested.parent.rmdir()
    finally:
        _cleanup(source_dir)
    real = _new_dir(); link = Path(f"{real}-link"); link.symlink_to(real, target_is_directory=True)
    try:
        with pytest.raises(MarketRegimePreviewError, match="symlink"):
            read_market_regime_preview_bundle(link)
    finally:
        _cleanup(link); _cleanup(real)


def test_api_is_absent_by_default_and_enabled_bundle_is_read_only():
    target = _new_dir(); payload = _payload()
    try:
        _write_and_read_bundle(target, payload, datetime.now(UTC), payload.source_logical_fingerprints)
        default = TestClient(create_app(AppConfig()))
        assert default.get("/api/v1/health").status_code == 200
        assert default.get("/api/v1/private/market-regime/overview").status_code == 404
        enabled = TestClient(create_app(AppConfig(enable_market_regime_preview_routes=True, market_regime_preview_bundle=target)))
        response = enabled.get("/api/v1/private/market-regime/overview", params={"universe_id": SECONDARY})
        assert response.status_code == 200
        assert response.json()["selected_universe_id"] == SECONDARY
        assert len(response.json()["relationships"]) == 16
        assert enabled.get("/api/v1/private/market-regime/overview", params={"universe_id": "unknown"}).status_code == 422
        assert enabled.get("/api/v1/private/market-regime/relationships/pair_00").status_code == 200
    finally:
        _cleanup(target)


def test_relationship_change_summary_uses_retained_history_without_thresholds():
    base = _relationship(0).current
    values = ("0.0100000000", "0.0000000000", "0.0050000000", "0.0100000000", "0.0150000000", "0.0200000000")
    history = []
    for index, value in enumerate(values):
        windows = tuple(
            item.model_copy(update={"relative_return": value}) for item in base.windows
        )
        history.append(base.model_copy(update={
            "as_of_session": date(2026, 8, 16 + index),
            "windows": windows,
            "relationship_state": "neutral" if index == 0 else "synchronous_strengthening",
            "logical_fingerprint": f"{index + 1:064x}",
        }))
    summary = build_relationship_change_summary(current=history[-1], history=history)
    five = summary.windows[0]
    assert summary.current_state_run_started_session == date(2026, 8, 17)
    assert summary.current_state_run_session_count == 5
    assert summary.state_run_reaches_history_start is False
    assert summary.state_changed_this_session is False
    assert summary.current_5_session_leader == "left"
    assert five.change_1_session == "0.0050000000"
    assert five.change_5_sessions == "0.0100000000"
    assert five.leadership_change_1 == "strengthening"
    assert five.leadership_change_5 == "strengthening"


def test_relationship_state_timeline_is_bounded_current_and_window_complete():
    base = _relationship(0).current
    history = []
    for index in range(12):
        windows = tuple(
            item.model_copy(update={"relative_return": f"{index / 100:.10f}"})
            for item in base.windows
        )
        history.append(base.model_copy(update={
            "as_of_session": date(2026, 8, 1 + index),
            "windows": windows,
            "relationship_state": "neutral" if index < 8 else "divergence",
            "confidence": "low",
            "logical_fingerprint": f"{index + 1:064x}",
        }))
    timeline = build_relationship_state_timeline(current=history[-1], history=history)
    assert timeline.retained_first_session == date(2026, 8, 1)
    assert timeline.retained_session_count == 12
    assert timeline.displayed_session_count == 10
    assert timeline.truncated_before is True
    assert timeline.points[0].as_of_session == date(2026, 8, 3)
    assert timeline.points[-1].as_of_session == date(2026, 8, 12)
    assert timeline.points[6].changed_from_prior_retained_session is True
    assert tuple(item.window_sessions for item in timeline.points[-1].windows) == (5, 10, 20)
    with pytest.raises(RelationshipChangeSummaryError, match="display limit"):
        build_relationship_state_timeline(current=history[-1], history=history, display_limit=11)


def test_cli_rejects_apply_and_config_requires_explicit_absolute_bundle():
    with pytest.raises(SystemExit) as error:
        preview_cli_main(["--apply"])
    assert error.value.code == 2
    with pytest.raises(ValueError, match="explicit bundle"):
        AppConfig(enable_market_regime_preview_routes=True)
    with pytest.raises(ValueError, match="absolute"):
        AppConfig(market_regime_preview_bundle=Path("relative"))
    for unsafe in (Path("/data/market-preview"), Path.cwd() / "market-preview"):
        with pytest.raises(MarketRegimePreviewError, match="direct child of /tmp"):
            _safe_new_output_dir(unsafe)
