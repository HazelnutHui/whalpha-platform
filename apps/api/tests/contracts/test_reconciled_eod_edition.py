from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    MAPPER_POLICY_ID,
    ReconciledEodDiffDisposition,
    ReconciledEodDiffSummaryV1,
    ReconciledEodIntervalSessionReferenceV1,
    ReconciledEodSessionManifestV1,
    ReconciledEodSourceProvenance,
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
        "unexpected_provenance_change_count": 0,
        "added_record_count": 1,
        "unexpected_added_record_count": 0,
        "absent_record_count": 0,
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
        "created_at": NOW,
    }
    with pytest.raises(ValidationError, match="first boundary"):
        seal_reconciled_eod_interval_manifest(values)
