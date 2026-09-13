"""Network-free candidate corroboration census across FINRA and Massive."""

from __future__ import annotations

import calendar
import hashlib
import json
import os
import stat
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.finra_otc_daily_list_source import (
    read_finra_otc_daily_list_source_payloads,
)
from tip_api.services.finra_otc_daily_list_range_census import (
    read_sealed_finra_otc_daily_list_range_census,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    read_historical_corporate_action_source_package,
)


CONTRACT_VERSION = "finra-massive-action-cross-source-census/1.0"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_MAXIMUM_OUTPUT_BYTES = 1024 * 1024
_SEMANTIC_FIELDS = (
    "bankruptcyFlag",
    "cashAmountText",
    "changeSecurityAttributeFlag",
    "changeSecurityDescriptionFlag",
    "changeSymbolFlag",
    "declarationDate",
    "exDate",
    "forwardSplitRate",
    "newSymbolCode",
    "oldSymbolCode",
    "paymentDate",
    "recordDate",
    "reverseSplitRate",
    "securityAddFlag",
    "securityDeleteFlag",
    "subjectCorporateActionCode",
)
_FLAG_FIELDS = (
    "bankruptcyFlag",
    "changeSecurityAttributeFlag",
    "changeSecurityDescriptionFlag",
    "changeSymbolFlag",
    "securityAddFlag",
    "securityDeleteFlag",
)


class FinraMassiveActionCrossSourceCensusError(RuntimeError):
    """Raised when cross-source facts cannot be reconciled conservatively."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceBindingV1(_FrozenModel):
    provider_id: Literal["finra_otc_daily_list", "massive_stocks_basic"]
    family: Literal["otc_daily_list", "split", "dividend"]
    range_start: date
    range_end: date
    package_count: int = Field(ge=1)
    record_count: int = Field(ge=0)
    manifest_chain_fingerprint: str = Field(pattern=_SHA256_PATTERN)


class ActionFamilyCensusV1(_FrozenModel):
    family: Literal["split", "dividend"]
    numeric_semantics: Literal[
        "ratio_candidate_only",
        "amount_candidate_only_currency_unverified",
    ]
    finra_observation_count: int = Field(ge=0)
    event_code_counts: tuple[tuple[str, int], ...]
    effective_date_in_scope_count: int = Field(ge=0)
    effective_date_outside_or_invalid_count: int = Field(ge=0)
    candidate_key_none_count: int = Field(ge=0)
    candidate_key_unique_count: int = Field(ge=0)
    candidate_key_ambiguous_count: int = Field(ge=0)
    numeric_match_none_count: int = Field(ge=0)
    numeric_match_unique_count: int = Field(ge=0)
    numeric_match_ambiguous_count: int = Field(ge=0)
    invalid_finra_numeric_count: int = Field(ge=0)
    unique_key_numeric_equal_count: int = Field(ge=0)
    unique_key_numeric_disagree_count: int = Field(ge=0)
    ambiguous_key_unique_numeric_count: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_reconcile(self) -> "ActionFamilyCensusV1":
        total = self.finra_observation_count
        if self.effective_date_in_scope_count + self.effective_date_outside_or_invalid_count != total:
            raise ValueError("effective-date counts differ")
        if (
            self.candidate_key_none_count
            + self.candidate_key_unique_count
            + self.candidate_key_ambiguous_count
            != total
        ):
            raise ValueError("candidate-key counts differ")
        if (
            self.numeric_match_none_count
            + self.numeric_match_unique_count
            + self.numeric_match_ambiguous_count
            != total
        ):
            raise ValueError("numeric-match counts differ")
        if (
            self.unique_key_numeric_equal_count
            + self.unique_key_numeric_disagree_count
            != self.candidate_key_unique_count
        ):
            raise ValueError("unique-key numeric counts differ")
        if self.ambiguous_key_unique_numeric_count > self.candidate_key_ambiguous_count:
            raise ValueError("ambiguous-key refinement count differs")
        return self


class FinraMassiveActionCrossSourceCensusV1(_FrozenModel):
    contract_version: Literal[
        "finra-massive-action-cross-source-census/1.0"
    ] = CONTRACT_VERSION
    range_start: date
    range_end: date
    evaluated_at: datetime
    evidence_role: Literal["candidate_corroboration_only"] = (
        "candidate_corroboration_only"
    )
    source_event_semantics: Literal[
        "opaque_provider_codes_no_state_inference"
    ] = "opaque_provider_codes_no_state_inference"
    candidate_key_semantics: Literal[
        "exact_effective_date_and_old_or_new_finra_symbol_to_massive_ticker"
    ] = "exact_effective_date_and_old_or_new_finra_symbol_to_massive_ticker"
    source_bindings: tuple[SourceBindingV1, ...] = Field(min_length=3, max_length=3)
    finra_record_count: int = Field(ge=0)
    finra_event_code_counts: tuple[tuple[str, int], ...]
    semantic_field_presence_counts: tuple[tuple[str, int], ...]
    flag_value_counts: tuple[tuple[str, str, int], ...]
    split: ActionFamilyCensusV1
    dividend: ActionFamilyCensusV1
    non_action_observation_count: int = Field(ge=0)
    overlapping_action_family_count: int = Field(ge=0)
    stable_identity_resolution_count: Literal[0] = 0
    canonical_action_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
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
    def census_reconciles(self) -> "FinraMassiveActionCrossSourceCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("cross-source range is reversed")
        if tuple((item.provider_id, item.family) for item in self.source_bindings) != (
            ("finra_otc_daily_list", "otc_daily_list"),
            ("massive_stocks_basic", "split"),
            ("massive_stocks_basic", "dividend"),
        ):
            raise ValueError("cross-source bindings differ")
        if self.split.family != "split" or self.dividend.family != "dividend":
            raise ValueError("cross-source family placement differs")
        if (
            self.split.finra_observation_count
            + self.dividend.finra_observation_count
            + self.non_action_observation_count
            - self.overlapping_action_family_count
            != self.finra_record_count
        ):
            raise ValueError("FINRA source population differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("cross-source census fingerprint differs")
        return self


def census_finra_massive_action_sources(
    *,
    finra_custody_root: Path,
    massive_custody_root: Path,
    range_start: date,
    range_end: date,
    evaluated_at: datetime | None = None,
) -> FinraMassiveActionCrossSourceCensusV1:
    """Reread exact source packages and measure candidate-level agreement."""

    if range_end < range_start:
        raise FinraMassiveActionCrossSourceCensusError("source range is reversed")
    sealed_finra = read_sealed_finra_otc_daily_list_range_census(
        custody_root=finra_custody_root,
        range_start=range_start,
        range_end=range_end,
    )
    finra_rows: list[dict[str, object]] = []
    finra_chain_items: list[tuple[object, ...]] = []
    for start, end in _monthly_partitions(range_start, range_end):
        package_name = f"period={start.isoformat()}--{end.isoformat()}"
        validated = read_finra_otc_daily_list_source_payloads(
            package_path=finra_custody_root / package_name,
            expected_partition_start=start,
            expected_partition_end=end,
            approved_custody_root=finra_custody_root,
        )
        manifest = validated.manifest
        finra_chain_items.append(
            (
                package_name,
                validated.manifest_sha256,
                manifest.logical_fingerprint,
                manifest.record_count,
                manifest.request_count,
                manifest.data_version,
            )
        )
        for page in validated.pages:
            finra_rows.extend(dict(row) for row in page.rows)
    finra_chain = _fingerprint(tuple(finra_chain_items))
    if (
        len(finra_rows) != sealed_finra.record_count
        or finra_chain != sealed_finra.package_chain_fingerprint
    ):
        raise FinraMassiveActionCrossSourceCensusError(
            "FINRA range differs from its sealed census"
        )

    massive_packages = {
        kind: read_historical_corporate_action_source_package(
            package_path=massive_custody_root
            / f"{kind.value}={range_start.isoformat()}_{range_end.isoformat()}",
            expected_action_kind=kind,
            expected_start_date=range_start,
            expected_end_date=range_end,
            approved_custody_root=massive_custody_root,
        )
        for kind in (CorporateActionSourceKind.SPLIT, CorporateActionSourceKind.DIVIDEND)
    }
    massive_rows = {
        kind: tuple(
            row
            for page in package.pages
            for row in _response_rows(page.sanitized_response)
        )
        for kind, package in massive_packages.items()
    }

    event_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    flag_counts: Counter[tuple[str, str]] = Counter()
    split_rows: list[dict[str, object]] = []
    dividend_rows: list[dict[str, object]] = []
    non_action = 0
    overlapping = 0
    for row in finra_rows:
        code = _code(row.get("dailyListEventCode"))
        event_counts[code] += 1
        for field in _SEMANTIC_FIELDS:
            if _present(row.get(field)):
                field_counts[field] += 1
        for field in _FLAG_FIELDS:
            value = _code(row.get(field))
            flag_counts[(field, value)] += 1
        is_split = _present(row.get("forwardSplitRate")) or _present(
            row.get("reverseSplitRate")
        )
        is_dividend = _present(row.get("cashAmountText"))
        if is_split:
            split_rows.append(row)
        if is_dividend:
            dividend_rows.append(row)
        if is_split and is_dividend:
            overlapping += 1
        if not is_split and not is_dividend:
            non_action += 1

    split_census = _family_census(
        family="split",
        finra_rows=split_rows,
        massive_rows=massive_rows[CorporateActionSourceKind.SPLIT],
        range_start=range_start,
        range_end=range_end,
    )
    dividend_census = _family_census(
        family="dividend",
        finra_rows=dividend_rows,
        massive_rows=massive_rows[CorporateActionSourceKind.DIVIDEND],
        range_start=range_start,
        range_end=range_end,
    )
    bindings = (
        SourceBindingV1(
            provider_id="finra_otc_daily_list",
            family="otc_daily_list",
            range_start=range_start,
            range_end=range_end,
            package_count=sealed_finra.package_count,
            record_count=sealed_finra.record_count,
            manifest_chain_fingerprint=finra_chain,
        ),
        *(
            SourceBindingV1(
                provider_id="massive_stocks_basic",
                family=kind.value,
                range_start=range_start,
                range_end=range_end,
                package_count=1,
                record_count=package.manifest.record_count,
                manifest_chain_fingerprint=_fingerprint(
                    (
                        package.manifest_sha256,
                        package.manifest.logical_fingerprint,
                        package.manifest.record_count,
                    )
                ),
            )
            for kind, package in massive_packages.items()
        ),
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "range_start": range_start,
        "range_end": range_end,
        "evaluated_at": normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
        "evidence_role": "candidate_corroboration_only",
        "source_event_semantics": "opaque_provider_codes_no_state_inference",
        "candidate_key_semantics": (
            "exact_effective_date_and_old_or_new_finra_symbol_to_massive_ticker"
        ),
        "source_bindings": bindings,
        "finra_record_count": len(finra_rows),
        "finra_event_code_counts": tuple(sorted(event_counts.items())),
        "semantic_field_presence_counts": tuple(
            (field, field_counts[field]) for field in _SEMANTIC_FIELDS
        ),
        "flag_value_counts": tuple(
            (field, value, count)
            for (field, value), count in sorted(flag_counts.items())
        ),
        "split": split_census,
        "dividend": dividend_census,
        "non_action_observation_count": non_action,
        "overlapping_action_family_count": overlapping,
        "stable_identity_resolution_count": 0,
        "canonical_action_write_count": 0,
        "adjustment_ledger_write_count": 0,
        "network_request_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return FinraMassiveActionCrossSourceCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def seal_finra_massive_action_cross_source_census(
    *, output_root: Path, census: FinraMassiveActionCrossSourceCensusV1
) -> Path:
    root = _validate_output_root(output_root)
    target = root / (
        f"census={census.range_start.isoformat()}--{census.range_end.isoformat()}.json"
    )
    raw = _json_bytes(census.model_dump(mode="json")) + b"\n"
    if len(raw) > _MAXIMUM_OUTPUT_BYTES:
        raise FinraMassiveActionCrossSourceCensusError("census exceeds byte ceiling")
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


def read_sealed_finra_massive_action_cross_source_census(
    *, output_root: Path, range_start: date, range_end: date
) -> FinraMassiveActionCrossSourceCensusV1:
    root = _validate_output_root(output_root)
    target = root / f"census={range_start.isoformat()}--{range_end.isoformat()}.json"
    if target.is_symlink() or not target.is_file():
        raise FinraMassiveActionCrossSourceCensusError("sealed census is unavailable")
    metadata = target.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise FinraMassiveActionCrossSourceCensusError("sealed census mode differs")
    if metadata.st_size < 1 or metadata.st_size > _MAXIMUM_OUTPUT_BYTES:
        raise FinraMassiveActionCrossSourceCensusError("sealed census size differs")
    try:
        result = FinraMassiveActionCrossSourceCensusV1.model_validate_json(
            target.read_bytes()
        )
    except Exception as exc:
        raise FinraMassiveActionCrossSourceCensusError("sealed census is invalid") from exc
    if result.range_start != range_start or result.range_end != range_end:
        raise FinraMassiveActionCrossSourceCensusError("sealed census range differs")
    return result


def _family_census(
    *,
    family: Literal["split", "dividend"],
    finra_rows: list[dict[str, object]],
    massive_rows: tuple[dict[str, object], ...],
    range_start: date,
    range_end: date,
) -> ActionFamilyCensusV1:
    index: defaultdict[
        tuple[date, str], list[tuple[int, dict[str, object]]]
    ] = defaultdict(list)
    for occurrence, row in enumerate(massive_rows, 1):
        effective = _date_value(
            row.get("execution_date" if family == "split" else "ex_dividend_date")
        )
        ticker = _symbol(row.get("ticker"))
        if effective is None or ticker is None:
            raise FinraMassiveActionCrossSourceCensusError(
                "validated Massive action key is malformed"
            )
        index[(effective, ticker)].append((occurrence, row))

    counts: Counter[str] = Counter()
    events: Counter[str] = Counter()
    for row in finra_rows:
        counts["total"] += 1
        events[_code(row.get("dailyListEventCode"))] += 1
        effective = _date_value(row.get("exDate"))
        if effective is not None and range_start <= effective <= range_end:
            counts["effective_in"] += 1
        else:
            counts["effective_out"] += 1
        symbols = {
            value
            for value in (
                _symbol(row.get("oldSymbolCode")),
                _symbol(row.get("newSymbolCode")),
            )
            if value is not None
        }
        candidates = {
            occurrence: candidate
            for symbol in symbols
            for occurrence, candidate in index.get((effective, symbol), ())
        }
        key_state = "none" if not candidates else "unique" if len(candidates) == 1 else "ambiguous"
        counts[f"key_{key_state}"] += 1
        finra_values = _finra_numeric_values(row, family)
        if not finra_values:
            counts["invalid_numeric"] += 1
        matches = [
            candidate
            for candidate in candidates.values()
            if _massive_numeric_value(candidate, family) in finra_values
        ]
        numeric_state = "none" if not matches else "unique" if len(matches) == 1 else "ambiguous"
        counts[f"numeric_{numeric_state}"] += 1
        if key_state == "unique":
            counts[
                "unique_key_equal" if numeric_state == "unique" else "unique_key_disagree"
            ] += 1
        if key_state == "ambiguous" and numeric_state == "unique":
            counts["ambiguous_key_unique_numeric"] += 1

    return ActionFamilyCensusV1(
        family=family,
        numeric_semantics=(
            "ratio_candidate_only"
            if family == "split"
            else "amount_candidate_only_currency_unverified"
        ),
        finra_observation_count=counts["total"],
        event_code_counts=tuple(sorted(events.items())),
        effective_date_in_scope_count=counts["effective_in"],
        effective_date_outside_or_invalid_count=counts["effective_out"],
        candidate_key_none_count=counts["key_none"],
        candidate_key_unique_count=counts["key_unique"],
        candidate_key_ambiguous_count=counts["key_ambiguous"],
        numeric_match_none_count=counts["numeric_none"],
        numeric_match_unique_count=counts["numeric_unique"],
        numeric_match_ambiguous_count=counts["numeric_ambiguous"],
        invalid_finra_numeric_count=counts["invalid_numeric"],
        unique_key_numeric_equal_count=counts["unique_key_equal"],
        unique_key_numeric_disagree_count=counts["unique_key_disagree"],
        ambiguous_key_unique_numeric_count=counts["ambiguous_key_unique_numeric"],
    )


def _finra_numeric_values(
    row: dict[str, object], family: Literal["split", "dividend"]
) -> frozenset[object]:
    if family == "dividend":
        value = _decimal(row.get("cashAmountText"))
        return frozenset(() if value is None else (value,))
    values: set[object] = set()
    for field in ("forwardSplitRate", "reverseSplitRate"):
        raw = row.get(field)
        if not _present(raw):
            continue
        parts = str(raw).strip().split(":")
        if len(parts) != 2:
            continue
        split_to, split_from = _decimal(parts[0]), _decimal(parts[1])
        if (
            split_from is not None
            and split_to is not None
            and split_from > 0
            and split_to > 0
        ):
            values.add((split_from, split_to))
    return frozenset(values)


def _massive_numeric_value(
    row: dict[str, object], family: Literal["split", "dividend"]
) -> object:
    if family == "dividend":
        return _decimal(row.get("cash_amount"))
    return (_decimal(row.get("split_from")), _decimal(row.get("split_to")))


def _response_rows(response: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows = response.get("results")
    if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
        raise FinraMassiveActionCrossSourceCensusError("Massive results are malformed")
    return tuple(dict(item) for item in rows)


def _monthly_partitions(start: date, end: date) -> tuple[tuple[date, date], ...]:
    values: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        partition_end = min(last, end)
        values.append((cursor, partition_end))
        cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
    return tuple(values)


def _date_value(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _symbol(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    result = value.strip().upper()
    return result or None


def _code(value: object) -> str:
    if not isinstance(value, str):
        return "<missing>"
    result = value.strip().upper()
    return result or "<missing>"


def _present(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _validate_output_root(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise FinraMassiveActionCrossSourceCensusError("output root is unsafe")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise FinraMassiveActionCrossSourceCensusError("output root mode differs")
    return root


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
