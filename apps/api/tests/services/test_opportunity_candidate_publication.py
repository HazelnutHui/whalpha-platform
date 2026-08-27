from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    OpportunityCandidatePublicationSourceV1,
    OpportunityCandidatePublicationV1_1,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_CALCULATION_VERSION,
    CANDIDATE_CONTRACT_VERSION,
    CANDIDATE_PARAMETER_FINGERPRINT,
    CANDIDATE_PARAMETER_SET_ID,
    CANDIDATE_STATE_CALCULATION_VERSION,
    CANDIDATE_STATE_CONTRACT_VERSION,
    CANDIDATE_STATE_PARAMETER_FINGERPRINT,
    CANDIDATE_STATE_PARAMETER_SET_ID,
)
from tip_api.services.opportunity_candidate_publication import (
    build_opportunity_candidate_publication,
)
from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tip_api.services.opportunity_candidate_snapshot_split import (
    build_split_candidate_snapshot,
    reconstruct_full_candidate_publication,
)
from tests.services import test_opportunity_candidate_audit as fixture


def test_bounded_publication_uses_stable_id_ranks_and_structured_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    panel = fixture._panel()
    batches, risks, _ = fixture._actuals(panel)
    states = []
    for batch in batches:
        for candidate in batch.candidates:
            single = batch.model_copy(update={"candidates": (candidate,)})
            states.extend(fixture._state_case(panel, single).actual_records)
    manifest = {
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_ids": [fixture.PRIMARY, fixture.SECONDARY],
        "logical_content_fingerprint": "1" * 64,
        "candidate_history_fingerprint": "2" * 64,
        "candidate_state_history_fingerprint": "3" * 64,
        "risk_results_fingerprint": "4" * 64,
        "oracle_fingerprint": "5" * 64,
        "oracle_mismatch_count": 0,
        "shared_raw_fact_match": True,
        "input_permutation_match": True,
        "equivalence_flags": {
            "append_full_replay_match": True,
            "restart_replay_match": True,
            "future_prefix_stable": True,
            "input_permutation_match": True,
        },
        "candidate_contract_version": CANDIDATE_CONTRACT_VERSION,
        "candidate_calculation_version": CANDIDATE_CALCULATION_VERSION,
        "candidate_parameter_set_id": CANDIDATE_PARAMETER_SET_ID,
        "candidate_parameter_fingerprint": CANDIDATE_PARAMETER_FINGERPRINT,
        "candidate_state_contract_version": CANDIDATE_STATE_CONTRACT_VERSION,
        "candidate_state_calculation_version": CANDIDATE_STATE_CALCULATION_VERSION,
        "candidate_state_parameter_set_id": CANDIDATE_STATE_PARAMETER_SET_ID,
        "candidate_state_parameter_fingerprint": CANDIDATE_STATE_PARAMETER_FINGERPRINT,
    }
    monkeypatch.setattr(
        "tip_api.services.opportunity_candidate_publication.read_opportunity_candidate_audit",
        lambda _: manifest,
    )
    (tmp_path / "candidate-audit-manifest.json").write_text("{}\n")
    (tmp_path / "candidate-score-history.json").write_text(
        json.dumps({"records": [row.model_dump(mode="json") for row in batches]})
    )
    (tmp_path / "candidate-state-history.json").write_text(
        json.dumps({"records": [row.model_dump(mode="json") for row in states]})
    )
    (tmp_path / "current-risk-mode-results.json").write_text(
        json.dumps({"records": [row.model_dump(mode="json") for row in risks]})
    )
    (tmp_path / "source-input-manifest.json").write_text(
        json.dumps(
            {
                "panels": [
                    {
                        "as_of_session": panel.as_of_session.isoformat(),
                        "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
                        "identity_logical_fingerprint": panel.identity_logical_fingerprint,
                        "eod_content_fingerprint": panel.eod_content_fingerprint,
                        "eod_business_key_fingerprint": panel.eod_business_key_fingerprint,
                        "history_source_fingerprint": panel.history_source_fingerprint,
                        "universes": [
                            {
                                "universe_id": row.universe_id,
                                "membership_fingerprint": row.membership_fingerprint,
                            }
                            for row in panel.universes
                        ],
                    }
                ]
            }
        )
    )

    publication = build_opportunity_candidate_publication(tmp_path)

    assert publication.universe_order == (fixture.PRIMARY, fixture.SECONDARY)
    assert publication.source.oracle_mismatch_count == 0
    assert publication.underlying_stock_result_not_option_return is True
    assert publication.price_volume_not_fund_flow is True
    for universe in publication.universes:
        ids = tuple(str(row.instrument_id) for row in universe.candidates)
        assert ids == tuple(sorted(ids))
        assert all(row.evidence for row in universe.candidates)
        for mode in universe.risk_modes:
            assert set(mode.displayed_instrument_ids).issubset(
                {row.instrument_id for row in universe.candidates}
            )

    invalid_source = publication.source.model_dump(mode="json")
    invalid_source["current_candidate_batch_fingerprints"][0] = "not-a-digest"
    with pytest.raises(ValidationError, match="SHA-256"):
        OpportunityCandidatePublicationSourceV1.model_validate(invalid_source)

    entry_dir = tmp_path / "entry"
    entry_dir.mkdir()
    entry_batches = tuple(
        calculate_candidate_entry_geometry(
            panel=panel,
            candidate_batch=batch,
            state_records=tuple(row for row in states if row.universe_id == batch.universe_id),
        )
        for batch in batches
    )
    entry_manifest = {
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_ids": [fixture.PRIMARY, fixture.SECONDARY],
        "logical_content_fingerprint": "6" * 64,
        "contract_version": "candidate-entry-geometry/1.0",
        "calculation_version": "candidate-entry-geometry-v1.0.0",
        "parameter_set_id": "candidate-entry-geometry-v1-fixed-baseline-1",
        "parameter_fingerprint": entry_batches[0].parameter_fingerprint,
        "oracle_mismatch_count": 0,
        "input_permutation_match": True,
        "batch_fingerprints": [row.logical_fingerprint for row in entry_batches],
        "source": {
            "candidate_audit_logical_fingerprint": manifest["logical_content_fingerprint"],
            "candidate_audit_manifest_sha256": __import__("hashlib").sha256(b"{}\n").hexdigest(),
        },
    }
    monkeypatch.setattr(
        "tip_api.services.opportunity_candidate_publication.read_candidate_entry_geometry_audit",
        lambda _: entry_manifest,
    )
    (entry_dir / "entry-geometry-audit-manifest.json").write_text("{}\n")
    (entry_dir / "entry-geometry-batches.json").write_text(
        json.dumps({"records": [row.model_dump(mode="json") for row in entry_batches]})
    )
    entry_publication = build_opportunity_candidate_publication(tmp_path, entry_dir)
    assert isinstance(entry_publication, OpportunityCandidatePublicationV1_1)
    assert entry_publication.leadership_rank_preserved is True
    assert entry_publication.entry_location_separate_from_leadership is True
    assert all(row.entry_risk_modes for row in entry_publication.universes)
    assert all(
        candidate.entry_geometry.instrument_id == candidate.instrument_id
        for universe in entry_publication.universes
        for candidate in universe.candidates
    )
    summary, shards = build_split_candidate_snapshot(
        candidate_analytics=entry_publication,
        publication_id="2026-08-24T120000Z-abcdef0",
        payload_sha256="7" * 64,
        payload_logical_fingerprint="8" * 64,
    )
    assert reconstruct_full_candidate_publication(summary, shards) == entry_publication
    assert sum(item.item_count for item in shards) == sum(
        len(universe.candidates) for universe in entry_publication.universes
    )
    assert {
        item.filename for item in summary.analytics.detail_shards
    } == {
        f"opportunity-candidate-details-{item.shard_id}.json" for item in shards
    }
