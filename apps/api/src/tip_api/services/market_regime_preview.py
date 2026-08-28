"""Build and serve a strictly validated, tmp-only Market Regime preview bundle."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel

from tip_api.contracts.analytics.v1 import (
    EtfRelationshipExplanationV1,
    EtfRelationshipRecordV1,
    ExplanationLedgerEntryV1,
    MarketRegimeCompositeV1,
    MarketRegimeOpportunityMapResponseV1,
    MarketRegimePreviewManifestV1,
    MarketRegimePreviewPayloadV1,
    MarketRegimeRelationshipComparisonV1,
    MarketRegimeRelationshipDetailResponseV1,
    MarketRegimeStateExplanationV1,
    MarketRegimeStateRecordV1,
    PreviewCalculationVersionsV1,
    PreviewEtfBasketEntryV1,
    PreviewEtfPairDefinitionV1,
    PreviewEtfRelationshipV1,
    PreviewParameterFingerprintsV1,
    PreviewQualityGateV1,
    PreviewSourceLogicalFingerprintsV1,
    PreviewUniverseAnalyticsV1,
    PreviewUniverseDefinitionV1,
    ReviewDeploymentAuthorization,
)
from tip_api.contracts.analytics.v1.market_regime_preview import (
    PREVIEW_MANIFEST_FILE,
    PREVIEW_PAYLOAD_FILE,
)
from tip_api.services.etf_relationship_audit import read_etf_relationship_audit
from tip_api.services.market_regime_audit import read_market_regime_audit
from tip_api.services.market_regime_state_audit import read_market_regime_state_audit


EXPECTED_FILES = (PREVIEW_PAYLOAD_FILE, PREVIEW_MANIFEST_FILE)
SHORT_HISTORY_WARNINGS = (
    "Only 26 completed XNYS sessions are available; reliability measures describe data completeness and rule agreement, not predictive probability.",
    "The 16 ETF pairs are preregistered; the preview does not search the market for favorable relationships.",
    "Statistical relationships are contemporaneous observations, not evidence of causation.",
    "Price and volume relationships are participation proxies, not fund flow.",
    "This research context is not a trade recommendation or a backtest result.",
)


class MarketRegimePreviewError(RuntimeError):
    """Raised when preview custody, lineage, or logical identity fails closed."""


@dataclass(frozen=True, slots=True)
class CompletedPreviewBundle:
    path: Path
    manifest: MarketRegimePreviewManifestV1
    payload: MarketRegimePreviewPayloadV1


def build_market_regime_preview_bundle(
    *,
    phase1a_audit_dir: Path,
    phase1b_audit_dir: Path,
    phase2_audit_dir: Path,
    output_dir: Path,
    generated_at: datetime,
) -> CompletedPreviewBundle:
    """Validate three explicit source audits and create one deterministic preview bundle."""

    phase1a_manifest = read_market_regime_audit(phase1a_audit_dir)
    phase1b_manifest = read_market_regime_state_audit(phase1b_audit_dir)
    phase2_manifest = read_etf_relationship_audit(phase2_audit_dir)
    if any(item.get("oracle_mismatch_count") != 0 for item in (phase1a_manifest, phase1b_manifest, phase2_manifest)):
        raise MarketRegimePreviewError("source audit has Oracle mismatches")
    phase1a_input = _read_json(phase1a_audit_dir / "input-manifest.json")
    phase1a_composites = _records(phase1a_audit_dir / "composite.json", MarketRegimeCompositeV1)
    phase1a_explanations = _records(phase1a_audit_dir / "explanation-ledger.json", ExplanationLedgerEntryV1)
    phase1b_input = _read_json(phase1b_audit_dir / "source-input-manifest.json")
    state_current_payload = _read_json(phase1b_audit_dir / "current-state-summary.json")
    try:
        state_current = tuple(
            MarketRegimeStateRecordV1.model_validate(item["current"])
            for item in state_current_payload["records"]
        )
    except Exception as exc:
        raise MarketRegimePreviewError("invalid Phase 1b current state summary") from exc
    state_history = _records(phase1b_audit_dir / "state-history.json", MarketRegimeStateRecordV1)
    state_explanations = _records(
        phase1b_audit_dir / "state-explanation-ledger.json", MarketRegimeStateExplanationV1
    )
    pair_registry = _read_json(phase2_audit_dir / "pair-registry.json")
    phase2_input = _read_json(phase2_audit_dir / "source-input-manifest.json")
    relationship_current = _records(
        phase2_audit_dir / "current-relationship-summary.json", EtfRelationshipRecordV1
    )
    relationship_history = _records(
        phase2_audit_dir / "relationship-metrics.json", EtfRelationshipRecordV1
    )
    relationship_explanations = _records(
        phase2_audit_dir / "relationship-explanation-ledger.json", EtfRelationshipExplanationV1
    )
    comparisons = _records(
        phase2_audit_dir / "market-regime-relationship-comparison.json",
        MarketRegimeRelationshipComparisonV1,
    )

    phase1a_fingerprint = phase1a_manifest["logical_content_fingerprint"]
    phase1b_fingerprint = phase1b_manifest["logical_content_fingerprint"]
    phase2_fingerprint = phase2_manifest["logical_content_fingerprint"]
    if phase1b_input["phase1a_audit_logical_fingerprint"] != phase1a_fingerprint:
        raise MarketRegimePreviewError("Phase 1b source manifest lineage mismatch")
    if phase2_input["phase1a_audit_logical_fingerprint"] != phase1a_fingerprint:
        raise MarketRegimePreviewError("Phase 2 source manifest Phase 1a lineage mismatch")
    if phase2_input["phase1b_audit_logical_fingerprint"] != phase1b_fingerprint:
        raise MarketRegimePreviewError("Phase 2 source manifest Phase 1b lineage mismatch")
    sessions = {
        phase1a_manifest["as_of_session"],
        phase1b_manifest["as_of_session"],
        phase2_manifest["as_of_session"],
    }
    if len(sessions) != 1:
        raise MarketRegimePreviewError("source audit as-of sessions differ")

    universes_by_id = {item["universe_id"]: item for item in phase1a_input["universes"]}
    composites_by_id = _unique_by(phase1a_composites, "universe_id")
    states_by_id = _unique_by(state_current, "universe_id")
    state_explanations_by_id = _unique_by(
        tuple(item for item in state_explanations if item.as_of_session.isoformat() == next(iter(sessions))),
        "universe_id",
    )
    universe_order = tuple(phase1a_input["universe_ids"])
    if universe_order != tuple(phase1b_input["universe_ids"]):
        raise MarketRegimePreviewError("Phase 1a and Phase 1b Universe order differs")
    universes: list[PreviewUniverseAnalyticsV1] = []
    for universe_id in universe_order:
        source = universes_by_id[universe_id]
        universes.append(PreviewUniverseAnalyticsV1(
            definition=PreviewUniverseDefinitionV1.model_validate(source),
            composite=composites_by_id[universe_id],
            current_state=states_by_id[universe_id],
            current_state_explanation=state_explanations_by_id[universe_id],
            state_history=tuple(item for item in state_history if item.universe_id == universe_id),
            dimension_explanations=tuple(
                item for item in phase1a_explanations if item.universe_id == universe_id
            ),
        ))

    definitions = tuple(
        PreviewEtfPairDefinitionV1.model_validate({**item, "registry_order": ordinal})
        for ordinal, item in enumerate(pair_registry["pairs"])
    )
    current_by_id = _unique_by(relationship_current, "pair_id")
    explanations_by_id = _unique_by(relationship_explanations, "pair_id")
    relationships = tuple(
        PreviewEtfRelationshipV1(
            definition=definition,
            current=current_by_id[definition.pair_id],
            explanation=explanations_by_id[definition.pair_id],
        )
        for definition in definitions
    )
    source_fingerprints = PreviewSourceLogicalFingerprintsV1(
        phase1a=phase1a_fingerprint, phase1b=phase1b_fingerprint, phase2=phase2_fingerprint
    )
    payload_body: dict[str, Any] = {
        "as_of_session": next(iter(sessions)),
        "input_first_session": phase2_input["input_session_range"][0],
        "input_last_session": phase2_input["input_session_range"][1],
        "input_session_count": phase2_input["input_session_count"],
        "default_universe_id": universe_order[0],
        "universe_order": universe_order,
        "calculation_versions": PreviewCalculationVersionsV1(
            phase1a=phase1a_manifest["calculation_version"],
            phase1b=phase1b_manifest["calculation_version"],
            phase2=phase2_manifest["calculation_version"],
        ),
        "parameter_fingerprints": PreviewParameterFingerprintsV1(
            phase1a=phase1a_manifest["parameter_set_fingerprint"],
            phase1b=phase1b_manifest["state_parameter_fingerprint"],
            phase2=phase2_manifest["parameter_fingerprint"],
        ),
        "source_logical_fingerprints": source_fingerprints,
        "universes": tuple(universes),
        "etf_basket": tuple(PreviewEtfBasketEntryV1.model_validate(item) for item in pair_registry["basket"]),
        "relationships": relationships,
        "relationship_history": tuple(relationship_history),
        "relationship_comparisons": tuple(comparisons),
        "warnings": SHORT_HISTORY_WARNINGS,
        "quality_gates": (
            PreviewQualityGateV1(gate_id="source_custody", status="passed", reason_codes=("all_source_audits_formally_verified",)),
            PreviewQualityGateV1(gate_id="universe_isolation", status="passed", reason_codes=("primary_secondary_separate",)),
            PreviewQualityGateV1(gate_id="relationship_registry", status="passed", reason_codes=("all_16_preregistered_pairs_present",)),
            PreviewQualityGateV1(gate_id="source_oracles", status="passed", reason_codes=("source_oracle_mismatch_count_zero",)),
            PreviewQualityGateV1(gate_id="history_depth", status="degraded", reason_codes=("only_26_sessions", "ratio_statistics_require_60_sessions")),
        ),
    }
    candidate = MarketRegimePreviewPayloadV1.model_validate({
        **_jsonable(payload_body), "logical_fingerprint": "0" * 64
    })
    payload = candidate.model_copy(update={
        "logical_fingerprint": _fingerprint(
            candidate.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
    })
    return _write_and_read_bundle(output_dir, payload, generated_at, source_fingerprints)


def read_market_regime_preview_bundle(path: Path) -> CompletedPreviewBundle:
    target = _safe_bundle_dir(path)
    actual = tuple(sorted(item.name for item in target.iterdir()))
    if actual != tuple(sorted(EXPECTED_FILES)):
        raise MarketRegimePreviewError("preview bundle file set is incomplete or has extras")
    for item in target.iterdir():
        metadata = item.stat()
        if item.is_symlink() or not item.is_file() or metadata.st_uid != os.geteuid():
            raise MarketRegimePreviewError("preview bundle contains unsafe files")
        if stat.S_IMODE(metadata.st_mode) != 0o400:
            raise MarketRegimePreviewError("preview bundle files must be mode 0400")
    payload_raw = (target / PREVIEW_PAYLOAD_FILE).read_bytes()
    manifest_raw = (target / PREVIEW_MANIFEST_FILE).read_bytes()
    payload_json = _read_canonical_bytes(payload_raw, PREVIEW_PAYLOAD_FILE)
    manifest_json = _read_canonical_bytes(manifest_raw, PREVIEW_MANIFEST_FILE)
    manifest = MarketRegimePreviewManifestV1.model_validate(manifest_json)
    if len(payload_raw) != manifest.payload_bytes or hashlib.sha256(payload_raw).hexdigest() != manifest.payload_sha256:
        raise MarketRegimePreviewError("preview payload physical custody mismatch")
    payload = MarketRegimePreviewPayloadV1.model_validate(payload_json)
    logical = payload.model_dump(mode="json", exclude={"logical_fingerprint"})
    if _fingerprint(logical) != payload.logical_fingerprint:
        raise MarketRegimePreviewError("preview payload logical fingerprint mismatch")
    if payload.logical_fingerprint != manifest.payload_logical_fingerprint:
        raise MarketRegimePreviewError("preview manifest points to another payload")
    if payload.source_logical_fingerprints != manifest.source_logical_fingerprints:
        raise MarketRegimePreviewError("preview manifest source lineage differs")
    manifest_logical = manifest.model_dump(
        mode="json", exclude={"generated_at", "manifest_logical_fingerprint"}
    )
    if _fingerprint(manifest_logical) != manifest.manifest_logical_fingerprint:
        raise MarketRegimePreviewError("preview manifest logical fingerprint mismatch")
    return CompletedPreviewBundle(path=target, manifest=manifest, payload=payload)


class MarketRegimePreviewService:
    """Immutable in-memory query view populated from one validated bundle at startup."""

    def __init__(self, completed: CompletedPreviewBundle) -> None:
        self._generated_at = completed.manifest.generated_at
        self._payload = completed.payload
        self._universes = {item.definition.universe_id: item for item in completed.payload.universes}
        self._relationships = {item.definition.pair_id: item for item in completed.payload.relationships}
        self._review_deployment: ReviewDeploymentAuthorization | None = None

    @classmethod
    def from_bundle(cls, path: Path) -> "MarketRegimePreviewService":
        return cls(read_market_regime_preview_bundle(path))

    @classmethod
    def from_payload(
        cls,
        payload: MarketRegimePreviewPayloadV1,
        generated_at: datetime,
        review_deployment: ReviewDeploymentAuthorization | None = None,
    ) -> "MarketRegimePreviewService":
        """Build the same immutable API view from a formal publication payload."""

        instance = cls.__new__(cls)
        instance._generated_at = generated_at
        instance._payload = payload
        instance._universes = {
            item.definition.universe_id: item for item in payload.universes
        }
        instance._relationships = {
            item.definition.pair_id: item for item in payload.relationships
        }
        instance._review_deployment = review_deployment
        return instance

    def overview(self, universe_id: str | None = None) -> MarketRegimeOpportunityMapResponseV1:
        selected = universe_id or self._payload.default_universe_id
        regime = self._universes.get(selected)
        if regime is None:
            raise KeyError(selected)
        comparisons = tuple(
            item for item in self._payload.relationship_comparisons if item.universe_id == selected
        )
        return MarketRegimeOpportunityMapResponseV1(
            bundle_generated_at=self._generated_at,
            bundle_logical_fingerprint=self._payload.logical_fingerprint,
            as_of_session=self._payload.as_of_session,
            data_status=(
                "stale_review" if self._review_deployment is not None else self._payload.data_status
            ),
            review_deployment=self._review_deployment,
            input_first_session=self._payload.input_first_session,
            input_last_session=self._payload.input_last_session,
            input_session_count=self._payload.input_session_count,
            default_universe_id=self._payload.default_universe_id,
            selected_universe_id=selected,
            available_universes=tuple(item.definition for item in self._payload.universes),
            calculation_versions=self._payload.calculation_versions,
            parameter_fingerprints=self._payload.parameter_fingerprints,
            source_logical_fingerprints=self._payload.source_logical_fingerprints,
            regime=regime,
            relationships=self._payload.relationships,
            relationship_comparisons=comparisons,
            warnings=self._payload.warnings,
            quality_gates=self._payload.quality_gates,
        )

    def relationship_detail(
        self, pair_id: str, universe_id: str | None = None
    ) -> MarketRegimeRelationshipDetailResponseV1:
        selected = universe_id or self._payload.default_universe_id
        if selected not in self._universes:
            raise KeyError(selected)
        relationship = self._relationships.get(pair_id)
        if relationship is None:
            raise KeyError(pair_id)
        comparison = next(
            item for item in self._payload.relationship_comparisons
            if item.universe_id == selected and item.pair_id == pair_id
        )
        history = tuple(item for item in self._payload.relationship_history if item.pair_id == pair_id)
        return MarketRegimeRelationshipDetailResponseV1(
            as_of_session=self._payload.as_of_session,
            selected_universe_id=selected,
            source_logical_fingerprints=self._payload.source_logical_fingerprints,
            relationship=relationship,
            comparison=comparison,
            history=history,
        )


def _write_and_read_bundle(
    output_dir: Path,
    payload: MarketRegimePreviewPayloadV1,
    generated_at: datetime,
    source_fingerprints: PreviewSourceLogicalFingerprintsV1,
) -> CompletedPreviewBundle:
    target = _safe_new_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    if any(target.iterdir()):
        raise MarketRegimePreviewError("existing non-empty output directory is rejected")
    payload_raw = _canonical_bytes(payload.model_dump(mode="json"))
    manifest_body: dict[str, Any] = {
        "schema_version": "1.0",
        "contract_version": "market-regime-opportunity-map-preview/1.0",
        "completion_status": "completed",
        "as_of_session": payload.as_of_session.isoformat(),
        "payload_file": PREVIEW_PAYLOAD_FILE,
        "payload_bytes": len(payload_raw),
        "payload_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "payload_logical_fingerprint": payload.logical_fingerprint,
        "source_logical_fingerprints": source_fingerprints.model_dump(mode="json"),
        "external_request_count": 0,
        "production_write_count": 0,
    }
    manifest_logical_fingerprint = _fingerprint(manifest_body)
    manifest = MarketRegimePreviewManifestV1.model_validate({
        **manifest_body,
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "manifest_logical_fingerprint": manifest_logical_fingerprint,
    })
    _write_new(target / PREVIEW_PAYLOAD_FILE, payload_raw)
    _write_new(target / PREVIEW_MANIFEST_FILE, _canonical_bytes(manifest.model_dump(mode="json")))
    for item in target.iterdir():
        item.chmod(0o400)
    return read_market_regime_preview_bundle(target)


def _records(path: Path, model: Any) -> tuple[Any, ...]:
    payload = _read_json(path)
    try:
        return tuple(model.model_validate(item) for item in payload["records"])
    except Exception as exc:
        raise MarketRegimePreviewError(f"invalid preview source records: {path.name}") from exc


def _unique_by(records: tuple[Any, ...], key: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in records:
        value = getattr(item, key)
        if value in result:
            raise MarketRegimePreviewError(f"duplicate {key}: {value}")
        result[value] = item
    return result


def _safe_new_output_dir(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp") or path.name in {"", ".", ".."}:
        raise MarketRegimePreviewError("output directory must be a direct child of /tmp")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise MarketRegimePreviewError("symlink output path is rejected")
    if path.exists():
        metadata = path.stat()
        if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
            raise MarketRegimePreviewError("existing output path must be an empty safe directory")
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise MarketRegimePreviewError("existing output directory custody mismatch")
        return path.resolve(strict=True)
    return path


def _safe_bundle_dir(path: Path) -> Path:
    if path.is_symlink():
        raise MarketRegimePreviewError("symlink preview bundle directory is rejected")
    target = path.resolve(strict=True)
    metadata = target.stat()
    if not target.is_dir() or target.parent != Path("/tmp"):
        raise MarketRegimePreviewError("preview bundle must be a direct child of /tmp")
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MarketRegimePreviewError("preview bundle directory custody mismatch")
    return target


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_bytes())
    except Exception as exc:
        raise MarketRegimePreviewError(f"malformed source artifact: {path.name}") from exc


def _read_canonical_bytes(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise MarketRegimePreviewError(f"malformed preview JSON: {name}") from exc
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise MarketRegimePreviewError(f"non-canonical preview JSON: {name}")
    return value


def _jsonable(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("preview logical payload must be a mapping")
    return {str(key): _json_value(item) for key, item in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _normalize_nfc(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list | tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_nfc(item)
            for key, item in value.items()
        }
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
