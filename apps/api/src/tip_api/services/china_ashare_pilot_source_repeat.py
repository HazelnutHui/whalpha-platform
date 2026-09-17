"""Exact source-repeat comparison for temporary China A-share daily pilots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
    read_china_ashare_pilot_daily_package,
)


CONTRACT_VERSION = "china-ashare-pilot-source-repeat/1.0"
CHANGES_CONTRACT_VERSION = "china-ashare-pilot-source-repeat-changes/1.0"
MANIFEST_FILE = "source-repeat-report.json"
CHANGES_FILE = "source-repeat-changes.json"
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
_SHA256 = r"^[0-9a-f]{64}$"
_IGNORED_FIELDS = ("ingested_at",)


class ChinaAsharePilotSourceRepeatError(RuntimeError):
    """Raised when a pilot source-repeat comparison cannot be trusted."""


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChinaAsharePilotRepeatFamily(StrEnum):
    ADJUSTMENT_FACTOR = "adjustment_factor"
    DAILY_BAR = "daily_bar"
    DAILY_TRADING_STATE = "daily_trading_state"


class ChinaAsharePilotRepeatChangeV1(FrozenContract):
    family: ChinaAsharePilotRepeatFamily
    business_key: str = Field(min_length=1)
    change_type: Literal["added", "changed", "removed"]
    baseline_payload_sha256: str | None = Field(default=None, pattern=_SHA256)
    repeat_payload_sha256: str | None = Field(default=None, pattern=_SHA256)
    changed_fields: tuple[str, ...] = ()

    @field_validator("business_key")
    @classmethod
    def business_key_is_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("repeat business key must be trimmed")
        return value

    @field_validator("changed_fields")
    @classmethod
    def changed_fields_are_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item for item in value):
            raise ValueError("repeat changed fields must be unique and ordered")
        return value

    @model_validator(mode="after")
    def change_shape_reconciles(self) -> "ChinaAsharePilotRepeatChangeV1":
        if self.change_type == "added":
            if self.baseline_payload_sha256 is not None or self.repeat_payload_sha256 is None:
                raise ValueError("added repeat change hashes differ")
        elif self.change_type == "removed":
            if self.baseline_payload_sha256 is None or self.repeat_payload_sha256 is not None:
                raise ValueError("removed repeat change hashes differ")
        elif (
            self.baseline_payload_sha256 is None
            or self.repeat_payload_sha256 is None
            or self.baseline_payload_sha256 == self.repeat_payload_sha256
            or not self.changed_fields
        ):
            raise ValueError("changed repeat row contains no payload delta")
        if self.change_type != "changed" and self.changed_fields:
            raise ValueError("added or removed repeat rows cannot name changed fields")
        return self


class ChinaAsharePilotRepeatChangesV1(FrozenContract):
    contract_version: Literal[
        "china-ashare-pilot-source-repeat-changes/1.0"
    ] = CHANGES_CONTRACT_VERSION
    changes: tuple[ChinaAsharePilotRepeatChangeV1, ...]
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def changes_reconcile(self) -> "ChinaAsharePilotRepeatChangesV1":
        keys = tuple(
            (item.family.value, item.change_type, item.business_key)
            for item in self.changes
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("source-repeat changes must be unique and ordered")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("source-repeat changes fingerprint differs")
        return self


class ChinaAsharePilotRepeatFamilySummaryV1(FrozenContract):
    family: ChinaAsharePilotRepeatFamily
    baseline_count: int = Field(ge=0)
    repeat_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    changed_count: int = Field(ge=0)
    added_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_reconcile(self) -> "ChinaAsharePilotRepeatFamilySummaryV1":
        if self.baseline_count != (
            self.unchanged_count + self.changed_count + self.removed_count
        ):
            raise ValueError("baseline source-repeat family count differs")
        if self.repeat_count != (
            self.unchanged_count + self.changed_count + self.added_count
        ):
            raise ValueError("repeat source-repeat family count differs")
        return self


class ChinaAsharePilotSourceRepeatReportV1(FrozenContract):
    contract_version: Literal["china-ashare-pilot-source-repeat/1.0"] = (
        CONTRACT_VERSION
    )
    market_id: Literal["china_a_share"] = "china_a_share"
    plan_fingerprint: str = Field(pattern=_SHA256)
    reference_package_fingerprint: str = Field(pattern=_SHA256)
    baseline_daily_package_fingerprint: str = Field(pattern=_SHA256)
    repeat_daily_package_fingerprint: str = Field(pattern=_SHA256)
    baseline_created_at: datetime
    repeat_created_at: datetime
    compared_at: datetime
    ignored_fields: tuple[Literal["ingested_at"], ...] = _IGNORED_FIELDS
    family_summaries: tuple[ChinaAsharePilotRepeatFamilySummaryV1, ...]
    changes_file_sha256: str = Field(pattern=_SHA256)
    changes_file_bytes: int = Field(ge=1, le=MAXIMUM_JSON_BYTES)
    changes_logical_fingerprint: str = Field(pattern=_SHA256)
    total_change_count: int = Field(ge=0)
    economic_values_stable: bool
    source_repeat_qualified: bool
    raw_upstream_payload_retained: Literal[False] = False
    canonical_identity_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("baseline_created_at", "repeat_created_at", "compared_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("ignored_fields")
    @classmethod
    def ignored_fields_are_fixed(
        cls, value: tuple[Literal["ingested_at"], ...]
    ) -> tuple[Literal["ingested_at"], ...]:
        if value != _IGNORED_FIELDS:
            raise ValueError("source-repeat ignored-field policy differs")
        return value

    @field_validator("reason_codes")
    @classmethod
    def reasons_are_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item for item in value):
            raise ValueError("source-repeat reasons must be unique and ordered")
        return value

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAsharePilotSourceRepeatReportV1":
        if not (
            self.baseline_created_at < self.repeat_created_at <= self.compared_at
        ):
            raise ValueError("source-repeat observation order differs")
        families = tuple(item.family.value for item in self.family_summaries)
        expected_families = tuple(sorted(item.value for item in ChinaAsharePilotRepeatFamily))
        if families != expected_families:
            raise ValueError("source-repeat family set differs")
        aggregate = sum(
            item.changed_count + item.added_count + item.removed_count
            for item in self.family_summaries
        )
        if self.total_change_count != aggregate:
            raise ValueError("source-repeat total change count differs")
        expected_stable = self.total_change_count == 0
        if self.economic_values_stable is not expected_stable:
            raise ValueError("source-repeat economic stability differs")
        if self.source_repeat_qualified is not expected_stable:
            raise ValueError("source-repeat qualification differs")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("source-repeat report fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class ChinaAsharePilotSourceRepeatResultV1:
    report: ChinaAsharePilotSourceRepeatReportV1
    changes: tuple[ChinaAsharePilotRepeatChangeV1, ...]
    output_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    status: Literal["already_present", "published", "reread"]


def compare_china_ashare_pilot_daily_packages(
    *,
    baseline_package_path: Path,
    repeat_package_path: Path,
    compared_at: datetime,
) -> ChinaAsharePilotSourceRepeatResultV1:
    """Compare source economics while deliberately ignoring ingestion clocks."""

    baseline = read_china_ashare_pilot_daily_package(
        package_path=baseline_package_path
    )
    repeat = read_china_ashare_pilot_daily_package(package_path=repeat_package_path)
    compared_at = normalize_utc_datetime(compared_at)
    _validate_package_pair(baseline, repeat, compared_at)

    changes: list[ChinaAsharePilotRepeatChangeV1] = []
    summaries: list[ChinaAsharePilotRepeatFamilySummaryV1] = []
    for family in sorted(ChinaAsharePilotRepeatFamily, key=lambda item: item.value):
        baseline_rows = _rows_for_family(baseline, family)
        repeat_rows = _rows_for_family(repeat, family)
        family_changes, unchanged = _compare_rows(family, baseline_rows, repeat_rows)
        changes.extend(family_changes)
        summaries.append(
            ChinaAsharePilotRepeatFamilySummaryV1(
                family=family,
                baseline_count=len(baseline_rows),
                repeat_count=len(repeat_rows),
                unchanged_count=unchanged,
                changed_count=sum(
                    item.change_type == "changed" for item in family_changes
                ),
                added_count=sum(item.change_type == "added" for item in family_changes),
                removed_count=sum(
                    item.change_type == "removed" for item in family_changes
                ),
            )
        )
    ordered_changes = tuple(
        sorted(
            changes,
            key=lambda item: (item.family.value, item.change_type, item.business_key),
        )
    )
    changes_values = {
        "contract_version": CHANGES_CONTRACT_VERSION,
        "changes": ordered_changes,
    }
    changes_model = ChinaAsharePilotRepeatChangesV1.model_validate(
        {
            **changes_values,
            "logical_fingerprint": _fingerprint(changes_values),
        }
    )
    changes_bytes = _canonical_json_bytes(changes_model.model_dump(mode="json"))
    reasons = (
        ("economic_source_values_stable",)
        if not ordered_changes
        else ("economic_source_values_changed",)
    )
    report_values = {
        "contract_version": CONTRACT_VERSION,
        "market_id": "china_a_share",
        "plan_fingerprint": baseline.manifest.plan_fingerprint,
        "reference_package_fingerprint": (
            baseline.manifest.reference_package_fingerprint
        ),
        "baseline_daily_package_fingerprint": baseline.manifest.logical_fingerprint,
        "repeat_daily_package_fingerprint": repeat.manifest.logical_fingerprint,
        "baseline_created_at": baseline.manifest.created_at,
        "repeat_created_at": repeat.manifest.created_at,
        "compared_at": compared_at,
        "ignored_fields": _IGNORED_FIELDS,
        "family_summaries": tuple(summaries),
        "changes_file_sha256": _sha256(changes_bytes),
        "changes_file_bytes": len(changes_bytes),
        "changes_logical_fingerprint": changes_model.logical_fingerprint,
        "total_change_count": len(ordered_changes),
        "economic_values_stable": not ordered_changes,
        "source_repeat_qualified": not ordered_changes,
        "raw_upstream_payload_retained": False,
        "canonical_identity_authorized": False,
        "canonical_apply_authorized": False,
        "research_backtest_authorized": False,
        "product_publication_authorized": False,
        "deployment_authorized": False,
        "reason_codes": reasons,
    }
    report = ChinaAsharePilotSourceRepeatReportV1.model_validate(
        {
            **report_values,
            "logical_fingerprint": _fingerprint(report_values),
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    output = _output_path(baseline, report.logical_fingerprint)
    if output.exists() or output.is_symlink():
        existing = read_china_ashare_pilot_source_repeat(output_path=output)
        if existing.report != report or existing.changes != ordered_changes:
            raise ChinaAsharePilotSourceRepeatError(
                "existing A-share source-repeat report differs"
            )
        return replace(existing, status="already_present")

    staging = output.parent / f".{output.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        _write_owner_only(staging / CHANGES_FILE, changes_bytes)
        _write_owner_only(staging / MANIFEST_FILE, report_bytes)
        _fsync_directory(staging)
        staging.replace(output)
        _fsync_directory(output.parent)
        reread = read_china_ashare_pilot_source_repeat(output_path=output)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    if reread.report != report or reread.changes != ordered_changes:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat report changed after publication"
        )
    return replace(reread, status="published")


def read_china_ashare_pilot_source_repeat(
    *, output_path: Path
) -> ChinaAsharePilotSourceRepeatResultV1:
    output = _validate_output_path(output_path)
    actual_files = {item.name for item in output.iterdir()}
    if actual_files != {MANIFEST_FILE, CHANGES_FILE}:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat file set differs"
        )
    manifest_path = output / MANIFEST_FILE
    changes_path = output / CHANGES_FILE
    report_bytes = _read_owner_only(manifest_path)
    changes_bytes = _read_owner_only(changes_path)
    try:
        report = ChinaAsharePilotSourceRepeatReportV1.model_validate_json(
            report_bytes
        )
        changes_model = ChinaAsharePilotRepeatChangesV1.model_validate_json(
            changes_bytes
        )
    except Exception as exc:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat report is invalid"
        ) from exc
    if output.name != f"source-repeat={report.logical_fingerprint}":
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat path identity differs"
        )
    if (
        _sha256(changes_bytes) != report.changes_file_sha256
        or len(changes_bytes) != report.changes_file_bytes
        or changes_model.logical_fingerprint != report.changes_logical_fingerprint
        or len(changes_model.changes) != report.total_change_count
    ):
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat changes binding differs"
        )
    summary_counts = {
        item.family: (item.changed_count, item.added_count, item.removed_count)
        for item in report.family_summaries
    }
    actual_counts = {
        family: (
            sum(
                item.family is family and item.change_type == "changed"
                for item in changes_model.changes
            ),
            sum(
                item.family is family and item.change_type == "added"
                for item in changes_model.changes
            ),
            sum(
                item.family is family and item.change_type == "removed"
                for item in changes_model.changes
            ),
        )
        for family in ChinaAsharePilotRepeatFamily
    }
    if summary_counts != actual_counts:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat aggregate differs"
        )
    return ChinaAsharePilotSourceRepeatResultV1(
        report=report,
        changes=changes_model.changes,
        output_path=output,
        manifest_path=manifest_path,
        manifest_physical_sha256=_sha256(report_bytes),
        status="reread",
    )


def _validate_package_pair(
    baseline: ChinaAsharePilotDailyPackageResultV1,
    repeat: ChinaAsharePilotDailyPackageResultV1,
    compared_at: datetime,
) -> None:
    if baseline.package_path == repeat.package_path:
        raise ChinaAsharePilotSourceRepeatError(
            "source-repeat comparison requires distinct daily packages"
        )
    if baseline.plan != repeat.plan:
        raise ChinaAsharePilotSourceRepeatError("source-repeat plan differs")
    if (
        baseline.manifest.reference_package_fingerprint
        != repeat.manifest.reference_package_fingerprint
    ):
        raise ChinaAsharePilotSourceRepeatError(
            "source-repeat reference package differs"
        )
    if (
        baseline.captured.daily_batch.provider_id
        != repeat.captured.daily_batch.provider_id
        or baseline.captured.daily_batch.query != repeat.captured.daily_batch.query
    ):
        raise ChinaAsharePilotSourceRepeatError("source-repeat query differs")
    if not (
        baseline.manifest.created_at < repeat.manifest.created_at <= compared_at
    ):
        raise ChinaAsharePilotSourceRepeatError(
            "source-repeat package ordering differs"
        )


def _rows_for_family(
    package: ChinaAsharePilotDailyPackageResultV1,
    family: ChinaAsharePilotRepeatFamily,
) -> dict[str, Mapping[str, Any]]:
    if family is ChinaAsharePilotRepeatFamily.DAILY_BAR:
        rows = package.captured.daily_batch.bars
    elif family is ChinaAsharePilotRepeatFamily.DAILY_TRADING_STATE:
        rows = package.captured.daily_batch.trading_states
    else:
        rows = package.captured.adjustment_observations
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        key = f"{row.instrument_id}:{row.session_date.isoformat()}"
        if key in result:
            raise ChinaAsharePilotSourceRepeatError(
                "source-repeat package contains a duplicate business key"
            )
        result[key] = row.model_dump(mode="json", exclude=set(_IGNORED_FIELDS))
    return result


def _compare_rows(
    family: ChinaAsharePilotRepeatFamily,
    baseline: Mapping[str, Mapping[str, Any]],
    repeat: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[ChinaAsharePilotRepeatChangeV1, ...], int]:
    changes: list[ChinaAsharePilotRepeatChangeV1] = []
    unchanged = 0
    for key in sorted(set(baseline) | set(repeat)):
        before = baseline.get(key)
        after = repeat.get(key)
        before_hash = None if before is None else _fingerprint(before)
        after_hash = None if after is None else _fingerprint(after)
        if before_hash == after_hash:
            unchanged += 1
            continue
        if before is None:
            change_type = "added"
            changed_fields: tuple[str, ...] = ()
        elif after is None:
            change_type = "removed"
            changed_fields = ()
        else:
            change_type = "changed"
            changed_fields = tuple(
                sorted(
                    field
                    for field in set(before) | set(after)
                    if _canonical_value(before.get(field))
                    != _canonical_value(after.get(field))
                )
            )
        changes.append(
            ChinaAsharePilotRepeatChangeV1(
                family=family,
                business_key=key,
                change_type=change_type,
                baseline_payload_sha256=before_hash,
                repeat_payload_sha256=after_hash,
                changed_fields=changed_fields,
            )
        )
    return tuple(changes), unchanged


def _output_path(
    baseline: ChinaAsharePilotDailyPackageResultV1,
    logical_fingerprint: str,
) -> Path:
    plan_directory = baseline.package_path.parent
    target = plan_directory / f"source-repeat={logical_fingerprint}"
    if target.is_symlink():
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat target is a symlink"
        )
    return target


def _validate_output_path(path: Path) -> Path:
    output = path.absolute()
    if (
        Path("/tmp") not in output.parents
        or not output.name.startswith("source-repeat=")
        or not output.parent.name.startswith("plan=")
        or output.parent.parent.name != "china-a-share-research-pilot"
        or not output.is_dir()
        or output.is_symlink()
        or stat.S_IMODE(output.stat().st_mode) != 0o700
    ):
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat output path is invalid"
        )
    return output


def _write_owner_only(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o400)
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _read_owner_only(path: Path) -> bytes:
    if (
        not path.is_file()
        or path.is_symlink()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
    ):
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat file custody differs"
        )
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat file size differs"
        )
    return path.read_bytes()


def _canonical_json_bytes(value: object) -> bytes:
    payload = (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")
    if len(payload) > MAXIMUM_JSON_BYTES:
        raise ChinaAsharePilotSourceRepeatError(
            "A-share source-repeat payload exceeds its ceiling"
        )
    return payload


def _canonical_value(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return _sha256(_canonical_value(value))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
