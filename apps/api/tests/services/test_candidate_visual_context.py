from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateOpportunityStage,
    CandidateStateAvailability,
    VisualContextAvailability,
)
from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tip_api.services.candidate_visual_context import (
    CandidateVisualContextCalculationError,
    calculate_candidate_visual_context,
)
from tip_api.services.candidate_visual_context_audit import (
    CandidateVisualContextAuditError,
    read_candidate_visual_context_audit,
    write_candidate_visual_context_audit,
)
from tip_api.services.candidate_visual_context_oracle import (
    compare_with_independent_candidate_visual_context_oracle,
)
from tests.services import test_opportunity_candidate_audit as fixture


def _fingerprint(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _inputs():
    panel = fixture._panel()
    batches, _, _ = fixture._actuals(panel)
    candidate_batch = batches[0]
    current_states = []
    for candidate in candidate_batch.candidates:
        single = candidate_batch.model_copy(update={"candidates": (candidate,)})
        current_states.extend(fixture._state_case(panel, single).actual_records)
    entry = calculate_candidate_entry_geometry(
        panel=panel,
        candidate_batch=candidate_batch,
        state_records=tuple(current_states),
    )
    history = []
    for state in current_states:
        for session in panel.sessions[-3:-1]:
            history.append(
                state.model_copy(
                    update={
                        "as_of_session": session,
                        "logical_fingerprint": _fingerprint(
                            f"{state.instrument_id}:{session.isoformat()}"
                        ),
                    }
                )
            )
        history.append(state)
    return panel, candidate_batch, entry, tuple(history)


def test_visual_context_binds_real_twenty_session_path_and_observed_age() -> None:
    panel, candidates, entry, states = _inputs()

    result = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
    )

    assert result.record_count == len(candidates.candidates)
    assert result.price_path_availability_counts == {"available": len(result.records)}
    assert result.state_age_availability_counts == {"available": len(result.records)}
    assert result.strategy_score_input is False
    assert result.outcome_or_performance_claim is False
    for record in result.records:
        assert record.price_path_availability is VisualContextAvailability.AVAILABLE
        assert len(record.price_path) == 20
        assert record.price_path[0].session_date == panel.sessions[-20]
        assert record.price_path[-1].session_date == panel.as_of_session
        assert record.price_path[-1].close == record.reference_levels.current_close
        assert record.observed_state_age.observed_age_sessions == 3
        assert record.observed_state_age.left_censored is True


def test_visual_context_stops_observed_age_at_a_stage_change() -> None:
    panel, candidates, entry, states = _inputs()
    target = candidates.candidates[0].instrument_id
    changed_session = panel.sessions[-2]
    changed = tuple(
        row.model_copy(update={"final_stage": CandidateOpportunityStage.INVALIDATED})
        if row.instrument_id == target and row.as_of_session == changed_session
        else row
        for row in states
    )

    result = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=changed,
    )

    record = next(row for row in result.records if row.instrument_id == target)
    assert record.observed_state_age.observed_age_sessions == 1
    assert record.observed_state_age.first_observed_session == panel.as_of_session
    assert record.observed_state_age.left_censored is False


def test_visual_context_fails_closed_for_missing_price_path_without_losing_state_age() -> None:
    panel, candidates, entry, states = _inputs()
    target = candidates.candidates[0].instrument_id
    missing_session = panel.sessions[-10]
    partial = replace(
        panel,
        bars=tuple(
            row
            for row in panel.bars
            if not (row.instrument_id == target and row.session_date == missing_session)
        ),
    )

    result = calculate_candidate_visual_context(
        panel=partial,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
    )

    record = next(row for row in result.records if row.instrument_id == target)
    assert record.price_path_availability is VisualContextAvailability.UNAVAILABLE
    assert record.price_path == ()
    assert record.reference_levels is None
    assert record.price_path_missing_reason_codes == (
        "missing_contiguous_twenty_session_close_history",
    )
    assert record.state_age_availability is VisualContextAvailability.AVAILABLE


def test_visual_context_preserves_an_explicitly_unavailable_current_state() -> None:
    panel, candidates, _, states = _inputs()
    target = candidates.candidates[0].instrument_id
    current_session = panel.as_of_session
    current = next(
        row
        for row in states
        if row.instrument_id == target and row.as_of_session == current_session
    )
    unavailable = current.model_copy(
        update={
            "base_score": None,
            "confidence": None,
            "source_candidate_fingerprint": None,
            "state_availability": CandidateStateAvailability.UNAVAILABLE,
            "stale_state": True,
            "consecutive_missing_sessions": 1,
            "logical_fingerprint": _fingerprint("unavailable-current-state"),
        }
    )
    unavailable_states = tuple(
        unavailable
        if row.instrument_id == target and row.as_of_session == current_session
        else row
        for row in states
    )
    entry = calculate_candidate_entry_geometry(
        panel=panel,
        candidate_batch=candidates,
        state_records=tuple(
            row for row in unavailable_states if row.as_of_session == current_session
        ),
    )

    result = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=unavailable_states,
    )

    record = next(row for row in result.records if row.instrument_id == target)
    assert record.price_path_availability is VisualContextAvailability.AVAILABLE
    assert record.state_age_availability is VisualContextAvailability.UNAVAILABLE
    assert record.observed_state_age is None
    assert record.state_age_missing_reason_codes == (
        "current_candidate_state_unavailable_or_stale",
    )


def test_visual_context_is_input_permutation_invariant() -> None:
    panel, candidates, entry, states = _inputs()
    expected = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
    )

    actual = calculate_candidate_visual_context(
        panel=replace(panel, bars=tuple(reversed(panel.bars))),
        candidate_batch=candidates.model_copy(
            update={"candidates": tuple(reversed(candidates.candidates))}
        ),
        entry_geometry_batch=entry.model_copy(
            update={"records": tuple(reversed(entry.records))}
        ),
        state_history=tuple(reversed(states)),
    )

    assert actual == expected


def test_visual_context_rejects_entry_lineage_drift() -> None:
    panel, candidates, entry, states = _inputs()

    with pytest.raises(CandidateVisualContextCalculationError, match="lineage"):
        calculate_candidate_visual_context(
            panel=panel,
            candidate_batch=candidates,
            entry_geometry_batch=entry.model_copy(
                update={"source_history_fingerprint": "f" * 64}
            ),
            state_history=states,
        )


def test_independent_visual_context_oracle_reconciles_every_record() -> None:
    panel, candidates, entry, states = _inputs()
    actual = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
    )

    comparison = compare_with_independent_candidate_visual_context_oracle(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
        actual=actual,
    )

    assert comparison.record_count == len(candidates.candidates)
    assert comparison.mismatch_count == 0
    assert comparison.mismatches == ()
    assert comparison.input_permutation_match is True
    assert comparison.production_calculator_imported is False
    source = inspect.getsource(
        __import__(
            "tip_api.services.candidate_visual_context_oracle",
            fromlist=["dummy"],
        )
    )
    assert "from tip_api.services.candidate_visual_context import" not in source


def test_visual_context_audit_atomically_writes_and_formally_rereads() -> None:
    panel, candidates, entry, states = _inputs()
    batch = calculate_candidate_visual_context(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
    )
    oracle = compare_with_independent_candidate_visual_context_oracle(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        state_history=states,
        actual=batch,
    )
    candidate_source = Path(tempfile.mkdtemp(prefix="visual-candidate-source-", dir="/tmp"))
    entry_source = Path(tempfile.mkdtemp(prefix="visual-entry-source-", dir="/tmp"))
    panel_source = Path(tempfile.mkdtemp(prefix="visual-panel-source-", dir="/tmp"))
    output = Path("/tmp") / f"visual-context-audit-test-{uuid4().hex}"
    candidate_manifest = {
        "logical_content_fingerprint": "1" * 64,
        "as_of_session": candidates.as_of_session.isoformat(),
        "universe_ids": [candidates.universe_id],
        "candidate_batch_fingerprints": [candidates.logical_fingerprint],
    }
    entry_manifest = {
        "logical_content_fingerprint": "2" * 64,
        "as_of_session": entry.as_of_session.isoformat(),
        "universe_ids": [entry.universe_id],
        "batch_fingerprints": [entry.logical_fingerprint],
    }
    panel_manifest = {
        "logical_content_fingerprint": "3" * 64,
        "source_boundary": {
            "as_of_session": panel.as_of_session.isoformat(),
            "history_source_fingerprint": panel.history_source_fingerprint,
            "universes": [{"universe_id": candidates.universe_id}],
        },
    }
    try:
        (candidate_source / "candidate-audit-manifest.json").write_text(
            json.dumps(candidate_manifest), encoding="utf-8"
        )
        (entry_source / "entry-geometry-audit-manifest.json").write_text(
            json.dumps(entry_manifest), encoding="utf-8"
        )
        (panel_source / "manifest.json").write_text(
            json.dumps(panel_manifest), encoding="utf-8"
        )
        manifest = write_candidate_visual_context_audit(
            output_dir=output,
            candidate_audit_dir=candidate_source,
            candidate_audit_manifest=candidate_manifest,
            entry_geometry_audit_dir=entry_source,
            entry_geometry_audit_manifest=entry_manifest,
            panel_cache_entry_dir=panel_source,
            panel_cache_manifest=panel_manifest,
            batches=(batch,),
            oracle_reports=(oracle,),
            generated_at=datetime(2026, 8, 30, tzinfo=UTC),
        )

        assert manifest["completion_status"] == "completed"
        assert manifest["oracle_mismatch_count"] == 0
        assert manifest["record_count"] == len(candidates.candidates)
        assert read_candidate_visual_context_audit(output) == manifest
        assert {path.stat().st_mode & 0o777 for path in output.iterdir()} == {0o400}
        with pytest.raises(CandidateVisualContextAuditError, match="already exist"):
            write_candidate_visual_context_audit(
                output_dir=output,
                candidate_audit_dir=candidate_source,
                candidate_audit_manifest=candidate_manifest,
                entry_geometry_audit_dir=entry_source,
                entry_geometry_audit_manifest=entry_manifest,
                panel_cache_entry_dir=panel_source,
                panel_cache_manifest=panel_manifest,
                batches=(batch,),
                oracle_reports=(oracle,),
                generated_at=datetime(2026, 8, 30, tzinfo=UTC),
            )
    finally:
        shutil.rmtree(candidate_source, ignore_errors=True)
        shutil.rmtree(entry_source, ignore_errors=True)
        shutil.rmtree(panel_source, ignore_errors=True)
        if output.exists():
            shutil.rmtree(output)
