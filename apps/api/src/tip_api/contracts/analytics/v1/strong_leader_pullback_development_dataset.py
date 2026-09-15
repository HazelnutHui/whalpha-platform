"""Contracts for the owner-only reconstructed development dataset."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .candidate_strategy_evaluation import StrategyEvaluationSplit
from .candidate_strategy_research import STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_VERSION,
)


DEVELOPMENT_DATASET_CONTRACT_VERSION = (
    "strong-leader-pullback-reconstructed-development-dataset/1.0"
)
DEVELOPMENT_LABEL_CONTRACT_VERSION = (
    "strong-leader-pullback-reconstructed-development-label/1.0"
)
TERMINAL_REFERENCE_LEDGER_VERSION = (
    "strong-leader-pullback-terminal-reference-ledger/1.0"
)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_DECIMAL_PATTERN = r"^-?(?:0|[1-9][0-9]*)\.[0-9]{10}$"


class ReconstructedDevelopmentLabelState(StrEnum):
    OBSERVED_EOD_EXACT = "observed_eod_exact"
    TERMINAL_REFERENCE_EXACT = "terminal_reference_exact"
    TERMINAL_REFERENCE_INTERVAL = "terminal_reference_interval"
    UNEXECUTABLE_NO_NEXT_OPEN = "unexecutable_no_next_open"
    UNAVAILABLE_EVIDENCE = "unavailable_evidence"


class TerminalReferenceLedgerState(StrEnum):
    EXACT = "exact"
    FINITE_INTERVAL = "finite_interval"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackTerminalReferenceLedgerEntryV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-ledger/1.0"
    ] = TERMINAL_REFERENCE_LEDGER_VERSION
    instrument_id: UUID
    ticker_locator: str = Field(pattern=r"^[A-Z][A-Z0-9.]{0,14}$")
    last_observed_eod_session: date
    first_absent_exchange_session: date
    state: TerminalReferenceLedgerState
    lower_reference_value_usd: str = Field(pattern=_DECIMAL_PATTERN)
    upper_reference_value_usd: str = Field(pattern=_DECIMAL_PATTERN)
    evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    point_imputation_used: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def entry_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceLedgerEntryV1":
        lower = _decimal(self.lower_reference_value_usd, "terminal lower reference")
        upper = _decimal(self.upper_reference_value_usd, "terminal upper reference")
        exact = self.state is TerminalReferenceLedgerState.EXACT
        if (
            self.first_absent_exchange_session <= self.last_observed_eod_session
            or lower < 0
            or lower > upper
            or exact != (lower == upper)
            or (not exact and lower != Decimal("0"))
            or development_dataset_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("terminal-reference ledger entry differs")
        return self


class StrongLeaderPullbackReconstructedDevelopmentLabelV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-reconstructed-development-label/1.0"
    ] = DEVELOPMENT_LABEL_CONTRACT_VERSION
    experiment_fingerprint: Literal[
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    ] = STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    method_version: Literal[STRONG_LEADER_PULLBACK_METHOD_VERSION] = (
        STRONG_LEADER_PULLBACK_METHOD_VERSION
    )
    method_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )
    observation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    signal_session: date
    evaluation_split: Literal[StrategyEvaluationSplit.DEVELOPMENT] = (
        StrategyEvaluationSplit.DEVELOPMENT
    )
    instrument_id: UUID
    ticker_locator: str = Field(pattern=r"^[A-Z][A-Z0-9.]{0,14}$")
    horizon_sessions: Literal[1, 3, 5]
    expected_entry_session: date
    expected_exit_session: date
    expected_path_sessions: tuple[date, ...] = Field(min_length=1, max_length=5)
    split_basis_session: date
    state: ReconstructedDevelopmentLabelState
    entry_price_usd: str | None = Field(default=None, pattern=_DECIMAL_PATTERN)
    exit_price_lower_usd: str | None = Field(default=None, pattern=_DECIMAL_PATTERN)
    exit_price_upper_usd: str | None = Field(default=None, pattern=_DECIMAL_PATTERN)
    underlying_price_return_lower: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    underlying_price_return_upper: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    benchmark_price_return: str | None = Field(default=None, pattern=_DECIMAL_PATTERN)
    relative_to_benchmark_return_lower: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    relative_to_benchmark_return_upper: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    maximum_favorable_excursion: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    maximum_adverse_excursion: str | None = Field(
        default=None, pattern=_DECIMAL_PATTERN
    )
    source_eod_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_adjustment_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    terminal_reference_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    reason_codes: tuple[str, ...]
    reconstructed_latest_vintage: Literal[True] = True
    as_operated: Literal[False] = False
    underlying_stock_result_not_option_return: Literal[True] = True
    transaction_costs_not_applied: Literal[True] = True
    point_imputation_used: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_unique_and_sorted(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("development label reasons must be unique and sorted")
        return values

    @model_validator(mode="after")
    def label_reconciles(
        self,
    ) -> "StrongLeaderPullbackReconstructedDevelopmentLabelV1":
        if (
            len(self.expected_path_sessions) != self.horizon_sessions
            or self.expected_path_sessions
            != tuple(sorted(set(self.expected_path_sessions)))
            or self.expected_path_sessions[0] != self.expected_entry_session
            or self.expected_path_sessions[-1] != self.expected_exit_session
            or not self.signal_session
            < self.expected_entry_session
            <= self.expected_exit_session
            or self.split_basis_session < self.expected_exit_session
        ):
            raise ValueError("development label sessions differ")
        numeric = (
            self.entry_price_usd,
            self.exit_price_lower_usd,
            self.exit_price_upper_usd,
            self.underlying_price_return_lower,
            self.underlying_price_return_upper,
            self.benchmark_price_return,
            self.relative_to_benchmark_return_lower,
            self.relative_to_benchmark_return_upper,
        )
        nonnumeric = self.state in {
            ReconstructedDevelopmentLabelState.UNEXECUTABLE_NO_NEXT_OPEN,
            ReconstructedDevelopmentLabelState.UNAVAILABLE_EVIDENCE,
        }
        if nonnumeric:
            if (
                any(value is not None for value in numeric)
                or self.maximum_favorable_excursion is not None
                or self.maximum_adverse_excursion is not None
                or not self.reason_codes
            ):
                raise ValueError("non-numeric label carries numeric outcome")
            if (
                self.state
                is ReconstructedDevelopmentLabelState.UNEXECUTABLE_NO_NEXT_OPEN
                and (
                    self.terminal_reference_fingerprint is None
                    or self.reason_codes != ("no_executable_next_session_open",)
                )
            ):
                raise ValueError("unexecutable label evidence differs")
        else:
            if any(value is None for value in numeric):
                raise ValueError("numeric development label is incomplete")
            entry = _decimal(self.entry_price_usd, "entry price")
            lower_exit = _decimal(self.exit_price_lower_usd, "lower exit price")
            upper_exit = _decimal(self.exit_price_upper_usd, "upper exit price")
            lower_return = _decimal(
                self.underlying_price_return_lower, "lower underlying return"
            )
            upper_return = _decimal(
                self.underlying_price_return_upper, "upper underlying return"
            )
            benchmark = _decimal(self.benchmark_price_return, "benchmark return")
            lower_relative = _decimal(
                self.relative_to_benchmark_return_lower, "lower relative return"
            )
            upper_relative = _decimal(
                self.relative_to_benchmark_return_upper, "upper relative return"
            )
            if (
                entry <= 0
                or lower_exit < 0
                or lower_exit > upper_exit
                or lower_return != _return(lower_exit, entry)
                or upper_return != _return(upper_exit, entry)
                or lower_relative != _quantize(lower_return - benchmark)
                or upper_relative != _quantize(upper_return - benchmark)
            ):
                raise ValueError("development label return arithmetic differs")
            interval = (
                self.state
                is ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL
            )
            terminal = self.state in {
                ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_EXACT,
                ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL,
            }
            if interval != (lower_exit < upper_exit):
                raise ValueError("development label interval state differs")
            if terminal != (self.terminal_reference_fingerprint is not None):
                raise ValueError("development label terminal binding differs")
            excursions = (
                self.maximum_favorable_excursion,
                self.maximum_adverse_excursion,
            )
            if all(value is not None for value in excursions):
                favorable = _decimal(excursions[0], "maximum favorable excursion")
                adverse = _decimal(excursions[1], "maximum adverse excursion")
                if favorable < 0 or adverse > 0 or self.reason_codes:
                    raise ValueError("development label excursion evidence differs")
            elif any(value is not None for value in excursions) or not self.reason_codes:
                raise ValueError("unavailable excursions require one explicit reason")
        if development_dataset_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("development label fingerprint differs")
        return self


class StrongLeaderPullbackReconstructedDevelopmentManifestV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-reconstructed-development-dataset/1.0"
    ] = DEVELOPMENT_DATASET_CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: datetime
    admission_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    admission_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    diagnostics_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    diagnostics_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    chronological_plan_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_eod_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_adjustment_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    terminal_reference_ledger_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    terminal_reference_entries: tuple[
        StrongLeaderPullbackTerminalReferenceLedgerEntryV1, ...
    ] = Field(min_length=1)
    split_basis_session: date
    first_development_signal_session: date
    last_development_signal_session: date
    development_signal_session_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)
    label_count: int = Field(ge=3)
    label_state_counts: dict[str, int]
    horizon_label_counts: dict[str, int]
    observation_file: Literal["observations.parquet"] = "observations.parquet"
    observation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    observation_parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    observation_parquet_bytes: int = Field(ge=1)
    label_file: Literal["labels.parquet"] = "labels.parquet"
    label_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    label_parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    label_parquet_bytes: int = Field(ge=1)
    reconstructed_latest_vintage: Literal[True] = True
    as_operated: Literal[False] = False
    development_only: Literal[True] = True
    validation_observation_count: Literal[0] = 0
    validation_label_count: Literal[0] = 0
    holdout_observation_count: Literal[0] = 0
    holdout_label_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    performance_claim_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    network_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "StrongLeaderPullbackReconstructedDevelopmentManifestV1":
        expected_states = tuple(
            item.value for item in ReconstructedDevelopmentLabelState
        )
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.first_development_signal_session
            > self.last_development_signal_session
            or self.label_count != self.observation_count * 3
            or tuple(sorted(self.label_state_counts)) != tuple(sorted(expected_states))
            or sum(self.label_state_counts.values()) != self.label_count
            or self.horizon_label_counts
            != {
                "1": self.observation_count,
                "3": self.observation_count,
                "5": self.observation_count,
            }
            or tuple(
                (item.ticker_locator, str(item.instrument_id))
                for item in self.terminal_reference_entries
            )
            != tuple(
                sorted(
                    {
                        (item.ticker_locator, str(item.instrument_id))
                        for item in self.terminal_reference_entries
                    }
                )
            )
            or self.terminal_reference_ledger_fingerprint
            != development_dataset_fingerprint(
                {
                    "entries": [
                        item.model_dump(mode="json")
                        for item in self.terminal_reference_entries
                    ]
                },
                exclude=set(),
            )
            or development_dataset_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("reconstructed development manifest differs")
        return self


def development_dataset_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(
            mode="json", exclude=exclude or {"logical_fingerprint"}
        )
    else:
        payload = dict(value)
        for key in exclude or {"logical_fingerprint"}:
            payload.pop(key, None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _decimal(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a decimal") from exc
    if not parsed.is_finite() or value != format(_quantize(parsed), "f"):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0000000001"))


def _return(exit_price: Decimal, entry_price: Decimal) -> Decimal:
    return _quantize(exit_price / entry_price - Decimal("1"))
