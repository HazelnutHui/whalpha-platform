from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_cycle import (
    QuantResearchDiscoveryStageId,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WEB_REGISTRY_RECORD = (
    REPOSITORY_ROOT
    / "apps"
    / "web"
    / "src"
    / "modelRecords"
    / "quant-research-reusable-artifact-registry-v1.json"
)
from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts import (
    QuantResearchArtifactCustody,
    QuantResearchArtifactKind,
    QuantResearchReusableArtifactDescriptorV1,
    QuantResearchReusableArtifactIdentityV1,
    QuantResearchReusableArtifactRegistryV1,
    quant_research_reusable_artifact_registry_v1,
    reusable_artifact_exact_match,
    reusable_artifact_identity_fingerprint,
    reusable_artifact_registry_fingerprint,
)


def _identity(**updates: object) -> QuantResearchReusableArtifactIdentityV1:
    payload: dict[str, object] = {
        "artifact_kind": "feature_matrix",
        "source_logical_fingerprints": ("1" * 64, "2" * 64),
        "source_contract_versions": ("eod-price-bar/1.0", "membership/1.0"),
        "stable_universe_fingerprint": "3" * 64,
        "knowledge_time_cutoff": "completed_session_close_t",
        "session_partition_fingerprint": "4" * 64,
        "calculation_code_sha256": "5" * 64,
        "parameter_fingerprint": "6" * 64,
        "upstream_artifact_fingerprints": ("7" * 64,),
    }
    payload.update(updates)
    return QuantResearchReusableArtifactIdentityV1.model_validate(payload)


def _descriptor(
    identity: QuantResearchReusableArtifactIdentityV1,
) -> QuantResearchReusableArtifactDescriptorV1:
    return QuantResearchReusableArtifactDescriptorV1(
        identity=identity,
        identity_fingerprint=reusable_artifact_identity_fingerprint(identity),
        content_sha256="8" * 64,
        record_count=100,
        first_session=date(2026, 1, 2),
        last_session=date(2026, 1, 5),
    )


def test_registry_defines_five_separated_reusable_artifact_families() -> None:
    registry = quant_research_reusable_artifact_registry_v1()

    assert registry.implementation_status == "contract_ready_not_materialized"
    assert registry.materialized_artifact_count == 0
    assert registry.next_campaign_registered is False
    assert registry.new_outcome_access_authorized is False
    assert registry.physical_data_write_authorized is False
    assert [item.artifact_kind for item in registry.artifact_families] == list(
        QuantResearchArtifactKind
    )
    assert [item.custody for item in registry.artifact_families] == [
        QuantResearchArtifactCustody.OUTCOME_BLIND,
        QuantResearchArtifactCustody.OUTCOME_BLIND,
        QuantResearchArtifactCustody.OUTCOME_BLIND,
        QuantResearchArtifactCustody.OUTCOME_BEARING,
        QuantResearchArtifactCustody.OUTCOME_BEARING,
    ]
    for policy in registry.artifact_families[-2:]:
        assert policy.permitted_row_access_stages == (
            QuantResearchDiscoveryStageId.DEVELOPMENT_SCREEN,
            QuantResearchDiscoveryStageId.INDEPENDENT_REPLAY_AND_RED_TEAM,
        )
        assert policy.registered_campaign_required is True


def test_artifact_reuse_requires_an_exact_content_identity() -> None:
    identity = _identity()
    existing = _descriptor(identity)

    assert reusable_artifact_exact_match(identity, existing) is True
    assert reusable_artifact_exact_match(
        _identity(parameter_fingerprint="9" * 64), existing
    ) is False
    assert reusable_artifact_exact_match(
        _identity(calculation_code_sha256="a" * 64), existing
    ) is False
    assert reusable_artifact_exact_match(
        _identity(knowledge_time_cutoff="next_session_open_t_plus_1"), existing
    ) is False


def test_artifact_identity_rejects_noncanonical_lineage_order() -> None:
    with pytest.raises(ValidationError, match="sorted and unique"):
        _identity(source_logical_fingerprints=("2" * 64, "1" * 64))


def test_descriptor_rejects_identity_fingerprint_or_session_tamper() -> None:
    identity = _identity()
    with pytest.raises(ValidationError, match="identity fingerprint differs"):
        QuantResearchReusableArtifactDescriptorV1(
            identity=identity,
            identity_fingerprint="0" * 64,
            content_sha256="8" * 64,
            record_count=100,
        )
    with pytest.raises(ValidationError, match="session bounds are reversed"):
        QuantResearchReusableArtifactDescriptorV1(
            identity=identity,
            identity_fingerprint=reusable_artifact_identity_fingerprint(identity),
            content_sha256="8" * 64,
            record_count=100,
            first_session=date(2026, 1, 5),
            last_session=date(2026, 1, 2),
        )


def test_registry_rejects_outcome_label_access_during_qualification() -> None:
    payload = quant_research_reusable_artifact_registry_v1().model_dump(
        mode="python"
    )
    families = deepcopy(payload["artifact_families"])
    families[-1]["permitted_row_access_stages"] = (
        QuantResearchDiscoveryStageId.OUTCOME_BLIND_QUALIFICATION,
    )
    payload["artifact_families"] = families
    payload["logical_fingerprint"] = reusable_artifact_registry_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchReusableArtifactRegistryV1.model_validate(payload)


def test_checked_in_web_registry_projection_matches_contract() -> None:
    projection = json.loads(WEB_REGISTRY_RECORD.read_text(encoding="utf-8"))

    assert projection == quant_research_reusable_artifact_registry_v1().model_dump(
        mode="json"
    )
