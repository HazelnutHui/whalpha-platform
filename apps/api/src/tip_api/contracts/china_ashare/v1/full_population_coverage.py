"""Outcome-blind full-population A-share cross-family coverage diagnostic."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import Field, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract


FULL_POPULATION_COVERAGE_VERSION = "china-ashare-full-population-coverage/1.0"
POPULATION_PACKAGE_FINGERPRINT = (
    "13595c0645aa36acc5fea8d818509b484582ad13d7def53d377b984d549c02c0"
)
SOURCE_COMPLETION_FINGERPRINT = (
    "833f79859b411f0422c4c1e9c0cbf2898dbe59df52c005ff17d546b56af7aab2"
)
NORMALIZED_RUN_FINGERPRINT = (
    "a7d24928a464b20632c44d6c92ac7aea3b99bfc22e077ced13073781c63682b4"
)


class CoverageDisposition(StrEnum):
    SOURCE_COMPLETE = "source_complete"
    PROVISIONAL_RECONSTRUCTION_ONLY = "provisional_reconstruction_only"
    BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"


class ChinaAshareCoverageFamilyV1(FrozenContract):
    ordinal: int = Field(ge=1, le=13)
    family_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    disposition: CoverageDisposition
    current_evidence: str
    blocking_gap: str | None = None
    next_offline_action: str | None = None
    external_evidence_required: bool
    authorizes_backtest: Literal[False] = False


class ChinaAshareFullPopulationCoverageReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-full-population-coverage/1.0"
    ] = FULL_POPULATION_COVERAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    evaluated_date: Literal[date(2026, 9, 17)] = date(2026, 9, 17)
    scope: Literal["sse_szse_frozen_five_year_acquisition_population"] = (
        "sse_szse_frozen_five_year_acquisition_population"
    )
    population_package_fingerprint: Literal[POPULATION_PACKAGE_FINGERPRINT] = (
        POPULATION_PACKAGE_FINGERPRINT
    )
    source_completion_fingerprint: Literal[SOURCE_COMPLETION_FINGERPRINT] = (
        SOURCE_COMPLETION_FINGERPRINT
    )
    normalized_run_fingerprint: Literal[NORMALIZED_RUN_FINGERPRINT] = (
        NORMALIZED_RUN_FINGERPRINT
    )
    partition_count: Literal[109] = 109
    target_count: Literal[5409] = 5409
    resolved_target_count: Literal[5296] = 5296
    quarantined_target_count: Literal[113] = 113
    normalized_state_count: Literal[5997301] = 5997301
    normalized_bar_count: Literal[5987288] = 5987288
    normalized_adjustment_observation_count: Literal[62272] = 62272
    suspended_state_count: Literal[10013] = 10013
    risk_warning_present_unspecified_count: Literal[160626] = 160626
    price_limit_regime_unknown_count: Literal[5997301] = 5997301
    source_available_at_null_count: Literal[5997301] = 5997301
    resolved_window_listing_count: Literal[930] = 930
    resolved_delisted_occurrence_count: Literal[76] = 76
    terminal_boundary_occurrence_gap_count: Literal[22] = 22
    terminal_boundary_session_gap_count: Literal[23] = 23
    families: tuple[ChinaAshareCoverageFamilyV1, ...] = Field(
        min_length=13, max_length=13
    )
    source_acquisition_complete: Literal[True] = True
    normalization_complete: Literal[True] = True
    full_market_claim_authorized: Literal[False] = False
    historical_coverage_admitted: Literal[False] = False
    adjusted_return_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    logical_fingerprint: str

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareFullPopulationCoverageReportV1":
        if (
            self.resolved_target_count + self.quarantined_target_count
            != self.target_count
            or self.normalized_bar_count + self.suspended_state_count
            != self.normalized_state_count
            or self.price_limit_regime_unknown_count != self.normalized_state_count
            or self.source_available_at_null_count != self.normalized_state_count
            or tuple(item.ordinal for item in self.families) != tuple(range(1, 14))
            or len({item.family_id for item in self.families}) != 13
            or self.families != _families()
            or full_population_coverage_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("A-share full-population coverage report differs")
        return self


def full_population_coverage_fingerprint(
    value: ChinaAshareFullPopulationCoverageReportV1 | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, ChinaAshareFullPopulationCoverageReportV1)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def china_ashare_full_population_coverage_report_v1() -> (
    ChinaAshareFullPopulationCoverageReportV1
):
    payload = {"families": _families()}
    provisional = ChinaAshareFullPopulationCoverageReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return ChinaAshareFullPopulationCoverageReportV1.model_validate(
        {**payload, "logical_fingerprint": full_population_coverage_fingerprint(provisional)}
    )


@lru_cache(maxsize=1)
def _families() -> tuple[ChinaAshareCoverageFamilyV1, ...]:
    values = (
        (1, "instrument_identity", "provisional_reconstruction_only", "5,296 stable listed-occurrence identities; 113 quarantined targets retained separately.", "113 historical SZSE occurrences lack sufficient official board evidence.", "Freeze a resolved identity census and a separate official-evidence request queue.", True),
        (2, "trading_calendar", "provisional_reconstruction_only", "1,211 observed SSE/SZSE sessions plus existing annual official closure evidence.", "Full-population lifecycle-by-calendar reconciliation has not been materialized.", "Reconcile every resolved occurrence against the frozen session set and listing interval.", False),
        (3, "raw_unadjusted_eod", "source_complete", "5,987,288 normalized unadjusted bars and explicit quarantine custody.", "The 113 quarantined targets prevent a claim of complete admitted-market coverage.", "Run uniqueness, OHLC, bar/state, and lifecycle-boundary checks on resolved scope.", False),
        (4, "daily_price_limits", "blocked_missing_evidence", "All 5,997,301 normalized states retain price_limit_regime=unknown.", "IPO no-limit windows, old main-board IPO rules, and STAR/ChiNext risk-warning rules are not covered by the pilot rule set.", "Generate a rule-applicability gap census; obtain effective-dated official rule evidence before evaluation.", True),
        (5, "suspension_state", "provisional_reconstruction_only", "10,013 resolved suspension states and zero normalized unknown trading states.", "Provider observation is not the same as point-in-time official suspension-notice evidence.", "Reconcile state continuity offline and preserve reconstructed-evidence status.", True),
        (6, "risk_warning_state", "blocked_missing_evidence", "160,626 states are only present_unspecified.", "Effective-dated ST/*ST/delisting-risk subtypes and historical source clocks are absent.", "Build an official status-change evidence queue; do not infer subtype from names.", True),
        (7, "adjustment_factors", "blocked_missing_evidence", "62,272 provider adjustment observations retained with normalized_return_authorized=false.", "Provider factor steps do not prove corporate-action terms or total-return semantics.", "Deduplicate factor transitions into a candidate evidence registry for independent reconciliation.", True),
        (8, "corporate_actions", "blocked_missing_evidence", "Pilot evidence exists for six instruments only; no full-population event family is admitted.", "Cash, stock, rights, merger, and terminal consideration terms are not reconciled for the population.", "Acquire and reconcile independent CNINFO or exchange event terms for candidate transitions.", True),
        (9, "instrument_lifecycle", "provisional_reconstruction_only", "5,220 current and 76 delisted resolved occurrences; 930 listed inside the window.", "113 identities and 22 terminal occurrences with 23 boundary sessions remain unresolved.", "Create a full-population lifecycle contract supporting within-window listing and delisting.", True),
        (10, "daily_universe_membership", "blocked_missing_evidence", "No full-population daily decision artifact has been admitted.", "Identity, warning-state, price-limit, and lifecycle gaps prevent complete membership decisions.", "Materialize provisional decisions with dependency-driven quarantine only after the offline census.", False),
        (11, "effective_dated_trading_rules", "blocked_missing_evidence", "Ten pilot rules cover normal regimes and selected main-board warning states.", "Full-scope IPO and special-board rule intervals are incomplete.", "Run full-population rule selection to expose exact uncovered intervals, without filling gaps heuristically.", True),
        (12, "effective_dated_fees", "provisional_reconstruction_only", "Fourteen official statutory fee rules exist in the pilot package.", "Actual Ping An commission history, minimum commission, and account-specific terms remain assumptions.", "Extend statutory interval coverage offline and keep broker commission as an explicit scenario.", True),
        (13, "historical_coverage", "blocked_missing_evidence", "Source acquisition and normalization are complete for the frozen SSE/SZSE target list.", "The preceding family gaps prevent Historical Coverage admission.", "Publish and exactly replay this ordered family census; keep admission closed until blockers are resolved.", False),
    )
    return tuple(
        ChinaAshareCoverageFamilyV1(
            ordinal=ordinal,
            family_id=family_id,
            disposition=CoverageDisposition(disposition),
            current_evidence=evidence,
            blocking_gap=gap,
            next_offline_action=action,
            external_evidence_required=external,
        )
        for ordinal, family_id, disposition, evidence, gap, action, external in values
    )
