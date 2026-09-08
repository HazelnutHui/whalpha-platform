"""Build a split-action candidate directly from canonical source custody."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python
from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionType,
    ResolutionStatus,
)
from tip_api.services.corporate_action_source_canonical import (
    CanonicalCorporateActionSourceError,
    read_canonical_corporate_action_source,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    HistoricalCorporateActionResolutionShadowError,
    read_historical_ticker_candidates_bound_to_identity_evidence,
)
from tip_api.services.historical_split_adjustment_candidate import (
    FrozenModel,
    SplitAdjustmentEventCandidateV1,
    UnresolvedSplitImpactCandidateV1,
    build_split_event_candidates,
    build_unresolved_split_impacts,
)


CONTRACT_VERSION = "canonical-source-split-action-candidate/1.0"
METHODOLOGY_VERSION = "canonical-source-resolved-event-ratio-v1"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
FILE_NAME = "candidate.json"
MAXIMUM_JSON_BYTES = 16 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SPLIT_TYPES = frozenset(
    {
        CorporateActionType.STOCK_SPLIT,
        CorporateActionType.REVERSE_SPLIT,
        CorporateActionType.STOCK_DIVIDEND,
    }
)


class CanonicalSplitActionCandidateError(RuntimeError):
    """Raised when a canonical-source split candidate cannot be trusted."""


class CanonicalSourceSplitEventCandidateV1(SplitAdjustmentEventCandidateV1):
    """One grouped event candidate with an explicit ledger-admission gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    ledger_admission_status: Literal["clear_candidate", "quarantined"]

    @model_validator(mode="after")
    def admission_reconciles(self) -> "CanonicalSourceSplitEventCandidateV1":
        expected = (
            "quarantined" if len(self.source_actions) > 1 else "clear_candidate"
        )
        if self.ledger_admission_status != expected:
            raise ValueError("split event ledger-admission status differs")
        return self


class CanonicalSourceSplitActionCandidateV1(FrozenModel):
    """Small, non-canonical candidate derived from one formal source marker."""

    contract_version: Literal[
        "canonical-source-split-action-candidate/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    methodology_version: Literal[
        "canonical-source-resolved-event-ratio-v1"
    ] = METHODOLOGY_VERSION
    implementation_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    source_publication_path: str
    source_publication_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_publication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_evidence_path: str
    identity_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_evidence_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_session_count: int = Field(ge=1)
    start_date: date
    basis_session: date
    source_data_cutoff: datetime
    calculated_at: datetime
    split_source_record_count: int = Field(ge=1)
    resolved_active_split_source_record_count: int = Field(ge=0)
    quarantined_split_source_record_count: int = Field(ge=0)
    resolved_event_group_count: int = Field(ge=0)
    clear_event_group_count: int = Field(ge=0)
    quarantined_event_group_count: int = Field(ge=0)
    unresolved_with_historical_identity_count: int = Field(ge=0)
    unresolved_without_historical_identity_count: int = Field(ge=0)
    unresolved_with_ambiguous_historical_identity_count: int = Field(ge=0)
    possible_impact_instrument_count: int = Field(ge=0)
    resolved_events: tuple[CanonicalSourceSplitEventCandidateV1, ...]
    possible_unresolved_impacts: tuple[UnresolvedSplitImpactCandidateV1, ...]
    quarantined_source_action_set_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    factor_direction: Literal["multiply_raw_value_to_basis"] = (
        "multiply_raw_value_to_basis"
    )
    event_inclusion_rule: Literal["source_session_lt_event_lte_basis"] = (
        "source_session_lt_event_lte_basis"
    )
    provider_cumulative_factor_usage: Literal["audit_only"] = "audit_only"
    source_coverage_status: Literal["bounded_query_snapshot_only"] = (
        "bounded_query_snapshot_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    canonical_action_publication_status: Literal["not_built"] = "not_built"
    adjustment_ledger_projection_status: Literal["not_built"] = "not_built"
    total_return_adjustment_status: Literal["unavailable"] = "unavailable"
    latest_ticker_fallback_count: Literal[0] = 0
    nearest_session_fallback_count: Literal[0] = 0
    unresolved_action_assignment_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_publication_path", "identity_evidence_path")
    @classmethod
    def paths_are_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or not value.endswith("/manifest.json")
        ):
            raise ValueError("split candidate evidence path is invalid")
        return value

    @field_validator("source_data_cutoff", "calculated_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def candidate_reconciles(self) -> "CanonicalSourceSplitActionCandidateV1":
        if self.basis_session < self.start_date:
            raise ValueError("split candidate basis precedes start")
        if self.source_data_cutoff > self.calculated_at:
            raise ValueError("split candidate calculation precedes source cutoff")
        if self.split_source_record_count != (
            self.resolved_active_split_source_record_count
            + self.quarantined_split_source_record_count
        ):
            raise ValueError("split candidate source counts differ")
        expected_events = tuple(
            sorted(
                self.resolved_events,
                key=lambda item: (str(item.instrument_id), item.effective_date),
            )
        )
        expected_impacts = tuple(
            sorted(
                self.possible_unresolved_impacts,
                key=lambda item: str(item.instrument_id),
            )
        )
        event_keys = tuple(
            (item.instrument_id, item.effective_date) for item in self.resolved_events
        )
        action_keys = tuple(
            (action.source_action_id, action.source_revision)
            for event in self.resolved_events
            for action in event.source_actions
        )
        if (
            self.resolved_events != expected_events
            or self.possible_unresolved_impacts != expected_impacts
            or len(event_keys) != len(set(event_keys))
            or len(action_keys) != len(set(action_keys))
            or any(
                not (self.start_date <= item.effective_date <= self.basis_session)
                for item in self.resolved_events
            )
        ):
            raise ValueError("split candidate records are not ordered")
        if (
            self.resolved_event_group_count != len(self.resolved_events)
            or self.resolved_active_split_source_record_count
            != sum(len(item.source_actions) for item in self.resolved_events)
            or self.clear_event_group_count
            != sum(
                item.ledger_admission_status == "clear_candidate"
                for item in self.resolved_events
            )
            or self.quarantined_event_group_count
            != sum(
                item.ledger_admission_status == "quarantined"
                for item in self.resolved_events
            )
            or self.clear_event_group_count + self.quarantined_event_group_count
            != self.resolved_event_group_count
            or self.possible_impact_instrument_count
            != len(self.possible_unresolved_impacts)
            or self.unresolved_with_historical_identity_count
            + self.unresolved_without_historical_identity_count
            != self.quarantined_split_source_record_count
            or self.unresolved_with_ambiguous_historical_identity_count
            > self.unresolved_with_historical_identity_count
        ):
            raise ValueError("split candidate aggregate counts differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("split candidate logical fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class CanonicalSourceSplitActionCandidateResult:
    output_root: Path
    candidate: CanonicalSourceSplitActionCandidateV1
    file_sha256: str
    status: Literal["published", "already_present"]


def build_canonical_source_split_action_candidate(
    *,
    data_root: Path,
    source_publication_path: Path,
    output_root: Path,
    basis_session: date,
    calculated_at: datetime,
    implementation_revision: str,
) -> CanonicalSourceSplitActionCandidateResult:
    """Build a disconnected candidate from formally published source rows."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        target = _validated_output_target(output_root)
        calculated_at = normalize_utc_datetime(calculated_at)
        try:
            source = read_canonical_corporate_action_source(
                data_root=root,
                publication_path=source_publication_path,
            )
        except CanonicalCorporateActionSourceError as exc:
            raise CanonicalSplitActionCandidateError(
                "canonical corporate-action source failed formal reread"
            ) from exc
        publication = source.publication
        if basis_session != publication.end_date:
            raise CanonicalSplitActionCandidateError(
                "split candidate basis must equal the source-publication range end"
            )
        if calculated_at < publication.created_at:
            raise CanonicalSplitActionCandidateError(
                "split candidate calculation precedes source publication"
            )
        split_records = tuple(
            item for item in source.records if item.action_type in _SPLIT_TYPES
        )
        admitted = tuple(
            item
            for item in split_records
            if item.instrument_resolution_status is ResolutionStatus.RESOLVED
            and item.record_status is CorporateActionRecordStatus.ACTIVE
        )
        non_admitted = tuple(item for item in split_records if item not in admitted)
        if any(
            item.instrument_resolution_status is ResolutionStatus.RESOLVED
            or item.instrument_id is not None
            for item in non_admitted
        ):
            raise CanonicalSplitActionCandidateError(
                "non-active or inconsistent resolved split requires a new rule"
            )
        legacy_events = build_split_event_candidates(admitted, basis_session)
        events = tuple(
            CanonicalSourceSplitEventCandidateV1.model_validate(
                {
                    **item.model_dump(mode="json"),
                    "ledger_admission_status": (
                        "quarantined"
                        if len(item.source_actions) > 1
                        else "clear_candidate"
                    ),
                }
            )
            for item in legacy_events
        )
        requested_tickers = frozenset(
            item.provider_ticker for item in non_admitted
        )
        try:
            historical_candidates = (
                read_historical_ticker_candidates_bound_to_identity_evidence(
                    data_root=root,
                    identity_evidence_path=root
                    / PurePosixPath(publication.identity_evidence_path),
                    identity_evidence_sha256=publication.identity_evidence_sha256,
                    identity_evidence_logical_fingerprint=(
                        publication.identity_evidence_logical_fingerprint
                    ),
                    identity_session_count=publication.identity_session_count,
                    first_session=publication.start_date,
                    last_session=publication.end_date,
                    provider_tickers=requested_tickers,
                )
                if requested_tickers
                else {}
            )
        except HistoricalCorporateActionResolutionShadowError as exc:
            raise CanonicalSplitActionCandidateError(
                "historical unresolved-impact scan failed"
            ) from exc
        impacts, with_history, without_history, ambiguous = (
            build_unresolved_split_impacts(non_admitted, historical_candidates)
        )
        quarantine_fingerprint = _fingerprint(
            tuple(
                {
                    "source_action_id": item.source_action_id,
                    "source_revision": item.source_revision,
                    "provider_ticker": item.provider_ticker,
                    "effective_date": item.effective_date.isoformat(),
                    "action_type": item.action_type.value,
                    "split_ratio_from": str(item.split_ratio_from),
                    "split_ratio_to": str(item.split_ratio_to),
                    "quality_flags": item.quality_flags,
                }
                for item in sorted(
                    non_admitted,
                    key=lambda item: (item.source_action_id, item.source_revision),
                )
            )
        )
        values = {
            "contract_version": CONTRACT_VERSION,
            "completion_status": "completed",
            "methodology_version": METHODOLOGY_VERSION,
            "implementation_revision": implementation_revision,
            "source_publication_path": source.publication_path.relative_to(root).as_posix(),
            "source_publication_sha256": source.publication_sha256,
            "source_publication_logical_fingerprint": publication.logical_fingerprint,
            "identity_evidence_path": publication.identity_evidence_path,
            "identity_evidence_sha256": publication.identity_evidence_sha256,
            "identity_evidence_logical_fingerprint": (
                publication.identity_evidence_logical_fingerprint
            ),
            "identity_session_count": publication.identity_session_count,
            "start_date": publication.start_date,
            "basis_session": basis_session,
            "source_data_cutoff": publication.created_at,
            "calculated_at": calculated_at,
            "split_source_record_count": len(split_records),
            "resolved_active_split_source_record_count": len(admitted),
            "quarantined_split_source_record_count": len(non_admitted),
            "resolved_event_group_count": len(events),
            "clear_event_group_count": sum(
                item.ledger_admission_status == "clear_candidate" for item in events
            ),
            "quarantined_event_group_count": sum(
                item.ledger_admission_status == "quarantined" for item in events
            ),
            "unresolved_with_historical_identity_count": with_history,
            "unresolved_without_historical_identity_count": without_history,
            "unresolved_with_ambiguous_historical_identity_count": ambiguous,
            "possible_impact_instrument_count": len(impacts),
            "resolved_events": events,
            "possible_unresolved_impacts": impacts,
            "quarantined_source_action_set_fingerprint": quarantine_fingerprint,
            "factor_direction": "multiply_raw_value_to_basis",
            "event_inclusion_rule": "source_session_lt_event_lte_basis",
            "provider_cumulative_factor_usage": "audit_only",
            "source_coverage_status": "bounded_query_snapshot_only",
            "point_in_time_eligibility": "outcome_reconciliation_only",
            "canonical_action_publication_status": "not_built",
            "adjustment_ledger_projection_status": "not_built",
            "total_return_adjustment_status": "unavailable",
            "latest_ticker_fallback_count": 0,
            "nearest_session_fallback_count": 0,
            "unresolved_action_assignment_count": 0,
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "adjustment_ledger_write_count": 0,
            "analytics_execution_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
        }
        candidate = CanonicalSourceSplitActionCandidateV1.model_validate(
            {**values, "logical_fingerprint": _fingerprint(values)}
        )
        existing = _read_if_present(target)
        if existing is not None:
            if existing.candidate != candidate:
                raise CanonicalSplitActionCandidateError(
                    "existing canonical-source split candidate differs"
                )
            return existing

        staging = target.parent / f".{target.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise CanonicalSplitActionCandidateError(
                "canonical-source split candidate staging target exists"
            )
        staging.mkdir(mode=0o700)
        try:
            output = staging / FILE_NAME
            output.write_bytes(_pretty_json(candidate.model_dump(mode="json")))
            output.chmod(0o400)
            _fsync_file(output)
            _fsync_directory(staging)
            staging.replace(target)
            _fsync_directory(target.parent)
        except Exception:
            if staging.exists() and not staging.is_symlink():
                for child in staging.iterdir():
                    child.unlink()
                staging.rmdir()
            raise
        reread = read_canonical_source_split_action_candidate(output_root=target)
        if reread.candidate != candidate:
            raise CanonicalSplitActionCandidateError(
                "canonical-source split candidate formal reread differs"
            )
        return CanonicalSourceSplitActionCandidateResult(
            output_root=reread.output_root,
            candidate=reread.candidate,
            file_sha256=reread.file_sha256,
            status="published",
        )


def read_canonical_source_split_action_candidate(
    *, output_root: Path
) -> CanonicalSourceSplitActionCandidateResult:
    root = _validated_completed_output(output_root)
    entries = tuple(root.iterdir())
    if len(entries) != 1 or entries[0].name != FILE_NAME:
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate file set differs"
        )
    path = root / FILE_NAME
    _require_regular_file(path, 0o400)
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate size is invalid"
        )
    raw = path.read_bytes()
    try:
        candidate = CanonicalSourceSplitActionCandidateV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate contract is invalid"
        ) from exc
    return CanonicalSourceSplitActionCandidateResult(
        output_root=root,
        candidate=candidate,
        file_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def _read_if_present(
    target: Path,
) -> CanonicalSourceSplitActionCandidateResult | None:
    if not target.exists() and not target.is_symlink():
        return None
    return read_canonical_source_split_action_candidate(output_root=target)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitActionCandidateError("canonical data root is unavailable")
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT or path != resolved:
        raise CanonicalSplitActionCandidateError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_output_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate must be below /tmp"
        )
    _reject_symlink_chain(target.parent, tmp)
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate parent is unsafe"
        )
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise CanonicalSplitActionCandidateError(
                "canonical-source split candidate target is unsafe"
            )
    return target


def _validated_completed_output(path: Path) -> Path:
    root = _validated_output_target(path)
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise CanonicalSplitActionCandidateError(
            "completed canonical-source split candidate is unavailable"
        )
    return root


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    current = path.absolute()
    while current != stop:
        if current.exists() and current.is_symlink():
            raise CanonicalSplitActionCandidateError("path contains a symlink")
        if stop not in current.parents:
            raise CanonicalSplitActionCandidateError("path escapes its trusted root")
        current = current.parent


def _require_regular_file(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise CanonicalSplitActionCandidateError(
            "required canonical-source split candidate file is missing"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != mode:
        raise CanonicalSplitActionCandidateError(
            "canonical-source split candidate file mode differs"
        )


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalSplitActionCandidateError(
            "network access is prohibited while building split actions"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
