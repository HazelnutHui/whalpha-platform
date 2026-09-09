"""Standing-authorized provider fetch and canonical Apply capability adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import (
    SameDayCatchupError,
    apply_approved_plan,
    fetch_eod_package,
    fetch_identity_package,
)
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)
from tip_api.services.daily_eod_acquisition_custody import (
    AcquisitionCustodyResult,
    record_acquisition_outcome,
    reserve_acquisition_attempt,
)
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_canonical_apply_custody import (
    CanonicalApplyCustodyResult,
    DailyEodCanonicalApplyConfig,
    record_canonical_apply_success,
    reserve_canonical_apply,
)
from tip_api.services.daily_eod_coordinator import (
    AuthorizedTransitionContext,
    AuthorizedTransitionEvidence,
)
from tip_api.services.daily_eod_readiness import (
    AttemptOutcome,
    ReadinessNextAction,
)
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
    DailyEodAuthorizationDecision,
    DailyEodAuthorizedTransitionRequestV1,
    DailyEodStandingAuthorizationV1,
    StandingOperation,
    authorize_standing_transition,
    read_standing_authorization,
    validate_standing_authorization_runtime,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_daily_eod_data_artifact_pair,
)


CONTRACT_VERSION = "daily-eod-authorized-capabilities/1.0"


class DailyEodAuthorizedCapabilityError(RuntimeError):
    """Raised when an authorized capability cannot preserve exact custody."""


@dataclass(frozen=True, slots=True)
class DailyEodAuthorizedCapabilityConfig:
    authorization_path: Path
    authorization_root: Path
    repository_root: Path
    expected_authorization_file_sha256: str
    actual_host: str
    implementation_revision: str
    readiness_policy_fingerprint: str
    data_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths
    credential_path: Path | None = None
    approved_plan_sha256: str | None = None
    expected_current_state_fingerprint: str | None = None


Clock = Callable[[], datetime]
AuthorizationReader = Callable[..., DailyEodStandingAuthorizationV1]
Authorizer = Callable[..., DailyEodAuthorizationDecision]
RuntimeValidator = Callable[..., None]
CredentialLoader = Callable[..., MassiveProviderConfig]
Fetcher = Callable[..., object]
ApplyExecutor = Callable[..., object]
AcquisitionReserver = Callable[..., AcquisitionCustodyResult]
AcquisitionRecorder = Callable[..., AcquisitionCustodyResult]
ApplyReserver = Callable[..., CanonicalApplyCustodyResult]
ApplyRecorder = Callable[..., CanonicalApplyCustodyResult]
Planner = Callable[..., DailyEodAutomationPlan]


class DailyEodAuthorizedCapabilities:
    """Explicitly installed adapters; construction alone performs no I/O."""

    def __init__(
        self,
        *,
        config: DailyEodAuthorizedCapabilityConfig,
        clock: Clock = lambda: datetime.now(UTC),
        authorization_reader: AuthorizationReader = read_standing_authorization,
        runtime_validator: RuntimeValidator = validate_standing_authorization_runtime,
        authorizer: Authorizer = authorize_standing_transition,
        credential_loader: CredentialLoader = load_massive_provider_config_from_file,
        transport: MassiveHttpTransport | None = None,
        identity_fetcher: Fetcher = fetch_identity_package,
        eod_fetcher: Fetcher = fetch_eod_package,
        apply_executor: ApplyExecutor = apply_approved_plan,
        acquisition_reserver: AcquisitionReserver = reserve_acquisition_attempt,
        acquisition_recorder: AcquisitionRecorder = record_acquisition_outcome,
        apply_reserver: ApplyReserver = reserve_canonical_apply,
        apply_recorder: ApplyRecorder = record_canonical_apply_success,
        planner: Planner = plan_daily_eod_automation,
    ) -> None:
        _validate_config(config)
        self._config = config
        self._clock = clock
        self._authorization_reader = authorization_reader
        self._runtime_validator = runtime_validator
        self._authorizer = authorizer
        self._credential_loader = credential_loader
        self._transport = transport or MassiveUrllibTransport()
        self._identity_fetcher = identity_fetcher
        self._eod_fetcher = eod_fetcher
        self._apply_executor = apply_executor
        self._acquisition_reserver = acquisition_reserver
        self._acquisition_recorder = acquisition_recorder
        self._apply_reserver = apply_reserver
        self._apply_recorder = apply_recorder
        self._planner = planner

    def fetch(self, context: AuthorizedTransitionContext) -> AuthorizedTransitionEvidence:
        """Reserve, authorize, execute, and record one exact provider fetch."""

        operation = _validate_context(self._config, context, apply=False)
        observed = _aware_utc(self._clock())
        authorization = self._read_and_preflight(operation, observed)
        reservation = self._acquisition_reserver(
            config=context.acquisition,
            checked_at=datetime.fromisoformat(context.readiness_plan.checked_at),
            expected_readiness_fingerprint=(
                context.readiness_plan.logical_content_fingerprint
            ),
            authorization_file_sha256=(
                self._config.expected_authorization_file_sha256
            ),
            authorization_content_sha256=(
                authorization.authorization_content_sha256
            ),
            clock=lambda: observed,
        )
        decision = self._authorize(
            authorization,
            _fetch_request(context, operation, reservation, observed),
            observed,
        )
        counting_transport = _CountingTransport(self._transport)
        try:
            provider_config = self._credential_loader(self._config.credential_path)
        except (MassiveCredentialFileError, ValidationError, ValueError):
            return self._record_fetch_outcome(
                context,
                decision,
                AttemptOutcome.PERMANENT_FAILURE,
                request_count=0,
            )
        try:
            fetcher = (
                self._identity_fetcher
                if operation is StandingOperation.FETCH_IDENTITY
                else self._eod_fetcher
            )
            manifest = fetcher(
                config=provider_config,
                transport=counting_transport,
                session_date=context.acquisition.target_session,
                package_path=context.acquisition.package_path,
            )
        except MassiveTransportResponseError as exc:
            outcome, retry_after = _response_outcome(exc)
            return self._record_fetch_outcome(
                context,
                decision,
                outcome,
                request_count=counting_transport.request_count,
                retry_after_seconds=retry_after,
                provider_http_status_code=exc.status_code,
            )
        except (MassiveTransportTimeoutError, MassiveTransportUnavailableError):
            return self._record_fetch_outcome(
                context,
                decision,
                AttemptOutcome.TRANSIENT_FAILURE,
                request_count=counting_transport.request_count,
            )
        except (MassiveTransportDataError, SameDayCatchupError):
            return self._record_fetch_outcome(
                context,
                decision,
                AttemptOutcome.QUALITY_FAILURE,
                request_count=counting_transport.request_count,
            )
        manifest_request_count = getattr(manifest, "request_count", None)
        if (
            type(manifest_request_count) is not int
            or manifest_request_count != counting_transport.request_count
            or not 1 <= counting_transport.request_count <= decision.provider_request_limit
        ):
            raise DailyEodAuthorizedCapabilityError(
                "provider request count differs from formal fetch evidence"
            )
        return self._record_fetch_outcome(
            context,
            decision,
            AttemptOutcome.FETCH_PACKAGE_READY,
            request_count=counting_transport.request_count,
        )

    def apply(self, context: AuthorizedTransitionContext) -> AuthorizedTransitionEvidence:
        """Reserve, authorize, execute, and formally prove one canonical Apply."""

        operation = _validate_context(self._config, context, apply=True)
        approved_plan_sha256, expected_state = _apply_bindings(self._config)
        observed = _aware_utc(self._clock())
        authorization = self._read_and_preflight(operation, observed)
        current = self._planner(
            target_session=context.acquisition.target_session,
            paths=self._config.automation_paths,
        )
        if (
            not isinstance(current, DailyEodAutomationPlan)
            or current.logical_content_fingerprint
            != context.automation_plan.logical_content_fingerprint
        ):
            raise DailyEodAuthorizedCapabilityError(
                "coordinator automation plan changed before Apply reservation"
            )
        apply_config = DailyEodCanonicalApplyConfig(
            target_session=context.acquisition.target_session,
            latest_canonical_session=context.acquisition.latest_canonical_session,
            acquisition_action=context.acquisition.acquisition_action,
            package_path=context.acquisition.package_path,
            approval_plan_path=context.approval_plan_path,
            approved_plan_sha256=approved_plan_sha256,
            expected_current_state_fingerprint=expected_state,
            data_root=self._config.data_root,
            run_root=self._config.run_root,
            automation_paths=self._config.automation_paths,
        )
        reservation = self._apply_reserver(
            config=apply_config,
            checked_at=datetime.fromisoformat(context.readiness_plan.checked_at),
            expected_readiness_fingerprint=(
                context.readiness_plan.logical_content_fingerprint
            ),
            authorization_file_sha256=(
                self._config.expected_authorization_file_sha256
            ),
            authorization_content_sha256=(
                authorization.authorization_content_sha256
            ),
            clock=lambda: observed,
        )
        if reservation.plan_evidence is None:
            raise DailyEodAuthorizedCapabilityError(
                "Apply reservation returned no formal plan evidence"
            )
        plan_evidence = reservation.plan_evidence
        if (
            plan_evidence.operation != _subject(operation)
            or plan_evidence.session_date != context.acquisition.target_session
            or plan_evidence.plan_path != str(context.approval_plan_path)
            or plan_evidence.plan_file_sha256 != approved_plan_sha256
            or plan_evidence.fetch_package_path
            != str(context.acquisition.package_path)
            or plan_evidence.expected_current_state_fingerprint != expected_state
            or plan_evidence.data_root != str(self._config.data_root)
        ):
            raise DailyEodAuthorizedCapabilityError(
                "Apply reservation evidence differs from exact runtime inputs"
            )
        decision = self._authorize(
            authorization,
            _apply_request(context, operation, reservation, observed),
            observed,
        )
        self._apply_executor(
            plan_path=context.approval_plan_path,
            approved_plan_sha256=approved_plan_sha256,
            expected_current_state_fingerprint=expected_state,
            data_root=self._config.data_root,
            expected_operation=_subject(operation),
            expected_session=context.acquisition.target_session,
        )
        completed = self._apply_recorder(
            config=apply_config,
            authorization_decision_fingerprint=decision.logical_content_fingerprint,
            clock=self._clock,
            planner=self._planner,
        )
        return AuthorizedTransitionEvidence(
            operation=operation.value,
            target_session=context.acquisition.target_session.isoformat(),
            precondition_fingerprint=(
                context.readiness_plan.logical_content_fingerprint
            ),
            outcome="succeeded",
            event_fingerprint=completed.event.event_fingerprint,
            external_request_count=0,
            production_write_count=1,
            reason_code=completed.reason_code,
        )

    def _read_and_preflight(
        self,
        operation: StandingOperation,
        observed: datetime,
    ) -> DailyEodStandingAuthorizationV1:
        authorization = self._authorization_reader(
            authorization_path=self._config.authorization_path,
            authorization_root=self._config.authorization_root,
            repository_root=self._config.repository_root,
            expected_file_sha256=(
                self._config.expected_authorization_file_sha256
            ),
        )
        self._runtime_validator(
            authorization=authorization,
            evaluated_at=observed,
            operation=operation,
            actual_host=self._config.actual_host,
            actual_provider_id=MASSIVE_PROVIDER_ID,
            actual_data_root=self._config.data_root,
            actual_run_root=self._config.run_root,
            actual_implementation_revision=self._config.implementation_revision,
            actual_readiness_policy_fingerprint=(
                self._config.readiness_policy_fingerprint
            ),
        )
        return authorization

    def _authorize(
        self,
        authorization: DailyEodStandingAuthorizationV1,
        request: DailyEodAuthorizedTransitionRequestV1,
        observed: datetime,
    ) -> DailyEodAuthorizationDecision:
        decision = self._authorizer(
            authorization=authorization,
            request=request,
            evaluated_at=observed,
            actual_host=self._config.actual_host,
            actual_provider_id=MASSIVE_PROVIDER_ID,
            actual_data_root=self._config.data_root,
            actual_run_root=self._config.run_root,
            actual_implementation_revision=self._config.implementation_revision,
            actual_readiness_policy_fingerprint=(
                self._config.readiness_policy_fingerprint
            ),
        )
        expected_request_limit = (
            20
            if request.operation is StandingOperation.FETCH_IDENTITY
            else 1 if request.operation is StandingOperation.FETCH_EOD else 0
        )
        expected_write_limit = (
            1
            if request.operation
            in {StandingOperation.APPLY_IDENTITY, StandingOperation.APPLY_EOD}
            else 0
        )
        if (
            not isinstance(decision, DailyEodAuthorizationDecision)
            or not decision.authorized
            or decision.authorization_id != authorization.authorization_id
            or decision.authorization_content_sha256
            != authorization.authorization_content_sha256
            or decision.operation != request.operation.value
            or decision.target_session != request.target_session.isoformat()
            or decision.provider_request_limit != expected_request_limit
            or decision.canonical_write_limit != expected_write_limit
            or decision.publication_authorized
            or decision.deployment_authorized
            or decision.scheduler_authorized
            or not _is_fingerprint(decision.request_fingerprint)
            or not _is_fingerprint(decision.logical_content_fingerprint)
        ):
            raise DailyEodAuthorizedCapabilityError(
                "standing authorization decision evidence is invalid"
            )
        return decision

    def _record_fetch_outcome(
        self,
        context: AuthorizedTransitionContext,
        decision: DailyEodAuthorizationDecision,
        outcome: AttemptOutcome,
        *,
        request_count: int,
        retry_after_seconds: int | None = None,
        provider_http_status_code: int | None = None,
    ) -> AuthorizedTransitionEvidence:
        if not 0 <= request_count <= decision.provider_request_limit:
            raise DailyEodAuthorizedCapabilityError(
                "provider request count exceeds authorization"
            )
        recorded = self._acquisition_recorder(
            config=context.acquisition,
            outcome=outcome,
            retry_after_seconds=retry_after_seconds,
            request_count=request_count,
            provider_http_status_code=provider_http_status_code,
            authorization_decision_fingerprint=decision.logical_content_fingerprint,
            clock=self._clock,
        )
        return AuthorizedTransitionEvidence(
            operation=decision.operation,
            target_session=context.acquisition.target_session.isoformat(),
            precondition_fingerprint=(
                context.readiness_plan.logical_content_fingerprint
            ),
            outcome=(
                "succeeded"
                if outcome is AttemptOutcome.FETCH_PACKAGE_READY
                else "failed"
                if outcome
                in {AttemptOutcome.PERMANENT_FAILURE, AttemptOutcome.QUALITY_FAILURE}
                else "waiting"
            ),
            event_fingerprint=recorded.event.event_fingerprint,
            external_request_count=request_count,
            production_write_count=0,
            reason_code=recorded.reason_code,
        )


class _CountingTransport:
    def __init__(self, delegate: MassiveHttpTransport) -> None:
        self._delegate = delegate
        self.request_count = 0

    def get_json(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        self.request_count += 1
        return self._delegate.get_json(*args, **kwargs)


def _fetch_request(
    context: AuthorizedTransitionContext,
    operation: StandingOperation,
    reservation: AcquisitionCustodyResult,
    requested_at: datetime,
) -> DailyEodAuthorizedTransitionRequestV1:
    return DailyEodAuthorizedTransitionRequestV1(
        requested_at=requested_at,
        operation=operation,
        target_session=context.acquisition.target_session,
        latest_canonical_session=context.acquisition.latest_canonical_session,
        acquisition_action=context.acquisition.acquisition_action,
        custody_attempt_id=reservation.attempt_id,
        custody_event_type=reservation.event.event_type,
        custody_event_fingerprint=reservation.event.event_fingerprint,
        readiness_policy_fingerprint=context.readiness_plan.policy_fingerprint,
        readiness_plan_fingerprint=context.readiness_plan.logical_content_fingerprint,
        package_path=str(context.acquisition.package_path),
    )


def _apply_request(
    context: AuthorizedTransitionContext,
    operation: StandingOperation,
    reservation: CanonicalApplyCustodyResult,
    requested_at: datetime,
) -> DailyEodAuthorizedTransitionRequestV1:
    evidence = reservation.plan_evidence
    if evidence is None:
        raise DailyEodAuthorizedCapabilityError(
            "Apply authorization requires formal plan evidence"
        )
    return DailyEodAuthorizedTransitionRequestV1(
        requested_at=requested_at,
        operation=operation,
        target_session=context.acquisition.target_session,
        latest_canonical_session=context.acquisition.latest_canonical_session,
        acquisition_action=context.acquisition.acquisition_action,
        custody_attempt_id=reservation.attempt_id,
        custody_event_type=reservation.event.event_type,
        custody_event_fingerprint=reservation.event.event_fingerprint,
        readiness_policy_fingerprint=context.readiness_plan.policy_fingerprint,
        readiness_plan_fingerprint=context.readiness_plan.logical_content_fingerprint,
        package_path=str(context.acquisition.package_path),
        package_manifest_sha256=evidence.fetch_package_manifest_sha256,
        package_content_sha256=evidence.fetch_package_content_sha256,
        approval_plan_path=str(context.approval_plan_path),
        approval_plan_sha256=evidence.plan_file_sha256,
        expected_current_state_fingerprint=(
            evidence.expected_current_state_fingerprint
        ),
    )


def _validate_context(
    config: DailyEodAuthorizedCapabilityConfig,
    context: AuthorizedTransitionContext,
    *,
    apply: bool,
) -> StandingOperation:
    if not isinstance(context, AuthorizedTransitionContext):
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability context is invalid"
        )
    try:
        operation = StandingOperation(context.operation)
    except ValueError as exc:
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability operation is invalid"
        ) from exc
    expected_prefix = "apply_" if apply else "fetch_"
    expected_action = (
        NextAction.PREPARE_IDENTITY_CATCHUP
        if operation in {StandingOperation.FETCH_IDENTITY, StandingOperation.APPLY_IDENTITY}
        else NextAction.PREPARE_EOD_CATCHUP
    )
    expected_readiness = (
        ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION
        if apply
        else ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
    )
    acquisition = context.acquisition
    if (
        not operation.value.startswith(expected_prefix)
        or acquisition.acquisition_action is not expected_action
        or acquisition.run_root != config.run_root
    ):
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability context differs from runtime configuration"
        )
    try:
        validate_daily_eod_data_artifact_pair(
            package_path=acquisition.package_path,
            plan_path=context.approval_plan_path,
            expected_session=acquisition.target_session,
        )
    except OfflineArtifactCustodyError as exc:
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability context differs from runtime configuration"
        ) from exc
    if (
        context.readiness_plan.next_action is not expected_readiness
        or context.readiness_plan.target_session
        != acquisition.target_session.isoformat()
        or context.readiness_plan.latest_canonical_session
        != acquisition.latest_canonical_session.isoformat()
        or context.readiness_plan.acquisition_action
        != acquisition.acquisition_action.value
        or context.readiness_plan.policy_fingerprint
        != config.readiness_policy_fingerprint
        or context.automation_plan.target_session
        != acquisition.target_session.isoformat()
    ):
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability plans are stale or mismatched"
        )
    return operation


def _apply_bindings(
    config: DailyEodAuthorizedCapabilityConfig,
) -> tuple[str, str]:
    if not _is_fingerprint(config.approved_plan_sha256) or not _is_fingerprint(
        config.expected_current_state_fingerprint
    ):
        raise DailyEodAuthorizedCapabilityError(
            "Apply capability requires exact approved plan and state fingerprints"
        )
    return config.approved_plan_sha256, config.expected_current_state_fingerprint


def _response_outcome(
    error: MassiveTransportResponseError,
) -> tuple[AttemptOutcome, int | None]:
    if error.status_code == 404:
        return AttemptOutcome.NOT_READY, None
    if error.status_code == 429:
        return AttemptOutcome.RATE_LIMITED, error.retry_after_seconds
    return AttemptOutcome.PERMANENT_FAILURE, None


def _subject(operation: StandingOperation) -> str:
    return "identity" if operation is StandingOperation.APPLY_IDENTITY else "eod"


def _validate_config(config: DailyEodAuthorizedCapabilityConfig) -> None:
    if (
        config.data_root != APPROVED_CANONICAL_DATA_ROOT
        or config.automation_paths.data_root != config.data_root
        or not config.run_root.is_absolute()
        or not config.repository_root.is_absolute()
        or not config.authorization_root.is_absolute()
        or config.authorization_path.parent != config.authorization_root
        or not _is_fingerprint(config.expected_authorization_file_sha256)
        or not _is_revision(config.implementation_revision)
        or not _is_fingerprint(config.readiness_policy_fingerprint)
    ):
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability configuration is invalid"
        )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodAuthorizedCapabilityError(
            "authorized capability timestamp must be timezone-aware"
        )
    return value.astimezone(UTC)


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
