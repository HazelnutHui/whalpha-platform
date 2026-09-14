"""Bounded source plan for listed-equity merger consideration identity."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import InstrumentMasterV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    SecSubmissionsSourceManifestV1,
    read_sec_submissions_source_package,
)
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
)
from tip_api.services.strong_leader_pullback_sec_party_relation_adjudication import (
    SecPartyRelationDecisionV1,
    StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    read_strong_leader_pullback_sec_party_relation_adjudication,
)
from tip_api.services.strong_leader_pullback_terminal_payoff_terms import (
    StrongLeaderPullbackTerminalPayoffTermsResult,
    TerminalPayoffTermsDecisionV1,
    read_strong_leader_pullback_terminal_payoff_terms,
)
from tip_api.services.strong_leader_pullback_trading_cessation_adjudication import (
    StrongLeaderPullbackTradingCessationAdjudicationResult,
    TradingCessationDecisionV1,
    read_strong_leader_pullback_trading_cessation_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-listed-consideration-source-plan/1.0"
REPORT_FILE = "listed-consideration-source-plan.json"
EXPECTED_CASE_COUNT = 12
MAXIMUM_REPORT_BYTES = 512 * 1024
MAXIMUM_SUBMISSION_MEMBER_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_CIK_PATTERN = r"^[0-9]{10}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_OUTPUT_NAME_PATTERN = r"^plan=[A-Za-z0-9._-]+$"


@dataclass(frozen=True, slots=True)
class _CaseSpec:
    source_party_literal: str
    cik: str
    canonical_session: date
    canonical_ticker: str
    canonical_instrument_id: UUID
    sec_name: str
    sec_ticker: str
    sec_exchange: str
    registration_form: str
    registration_filing_date: date
    registration_acceptance_datetime: datetime
    registration_accession_number: str
    registration_primary_document: str


def _dt(value: str) -> datetime:
    return normalize_utc_datetime(datetime.fromisoformat(value))


_CASE_SPECS = {
    1: _CaseSpec("Rayonier Inc.", "0000052827", date(2026, 2, 2), "RYN", UUID("bcb7aeb3-99d6-52fb-98c7-1d485a14f86f"), "RAYONIER INC", "RYN", "NYSE", "424B3", date(2025, 12, 23), _dt("2025-12-23T21:44:10Z"), "0001193125-25-331066", "d45886d424b3.htm"),
    14: _CaseSpec("Rocket Companies, Inc.", "0001805284", date(2025, 10, 1), "RKT", UUID("7590f499-6b3e-54fa-8e6c-abb40ae5276c"), "Rocket Companies, Inc.", "RKT", "NYSE", "424B3", date(2025, 7, 31), _dt("2025-07-31T00:44:46Z"), "0001104659-25-072363", "tm2513302-9_424b3.htm"),
    35: _CaseSpec("Acuren Corporation", "0002032966", date(2025, 8, 4), "TIC", UUID("0b8f9d96-5899-55c4-87d7-c15f7252da7f"), "TIC Solutions, Inc.", "TIC", "NYSE", "424B3", date(2025, 8, 4), _dt("2025-08-04T20:52:30Z"), "0001213900-25-071406", "ea025156901-424b3_acurencorp.htm"),
    40: _CaseSpec("Omnicom Group Inc.", "0000029989", date(2025, 11, 28), "OMC", UUID("d0b17749-7d3c-533d-ba30-b053d56a3055"), "OMNICOM GROUP INC.", "OMC", "NYSE", "424B3", date(2025, 1, 30), _dt("2025-01-30T21:26:36Z"), "0001193125-25-017282", "d881832d424b3.htm"),
    95: _CaseSpec("Compass, Inc.", "0001563190", date(2026, 1, 9), "COMP", UUID("e9d86b98-2536-57e3-8506-114ca91cf961"), "Compass, Inc.", "COMP", "NYSE", "424B3", date(2025, 12, 2), _dt("2025-12-02T21:33:45Z"), "0001628280-25-054790", "compassinc-424b3.htm"),
    107: _CaseSpec("Public Storage, a Maryland real estate investment trust", "0001393311", date(2026, 7, 22), "PSA", UUID("0aaf4702-a1ce-5409-a8c1-fb6b2a95e7b4"), "Public Storage", "PSA", "NYSE", "424B3", date(2026, 6, 12), _dt("2026-06-12T20:08:16Z"), "0001193125-26-269409", "d110345d424b3.htm"),
    158: _CaseSpec("IonQ, Inc.", "0001824920", date(2026, 7, 31), "IONQ", UUID("10854b64-ac5b-52de-bfcb-6b77c13afa5c"), "IonQ, Inc.", "IONQ", "NYSE", "424B3", date(2026, 3, 31), _dt("2026-03-31T21:12:09Z"), "0001193125-26-134933", "d88629d424b3.htm"),
    174: _CaseSpec("Fifth Third Bancorp", "0000035527", date(2026, 2, 2), "FITB", UUID("361edcf9-8ccb-5ccf-bf58-5df1841e9007"), "FIFTH THIRD BANCORP", "FITB", "NYSE", "424B3", date(2026, 1, 26), _dt("2026-01-26T14:36:39Z"), "0001193125-26-021809", "d55045d424b3.htm"),
    178: _CaseSpec("Huntington Bancshares Incorporated", "0000049196", date(2025, 10, 20), "HBAN", UUID("01ceda28-e2e1-5807-b4c1-c23d6756a99c"), "HUNTINGTON BANCSHARES INC /MD/", "HBAN", "Nasdaq", "424B3", date(2025, 8, 15), _dt("2025-08-15T20:11:07Z"), "0001140361-25-031511", "ny20052025x9_424b3.htm"),
    184: _CaseSpec("The Boeing Company", "0000012927", date(2025, 12, 8), "BA", UUID("aa1641e4-3ba0-55ae-b4f0-ab44d429c954"), "BOEING CO", "BA", "NYSE", "424B3", date(2024, 12, 20), _dt("2024-12-20T22:12:11Z"), "0001193125-24-283231", "d835944d424b3.htm"),
    197: _CaseSpec("Columbia Banking System, Inc.", "0000887343", date(2025, 9, 2), "COLB", UUID("4b4a537e-d50d-5fa5-9955-58ddd91e8eab"), "COLUMBIA BANKING SYSTEM, INC.", "COLB", "Nasdaq", "424B3", date(2025, 6, 16), _dt("2025-06-16T20:34:08Z"), "0001193125-25-141452", "d936202d424b3.htm"),
    218: _CaseSpec("Vivmark Residential (formerly known as Equity Residential)", "0000906107", date(2026, 8, 17), "EQR", UUID("14a409e3-b192-5325-9a21-56ef17aedd89"), "VIVMARK RESIDENTIAL", "VMRK", "NYSE", "424B3", date(2026, 7, 13), _dt("2026-07-13T20:11:08Z"), "0001140361-26-028312", "ny20076479x4_424b3.htm"),
}


class StrongLeaderPullbackListedConsiderationSourcePlanError(RuntimeError):
    """Raised when the bounded listed-consideration source plan differs."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ListedConsiderationSourcePlanDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    target_instrument_id: UUID
    payoff_terms_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_issuer_locator: str = Field(min_length=1, max_length=128)
    source_party_literal: str = Field(min_length=1, max_length=128)
    source_party_start: int = Field(ge=0)
    source_party_end: int = Field(ge=1)
    source_party_sha256: str = Field(pattern=_SHA256_PATTERN)
    proposed_cik: str = Field(pattern=_CIK_PATTERN)
    submissions_member_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_issuer_name: str = Field(min_length=1, max_length=256)
    submissions_current_ticker: str = Field(min_length=1, max_length=32)
    submissions_current_exchange: str = Field(min_length=1, max_length=32)
    registration_form: Literal["424B3"] = "424B3"
    registration_filing_date: date
    registration_acceptance_datetime: datetime
    registration_accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    registration_primary_document: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    registration_document_url: str = Field(
        pattern=r"^https://www\.sec\.gov/Archives/edgar/data/[0-9]+/[0-9]+/[A-Za-z0-9._-]+$"
    )
    canonical_evidence_session: date
    canonical_eod_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_identity_snapshot_date: date
    canonical_identity_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    proposed_consideration_instrument_id: UUID
    canonical_ticker: str = Field(min_length=1, max_length=32)
    canonical_name: str = Field(min_length=1, max_length=256)
    canonical_exchange: str = Field(min_length=1, max_length=32)
    canonical_cik: str = Field(pattern=_CIK_PATTERN)
    canonical_figi: str = Field(pattern=r"^BBG[A-Z0-9]+$")
    canonical_source_instrument_id: str = Field(min_length=1, max_length=128)
    source_document_required: Literal[True] = True
    consideration_security_identity_assignment_count: Literal[0] = 0
    terminal_value_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("registration_acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed-consideration plan reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ListedConsiderationSourcePlanDecisionV1":
        if (
            self.source_party_end <= self.source_party_start
            or self.source_party_sha256
            != _sha256_bytes(self.source_party_literal.encode("utf-8"))
            or self.canonical_cik != self.proposed_cik
            or not self.canonical_source_instrument_id.startswith(
                "share_class_figi:"
            )
            or not _decision_matches_registry(self)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-consideration plan decision differs")
        return self


class StrongLeaderPullbackListedConsiderationSourcePlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-source-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["listed_consideration_source_plan_frozen"] = (
        "listed_consideration_source_plan_frozen"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    party_relation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    planned_case_count: Literal[12] = EXPECTED_CASE_COUNT
    planned_source_document_count: Literal[12] = EXPECTED_CASE_COUNT
    proposed_stable_instrument_count: Literal[12] = EXPECTED_CASE_COUNT
    decisions: tuple[ListedConsiderationSourcePlanDecisionV1, ...]
    source_document_count: Literal[0] = 0
    consideration_security_identity_assignment_count: Literal[0] = 0
    canonical_lifecycle_fact_count: Literal[0] = 0
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackListedConsiderationSourcePlanV1":
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(_CASE_SPECS))
            or len({item.proposed_consideration_instrument_id for item in self.decisions})
            != EXPECTED_CASE_COUNT
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-consideration source plan differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationSourcePlanResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationSourcePlanV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _SubmissionProfile:
    member_sha256: str
    name: str
    ticker: str
    exchange: str


def build_strong_leader_pullback_listed_consideration_source_plan(
    *,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    party_relation_root: Path,
    party_relation_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    submissions_package_root: Path,
    submissions_custody_root: Path,
    canonical_eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationSourcePlanResult:
    with _network_prohibited():
        payoff_terms = read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        parties = read_strong_leader_pullback_sec_party_relation_adjudication(
            output_root=party_relation_root,
            output_custody_root=party_relation_custody_root,
        )
        cessation = read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        submissions = read_sec_submissions_source_package(
            package_path=submissions_package_root,
            approved_custody_root=submissions_custody_root,
        )
        profiles = _read_submission_profiles(
            submissions_package_root / ARCHIVE_FILE
        )
        identities = _read_canonical_identity_evidence(canonical_eod_root)
        report = _build_report(
            payoff_terms=payoff_terms,
            parties=parties,
            cessation=cessation,
            submissions=submissions,
            submissions_manifest_sha256=_sha256_file(
                submissions_package_root / "package.json"
            ),
            profiles=profiles,
            identities=identities,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_listed_consideration_source_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationSourcePlanResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackListedConsiderationSourcePlanV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationSourcePlanResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    payoff_terms: StrongLeaderPullbackTerminalPayoffTermsResult,
    parties: StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    cessation: StrongLeaderPullbackTradingCessationAdjudicationResult,
    submissions: SecSubmissionsSourceManifestV1,
    submissions_manifest_sha256: str,
    profiles: dict[int, _SubmissionProfile],
    identities: dict[int, tuple[object, InstrumentMasterV1]],
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationSourcePlanV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration plan revision is invalid"
        )
    if (
        payoff_terms.report.party_relation_report_sha256 != parties.report_sha256
        or payoff_terms.report.party_relation_logical_fingerprint
        != parties.report.logical_fingerprint
        or payoff_terms.report.cessation_report_sha256 != cessation.report_sha256
        or payoff_terms.report.cessation_logical_fingerprint
        != cessation.report.logical_fingerprint
        or not re.fullmatch(_SHA256_PATTERN, submissions_manifest_sha256)
    ):
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration plan input bindings differ"
        )
    term_map = {item.request_sequence: item for item in payoff_terms.report.decisions}
    party_map = {item.request_sequence: item for item in parties.report.decisions}
    cessation_map = {item.request_sequence: item for item in cessation.report.decisions}
    if not (
        set(_CASE_SPECS).issubset(term_map)
        and set(_CASE_SPECS).issubset(party_map)
        and set(_CASE_SPECS).issubset(cessation_map)
        and set(profiles) == set(identities) == set(_CASE_SPECS)
    ):
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration plan population differs"
        )
    decisions = tuple(
        _document_decision(
            payoff_terms=term_map[sequence],
            party=party_map[sequence],
            cessation=cessation_map[sequence],
            profile=profiles[sequence],
            identity_evidence=identities[sequence],
        )
        for sequence in sorted(_CASE_SPECS)
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "payoff_terms_report_sha256": payoff_terms.report_sha256,
        "payoff_terms_logical_fingerprint": payoff_terms.report.logical_fingerprint,
        "party_relation_report_sha256": parties.report_sha256,
        "party_relation_logical_fingerprint": parties.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "submissions_manifest_sha256": submissions_manifest_sha256,
        "submissions_source_fingerprint": submissions.logical_fingerprint,
        "submissions_archive_sha256": submissions.archive_sha256,
        "decisions": decisions,
    }
    provisional = StrongLeaderPullbackListedConsiderationSourcePlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackListedConsiderationSourcePlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    payoff_terms: TerminalPayoffTermsDecisionV1,
    party: SecPartyRelationDecisionV1,
    cessation: TradingCessationDecisionV1,
    profile: _SubmissionProfile,
    identity_evidence: tuple[object, InstrumentMasterV1],
) -> ListedConsiderationSourcePlanDecisionV1:
    spec = _CASE_SPECS[payoff_terms.request_sequence]
    integrity, instrument = identity_evidence
    if (
        payoff_terms.instrument_id != party.instrument_id
        or payoff_terms.instrument_id != cessation.instrument_id
        or payoff_terms.party_relation_fingerprint != party.logical_fingerprint
        or payoff_terms.cessation_fingerprint != cessation.logical_fingerprint
        or payoff_terms.terminal_candidate_state
        != "listed_security_identity_and_market_value_required"
        or party.resolution_state != "matched"
        or not party.listed_equity_consideration
        or cessation.resolution_state != "matched"
        or cessation.next_exchange_session != spec.canonical_session
        or party.party_definition_text.count(spec.source_party_literal) != 1
        or instrument.instrument_id != spec.canonical_instrument_id
        or instrument.ticker != spec.canonical_ticker
        or instrument.cik != spec.cik
        or instrument.instrument_type.value != "common_stock"
        or instrument.quality_status.value != "valid"
    ):
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source candidate differs"
        )
    start = party.party_definition_text.index(spec.source_party_literal)
    values = {
        "request_sequence": payoff_terms.request_sequence,
        "target_instrument_id": payoff_terms.instrument_id,
        "payoff_terms_fingerprint": payoff_terms.logical_fingerprint,
        "party_relation_fingerprint": party.logical_fingerprint,
        "cessation_fingerprint": cessation.logical_fingerprint,
        "consideration_issuer_locator": payoff_terms.listed_equity_issuer_locator,
        "source_party_literal": spec.source_party_literal,
        "source_party_start": start,
        "source_party_end": start + len(spec.source_party_literal),
        "source_party_sha256": _sha256_bytes(spec.source_party_literal.encode()),
        "proposed_cik": spec.cik,
        "submissions_member_sha256": profile.member_sha256,
        "submissions_issuer_name": profile.name,
        "submissions_current_ticker": profile.ticker,
        "submissions_current_exchange": profile.exchange,
        "registration_filing_date": spec.registration_filing_date,
        "registration_acceptance_datetime": spec.registration_acceptance_datetime,
        "registration_accession_number": spec.registration_accession_number,
        "registration_primary_document": spec.registration_primary_document,
        "registration_document_url": _document_url(spec),
        "canonical_evidence_session": spec.canonical_session,
        "canonical_eod_content_fingerprint": integrity.content_fingerprint,
        "canonical_identity_snapshot_date": integrity.identity_snapshot_date,
        "canonical_identity_snapshot_fingerprint": (
            integrity.identity_snapshot_fingerprint
        ),
        "proposed_consideration_instrument_id": instrument.instrument_id,
        "canonical_ticker": instrument.ticker,
        "canonical_name": instrument.name,
        "canonical_exchange": instrument.primary_exchange,
        "canonical_cik": instrument.cik,
        "canonical_figi": instrument.figi,
        "canonical_source_instrument_id": instrument.source_instrument_id,
        "decision_reasons": (
            "candidate_cik_is_cross_source_but_not_yet_transaction_proven",
            "exact_424b3_primary_document_is_required_before_assignment",
            "exact_source_party_literal_retained",
            "point_in_time_common_stock_candidate_is_formally_read",
            "ticker_and_name_are_candidate_locators_not_identity_authority",
        ),
    }
    provisional = ListedConsiderationSourcePlanDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ListedConsiderationSourcePlanDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _read_submission_profiles(archive_path: Path) -> dict[int, _SubmissionProfile]:
    result: dict[int, _SubmissionProfile] = {}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for sequence, spec in sorted(_CASE_SPECS.items()):
                member = f"CIK{spec.cik}.json"
                info = archive.getinfo(member)
                if info.file_size < 1 or info.file_size > MAXIMUM_SUBMISSION_MEMBER_BYTES:
                    raise StrongLeaderPullbackListedConsiderationSourcePlanError(
                        "submissions member size differs"
                    )
                raw = archive.read(info)
                payload = json.loads(raw)
                if (
                    str(payload.get("cik", "")).zfill(10) != spec.cik
                    or payload.get("name") != spec.sec_name
                ):
                    raise StrongLeaderPullbackListedConsiderationSourcePlanError(
                        "submissions issuer profile differs"
                    )
                tickers = payload.get("tickers")
                exchanges = payload.get("exchanges")
                if (
                    not isinstance(tickers, list)
                    or not isinstance(exchanges, list)
                    or len(tickers) != len(exchanges)
                    or spec.sec_ticker not in tickers
                    or exchanges[tickers.index(spec.sec_ticker)] != spec.sec_exchange
                    or not _registration_row_present(payload, spec)
                ):
                    raise StrongLeaderPullbackListedConsiderationSourcePlanError(
                        "submissions listed-security candidate differs"
                    )
                result[sequence] = _SubmissionProfile(
                    member_sha256=_sha256_bytes(raw),
                    name=spec.sec_name,
                    ticker=spec.sec_ticker,
                    exchange=spec.sec_exchange,
                )
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        if isinstance(exc, StrongLeaderPullbackListedConsiderationSourcePlanError):
            raise
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "submissions selected member read failed"
        ) from exc
    return result


def _registration_row_present(payload: dict[str, object], spec: _CaseSpec) -> bool:
    try:
        recent = payload["filings"]["recent"]  # type: ignore[index]
        fields = (
            recent["form"],  # type: ignore[index]
            recent["filingDate"],  # type: ignore[index]
            recent["acceptanceDateTime"],  # type: ignore[index]
            recent["accessionNumber"],  # type: ignore[index]
            recent["primaryDocument"],  # type: ignore[index]
        )
        if len({len(item) for item in fields}) != 1:
            return False
        for index, form in enumerate(fields[0]):
            if (
                form == spec.registration_form
                and fields[1][index] == spec.registration_filing_date.isoformat()
                and _dt(fields[2][index]) == spec.registration_acceptance_datetime
                and fields[3][index] == spec.registration_accession_number
                and fields[4][index] == spec.registration_primary_document
            ):
                return True
    except (KeyError, TypeError, ValueError):
        return False
    return False


def _read_canonical_identity_evidence(
    canonical_root: Path,
) -> dict[int, tuple[object, InstrumentMasterV1]]:
    repository = CanonicalEodReadRepository(canonical_root)
    by_session: dict[date, tuple[object, tuple[InstrumentMasterV1, ...]]] = {}
    result: dict[int, tuple[object, InstrumentMasterV1]] = {}
    for sequence, spec in sorted(_CASE_SPECS.items()):
        if spec.canonical_session not in by_session:
            by_session[spec.canonical_session] = (
                repository.inspect_session(spec.canonical_session),
                repository.read_instruments_for_session(spec.canonical_session),
            )
        integrity, instruments = by_session[spec.canonical_session]
        matches = tuple(
            item for item in instruments if item.instrument_id == spec.canonical_instrument_id
        )
        if len(matches) != 1:
            raise StrongLeaderPullbackListedConsiderationSourcePlanError(
                "canonical consideration-security candidate differs"
            )
        result[sequence] = (integrity, matches[0])
    return result


def _document_url(spec: _CaseSpec) -> str:
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(spec.cik)}/{spec.registration_accession_number.replace('-', '')}/"
        f"{spec.registration_primary_document}"
    )


def _decision_matches_registry(
    decision: ListedConsiderationSourcePlanDecisionV1,
) -> bool:
    spec = _CASE_SPECS.get(decision.request_sequence)
    if spec is None:
        return False
    return (
        decision.source_party_literal == spec.source_party_literal
        and decision.proposed_cik == spec.cik
        and decision.registration_form == spec.registration_form
        and decision.registration_filing_date == spec.registration_filing_date
        and decision.registration_acceptance_datetime
        == spec.registration_acceptance_datetime
        and decision.registration_accession_number
        == spec.registration_accession_number
        and decision.registration_primary_document
        == spec.registration_primary_document
        and decision.registration_document_url == _document_url(spec)
        and decision.canonical_evidence_session == spec.canonical_session
        and decision.proposed_consideration_instrument_id
        == spec.canonical_instrument_id
        and decision.canonical_ticker == spec.canonical_ticker
        and decision.submissions_issuer_name == spec.sec_name
        and decision.submissions_current_ticker == spec.sec_ticker
        and decision.submissions_current_exchange == spec.sec_exchange
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "cases": {
                str(sequence): {
                    "source_party_literal": spec.source_party_literal,
                    "cik": spec.cik,
                    "canonical_session": spec.canonical_session.isoformat(),
                    "canonical_ticker": spec.canonical_ticker,
                    "canonical_instrument_id": str(spec.canonical_instrument_id),
                    "sec_name": spec.sec_name,
                    "sec_ticker": spec.sec_ticker,
                    "sec_exchange": spec.sec_exchange,
                    "registration_form": spec.registration_form,
                    "registration_filing_date": spec.registration_filing_date.isoformat(),
                    "registration_acceptance_datetime": (
                        spec.registration_acceptance_datetime.isoformat()
                    ),
                    "registration_accession_number": (
                        spec.registration_accession_number
                    ),
                    "registration_primary_document": (
                        spec.registration_primary_document
                    ),
                }
                for sequence, spec in sorted(_CASE_SPECS.items())
            },
            "identity_authority": "candidate_only_until_424b3_content_matches_transaction",
            "ticker_and_name_authority": "locator_only",
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackListedConsiderationSourcePlanV1,
) -> StrongLeaderPullbackListedConsiderationSourcePlanResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_listed_consideration_source_plan(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationSourcePlanError(
                "existing listed-consideration source plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE, _json_bytes(report.model_dump(mode="json"))
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_listed_consideration_source_plan(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackListedConsiderationSourcePlanResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan paths must be absolute"
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
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan custody or target is unsafe"
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
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "listed-consideration source plan file metadata differs"
        )


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackListedConsiderationSourcePlanError(
            "network access is prohibited during listed-consideration planning"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
