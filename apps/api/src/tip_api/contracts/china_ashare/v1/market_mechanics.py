"""Effective-dated A-share market-mechanics and account-cost contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    FrozenContract,
)
from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)


MARKET_MECHANICS_METHOD_VERSION = "china-ashare-market-mechanics/1.0"
MARKET_MECHANICS_PACKAGE_VERSION = "china-ashare-market-mechanics-package/1.0"
ACCOUNT_COST_SCENARIO_VERSION = "ping-an-all-in-wanyi-min5/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]*$")
_OFFICIAL_HOSTS = {
    "www.sse.com.cn",
    "edu.sse.com.cn",
    "star.sse.com.cn",
    "www.szse.cn",
    "investor.szse.cn",
    "www.csrc.gov.cn",
    "www.chinaclear.cn",
    "www.mof.gov.cn",
    "jrj.sh.gov.cn",
    "chinatax.gov.cn",
    "www.chinatax.gov.cn",
    "shanxi.chinatax.gov.cn",
    "guangdong.chinatax.gov.cn",
    "tianjin.chinatax.gov.cn",
}


class ChinaAshareTradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ChinaAshareFeeKind(StrEnum):
    STAMP_DUTY = "stamp_duty"
    SECURITIES_REGULATORY_FEE = "securities_regulatory_fee"
    EXCHANGE_HANDLING_FEE = "exchange_handling_fee"
    TRANSFER_FEE = "transfer_fee"


class ChinaAshareCommissionBasis(StrEnum):
    ALL_IN = "all_in"
    NET_OF_REGULATORY_FEES = "net_of_regulatory_fees"


class ChinaAshareMarketMechanicsArtifactKind(StrEnum):
    SOURCE_REFERENCES = "source_references"
    TRADING_RULES = "trading_rules"
    FEE_RULES = "fee_rules"
    ACCOUNT_COST_SCENARIO = "account_cost_scenario"
    PRICE_LIMIT_DECISIONS = "price_limit_decisions"
    REPORT = "report"
    RAW_SOURCE = "raw_source"


class ChinaAshareOfficialSourceReferenceV1(FrozenContract):
    source_id: str
    source_url: str
    publisher: str
    published_date: date
    evidence_purpose: str
    retrieved_at: datetime
    final_url: str | None = None
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1, le=8 * 1024 * 1024)
    raw_sha256: str | None = None

    @field_validator(
        "source_id",
        "source_url",
        "publisher",
        "evidence_purpose",
        "final_url",
        "content_type",
        mode="before",
    )
    @classmethod
    def text_is_present(cls, value: str | None, info: Any) -> str | None:
        if value is None and info.field_name in {"final_url", "content_type"}:
            return None
        assert value is not None
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("published_date", mode="before")
    @classmethod
    def published_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("published_date must contain a date")
        return value

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("raw_sha256")
    @classmethod
    def raw_hash_is_sha256(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256.fullmatch(value):
            raise ValueError("raw_sha256 must be a SHA-256 value")
        return value

    @model_validator(mode="after")
    def source_is_official(self) -> "ChinaAshareOfficialSourceReferenceV1":
        parsed = urlparse(self.source_url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or (
            hostname not in _OFFICIAL_HOSTS
            and not hostname.endswith(".chinatax.gov.cn")
        ):
            raise ValueError("market-mechanics source must use an approved official host")
        if self.published_date > self.retrieved_at.date():
            raise ValueError("official source publication cannot follow retrieval")
        capture_fields = (
            self.final_url,
            self.content_type,
            self.raw_byte_size,
            self.raw_sha256,
        )
        if any(item is not None for item in capture_fields) and not all(
            item is not None for item in capture_fields
        ):
            raise ValueError("official source capture metadata must be all present or all absent")
        if self.final_url is not None:
            final = urlparse(self.final_url)
            final_host = (final.hostname or "").lower()
            if final.scheme != "https" or (
                final_host not in _OFFICIAL_HOSTS
                and not final_host.endswith(".chinatax.gov.cn")
            ):
                raise ValueError("official source redirect left the approved host set")
        return self


class ChinaAshareMarketMechanicsArtifactV1(FrozenContract):
    artifact_kind: ChinaAshareMarketMechanicsArtifactKind
    artifact_id: str
    relative_path: str
    byte_size: int = Field(ge=1, le=64 * 1024 * 1024)
    physical_sha256: str
    row_count: int = Field(ge=1)

    @field_validator("artifact_id", "relative_path", mode="before")
    @classmethod
    def artifact_text_is_present(cls, value: str, info: Any) -> str:
        value = normalize_required_string(value, field_name=info.field_name)
        if info.field_name == "relative_path" and (
            value.startswith("/") or ".." in value.split("/")
        ):
            raise ValueError("market mechanics artifact path is unsafe")
        return value

    @field_validator("physical_sha256")
    @classmethod
    def artifact_hash_is_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("physical_sha256 must be a SHA-256 value")
        return value


class ChinaAshareFeeRuleV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    fee_rule_id: str
    fee_kind: ChinaAshareFeeKind
    exchange: ChinaAshareExchange
    effective_from: date
    effective_to: date | None = None
    buy_rate: Decimal
    sell_rate: Decimal
    source_id: str
    quality_status: QualityStatus

    @field_validator("fee_rule_id", "source_id", mode="before")
    @classmethod
    def text_is_present(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("fee effective fields must contain dates")
        return value

    @field_validator("buy_rate", "sell_rate", mode="before")
    @classmethod
    def rates_are_exact(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator("buy_rate", "sell_rate")
    @classmethod
    def rates_are_bounded(cls, value: Decimal, info: Any) -> Decimal:
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value < 0 or value > Decimal("0.01"):
            raise ValueError(f"{info.field_name} must be in [0, 0.01]")
        return value

    @model_validator(mode="after")
    def fee_reconciles(self) -> "ChinaAshareFeeRuleV1":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("fee effective_to cannot precede effective_from")
        if self.fee_kind is ChinaAshareFeeKind.STAMP_DUTY and self.buy_rate != 0:
            raise ValueError("A-share stamp duty must remain seller-only")
        return self


class ChinaAshareAccountCostScenarioV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    scenario_version: Literal["ping-an-all-in-wanyi-min5/1.0"] = (
        ACCOUNT_COST_SCENARIO_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    broker_name: Literal["平安证券"] = "平安证券"
    access_channel: Literal["同花顺"] = "同花顺"
    commission_basis: ChinaAshareCommissionBasis
    commission_rate_per_side: Decimal
    minimum_commission_cny_per_order: Decimal
    slippage_rate_per_side: Decimal
    currency_quantum_cny: Decimal = Decimal("0.01")
    account_observation_status: Literal["user_reported"] = "user_reported"
    effective_from: date
    confirmed_at: datetime
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator(
        "commission_rate_per_side",
        "minimum_commission_cny_per_order",
        "slippage_rate_per_side",
        "currency_quantum_cny",
        mode="before",
    )
    @classmethod
    def decimals_are_exact(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "commission_rate_per_side",
        "minimum_commission_cny_per_order",
        "slippage_rate_per_side",
        "currency_quantum_cny",
    )
    @classmethod
    def decimals_are_bounded(cls, value: Decimal, info: Any) -> Decimal:
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return value

    @field_validator("effective_from", mode="before")
    @classmethod
    def effective_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("scenario effective_from must contain a date")
        return value

    @field_validator("confirmed_at")
    @classmethod
    def confirmed_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_reasons(value)

    @field_validator("logical_fingerprint")
    @classmethod
    def hash_is_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("logical_fingerprint must be a SHA-256 value")
        return value

    @model_validator(mode="after")
    def scenario_reconciles(self) -> "ChinaAshareAccountCostScenarioV1":
        if self.commission_rate_per_side > Decimal("0.01"):
            raise ValueError("commission rate exceeds the scenario ceiling")
        if self.minimum_commission_cny_per_order > Decimal("100"):
            raise ValueError("minimum commission exceeds the scenario ceiling")
        if self.slippage_rate_per_side > Decimal("0.01"):
            raise ValueError("slippage rate exceeds the scenario ceiling")
        if self.currency_quantum_cny != Decimal("0.01"):
            raise ValueError("A-share account costs must round to CNY cents")
        if account_cost_scenario_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("account cost scenario fingerprint differs")
        return self


class ChinaAshareExecutionCostBreakdownV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    session_date: date
    exchange: ChinaAshareExchange
    side: ChinaAshareTradeSide
    gross_notional_cny: Decimal
    broker_commission_cny: Decimal
    securities_regulatory_fee_cny: Decimal
    exchange_handling_fee_cny: Decimal
    transfer_fee_cny: Decimal
    stamp_duty_cny: Decimal
    slippage_cny: Decimal
    total_cost_cny: Decimal
    commission_basis: ChinaAshareCommissionBasis
    applied_fee_rule_ids: tuple[str, ...] = Field(min_length=3)
    scenario_fingerprint: str

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must contain a date")
        return value

    @field_validator(
        "gross_notional_cny",
        "broker_commission_cny",
        "securities_regulatory_fee_cny",
        "exchange_handling_fee_cny",
        "transfer_fee_cny",
        "stamp_duty_cny",
        "slippage_cny",
        "total_cost_cny",
        mode="before",
    )
    @classmethod
    def amounts_are_exact(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "gross_notional_cny",
        "broker_commission_cny",
        "securities_regulatory_fee_cny",
        "exchange_handling_fee_cny",
        "transfer_fee_cny",
        "stamp_duty_cny",
        "slippage_cny",
        "total_cost_cny",
    )
    @classmethod
    def amounts_are_nonnegative(cls, value: Decimal, info: Any) -> Decimal:
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return value

    @field_validator("applied_fee_rule_ids", mode="before")
    @classmethod
    def rule_ids_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_texts(value, field_name="applied_fee_rule_ids")

    @field_validator("scenario_fingerprint")
    @classmethod
    def scenario_hash_is_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("scenario_fingerprint must be a SHA-256 value")
        return value

    @model_validator(mode="after")
    def amounts_reconcile(self) -> "ChinaAshareExecutionCostBreakdownV1":
        expected = sum(
            (
                self.broker_commission_cny,
                self.securities_regulatory_fee_cny,
                self.exchange_handling_fee_cny,
                self.transfer_fee_cny,
                self.stamp_duty_cny,
                self.slippage_cny,
            ),
            Decimal("0"),
        )
        if self.total_cost_cny != expected:
            raise ValueError("execution cost components do not reconcile")
        if self.side is ChinaAshareTradeSide.BUY and self.stamp_duty_cny != 0:
            raise ValueError("buy-side A-share cost cannot contain stamp duty")
        if self.commission_basis is ChinaAshareCommissionBasis.ALL_IN and any(
            value != 0
            for value in (
                self.securities_regulatory_fee_cny,
                self.exchange_handling_fee_cny,
            )
        ):
            raise ValueError("all-in commission must not duplicate embedded regulatory fees")
        return self


class ChinaAsharePilotPriceLimitDecisionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    method_version: Literal["china-ashare-market-mechanics/1.0"] = (
        MARKET_MECHANICS_METHOD_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    session_date: date
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    trading_status: ChinaAshareTradingStatus
    risk_warning_status: ChinaAshareRiskWarningStatus
    price_limit_regime: ChinaAsharePriceLimitRegime
    rule_id: str
    pre_close: Decimal
    theoretical_up_limit: Decimal
    theoretical_down_limit: Decimal
    bar_high: Decimal | None = None
    bar_low: Decimal | None = None
    observed_bar_within_limits: bool | None = None
    price_tick_cny: Decimal = Decimal("0.01")
    calculation_method: Literal["previous_close_ratio_half_up_to_tick"] = (
        "previous_close_ratio_half_up_to_tick"
    )
    exact_limit_prices_source_observed: Literal[False] = False
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must contain a date")
        return value

    @field_validator("rule_id", mode="before")
    @classmethod
    def rule_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="rule_id")

    @field_validator(
        "pre_close",
        "theoretical_up_limit",
        "theoretical_down_limit",
        "bar_high",
        "bar_low",
        "price_tick_cny",
        mode="before",
    )
    @classmethod
    def prices_are_exact(cls, value: Any, info: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "pre_close",
        "theoretical_up_limit",
        "theoretical_down_limit",
        "bar_high",
        "bar_low",
        "price_tick_cny",
    )
    @classmethod
    def prices_are_positive(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_reasons(value)

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ChinaAsharePilotPriceLimitDecisionV1":
        if self.theoretical_up_limit <= self.theoretical_down_limit:
            raise ValueError("theoretical price limits are reversed")
        has_bar = self.bar_high is not None or self.bar_low is not None
        if has_bar != (self.bar_high is not None and self.bar_low is not None):
            raise ValueError("bar bounds must be both present or both absent")
        if has_bar != (self.observed_bar_within_limits is not None):
            raise ValueError("bar limit result must follow bar presence")
        if self.observed_bar_within_limits is not None:
            assert self.bar_high is not None and self.bar_low is not None
            expected = (
                self.bar_high <= self.theoretical_up_limit
                and self.bar_low >= self.theoretical_down_limit
            )
            if self.observed_bar_within_limits is not expected:
                raise ValueError("observed bar limit result differs")
        if self.price_tick_cny != Decimal("0.01"):
            raise ValueError("pilot price-limit decisions require the CNY 0.01 tick")
        return self


class ChinaAshareMarketMechanicsReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    method_version: Literal["china-ashare-market-mechanics/1.0"] = (
        MARKET_MECHANICS_METHOD_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    daily_package_fingerprint: str
    calendar_package_fingerprint: str
    evaluated_at: datetime
    target_session_count: int = Field(ge=1)
    source_reference_count: int = Field(ge=1)
    trading_rule_count: int = Field(ge=1)
    fee_rule_count: int = Field(ge=1)
    price_limit_decision_count: int = Field(ge=1)
    price_limit_bar_count: int = Field(ge=1)
    suspended_decision_count: int = Field(ge=0)
    price_limit_violation_count: int = Field(ge=0)
    unresolved_rule_count: int = Field(ge=0)
    effective_dated_rules_reconciled: bool
    effective_dated_fees_reconciled: bool
    account_cost_scenario_registered: bool
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator("daily_package_fingerprint", "calendar_package_fingerprint", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError(f"{info.field_name} must be a SHA-256 value")
        return value

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_reasons(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareMarketMechanicsReportV1":
        expected_rules = self.price_limit_violation_count == 0 and self.unresolved_rule_count == 0
        if self.effective_dated_rules_reconciled is not expected_rules:
            raise ValueError("trading-rule reconciliation status differs")
        if market_mechanics_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("market mechanics report fingerprint differs")
        return self


class ChinaAshareMarketMechanicsManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal["china-ashare-market-mechanics-package/1.0"] = (
        MARKET_MECHANICS_PACKAGE_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    daily_package_fingerprint: str
    calendar_package_fingerprint: str
    report_fingerprint: str
    account_cost_scenario_fingerprint: str
    created_at: datetime
    artifacts: tuple[ChinaAshareMarketMechanicsArtifactV1, ...] = Field(min_length=7)
    raw_source_payloads_retained: Literal[True] = True
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "daily_package_fingerprint",
        "calendar_package_fingerprint",
        "report_fingerprint",
        "account_cost_scenario_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def manifest_hashes_are_sha256(cls, value: str, info: Any) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError(f"{info.field_name} must be a SHA-256 value")
        return value

    @field_validator("created_at")
    @classmethod
    def created_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareMarketMechanicsManifestV1":
        keys = tuple((item.relative_path, item.artifact_id) for item in self.artifacts)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("market mechanics artifacts must be unique and ordered")
        kinds = {item.artifact_kind for item in self.artifacts}
        required = set(ChinaAshareMarketMechanicsArtifactKind)
        if not required.issubset(kinds):
            raise ValueError("market mechanics artifact family is incomplete")
        if market_mechanics_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("market mechanics manifest fingerprint differs")
        return self


def build_account_cost_scenario(**values: Any) -> ChinaAshareAccountCostScenarioV1:
    provisional = ChinaAshareAccountCostScenarioV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareAccountCostScenarioV1.model_validate(
        {**values, "logical_fingerprint": account_cost_scenario_fingerprint(provisional)}
    )


def build_market_mechanics_report(**values: Any) -> ChinaAshareMarketMechanicsReportV1:
    provisional = ChinaAshareMarketMechanicsReportV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareMarketMechanicsReportV1.model_validate(
        {
            **values,
            "logical_fingerprint": market_mechanics_report_fingerprint(provisional),
        }
    )


def build_market_mechanics_manifest(
    **values: Any,
) -> ChinaAshareMarketMechanicsManifestV1:
    provisional = ChinaAshareMarketMechanicsManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareMarketMechanicsManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": market_mechanics_manifest_fingerprint(provisional),
        }
    )


def account_cost_scenario_fingerprint(
    value: ChinaAshareAccountCostScenarioV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def market_mechanics_report_fingerprint(
    value: ChinaAshareMarketMechanicsReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def market_mechanics_manifest_fingerprint(
    value: ChinaAshareMarketMechanicsManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _canonical_texts(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be an ordered collection")
    normalized = tuple(sorted({normalize_required_string(item, field_name=field_name) for item in value}))
    if len(normalized) != len(value):
        raise ValueError(f"{field_name} must be unique and ordered")
    return normalized


def _canonical_reasons(value: Any) -> tuple[str, ...]:
    normalized = _canonical_texts(value, field_name="reason_codes")
    if any(not _REASON_CODE.fullmatch(item) for item in normalized):
        raise ValueError("reason_codes must contain lower snake-case values")
    return normalized
