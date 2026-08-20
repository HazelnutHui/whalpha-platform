"""Atomic Parquet repository for reviewed Universe pre-activation shadows."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.contracts.security_classification.v1.universe_review import (
    ReviewedEligibilityOverrideV1,
    UniversePreActivationManifestV1,
    UniverseReviewDatasetReferenceV1,
    UniverseReviewDecisionV1,
    UniverseSetSummaryV1,
    validate_override_intervals,
)
from tip_api.persistence.parquet.trailing_liquidity import read_completed_trailing_liquidity_publication
from tip_api.persistence.universe_review import (
    CompletedUniverseReviewPublication,
    UniverseReviewConflictError,
    UniverseReviewCorruptionError,
    UniverseReviewPublicationResult,
)

PARQUET = "part-00000.parquet"
MANIFEST = "manifest.json"
OVERRIDE_DATASET = "reviewed-universe-eligibility-overrides"
REVIEW_DATASET = "universe-pre-activation-review-decisions"
OVERRIDE_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("override_id", pa.string(), False),
    pa.field("instrument_id", pa.string(), False),
    pa.field("effective_from", pa.date32(), False), pa.field("effective_to", pa.date32(), True),
    pa.field("decision", pa.string(), False), pa.field("asserted_security_form", pa.string(), False),
    pa.field("asserted_issuer_structure", pa.string(), False), pa.field("evidence_grade", pa.string(), False),
    pa.field("source_reference", pa.string(), False), pa.field("source_document_date", pa.date32(), False),
    pa.field("reviewer_identifier", pa.string(), False), pa.field("reason_code", pa.string(), False),
    pa.field("reason", pa.string(), False), pa.field("created_at", pa.timestamp("us", tz="UTC"), False),
])
REVIEW_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("universe_id", pa.string(), False), pa.field("instrument_id", pa.string(), False),
    pa.field("provider_type_code", pa.string(), False), pa.field("base_included", pa.bool_(), False),
    pa.field("override_decision", pa.string(), True), pa.field("final_included", pa.bool_(), False),
    pa.field("primary_reason", pa.string(), False), pa.field("source_trailing_decision_fingerprint", pa.string(), False),
    pa.field("reviewed_override_fingerprint", pa.string(), False), pa.field("created_at", pa.timestamp("us", tz="UTC"), False),
])


@dataclass(frozen=True, slots=True)
class ParquetUniverseReviewRepository:
    root: Path

    def publish(self, *, analysis_session: date, overrides: tuple[ReviewedEligibilityOverrideV1, ...],
                decisions: tuple[UniverseReviewDecisionV1, ...], summaries: tuple[UniverseSetSummaryV1, ...],
                membership_evidence_as_of_date: date, trailing_logical_fingerprint: str,
                trailing_decision_fingerprint: str, legacy_count: int,
                legacy_membership_fingerprint: str, legacy_analysis_session: date,
                legacy_previous_session: date, legacy_current_eod_fingerprint: str,
                legacy_previous_eod_fingerprint: str, created_at: datetime) -> UniverseReviewPublicationResult:
        root = _root(self.root)
        validate_override_intervals(overrides)
        if not decisions or any(item.analysis_session != analysis_session for item in decisions):
            raise UniverseReviewCorruptionError("review decisions are missing or session-mismatched")
        keys = [(item.universe_id, item.instrument_id) for item in decisions]
        if len(keys) != len(set(keys)):
            raise UniverseReviewCorruptionError("duplicate review business key")
        override_rows = [_override_row(x) for x in sorted(overrides, key=lambda x: (str(x.instrument_id), x.effective_from))]
        review_rows = [_review_row(x) for x in sorted(decisions, key=lambda x: (x.universe_id, str(x.instrument_id)))]
        override_fp, review_fp = _rows_fp(override_rows), _rows_fp(review_rows)
        override_target, review_target, logical_target = _targets(root, analysis_session)
        for target in (override_target, review_target, logical_target):
            _reject_symlinks(root, target)
            if target.exists() or target.is_symlink():
                raise UniverseReviewConflictError("Universe review target already exists")
        stages = tuple(target.parent / f".{target.name}.staging-{uuid4().hex}" for target in (override_target, review_target, logical_target))
        renamed: list[Path] = []
        try:
            override_ref = _stage(stages[0], OVERRIDE_DATASET, OVERRIDE_SCHEMA, override_rows, override_fp, created_at)
            review_ref = _stage(stages[1], REVIEW_DATASET, REVIEW_SCHEMA, review_rows, review_fp, created_at)
            override_ref = override_ref.model_copy(update={"dataset_path": override_target.relative_to(root).as_posix()})
            review_ref = review_ref.model_copy(update={"dataset_path": review_target.relative_to(root).as_posix()})
            trailing_path = f"market-data/snapshots/trailing-liquidity-shadow/analysis_session={analysis_session.isoformat()}"
            payload = {
                "analysis_session": analysis_session.isoformat(),
                "membership_evidence_as_of_date": membership_evidence_as_of_date.isoformat(),
                "trailing_logical_path": trailing_path,
                "trailing_logical_fingerprint": trailing_logical_fingerprint,
                "trailing_decision_fingerprint": trailing_decision_fingerprint,
                "legacy_count": legacy_count,
                "legacy_membership_fingerprint": legacy_membership_fingerprint,
                "legacy_analysis_session": legacy_analysis_session.isoformat(),
                "legacy_previous_session": legacy_previous_session.isoformat(),
                "legacy_current_eod_fingerprint": legacy_current_eod_fingerprint,
                "legacy_previous_eod_fingerprint": legacy_previous_eod_fingerprint,
                "legacy_policy_version": "legacy-liquid-screen-provisional-v1",
                "override_dataset": override_ref.model_dump(mode="json"),
                "review_dataset": review_ref.model_dump(mode="json"),
                "universes": [x.model_dump(mode="json") for x in summaries],
            }
            logical_fp = _json_fp(payload)
            manifest = UniversePreActivationManifestV1(**payload, created_at=created_at, logical_content_fingerprint=logical_fp)
            stages[2].mkdir(parents=True)
            _write_json(stages[2] / MANIFEST, manifest.model_dump(mode="json"))
            if UniversePreActivationManifestV1.model_validate_json((stages[2] / MANIFEST).read_text()) != manifest:
                raise UniverseReviewCorruptionError("staged logical manifest reread failed")
            for staging, target in zip(stages, (override_target, review_target, logical_target), strict=True):
                target.parent.mkdir(parents=True, exist_ok=True)
                if os.stat(root).st_dev != os.stat(target.parent).st_dev:
                    raise UniverseReviewCorruptionError("staging filesystem differs")
                staging.replace(target); renamed.append(target)
            completed = read_completed_universe_review(root, analysis_session=analysis_session, validate_source=False)
            if completed.manifest.logical_content_fingerprint != logical_fp:
                raise UniverseReviewCorruptionError("production reread failed")
            return UniverseReviewPublicationResult(override_target, review_target, logical_target / MANIFEST,
                len(overrides), len(decisions), override_fp, review_fp, override_ref.parquet_sha256,
                review_ref.parquet_sha256, logical_fp)
        except Exception:
            for path in reversed(renamed):
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            for path in stages:
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            raise


def read_completed_universe_review(root: Path, *, analysis_session: date, validate_source: bool = True) -> CompletedUniverseReviewPublication:
    root = _root(root)
    override_target, review_target, logical_target = _targets(root, analysis_session)
    for target in (override_target, review_target, logical_target):
        _reject_symlinks(root, target)
        if target.is_symlink() or not target.is_dir(): raise UniverseReviewCorruptionError("completed target unavailable")
    mp = logical_target / MANIFEST
    if mp.is_symlink() or not mp.is_file(): raise UniverseReviewCorruptionError("logical manifest unavailable")
    manifest = UniversePreActivationManifestV1.model_validate_json(mp.read_text())
    payload = manifest.model_dump(mode="json", exclude={"manifest_version","completion_status","created_at","logical_content_fingerprint"})
    if _json_fp(payload) != manifest.logical_content_fingerprint: raise UniverseReviewCorruptionError("logical fingerprint mismatch")
    oc = _read(root, manifest.override_dataset, OVERRIDE_DATASET, OVERRIDE_SCHEMA, ReviewedEligibilityOverrideV1)
    rc = _read(root, manifest.review_dataset, REVIEW_DATASET, REVIEW_SCHEMA, UniverseReviewDecisionV1)
    if sum(x.base_passed_count for x in manifest.universes) != rc: raise UniverseReviewCorruptionError("review counts do not reconcile")
    if validate_source:
        trailing = read_completed_trailing_liquidity_publication(root, analysis_session=analysis_session, validate_sources=True)
        if trailing.manifest.logical_content_fingerprint != manifest.trailing_logical_fingerprint or trailing.manifest.decision_dataset.content_fingerprint != manifest.trailing_decision_fingerprint:
            raise UniverseReviewCorruptionError("trailing source reference mismatch")
        eod = CanonicalEodReadRepository(root)
        current = eod.inspect_session(manifest.legacy_analysis_session)
        previous = eod.inspect_session(manifest.legacy_previous_session)
        if (
            current.content_fingerprint != manifest.legacy_current_eod_fingerprint
            or previous.content_fingerprint != manifest.legacy_previous_eod_fingerprint
        ):
            raise UniverseReviewCorruptionError("Legacy EOD source reference mismatch")
    return CompletedUniverseReviewPublication(manifest, oc, rc)


def _stage(path: Path, name: str, schema: pa.Schema, rows: list[dict[str, Any]], fp: str, created_at: datetime) -> UniverseReviewDatasetReferenceV1:
    path.mkdir(parents=True); parquet = path / PARQUET
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), parquet)
    sha = _file_sha(parquet)
    table = pq.ParquetFile(parquet).read()
    if table.schema != schema or table.num_rows != len(rows) or _rows_fp(table.to_pylist()) != fp: raise UniverseReviewCorruptionError("staged Parquet reread failed")
    _write_json(path / MANIFEST, {"manifest_version":"1.0","dataset_name":name,"schema_version":"1.0","record_count":len(rows),"content_fingerprint":fp,"parquet_sha256":sha,"parquet_file":PARQUET,"created_at":created_at.astimezone(UTC).isoformat(),"completion_status":"completed"})
    return UniverseReviewDatasetReferenceV1(dataset_path="staging", record_count=len(rows), content_fingerprint=fp, parquet_sha256=sha)


def _read(root: Path, ref: UniverseReviewDatasetReferenceV1, name: str, schema: pa.Schema, model: type[Any]) -> int:
    path = root / ref.dataset_path; _reject_symlinks(root, path)
    manifest, parquet = path / MANIFEST, path / PARQUET
    if any(x.is_symlink() for x in (path, manifest, parquet)) or not manifest.is_file() or not parquet.is_file(): raise UniverseReviewCorruptionError("dataset incomplete")
    meta = json.loads(manifest.read_text())
    expected = {"dataset_name":name,"schema_version":"1.0","record_count":ref.record_count,"content_fingerprint":ref.content_fingerprint,"parquet_sha256":ref.parquet_sha256,"parquet_file":PARQUET,"completion_status":"completed"}
    if any(meta.get(k) != v for k,v in expected.items()): raise UniverseReviewCorruptionError("dataset manifest mismatch")
    table = pq.ParquetFile(parquet).read()
    if table.schema != schema or table.num_rows != ref.record_count or _rows_fp(table.to_pylist()) != ref.content_fingerprint or _file_sha(parquet) != ref.parquet_sha256: raise UniverseReviewCorruptionError("dataset content mismatch")
    records = tuple(model.model_validate(row) for row in table.to_pylist())
    if model is ReviewedEligibilityOverrideV1: validate_override_intervals(records)
    return table.num_rows


def _override_row(x: ReviewedEligibilityOverrideV1) -> dict[str, Any]:
    row=x.model_dump(mode="python"); row["override_id"]=str(x.override_id); row["instrument_id"]=str(x.instrument_id); row["decision"]=x.decision.value; row["asserted_security_form"]=x.asserted_security_form.value; row["asserted_issuer_structure"]=x.asserted_issuer_structure.value; row["evidence_grade"]=x.evidence_grade.value; return row
def _review_row(x: UniverseReviewDecisionV1) -> dict[str, Any]:
    row=x.model_dump(mode="python"); row["instrument_id"]=str(x.instrument_id); row["override_decision"]=None if x.override_decision is None else x.override_decision.value; return row
def _targets(root: Path, session: date):
    suffix=f"schema_version=1/analysis_session={session.isoformat()}"
    return (root/f"market-data/derived/reviewed-universe-eligibility-overrides/{suffix}", root/f"market-data/derived/universe-pre-activation-review/{suffix}", root/f"market-data/snapshots/universe-pre-activation-review/analysis_session={session.isoformat()}")
def _root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir(): raise UniverseReviewCorruptionError("data root must be an absolute regular directory")
    return root.resolve(strict=True)
def _reject_symlinks(root: Path, path: Path) -> None:
    try: path.relative_to(root)
    except ValueError as exc: raise UniverseReviewCorruptionError("path escapes root") from exc
    current=root
    for part in path.relative_to(root).parts:
        current=current/part
        if current.is_symlink(): raise UniverseReviewCorruptionError("symlink path rejected")
def _canonical(value: Any) -> Any:
    if isinstance(value, datetime): return value.astimezone(UTC).isoformat()
    if isinstance(value, date): return value.isoformat()
    return value
def _rows_fp(rows: list[dict[str, Any]]) -> str:
    return _json_fp([{k:_canonical(v) for k,v in row.items() if k != "created_at"} for row in rows])
def _json_fp(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def _file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()
def _write_json(path: Path, value: Any) -> None:
    with path.open("x",encoding="utf-8") as handle: json.dump(value,handle,sort_keys=True,separators=(",",":")); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
