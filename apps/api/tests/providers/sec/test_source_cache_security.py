from __future__ import annotations

import hashlib
import io
import json
import socket
import stat
import struct
import warnings
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import tip_api.providers.sec.bulk_sources as bulk_sources
from tip_api.providers.sec.bulk_sources import (
    COMPANY_EXCHANGE_URL,
    COMPANY_MF_URL,
    CSV_PATH_TEMPLATES,
    LANDING_PAGES,
    SOURCE_CACHE_ARTIFACTS,
    SOURCE_CACHE_RELATIVE_ROOT,
    SUBMISSIONS_URL,
    acquire_sec_source_cache,
    source_file_hash,
    validate_submissions_zip,
)
from tip_api.providers.sec.config import SEC_USER_AGENT_ENV, SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult, SecTransportError


CUTOFF = date(2026, 8, 14)
OBSERVED_AT = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
SENTINEL = "trading-intelligence-platform cache-fixture@invalid.example"


class FixtureDownloadTransport:
    def __init__(self, responses: dict[str, tuple[bytes, str]]) -> None:
        self.responses = responses
        self.urls: list[str] = []
        self.request_count = 0
        self.retry_count = 0

    def download(self, url: str, target: Path, **kwargs: object) -> SecDownloadResult:
        del kwargs
        self.urls.append(url)
        self.request_count += 1
        try:
            payload, content_type = self.responses[url]
        except KeyError as exc:
            raise SecTransportError("fixture response unavailable") from exc
        target.write_bytes(payload)
        return SecDownloadResult(
            url=url,
            content_type=content_type,
            byte_count=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            retry_count=0,
        )


def config() -> SecProviderConfig:
    return SecProviderConfig.from_environment({SEC_USER_AGENT_ENV: SENTINEL})


def landing(dataset: str) -> bytes:
    path = CSV_PATH_TEMPLATES[dataset].format(year=2026)
    return (
        "<html><body><table><tr><th>File</th><th>Format</th><th>Size</th></tr>"
        f'<tr><td><a href="{path}">2026</a> Updated 6/1/2026</td>'
        "<td>CSV</td><td>1 MB</td></tr></table></body></html>"
    ).encode()


def submissions_zip_bytes(
    members: list[tuple[str | zipfile.ZipInfo, bytes]],
    *,
    compression: int = zipfile.ZIP_STORED,
) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=compression) as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return target.getvalue()


def submission_payload(cik: str = "1") -> bytes:
    return json.dumps(
        {"cik": cik, "filings": {"recent": {}, "files": []}},
        separators=(",", ":"),
    ).encode()


def fixture_responses() -> dict[str, tuple[bytes, str]]:
    responses: dict[str, tuple[bytes, str]] = {
        COMPANY_EXCHANGE_URL: (b'{"fields":["cik","ticker"],"data":[[1,"AAA"]]}', "application/json"),
        COMPANY_MF_URL: (b'{"fields":["cik","ticker"],"data":[[2,"BBB"]]}', "application/json"),
        SUBMISSIONS_URL: (
            submissions_zip_bytes([("CIK0000000001.json", submission_payload())]),
            "application/zip",
        ),
    }
    csv_headers = {
        "investment_company_series_class": b"CIK,Series ID\n1,S000001\n",
        "closed_end_fund": b"CIK,Company Name\n1,Fixture CEF\n",
        "business_development_company": b"CIK,Company Name\n1,Fixture BDC\n",
    }
    for dataset, landing_url in LANDING_PAGES.items():
        responses[landing_url] = (landing(dataset), "text/html")
        responses[f"https://www.sec.gov{CSV_PATH_TEMPLATES[dataset].format(year=2026)}"] = (
            csv_headers[dataset],
            "text/csv",
        )
    return responses


def target(root: Path) -> Path:
    return root / SOURCE_CACHE_RELATIVE_ROOT / f"as_of_date={CUTOFF.isoformat()}"


def test_source_cache_publishes_exact_private_nine_artifact_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: pytest.fail("network attempted"),
    )
    transport = FixtureDownloadTransport(fixture_responses())
    result = acquire_sec_source_cache(
        tmp_path,
        as_of_date=CUTOFF,
        observed_at=OBSERVED_AT,
        config=config(),
        transport=transport,
    )
    assert result.path == target(tmp_path)
    assert result.status == "published"
    assert transport.request_count == 9
    assert len(result.sources) == 9
    assert {item.file_name: item.artifact_role for item in result.sources} == SOURCE_CACHE_ARTIFACTS
    assert {entry.name for entry in result.path.iterdir()} == set(SOURCE_CACHE_ARTIFACTS) | {"manifest.json"}
    manifest_text = (result.path / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["completion_status"] == "completed"
    assert manifest["artifact_count"] == 9
    assert len(manifest["sources"]) == 9
    assert {item["file_name"]: item["artifact_role"] for item in manifest["sources"]} == SOURCE_CACHE_ARTIFACTS
    for item in manifest["sources"]:
        artifact = result.path / item["file_name"]
        assert artifact.stat().st_size == item["byte_size"]
        assert source_file_hash(artifact) == item["sha256"]
        assert item["url"].startswith("https://www.sec.gov/")
    assert (result.path / "investment_company_series_class.landing.html").is_file()
    lowered = manifest_text.lower()
    assert SENTINEL not in manifest_text
    assert "user-agent" not in lowered
    assert "authorization" not in lowered
    assert "cookie" not in lowered
    assert not list(result.path.parent.glob(f".{result.path.name}.staging.*"))


def test_source_cache_rejects_landing_content_type_and_cleans_staging(tmp_path: Path) -> None:
    responses = fixture_responses()
    responses[LANDING_PAGES["investment_company_series_class"]] = (landing("investment_company_series_class"), "text/plain")
    transport = FixtureDownloadTransport(responses)
    with pytest.raises(SecTransportError, match="content type"):
        acquire_sec_source_cache(tmp_path, as_of_date=CUTOFF, observed_at=OBSERVED_AT, config=config(), transport=transport)
    assert not target(tmp_path).exists()
    assert not list(target(tmp_path).parent.glob(f".{target(tmp_path).name}.staging.*"))


def test_source_cache_rejects_empty_landing_and_cleans_staging(tmp_path: Path) -> None:
    responses = fixture_responses()
    responses[LANDING_PAGES["investment_company_series_class"]] = (b"", "text/html")
    transport = FixtureDownloadTransport(responses)
    with pytest.raises(SecTransportError, match="size"):
        acquire_sec_source_cache(tmp_path, as_of_date=CUTOFF, observed_at=OBSERVED_AT, config=config(), transport=transport)
    assert not target(tmp_path).exists()
    assert not list(target(tmp_path).parent.glob(f".{target(tmp_path).name}.staging.*"))


def test_source_cache_rejects_download_result_url_mismatch(tmp_path: Path) -> None:
    class MismatchedResultTransport(FixtureDownloadTransport):
        def download(self, url: str, target_path: Path, **kwargs: object) -> SecDownloadResult:
            result = super().download(url, target_path, **kwargs)
            return SecDownloadResult(
                url="https://www.sec.gov/files/unexpected.json",
                content_type=result.content_type,
                byte_count=result.byte_count,
                sha256=result.sha256,
                retry_count=0,
            )

    transport = MismatchedResultTransport(fixture_responses())
    with pytest.raises(SecTransportError, match="URL mismatch"):
        acquire_sec_source_cache(tmp_path, as_of_date=CUTOFF, observed_at=OBSERVED_AT, config=config(), transport=transport)
    assert transport.request_count == 1
    assert not target(tmp_path).exists()


def test_source_cache_rejects_existing_target_without_transport(tmp_path: Path) -> None:
    existing = target(tmp_path)
    existing.mkdir(parents=True)
    transport = FixtureDownloadTransport(fixture_responses())
    with pytest.raises(SecTransportError, match="already exists"):
        acquire_sec_source_cache(tmp_path, as_of_date=CUTOFF, observed_at=OBSERVED_AT, config=config(), transport=transport)
    assert transport.request_count == 0


def test_source_cache_rejects_symlink_target_without_transport(tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    partition = target(tmp_path)
    partition.parent.mkdir(parents=True)
    partition.symlink_to(destination, target_is_directory=True)
    transport = FixtureDownloadTransport(fixture_responses())
    with pytest.raises(SecTransportError, match="already exists"):
        acquire_sec_source_cache(tmp_path, as_of_date=CUTOFF, observed_at=OBSERVED_AT, config=config(), transport=transport)
    assert transport.request_count == 0


def write_zip(tmp_path: Path, name: str, members: list[tuple[str | zipfile.ZipInfo, bytes]], *, compression: int = zipfile.ZIP_STORED) -> Path:
    path = tmp_path / name
    path.write_bytes(submissions_zip_bytes(members, compression=compression))
    return path


def test_minimal_submissions_zip_passes_without_extracting(tmp_path: Path) -> None:
    path = write_zip(tmp_path, "valid.zip", [("CIK0000000001.json", submission_payload())])
    validate_submissions_zip(path)
    assert {item.name for item in tmp_path.iterdir()} == {"valid.zip"}


def test_encrypted_submissions_member_is_rejected(tmp_path: Path) -> None:
    path = write_zip(tmp_path, "encrypted.zip", [("CIK0000000001.json", submission_payload())])
    data = bytearray(path.read_bytes())
    local_flags = struct.unpack_from("<H", data, 6)[0] | 0x1
    struct.pack_into("<H", data, 6, local_flags)
    central = data.index(b"PK\x01\x02")
    central_flags = struct.unpack_from("<H", data, central + 8)[0] | 0x1
    struct.pack_into("<H", data, central + 8, central_flags)
    path.write_bytes(data)
    with pytest.raises(SecTransportError, match="encrypted"):
        validate_submissions_zip(path)


@pytest.mark.parametrize(
    "member_name",
    [
        "/CIK0000000001.json",
        "../CIK0000000001.json",
        "nested/../CIK0000000001.json",
        "nested\\CIK0000000001.json",
        "%2e%2e%2fCIK0000000001.json",
        "%252e%252e%252fCIK0000000001.json",
        "nested/CIK0000000001.json",
        "README.json",
        "CIK1.json",
        "CIK0000000001.JSON",
    ],
)
def test_unsafe_or_unapproved_submissions_member_names_are_rejected(tmp_path: Path, member_name: str) -> None:
    path = write_zip(tmp_path, "unsafe.zip", [(member_name, submission_payload())])
    with pytest.raises(SecTransportError):
        validate_submissions_zip(path)


def test_duplicate_submissions_members_are_rejected(tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        path = write_zip(
            tmp_path,
            "duplicate.zip",
            [
                ("CIK0000000001.json", submission_payload()),
                ("CIK0000000001.json", submission_payload()),
            ],
        )
    with pytest.raises(SecTransportError, match="duplicate"):
        validate_submissions_zip(path)


def test_normalized_duplicate_submissions_members_are_rejected(tmp_path: Path) -> None:
    path = write_zip(
        tmp_path,
        "normalized-duplicate.zip",
        [
            ("CIK0000000001.json", submission_payload()),
            ("cik0000000001.JSON", submission_payload()),
        ],
    )
    with pytest.raises(SecTransportError, match="duplicate"):
        validate_submissions_zip(path)


def test_symlink_and_nonregular_submissions_members_are_rejected(tmp_path: Path) -> None:
    for label, file_type in (("symlink", stat.S_IFLNK), ("fifo", stat.S_IFIFO)):
        info = zipfile.ZipInfo("CIK0000000001.json")
        info.create_system = 3
        info.external_attr = (file_type | 0o600) << 16
        path = write_zip(tmp_path, f"{label}.zip", [(info, submission_payload())])
        with pytest.raises(SecTransportError, match="non-regular"):
            validate_submissions_zip(path)


def test_submissions_member_count_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bulk_sources, "MAX_ZIP_MEMBERS", 1)
    path = write_zip(
        tmp_path,
        "members.zip",
        [
            ("CIK0000000001.json", submission_payload()),
            ("CIK0000000002.json", submission_payload("2")),
        ],
    )
    with pytest.raises(SecTransportError, match="member count"):
        validate_submissions_zip(path)


def test_submissions_single_and_total_size_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    one = submission_payload()
    monkeypatch.setattr(bulk_sources, "MAX_ZIP_MEMBER_BYTES", len(one) - 1)
    single = write_zip(tmp_path, "single.zip", [("CIK0000000001.json", one)])
    with pytest.raises(SecTransportError, match="member exceeds"):
        validate_submissions_zip(single)
    monkeypatch.setattr(bulk_sources, "MAX_ZIP_MEMBER_BYTES", len(one) + 1)
    monkeypatch.setattr(bulk_sources, "MAX_ZIP_TOTAL_UNCOMPRESSED", len(one) * 2 - 1)
    total = write_zip(
        tmp_path,
        "total.zip",
        [
            ("CIK0000000001.json", one),
            ("CIK0000000002.json", submission_payload("2")),
        ],
    )
    with pytest.raises(SecTransportError, match="expansion"):
        validate_submissions_zip(total)


def test_submissions_compression_ratio_and_zero_size_are_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bulk_sources, "MAX_ZIP_COMPRESSION_RATIO", 1)
    compressed = write_zip(
        tmp_path,
        "ratio.zip",
        [("CIK0000000001.json", submission_payload())],
        compression=zipfile.ZIP_DEFLATED,
    )
    with pytest.raises(SecTransportError, match="compression ratio"):
        validate_submissions_zip(compressed)
    empty = write_zip(tmp_path, "empty.zip", [("CIK0000000001.json", b"")])
    with pytest.raises(SecTransportError, match="JSON"):
        validate_submissions_zip(empty)


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"<html>error</html>",
        b"[]",
        b'{"cik":"1"}',
        b'{"cik":"2","filings":{"recent":{}}}',
        b'{"cik":"1","filings":[]}',
        b'{"cik":"1","filings":{"recent":[]}}',
        b'{"cik":"1","filings":{"files":{}}}',
    ],
)
def test_submissions_json_and_basic_schema_fail_closed(tmp_path: Path, payload: bytes) -> None:
    path = write_zip(tmp_path, "schema.zip", [("CIK0000000001.json", payload)])
    with pytest.raises(SecTransportError):
        validate_submissions_zip(path)
