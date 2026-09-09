"""Read-only negative-space diagnostic for canonical split coverage."""

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
from typing import Iterator, Literal
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CanonicalSplitActionQuarantineImpactV1,
    CanonicalSplitActionPublicationV1,
    CanonicalSplitActionV1,
    CorporateActionRecordStatus,
    HistoricalDatasetCoverageEvidenceV1,
    HistoricalDatasetFamily,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    CanonicalSplitActionPersistenceError,
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.services.historical_adjustment_invariants import (
    calculate_composed_split_adjustment_multipliers,
)
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "canonical-split-coverage-diagnostic/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
SEVERE_LOWER_RATIO = Decimal("0.5")
SEVERE_UPPER_RATIO = Decimal("2")
RATIO_QUANTUM = Decimal("0.000000000001")

FlagClassification = Literal[
    "active_split_residual_bounded",
    "active_split_residual_extreme",
    "canonical_action_quarantined",
    "unresolved_impact_quarantined",
    "known_event_current_bar_missing",
    "known_event_adjacent_transition_missing",
    "unexplained_price_discontinuity",
]


class CanonicalSplitCoverageDiagnosticError(RuntimeError):
    """Raised when the read-only split-coverage diagnostic cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitCoverageFlag:
    instrument_id: str
    prior_session: str | None
    session_date: str
    classification: FlagClassification
    raw_open_to_prior_close_ratio: str | None
    expected_split_price_multiplier: str | None
    residual_ratio: str | None
    source_action_set_fingerprint: str | None
    quality_flags: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalSplitCoverageDiagnosticReport:
    contract_version: str
    source_revision: str
    calculated_at: str
    data_root: str
    canonical_action_publication_root: str
    canonical_action_manifest_sha256: str
    canonical_action_publication_fingerprint: str
    eod_evidence_path: str
    eod_evidence_sha256: str
    eod_evidence_fingerprint: str
    first_session: str
    last_session: str
    source_session_count: int
    source_eod_record_count: int
    adjacent_transition_count: int
    known_event_group_count: int
    known_event_comparable_count: int
    known_event_current_bar_missing_count: int
    known_event_adjacent_transition_missing_count: int
    active_split_residual_bounded_count: int
    active_split_residual_extreme_count: int
    canonical_action_quarantined_count: int
    unresolved_impact_quarantined_count: int
    unexplained_price_discontinuity_count: int
    unexplained_price_discontinuity_instrument_count: int
    flag_count: int
    severe_lower_ratio: str
    severe_upper_ratio: str
    flags: tuple[CanonicalSplitCoverageFlag, ...]
    external_request_count: int
    filesystem_write_count: int
    canonical_data_write_count: int
    price_inference_promoted_to_action: bool
    absent_row_neutrality_authorized: bool
    full_corporate_action_coverage_authorized: bool
    total_return_adjustment_authorized: bool
    historical_coverage_authorized: bool
    research_performance_authorized: bool
    logical_fingerprint: str

    def as_dict(self, *, include_flags: bool = True) -> dict[str, object]:
        value = asdict(self)
        if not include_flags:
            value.pop("flags")
        return value


def diagnose_canonical_split_coverage(
    *,
    data_root: Path,
    canonical_action_publication_root: Path,
    eod_evidence_path: Path,
    source_revision: str,
    calculated_at: datetime,
) -> CanonicalSplitCoverageDiagnosticReport:
    """Scan adjacent EOD transitions without inferring or writing an action."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        calculated = normalize_utc_datetime(calculated_at)
        if not _is_revision(source_revision):
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage source revision is malformed"
            )
        try:
            action_source = read_canonical_split_action_publication(
                data_root=root,
                publication_root=canonical_action_publication_root,
            )
            eod_source = ParquetHistoricalCoverageRepository(
                root
            ).read_dataset_evidence(eod_evidence_path)
        except (
            CanonicalSplitActionPersistenceError,
            HistoricalResearchPersistenceError,
        ) as exc:
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage source failed formal reread"
            ) from exc

        evidence = eod_source.evidence
        _validate_source_scope(
            action_publication=action_source.publication,
            evidence=evidence,
            calculated_at=calculated,
        )
        active, quarantined = _action_groups(action_source.actions)
        impacts = _impact_groups(
            action_source.publication.possible_unresolved_impacts
        )
        known_keys = frozenset(active) | frozenset(quarantined) | frozenset(impacts)
        scan = _scan_eod_transitions(
            root=root,
            evidence=evidence,
            active=active,
            quarantined=quarantined,
            impacts=impacts,
        )
        missing_flags = _missing_known_event_flags(
            known_keys=known_keys,
            observed_current_keys=scan.observed_current_keys,
            comparable_known_keys=scan.comparable_known_keys,
            active=active,
            quarantined=quarantined,
            impacts=impacts,
        )
        flags = tuple(
            sorted(
                (*scan.flags, *missing_flags),
                key=lambda item: (
                    item.session_date,
                    item.instrument_id,
                    item.classification,
                ),
            )
        )
        classifications = tuple(item.classification for item in flags)
        logical = {
            "contract_version": CONTRACT_VERSION,
            "source_revision": source_revision,
            "calculated_at": calculated.isoformat(),
            "data_root": str(root),
            "canonical_action_publication_root": str(action_source.root),
            "canonical_action_manifest_sha256": action_source.manifest_sha256,
            "canonical_action_publication_fingerprint": (
                action_source.publication.logical_fingerprint
            ),
            "eod_evidence_path": str(eod_source.evidence_path),
            "eod_evidence_sha256": eod_source.physical_sha256,
            "eod_evidence_fingerprint": evidence.logical_fingerprint,
            "first_session": evidence.sessions[0].isoformat(),
            "last_session": evidence.sessions[-1].isoformat(),
            "source_session_count": len(evidence.sessions),
            "source_eod_record_count": evidence.record_count,
            "adjacent_transition_count": scan.adjacent_transition_count,
            "known_event_group_count": len(known_keys),
            "known_event_comparable_count": len(scan.comparable_known_keys),
            "known_event_current_bar_missing_count": classifications.count(
                "known_event_current_bar_missing"
            ),
            "known_event_adjacent_transition_missing_count": classifications.count(
                "known_event_adjacent_transition_missing"
            ),
            "active_split_residual_bounded_count": classifications.count(
                "active_split_residual_bounded"
            ),
            "active_split_residual_extreme_count": classifications.count(
                "active_split_residual_extreme"
            ),
            "canonical_action_quarantined_count": classifications.count(
                "canonical_action_quarantined"
            ),
            "unresolved_impact_quarantined_count": classifications.count(
                "unresolved_impact_quarantined"
            ),
            "unexplained_price_discontinuity_count": classifications.count(
                "unexplained_price_discontinuity"
            ),
            "unexplained_price_discontinuity_instrument_count": len(
                {
                    item.instrument_id
                    for item in flags
                    if item.classification
                    == "unexplained_price_discontinuity"
                }
            ),
            "flag_count": len(flags),
            "severe_lower_ratio": str(SEVERE_LOWER_RATIO),
            "severe_upper_ratio": str(SEVERE_UPPER_RATIO),
            "flags": tuple(item.as_dict() for item in flags),
            "external_request_count": 0,
            "filesystem_write_count": 0,
            "canonical_data_write_count": 0,
            "price_inference_promoted_to_action": False,
            "absent_row_neutrality_authorized": False,
            "full_corporate_action_coverage_authorized": False,
            "total_return_adjustment_authorized": False,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
        }
        report_values = dict(logical)
        report_values["flags"] = flags
        report = CanonicalSplitCoverageDiagnosticReport(
            **report_values,
            logical_fingerprint=_fingerprint(logical),
        )
        verify_canonical_split_coverage_diagnostic(report)
        return report


def verify_canonical_split_coverage_diagnostic(
    report: CanonicalSplitCoverageDiagnosticReport,
) -> None:
    if not isinstance(report, CanonicalSplitCoverageDiagnosticReport):
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage report contract is invalid"
        )
    if not all(isinstance(item, CanonicalSplitCoverageFlag) for item in report.flags):
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage report flags are invalid"
        )
    classifications = tuple(item.classification for item in report.flags)
    logical = report.as_dict()
    logical.pop("logical_fingerprint")
    if (
        report.contract_version != CONTRACT_VERSION
        or report.logical_fingerprint != _fingerprint(logical)
        or not _is_revision(report.source_revision)
        or Path(report.data_root) != APPROVED_DATA_ROOT
        or report.severe_lower_ratio != str(SEVERE_LOWER_RATIO)
        or report.severe_upper_ratio != str(SEVERE_UPPER_RATIO)
        or report.flag_count != len(report.flags)
        or report.active_split_residual_bounded_count
        != classifications.count("active_split_residual_bounded")
        or report.active_split_residual_extreme_count
        != classifications.count("active_split_residual_extreme")
        or report.canonical_action_quarantined_count
        != classifications.count("canonical_action_quarantined")
        or report.unresolved_impact_quarantined_count
        != classifications.count("unresolved_impact_quarantined")
        or report.known_event_current_bar_missing_count
        != classifications.count("known_event_current_bar_missing")
        or report.known_event_adjacent_transition_missing_count
        != classifications.count("known_event_adjacent_transition_missing")
        or report.unexplained_price_discontinuity_count
        != classifications.count("unexplained_price_discontinuity")
        or report.unexplained_price_discontinuity_instrument_count
        != len(
            {
                item.instrument_id
                for item in report.flags
                if item.classification == "unexplained_price_discontinuity"
            }
        )
        or report.known_event_group_count
        != (
            report.known_event_comparable_count
            + report.known_event_current_bar_missing_count
            + report.known_event_adjacent_transition_missing_count
        )
        or report.external_request_count != 0
        or report.filesystem_write_count != 0
        or report.canonical_data_write_count != 0
        or report.price_inference_promoted_to_action
        or report.absent_row_neutrality_authorized
        or report.full_corporate_action_coverage_authorized
        or report.total_return_adjustment_authorized
        or report.historical_coverage_authorized
        or report.research_performance_authorized
    ):
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage report content or authority differs"
        )


@dataclass(frozen=True, slots=True)
class _ScanResult:
    adjacent_transition_count: int
    observed_current_keys: frozenset[tuple[UUID, date]]
    comparable_known_keys: frozenset[tuple[UUID, date]]
    flags: tuple[CanonicalSplitCoverageFlag, ...]


def _scan_eod_transitions(
    *,
    root: Path,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    active: dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
    quarantined: dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
    impacts: dict[tuple[UUID, date], CanonicalSplitActionQuarantineImpactV1],
) -> _ScanResult:
    calendar = ExchangeCalendar()
    expected_prior = {
        session: calendar.previous_session(session) for session in evidence.sessions
    }
    previous: dict[UUID, tuple[date, Decimal]] = {}
    observed_current: set[tuple[UUID, date]] = set()
    comparable_known: set[tuple[UUID, date]] = set()
    flags: list[CanonicalSplitCoverageFlag] = []
    adjacent_count = 0
    observed_records = 0

    for artifact in evidence.artifacts:
        references = tuple(
            item for item in artifact.payload_files if item.path.endswith(".parquet")
        )
        if len(references) != 1 or artifact.first_session != artifact.last_session:
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage EOD artifact scope differs"
            )
        session = artifact.first_session
        path = root / references[0].path
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve(strict=True) != path
            or not path.is_relative_to(root)
        ):
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage EOD artifact custody differs"
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
                        raise CanonicalSplitCoverageDiagnosticError(
                            "split-coverage EOD row identity differs"
                        )
                    seen.add(instrument_id)
                    observed_records += 1
                    if raw_open <= 0 or raw_close <= 0:
                        raise CanonicalSplitCoverageDiagnosticError(
                            "split-coverage EOD price is nonpositive"
                        )
                    key = (instrument_id, session)
                    if key in active or key in quarantined or key in impacts:
                        observed_current.add(key)
                    prior = previous.get(instrument_id)
                    if prior is not None and prior[0] == expected_prior[session]:
                        adjacent_count += 1
                        ratio = _ratio(raw_open, prior[1])
                        known = (
                            key in active or key in quarantined or key in impacts
                        )
                        if known:
                            comparable_known.add(key)
                            flags.append(
                                _known_event_flag(
                                    instrument_id=instrument_id,
                                    prior_session=prior[0],
                                    session=session,
                                    ratio=ratio,
                                    active=active.get(key, ()),
                                    quarantined=quarantined.get(key, ()),
                                    impact=impacts.get(key),
                                )
                            )
                        elif _severe(ratio):
                            flags.append(
                                CanonicalSplitCoverageFlag(
                                    instrument_id=str(instrument_id),
                                    prior_session=prior[0].isoformat(),
                                    session_date=session.isoformat(),
                                    classification=(
                                        "unexplained_price_discontinuity"
                                    ),
                                    raw_open_to_prior_close_ratio=str(ratio),
                                    expected_split_price_multiplier=None,
                                    residual_ratio=None,
                                    source_action_set_fingerprint=None,
                                    quality_flags=(
                                        "price_discontinuity_is_review_flag_only",
                                        "no_same_date_canonical_split_evidence",
                                        "absent_row_neutrality_unauthorized",
                                    ),
                                )
                            )
                    previous[instrument_id] = (session, raw_close)
        except CanonicalSplitCoverageDiagnosticError:
            raise
        except (
            AttributeError,
            pa.ArrowException,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage EOD scan failed"
            ) from exc
        if len(seen) != artifact.record_count:
            raise CanonicalSplitCoverageDiagnosticError(
                "split-coverage EOD artifact count differs"
            )
    if observed_records != evidence.record_count:
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage EOD family count differs"
        )
    return _ScanResult(
        adjacent_transition_count=adjacent_count,
        observed_current_keys=frozenset(observed_current),
        comparable_known_keys=frozenset(comparable_known),
        flags=tuple(flags),
    )


def _known_event_flag(
    *,
    instrument_id: UUID,
    prior_session: date,
    session: date,
    ratio: Decimal,
    active: tuple[CanonicalSplitActionV1, ...],
    quarantined: tuple[CanonicalSplitActionV1, ...],
    impact: CanonicalSplitActionQuarantineImpactV1 | None,
) -> CanonicalSplitCoverageFlag:
    evidence = _event_evidence(active, quarantined, impact)
    evidence_fingerprint = _fingerprint(evidence)
    if quarantined:
        return CanonicalSplitCoverageFlag(
            instrument_id=str(instrument_id),
            prior_session=prior_session.isoformat(),
            session_date=session.isoformat(),
            classification="canonical_action_quarantined",
            raw_open_to_prior_close_ratio=str(ratio),
            expected_split_price_multiplier=None,
            residual_ratio=None,
            source_action_set_fingerprint=evidence_fingerprint,
            quality_flags=(
                "canonical_action_quarantined",
                "price_fit_cannot_promote_action",
                "absent_row_neutrality_unauthorized",
            ),
        )
    if impact is not None:
        return CanonicalSplitCoverageFlag(
            instrument_id=str(instrument_id),
            prior_session=prior_session.isoformat(),
            session_date=session.isoformat(),
            classification="unresolved_impact_quarantined",
            raw_open_to_prior_close_ratio=str(ratio),
            expected_split_price_multiplier=None,
            residual_ratio=None,
            source_action_set_fingerprint=evidence_fingerprint,
            quality_flags=tuple(
                sorted(
                    {
                        *impact.quality_flags,
                        "unresolved_split_impact_quarantined",
                        "price_fit_cannot_promote_action",
                    }
                )
            ),
        )
    factors = calculate_composed_split_adjustment_multipliers(
        (item.split_ratio_from, item.split_ratio_to) for item in active
    )
    expected = factors.price_multiplier_to_post_event_basis
    residual = _ratio(ratio, expected)
    extreme = _severe(residual)
    return CanonicalSplitCoverageFlag(
        instrument_id=str(instrument_id),
        prior_session=prior_session.isoformat(),
        session_date=session.isoformat(),
        classification=(
            "active_split_residual_extreme"
            if extreme
            else "active_split_residual_bounded"
        ),
        raw_open_to_prior_close_ratio=str(ratio),
        expected_split_price_multiplier=str(expected),
        residual_ratio=str(residual),
        source_action_set_fingerprint=evidence_fingerprint,
        quality_flags=(
            "canonical_active_split_cross_checked",
            (
                "split_adjusted_open_residual_extreme"
                if extreme
                else "split_adjusted_open_residual_bounded"
            ),
            "price_fit_is_diagnostic_only",
        ),
    )


def _missing_known_event_flags(
    *,
    known_keys: frozenset[tuple[UUID, date]],
    observed_current_keys: frozenset[tuple[UUID, date]],
    comparable_known_keys: frozenset[tuple[UUID, date]],
    active: dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
    quarantined: dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
    impacts: dict[tuple[UUID, date], CanonicalSplitActionQuarantineImpactV1],
) -> tuple[CanonicalSplitCoverageFlag, ...]:
    flags = []
    for instrument_id, session in sorted(
        known_keys - comparable_known_keys,
        key=lambda item: (item[1], str(item[0])),
    ):
        key = (instrument_id, session)
        evidence = _event_evidence(
            active.get(key, ()),
            quarantined.get(key, ()),
            impacts.get(key),
        )
        current_missing = key not in observed_current_keys
        flags.append(
            CanonicalSplitCoverageFlag(
                instrument_id=str(instrument_id),
                prior_session=None,
                session_date=session.isoformat(),
                classification=(
                    "known_event_current_bar_missing"
                    if current_missing
                    else "known_event_adjacent_transition_missing"
                ),
                raw_open_to_prior_close_ratio=None,
                expected_split_price_multiplier=None,
                residual_ratio=None,
                source_action_set_fingerprint=_fingerprint(evidence),
                quality_flags=(
                    (
                        "current_session_eod_bar_missing"
                        if current_missing
                        else "adjacent_prior_eod_bar_missing"
                    ),
                    "price_continuity_untested",
                ),
            )
        )
    return tuple(flags)


def _action_groups(
    actions: tuple[CanonicalSplitActionV1, ...],
) -> tuple[
    dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
    dict[tuple[UUID, date], tuple[CanonicalSplitActionV1, ...]],
]:
    active: dict[tuple[UUID, date], list[CanonicalSplitActionV1]] = defaultdict(list)
    quarantined: dict[
        tuple[UUID, date], list[CanonicalSplitActionV1]
    ] = defaultdict(list)
    for item in actions:
        key = (item.instrument_id, item.effective_date)
        target = (
            active
            if item.record_status is CorporateActionRecordStatus.ACTIVE
            else quarantined
        )
        target[key].append(item)
    return (
        {
            key: tuple(sorted(value, key=_action_sort_key))
            for key, value in active.items()
        },
        {
            key: tuple(sorted(value, key=_action_sort_key))
            for key, value in quarantined.items()
        },
    )


def _impact_groups(
    impacts: tuple[CanonicalSplitActionQuarantineImpactV1, ...],
) -> dict[tuple[UUID, date], CanonicalSplitActionQuarantineImpactV1]:
    grouped: dict[tuple[UUID, date], CanonicalSplitActionQuarantineImpactV1] = {}
    for impact in impacts:
        for effective_date in impact.effective_dates:
            key = (impact.instrument_id, effective_date)
            if key in grouped:
                raise CanonicalSplitCoverageDiagnosticError(
                    "split-coverage unresolved impact identity is duplicated"
                )
            grouped[key] = impact
    return grouped


def _event_evidence(
    active: tuple[CanonicalSplitActionV1, ...],
    quarantined: tuple[CanonicalSplitActionV1, ...],
    impact: CanonicalSplitActionQuarantineImpactV1 | None,
) -> tuple[dict[str, object], ...]:
    values = [
        {
            "kind": "canonical_action",
            "corporate_action_id": str(item.corporate_action_id),
            "source_action_set_fingerprint": item.source_action_set_fingerprint,
            "record_status": item.record_status.value,
        }
        for item in (*active, *quarantined)
    ]
    if impact is not None:
        values.append(
            {
                "kind": "unresolved_impact",
                "source_action_set_fingerprint": (
                    impact.source_action_set_fingerprint
                ),
                "source_action_ids": impact.source_action_ids,
            }
        )
    return tuple(values)


def _validate_source_scope(
    *,
    action_publication: CanonicalSplitActionPublicationV1,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    calculated_at: datetime,
) -> None:
    if (
        evidence.family is not HistoricalDatasetFamily.EOD_PRICE_BAR
        or not evidence.sessions
        or evidence.sessions[0] != action_publication.start_date
        or evidence.sessions[-1] != action_publication.end_date
        or action_publication.source_coverage_status
        != "bounded_query_snapshot_only"
        or action_publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or action_publication.full_corporate_action_coverage_authorized
        is not False
        or calculated_at < max(action_publication.created_at, evidence.created_at)
    ):
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage source scope differs"
        )


def _validate_eod_schema(schema: pa.Schema) -> None:
    if (
        schema.names != ["instrument_id", "session_date", "open", "close"]
        or not pa.types.is_string(schema.field("instrument_id").type)
        or not pa.types.is_date32(schema.field("session_date").type)
        or not pa.types.is_decimal(schema.field("open").type)
        or not pa.types.is_decimal(schema.field("close").type)
    ):
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage EOD projection schema differs"
        )


def _action_sort_key(item: CanonicalSplitActionV1) -> tuple[object, ...]:
    return (
        item.effective_date,
        item.source,
        item.source_action_id,
        item.source_revision,
    )


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if numerator <= 0 or denominator <= 0:
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage ratio requires positive prices"
        )
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        return (numerator / denominator).quantize(RATIO_QUANTUM)


def _severe(ratio: Decimal) -> bool:
    return ratio <= SEVERE_LOWER_RATIO or ratio >= SEVERE_UPPER_RATIO


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitCoverageDiagnosticError(
            "split-coverage data root is not approved"
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
        raise CanonicalSplitCoverageDiagnosticError(
            "network is prohibited during split-coverage diagnosis"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
