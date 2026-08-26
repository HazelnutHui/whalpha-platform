from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tip_api.persistence.eod_read import EodDatasetUnavailableError
from tip_api.persistence.parquet.eod_bars import _table_to_fingerprint_rows
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.manifest import table_rows_fingerprint
from tests.support.eod_read_dataset import SESSION_DATE, eod_manifest_path, publish_completed_eod_dataset


def test_history_read_validates_integrity_and_does_not_call_resolver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = publish_completed_eod_dataset(tmp_path)
    repository = CanonicalEodReadRepository(tmp_path)
    monkeypatch.setattr(CanonicalEodReadRepository, "_read_resolver", lambda *args, **kwargs: pytest.fail("resolver called"))
    result = repository.read_history_sessions((SESSION_DATE,))
    assert len(result) == 1
    assert result[0].integrity.record_count == 3
    assert result[0].integrity.content_fingerprint == fixture.eod_content_sha256
    assert len(result[0].integrity.parquet_sha256) == 64
    assert result[0].integrity.identity_snapshot_date == SESSION_DATE
    assert result[0].integrity.future_identity_reference_count == 0
    assert len(result[0].bars) == 3
    testa = next(item for item in result[0].bars if item.ticker == "TESTA")
    assert testa.split_adjustment_factor == Decimal("0.5000000000")
    assert testa.dividend_adjustment_factor == Decimal("1.0000000000")
    assert testa.total_return_adjustment_factor == Decimal("0.5000000000")


def test_duplicate_requested_session_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    with pytest.raises(EodDatasetUnavailableError, match="duplicate requested"):
        CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE, SESSION_DATE))


def test_future_identity_reference_is_rejected_before_fallback(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    path = eod_manifest_path(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["identity_snapshot"]["as_of_date"] = date(2026, 8, 14).isoformat()
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(EodDatasetUnavailableError, match="future identity"):
        CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE,))


def test_duplicate_instrument_session_and_multiple_revision_are_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    partition = eod_manifest_path(tmp_path).parent
    parquet = partition / "part-00000.parquet"
    table = pq.ParquetFile(parquet).read()
    revision_index = table.schema.get_field_index("revision")
    duplicate = table.slice(0, 1).set_column(revision_index, table.schema.field(revision_index), pa.array([2], type=pa.int32()))
    combined = pa.concat_tables((table, duplicate))
    pq.write_table(combined, parquet)
    manifest = json.loads(eod_manifest_path(tmp_path).read_text(encoding="utf-8"))
    manifest["record_count"] = combined.num_rows
    manifest["content_sha256"] = table_rows_fingerprint(_table_to_fingerprint_rows(combined))
    eod_manifest_path(tmp_path).write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(EodDatasetUnavailableError, match="duplicate instrument/session"):
        CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE,))


def test_non_latest_revision_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    parquet = eod_manifest_path(tmp_path).parent / "part-00000.parquet"
    table = pq.ParquetFile(parquet).read()
    latest_index = table.schema.get_field_index("is_latest_revision")
    flags = [False] + [True] * (table.num_rows - 1)
    changed = table.set_column(latest_index, table.schema.field(latest_index), pa.array(flags, type=pa.bool_()))
    pq.write_table(changed, parquet)
    manifest = json.loads(eod_manifest_path(tmp_path).read_text(encoding="utf-8"))
    manifest["content_sha256"] = table_rows_fingerprint(_table_to_fingerprint_rows(changed))
    eod_manifest_path(tmp_path).write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(EodDatasetUnavailableError, match="non-latest"):
        CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE,))


def test_symlink_in_partition_chain_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    publish_completed_eod_dataset(target)
    market_data = tmp_path / "market-data"
    market_data.symlink_to(target / "market-data", target_is_directory=True)
    with pytest.raises(EodDatasetUnavailableError, match="symlink"):
        CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE,))


def test_history_read_is_read_only(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    before = sorted((item.relative_to(tmp_path).as_posix(), item.stat().st_mtime_ns) for item in tmp_path.rglob("*") if item.is_file())
    CanonicalEodReadRepository(tmp_path).read_history_sessions((SESSION_DATE,))
    after = sorted((item.relative_to(tmp_path).as_posix(), item.stat().st_mtime_ns) for item in tmp_path.rglob("*") if item.is_file())
    assert before == after
