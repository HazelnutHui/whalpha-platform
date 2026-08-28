"""Source-bound product projection for the audited strategy-channel preview."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelBatchV1,
    CandidateStrategyChannelConsumerV1,
    CandidateStrategyChannelProductV1,
    OpportunityCandidatePublicationV1_1,
    STRATEGY_CHANNEL_PRODUCT_CONTRACT_VERSION,
    strategy_product_logical_fingerprint,
)
from tip_api.services.candidate_strategy_channel_audit import (
    STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION,
    STRATEGY_CHANNEL_AUDIT_MANIFEST,
    read_candidate_strategy_channel_audit,
)


class CandidateStrategyChannelProductError(RuntimeError):
    """Raised when an audited strategy preview cannot bind to Candidate product data."""


def build_candidate_strategy_channel_product(
    *,
    strategy_audit_dir: Path,
    candidate_analytics: OpportunityCandidatePublicationV1_1,
) -> CandidateStrategyChannelProductV1:
    """Project bounded consumers without exposing full deprioritized populations."""

    manifest = read_candidate_strategy_channel_audit(strategy_audit_dir)
    batches = tuple(
        CandidateStrategyChannelBatchV1.model_validate(item)
        for item in _read_records(
            strategy_audit_dir / "strategy-channel-batches.json"
        )
    )
    consumers = tuple(
        CandidateStrategyChannelConsumerV1.model_validate(item)
        for item in _read_records(
            strategy_audit_dir / "strategy-channel-consumers.json"
        )
    )
    if len(batches) != 2 or len(consumers) != 2:
        raise CandidateStrategyChannelProductError(
            "strategy product requires exactly two Universe batches and consumers"
        )
    universe_order = tuple(item.universe_id for item in batches)
    if (
        candidate_analytics.as_of_session != batches[0].as_of_session
        or candidate_analytics.universe_order != universe_order
        or tuple(item.universe_id for item in consumers) != universe_order
    ):
        raise CandidateStrategyChannelProductError(
            "strategy product Candidate session or Universe order differs"
        )
    candidate_batch_fingerprints = tuple(
        item.source_candidate_batch_fingerprint for item in batches
    )
    entry_batch_fingerprints = tuple(
        item.source_entry_geometry_batch_fingerprint for item in batches
    )
    if (
        candidate_batch_fingerprints
        != candidate_analytics.source.current_candidate_batch_fingerprints
        or candidate_batch_fingerprints
        != tuple(
            item.candidate_batch_logical_fingerprint
            for item in candidate_analytics.universes
        )
        or entry_batch_fingerprints
        != candidate_analytics.source.entry_geometry_batch_fingerprints
    ):
        raise CandidateStrategyChannelProductError(
            "strategy product Candidate or Entry Geometry batch binding differs"
        )
    source = manifest.get("source", {})
    candidate_source = source.get("candidate_audit", {})
    entry_source = source.get("entry_geometry_audit", {})
    if (
        candidate_source.get("logical_content_fingerprint")
        != candidate_analytics.source.candidate_audit_logical_fingerprint
        or entry_source.get("logical_content_fingerprint")
        != candidate_analytics.source.entry_geometry_audit_logical_fingerprint
    ):
        raise CandidateStrategyChannelProductError(
            "strategy product formal audit lineage differs from Candidate publication"
        )
    batch_fingerprints = tuple(item.logical_fingerprint for item in batches)
    consumer_fingerprints = tuple(item.logical_fingerprint for item in consumers)
    if (
        batch_fingerprints != tuple(manifest.get("batch_fingerprints", ()))
        or consumer_fingerprints
        != tuple(manifest.get("consumer_fingerprints", ()))
    ):
        raise CandidateStrategyChannelProductError(
            "strategy product batch or consumer manifest binding differs"
        )

    manifest_path = strategy_audit_dir / STRATEGY_CHANNEL_AUDIT_MANIFEST
    product = {
        "schema_version": "1.0",
        "contract_version": STRATEGY_CHANNEL_PRODUCT_CONTRACT_VERSION,
        "as_of_session": candidate_analytics.as_of_session.isoformat(),
        "default_universe_id": candidate_analytics.default_universe_id,
        "universe_order": list(universe_order),
        "channel_order": list(consumers[0].channel_order),
        "source": {
            "strategy_audit_manifest_sha256": hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
            "strategy_audit_logical_fingerprint": manifest[
                "logical_content_fingerprint"
            ],
            "strategy_audit_contract_version": STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION,
            "strategy_contract_version": manifest["contract_version"],
            "strategy_consumer_contract_version": manifest[
                "consumer_contract_version"
            ],
            "strategy_parameter_fingerprint": manifest["parameter_fingerprint"],
            "strategy_oracle_mismatch_count": manifest["oracle_mismatch_count"],
            "strategy_input_permutation_match": manifest[
                "input_permutation_match"
            ],
            "strategy_oracle_production_calculator_imported": manifest[
                "production_calculator_imported_by_oracle"
            ],
            "external_request_count": manifest["external_request_count"],
            "production_write_count": manifest["production_write_count"],
            "candidate_publication_contract_version": candidate_analytics.contract_version,
            "candidate_analytics_logical_fingerprint": (
                candidate_analytics.logical_fingerprint
            ),
            "candidate_audit_logical_fingerprint": (
                candidate_analytics.source.candidate_audit_logical_fingerprint
            ),
            "entry_geometry_audit_logical_fingerprint": (
                candidate_analytics.source.entry_geometry_audit_logical_fingerprint
            ),
            "source_candidate_batch_fingerprints": list(
                candidate_batch_fingerprints
            ),
            "source_entry_geometry_batch_fingerprints": list(
                entry_batch_fingerprints
            ),
            "strategy_batch_fingerprints": list(batch_fingerprints),
            "strategy_consumer_fingerprints": list(consumer_fingerprints),
        },
        "universes": [item.model_dump(mode="json") for item in consumers],
        "language_neutral": True,
        "research_priority_only": True,
        "fixed_baseline_not_chronologically_validated": True,
        "cross_channel_score_comparison_prohibited": True,
        "market_fit_separate_and_unvalidated": True,
        "event_context_auxiliary": True,
        "underlying_stock_result_not_option_return": True,
        "price_volume_not_fund_flow": True,
        "guest_and_credential_capability_identical": True,
        "warnings": (
            "fixed_baseline_not_chronologically_validated",
            "channel_score_not_probability_expected_return_or_recommendation",
            "cross_channel_score_comparison_prohibited",
            "market_fit_not_yet_calibrated",
            "technical_fundamental_and_defensive_channels_may_be_unavailable",
            "underlying_stock_result_not_option_return",
            "price_volume_not_fund_flow",
        ),
    }
    product["logical_fingerprint"] = strategy_product_logical_fingerprint(product)
    return CandidateStrategyChannelProductV1.model_validate(product)


def _read_records(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise CandidateStrategyChannelProductError(
            "strategy product source artifact is unsafe"
        )
    try:
        payload = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateStrategyChannelProductError(
            "strategy product source artifact is malformed"
        ) from exc
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not all(
        isinstance(item, dict) for item in records
    ):
        raise CandidateStrategyChannelProductError(
            "strategy product source records are malformed"
        )
    return records
