"""Channel-neutral, non-delivering alert intents for the daily EOD control plane."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum

from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
)


CONTRACT_VERSION = "daily-eod-alert-intent/1.0"


class DailyEodAlertingError(RuntimeError):
    """Raised when a coordinator result cannot form one safe alert intent."""


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class DailyEodAlertIntent:
    contract_version: str
    target_session: str
    category: str
    severity: AlertSeverity
    coordinator_status: str
    next_action: str
    reason_codes: tuple[str, ...]
    source_fingerprint: str
    deduplication_key: str
    delivery_attempted: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["severity"] = self.severity.value
        return value


def plan_daily_eod_alert(
    *,
    target_session: date,
    result: DailyEodCoordinatorResult,
) -> DailyEodAlertIntent | None:
    """Return one stable alert intent without delivering or persisting it."""

    if not isinstance(result, DailyEodCoordinatorResult):
        raise DailyEodAlertingError("alert source result is invalid")
    if not result.alert_required:
        return None
    if (
        result.target_session != target_session.isoformat()
        or not _is_fingerprint(result.logical_content_fingerprint)
        or not result.next_action
        or not result.reason_codes
        or any(not reason for reason in result.reason_codes)
    ):
        raise DailyEodAlertingError("alert source evidence is malformed")
    category, severity = _classification(result.status)
    deduplication_key = _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_session": result.target_session,
            "category": category,
            "source_fingerprint": result.logical_content_fingerprint,
        }
    )
    base = {
        "contract_version": CONTRACT_VERSION,
        "target_session": result.target_session,
        "category": category,
        "severity": severity,
        "coordinator_status": result.status.value,
        "next_action": result.next_action,
        "reason_codes": result.reason_codes,
        "source_fingerprint": result.logical_content_fingerprint,
        "deduplication_key": deduplication_key,
        "delivery_attempted": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return DailyEodAlertIntent(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )


def _classification(
    status: CoordinatorStatus,
) -> tuple[str, AlertSeverity]:
    if status is CoordinatorStatus.BLOCKED:
        return "pipeline_blocked", AlertSeverity.CRITICAL
    if status is CoordinatorStatus.RECOVERY_REQUIRED:
        return "interrupted_transition", AlertSeverity.WARNING
    if status is CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED:
        return "missed_session_attention", AlertSeverity.WARNING
    raise DailyEodAlertingError("alert-required coordinator status is unsupported")


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=lambda item: item.value if isinstance(item, StrEnum) else str(item),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
