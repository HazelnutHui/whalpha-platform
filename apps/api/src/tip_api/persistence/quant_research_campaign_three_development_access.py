"""Owner-only immutable custody for Campaign Three access and execution slots."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessGrantV1,
    CampaignThreeDevelopmentAccessRequestV1,
    CampaignThreeDevelopmentExecutionCompletionV1,
    CampaignThreeDevelopmentExecutionKind,
    CampaignThreeDevelopmentExecutionReservationV1,
    build_campaign_three_execution_completion,
    build_campaign_three_execution_reservation,
    validate_campaign_three_development_grant,
)


REQUEST_FILE = "campaign-three-development-access-request.json"
GRANT_FILE = "campaign-three-development-access-grant.json"
FORMAL_RESERVATION_FILE = "formal-reservation.json"
FORMAL_COMPLETION_FILE = "formal-completion.json"
REPLAY_RESERVATION_FILE = "exact-replay-reservation.json"
REPLAY_COMPLETION_FILE = "exact-replay-completion.json"
REQUEST_PREFIX = "request="
GRANT_PREFIX = "grant="
EXECUTION_PREFIX = "execution="
MAXIMUM_RECORD_BYTES = 1024 * 1024

_T = TypeVar("_T", bound=BaseModel)
_EXECUTION_FILES = {
    FORMAL_RESERVATION_FILE,
    FORMAL_COMPLETION_FILE,
    REPLAY_RESERVATION_FILE,
    REPLAY_COMPLETION_FILE,
}


class CampaignThreeDevelopmentAccessPersistenceError(RuntimeError):
    """Raised when Campaign Three private access custody cannot be trusted."""


def write_campaign_three_development_access_request(
    *,
    output_root: Path,
    output_custody_root: Path,
    request: CampaignThreeDevelopmentAccessRequestV1,
) -> tuple[Path, str, str]:
    return _write_single_model_root(
        output_root=output_root,
        output_custody_root=output_custody_root,
        required_prefix=REQUEST_PREFIX,
        file_name=REQUEST_FILE,
        model=request,
        model_type=CampaignThreeDevelopmentAccessRequestV1,
    )


def read_campaign_three_development_access_request(
    *, output_root: Path, output_custody_root: Path
) -> tuple[CampaignThreeDevelopmentAccessRequestV1, str]:
    return _read_single_model_root(
        output_root=output_root,
        output_custody_root=output_custody_root,
        required_prefix=REQUEST_PREFIX,
        file_name=REQUEST_FILE,
        model_type=CampaignThreeDevelopmentAccessRequestV1,
    )


def write_campaign_three_development_access_grant(
    *,
    output_root: Path,
    output_custody_root: Path,
    request: CampaignThreeDevelopmentAccessRequestV1,
    grant: CampaignThreeDevelopmentAccessGrantV1,
) -> tuple[Path, str, str]:
    validate_campaign_three_development_grant(request=request, grant=grant)
    return _write_single_model_root(
        output_root=output_root,
        output_custody_root=output_custody_root,
        required_prefix=GRANT_PREFIX,
        file_name=GRANT_FILE,
        model=grant,
        model_type=CampaignThreeDevelopmentAccessGrantV1,
    )


def read_campaign_three_development_access_grant(
    *, output_root: Path, output_custody_root: Path
) -> tuple[CampaignThreeDevelopmentAccessGrantV1, str]:
    return _read_single_model_root(
        output_root=output_root,
        output_custody_root=output_custody_root,
        required_prefix=GRANT_PREFIX,
        file_name=GRANT_FILE,
        model_type=CampaignThreeDevelopmentAccessGrantV1,
    )


def campaign_three_output_root_fingerprint(output_root: Path) -> str:
    normalized = output_root.absolute().resolve(strict=False)
    return hashlib.sha256(str(normalized).encode("utf-8")).hexdigest()


def reserve_campaign_three_development_execution(
    *,
    execution_root: Path,
    execution_custody_root: Path,
    request: CampaignThreeDevelopmentAccessRequestV1,
    grant: CampaignThreeDevelopmentAccessGrantV1,
    execution_kind: CampaignThreeDevelopmentExecutionKind,
    run_created_at: datetime,
    reserved_at: datetime,
    report_output_root: Path,
) -> CampaignThreeDevelopmentExecutionReservationV1:
    validate_campaign_three_development_grant(request=request, grant=grant)
    root = _ensure_execution_root(execution_root, execution_custody_root)
    state = read_campaign_three_development_execution_state(
        execution_root=root,
        execution_custody_root=execution_custody_root,
    )
    formal_reservation, formal_completion, replay_reservation, replay_completion = state
    output_fingerprint = campaign_three_output_root_fingerprint(report_output_root)
    if execution_kind is CampaignThreeDevelopmentExecutionKind.FORMAL:
        if any(item is not None for item in state):
            raise CampaignThreeDevelopmentAccessPersistenceError(
                "Campaign Three formal execution slot is already consumed"
            )
        prior_completion = None
        file_name = FORMAL_RESERVATION_FILE
    else:
        if (
            formal_reservation is None
            or formal_completion is None
            or replay_reservation is not None
            or replay_completion is not None
        ):
            raise CampaignThreeDevelopmentAccessPersistenceError(
                "Campaign Three replay requires one completed formal execution"
            )
        if (
            formal_reservation.request_fingerprint != request.logical_fingerprint
            or formal_reservation.grant_fingerprint != grant.logical_fingerprint
            or formal_reservation.implementation_revision
            != request.implementation_revision
            or formal_reservation.run_created_at != run_created_at
            or formal_reservation.output_root_fingerprint == output_fingerprint
        ):
            raise CampaignThreeDevelopmentAccessPersistenceError(
                "Campaign Three replay binding or output root differs"
            )
        prior_completion = formal_completion
        file_name = REPLAY_RESERVATION_FILE
    reservation = build_campaign_three_execution_reservation(
        request=request,
        grant=grant,
        execution_kind=execution_kind,
        run_created_at=run_created_at,
        reserved_at=reserved_at,
        output_root_fingerprint=output_fingerprint,
        formal_completion=prior_completion,
    )
    _write_execution_event(root / file_name, reservation)
    reread = _read_execution_event(
        root / file_name, CampaignThreeDevelopmentExecutionReservationV1
    )
    if reread != reservation:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution reservation reread differs"
        )
    return reservation


def complete_campaign_three_development_execution(
    *,
    execution_root: Path,
    execution_custody_root: Path,
    execution_kind: CampaignThreeDevelopmentExecutionKind,
    report_sha256: str,
    report_fingerprint: str,
    completed_at: datetime,
) -> CampaignThreeDevelopmentExecutionCompletionV1:
    root = _validated_execution_root(execution_root, execution_custody_root)
    state = read_campaign_three_development_execution_state(
        execution_root=root,
        execution_custody_root=execution_custody_root,
    )
    formal_reservation, formal_completion, replay_reservation, replay_completion = state
    if execution_kind is CampaignThreeDevelopmentExecutionKind.FORMAL:
        reservation = formal_reservation
        existing_completion = formal_completion
        file_name = FORMAL_COMPLETION_FILE
    else:
        reservation = replay_reservation
        existing_completion = replay_completion
        file_name = REPLAY_COMPLETION_FILE
    if reservation is None or existing_completion is not None:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution completion state differs"
        )
    completion = build_campaign_three_execution_completion(
        reservation=reservation,
        report_sha256=report_sha256,
        report_fingerprint=report_fingerprint,
        completed_at=completed_at,
    )
    _write_execution_event(root / file_name, completion)
    reread = _read_execution_event(
        root / file_name, CampaignThreeDevelopmentExecutionCompletionV1
    )
    if reread != completion:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution completion reread differs"
        )
    return completion


def read_campaign_three_development_execution_state(
    *, execution_root: Path, execution_custody_root: Path
) -> tuple[
    CampaignThreeDevelopmentExecutionReservationV1 | None,
    CampaignThreeDevelopmentExecutionCompletionV1 | None,
    CampaignThreeDevelopmentExecutionReservationV1 | None,
    CampaignThreeDevelopmentExecutionCompletionV1 | None,
]:
    root = _validated_execution_root(execution_root, execution_custody_root)
    items = tuple(root.iterdir())
    names = {item.name for item in items}
    if (
        not names.issubset(_EXECUTION_FILES)
        or any(item.is_symlink() or not item.is_file() for item in items)
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution custody contains unexpected records"
        )
    formal_reservation = _read_optional_execution_event(
        root / FORMAL_RESERVATION_FILE,
        CampaignThreeDevelopmentExecutionReservationV1,
    )
    formal_completion = _read_optional_execution_event(
        root / FORMAL_COMPLETION_FILE,
        CampaignThreeDevelopmentExecutionCompletionV1,
    )
    replay_reservation = _read_optional_execution_event(
        root / REPLAY_RESERVATION_FILE,
        CampaignThreeDevelopmentExecutionReservationV1,
    )
    replay_completion = _read_optional_execution_event(
        root / REPLAY_COMPLETION_FILE,
        CampaignThreeDevelopmentExecutionCompletionV1,
    )
    if (
        formal_reservation is not None
        and formal_reservation.execution_kind
        is not CampaignThreeDevelopmentExecutionKind.FORMAL
    ) or (
        formal_completion is not None
        and (
            formal_reservation is None
            or formal_completion.execution_kind
            is not CampaignThreeDevelopmentExecutionKind.FORMAL
            or formal_completion.reservation_fingerprint
            != formal_reservation.logical_fingerprint
            or formal_completion.completed_at < formal_reservation.reserved_at
        )
    ) or (
        replay_reservation is not None
        and (
            formal_completion is None
            or replay_reservation.execution_kind
            is not CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY
            or replay_reservation.expected_formal_report_sha256
            != formal_completion.report_sha256
            or replay_reservation.expected_formal_report_fingerprint
            != formal_completion.report_fingerprint
            or formal_reservation is None
            or replay_reservation.request_fingerprint
            != formal_reservation.request_fingerprint
            or replay_reservation.grant_fingerprint
            != formal_reservation.grant_fingerprint
            or replay_reservation.protocol_fingerprint
            != formal_reservation.protocol_fingerprint
            or replay_reservation.ledger_fingerprint
            != formal_reservation.ledger_fingerprint
            or replay_reservation.implementation_revision
            != formal_reservation.implementation_revision
            or replay_reservation.run_created_at
            != formal_reservation.run_created_at
            or replay_reservation.output_root_fingerprint
            == formal_reservation.output_root_fingerprint
        )
    ) or (
        replay_completion is not None
        and (
            replay_reservation is None
            or replay_completion.execution_kind
            is not CampaignThreeDevelopmentExecutionKind.EXACT_REPLAY
            or replay_completion.reservation_fingerprint
            != replay_reservation.logical_fingerprint
            or replay_completion.completed_at < replay_reservation.reserved_at
            or formal_completion is None
            or replay_completion.report_sha256 != formal_completion.report_sha256
            or replay_completion.report_fingerprint
            != formal_completion.report_fingerprint
        )
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution event chain differs"
        )
    return (
        formal_reservation,
        formal_completion,
        replay_reservation,
        replay_completion,
    )


def canonical_record_bytes(model: BaseModel) -> bytes:
    return (
        json.dumps(
            model.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_single_model_root(
    *, output_root, output_custody_root, required_prefix, file_name, model, model_type
):
    target, custody = _validated_single_target(
        output_root, output_custody_root, required_prefix
    )
    if target.exists() or target.is_symlink():
        existing, sha256 = _read_single_model_root(
            output_root=target,
            output_custody_root=custody,
            required_prefix=required_prefix,
            file_name=file_name,
            model_type=model_type,
        )
        if existing != model:
            raise CampaignThreeDevelopmentAccessPersistenceError(
                "existing Campaign Three access record differs"
            )
        return target / file_name, sha256, "already_present"
    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(staging / file_name, canonical_record_bytes(model))
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        _cleanup_single_staging(staging, file_name)
        if isinstance(exc, CampaignThreeDevelopmentAccessPersistenceError):
            raise
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record write failed"
        ) from exc
    reread, sha256 = _read_single_model_root(
        output_root=target,
        output_custody_root=custody,
        required_prefix=required_prefix,
        file_name=file_name,
        model_type=model_type,
    )
    if reread != model:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record reread differs"
        )
    return target / file_name, sha256, "published"


def _read_single_model_root(
    *, output_root, output_custody_root, required_prefix, file_name, model_type
):
    root, _ = _validated_single_target(
        output_root, output_custody_root, required_prefix
    )
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {file_name}
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record directory differs"
        )
    path = root / file_name
    model = _read_execution_event(path, model_type)
    payload = path.read_bytes()
    return model, hashlib.sha256(payload).hexdigest()


def _validated_single_target(output_root, output_custody_root, required_prefix):
    custody = Path(output_custody_root).absolute()
    target = Path(output_root).absolute()
    if (
        custody.is_symlink()
        or not custody.is_dir()
        or custody.resolve(strict=True) != custody
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or target.parent != custody
        or not target.name.startswith(required_prefix)
        or target.name == required_prefix
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access custody differs"
        )
    return target, custody


def _ensure_execution_root(execution_root: Path, execution_custody_root: Path) -> Path:
    custody = execution_custody_root.absolute()
    root = execution_root.absolute()
    _validate_custody_parent(root, custody)
    if not root.exists():
        root.mkdir(mode=0o700)
        _fsync_directory(custody)
    return _validated_execution_root(root, custody)


def _validated_execution_root(
    execution_root: Path, execution_custody_root: Path
) -> Path:
    custody = execution_custody_root.absolute()
    root = execution_root.absolute()
    _validate_custody_parent(root, custody)
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution root differs"
        )
    return root


def _validate_custody_parent(root: Path, custody: Path) -> None:
    if (
        custody.is_symlink()
        or not custody.is_dir()
        or custody.resolve(strict=True) != custody
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or root.parent != custody
        or not root.name.startswith(EXECUTION_PREFIX)
        or root.name == EXECUTION_PREFIX
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution custody differs"
        )


def _write_execution_event(path: Path, model: BaseModel) -> None:
    try:
        _write_exclusive(path, canonical_record_bytes(model))
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three execution slot is already consumed"
        ) from exc


def _read_optional_execution_event(path: Path, model_type: type[_T]) -> _T | None:
    return None if not path.exists() else _read_execution_event(path, model_type)


def _read_execution_event(path: Path, model_type: type[_T]) -> _T:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_RECORD_BYTES
    ):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record file differs"
        )
    payload = path.read_bytes()
    try:
        model = model_type.model_validate_json(payload)
    except Exception as exc:
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record is invalid"
        ) from exc
    if payload != canonical_record_bytes(model):
        raise CampaignThreeDevelopmentAccessPersistenceError(
            "Campaign Three access record bytes are not canonical"
        )
    return model


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _cleanup_single_staging(staging: Path, file_name: str) -> None:
    if staging.is_symlink() or not staging.exists():
        return
    path = staging / file_name
    if path.exists() and not path.is_symlink():
        path.unlink()
    try:
        staging.rmdir()
    except OSError:
        pass


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
