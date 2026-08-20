"""Atomic Parquet repository for full-base liquidity scope-review shadows."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
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
    _write_json,
)

METRIC_DATASET = "trailing-liquidity-full-base-metrics"
DECISION_DATASET = "trailing-liquidity-full-base-decisions"
MEMBERSHIP_DATASET = "trailing-liquidity-full-base-memberships"
DIFF_DATASET = "trailing-liquidity-full-base-diffs"
FUNNEL_DATASET = "trailing-liquidity-full-base-funnels"
BASE_DIRECTORY = "market-data/derived"
LOGICAL_DIRECTORY = "market-data/snapshots/trailing-liquidity-full-base-scope-review"

# A Decimal128(38,10) input can produce a 76-digit/scale-20 product.  The
# average of two products can require 77 digits and scale 21.  Arrow's
# Decimal256 tops out at 76 digits, so the median uses an exact Decimal tuple.
MEDIAN_MAX_PRECISION = 77
MEDIAN_MAX_SCALE = 21
MEDIAN_MAX_INTEGER_DIGITS = 56
EXACT_DECIMAL_TYPE = pa.struct([
    pa.field("sign", pa.bool_(), False),
    pa.field("coefficient", pa.binary(), False),
    pa.field("exponent", pa.int32(), False),
])

METRIC_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of_date", pa.date32(), False), pa.field("instrument_id", pa.string(), False),
    pa.field("display_ticker", pa.string(), False), pa.field("provider_type_code", pa.string(), False),
    pa.field("primary_exchange", pa.string(), True), pa.field("supported_exchange", pa.bool_(), False),
    pa.field("current_bar_present", pa.bool_(), False), pa.field("previous_bar_present", pa.bool_(), False),
    pa.field("previous_close", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), True),
    pa.field("previous_dollar_volume_below_threshold", pa.bool_(), True),
    pa.field("observation_count", pa.int16(), False),
    pa.field("median_dollar_volume_proxy_20s", EXACT_DECIMAL_TYPE, True),
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
    pa.field("rescued_from_previous_session_scope", pa.bool_(), False),
    pa.field("median_dollar_volume_proxy_20s", EXACT_DECIMAL_TYPE, True),
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
        data = _publication_data(metrics, decisions, memberships, diffs, funnels)
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
        transform = _logical_row if key in {"metric", "diff"} else None
        _read_partition(root, reference, dataset, schema, model, row_transform=transform)
        table = pq.ParquetFile(root / reference.dataset_path / PARQUET_FILE).read()
        output[key] = tuple(model.model_validate(row if transform is None else transform(row)) for row in table.to_pylist())
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


def _publication_data(metrics, decisions, memberships, diffs, funnels):
    return {
        "metric": (METRIC_DATASET, METRIC_SCHEMA, [_row(item, METRIC_DATASET) for item in sorted(metrics, key=lambda x: str(x.instrument_id))]),
        "decision": (DECISION_DATASET, DECISION_SCHEMA, [_row(item, DECISION_DATASET) for item in sorted(decisions, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
        "membership": (MEMBERSHIP_DATASET, MEMBERSHIP_SCHEMA, [_row(item, MEMBERSHIP_DATASET) for item in sorted(memberships, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
        "diff": (DIFF_DATASET, DIFF_SCHEMA, [_row(item, DIFF_DATASET) for item in sorted(diffs, key=lambda x: (x.policy_id, str(x.instrument_id)))]),
        "funnel": (FUNNEL_DATASET, FUNNEL_SCHEMA, [_row(item, FUNNEL_DATASET) for item in sorted(funnels, key=lambda x: (x.policy_id, x.stage_order))]),
    }


def validate_full_base_physical_round_trip(*, metrics, decisions, memberships, diffs, funnels, temp_root: Path | None = None) -> dict[str, int]:
    """Exercise every physical schema through local Parquet without touching /data."""
    data = _publication_data(metrics, decisions, memberships, diffs, funnels)
    with tempfile.TemporaryDirectory(prefix="tip-full-base-physical-", dir=temp_root or Path("/tmp")) as directory:
        root = Path(directory)
        counts = {}
        for key, (_, schema, rows) in data.items():
            path = root / f"{key}.parquet"
            table = pa.Table.from_pylist(rows, schema=schema)
            pq.write_table(table, path)
            reread = pq.ParquetFile(path).read()
            if not reread.schema.equals(schema, check_metadata=False) or reread.num_rows != len(rows):
                raise TrailingLiquidityCorruptionError(f"{key} temporary Parquet schema/count mismatch")
            if _rows_fingerprint(reread.to_pylist()) != _rows_fingerprint(rows):
                raise TrailingLiquidityCorruptionError(f"{key} temporary Parquet fingerprint mismatch")
            model = {"metric": FullBaseMetricV1, "decision": FullBaseDecisionV1, "membership": FullBaseMembershipV1,
                     "diff": FullBaseSetDiffV1, "funnel": FullBaseFunnelStageV1}[key]
            transform = _logical_row if key in {"metric", "diff"} else None
            logical = tuple(model.model_validate(row if transform is None else transform(row)) for row in reread.to_pylist())
            if len(logical) != len(rows):
                raise TrailingLiquidityCorruptionError(f"{key} temporary Parquet logical reread mismatch")
            counts[key] = len(logical)
        return counts


def _row(item, dataset: str) -> dict[str, Any]:
    row = item.model_dump(mode="python")
    if "instrument_id" in row: row["instrument_id"] = str(item.instrument_id)
    if "disposition" in row: row["disposition"] = item.disposition.value
    for key in ("quality_flags", "reason_codes", "exclusion_reason_codes", "source_fingerprints"):
        if key in row: row[key] = list(row[key])
    if "previous_close" in row:
        _validate_fixed_decimal(row["previous_close"], dataset=dataset, field="previous_close", item=item)
    if "median_dollar_volume_proxy_20s" in row:
        row["median_dollar_volume_proxy_20s"] = _encode_exact_median(
            row["median_dollar_volume_proxy_20s"], dataset=dataset, item=item
        )
    return row


def _decimal_shape(value: Decimal) -> tuple[int, int, int]:
    _, digits, exponent = value.as_tuple()
    precision = len(digits)
    scale = max(-exponent, 0)
    integer_digits = max(precision - scale, 0) if exponent < 0 else precision + exponent
    return precision, scale, integer_digits


def _contract_error(*, dataset: str, field: str, item, value: Decimal, approved_precision: int,
                    approved_scale: int, reason: str) -> TrailingLiquidityPersistenceError:
    precision, scale, _ = _decimal_shape(value)
    return TrailingLiquidityPersistenceError(
        f"dataset={dataset} field={field} instrument_id={item.instrument_id} "
        f"ticker={getattr(item, 'display_ticker', '<unavailable>')} observed_precision={precision} "
        f"observed_scale={scale} approved_precision={approved_precision} approved_scale={approved_scale} reason={reason}"
    )


def _validate_fixed_decimal(value: Decimal | None, *, dataset: str, field: str, item) -> None:
    if value is None:
        return
    precision, scale, integer_digits = _decimal_shape(value)
    if not value.is_finite() or scale > DECIMAL_SCALE or precision > DECIMAL_PRECISION or integer_digits > DECIMAL_PRECISION - DECIMAL_SCALE:
        raise _contract_error(dataset=dataset, field=field, item=item, value=value,
                              approved_precision=DECIMAL_PRECISION, approved_scale=DECIMAL_SCALE,
                              reason="fixed_decimal_contract_exceeded")


def _encode_exact_median(value: Decimal | None, *, dataset: str, item) -> dict[str, Any] | None:
    if value is None:
        return None
    precision, scale, integer_digits = _decimal_shape(value)
    if (not value.is_finite() or value.is_signed() or precision > MEDIAN_MAX_PRECISION or
            scale > MEDIAN_MAX_SCALE or integer_digits > MEDIAN_MAX_INTEGER_DIGITS):
        raise _contract_error(dataset=dataset, field="median_dollar_volume_proxy_20s", item=item, value=value,
                              approved_precision=MEDIAN_MAX_PRECISION, approved_scale=MEDIAN_MAX_SCALE,
                              reason="exact_median_contract_exceeded")
    sign, digits, exponent = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in digits))
    encoded = coefficient.to_bytes(max(1, (coefficient.bit_length() + 7) // 8), "big", signed=False)
    return {"sign": bool(sign), "coefficient": encoded, "exponent": exponent}


def _decode_exact_median(value: dict[str, Any] | None) -> Decimal | None:
    if value is None:
        return None
    if set(value) != {"sign", "coefficient", "exponent"} or not isinstance(value["coefficient"], bytes):
        raise TrailingLiquidityCorruptionError("exact median physical tuple is malformed")
    coefficient = int.from_bytes(value["coefficient"], "big", signed=False)
    digits = tuple(int(digit) for digit in str(coefficient))
    return Decimal((int(value["sign"]), digits, int(value["exponent"])))


def _logical_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    if "median_dollar_volume_proxy_20s" in output:
        output["median_dollar_volume_proxy_20s"] = _decode_exact_median(output["median_dollar_volume_proxy_20s"])
    return output


def _validate_records(analysis_session, metrics, decisions, memberships, diffs, funnels):
    if not all((metrics, decisions, memberships, diffs, funnels)): raise TrailingLiquidityPersistenceError("all scope-review datasets are required")
    for group in (metrics, decisions, memberships, diffs, funnels):
        if any(item.analysis_session != analysis_session for item in group): raise TrailingLiquidityPersistenceError("record analysis session mismatch")
    metric_ids = {item.instrument_id for item in metrics}
    if len(metric_ids) != len(metrics): raise TrailingLiquidityPersistenceError("duplicate metric business key")
    if any(item.instrument_id not in metric_ids for item in decisions): raise TrailingLiquidityPersistenceError("orphan decision metric reference")
