"""Build and formally reread an offline inactive-lifecycle corroboration plan."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
    inactive_lifecycle_fingerprint,
)
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle_corroboration import (
    PLAN_CONTRACT_VERSION,
    REQUIRED_LIFECYCLE_EVIDENCE,
    HistoricalInactiveLifecycleCorroborationPlanV1,
    HistoricalInactiveLifecycleCorroborationWorkItemV1,
    LifecycleCorroborationRoute,
    LifecycleCorroborationStatus,
)
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    HistoricalInactiveLifecycleResolutionShadowError,
    read_historical_inactive_lifecycle_resolution_shadow,
)


_TMP_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class HistoricalInactiveLifecycleCorroborationPlanError(RuntimeError):
    """Raised when the offline corroboration plan cannot be trusted."""


@dataclass(frozen=True, slots=True)
class HistoricalInactiveLifecycleCorroborationPlanEvidence:
    plan_path: Path
    plan: HistoricalInactiveLifecycleCorroborationPlanV1
    plan_sha256: str
    status: str


def build_historical_inactive_lifecycle_corroboration_plan(
    *,
    shadow_root: Path,
    anchor_date: date,
    plan_path: Path,
    planned_at: datetime,
    implementation_revision: str,
) -> HistoricalInactiveLifecycleCorroborationPlanEvidence:
    """Create one owner-only plan without network, canonical writes, or promotion."""

    candidate_path = _validated_plan_path(plan_path, must_exist=False)
    normalized_planned_at = normalize_utc_datetime(planned_at)
    if len(implementation_revision) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_revision
    ):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "implementation revision is invalid"
        )
    with _network_prohibited():
        try:
            shadow = read_historical_inactive_lifecycle_resolution_shadow(
                root=shadow_root,
                anchor_date=anchor_date,
            )
        except HistoricalInactiveLifecycleResolutionShadowError as exc:
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "inactive lifecycle shadow failed formal reread"
            ) from exc
        items = _work_items(shadow.source_observations, shadow.decisions)
        dispositions = dict(shadow.manifest.disposition_counts)
        review_count = dispositions.get("review_candidate", 0)
        quarantined_count = dispositions.get("quarantined", 0)
        if len(items) != review_count or review_count < 1:
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "inactive lifecycle candidate count differs"
            )
        base = {
            "contract_version": PLAN_CONTRACT_VERSION,
            "operation": "plan_inactive_lifecycle_corroboration",
            "anchor_date": anchor_date,
            "planned_at": normalized_planned_at,
            "implementation_revision": implementation_revision,
            "shadow_manifest_sha256": shadow.manifest_sha256,
            "shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
            "shadow_source_record_count": shadow.manifest.source_package_record_count,
            "shadow_review_candidate_count": review_count,
            "shadow_quarantined_count": quarantined_count,
            "work_items": items,
            "primary_exchange_counts": _counts(
                item.primary_exchange for item in items
            ),
            "route_counts": _counts(item.route.value for item in items),
            "status_counts": _counts(item.status.value for item in items),
            "required_evidence": REQUIRED_LIFECYCLE_EVIDENCE,
            "unique_source_observation_count": len(
                {item.source_observation_fingerprint for item in items}
            ),
            "unique_instrument_count": len(
                {item.canonical_instrument_id for item in items}
            ),
            "provider_last_updated_present_count": sum(
                item.provider_last_updated_field_present for item in items
            ),
            "point_in_time_eligible_count": 0,
            "ticker_locator_retained_count": 0,
            "nasdaq_daily_list_sufficiency_claimed": False,
            "all_exchange_source_selected": False,
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "analytics_execution_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
            "scheduler_change_count": 0,
            "acquisition_authorized": False,
            "canonical_lifecycle_authorized": False,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
            "operational_authority": "none",
        }
        plan = HistoricalInactiveLifecycleCorroborationPlanV1.model_validate(
            {
                **base,
                "logical_fingerprint": inactive_lifecycle_fingerprint(base),
            }
        )
        payload = _plan_bytes(plan)
        if os.path.lexists(candidate_path):
            existing = read_historical_inactive_lifecycle_corroboration_plan(
                plan_path=candidate_path
            )
            if existing.plan != plan or existing.plan_sha256 != _sha256(payload):
                raise HistoricalInactiveLifecycleCorroborationPlanError(
                    "existing lifecycle corroboration plan differs"
                )
            return HistoricalInactiveLifecycleCorroborationPlanEvidence(
                plan_path=candidate_path,
                plan=plan,
                plan_sha256=existing.plan_sha256,
                status="already_present",
            )
        _write_plan(candidate_path, payload)
        reread = read_historical_inactive_lifecycle_corroboration_plan(
            plan_path=candidate_path,
            approved_plan_sha256=_sha256(payload),
        )
        if reread.plan != plan:
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "lifecycle corroboration plan formal reread differs"
            )
        return HistoricalInactiveLifecycleCorroborationPlanEvidence(
            plan_path=candidate_path,
            plan=plan,
            plan_sha256=reread.plan_sha256,
            status="plan_created",
        )


def read_historical_inactive_lifecycle_corroboration_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
) -> HistoricalInactiveLifecycleCorroborationPlanEvidence:
    """Formally read one immutable owner-only corroboration plan."""

    candidate_path = _validated_plan_path(plan_path, must_exist=True)
    _require_regular_owner_file(candidate_path, mode=0o400)
    payload = candidate_path.read_bytes()
    physical_sha256 = _sha256(payload)
    if approved_plan_sha256 is not None:
        if len(approved_plan_sha256) != _SHA256_LENGTH or physical_sha256 != approved_plan_sha256:
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "lifecycle corroboration plan SHA-256 differs"
            )
    try:
        plan = HistoricalInactiveLifecycleCorroborationPlanV1.model_validate_json(
            payload
        )
    except Exception as exc:
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan is invalid"
        ) from exc
    return HistoricalInactiveLifecycleCorroborationPlanEvidence(
        plan_path=candidate_path,
        plan=plan,
        plan_sha256=physical_sha256,
        status="plan_revalidated",
    )


def _work_items(source_observations: tuple, decisions: tuple) -> tuple[
    HistoricalInactiveLifecycleCorroborationWorkItemV1, ...
]:
    if len(source_observations) != len(decisions):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "shadow source and decision counts differ"
        )
    items: list[HistoricalInactiveLifecycleCorroborationWorkItemV1] = []
    for observation, decision in zip(source_observations, decisions, strict=True):
        if decision.disposition is not InactiveLifecycleDisposition.REVIEW_CANDIDATE:
            continue
        if (
            observation.source_observation_fingerprint
            != decision.source_observation_fingerprint
            or decision.canonical_instrument_id is None
            or decision.effective_date_candidate is None
            or decision.canonical_first_observed_date is None
            or decision.canonical_last_observed_date is None
            or observation.primary_exchange is None
        ):
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "review candidate lineage is incomplete"
            )
        is_nasdaq = observation.primary_exchange.strip().upper() == "XNAS"
        route = (
            LifecycleCorroborationRoute.NASDAQ_DAILY_LIST_PILOT_REQUIRED
            if is_nasdaq
            else LifecycleCorroborationRoute.ALL_EXCHANGE_SOURCE_SELECTION_REQUIRED
        )
        status = (
            LifecycleCorroborationStatus.DOCUMENTED_SOURCE_PILOT_REQUIRED
            if is_nasdaq
            else LifecycleCorroborationStatus.SOURCE_SELECTION_REQUIRED
        )
        items.append(
            HistoricalInactiveLifecycleCorroborationWorkItemV1(
                anchor_date=decision.anchor_date,
                source_observation_fingerprint=(
                    decision.source_observation_fingerprint
                ),
                shadow_decision_fingerprint=inactive_lifecycle_fingerprint(
                    decision.model_dump(mode="json")
                ),
                canonical_instrument_id=decision.canonical_instrument_id,
                primary_exchange=observation.primary_exchange,
                effective_date_candidate=decision.effective_date_candidate,
                canonical_first_observed_date=(
                    decision.canonical_first_observed_date
                ),
                canonical_last_observed_date=(
                    decision.canonical_last_observed_date
                ),
                source_first_observed_at=observation.source_observed_at,
                provider_last_updated_field_present=bool(
                    observation.last_updated_utc
                    and observation.last_updated_utc.strip()
                ),
                route=route,
                status=status,
            )
        )
    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.primary_exchange,
                item.effective_date_candidate,
                str(item.canonical_instrument_id),
            ),
        )
    )


def _plan_bytes(plan: HistoricalInactiveLifecycleCorroborationPlanV1) -> bytes:
    return (
        json.dumps(
            plan.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _write_plan(path: Path, payload: bytes) -> None:
    staging = path.with_name(f".{path.name}.staging.{os.getpid()}")
    if os.path.lexists(staging):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan staging path exists"
        )
    descriptor = os.open(
        staging,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o600,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise HistoricalInactiveLifecycleCorroborationPlanError(
                    "lifecycle corroboration plan write did not progress"
                )
            remaining = remaining[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    except Exception:
        os.close(descriptor)
        _remove_staging(staging)
        raise
    os.close(descriptor)
    try:
        os.link(staging, path, follow_symlinks=False)
        staging.unlink()
        _fsync_directory(path.parent)
    except Exception:
        _remove_staging(staging)
        raise


def _validated_plan_path(path: Path, *, must_exist: bool) -> Path:
    if (
        not path.is_absolute()
        or path.name in {"", ".", ".."}
        or ".." in path.parts
        or path.parts[:2] != ("/", "tmp")
    ):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan path is invalid"
        )
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan parent is unavailable"
        )
    _reject_symlink_chain(parent)
    resolved_parent = parent.resolve(strict=True)
    if resolved_parent != _TMP_ROOT and _TMP_ROOT not in resolved_parent.parents:
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan must remain below /tmp"
        )
    candidate = resolved_parent / path.name
    if must_exist and not os.path.lexists(candidate):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan is unavailable"
        )
    return candidate


def _reject_symlink_chain(path: Path) -> None:
    current = path
    while current != _TMP_ROOT:
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "lifecycle corroboration plan path contains a symlink"
            )
        current = current.parent


def _require_regular_owner_file(path: Path, *, mode: int) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration plan custody differs"
        )


def _remove_staging(path: Path) -> None:
    if not os.path.lexists(path):
        return
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "lifecycle corroboration staging cleanup refused"
        )
    path.chmod(0o600, follow_symlinks=False)
    path.unlink()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _counts(values: Iterator[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "network is prohibited while planning lifecycle corroboration"
            )

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise HistoricalInactiveLifecycleCorroborationPlanError(
                "network is prohibited while planning lifecycle corroboration"
            )

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "network is prohibited while planning lifecycle corroboration"
        )

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo
