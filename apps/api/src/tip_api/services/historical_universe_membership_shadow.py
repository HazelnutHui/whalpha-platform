"""Offline historical Universe reconstruction from custody-validated source facts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping
from uuid import UUID

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    EodHistoryWindowDescriptorV1,
    EodSessionIntegrityV1,
    FullBaseDecisionV1,
    FullBaseDisposition,
    TrailingLiquidityEligibilityStatus,
    TrailingLiquidityResultV1,
)
from tip_api.contracts.security_classification.v1 import (
    ProviderInstrumentSecurityEvidenceV1,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotReadResult
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
    identity_content_fingerprint,
    instrument_content_fingerprint,
    resolver_content_fingerprint,
)
from tip_api.persistence.parquet.security_evidence import (
    read_completed_security_evidence_snapshot,
)
from tip_api.persistence.security_evidence import CompletedSecurityEvidenceSnapshot
from tip_api.providers.massive.same_day_catchup import (
    ValidatedIdentityReferencePackage,
    read_identity_reference_package,
)
from tip_api.providers.massive.instrument_master_snapshot import (
    ReferenceSnapshotBuildResult,
    build_snapshot_from_payloads,
)
from tip_api.providers.massive.security_type_evidence import (
    EvidenceBuildResult,
    build_identity_indexes,
    build_instrument_evidence,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.eod_history import (
    CANONICAL_DECIMAL_SCALE,
    HISTORY_SESSION_COUNT,
    MATERIAL_QUALITY_FLAGS,
    PREVIOUS_CLOSE_THRESHOLD,
    audit_trailing_liquidity,
    describe_eod_history_window,
    fixed_scale_coefficient,
)
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar
from tip_api.services.security_classification import SUPPORTED_EXCHANGES
from tip_api.services.universe_membership_reconstruction import (
    POLICY_TO_UNIVERSE,
    UniverseMembershipReconstruction,
    reconstruct_daily_universe_membership,
)

HISTORICAL_METHODOLOGY_VERSION = "provider-form-complete-base-point-in-time-v2"
MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS = 5
_LOCALIZABLE_EVIDENCE_FAILURES = frozenset(
    {
        "ambiguous_mapping_nonzero",
        "canonical_business_key_conflict_nonzero",
        "stable_identifier_collision_nonzero",
    }
)


class HistoricalUniverseMembershipShadowError(RuntimeError):
    """Fail-closed error at the offline reconstruction boundary."""


class HistoricalUniverseMembershipIdentityMismatchError(
    HistoricalUniverseMembershipShadowError
):
    """The retained package is valid but not equal to accepted same-day Identity."""


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipEodPanel:
    """Bounded formal EOD reads shared across adjacent analysis sessions."""

    data_root: Path
    analysis_sessions: tuple[date, ...]
    canonical_session_index: tuple[date, ...]
    session_reads: tuple[EodHistorySessionRead, ...]


@dataclass(frozen=True, slots=True)
class HistoricalIdentityPackageEquivalence:
    """Formal package rebuild compared with one accepted same-day Identity."""

    identity: InstrumentMasterSnapshotReadResult
    package: ValidatedIdentityReferencePackage
    rebuilt_identity: ReferenceSnapshotBuildResult
    rebuilt_instrument_fingerprint: str
    rebuilt_identity_fingerprint: str
    rebuilt_resolver_fingerprint: str
    instrument_match: bool
    identity_match: bool
    resolver_match: bool

    @property
    def exact_match(self) -> bool:
        return self.instrument_match and self.identity_match and self.resolver_match


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipShadow:
    reconstruction: UniverseMembershipReconstruction
    source_decisions: tuple[FullBaseDecisionV1, ...]
    history_descriptor_fingerprint: str
    identity_snapshot_fingerprint: str
    package_manifest_fingerprint: str
    package_content_fingerprint: str
    catalog_snapshot_fingerprint: str
    derived_security_evidence_fingerprint: str
    eod_source_fingerprint: str
    source_data_cutoff: datetime
    raw_provider_record_count: int
    canonical_evidence_count: int
    source_quarantined_instrument_count: int
    evidence_quality_gate_failures: tuple[str, ...]


def inspect_historical_identity_package_equivalence(
    *,
    data_root: Path,
    package_path: Path,
    session_date: date,
    identity: InstrumentMasterSnapshotReadResult | None = None,
) -> HistoricalIdentityPackageEquivalence:
    """Formally rebuild one retained package and compare all Identity families."""

    root = data_root.resolve(strict=True)
    accepted = identity or ParquetInstrumentMasterSnapshotRepository(
        root
    ).inspect_snapshot(session_date)
    if accepted.as_of_date != session_date:
        raise HistoricalUniverseMembershipShadowError(
            "accepted Identity snapshot session mismatch"
        )
    package = read_identity_reference_package(
        package_path=package_path,
        expected_session=session_date,
    )
    rebuilt = build_snapshot_from_payloads(
        payloads=_flatten_reference_pages(package.pages),
        as_of_date=session_date,
        ingested_at=package.manifest.fetched_at,
        request_count=package.manifest.request_count,
        pagination_complete=package.manifest.pagination_complete,
    )
    rebuilt_instrument_fingerprint = instrument_content_fingerprint(
        rebuilt.instruments
    )
    rebuilt_identity_fingerprint = identity_content_fingerprint(
        rebuilt.identities
    )
    rebuilt_resolver_fingerprint = resolver_content_fingerprint(
        rebuilt.resolvers
    )
    return HistoricalIdentityPackageEquivalence(
        identity=accepted,
        package=package,
        rebuilt_identity=rebuilt,
        rebuilt_instrument_fingerprint=rebuilt_instrument_fingerprint,
        rebuilt_identity_fingerprint=rebuilt_identity_fingerprint,
        rebuilt_resolver_fingerprint=rebuilt_resolver_fingerprint,
        instrument_match=(
            rebuilt_instrument_fingerprint == accepted.instrument_content_sha256
        ),
        identity_match=(
            rebuilt_identity_fingerprint == accepted.identity_content_sha256
        ),
        resolver_match=(
            rebuilt_resolver_fingerprint == accepted.resolver_content_sha256
        ),
    )


def prepare_historical_universe_membership_eod_panel(
    *,
    data_root: Path,
    analysis_sessions: tuple[date, ...],
    calendar: MarketSessionCalendar | None = None,
) -> HistoricalUniverseMembershipEodPanel:
    """Read every EOD partition needed by a bounded adjacent batch once."""

    root = data_root.resolve(strict=True)
    if (
        not analysis_sessions
        or len(analysis_sessions) != len(set(analysis_sessions))
        or len(analysis_sessions) > MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS
    ):
        raise HistoricalUniverseMembershipShadowError(
            "shared EOD panel requires one to five unique analysis sessions"
        )
    ordered_sessions = tuple(sorted(analysis_sessions))
    session_calendar = calendar or ExchangeCalendar()
    if any(
        session_calendar.next_session(left) != right
        for left, right in zip(ordered_sessions, ordered_sessions[1:])
    ):
        raise HistoricalUniverseMembershipShadowError(
            "shared EOD panel analysis sessions must be adjacent XNYS sessions"
        )
    repository = CanonicalEodReadRepository(root)
    canonical_session_index = repository.list_session_index()
    canonical_session_set = set(canonical_session_index)
    missing_analysis = set(ordered_sessions) - canonical_session_set
    if missing_analysis:
        raise HistoricalUniverseMembershipShadowError(
            "analysis session is absent from the canonical EOD completion index"
        )
    required_sessions = set(ordered_sessions)
    for session in ordered_sessions:
        required_sessions.update(
            item
            for item in session_calendar.sessions_before(session, HISTORY_SESSION_COUNT)
            if item in canonical_session_set
        )
    reads = repository.read_history_sessions(tuple(sorted(required_sessions)))
    if tuple(item.integrity.session_date for item in reads) != tuple(
        sorted(required_sessions)
    ):
        raise HistoricalUniverseMembershipShadowError(
            "formal shared EOD reads do not match the required session set"
        )
    return HistoricalUniverseMembershipEodPanel(
        data_root=root,
        analysis_sessions=ordered_sessions,
        canonical_session_index=canonical_session_index,
        session_reads=reads,
    )


def build_historical_universe_membership_shadow(
    *,
    data_root: Path,
    package_path: Path,
    session_date: date,
    catalog_as_of_date: date,
    evaluated_at: datetime,
    calendar: MarketSessionCalendar | None = None,
    eod_panel: HistoricalUniverseMembershipEodPanel | None = None,
    security_snapshot: CompletedSecurityEvidenceSnapshot | None = None,
) -> HistoricalUniverseMembershipShadow:
    """Build one complete, tmp-ready daily ledger without network or data writes."""

    evaluated_at = normalize_utc_datetime(evaluated_at)
    calendar = calendar or ExchangeCalendar()
    data_root = data_root.resolve(strict=True)
    eod_repository = CanonicalEodReadRepository(data_root)

    equivalence = inspect_historical_identity_package_equivalence(
        data_root=data_root,
        package_path=package_path,
        session_date=session_date,
    )
    if not equivalence.exact_match:
        raise HistoricalUniverseMembershipIdentityMismatchError(
            "Identity package does not exactly reconstruct the accepted snapshot"
        )
    identity = equivalence.identity
    package = equivalence.package
    rebuilt_identity = equivalence.rebuilt_identity
    payloads = _flatten_reference_pages(package.pages)
    indexes = build_identity_indexes(
        identities=rebuilt_identity.identities,
        resolvers=rebuilt_identity.resolvers,
    )
    evaluated_base_ids = frozenset(
        item.instrument_id for item in rebuilt_identity.instruments
    )
    if (
        len(indexes.ticker_resolver) != identity.resolver_count
        or len(evaluated_base_ids) != identity.instrument_count
        or frozenset(indexes.ticker_resolver.values()) != evaluated_base_ids
    ):
        raise HistoricalUniverseMembershipShadowError(
            "Identity resolver does not exactly cover the canonical Instrument Master"
        )
    if security_snapshot is None:
        security_snapshot = read_completed_security_evidence_snapshot(
            data_root,
            as_of_date=catalog_as_of_date,
        )
    elif security_snapshot.manifest.as_of_date != catalog_as_of_date:
        raise HistoricalUniverseMembershipShadowError(
            "shared security catalog as-of date mismatch"
        )
    evidence_result = build_instrument_evidence(
        catalog=security_snapshot.catalog,
        payloads=payloads,
        indexes=indexes,
        as_of_date=session_date,
        observed_at=package.manifest.fetched_at,
        request_count=package.manifest.request_count + 1,
        all_tickers_request_count=package.manifest.request_count,
    )
    blocking_failures = set(evidence_result.quality_gate_failures) - set(
        _LOCALIZABLE_EVIDENCE_FAILURES
    )
    if blocking_failures:
        raise HistoricalUniverseMembershipShadowError(
            "provider security evidence has non-localizable quality failures: "
            + ",".join(sorted(blocking_failures))
        )

    if eod_panel is None:
        eod_panel = prepare_historical_universe_membership_eod_panel(
            data_root=data_root,
            analysis_sessions=(session_date,),
            calendar=calendar,
        )
    descriptor, history_integrity, history_reads, current_read = _panel_window(
        panel=eod_panel,
        data_root=data_root,
        session_date=session_date,
        calendar=calendar,
    )
    current_integrity = current_read.integrity
    if (
        current_integrity.identity_snapshot_date != session_date
        or current_integrity.identity_snapshot_fingerprint
        != identity.snapshot_content_sha256
    ):
        raise HistoricalUniverseMembershipShadowError(
            "current EOD is not bound to the exact same-session Identity snapshot"
        )
    current_bars = current_read.bars
    previous_bars = next(
        (
            item.bars
            for item in history_reads
            if item.integrity.session_date == descriptor.previous_session
        ),
        (),
    )
    liquidity_audit = audit_trailing_liquidity(
        descriptor=descriptor,
        repository=eod_repository,
        instrument_ids=evaluated_base_ids,
        session_reads=history_reads,
    )
    source_decisions = build_complete_point_in_time_source_decisions(
        session_date=session_date,
        evaluated_base_ids=evaluated_base_ids,
        evidence=evidence_result.evidence,
        source_quarantines=dict(evidence_result.quarantined_instrument_reasons),
        current_bars=current_bars,
        previous_bars=previous_bars,
        trailing_results=liquidity_audit.results,
        calculated_at=evaluated_at,
    )

    evidence_fingerprint = _derived_evidence_fingerprint(evidence_result)
    eod_source_fingerprint = _eod_source_fingerprint(
        current=current_integrity,
        history=history_integrity,
    )
    source_fingerprints = tuple(
        sorted(
            {
                package.package_manifest_sha256,
                package.manifest.package_content_sha256,
                identity.snapshot_content_sha256,
                security_snapshot.manifest.catalog_content_sha256,
                security_snapshot.manifest.catalog_parquet_sha256,
                descriptor.fingerprint,
                evidence_fingerprint,
                eod_source_fingerprint,
            }
        )
    )
    eod_available_at = tuple(
        item.available_at for item in (current_read,) + history_reads
    )
    if any(item is None for item in eod_available_at):
        raise HistoricalUniverseMembershipShadowError(
            "canonical EOD source availability time is unavailable"
        )
    source_data_cutoff = max(
        normalize_utc_datetime(package.manifest.fetched_at),
        normalize_utc_datetime(identity.created_at),
        normalize_utc_datetime(security_snapshot.manifest.created_at),
        *(item for item in eod_available_at if item is not None),
    )
    if source_data_cutoff > evaluated_at:
        raise HistoricalUniverseMembershipShadowError(
            "evaluated_at precedes the latest validated source availability"
        )

    reconstruction = reconstruct_daily_universe_membership(
        session_date=session_date,
        source_decisions=source_decisions,
        evaluated_base_ids=evaluated_base_ids,
        source_policy_to_universe=POLICY_TO_UNIVERSE,
        source_fingerprints=source_fingerprints,
        source_data_cutoff=source_data_cutoff,
        evaluated_at=evaluated_at,
        methodology_version=HISTORICAL_METHODOLOGY_VERSION,
    )
    return HistoricalUniverseMembershipShadow(
        reconstruction=reconstruction,
        source_decisions=source_decisions,
        history_descriptor_fingerprint=descriptor.fingerprint,
        identity_snapshot_fingerprint=identity.snapshot_content_sha256,
        package_manifest_fingerprint=package.package_manifest_sha256,
        package_content_fingerprint=package.manifest.package_content_sha256,
        catalog_snapshot_fingerprint=security_snapshot.manifest.logical_content_sha256,
        derived_security_evidence_fingerprint=evidence_fingerprint,
        eod_source_fingerprint=eod_source_fingerprint,
        source_data_cutoff=source_data_cutoff,
        raw_provider_record_count=evidence_result.raw_record_count,
        canonical_evidence_count=len(evidence_result.evidence),
        source_quarantined_instrument_count=len(
            evidence_result.quarantined_instrument_reasons
        ),
        evidence_quality_gate_failures=evidence_result.quality_gate_failures,
    )


def _panel_window(
    *,
    panel: HistoricalUniverseMembershipEodPanel,
    data_root: Path,
    session_date: date,
    calendar: MarketSessionCalendar,
) -> tuple[
    EodHistoryWindowDescriptorV1,
    tuple[EodSessionIntegrityV1, ...],
    tuple[EodHistorySessionRead, ...],
    EodHistorySessionRead,
]:
    if panel.data_root != data_root or session_date not in panel.analysis_sessions:
        raise HistoricalUniverseMembershipShadowError(
            "shared EOD panel is outside the requested source/session boundary"
        )
    read_by_session = {
        item.integrity.session_date: item for item in panel.session_reads
    }
    if len(read_by_session) != len(panel.session_reads):
        raise HistoricalUniverseMembershipShadowError(
            "shared EOD panel contains duplicate sessions"
        )
    current_read = read_by_session.get(session_date)
    if current_read is None:
        raise HistoricalUniverseMembershipShadowError(
            "shared EOD panel is missing the analysis session"
        )
    expected = calendar.sessions_before(session_date, HISTORY_SESSION_COUNT)
    canonical_sessions = set(panel.canonical_session_index)
    completed_sessions = tuple(item for item in expected if item in canonical_sessions)
    missing_sessions = tuple(item for item in expected if item not in canonical_sessions)
    if any(item not in read_by_session for item in completed_sessions):
        raise HistoricalUniverseMembershipShadowError(
            "completion-index history is absent from the formal shared EOD panel"
        )
    history_reads = tuple(read_by_session[item] for item in completed_sessions)
    descriptor, history_integrity = describe_eod_history_window(
        analysis_session=session_date,
        calendar=calendar,
        completed_integrity=tuple(item.integrity for item in history_reads),
        missing_sessions=missing_sessions,
    )
    return descriptor, history_integrity, history_reads, current_read


def build_complete_point_in_time_source_decisions(
    *,
    session_date: date,
    evaluated_base_ids: frozenset[UUID],
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    source_quarantines: Mapping[UUID, tuple[str, ...]],
    current_bars: tuple[EodMarketBarReadModel, ...],
    previous_bars: tuple[EodMarketBarReadModel, ...],
    trailing_results: tuple[TrailingLiquidityResultV1, ...],
    calculated_at: datetime,
) -> tuple[FullBaseDecisionV1, ...]:
    """Create both policy decisions for every exact same-day Identity ID."""

    if not evaluated_base_ids:
        raise ValueError("evaluated base must not be empty")
    calculated_at = normalize_utc_datetime(calculated_at)
    evidence_by_id: dict[UUID, list[ProviderInstrumentSecurityEvidenceV1]] = (
        defaultdict(list)
    )
    for item in evidence:
        if item.instrument_id not in evaluated_base_ids:
            raise ValueError("provider evidence is outside the evaluated Identity base")
        evidence_by_id[item.instrument_id].append(item)
    analysis_sessions = {item.analysis_session for item in trailing_results}
    previous_sessions = {item.window_end for item in trailing_results}
    if analysis_sessions != {session_date} or len(previous_sessions) != 1:
        raise ValueError("trailing results do not share the requested session boundary")
    current_by_id = _unique_bars(current_bars, session_date, "current")
    previous_by_id = _unique_bars(
        previous_bars,
        next(iter(previous_sessions)),
        "previous",
    )
    trailing_by_id = {item.instrument_id: item for item in trailing_results}
    if len(trailing_by_id) != len(trailing_results):
        raise ValueError("trailing results contain duplicate stable IDs")
    if set(trailing_by_id) != set(evaluated_base_ids):
        raise ValueError("trailing results do not exactly cover the evaluated Identity base")
    unknown_quarantine_ids = set(source_quarantines) - set(evaluated_base_ids)
    if unknown_quarantine_ids:
        raise ValueError("source quarantine references an ID outside the evaluated base")

    records = []
    for instrument_id in sorted(evaluated_base_ids, key=str):
        selected, source_reasons = _select_security_evidence(
            session_date=session_date,
            values=tuple(evidence_by_id.get(instrument_id, ())),
            source_quarantine=source_quarantines.get(instrument_id, ()),
        )
        for policy_id in (FULL_BASE_A_ID, FULL_BASE_B_ID):
            records.append(
                _source_decision(
                    session_date=session_date,
                    policy_id=policy_id,
                    instrument_id=instrument_id,
                    source=selected,
                    source_reasons=source_reasons,
                    current=current_by_id.get(instrument_id),
                    previous=previous_by_id.get(instrument_id),
                    trailing=trailing_by_id[instrument_id],
                    calculated_at=calculated_at,
                )
            )
    output = tuple(records)
    _validate_policy_relationship(output)
    return output


def _validate_policy_relationship(
    records: tuple[FullBaseDecisionV1, ...],
) -> None:
    included = {
        policy_id: {
            item.instrument_id
            for item in records
            if item.policy_id == policy_id and item.included
        }
        for policy_id in (FULL_BASE_A_ID, FULL_BASE_B_ID)
    }
    if not included[FULL_BASE_A_ID] <= included[FULL_BASE_B_ID]:
        raise ValueError("historical Primary membership is not a subset of Secondary")
    type_by_id = {
        item.instrument_id: item.provider_type_code
        for item in records
        if item.policy_id == FULL_BASE_B_ID
    }
    if any(
        type_by_id[instrument_id] != "ADRC"
        for instrument_id in included[FULL_BASE_B_ID] - included[FULL_BASE_A_ID]
    ):
        raise ValueError("historical Secondary minus Primary contains a non-ADRC ID")


def _select_security_evidence(
    *,
    session_date: date,
    values: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    source_quarantine: tuple[str, ...],
) -> tuple[ProviderInstrumentSecurityEvidenceV1 | None, tuple[str, ...]]:
    reasons = set(source_quarantine)
    if not values:
        reasons.add("same_day_provider_security_evidence_missing")
        return None, tuple(sorted(reasons))
    if any(item.as_of_date != session_date for item in values):
        reasons.add("provider_security_evidence_date_mismatch")
    signatures = {
        (
            item.provider_type_code,
            item.primary_exchange,
            item.security_form_evidence,
            item.classification_status,
        )
        for item in values
    }
    if len(signatures) != 1:
        reasons.add("conflicting_provider_security_evidence_for_instrument")
    if reasons:
        return None, tuple(sorted(reasons))
    return min(
        values,
        key=lambda item: (item.provider_ticker, item.provider_observation_ids),
    ), ()


def _source_decision(
    *,
    session_date: date,
    policy_id: str,
    instrument_id: UUID,
    source: ProviderInstrumentSecurityEvidenceV1 | None,
    source_reasons: tuple[str, ...],
    current: EodMarketBarReadModel | None,
    previous: EodMarketBarReadModel | None,
    trailing: TrailingLiquidityResultV1,
    calculated_at: datetime,
) -> FullBaseDecisionV1:
    provider_type = source.provider_type_code if source is not None else "UNKNOWN"
    if source is None:
        disposition = FullBaseDisposition.INVALID_INPUT
        reasons = set(source_reasons)
        stage = "provider_security_evidence"
    elif provider_type not in {"CS", "ADRC"}:
        disposition = FullBaseDisposition.TARGET_SECURITY_FORM
        reasons = {"provider_security_form_not_eligible_for_policy"}
        stage = "target_security_form"
    elif policy_id == FULL_BASE_A_ID and provider_type == "ADRC":
        disposition = FullBaseDisposition.TARGET_SECURITY_FORM
        reasons = {"provider_adrc_not_eligible_for_primary"}
        stage = "target_security_form"
    elif source.primary_exchange not in SUPPORTED_EXCHANGES:
        disposition = FullBaseDisposition.UNSUPPORTED_EXCHANGE
        reasons = {"unsupported_exchange"}
        stage = "supported_exchange"
    elif current is None:
        disposition = FullBaseDisposition.MISSING_CURRENT_BAR
        reasons = {"missing_current_bar"}
        stage = "comparable_bars"
    elif previous is None:
        disposition = FullBaseDisposition.MISSING_PREVIOUS_BAR
        reasons = {"missing_previous_bar"}
        stage = "comparable_bars"
    elif current.primary_exchange != source.primary_exchange:
        disposition = FullBaseDisposition.INVALID_INPUT
        reasons = {"same_day_exchange_evidence_conflict"}
        stage = "input_quality"
    elif MATERIAL_QUALITY_FLAGS.intersection(
        set(current.quality_flags) | set(previous.quality_flags)
    ):
        disposition = FullBaseDisposition.INVALID_INPUT
        reasons = {"material_data_quality_flag"}
        stage = "input_quality"
    elif _is_material_return_outlier(current, previous):
        disposition = FullBaseDisposition.OUTLIER_QUARANTINE
        reasons = {"material_return_outlier_review"}
        stage = "outlier_quarantine"
    elif previous.close < PREVIOUS_CLOSE_THRESHOLD:
        disposition = FullBaseDisposition.BELOW_PREVIOUS_CLOSE
        reasons = {"previous_close_below_5"}
        stage = "previous_close"
    else:
        disposition, stage = _trailing_disposition(trailing.eligibility_status)
        reasons = set(trailing.reason_codes)
        if disposition is FullBaseDisposition.INCLUDED:
            reasons.add("full_base_trailing_liquidity_passed")
            reasons.add("provisional_provider_security_form_policy")
    if not reasons:
        reasons.add("unclassified_membership_decision")
    return FullBaseDecisionV1(
        analysis_session=session_date,
        membership_evidence_as_of_date=session_date,
        policy_id=policy_id,
        instrument_id=instrument_id,
        provider_type_code=provider_type,
        disposition=disposition,
        included=disposition is FullBaseDisposition.INCLUDED,
        stage_id=stage,
        reason_codes=tuple(sorted(reasons)),
        reviewed_override_decision=None,
        calculated_at=calculated_at,
    )


def _trailing_disposition(
    status: TrailingLiquidityEligibilityStatus,
) -> tuple[FullBaseDisposition, str]:
    return {
        TrailingLiquidityEligibilityStatus.PASSED: (
            FullBaseDisposition.INCLUDED,
            "final_membership",
        ),
        TrailingLiquidityEligibilityStatus.BELOW_PRICE_THRESHOLD: (
            FullBaseDisposition.BELOW_PREVIOUS_CLOSE,
            "previous_close",
        ),
        TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD: (
            FullBaseDisposition.BELOW_TRAILING_LIQUIDITY,
            "trailing_liquidity",
        ),
        TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY: (
            FullBaseDisposition.INSUFFICIENT_HISTORY,
            "history_completeness",
        ),
        TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR: (
            FullBaseDisposition.MISSING_PREVIOUS_BAR,
            "comparable_bars",
        ),
        TrailingLiquidityEligibilityStatus.IDENTITY_REFERENCE_FAILURE: (
            FullBaseDisposition.INVALID_INPUT,
            "input_quality",
        ),
        TrailingLiquidityEligibilityStatus.DATA_QUALITY_FAILURE: (
            FullBaseDisposition.INVALID_INPUT,
            "input_quality",
        ),
    }[status]


def _is_material_return_outlier(
    current: EodMarketBarReadModel,
    previous: EodMarketBarReadModel,
) -> bool:
    current_close = fixed_scale_coefficient(
        current.close,
        scale=CANONICAL_DECIMAL_SCALE,
    )
    previous_close = fixed_scale_coefficient(
        previous.close,
        scale=CANONICAL_DECIMAL_SCALE,
    )
    return current_close >= 2 * previous_close or 2 * current_close <= previous_close


def _unique_bars(
    bars: tuple[EodMarketBarReadModel, ...],
    expected_session: date | None,
    label: str,
) -> dict[UUID, EodMarketBarReadModel]:
    result: dict[UUID, EodMarketBarReadModel] = {}
    sessions = {item.session_date for item in bars}
    if expected_session is not None and sessions - {expected_session}:
        raise ValueError(f"{label} bars contain an unexpected session")
    if expected_session is None and len(sessions) > 1:
        raise ValueError(f"{label} bars contain multiple sessions")
    for item in bars:
        if item.instrument_id in result:
            raise ValueError(f"{label} bars contain duplicate stable IDs")
        result[item.instrument_id] = item
    return result


def _flatten_reference_pages(
    pages: tuple[Mapping[str, object], ...],
) -> tuple[Mapping[str, object], ...]:
    payloads = []
    for page in pages:
        results = page.get("results")
        if not isinstance(results, list) or not all(
            isinstance(item, Mapping) for item in results
        ):
            raise HistoricalUniverseMembershipShadowError(
                "validated reference package contains malformed results"
            )
        payloads.extend(results)
    return tuple(payloads)


def _derived_evidence_fingerprint(result: EvidenceBuildResult) -> str:
    payload = {
        "observations": [
            item.model_dump(mode="json") for item in result.observations
        ],
        "evidence": [item.model_dump(mode="json") for item in result.evidence],
        "quarantines": [
            [str(instrument_id), list(reasons)]
            for instrument_id, reasons in result.quarantined_instrument_reasons
        ],
        "quality_gate_failures": list(result.quality_gate_failures),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _eod_source_fingerprint(
    *,
    current: EodSessionIntegrityV1,
    history: tuple[EodSessionIntegrityV1, ...],
) -> str:
    payload = {
        "current": current.model_dump(mode="json"),
        "history": [item.model_dump(mode="json") for item in history],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
