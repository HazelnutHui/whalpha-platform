"""Strict listed-security identity and reference values for the SCS terminal case."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    read_sec_submissions_source_package,
)
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import (
    strong_leader_pullback_terminal_population_payoff_policy as policy_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_core_adjudication as core_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_trading_cessation_adjudication as cessation_reader,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-listed-reference/1.0"
)
REPORT_FILE = "listed-reference.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
MAXIMUM_SUBMISSIONS_MEMBER_BYTES = 8 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_PRICE_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{10}$"
_VALUE_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{16}$"
_CASH_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$"
_RATIO_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"

TARGET_INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")
HNI_INSTRUMENT_ID = UUID("8bde034d-a7f8-5dce-a432-134c583eb9ac")
HNI_CIK = "0000048287"
VALUATION_SESSION = date(2025, 12, 10)
HNI_SUBMISSIONS_MEMBER = f"CIK{HNI_CIK}.json"
HNI_EVENT_ACCESSION = "0000950103-25-015967"
HNI_EVENT_PRIMARY_DOCUMENT = "dp238589_8k.htm"
HNI_EVENT_ACCEPTED_AT = datetime.fromisoformat("2025-12-10T21:49:32+00:00")

_ALTERNATIVE_TERMS = {
    "cash_election": ("cash_election_cash", "cash_election_stock_ratio"),
    "mixed_election": ("mixed_election_cash", "mixed_election_stock_ratio"),
    "stock_election": ("stock_election_stock_ratio",),
}


class StrongLeaderPullbackTerminalPopulationListedReferenceError(RuntimeError):
    """Raised when the corrected listed reference cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalPopulationListedIdentityV1(_FrozenModel):
    resolution_state: Literal["strict_stable_security_match"] = (
        "strict_stable_security_match"
    )
    source_target_instrument_id: UUID
    source_issuer_locator: Literal["HNI"] = "HNI"
    source_issuer_name: Literal["HNI Corporation"] = "HNI Corporation"
    source_security_title: Literal["HNI common stock"] = "HNI common stock"
    sec_submissions_member: Literal["CIK0000048287.json"] = HNI_SUBMISSIONS_MEMBER
    sec_submissions_member_sha256: str = Field(pattern=_SHA256_PATTERN)
    sec_cik: Literal["0000048287"] = HNI_CIK
    sec_entity_type: Literal["operating"] = "operating"
    sec_issuer_name: Literal["HNI CORP"] = "HNI CORP"
    sec_ticker: Literal["HNI"] = "HNI"
    sec_exchange: Literal["NYSE"] = "NYSE"
    sec_event_accession_number: Literal["0000950103-25-015967"] = (
        HNI_EVENT_ACCESSION
    )
    sec_event_acceptance_datetime: datetime
    sec_event_primary_document: Literal["dp238589_8k.htm"] = (
        HNI_EVENT_PRIMARY_DOCUMENT
    )
    canonical_evidence_session: date = VALUATION_SESSION
    assigned_consideration_instrument_id: UUID
    canonical_instrument_type: Literal["common_stock"] = "common_stock"
    canonical_status: Literal["active"] = "active"
    canonical_ticker: Literal["HNI"] = "HNI"
    canonical_name: Literal["HNI Corporation"] = "HNI Corporation"
    canonical_exchange: Literal["XNYS"] = "XNYS"
    canonical_listing_country: Literal["US"] = "US"
    canonical_currency: Literal["USD"] = "USD"
    canonical_cik: Literal["0000048287"] = HNI_CIK
    canonical_figi: Literal["BBG000C7QK61"] = "BBG000C7QK61"
    canonical_source: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    canonical_source_instrument_id: Literal[
        "share_class_figi:BBG001S6Q6F5"
    ] = "share_class_figi:BBG001S6Q6F5"
    canonical_quality_status: Literal["valid"] = "valid"
    identity_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("sec_event_acceptance_datetime")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed-reference identity reasons differ")
        return values

    @model_validator(mode="after")
    def identity_reconciles(self) -> "TerminalPopulationListedIdentityV1":
        if (
            self.source_target_instrument_id != TARGET_INSTRUMENT_ID
            or self.assigned_consideration_instrument_id != HNI_INSTRUMENT_ID
            or self.canonical_evidence_session != VALUATION_SESSION
            or self.sec_event_acceptance_datetime != HNI_EVENT_ACCEPTED_AT
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-reference identity differs")
        return self


class TerminalPopulationAlternativeReferenceV1(_FrozenModel):
    alternative_code: Literal["cash_election", "mixed_election", "stock_election"]
    term_keys: tuple[str, ...] = Field(min_length=1)
    term_fingerprints: tuple[str, ...] = Field(min_length=1)
    default_if_no_valid_election: bool
    cash_amount_usd: str = Field(pattern=_CASH_PATTERN)
    listed_equity_ratio: str = Field(pattern=_RATIO_PATTERN)
    consideration_close_usd: str = Field(pattern=_PRICE_PATTERN)
    listed_equity_component_value_usd: str = Field(pattern=_VALUE_PATTERN)
    gross_reference_value_usd: str = Field(pattern=_VALUE_PATTERN)
    automatic_adjustment_details_resolved: Literal[False] = False
    proration_state: Literal["not_stated_in_retained_completion_scope"] = (
        "not_stated_in_retained_completion_scope"
    )
    actual_holder_election_proven: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("term_keys", "term_fingerprints", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed-reference alternative tuple differs")
        return values

    @model_validator(mode="after")
    def alternative_reconciles(self) -> "TerminalPopulationAlternativeReferenceV1":
        try:
            cash = Decimal(self.cash_amount_usd)
            ratio = Decimal(self.listed_equity_ratio)
            close = Decimal(self.consideration_close_usd)
            component = Decimal(self.listed_equity_component_value_usd)
            total = Decimal(self.gross_reference_value_usd)
        except InvalidOperation as exc:
            raise ValueError("listed-reference alternative decimal differs") from exc
        if (
            self.term_keys != tuple(sorted(_ALTERNATIVE_TERMS[self.alternative_code]))
            or component != ratio * close
            or total != cash + component
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-reference alternative differs")
        return self


class StrongLeaderPullbackTerminalPopulationListedReferenceV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-listed-reference/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "strict_identity_and_three_daily_reference_values_documented"
    ] = "strict_identity_and_three_daily_reference_values_documented"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_policy_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_policy_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    sec_submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    sec_submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    sec_submissions_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    sec_snapshot_completed_at: datetime
    identity: TerminalPopulationListedIdentityV1
    valuation_session: date = VALUATION_SESSION
    valuation_session_record_count: int = Field(ge=1)
    valuation_session_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    valuation_session_parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    valuation_identity_snapshot_date: date = VALUATION_SESSION
    valuation_identity_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_partition_created_at: datetime
    consideration_close_usd: str = Field(pattern=_PRICE_PATTERN)
    price_source: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    price_revision: Literal[1] = 1
    price_quality_status: Literal["valid"] = "valid"
    price_quality_flags: tuple[str, ...]
    alternatives: tuple[TerminalPopulationAlternativeReferenceV1, ...]
    primary_reference_alternative: Literal["mixed_election"] = "mixed_election"
    primary_gross_reference_value_usd: str = Field(pattern=_VALUE_PATTERN)
    sensitivity_min_gross_reference_value_usd: str = Field(pattern=_VALUE_PATTERN)
    sensitivity_max_gross_reference_value_usd: str = Field(pattern=_VALUE_PATTERN)
    sensitivity_range_usd: str = Field(pattern=_VALUE_PATTERN)
    terminal_reference_case_count: Literal[1] = 1
    alternative_reference_value_count: Literal[3] = 3
    consideration_issuer_stable_id_assignment_count: Literal[1] = 1
    actual_holder_election_count: Literal[0] = 0
    canonical_terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    forward_return_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "evaluated_at", "sec_snapshot_completed_at", "canonical_partition_created_at"
    )
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("price_quality_flags", mode="before")
    @classmethod
    def flags_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed-reference quality flags differ")
        return values

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationListedReferenceV1":
        codes = tuple(item.alternative_code for item in self.alternatives)
        values = tuple(Decimal(item.gross_reference_value_usd) for item in self.alternatives)
        primary = next(
            item for item in self.alternatives if item.alternative_code == "mixed_election"
        )
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.valuation_session != VALUATION_SESSION
            or self.valuation_identity_snapshot_date != VALUATION_SESSION
            or codes != ("cash_election", "mixed_election", "stock_election")
            or tuple(
                item.alternative_code
                for item in self.alternatives
                if item.default_if_no_valid_election
            )
            != ("mixed_election",)
            or self.primary_gross_reference_value_usd
            != primary.gross_reference_value_usd
            or Decimal(self.sensitivity_min_gross_reference_value_usd) != min(values)
            or Decimal(self.sensitivity_max_gross_reference_value_usd) != max(values)
            or Decimal(self.sensitivity_range_usd) != max(values) - min(values)
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-reference report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationListedReferenceResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationListedReferenceV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_listed_reference(
    *,
    payoff_policy_root: Path,
    payoff_policy_custody_root: Path,
    core_adjudication_root: Path,
    core_adjudication_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    submissions_package_root: Path,
    submissions_custody_root: Path,
    canonical_eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationListedReferenceResult:
    """Bind HNI and calculate three daily references without creating an outcome."""

    with base._network_prohibited():
        policy = policy_reader.read_strong_leader_pullback_terminal_population_payoff_policy(
            output_root=payoff_policy_root,
            output_custody_root=payoff_policy_custody_root,
        )
        core = core_reader.read_strong_leader_pullback_terminal_population_sec_core_adjudication(
            output_root=core_adjudication_root,
            output_custody_root=core_adjudication_custody_root,
        )
        cessation = (
            cessation_reader.read_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
                output_root=cessation_root,
                output_custody_root=cessation_custody_root,
            )
        )
        submissions = read_sec_submissions_source_package(
            package_path=submissions_package_root,
            approved_custody_root=submissions_custody_root,
        )
        member_sha256, submission_payload = _read_hni_submission(
            submissions_package_root / ARCHIVE_FILE
        )
        repository = CanonicalEodReadRepository(canonical_eod_root)
        history = repository.read_history_sessions((VALUATION_SESSION,))
        if len(history) != 1 or history[0].available_at is None:
            raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                "HNI valuation session custody differs"
            )
        report = _build_report(
            policy=policy,
            core=core,
            cessation=cessation,
            submissions=submissions,
            submissions_manifest_sha256=base._sha256_bytes(
                (submissions_package_root / "package.json").read_bytes()
            ),
            submissions_member_sha256=member_sha256,
            submission_payload=submission_payload,
            integrity=history[0].integrity,
            available_at=history[0].available_at,
            instruments=repository.read_instruments_for_session(VALUATION_SESSION),
            records=repository.read_canonical_records(VALUATION_SESSION),
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_listed_reference(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationListedReferenceResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationListedReferenceV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationListedReferenceResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    policy: Any,
    core: Any,
    cessation: Any,
    submissions: Any,
    submissions_manifest_sha256: str,
    submissions_member_sha256: str,
    submission_payload: dict[str, Any],
    integrity: Any,
    available_at: datetime,
    instruments: tuple[Any, ...],
    records: tuple[Any, ...],
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationListedReferenceV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference revision is invalid"
        )
    policy_report = policy.report
    core_report = core.report
    cessation_report = cessation.report
    if (
        policy_report.core_adjudication_report_sha256 != core.report_sha256
        or policy_report.core_adjudication_logical_fingerprint
        != core_report.logical_fingerprint
        or policy_report.cessation_report_sha256 != cessation.report_sha256
        or policy_report.cessation_logical_fingerprint
        != cessation_report.logical_fingerprint
        or policy_report.listed_equity_issuer_locator != "HNI"
        or policy_report.party_relation.instrument_id != TARGET_INSTRUMENT_ID
        or "HNI Corporation" not in policy_report.party_relation.party_definition_text
        or "HNI common stock" not in core_report.common_share_consideration.evidence_text
        or cessation_report.decision.resolution_state != "matched"
        or cessation_report.decision.next_exchange_session != VALUATION_SESSION
        or cessation_report.decision.observed_last_eod_session >= VALUATION_SESSION
        or submissions.logical_fingerprint == ""
    ):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference upstream binding differs"
        )
    _validate_hni_submission(submission_payload)
    identity_matches = tuple(
        item for item in instruments if item.instrument_id == HNI_INSTRUMENT_ID
    )
    price_matches = tuple(
        item for item in records if item.instrument_id == HNI_INSTRUMENT_ID
    )
    if len(identity_matches) != 1 or len(price_matches) != 1:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI canonical evidence cardinality differs"
        )
    instrument = identity_matches[0]
    bar = price_matches[0]
    if (
        instrument.instrument_type.value != "common_stock"
        or instrument.status.value != "active"
        or instrument.ticker != "HNI"
        or instrument.name != "HNI Corporation"
        or instrument.primary_exchange != "XNYS"
        or instrument.listing_country != "US"
        or instrument.currency != "USD"
        or instrument.cik != HNI_CIK
        or instrument.figi != "BBG000C7QK61"
        or instrument.source != "massive_stocks_basic"
        or instrument.source_instrument_id != "share_class_figi:BBG001S6Q6F5"
        or instrument.quality_status.value != "valid"
        or bar.session_date != VALUATION_SESSION
        or bar.currency != "USD"
        or bar.source != "massive_stocks_basic"
        or bar.revision != 1
        or not bar.is_latest_revision
        or bar.quality_status.value != "valid"
        or bar.close <= 0
        or integrity.session_date != VALUATION_SESSION
        or integrity.record_count != len(records)
        or integrity.duplicate_instrument_session_count != 0
        or integrity.multiple_latest_revision_count != 0
        or integrity.future_identity_reference_count != 0
    ):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI canonical evidence differs"
        )
    identity = _identity(
        policy_report=policy_report,
        member_sha256=submissions_member_sha256,
        instrument=instrument,
        integrity=integrity,
    )
    alternatives = _alternatives(policy_report, bar.close)
    gross_values = tuple(Decimal(item.gross_reference_value_usd) for item in alternatives)
    primary = next(
        item for item in alternatives if item.alternative_code == "mixed_election"
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "payoff_policy_report_sha256": policy.report_sha256,
        "payoff_policy_logical_fingerprint": policy_report.logical_fingerprint,
        "core_adjudication_report_sha256": core.report_sha256,
        "core_adjudication_logical_fingerprint": core_report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation_report.logical_fingerprint,
        "sec_submissions_manifest_sha256": submissions_manifest_sha256,
        "sec_submissions_archive_sha256": submissions.archive_sha256,
        "sec_submissions_logical_fingerprint": submissions.logical_fingerprint,
        "sec_snapshot_completed_at": submissions.completed_at,
        "identity": identity,
        "valuation_session_record_count": integrity.record_count,
        "valuation_session_content_fingerprint": integrity.content_fingerprint,
        "valuation_session_parquet_sha256": integrity.parquet_sha256,
        "valuation_identity_snapshot_fingerprint": integrity.identity_snapshot_fingerprint,
        "canonical_partition_created_at": available_at,
        "consideration_close_usd": _fixed(bar.close, 10),
        "price_quality_flags": tuple(sorted(bar.quality_flags)),
        "alternatives": alternatives,
        "primary_gross_reference_value_usd": primary.gross_reference_value_usd,
        "sensitivity_min_gross_reference_value_usd": _fixed(min(gross_values), 16),
        "sensitivity_max_gross_reference_value_usd": _fixed(max(gross_values), 16),
        "sensitivity_range_usd": _fixed(max(gross_values) - min(gross_values), 16),
    }
    provisional = StrongLeaderPullbackTerminalPopulationListedReferenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationListedReferenceV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _identity(
    *, policy_report: Any, member_sha256: str, instrument: Any, integrity: Any,
) -> TerminalPopulationListedIdentityV1:
    values = {
        "source_target_instrument_id": policy_report.party_relation.instrument_id,
        "sec_submissions_member_sha256": member_sha256,
        "sec_event_acceptance_datetime": HNI_EVENT_ACCEPTED_AT,
        "assigned_consideration_instrument_id": instrument.instrument_id,
        "identity_snapshot_fingerprint": integrity.identity_snapshot_fingerprint,
        "decision_reasons": tuple(
            sorted(
                {
                    "source_defines_hni_corporation_and_hni_common_stock",
                    "official_sec_profile_binds_cik_ticker_and_nyse",
                    "canonical_identity_matches_same_cik_ticker_exchange_and_common_stock",
                    "stable_instrument_id_is_assignment_authority",
                    "ticker_and_name_are_not_used_alone",
                    "sec_snapshot_is_reconstruction_evidence_not_signal_knowledge",
                }
            )
        ),
    }
    provisional = TerminalPopulationListedIdentityV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalPopulationListedIdentityV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _alternatives(
    policy_report: Any, close: Decimal
) -> tuple[TerminalPopulationAlternativeReferenceV1, ...]:
    terms = {item.term_key: item for item in policy_report.normalized_terms}
    if set(terms) != {key for keys in _ALTERNATIVE_TERMS.values() for key in keys}:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference payoff terms differ"
        )
    result = []
    for policy_alternative in policy_report.alternatives:
        code = policy_alternative.alternative_code
        expected_keys = tuple(sorted(_ALTERNATIVE_TERMS[code]))
        if tuple(policy_alternative.term_keys) != expected_keys:
            raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                "listed-reference alternative policy differs"
            )
        selected = tuple(terms[key] for key in expected_keys)
        cash_terms = tuple(
            item for item in selected if item.term_kind == "cash_usd_per_target_share"
        )
        ratio_terms = tuple(
            item
            for item in selected
            if item.term_kind == "listed_equity_shares_per_target_share"
        )
        if len(cash_terms) > 1 or len(ratio_terms) != 1:
            raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                "listed-reference component cardinality differs"
            )
        cash = Decimal(cash_terms[0].normalized_value) if cash_terms else Decimal(0)
        ratio = Decimal(ratio_terms[0].normalized_value)
        component = ratio * close
        values = {
            "alternative_code": code,
            "term_keys": expected_keys,
            "term_fingerprints": tuple(
                sorted(item.logical_fingerprint for item in selected)
            ),
            "default_if_no_valid_election": (
                policy_alternative.default_if_no_valid_election
            ),
            "cash_amount_usd": _fixed(cash, 2),
            "listed_equity_ratio": _fixed(ratio, 6),
            "consideration_close_usd": _fixed(close, 10),
            "listed_equity_component_value_usd": _fixed(component, 16),
            "gross_reference_value_usd": _fixed(cash + component, 16),
        }
        provisional = TerminalPopulationAlternativeReferenceV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        result.append(
            TerminalPopulationAlternativeReferenceV1.model_validate(
                {
                    **values,
                    "logical_fingerprint": base._fingerprint(
                        provisional.model_dump(
                            mode="json", exclude={"logical_fingerprint"}
                        )
                    ),
                }
            )
        )
    return tuple(result)


def _read_hni_submission(archive_path: Path) -> tuple[str, dict[str, Any]]:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            info = archive.getinfo(HNI_SUBMISSIONS_MEMBER)
            if info.file_size < 1 or info.file_size > MAXIMUM_SUBMISSIONS_MEMBER_BYTES:
                raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                    "HNI submissions member size differs"
                )
            raw = archive.read(info)
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI submissions member read failed"
        ) from exc
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI submissions member is invalid"
        ) from exc
    _validate_hni_submission(payload)
    return base._sha256_bytes(raw), payload


def _validate_hni_submission(payload: dict[str, Any]) -> None:
    try:
        tickers = payload["tickers"]
        exchanges = payload["exchanges"]
        recent = payload["filings"]["recent"]
        fields = (
            recent["form"],
            recent["filingDate"],
            recent["acceptanceDateTime"],
            recent["accessionNumber"],
            recent["primaryDocument"],
        )
        ticker_index = tickers.index("HNI")
        event_found = any(
            fields[0][index] == "8-K"
            and fields[1][index] == VALUATION_SESSION.isoformat()
            and normalize_utc_datetime(datetime.fromisoformat(fields[2][index]))
            == HNI_EVENT_ACCEPTED_AT
            and fields[3][index] == HNI_EVENT_ACCESSION
            and fields[4][index] == HNI_EVENT_PRIMARY_DOCUMENT
            for index in range(len(fields[0]))
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI submissions profile differs"
        ) from exc
    if (
        str(payload.get("cik", "")).zfill(10) != HNI_CIK
        or payload.get("entityType") != "operating"
        or payload.get("name") != "HNI CORP"
        or len(tickers) != len(exchanges)
        or exchanges[ticker_index] != "NYSE"
        or len({len(field) for field in fields}) != 1
        or not event_found
    ):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "HNI submissions profile differs"
        )


def _fixed(value: Decimal, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    if not value.is_finite() or value < 0 or value != value.quantize(quantum):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference decimal scale differs"
        )
    return f"{value:.{places}f}"


def _ruleset_fingerprint() -> str:
    return base._fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_instrument_id": str(TARGET_INSTRUMENT_ID),
            "consideration_instrument_id": str(HNI_INSTRUMENT_ID),
            "consideration_cik": HNI_CIK,
            "valuation_session": VALUATION_SESSION.isoformat(),
            "sec_member": HNI_SUBMISSIONS_MEMBER,
            "sec_event_accession": HNI_EVENT_ACCESSION,
            "identity_gate": "source_plus_sec_cik_ticker_exchange_plus_canonical_stable_id",
            "valuation_basis": "first_absent_target_session_unadjusted_hni_close",
            "research_policy": "mixed_default_plus_all_alternative_sensitivity",
            "actual_holder_election": "unknown",
            "adjustment_details": "unresolved",
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationListedReferenceV1,
) -> StrongLeaderPullbackTerminalPopulationListedReferenceResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_listed_reference(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                "existing listed-reference report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
                "listed-reference report exceeds byte ceiling"
            )
        source_base._write_exclusive(partial / REPORT_FILE, raw)
        source_base._fsync_directory(partial)
        partial.replace(target)
        source_base._fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            source_base._fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_population_listed_reference(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationListedReferenceResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_OUTPUT_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference target is unsafe"
        )
    return path


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or target.resolve(strict=True) != target
    ):
        raise StrongLeaderPullbackTerminalPopulationListedReferenceError(
            "listed-reference output is unsafe"
        )
    return target
