"""Default-disabled SMTP delivery behind immutable daily alert custody."""

from __future__ import annotations

import hashlib
import json
import os
import re
import smtplib
import ssl
import stat
from datetime import UTC, datetime
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import to_jsonable_python

from tip_api.services.daily_eod_alert_custody import (
    AlertDeliveryContext,
    AlertDeliveryEvidence,
    DailyEodAlertCustodyConfig,
)
from tip_api.services.daily_eod_alerting import validate_daily_eod_alert_intent
from tip_api.services.daily_eod_host_runtime import VerifiedDellRuntime
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
)


CONTRACT_VERSION = "daily-eod-email-transport-config/1.0"
CHANNEL = "email"
MAXIMUM_CONFIG_BYTES = 64 * 1024
MAXIMUM_MESSAGE_BYTES = 64 * 1024
USERNAME_KEY = "TIP_SMTP_USERNAME"
PASSWORD_KEY = "TIP_SMTP_PASSWORD"
_ALLOWED_CREDENTIAL_KEYS = frozenset({USERNAME_KEY, PASSWORD_KEY})
_HOSTNAME = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
)
_EMAIL = re.compile(
    r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


class DailyEodEmailConfigError(RuntimeError):
    """Raised when external email configuration is not exact and safe."""


class DailyEodEmailCredentialError(RuntimeError):
    """Raised without secret content when credential custody is invalid."""


class DailyEodEmailTransportError(RuntimeError):
    """Raised when an initiated SMTP transaction has an unknown outcome."""


class DailyEodEmailTransportConfigV1(BaseModel):
    """Externally installed SMTP policy; absence or disabled means no delivery."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-email-transport-config/1.0"] = (
        CONTRACT_VERSION
    )
    config_id: str = Field(
        min_length=16,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.:-]+$",
    )
    host: Literal["dell5820"]
    channel: Literal["email"] = CHANNEL
    repository_root: str
    implementation_revision: str
    data_root: str
    run_root: str
    alert_root: str
    smtp_host: str
    smtp_port: int
    transport_security: Literal["implicit_tls", "starttls"]
    sender_email: str
    recipient_emails: tuple[str, ...]
    credential_path: str
    connect_timeout_seconds: int = Field(ge=5, le=60)
    enabled: bool
    one_message_per_invocation: Literal[True] = True
    scheduler_enabled: Literal[False] = False
    publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    maximum_message_bytes: Literal[65536] = MAXIMUM_MESSAGE_BYTES
    config_content_sha256: str

    @model_validator(mode="after")
    def validate_exact_boundaries(self) -> "DailyEodEmailTransportConfigV1":
        repository_root = Path(self.repository_root)
        data_root = Path(self.data_root)
        run_root = Path(self.run_root)
        alert_root = Path(self.alert_root)
        credential_path = Path(self.credential_path)
        roots = (repository_root, data_root, run_root, alert_root)
        if (
            not all(path.is_absolute() for path in (*roots, credential_path))
            or data_root != APPROVED_CANONICAL_DATA_ROOT
            or any(_is_within(alert_root, root) or _is_within(root, alert_root) for root in roots[:3])
            or any(_is_within(credential_path, root) for root in roots)
            or credential_path.name.startswith(".")
            or credential_path.suffix != ".env"
        ):
            raise ValueError("email transport path boundary is invalid")
        if not _is_revision(self.implementation_revision):
            raise ValueError("email transport implementation revision is malformed")
        if (
            _HOSTNAME.fullmatch(self.smtp_host) is None
            or self.smtp_host != self.smtp_host.lower()
            or (self.transport_security, self.smtp_port)
            not in {("implicit_tls", 465), ("starttls", 587)}
        ):
            raise ValueError("email transport SMTP boundary is invalid")
        if (
            _EMAIL.fullmatch(self.sender_email) is None
            or self.sender_email != self.sender_email.lower()
            or not 1 <= len(self.recipient_emails) <= 5
            or tuple(sorted(set(self.recipient_emails))) != self.recipient_emails
            or any(
                _EMAIL.fullmatch(address) is None or address != address.lower()
                for address in self.recipient_emails
            )
        ):
            raise ValueError("email transport address boundary is invalid")
        if not _is_fingerprint(self.config_content_sha256):
            raise ValueError("email transport content fingerprint is malformed")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"config_content_sha256"})
        )
        if self.config_content_sha256 != expected:
            raise ValueError("email transport content fingerprint mismatch")
        return self


class SmtpCredential:
    """In-memory secret with a deliberately redacted representation."""

    __slots__ = ("_password", "_username")

    def __init__(self, *, username: str, password: str) -> None:
        if not _safe_secret(username) or not _safe_secret(password):
            raise DailyEodEmailCredentialError("SMTP credential value is invalid")
        self._username = username
        self._password = password

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    def __repr__(self) -> str:
        return "SmtpCredential(username=<redacted>, password=<redacted>)"


CredentialLoader = Callable[[Path], SmtpCredential]
Clock = Callable[[], datetime]
SmtpSender = Callable[
    [DailyEodEmailTransportConfigV1, SmtpCredential, EmailMessage], None
]


def build_email_transport_config_candidate(
    *,
    config_id: str,
    repository_root: Path,
    implementation_revision: str,
    data_root: Path,
    run_root: Path,
    alert_root: Path,
    smtp_host: str,
    smtp_port: int,
    transport_security: Literal["implicit_tls", "starttls"],
    sender_email: str,
    recipient_emails: tuple[str, ...],
    credential_path: Path,
    connect_timeout_seconds: int = 20,
    enabled: bool = False,
) -> DailyEodEmailTransportConfigV1:
    """Build a review candidate without writing config or touching credentials."""

    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "config_id": config_id,
        "host": "dell5820",
        "channel": CHANNEL,
        "repository_root": str(repository_root),
        "implementation_revision": implementation_revision,
        "data_root": str(data_root),
        "run_root": str(run_root),
        "alert_root": str(alert_root),
        "smtp_host": smtp_host.strip().lower(),
        "smtp_port": smtp_port,
        "transport_security": transport_security,
        "sender_email": sender_email.strip().lower(),
        "recipient_emails": tuple(
            sorted({address.strip().lower() for address in recipient_emails})
        ),
        "credential_path": str(credential_path),
        "connect_timeout_seconds": connect_timeout_seconds,
        "enabled": enabled,
        "one_message_per_invocation": True,
        "scheduler_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "maximum_message_bytes": MAXIMUM_MESSAGE_BYTES,
    }
    return DailyEodEmailTransportConfigV1.model_validate(
        {**base, "config_content_sha256": _fingerprint(base)}
    )


def canonical_email_transport_config_bytes(
    config: DailyEodEmailTransportConfigV1,
) -> bytes:
    return _canonical_bytes(config.model_dump(mode="json"))


def read_email_transport_config(
    *,
    config_path: Path,
    config_root: Path,
    repository_root: Path,
    expected_file_sha256: str,
) -> DailyEodEmailTransportConfigV1:
    """Read SHA-pinned owner-only config without touching its credential path."""

    if not _is_fingerprint(expected_file_sha256):
        raise DailyEodEmailConfigError("email transport file SHA is malformed")
    if (
        not config_root.is_absolute()
        or not repository_root.is_absolute()
        or config_path.parent != config_root
        or config_path.name.startswith(".")
        or config_path.suffix != ".json"
        or _is_within(config_root, APPROVED_CANONICAL_DATA_ROOT)
        or _is_within(config_root, repository_root)
    ):
        raise DailyEodEmailConfigError("email transport config path boundary is invalid")
    try:
        root_metadata = config_root.lstat()
        file_metadata = config_path.lstat()
    except OSError as exc:
        raise DailyEodEmailConfigError(
            "email transport config custody is unavailable"
        ) from exc
    if (
        config_root.resolve() != config_root
        or stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or root_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
        or stat.S_ISLNK(file_metadata.st_mode)
        or not stat.S_ISREG(file_metadata.st_mode)
        or file_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(file_metadata.st_mode) != 0o400
        or not 0 < file_metadata.st_size <= MAXIMUM_CONFIG_BYTES
    ):
        raise DailyEodEmailConfigError("email transport config custody is unsafe")
    try:
        raw = config_path.read_bytes()
        config = DailyEodEmailTransportConfigV1.model_validate(json.loads(raw))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DailyEodEmailConfigError("email transport config is invalid") from exc
    if hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        raise DailyEodEmailConfigError("email transport config file SHA mismatch")
    if raw != canonical_email_transport_config_bytes(config):
        raise DailyEodEmailConfigError("email transport config is not canonical")
    if Path(config.repository_root) != repository_root:
        raise DailyEodEmailConfigError("email transport config identity mismatch")
    return config


def load_smtp_credential(path: Path) -> SmtpCredential:
    """Read one minimal owner-only env file without evaluating shell syntax."""

    if not path.is_absolute():
        raise DailyEodEmailCredentialError("SMTP credential path is invalid")
    try:
        parent_metadata = path.parent.lstat()
        file_metadata = path.lstat()
    except OSError as exc:
        raise DailyEodEmailCredentialError("SMTP credential custody is unavailable") from exc
    if (
        path.parent.resolve() != path.parent
        or stat.S_ISLNK(parent_metadata.st_mode)
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
        or stat.S_ISLNK(file_metadata.st_mode)
        or not stat.S_ISREG(file_metadata.st_mode)
        or file_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(file_metadata.st_mode) != 0o400
        or not 0 < file_metadata.st_size <= 16 * 1024
    ):
        raise DailyEodEmailCredentialError("SMTP credential custody is unsafe")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise DailyEodEmailCredentialError("SMTP credential file is invalid") from exc
    values: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export ") or "=" not in stripped:
            raise DailyEodEmailCredentialError(
                f"SMTP credential syntax is invalid on line {line_number}"
            )
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in _ALLOWED_CREDENTIAL_KEYS or key in values or not _safe_secret(value):
            raise DailyEodEmailCredentialError(
                f"SMTP credential entry is invalid on line {line_number}"
            )
        values[key] = value
    if set(values) != _ALLOWED_CREDENTIAL_KEYS:
        raise DailyEodEmailCredentialError("SMTP credential file is incomplete")
    return SmtpCredential(
        username=values[USERNAME_KEY],
        password=values[PASSWORD_KEY],
    )


def render_daily_eod_email(context: AlertDeliveryContext) -> EmailMessage:
    """Render one deterministic bilingual message containing no credentials."""

    validate_daily_eod_alert_intent(context.intent)
    if (
        context.channel != CHANNEL
        or context.idempotency_key != context.intent.deduplication_key
        or not _is_fingerprint(context.attempt_id)
    ):
        raise DailyEodEmailConfigError("email delivery context is inconsistent")
    severity = context.intent.severity.value.upper()
    message = EmailMessage(policy=SMTP)
    message["Subject"] = (
        f"[WH Alpha][{severity}] Daily EOD attention — "
        f"{context.intent.target_session}"
    )
    message["Message-ID"] = (
        f"<whalpha-alert-{context.idempotency_key}@alerts.whalpha.local>"
    )
    message["X-WHAlpha-Deduplication-Key"] = context.idempotency_key
    reasons = ", ".join(context.intent.reason_codes)
    message.set_content(
        "\n".join(
            (
                "WH Alpha daily pipeline requires attention.",
                "WH Alpha 每日流水线需要人工关注。",
                "",
                f"Session / 交易日: {context.intent.target_session}",
                f"Severity / 级别: {context.intent.severity.value}",
                f"Category / 类别: {context.intent.category}",
                f"Status / 状态: {context.intent.coordinator_status}",
                f"Next action / 下一步: {context.intent.next_action}",
                f"Reason codes / 原因代码: {reasons}",
                f"Deduplication key / 去重键: {context.idempotency_key}",
                "",
                "This is an operational alert, not a trading recommendation.",
                "这是运行告警，不是交易建议。",
            )
        ),
        charset="utf-8",
    )
    return message


class DailyEodEmailDeliveryCapability:
    """Callable SMTP adapter whose invocation is owned by ADR 0040 custody."""

    def __init__(
        self,
        *,
        config: DailyEodEmailTransportConfigV1,
        custody_config: DailyEodAlertCustodyConfig,
        verified_runtime: VerifiedDellRuntime,
        credential_loader: CredentialLoader = load_smtp_credential,
        smtp_sender: SmtpSender | None = None,
        clock: Clock = lambda: datetime.now(UTC),
    ) -> None:
        _validate_bindings(config, custody_config, verified_runtime)
        if not config.enabled:
            raise DailyEodEmailConfigError("email transport is disabled")
        if not callable(credential_loader):
            raise DailyEodEmailConfigError("SMTP credential loader is absent")
        self._config = config
        self._credential_loader = credential_loader
        self._smtp_sender = send_smtp_message if smtp_sender is None else smtp_sender
        if not callable(self._smtp_sender):
            raise DailyEodEmailConfigError("SMTP sender is absent")
        if not callable(clock):
            raise DailyEodEmailConfigError("email delivery clock is absent")
        self._clock = clock

    def __call__(self, context: AlertDeliveryContext) -> AlertDeliveryEvidence:
        if context.channel != CHANNEL:
            raise DailyEodEmailConfigError("email delivery channel is inconsistent")
        message = render_daily_eod_email(context)
        message["From"] = self._config.sender_email
        message["To"] = ", ".join(self._config.recipient_emails)
        observed_at = self._clock()
        if (
            not isinstance(observed_at, datetime)
            or observed_at.tzinfo is None
            or observed_at.utcoffset() is None
        ):
            raise DailyEodEmailConfigError("email delivery clock is invalid")
        message["Date"] = format_datetime(observed_at.astimezone(UTC))
        if len(message.as_bytes(policy=SMTP)) > self._config.maximum_message_bytes:
            return _failed(context, "email_message_exceeds_limit")
        try:
            credential = self._credential_loader(Path(self._config.credential_path))
        except DailyEodEmailCredentialError:
            return _failed(context, "email_credential_rejected_before_request")
        if not isinstance(credential, SmtpCredential):
            return _failed(context, "email_credential_rejected_before_request")
        self._smtp_sender(self._config, credential, message)
        message_id = str(message["Message-ID"])
        return AlertDeliveryEvidence(
            channel=CHANNEL,
            deduplication_key=context.idempotency_key,
            outcome="delivered",
            external_request_count=1,
            delivery_reference_fingerprint=hashlib.sha256(
                message_id.encode("ascii")
            ).hexdigest(),
            reason_code="smtp_message_accepted",
        )


def send_smtp_message(
    config: DailyEodEmailTransportConfigV1,
    credential: SmtpCredential,
    message: EmailMessage,
) -> None:
    """Perform one SMTP delivery transaction with certificate verification."""

    context = ssl.create_default_context()
    try:
        if config.transport_security == "implicit_tls":
            client = smtplib.SMTP_SSL(
                config.smtp_host,
                config.smtp_port,
                timeout=config.connect_timeout_seconds,
                context=context,
            )
        else:
            client = smtplib.SMTP(
                config.smtp_host,
                config.smtp_port,
                timeout=config.connect_timeout_seconds,
            )
        with client:
            if config.transport_security == "starttls":
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(credential.username, credential.password)
            refused = client.send_message(message)
            if refused:
                raise DailyEodEmailTransportError(
                    "SMTP recipient acceptance is incomplete"
                )
    except DailyEodEmailTransportError:
        raise
    except (OSError, smtplib.SMTPException) as exc:
        raise DailyEodEmailTransportError(
            "SMTP delivery outcome is unknown; automatic retry is prohibited"
        ) from exc


def _validate_bindings(
    config: DailyEodEmailTransportConfigV1,
    custody: DailyEodAlertCustodyConfig,
    runtime: VerifiedDellRuntime,
) -> None:
    try:
        validated_config = DailyEodEmailTransportConfigV1.model_validate(
            config.model_dump(mode="json")
        )
    except (AttributeError, ValueError) as exc:
        raise DailyEodEmailConfigError(
            "email transport config is invalid"
        ) from exc
    if (
        validated_config != config
        or not isinstance(custody, DailyEodAlertCustodyConfig)
        or not isinstance(runtime, VerifiedDellRuntime)
        or custody.channel != CHANNEL
        or Path(config.repository_root) != custody.repository_root
        or Path(config.data_root) != custody.data_root
        or Path(config.run_root) != custody.run_root
        or Path(config.alert_root) != custody.alert_root
        or config.host != runtime.host
        or config.repository_root != runtime.repository_root
        or config.implementation_revision != runtime.implementation_revision
        or not runtime.worktree_clean
    ):
        raise DailyEodEmailConfigError("email transport runtime binding is invalid")


def _failed(context: AlertDeliveryContext, reason: str) -> AlertDeliveryEvidence:
    return AlertDeliveryEvidence(
        channel=CHANNEL,
        deduplication_key=context.idempotency_key,
        outcome="failed",
        external_request_count=0,
        delivery_reference_fingerprint=None,
        reason_code=reason,
    )


def _safe_secret(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= 4096
        and "\n" not in value
        and "\r" not in value
        and "\x00" not in value
        and "$(" not in value
        and "`" not in value
    )


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
