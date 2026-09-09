"""Read-only candidate diagnostic for resolved cash-dividend observations."""

from __future__ import annotations

import hashlib
import json
import socket
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Iterator
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    HistoricalDatasetCoverageEvidenceV1,
    HistoricalDatasetFamily,
    ResolutionStatus,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.services.corporate_action_source_canonical import (
    CanonicalCorporateActionSourceError,
    read_canonical_corporate_action_source,
)
from tip_api.services.historical_adjustment_invariants import (
    calculate_cash_dividend_backward_factor,
)
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "canonical-cash-dividend-candidate-diagnostic/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LARGE_DISTRIBUTION_REVIEW_THRESHOLD = Decimal("0.25")
SEVERE_LOWER_RATIO = Decimal("0.5")
SEVERE_UPPER_RATIO = Decimal("2")
RATIO_QUANTUM = Decimal("0.000000000001")
_SPLIT_TYPES = frozenset(
    {
        CorporateActionType.STOCK_SPLIT,
        CorporateActionType.REVERSE_SPLIT,
        CorporateActionType.STOCK_DIVIDEND,
    }
)


class CanonicalCashDividendCandidateDiagnosticError(RuntimeError):
    """Raised when the cash-dividend diagnostic cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CashDividendCandidateReviewFlag:
    instrument_id: str
    effective_date: str
    prior_session: str | None
    source_action_ids: tuple[str, ...]
    provider_tickers: tuple[str, ...]
    currencies: tuple[str, ...]
    cash_amount_total: str | None
    pre_ex_close: str | None
    current_open: str | None
    calculated_backward_factor: str | None
    cash_to_prior_close_ratio: str | None
    raw_open_to_prior_close_ratio: str | None
    cash_inclusive_open_to_prior_close_ratio: str | None
    review_reasons: tuple[str, ...]
    source_action_set_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalCashDividendCandidateDiagnosticReport:
    contract_version: str
    source_revision: str
    calculated_at: str
    data_root: str
    source_publication_path: str
    source_publication_sha256: str
    source_publication_fingerprint: str
    eod_evidence_path: str
    eod_evidence_sha256: str
    eod_evidence_fingerprint: str
    first_session: str
    last_session: str
    source_dividend_record_count: int
    resolved_dividend_record_count: int
    unresolved_dividend_record_count: int
    resolved_dividend_group_count: int
    bounded_arithmetic_candidate_group_count: int
    review_group_count: int
    large_distribution_review_group_count: int
    large_distribution_date_order_review_group_count: int
    multiple_same_date_dividend_group_count: int
    same_date_split_group_count: int
    non_usd_group_count: int
    adjacent_eod_unavailable_group_count: int
    cash_not_below_pre_ex_close_group_count: int
    cash_inclusive_price_discontinuity_review_group_count: int
    review_flags: tuple[CashDividendCandidateReviewFlag, ...]
    large_distribution_review_threshold: str
    severe_lower_ratio: str
    severe_upper_ratio: str
    provider_factor_usage: str
    source_point_in_time_eligibility: str
    external_request_count: int
    filesystem_write_count: int
    canonical_data_write_count: int
    adjustment_ledger_write_count: int
    canonical_dividend_authorized: bool
    total_return_adjustment_authorized: bool
    absent_row_neutrality_authorized: bool
    historical_coverage_authorized: bool
    research_performance_authorized: bool
    logical_fingerprint: str

    def as_dict(self, *, include_flags: bool = True) -> dict[str, object]:
        value = asdict(self)
        if not include_flags:
            value.pop("review_flags")
        return value


@dataclass(frozen=True, slots=True)
class _PricePair:
    prior_session: date
    pre_ex_close: Decimal
    current_open: Decimal


def diagnose_canonical_cash_dividend_candidates(
    *,
    data_root: Path,
    source_publication_path: Path,
    eod_evidence_path: Path,
    source_revision: str,
    calculated_at: datetime,
) -> CanonicalCashDividendCandidateDiagnosticReport:
    """Classify bounded dividend arithmetic without writing or promotion."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        calculated = normalize_utc_datetime(calculated_at)
        if not _is_revision(source_revision):
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend diagnostic source revision is malformed"
            )
        try:
            source = read_canonical_corporate_action_source(
                data_root=root,
                publication_path=source_publication_path,
            )
            eod_source = ParquetHistoricalCoverageRepository(
                root
            ).read_dataset_evidence(eod_evidence_path)
        except (
            CanonicalCorporateActionSourceError,
            HistoricalResearchPersistenceError,
        ) as exc:
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend source failed formal reread"
            ) from exc

        evidence = eod_source.evidence
        _validate_source_scope(
            source_publication=source.publication,
            evidence=evidence,
            calculated_at=calculated,
        )
        dividends = tuple(
            item
            for item in source.records
            if item.action_type is CorporateActionType.CASH_DIVIDEND
        )
        resolved = tuple(
            item
            for item in dividends
            if item.instrument_resolution_status is ResolutionStatus.RESOLVED
        )
        unresolved = tuple(
            item
            for item in dividends
            if item.instrument_resolution_status is not ResolutionStatus.RESOLVED
        )
        groups = _resolved_dividend_groups(resolved)
        same_date_split_keys = frozenset(
            (item.instrument_id, item.effective_date)
            for item in source.records
            if item.instrument_id is not None
            and item.action_type in _SPLIT_TYPES
        )
        prices = _read_required_price_pairs(
            root=root,
            evidence=evidence,
            keys=frozenset(groups),
        )

        review_flags: list[CashDividendCandidateReviewFlag] = []
        bounded_candidate_count = 0
        for key, group in sorted(
            groups.items(), key=lambda item: (item[0][1], str(item[0][0]))
        ):
            flag = _review_group(
                key=key,
                group=group,
                price_pair=prices.get(key),
                same_date_split=key in same_date_split_keys,
            )
            if flag is None:
                bounded_candidate_count += 1
            else:
                review_flags.append(flag)
        flags = tuple(review_flags)
        reason_sets = tuple(frozenset(item.review_reasons) for item in flags)
        logical = {
            "contract_version": CONTRACT_VERSION,
            "source_revision": source_revision,
            "calculated_at": calculated.isoformat(),
            "data_root": str(root),
            "source_publication_path": str(source.publication_path),
            "source_publication_sha256": source.publication_sha256,
            "source_publication_fingerprint": source.publication.logical_fingerprint,
            "eod_evidence_path": str(eod_source.evidence_path),
            "eod_evidence_sha256": eod_source.physical_sha256,
            "eod_evidence_fingerprint": evidence.logical_fingerprint,
            "first_session": evidence.sessions[0].isoformat(),
            "last_session": evidence.sessions[-1].isoformat(),
            "source_dividend_record_count": len(dividends),
            "resolved_dividend_record_count": len(resolved),
            "unresolved_dividend_record_count": len(unresolved),
            "resolved_dividend_group_count": len(groups),
            "bounded_arithmetic_candidate_group_count": bounded_candidate_count,
            "review_group_count": len(flags),
            "large_distribution_review_group_count": _reason_count(
                reason_sets, "large_cash_distribution_requires_independent_ex_date"
            ),
            "large_distribution_date_order_review_group_count": _reason_count(
                reason_sets, "large_cash_distribution_date_order_review"
            ),
            "multiple_same_date_dividend_group_count": _reason_count(
                reason_sets, "multiple_same_date_dividend_actions"
            ),
            "same_date_split_group_count": _reason_count(
                reason_sets, "same_date_split_action"
            ),
            "non_usd_group_count": _reason_count(
                reason_sets, "non_usd_cash_distribution"
            ),
            "adjacent_eod_unavailable_group_count": _reason_count(
                reason_sets, "adjacent_eod_unavailable"
            ),
            "cash_not_below_pre_ex_close_group_count": _reason_count(
                reason_sets, "cash_not_below_pre_ex_close"
            ),
            "cash_inclusive_price_discontinuity_review_group_count": _reason_count(
                reason_sets, "cash_inclusive_price_discontinuity_review"
            ),
            "review_flags": tuple(item.as_dict() for item in flags),
            "large_distribution_review_threshold": str(
                LARGE_DISTRIBUTION_REVIEW_THRESHOLD
            ),
            "severe_lower_ratio": str(SEVERE_LOWER_RATIO),
            "severe_upper_ratio": str(SEVERE_UPPER_RATIO),
            "provider_factor_usage": "audit_only_cumulative_or_unverified_basis",
            "source_point_in_time_eligibility": "outcome_reconciliation_only",
            "external_request_count": 0,
            "filesystem_write_count": 0,
            "canonical_data_write_count": 0,
            "adjustment_ledger_write_count": 0,
            "canonical_dividend_authorized": False,
            "total_return_adjustment_authorized": False,
            "absent_row_neutrality_authorized": False,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
        }
        values = dict(logical)
        values["review_flags"] = flags
        report = CanonicalCashDividendCandidateDiagnosticReport(
            **values,
            logical_fingerprint=_fingerprint(logical),
        )
        verify_canonical_cash_dividend_candidate_diagnostic(report)
        return report


def verify_canonical_cash_dividend_candidate_diagnostic(
    report: CanonicalCashDividendCandidateDiagnosticReport,
) -> None:
    if not isinstance(report, CanonicalCashDividendCandidateDiagnosticReport):
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend report contract is invalid"
        )
    if not all(
        isinstance(item, CashDividendCandidateReviewFlag)
        for item in report.review_flags
    ):
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend report flags are invalid"
        )
    reason_sets = tuple(
        frozenset(item.review_reasons) for item in report.review_flags
    )
    logical = report.as_dict()
    logical.pop("logical_fingerprint")
    if (
        report.contract_version != CONTRACT_VERSION
        or report.logical_fingerprint != _fingerprint(logical)
        or not _is_revision(report.source_revision)
        or Path(report.data_root) != APPROVED_DATA_ROOT
        or report.resolved_dividend_record_count
        + report.unresolved_dividend_record_count
        != report.source_dividend_record_count
        or report.bounded_arithmetic_candidate_group_count
        + report.review_group_count
        != report.resolved_dividend_group_count
        or report.review_group_count != len(report.review_flags)
        or report.large_distribution_review_group_count
        != _reason_count(
            reason_sets, "large_cash_distribution_requires_independent_ex_date"
        )
        or report.large_distribution_date_order_review_group_count
        != _reason_count(
            reason_sets, "large_cash_distribution_date_order_review"
        )
        or report.multiple_same_date_dividend_group_count
        != _reason_count(reason_sets, "multiple_same_date_dividend_actions")
        or report.same_date_split_group_count
        != _reason_count(reason_sets, "same_date_split_action")
        or report.non_usd_group_count
        != _reason_count(reason_sets, "non_usd_cash_distribution")
        or report.adjacent_eod_unavailable_group_count
        != _reason_count(reason_sets, "adjacent_eod_unavailable")
        or report.cash_not_below_pre_ex_close_group_count
        != _reason_count(reason_sets, "cash_not_below_pre_ex_close")
        or report.cash_inclusive_price_discontinuity_review_group_count
        != _reason_count(reason_sets, "cash_inclusive_price_discontinuity_review")
        or report.large_distribution_review_threshold
        != str(LARGE_DISTRIBUTION_REVIEW_THRESHOLD)
        or report.severe_lower_ratio != str(SEVERE_LOWER_RATIO)
        or report.severe_upper_ratio != str(SEVERE_UPPER_RATIO)
        or report.provider_factor_usage
        != "audit_only_cumulative_or_unverified_basis"
        or report.source_point_in_time_eligibility
        != "outcome_reconciliation_only"
        or report.external_request_count != 0
        or report.filesystem_write_count != 0
        or report.canonical_data_write_count != 0
        or report.adjustment_ledger_write_count != 0
        or report.canonical_dividend_authorized
        or report.total_return_adjustment_authorized
        or report.absent_row_neutrality_authorized
        or report.historical_coverage_authorized
        or report.research_performance_authorized
    ):
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend report content or authority differs"
        )


def _resolved_dividend_groups(
    records: tuple[CorporateActionSourceObservationV1, ...],
) -> dict[tuple[UUID, date], tuple[CorporateActionSourceObservationV1, ...]]:
    grouped: dict[
        tuple[UUID, date], list[CorporateActionSourceObservationV1]
    ] = defaultdict(list)
    for record in records:
        if record.instrument_id is None:
            raise CanonicalCashDividendCandidateDiagnosticError(
                "resolved dividend is missing stable identity"
            )
        grouped[(record.instrument_id, record.effective_date)].append(record)
    return {
        key: tuple(
            sorted(
                values,
                key=lambda item: (item.source_action_id, item.source_revision),
            )
        )
        for key, values in grouped.items()
    }


def _read_required_price_pairs(
    *,
    root: Path,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    keys: frozenset[tuple[UUID, date]],
) -> dict[tuple[UUID, date], _PricePair]:
    calendar = ExchangeCalendar()
    prior_by_key = {
        key: calendar.previous_session(key[1]) for key in keys
    }
    current_targets = defaultdict(set)
    prior_targets = defaultdict(set)
    for key, prior_session in prior_by_key.items():
        current_targets[key[1]].add(key[0])
        prior_targets[prior_session].add(key[0])
    current_open: dict[tuple[UUID, date], Decimal] = {}
    prior_close: dict[tuple[UUID, date], Decimal] = {}
    observed_records = 0
    for artifact in evidence.artifacts:
        references = tuple(
            item for item in artifact.payload_files if item.path.endswith(".parquet")
        )
        if len(references) != 1 or artifact.first_session != artifact.last_session:
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend EOD artifact scope differs"
            )
        session = artifact.first_session
        path = root / references[0].path
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve(strict=True) != path
            or not path.is_relative_to(root)
        ):
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend EOD artifact custody differs"
            )
        seen: set[UUID] = set()
        try:
            batches = pq.ParquetFile(path).iter_batches(
                batch_size=65_536,
                columns=["instrument_id", "session_date", "open", "close"],
            )
            for batch in batches:
                table = pa.Table.from_batches([batch])
                _validate_eod_schema(table.schema)
                columns = [
                    table.column(name).to_pylist() for name in table.column_names
                ]
                for raw_id, raw_session, raw_open, raw_close in zip(
                    *columns, strict=True
                ):
                    instrument_id = UUID(raw_id)
                    if instrument_id in seen or raw_session != session:
                        raise CanonicalCashDividendCandidateDiagnosticError(
                            "cash-dividend EOD row identity differs"
                        )
                    seen.add(instrument_id)
                    observed_records += 1
                    if raw_open <= 0 or raw_close <= 0:
                        raise CanonicalCashDividendCandidateDiagnosticError(
                            "cash-dividend EOD price is nonpositive"
                        )
                    if instrument_id in current_targets.get(session, set()):
                        current_open[(instrument_id, session)] = raw_open
                    if instrument_id in prior_targets.get(session, set()):
                        prior_close[(instrument_id, session)] = raw_close
        except CanonicalCashDividendCandidateDiagnosticError:
            raise
        except (
            AttributeError,
            pa.ArrowException,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend EOD scan failed"
            ) from exc
        if len(seen) != artifact.record_count:
            raise CanonicalCashDividendCandidateDiagnosticError(
                "cash-dividend EOD artifact count differs"
            )
    if observed_records != evidence.record_count:
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend EOD family count differs"
        )
    result = {}
    for key, prior_session in prior_by_key.items():
        prior = prior_close.get((key[0], prior_session))
        current = current_open.get(key)
        if prior is not None and current is not None:
            result[key] = _PricePair(
                prior_session=prior_session,
                pre_ex_close=prior,
                current_open=current,
            )
    return result


def _review_group(
    *,
    key: tuple[UUID, date],
    group: tuple[CorporateActionSourceObservationV1, ...],
    price_pair: _PricePair | None,
    same_date_split: bool,
) -> CashDividendCandidateReviewFlag | None:
    reasons: set[str] = set()
    if any(item.record_status is not CorporateActionRecordStatus.ACTIVE for item in group):
        reasons.add("source_record_not_active")
    if len(group) > 1:
        reasons.add("multiple_same_date_dividend_actions")
    currencies = tuple(sorted({item.currency or "UNKNOWN" for item in group}))
    if len(currencies) > 1:
        reasons.add("mixed_cash_currencies")
    if currencies != ("USD",):
        reasons.add("non_usd_cash_distribution")
    if same_date_split:
        reasons.add("same_date_split_action")
    if any(item.ex_date != item.effective_date for item in group):
        reasons.add("reported_ex_date_mismatch")
    if price_pair is None:
        reasons.add("adjacent_eod_unavailable")

    cash_total: Decimal | None = None
    factor: Decimal | None = None
    cash_ratio: Decimal | None = None
    raw_ratio: Decimal | None = None
    cash_inclusive_ratio: Decimal | None = None
    if currencies == ("USD",) and all(item.cash_amount is not None for item in group):
        cash_total = sum(
            (item.cash_amount for item in group if item.cash_amount is not None),
            start=Decimal("0"),
        )
    if cash_total is not None and price_pair is not None:
        raw_ratio = _ratio(price_pair.current_open, price_pair.pre_ex_close)
        cash_inclusive_ratio = _ratio(
            price_pair.current_open + cash_total,
            price_pair.pre_ex_close,
        )
        cash_ratio = _ratio(cash_total, price_pair.pre_ex_close)
        if cash_total >= price_pair.pre_ex_close:
            reasons.add("cash_not_below_pre_ex_close")
        else:
            factor = calculate_cash_dividend_backward_factor(
                cash_amount_on_reference_share_basis=cash_total,
                pre_ex_close_on_same_share_basis=price_pair.pre_ex_close,
            )
        if cash_ratio >= LARGE_DISTRIBUTION_REVIEW_THRESHOLD:
            reasons.add("large_cash_distribution_requires_independent_ex_date")
            if any(
                item.pay_date is None or item.effective_date <= item.pay_date
                for item in group
            ):
                reasons.add("large_cash_distribution_date_order_review")
        if _severe(cash_inclusive_ratio):
            reasons.add("cash_inclusive_price_discontinuity_review")
    if not reasons:
        return None
    source_evidence = tuple(
        {
            "source_action_id": item.source_action_id,
            "source_revision": item.source_revision,
        }
        for item in group
    )
    return CashDividendCandidateReviewFlag(
        instrument_id=str(key[0]),
        effective_date=key[1].isoformat(),
        prior_session=(
            price_pair.prior_session.isoformat() if price_pair is not None else None
        ),
        source_action_ids=tuple(item.source_action_id for item in group),
        provider_tickers=tuple(sorted({item.provider_ticker for item in group})),
        currencies=currencies,
        cash_amount_total=_optional_decimal(cash_total),
        pre_ex_close=_optional_decimal(
            price_pair.pre_ex_close if price_pair is not None else None
        ),
        current_open=_optional_decimal(
            price_pair.current_open if price_pair is not None else None
        ),
        calculated_backward_factor=_optional_decimal(factor),
        cash_to_prior_close_ratio=_optional_decimal(cash_ratio),
        raw_open_to_prior_close_ratio=_optional_decimal(raw_ratio),
        cash_inclusive_open_to_prior_close_ratio=_optional_decimal(
            cash_inclusive_ratio
        ),
        review_reasons=tuple(sorted(reasons)),
        source_action_set_fingerprint=_fingerprint(source_evidence),
    )


def _validate_source_scope(
    *,
    source_publication: object,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    calculated_at: datetime,
) -> None:
    if (
        evidence.family is not HistoricalDatasetFamily.EOD_PRICE_BAR
        or not evidence.sessions
        or evidence.sessions[0] != source_publication.start_date
        or evidence.sessions[-1] != source_publication.end_date
        or source_publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or source_publication.canonical_corporate_action_authorized is not False
        or source_publication.adjustment_ledger_authorized is not False
        or calculated_at < max(source_publication.created_at, evidence.created_at)
    ):
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend source scope differs"
        )


def _validate_eod_schema(schema: pa.Schema) -> None:
    if (
        schema.names != ["instrument_id", "session_date", "open", "close"]
        or not pa.types.is_string(schema.field("instrument_id").type)
        or not pa.types.is_date32(schema.field("session_date").type)
        or not pa.types.is_decimal(schema.field("open").type)
        or not pa.types.is_decimal(schema.field("close").type)
    ):
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend EOD projection schema differs"
        )


def _reason_count(reason_sets: tuple[frozenset[str], ...], reason: str) -> int:
    return sum(reason in item for item in reason_sets)


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if numerator < 0 or denominator <= 0:
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend ratio inputs differ"
        )
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        return (numerator / denominator).quantize(RATIO_QUANTUM)


def _severe(ratio: Decimal) -> bool:
    return ratio <= SEVERE_LOWER_RATIO or ratio >= SEVERE_UPPER_RATIO


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalCashDividendCandidateDiagnosticError(
            "cash-dividend data root is not approved"
        )
    return resolved


def _is_revision(value: str) -> bool:
    return len(value) == 40 and all(
        character in "0123456789abcdef" for character in value
    )


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalCashDividendCandidateDiagnosticError(
            "network is prohibited during cash-dividend diagnosis"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
