from __future__ import annotations

import gzip
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.providers.massive.flat_file_day_aggregates import (
    ACCESS_KEY_ENV,
    SECRET_KEY_ENV,
    MassiveFlatFileConfig,
    MassiveFlatFileCredentialError,
    MassiveFlatFileError,
    MassiveFlatFileObject,
    day_aggregate_object_key,
    fetch_flat_file_day_aggregate_package,
    load_massive_flat_file_config_from_file,
    parse_flat_file_day_aggregate,
)
from tip_api.providers.massive.same_day_catchup import (
    SameDayCatchupError,
    read_fetch_package_evidence,
)


SESSION = date(2022, 1, 3)


def _gzip_csv(*, header: str | None = None) -> bytes:
    window_start = int(datetime(2022, 1, 3, 5, tzinfo=UTC).timestamp() * 1_000_000_000)
    columns = header or (
        "ticker,volume,open,close,high,low,window_start,transactions"
    )
    value = (
        f"{columns}\n"
        f"AAPL,1000,175.0,176.0,177.0,174.0,{window_start},100\n"
        f"MSFT,2000,330.0,332.0,333.0,329.0,{window_start},200\n"
    )
    return gzip.compress(value.encode("utf-8"), mtime=0)


class FakeTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[tuple[str, str]] = []

    def get_object(self, *, bucket: str, object_key: str) -> MassiveFlatFileObject:
        self.calls.append((bucket, object_key))
        return MassiveFlatFileObject(
            body=self.body,
            etag="fixture-etag",
            last_modified=datetime(2022, 1, 4, 16, tzinfo=UTC),
        )


def test_object_key_and_csv_conversion_are_exact() -> None:
    assert (
        day_aggregate_object_key(SESSION)
        == "us_stocks_sip/day_aggs_v1/2022/01/2022-01-03.csv.gz"
    )
    rows = parse_flat_file_day_aggregate(_gzip_csv(), session_date=SESSION)

    assert rows == (
        {
            "T": "AAPL",
            "v": "1000",
            "o": "175.0",
            "c": "176.0",
            "h": "177.0",
            "l": "174.0",
            "t": 1641186000000,
            "n": "100",
        },
        {
            "T": "MSFT",
            "v": "2000",
            "o": "330.0",
            "c": "332.0",
            "h": "333.0",
            "l": "329.0",
            "t": 1641186000000,
            "n": "200",
        },
    )


def test_fetch_package_retains_and_transitively_validates_raw_source(
    tmp_path: Path,
) -> None:
    raw = _gzip_csv()
    transport = FakeTransport(raw)
    package = tmp_path / "acquisition-package"
    manifest = fetch_flat_file_day_aggregate_package(
        config=MassiveFlatFileConfig(
            access_key_id="fixture-access",
            secret_access_key="fixture-secret",
        ),
        transport=transport,
        session_date=SESSION,
        package_path=package,
        fetched_at=datetime(2022, 1, 4, 16, tzinfo=UTC),
    )

    assert transport.calls == [("flatfiles", day_aggregate_object_key(SESSION))]
    assert manifest.request_count == 1
    assert (package / "source.csv.gz").read_bytes() == raw
    evidence = read_fetch_package_evidence(
        package_path=package,
        operation="eod",
        expected_session=SESSION,
    )
    assert evidence.package_content_sha256 == manifest.package_content_sha256

    source = package / "source.csv.gz"
    source.chmod(0o600)
    source.write_bytes(raw + b"tampered")
    with pytest.raises(SameDayCatchupError, match="custody differs"):
        read_fetch_package_evidence(
            package_path=package,
            operation="eod",
            expected_session=SESSION,
        )


def test_flat_file_rejects_schema_drift_and_wrong_session() -> None:
    with pytest.raises(MassiveFlatFileError, match="header differs"):
        parse_flat_file_day_aggregate(
            _gzip_csv(header="ticker,open"),
            session_date=SESSION,
        )

    with pytest.raises(MassiveFlatFileError, match="no aggregate rows"):
        parse_flat_file_day_aggregate(
            gzip.compress(
                b"ticker,volume,open,close,high,low,window_start,transactions\n",
                mtime=0,
            ),
            session_date=SESSION,
        )

    with pytest.raises(MassiveFlatFileError, match="another session"):
        parse_flat_file_day_aggregate(
            _gzip_csv(),
            session_date=date(2022, 1, 4),
        )


def test_flat_file_credential_loader_is_strict_and_secret_typed(
    tmp_path: Path,
) -> None:
    sentinel = "sentinel-secret-value"
    path = tmp_path / "massive-flat-files.env"
    path.write_text(
        f"{ACCESS_KEY_ENV}=access\n{SECRET_KEY_ENV}={sentinel}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)

    config = load_massive_flat_file_config_from_file(path)

    assert config.access_key_id.get_secret_value() == "access"
    assert config.secret_access_key.get_secret_value() == sentinel
    assert sentinel not in repr(config)

    path.chmod(0o644)
    with pytest.raises(MassiveFlatFileCredentialError, match="custody"):
        load_massive_flat_file_config_from_file(path)
