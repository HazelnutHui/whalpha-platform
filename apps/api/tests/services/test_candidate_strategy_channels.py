from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelBatchV1,
    StrategyChannel,
    StrategyChannelStatus,
)
from tip_api.services.candidate_entry_geometry import (
    calculate_candidate_entry_geometry,
)
from tip_api.services.candidate_strategy_channels import (
    CandidateStrategyChannelCalculationError,
    build_candidate_strategy_channel_consumer,
    calculate_candidate_strategy_channels,
)
from tip_api.services.candidate_strategy_channels_oracle import (
    compare_with_independent_strategy_channel_oracle,
)
from tip_api.services.candidate_strategy_channel_audit import (
    CandidateStrategyChannelAuditError,
    read_candidate_strategy_channel_audit,
    write_candidate_strategy_channel_audit,
)
from tests.services import test_opportunity_candidate_audit as fixture


def _inputs():
    panel = fixture._panel()
    batches, _, _ = fixture._actuals(panel)
    candidate_batch = batches[0]
    states = []
    for candidate in candidate_batch.candidates:
        single = candidate_batch.model_copy(update={"candidates": (candidate,)})
        states.extend(fixture._state_case(panel, single).actual_records)
    entry = calculate_candidate_entry_geometry(
        panel=panel,
        candidate_batch=candidate_batch,
        state_records=tuple(states),
    )
    return candidate_batch, entry


def test_strategy_preview_is_explicit_explainable_and_channel_local() -> None:
    candidates, entry = _inputs()

    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    assert isinstance(batch, CandidateStrategyChannelBatchV1)
    assert len(batch.records) == len(candidates.candidates) * 6
    grouped = defaultdict(list)
    for row in batch.records:
        grouped[row.instrument_id].append(row)
        assert row.first_rejection_code
        assert row.required_manual_check_codes
        assert row.market_fit.value == "unavailable"
        assert row.market_fit_separate_from_channel_score is True
    assert all(
        tuple(row.channel for row in rows) == tuple(StrategyChannel)
        for rows in grouped.values()
    )

    technical = [
        row
        for row in batch.records
        if row.channel
        in {
            StrategyChannel.MOMENTUM_BREAKOUT,
            StrategyChannel.STRONG_STOCK_PULLBACK,
            StrategyChannel.TREND_CONTINUATION,
        }
    ]
    assessable = [
        row for row in technical if row.status is not StrategyChannelStatus.UNAVAILABLE
    ]
    assert assessable
    assert all(row.channel_score is not None for row in assessable)
    assert all(
        row.channel_score is None
        for row in technical
        if row.status is StrategyChannelStatus.UNAVAILABLE
    )
    assert all(row.evidence for row in technical)
    assert "cross_channel_score_comparison_prohibited" in batch.warnings


def test_unsupported_channels_remain_explicitly_unavailable() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    unavailable_channels = {
        StrategyChannel.TECHNICAL_REVERSAL,
        StrategyChannel.FUNDAMENTAL_VALUE_REVERSAL,
        StrategyChannel.DEFENSIVE_ROTATION,
    }
    rows = [row for row in batch.records if row.channel in unavailable_channels]
    assert rows
    assert all(row.status is StrategyChannelStatus.UNAVAILABLE for row in rows)
    assert all(row.channel_score is None and row.within_channel_rank is None for row in rows)
    assert all(row.missing_required_evidence_codes for row in rows)
    assert all(
        evidence.availability.value == "unavailable"
        for row in rows
        for evidence in row.evidence
    )


def test_rankable_results_are_contiguous_only_inside_each_channel() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    for channel in StrategyChannel:
        ranks = sorted(
            row.within_channel_rank
            for row in batch.records
            if row.channel is channel and row.within_channel_rank is not None
        )
        assert ranks == list(range(1, len(ranks) + 1))


def test_bounded_consumer_keeps_counts_but_displays_at_most_eight() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    consumer = build_candidate_strategy_channel_consumer(batch)

    assert consumer.source_batch_logical_fingerprint == batch.logical_fingerprint
    assert tuple(view.channel for view in consumer.channels) == tuple(StrategyChannel)
    for view in consumer.channels:
        assert view.status_counts == batch.status_counts[view.channel]
        assert len(view.displayed_records) <= 8
        assert tuple(row.within_channel_rank for row in view.displayed_records) == tuple(
            range(1, len(view.displayed_records) + 1)
        )
    unavailable = {
        view.channel: view
        for view in consumer.channels
        if view.channel
        in {
            StrategyChannel.TECHNICAL_REVERSAL,
            StrategyChannel.FUNDAMENTAL_VALUE_REVERSAL,
            StrategyChannel.DEFENSIVE_ROTATION,
        }
    }
    assert all(view.qualifying_count == 0 for view in unavailable.values())
    assert all(not view.displayed_records for view in unavailable.values())


def test_strategy_preview_is_input_permutation_invariant() -> None:
    candidates, entry = _inputs()
    expected = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )
    permuted_candidates = candidates.model_copy(
        update={"candidates": tuple(reversed(candidates.candidates))}
    )
    permuted_entry = entry.model_copy(
        update={"records": tuple(reversed(entry.records))}
    )

    actual = calculate_candidate_strategy_channels(
        candidate_batch=permuted_candidates,
        entry_geometry_batch=permuted_entry,
    )

    assert actual == expected


def test_strategy_preview_rejects_cross_batch_entry_geometry() -> None:
    candidates, entry = _inputs()
    mismatched = entry.model_copy(
        update={"source_candidate_batch_fingerprint": "f" * 64}
    )

    with pytest.raises(CandidateStrategyChannelCalculationError, match="not bound"):
        calculate_candidate_strategy_channels(
            candidate_batch=candidates,
            entry_geometry_batch=mismatched,
        )


def test_independent_strategy_oracle_reconciles_scores_statuses_and_ranks() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    oracle = compare_with_independent_strategy_channel_oracle(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        actual=batch,
    )

    assert oracle.record_count == len(candidates.candidates) * len(StrategyChannel)
    assert oracle.mismatch_count == 0
    assert not oracle.mismatches
    assert oracle.input_permutation_match is True
    assert oracle.production_calculator_imported is False
    assert len(oracle.oracle_fingerprint) == 64


def test_independent_strategy_oracle_detects_production_output_drift() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )
    index = next(
        index
        for index, row in enumerate(batch.records)
        if row.channel_score is not None
    )
    records = list(batch.records)
    records[index] = records[index].model_copy(update={"channel_score": "0.0000"})
    tampered = batch.model_copy(update={"records": tuple(records)})

    oracle = compare_with_independent_strategy_channel_oracle(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        actual=tampered,
    )

    assert oracle.mismatch_count == 1
    assert oracle.mismatches[0].endswith(":channel_score")


def test_strategy_audit_atomically_writes_and_formally_rereads() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )
    consumer = build_candidate_strategy_channel_consumer(batch)
    oracle = compare_with_independent_strategy_channel_oracle(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        actual=batch,
    )
    candidate_source = Path(
        tempfile.mkdtemp(prefix="strategy-candidate-source-", dir="/tmp")
    )
    entry_source = Path(
        tempfile.mkdtemp(prefix="strategy-entry-source-", dir="/tmp")
    )
    output = Path("/tmp") / f"strategy-audit-test-{uuid4().hex}"
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
    (candidate_source / "candidate-audit-manifest.json").write_bytes(
        (json.dumps(candidate_manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    (entry_source / "entry-geometry-audit-manifest.json").write_bytes(
        (json.dumps(entry_manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    try:
        manifest = write_candidate_strategy_channel_audit(
            output_dir=output,
            candidate_audit_dir=candidate_source,
            candidate_audit_manifest=candidate_manifest,
            entry_geometry_audit_dir=entry_source,
            entry_geometry_audit_manifest=entry_manifest,
            batches=(batch,),
            consumers=(consumer,),
            oracle_reports=(oracle,),
            generated_at=datetime(2026, 8, 28, tzinfo=UTC),
        )

        assert manifest["completion_status"] == "completed"
        assert manifest["oracle_mismatch_count"] == 0
        assert manifest["production_calculator_imported_by_oracle"] is False
        assert read_candidate_strategy_channel_audit(output) == manifest
        assert {path.stat().st_mode & 0o777 for path in output.iterdir()} == {0o400}
        with pytest.raises(CandidateStrategyChannelAuditError, match="already exist"):
            write_candidate_strategy_channel_audit(
                output_dir=output,
                candidate_audit_dir=candidate_source,
                candidate_audit_manifest=candidate_manifest,
                entry_geometry_audit_dir=entry_source,
                entry_geometry_audit_manifest=entry_manifest,
                batches=(batch,),
                consumers=(consumer,),
                oracle_reports=(oracle,),
                generated_at=datetime(2026, 8, 28, tzinfo=UTC),
            )
    finally:
        for directory in (output, candidate_source, entry_source):
            if directory.exists():
                for path in directory.iterdir():
                    path.chmod(0o600)
                    path.unlink()
                directory.rmdir()
