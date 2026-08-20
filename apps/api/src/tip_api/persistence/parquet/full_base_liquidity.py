"""Atomic Parquet repository for full-base liquidity scope-review shadows."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1.full_base_liquidity import (
    FullBaseDatasetReferenceV1,
    FullBaseDecisionV1,
    FullBaseFunnelStageV1,
    FullBaseMembershipV1,
    FullBaseMetricV1,
    FullBasePolicySummaryV1,
    FullBaseScopeReviewManifestV1,
    FullBaseSetDiffV1,
)
from tip_api.persistence.parquet.trailing_liquidity import (
    DECIMAL_PRECISION,
    DECIMAL_SCALE,
    MANIFEST_FILE,
    PARQUET_FILE,
    TrailingLiquidityConflictError,
    TrailingLiquidityCorruptionError,
    TrailingLiquidityPersistenceError,
    _file_sha256,
    _fsync_directory,
    _json_fingerprint,
    _read_partition,
    _reject_symlink_chain,
    _rows_fingerprint,
    _stage_partition,
    _staging,
    _validated_root,
    _validate_decimal,
    _write_json,
)

METRIC_DATASET = "trailing-liquidity-full-base-metrics"
DECISION_DATASET = "trailing-liquidity-full-base-decisions"
MEMBERSHIP_DATASET = "trailing-liquidity-full-base-memberships"
DIFF_DATASET = "trailing-liquidity-full-base-diffs"
FUNNEL_DATASET = "trailing-liquidity-full-base-funnels"
BASE_DIRECTORY = "market-data/derived"
LOGICAL_DIRECTORY = "market-data/snapshots/trailing-liquidity-full-base-scope-review"

METRIC_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of_date", pa.date32(), False), pa.field("instrument_id", pa.string(), False),
    pa.field("display_ticker", pa.string(), False), pa.field("provider_type_code", pa.string(), False),
    pa.field("primary_exchange", pa.string(), True), pa.field("supported_exchange", pa.bool_(), False),
    pa.field("current_bar_present", pa.bool_(), False), pa.field("previous_bar_present", pa.bool_(), False),
    pa.field("previous_close", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
    pa.field("previous_dollar_volume_proxy", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
    pa.field("observation_count", pa.int16(), False),
    pa.field("median_dollar_volume_proxy_20s", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
    pa.field("metric_status", pa.string(), False), pa.field("quality_flags", pa.list_(pa.string()), False),
    pa.field("source_window_fingerprint", pa.string(), False), pa.field("calculated_at", pa.timestamp("us", tz="UTC"), False),
])
DECISION_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of_date", pa.date32(), False), pa.field("policy_id", pa.string(), False),
    pa.field("instrument_id", pa.string(), False), pa.field("provider_type_code", pa.string(), False),
    pa.field("disposition", pa.string(), False), pa.field("included", pa.bool_(), False), pa.field("stage_id", pa.string(), False),
    pa.field("reason_codes", pa.list_(pa.string()), False), pa.field("reviewed_override_decision", pa.string(), True),
    pa.field("calculated_at", pa.timestamp("us", tz="UTC"), False),
])
MEMBERSHIP_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("policy_id", pa.string(), False), pa.field("instrument_id", pa.string(), False),
    pa.field("provider_type_code", pa.string(), False),
])
DIFF_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("policy_id", pa.string(), False), pa.field("instrument_id", pa.string(), False),
    pa.field("provider_type_code", pa.string(), False), pa.field("direction", pa.string(), False),
    pa.field("reason_code", pa.string(), False),
    pa.field("previous_dollar_volume_proxy", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
    pa.field("median_dollar_volume_proxy_20s", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
])
FUNNEL_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of_date", pa.date32(), False), pa.field("policy_id", pa.string(), False),
    pa.field("stage_order", pa.int16(), False), pa.field("stage_id", pa.string(), False), pa.field("stage_label", pa.string(), False),
    pa.field("stage_kind", pa.string(), False), pa.field("input_count", pa.int32(), False), pa.field("excluded_count", pa.int32(), False),
    pa.field("remaining_count", pa.int32(), False), pa.field("exclusion_reason_codes", pa.list_(pa.string()), False),
    pa.field("source_fingerprints", pa.list_(pa.string()), False), pa.field("calculation_version", pa.string(), False),
])


@dataclass(frozen=True, slots=True)
class CompletedFullBaseScopeReview:
    manifest: FullBaseScopeReviewManifestV1
    metrics: tuple[FullBaseMetricV1, ...]
    decisions: tuple[FullBaseDecisionV1, ...]
    memberships: tuple[FullBaseMembershipV1, ...]
    diffs: tuple[FullBaseSetDiffV1, ...]
    funnels: tuple[FullBaseFunnelStageV1, ...]


@dataclass(frozen=True, slots=True)
class FullBasePublicationResult:
    logical_manifest_path: Path
    references: dict[str, FullBaseDatasetReferenceV1]
    logical_fingerprint: str
    status: str


@dataclass(frozen=True, slots=True)
class ParquetFullBaseScopeReviewRepository:
    root: Path

    def publish(self, *, analysis_session: date, metrics, decisions, memberships, diffs, funnels,
                membership_evidence_as_of_date: date, calendar_name: str, calendar_version: str,
                window_sessions: tuple[date, ...], source_descriptor_fingerprint: str,
                source_sessions: tuple[object, ...],
                security_evidence_path: str, security_evidence_fingerprint: str,
                legacy_v1_logical_path: str, legacy_v1_logical_fingerprint: str,
                reviewed_override_logical_path: str, reviewed_override_fingerprint: str,
                policies: tuple[FullBasePolicySummaryV1, ...], previous_close_threshold,
                median_dollar_volume_threshold, created_at: datetime) -> FullBasePublicationResult:
        root = _validated_root(self.root)
        _validate_records(analysis_session, metrics, decisions, memberships, diffs, funnels)
        data = {
            "metric": (METRIC_DATASET, METRIC_SCHEMA, [_row(item) for item in sorted(metrics, key=lambda x: str(x.instrument_id))]),
            "decision": (DECISION_DATASET, DECISION_SCHEMA, [_row(item) for item in sorted(decisions, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
            "membership": (MEMBERSHIP_DATASET, MEMBERSHIP_SCHEMA, [_row(item) for item in sorted(memberships, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
            "diff": (DIFF_DATASET, DIFF_SCHEMA, [_row(item) for item in sorted(diffs, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
            "funnel": (FUNNEL_DATASET, FUNNEL_SCHEMA, [_row(item) for item in sorted(funnels, key=lambda x: (x.policy_id, x.stage_order))]),
        }
        targets, logical_target = _targets(root, analysis_session)
        for path in (*targets.values(), logical_target):
            _reject_symlink_chain(root, path)
            if path.exists() or path.is_symlink():
                raise TrailingLiquidityConflictError("full-base scope-review target already exists")
        stagings = {key: _staging(path) for key, path in targets.items()}
        logical_staging = _staging(logical_target)
        renamed: list[Path] = []
        created_at = created_at.astimezone(UTC)
        try:
            references = {}
            for key in ("metric", "decision", "membership", "diff", "funnel"):
                dataset, schema, rows = data[key]
                reference = _stage_partition(stagings[key], dataset, schema, rows, _rows_fingerprint(rows), created_at)
                references[key] = FullBaseDatasetReferenceV1(
                    dataset_path=targets[key].relative_to(root).as_posix(), record_count=reference.record_count,
                    content_fingerprint=reference.content_fingerprint, parquet_sha256=reference.parquet_sha256,
                )
            payload = {
                "analysis_session": analysis_session.isoformat(), "membership_evidence_as_of_date": membership_evidence_as_of_date.isoformat(),
                "calendar_name": calendar_name, "calendar_version": calendar_version,
                "window_sessions": [item.isoformat() for item in window_sessions],
                "source_sessions": [item.model_dump(mode="json") for item in source_sessions],
                "source_descriptor_fingerprint": source_descriptor_fingerprint,
                "security_evidence_path": security_evidence_path, "security_evidence_fingerprint": security_evidence_fingerprint,
                "legacy_v1_logical_path": legacy_v1_logical_path, "legacy_v1_logical_fingerprint": legacy_v1_logical_fingerprint,
                "legacy_v1_reproduced": True, "reviewed_override_logical_path": reviewed_override_logical_path,
                "reviewed_override_fingerprint": reviewed_override_fingerprint,
                "metric_dataset": references["metric"].model_dump(mode="json"),
                "decision_dataset": references["decision"].model_dump(mode="json"),
                "membership_dataset": references["membership"].model_dump(mode="json"),
                "diff_dataset": references["diff"].model_dump(mode="json"),
                "funnel_dataset": references["funnel"].model_dump(mode="json"),
                "policies": [item.model_dump(mode="json") for item in policies],
                "previous_close_threshold": str(previous_close_threshold), "median_dollar_volume_threshold": str(median_dollar_volume_threshold),
                "methodology_mode": "current_as_of_constituent_liquidity", "calculation_version": "full-classified-base-trailing-liquidity-v1",
            }
            logical_fingerprint = _json_fingerprint(payload)
            manifest = FullBaseScopeReviewManifestV1(**payload, created_at=created_at, logical_content_fingerprint=logical_fingerprint)
            logical_staging.mkdir()
            _write_json(logical_staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
            if FullBaseScopeReviewManifestV1.model_validate_json((logical_staging / MANIFEST_FILE).read_text()) != manifest:
                raise TrailingLiquidityCorruptionError("logical staging reread mismatch")
            _fsync_directory(logical_staging)
            for key in ("metric", "decision", "membership", "diff", "funnel"):
                target = targets[key]
                if os.stat(root).st_dev != os.stat(target.parent).st_dev:
                    raise TrailingLiquidityPersistenceError("staging and target filesystem differ")
                stagings[key].replace(target); renamed.append(target); _fsync_directory(target.parent)
            logical_staging.replace(logical_target); renamed.append(logical_target); _fsync_directory(logical_target.parent)
            completed = read_completed_full_base_scope_review(root, analysis_session=analysis_session, validate_sources=False)
            if completed.manifest.logical_content_fingerprint != logical_fingerprint:
                raise TrailingLiquidityCorruptionError("formal production reread failed")
            return FullBasePublicationResult(logical_target / MANIFEST_FILE, references, logical_fingerprint, "published")
        except Exception:
            for path in reversed(renamed):
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            for path in (*stagings.values(), logical_staging):
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            raise


def read_completed_full_base_scope_review(root: Path, *, analysis_session: date, validate_sources: bool = True) -> CompletedFullBaseScopeReview:
    root = _validated_root(root)
    targets, logical = _targets(root, analysis_session)
    manifest_path = logical / MANIFEST_FILE
    for path in (*targets.values(), logical, manifest_path):
        _reject_symlink_chain(root, path)
        if path.is_symlink(): raise TrailingLiquidityCorruptionError("scope-review path contains symlink")
    if not manifest_path.is_file(): raise TrailingLiquidityCorruptionError("scope-review logical manifest is unavailable")
    manifest = FullBaseScopeReviewManifestV1.model_validate_json(manifest_path.read_text())
    if manifest.analysis_session != analysis_session: raise TrailingLiquidityCorruptionError("analysis session mismatch")
    payload = manifest.model_dump(mode="json", exclude={"manifest_version", "completion_status", "created_at", "logical_content_fingerprint"})
    if _json_fingerprint(payload) != manifest.logical_content_fingerprint: raise TrailingLiquidityCorruptionError("logical fingerprint mismatch")
    specs = {
        "metric": (manifest.metric_dataset, METRIC_DATASET, METRIC_SCHEMA, FullBaseMetricV1),
        "decision": (manifest.decision_dataset, DECISION_DATASET, DECISION_SCHEMA, FullBaseDecisionV1),
        "membership": (manifest.membership_dataset, MEMBERSHIP_DATASET, MEMBERSHIP_SCHEMA, FullBaseMembershipV1),
        "diff": (manifest.diff_dataset, DIFF_DATASET, DIFF_SCHEMA, FullBaseSetDiffV1),
        "funnel": (manifest.funnel_dataset, FUNNEL_DATASET, FUNNEL_SCHEMA, FullBaseFunnelStageV1),
    }
    output = {}
    for key, (reference, dataset, schema, model) in specs.items():
        _read_partition(root, reference, dataset, schema, model)
        table = pq.ParquetFile(root / reference.dataset_path / PARQUET_FILE).read()
        output[key] = tuple(model.model_validate(row) for row in table.to_pylist())
    if len({item.instrument_id for item in output["metric"]}) != len(output["metric"]): raise TrailingLiquidityCorruptionError("duplicate metric key")
    if len({(item.policy_id, item.instrument_id) for item in output["decision"]}) != len(output["decision"]): raise TrailingLiquidityCorruptionError("duplicate decision key")
    membership_ids = {(item.policy_id, item.instrument_id) for item in output["membership"]}
    included_ids = {(item.policy_id, item.instrument_id) for item in output["decision"] if item.included}
    if membership_ids != included_ids: raise TrailingLiquidityCorruptionError("membership and decision references disagree")
    if validate_sources:
        _validate_sources(root, manifest)
    return CompletedFullBaseScopeReview(manifest, output["metric"], output["decision"], output["membership"], output["diff"], output["funnel"])


def _validate_sources(root: Path, manifest: FullBaseScopeReviewManifestV1) -> None:
    from tip_api.contracts.security_classification.v1.universe_review import ReviewedEligibilityOverrideV1
    from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
    from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
    from tip_api.persistence.parquet.trailing_liquidity import read_completed_trailing_liquidity_publication
    from tip_api.persistence.parquet.universe_review import OVERRIDE_SCHEMA, read_completed_universe_review
    from tip_api.services.universe_pre_activation import records_fingerprint
    repository = CanonicalEodReadRepository(root)
    for reference in manifest.source_sessions:
        actual = repository.inspect_session(reference.session_date)
        if (actual.record_count, actual.content_fingerprint, actual.parquet_sha256,
            actual.identity_snapshot_date, actual.identity_snapshot_fingerprint) != (
            reference.record_count, reference.content_fingerprint, reference.parquet_sha256,
            reference.identity_snapshot_date, reference.identity_snapshot_fingerprint):
            raise TrailingLiquidityCorruptionError("full-base EOD source reference mismatch")
    security = read_completed_security_evidence_snapshot(root, as_of_date=manifest.membership_evidence_as_of_date)
    if (security.manifest.evidence_path, security.manifest.logical_content_sha256) != (
        manifest.security_evidence_path, manifest.security_evidence_fingerprint):
        raise TrailingLiquidityCorruptionError("full-base security evidence reference mismatch")
    trailing = read_completed_trailing_liquidity_publication(root, analysis_session=manifest.analysis_session, validate_sources=True)
    if trailing.manifest.logical_content_fingerprint != manifest.legacy_v1_logical_fingerprint:
        raise TrailingLiquidityCorruptionError("full-base V1 reproduction source mismatch")
    review = read_completed_universe_review(root, analysis_session=manifest.analysis_session, validate_source=True)
    expected_override_path = manifest.reviewed_override_logical_path.replace(
        "market-data/snapshots/universe-pre-activation-review", "market-data/derived/reviewed-universe-eligibility-overrides/schema_version=1"
    )
    if review.manifest.override_dataset.dataset_path != expected_override_path:
        raise TrailingLiquidityCorruptionError("full-base reviewed override dataset reference mismatch")
    logical = root / manifest.reviewed_override_logical_path / MANIFEST_FILE
    if not logical.is_file() or logical.is_symlink():
        raise TrailingLiquidityCorruptionError("full-base reviewed override logical reference mismatch")
    override_table = pq.ParquetFile(root / review.manifest.override_dataset.dataset_path / PARQUET_FILE).read()
    if override_table.schema != OVERRIDE_SCHEMA:
        raise TrailingLiquidityCorruptionError("full-base reviewed override schema mismatch")
    overrides = tuple(ReviewedEligibilityOverrideV1.model_validate(row) for row in override_table.to_pylist())
    if records_fingerprint(overrides) != manifest.reviewed_override_fingerprint:
        raise TrailingLiquidityCorruptionError("full-base reviewed override semantic fingerprint mismatch")


def _targets(root: Path, analysis_session: date):
    suffix = f"analysis_session={analysis_session.isoformat()}"
    targets = {key: root / BASE_DIRECTORY / f"{dataset}/schema_version=1/{suffix}" for key, dataset in {
        "metric": METRIC_DATASET, "decision": DECISION_DATASET, "membership": MEMBERSHIP_DATASET,
        "diff": DIFF_DATASET, "funnel": FUNNEL_DATASET,
    }.items()}
    return targets, root / LOGICAL_DIRECTORY / suffix


def _row(item) -> dict[str, Any]:
    row = item.model_dump(mode="python")
    if "instrument_id" in row: row["instrument_id"] = str(item.instrument_id)
    if "disposition" in row: row["disposition"] = item.disposition.value
    for key in ("quality_flags", "reason_codes", "exclusion_reason_codes", "source_fingerprints"):
        if key in row: row[key] = list(row[key])
    for key in ("previous_close", "previous_dollar_volume_proxy", "median_dollar_volume_proxy_20s"):
        if key in row: _validate_decimal(row[key])
    return row


def _validate_records(analysis_session, metrics, decisions, memberships, diffs, funnels):
    if not all((metrics, decisions, memberships, diffs, funnels)): raise TrailingLiquidityPersistenceError("all scope-review datasets are required")
    for group in (metrics, decisions, memberships, diffs, funnels):
        if any(item.analysis_session != analysis_session for item in group): raise TrailingLiquidityPersistenceError("record analysis session mismatch")
    metric_ids = {item.instrument_id for item in metrics}
    if len(metric_ids) != len(metrics): raise TrailingLiquidityPersistenceError("duplicate metric business key")
    if any(item.instrument_id not in metric_ids for item in decisions): raise TrailingLiquidityPersistenceError("orphan decision metric reference")
