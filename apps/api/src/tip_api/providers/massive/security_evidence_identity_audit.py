"""Offline-only reconciliation of accepted provider identity observations."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class DuplicateTickerGroupAudit:
    provider_ticker: str
    observation_count: int
    resolution_statuses: tuple[str, ...]
    canonical_instrument_ids: tuple[str, ...]
    share_class_figi_count: int
    composite_figi_count: int
    provider_stable_id_count: int
    resolver_included: bool


@dataclass(frozen=True, slots=True)
class IdentityReconciliationAudit:
    total_observations: int
    status_counts: tuple[tuple[str, int], ...]
    duplicate_ticker_groups: tuple[DuplicateTickerGroupAudit, ...]
    stable_identifier_collision_count: int
    ticker_ambiguity_count: int
    expected_unjoined_count: int
    linkage_numerator: int
    linkage_denominator: int
    linkage_ratio: float
    reconciliation_passed: bool


def audit_identity_reconciliation(
    identity_rows: Sequence[Mapping[str, object]],
    resolver_rows: Sequence[Mapping[str, object]],
) -> IdentityReconciliationAudit:
    resolver = {
        str(row["provider_ticker"]).upper(): str(row["canonical_instrument_id"])
        for row in resolver_rows
    }
    statuses = Counter(str(row["resolution_status"]) for row in identity_rows)
    by_ticker: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    stable_to_canonical: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in identity_rows:
        ticker = str(row["provider_ticker"]).upper()
        by_ticker[ticker].append(row)
        canonical = row.get("canonical_instrument_id")
        if canonical is None:
            continue
        for field in ("share_class_figi", "composite_figi", "provider_instrument_id"):
            value = row.get(field)
            if value:
                stable_to_canonical[(field, str(value).upper())].add(str(canonical))

    duplicate_groups = []
    ticker_ambiguity_count = 0
    for ticker, rows in sorted(by_ticker.items()):
        if len(rows) <= 1:
            continue
        canonical_ids = tuple(sorted({str(row["canonical_instrument_id"]) for row in rows if row.get("canonical_instrument_id") is not None}))
        if len(canonical_ids) > 1:
            ticker_ambiguity_count += len(rows)
        duplicate_groups.append(
            DuplicateTickerGroupAudit(
                provider_ticker=ticker,
                observation_count=len(rows),
                resolution_statuses=tuple(sorted(str(row["resolution_status"]) for row in rows)),
                canonical_instrument_ids=canonical_ids,
                share_class_figi_count=sum(row.get("share_class_figi") is not None for row in rows),
                composite_figi_count=sum(row.get("composite_figi") is not None for row in rows),
                provider_stable_id_count=sum(row.get("provider_instrument_id") is not None for row in rows),
                resolver_included=ticker in resolver,
            )
        )

    resolved = [row for row in identity_rows if str(row["resolution_status"]) == "resolved"]
    linkage_numerator = sum(
        row.get("canonical_instrument_id") is not None
        and resolver.get(str(row["provider_ticker"]).upper()) == str(row["canonical_instrument_id"])
        for row in resolved
    )
    linkage_denominator = len(resolved)
    expected_unjoined_count = len(identity_rows) - linkage_denominator
    reconciled = sum(statuses.values()) == len(identity_rows)
    collisions = sum(len(values) > 1 for values in stable_to_canonical.values())
    return IdentityReconciliationAudit(
        total_observations=len(identity_rows),
        status_counts=tuple(sorted(statuses.items())),
        duplicate_ticker_groups=tuple(duplicate_groups),
        stable_identifier_collision_count=collisions,
        ticker_ambiguity_count=ticker_ambiguity_count,
        expected_unjoined_count=expected_unjoined_count,
        linkage_numerator=linkage_numerator,
        linkage_denominator=linkage_denominator,
        linkage_ratio=linkage_numerator / linkage_denominator if linkage_denominator else 0.0,
        reconciliation_passed=reconciled,
    )
