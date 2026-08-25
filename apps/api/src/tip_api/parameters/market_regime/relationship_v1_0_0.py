"""Frozen Phase 2 ETF relationship registry and deterministic parameters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal


RELATIONSHIP_CONTRACT_VERSION = "etf-relationship-map/1.0"
RELATIONSHIP_CALCULATION_VERSION = "market-regime-opportunity-map-etf-relationships-v1.0.0"
RELATIONSHIP_PARAMETER_SET_ID = "mrom-etf-relationships-v1-fixed-registry-1"
WINDOWS = (5, 10, 20)
CORRELATION_MINIMUM_OBSERVATIONS = 18
CORRELATION_POSITIVE_THRESHOLD = Decimal("0.35")
RELATIONSHIP_BREAK_PRIOR_THRESHOLD = Decimal("0.50")
RELATIONSHIP_BREAK_CURRENT_THRESHOLD = Decimal("0.10")
RELATIONSHIP_BREAK_CHANGE_THRESHOLD = Decimal("-0.30")
DIVERGENCE_SPREAD_THRESHOLD = Decimal("0.02")
ROTATION_Z_THRESHOLD = Decimal("1.50")
ROTATION_CONFIRMATION_SESSIONS = 2
RATIO_STATISTICS_MINIMUM_OBSERVATIONS = 60
RATIO_STATISTICS_WINDOW = 20
RATIO_PERCENTILE_WINDOW = 60
CORRELATION_PERTURBATION_WINDOWS = (18, 20, 22)
NUMERIC_SCALE = Decimal("0.0000000001")


@dataclass(frozen=True, slots=True)
class EtfBasketEntry:
    ticker: str
    family: str
    role: str


@dataclass(frozen=True, slots=True)
class EtfPairDefinition:
    pair_id: str
    left_ticker: str
    right_ticker: str
    relationship_family: str
    economic_rationale: str
    expected_interpretation: str
    forbidden_interpretation: str
    regime_orientation: str
    applicable_windows: tuple[int, ...] = WINDOWS
    availability_requirement: str = "paired_positive_closes_on_contiguous_xnys_sessions"


ETF_BASKET = (
    EtfBasketEntry("SPY", "broad_market", "large_cap_broad"),
    EtfBasketEntry("QQQ", "broad_market", "growth_heavy_broad"),
    EtfBasketEntry("DIA", "broad_market", "blue_chip_broad"),
    EtfBasketEntry("IWF", "growth_value", "large_cap_growth"),
    EtfBasketEntry("IWD", "growth_value", "large_cap_value"),
    EtfBasketEntry("VUG", "growth_value", "growth_context"),
    EtfBasketEntry("VTV", "growth_value", "value_context"),
    EtfBasketEntry("IWM", "size", "small_cap"),
    EtfBasketEntry("MDY", "size", "mid_cap"),
    EtfBasketEntry("IJR", "size", "small_cap_context"),
    EtfBasketEntry("XLB", "sector", "materials"),
    EtfBasketEntry("XLC", "sector", "communication_services"),
    EtfBasketEntry("XLE", "sector", "energy"),
    EtfBasketEntry("XLF", "sector", "financials"),
    EtfBasketEntry("XLI", "sector", "industrials"),
    EtfBasketEntry("XLK", "sector", "technology"),
    EtfBasketEntry("XLP", "sector", "consumer_staples_defensive"),
    EtfBasketEntry("XLRE", "sector", "real_estate"),
    EtfBasketEntry("XLU", "sector", "utilities_defensive"),
    EtfBasketEntry("XLV", "sector", "health_care_defensive_context"),
    EtfBasketEntry("XLY", "sector", "consumer_discretionary"),
    EtfBasketEntry("SMH", "industry_theme", "semiconductors"),
    EtfBasketEntry("XBI", "industry_theme", "biotechnology"),
    EtfBasketEntry("KRE", "industry_theme", "regional_banks"),
    EtfBasketEntry("IGV", "industry_theme", "software"),
    EtfBasketEntry("TLT", "rates_credit", "long_treasury_duration"),
    EtfBasketEntry("IEF", "rates_credit", "intermediate_treasury"),
    EtfBasketEntry("SHY", "rates_credit", "short_treasury"),
    EtfBasketEntry("HYG", "rates_credit", "high_yield_credit"),
    EtfBasketEntry("LQD", "rates_credit", "investment_grade_credit"),
)


ETF_PAIRS = (
    EtfPairDefinition("growth_broad", "QQQ", "SPY", "growth_vs_broad", "Growth-heavy equities versus the broad large-cap market.", "Positive spread is relative growth leadership.", "It is not evidence that capital flowed from SPY to QQQ or that QQQ caused SPY.", "risk_on_if_left_leads"),
    EtfPairDefinition("growth_value", "IWF", "IWD", "style_rotation", "Large-cap growth versus large-cap value.", "The spread is a transparent style-relative-strength proxy.", "It is not a fund-flow measure or a directive to trade a style spread.", "risk_on_if_left_leads"),
    EtfPairDefinition("small_large", "IWM", "SPY", "size_participation", "Small caps versus broad large caps.", "Positive spread is broader small-cap participation context.", "It does not prove broad economic acceleration or capital rotation.", "risk_on_if_left_leads"),
    EtfPairDefinition("mid_large", "MDY", "SPY", "size_participation", "Mid caps versus broad large caps.", "Positive spread is mid-cap relative participation context.", "It does not prove fund flows or future outperformance.", "risk_on_if_left_leads"),
    EtfPairDefinition("consumer_risk", "XLY", "XLP", "cyclical_defensive", "Consumer discretionary versus consumer staples.", "Positive spread is a cyclical-versus-defensive price proxy.", "It is not a causal consumer-risk or fund-flow conclusion.", "risk_on_if_left_leads"),
    EtfPairDefinition("technology_defensive", "XLK", "XLU", "cyclical_defensive", "Technology versus utilities.", "Positive spread is growth/cyclical relative strength versus a defensive proxy.", "It is not proof that risk appetite caused either return.", "risk_on_if_left_leads"),
    EtfPairDefinition("industrial_defensive", "XLI", "XLU", "cyclical_defensive", "Industrials versus utilities.", "Positive spread is cyclical relative strength versus a defensive proxy.", "It is not an economic forecast or fund-flow measure.", "risk_on_if_left_leads"),
    EtfPairDefinition("financial_defensive", "XLF", "XLU", "cyclical_defensive", "Financials versus utilities.", "Positive spread is financial-sector relative strength versus a defensive proxy.", "It is not proof about credit creation or capital movement.", "risk_on_if_left_leads"),
    EtfPairDefinition("energy_broad", "XLE", "SPY", "sector_relative", "Energy versus the broad market.", "The spread is energy-sector relative performance context.", "Energy leadership is not unconditionally risk-on and is not fund flow.", "contextual"),
    EtfPairDefinition("health_broad", "XLV", "SPY", "defensive_relative", "Health care versus the broad market.", "Positive spread may be defensive relative-strength context.", "It is not a causal defensive-flow conclusion.", "defensive_if_left_leads"),
    EtfPairDefinition("semis_growth", "SMH", "QQQ", "industry_within_growth", "Semiconductors versus growth-heavy equities.", "The spread shows semiconductor leadership inside growth context.", "It is not a causal technology-cycle signal.", "risk_on_if_left_leads"),
    EtfPairDefinition("biotech_health", "XBI", "XLV", "industry_within_sector", "Biotechnology versus broad health care.", "The spread shows higher-beta biotech relative performance.", "It is not a clinical, fundamental, or fund-flow conclusion.", "risk_on_if_left_leads"),
    EtfPairDefinition("regional_financials", "KRE", "XLF", "industry_within_sector", "Regional banks versus broad financials.", "The spread is regional-bank relative performance context.", "It does not prove banking-system health or deposit flows.", "risk_on_if_left_leads"),
    EtfPairDefinition("software_growth", "IGV", "QQQ", "industry_within_growth", "Software versus growth-heavy equities.", "The spread shows software leadership within growth context.", "It is not a causal technology-demand signal.", "risk_on_if_left_leads"),
    EtfPairDefinition("credit_quality", "HYG", "LQD", "credit_risk", "High-yield versus investment-grade credit ETFs.", "Positive spread is a market-price credit-risk-appetite proxy.", "It is not true credit flow, default forecasting, or causal evidence.", "risk_on_if_left_leads"),
    EtfPairDefinition("credit_duration", "HYG", "TLT", "credit_vs_duration", "High-yield credit versus long Treasury duration.", "Positive spread is a risk-credit versus duration price relationship.", "It is not a fund-flow measure or a complete rates model.", "risk_on_if_left_leads"),
)


def parameter_payload() -> dict[str, object]:
    return {
        "contract_version": RELATIONSHIP_CONTRACT_VERSION,
        "calculation_version": RELATIONSHIP_CALCULATION_VERSION,
        "parameter_set_id": RELATIONSHIP_PARAMETER_SET_ID,
        "windows": list(WINDOWS),
        "correlation_minimum_observations": CORRELATION_MINIMUM_OBSERVATIONS,
        "correlation_positive_threshold": str(CORRELATION_POSITIVE_THRESHOLD),
        "relationship_break": {
            "prior_threshold": str(RELATIONSHIP_BREAK_PRIOR_THRESHOLD),
            "current_threshold": str(RELATIONSHIP_BREAK_CURRENT_THRESHOLD),
            "change_threshold": str(RELATIONSHIP_BREAK_CHANGE_THRESHOLD),
        },
        "divergence_spread_threshold": str(DIVERGENCE_SPREAD_THRESHOLD),
        "rotation_z_threshold": str(ROTATION_Z_THRESHOLD),
        "rotation_confirmation_sessions": ROTATION_CONFIRMATION_SESSIONS,
        "ratio_statistics_minimum_observations": RATIO_STATISTICS_MINIMUM_OBSERVATIONS,
        "ratio_statistics_window": RATIO_STATISTICS_WINDOW,
        "ratio_percentile_window": RATIO_PERCENTILE_WINDOW,
        "correlation_perturbation_windows": list(CORRELATION_PERTURBATION_WINDOWS),
        "numeric_scale": str(NUMERIC_SCALE),
        "basket": [asdict(item) for item in ETF_BASKET],
        "pairs": [asdict(item) for item in ETF_PAIRS],
        "state_priority": [
            "relationship_break_candidate",
            "rotation_candidate",
            "divergence",
            "synchronous_strengthening",
            "synchronous_weakening",
            "neutral",
        ],
    }


RELATIONSHIP_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(parameter_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
).hexdigest()


if len({item.ticker for item in ETF_BASKET}) != 30:
    raise RuntimeError("ETF basket must contain exactly 30 unique tickers")
if len({item.pair_id for item in ETF_PAIRS}) != 16:
    raise RuntimeError("ETF pair registry must contain exactly 16 unique pairs")
if any(item.left_ticker not in {row.ticker for row in ETF_BASKET} or item.right_ticker not in {row.ticker for row in ETF_BASKET} for item in ETF_PAIRS):
    raise RuntimeError("every pair ticker must be registered in the frozen basket")
