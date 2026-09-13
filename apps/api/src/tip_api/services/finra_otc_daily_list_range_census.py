"""Network-free transitive census of exact FINRA monthly source packages."""

from __future__ import annotations

import calendar
import hashlib
import json
import os
import stat
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.finra_otc_daily_list_source import (
    PROVIDER_ID,
    read_finra_otc_daily_list_source_payloads,
)


CONTRACT_VERSION = "finra-otc-daily-list-range-census/1.0"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_MAXIMUM_CENSUS_BYTES = 1024 * 1024


class FinraOtcDailyListRangeCensusError(RuntimeError):
    """Raised when the exact source range cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FinraOtcDailyListRangePackageV1(_FrozenModel):
    partition_start: date
    partition_end: date
    package_name: str
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    data_version: int = Field(ge=1)
    request_count: int = Field(ge=1)
    record_count: int = Field(ge=0)
    package_bytes: int = Field(ge=1)


class FinraOtcRepeatedSourceIdentifierOccurrenceV1(_FrozenModel):
    partition_start: date
    calendar_day: date
    page_sequence: int = Field(ge=1)
    row_sequence: int = Field(ge=1)
    payload_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    event_code: str | None = None
    old_symbol: str | None = None
    new_symbol: str | None = None


class FinraOtcRepeatedSourceIdentifierV1(_FrozenModel):
    source_identifier: int = Field(ge=1)
    occurrence_count: int = Field(ge=2)
    distinct_payload_count: int = Field(ge=1)
    occurrences: tuple[FinraOtcRepeatedSourceIdentifierOccurrenceV1, ...] = Field(
        min_length=2
    )

    @model_validator(mode="after")
    def repeated_identifier_reconciles(self) -> "FinraOtcRepeatedSourceIdentifierV1":
        if self.occurrence_count != len(self.occurrences):
            raise ValueError("FINRA repeated-identifier occurrence count differs")
        if self.distinct_payload_count != len(
            {item.payload_fingerprint for item in self.occurrences}
        ):
            raise ValueError("FINRA repeated-identifier payload count differs")
        return self


class FinraOtcDailyListRangeCensusV1(_FrozenModel):
    contract_version: Literal[
        "finra-otc-daily-list-range-census/1.0"
    ] = CONTRACT_VERSION
    provider_id: Literal["finra_otc_daily_list"] = PROVIDER_ID
    range_start: date
    range_end: date
    evaluated_at: datetime
    coverage_status: Literal["complete", "complete_with_repeated_identifiers"]
    evidence_role: Literal["official_otc_corroboration_only"] = (
        "official_otc_corroboration_only"
    )
    package_count: int = Field(ge=1)
    request_count: int = Field(ge=1)
    record_count: int = Field(ge=0)
    unique_source_identifier_count: int = Field(ge=0)
    repeated_source_identifier_group_count: int = Field(ge=0)
    repeated_source_identifier_additional_occurrence_count: int = Field(ge=0)
    retained_page_bytes: int = Field(ge=1)
    data_version_counts: tuple[tuple[int, int], ...]
    event_code_counts: tuple[tuple[str, int], ...]
    packages: tuple[FinraOtcDailyListRangePackageV1, ...] = Field(min_length=1)
    repeated_source_identifiers: tuple[FinraOtcRepeatedSourceIdentifierV1, ...]
    package_chain_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    network_request_count: Literal[0] = 0
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
    def census_reconciles(self) -> "FinraOtcDailyListRangeCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("FINRA census range is reversed")
        if self.package_count != len(self.packages):
            raise ValueError("FINRA census package count differs")
        if self.request_count != sum(item.request_count for item in self.packages):
            raise ValueError("FINRA census request count differs")
        if self.record_count != sum(item.record_count for item in self.packages):
            raise ValueError("FINRA census record count differs")
        if self.retained_page_bytes != sum(item.package_bytes for item in self.packages):
            raise ValueError("FINRA census byte count differs")
        if self.repeated_source_identifier_group_count != len(
            self.repeated_source_identifiers
        ):
            raise ValueError("FINRA repeated-identifier group count differs")
        additional = sum(
            item.occurrence_count - 1 for item in self.repeated_source_identifiers
        )
        if self.repeated_source_identifier_additional_occurrence_count != additional:
            raise ValueError("FINRA repeated-identifier occurrence count differs")
        if self.unique_source_identifier_count + additional != self.record_count:
            raise ValueError("FINRA source identifier population differs")
        expected_status = (
            "complete_with_repeated_identifiers"
            if self.repeated_source_identifiers
            else "complete"
        )
        if self.coverage_status != expected_status:
            raise ValueError("FINRA census coverage status differs")
        expected_chain = _fingerprint(
            tuple(
                (
                    item.package_name,
                    item.manifest_sha256,
                    item.logical_fingerprint,
                    item.record_count,
                    item.request_count,
                    item.data_version,
                )
                for item in self.packages
            )
        )
        if self.package_chain_fingerprint != expected_chain:
            raise ValueError("FINRA package chain fingerprint differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("FINRA range census fingerprint differs")
        return self


def census_finra_otc_daily_list_range(
    *,
    custody_root: Path,
    range_start: date,
    range_end: date,
    evaluated_at: datetime | None = None,
) -> FinraOtcDailyListRangeCensusV1:
    """Reread every exact monthly package with no network or writes."""

    if range_end < range_start:
        raise FinraOtcDailyListRangeCensusError("FINRA census range is reversed")
    root = custody_root.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise FinraOtcDailyListRangeCensusError("FINRA census custody root is unsafe")

    package_records: list[FinraOtcDailyListRangePackageV1] = []
    event_counts: Counter[str] = Counter()
    version_counts: Counter[int] = Counter()
    occurrences: defaultdict[
        int, list[FinraOtcRepeatedSourceIdentifierOccurrenceV1]
    ] = defaultdict(list)
    for start, end in _monthly_partitions(range_start, range_end):
        package_name = f"period={start.isoformat()}--{end.isoformat()}"
        validated = read_finra_otc_daily_list_source_payloads(
            package_path=root / package_name,
            expected_partition_start=start,
            expected_partition_end=end,
            approved_custody_root=root,
        )
        manifest = validated.manifest
        package_records.append(
            FinraOtcDailyListRangePackageV1(
                partition_start=start,
                partition_end=end,
                package_name=package_name,
                manifest_sha256=validated.manifest_sha256,
                logical_fingerprint=manifest.logical_fingerprint,
                data_version=manifest.data_version,
                request_count=manifest.request_count,
                record_count=manifest.record_count,
                package_bytes=manifest.package_bytes,
            )
        )
        event_counts.update(dict(manifest.event_code_counts))
        version_counts[manifest.data_version] += 1
        for page in validated.pages:
            for row_sequence, row in enumerate(page.rows, 1):
                identifier = row.get("OTCDailyListID")
                calendar_day = row.get("calendarDay")
                if not isinstance(identifier, int) or not isinstance(calendar_day, str):
                    raise FinraOtcDailyListRangeCensusError(
                        "validated FINRA row identity differs"
                    )
                occurrences[identifier].append(
                    FinraOtcRepeatedSourceIdentifierOccurrenceV1(
                        partition_start=start,
                        calendar_day=date.fromisoformat(calendar_day),
                        page_sequence=page.sequence,
                        row_sequence=row_sequence,
                        payload_fingerprint=_fingerprint(row),
                        event_code=_optional_code(row.get("dailyListEventCode")),
                        old_symbol=_optional_code(row.get("oldSymbolCode")),
                        new_symbol=_optional_code(row.get("newSymbolCode")),
                    )
                )

    repeated = tuple(
        FinraOtcRepeatedSourceIdentifierV1(
            source_identifier=identifier,
            occurrence_count=len(items),
            distinct_payload_count=len({item.payload_fingerprint for item in items}),
            occurrences=tuple(items),
        )
        for identifier, items in sorted(occurrences.items())
        if len(items) > 1
    )
    packages = tuple(package_records)
    record_count = sum(item.record_count for item in packages)
    additional = sum(item.occurrence_count - 1 for item in repeated)
    values = {
        "contract_version": CONTRACT_VERSION,
        "provider_id": PROVIDER_ID,
        "range_start": range_start,
        "range_end": range_end,
        "evaluated_at": normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
        "coverage_status": (
            "complete_with_repeated_identifiers" if repeated else "complete"
        ),
        "evidence_role": "official_otc_corroboration_only",
        "package_count": len(packages),
        "request_count": sum(item.request_count for item in packages),
        "record_count": record_count,
        "unique_source_identifier_count": len(occurrences),
        "repeated_source_identifier_group_count": len(repeated),
        "repeated_source_identifier_additional_occurrence_count": additional,
        "retained_page_bytes": sum(item.package_bytes for item in packages),
        "data_version_counts": tuple(sorted(version_counts.items())),
        "event_code_counts": tuple(sorted(event_counts.items())),
        "packages": packages,
        "repeated_source_identifiers": repeated,
        "package_chain_fingerprint": _fingerprint(
            tuple(
                (
                    item.package_name,
                    item.manifest_sha256,
                    item.logical_fingerprint,
                    item.record_count,
                    item.request_count,
                    item.data_version,
                )
                for item in packages
            )
        ),
        "network_request_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return FinraOtcDailyListRangeCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def seal_finra_otc_daily_list_range_census(
    *,
    custody_root: Path,
    census: FinraOtcDailyListRangeCensusV1,
) -> Path:
    """Write one owner-only immutable transitive census beside its packages."""

    root = _validate_custody_root(custody_root)
    target = root / _census_file_name(census.range_start, census.range_end)
    raw = _json_bytes(census.model_dump(mode="json")) + b"\n"
    if len(raw) > _MAXIMUM_CENSUS_BYTES:
        raise FinraOtcDailyListRangeCensusError("FINRA census exceeds byte ceiling")
    descriptor = os.open(
        target,
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
    target.chmod(0o400)
    _fsync_directory(root)
    return target


def read_sealed_finra_otc_daily_list_range_census(
    *,
    custody_root: Path,
    range_start: date,
    range_end: date,
) -> FinraOtcDailyListRangeCensusV1:
    """Reread one sealed range census without rereading all source pages."""

    root = _validate_custody_root(custody_root)
    target = root / _census_file_name(range_start, range_end)
    if target.is_symlink() or not target.is_file():
        raise FinraOtcDailyListRangeCensusError("sealed FINRA census is unavailable")
    metadata = target.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise FinraOtcDailyListRangeCensusError("sealed FINRA census mode differs")
    if metadata.st_size < 1 or metadata.st_size > _MAXIMUM_CENSUS_BYTES:
        raise FinraOtcDailyListRangeCensusError("sealed FINRA census size differs")
    try:
        census = FinraOtcDailyListRangeCensusV1.model_validate_json(
            target.read_bytes()
        )
    except Exception as exc:
        raise FinraOtcDailyListRangeCensusError(
            "sealed FINRA census contract is invalid"
        ) from exc
    if census.range_start != range_start or census.range_end != range_end:
        raise FinraOtcDailyListRangeCensusError("sealed FINRA census range differs")
    return census


def _monthly_partitions(start: date, end: date) -> tuple[tuple[date, date], ...]:
    values: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        partition_end = min(date(cursor.year, cursor.month, last_day), end)
        values.append((cursor, partition_end))
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    return tuple(values)


def _validate_custody_root(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise FinraOtcDailyListRangeCensusError("FINRA census custody root is unsafe")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise FinraOtcDailyListRangeCensusError("FINRA census custody root mode differs")
    return root


def _census_file_name(start: date, end: date) -> str:
    return f"range-census={start.isoformat()}--{end.isoformat()}.json"


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _optional_code(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FinraOtcDailyListRangeCensusError("FINRA source code is malformed")
    normalized = value.strip().upper()
    return normalized or None


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
