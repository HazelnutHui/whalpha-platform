from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    MAPPER_POLICY_ID,
    ReconciledEodDiffDisposition,
    ReconciledEodDiffSummaryV1,
    ReconciledEodEditionApplyArtifactV1,
    ReconciledEodEditionApplyPlanV1,
    ReconciledEodIntervalSessionReferenceV1,
    ReconciledEodSessionManifestV1,
    ReconciledEodSourceProvenance,
    reconciled_eod_apply_inventory_fingerprint,
    seal_reconciled_eod_apply_plan,
    seal_reconciled_eod_interval_manifest,
    seal_reconciled_eod_session_manifest,
)


NOW = datetime(2026, 9, 10, 23, tzinfo=UTC)
SESSION = date(2026, 9, 9)
SHA = "a" * 64
REVISION = "b" * 40


def diff(**override: object) -> ReconciledEodDiffSummaryV1:
    values: dict[str, object] = {
        "base_record_count": 10,
        "rebuilt_record_count": 11,
        "unchanged_record_count": 10,
        "provenance_only_change_count": 0,
        "expected_provenance_change_count": 0,
        "unexpected_provenance_change_count": 0,
        "added_record_count": 1,
        "unexpected_added_record_count": 0,
        "absent_record_count": 0,
        "expected_absent_record_count": 0,
        "unexpected_absent_record_count": 0,
        "economic_change_record_count": 0,
        "disposition": "accepted_case_sensitive_additions_only",
        "quarantine_reasons": (),
    }
    values.update(override)
    return ReconciledEodDiffSummaryV1.model_validate(values)


def session_manifest(**override: object) -> ReconciledEodSessionManifestV1:
    values: dict[str, object] = {
        "edition_id": "massive-exact-symbol-v1",
        "session_date": SESSION,
        "provider": "massive_stocks_basic",
        "mapper_policy_id": MAPPER_POLICY_ID,
        "implementation_revision": REVISION,
        "source_provenance": "retained_original",
        "source_observed_at": NOW,
        "source_package_manifest_sha256": SHA,
        "source_package_content_sha256": "b" * 64,
        "identity_as_of_date": SESSION,
        "identity_snapshot_fingerprint": "c" * 64,
        "identity_source_fingerprint": "d" * 64,
        "base_eod_fingerprint": "e" * 64,
        "rebuilt_eod_fingerprint": "f" * 64,
        "diff": diff(),
        "quality_summary_fingerprint": "1" * 64,
        "quality_warnings": ("case_sensitive_provider_tickers_present",),
        "parquet_sha256": "2" * 64,
        "created_at": NOW,
    }
    values.update(override)
    return seal_reconciled_eod_session_manifest(values)


def test_session_manifest_binds_source_identity_base_and_diff() -> None:
    manifest = session_manifest()

    assert manifest.diff.added_record_count == 1
    assert manifest.candidate_authority is False
    assert manifest.production_authority is False

    forged = manifest.model_dump(mode="json")
    forged["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        ReconciledEodSessionManifestV1.model_validate(forged)


def test_diff_rejects_unexplained_economic_change() -> None:
    with pytest.raises(ValidationError, match="blocking difference"):
        diff(
            unchanged_record_count=9,
            economic_change_record_count=1,
        )


def test_diff_accepts_only_accounted_case_sensitive_absence() -> None:
    reconciled = diff(
        base_record_count=10,
        rebuilt_record_count=9,
        unchanged_record_count=9,
        added_record_count=0,
        absent_record_count=1,
        expected_absent_record_count=1,
        disposition="accepted_case_sensitive_reconciliation",
    )

    assert reconciled.expected_absent_record_count == 1
    assert reconciled.unexpected_absent_record_count == 0

    with pytest.raises(ValidationError, match="absences do not reconcile"):
        diff(
            base_record_count=11,
            absent_record_count=1,
            expected_absent_record_count=0,
            unexpected_absent_record_count=0,
        )


def test_quarantined_diff_requires_typed_reason() -> None:
    quarantined = diff(
        unchanged_record_count=9,
        economic_change_record_count=1,
        disposition="quarantined",
        quarantine_reasons=("economic_value_changed",),
    )

    assert quarantined.disposition == ReconciledEodDiffDisposition.QUARANTINED

    with pytest.raises(ValidationError, match="cannot publish"):
        session_manifest(
            diff=quarantined,
            rebuilt_eod_fingerprint="f" * 64,
        )


def test_interval_requires_final_marker_reconciliation() -> None:
    session = session_manifest()
    reference = ReconciledEodIntervalSessionReferenceV1(
        session_date=SESSION,
        session_manifest_fingerprint=session.logical_fingerprint,
        rebuilt_eod_fingerprint=session.rebuilt_eod_fingerprint,
        record_count=session.diff.rebuilt_record_count,
        added_record_count=session.diff.added_record_count,
        absent_record_count=session.diff.absent_record_count,
        provenance_only_change_count=session.diff.provenance_only_change_count,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        disposition="accepted_case_sensitive_additions_only",
    )
    values = {
        "edition_id": session.edition_id,
        "provider": session.provider,
        "implementation_revision": REVISION,
        "evaluation_first_session": SESSION,
        "evaluation_last_session": SESSION,
        "sessions": (reference,),
        "retained_original_session_count": 1,
        "later_reacquisition_session_count": 0,
        "added_record_count": 1,
        "absent_record_count": 0,
        "provenance_only_change_count": 0,
        "created_at": NOW,
    }
    interval = seal_reconciled_eod_interval_manifest(values)

    assert interval.source_gap_count == 0
    assert interval.quarantine_count == 0


def test_interval_rejects_partial_declared_bounds() -> None:
    reference = ReconciledEodIntervalSessionReferenceV1(
        session_date=SESSION,
        session_manifest_fingerprint=SHA,
        rebuilt_eod_fingerprint="b" * 64,
        record_count=10,
        added_record_count=0,
        absent_record_count=0,
        provenance_only_change_count=0,
        source_provenance="later_reacquisition",
        disposition="identical",
    )
    values = {
        "edition_id": "massive-exact-symbol-v1",
        "provider": "massive_stocks_basic",
        "implementation_revision": REVISION,
        "evaluation_first_session": date(2026, 9, 8),
        "evaluation_last_session": SESSION,
        "sessions": (reference,),
        "retained_original_session_count": 0,
        "later_reacquisition_session_count": 1,
        "added_record_count": 0,
        "absent_record_count": 0,
        "provenance_only_change_count": 0,
        "created_at": NOW,
    }
    with pytest.raises(ValidationError, match="first boundary"):
        seal_reconciled_eod_interval_manifest(values)


def apply_artifacts() -> tuple[ReconciledEodEditionApplyArtifactV1, ...]:
    relative = (
        f"session_date={SESSION.isoformat()}/manifest.json",
        f"session_date={SESSION.isoformat()}/part-00000.parquet",
        "interval-manifest.json",
    )
    return tuple(
        ReconciledEodEditionApplyArtifactV1(
            relative_path=item,
            size=index + 1,
            sha256=str(index + 3) * 64,
        )
        for index, item in enumerate(relative)
    )


def apply_plan(**override: object) -> ReconciledEodEditionApplyPlanV1:
    artifacts = apply_artifacts()
    values: dict[str, object] = {
        "created_at": NOW,
        "planner_revision": REVISION,
        "candidate_implementation_revision": REVISION,
        "edition_id": "massive-exact-symbol-v1",
        "data_root": "/data/trading-intelligence-platform",
        "candidate_location_fingerprint": "9" * 64,
        "target_edition_path": (
            "/data/trading-intelligence-platform/market-data/"
            "reconciled-eod-price-bar-editions/contract_version=1/"
            "edition_id=massive-exact-symbol-v1"
        ),
        "expected_current_state_fingerprint": SHA,
        "candidate_interval_manifest_fingerprint": "b" * 64,
        "candidate_inventory_fingerprint": (
            reconciled_eod_apply_inventory_fingerprint(artifacts)
        ),
        "candidate_session_count": 1,
        "candidate_record_count": 11,
        "candidate_added_record_count": 1,
        "candidate_absent_record_count": 0,
        "candidate_provenance_only_change_count": 0,
        "artifacts": artifacts,
        "inventory_change_file_count": 3,
        "inventory_change_bytes": 6,
    }
    values.update(override)
    return seal_reconciled_eod_apply_plan(values)


def test_apply_plan_binds_exact_inventory_and_denies_authority() -> None:
    plan = apply_plan()

    assert plan.inventory_change_file_count == 3
    assert plan.apply_authorized is False
    assert plan.candidate_authority is False
    assert plan.production_authority is False
    assert plan.research_performance_authorized is False

    forged = plan.model_dump(mode="json")
    forged["candidate_record_count"] = 12
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        ReconciledEodEditionApplyPlanV1.model_validate(forged)


def test_apply_plan_rejects_artifact_path_order_and_inventory_tamper() -> None:
    artifacts = list(apply_artifacts())
    with pytest.raises(ValidationError, match="unordered"):
        apply_plan(artifacts=tuple(reversed(artifacts)))

    with pytest.raises(ValidationError, match="root artifact is invalid"):
        ReconciledEodEditionApplyArtifactV1(
            relative_path="wrong.json",
            size=1,
            sha256=SHA,
        )

    with pytest.raises(ValidationError, match="candidate inventory differs"):
        apply_plan(candidate_inventory_fingerprint="0" * 64)
