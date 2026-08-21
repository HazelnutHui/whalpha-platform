"""Manifest and fingerprint helpers for EOD Price Bar Parquet partitions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from tip_api.contracts.market_data.v1 import EodPriceBarV1

MANIFEST_VERSION = "1.0"
DATASET_NAME = "eod-price-bars"
PARQUET_FILE_NAME = "part-00000.parquet"
MANIFEST_FILE_NAME = "manifest.json"
COMPLETION_STATUS = "completed"


def sort_eod_bars(records: tuple[EodPriceBarV1, ...]) -> tuple[EodPriceBarV1, ...]:
    """Sort records by the canonical EOD bar ordering contract."""

    return tuple(
        sorted(
            records,
            key=lambda record: (
                str(record.instrument_id),
                record.session_date.isoformat(),
                record.source,
                record.revision,
            ),
        )
    )


def record_business_key(record: EodPriceBarV1) -> tuple[str, str, str, int]:
    """Return the canonical business key used for duplicate detection."""

    return (str(record.instrument_id), record.session_date.isoformat(), record.source, record.revision)


def logical_revision_key(record: EodPriceBarV1) -> tuple[str, str, str]:
    """Return the source-level logical record key across revisions."""

    return (str(record.instrument_id), record.session_date.isoformat(), record.source)


def decimal_to_string(value: Decimal | None) -> str | None:
    """Represent a finite Decimal canonically without consulting its context."""

    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("fingerprint Decimal must be finite")
    sign, raw_digits, exponent = value.as_tuple()
    digits = "".join(str(digit) for digit in raw_digits).lstrip("0")
    if not digits:
        return "-0" if sign else "0"
    # Numeric equivalence, including trailing fractional zeroes, is part of the
    # historical fingerprint contract.  Canonicalize the coefficient directly;
    # Decimal.normalize() is unsuitable because it obeys the process context.
    trailing_zero_count = len(digits) - len(digits.rstrip("0"))
    if trailing_zero_count:
        digits = digits[:-trailing_zero_count]
        exponent += trailing_zero_count
    if exponent >= 0:
        rendered = digits + ("0" * exponent)
    else:
        point = len(digits) + exponent
        rendered = (
            digits[:point] + "." + digits[point:]
            if point > 0
            else "0." + ("0" * -point) + digits
        )
    return ("-" if sign else "") + rendered


def record_to_fingerprint_row(record: EodPriceBarV1) -> dict[str, Any]:
    """Convert a canonical record to a stable JSON-compatible row."""

    return {
        "instrument_id": str(record.instrument_id),
        "session_date": record.session_date.isoformat(),
        "open": decimal_to_string(record.open),
        "high": decimal_to_string(record.high),
        "low": decimal_to_string(record.low),
        "close": decimal_to_string(record.close),
        "volume": decimal_to_string(record.volume),
        "vwap": decimal_to_string(record.vwap),
        "trade_count": record.trade_count,
        "notional": decimal_to_string(record.notional),
        "currency": record.currency,
        "split_adjustment_factor": decimal_to_string(record.split_adjustment_factor),
        "dividend_adjustment_factor": decimal_to_string(record.dividend_adjustment_factor),
        "total_return_adjustment_factor": decimal_to_string(record.total_return_adjustment_factor),
        "adjusted_close": decimal_to_string(record.adjusted_close),
        "source": record.source,
        "source_record_id": record.source_record_id,
        "ingested_at": record.ingested_at.astimezone(UTC).isoformat(),
        "revision": record.revision,
        "is_latest_revision": record.is_latest_revision,
        "quality_status": record.quality_status.value,
        "quality_flags": list(record.quality_flags),
        "schema_version": record.schema_version,
    }


def content_fingerprint(records: tuple[EodPriceBarV1, ...]) -> str:
    """Return an input-order-independent SHA-256 fingerprint for canonical records."""

    rows = [record_to_fingerprint_row(record) for record in sort_eod_bars(records)]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def table_rows_fingerprint(rows: list[dict[str, Any]]) -> str:
    """Return a SHA-256 fingerprint for rows read back from Parquet."""

    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    schema_version: str,
    session_date: date,
    provider_id: str,
    record_count: int,
    content_sha256: str,
    parquet_file: str,
    created_at: datetime,
    records: tuple[EodPriceBarV1, ...],
    quality_summary: dict[str, Any] | None = None,
    identity_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build non-sensitive manifest metadata for a completed partition."""

    sorted_records = sort_eod_bars(records)
    quality_counts: dict[str, int] = {}
    for record in sorted_records:
        quality_counts[record.quality_status.value] = quality_counts.get(record.quality_status.value, 0) + 1

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "dataset_name": DATASET_NAME,
        "schema_version": schema_version,
        "session_date": session_date.isoformat(),
        "provider_id": provider_id,
        "record_count": record_count,
        "minimum_instrument_id": str(sorted_records[0].instrument_id),
        "maximum_instrument_id": str(sorted_records[-1].instrument_id),
        "minimum_session_date": session_date.isoformat(),
        "maximum_session_date": session_date.isoformat(),
        "content_sha256": content_sha256,
        "parquet_file": parquet_file,
        "created_at": created_at.astimezone(UTC).isoformat(),
        "quality_summary": quality_summary or quality_counts,
        "completion_status": COMPLETION_STATUS,
    }
    if identity_snapshot is not None:
        manifest["identity_snapshot"] = identity_snapshot
    return manifest


def write_manifest_atomic(path: Path, manifest: dict[str, Any]) -> None:
    """Write a manifest using a same-directory temporary file and atomic rename."""

    tmp_path = path.with_name(f".{path.name}.tmp")
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    tmp_path.write_text(payload, encoding="utf-8")
    with tmp_path.open("rb") as handle:
        import os

        os.fsync(handle.fileno())
    tmp_path.replace(path)
