"""Source-driven final terminal-reference review for Strong-Leader Pullback.

The review closes the finite-reference gate without reading a forward outcome.
It binds the previously quarantined 18 cases to retained SEC terms and exact
canonical daily closes, then publishes the generic ADR 0269 bounds contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services import strong_leader_pullback_sec_document_content_census as text
from tip_api.services import strong_leader_pullback_sec_document_source as legacy_source
from tip_api.services import (
    strong_leader_pullback_sec_consideration_adjudication as consideration_source,
)
from tip_api.services import strong_leader_pullback_terminal_gap_census_v3 as gap_v3_source
from tip_api.services import strong_leader_pullback_terminal_gap_census_v4 as gap_v4_source
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff_source
from tip_api.services import strong_leader_pullback_terminal_reference_bounds as bounds
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_adjudication as sec_review,
)


REPORT_FILE = "terminal-reference-bounds.json"
MAXIMUM_REPORT_BYTES = 128 * 1024
_OUTPUT_NAME_PATTERN = r"^review=[A-Za-z0-9._-]+$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_MONEY_QUANTUM = Decimal("0.0000000001")


class StrongLeaderPullbackTerminalReferenceFinalReviewError(RuntimeError):
    """Raised when final terminal-reference evidence cannot be reproduced."""


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalReferenceFinalReviewResult:
    output_root: Path
    report: bounds.StrongLeaderPullbackTerminalReferenceBoundsV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _CloseSpec:
    session_date: date
    instrument_id: UUID
    ticker: str
    close_usd: Decimal
    content_fingerprint: str


@dataclass(frozen=True, slots=True)
class _CaseSpec:
    instrument_id: UUID
    ticker: str
    crossing_path_count: int
    policy: bounds.TerminalReferencePolicy
    calculation: str
    close_key: str | None = None
    legacy_request_sequence: int | None = None


_CLOSES = {
    "CECO": _CloseSpec(
        date(2026, 6, 1),
        UUID("66acad23-2b15-5c91-8bc6-334498bc4e45"),
        "CECO",
        Decimal("79.0300000000"),
        "01c316a18cd61efdf5046c76209f5ab392849c2fa22942a5f1f5d8fe2f6c9097",
    ),
    "LNW": _CloseSpec(
        date(2025, 11, 12),
        UUID("15366b01-e0b4-518a-84b9-4017bac9464c"),
        "LNW",
        Decimal("86.2200000000"),
        "72dd60ec24d2fa1412ac153c771cab169425a480d87d4b4ec0241aff18e62997",
    ),
    "PNFP": _CloseSpec(
        date(2026, 1, 2),
        UUID("772f9ddd-25e8-5443-8f02-6bb1e1f70c6f"),
        "PNFP",
        Decimal("95.1000000000"),
        "270e153cc6288dab777bc600c505d50836bad0191f857c683f4d7ceb34888d84",
    ),
    "QXO": _CloseSpec(
        date(2026, 7, 1),
        UUID("94f15dc6-d4c0-5633-93e0-5cbeeb454e1e"),
        "QXO",
        Decimal("16.5400000000"),
        "ff1936c75f6f4d8a82dedc09ab2285b9ce8545b73fb745f176fb94a0dcda1531",
    ),
    "RGLD": _CloseSpec(
        date(2025, 10, 20),
        UUID("26d52c8b-5878-56b7-9a76-69a25f105654"),
        "RGLD",
        Decimal("194.1200000000"),
        "a84653019dec2745732375f05b6f443904dfe01eca35600b1caa6b01b626ea24",
    ),
    "TEX": _CloseSpec(
        date(2026, 2, 2),
        UUID("eca24bf1-d97d-5269-af60-2563843b80c5"),
        "TEX",
        Decimal("58.9900000000"),
        "016f0a9c307851989ab2013a81c57720a2e874abf1f8c57f8e06abbc2778a7e4",
    ),
}


_CASES = tuple(
    sorted(
        (
            _CaseSpec(
                UUID("c6c4a32a-49a4-51db-ad16-bfd6d7e58ea0"),
                "ACLX",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "aclx_source",
                legacy_request_sequence=172,
            ),
            _CaseSpec(
                UUID("39b319b3-e240-5d5f-9fef-1abfa12afa48"),
                "AKRO",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "cash_plus_cvr",
            ),
            _CaseSpec(
                UUID("98f50e3f-4ec1-5236-83f3-fd4fe009350d"),
                "AMED",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_FIXED_CASH,
                "fixed_cash",
            ),
            _CaseSpec(
                UUID("5594a37d-0a8f-528b-a40a-310305d07808"),
                "APLS",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "cash_plus_cvr",
            ),
            _CaseSpec(
                UUID("57d24075-0478-5e91-8e22-fceda7700ac1"),
                "BLD",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_LISTED_CONSIDERATION_MAX,
                "bld_election",
                "QXO",
            ),
            _CaseSpec(
                UUID("37cc3174-100b-51c0-82e8-cd055d1213b8"),
                "ETNB",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "cash_plus_cvr",
            ),
            _CaseSpec(
                UUID("d90fa658-61a6-55b1-ac2a-5bd977a0ea0d"),
                "GTLS",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_FIXED_CASH,
                "fixed_cash",
            ),
            _CaseSpec(
                UUID("8164e4a6-705b-5d0f-a93c-4836e08e9278"),
                "HOLX",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "holx_source",
                legacy_request_sequence=118,
            ),
            _CaseSpec(
                UUID("15366b01-e0b4-518a-84b9-4017bac9464c"),
                "LNW",
                5,
                bounds.TerminalReferencePolicy.FORCED_LAST_US_CLOSE,
                "lnw_exact",
                "LNW",
            ),
            _CaseSpec(
                UUID("34deeee9-8d40-52d5-ba8a-eacb9b4004a5"),
                "MTSR",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "mtsr_source",
            ),
            _CaseSpec(
                UUID("2537e45b-62a8-5a96-9b7b-f30ba708645c"),
                "REVG",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_LISTED_CONSIDERATION_MAX,
                "revg_source",
                "TEX",
            ),
            _CaseSpec(
                UUID("2fe2a99c-8799-5188-ad89-5e471afddf3c"),
                "SAND",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_LISTED_CONSIDERATION_MAX,
                "sand_source",
                "RGLD",
            ),
            _CaseSpec(
                UUID("714c4ae2-2938-5196-a02f-198c6b5b8415"),
                "SKX",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_UNLISTED_CONSIDERATION_VALUE,
                "skx_source",
            ),
            _CaseSpec(
                UUID("beb7b379-364b-5917-ada1-110fb2c19f67"),
                "SLNO",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_FIXED_CASH,
                "fixed_cash",
            ),
            _CaseSpec(
                UUID("8f99481e-e0e1-5f43-9d0a-dfe0176a3814"),
                "SNV",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_LISTED_CONSIDERATION_MAX,
                "snv_stock",
                "PNFP",
            ),
            _CaseSpec(
                UUID("650a846c-bc83-5c8a-adc2-cd05a87abc11"),
                "THR",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_LISTED_CONSIDERATION_MAX,
                "thr_election",
                "CECO",
            ),
            _CaseSpec(
                UUID("62620f34-d002-5b43-a731-70f6679ea04e"),
                "TMHC",
                5,
                bounds.TerminalReferencePolicy.ZERO_TO_FIXED_CASH,
                "fixed_cash",
            ),
            _CaseSpec(
                UUID("72108e8d-6854-5266-a8ad-68b83ebceb5a"),
                "VERV",
                3,
                bounds.TerminalReferencePolicy.ZERO_TO_CASH_PLUS_CVR_CAP,
                "cash_plus_cvr",
            ),
        ),
        key=lambda item: (item.ticker, str(item.instrument_id)),
    )
)


def build_strong_leader_pullback_terminal_reference_final_review(
    *,
    gap_v3_root: Path,
    gap_v3_custody_root: Path,
    gap_v4_root: Path,
    gap_v4_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    consideration_root: Path,
    consideration_custody_root: Path,
    legacy_sec_source_root: Path,
    legacy_sec_source_custody_root: Path,
    terminal_sec_plan_root: Path,
    terminal_sec_plan_custody_root: Path,
    terminal_sec_source_root: Path,
    terminal_sec_source_custody_root: Path,
    supplement_plan_root: Path,
    supplement_plan_custody_root: Path,
    supplement_source_root: Path,
    supplement_source_custody_root: Path,
    canonical_eod_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> bounds.StrongLeaderPullbackTerminalReferenceBoundsV1:
    """Rebuild all 18 bounds from formally retained, outcome-blind evidence."""

    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final-review implementation revision is invalid"
        )
    with _network_prohibited():
        gap_v3 = gap_v3_source.read_strong_leader_pullback_terminal_gap_census_v3(
            output_root=gap_v3_root, output_custody_root=gap_v3_custody_root
        )
        gap_v4 = gap_v4_source.read_strong_leader_pullback_terminal_gap_census_v4(
            output_root=gap_v4_root, output_custody_root=gap_v4_custody_root
        )
        payoff = payoff_source.read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        read_consideration = (
            consideration_source.read_strong_leader_pullback_sec_consideration_adjudication
        )
        consideration = read_consideration(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        initial = sec_review.adjudicate_strong_leader_pullback_terminal_reference_sec_source(
            plan_root=terminal_sec_plan_root,
            plan_custody_root=terminal_sec_plan_custody_root,
            source_root=terminal_sec_source_root,
            source_custody_root=terminal_sec_source_custody_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        adjudicate_supplement = (
            sec_review.adjudicate_strong_leader_pullback_terminal_reference_sec_supplement_source
        )
        supplement = adjudicate_supplement(
            plan_root=supplement_plan_root,
            plan_custody_root=supplement_plan_custody_root,
            source_root=supplement_source_root,
            source_custody_root=supplement_source_custody_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _build_report(
            gap_v3=gap_v3,
            gap_v4=gap_v4,
            payoff=payoff,
            consideration=consideration,
            legacy_sec_source_root=legacy_sec_source_root,
            legacy_sec_source_custody_root=legacy_sec_source_custody_root,
            initial=initial,
            supplement=supplement,
            canonical_eod_root=canonical_eod_root,
        )


def publish_strong_leader_pullback_terminal_reference_final_review(
    *, output_root: Path, output_custody_root: Path, **kwargs: object
) -> StrongLeaderPullbackTerminalReferenceFinalReviewResult:
    """Publish and formally reread an immutable final bounds report."""

    report = build_strong_leader_pullback_terminal_reference_final_review(
        **kwargs  # type: ignore[arg-type]
    )
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_reference_final_review(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                "existing final terminal-reference review differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = _json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                "final terminal-reference report exceeds byte ceiling"
            )
        _write_exclusive(partial / REPORT_FILE, raw)
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_reference_final_review(
        output_root=target, output_custody_root=output_custody_root
    )
    if reread.report != report:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference reread differs"
        )
    return StrongLeaderPullbackTerminalReferenceFinalReviewResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def read_strong_leader_pullback_terminal_reference_final_review(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalReferenceFinalReviewResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = bounds.StrongLeaderPullbackTerminalReferenceBoundsV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference report bytes differ"
        )
    return StrongLeaderPullbackTerminalReferenceFinalReviewResult(
        output_root=root,
        report=report,
        report_sha256=_sha256(raw),
        status="already_present",
    )


def _build_report(
    *, gap_v3: object, gap_v4: object, payoff: object, consideration: object,
    legacy_sec_source_root: Path, legacy_sec_source_custody_root: Path,
    initial: sec_review.StrongLeaderPullbackTerminalReferenceSecAdjudicationV1,
    supplement: sec_review.StrongLeaderPullbackTerminalReferenceSecSupplementAdjudicationV1,
    canonical_eod_root: Path,
) -> bounds.StrongLeaderPullbackTerminalReferenceBoundsV1:
    v3 = gap_v3.report
    v4 = gap_v4.report
    payoff_report = payoff.report
    consideration_report = consideration.report
    if (
        v4.prior_census_report_sha256 != gap_v3.report_sha256
        or v4.prior_census_logical_fingerprint != v3.logical_fingerprint
        or v4.remaining_gap_instrument_count != len(_CASES)
        or v4.remaining_horizon_5_crossing_path_count != bounds.EXPECTED_RESIDUAL_PATH_COUNT
        or payoff_report.consideration_report_sha256 != consideration.report_sha256
        or payoff_report.consideration_logical_fingerprint
        != consideration_report.logical_fingerprint
    ):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference upstream binding differs"
        )
    resolved_by_v4 = {item.instrument_id for item in v4.references}
    gap_by_id = {
        item.instrument_id: item
        for item in v3.decisions
        if item.reference_evidence_count == 0 and item.instrument_id not in resolved_by_v4
    }
    if set(gap_by_id) != {item.instrument_id for item in _CASES}:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference residual population differs"
        )
    payoff_by_id = {item.instrument_id: item for item in payoff_report.decisions}
    initial_by_ticker = {item.ticker_locator: item for item in initial.cases}
    supplement_by_ticker = {item.ticker_locator: item for item in supplement.cases}
    closes = _read_closes(canonical_eod_root)
    legacy_documents = _read_legacy_documents(
        source_root=legacy_sec_source_root,
        custody_root=legacy_sec_source_custody_root,
        expected_manifest_sha256=consideration_report.source_manifest_sha256,
        consideration_by_id={
            item.instrument_id: item for item in consideration_report.decisions
        },
    )
    cases = tuple(
        _build_case(
            spec=spec,
            gap=gap_by_id[spec.instrument_id],
            payoff=payoff_by_id.get(spec.instrument_id),
            initial=initial_by_ticker,
            supplement=supplement_by_ticker,
            closes=closes,
            legacy_documents=legacy_documents,
        )
        for spec in _CASES
    )
    return bounds.build_strong_leader_pullback_terminal_reference_bounds(
        terminal_population_fingerprint=v4.logical_fingerprint,
        cases=cases,
    )


def _build_case(
    *, spec: _CaseSpec, gap: object, payoff: object | None,
    initial: dict[str, sec_review.TerminalReferenceSourceCaseV1],
    supplement: dict[str, sec_review.TerminalReferenceSourceCaseV1],
    closes: dict[str, _CloseSpec], legacy_documents: dict[str, tuple[str, str]],
) -> bounds.TerminalReferenceBoundCaseV1:
    ticker = tuple(gap.provider_ticker_locators)
    if (
        ticker != (spec.ticker,)
        or gap.horizon_5_crossing_path_count != spec.crossing_path_count
    ):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            f"{spec.ticker} residual identity or path count differs"
        )
    terms = _payoff_terms(payoff)
    fields = _source_fields(initial.get(spec.ticker), supplement.get(spec.ticker))
    upper = _calculate_upper(
        calculation=spec.calculation,
        terms=terms,
        fields=fields,
        close=closes.get(spec.close_key or ""),
        legacy_text=(legacy_documents.get(spec.ticker) or ("", ""))[0],
    )
    evidence: list[bounds.TerminalReferenceEvidenceLocatorV1] = []
    if payoff is not None and spec.ticker not in {"LNW", "MTSR", "REVG", "SAND", "SKX"}:
        evidence.append(
            bounds.TerminalReferenceEvidenceLocatorV1(
                evidence_role="retained_payoff_terms",
                evidence_fingerprint=payoff.logical_fingerprint,
            )
        )
    if spec.ticker in legacy_documents:
        evidence.append(
            bounds.TerminalReferenceEvidenceLocatorV1(
                evidence_role="retained_sec_document",
                evidence_fingerprint=legacy_documents[spec.ticker][1],
            )
        )
    for source_case in (initial.get(spec.ticker), supplement.get(spec.ticker)):
        if source_case is not None:
            evidence.append(
                bounds.TerminalReferenceEvidenceLocatorV1(
                    evidence_role="retained_sec_document",
                    evidence_fingerprint=source_case.source_document_sha256,
                )
            )
    if spec.close_key is not None:
        evidence.append(
            bounds.TerminalReferenceEvidenceLocatorV1(
                evidence_role=(
                    "canonical_target_close"
                    if spec.calculation == "lnw_exact"
                    else "canonical_successor_close"
                ),
                evidence_fingerprint=closes[spec.close_key].content_fingerprint,
            )
        )
    evidence_tuple = tuple(
        sorted(
            set(evidence),
            key=lambda item: (item.evidence_role, item.evidence_fingerprint),
        )
    )
    exact = spec.calculation == "lnw_exact"
    return bounds.TerminalReferenceBoundCaseV1(
        instrument_id=spec.instrument_id,
        ticker_locator=spec.ticker,
        prior_gap_state=str(gap.gap_state),
        crossing_path_count=spec.crossing_path_count,
        bound_state=(
            bounds.TerminalReferenceBoundState.EXACT_REFERENCE_READY
            if exact
            else bounds.TerminalReferenceBoundState.FINITE_INTERVAL_READY
        ),
        policy=spec.policy,
        lower_reference_value_usd=_money(upper if exact else Decimal("0")),
        upper_reference_value_usd=_money(upper),
        evidence=evidence_tuple,
    )


def _calculate_upper(
    *, calculation: str, terms: dict[str, Decimal], fields: dict[str, str | Decimal],
    close: _CloseSpec | None, legacy_text: str,
) -> Decimal:
    if calculation == "fixed_cash":
        return _required(terms, "guaranteed_cash")
    if calculation == "cash_plus_cvr":
        return _required(terms, "guaranteed_cash") + _required(terms, "cvr_max_cash")
    if calculation == "aclx_source":
        _require_patterns(
            legacy_text,
            (
                r"price per Share of \(x\)\s*\$115\.00",
                r"(?:amount|payment) of \$5\.00 per CVR",
            ),
        )
        return Decimal("120.00")
    if calculation == "holx_source":
        _require_patterns(legacy_text, (r"\$76\.00 per Share", r"CVR payment \(up to \$3\.00\)"))
        return Decimal("79.00")
    if calculation == "bld_election":
        return max(
            _required(terms, "cash_election_cash"),
            _required(terms, "stock_election_ratio") * _required_close(close),
        )
    if calculation == "snv_stock":
        return _required(terms, "listed_equity_ratio") * _required_close(close)
    if calculation == "thr_election":
        market = _required_close(close)
        return max(
            _required(terms, "cash_election_cash"),
            _required(terms, "mixed_election_cash")
            + _required(terms, "mixed_election_ratio") * market,
            _required(terms, "stock_election_ratio") * market,
        )
    if calculation == "lnw_exact":
        _required_present(fields, "foreign_sole_listing_date")
        _required_present(fields, "last_us_trading_date")
        return _required_close(close)
    if calculation == "mtsr_source":
        return _required_decimal(fields, "cash_usd") + _required_decimal(fields, "cvr_cap_usd")
    if calculation == "revg_source":
        return _required_decimal(fields, "cash_usd") + _required_decimal(
            fields, "listed_equity_ratio"
        ) * _required_close(close)
    if calculation == "sand_source":
        return _required_decimal(fields, "listed_equity_ratio") * _required_close(close)
    if calculation == "skx_source":
        return max(
            _required_decimal(fields, "cash_election_usd"),
            _required_decimal(fields, "mixed_cash_usd")
            + _required_decimal(fields, "unlisted_unit_count")
            * _required_decimal(fields, "unlisted_unit_value_usd"),
        )
    raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
        f"unknown final terminal-reference calculation: {calculation}"
    )


def _payoff_terms(decision: object | None) -> dict[str, Decimal]:
    if decision is None:
        return {}
    return {item.term_key: Decimal(item.normalized_value) for item in decision.terms}


def _source_fields(
    *cases: sec_review.TerminalReferenceSourceCaseV1 | None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for case in cases:
        if case is None:
            continue
        for field in case.fields:
            if field.state is sec_review.TerminalReferenceSourceFieldState.MATCHED:
                current = values.setdefault(field.field_key, field.expected_value)
                if current != field.expected_value:
                    raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                        "terminal-reference duplicate source fields differ"
                    )
    return values


def _read_closes(canonical_eod_root: Path) -> dict[str, _CloseSpec]:
    repository = CanonicalEodReadRepository(canonical_eod_root)
    result: dict[str, _CloseSpec] = {}
    for key, spec in _CLOSES.items():
        integrity = repository.inspect_session(spec.session_date)
        matches = tuple(
            item
            for item in repository.read_bars(spec.session_date)
            if item.instrument_id == spec.instrument_id
        )
        if (
            integrity.content_fingerprint != spec.content_fingerprint
            or len(matches) != 1
            or matches[0].ticker != spec.ticker
            or Decimal(matches[0].close) != spec.close_usd
            or matches[0].currency != "USD"
            or matches[0].quality_status.value != "valid"
        ):
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                f"canonical close evidence differs for {key}"
            )
        result[key] = spec
    return result


def _read_legacy_documents(
    *, source_root: Path, custody_root: Path, expected_manifest_sha256: str,
    consideration_by_id: dict[UUID, object],
) -> dict[str, tuple[str, str]]:
    root = legacy_source._validated_completed_output(source_root, custody_root)
    manifest_path = root / legacy_source.MANIFEST_FILE
    legacy_source._require_regular_file(
        manifest_path, 0o400, legacy_source.MAXIMUM_MANIFEST_BYTES
    )
    manifest_raw = manifest_path.read_bytes()
    try:
        model = legacy_source.StrongLeaderPullbackSecDocumentSourceManifestV1
        manifest = model.model_validate_json(manifest_raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "legacy SEC source manifest is invalid"
        ) from exc
    if (
        _sha256(manifest_raw) != expected_manifest_sha256
        or manifest_raw != legacy_source._json_bytes(manifest.model_dump(mode="json"))
    ):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "legacy SEC source manifest binding differs"
        )
    results: dict[str, tuple[str, str]] = {}
    for spec in _CASES:
        if spec.legacy_request_sequence is None:
            continue
        directory = root / f"request={spec.legacy_request_sequence:06d}"
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or directory.parent != root
            or directory.stat().st_uid != os.getuid()
            or stat.S_IMODE(directory.stat().st_mode) != 0o700
            or directory.resolve(strict=True) != directory
        ):
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                f"legacy SEC artifact directory differs for {spec.ticker}"
            )
        artifact_path = directory / legacy_source.ARTIFACT_FILE
        document_path = directory / legacy_source.DOCUMENT_FILE
        legacy_source._require_regular_file(
            artifact_path, 0o400, legacy_source.MAXIMUM_ARTIFACT_BYTES
        )
        legacy_source._require_regular_file(
            document_path, 0o400, legacy_source.MAXIMUM_DOCUMENT_BYTES
        )
        try:
            artifact_raw = artifact_path.read_bytes()
            artifact = (
                legacy_source.SecPrimaryDocumentArtifactV1.model_validate_json(
                    artifact_raw
                )
            )
        except Exception as exc:
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                f"legacy SEC artifact is invalid for {spec.ticker}"
            ) from exc
        consideration = consideration_by_id.get(spec.instrument_id)
        raw = document_path.read_bytes()
        if (
            consideration is None
            or artifact.request_sequence != spec.legacy_request_sequence
            or artifact.instrument_id != spec.instrument_id
            or artifact.physical_sha256 != _sha256(raw)
            or artifact.physical_sha256 != consideration.document_sha256
            or artifact.byte_count != len(raw)
            or artifact_raw
            != legacy_source._json_bytes(artifact.model_dump(mode="json"))
        ):
            raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
                f"legacy SEC document binding differs for {spec.ticker}"
            )
        decoded, _ = text._decode(raw)
        parser = text._DocumentTextParser()
        parser.feed(decoded)
        parser.close()
        normalized = " ".join(" ".join(parser.parts).split())
        results[spec.ticker] = (normalized, artifact.physical_sha256)
    return results


def _required(values: dict[str, Decimal], key: str) -> Decimal:
    value = values.get(key)
    if value is None:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            f"required terminal-reference term is absent: {key}"
        )
    return value


def _required_present(values: dict[str, str | Decimal], key: str) -> str | Decimal:
    value = values.get(key)
    if value is None:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            f"required terminal-reference term is absent: {key}"
        )
    return value


def _required_decimal(values: dict[str, str | Decimal], key: str) -> Decimal:
    return Decimal(str(_required_present(values, key)))


def _required_close(value: _CloseSpec | None) -> Decimal:
    if value is None:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "required canonical close is absent"
        )
    return value.close_usd


def _require_patterns(value: str, patterns: tuple[str, ...]) -> None:
    if any(re.search(pattern, value, flags=re.IGNORECASE) is None for pattern in patterns):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "legacy SEC terminal-reference fields differ"
        )


def _money(value: Decimal) -> str:
    return format(value.quantize(_MONEY_QUANTUM), "f")


@contextmanager
def _network_prohibited() -> Iterator[None]:
    import socket

    original = socket.socket

    def stopped(*args: object, **kwargs: object) -> object:
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "network access is prohibited during final terminal-reference review"
        )

    socket.socket = stopped  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original  # type: ignore[assignment]


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference paths must be absolute"
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
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference custody or target is unsafe"
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
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalReferenceFinalReviewError(
            "final terminal-reference file metadata differs"
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
