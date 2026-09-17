"""Owner-only immutable custody for A-share market-mechanics evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAccountCostScenarioV1,
    ChinaAshareFeeRuleV1,
    ChinaAshareMarketMechanicsArtifactKind,
    ChinaAshareMarketMechanicsArtifactV1,
    ChinaAshareMarketMechanicsManifestV1,
    ChinaAshareMarketMechanicsReportV1,
    ChinaAshareOfficialSourceReferenceV1,
    ChinaAsharePilotPriceLimitDecisionV1,
    ChinaAshareTradingRuleV1,
    build_market_mechanics_manifest,
)
from tip_api.providers.china_ashare.official_market_mechanics_adapter import (
    CapturedOfficialMarketMechanicsSourceV1,
)


SOURCE_REFERENCES_FILE = "normalized/source-references.json"
TRADING_RULES_FILE = "normalized/trading-rules.json"
FEE_RULES_FILE = "normalized/fee-rules.json"
ACCOUNT_COST_SCENARIO_FILE = "normalized/account-cost-scenario.json"
PRICE_LIMIT_DECISIONS_FILE = "normalized/price-limit-decisions.json"
REPORT_FILE = "reports/market-mechanics-report.json"
MANIFEST_FILE = "market-mechanics-manifest.json"
MAXIMUM_ARTIFACT_BYTES = 64 * 1024 * 1024


class ChinaAshareMarketMechanicsPackageError(RuntimeError):
    """Base failure for market-mechanics evidence custody."""


class ChinaAshareMarketMechanicsPackageConflictError(
    ChinaAshareMarketMechanicsPackageError
):
    """Raised when immutable package scope or content conflicts."""


class ChinaAshareMarketMechanicsPackageCorruptionError(
    ChinaAshareMarketMechanicsPackageError
):
    """Raised when exact reread detects changed or malformed custody."""


@dataclass(frozen=True, slots=True)
class ChinaAshareMarketMechanicsPackageResultV1:
    manifest: ChinaAshareMarketMechanicsManifestV1
    source_references: tuple[ChinaAshareOfficialSourceReferenceV1, ...]
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...]
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...]
    account_cost_scenario: ChinaAshareAccountCostScenarioV1
    price_limit_decisions: tuple[ChinaAsharePilotPriceLimitDecisionV1, ...]
    report: ChinaAshareMarketMechanicsReportV1
    captured_sources: tuple[CapturedOfficialMarketMechanicsSourceV1, ...]
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_market_mechanics_package(
    *,
    custody_root: Path,
    captured_sources: tuple[CapturedOfficialMarketMechanicsSourceV1, ...],
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...],
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    account_cost_scenario: ChinaAshareAccountCostScenarioV1,
    price_limit_decisions: tuple[ChinaAsharePilotPriceLimitDecisionV1, ...],
    report: ChinaAshareMarketMechanicsReportV1,
) -> ChinaAshareMarketMechanicsPackageResultV1:
    """Persist exact public bytes and typed mechanics evidence without activation."""

    root = _validate_custody_root(custody_root)
    sources = tuple(sorted(captured_sources, key=lambda item: item.reference.source_id))
    rules = tuple(sorted(trading_rules, key=lambda item: item.rule_id))
    fees = tuple(sorted(fee_rules, key=lambda item: item.fee_rule_id))
    decisions = tuple(
        sorted(
            price_limit_decisions,
            key=lambda item: (str(item.instrument_id), item.session_date),
        )
    )
    _validate_inputs(
        captured_sources=sources,
        trading_rules=rules,
        fee_rules=fees,
        account_cost_scenario=account_cost_scenario,
        price_limit_decisions=decisions,
        report=report,
    )
    source_references = tuple(item.reference for item in sources)
    normalized_payloads = (
        (
            ChinaAshareMarketMechanicsArtifactKind.SOURCE_REFERENCES,
            "source-references",
            SOURCE_REFERENCES_FILE,
            _rows_bytes(source_references),
            len(source_references),
        ),
        (
            ChinaAshareMarketMechanicsArtifactKind.TRADING_RULES,
            "trading-rules",
            TRADING_RULES_FILE,
            _rows_bytes(rules),
            len(rules),
        ),
        (
            ChinaAshareMarketMechanicsArtifactKind.FEE_RULES,
            "fee-rules",
            FEE_RULES_FILE,
            _rows_bytes(fees),
            len(fees),
        ),
        (
            ChinaAshareMarketMechanicsArtifactKind.ACCOUNT_COST_SCENARIO,
            "account-cost-scenario",
            ACCOUNT_COST_SCENARIO_FILE,
            _canonical_json_bytes(account_cost_scenario.model_dump(mode="json")),
            1,
        ),
        (
            ChinaAshareMarketMechanicsArtifactKind.PRICE_LIMIT_DECISIONS,
            "price-limit-decisions",
            PRICE_LIMIT_DECISIONS_FILE,
            _rows_bytes(decisions),
            len(decisions),
        ),
        (
            ChinaAshareMarketMechanicsArtifactKind.REPORT,
            "market-mechanics-report",
            REPORT_FILE,
            _canonical_json_bytes(report.model_dump(mode="json")),
            1,
        ),
    )
    raw_payloads = tuple(
        (
            ChinaAshareMarketMechanicsArtifactKind.RAW_SOURCE,
            item.reference.source_id,
            _raw_relative_path(item.reference),
            item.raw_bytes,
            1,
        )
        for item in sources
    )
    payloads = tuple(
        sorted((*normalized_payloads, *raw_payloads), key=lambda item: (item[2], item[1]))
    )
    artifacts = tuple(
        ChinaAshareMarketMechanicsArtifactV1(
            artifact_kind=kind,
            artifact_id=artifact_id,
            relative_path=relative_path,
            byte_size=len(payload),
            physical_sha256=_sha256(payload),
            row_count=row_count,
        )
        for kind, artifact_id, relative_path, payload, row_count in payloads
    )
    manifest = build_market_mechanics_manifest(
        daily_package_fingerprint=report.daily_package_fingerprint,
        calendar_package_fingerprint=report.calendar_package_fingerprint,
        report_fingerprint=report.logical_fingerprint,
        account_cost_scenario_fingerprint=account_cost_scenario.logical_fingerprint,
        created_at=report.evaluated_at,
        artifacts=artifacts,
        raw_source_payloads_retained=True,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    daily_directory = root / f"mechanics-daily={report.daily_package_fingerprint}"
    target = daily_directory / f"mechanics-package={manifest.logical_fingerprint}"
    daily_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if daily_directory.is_symlink() or not daily_directory.is_dir():
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics daily directory is invalid"
        )
    daily_directory.chmod(0o700)
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_market_mechanics_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAshareMarketMechanicsPackageConflictError(
                "existing immutable market mechanics package differs"
            )
        return existing

    temporary = Path(tempfile.mkdtemp(prefix=".mechanics-package-", dir=daily_directory))
    try:
        for artifact, (_, _, _, payload, _) in zip(artifacts, payloads, strict=True):
            destination = temporary / artifact.relative_path
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _write_file(destination, payload)
        _write_file(temporary / MANIFEST_FILE, manifest_bytes)
        _make_directories_owner_only(temporary)
        _fsync_tree(temporary)
        temporary.rename(target)
        _fsync_directory(daily_directory)
    except BaseException:
        if temporary.exists() and not temporary.is_symlink():
            shutil.rmtree(temporary)
        raise
    return read_china_ashare_market_mechanics_package(package_path=target)


def read_china_ashare_market_mechanics_package(
    *, package_path: Path
) -> ChinaAshareMarketMechanicsPackageResultV1:
    package = _validate_package_path(package_path)
    manifest_payload = _read_regular_file(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareMarketMechanicsManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics manifest is invalid"
        ) from exc
    if package.name != f"mechanics-package={manifest.logical_fingerprint}":
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics package path identity differs"
        )
    if package.parent.name != (
        f"mechanics-daily={manifest.daily_package_fingerprint}"
    ):
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics daily path identity differs"
        )

    decoded: dict[ChinaAshareMarketMechanicsArtifactKind, Any] = {}
    captured_raw: dict[str, bytes] = {}
    expected_files = {Path(MANIFEST_FILE)}
    for artifact in manifest.artifacts:
        relative = Path(artifact.relative_path)
        expected_files.add(relative)
        payload = _read_regular_file(package / relative)
        if len(payload) != artifact.byte_size or _sha256(payload) != artifact.physical_sha256:
            raise ChinaAshareMarketMechanicsPackageCorruptionError(
                "market mechanics artifact bytes differ"
            )
        if artifact.artifact_kind is ChinaAshareMarketMechanicsArtifactKind.RAW_SOURCE:
            captured_raw[artifact.artifact_id] = payload
        else:
            decoded[artifact.artifact_kind] = payload

    try:
        source_references = _decode_rows(
            decoded[ChinaAshareMarketMechanicsArtifactKind.SOURCE_REFERENCES],
            ChinaAshareOfficialSourceReferenceV1,
        )
        trading_rules = _decode_rows(
            decoded[ChinaAshareMarketMechanicsArtifactKind.TRADING_RULES],
            ChinaAshareTradingRuleV1,
        )
        fee_rules = _decode_rows(
            decoded[ChinaAshareMarketMechanicsArtifactKind.FEE_RULES],
            ChinaAshareFeeRuleV1,
        )
        account_cost_scenario = ChinaAshareAccountCostScenarioV1.model_validate_json(
            decoded[ChinaAshareMarketMechanicsArtifactKind.ACCOUNT_COST_SCENARIO]
        )
        price_limit_decisions = _decode_rows(
            decoded[ChinaAshareMarketMechanicsArtifactKind.PRICE_LIMIT_DECISIONS],
            ChinaAsharePilotPriceLimitDecisionV1,
        )
        report = ChinaAshareMarketMechanicsReportV1.model_validate_json(
            decoded[ChinaAshareMarketMechanicsArtifactKind.REPORT]
        )
    except (KeyError, ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics normalized document is invalid"
        ) from exc
    artifact_by_kind = {
        item.artifact_kind: item
        for item in manifest.artifacts
        if item.artifact_kind is not ChinaAshareMarketMechanicsArtifactKind.RAW_SOURCE
    }
    for kind, rows in (
        (ChinaAshareMarketMechanicsArtifactKind.SOURCE_REFERENCES, source_references),
        (ChinaAshareMarketMechanicsArtifactKind.TRADING_RULES, trading_rules),
        (ChinaAshareMarketMechanicsArtifactKind.FEE_RULES, fee_rules),
        (ChinaAshareMarketMechanicsArtifactKind.PRICE_LIMIT_DECISIONS, price_limit_decisions),
    ):
        if artifact_by_kind[kind].row_count != len(rows):
            raise ChinaAshareMarketMechanicsPackageCorruptionError(
                "market mechanics artifact row count differs"
            )
    captured_sources = tuple(
        CapturedOfficialMarketMechanicsSourceV1(
            reference=reference,
            raw_bytes=captured_raw[reference.source_id],
        )
        for reference in source_references
    )
    _validate_inputs(
        captured_sources=captured_sources,
        trading_rules=trading_rules,
        fee_rules=fee_rules,
        account_cost_scenario=account_cost_scenario,
        price_limit_decisions=price_limit_decisions,
        report=report,
    )
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics report binding differs"
        )
    if account_cost_scenario.logical_fingerprint != (
        manifest.account_cost_scenario_fingerprint
    ):
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics cost scenario binding differs"
        )

    actual_files = {
        item.relative_to(package)
        for item in package.rglob("*")
        if item.is_file() and not item.is_symlink()
    }
    if actual_files != expected_files:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics package file set differs"
        )
    for item in package.rglob("*"):
        if item.is_symlink():
            raise ChinaAshareMarketMechanicsPackageCorruptionError(
                "market mechanics package contains a symlink"
            )
        if item.is_file() and item.stat().st_mode & 0o777 != 0o400:
            raise ChinaAshareMarketMechanicsPackageCorruptionError(
                "market mechanics file mode differs"
            )
        if item.is_dir() and item.stat().st_mode & 0o777 != 0o700:
            raise ChinaAshareMarketMechanicsPackageCorruptionError(
                "market mechanics directory mode differs"
            )
    if package.stat().st_mode & 0o777 != 0o700:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics package mode differs"
        )
    total_bytes = sum((package / item).stat().st_size for item in expected_files)
    return ChinaAshareMarketMechanicsPackageResultV1(
        manifest=manifest,
        source_references=source_references,
        trading_rules=trading_rules,
        fee_rules=fee_rules,
        account_cost_scenario=account_cost_scenario,
        price_limit_decisions=price_limit_decisions,
        report=report,
        captured_sources=captured_sources,
        package_path=package,
        manifest_path=package / MANIFEST_FILE,
        manifest_physical_sha256=_sha256(manifest_payload),
        file_count=len(expected_files),
        total_bytes=total_bytes,
        status="exact_reread_complete",
    )


def _validate_inputs(
    *,
    captured_sources: tuple[CapturedOfficialMarketMechanicsSourceV1, ...],
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...],
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    account_cost_scenario: ChinaAshareAccountCostScenarioV1,
    price_limit_decisions: tuple[ChinaAsharePilotPriceLimitDecisionV1, ...],
    report: ChinaAshareMarketMechanicsReportV1,
) -> None:
    source_ids = tuple(item.reference.source_id for item in captured_sources)
    if source_ids != tuple(sorted(set(source_ids))):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "captured market mechanics sources must be unique and ordered"
        )
    for item in captured_sources:
        if item.reference.raw_sha256 != _sha256(item.raw_bytes):
            raise ChinaAshareMarketMechanicsPackageConflictError(
                "captured market mechanics bytes differ from source metadata"
            )
        if item.reference.raw_byte_size != len(item.raw_bytes):
            raise ChinaAshareMarketMechanicsPackageConflictError(
                "captured market mechanics byte size differs"
            )
    if any(item.source_id not in source_ids for item in fee_rules):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "fee rule references an uncaptured official source"
        )
    source_urls = {item.reference.source_url for item in captured_sources}
    if any(item.official_source_url not in source_urls for item in trading_rules):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "trading rule references an uncaptured official source"
        )
    if report.source_reference_count != len(captured_sources):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics source count differs from report"
        )
    if report.trading_rule_count != len(trading_rules):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics trading-rule count differs from report"
        )
    if report.fee_rule_count != len(fee_rules):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics fee-rule count differs from report"
        )
    if report.price_limit_decision_count != len(price_limit_decisions):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics decision count differs from report"
        )
    if report.research_backtest_authorized or report.canonical_apply_authorized:
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics package cannot carry activation authority"
        )
    if account_cost_scenario.market_id != report.market_id:
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics cost scenario market differs"
        )


def _raw_relative_path(reference: ChinaAshareOfficialSourceReferenceV1) -> str:
    suffix = ".pdf" if reference.content_type == "application/pdf" else ".html"
    return f"raw/{reference.source_id}{suffix}"


def _rows_bytes(rows: tuple[Any, ...]) -> bytes:
    return _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in rows],
        }
    )


def _decode_rows(payload: bytes, contract: Any) -> tuple[Any, ...]:
    document = json.loads(payload)
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "1.0"
        or not isinstance(document.get("rows"), list)
    ):
        raise ValueError("market mechanics row document shape differs")
    return tuple(contract.model_validate(item) for item in document["rows"])


def _validate_custody_root(path: Path) -> Path:
    root = path.absolute()
    if root.name != "china-a-share-research-pilot" or Path("/tmp") not in root.parents:
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics custody must use the dedicated pilot path below /tmp"
        )
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics custody root is invalid"
        )
    if not root.parent.is_dir() or root.parent.is_symlink():
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics custody parent is invalid"
        )
    root.mkdir(mode=0o700, exist_ok=True)
    root.chmod(0o700)
    return root


def _validate_package_path(path: Path) -> Path:
    package = path.absolute()
    if (
        Path("/tmp") not in package.parents
        or not package.name.startswith("mechanics-package=")
        or not package.parent.name.startswith("mechanics-daily=")
        or package.parent.parent.name != "china-a-share-research-pilot"
        or not package.is_dir()
        or package.is_symlink()
    ):
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics package path is invalid"
        )
    return package


def _read_regular_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics artifact is invalid"
        )
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_ARTIFACT_BYTES:
        raise ChinaAshareMarketMechanicsPackageCorruptionError(
            "market mechanics artifact size is invalid"
        )
    return path.read_bytes()


def _canonical_json_bytes(value: Any) -> bytes:
    payload = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    if len(payload) > MAXIMUM_ARTIFACT_BYTES:
        raise ChinaAshareMarketMechanicsPackageConflictError(
            "market mechanics JSON exceeds its byte ceiling"
        )
    return payload


def _write_file(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o400)


def _make_directories_owner_only(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o700)
    root.chmod(0o700)


def _fsync_tree(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        _fsync_directory(path)
    _fsync_directory(root)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
