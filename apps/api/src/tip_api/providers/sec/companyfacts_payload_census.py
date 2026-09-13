"""Parallel, network-free payload census for a sealed SEC Company Facts ZIP."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import stat
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_source import (
    ARCHIVE_FILE,
    SecCompanyfactsSourceManifestV1,
    read_sec_companyfacts_source_package,
)


CONTRACT_VERSION = "sec-companyfacts-payload-census/1.1"
MAXIMUM_WORKERS = 16
MEMBERS_PER_BATCH = 128
MAXIMUM_OUTPUT_BYTES = 16 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")
_CIK_MEMBER = re.compile(r"CIK(?P<cik>[0-9]{10})\.json\Z")
_ROOT_FIELDS = frozenset({"cik", "entityName", "facts"})
_CONCEPT_FIELDS = frozenset({"label", "description", "units"})
_FACT_FIELDS = frozenset(
    {"start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"}
)


class SecCompanyfactsPayloadCensusError(RuntimeError):
    """Raised when a complete payload census cannot be established."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NamespaceCensusV1(_FrozenModel):
    namespace: str
    entity_count: int = Field(ge=1)
    concept_count: int = Field(ge=1)
    fact_count: int = Field(ge=1)


class QuarantinedMemberV1(_FrozenModel):
    member_name: str
    reason_code: str


class SecCompanyfactsPayloadCensusV1(_FrozenModel):
    contract_version: Literal["sec-companyfacts-payload-census/1.1"] = (
        CONTRACT_VERSION
    )
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    source_family: Literal["companyfacts_bulk_archive"] = (
        "companyfacts_bulk_archive"
    )
    source_snapshot_date: date
    range_start: date
    range_end: date
    evaluated_at: datetime
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_member_name_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_member_count: int = Field(ge=1)
    payload_read_member_count: int = Field(ge=1)
    populated_member_count: int = Field(ge=0)
    empty_object_member_count: int = Field(ge=0)
    empty_facts_member_count: int = Field(ge=0)
    quarantined_member_count: int = Field(ge=0)
    quarantined_members: tuple[QuarantinedMemberV1, ...]
    payload_validation_status: Literal[
        "complete", "complete_with_quarantined_members"
    ]
    fact_count: int = Field(ge=0)
    fact_filed_before_range_count: int = Field(ge=0)
    fact_filed_in_range_count: int = Field(ge=0)
    fact_filed_after_range_count: int = Field(ge=0)
    fact_filed_invalid_or_missing_count: int = Field(ge=0)
    earliest_valid_filed_date: date | None = None
    latest_valid_filed_date: date | None = None
    unique_accession_count: int = Field(ge=0)
    in_range_unique_accession_count: int = Field(ge=0)
    invalid_or_missing_accession_count: int = Field(ge=0)
    duration_fact_count: int = Field(ge=0)
    instant_fact_count: int = Field(ge=0)
    amended_form_fact_count: int = Field(ge=0)
    frame_present_fact_count: int = Field(ge=0)
    fact_value_type_counts: tuple[tuple[str, int], ...]
    fact_field_presence_counts: tuple[tuple[str, int], ...]
    form_counts: tuple[tuple[str, int], ...]
    in_range_form_counts: tuple[tuple[str, int], ...]
    unit_counts: tuple[tuple[str, int], ...]
    namespace_counts: tuple[NamespaceCensusV1, ...]
    unexpected_root_field_counts: tuple[tuple[str, int], ...]
    unexpected_concept_field_counts: tuple[tuple[str, int], ...]
    unexpected_fact_field_counts: tuple[tuple[str, int], ...]
    malformed_fact_count: int = Field(ge=0)
    worker_count: int = Field(ge=1, le=MAXIMUM_WORKERS)
    member_batch_count: int = Field(ge=1)
    full_member_crc_and_json_read: Literal[True] = True
    acceptance_timestamp_count: Literal[0] = 0
    filed_date_same_day_eligibility: Literal[False] = False
    source_availability_status: Literal[
        "date_only_pending_accession_acceptance_join"
    ] = "date_only_pending_accession_acceptance_join"
    normalized_fact_write_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(self) -> "SecCompanyfactsPayloadCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("SEC Company Facts census range is reversed")
        if self.payload_read_member_count != self.source_member_count:
            raise ValueError("SEC Company Facts member read count differs")
        if (
            self.populated_member_count
            + self.empty_object_member_count
            + self.empty_facts_member_count
            + self.quarantined_member_count
            != self.source_member_count
        ):
            raise ValueError("SEC Company Facts member population differs")
        if self.quarantined_member_count != len(self.quarantined_members):
            raise ValueError("SEC Company Facts quarantine count differs")
        expected_status = (
            "complete_with_quarantined_members"
            if self.quarantined_members
            else "complete"
        )
        if self.payload_validation_status != expected_status:
            raise ValueError("SEC Company Facts payload status differs")
        if (
            self.fact_filed_before_range_count
            + self.fact_filed_in_range_count
            + self.fact_filed_after_range_count
            + self.fact_filed_invalid_or_missing_count
            != self.fact_count
        ):
            raise ValueError("SEC Company Facts filed-date counts differ")
        if self.duration_fact_count + self.instant_fact_count != self.fact_count:
            raise ValueError("SEC Company Facts duration counts differ")
        if sum(count for _, count in self.fact_value_type_counts) != self.fact_count:
            raise ValueError("SEC Company Facts value-type counts differ")
        if sum(count for _, count in self.unit_counts) != self.fact_count:
            raise ValueError("SEC Company Facts unit counts differ")
        if sum(item.fact_count for item in self.namespace_counts) != self.fact_count:
            raise ValueError("SEC Company Facts namespace fact counts differ")
        for values in (
            self.fact_value_type_counts,
            self.fact_field_presence_counts,
            self.form_counts,
            self.in_range_form_counts,
            self.unit_counts,
            self.unexpected_root_field_counts,
            self.unexpected_concept_field_counts,
            self.unexpected_fact_field_counts,
        ):
            if values != tuple(sorted(values)) or any(count < 1 for _, count in values):
                raise ValueError("SEC Company Facts ordered counts differ")
        if tuple(item.namespace for item in self.namespace_counts) != tuple(
            sorted(item.namespace for item in self.namespace_counts)
        ):
            raise ValueError("SEC Company Facts namespace order differs")
        if tuple((item.member_name, item.reason_code) for item in self.quarantined_members) != tuple(
            sorted((item.member_name, item.reason_code) for item in self.quarantined_members)
        ):
            raise ValueError("SEC Company Facts quarantine order differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC Company Facts census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class _Partial:
    member_count: int
    populated_count: int
    empty_count: int
    empty_facts_count: int
    quarantined: tuple[tuple[str, str], ...]
    fact_count: int
    filed_counts: Counter[str]
    earliest_valid_filed_date: date | None
    latest_valid_filed_date: date | None
    accessions: frozenset[str]
    in_range_accessions: frozenset[str]
    invalid_accession_count: int
    duration_count: int
    instant_count: int
    amended_count: int
    frame_count: int
    value_types: Counter[str]
    field_presence: Counter[str]
    forms: Counter[str]
    in_range_forms: Counter[str]
    units: Counter[str]
    namespace_entities: Counter[str]
    namespace_concepts: Counter[str]
    namespace_facts: Counter[str]
    unexpected_root: Counter[str]
    unexpected_concept: Counter[str]
    unexpected_fact: Counter[str]
    malformed_fact_count: int


def census_sec_companyfacts_payloads(
    *,
    source_package_path: Path,
    source_custody_root: Path,
    range_start: date,
    range_end: date,
    worker_count: int,
    evaluated_at: datetime | None = None,
) -> SecCompanyfactsPayloadCensusV1:
    """Read every member and produce a deterministic structural census."""

    if range_end < range_start:
        raise SecCompanyfactsPayloadCensusError("payload census range is reversed")
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecCompanyfactsPayloadCensusError("payload census worker count is invalid")
    manifest = read_sec_companyfacts_source_package(
        package_path=source_package_path,
        approved_custody_root=source_custody_root,
    )
    archive_path = source_package_path / ARCHIVE_FILE
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = tuple(sorted(item.filename for item in archive.infolist()))
    except (OSError, zipfile.BadZipFile) as exc:
        raise SecCompanyfactsPayloadCensusError("Company Facts ZIP is unavailable") from exc
    if len(names) != manifest.member_count or _fingerprint(names) != manifest.member_name_fingerprint:
        raise SecCompanyfactsPayloadCensusError("Company Facts member binding differs")
    batches = tuple(
        names[index : index + MEMBERS_PER_BATCH]
        for index in range(0, len(names), MEMBERS_PER_BATCH)
    )
    arguments = tuple(
        (str(archive_path), batch, range_start, range_end) for batch in batches
    )
    if worker_count == 1:
        partials = tuple(_census_batch(argument) for argument in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            partials = tuple(executor.map(_census_batch, arguments))
    return _combine(
        partials=partials,
        manifest=manifest,
        source_manifest_sha256=_sha256_file(source_package_path / "package.json"),
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
        batch_count=len(batches),
        evaluated_at=normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
    )


def seal_sec_companyfacts_payload_census(
    *, output_root: Path, census: SecCompanyfactsPayloadCensusV1
) -> Path:
    root = _validate_output_root(output_root)
    target = root / _file_name(census.source_snapshot_date, census.range_start, census.range_end)
    raw = _json_bytes(census.model_dump(mode="json")) + b"\n"
    if len(raw) > MAXIMUM_OUTPUT_BYTES:
        raise SecCompanyfactsPayloadCensusError("payload census exceeds byte ceiling")
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o400)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    target.chmod(0o400)
    _fsync_directory(root)
    return target


def read_sealed_sec_companyfacts_payload_census(
    *, output_root: Path, source_snapshot_date: date, range_start: date, range_end: date
) -> SecCompanyfactsPayloadCensusV1:
    root = _validate_output_root(output_root)
    target = root / _file_name(source_snapshot_date, range_start, range_end)
    if target.is_symlink() or not target.is_file():
        raise SecCompanyfactsPayloadCensusError("sealed payload census is unavailable")
    metadata = target.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise SecCompanyfactsPayloadCensusError("sealed payload census mode differs")
    if metadata.st_size < 1 or metadata.st_size > MAXIMUM_OUTPUT_BYTES:
        raise SecCompanyfactsPayloadCensusError("sealed payload census size differs")
    try:
        result = SecCompanyfactsPayloadCensusV1.model_validate_json(target.read_bytes())
    except Exception as exc:
        raise SecCompanyfactsPayloadCensusError("sealed payload census is invalid") from exc
    if (
        result.source_snapshot_date != source_snapshot_date
        or result.range_start != range_start
        or result.range_end != range_end
    ):
        raise SecCompanyfactsPayloadCensusError("sealed payload census scope differs")
    return result


def extract_sec_companyfacts_in_range_accessions(
    *,
    source_package_path: Path,
    source_custody_root: Path,
    range_start: date,
    range_end: date,
    worker_count: int,
) -> dict[str, tuple[date, ...]]:
    """Return admitted accession-to-filed-date evidence for an exact range."""

    if range_end < range_start:
        raise SecCompanyfactsPayloadCensusError("accession range is reversed")
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecCompanyfactsPayloadCensusError("accession worker count is invalid")
    manifest = read_sec_companyfacts_source_package(
        package_path=source_package_path,
        approved_custody_root=source_custody_root,
    )
    archive_path = source_package_path / ARCHIVE_FILE
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
    if len(names) != manifest.member_count:
        raise SecCompanyfactsPayloadCensusError("accession member binding differs")
    partitions = tuple(
        names[index::worker_count] for index in range(worker_count) if names[index::worker_count]
    )
    arguments = tuple(
        (str(archive_path), partition, range_start, range_end)
        for partition in partitions
    )
    if worker_count == 1:
        partials = tuple(_extract_accession_batch(argument) for argument in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            partials = tuple(executor.map(_extract_accession_batch, arguments))
    merged: dict[str, set[date]] = {}
    for partial in partials:
        for accession, filed_dates in partial.items():
            merged.setdefault(accession, set()).update(filed_dates)
    return {
        accession: tuple(sorted(filed_dates))
        for accession, filed_dates in sorted(merged.items())
    }


def _extract_accession_batch(
    argument: tuple[str, tuple[str, ...], date, date]
) -> dict[str, tuple[date, ...]]:
    archive_name, names, range_start, range_end = argument
    result: dict[str, set[date]] = {}
    with zipfile.ZipFile(archive_name) as archive:
        for name in names:
            try:
                with archive.open(name) as handle:
                    payload = json.load(handle)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise SecCompanyfactsPayloadCensusError(
                    "Company Facts accession member read failed"
                ) from exc
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if payload == {} or _identity_and_facts_reason(name, payload) is not None:
                continue
            assert isinstance(payload, dict)
            if payload["facts"] == {} or _entity_name_reason(payload) is not None:
                continue
            if _structure_reason(payload) is not None:
                continue
            facts = payload["facts"]
            for concepts in facts.values():
                for concept in concepts.values():
                    for values in concept["units"].values():
                        for fact in values:
                            if not isinstance(fact, dict):
                                continue
                            filed = _date_value(fact.get("filed"))
                            accession = _text(fact.get("accn"))
                            if (
                                filed is not None
                                and range_start <= filed <= range_end
                                and accession is not None
                                and _ACCESSION.fullmatch(accession)
                            ):
                                result.setdefault(accession, set()).add(filed)
    return {
        accession: tuple(sorted(filed_dates))
        for accession, filed_dates in result.items()
    }


def _census_batch(argument: tuple[str, tuple[str, ...], date, date]) -> _Partial:
    archive_name, names, range_start, range_end = argument
    counters: dict[str, Counter] = {
        key: Counter()
        for key in (
            "filed",
            "value_types",
            "field_presence",
            "forms",
            "in_range_forms",
            "units",
            "namespace_entities",
            "namespace_concepts",
            "namespace_facts",
            "unexpected_root",
            "unexpected_concept",
            "unexpected_fact",
        )
    }
    populated = empty = empty_facts = fact_count = invalid_accessions = 0
    duration = instant = amended = frames = malformed_facts = 0
    quarantined: list[tuple[str, str]] = []
    earliest_filed: date | None = None
    latest_filed: date | None = None
    accessions: set[str] = set()
    range_accessions: set[str] = set()
    try:
        archive = zipfile.ZipFile(archive_name)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SecCompanyfactsPayloadCensusError("worker could not open ZIP") from exc
    with archive:
        for name in names:
            try:
                with archive.open(name) as handle:
                    raw = handle.read()
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise SecCompanyfactsPayloadCensusError(
                    "Company Facts member CRC/read failed"
                ) from exc
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                quarantined.append((name, "invalid_json"))
                continue
            if payload == {}:
                empty += 1
                continue
            reason = _identity_and_facts_reason(name, payload)
            if reason is not None:
                quarantined.append((name, reason))
                continue
            assert isinstance(payload, dict)
            if payload["facts"] == {}:
                empty_facts += 1
                continue
            reason = _entity_name_reason(payload)
            if reason is not None:
                quarantined.append((name, reason))
                continue
            reason = _structure_reason(payload)
            if reason is not None:
                quarantined.append((name, reason))
                continue
            populated += 1
            counters["unexpected_root"].update(set(payload) - _ROOT_FIELDS)
            facts = payload["facts"]
            for namespace, concepts in facts.items():
                counters["namespace_entities"][namespace] += 1
                counters["namespace_concepts"][namespace] += len(concepts)
                for concept in concepts.values():
                    counters["unexpected_concept"].update(set(concept) - _CONCEPT_FIELDS)
                    for unit, values in concept["units"].items():
                        for fact in values:
                            if not isinstance(fact, dict):
                                malformed_facts += 1
                                continue
                            fact_count += 1
                            counters["units"][unit] += 1
                            counters["namespace_facts"][namespace] += 1
                            counters["unexpected_fact"].update(set(fact) - _FACT_FIELDS)
                            for field in _FACT_FIELDS:
                                if field in fact and fact[field] is not None:
                                    counters["field_presence"][field] += 1
                            counters["value_types"][_value_type(fact.get("val"))] += 1
                            if "start" in fact and fact.get("start") is not None:
                                duration += 1
                            else:
                                instant += 1
                            if fact.get("frame") not in (None, ""):
                                frames += 1
                            form = _text(fact.get("form"))
                            if form is not None:
                                counters["forms"][form] += 1
                                if form.endswith("/A"):
                                    amended += 1
                            accession = _text(fact.get("accn"))
                            if accession is None or _ACCESSION.fullmatch(accession) is None:
                                invalid_accessions += 1
                            else:
                                accessions.add(accession)
                            filed = _date_value(fact.get("filed"))
                            if filed is None:
                                counters["filed"]["invalid"] += 1
                            else:
                                earliest_filed = min(earliest_filed, filed) if earliest_filed else filed
                                latest_filed = max(latest_filed, filed) if latest_filed else filed
                                if filed < range_start:
                                    counters["filed"]["before"] += 1
                                elif filed > range_end:
                                    counters["filed"]["after"] += 1
                                else:
                                    counters["filed"]["in_range"] += 1
                                    if form is not None:
                                        counters["in_range_forms"][form] += 1
                                    if accession is not None and _ACCESSION.fullmatch(accession):
                                        range_accessions.add(accession)
    return _Partial(
        member_count=len(names),
        populated_count=populated,
        empty_count=empty,
        empty_facts_count=empty_facts,
        quarantined=tuple(quarantined),
        fact_count=fact_count,
        filed_counts=counters["filed"],
        earliest_valid_filed_date=earliest_filed,
        latest_valid_filed_date=latest_filed,
        accessions=frozenset(accessions),
        in_range_accessions=frozenset(range_accessions),
        invalid_accession_count=invalid_accessions,
        duration_count=duration,
        instant_count=instant,
        amended_count=amended,
        frame_count=frames,
        value_types=counters["value_types"],
        field_presence=counters["field_presence"],
        forms=counters["forms"],
        in_range_forms=counters["in_range_forms"],
        units=counters["units"],
        namespace_entities=counters["namespace_entities"],
        namespace_concepts=counters["namespace_concepts"],
        namespace_facts=counters["namespace_facts"],
        unexpected_root=counters["unexpected_root"],
        unexpected_concept=counters["unexpected_concept"],
        unexpected_fact=counters["unexpected_fact"],
        malformed_fact_count=malformed_facts,
    )


def _combine(
    *,
    partials: tuple[_Partial, ...],
    manifest: SecCompanyfactsSourceManifestV1,
    source_manifest_sha256: str,
    range_start: date,
    range_end: date,
    worker_count: int,
    batch_count: int,
    evaluated_at: datetime,
) -> SecCompanyfactsPayloadCensusV1:
    counters = {
        name: sum((getattr(partial, name) for partial in partials), Counter())
        for name in (
            "filed_counts",
            "value_types",
            "field_presence",
            "forms",
            "in_range_forms",
            "units",
            "namespace_entities",
            "namespace_concepts",
            "namespace_facts",
            "unexpected_root",
            "unexpected_concept",
            "unexpected_fact",
        )
    }
    earliest_dates = tuple(
        item.earliest_valid_filed_date
        for item in partials
        if item.earliest_valid_filed_date is not None
    )
    latest_dates = tuple(
        item.latest_valid_filed_date
        for item in partials
        if item.latest_valid_filed_date is not None
    )
    accessions = set().union(*(partial.accessions for partial in partials))
    in_range_accessions = set().union(
        *(partial.in_range_accessions for partial in partials)
    )
    quarantined = tuple(
        QuarantinedMemberV1(member_name=name, reason_code=reason)
        for name, reason in sorted(
            item for partial in partials for item in partial.quarantined
        )
    )
    namespaces = tuple(
        NamespaceCensusV1(
            namespace=namespace,
            entity_count=counters["namespace_entities"][namespace],
            concept_count=counters["namespace_concepts"][namespace],
            fact_count=counters["namespace_facts"][namespace],
        )
        for namespace in sorted(counters["namespace_facts"])
        if counters["namespace_facts"][namespace] > 0
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "provider_id": "sec_edgar",
        "source_family": "companyfacts_bulk_archive",
        "source_snapshot_date": manifest.remote.last_modified.date(),
        "range_start": range_start,
        "range_end": range_end,
        "evaluated_at": evaluated_at,
        "source_manifest_sha256": source_manifest_sha256,
        "source_logical_fingerprint": manifest.logical_fingerprint,
        "source_archive_sha256": manifest.archive_sha256,
        "source_member_name_fingerprint": manifest.member_name_fingerprint,
        "source_member_count": manifest.member_count,
        "payload_read_member_count": sum(item.member_count for item in partials),
        "populated_member_count": sum(item.populated_count for item in partials),
        "empty_object_member_count": sum(item.empty_count for item in partials),
        "empty_facts_member_count": sum(
            item.empty_facts_count for item in partials
        ),
        "quarantined_member_count": len(quarantined),
        "quarantined_members": quarantined,
        "payload_validation_status": (
            "complete_with_quarantined_members" if quarantined else "complete"
        ),
        "fact_count": sum(item.fact_count for item in partials),
        "fact_filed_before_range_count": counters["filed_counts"]["before"],
        "fact_filed_in_range_count": counters["filed_counts"]["in_range"],
        "fact_filed_after_range_count": counters["filed_counts"]["after"],
        "fact_filed_invalid_or_missing_count": counters["filed_counts"]["invalid"],
        "earliest_valid_filed_date": min(earliest_dates) if earliest_dates else None,
        "latest_valid_filed_date": max(latest_dates) if latest_dates else None,
        "unique_accession_count": len(accessions),
        "in_range_unique_accession_count": len(in_range_accessions),
        "invalid_or_missing_accession_count": sum(
            item.invalid_accession_count for item in partials
        ),
        "duration_fact_count": sum(item.duration_count for item in partials),
        "instant_fact_count": sum(item.instant_count for item in partials),
        "amended_form_fact_count": sum(item.amended_count for item in partials),
        "frame_present_fact_count": sum(item.frame_count for item in partials),
        "fact_value_type_counts": _ordered(counters["value_types"]),
        "fact_field_presence_counts": _ordered(counters["field_presence"]),
        "form_counts": _ordered(counters["forms"]),
        "in_range_form_counts": _ordered(counters["in_range_forms"]),
        "unit_counts": _ordered(counters["units"]),
        "namespace_counts": namespaces,
        "unexpected_root_field_counts": _ordered(counters["unexpected_root"]),
        "unexpected_concept_field_counts": _ordered(counters["unexpected_concept"]),
        "unexpected_fact_field_counts": _ordered(counters["unexpected_fact"]),
        "malformed_fact_count": sum(item.malformed_fact_count for item in partials),
        "worker_count": worker_count,
        "member_batch_count": batch_count,
        "full_member_crc_and_json_read": True,
        "acceptance_timestamp_count": 0,
        "filed_date_same_day_eligibility": False,
        "source_availability_status": "date_only_pending_accession_acceptance_join",
        "normalized_fact_write_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecCompanyfactsPayloadCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _identity_and_facts_reason(name: str, payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "root_not_object"
    match = _CIK_MEMBER.fullmatch(name)
    cik = payload.get("cik")
    if match is None or str(cik).zfill(10) != match.group("cik"):
        return "cik_filename_mismatch"
    if not isinstance(payload.get("facts"), dict):
        return "facts_root_invalid"
    return None


def _entity_name_reason(payload: dict[str, object]) -> str | None:
    name = payload.get("entityName")
    if not isinstance(name, str) or not name.strip():
        return "entity_name_invalid"
    return None


def _structure_reason(payload: dict[str, object]) -> str | None:
    """Validate containers before contributing any member-level counters."""

    facts = payload["facts"]
    assert isinstance(facts, dict)
    for namespace, concepts in facts.items():
        if not isinstance(namespace, str) or not namespace or not isinstance(concepts, dict):
            return "malformed_namespace"
        for concept_name, concept in concepts.items():
            if not isinstance(concept_name, str) or not concept_name:
                return "malformed_concept_name"
            if not isinstance(concept, dict) or not isinstance(concept.get("units"), dict):
                return "malformed_concept"
            for unit, values in concept["units"].items():
                if not isinstance(unit, str) or not unit or not isinstance(values, list):
                    return "malformed_unit"
    return None


def _value_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "other"


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _date_value(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _file_name(snapshot: date, start: date, end: date) -> str:
    return f"census=snapshot-{snapshot.isoformat()}--range-{start.isoformat()}--{end.isoformat()}.json"


def _validate_output_root(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecCompanyfactsPayloadCensusError("payload census root is unsafe")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SecCompanyfactsPayloadCensusError("payload census root mode differs")
    return root


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
