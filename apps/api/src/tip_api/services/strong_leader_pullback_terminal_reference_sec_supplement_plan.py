"""Freeze two SEC supplements for unresolved terminal-reference fields."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    read_sec_submissions_source_package,
)
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_plan as base,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-reference-sec-supplement-plan/1.0"
)
REPORT_FILE = "terminal-reference-sec-supplement-plan.json"
EXPECTED_REQUEST_COUNT = 2
MAXIMUM_REQUESTS_PER_SECOND = 2
MAXIMUM_RETRIES_PER_REQUEST = 2
MAXIMUM_DOCUMENT_BYTES = 64 * 1024 * 1024
MAXIMUM_REPORT_BYTES = 64 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"


class TerminalReferenceSecSupplementPlanError(RuntimeError):
    """Raised when the two-document supplemental plan cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-sec-supplement-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["planned_not_executed"] = "planned_not_executed"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    planned_at: datetime
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_completed_at: datetime
    selection_rule: Literal[
        "two_unresolved_initial_batch_fields_official_documents_v1"
    ] = "two_unresolved_initial_batch_fields_official_documents_v1"
    planned_request_count: Literal[2] = EXPECTED_REQUEST_COUNT
    unique_url_count: Literal[2] = EXPECTED_REQUEST_COUNT
    allowed_hosts: tuple[Literal["www.sec.gov"], ...] = ("www.sec.gov",)
    maximum_requests_per_second: Literal[2] = MAXIMUM_REQUESTS_PER_SECOND
    maximum_retries_per_request: Literal[2] = MAXIMUM_RETRIES_PER_REQUEST
    maximum_document_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    items: tuple[base.TerminalReferenceSecPlanItemV1, ...] = Field(
        min_length=2, max_length=2
    )
    external_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
    document_write_count: Literal[0] = 0
    source_field_adjudication_count: Literal[0] = 0
    outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("planned_at", "submissions_completed_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1":
        sequences = tuple(item.request_sequence for item in self.items)
        tickers = tuple(item.ticker_locator for item in self.items)
        urls = tuple(item.request_url for item in self.items)
        registered = tuple(
            (
                str(item.instrument_id),
                item.ticker_locator,
                item.source_cik,
                item.accession_number,
                item.requested_document,
                item.missing_source_role,
                item.planned_reference_policy,
            )
            for item in self.items
        )
        expected = tuple(
            (
                item["instrument_id"],
                item["ticker_locator"],
                item["source_cik"],
                item["accession_number"],
                item["requested_document"],
                item["missing_source_role"],
                item["planned_reference_policy"],
            )
            for item in _REQUESTS
        )
        if (
            self.planned_at < self.submissions_completed_at
            or len(self.items) != EXPECTED_REQUEST_COUNT
            or sequences != tuple(range(1, EXPECTED_REQUEST_COUNT + 1))
            or tickers != tuple(sorted(set(tickers)))
            or len(set(urls)) != self.unique_url_count
            or registered != expected
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-reference SEC supplement plan differs")
        return self


_REQUESTS = (
    {
        "instrument_id": "2537e45b-62a8-5a96-9b7b-f30ba708645c",
        "ticker_locator": "REVG",
        "source_cik": "0000097216",
        "source_party_role": "acquirer_filer",
        "accession_number": "0000097216-26-000124",
        "form": "8-K",
        "filing_date": "2026-07-31",
        "acceptance_datetime": "2026-07-31T17:01:55Z",
        "submissions_primary_document": "tex-20260731.htm",
        "requested_document": "exhibit992-texxrevproforma.htm",
        "missing_source_role": "listed_consideration_terms",
        "planned_reference_policy": "zero_to_listed_consideration_max",
    },
    {
        "instrument_id": "714c4ae2-2938-5196-a02f-198c6b5b8415",
        "ticker_locator": "SKX",
        "source_cik": "0001065837",
        "source_party_role": "target_filer",
        "accession_number": "0001104659-25-074187",
        "form": "DEFM14C",
        "filing_date": "2025-08-05",
        "acceptance_datetime": "2025-08-05T16:13:28Z",
        "submissions_primary_document": "tm2516935-12_defm14c.htm",
        "requested_document": "tm2516935-12_defm14c.htm",
        "missing_source_role": "unlisted_unit_acquisition_value",
        "planned_reference_policy": "zero_to_unlisted_consideration_value",
    },
)


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalReferenceSecSupplementPlanResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_reference_sec_supplement_plan(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1:
    """Build an outcome-blind plan from retained SEC Submissions metadata."""

    source = read_sec_submissions_source_package(
        package_path=submissions_package_path,
        approved_custody_root=submissions_custody_root,
    )
    items: list[base.TerminalReferenceSecPlanItemV1] = []
    try:
        with zipfile.ZipFile(submissions_package_path / ARCHIVE_FILE) as handle:
            for sequence, registered in enumerate(_REQUESTS, start=1):
                base._validate_submission_metadata(
                    zip_handle=handle, registered=registered
                )
                items.append(
                    base.TerminalReferenceSecPlanItemV1.model_validate(
                        {
                            **registered,
                            "request_sequence": sequence,
                            "request_url": base._document_url(
                                cik=str(registered["source_cik"]),
                                accession=str(registered["accession_number"]),
                                primary_document=str(
                                    registered["requested_document"]
                                ),
                            ),
                        }
                    )
                )
    except (
        OSError,
        zipfile.BadZipFile,
        KeyError,
        json.JSONDecodeError,
        base.TerminalReferenceSecPlanError,
    ) as exc:
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement submissions read failed"
        ) from exc
    values = {
        "implementation_revision": implementation_revision,
        "planned_at": normalize_utc_datetime(planned_at),
        "submissions_source_fingerprint": source.logical_fingerprint,
        "submissions_archive_sha256": source.archive_sha256,
        "submissions_completed_at": source.completed_at,
        "items": tuple(items),
    }
    report_class = StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1
    provisional = report_class.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return report_class.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def publish_strong_leader_pullback_terminal_reference_sec_supplement_plan(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecSupplementPlanResult:
    """Publish and formally reread the immutable supplemental plan."""

    report = build_strong_leader_pullback_terminal_reference_sec_supplement_plan(
        submissions_package_path=submissions_package_path,
        submissions_custody_root=submissions_custody_root,
        implementation_revision=implementation_revision,
        planned_at=planned_at,
    )
    target = base._validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_reference_sec_supplement_plan(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise TerminalReferenceSecSupplementPlanError(
                "existing terminal-reference SEC supplement plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement plan staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise TerminalReferenceSecSupplementPlanError(
                "terminal-reference SEC supplement plan exceeds byte ceiling"
            )
        base._write_exclusive(partial / REPORT_FILE, raw)
        base._fsync_directory(partial)
        partial.replace(target)
        base._fsync_directory(target.parent)
    except Exception:
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            base._fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_reference_sec_supplement_plan(
        output_root=target, output_custody_root=output_custody_root
    )
    if reread.report != report:
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement plan reread differs"
        )
    return StrongLeaderPullbackTerminalReferenceSecSupplementPlanResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def read_strong_leader_pullback_terminal_reference_sec_supplement_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalReferenceSecSupplementPlanResult:
    """Reread the immutable two-document plan without network access."""

    root = base._validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement plan members differ"
        )
    path = root / REPORT_FILE
    base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = (
            StrongLeaderPullbackTerminalReferenceSecSupplementPlanV1
            .model_validate_json(raw)
        )
    except Exception as exc:
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement plan is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise TerminalReferenceSecSupplementPlanError(
            "terminal-reference SEC supplement plan bytes differ"
        )
    return StrongLeaderPullbackTerminalReferenceSecSupplementPlanResult(
        output_root=root,
        report=report,
        report_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )
