"""Offline audit for provider-classified common-share shadow candidates.

This module deliberately classifies security form only.  It does not infer issuer
domicile, operating-company status, or production-universe eligibility.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from tip_api.contracts.security_classification.v1 import (
    ProviderInstrumentSecurityEvidenceV1,
    ProviderObservationStatus,
    ProviderSecurityObservationV1,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.security_classification import (
    MINIMUM_PREVIOUS_CLOSE,
    MINIMUM_PREVIOUS_DOLLAR_VOLUME,
    SUPPORTED_EXCHANGES,
)

CANDIDATE_A_ID = "provider_classified_common_shares_v1"
CANDIDATE_A_NAME = "Provider-Classified Common Shares (Provisional)"
CANDIDATE_A_NAME_ZH = "供应商分类普通股（暂定）"
CANDIDATE_B_ID = "provider_classified_common_shares_plus_adrs_shadow_v1"
CANDIDATE_B_NAME = "Provider-Classified Common Shares + ADRs (Shadow)"
CANDIDATE_B_NAME_ZH = "供应商分类普通股及ADR（影子比较）"
LIQUIDITY_RULE = "one_session_liquidity_provisional"


@dataclass(frozen=True, slots=True)
class ClassificationDecision:
    instrument_id: UUID
    provider_type_code: str | None
    bucket: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class CandidateFunnel:
    provider_type_classified: int
    both_sessions_available: int
    supported_exchange: int
    previous_close_at_least_5: int
    previous_dollar_volume_at_least_20m: int
    final_shadow_candidate: int
    exclusion_reasons: tuple[tuple[str, int], ...]
    overlapping_exclusion_reasons: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class LegacyComparison:
    legacy_count: int
    retained: int
    removed: int
    added: int
    legacy_type_distribution: tuple[tuple[str, int], ...]
    removed_reason_counts: tuple[tuple[str, int], ...]
    added_reason_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class ShadowCandidateAudit:
    candidate_id: str
    name_en: str
    name_zh: str
    allowed_provider_codes: tuple[str, ...]
    liquidity_rule: str
    member_ids: frozenset[UUID]
    membership_fingerprint: str
    funnel: CandidateFunnel
    legacy: LegacyComparison


@dataclass(frozen=True, slots=True)
class ProviderClassifiedUniverseAudit:
    analysis_date: date
    previous_session_date: date
    catalog_type_count: int
    observation_count: int
    canonical_evidence_count: int
    expected_unjoined_count: int
    observation_status_distribution: tuple[tuple[str, int], ...]
    observation_type_distribution: tuple[tuple[str, int], ...]
    canonical_type_distribution: tuple[tuple[str, int], ...]
    decisions: tuple[ClassificationDecision, ...]
    quarantine_reason_distribution: tuple[tuple[str, int], ...]
    candidate_a: ShadowCandidateAudit
    candidate_b: ShadowCandidateAudit
    hard_gates: tuple[tuple[str, bool], ...]
    audit_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        for key in ("candidate_a", "candidate_b"):
            candidate = value[key]
            assert isinstance(candidate, dict)
            candidate["member_ids"] = sorted(str(item) for item in candidate["member_ids"])
        return value


def audit_provider_classified_universes(
    *,
    analysis_date: date,
    identity_instrument_ids: frozenset[UUID],
    catalog_type_codes: frozenset[str],
    observations: tuple[ProviderSecurityObservationV1, ...],
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    current_bars: tuple[EodMarketBarReadModel, ...],
    previous_bars: tuple[EodMarketBarReadModel, ...],
) -> ProviderClassifiedUniverseAudit:
    """Return a deterministic, read-only shadow audit keyed only by instrument_id."""

    if not identity_instrument_ids or not catalog_type_codes:
        raise ValueError("completed identity and provider type catalog are required")
    current_date = _single_date(current_bars)
    previous_date = _single_date(previous_bars)
    if current_date != analysis_date or previous_date >= current_date:
        raise ValueError("EOD session dates do not match the analysis window")
    current = _unique_bars(current_bars)
    previous = _unique_bars(previous_bars)

    status_distribution = Counter(item.observation_status.value for item in observations)
    observation_types = Counter(item.provider_type_code or "missing" for item in observations)
    evidence_by_id: dict[UUID, list[ProviderInstrumentSecurityEvidenceV1]] = defaultdict(list)
    for item in evidence:
        evidence_by_id[item.instrument_id].append(item)
    canonical_types = Counter(item.provider_type_code for item in evidence)

    decisions: list[ClassificationDecision] = []
    for instrument_id in sorted(identity_instrument_ids, key=str):
        records = evidence_by_id.get(instrument_id, [])
        if not records:
            decisions.append(ClassificationDecision(instrument_id, None, "quarantine", "missing_evidence"))
            continue
        codes = {item.provider_type_code for item in records}
        if len(records) != 1:
            reason = "conflicting_type_evidence" if len(codes) > 1 else "multiple_type_evidence"
            decisions.append(ClassificationDecision(instrument_id, None, "quarantine", reason))
            continue
        item = records[0]
        if item.as_of_date > analysis_date:
            decisions.append(ClassificationDecision(instrument_id, item.provider_type_code, "quarantine", "future_dated_evidence"))
        elif item.provider_type_code not in catalog_type_codes:
            decisions.append(ClassificationDecision(instrument_id, item.provider_type_code, "quarantine", "unknown_provider_code"))
        elif item.provider_type_code == "CS":
            decisions.append(ClassificationDecision(instrument_id, "CS", "candidate_a", "provider_type_cs"))
        elif item.provider_type_code == "ADRC":
            decisions.append(ClassificationDecision(instrument_id, "ADRC", "candidate_b_extension", "provider_type_adrc"))
        else:
            decisions.append(ClassificationDecision(instrument_id, item.provider_type_code, "excluded", "provider_type_explicitly_excluded"))

    orphan_ids = set(evidence_by_id) - set(identity_instrument_ids)
    decision_by_id = {item.instrument_id: item for item in decisions}
    if len(decision_by_id) != len(identity_instrument_ids):
        raise ValueError("identity classification reconciliation failed")
    a_classified = {item.instrument_id for item in decisions if item.bucket == "candidate_a"}
    b_classified = a_classified | {item.instrument_id for item in decisions if item.bucket == "candidate_b_extension"}
    legacy_ids = {
        instrument_id
        for instrument_id in set(current) & set(previous)
        if _legacy_passes(current[instrument_id], previous[instrument_id])
    }
    candidate_a = _candidate(
        candidate_id=CANDIDATE_A_ID,
        name_en=CANDIDATE_A_NAME,
        name_zh=CANDIDATE_A_NAME_ZH,
        allowed=("CS",),
        classified=a_classified,
        decision_by_id=decision_by_id,
        current=current,
        previous=previous,
        legacy_ids=legacy_ids,
    )
    candidate_b = _candidate(
        candidate_id=CANDIDATE_B_ID,
        name_en=CANDIDATE_B_NAME,
        name_zh=CANDIDATE_B_NAME_ZH,
        allowed=("ADRC", "CS"),
        classified=b_classified,
        decision_by_id=decision_by_id,
        current=current,
        previous=previous,
        legacy_ids=legacy_ids,
    )
    quarantine = Counter(item.reason_code for item in decisions if item.bucket == "quarantine")
    bad_observations = sum(status_distribution.get(code, 0) for code in ("ambiguous", "collision", "malformed"))
    conflicting = sum(1 for item in decisions if item.reason_code == "conflicting_type_evidence")
    multiple_evidence = sum(1 for records in evidence_by_id.values() if len(records) > 1)
    a_codes = {decision_by_id[item].provider_type_code for item in candidate_a.member_ids}
    b_codes = {decision_by_id[item].provider_type_code for item in candidate_b.member_ids}
    hard_gates = {
        "candidate_a_non_cs_zero": a_codes <= {"CS"},
        "candidate_b_codes_cs_or_adrc": b_codes <= {"CS", "ADRC"},
        "included_evidence_coverage_100_percent": all(item in evidence_by_id for item in candidate_b.member_ids),
        "duplicate_instrument_id_zero": len(candidate_b.member_ids) == len(set(candidate_b.member_ids)),
        "multiple_canonical_evidence_zero": multiple_evidence == 0,
        "orphan_reference_zero": not orphan_ids,
        "ambiguous_collision_malformed_zero": bad_observations == 0,
        "canonical_conflict_zero": conflicting == 0,
        "unknown_codes_quarantined": all(
            item.provider_type_code in catalog_type_codes or item.bucket == "quarantine" for item in decisions
        ),
        "reconciliation_complete": len(decisions) == len(identity_instrument_ids),
    }
    fingerprint_payload = {
        "analysis_date": analysis_date.isoformat(),
        "catalog_codes": sorted(catalog_type_codes),
        "observation_status_distribution": sorted(status_distribution.items()),
        "canonical_type_distribution": sorted(canonical_types.items()),
        "candidate_a": candidate_a.membership_fingerprint,
        "candidate_b": candidate_b.membership_fingerprint,
        "hard_gates": sorted(hard_gates.items()),
    }
    return ProviderClassifiedUniverseAudit(
        analysis_date=analysis_date,
        previous_session_date=previous_date,
        catalog_type_count=len(catalog_type_codes),
        observation_count=len(observations),
        canonical_evidence_count=len(evidence),
        expected_unjoined_count=status_distribution.get(ProviderObservationStatus.EXPECTED_UNJOINED.value, 0),
        observation_status_distribution=tuple(sorted(status_distribution.items())),
        observation_type_distribution=tuple(sorted(observation_types.items())),
        canonical_type_distribution=tuple(sorted(canonical_types.items())),
        decisions=tuple(decisions),
        quarantine_reason_distribution=tuple(sorted(quarantine.items())),
        candidate_a=candidate_a,
        candidate_b=candidate_b,
        hard_gates=tuple(sorted(hard_gates.items())),
        audit_fingerprint=_sha256(fingerprint_payload),
    )


def _candidate(
    *,
    candidate_id: str,
    name_en: str,
    name_zh: str,
    allowed: tuple[str, ...],
    classified: set[UUID],
    decision_by_id: dict[UUID, ClassificationDecision],
    current: dict[UUID, EodMarketBarReadModel],
    previous: dict[UUID, EodMarketBarReadModel],
    legacy_ids: set[UUID],
) -> ShadowCandidateAudit:
    both = classified & set(current) & set(previous)
    exchange = {item for item in both if current[item].primary_exchange in SUPPORTED_EXCHANGES}
    price = {item for item in exchange if previous[item].close >= MINIMUM_PREVIOUS_CLOSE}
    liquid = {
        item for item in price
        if previous[item].close * previous[item].volume >= MINIMUM_PREVIOUS_DOLLAR_VOLUME
    }
    sequential_exclusions = Counter()
    sequential_exclusions["missing_current_or_previous_session"] = len(classified - both)
    sequential_exclusions["unsupported_exchange"] = len(both - exchange)
    sequential_exclusions["previous_close_below_5"] = len(exchange - price)
    sequential_exclusions["previous_dollar_volume_below_20m"] = len(price - liquid)
    overlapping_exclusions = Counter()
    overlapping_exclusions["missing_current_or_previous_session"] = len(classified - both)
    overlapping_exclusions["unsupported_exchange"] = sum(
        1 for item in classified & set(current) if current[item].primary_exchange not in SUPPORTED_EXCHANGES
    )
    overlapping_exclusions["previous_close_below_5"] = sum(
        1 for item in classified & set(previous) if previous[item].close < MINIMUM_PREVIOUS_CLOSE
    )
    overlapping_exclusions["previous_dollar_volume_below_20m"] = sum(
        1 for item in classified & set(previous)
        if previous[item].close * previous[item].volume < MINIMUM_PREVIOUS_DOLLAR_VOLUME
    )
    funnel = CandidateFunnel(
        len(classified), len(both), len(exchange), len(price), len(liquid), len(liquid),
        tuple((key, value) for key, value in sorted(sequential_exclusions.items()) if value),
        tuple((key, value) for key, value in sorted(overlapping_exclusions.items()) if value),
    )
    counts = (
        funnel.provider_type_classified,
        funnel.both_sessions_available,
        funnel.supported_exchange,
        funnel.previous_close_at_least_5,
        funnel.previous_dollar_volume_at_least_20m,
        funnel.final_shadow_candidate,
    )
    if counts != tuple(sorted(counts, reverse=True)):
        raise ValueError("shadow candidate funnel must be non-increasing")
    retained = legacy_ids & liquid
    removed = legacy_ids - liquid
    added = liquid - legacy_ids
    legacy_types = Counter(
        (decision_by_id[item].provider_type_code or decision_by_id[item].bucket)
        if item in decision_by_id else "missing_identity"
        for item in legacy_ids
    )
    removed_reasons = Counter(
        decision_by_id[item].reason_code if item in decision_by_id else "missing_identity"
        for item in removed
    )
    added_reasons = Counter("provider_classified_but_not_legacy_common_stock" for _ in added)
    fingerprint = _sha256({"candidate_id": candidate_id, "member_ids": sorted(str(item) for item in liquid)})
    return ShadowCandidateAudit(
        candidate_id, name_en, name_zh, allowed, LIQUIDITY_RULE, frozenset(liquid), fingerprint, funnel,
        LegacyComparison(
            len(legacy_ids), len(retained), len(removed), len(added),
            tuple(sorted(legacy_types.items())), tuple(sorted(removed_reasons.items())),
            tuple(sorted(added_reasons.items())),
        ),
    )


def _legacy_passes(current: EodMarketBarReadModel, previous: EodMarketBarReadModel) -> bool:
    from tip_api.contracts.market_data.v1 import InstrumentType
    return (
        current.instrument_type is InstrumentType.COMMON_STOCK
        and current.primary_exchange in SUPPORTED_EXCHANGES
        and previous.close >= MINIMUM_PREVIOUS_CLOSE
        and previous.close * previous.volume >= MINIMUM_PREVIOUS_DOLLAR_VOLUME
    )


def _unique_bars(rows: Iterable[EodMarketBarReadModel]) -> dict[UUID, EodMarketBarReadModel]:
    result: dict[UUID, EodMarketBarReadModel] = {}
    for row in rows:
        if row.instrument_id in result:
            raise ValueError("duplicate instrument_id")
        result[row.instrument_id] = row
    return result


def _single_date(rows: tuple[EodMarketBarReadModel, ...]) -> date:
    dates = {item.session_date for item in rows}
    if len(dates) != 1:
        raise ValueError("one non-empty EOD session is required")
    return next(iter(dates))


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
