from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    DailyEodAuthorizedTransitionRequestV1,
    DailyEodStandingAuthorizationError,
    StandingOperation,
    authorize_standing_transition,
    build_standing_authorization_candidate,
    canonical_authorization_bytes,
    read_standing_authorization,
)


NOW = datetime(2026, 8, 27, 22, 0, tzinfo=UTC)
RUN_ROOT = Path("/home/hui/.local/state/trading-intelligence-platform/daily-eod")
DATA_ROOT = Path("/data/trading-intelligence-platform")
REVISION = "a" * 40
POLICY_FINGERPRINT = DailyEodReadinessPolicy().logical_fingerprint
FINGERPRINT = "b" * 64


def authorization(**overrides):
    values = {
        "authorization_id": "daily-eod-authorization-2026q3",
        "approved_at": NOW,
        "valid_from": NOW,
        "expires_at": NOW + timedelta(days=30),
        "host": "dell5820",
        "data_root": DATA_ROOT,
        "run_root": RUN_ROOT,
        "implementation_revision": REVISION,
        "readiness_policy_fingerprint": POLICY_FINGERPRINT,
        "allowed_operations": tuple(StandingOperation),
    }
    values.update(overrides)
    return build_standing_authorization_candidate(**values)


def request(operation: StandingOperation, **overrides):
    identity = operation in {
        StandingOperation.FETCH_IDENTITY,
        StandingOperation.APPLY_IDENTITY,
    }
    applying = operation in {
        StandingOperation.APPLY_IDENTITY,
        StandingOperation.APPLY_EOD,
    }
    values = {
        "requested_at": NOW + timedelta(minutes=1),
        "operation": operation,
        "target_session": "2026-08-27",
        "latest_canonical_session": "2026-08-26",
        "acquisition_action": (
            NextAction.PREPARE_IDENTITY_CATCHUP
            if identity
            else NextAction.PREPARE_EOD_CATCHUP
        ),
        "custody_attempt_id": "c" * 64,
        "custody_event_type": (
            "canonical_apply_started" if applying else "acquisition_started"
        ),
        "custody_event_fingerprint": "d" * 64,
        "readiness_policy_fingerprint": POLICY_FINGERPRINT,
        "readiness_plan_fingerprint": FINGERPRINT,
        "package_path": "/tmp/exact-daily-package",
        "package_manifest_sha256": "e" * 64 if applying else None,
        "package_content_sha256": "f" * 64 if applying else None,
        "approval_plan_path": "/tmp/exact-daily-plan.json" if applying else None,
        "approval_plan_sha256": "1" * 64 if applying else None,
        "expected_current_state_fingerprint": "2" * 64 if applying else None,
        "oldest_missing_session_proven": True,
    }
    values.update(overrides)
    return DailyEodAuthorizedTransitionRequestV1.model_validate(values)


def authorize(operation: StandingOperation, **overrides):
    values = {
        "authorization": authorization(),
        "request": request(operation),
        "evaluated_at": NOW + timedelta(minutes=2),
        "actual_host": "dell5820",
        "actual_provider_id": MASSIVE_PROVIDER_ID,
        "actual_data_root": DATA_ROOT,
        "actual_run_root": RUN_ROOT,
        "actual_implementation_revision": REVISION,
        "actual_readiness_policy_fingerprint": POLICY_FINGERPRINT,
    }
    values.update(overrides)
    return authorize_standing_transition(**values)


@pytest.mark.parametrize(
    ("operation", "requests", "writes"),
    (
        (StandingOperation.FETCH_IDENTITY, 20, 0),
        (StandingOperation.APPLY_IDENTITY, 0, 1),
        (StandingOperation.FETCH_EOD, 1, 0),
        (StandingOperation.APPLY_EOD, 0, 1),
    ),
)
def test_exact_scoped_transition_is_authorized(
    operation: StandingOperation, requests: int, writes: int
) -> None:
    decision = authorize(operation)

    assert decision.authorized is True
    assert decision.operation == operation.value
    assert decision.provider_request_limit == requests
    assert decision.canonical_write_limit == writes
    assert decision.publication_authorized is False
    assert decision.deployment_authorized is False
    assert decision.scheduler_authorized is False
    assert len(decision.request_fingerprint) == 64
    assert len(decision.logical_content_fingerprint) == 64


@pytest.mark.parametrize(
    ("override", "value"),
    (
        ("actual_host", "other-host"),
        ("actual_provider_id", "other-provider"),
        ("actual_data_root", Path("/tmp/data")),
        ("actual_run_root", Path("/tmp/run")),
        ("actual_implementation_revision", "3" * 40),
        ("actual_readiness_policy_fingerprint", "4" * 64),
    ),
)
def test_runtime_binding_change_fails_closed(override: str, value: object) -> None:
    with pytest.raises(
        DailyEodStandingAuthorizationError,
        match="runtime differs",
    ):
        authorize(StandingOperation.FETCH_EOD, **{override: value})


def test_expired_or_stale_request_fails_closed() -> None:
    with pytest.raises(DailyEodStandingAuthorizationError, match="not active"):
        authorize(
            StandingOperation.FETCH_EOD,
            evaluated_at=NOW + timedelta(days=31),
        )
    with pytest.raises(DailyEodStandingAuthorizationError, match="request is stale"):
        authorize(
            StandingOperation.FETCH_EOD,
            request=request(
                StandingOperation.FETCH_EOD,
                requested_at=NOW - timedelta(minutes=10),
            ),
        )


def test_operation_outside_reviewed_subset_fails_closed() -> None:
    limited = authorization(
        allowed_operations=(StandingOperation.FETCH_IDENTITY,)
    )
    with pytest.raises(DailyEodStandingAuthorizationError, match="outside"):
        authorize(
            StandingOperation.FETCH_EOD,
            authorization=limited,
        )


def test_authorization_rejects_excessive_lifetime_and_unordered_scope() -> None:
    with pytest.raises(ValidationError, match="time boundary"):
        authorization(expires_at=NOW + timedelta(days=91))
    with pytest.raises(ValidationError, match="operation scope"):
        authorization(
            allowed_operations=(
                StandingOperation.FETCH_EOD,
                StandingOperation.FETCH_IDENTITY,
            )
        )


@pytest.mark.parametrize(
    "change",
    (
        {"acquisition_action": NextAction.PREPARE_IDENTITY_CATCHUP},
        {"custody_event_type": "acquisition_package_ready"},
        {"package_path": "/tmp/.hidden"},
        {"readiness_policy_fingerprint": "not-a-fingerprint"},
    ),
)
def test_fetch_request_rejects_mismatched_or_unsafe_custody(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        request(StandingOperation.FETCH_EOD, **change)


def test_request_cannot_skip_an_xnys_session() -> None:
    with pytest.raises(ValidationError, match="oldest missing session"):
        request(
            StandingOperation.FETCH_EOD,
            target_session="2026-08-28",
            latest_canonical_session="2026-08-26",
        )


@pytest.mark.parametrize(
    "change",
    (
        {"custody_event_type": "acquisition_package_ready"},
        {"package_manifest_sha256": None},
        {"approval_plan_path": "/var/tmp/plan.json"},
        {"approval_plan_sha256": "bad"},
        {"expected_current_state_fingerprint": None},
    ),
)
def test_apply_request_requires_completed_package_and_exact_plan(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        request(StandingOperation.APPLY_EOD, **change)


def test_canonical_owner_only_artifact_requires_external_whole_file_sha(
    tmp_path: Path,
) -> None:
    root = tmp_path / "authorizations"
    root.mkdir(mode=0o700)
    path = root / "daily-eod.json"
    raw = canonical_authorization_bytes(authorization())
    path.write_bytes(raw)
    path.chmod(0o400)
    expected = hashlib.sha256(raw).hexdigest()

    loaded = read_standing_authorization(
        authorization_path=path,
        authorization_root=root,
        repository_root=Path("/opt/trading-intelligence-platform"),
        expected_file_sha256=expected,
    )

    assert loaded.authorization_id == "daily-eod-authorization-2026q3"
    with pytest.raises(DailyEodStandingAuthorizationError, match="SHA mismatch"):
        read_standing_authorization(
            authorization_path=path,
            authorization_root=root,
            repository_root=Path("/opt/trading-intelligence-platform"),
            expected_file_sha256="9" * 64,
        )


def test_artifact_rejects_noncanonical_bytes_or_unsafe_mode(tmp_path: Path) -> None:
    root = tmp_path / "authorizations"
    root.mkdir(mode=0o700)
    path = root / "daily-eod.json"
    payload = authorization().model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    path.chmod(0o400)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(DailyEodStandingAuthorizationError, match="not canonical"):
        read_standing_authorization(
            authorization_path=path,
            authorization_root=root,
            repository_root=Path("/opt/trading-intelligence-platform"),
            expected_file_sha256=expected,
        )

    path.chmod(0o600)
    with pytest.raises(DailyEodStandingAuthorizationError, match="custody is unsafe"):
        read_standing_authorization(
            authorization_path=path,
            authorization_root=root,
            repository_root=Path("/opt/trading-intelligence-platform"),
            expected_file_sha256=expected,
        )


def test_authorization_root_cannot_be_inside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repository" / "authorizations"
    root.mkdir(parents=True, mode=0o700)
    path = root / "daily-eod.json"
    raw = canonical_authorization_bytes(authorization())
    path.write_bytes(raw)
    path.chmod(0o400)

    with pytest.raises(DailyEodStandingAuthorizationError, match="path boundary"):
        read_standing_authorization(
            authorization_path=path,
            authorization_root=root,
            repository_root=tmp_path / "repository",
            expected_file_sha256=hashlib.sha256(raw).hexdigest(),
        )

def test_candidate_has_no_publication_deployment_or_scheduler_authority() -> None:
    candidate = authorization()

    assert candidate.overwrite_allowed is False
    assert candidate.publication_authorized is False
    assert candidate.snapshot_authorized is False
    assert candidate.bundle_authorized is False
    assert candidate.deployment_authorized is False
    assert candidate.rollback_authorized is False
    assert candidate.universe_activation_authorized is False
    assert candidate.sec_authorized is False
    assert candidate.intraday_options_authorized is False
    assert candidate.order_execution_authorized is False
    assert candidate.scheduler_authorized is False
