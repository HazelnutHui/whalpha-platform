"""Outcome-blind field adjudication for five terminal-reference SEC files."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_sec_document_content_census as text
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import strong_leader_pullback_terminal_reference_sec_plan as plan
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_source as source,
)
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_supplement_plan as supplement_plan,
)
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_supplement_source as supplement_source,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-reference-sec-adjudication/1.0"
)
SUPPLEMENT_CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-reference-sec-supplement-adjudication/1.0"
)
EXPECTED_CASE_COUNT = 5
EXPECTED_SUPPLEMENT_CASE_COUNT = 2
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"


class TerminalReferenceSourceFieldState(StrEnum):
    MATCHED = "matched"
    UNSUPPORTED = "unsupported"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalReferenceSourceFieldV1(_FrozenModel):
    field_key: str = Field(min_length=1)
    expected_value: str = Field(min_length=1)
    state: TerminalReferenceSourceFieldState
    evidence_text: str | None = Field(default=None, max_length=768)
    evidence_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)

    @field_validator("evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != _normalize(value):
            raise ValueError("terminal-reference evidence text is not normalized")
        return value

    @model_validator(mode="after")
    def field_reconciles(self) -> "TerminalReferenceSourceFieldV1":
        matched = self.state is TerminalReferenceSourceFieldState.MATCHED
        if (
            matched != (self.evidence_text is not None)
            or matched != (self.evidence_sha256 is not None)
            or (
                self.evidence_text is not None
                and self.evidence_sha256
                != _sha256(self.evidence_text.encode("utf-8"))
            )
        ):
            raise ValueError("terminal-reference source field differs")
        return self


class TerminalReferenceSourceCaseV1(_FrozenModel):
    instrument_id: UUID
    ticker_locator: str
    source_cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str
    source_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    normalized_text_sha256: str = Field(pattern=_SHA256_PATTERN)
    fields: tuple[TerminalReferenceSourceFieldV1, ...] = Field(min_length=1)
    completion_status: Literal["matched", "unsupported"]
    terminal_reference_authorized: Literal[False] = False
    outcome_read: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def case_reconciles(self) -> "TerminalReferenceSourceCaseV1":
        keys = tuple(item.field_key for item in self.fields)
        matched = all(
            item.state is TerminalReferenceSourceFieldState.MATCHED
            for item in self.fields
        )
        if (
            keys != tuple(sorted(set(keys)))
            or self.completion_status != ("matched" if matched else "unsupported")
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-reference source case differs")
        return self


class StrongLeaderPullbackTerminalReferenceSecAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-sec-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["all_fields_matched", "source_fields_unresolved"]
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    case_count: Literal[5] = EXPECTED_CASE_COUNT
    matched_case_count: int = Field(ge=0, le=5)
    unsupported_case_count: int = Field(ge=0, le=5)
    cases: tuple[TerminalReferenceSourceCaseV1, ...] = Field(min_length=5)
    source_fact_count: int = Field(ge=0)
    terminal_reference_count: Literal[0] = 0
    outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceSecAdjudicationV1":
        keys = tuple(item.ticker_locator for item in self.cases)
        matched = sum(item.completion_status == "matched" for item in self.cases)
        source_facts = sum(
            item.state is TerminalReferenceSourceFieldState.MATCHED
            for case in self.cases
            for item in case.fields
        )
        if (
            len(self.cases) != EXPECTED_CASE_COUNT
            or keys != tuple(sorted(set(keys)))
            or self.matched_case_count != matched
            or self.unsupported_case_count != EXPECTED_CASE_COUNT - matched
            or self.source_fact_count != source_facts
            or self.completion_status
            != (
                "all_fields_matched"
                if matched == EXPECTED_CASE_COUNT
                else "source_fields_unresolved"
            )
            or self.ruleset_fingerprint != _fingerprint(_RULES)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-reference SEC adjudication differs")
        return self


class StrongLeaderPullbackTerminalReferenceSecSupplementAdjudicationV1(
    _FrozenModel
):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-sec-supplement-adjudication/1.0"
    ] = SUPPLEMENT_CONTRACT_VERSION
    completion_status: Literal["all_fields_matched", "source_fields_unresolved"]
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    case_count: Literal[2] = EXPECTED_SUPPLEMENT_CASE_COUNT
    matched_case_count: int = Field(ge=0, le=2)
    unsupported_case_count: int = Field(ge=0, le=2)
    cases: tuple[TerminalReferenceSourceCaseV1, ...] = Field(
        min_length=2, max_length=2
    )
    source_fact_count: int = Field(ge=0, le=3)
    terminal_reference_count: Literal[0] = 0
    outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceSecSupplementAdjudicationV1":
        keys = tuple(item.ticker_locator for item in self.cases)
        matched = sum(item.completion_status == "matched" for item in self.cases)
        source_facts = sum(
            item.state is TerminalReferenceSourceFieldState.MATCHED
            for case in self.cases
            for item in case.fields
        )
        expected_status = (
            "all_fields_matched"
            if matched == EXPECTED_SUPPLEMENT_CASE_COUNT
            else "source_fields_unresolved"
        )
        if (
            len(self.cases) != EXPECTED_SUPPLEMENT_CASE_COUNT
            or keys != tuple(sorted(set(keys)))
            or keys != tuple(_SUPPLEMENT_RULES)
            or self.matched_case_count != matched
            or self.unsupported_case_count
            != EXPECTED_SUPPLEMENT_CASE_COUNT - matched
            or self.source_fact_count != source_facts
            or self.completion_status != expected_status
            or self.ruleset_fingerprint != _fingerprint(_SUPPLEMENT_RULES)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError(
                "terminal-reference SEC supplement adjudication differs"
            )
        return self


_RULES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "LNW": (
        (
            "foreign_sole_listing_date",
            "2025-11-14",
            r"(?:sole|only).{0,240}(?:ASX|Australian Securities Exchange)"
            r".{0,240}November 14, 2025|November 14, 2025.{0,240}"
            r"(?:sole|only).{0,240}(?:ASX|Australian Securities Exchange)",
        ),
        (
            "last_us_trading_date",
            "2025-11-12",
            r"(?:last|final).{0,160}(?:trade|trading).{0,160}Nasdaq"
            r".{0,240}November 12, 2025|November 12, 2025.{0,240}"
            r"(?:last|final).{0,160}(?:trade|trading).{0,160}Nasdaq",
        ),
    ),
    "MTSR": (
        ("cash_usd", "65.60", r"\$\s*65\.60.{0,240}(?:cash|share)"),
        (
            "cvr_cap_usd",
            "20.65",
            r"(?:CVR|contingent value right).{0,480}"
            r"(?:up to|maximum|aggregate).{0,160}\$\s*20\.65|"
            r"\$\s*20\.65.{0,320}(?:CVR|contingent value right)",
        ),
    ),
    "REVG": (
        (
            "cash_usd",
            "8.71",
            r"\$\s*8\.71.{0,480}0\.9809|0\.9809.{0,480}\$\s*8\.71",
        ),
        (
            "listed_equity_ratio",
            "0.9809",
            r"0\.9809.{0,240}(?:Terex|common stock|common shares)",
        ),
    ),
    "SAND": (
        (
            "listed_equity_ratio",
            "0.0625",
            r"0\.0625.{0,320}(?:Royal Gold|common share|common stock)",
        ),
    ),
    "SKX": (
        (
            "cash_election_usd",
            "63.00",
            r"\$\s*63(?:\.00)?.{0,240}cash|cash.{0,240}\$\s*63"
            r"(?:\.00)?.{0,240}(?:purchase price|per share)",
        ),
        (
            "mixed_cash_usd",
            "57.00",
            r"\$\s*57(?:\.00)?.{0,320}(?:Common Unit|common unit)",
        ),
        (
            "unlisted_unit_count",
            "1.000000",
            r"(?:one|1).{0,100}(?:Common Unit|common unit)",
        ),
        (
            "unlisted_unit_value_usd",
            "29.00",
            r"(?:market value|fair value).{0,320}(?:Common Unit|common unit)"
            r".{0,320}\$\s*29(?:\.00)?|(?:Common Unit|common unit).{0,320}"
            r"(?:market value|fair value).{0,320}\$\s*29(?:\.00)?",
        ),
    ),
}


_SUPPLEMENT_RULES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "REVG": (
        (
            "cash_usd",
            "8.71",
            r"\$\s*8\.71.{0,480}0\.9809|0\.9809.{0,480}\$\s*8\.71",
        ),
        (
            "listed_equity_ratio",
            "0.9809",
            r"0\.9809.{0,240}(?:Terex|combined company|common stock|share)",
        ),
    ),
    "SKX": (
        (
            "mixed_cash_usd",
            "57.00",
            r"\$\s*57(?:\.00)?.{0,320}(?:one|1).{0,120}"
            r"(?:Common Unit|common limited liability company unit)",
        ),
    ),
}


def adjudicate_strong_leader_pullback_terminal_reference_sec_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecAdjudicationV1:
    """Adjudicate only preregistered fields from formally retained documents."""

    plan_result = plan.read_strong_leader_pullback_terminal_reference_sec_plan(
        output_root=plan_root, output_custody_root=plan_custody_root
    )
    source_result = source.read_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody_root,
        output_root=source_root,
        output_custody_root=source_custody_root,
    )
    cases = tuple(
        _adjudicate_case(
            item=item,
            document_path=(
                source_result.output_root
                / f"request={item.request_sequence:06d}"
                / source_base.DOCUMENT_FILE
            ),
        )
        for item in plan_result.report.items
    )
    matched = sum(item.completion_status == "matched" for item in cases)
    values = {
        "completion_status": (
            "all_fields_matched"
            if matched == EXPECTED_CASE_COUNT
            else "source_fields_unresolved"
        ),
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "plan_report_sha256": plan_result.report_sha256,
        "plan_logical_fingerprint": plan_result.report.logical_fingerprint,
        "source_manifest_sha256": source_result.manifest_sha256,
        "source_logical_fingerprint": source_result.manifest.logical_fingerprint,
        "ruleset_fingerprint": _fingerprint(_RULES),
        "matched_case_count": matched,
        "unsupported_case_count": EXPECTED_CASE_COUNT - matched,
        "cases": cases,
        "source_fact_count": sum(
            field.state is TerminalReferenceSourceFieldState.MATCHED
            for case in cases
            for field in case.fields
        ),
    }
    report_class = StrongLeaderPullbackTerminalReferenceSecAdjudicationV1
    provisional = report_class.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return report_class.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def adjudicate_strong_leader_pullback_terminal_reference_sec_supplement_source(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecSupplementAdjudicationV1:
    """Adjudicate only the three fields missing from the initial batch."""

    plan_result = (
        supplement_plan
        .read_strong_leader_pullback_terminal_reference_sec_supplement_plan(
            output_root=plan_root,
            output_custody_root=plan_custody_root,
        )
    )
    source_result = (
        supplement_source
        .read_strong_leader_pullback_terminal_reference_sec_supplement_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
    )
    cases = tuple(
        _adjudicate_case(
            item=item,
            document_path=(
                source_result.output_root
                / f"request={item.request_sequence:06d}"
                / source_base.DOCUMENT_FILE
            ),
            rules=_SUPPLEMENT_RULES[item.ticker_locator],
        )
        for item in plan_result.report.items
    )
    matched = sum(item.completion_status == "matched" for item in cases)
    values = {
        "completion_status": (
            "all_fields_matched"
            if matched == EXPECTED_SUPPLEMENT_CASE_COUNT
            else "source_fields_unresolved"
        ),
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "plan_report_sha256": plan_result.report_sha256,
        "plan_logical_fingerprint": plan_result.report.logical_fingerprint,
        "source_manifest_sha256": source_result.manifest_sha256,
        "source_logical_fingerprint": source_result.manifest.logical_fingerprint,
        "ruleset_fingerprint": _fingerprint(_SUPPLEMENT_RULES),
        "matched_case_count": matched,
        "unsupported_case_count": EXPECTED_SUPPLEMENT_CASE_COUNT - matched,
        "cases": cases,
        "source_fact_count": sum(
            field.state is TerminalReferenceSourceFieldState.MATCHED
            for case in cases
            for field in case.fields
        ),
    }
    report_class = (
        StrongLeaderPullbackTerminalReferenceSecSupplementAdjudicationV1
    )
    provisional = report_class.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return report_class.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def _adjudicate_case(
    *,
    item: plan.TerminalReferenceSecPlanItemV1,
    document_path: Path,
    rules: tuple[tuple[str, str, str], ...] | None = None,
) -> TerminalReferenceSourceCaseV1:
    raw = document_path.read_bytes()
    decoded, _ = text._decode(raw)
    parser = text._DocumentTextParser()
    parser.feed(decoded)
    parser.close()
    normalized = _normalize(" ".join(parser.parts))
    active_rules = rules or _RULES[item.ticker_locator]
    fields = tuple(
        _match_field(normalized=normalized, key=key, value=value, pattern=pattern)
        for key, value, pattern in sorted(active_rules)
    )
    matched = all(
        field.state is TerminalReferenceSourceFieldState.MATCHED
        for field in fields
    )
    values = {
        "instrument_id": item.instrument_id,
        "ticker_locator": item.ticker_locator,
        "source_cik": item.source_cik,
        "accession_number": item.accession_number,
        "source_document_sha256": _sha256(raw),
        "normalized_text_sha256": _sha256(normalized.encode("utf-8")),
        "fields": fields,
        "completion_status": "matched" if matched else "unsupported",
    }
    provisional = TerminalReferenceSourceCaseV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalReferenceSourceCaseV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def _match_field(
    *, normalized: str, key: str, value: str, pattern: str
) -> TerminalReferenceSourceFieldV1:
    match = re.search(pattern, normalized, flags=re.IGNORECASE)
    if match is None:
        return TerminalReferenceSourceFieldV1(
            field_key=key,
            expected_value=value,
            state=TerminalReferenceSourceFieldState.UNSUPPORTED,
        )
    start = max(0, match.start() - 96)
    end = min(len(normalized), match.end() + 96)
    evidence = _normalize(normalized[start:end])
    return TerminalReferenceSourceFieldV1(
        field_key=key,
        expected_value=value,
        state=TerminalReferenceSourceFieldState.MATCHED,
        evidence_text=evidence,
        evidence_sha256=_sha256(evidence.encode("utf-8")),
    )


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _fingerprint(value: object) -> str:
    return _sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
