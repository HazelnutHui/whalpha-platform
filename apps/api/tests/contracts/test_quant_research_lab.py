from __future__ import annotations

from copy import deepcopy
from decimal import Inexact, Rounded, localcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    QuantResearchLabCatalogV1,
    QuantResearchLabModelRecordV1,
    QuantResearchLabResultPublicationV1,
    lab_fingerprint,
    strong_leader_pullback_method_v1,
    strong_leader_pullback_lab_catalog_v1,
    strong_leader_pullback_lab_model_record_v1,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WEB_MODEL_RECORD = (
    REPOSITORY_ROOT
    / "apps"
    / "web"
    / "src"
    / "modelRecords"
    / "quant-research-lab-model-record-v1.json"
)


def _record_payload() -> dict[str, object]:
    return strong_leader_pullback_lab_model_record_v1().model_dump(mode="json")


def _result_payload(*, evidence_scope: str = "method_only") -> dict[str, object]:
    record = strong_leader_pullback_lab_model_record_v1()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": "quant-research-lab-result/1.0",
        "publication_id": "method-record-only",
        "model_id": record.model_id,
        "model_record_fingerprint": record.logical_fingerprint,
        "evidence_scope": evidence_scope,
        "fixture_only": False,
        "performance_claims_authorized": False,
        "candidate_authority_granted": False,
        "period_start": None,
        "period_end": None,
        "source_dataset_fingerprint": None,
        "portfolio_construction_fingerprint": None,
        "metrics": (),
        "supporting_evidence": (),
        "counterevidence": (),
        "limitation_codes": ("no_real_evaluation",),
    }
    payload["logical_fingerprint"] = lab_fingerprint(payload)
    return payload


def test_pre_architecture_method_record_is_not_a_web_projection() -> None:
    assert not WEB_MODEL_RECORD.exists()


def test_model_record_rejects_formula_drift_without_new_fingerprint() -> None:
    payload = _record_payload()
    features = deepcopy(payload["feature_disclosures"])
    features[1]["exact_formula"] = "close / ATR"
    payload["feature_disclosures"] = features

    with pytest.raises(ValidationError, match="model record fingerprint mismatch"):
        QuantResearchLabModelRecordV1.model_validate(payload)


def test_model_record_rejects_method_engineering_evidence_drift() -> None:
    payload = _record_payload()
    evidence = deepcopy(payload["method_engineering_evidence"])
    evidence["complete_observation_count"] = 417_208
    payload["method_engineering_evidence"] = evidence

    with pytest.raises(
        ValidationError,
        match="method-engineering evidence differs",
    ):
        QuantResearchLabModelRecordV1.model_validate(payload)


def test_method_engineering_ratio_does_not_pollute_decimal_context() -> None:
    with localcontext() as context:
        context.clear_flags()

        strong_leader_pullback_lab_model_record_v1()

        assert context.flags[Inexact] is False
        assert context.flags[Rounded] is False


def test_non_active_model_cannot_claim_candidate_eligibility() -> None:
    payload = _record_payload()
    payload["candidate_eligible"] = True
    payload["candidate_activation_fingerprint"] = "a" * 64

    with pytest.raises(ValidationError, match="cannot claim Candidate eligibility"):
        QuantResearchLabModelRecordV1.model_validate(payload)


def test_fixture_evidence_cannot_advance_model_lifecycle() -> None:
    payload = _record_payload()
    payload.update(
        {
            "lifecycle_state": "validated_research",
            "evidence_scope": "fixture_only",
            "last_validation_date": "2026-09-10",
            "out_of_sample_observation_count": 100,
            "result_publication_id": "fixture-only-result",
            "blocker_codes": (),
        }
    )

    with pytest.raises(ValidationError, match="requires real evaluated evidence"):
        QuantResearchLabModelRecordV1.model_validate(payload)


def test_method_only_publication_cannot_smuggle_performance() -> None:
    payload = _result_payload()
    payload["metrics"] = (
        {
            "metric_id": "win_rate",
            "value": "0.75",
            "unit": "ratio",
            "split": "fixture",
            "sample_count": 4,
            "net_of_costs": False,
        },
    )

    with pytest.raises(ValidationError, match="method-only publication cannot carry results"):
        QuantResearchLabResultPublicationV1.model_validate(payload)


def test_method_only_publication_is_valid_without_results() -> None:
    publication = QuantResearchLabResultPublicationV1.model_validate(
        _result_payload()
    )

    assert publication.metrics == ()
    assert publication.performance_claims_authorized is False
    assert publication.candidate_authority_granted is False


def test_fixture_publication_cannot_authorize_performance_claims() -> None:
    payload = _result_payload(evidence_scope="fixture_only")
    payload["fixture_only"] = True
    payload["performance_claims_authorized"] = True

    with pytest.raises(ValidationError, match="cannot authorize performance claims"):
        QuantResearchLabResultPublicationV1.model_validate(payload)


def test_event_study_rejects_portfolio_only_metrics() -> None:
    payload = _result_payload(evidence_scope="signal_event_study")
    payload.update(
        {
            "performance_claims_authorized": True,
            "period_start": "2025-01-02",
            "period_end": "2025-12-31",
            "source_dataset_fingerprint": "b" * 64,
            "counterevidence": ("sector_concentration_reviewed",),
            "metrics": (
                {
                    "metric_id": "sharpe_ratio",
                    "value": "1.20",
                    "unit": "ratio",
                    "split": "holdout",
                    "sample_count": 120,
                    "net_of_costs": True,
                },
            ),
        }
    )

    with pytest.raises(ValidationError, match="event study cannot carry portfolio-only metrics"):
        QuantResearchLabResultPublicationV1.model_validate(payload)


def test_real_event_study_retains_scope_cost_sample_and_counterevidence() -> None:
    payload = _result_payload(evidence_scope="signal_event_study")
    payload.update(
        {
            "performance_claims_authorized": True,
            "period_start": "2025-01-02",
            "period_end": "2025-12-31",
            "source_dataset_fingerprint": "b" * 64,
            "supporting_evidence": ("primary_contrast_positive",),
            "counterevidence": ("sector_concentration_reviewed",),
            "metrics": (
                {
                    "metric_id": "net_expectancy",
                    "value": "0.004",
                    "unit": "return",
                    "split": "holdout",
                    "horizon_sessions": 3,
                    "slice_code": "all",
                    "sample_count": 120,
                    "net_of_costs": True,
                    "benchmark": "spy_price_return",
                    "uncertainty_lower": "0.001",
                    "uncertainty_upper": "0.007",
                },
            ),
        }
    )
    payload["logical_fingerprint"] = lab_fingerprint(payload)

    publication = QuantResearchLabResultPublicationV1.model_validate(payload)
    assert publication.metrics[0].horizon_sessions == 3
    assert publication.metrics[0].net_of_costs is True
    assert publication.candidate_authority_granted is False


def test_portfolio_metrics_require_frozen_construction() -> None:
    payload = _result_payload(evidence_scope="portfolio_simulation")
    payload.update(
        {
            "performance_claims_authorized": True,
            "period_start": "2025-01-02",
            "period_end": "2025-12-31",
            "source_dataset_fingerprint": "b" * 64,
            "counterevidence": ("capacity_sensitivity_reviewed",),
            "metrics": (
                {
                    "metric_id": "annualized_return",
                    "value": "0.15",
                    "unit": "return",
                    "split": "holdout",
                    "sample_count": 252,
                    "net_of_costs": True,
                },
            ),
        }
    )

    with pytest.raises(ValidationError, match="requires frozen portfolio construction"):
        QuantResearchLabResultPublicationV1.model_validate(payload)


def test_catalog_has_no_active_candidate_model_before_activation() -> None:
    catalog = strong_leader_pullback_lab_catalog_v1()
    assert catalog.active_candidate_model_ids == ()

    payload = catalog.model_dump(mode="json")
    payload["active_candidate_model_ids"] = [catalog.featured_model_id]
    payload["logical_fingerprint"] = lab_fingerprint(payload)
    with pytest.raises(ValidationError, match="lacks reviewed activation"):
        QuantResearchLabCatalogV1.model_validate(payload)
