"""Tests for deterministic EOD Price Bar Parquet persistence."""

from __future__ import annotations

import json
import socket
from datetime import UTC, date, datetime
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, Rounded, localcontext
from pathlib import Path
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus
from tip_api.persistence.eod_bars import (
    EodPriceBarConflictError,
    EodPriceBarCorruptionError,
    EodPriceBarPersistenceError,
)
from tip_api.persistence.parquet.eod_bars import (
    DECIMAL_PRECISION,
    DECIMAL_SCALE,
    EOD_PRICE_BAR_ARROW_SCHEMA,
    ParquetEodPriceBarRepository,
    records_to_table,
)
from tip_api.persistence.parquet.manifest import content_fingerprint, decimal_to_string

SESSION = date(2026, 8, 13)
CREATED_AT = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
INGESTED_AT = datetime(2026, 8, 14, 1, 30, tzinfo=UTC)
TESTA_ID = UUID("00000000-0000-4000-8000-000000000001")
TESTB_ID = UUID("00000000-0000-4000-8000-000000000002")
TESTC_ID = UUID("00000000-0000-4000-8000-000000000003")


def make_bar(
    instrument_id: UUID = TESTA_ID,
    *,
    session_date: date = SESSION,
    source: str = "mocked_provider",
    revision: int = 1,
    is_latest_revision: bool = True,
    close: str = "10.25",
    vwap: str | None = "10.20",
    trade_count: int | None = 100,
    volume: str = "1000",
    quality_flags: tuple[str, ...] = ("mock_fixture",),
) -> EodPriceBarV1:
    close_decimal = Decimal(close)
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=session_date,
        open=Decimal("10.00"),
        high=Decimal("10.50"),
        low=Decimal("9.75"),
        close=close_decimal,
        volume=Decimal(volume),
        vwap=Decimal(vwap) if vwap is not None else None,
        trade_count=trade_count,
        notional=Decimal("10250.00"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=close_decimal,
        source=source,
        source_record_id=f"{instrument_id}:{session_date}:{source}:{revision}",
        ingested_at=INGESTED_AT,
        revision=revision,
        is_latest_revision=is_latest_revision,
        quality_status=QualityStatus.VALID,
        quality_flags=quality_flags,
    )


def repository(root: Path) -> ParquetEodPriceBarRepository:
    return ParquetEodPriceBarRepository(root=root, created_at=CREATED_AT)


def partition_path(root: Path) -> Path:
    return root / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION.isoformat()}"


def test_explicit_arrow_schema() -> None:
    assert EOD_PRICE_BAR_ARROW_SCHEMA.field("instrument_id").type == pa.string()
    assert EOD_PRICE_BAR_ARROW_SCHEMA.field("session_date").type == pa.date32()
    assert EOD_PRICE_BAR_ARROW_SCHEMA.field("open").type == pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE)
    assert EOD_PRICE_BAR_ARROW_SCHEMA.field("ingested_at").type == pa.timestamp("us", tz="UTC")


def test_canonical_model_to_arrow_conversion_and_round_trip(tmp_path: Path) -> None:
    records = (make_bar(TESTB_ID, vwap=None, trade_count=None), make_bar(TESTA_ID))
    table = records_to_table(records)
    assert table.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False)
    assert table.column("instrument_id").to_pylist() == [str(TESTA_ID), str(TESTB_ID)]
    path = tmp_path / "bars.parquet"
    pq.write_table(table, path)
    read_back = pq.ParquetFile(path).read()
    assert read_back.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False)
    rows = read_back.to_pylist()
    assert rows[0]["session_date"] == SESSION
    assert rows[0]["ingested_at"].tzinfo is not None
    assert rows[0]["open"] == Decimal("10.0000000000")
    assert rows[1]["vwap"] is None
    assert rows[1]["trade_count"] is None


def test_fractional_volume_parquet_round_trip(tmp_path: Path) -> None:
    table = records_to_table((make_bar(volume="1000.125"),))
    path = tmp_path / "fractional-volume.parquet"
    pq.write_table(table, path)
    row = pq.ParquetFile(path).read().to_pylist()[0]

    assert row["volume"] == Decimal("1000.1250000000")


def test_large_volume_parquet_round_trip(tmp_path: Path) -> None:
    table = records_to_table((make_bar(volume="123456789012345678.1234567890"),))
    path = tmp_path / "large-volume.parquet"
    pq.write_table(table, path)
    row = pq.ParquetFile(path).read().to_pylist()[0]

    assert row["volume"] == Decimal("123456789012345678.1234567890")


def test_volume_decimal_scale_overflow_rejected(tmp_path: Path) -> None:
    record = make_bar(volume="1000.12345678901")
    with pytest.raises(EodPriceBarPersistenceError, match="scale"):
        repository(tmp_path).publish_session((record,), session_date=SESSION, provider_id="mocked_provider")


def test_volume_decimal_precision_overflow_rejected(tmp_path: Path) -> None:
    record = make_bar(volume="12345678901234567890123456789.1234567890")
    with pytest.raises(EodPriceBarPersistenceError, match="precision"):
        repository(tmp_path).publish_session((record,), session_date=SESSION, provider_id="mocked_provider")


def test_volume_fingerprint_normalizes_numeric_equivalence() -> None:
    assert content_fingerprint((make_bar(volume="10"),)) == content_fingerprint((make_bar(volume="10.0"),))


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("0", "0"), ("-0.000", "-0"), ("12.3400", "12.34"),
        ("-0.0012300", "-0.00123"), ("1.2300E+7", "12300000"),
        ("123456789012345678901234567890.0000", "123456789012345678901234567890"),
    ),
)
@pytest.mark.parametrize(("precision", "rounding"), ((9, ROUND_DOWN), (28, ROUND_UP), (50, ROUND_DOWN)))
def test_decimal_fingerprint_string_is_context_independent(value, expected, precision, rounding) -> None:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        assert decimal_to_string(Decimal(value)) == expected
        assert context.flags[Inexact] is False
        assert context.flags[Rounded] is False


def test_eod_fingerprint_is_context_independent_with_traps() -> None:
    records = (make_bar(volume="123456789012345678.1234567890"),)
    reference = content_fingerprint(records)
    for precision, rounding in ((9, ROUND_DOWN), (28, ROUND_UP), (50, ROUND_DOWN)):
        with localcontext() as context:
            context.prec = precision
            context.rounding = rounding
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            assert content_fingerprint(records) == reference
            assert context.flags[Inexact] is False
            assert context.flags[Rounded] is False


def test_quality_flags_deterministic_encoding() -> None:
    table = records_to_table((make_bar(quality_flags=("mock_fixture", "vendor_warning")),))
    assert table.column("quality_flags").to_pylist() == [["mock_fixture", "vendor_warning"]]


def test_input_order_does_not_affect_fingerprint() -> None:
    first = (make_bar(TESTB_ID), make_bar(TESTA_ID), make_bar(TESTC_ID))
    second = tuple(reversed(first))
    assert content_fingerprint(first) == content_fingerprint(second)


def test_successful_one_session_write_and_manifest(tmp_path: Path) -> None:
    records = (make_bar(TESTB_ID), make_bar(TESTA_ID, vwap=None, trade_count=None))
    result = repository(tmp_path).publish_session(records, session_date=SESSION, provider_id="mocked_provider")
    part = partition_path(tmp_path)
    manifest = json.loads((part / "manifest.json").read_text())
    assert result.status == "published"
    assert result.written_record_count == 2
    assert result.partition_path == part
    assert (part / "part-00000.parquet").exists()
    assert manifest["dataset_name"] == "eod-price-bars"
    assert manifest["schema_version"] == "1.0"
    assert manifest["session_date"] == SESSION.isoformat()
    assert manifest["provider_id"] == "mocked_provider"
    assert manifest["record_count"] == 2
    assert manifest["content_sha256"] == result.content_sha256
    assert manifest["completion_status"] == "completed"
    assert manifest["quality_summary"] == {"valid": 2}


def test_parquet_reread_validation(tmp_path: Path) -> None:
    records = (make_bar(TESTA_ID), make_bar(TESTB_ID))
    repository(tmp_path).publish_session(records, session_date=SESSION, provider_id="mocked_provider")
    table = pq.ParquetFile(partition_path(tmp_path) / "part-00000.parquet").read()
    assert table.num_rows == 2
    assert {row["session_date"] for row in table.to_pylist()} == {SESSION}


def test_empty_result_rejected(tmp_path: Path) -> None:
    with pytest.raises(EodPriceBarPersistenceError, match="empty"):
        repository(tmp_path).publish_session((), session_date=SESSION, provider_id="mocked_provider")


def test_wrong_session_date_rejected(tmp_path: Path) -> None:
    record = make_bar(session_date=date(2026, 8, 12))
    with pytest.raises(EodPriceBarPersistenceError, match="session_date"):
        repository(tmp_path).publish_session((record,), session_date=SESSION, provider_id="mocked_provider")


def test_duplicate_business_key_rejected(tmp_path: Path) -> None:
    record = make_bar()
    with pytest.raises(EodPriceBarPersistenceError, match="duplicate"):
        repository(tmp_path).publish_session((record, record), session_date=SESSION, provider_id="mocked_provider")


def test_conflicting_latest_revision_rejected(tmp_path: Path) -> None:
    records = (make_bar(revision=1, is_latest_revision=True), make_bar(revision=2, is_latest_revision=True))
    with pytest.raises(EodPriceBarPersistenceError, match="latest"):
        repository(tmp_path).publish_session(records, session_date=SESSION, provider_id="mocked_provider")


def test_identical_rerun_is_idempotent(tmp_path: Path) -> None:
    records = (make_bar(TESTA_ID), make_bar(TESTB_ID))
    first = repository(tmp_path).publish_session(records, session_date=SESSION, provider_id="mocked_provider")
    second = repository(tmp_path).publish_session(tuple(reversed(records)), session_date=SESSION, provider_id="mocked_provider")
    assert first.content_sha256 == second.content_sha256
    assert second.status == "already_present"
    assert second.written_record_count == 0


def test_conflicting_rerun_rejected(tmp_path: Path) -> None:
    repository(tmp_path).publish_session((make_bar(close="10.25"),), session_date=SESSION, provider_id="mocked_provider")
    with pytest.raises(EodPriceBarConflictError):
        repository(tmp_path).publish_session((make_bar(close="10.30"),), session_date=SESSION, provider_id="mocked_provider")


def test_incomplete_existing_partition_rejected(tmp_path: Path) -> None:
    part = partition_path(tmp_path)
    part.mkdir(parents=True)
    (part / "part-00000.parquet").write_text("not real parquet")
    with pytest.raises(EodPriceBarCorruptionError, match="incomplete"):
        repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")


def test_corrupted_manifest_rejected(tmp_path: Path) -> None:
    repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")
    (partition_path(tmp_path) / "manifest.json").write_text("not-json")
    with pytest.raises(EodPriceBarCorruptionError, match="manifest"):
        repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")


def test_corrupted_parquet_detected(tmp_path: Path) -> None:
    repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")
    (partition_path(tmp_path) / "part-00000.parquet").write_text("corrupt")
    with pytest.raises(EodPriceBarCorruptionError, match="parquet"):
        repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")


def test_staging_cleanup_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr("tip_api.persistence.parquet.eod_bars.pq.write_table", fail_write)
    with pytest.raises(RuntimeError, match="simulated"):
        repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")
    staging_paths = list((tmp_path / "market-data" / "eod-price-bars" / "schema_version=1").glob("*.staging.*"))
    assert staging_paths == []
    assert not partition_path(tmp_path).exists()


def test_root_symlink_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "root-link"
    root.symlink_to(target, target_is_directory=True)
    with pytest.raises(EodPriceBarPersistenceError, match="symlink"):
        repository(root).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")


def test_existing_partition_symlink_rejected(tmp_path: Path) -> None:
    part = partition_path(tmp_path)
    part.parent.mkdir(parents=True)
    target = tmp_path / "target"
    target.mkdir()
    part.symlink_to(target, target_is_directory=True)
    with pytest.raises(EodPriceBarPersistenceError, match="symlink"):
        repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")


def test_no_silent_overwrite(tmp_path: Path) -> None:
    repository(tmp_path).publish_session((make_bar(close="10.25"),), session_date=SESSION, provider_id="mocked_provider")
    parquet_path = partition_path(tmp_path) / "part-00000.parquet"
    before = parquet_path.stat().st_mtime_ns
    with pytest.raises(EodPriceBarConflictError):
        repository(tmp_path).publish_session((make_bar(close="10.40"),), session_date=SESSION, provider_id="mocked_provider")
    assert parquet_path.stat().st_mtime_ns == before


def test_decimal_scale_overflow_rejected(tmp_path: Path) -> None:
    record = make_bar(close="10.12345678901")
    with pytest.raises(EodPriceBarPersistenceError, match="scale"):
        repository(tmp_path).publish_session((record,), session_date=SESSION, provider_id="mocked_provider")


def test_vwap_scale_overflow_still_rejected_by_provider_neutral_repository(tmp_path: Path) -> None:
    record = make_bar(vwap="10.12345678901")
    with pytest.raises(EodPriceBarPersistenceError, match="scale"):
        repository(tmp_path).publish_session((record,), session_date=SESSION, provider_id="mocked_provider")


def test_repository_does_not_import_massive_package() -> None:
    source = Path("apps/api/src/tip_api/persistence/parquet/eod_bars.py").read_text()
    assert "providers.massive" not in source


def test_repository_does_not_use_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    result = repository(tmp_path).publish_session((make_bar(),), session_date=SESSION, provider_id="mocked_provider")
    assert result.status == "published"
