"""Atomic single-target repository for reviewed-form superseding shadows."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1.full_base_liquidity import FullBaseDatasetReferenceV1
from tip_api.contracts.market_data.v2.superseding_full_base import SupersedingFullBaseManifestV2
from tip_api.contracts.security_classification.v1 import SecurityForm
from tip_api.contracts.security_classification.v1.universe_review import ReviewedSecurityFormEvidenceV1, validate_reviewed_security_form_intervals
from tip_api.persistence.parquet.full_base_liquidity import (
    DECISION_SCHEMA, DIFF_SCHEMA, FUNNEL_SCHEMA, MEMBERSHIP_SCHEMA, METRIC_SCHEMA,
    _logical_row, _publication_data,
)
from tip_api.persistence.parquet.trailing_liquidity import (
    TrailingLiquidityConflictError, TrailingLiquidityCorruptionError,
    _file_sha256, _fsync_directory, _json_fingerprint, _reject_symlink_chain,
    _rows_fingerprint, _validated_root,
)

REVISION_ID = "authoritative-security-form-v2"
BASE = "market-data/snapshots/trailing-liquidity-full-base-scope-review-v2"
PARQUET_FILES = {
    "reviewed_security_form": "reviewed-security-form-evidence.parquet",
    "metric": "metrics.parquet", "decision": "decisions.parquet",
    "membership": "memberships.parquet", "diff": "diffs.parquet", "funnel": "funnels.parquet",
}
MANIFEST_FILE = "manifest.json"
REVIEWED_FORM_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False),
    pa.field("evidence_id", pa.string(), False),
    pa.field("instrument_id", pa.string(), False),
    pa.field("effective_from", pa.date32(), False),
    pa.field("effective_to", pa.date32(), True),
    pa.field("reviewed_security_form", pa.string(), False),
    pa.field("evidence_type", pa.string(), False),
    pa.field("sources", pa.list_(pa.struct([
        pa.field("filing_type", pa.string(), False), pa.field("document_date", pa.date32(), False),
        pa.field("filing_date", pa.date32(), True),
        pa.field("covered_fact", pa.string(), False), pa.field("fact_effective_from", pa.date32(), False),
        pa.field("official_source_url", pa.string(), False), pa.field("supported_conclusion", pa.string(), False),
    ])), False),
    pa.field("reviewer_identifier", pa.string(), False), pa.field("reason_code", pa.string(), False),
    pa.field("reason", pa.string(), False), pa.field("recorded_at", pa.timestamp("us", tz="UTC"), False),
    pa.field("reviewed_at", pa.timestamp("us", tz="UTC"), False),
])


@dataclass(frozen=True, slots=True)
class CompletedSupersedingFullBase:
    manifest: SupersedingFullBaseManifestV2
    reviewed_security_forms: tuple[ReviewedSecurityFormEvidenceV1, ...]
    metrics: tuple
    decisions: tuple
    memberships: tuple
    diffs: tuple
    funnels: tuple


def target_path(root: Path, analysis_session: date) -> Path:
    return root / BASE / f"revision={REVISION_ID}" / f"analysis_session={analysis_session.isoformat()}"


def _evidence_rows(records):
    rows = []
    for item in sorted(records, key=lambda row: (str(row.instrument_id), row.effective_from, str(row.evidence_id))):
        row = item.model_dump(mode="python")
        row["evidence_id"] = str(item.evidence_id); row["instrument_id"] = str(item.instrument_id)
        row["reviewed_security_form"] = item.reviewed_security_form.value
        row["evidence_type"] = item.evidence_type.value
        row["sources"] = [
            {**source.model_dump(mode="python"), "covered_fact": source.covered_fact.value}
            for source in item.sources
        ]
        rows.append(row)
    return rows


def _write_table(path: Path, rows, schema) -> FullBaseDatasetReferenceV1:
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path)
    with path.open("rb") as handle: os.fsync(handle.fileno())
    reread = pq.ParquetFile(path).read()
    if not reread.schema.equals(schema, check_metadata=False) or reread.num_rows != len(rows):
        raise TrailingLiquidityCorruptionError("superseding temporary Parquet reread mismatch")
    return FullBaseDatasetReferenceV1(dataset_path=path.name, record_count=len(rows),
        content_fingerprint=_rows_fingerprint(rows), parquet_sha256=_file_sha256(path))


@dataclass(frozen=True, slots=True)
class ParquetSupersedingFullBaseRepository:
    root: Path

    def publish(self, *, analysis_session, membership_evidence_as_of_date, reviewed_security_forms,
                metrics, decisions, memberships, diffs, funnels, policies,
                source_full_base_logical_path, source_full_base_logical_fingerprint,
                source_descriptor_fingerprint, created_at):
        root = _validated_root(self.root)
        target = target_path(root, analysis_session)
        _reject_symlink_chain(root, target)
        if target.exists() or target.is_symlink():
            raise TrailingLiquidityConflictError("superseding full-base target already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / f".{target.name}.staging-{os.getpid()}"
        _reject_symlink_chain(root, staging)
        if staging.exists() or staging.is_symlink():
            raise TrailingLiquidityConflictError("superseding staging already exists")
        renamed = False
        try:
            staging.mkdir()
            data = _publication_data(metrics, decisions, memberships, diffs, funnels)
            specs = {key: (data[key][2], data[key][1]) for key in data}
            specs["reviewed_security_form"] = (_evidence_rows(reviewed_security_forms), REVIEWED_FORM_SCHEMA)
            refs = {key: _write_table(staging / PARQUET_FILES[key], rows, schema) for key, (rows, schema) in specs.items()}
            payload = {
                "revision_id": REVISION_ID, "analysis_session": analysis_session.isoformat(),
                "membership_evidence_as_of_date": membership_evidence_as_of_date.isoformat(),
                "source_full_base_logical_path": source_full_base_logical_path,
                "source_full_base_logical_fingerprint": source_full_base_logical_fingerprint,
                "source_descriptor_fingerprint": source_descriptor_fingerprint,
                "reviewed_security_form_dataset": refs["reviewed_security_form"].model_dump(mode="json"),
                "metric_dataset": refs["metric"].model_dump(mode="json"),
                "decision_dataset": refs["decision"].model_dump(mode="json"),
                "membership_dataset": refs["membership"].model_dump(mode="json"),
                "diff_dataset": refs["diff"].model_dump(mode="json"),
                "funnel_dataset": refs["funnel"].model_dump(mode="json"),
                "policies": [item.model_dump(mode="json") for item in policies],
            }
            logical = _json_fingerprint(payload)
            manifest = SupersedingFullBaseManifestV2(**payload, created_at=created_at.astimezone(UTC), logical_content_fingerprint=logical)
            manifest_path = staging / MANIFEST_FILE
            manifest_path.write_text(json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n")
            with manifest_path.open("rb") as handle: os.fsync(handle.fileno())
            _fsync_directory(staging)
            staging.replace(target); renamed = True; _fsync_directory(target.parent)
            completed = read_completed_superseding_full_base(root, analysis_session=analysis_session)
            if completed.manifest.logical_content_fingerprint != logical:
                raise TrailingLiquidityCorruptionError("superseding formal reread mismatch")
            return completed
        except Exception:
            if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
            if renamed and target.exists() and not target.is_symlink(): shutil.rmtree(target)
            raise


def read_completed_superseding_full_base(root: Path, *, analysis_session: date) -> CompletedSupersedingFullBase:
    from tip_api.contracts.market_data.v1.full_base_liquidity import FullBaseDecisionV1, FullBaseFunnelStageV1, FullBaseMembershipV1, FullBaseMetricV1, FullBaseSetDiffV1
    root = _validated_root(root); target = target_path(root, analysis_session)
    _reject_symlink_chain(root, target)
    manifest_path = target / MANIFEST_FILE
    if not manifest_path.is_file() or manifest_path.is_symlink(): raise TrailingLiquidityCorruptionError("superseding manifest unavailable")
    manifest = SupersedingFullBaseManifestV2.model_validate_json(manifest_path.read_text())
    payload = manifest.model_dump(mode="json", exclude={"manifest_version", "completion_status", "created_at", "logical_content_fingerprint"})
    if _json_fingerprint(payload) != manifest.logical_content_fingerprint: raise TrailingLiquidityCorruptionError("superseding logical fingerprint mismatch")
    specs = {
        "reviewed_security_form": (manifest.reviewed_security_form_dataset, REVIEWED_FORM_SCHEMA, ReviewedSecurityFormEvidenceV1, None),
        "metric": (manifest.metric_dataset, METRIC_SCHEMA, FullBaseMetricV1, _logical_row),
        "decision": (manifest.decision_dataset, DECISION_SCHEMA, FullBaseDecisionV1, None),
        "membership": (manifest.membership_dataset, MEMBERSHIP_SCHEMA, FullBaseMembershipV1, None),
        "diff": (manifest.diff_dataset, DIFF_SCHEMA, FullBaseSetDiffV1, _logical_row),
        "funnel": (manifest.funnel_dataset, FUNNEL_SCHEMA, FullBaseFunnelStageV1, None),
    }
    output = {}
    for key, (ref, schema, model, transform) in specs.items():
        path = target / ref.dataset_path; _reject_symlink_chain(root, path)
        if path.name != PARQUET_FILES[key] or not path.is_file() or path.is_symlink(): raise TrailingLiquidityCorruptionError("superseding dataset path mismatch")
        if _file_sha256(path) != ref.parquet_sha256: raise TrailingLiquidityCorruptionError("superseding Parquet hash mismatch")
        table = pq.ParquetFile(path).read()
        if not table.schema.equals(schema, check_metadata=False) or table.num_rows != ref.record_count: raise TrailingLiquidityCorruptionError("superseding schema/count mismatch")
        rows = table.to_pylist()
        if _rows_fingerprint(rows) != ref.content_fingerprint: raise TrailingLiquidityCorruptionError("superseding content fingerprint mismatch")
        output[key] = tuple(model.model_validate(row if transform is None else transform(row)) for row in rows)
    decision_keys = {(item.policy_id, item.instrument_id) for item in output["decision"]}
    if len(decision_keys) != len(output["decision"]): raise TrailingLiquidityCorruptionError("duplicate superseding decision key")
    metric_ids = {item.instrument_id for item in output["metric"]}
    if len(metric_ids) != len(output["metric"]): raise TrailingLiquidityCorruptionError("duplicate superseding metric key")
    validate_reviewed_security_form_intervals(output["reviewed_security_form"])
    for item in output["reviewed_security_form"]:
        if item.instrument_id not in metric_ids: raise TrailingLiquidityCorruptionError("orphan reviewed security-form reference")
        expected_code = "ADRC" if item.reviewed_security_form is SecurityForm.ADR_ADS else "CS"
        metric = next(row for row in output["metric"] if row.instrument_id == item.instrument_id)
        if item.is_effective_on(analysis_session) and metric.provider_type_code != expected_code:
            raise TrailingLiquidityCorruptionError("reviewed security form and effective metric type disagree")
    memberships = {(item.policy_id, item.instrument_id) for item in output["membership"]}
    included = {(item.policy_id, item.instrument_id) for item in output["decision"] if item.included}
    if memberships != included: raise TrailingLiquidityCorruptionError("superseding membership references disagree")
    if len({(item.policy_id, item.instrument_id) for item in output["diff"]}) != len(output["diff"]):
        raise TrailingLiquidityCorruptionError("duplicate superseding diff key")
    by_policy = {summary.policy_id: summary for summary in manifest.policies}
    if len(by_policy) != len(manifest.policies): raise TrailingLiquidityCorruptionError("duplicate superseding policy summary")
    for policy_id, summary in by_policy.items():
        ids = frozenset(instrument_id for candidate_policy, instrument_id in memberships if candidate_policy == policy_id)
        from tip_api.services.universe_pre_activation import membership_fingerprint
        if len(ids) != summary.final_count or membership_fingerprint(ids) != summary.membership_fingerprint:
            raise TrailingLiquidityCorruptionError("superseding policy summary mismatch")
    return CompletedSupersedingFullBase(manifest, output["reviewed_security_form"], output["metric"], output["decision"], output["membership"], output["diff"], output["funnel"])
