"""Language-neutral product projection for Candidate strategy channels."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.parameters.market_regime.candidate_strategy_preview_v1_0_0 import (
    STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
    STRATEGY_CHANNEL_CONTRACT_VERSION,
    STRATEGY_CHANNEL_ORDER,
    STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
)

from .candidate_strategy_channel import CandidateStrategyChannelConsumerV1


STRATEGY_CHANNEL_PRODUCT_CONTRACT_VERSION = "candidate-strategy-channel-product/1.0"
STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION = "candidate-strategy-channel-audit/1.0"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CandidateStrategyChannelProductSourceV1(FrozenModel):
    strategy_audit_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    strategy_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    strategy_audit_contract_version: Literal[
        STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION
    ] = STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION
    strategy_contract_version: Literal[STRATEGY_CHANNEL_CONTRACT_VERSION] = (
        STRATEGY_CHANNEL_CONTRACT_VERSION
    )
    strategy_consumer_contract_version: Literal[
        STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION
    ] = STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION
    strategy_parameter_fingerprint: Literal[STRATEGY_CHANNEL_PARAMETER_FINGERPRINT] = (
        STRATEGY_CHANNEL_PARAMETER_FINGERPRINT
    )
    strategy_oracle_mismatch_count: Literal[0] = 0
    strategy_input_permutation_match: Literal[True] = True
    strategy_oracle_production_calculator_imported: Literal[False] = False
    external_request_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    candidate_publication_contract_version: Literal[
        "opportunity-candidate-publication/1.1"
    ]
    candidate_analytics_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_geometry_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_candidate_batch_fingerprints: tuple[str, str]
    source_entry_geometry_batch_fingerprints: tuple[str, str]
    strategy_batch_fingerprints: tuple[str, str]
    strategy_consumer_fingerprints: tuple[str, str]

    @model_validator(mode="after")
    def digests_are_valid(self) -> "CandidateStrategyChannelProductSourceV1":
        values = (
            *self.source_candidate_batch_fingerprints,
            *self.source_entry_geometry_batch_fingerprints,
            *self.strategy_batch_fingerprints,
            *self.strategy_consumer_fingerprints,
        )
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            for value in values
        ):
            raise ValueError("strategy product source fingerprints must be SHA-256 digests")
        return self


class CandidateStrategyChannelProductV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_CHANNEL_PRODUCT_CONTRACT_VERSION] = (
        STRATEGY_CHANNEL_PRODUCT_CONTRACT_VERSION
    )
    as_of_session: date
    default_universe_id: str
    universe_order: tuple[str, str]
    channel_order: tuple[str, str, str, str, str, str] = STRATEGY_CHANNEL_ORDER
    source: CandidateStrategyChannelProductSourceV1
    universes: tuple[
        CandidateStrategyChannelConsumerV1,
        CandidateStrategyChannelConsumerV1,
    ]
    language_neutral: Literal[True] = True
    research_priority_only: Literal[True] = True
    fixed_baseline_not_chronologically_validated: Literal[True] = True
    cross_channel_score_comparison_prohibited: Literal[True] = True
    market_fit_separate_and_unvalidated: Literal[True] = True
    event_context_auxiliary: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    price_volume_not_fund_flow: Literal[True] = True
    guest_and_credential_capability_identical: Literal[True] = True
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def product_reconciles(self) -> "CandidateStrategyChannelProductV1":
        if self.default_universe_id != self.universe_order[0]:
            raise ValueError("strategy product default Universe differs")
        if tuple(item.value for item in self.universes[0].channel_order) != self.channel_order:
            raise ValueError("strategy product channel order differs")
        if tuple(item.universe_id for item in self.universes) != self.universe_order:
            raise ValueError("strategy product Universe order differs")
        if any(item.as_of_session != self.as_of_session for item in self.universes):
            raise ValueError("strategy product session differs")
        if tuple(item.source_batch_logical_fingerprint for item in self.universes) != (
            self.source.strategy_batch_fingerprints
        ):
            raise ValueError("strategy product consumer batch binding differs")
        if tuple(item.logical_fingerprint for item in self.universes) != (
            self.source.strategy_consumer_fingerprints
        ):
            raise ValueError("strategy product consumer fingerprints differ")
        if strategy_product_logical_fingerprint(
            self, exclude={"logical_fingerprint"}
        ) != self.logical_fingerprint:
            raise ValueError("strategy product logical fingerprint mismatch")
        return self


def strategy_product_logical_fingerprint(
    value: BaseModel | dict[str, object], *, exclude: set[str] | None = None
) -> str:
    payload = (
        value.model_dump(mode="json", exclude=exclude or set())
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key not in (exclude or set())}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
