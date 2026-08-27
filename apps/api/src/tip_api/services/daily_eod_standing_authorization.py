"""Default-deny standing authorization contract for daily Identity and EOD data."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import to_jsonable_python

from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "daily-eod-standing-authorization/1.0"
REQUEST_CONTRACT_VERSION = "daily-eod-authorized-transition-request/1.1"
DECISION_CONTRACT_VERSION = "daily-eod-authorization-decision/1.0"
MAXIMUM_VALIDITY = timedelta(days=90)
MAXIMUM_REQUEST_AGE = timedelta(minutes=5)
MAXIMUM_ARTIFACT_BYTES = 64 * 1024
APPROVED_CANONICAL_DATA_ROOT = Path("/data/trading-intelligence-platform")


class DailyEodStandingAuthorizationError(RuntimeError):
    """Raised when standing authority cannot be proven exactly."""


class StandingOperation(StrEnum):
    FETCH_IDENTITY = "fetch_identity"
    APPLY_IDENTITY = "apply_identity"
    FETCH_EOD = "fetch_eod"
    APPLY_EOD = "apply_eod"


OPERATION_ORDER = tuple(StandingOperation)
FETCH_OPERATIONS = frozenset(
    {StandingOperation.FETCH_IDENTITY, StandingOperation.FETCH_EOD}
)
APPLY_OPERATIONS = frozenset(
    {StandingOperation.APPLY_IDENTITY, StandingOperation.APPLY_EOD}
)
OPERATION_ACTION = {
    StandingOperation.FETCH_IDENTITY: NextAction.PREPARE_IDENTITY_CATCHUP,
    StandingOperation.APPLY_IDENTITY: NextAction.PREPARE_IDENTITY_CATCHUP,
    StandingOperation.FETCH_EOD: NextAction.PREPARE_EOD_CATCHUP,
    StandingOperation.APPLY_EOD: NextAction.PREPARE_EOD_CATCHUP,
}
APPLY_EVENT_TYPES = frozenset({"canonical_apply_started"})


class DailyEodStandingAuthorizationV1(BaseModel):
    """Reviewed scope candidate; activation also requires an external SHA pin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-standing-authorization/1.0"] = (
        CONTRACT_VERSION
    )
    authorization_id: str = Field(
        min_length=16,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.:-]+$",
    )
    approved_at: datetime
    valid_from: datetime
    expires_at: datetime
    host: Literal["dell5820"]
    provider_id: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    data_root: str
    run_root: str
    implementation_revision: str
    readiness_policy_fingerprint: str
    allowed_operations: tuple[StandingOperation, ...]
    oldest_missing_session_only: Literal[True] = True
    one_transition_per_invocation: Literal[True] = True
    package_custody_required: Literal[True] = True
    approved_plan_required_for_apply: Literal[True] = True
    overwrite_allowed: Literal[False] = False
    publication_authorized: Literal[False] = False
    snapshot_authorized: Literal[False] = False
    bundle_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    rollback_authorized: Literal[False] = False
    universe_activation_authorized: Literal[False] = False
    sec_authorized: Literal[False] = False
    intraday_options_authorized: Literal[False] = False
    order_execution_authorized: Literal[False] = False
    scheduler_authorized: Literal[False] = False
    authorization_content_sha256: str

    @model_validator(mode="after")
    def validate_exact_scope(self) -> "DailyEodStandingAuthorizationV1":
        approved = _aware_utc(self.approved_at)
        valid_from = _aware_utc(self.valid_from)
        expires = _aware_utc(self.expires_at)
        if (
            approved > valid_from
            or expires <= valid_from
            or expires - valid_from > MAXIMUM_VALIDITY
        ):
            raise ValueError("standing authorization time boundary is invalid")
        if Path(self.data_root) != APPROVED_CANONICAL_DATA_ROOT:
            raise ValueError(
                "standing authorization data root must be the approved canonical root"
            )
        run_root = Path(self.run_root)
        if not run_root.is_absolute() or _is_within(run_root, Path("/data")):
            raise ValueError("standing authorization run root is invalid")
        if not _is_revision(self.implementation_revision):
            raise ValueError("standing authorization implementation revision is malformed")
        if not _is_fingerprint(self.readiness_policy_fingerprint):
            raise ValueError("standing authorization readiness fingerprint is malformed")
        if (
            not self.allowed_operations
            or len(set(self.allowed_operations)) != len(self.allowed_operations)
            or tuple(item for item in OPERATION_ORDER if item in self.allowed_operations)
            != self.allowed_operations
        ):
            raise ValueError("standing authorization operation scope is malformed")
        if not _is_fingerprint(self.authorization_content_sha256):
            raise ValueError("standing authorization content fingerprint is malformed")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"authorization_content_sha256"})
        )
        if self.authorization_content_sha256 != expected:
            raise ValueError("standing authorization content fingerprint mismatch")
        return self


class DailyEodAuthorizedTransitionRequestV1(BaseModel):
    """One exact coordinator-derived transition presented for authorization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-authorized-transition-request/1.1"] = (
        REQUEST_CONTRACT_VERSION
    )
    requested_at: datetime
    operation: StandingOperation
    target_session: date
    latest_canonical_session: date
    acquisition_action: NextAction
    custody_attempt_id: str
    custody_event_type: str
    custody_event_fingerprint: str
    readiness_policy_fingerprint: str
    readiness_plan_fingerprint: str
    package_path: str
    package_manifest_sha256: str | None = None
    package_content_sha256: str | None = None
    approval_plan_path: str | None = None
    approval_plan_sha256: str | None = None
    expected_current_state_fingerprint: str | None = None
    oldest_missing_session_proven: Literal[True] = True

    @model_validator(mode="after")
    def validate_transition_shape(self) -> "DailyEodAuthorizedTransitionRequestV1":
        _aware_utc(self.requested_at)
        if self.target_session <= self.latest_canonical_session:
            raise ValueError("authorized transition must advance one missing session")
        try:
            expected_target = ExchangeCalendar().next_session(
                self.latest_canonical_session
            )
        except (KeyError, RuntimeError, ValueError) as exc:
            raise ValueError("authorized transition calendar boundary is invalid") from exc
        if self.target_session != expected_target:
            raise ValueError("authorized transition must target the oldest missing session")
        if self.acquisition_action is not OPERATION_ACTION[self.operation]:
            raise ValueError("authorized transition action disagrees with operation")
        if not all(
            _is_fingerprint(value)
            for value in (
                self.custody_attempt_id,
                self.custody_event_fingerprint,
                self.readiness_policy_fingerprint,
                self.readiness_plan_fingerprint,
            )
        ):
            raise ValueError("authorized transition custody binding is malformed")
        package = Path(self.package_path)
        if not _is_direct_tmp_path(package):
            raise ValueError("authorized transition package path is invalid")
        package_fields = (
            self.package_manifest_sha256,
            self.package_content_sha256,
        )
        plan_fields = (
            self.approval_plan_path,
            self.approval_plan_sha256,
            self.expected_current_state_fingerprint,
        )
        if self.operation in FETCH_OPERATIONS:
            if self.custody_event_type != "acquisition_started":
                raise ValueError("fetch authorization requires an unresolved reservation")
            if any(value is not None for value in (*package_fields, *plan_fields)):
                raise ValueError("fetch authorization cannot carry apply evidence")
        else:
            if self.custody_event_type not in APPLY_EVENT_TYPES:
                raise ValueError("apply authorization requires an unresolved apply reservation")
            if not all(_is_fingerprint(value) for value in package_fields):
                raise ValueError("apply authorization package hashes are malformed")
            if self.approval_plan_path is None or not _is_direct_tmp_path(
                Path(self.approval_plan_path)
            ):
                raise ValueError("apply authorization plan path is invalid")
            if self.approval_plan_path == self.package_path:
                raise ValueError("apply plan and fetch package paths must differ")
            if not all(_is_fingerprint(value) for value in plan_fields[1:]):
                raise ValueError("apply authorization plan binding is malformed")
        return self


@dataclass(frozen=True, slots=True)
class DailyEodAuthorizationDecision:
    contract_version: str
    authorized: bool
    authorization_id: str
    authorization_content_sha256: str
    operation: str
    target_session: str
    request_fingerprint: str
    provider_request_limit: int
    canonical_write_limit: int
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_authorized: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_standing_authorization_candidate(
    *,
    authorization_id: str,
    approved_at: datetime,
    valid_from: datetime,
    expires_at: datetime,
    host: Literal["dell5820"],
    data_root: Path,
    run_root: Path,
    implementation_revision: str,
    readiness_policy_fingerprint: str,
    allowed_operations: tuple[StandingOperation, ...],
) -> DailyEodStandingAuthorizationV1:
    """Build an in-memory review candidate; this does not activate or write it."""

    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "authorization_id": authorization_id,
        "approved_at": _aware_utc(approved_at),
        "valid_from": _aware_utc(valid_from),
        "expires_at": _aware_utc(expires_at),
        "host": host,
        "provider_id": MASSIVE_PROVIDER_ID,
        "data_root": str(data_root),
        "run_root": str(run_root),
        "implementation_revision": implementation_revision,
        "readiness_policy_fingerprint": readiness_policy_fingerprint,
        "allowed_operations": allowed_operations,
        "oldest_missing_session_only": True,
        "one_transition_per_invocation": True,
        "package_custody_required": True,
        "approved_plan_required_for_apply": True,
        "overwrite_allowed": False,
        "publication_authorized": False,
        "snapshot_authorized": False,
        "bundle_authorized": False,
        "deployment_authorized": False,
        "rollback_authorized": False,
        "universe_activation_authorized": False,
        "sec_authorized": False,
        "intraday_options_authorized": False,
        "order_execution_authorized": False,
        "scheduler_authorized": False,
    }
    return DailyEodStandingAuthorizationV1.model_validate(
        {**base, "authorization_content_sha256": _fingerprint(base)}
    )


def canonical_authorization_bytes(
    authorization: DailyEodStandingAuthorizationV1,
) -> bytes:
    return _canonical_bytes(authorization.model_dump(mode="json"))


def read_standing_authorization(
    *,
    authorization_path: Path,
    authorization_root: Path,
    repository_root: Path,
    expected_file_sha256: str,
) -> DailyEodStandingAuthorizationV1:
    """Read an externally provisioned authorization under strict local custody."""

    if not _is_fingerprint(expected_file_sha256):
        raise DailyEodStandingAuthorizationError("authorization file SHA is malformed")
    if (
        not authorization_root.is_absolute()
        or not repository_root.is_absolute()
        or authorization_path.parent != authorization_root
        or authorization_path.name.startswith(".")
        or authorization_path.suffix != ".json"
        or _is_within(authorization_root, Path("/data"))
        or _is_within(authorization_root, repository_root)
    ):
        raise DailyEodStandingAuthorizationError("authorization path boundary is invalid")
    try:
        root_metadata = authorization_root.lstat()
        file_metadata = authorization_path.lstat()
    except OSError as exc:
        raise DailyEodStandingAuthorizationError("authorization custody is unavailable") from exc
    if (
        authorization_root.resolve() != authorization_root
        or stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or root_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
        or stat.S_ISLNK(file_metadata.st_mode)
        or not stat.S_ISREG(file_metadata.st_mode)
        or file_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(file_metadata.st_mode) != 0o400
        or not 0 < file_metadata.st_size <= MAXIMUM_ARTIFACT_BYTES
    ):
        raise DailyEodStandingAuthorizationError("authorization custody is unsafe")
    try:
        raw = authorization_path.read_bytes()
        payload = json.loads(raw)
        authorization = DailyEodStandingAuthorizationV1.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DailyEodStandingAuthorizationError("authorization artifact is invalid") from exc
    if hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        raise DailyEodStandingAuthorizationError("authorization file SHA mismatch")
    if raw != canonical_authorization_bytes(authorization):
        raise DailyEodStandingAuthorizationError("authorization artifact is not canonical")
    return authorization


def authorize_standing_transition(
    *,
    authorization: DailyEodStandingAuthorizationV1,
    request: DailyEodAuthorizedTransitionRequestV1,
    evaluated_at: datetime,
    actual_host: str,
    actual_provider_id: str,
    actual_data_root: Path,
    actual_run_root: Path,
    actual_implementation_revision: str,
    actual_readiness_policy_fingerprint: str,
) -> DailyEodAuthorizationDecision:
    """Authorize one exact request without executing provider or filesystem work."""

    checked = _aware_utc(evaluated_at)
    requested = _aware_utc(request.requested_at)
    validate_standing_authorization_runtime(
        authorization=authorization,
        evaluated_at=checked,
        operation=request.operation,
        actual_host=actual_host,
        actual_provider_id=actual_provider_id,
        actual_data_root=actual_data_root,
        actual_run_root=actual_run_root,
        actual_implementation_revision=actual_implementation_revision,
        actual_readiness_policy_fingerprint=actual_readiness_policy_fingerprint,
    )
    if request.readiness_policy_fingerprint != authorization.readiness_policy_fingerprint:
        raise DailyEodStandingAuthorizationError(
            "runtime differs from standing authorization"
        )
    if requested > checked or checked - requested > MAXIMUM_REQUEST_AGE:
        raise DailyEodStandingAuthorizationError("standing authorization request is stale")
    request_fingerprint = _fingerprint(request.model_dump(mode="json"))
    base = {
        "contract_version": DECISION_CONTRACT_VERSION,
        "authorized": True,
        "authorization_id": authorization.authorization_id,
        "authorization_content_sha256": authorization.authorization_content_sha256,
        "operation": request.operation.value,
        "target_session": request.target_session.isoformat(),
        "request_fingerprint": request_fingerprint,
        "provider_request_limit": (
            20
            if request.operation is StandingOperation.FETCH_IDENTITY
            else 1 if request.operation is StandingOperation.FETCH_EOD else 0
        ),
        "canonical_write_limit": 1 if request.operation in APPLY_OPERATIONS else 0,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_authorized": False,
    }
    return DailyEodAuthorizationDecision(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )


def validate_standing_authorization_runtime(
    *,
    authorization: DailyEodStandingAuthorizationV1,
    evaluated_at: datetime,
    operation: StandingOperation,
    actual_host: str,
    actual_provider_id: str,
    actual_data_root: Path,
    actual_run_root: Path,
    actual_implementation_revision: str,
    actual_readiness_policy_fingerprint: str,
) -> None:
    """Reject an inactive or mismatched grant before creating a custody start."""

    checked = _aware_utc(evaluated_at)
    if checked < authorization.valid_from or checked > authorization.expires_at:
        raise DailyEodStandingAuthorizationError("standing authorization is not active")
    if operation not in authorization.allowed_operations:
        raise DailyEodStandingAuthorizationError("operation is outside standing authorization")
    if (
        actual_host != authorization.host
        or actual_provider_id != authorization.provider_id
        or str(actual_data_root) != authorization.data_root
        or str(actual_run_root) != authorization.run_root
        or actual_implementation_revision != authorization.implementation_revision
        or actual_readiness_policy_fingerprint
        != authorization.readiness_policy_fingerprint
    ):
        raise DailyEodStandingAuthorizationError("runtime differs from standing authorization")


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("standing authorization timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _is_direct_tmp_path(path: Path) -> bool:
    return (
        path.is_absolute()
        and path.parent == Path("/tmp")
        and not path.name.startswith(".")
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )
