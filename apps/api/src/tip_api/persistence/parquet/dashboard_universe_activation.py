"""Atomic Parquet publication and formal reader for Dashboard Universe Activation V1."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1.dashboard_universe_activation import (
    DashboardUniverseActivationDatasetReferenceV1,
    DashboardUniverseActivationManifestV1,
    DashboardUniverseActivationRecordV1,
)
from tip_api.contracts.security_classification.v1.universe_review import UniverseReviewDecisionV1
from tip_api.persistence.parquet.universe_review import REVIEW_SCHEMA, read_completed_universe_review
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.universe_pre_activation import membership_fingerprint

PUBLIC_SECONDARY_ID = "provider_classified_common_shares_plus_adrs_v1"
PARQUET = "part-00000.parquet"
MANIFEST = "manifest.json"
DATASET_NAME = "dashboard-universe-activation"
SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False), pa.field("activation_id", pa.string(), False),
    pa.field("policy_version", pa.string(), False), pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of", pa.date32(), False), pa.field("activated_at", pa.timestamp("us", tz="UTC"), False),
    pa.field("universe_id", pa.string(), False), pa.field("display_name", pa.string(), False),
    pa.field("long_display_name", pa.string(), False), pa.field("description", pa.string(), False),
    pa.field("provisional", pa.bool_(), False), pa.field("is_default", pa.bool_(), False),
    pa.field("member_count", pa.int64(), False),
    pa.field("security_type_composition", pa.list_(pa.struct([pa.field("provider_type_code", pa.string(), False), pa.field("count", pa.int64(), False)])), False),
    pa.field("membership_fingerprint", pa.string(), False), pa.field("trailing_liquidity_source_fingerprint", pa.string(), False),
    pa.field("reviewed_override_source_fingerprint", pa.string(), False), pa.field("pre_activation_review_fingerprint", pa.string(), False),
    pa.field("current_eod_fingerprint", pa.string(), False), pa.field("previous_eod_fingerprint", pa.string(), False),
    pa.field("legacy_rollback_reference", pa.string(), False), pa.field("limitations", pa.list_(pa.string()), False),
    pa.field("status", pa.string(), False),
])


class DashboardUniverseActivationError(RuntimeError): pass
class DashboardUniverseActivationConflictError(DashboardUniverseActivationError): pass


@dataclass(frozen=True, slots=True)
class CompletedDashboardUniverseActivation:
    manifest: DashboardUniverseActivationManifestV1
    universes: tuple[DashboardUniverseActivationRecordV1, ...]
    member_ids_by_universe: dict[str, frozenset[UUID]]

    def select(self, universe_id: str | None) -> tuple[DashboardUniverseActivationRecordV1, frozenset[UUID]]:
        selected = universe_id or self.manifest.default_universe_id
        records = {item.universe_id: item for item in self.universes}
        if selected not in records:
            raise ValueError("unknown dashboard universe")
        return records[selected], self.member_ids_by_universe[selected]


@dataclass(frozen=True, slots=True)
class DashboardUniverseActivationPublicationResult:
    dataset_path: Path
    logical_manifest_path: Path
    record_count: int
    content_fingerprint: str
    parquet_sha256: str
    logical_content_fingerprint: str


@dataclass(frozen=True, slots=True)
class ParquetDashboardUniverseActivationRepository:
    root: Path

    def publish(self, *, records: tuple[DashboardUniverseActivationRecordV1, ...], legacy_count: int,
                legacy_fingerprint: str, trailing_window_start: date, trailing_window_end: date,
                trailing_window_session_count: int, reviewed_override_count: int,
                activated_at: datetime) -> DashboardUniverseActivationPublicationResult:
        root = _root(self.root)
        _validate_records(records)
        session = records[0].analysis_session
        dataset_target, logical_target = _targets(root, session)
        for target in (dataset_target, logical_target):
            _reject_symlinks(root, target)
            if target.exists() or target.is_symlink(): raise DashboardUniverseActivationConflictError("activation target already exists")
        rows = [_row(item) for item in sorted(records, key=lambda item: item.universe_id)]
        content_fp = _rows_fp(rows)
        stages = (dataset_target.parent / f".{dataset_target.name}.staging-{uuid4().hex}", logical_target.parent / f".{logical_target.name}.staging-{uuid4().hex}")
        renamed: list[Path] = []
        try:
            stages[0].mkdir(parents=True); parquet = stages[0] / PARQUET
            pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), parquet)
            parquet_sha = _file_sha(parquet)
            _write_json(stages[0] / MANIFEST, {"manifest_version":"1.0","dataset_name":DATASET_NAME,"schema_version":"1.0","record_count":2,"content_fingerprint":content_fp,"parquet_sha256":parquet_sha,"parquet_file":PARQUET,"completion_status":"completed","created_at":activated_at.astimezone(UTC).isoformat()})
            ref = DashboardUniverseActivationDatasetReferenceV1(dataset_path=dataset_target.relative_to(root).as_posix(),record_count=2,content_fingerprint=content_fp,parquet_sha256=parquet_sha)
            payload = {"policy_version":"dashboard-universe-v1","analysis_session":session.isoformat(),"membership_evidence_as_of":records[0].membership_evidence_as_of.isoformat(),"trailing_window_start":trailing_window_start.isoformat(),"trailing_window_end":trailing_window_end.isoformat(),"trailing_window_session_count":trailing_window_session_count,"reviewed_override_count":reviewed_override_count,"activated_at":activated_at.astimezone(UTC).isoformat(),"default_universe_id":CANDIDATE_A_ID,"available_universe_ids":[CANDIDATE_A_ID,PUBLIC_SECONDARY_ID],"activation_dataset":ref.model_dump(mode="json"),"pre_activation_review_path":f"market-data/snapshots/universe-pre-activation-review/analysis_session={session.isoformat()}","pre_activation_review_fingerprint":records[0].pre_activation_review_fingerprint,"legacy_member_count":legacy_count,"legacy_membership_fingerprint":legacy_fingerprint}
            provisional = DashboardUniverseActivationManifestV1(**payload,logical_content_fingerprint="0"*64)
            normalized=provisional.model_dump(mode="json",exclude={"manifest_version","completion_status","logical_content_fingerprint"})
            logical_fp = _json_fp(normalized)
            manifest = provisional.model_copy(update={"logical_content_fingerprint":logical_fp})
            stages[1].mkdir(parents=True); _write_json(stages[1]/MANIFEST,manifest.model_dump(mode="json"))
            _read_dataset(stages[0],ref)
            for stage,target in zip(stages,(dataset_target,logical_target),strict=True):
                target.parent.mkdir(parents=True,exist_ok=True)
                if os.stat(root).st_dev != os.stat(target.parent).st_dev: raise DashboardUniverseActivationError("staging filesystem differs")
                stage.replace(target); renamed.append(target)
            completed=read_completed_dashboard_universe_activation(root,analysis_session=session,validate_sources=True)
            if completed.manifest.logical_content_fingerprint != logical_fp: raise DashboardUniverseActivationError("production reread mismatch")
            return DashboardUniverseActivationPublicationResult(dataset_target,logical_target/MANIFEST,2,content_fp,parquet_sha,logical_fp)
        except Exception:
            for path in reversed(renamed):
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            for path in stages:
                if path.exists() and not path.is_symlink(): shutil.rmtree(path)
            raise


def read_completed_dashboard_universe_activation(root: Path, *, analysis_session: date, validate_sources: bool=True) -> CompletedDashboardUniverseActivation:
    root=_root(root); dataset,logical=_targets(root,analysis_session)
    for target in (dataset,logical):
        _reject_symlinks(root,target)
        if target.is_symlink() or not target.is_dir(): raise DashboardUniverseActivationError("completed activation target unavailable")
    mp=logical/MANIFEST
    if mp.is_symlink() or not mp.is_file(): raise DashboardUniverseActivationError("activation logical manifest unavailable")
    manifest=DashboardUniverseActivationManifestV1.model_validate_json(mp.read_text())
    payload=manifest.model_dump(mode="json",exclude={"manifest_version","completion_status","logical_content_fingerprint"})
    if _json_fp(payload)!=manifest.logical_content_fingerprint: raise DashboardUniverseActivationError("activation logical fingerprint mismatch")
    records=_read_dataset(dataset,manifest.activation_dataset); _validate_records(records)
    review=read_completed_universe_review(root,analysis_session=analysis_session,validate_source=validate_sources)
    if review.manifest.logical_content_fingerprint!=manifest.pre_activation_review_fingerprint or review.manifest.legacy_count!=manifest.legacy_member_count or review.manifest.legacy_membership_fingerprint!=manifest.legacy_membership_fingerprint or review.manifest.override_dataset.record_count!=manifest.reviewed_override_count:
        raise DashboardUniverseActivationError("activation source reference mismatch")
    members=_read_review_members(root,review.manifest.review_dataset.dataset_path)
    public_members={CANDIDATE_A_ID:members[CANDIDATE_A_ID],PUBLIC_SECONDARY_ID:members[CANDIDATE_B_ID]}
    for record in records:
        ids=public_members[record.universe_id]
        if len(ids)!=record.member_count or membership_fingerprint(ids)!=record.membership_fingerprint: raise DashboardUniverseActivationError("activation membership reference mismatch")
    return CompletedDashboardUniverseActivation(manifest,records,public_members)


def _read_review_members(root:Path,relative:str)->dict[str,frozenset[UUID]]:
    records=_read_review_records(root,relative)
    output={CANDIDATE_A_ID:set(),CANDIDATE_B_ID:set()}
    for item in records:
        if item.final_included: output[item.universe_id].add(item.instrument_id)
    return {key:frozenset(value) for key,value in output.items()}

def _read_review_records(root:Path,relative:str)->tuple[UniverseReviewDecisionV1,...]:
    path=root/relative/PARQUET; _reject_symlinks(root,path)
    table=pq.ParquetFile(path).read()
    if table.schema!=REVIEW_SCHEMA: raise DashboardUniverseActivationError("review schema mismatch")
    return tuple(UniverseReviewDecisionV1.model_validate(row) for row in table.to_pylist())


def _validate_records(records:tuple[DashboardUniverseActivationRecordV1,...])->None:
    if len(records)!=2 or {x.universe_id for x in records}!={CANDIDATE_A_ID,PUBLIC_SECONDARY_ID}: raise DashboardUniverseActivationError("exact activation catalog required")
    if sum(x.is_default for x in records)!=1 or not next(x for x in records if x.is_default).universe_id==CANDIDATE_A_ID: raise DashboardUniverseActivationError("Common Shares must be sole default")
    if len({x.activation_id for x in records})!=2 or len({x.analysis_session for x in records})!=1: raise DashboardUniverseActivationError("activation records conflict")


def _row(item:DashboardUniverseActivationRecordV1)->dict[str,Any]:
    row=item.model_dump(mode="python"); row["activation_id"]=str(item.activation_id); row["security_type_composition"]=[x.model_dump(mode="python") for x in item.security_type_composition]; return row
def _read_dataset(path:Path,ref:DashboardUniverseActivationDatasetReferenceV1)->tuple[DashboardUniverseActivationRecordV1,...]:
    manifest,path_parquet=path/MANIFEST,path/PARQUET
    if any(x.is_symlink() for x in (path,manifest,path_parquet)) or not manifest.is_file() or not path_parquet.is_file(): raise DashboardUniverseActivationError("activation dataset incomplete")
    meta=json.loads(manifest.read_text()); expected={"dataset_name":DATASET_NAME,"record_count":2,"content_fingerprint":ref.content_fingerprint,"parquet_sha256":ref.parquet_sha256,"completion_status":"completed"}
    if any(meta.get(k)!=v for k,v in expected.items()): raise DashboardUniverseActivationError("activation dataset manifest mismatch")
    table=pq.ParquetFile(path_parquet).read()
    if table.schema!=SCHEMA or table.num_rows!=2 or _rows_fp(table.to_pylist())!=ref.content_fingerprint or _file_sha(path_parquet)!=ref.parquet_sha256: raise DashboardUniverseActivationError("activation dataset content mismatch")
    return tuple(DashboardUniverseActivationRecordV1.model_validate(row) for row in table.to_pylist())
def _targets(root:Path,session:date):
    suffix=f"schema_version=1/analysis_session={session.isoformat()}"; return root/f"market-data/derived/dashboard-universe-activation/{suffix}",root/f"market-data/snapshots/dashboard-universe-activation/analysis_session={session.isoformat()}"
def _root(root:Path)->Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir(): raise DashboardUniverseActivationError("data root must be absolute regular directory")
    return root.resolve(strict=True)
def _reject_symlinks(root:Path,path:Path)->None:
    try:path.relative_to(root)
    except ValueError as exc:raise DashboardUniverseActivationError("path escapes root") from exc
    current=root
    for part in path.relative_to(root).parts:
        current/=part
        if current.is_symlink():raise DashboardUniverseActivationError("symlink path rejected")
def _canonical(value:Any)->Any:
    if isinstance(value,datetime):return value.astimezone(UTC).isoformat()
    if isinstance(value,date):return value.isoformat()
    return value
def _rows_fp(rows:list[dict[str,Any]])->str:return _json_fp([{k:_canonical(v) for k,v in row.items() if k!="activated_at"} for row in rows])
def _json_fp(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def _file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def _write_json(path:Path,value:Any)->None:
    with path.open("x",encoding="utf-8") as handle:json.dump(value,handle,sort_keys=True,separators=(",",":"));handle.write("\n");handle.flush();os.fsync(handle.fileno())
