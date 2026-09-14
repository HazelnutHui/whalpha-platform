from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tip_api.persistence.eod_read import EodDatasetUnavailableError, EodSessionNotFoundError
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tests.support.eod_read_dataset import SESSION_DATE, eod_manifest_path, publish_completed_eod_dataset, update_json


def test_lists_completed_sessions_and_reads_joined_bars(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    repository = CanonicalEodReadRepository(tmp_path)

    assert repository.list_session_index() == (SESSION_DATE,)
    sessions = repository.list_sessions()
    assert [item.session_date for item in sessions] == [SESSION_DATE]
    assert sessions[0].record_count == 3
    assert sessions[0].identity_as_of_date == SESSION_DATE

    bars = repository.read_bars(SESSION_DATE)
    assert [bar.ticker for bar in bars] == ["TESTA", "TESTB", "TESTC"]
    assert bars[0].name == "TESTA Test Instrument"
    assert str(bars[0].volume) == "100.2500000000"
    assert bars[0].split_adjustment_factor == Decimal("0.5000000000")
    assert bars[0].dividend_adjustment_factor == Decimal("1.0000000000")
    assert bars[0].total_return_adjustment_factor == Decimal("0.5000000000")
    assert bars[1].vwap is None
    assert bars[1].trade_count is None

    canonical = repository.read_canonical_records(SESSION_DATE)
    assert len(canonical) == 3
    assert all(item.session_date == SESSION_DATE for item in canonical)
    assert canonical[0].schema_version == "1.0"

    instruments = repository.read_instruments_for_session(SESSION_DATE)
    assert [item.ticker for item in instruments] == ["TESTA", "TESTB", "TESTC"]
    assert all(item.as_of_date == SESSION_DATE for item in instruments)


def test_unknown_session_raises_not_found(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    with pytest.raises(EodSessionNotFoundError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE.replace(day=12))


def test_incomplete_partition_is_ignored_in_listing(tmp_path: Path) -> None:
    base = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION_DATE.isoformat()}"
    base.mkdir(parents=True)
    assert CanonicalEodReadRepository(tmp_path).list_sessions() == ()


def test_incomplete_partition_is_rejected_by_scheduler_completion_index(
    tmp_path: Path,
) -> None:
    base = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION_DATE.isoformat()}"
    base.mkdir(parents=True)
    with pytest.raises(EodDatasetUnavailableError, match="completion index is incomplete"):
        CanonicalEodReadRepository(tmp_path).list_session_index()


def test_corrupted_manifest_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    eod_manifest_path(tmp_path).write_text("[]\n", encoding="utf-8")
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).list_session_index()
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_row_count_mismatch_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    update_json(eod_manifest_path(tmp_path), record_count=99)
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_fingerprint_mismatch_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    update_json(eod_manifest_path(tmp_path), content_sha256="0" * 64)
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_schema_mismatch_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    parquet_path = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION_DATE.isoformat()}" / "part-00000.parquet"
    pq.write_table(pa.table({"bad": [1]}), parquet_path)
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_identity_snapshot_reference_mismatch_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    manifest = json.loads(eod_manifest_path(tmp_path).read_text(encoding="utf-8"))
    manifest["identity_snapshot"]["snapshot_content_sha256"] = "1" * 64
    eod_manifest_path(tmp_path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_resolver_join_mismatch_is_rejected(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    resolver_path = tmp_path / "market-data" / "provider-ticker-resolver" / "schema_version=1" / "provider=massive" / f"as_of_date={SESSION_DATE.isoformat()}" / "manifest.json"
    update_json(resolver_path, content_sha256="2" * 64)
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)


def test_root_must_be_absolute() -> None:
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(Path("relative-root")).list_sessions()


def test_symlink_root_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(EodDatasetUnavailableError):
        CanonicalEodReadRepository(link).list_sessions()


def test_repository_does_not_write_when_reading(tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    CanonicalEodReadRepository(tmp_path).read_bars(SESSION_DATE)
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert after == before


def test_repository_has_no_massive_dependency() -> None:
    source = Path("apps/api/src/tip_api/persistence/parquet/eod_read.py").read_text(encoding="utf-8")
    assert "providers.massive" not in source
    assert "credential" not in source.lower()
