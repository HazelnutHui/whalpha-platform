"""Read-only go/no-go validation for current-session segmented Candidate consumers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from tip_api.contracts.analytics.v1 import (
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services.candidate_entry_geometry import (
    calculate_candidate_entry_geometry,
)
from tip_api.services.candidate_entry_geometry_oracle import (
    compare_with_independent_entry_geometry_oracle,
)
from tip_api.services.candidate_strategy_channels import (
    calculate_candidate_strategy_channels,
)
from tip_api.services.candidate_strategy_channels_oracle import (
    compare_with_independent_strategy_channel_oracle,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel
from tip_api.services.opportunity_candidate_segmented_append import (
    read_candidate_segmented_append,
)


CURRENT_CONSUMER_CONTRACT = (
    "opportunity-candidate-segmented-current-consumer/1.0"
)


class CandidateSegmentedConsumerError(RuntimeError):
    """Raised when segmented current-session evidence is not safe to consume."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedCurrentConsumerEvidence:
    """Typed, exact-identity current-session evidence from one append."""

    append_path: Path
    append_manifest: Mapping[str, Any]
    append_manifest_sha256: str
    source_panel: Mapping[str, Any]
    candidate_batches: tuple[OpportunityCandidateBatchV1, ...]
    state_records: tuple[OpportunityCandidateStateRecordV1, ...]
    risk_results: tuple[CandidateRiskModeResultV1, ...]
    logical_content_fingerprint: str
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


@dataclass(frozen=True, slots=True)
class CandidateSegmentedCurrentEquivalence:
    """Exact V1/current-segment comparison result."""

    as_of_session: str
    universe_ids: tuple[str, ...]
    candidate_batch_fingerprints: tuple[str, ...]
    state_record_count: int
    current_projection_fingerprints: Mapping[str, str]
    logical_content_fingerprint: str
    mismatch_count: int = 0
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


@dataclass(frozen=True, slots=True)
class CandidateSegmentedDownstreamValidation:
    """Pure downstream calculation evidence and bounded replacement decision."""

    as_of_session: str
    entry_batch_fingerprints: tuple[str, ...]
    strategy_batch_fingerprints: tuple[str, ...]
    entry_oracle_mismatch_count: int
    strategy_oracle_mismatch_count: int
    current_session_entry_strategy_ready: bool
    visual_context_ready: bool
    visual_context_blocker: str
    v1_replacement_ready: bool
    logical_content_fingerprint: str
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


def read_candidate_segmented_current_consumer(
    *,
    base_shadow: Path,
    append_package: Path,
    as_of_session: date,
    expected_append_logical_fingerprint: str,
    expected_source_audit_logical_fingerprint: str,
    parent_appends: Sequence[Path] = (),
) -> CandidateSegmentedCurrentConsumerEvidence:
    """Read one exact append into typed current-session consumer inputs."""

    evidence = read_candidate_segmented_append(
        parent_shadow=base_shadow,
        output_dir=append_package,
        parent_appends=parent_appends,
    )
    manifest = evidence.manifest
    session = as_of_session.isoformat()
    if (
        manifest.get("logical_content_fingerprint")
        != expected_append_logical_fingerprint
        or manifest.get("source_audit", {}).get("logical_content_fingerprint")
        != expected_source_audit_logical_fingerprint
        or manifest.get("as_of_session") != session
        or manifest.get("publication_authorized") is not False
        or manifest.get("production_write_count") != 0
        or manifest.get("external_request_count") != 0
    ):
        raise CandidateSegmentedConsumerError(
            "segmented current consumer identity or safety boundary differs"
        )

    segment = evidence.segment
    try:
        batches = tuple(
            OpportunityCandidateBatchV1.model_validate(item)
            for item in segment["candidate_batches"]
        )
        states = tuple(
            OpportunityCandidateStateRecordV1.model_validate(item)
            for item in segment["state_records"]
        )
        risks = tuple(
            CandidateRiskModeResultV1.model_validate(item)
            for item in segment["risk_results"]
        )
    except Exception as exc:
        raise CandidateSegmentedConsumerError(
            f"segmented current typed projection failed: {type(exc).__name__}"
        ) from exc
    v1._validate_typed_fingerprints(batches=batches, states=states, risks=risks)

    universe_ids = tuple(manifest.get("universe_ids", ()))
    panel = segment.get("source_panel")
    panel_universes = panel.get("universes") if isinstance(panel, Mapping) else None
    ordered_panel_universes = (
        tuple(sorted(panel_universes, key=lambda item: item.get("catalog_order", -1)))
        if isinstance(panel_universes, list)
        and all(isinstance(item, Mapping) for item in panel_universes)
        else ()
    )
    panel_by_id = {
        str(item.get("universe_id")): item for item in ordered_panel_universes
    }
    if (
        not isinstance(panel, Mapping)
        or panel.get("as_of_session") != session
        or tuple(item.get("universe_id") for item in ordered_panel_universes)
        != universe_ids
        or tuple(batch.universe_id for batch in batches) != universe_ids
    ):
        raise CandidateSegmentedConsumerError(
            "segmented current panel or Universe order differs"
        )

    state_by_universe: dict[str, set[object]] = {
        universe_id: set() for universe_id in universe_ids
    }
    for state in states:
        if state.as_of_session != as_of_session or state.universe_id not in state_by_universe:
            raise CandidateSegmentedConsumerError(
                "segmented current state session or Universe differs"
            )
        if state.instrument_id in state_by_universe[state.universe_id]:
            raise CandidateSegmentedConsumerError(
                "segmented current state coverage contains duplicates"
            )
        state_by_universe[state.universe_id].add(state.instrument_id)

    for batch in batches:
        source_universe = panel_by_id.get(batch.universe_id, {})
        expected_ids = {
            *(item.instrument_id for item in batch.candidates),
            *batch.missing_member_ids,
        }
        if (
            batch.as_of_session != as_of_session
            or batch.history_source_fingerprint
            != panel.get("history_source_fingerprint")
            or batch.membership_fingerprint
            != source_universe.get("membership_fingerprint")
            or batch.universe_member_count != source_universe.get("member_count")
            or state_by_universe[batch.universe_id] != expected_ids
        ):
            raise CandidateSegmentedConsumerError(
                "segmented current batch, panel, and state coverage differs"
            )

    logical = {
        "contract_version": CURRENT_CONSUMER_CONTRACT,
        "append_logical_content_fingerprint": expected_append_logical_fingerprint,
        "source_audit_logical_fingerprint": (
            expected_source_audit_logical_fingerprint
        ),
        "as_of_session": session,
        "universe_ids": list(universe_ids),
        "source_panel_fingerprint": v1._fingerprint(panel),
        "candidate_batch_fingerprints": [
            item.logical_fingerprint for item in batches
        ],
        "state_record_fingerprints": [item.logical_fingerprint for item in states],
        "risk_result_fingerprints": [item.logical_fingerprint for item in risks],
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return CandidateSegmentedCurrentConsumerEvidence(
        append_path=evidence.path,
        append_manifest=manifest,
        append_manifest_sha256=evidence.manifest_sha256,
        source_panel=panel,
        candidate_batches=batches,
        state_records=states,
        risk_results=risks,
        logical_content_fingerprint=v1._fingerprint(logical),
    )


def verify_candidate_segmented_current_equivalence(
    *,
    base_shadow: Path,
    append_package: Path,
    source_v1_audit: Path,
    as_of_session: date,
    expected_append_logical_fingerprint: str,
    expected_source_audit_logical_fingerprint: str,
    parent_appends: Sequence[Path] = (),
) -> CandidateSegmentedCurrentEquivalence:
    """Fail closed unless exact V1 and segmented current consumer inputs match."""

    segmented = read_candidate_segmented_current_consumer(
        base_shadow=base_shadow,
        append_package=append_package,
        as_of_session=as_of_session,
        expected_append_logical_fingerprint=expected_append_logical_fingerprint,
        expected_source_audit_logical_fingerprint=(
            expected_source_audit_logical_fingerprint
        ),
        parent_appends=parent_appends,
    )
    v1_current = v1.read_opportunity_candidate_current_batches(
        source_v1_audit,
        as_of_session=as_of_session,
    )
    if (
        v1_current.manifest.get("logical_content_fingerprint")
        != expected_source_audit_logical_fingerprint
    ):
        raise CandidateSegmentedConsumerError(
            "V1 current consumer source identity differs"
        )
    v1_states = tuple(
        item
        for item in v1.read_opportunity_candidate_state_history(source_v1_audit)
        if item.as_of_session == as_of_session
    )
    segmented_batches = [
        item.model_dump(mode="json") for item in segmented.candidate_batches
    ]
    segmented_states = [
        item.model_dump(mode="json") for item in segmented.state_records
    ]
    current_projections = {
        "source_panel": v1._fingerprint(segmented.source_panel),
        "candidate_batches": v1._fingerprint(segmented_batches),
        "state_records": v1._fingerprint(segmented_states),
    }
    mismatches = tuple(
        label
        for label, matches in (
            (
                "source_audit_manifest_sha256",
                v1_current.manifest_sha256
                == segmented.append_manifest["source_audit"].get(
                    "manifest_sha256"
                ),
            ),
            ("source_panel", segmented.source_panel == v1_current.source_panel),
            (
                "candidate_batches",
                segmented.candidate_batches == v1_current.candidate_batches,
            ),
            ("state_records", segmented.state_records == v1_states),
            (
                "append_projection_fingerprints",
                all(
                    segmented.append_manifest["current_projection_fingerprints"].get(
                        name
                    )
                    == fingerprint
                    for name, fingerprint in current_projections.items()
                ),
            ),
        )
        if not matches
    )
    if mismatches:
        raise CandidateSegmentedConsumerError(
            "segmented current consumer differs from V1: " + ", ".join(mismatches)
        )
    logical = {
        "contract_version": CURRENT_CONSUMER_CONTRACT,
        "comparison": "exact_v1_current_consumer_projection",
        "as_of_session": as_of_session.isoformat(),
        "universe_ids": list(segmented.append_manifest["universe_ids"]),
        "candidate_batch_fingerprints": [
            item.logical_fingerprint for item in segmented.candidate_batches
        ],
        "state_record_count": len(segmented.state_records),
        "current_projection_fingerprints": current_projections,
        "mismatch_count": 0,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return CandidateSegmentedCurrentEquivalence(
        as_of_session=as_of_session.isoformat(),
        universe_ids=tuple(segmented.append_manifest["universe_ids"]),
        candidate_batch_fingerprints=tuple(
            item.logical_fingerprint for item in segmented.candidate_batches
        ),
        state_record_count=len(segmented.state_records),
        current_projection_fingerprints=current_projections,
        logical_content_fingerprint=v1._fingerprint(logical),
    )


def validate_candidate_segmented_current_downstream(
    *,
    evidence: CandidateSegmentedCurrentConsumerEvidence,
    panel: MarketRegimeInputPanel,
    expected_entry_batch_fingerprints: Sequence[str] | None = None,
    expected_strategy_batch_fingerprints: Sequence[str] | None = None,
) -> CandidateSegmentedDownstreamValidation:
    """Recalculate current Entry and Strategy; state why Visual cannot replace V1."""

    if v1._panel_source_row(panel) != evidence.source_panel:
        raise CandidateSegmentedConsumerError(
            "downstream panel differs from segmented source panel"
        )
    entries = []
    strategies = []
    entry_mismatches = 0
    strategy_mismatches = 0
    for batch in evidence.candidate_batches:
        states = tuple(
            item
            for item in evidence.state_records
            if item.universe_id == batch.universe_id
        )
        entry = calculate_candidate_entry_geometry(
            panel=panel,
            candidate_batch=batch,
            state_records=states,
        )
        entry_oracle = compare_with_independent_entry_geometry_oracle(
            panel=panel,
            candidate_batch=batch,
            state_records=states,
            actual=entry,
        )
        entry_mismatches += entry_oracle.mismatch_count
        if not entry_oracle.input_permutation_match:
            entry_mismatches += 1
        strategy = calculate_candidate_strategy_channels(
            candidate_batch=batch,
            entry_geometry_batch=entry,
        )
        strategy_oracle = compare_with_independent_strategy_channel_oracle(
            candidate_batch=batch,
            entry_geometry_batch=entry,
            actual=strategy,
        )
        strategy_mismatches += strategy_oracle.mismatch_count
        if not strategy_oracle.input_permutation_match:
            strategy_mismatches += 1
        entries.append(entry)
        strategies.append(strategy)

    entry_fingerprints = tuple(item.logical_fingerprint for item in entries)
    strategy_fingerprints = tuple(item.logical_fingerprint for item in strategies)
    if (
        entry_mismatches
        or strategy_mismatches
        or (
            expected_entry_batch_fingerprints is not None
            and entry_fingerprints != tuple(expected_entry_batch_fingerprints)
        )
        or (
            expected_strategy_batch_fingerprints is not None
            and strategy_fingerprints != tuple(expected_strategy_batch_fingerprints)
        )
    ):
        raise CandidateSegmentedConsumerError(
            "segmented current Entry or Strategy result differs"
        )

    blocker = "cumulative_candidate_state_history_not_in_current_session_projection"
    logical = {
        "contract_version": CURRENT_CONSUMER_CONTRACT,
        "as_of_session": panel.as_of_session.isoformat(),
        "entry_batch_fingerprints": list(entry_fingerprints),
        "strategy_batch_fingerprints": list(strategy_fingerprints),
        "entry_oracle_mismatch_count": entry_mismatches,
        "strategy_oracle_mismatch_count": strategy_mismatches,
        "current_session_entry_strategy_ready": True,
        "visual_context_ready": False,
        "visual_context_blocker": blocker,
        "v1_replacement_ready": False,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return CandidateSegmentedDownstreamValidation(
        as_of_session=panel.as_of_session.isoformat(),
        entry_batch_fingerprints=entry_fingerprints,
        strategy_batch_fingerprints=strategy_fingerprints,
        entry_oracle_mismatch_count=entry_mismatches,
        strategy_oracle_mismatch_count=strategy_mismatches,
        current_session_entry_strategy_ready=True,
        visual_context_ready=False,
        visual_context_blocker=blocker,
        v1_replacement_ready=False,
        logical_content_fingerprint=v1._fingerprint(logical),
    )
