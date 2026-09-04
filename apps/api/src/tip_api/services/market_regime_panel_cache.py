"""Content-addressed, local-only cache for formally validated Market Regime panels."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
    load_formal_market_regime_panel,
)


PANEL_CACHE_CONTRACT = "market-regime-formal-panel-cache/1.0"
PANEL_CACHE_MANIFEST = "manifest.json"
PANEL_CACHE_BARS = "bars.parquet"
PANEL_CACHE_FILES = {PANEL_CACHE_MANIFEST, PANEL_CACHE_BARS}
PANEL_CACHE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("ticker", pa.string(), nullable=False),
        pa.field("instrument_type", pa.string(), nullable=False),
        pa.field("primary_exchange", pa.string(), nullable=False),
        pa.field("session_date", pa.string(), nullable=False),
        pa.field("open", pa.string(), nullable=False),
        pa.field("high", pa.string(), nullable=False),
        pa.field("low", pa.string(), nullable=False),
        pa.field("close", pa.string(), nullable=False),
        pa.field("volume", pa.string(), nullable=False),
        pa.field("split_adjustment_factor", pa.string(), nullable=False),
        pa.field("dividend_adjustment_factor", pa.string(), nullable=False),
        pa.field("total_return_adjustment_factor", pa.string(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)


class MarketRegimePanelCacheError(RuntimeError):
    """Raised when a panel cache cannot prove its source or local custody."""


class MarketRegimePanelCacheMiss(MarketRegimePanelCacheError):
    """Raised only when the exact content-addressed entry does not exist."""


def write_market_regime_panel_cache(*, cache_root: Path, panel: MarketRegimeInputPanel) -> dict[str, Any]:
    """Write one immutable content-addressed panel entry, or reread an exact existing entry."""

    _validate_panel_for_cache(panel)
    root = _safe_cache_root(cache_root, create=True)
    source_boundary = panel_source_boundary(panel)
    cache_key = _fingerprint({"contract": PANEL_CACHE_CONTRACT, "source_boundary": source_boundary})
    target = root / cache_key
    if target.exists():
        _, manifest = read_market_regime_panel_cache(cache_root=root, expected_source=source_boundary)
        return manifest

    temporary = Path(tempfile.mkdtemp(prefix=f".{cache_key[:12]}-", dir=root))
    temporary.chmod(0o700)
    try:
        rows = [_bar_row(item) for item in sorted(panel.bars, key=lambda row: (row.session_date, str(row.instrument_id)))]
        table = pa.Table.from_pylist(rows, schema=PANEL_CACHE_ARROW_SCHEMA)
        bars_path = temporary / PANEL_CACHE_BARS
        pq.write_table(table, bars_path, compression="zstd", use_dictionary=True)
        with bars_path.open("rb") as handle:
            os.fsync(handle.fileno())
        bars_path.chmod(0o400)
        bars_sha256 = _file_sha256(bars_path)
        logical = {
            "schema_version": "1.0",
            "contract_version": PANEL_CACHE_CONTRACT,
            "cache_key": cache_key,
            "source_boundary": source_boundary,
            "panel": _panel_metadata(panel),
            "bars_file": PANEL_CACHE_BARS,
            "bar_record_count": len(rows),
            "bar_logical_fingerprint": _bar_rows_fingerprint(rows),
            "bars_sha256": bars_sha256,
            "completion_status": "completed",
        }
        manifest = {**logical, "logical_content_fingerprint": _fingerprint(logical)}
        manifest_path = temporary / PANEL_CACHE_MANIFEST
        _write_new(manifest_path, _canonical_bytes(manifest))
        manifest_path.chmod(0o400)
        _fsync_directory(temporary)
        os.rename(temporary, target)
        _fsync_directory(root)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    _, reread = read_market_regime_panel_cache(cache_root=root, expected_source=source_boundary)
    return reread


def read_market_regime_panel_cache(
    *, cache_root: Path, expected_source: Mapping[str, Any]
) -> tuple[MarketRegimeInputPanel, dict[str, Any]]:
    """Reread one exact cache entry selected only by the expected immutable source ledger."""

    source_boundary = normalize_source_boundary(expected_source)
    root = _safe_cache_root(cache_root, create=False)
    cache_key = _fingerprint({"contract": PANEL_CACHE_CONTRACT, "source_boundary": source_boundary})
    target = _safe_entry(root, cache_key)
    manifest = _read_canonical_json(target / PANEL_CACHE_MANIFEST)
    logical = {key: value for key, value in manifest.items() if key != "logical_content_fingerprint"}
    if manifest.get("logical_content_fingerprint") != _fingerprint(logical):
        raise MarketRegimePanelCacheError("panel cache manifest fingerprint mismatch")
    if (
        manifest.get("contract_version") != PANEL_CACHE_CONTRACT
        or manifest.get("cache_key") != cache_key
        or manifest.get("source_boundary") != source_boundary
        or manifest.get("completion_status") != "completed"
        or manifest.get("bars_file") != PANEL_CACHE_BARS
    ):
        raise MarketRegimePanelCacheError("panel cache source binding mismatch")
    bars_path = target / PANEL_CACHE_BARS
    if _file_sha256(bars_path) != manifest.get("bars_sha256"):
        raise MarketRegimePanelCacheError("panel cache bars physical fingerprint mismatch")
    try:
        table = pq.ParquetFile(bars_path).read()
    except Exception as exc:
        raise MarketRegimePanelCacheError("panel cache bars cannot be read") from exc
    if not table.schema.equals(PANEL_CACHE_ARROW_SCHEMA, check_metadata=False):
        raise MarketRegimePanelCacheError("panel cache bars schema mismatch")
    rows = table.to_pylist()
    if len(rows) != manifest.get("bar_record_count") or _bar_rows_fingerprint(rows) != manifest.get(
        "bar_logical_fingerprint"
    ):
        raise MarketRegimePanelCacheError("panel cache bars logical fingerprint mismatch")
    panel_metadata = manifest.get("panel")
    if not isinstance(panel_metadata, Mapping):
        raise MarketRegimePanelCacheError("panel cache metadata is malformed")
    panel = _panel_from_manifest(panel_metadata, rows)
    if panel_source_boundary(panel) != source_boundary:
        raise MarketRegimePanelCacheError("reconstructed panel source boundary mismatch")
    return panel, manifest


def load_market_regime_panel_with_cache(
    *,
    data_root: Path,
    as_of_session: date,
    cache_root: Path | None,
    expected_source: Mapping[str, Any],
) -> tuple[MarketRegimeInputPanel, str, str | None]:
    """Load an exact cache entry or prove the same boundary through the cold reader."""

    expected_boundary = normalize_source_boundary(expected_source)
    if expected_boundary["as_of_session"] != as_of_session.isoformat():
        raise MarketRegimePanelCacheError(
            "panel cache expected source session differs"
        )
    if cache_root is not None and cache_root.exists():
        try:
            panel, manifest = read_market_regime_panel_cache(
                cache_root=cache_root,
                expected_source=expected_boundary,
            )
            return panel, "hit", manifest["logical_content_fingerprint"]
        except MarketRegimePanelCacheMiss:
            pass

    panel = load_formal_market_regime_panel(
        data_root=data_root,
        as_of_session=as_of_session,
    )
    if panel_source_boundary(panel) != expected_boundary:
        raise MarketRegimePanelCacheError(
            "formal panel does not match the expected source boundary"
        )
    if cache_root is None:
        return panel, "disabled", None
    manifest = write_market_regime_panel_cache(cache_root=cache_root, panel=panel)
    return panel, "populated", manifest["logical_content_fingerprint"]


def panel_source_boundary(panel: MarketRegimeInputPanel) -> dict[str, Any]:
    return normalize_source_boundary(
        {
            "as_of_session": panel.as_of_session.isoformat(),
            "history_sessions": [item.isoformat() for item in panel.sessions],
            "history_source_fingerprint": panel.history_source_fingerprint,
            "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
            "identity_logical_fingerprint": panel.identity_logical_fingerprint,
            "eod_content_fingerprint": panel.eod_content_fingerprint,
            "source_sessions": [_source_row(item) for item in panel.source_sessions],
            "universes": [
                {
                    "universe_id": item.universe_id,
                    "catalog_order": item.catalog_order,
                    "is_default": item.is_default,
                    "member_count": len(item.member_ids),
                    "membership_fingerprint": item.membership_fingerprint,
                }
                for item in sorted(panel.universes, key=lambda row: row.catalog_order)
            ],
        }
    )


def normalize_source_boundary(value: Mapping[str, Any]) -> dict[str, Any]:
    """Project a Phase 1a/1b source manifest onto the cache identity boundary."""

    fields = (
        "as_of_session",
        "history_source_fingerprint",
        "activation_pointer_fingerprint",
        "identity_logical_fingerprint",
        "eod_content_fingerprint",
    )
    if not isinstance(value, Mapping) or not isinstance(value.get("as_of_session"), str):
        raise MarketRegimePanelCacheError("panel cache expected source is incomplete")
    if any(not _is_fingerprint(value.get(name)) for name in fields[1:]):
        raise MarketRegimePanelCacheError("panel cache expected source has malformed fingerprints")
    history_sessions = value.get("history_sessions")
    source_sessions = value.get("source_sessions")
    universes = value.get("universes")
    try:
        parsed_history_sessions = [date.fromisoformat(item) for item in history_sessions]
    except (TypeError, ValueError):
        raise MarketRegimePanelCacheError("panel cache history sessions are malformed") from None
    if (
        not isinstance(history_sessions, list)
        or len(history_sessions) != 26
        or history_sessions != sorted(history_sessions)
        or len(set(history_sessions)) != 26
        or history_sessions[-1] != value["as_of_session"]
        or not isinstance(source_sessions, list)
        or len(source_sessions) != 26
        or not isinstance(universes, list)
        or not universes
    ):
        raise MarketRegimePanelCacheError("panel cache requires one exact 26-session source ledger")
    if [item.isoformat() for item in parsed_history_sessions] != history_sessions:
        raise MarketRegimePanelCacheError("panel cache history sessions are not canonical dates")
    normalized_sources = [
        {
            "session_date": item.get("session_date"),
            "dataset_path": item.get("dataset_path"),
            "record_count": item.get("record_count"),
            "content_fingerprint": item.get("content_fingerprint"),
            "parquet_sha256": item.get("parquet_sha256"),
            "identity_snapshot_date": item.get("identity_snapshot_date"),
            "identity_snapshot_fingerprint": item.get("identity_snapshot_fingerprint"),
        }
        for item in source_sessions
        if isinstance(item, Mapping)
    ]
    normalized_universes = [
        {
            "universe_id": item.get("universe_id"),
            "catalog_order": item.get("catalog_order"),
            "is_default": item.get("is_default"),
            "member_count": item.get("member_count"),
            "membership_fingerprint": item.get("membership_fingerprint"),
        }
        for item in universes
        if isinstance(item, Mapping)
    ]
    try:
        parsed_source_dates = [date.fromisoformat(item["session_date"]) for item in normalized_sources]
        parsed_identity_dates = [date.fromisoformat(item["identity_snapshot_date"]) for item in normalized_sources]
    except (TypeError, ValueError):
        raise MarketRegimePanelCacheError("panel cache source dates are malformed") from None
    try:
        unique_universe_count = len({item["universe_id"] for item in normalized_universes})
    except TypeError:
        raise MarketRegimePanelCacheError("panel cache Universe ledger is malformed") from None
    if (
        len(normalized_sources) != 26
        or [item["session_date"] for item in normalized_sources] != history_sessions
        or [item.isoformat() for item in parsed_source_dates] != history_sessions
        or any(identity_date > source_date for identity_date, source_date in zip(parsed_identity_dates, parsed_source_dates))
        or len(normalized_universes) != len(universes)
        or [item["catalog_order"] for item in normalized_universes]
        != list(range(len(normalized_universes)))
        or unique_universe_count != len(normalized_universes)
        or any(
            not isinstance(item["record_count"], int)
            or isinstance(item["record_count"], bool)
            or item["record_count"] < 0
            or not isinstance(item["dataset_path"], str)
            or not item["dataset_path"]
            or not _is_fingerprint(item["content_fingerprint"])
            or not _is_fingerprint(item["parquet_sha256"])
            or not _is_fingerprint(item["identity_snapshot_fingerprint"])
            for item in normalized_sources
        )
        or any(
            not isinstance(item["universe_id"], str)
            or not item["universe_id"]
            or not isinstance(item["catalog_order"], int)
            or isinstance(item["catalog_order"], bool)
            or not isinstance(item["is_default"], bool)
            or not isinstance(item["member_count"], int)
            or isinstance(item["member_count"], bool)
            or item["member_count"] < 1
            or not _is_fingerprint(item["membership_fingerprint"])
            for item in normalized_universes
        )
    ):
        raise MarketRegimePanelCacheError("panel cache expected ledger fields are malformed")
    return {
        **{name: value[name] for name in fields},
        "history_sessions": list(history_sessions),
        "source_sessions": normalized_sources,
        "universes": normalized_universes,
    }


def _panel_metadata(panel: MarketRegimeInputPanel) -> dict[str, Any]:
    return {
        "as_of_session": panel.as_of_session.isoformat(),
        "calendar_id": panel.calendar_id,
        "calendar_version": panel.calendar_version,
        "sessions": [item.isoformat() for item in panel.sessions],
        "source_sessions": [_source_row(item) for item in panel.source_sessions],
        "universes": [
            {
                "universe_id": item.universe_id,
                "display_name": item.display_name,
                "is_default": item.is_default,
                "catalog_order": item.catalog_order,
                "member_ids": [str(value) for value in sorted(item.member_ids, key=str)],
                "membership_fingerprint": item.membership_fingerprint,
            }
            for item in sorted(panel.universes, key=lambda row: row.catalog_order)
        ],
        "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
        "identity_logical_fingerprint": panel.identity_logical_fingerprint,
        "eod_content_fingerprint": panel.eod_content_fingerprint,
        "eod_business_key_fingerprint": panel.eod_business_key_fingerprint,
        "history_source_fingerprint": panel.history_source_fingerprint,
    }


def _validate_panel_for_cache(panel: MarketRegimeInputPanel) -> None:
    if not isinstance(panel, MarketRegimeInputPanel):
        raise MarketRegimePanelCacheError("panel cache input has the wrong type")
    if tuple(item.session_date for item in panel.source_sessions) != panel.sessions:
        raise MarketRegimePanelCacheError("panel cache input source sessions do not align")
    bar_keys = tuple((item.instrument_id, item.session_date) for item in panel.bars)
    if (
        not panel.bars
        or len(set(bar_keys)) != len(bar_keys)
        or any(item.session_date not in panel.sessions for item in panel.bars)
        or any(not item.member_ids for item in panel.universes)
    ):
        raise MarketRegimePanelCacheError("panel cache input is not a unique complete session panel")


def _panel_from_manifest(value: Mapping[str, Any], rows: list[dict[str, Any]]) -> MarketRegimeInputPanel:
    try:
        source_sessions = tuple(
            MarketRegimeSourceSession(
                session_date=date.fromisoformat(item["session_date"]),
                dataset_path=item["dataset_path"],
                record_count=item["record_count"],
                content_fingerprint=item["content_fingerprint"],
                parquet_sha256=item["parquet_sha256"],
                identity_snapshot_date=date.fromisoformat(item["identity_snapshot_date"]),
                identity_snapshot_fingerprint=item["identity_snapshot_fingerprint"],
            )
            for item in value["source_sessions"]
        )
        universes = tuple(
            MarketRegimeUniverseSource(
                universe_id=item["universe_id"],
                display_name=item["display_name"],
                is_default=item["is_default"],
                catalog_order=item["catalog_order"],
                member_ids=frozenset(UUID(member) for member in item["member_ids"]),
                membership_fingerprint=item["membership_fingerprint"],
            )
            for item in value["universes"]
        )
        bars = tuple(_bar_from_row(item) for item in rows)
        panel = MarketRegimeInputPanel(
            as_of_session=date.fromisoformat(value["as_of_session"]),
            calendar_id=value["calendar_id"],
            calendar_version=value["calendar_version"],
            sessions=tuple(date.fromisoformat(item) for item in value["sessions"]),
            source_sessions=source_sessions,
            bars=bars,
            universes=universes,
            activation_pointer_fingerprint=value["activation_pointer_fingerprint"],
            identity_logical_fingerprint=value["identity_logical_fingerprint"],
            eod_content_fingerprint=value["eod_content_fingerprint"],
            eod_business_key_fingerprint=value["eod_business_key_fingerprint"],
            history_source_fingerprint=value["history_source_fingerprint"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MarketRegimePanelCacheError("panel cache metadata is malformed") from exc
    if tuple(item.session_date for item in source_sessions) != panel.sessions:
        raise MarketRegimePanelCacheError("panel cache source sessions do not align")
    if tuple(sorted(bars, key=lambda item: (item.session_date, str(item.instrument_id)))) != bars:
        raise MarketRegimePanelCacheError("panel cache bars are not canonically ordered")
    bar_keys = tuple((item.instrument_id, item.session_date) for item in bars)
    if len(set(bar_keys)) != len(bar_keys) or any(item.session_date not in panel.sessions for item in bars):
        raise MarketRegimePanelCacheError("panel cache bars do not form a unique session panel")
    if any(len(item.member_ids) == 0 for item in universes):
        raise MarketRegimePanelCacheError("panel cache Universe is empty")
    return panel


def _source_row(item: MarketRegimeSourceSession) -> dict[str, Any]:
    return {
        "session_date": item.session_date.isoformat(),
        "dataset_path": item.dataset_path,
        "record_count": item.record_count,
        "content_fingerprint": item.content_fingerprint,
        "parquet_sha256": item.parquet_sha256,
        "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
        "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint,
    }


def _bar_row(item: MarketRegimeBar) -> dict[str, Any]:
    return {
        "instrument_id": str(item.instrument_id),
        "ticker": item.ticker,
        "instrument_type": item.instrument_type,
        "primary_exchange": item.primary_exchange,
        "session_date": item.session_date.isoformat(),
        "open": str(item.open),
        "high": str(item.high),
        "low": str(item.low),
        "close": str(item.close),
        "volume": str(item.volume),
        "split_adjustment_factor": str(item.split_adjustment_factor),
        "dividend_adjustment_factor": str(item.dividend_adjustment_factor),
        "total_return_adjustment_factor": str(item.total_return_adjustment_factor),
        "quality_status": item.quality_status,
        "quality_flags": list(item.quality_flags),
    }


def _bar_from_row(item: Mapping[str, Any]) -> MarketRegimeBar:
    try:
        return MarketRegimeBar(
            instrument_id=UUID(item["instrument_id"]),
            ticker=item["ticker"],
            instrument_type=item["instrument_type"],
            primary_exchange=item["primary_exchange"],
            session_date=date.fromisoformat(item["session_date"]),
            open=Decimal(item["open"]),
            high=Decimal(item["high"]),
            low=Decimal(item["low"]),
            close=Decimal(item["close"]),
            volume=Decimal(item["volume"]),
            split_adjustment_factor=Decimal(item["split_adjustment_factor"]),
            dividend_adjustment_factor=Decimal(item["dividend_adjustment_factor"]),
            total_return_adjustment_factor=Decimal(item["total_return_adjustment_factor"]),
            quality_status=item["quality_status"],
            quality_flags=tuple(item["quality_flags"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MarketRegimePanelCacheError("panel cache bar is malformed") from exc


def _bar_rows_fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical_bytes(row))
    return digest.hexdigest()


def _safe_cache_root(cache_root: Path, *, create: bool) -> Path:
    if not cache_root.is_absolute() or cache_root.name in {"", ".", ".."}:
        raise MarketRegimePanelCacheError("panel cache root must be absolute")
    current = Path("/")
    for part in cache_root.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise MarketRegimePanelCacheError("panel cache path contains a symlink")
    if not cache_root.exists():
        if not create or not cache_root.parent.is_dir():
            raise MarketRegimePanelCacheError("panel cache root is unavailable")
        cache_root.mkdir(mode=0o700)
    root = cache_root.resolve(strict=True)
    metadata = root.stat()
    if not root.is_dir() or metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MarketRegimePanelCacheError("panel cache root custody mismatch")
    return root


def _safe_entry(root: Path, cache_key: str) -> Path:
    target = root / cache_key
    if target.is_symlink():
        raise MarketRegimePanelCacheError("panel cache entry is unavailable")
    if not target.exists():
        raise MarketRegimePanelCacheMiss("exact panel cache entry is absent")
    if target.is_symlink() or not target.is_dir() or target.resolve().parent != root:
        raise MarketRegimePanelCacheError("panel cache entry is unavailable")
    metadata = target.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MarketRegimePanelCacheError("panel cache entry custody mismatch")
    if {item.name for item in target.iterdir()} != PANEL_CACHE_FILES or any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise MarketRegimePanelCacheError("panel cache file set is unsafe")
    return target


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(_normalize_nfc(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list | tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", str(key)): _normalize_nfc(item) for key, item in value.items()}
    return value


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise MarketRegimePanelCacheError("panel cache manifest is malformed") from exc
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise MarketRegimePanelCacheError("panel cache manifest is not canonical")
    return value


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
