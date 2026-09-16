"""Build the immutable outcome-blind market-state qualification report."""

from __future__ import annotations

from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QuantResearchMarketStateQualificationReportV1,
    QuantResearchMarketStateQualificationStatus,
    QuantResearchMarketStateSessionV1,
    market_state_coverage,
    market_state_distributions,
    market_state_joint_coverage,
    market_state_panel_sha256,
    market_state_pair_correlations,
    market_state_qualification_ready,
    market_state_temporal_diagnostics,
    qualification_fingerprint,
    quant_research_market_state_qualification_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    quant_research_market_state_vector_definition_v1,
)
from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts import (
    QuantResearchArtifactKind,
    QuantResearchReusableArtifactDescriptorV1,
    QuantResearchReusableArtifactIdentityV1,
    reusable_artifact_identity_fingerprint,
)


class QuantResearchMarketStateQualificationError(ValueError):
    """Raised when a market-state qualification input is not canonical."""


def build_quant_research_market_state_qualification_v1(
    *,
    source_revision: str,
    source_eod_fingerprint: str,
    source_membership_fingerprint: str,
    source_action_fingerprint: str,
    source_adjustment_fingerprint: str,
    source_census_fingerprint: str,
    source_population_fingerprint: str,
    calculation_code_sha256: str,
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
    limitation_codes: tuple[str, ...],
) -> QuantResearchMarketStateQualificationReportV1:
    protocol = quant_research_market_state_qualification_protocol_v1()
    vector = quant_research_market_state_vector_definition_v1()
    if (
        len(sessions) != protocol.expected_signal_session_count
        or limitation_codes != tuple(sorted(set(limitation_codes)))
    ):
        raise QuantResearchMarketStateQualificationError(
            "market-state qualification inputs differ"
        )
    coverage = market_state_coverage(sessions)
    distributions = market_state_distributions(sessions)
    joint = market_state_joint_coverage(sessions)
    temporal = market_state_temporal_diagnostics(sessions)
    pairs = market_state_pair_correlations(sessions)
    status = (
        QuantResearchMarketStateQualificationStatus.READY_FOR_CAMPAIGN_PROTOCOL_DESIGN
        if market_state_qualification_ready(
            coverage,
            distributions,
            joint,
            temporal,
        )
        else QuantResearchMarketStateQualificationStatus.REJECTED_DATA_OR_IMPLEMENTATION
    )
    artifact_identity = QuantResearchReusableArtifactIdentityV1(
        artifact_kind=QuantResearchArtifactKind.MARKET_STATE,
        source_logical_fingerprints=tuple(
            sorted(
                {
                    source_eod_fingerprint,
                    source_membership_fingerprint,
                    source_action_fingerprint,
                    source_adjustment_fingerprint,
                    source_census_fingerprint,
                }
            )
        ),
        source_contract_versions=(
            "quant-research-historical-split-extension/1.0",
            "quant-research-market-state-vector/1.1",
            "reconciled-eod-price-bar-edition-session/1.2",
            "strong-leader-pullback-development-coverage-census/1.0",
            "universe-membership-partition-manifest/1.1",
        ),
        stable_universe_fingerprint=source_population_fingerprint,
        knowledge_time_cutoff=(
            "completed_session_close_each_row_earliest_next_open"
        ),
        session_partition_fingerprint=(
            "1d2151281b6ed45c352294529d544d58bb5e41c19798a73a0ef5d72fc54c1eff"
        ),
        calculation_code_sha256=calculation_code_sha256,
        parameter_fingerprint=vector.logical_fingerprint,
        upstream_artifact_fingerprints=(protocol.logical_fingerprint,),
    )
    artifact = QuantResearchReusableArtifactDescriptorV1(
        identity=artifact_identity,
        identity_fingerprint=reusable_artifact_identity_fingerprint(
            artifact_identity
        ),
        content_sha256=market_state_panel_sha256(sessions),
        record_count=len(sessions),
        first_session=sessions[0].as_of_session,
        last_session=sessions[-1].as_of_session,
    )
    payload = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "vector_definition_fingerprint": vector.logical_fingerprint,
        "source_revision": source_revision,
        "source_eod_fingerprint": source_eod_fingerprint,
        "source_membership_fingerprint": source_membership_fingerprint,
        "source_action_fingerprint": source_action_fingerprint,
        "source_adjustment_fingerprint": source_adjustment_fingerprint,
        "source_census_fingerprint": source_census_fingerprint,
        "source_population_fingerprint": source_population_fingerprint,
        "calculation_code_sha256": calculation_code_sha256,
        "artifact": artifact,
        "first_session": sessions[0].as_of_session,
        "last_session": sessions[-1].as_of_session,
        "coverage": coverage,
        "distributions": distributions,
        "temporal_diagnostics": temporal,
        "pair_correlations": pairs,
        "sessions": sessions,
        "status": status,
        "reconstructed_joint_available_session_count": joint[0],
        "reconstructed_joint_first_half_session_count": joint[1],
        "reconstructed_joint_second_half_session_count": joint[2],
        "limitation_codes": limitation_codes,
    }
    provisional = QuantResearchMarketStateQualificationReportV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchMarketStateQualificationReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": qualification_fingerprint(provisional),
        }
    )
