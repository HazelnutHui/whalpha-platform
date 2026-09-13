from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.sec.companyfacts_payload_census import (
    SecCompanyfactsPayloadCensusError,
    census_sec_companyfacts_payloads,
    extract_sec_companyfacts_in_range_accessions,
    read_sealed_sec_companyfacts_payload_census,
    seal_sec_companyfacts_payload_census,
)
from tip_api.providers.sec.companyfacts_source import (
    COMPANYFACTS_URL,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsRangeResult,
    SecCompanyfactsRemoteMetadataV1,
    acquire_sec_companyfacts_source_package,
)
from tip_api.providers.sec.config import SecProviderConfig


NOW = datetime(2026, 9, 10, 13, tzinfo=UTC)
START = date(2021, 8, 11)
END = date(2026, 9, 9)


class NoWait(SecCompanyfactsFixedIntervalLimiter):
    def __init__(self) -> None:
        pass

    def wait(self) -> None:
        return None


class FixtureTransport:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def head(self, **kwargs: object) -> SecCompanyfactsRemoteMetadataV1:
        return SecCompanyfactsRemoteMetadataV1(
            url=COMPANYFACTS_URL,
            content_type="application/zip",
            content_length=len(self.payload),
            last_modified=datetime(2026, 9, 10, 3, tzinfo=UTC),
            etag='"fixture"',
            accept_ranges="bytes",
            observed_at=kwargs["observed_at"],  # type: ignore[arg-type]
        )

    def download_range(self, **kwargs: object) -> SecCompanyfactsRangeResult:
        start = int(kwargs["byte_start"])
        end = int(kwargs["byte_end"])
        selected = self.payload[start : end + 1]
        kwargs["target"].write(selected)  # type: ignore[attr-defined]
        import hashlib

        return SecCompanyfactsRangeResult(
            byte_count=len(selected),
            physical_sha256=hashlib.sha256(selected).hexdigest(),
        )


def _archive() -> bytes:
    facts = {
        "cik": 1,
        "entityName": "Fixture Issuer",
        "facts": {
            "us-gaap": {
                "Revenue": {
                    "label": "Revenue",
                    "description": "Fixture",
                    "unexpectedConcept": "preserved in census",
                    "units": {
                        "USD": [
                            {
                                "start": "2020-01-01",
                                "end": "2020-12-31",
                                "val": 10,
                                "accn": "0000000001-20-000001",
                                "form": "10-K",
                                "filed": "2021-03-01",
                            },
                            {
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "val": 12.5,
                                "accn": "0000000001-25-000001",
                                "form": "10-K/A",
                                "filed": "2025-03-01",
                                "frame": "CY2024",
                                "unexpectedFact": True,
                            },
                            {
                                "end": "2026-09-09",
                                "val": "n/a",
                                "accn": "invalid",
                                "form": "8-K",
                                "filed": "2026-09-10",
                            },
                            "malformed fact item",
                        ]
                    },
                }
            }
        },
        "unexpectedRoot": "preserved in census",
    }
    malformed = {
        "cik": 3,
        "entityName": "Quarantined Issuer",
        "facts": {"us-gaap": {"Revenue": {"units": "invalid"}}},
    }
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("CIK0000000001.json", json.dumps(facts))
        archive.writestr("CIK0000000002.json", "{}")
        archive.writestr("CIK0000000003.json", json.dumps(malformed))
        archive.writestr(
            "CIK0000000004.json",
            json.dumps({"cik": "0000000004", "entityName": "", "facts": {}}),
        )
    return target.getvalue()


def _source(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "source"
    root.mkdir(mode=0o700)
    package = root / "snapshot=2026-09-10"
    config = SecProviderConfig(
        user_agent=SecretStr("trading-intelligence-platform test@example.com"),
        request_timeout_seconds=Decimal("15"),
    )
    acquire_sec_companyfacts_source_package(
        config=config,
        package_path=package,
        approved_custody_root=root,
        transport=FixtureTransport(_archive()),
        rate_limiter=NoWait(),
        clock=lambda: NOW,
    )
    return root, package


def test_payload_census_reads_all_members_and_preserves_anomalies(tmp_path: Path) -> None:
    root, package = _source(tmp_path)

    result = census_sec_companyfacts_payloads(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )

    assert result.source_member_count == result.payload_read_member_count == 4
    assert result.populated_member_count == 1
    assert result.empty_object_member_count == 1
    assert result.empty_facts_member_count == 1
    assert result.quarantined_member_count == 1
    assert result.quarantined_members[0].reason_code == "malformed_concept"
    assert result.payload_validation_status == "complete_with_quarantined_members"
    assert result.fact_count == 3
    assert result.malformed_fact_count == 1
    assert result.fact_filed_before_range_count == 1
    assert result.fact_filed_in_range_count == 1
    assert result.fact_filed_after_range_count == 1
    assert result.unique_accession_count == 2
    assert result.in_range_unique_accession_count == 1
    assert result.invalid_or_missing_accession_count == 1
    assert result.duration_fact_count == 2
    assert result.instant_fact_count == 1
    assert result.amended_form_fact_count == 1
    assert result.frame_present_fact_count == 1
    assert dict(result.unexpected_root_field_counts) == {"unexpectedRoot": 1}
    assert dict(result.unexpected_concept_field_counts) == {"unexpectedConcept": 1}
    assert dict(result.unexpected_fact_field_counts) == {"unexpectedFact": 1}
    assert result.acceptance_timestamp_count == 0
    assert result.filed_date_same_day_eligibility is False


def test_payload_census_is_equivalent_across_worker_counts(tmp_path: Path) -> None:
    root, package = _source(tmp_path)
    one = census_sec_companyfacts_payloads(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    two = census_sec_companyfacts_payloads(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=2,
        evaluated_at=NOW,
    )

    assert one.model_dump(exclude={"worker_count", "logical_fingerprint"}) == two.model_dump(
        exclude={"worker_count", "logical_fingerprint"}
    )


def test_payload_census_seal_is_owner_only_and_formally_readable(tmp_path: Path) -> None:
    root, package = _source(tmp_path)
    result = census_sec_companyfacts_payloads(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    output = tmp_path / "output"
    output.mkdir(mode=0o700)

    target = seal_sec_companyfacts_payload_census(output_root=output, census=result)

    assert target.stat().st_mode & 0o777 == 0o400
    assert read_sealed_sec_companyfacts_payload_census(
        output_root=output,
        source_snapshot_date=date(2026, 9, 10),
        range_start=START,
        range_end=END,
    ) == result
    with pytest.raises(FileExistsError):
        seal_sec_companyfacts_payload_census(output_root=output, census=result)


def test_payload_census_output_root_must_be_owner_only(tmp_path: Path) -> None:
    root, package = _source(tmp_path)
    result = census_sec_companyfacts_payloads(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=1,
        evaluated_at=NOW,
    )
    output = tmp_path / "unsafe-output"
    output.mkdir(mode=0o755)

    with pytest.raises(SecCompanyfactsPayloadCensusError, match="mode differs"):
        seal_sec_companyfacts_payload_census(output_root=output, census=result)


def test_accession_extraction_matches_admitted_in_range_census(tmp_path: Path) -> None:
    root, package = _source(tmp_path)

    accessions = extract_sec_companyfacts_in_range_accessions(
        source_package_path=package,
        source_custody_root=root,
        range_start=START,
        range_end=END,
        worker_count=2,
    )

    assert accessions == {"0000000001-25-000001": (date(2025, 3, 1),)}
