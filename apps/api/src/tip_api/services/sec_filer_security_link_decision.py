"""Build immutable daily SEC filer-to-stable-security link decisions."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import shutil
import stat
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    ProviderInstrumentIdentityV1,
    ResolutionStatus,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    PARQUET_FILE_NAME,
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.services.historical_identity_source_custody import (
    HistoricalIdentitySourceCustodyError,
    read_identity_source_custody_at_data_root,
)
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "sec-filer-security-link-decision/1.0"
MANIFEST_FILE = "manifest.json"
PARQUET_FILE = "part-00000.parquet"
MAXIMUM_WORKERS = 8
MAXIMUM_MANIFEST_BYTES = 8 * 1024 * 1024
_SHA256 = r"^[0-9a-f]{64}$"
_REVISION = r"^[0-9a-f]{40}$"
_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
_CIK = re.compile(r"[0-9]{10}\Z")

DecisionStatus = Literal[
    "admitted_unique_cik",
    "quarantined_missing_cik",
    "quarantined_conflicting_cik",
    "quarantined_identity_mismatch",
    "quarantined_source_custody_missing",
]
KnowledgeClass = Literal[
    "outcome_reconciliation_only",
    "eligible_at_source_observed_at",
    "source_custody_missing",
]


LINK_ARROW_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("ticker", pa.string(), nullable=False),
        pa.field("instrument_type", pa.string(), nullable=False),
        pa.field("sec_cik", pa.string(), nullable=True),
        pa.field("sec_filer_key", pa.string(), nullable=True),
        pa.field("decision_status", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("source_identity_occurrence_count", pa.int32(), nullable=False),
        pa.field("cik_instrument_count", pa.int32(), nullable=True),
        pa.field("point_in_time_eligibility", pa.string(), nullable=False),
        pa.field(
            "source_observed_at",
            pa.timestamp("us", tz="UTC"),
            nullable=True,
        ),
        pa.field("source_row_set_fingerprint", pa.string(), nullable=False),
        pa.field("issuer_projection_authorized", pa.bool_(), nullable=False),
    ]
)


class SecFilerSecurityLinkError(RuntimeError):
    """Raised when a filer-security link package cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecFilerSecurityLinkDecisionV1(_FrozenModel):
    contract_version: Literal[
        "sec-filer-security-link-decision/1.0"
    ] = CONTRACT_VERSION
    as_of_date: date
    instrument_id: str = Field(pattern=_UUID)
    ticker: str = Field(min_length=1)
    instrument_type: Literal["common_stock", "etf"]
    sec_cik: str | None = Field(default=None, pattern=r"^[0-9]{10}$")
    sec_filer_key: str | None = Field(default=None, pattern=r"^sec-cik:[0-9]{10}$")
    decision_status: DecisionStatus
    reason_codes: tuple[str, ...]
    source_identity_occurrence_count: int = Field(ge=0)
    cik_instrument_count: int | None = Field(default=None, ge=1)
    point_in_time_eligibility: KnowledgeClass
    source_observed_at: datetime | None = None
    source_row_set_fingerprint: str = Field(pattern=_SHA256)
    issuer_projection_authorized: Literal[False] = False

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecFilerSecurityLinkDecisionV1":
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("link-decision reasons are not unique and ordered")
        admitted = self.decision_status == "admitted_unique_cik"
        if admitted != (self.sec_cik is not None):
            raise ValueError("link-decision CIK admission differs")
        if (self.sec_cik is None) != (self.sec_filer_key is None):
            raise ValueError("link-decision filer key is incomplete")
        if self.sec_cik is not None and self.sec_filer_key != f"sec-cik:{self.sec_cik}":
            raise ValueError("link-decision filer key differs")
        if admitted != (self.cik_instrument_count is not None):
            raise ValueError("link-decision CIK cardinality differs")
        if admitted and self.reason_codes:
            raise ValueError("admitted link-decision carries quarantine reasons")
        if not admitted and not self.reason_codes:
            raise ValueError("quarantined link-decision lacks reasons")
        source_missing = self.point_in_time_eligibility == "source_custody_missing"
        if source_missing != (self.source_observed_at is None):
            raise ValueError("link-decision source clock differs")
        if source_missing != (
            self.decision_status == "quarantined_source_custody_missing"
        ):
            raise ValueError("link-decision missing-source status differs")
        return self


class SecFilerSecurityLinkSessionV1(_FrozenModel):
    as_of_date: date
    relative_path: str
    row_count: int = Field(ge=1)
    byte_size: int = Field(ge=1)
    physical_sha256: str = Field(pattern=_SHA256)
    logical_fingerprint: str = Field(pattern=_SHA256)
    instrument_manifest_sha256: str = Field(pattern=_SHA256)
    instrument_parquet_sha256: str = Field(pattern=_SHA256)
    identity_manifest_sha256: str = Field(pattern=_SHA256)
    identity_parquet_sha256: str = Field(pattern=_SHA256)
    instrument_content_fingerprint: str = Field(pattern=_SHA256)
    identity_content_fingerprint: str = Field(pattern=_SHA256)
    identity_source_custody_status: Literal["present", "missing_allowed"]
    identity_source_manifest_sha256: str | None = Field(
        default=None, pattern=_SHA256
    )
    identity_source_manifest_fingerprint: str | None = Field(
        default=None, pattern=_SHA256
    )
    identity_source_content_fingerprint: str | None = Field(
        default=None, pattern=_SHA256
    )
    point_in_time_eligibility: KnowledgeClass
    source_observed_at: datetime | None = None
    identity_resolution_counts: tuple[tuple[str, int], ...]
    decision_status_counts: tuple[tuple[str, int], ...]
    multi_security_cik_count: int = Field(ge=0)

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def session_reconciles(self) -> "SecFilerSecurityLinkSessionV1":
        if self.relative_path != f"as_of_date={self.as_of_date.isoformat()}/{PARQUET_FILE}":
            raise ValueError("link-decision session path differs")
        for counts in (self.identity_resolution_counts, self.decision_status_counts):
            if counts != tuple(sorted(counts)) or any(value < 1 for _, value in counts):
                raise ValueError("link-decision session counts differ")
        if sum(value for _, value in self.decision_status_counts) != self.row_count:
            raise ValueError("link-decision status denominator differs")
        present = self.identity_source_custody_status == "present"
        source_values = (
            self.identity_source_manifest_sha256,
            self.identity_source_manifest_fingerprint,
            self.identity_source_content_fingerprint,
            self.source_observed_at,
        )
        if present != all(value is not None for value in source_values):
            raise ValueError("link-decision source evidence is incomplete")
        if not present and any(value is not None for value in source_values):
            raise ValueError("missing link-decision source invents evidence")
        if present == (self.point_in_time_eligibility == "source_custody_missing"):
            raise ValueError("link-decision source eligibility differs")
        return self


class SecFilerSecurityLinkManifestV1(_FrozenModel):
    contract_version: Literal[
        "sec-filer-security-link-decision/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    implementation_revision: str = Field(pattern=_REVISION)
    built_at: datetime
    range_start: date
    range_end: date
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str = Field(min_length=1)
    session_index_fingerprint: str = Field(pattern=_SHA256)
    allowed_missing_source_sessions: tuple[date, ...]
    sessions: tuple[SecFilerSecurityLinkSessionV1, ...]
    session_count: int = Field(ge=1)
    row_count: int = Field(ge=1)
    decision_status_counts: tuple[tuple[str, int], ...]
    identity_resolution_counts: tuple[tuple[str, int], ...]
    missing_source_session_count: int = Field(ge=0)
    multi_security_cik_session_count: int = Field(ge=0)
    schema_fingerprint: str = Field(pattern=_SHA256)
    content_fingerprint: str = Field(pattern=_SHA256)
    stable_instrument_resolution_count: int = Field(ge=1)
    issuer_projection_authorized: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    membership_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("built_at")
    @classmethod
    def built_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "SecFilerSecurityLinkManifestV1":
        if self.range_end < self.range_start:
            raise ValueError("link-decision range is reversed")
        dates = tuple(item.as_of_date for item in self.sessions)
        if dates != tuple(sorted(dates)) or len(set(dates)) != len(dates):
            raise ValueError("link-decision sessions are not unique and ordered")
        if not dates or dates[0] != self.range_start or dates[-1] != self.range_end:
            raise ValueError("link-decision session range differs")
        if self.session_count != len(self.sessions):
            raise ValueError("link-decision session count differs")
        if self.row_count != sum(item.row_count for item in self.sessions):
            raise ValueError("link-decision row count differs")
        if self.stable_instrument_resolution_count != self.row_count:
            raise ValueError("link-decision stable-ID count differs")
        if self.allowed_missing_source_sessions != tuple(
            item.as_of_date
            for item in self.sessions
            if item.identity_source_custody_status == "missing_allowed"
        ):
            raise ValueError("link-decision allowed-missing set differs")
        if self.missing_source_session_count != len(
            self.allowed_missing_source_sessions
        ):
            raise ValueError("link-decision missing-source count differs")
        if self.multi_security_cik_session_count != sum(
            item.multi_security_cik_count for item in self.sessions
        ):
            raise ValueError("link-decision multi-security count differs")
        for counts in (self.decision_status_counts, self.identity_resolution_counts):
            if counts != tuple(sorted(counts)) or any(value < 1 for _, value in counts):
                raise ValueError("link-decision aggregate counts differ")
        if sum(value for _, value in self.decision_status_counts) != self.row_count:
            raise ValueError("link-decision aggregate denominator differs")
        if self.session_index_fingerprint != _fingerprint(
            tuple(item.isoformat() for item in dates)
        ):
            raise ValueError("link-decision session fingerprint differs")
        if self.content_fingerprint != _fingerprint(
            tuple((item.relative_path, item.logical_fingerprint) for item in self.sessions)
        ):
            raise ValueError("link-decision content fingerprint differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("link-decision manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecFilerSecurityLinkResult:
    package_path: Path
    manifest: SecFilerSecurityLinkManifestV1


@dataclass(frozen=True, slots=True)
class _SessionBuild:
    evidence: SecFilerSecurityLinkSessionV1
    status_counts: Counter[str]
    resolution_counts: Counter[str]


@dataclass(frozen=True, slots=True)
class _SessionRead:
    as_of_date: date
    status_counts: tuple[tuple[str, int], ...]
    resolution_counts: tuple[tuple[str, int], ...]


def derive_sec_filer_security_link_decisions(
    *,
    as_of_date: date,
    instruments: tuple[InstrumentMasterV1, ...],
    identities: tuple[ProviderInstrumentIdentityV1, ...],
    point_in_time_eligibility: KnowledgeClass,
    source_observed_at: datetime | None,
) -> tuple[SecFilerSecurityLinkDecisionV1, ...]:
    """Create one complete stable-security disposition for one session."""

    if point_in_time_eligibility == "source_custody_missing":
        if source_observed_at is not None:
            raise SecFilerSecurityLinkError("missing source custody invents a clock")
    elif source_observed_at is None:
        raise SecFilerSecurityLinkError("present source custody lacks a clock")
    instrument_by_id = {str(item.instrument_id): item for item in instruments}
    if len(instrument_by_id) != len(instruments):
        raise SecFilerSecurityLinkError("Instrument Master stable ID is duplicated")
    if any(item.as_of_date != as_of_date for item in instruments):
        raise SecFilerSecurityLinkError("Instrument Master session differs")
    resolved: dict[str, list[ProviderInstrumentIdentityV1]] = defaultdict(list)
    for identity in identities:
        if identity.as_of_date != as_of_date:
            raise SecFilerSecurityLinkError("Provider Identity session differs")
        if identity.resolution_status is ResolutionStatus.RESOLVED:
            assert identity.canonical_instrument_id is not None
            resolved[str(identity.canonical_instrument_id)].append(identity)
    unknown_ids = set(resolved).difference(instrument_by_id)
    if unknown_ids:
        raise SecFilerSecurityLinkError(
            "Provider Identity references an unknown stable instrument"
        )

    provisional: list[dict[str, object]] = []
    for instrument_id in sorted(instrument_by_id):
        instrument = instrument_by_id[instrument_id]
        source_rows = tuple(resolved.get(instrument_id, ()))
        reasons: set[str] = set()
        if not source_rows:
            reasons.add("resolved_identity_missing")
        tickers = {item.provider_ticker for item in source_rows}
        if tickers != {instrument.ticker}:
            reasons.add("effective_ticker_mismatch")
        raw_ciks = {item.cik for item in source_rows if item.cik is not None}
        invalid_cik = any(_CIK.fullmatch(value) is None for value in raw_ciks)
        if invalid_cik:
            reasons.add("cik_invalid")
        valid_ciks = {value for value in raw_ciks if _CIK.fullmatch(value)}
        instrument_cik = instrument.cik
        if instrument_cik is not None and _CIK.fullmatch(instrument_cik) is None:
            reasons.add("instrument_master_cik_invalid")
        if len(valid_ciks) == 0:
            reasons.add("cik_missing")
        elif len(valid_ciks) > 1:
            reasons.add("cik_conflict")
        selected_cik = next(iter(valid_ciks)) if len(valid_ciks) == 1 else None
        if (
            selected_cik is not None
            and instrument_cik is not None
            and instrument_cik != selected_cik
        ):
            reasons.add("instrument_master_cik_mismatch")
        if point_in_time_eligibility == "source_custody_missing":
            reasons.add("source_custody_missing")
            status: DecisionStatus = "quarantined_source_custody_missing"
        elif {
            "resolved_identity_missing",
            "effective_ticker_mismatch",
            "cik_invalid",
            "instrument_master_cik_invalid",
            "instrument_master_cik_mismatch",
        }.intersection(reasons):
            status = "quarantined_identity_mismatch"
        elif "cik_conflict" in reasons:
            status = "quarantined_conflicting_cik"
        elif "cik_missing" in reasons:
            status = "quarantined_missing_cik"
        else:
            status = "admitted_unique_cik"
            reasons.clear()
        admitted_cik = selected_cik if status == "admitted_unique_cik" else None
        source_rows_json = tuple(
            item.model_dump(mode="json")
            for item in sorted(
                source_rows,
                key=lambda item: (
                    item.provider_ticker,
                    item.provider_instrument_id or "",
                    item.composite_figi or "",
                    item.share_class_figi or "",
                ),
            )
        )
        provisional.append(
            {
                "contract_version": CONTRACT_VERSION,
                "as_of_date": as_of_date,
                "instrument_id": instrument_id,
                "ticker": instrument.ticker,
                "instrument_type": instrument.instrument_type.value,
                "sec_cik": admitted_cik,
                "sec_filer_key": (
                    f"sec-cik:{admitted_cik}" if admitted_cik is not None else None
                ),
                "decision_status": status,
                "reason_codes": tuple(sorted(reasons)),
                "source_identity_occurrence_count": len(source_rows),
                "cik_instrument_count": None,
                "point_in_time_eligibility": point_in_time_eligibility,
                "source_observed_at": source_observed_at,
                "source_row_set_fingerprint": _fingerprint(source_rows_json),
                "issuer_projection_authorized": False,
            }
        )
    cik_counts = Counter(
        str(item["sec_cik"])
        for item in provisional
        if item["decision_status"] == "admitted_unique_cik"
    )
    return tuple(
        SecFilerSecurityLinkDecisionV1.model_validate(
            {
                **item,
                "cik_instrument_count": (
                    cik_counts[str(item["sec_cik"])]
                    if item["decision_status"] == "admitted_unique_cik"
                    else None
                ),
            }
        )
        for item in provisional
    )


def build_sec_filer_security_link_package(
    *,
    data_root: Path,
    output_package_path: Path,
    range_start: date,
    range_end: date,
    provider: str,
    worker_count: int,
    allowed_missing_source_sessions: tuple[date, ...],
    implementation_revision: str,
    built_at: datetime | None = None,
) -> SecFilerSecurityLinkResult:
    """Build one immutable owner-only candidate package."""

    if provider != "massive_stocks_basic":
        raise SecFilerSecurityLinkError("link-decision provider differs")
    if re.fullmatch(_REVISION, implementation_revision) is None:
        raise SecFilerSecurityLinkError("link-decision revision is invalid")
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecFilerSecurityLinkError("link-decision worker count is invalid")
    if allowed_missing_source_sessions != tuple(
        sorted(set(allowed_missing_source_sessions))
    ):
        raise SecFilerSecurityLinkError("allowed missing sessions are not canonical")
    calendar = ExchangeCalendar()
    sessions = calendar.sessions_in_range(range_start, range_end)
    if sessions[0] != range_start or sessions[-1] != range_end:
        raise SecFilerSecurityLinkError("link-decision range boundaries are not XNYS sessions")
    if not set(allowed_missing_source_sessions).issubset(sessions):
        raise SecFilerSecurityLinkError("allowed missing session is outside range")
    data_root = _validate_data_root(data_root)
    target, partial = _validate_output_target(output_package_path)
    os.mkdir(partial, mode=0o700)
    args = tuple(
        (
            str(data_root),
            str(partial),
            provider,
            session,
            session in allowed_missing_source_sessions,
        )
        for session in sessions
    )
    try:
        if worker_count == 1:
            results = tuple(_build_session(item) for item in args)
        else:
            with ProcessPoolExecutor(
                max_workers=worker_count,
                mp_context=multiprocessing.get_context("spawn"),
            ) as executor:
                results = tuple(executor.map(_build_session, args))
        results = tuple(sorted(results, key=lambda item: item.evidence.as_of_date))
        missing = tuple(
            item.evidence.as_of_date
            for item in results
            if item.evidence.identity_source_custody_status == "missing_allowed"
        )
        if missing != allowed_missing_source_sessions:
            raise SecFilerSecurityLinkError(
                "observed missing source sessions differ from explicit allowance"
            )
        manifest = _build_manifest(
            results=results,
            sessions=sessions,
            allowed_missing_source_sessions=allowed_missing_source_sessions,
            implementation_revision=implementation_revision,
            built_at=normalize_utc_datetime(built_at or datetime.now(UTC)),
            range_start=range_start,
            range_end=range_end,
            provider=provider,
            calendar_version=calendar.calendar_version,
        )
        _write_exclusive_json(partial / MANIFEST_FILE, manifest.model_dump(mode="json"))
        _fsync_directory(partial)
        os.rename(partial, target)
        _fsync_directory(target.parent)
    except Exception:
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    return read_sec_filer_security_link_package(
        package_path=target,
        data_root=data_root,
        formal_read_workers=worker_count,
    )


def read_sec_filer_security_link_package(
    *,
    package_path: Path,
    data_root: Path,
    formal_read_workers: int = 1,
) -> SecFilerSecurityLinkResult:
    """Formally reread all outputs and transitively validate present inputs."""

    if formal_read_workers < 1 or formal_read_workers > MAXIMUM_WORKERS:
        raise SecFilerSecurityLinkError(
            "link-decision formal-read worker count is invalid"
        )
    package = _validate_completed_package(package_path)
    data_root = _validate_data_root(data_root)
    manifest_path = package / MANIFEST_FILE
    _require_regular_mode(manifest_path, 0o400)
    if manifest_path.stat().st_size > MAXIMUM_MANIFEST_BYTES:
        raise SecFilerSecurityLinkError("link-decision manifest exceeds byte ceiling")
    try:
        manifest = SecFilerSecurityLinkManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise SecFilerSecurityLinkError("link-decision manifest is invalid") from exc
    calendar = ExchangeCalendar()
    sessions = calendar.sessions_in_range(manifest.range_start, manifest.range_end)
    if (
        sessions != tuple(item.as_of_date for item in manifest.sessions)
        or calendar.calendar_version != manifest.calendar_version
        or manifest.schema_fingerprint
        != hashlib.sha256(LINK_ARROW_SCHEMA.serialize().to_pybytes()).hexdigest()
    ):
        raise SecFilerSecurityLinkError("link-decision calendar binding differs")
    expected_root = {MANIFEST_FILE, *(f"as_of_date={item.isoformat()}" for item in sessions)}
    if {item.name for item in package.iterdir()} != expected_root:
        raise SecFilerSecurityLinkError("link-decision package members differ")
    arguments = tuple(
        (
            str(package),
            str(data_root),
            manifest.provider,
            evidence,
        )
        for evidence in manifest.sessions
    )
    if formal_read_workers == 1:
        read_results = tuple(_read_session_evidence(item) for item in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=formal_read_workers,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            read_results = tuple(executor.map(_read_session_evidence, arguments))
    read_results = tuple(sorted(read_results, key=lambda item: item.as_of_date))
    if tuple(item.as_of_date for item in read_results) != sessions:
        raise SecFilerSecurityLinkError("link-decision read session order differs")
    status_counts: Counter[str] = sum(
        (Counter(dict(item.status_counts)) for item in read_results),
        Counter(),
    )
    resolution_counts: Counter[str] = sum(
        (Counter(dict(item.resolution_counts)) for item in read_results),
        Counter(),
    )
    if (
        _ordered(status_counts) != manifest.decision_status_counts
        or _ordered(resolution_counts) != manifest.identity_resolution_counts
    ):
        raise SecFilerSecurityLinkError("link-decision aggregate reread differs")
    return SecFilerSecurityLinkResult(package_path=package, manifest=manifest)


def _read_session_evidence(
    argument: tuple[
        str,
        str,
        str,
        SecFilerSecurityLinkSessionV1,
    ],
) -> _SessionRead:
    package_raw, data_root_raw, provider, evidence = argument
    package = Path(package_raw)
    data_root = Path(data_root_raw)
    _validate_input_evidence(data_root, provider, evidence)
    session_dir = package / f"as_of_date={evidence.as_of_date.isoformat()}"
    if session_dir.is_symlink() or not session_dir.is_dir():
        raise SecFilerSecurityLinkError(
            "link-decision session directory is unavailable"
        )
    _require_mode(session_dir, 0o700)
    if {item.name for item in session_dir.iterdir()} != {PARQUET_FILE}:
        raise SecFilerSecurityLinkError("link-decision session members differ")
    path = session_dir / PARQUET_FILE
    _require_regular_mode(path, 0o400)
    if (
        path.stat().st_size != evidence.byte_size
        or _sha256_file(path) != evidence.physical_sha256
    ):
        raise SecFilerSecurityLinkError("link-decision artifact identity differs")
    table = pq.ParquetFile(path).read()
    if table.schema != LINK_ARROW_SCHEMA or table.num_rows != evidence.row_count:
        raise SecFilerSecurityLinkError(
            "link-decision artifact schema or count differs"
        )
    rows = tuple(
        SecFilerSecurityLinkDecisionV1.model_validate(row)
        for row in table.to_pylist()
    )
    if tuple(item.instrument_id for item in rows) != tuple(
        sorted(item.instrument_id for item in rows)
    ) or len({item.instrument_id for item in rows}) != len(rows):
        raise SecFilerSecurityLinkError("link-decision row order differs")
    if any(item.as_of_date != evidence.as_of_date for item in rows):
        raise SecFilerSecurityLinkError("link-decision row session differs")
    if any(
        item.point_in_time_eligibility != evidence.point_in_time_eligibility
        or item.source_observed_at != evidence.source_observed_at
        for item in rows
    ):
        raise SecFilerSecurityLinkError(
            "link-decision row source-time evidence differs"
        )
    if _table_fingerprint(table) != evidence.logical_fingerprint:
        raise SecFilerSecurityLinkError(
            "link-decision artifact fingerprint differs"
        )
    observed_status = Counter(item.decision_status for item in rows)
    if _ordered(observed_status) != evidence.decision_status_counts:
        raise SecFilerSecurityLinkError(
            "link-decision artifact status counts differ"
        )
    admitted_cik_counts = Counter(
        item.sec_cik for item in rows if item.sec_cik is not None
    )
    if any(
        item.sec_cik is not None
        and item.cik_instrument_count != admitted_cik_counts[item.sec_cik]
        for item in rows
    ):
        raise SecFilerSecurityLinkError(
            "link-decision row CIK cardinality differs"
        )
    observed_multi = sum(1 for value in admitted_cik_counts.values() if value > 1)
    if observed_multi != evidence.multi_security_cik_count:
        raise SecFilerSecurityLinkError(
            "link-decision CIK cardinality differs"
        )
    return _SessionRead(
        as_of_date=evidence.as_of_date,
        status_counts=_ordered(observed_status),
        resolution_counts=evidence.identity_resolution_counts,
    )


def _build_session(
    argument: tuple[str, str, str, date, bool]
) -> _SessionBuild:
    data_root_raw, partial_raw, provider, session, missing_allowed = argument
    data_root = Path(data_root_raw)
    partial = Path(partial_raw)
    snapshot = ParquetInstrumentMasterSnapshotRepository(data_root).inspect_snapshot(
        session
    )
    instruments = tuple(
        InstrumentMasterV1.model_validate(row)
        for row in pq.ParquetFile(snapshot.instrument_partition_path / PARQUET_FILE_NAME)
        .read()
        .to_pylist()
    )
    identities = tuple(
        ProviderInstrumentIdentityV1.model_validate(row)
        for row in pq.ParquetFile(snapshot.identity_partition_path / PARQUET_FILE_NAME)
        .read()
        .to_pylist()
    )
    source = None
    source_partition = (
        data_root
        / "market-data"
        / "provider-identity-reference-observation"
        / "schema_version=1"
        / f"provider={provider}"
        / f"as_of_date={session.isoformat()}"
    )
    if os.path.lexists(source_partition):
        source = read_identity_source_custody_at_data_root(
            data_root=data_root,
            provider=provider,
            session_date=session,
        )
    elif not missing_allowed:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody partition is unavailable"
        )
    if source is None:
        knowledge: KnowledgeClass = "source_custody_missing"
        observed_at = None
    else:
        if (
            source.manifest.canonical_instrument_fingerprint
            != snapshot.instrument_content_sha256
            or source.manifest.canonical_identity_fingerprint
            != snapshot.identity_content_sha256
        ):
            raise SecFilerSecurityLinkError("Identity source canonical binding differs")
        knowledge = source.manifest.point_in_time_eligibility
        observed_at = source.manifest.source_package_fetched_at
    rows = derive_sec_filer_security_link_decisions(
        as_of_date=session,
        instruments=instruments,
        identities=identities,
        point_in_time_eligibility=knowledge,
        source_observed_at=observed_at,
    )
    session_dir = partial / f"as_of_date={session.isoformat()}"
    os.mkdir(session_dir, mode=0o700)
    path = session_dir / PARQUET_FILE
    table = pa.Table.from_pylist(
        [item.model_dump(mode="python") for item in rows],
        schema=LINK_ARROW_SCHEMA,
    )
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    path.chmod(0o400)
    _fsync_file(path)
    _fsync_directory(session_dir)
    status_counts = Counter(item.decision_status for item in rows)
    resolution_counts = Counter(item.resolution_status.value for item in identities)
    multi_count = len(
        {
            item.sec_cik
            for item in rows
            if item.sec_cik is not None and item.cik_instrument_count > 1
        }
    )
    instrument_manifest = snapshot.instrument_partition_path / MANIFEST_FILE
    identity_manifest = snapshot.identity_partition_path / MANIFEST_FILE
    return _SessionBuild(
        evidence=SecFilerSecurityLinkSessionV1(
            as_of_date=session,
            relative_path=f"as_of_date={session.isoformat()}/{PARQUET_FILE}",
            row_count=len(rows),
            byte_size=path.stat().st_size,
            physical_sha256=_sha256_file(path),
            logical_fingerprint=_table_fingerprint(table),
            instrument_manifest_sha256=_sha256_file(instrument_manifest),
            instrument_parquet_sha256=_sha256_file(
                snapshot.instrument_partition_path / PARQUET_FILE_NAME
            ),
            identity_manifest_sha256=_sha256_file(identity_manifest),
            identity_parquet_sha256=_sha256_file(
                snapshot.identity_partition_path / PARQUET_FILE_NAME
            ),
            instrument_content_fingerprint=snapshot.instrument_content_sha256,
            identity_content_fingerprint=snapshot.identity_content_sha256,
            identity_source_custody_status=(
                "present" if source is not None else "missing_allowed"
            ),
            identity_source_manifest_sha256=(
                source.manifest_sha256 if source is not None else None
            ),
            identity_source_manifest_fingerprint=(
                source.manifest.logical_fingerprint if source is not None else None
            ),
            identity_source_content_fingerprint=(
                source.manifest.content_fingerprint if source is not None else None
            ),
            point_in_time_eligibility=knowledge,
            source_observed_at=observed_at,
            identity_resolution_counts=_ordered(resolution_counts),
            decision_status_counts=_ordered(status_counts),
            multi_security_cik_count=multi_count,
        ),
        status_counts=status_counts,
        resolution_counts=resolution_counts,
    )


def _validate_input_evidence(
    data_root: Path,
    provider: str,
    evidence: SecFilerSecurityLinkSessionV1,
) -> None:
    snapshot = ParquetInstrumentMasterSnapshotRepository(data_root).inspect_snapshot(
        evidence.as_of_date
    )
    checks = (
        (
            _sha256_file(snapshot.instrument_partition_path / MANIFEST_FILE),
            evidence.instrument_manifest_sha256,
        ),
        (
            _sha256_file(snapshot.instrument_partition_path / PARQUET_FILE_NAME),
            evidence.instrument_parquet_sha256,
        ),
        (
            _sha256_file(snapshot.identity_partition_path / MANIFEST_FILE),
            evidence.identity_manifest_sha256,
        ),
        (
            _sha256_file(snapshot.identity_partition_path / PARQUET_FILE_NAME),
            evidence.identity_parquet_sha256,
        ),
        (snapshot.instrument_content_sha256, evidence.instrument_content_fingerprint),
        (snapshot.identity_content_sha256, evidence.identity_content_fingerprint),
    )
    if any(actual != expected for actual, expected in checks):
        raise SecFilerSecurityLinkError("link-decision input Identity evidence drifted")
    identity_rows = pq.ParquetFile(
        snapshot.identity_partition_path / PARQUET_FILE_NAME
    ).read(columns=["resolution_status"])
    observed_resolutions = Counter(
        row["resolution_status"] for row in identity_rows.to_pylist()
    )
    if _ordered(observed_resolutions) != evidence.identity_resolution_counts:
        raise SecFilerSecurityLinkError(
            "link-decision input resolution counts drifted"
        )
    if evidence.identity_source_custody_status == "present":
        source = read_identity_source_custody_at_data_root(
            data_root=data_root,
            provider=provider,
            session_date=evidence.as_of_date,
        )
        if (
            source.manifest_sha256 != evidence.identity_source_manifest_sha256
            or source.manifest.logical_fingerprint
            != evidence.identity_source_manifest_fingerprint
            or source.manifest.content_fingerprint
            != evidence.identity_source_content_fingerprint
            or source.manifest.point_in_time_eligibility
            != evidence.point_in_time_eligibility
            or source.manifest.source_package_fetched_at != evidence.source_observed_at
        ):
            raise SecFilerSecurityLinkError("link-decision source evidence drifted")


def _build_manifest(
    *,
    results: tuple[_SessionBuild, ...],
    sessions: tuple[date, ...],
    allowed_missing_source_sessions: tuple[date, ...],
    implementation_revision: str,
    built_at: datetime,
    range_start: date,
    range_end: date,
    provider: str,
    calendar_version: str,
) -> SecFilerSecurityLinkManifestV1:
    evidence = tuple(item.evidence for item in results)
    statuses = sum((item.status_counts for item in results), Counter())
    resolutions = sum((item.resolution_counts for item in results), Counter())
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider": provider,
        "implementation_revision": implementation_revision,
        "built_at": built_at,
        "range_start": range_start,
        "range_end": range_end,
        "calendar_id": "XNYS",
        "calendar_version": calendar_version,
        "session_index_fingerprint": _fingerprint(
            tuple(item.isoformat() for item in sessions)
        ),
        "allowed_missing_source_sessions": allowed_missing_source_sessions,
        "sessions": evidence,
        "session_count": len(evidence),
        "row_count": sum(item.row_count for item in evidence),
        "decision_status_counts": _ordered(statuses),
        "identity_resolution_counts": _ordered(resolutions),
        "missing_source_session_count": len(allowed_missing_source_sessions),
        "multi_security_cik_session_count": sum(
            item.multi_security_cik_count for item in evidence
        ),
        "schema_fingerprint": hashlib.sha256(
            LINK_ARROW_SCHEMA.serialize().to_pybytes()
        ).hexdigest(),
        "content_fingerprint": _fingerprint(
            tuple((item.relative_path, item.logical_fingerprint) for item in evidence)
        ),
        "stable_instrument_resolution_count": sum(
            item.row_count for item in evidence
        ),
        "issuer_projection_authorized": False,
        "canonical_data_write_count": 0,
        "membership_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
        "research_performance_authorized": False,
    }
    return SecFilerSecurityLinkManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _validate_data_root(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecFilerSecurityLinkError("link-decision data root is unsafe")
    return root


def _validate_output_target(path: Path) -> tuple[Path, Path]:
    target = path.absolute()
    parent = target.parent
    if (
        parent.is_symlink()
        or not parent.is_dir()
        or parent.resolve(strict=True) != parent
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
        or parent.stat().st_uid != os.getuid()
        or re.fullmatch(r"build=[A-Za-z0-9._-]+", target.name) is None
    ):
        raise SecFilerSecurityLinkError("link-decision output target is unsafe")
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecFilerSecurityLinkError("link-decision output target already exists")
    return target, partial


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if package.is_symlink() or not package.is_dir() or package.resolve(strict=True) != package:
        raise SecFilerSecurityLinkError("link-decision package is unsafe")
    _require_mode(package, 0o700)
    return package


def _require_regular_mode(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise SecFilerSecurityLinkError("link-decision file is unsafe")
    _require_mode(path, mode)


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecFilerSecurityLinkError("link-decision ownership or mode differs")


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_MANIFEST_BYTES:
        raise SecFilerSecurityLinkError("link-decision manifest exceeds byte ceiling")
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(0o400)


def _table_fingerprint(table: pa.Table) -> str:
    digest = hashlib.sha256()
    for row in table.to_pylist():
        digest.update(_json_bytes(row))
        digest.update(b"\n")
    return digest.hexdigest()


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, value) for key, value in counter.items() if value > 0))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
