"""Compare two complete corporate-action source observations without network."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    HistoricalCorporateActionSourceError,
    ValidatedCorporateActionSourcePackage,
    read_historical_corporate_action_source_package,
)


CONTRACT_VERSION = "historical-corporate-action-source-repeat-diff/1.0"
CHANGES_CONTRACT_VERSION = (
    "historical-corporate-action-source-repeat-diff-changes/1.0"
)
MANIFEST_FILE = "diff.json"
CHANGES_FILE = "changes.json"
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class HistoricalCorporateActionRepeatDiffError(RuntimeError):
    """Raised when a source-observation comparison is not trustworthy."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorporateActionSourceRepeatChangeV1(FrozenModel):
    source_action_id: str
    change_type: Literal["added", "removed", "changed"]
    baseline_payload_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    repeat_payload_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    changed_fields: tuple[str, ...] = ()
    baseline_effective_date: date | None = None
    repeat_effective_date: date | None = None
    baseline_provider_ticker: str | None = None
    repeat_provider_ticker: str | None = None

    @field_validator("source_action_id")
    @classmethod
    def source_id_is_nonempty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("source action ID is invalid")
        return value

    @field_validator("changed_fields")
    @classmethod
    def changed_fields_are_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item for item in value):
            raise ValueError("changed fields must be unique and ordered")
        return value

    @field_validator("baseline_provider_ticker", "repeat_provider_ticker")
    @classmethod
    def optional_ticker_is_trimmed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or value != value.strip():
            raise ValueError("provider ticker is invalid")
        return value

    @model_validator(mode="after")
    def change_shape_reconciles(self) -> "CorporateActionSourceRepeatChangeV1":
        if self.change_type == "added":
            if self.baseline_payload_sha256 is not None or (
                self.repeat_payload_sha256 is None
            ):
                raise ValueError("added change hashes differ")
            if self.baseline_effective_date is not None or (
                self.baseline_provider_ticker is not None
            ):
                raise ValueError("added change carries baseline facts")
        elif self.change_type == "removed":
            if self.baseline_payload_sha256 is None or (
                self.repeat_payload_sha256 is not None
            ):
                raise ValueError("removed change hashes differ")
            if self.repeat_effective_date is not None or (
                self.repeat_provider_ticker is not None
            ):
                raise ValueError("removed change carries repeat facts")
        elif (
            self.baseline_payload_sha256 is None
            or self.repeat_payload_sha256 is None
            or self.baseline_payload_sha256 == self.repeat_payload_sha256
            or not self.changed_fields
        ):
            raise ValueError("changed record does not contain a payload delta")
        if self.change_type != "changed" and self.changed_fields:
            raise ValueError("added/removed records cannot claim changed fields")
        return self


class CorporateActionSourceRepeatChangesV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-source-repeat-diff-changes/1.0"
    ] = CHANGES_CONTRACT_VERSION
    changes: tuple[CorporateActionSourceRepeatChangeV1, ...]
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def changes_reconcile(self) -> "CorporateActionSourceRepeatChangesV1":
        keys = tuple((item.change_type, item.source_action_id) for item in self.changes)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("repeat changes are not unique and ordered")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("repeat changes logical fingerprint differs")
        return self


class CorporateActionSourceRepeatDiffManifestV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-source-repeat-diff/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    action_kind: CorporateActionSourceKind
    start_date: date
    end_date: date
    compared_at: datetime
    baseline_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    baseline_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    baseline_started_at: datetime
    baseline_completed_at: datetime
    baseline_request_count: int = Field(ge=1)
    baseline_record_count: int = Field(ge=0)
    baseline_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    repeat_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    repeat_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    repeat_started_at: datetime
    repeat_completed_at: datetime
    repeat_request_count: int = Field(ge=1)
    repeat_record_count: int = Field(ge=0)
    repeat_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    all_rows_have_provider_action_id: Literal[True] = True
    duplicate_provider_action_id_count: Literal[0] = 0
    unchanged_record_count: int = Field(ge=0)
    changed_record_count: int = Field(ge=0)
    added_record_count: int = Field(ge=0)
    removed_record_count: int = Field(ge=0)
    changed_field_counts: tuple[tuple[str, int], ...]
    effective_date_changed_record_count: int = Field(ge=0)
    provider_ticker_changed_record_count: int = Field(ge=0)
    pagination_shape_changed: bool
    changes_file: Literal["changes.json"] = CHANGES_FILE
    changes_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    changes_file_bytes: int = Field(ge=1, le=MAXIMUM_JSON_BYTES)
    changes_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    observation_order_valid: Literal[True] = True
    revision_interpretation: Literal["observed_snapshot_delta_only"] = (
        "observed_snapshot_delta_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "compared_at",
        "baseline_started_at",
        "baseline_completed_at",
        "repeat_started_at",
        "repeat_completed_at",
    )
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "CorporateActionSourceRepeatDiffManifestV1":
        if self.end_date < self.start_date:
            raise ValueError("repeat diff date range is reversed")
        if not (
            self.baseline_started_at
            <= self.baseline_completed_at
            < self.repeat_started_at
            <= self.repeat_completed_at
            <= self.compared_at
        ):
            raise ValueError("repeat observation ordering differs")
        if self.baseline_record_count != (
            self.unchanged_record_count
            + self.changed_record_count
            + self.removed_record_count
        ):
            raise ValueError("baseline repeat-diff counts differ")
        if self.repeat_record_count != (
            self.unchanged_record_count
            + self.changed_record_count
            + self.added_record_count
        ):
            raise ValueError("repeat repeat-diff counts differ")
        if self.effective_date_changed_record_count > self.changed_record_count:
            raise ValueError("effective-date change count differs")
        if self.provider_ticker_changed_record_count > self.changed_record_count:
            raise ValueError("ticker change count differs")
        if self.changed_field_counts != tuple(sorted(self.changed_field_counts)) or any(
            not field or count < 1 for field, count in self.changed_field_counts
        ):
            raise ValueError("changed-field counts are invalid")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("repeat diff logical fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class CorporateActionSourceRepeatDiffResult:
    output_root: Path
    manifest: CorporateActionSourceRepeatDiffManifestV1
    changes: tuple[CorporateActionSourceRepeatChangeV1, ...]
    manifest_sha256: str
    status: Literal["published", "already_present"]


def build_historical_corporate_action_repeat_diff(
    *,
    baseline_package_path: Path,
    repeat_package_path: Path,
    output_root: Path,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    compared_at: datetime,
) -> CorporateActionSourceRepeatDiffResult:
    """Compare two complete source packages and publish only diff metadata."""

    with _network_prohibited():
        return _build_diff(
            baseline_package_path=baseline_package_path,
            repeat_package_path=repeat_package_path,
            output_root=output_root,
            action_kind=CorporateActionSourceKind(action_kind),
            start_date=start_date,
            end_date=end_date,
            compared_at=compared_at,
        )


def _build_diff(
    *,
    baseline_package_path: Path,
    repeat_package_path: Path,
    output_root: Path,
    action_kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
    compared_at: datetime,
) -> CorporateActionSourceRepeatDiffResult:
    baseline = _read_source(
        baseline_package_path, action_kind, start_date, end_date
    )
    repeat = _read_source(repeat_package_path, action_kind, start_date, end_date)
    compared_at = normalize_utc_datetime(compared_at)
    if baseline.package_path == repeat.package_path:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat comparison requires two distinct packages"
        )
    if baseline.manifest.completed_at >= repeat.manifest.started_at:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat source observation does not follow the baseline"
        )
    if compared_at < repeat.manifest.completed_at:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff time precedes source completion"
        )
    baseline_rows = _rows_by_source_id(baseline)
    repeat_rows = _rows_by_source_id(repeat)
    changes, unchanged = _compare_rows(
        baseline_rows, repeat_rows, action_kind=action_kind
    )
    changes_values = {
        "contract_version": CHANGES_CONTRACT_VERSION,
        "changes": changes,
    }
    changes_model = CorporateActionSourceRepeatChangesV1.model_validate(
        {
            **changes_values,
            "logical_fingerprint": _fingerprint(changes_values),
        }
    )
    changes_bytes = _pretty_json(changes_model.model_dump(mode="json"))
    if len(changes_bytes) > MAXIMUM_JSON_BYTES:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat change metadata exceeds its byte ceiling"
        )
    changed = tuple(item for item in changes if item.change_type == "changed")
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": MASSIVE_PROVIDER_ID,
        "action_kind": action_kind,
        "start_date": start_date,
        "end_date": end_date,
        "compared_at": compared_at,
        "baseline_manifest_sha256": baseline.manifest_sha256,
        "baseline_logical_fingerprint": baseline.manifest.logical_fingerprint,
        "baseline_started_at": baseline.manifest.started_at,
        "baseline_completed_at": baseline.manifest.completed_at,
        "baseline_request_count": baseline.manifest.request_count,
        "baseline_record_count": baseline.manifest.record_count,
        "baseline_content_fingerprint": _content_fingerprint(baseline_rows),
        "repeat_manifest_sha256": repeat.manifest_sha256,
        "repeat_logical_fingerprint": repeat.manifest.logical_fingerprint,
        "repeat_started_at": repeat.manifest.started_at,
        "repeat_completed_at": repeat.manifest.completed_at,
        "repeat_request_count": repeat.manifest.request_count,
        "repeat_record_count": repeat.manifest.record_count,
        "repeat_content_fingerprint": _content_fingerprint(repeat_rows),
        "all_rows_have_provider_action_id": True,
        "duplicate_provider_action_id_count": 0,
        "unchanged_record_count": unchanged,
        "changed_record_count": len(changed),
        "added_record_count": sum(
            item.change_type == "added" for item in changes
        ),
        "removed_record_count": sum(
            item.change_type == "removed" for item in changes
        ),
        "changed_field_counts": _counts(
            field for item in changed for field in item.changed_fields
        ),
        "effective_date_changed_record_count": sum(
            item.baseline_effective_date != item.repeat_effective_date
            for item in changed
        ),
        "provider_ticker_changed_record_count": sum(
            item.baseline_provider_ticker != item.repeat_provider_ticker
            for item in changed
        ),
        "pagination_shape_changed": (
            tuple(item.row_count for item in baseline.manifest.artifacts)
            != tuple(item.row_count for item in repeat.manifest.artifacts)
        ),
        "changes_file": CHANGES_FILE,
        "changes_file_sha256": _sha256(changes_bytes),
        "changes_file_bytes": len(changes_bytes),
        "changes_logical_fingerprint": changes_model.logical_fingerprint,
        "observation_order_valid": True,
        "revision_interpretation": "observed_snapshot_delta_only",
        "point_in_time_eligibility": "outcome_reconciliation_only",
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "adjustment_ledger_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    manifest = CorporateActionSourceRepeatDiffManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )
    target = _validated_output_target(output_root)
    existing = _read_if_present(target)
    if existing is not None:
        if existing.manifest != manifest or existing.changes != changes:
            raise HistoricalCorporateActionRepeatDiffError(
                "existing repeat diff differs"
            )
        return existing
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff staging target exists"
        )
    staging.mkdir(mode=0o700)
    try:
        changes_path = staging / CHANGES_FILE
        changes_path.write_bytes(changes_bytes)
        _fsync_file(changes_path)
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(_pretty_json(manifest.model_dump(mode="json")))
        _fsync_file(manifest_path)
        changes_path.chmod(0o400)
        manifest_path.chmod(0o400)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink() and staging.parent == target.parent:
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    reread = read_historical_corporate_action_repeat_diff(output_root=target)
    if reread.manifest != manifest or reread.changes != changes:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff formal reread differs"
        )
    return CorporateActionSourceRepeatDiffResult(
        output_root=target,
        manifest=manifest,
        changes=changes,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_historical_corporate_action_repeat_diff(
    *, output_root: Path
) -> CorporateActionSourceRepeatDiffResult:
    """Formally reread one completed repeat-diff report."""

    root = _validated_completed_output(output_root)
    actual = {path.name for path in root.iterdir()}
    if actual != {MANIFEST_FILE, CHANGES_FILE}:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff file set differs"
        )
    manifest_path = root / MANIFEST_FILE
    changes_path = root / CHANGES_FILE
    _require_regular_file(manifest_path, mode=0o400)
    _require_regular_file(changes_path, mode=0o400)
    try:
        manifest = CorporateActionSourceRepeatDiffManifestV1.model_validate_json(
            _read_bounded_bytes(manifest_path)
        )
        changes_model = CorporateActionSourceRepeatChangesV1.model_validate_json(
            _read_bounded_bytes(changes_path)
        )
    except Exception as exc:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff output is invalid"
        ) from exc
    changes_bytes = _read_bounded_bytes(changes_path)
    if (
        _sha256(changes_bytes) != manifest.changes_file_sha256
        or len(changes_bytes) != manifest.changes_file_bytes
        or changes_model.logical_fingerprint != manifest.changes_logical_fingerprint
    ):
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat change artifact binding differs"
        )
    changes = changes_model.changes
    changed = tuple(item for item in changes if item.change_type == "changed")
    expected = {
        "changed_record_count": len(changed),
        "added_record_count": sum(item.change_type == "added" for item in changes),
        "removed_record_count": sum(
            item.change_type == "removed" for item in changes
        ),
        "changed_field_counts": _counts(
            field for item in changed for field in item.changed_fields
        ),
        "effective_date_changed_record_count": sum(
            item.baseline_effective_date != item.repeat_effective_date
            for item in changed
        ),
        "provider_ticker_changed_record_count": sum(
            item.baseline_provider_ticker != item.repeat_provider_ticker
            for item in changed
        ),
    }
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff aggregate differs"
        )
    return CorporateActionSourceRepeatDiffResult(
        output_root=root,
        manifest=manifest,
        changes=changes,
        manifest_sha256=_file_sha256(manifest_path),
        status="already_present",
    )


def _read_source(
    path: Path,
    kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> ValidatedCorporateActionSourcePackage:
    try:
        return read_historical_corporate_action_source_package(
            package_path=path,
            expected_action_kind=kind,
            expected_start_date=start_date,
            expected_end_date=end_date,
        )
    except HistoricalCorporateActionSourceError as exc:
        raise HistoricalCorporateActionRepeatDiffError(
            "corporate-action source package failed formal reread"
        ) from exc


def _rows_by_source_id(
    package: ValidatedCorporateActionSourcePackage,
) -> dict[str, Mapping[str, object]]:
    rows: dict[str, Mapping[str, object]] = {}
    for page in package.pages:
        raw_rows = page.sanitized_response.get("results")
        if not isinstance(raw_rows, list):
            raise HistoricalCorporateActionRepeatDiffError(
                "corporate-action source results changed after reread"
            )
        for row in raw_rows:
            if not isinstance(row, Mapping):
                raise HistoricalCorporateActionRepeatDiffError(
                    "corporate-action source row is not an object"
                )
            source_id = row.get("id")
            if (
                not isinstance(source_id, str)
                or not source_id.strip()
                or source_id != source_id.strip()
            ):
                raise HistoricalCorporateActionRepeatDiffError(
                    "repeat comparison requires every provider action ID"
                )
            if source_id in rows:
                raise HistoricalCorporateActionRepeatDiffError(
                    "repeat comparison contains a duplicate provider action ID"
                )
            rows[source_id] = row
    if len(rows) != package.manifest.record_count:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat comparison source count differs"
        )
    return rows


def _compare_rows(
    baseline: Mapping[str, Mapping[str, object]],
    repeat: Mapping[str, Mapping[str, object]],
    *,
    action_kind: CorporateActionSourceKind,
) -> tuple[tuple[CorporateActionSourceRepeatChangeV1, ...], int]:
    date_field = (
        "execution_date"
        if action_kind is CorporateActionSourceKind.SPLIT
        else "ex_dividend_date"
    )
    changes: list[CorporateActionSourceRepeatChangeV1] = []
    unchanged = 0
    for source_id in sorted(set(baseline) | set(repeat)):
        before = baseline.get(source_id)
        after = repeat.get(source_id)
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
                    key
                    for key in set(before) | set(after)
                    if _value_bytes(before.get(key)) != _value_bytes(after.get(key))
                )
            )
        changes.append(
            CorporateActionSourceRepeatChangeV1(
                source_action_id=source_id,
                change_type=change_type,
                baseline_payload_sha256=before_hash,
                repeat_payload_sha256=after_hash,
                changed_fields=changed_fields,
                baseline_effective_date=(
                    _optional_date(before.get(date_field)) if before is not None else None
                ),
                repeat_effective_date=(
                    _optional_date(after.get(date_field)) if after is not None else None
                ),
                baseline_provider_ticker=(
                    _optional_text(before.get("ticker")) if before is not None else None
                ),
                repeat_provider_ticker=(
                    _optional_text(after.get("ticker")) if after is not None else None
                ),
            )
        )
    ordered = tuple(
        sorted(changes, key=lambda item: (item.change_type, item.source_action_id))
    )
    return ordered, unchanged


def _content_fingerprint(rows: Mapping[str, Mapping[str, object]]) -> str:
    return _fingerprint(
        tuple(
            {
                "source_action_id": source_id,
                "payload_sha256": _fingerprint(rows[source_id]),
            }
            for source_id in sorted(rows)
        )
    )


def _optional_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() == value and value else None


def _validated_output_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff must be below /tmp"
        )
    _reject_symlink_chain(target.parent, tmp)
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff parent is unsafe"
        )
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise HistoricalCorporateActionRepeatDiffError(
                "repeat diff target is unsafe"
            )
    return target


def _validated_completed_output(path: Path) -> Path:
    root = _validated_output_target(path)
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise HistoricalCorporateActionRepeatDiffError(
            "completed repeat diff is unavailable or not owner-only"
        )
    return root


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    current = path.absolute()
    while current != stop:
        if current.exists() and current.is_symlink():
            raise HistoricalCorporateActionRepeatDiffError(
                "path contains a symlink"
            )
        if stop not in current.parents:
            raise HistoricalCorporateActionRepeatDiffError(
                "path escapes its trusted root"
            )
        current = current.parent


def _read_if_present(
    target: Path,
) -> CorporateActionSourceRepeatDiffResult | None:
    if not target.exists() and not target.is_symlink():
        return None
    return read_historical_corporate_action_repeat_diff(output_root=target)


def _require_regular_file(path: Path, *, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalCorporateActionRepeatDiffError(
            "required repeat diff file is missing or unsafe"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or (
        mode is not None and stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalCorporateActionRepeatDiffError(
            "required repeat diff file mode differs"
        )


def _read_bounded_bytes(path: Path) -> bytes:
    _require_regular_file(path)
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise HistoricalCorporateActionRepeatDiffError(
            "repeat diff file size is invalid"
        )
    return path.read_bytes()


def _counts(values: Iterator[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


def _value_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    return _sha256(_value_bytes(value))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalCorporateActionRepeatDiffError(
            "network access is prohibited while building the repeat diff"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
