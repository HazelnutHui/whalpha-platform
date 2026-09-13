from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import SecretStr

from tip_api.providers.sec.companyfacts_payload_census import (
    census_sec_companyfacts_payloads,
    seal_sec_companyfacts_payload_census,
)
from tip_api.providers.sec.companyfacts_normalized_source import (
    build_sec_companyfacts_normalized_source,
    read_sec_companyfacts_normalized_source,
)
from tip_api.providers.sec.companyfacts_source import (
    COMPANYFACTS_URL,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsRangeResult,
    SecCompanyfactsRemoteMetadataV1,
    acquire_sec_companyfacts_source_package,
)
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.filing_clock_ledger import (
    build_sec_filing_clock_package,
    read_sec_filing_clock_package,
)
from tip_api.providers.sec.submissions_payload_census import (
    census_sec_submissions_payloads,
    read_sealed_sec_submissions_payload_census,
    seal_sec_submissions_payload_census,
)
from tip_api.providers.sec.submissions_source import (
    SUBMISSIONS_URL,
    acquire_sec_submissions_source_package,
)


NOW = datetime(2026, 9, 10, 16, tzinfo=UTC)
START = date(2021, 8, 11)
END = date(2026, 9, 9)


class NoWait(SecCompanyfactsFixedIntervalLimiter):
    def __init__(self) -> None:
        pass

    def wait(self) -> None:
        return None


class FixtureTransport:
    def __init__(self, payload: bytes, url: str) -> None:
        self.payload = payload
        self.url = url

    def head(self, **kwargs: object) -> SecCompanyfactsRemoteMetadataV1:
        return SecCompanyfactsRemoteMetadataV1(
            url=self.url,
            content_type="application/zip",
            content_length=len(self.payload),
            last_modified=datetime(2026, 9, 10, 4, tzinfo=UTC),
            etag='"fixture"',
            accept_ranges="bytes",
            observed_at=kwargs["observed_at"],  # type: ignore[arg-type]
        )

    def download_range(self, **kwargs: object) -> SecCompanyfactsRangeResult:
        start = int(kwargs["byte_start"])
        end = int(kwargs["byte_end"])
        selected = self.payload[start : end + 1]
        kwargs["target"].write(selected)  # type: ignore[attr-defined]
        return SecCompanyfactsRangeResult(
            byte_count=len(selected),
            physical_sha256=hashlib.sha256(selected).hexdigest(),
        )


def _config() -> SecProviderConfig:
    return SecProviderConfig(
        user_agent=SecretStr("trading-intelligence-platform test@example.com"),
        request_timeout_seconds=Decimal("15"),
    )


def _zip(members: dict[str, object]) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(
                name,
                payload if isinstance(payload, str) else json.dumps(payload),
            )
    return target.getvalue()


def _companyfacts() -> bytes:
    facts = []
    for year in (2024, 2025, 2026):
        facts.append(
            {
                "end": f"{year}-06-30",
                "val": year,
                "accn": f"0000000001-{str(year)[2:]}-000001",
                "form": "10-Q",
                "filed": f"{year}-08-01",
            }
        )
    return _zip(
        {
            "CIK0000000001.json": {
                "cik": 1,
                "entityName": "Fixture Issuer",
                "facts": {
                    "us-gaap": {
                        "Revenue": {
                            "label": "Revenue",
                            "description": "Fixture",
                            "units": {"USD": facts},
                        }
                    }
                },
            }
        }
    )


def _submissions() -> bytes:
    columns = {
        "accessionNumber": ["0000000001-25-000001"],
        "filingDate": ["2025-08-01"],
        "acceptanceDateTime": ["2025-08-01T16:30:00.000Z"],
        "form": ["10-Q"],
    }
    root = {
        "cik": "0000000001",
        "name": "Fixture Issuer",
        "tickers": ["FIX"],
        "exchanges": ["NYSE"],
        "formerNames": [{"name": "Old Fixture"}],
        "filings": {
            "recent": columns,
            "files": [
                {
                    "name": "CIK0000000001-submissions-001.json",
                    "filingCount": 2,
                    "filingFrom": "2024-01-01",
                    "filingTo": "2024-12-31",
                }
            ],
        },
    }
    shard = {
        "accessionNumber": [
            "0000000001-24-000001",
            "0000000001-25-000001",
        ],
        "filingDate": ["2024-08-01", "2025-08-01"],
        "acceptanceDateTime": [
            "2024-08-01T00:00:00.000Z",
            "2025-08-01T17:30:00.000Z",
        ],
        "form": ["10-Q", "10-Q"],
    }
    return _zip(
        {
            "CIK0000000001.json": root,
            "CIK0000000001-submissions-001.json": shard,
            "placeholder.txt": "fixture marker",
        }
    )


def _source_package(
    root: Path, payload: bytes, url: str, *, companyfacts: bool
) -> Path:
    root.mkdir(mode=0o700)
    package = root / "snapshot=2026-09-10"
    kwargs = {
        "config": _config(),
        "package_path": package,
        "approved_custody_root": root,
        "transport": FixtureTransport(payload, url),
        "rate_limiter": NoWait(),
        "clock": lambda: NOW,
    }
    if companyfacts:
        acquire_sec_companyfacts_source_package(**kwargs)  # type: ignore[arg-type]
    else:
        acquire_sec_submissions_source_package(**kwargs)  # type: ignore[arg-type]
    return package


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    companyfacts_root = tmp_path / "companyfacts"
    companyfacts_package = _source_package(
        companyfacts_root, _companyfacts(), COMPANYFACTS_URL, companyfacts=True
    )
    companyfacts_census_root = tmp_path / "companyfacts-census"
    companyfacts_census_root.mkdir(mode=0o700)
    companyfacts_census = census_sec_companyfacts_payloads(
        source_package_path=companyfacts_package,
        source_custody_root=companyfacts_root,
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    seal_sec_companyfacts_payload_census(
        output_root=companyfacts_census_root, census=companyfacts_census
    )
    submissions_root = tmp_path / "submissions"
    submissions_package = _source_package(
        submissions_root, _submissions(), SUBMISSIONS_URL, companyfacts=False
    )
    return (
        submissions_root,
        submissions_package,
        companyfacts_root,
        companyfacts_package,
        companyfacts_census_root,
    )


def test_submissions_census_measures_root_shard_and_target_clocks(
    tmp_path: Path,
) -> None:
    roots = _inputs(tmp_path)

    result = census_sec_submissions_payloads(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        range_start=START,
        range_end=END,
        worker_count=2,
        evaluated_at=NOW,
    )

    assert result.source_member_count == result.payload_read_member_count == 3
    assert result.source_root_member_count == result.validated_root_member_count == 1
    assert result.source_historical_shard_member_count == 1
    assert result.validated_historical_shard_member_count == 1
    assert result.source_placeholder_member_count == 1
    assert result.validated_placeholder_member_count == 1
    assert result.quarantined_member_count == 0
    assert result.filing_row_count == 3
    assert result.valid_acceptance_datetime_row_count == 3
    assert result.companyfacts_target_accession_count == 3
    assert result.target_accession_matched_count == 2
    assert result.target_accession_missing_count == 1
    assert result.target_with_valid_acceptance_count == 2
    assert result.target_conflicting_acceptance_count == 1
    assert result.target_filing_date_exact_match_count == 2
    assert result.target_missing_accession_samples == ("0000000001-26-000001",)
    assert result.referenced_shard_present_count == 1
    assert result.missing_referenced_shard_count == 0
    assert result.unreferenced_actual_shard_count == 0
    assert result.root_current_ticker_exchange_aligned_count == 1


def test_submissions_census_seal_is_formally_readable(tmp_path: Path) -> None:
    roots = _inputs(tmp_path)
    result = census_sec_submissions_payloads(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    output = tmp_path / "output"
    output.mkdir(mode=0o700)

    target = seal_sec_submissions_payload_census(output_root=output, census=result)

    assert target.stat().st_mode & 0o777 == 0o400
    assert read_sealed_sec_submissions_payload_census(
        output_root=output,
        source_snapshot_date=date(2026, 9, 10),
        range_start=START,
        range_end=END,
    ) == result


def _ledger_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    roots = _inputs(tmp_path)
    submissions_census_root = tmp_path / "submissions-census"
    submissions_census_root.mkdir(mode=0o700)
    census = census_sec_submissions_payloads(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    seal_sec_submissions_payload_census(
        output_root=submissions_census_root, census=census
    )
    return (*roots, submissions_census_root)


def test_filing_clock_package_preserves_missing_and_maps_next_open(
    tmp_path: Path,
) -> None:
    roots = _ledger_inputs(tmp_path)
    output_root = tmp_path / "filing-clock"
    output_root.mkdir(mode=0o700)
    package = output_root / "build=fixture"

    result = build_sec_filing_clock_package(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        submissions_census_root=roots[5],
        output_package_path=package,
        range_start=START,
        range_end=END,
        worker_count=2,
        implementation_revision="a" * 40,
        built_at=NOW,
    )

    assert result.manifest.record_count == 3
    assert result.manifest.admitted_accession_count == 2
    assert result.manifest.quarantined_accession_count == 1
    assert result.manifest.conflicting_acceptance_accession_count == 1
    assert result.manifest.selected_midnight_acceptance_count == 1
    assert read_sec_filing_clock_package(package_path=package) == result
    rows = {
        row["accession_number"]: row
        for row in pq.ParquetFile(package / "filing-clocks.parquet").read().to_pylist()
    }
    assert rows["0000000001-24-000001"]["signal_eligible_session"] == date(
        2024, 8, 2
    )
    assert "acceptance_midnight_time_quality_warning" in rows[
        "0000000001-24-000001"
    ]["reason_codes"]
    assert rows["0000000001-25-000001"]["signal_eligible_session"] == date(
        2025, 8, 4
    )
    assert rows["0000000001-25-000001"]["availability_resolution"] == (
        "conservative_latest_conflict"
    )
    missing = rows["0000000001-26-000001"]
    assert missing["admission_status"] == "quarantined"
    assert missing["selected_source_available_at_utc"] is None
    assert missing["reason_codes"] == ["missing_submission_accession"]


def test_filing_clock_reader_rejects_mutable_artifact_mode(tmp_path: Path) -> None:
    roots = _ledger_inputs(tmp_path)
    output_root = tmp_path / "filing-clock"
    output_root.mkdir(mode=0o700)
    package = output_root / "build=fixture"
    build_sec_filing_clock_package(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        submissions_census_root=roots[5],
        output_package_path=package,
        range_start=START,
        range_end=END,
        worker_count=1,
        implementation_revision="a" * 40,
        built_at=NOW,
    )
    (package / "filing-clocks.parquet").chmod(0o600)

    try:
        read_sec_filing_clock_package(package_path=package)
    except RuntimeError as exc:
        assert "mode differs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("mutable filing-clock artifact was accepted")


def test_companyfacts_normalization_retains_every_occurrence_and_clock_state(
    tmp_path: Path,
) -> None:
    roots = _ledger_inputs(tmp_path)
    filing_clock_root = tmp_path / "filing-clock"
    filing_clock_root.mkdir(mode=0o700)
    filing_clock_package = filing_clock_root / "build=fixture"
    build_sec_filing_clock_package(
        submissions_custody_root=roots[0],
        submissions_package_path=roots[1],
        companyfacts_custody_root=roots[2],
        companyfacts_package_path=roots[3],
        companyfacts_census_root=roots[4],
        submissions_census_root=roots[5],
        output_package_path=filing_clock_package,
        range_start=START,
        range_end=END,
        worker_count=1,
        implementation_revision="a" * 40,
        built_at=NOW,
    )
    normalized_root = tmp_path / "normalized"
    normalized_root.mkdir(mode=0o700)
    normalized_package = normalized_root / "build=fixture"

    result = build_sec_companyfacts_normalized_source(
        companyfacts_package_path=roots[3],
        companyfacts_custody_root=roots[2],
        companyfacts_census_root=roots[4],
        filing_clock_package_path=filing_clock_package,
        output_package_path=normalized_package,
        range_start=START,
        range_end=END,
        worker_count=1,
        implementation_revision="b" * 40,
        built_at=NOW,
    )

    assert result.manifest.entity_count == 1
    assert result.manifest.concept_count == 1
    assert result.manifest.occurrence_count == 3
    assert result.manifest.clock_admitted_occurrence_count == 2
    assert result.manifest.clock_quarantined_occurrence_count == 1
    assert result.manifest.normalization_quarantined_occurrence_count == 1
    assert read_sec_companyfacts_normalized_source(
        package_path=normalized_package
    ) == result
    fact_rows = []
    for path in sorted(normalized_package.rglob("occurrences-*.parquet")):
        fact_rows.extend(pq.ParquetFile(path).read().to_pylist())
    assert len(fact_rows) == 3
    assert {row["value_text"] for row in fact_rows} == {"2024", "2025", "2026"}
    missing = next(
        row
        for row in fact_rows
        if row["accession_number"] == "0000000001-26-000001"
    )
    assert missing["normalization_status"] == "quarantined"
    assert missing["normalization_reason_codes"] == ["missing_filing_clock"]
    assert missing["source_available_at_utc"] is None
    assert missing["instrument_id"] is None
