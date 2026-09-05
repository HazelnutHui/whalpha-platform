"""Fingerprint-bound routing for historical Identity reconstruction profiles."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import date, datetime
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.contracts.common import normalize_utc_datetime

CURRENT_IDENTITY_REBUILD_PROFILE = "current_v1"
PRE_ETV_IDENTITY_REBUILD_PROFILE = "pre_etv_governance_v1"
PROFILE_MAP_CONTRACT_VERSION = "historical-identity-rebuild-profile-map/1.1"
LEGACY_PROFILE_MAP_CONTRACT_VERSION = "historical-identity-rebuild-profile-map/1.0"
HistoricalIdentityRebuildProfile: TypeAlias = Literal[
    "current_v1",
    "pre_etv_governance_v1",
]
CandidateStatus: TypeAlias = Literal[
    "exact_equivalent",
    "identity_snapshot_mismatch",
    "package_custody_failed",
]
SessionStatus: TypeAlias = Literal[
    "missing_source",
    "package_custody_failed",
    "identity_snapshot_mismatch",
    "exact_equivalent",
    "duplicate_source_review_required",
    "canonical_identity_unavailable",
]

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SESSION_STATUSES = (
    "canonical_identity_unavailable",
    "duplicate_source_review_required",
    "exact_equivalent",
    "identity_snapshot_mismatch",
    "missing_source",
    "package_custody_failed",
)


class HistoricalIdentityRebuildProfileMapError(RuntimeError):
    """Fail-closed error at the census-to-profile-map boundary."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class _CensusCandidateV1(_FrozenModel):
    source_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_content_sha256: str = Field(pattern=_SHA256_PATTERN)
    fetched_at: datetime
    status: CandidateStatus
    rebuilt_instrument_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    rebuilt_identity_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    rebuilt_resolver_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    instrument_match: bool | None
    identity_match: bool | None
    resolver_match: bool | None

    @model_validator(mode="after")
    def candidate_shape_reconciles(self) -> "_CensusCandidateV1":
        normalize_utc_datetime(self.fetched_at)
        values = (
            self.rebuilt_instrument_fingerprint,
            self.rebuilt_identity_fingerprint,
            self.rebuilt_resolver_fingerprint,
            self.instrument_match,
            self.identity_match,
            self.resolver_match,
        )
        if self.status == "package_custody_failed":
            if any(item is not None for item in values):
                raise ValueError(
                    "custody-failed census candidate carries rebuild evidence"
                )
        elif any(item is None for item in values):
            raise ValueError("validated census candidate lacks rebuild evidence")
        if self.status == "exact_equivalent" and (
            self.instrument_match,
            self.identity_match,
            self.resolver_match,
        ) != (True, True, True):
            raise ValueError("exact census candidate has non-exact match flags")
        return self


class _CensusSessionV1(_FrozenModel):
    session_date: date
    status: SessionStatus
    candidate_count: int = Field(ge=0)
    custody_valid_candidate_count: int = Field(ge=0)
    exact_equivalent_candidate_count: int = Field(ge=0)
    canonical_snapshot_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    canonical_instrument_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    canonical_identity_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    canonical_resolver_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    candidates: tuple[_CensusCandidateV1, ...]

    @model_validator(mode="after")
    def session_counts_reconcile(self) -> "_CensusSessionV1":
        if self.status != "canonical_identity_unavailable" and (
            self.candidate_count != len(self.candidates)
        ):
            raise ValueError("census session candidate count differs")
        custody_count = sum(
            item.status != "package_custody_failed" for item in self.candidates
        )
        exact_count = sum(
            item.status == "exact_equivalent" for item in self.candidates
        )
        if self.status != "canonical_identity_unavailable" and (
            self.custody_valid_candidate_count != custody_count
            or self.exact_equivalent_candidate_count != exact_count
        ):
            raise ValueError("census session validation counts differ")
        return self


class _CensusReportV1(_FrozenModel):
    contract_version: Literal["1.0", "1.1"]
    rebuild_profile: HistoricalIdentityRebuildProfile | None = None
    scope: Literal["full_canonical_index", "bounded_sample"]
    evaluated_at: datetime
    canonical_session_count: int = Field(ge=1)
    evaluated_session_count: int = Field(ge=1)
    worker_count: int = Field(ge=1, le=4)
    canonical_session_index_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    package_root_count: int = Field(ge=1)
    discovered_identity_package_count: int = Field(ge=0)
    ignored_non_identity_package_count: int = Field(ge=0)
    unroutable_manifest_count: int = Field(ge=0)
    outside_canonical_session_package_count: int = Field(ge=0)
    discovered_package_inventory_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    exact_equivalent_session_count: int = Field(ge=0)
    duplicate_source_session_count: int = Field(ge=0)
    status_counts: tuple[tuple[SessionStatus, int], ...]
    sessions: tuple[_CensusSessionV1, ...]
    external_request_count: Literal[0]
    canonical_data_write_count: Literal[0]

    @model_validator(mode="after")
    def report_reconciles(self) -> "_CensusReportV1":
        normalize_utc_datetime(self.evaluated_at)
        if self.contract_version == "1.0" and self.rebuild_profile is not None:
            raise ValueError("census contract 1.0 cannot declare a profile")
        if self.contract_version == "1.1" and self.rebuild_profile is None:
            raise ValueError("census contract 1.1 requires a profile")
        session_dates = tuple(item.session_date for item in self.sessions)
        if (
            session_dates != tuple(sorted(session_dates))
            or len(session_dates) != len(set(session_dates))
            or len(self.sessions) != self.evaluated_session_count
        ):
            raise ValueError("census report sessions are not a complete ordered set")
        calculated_status_counts = tuple(
            (status, sum(item.status == status for item in self.sessions))
            for status in _SESSION_STATUSES
        )
        if self.status_counts != calculated_status_counts:
            raise ValueError("census status counts differ from sessions")
        if self.exact_equivalent_session_count != sum(
            item.status == "exact_equivalent" for item in self.sessions
        ):
            raise ValueError("census exact count differs from sessions")
        if self.duplicate_source_session_count != sum(
            item.status == "duplicate_source_review_required"
            for item in self.sessions
        ):
            raise ValueError("census duplicate count differs from sessions")
        return self


class HistoricalIdentityRebuildProfileBindingV1(_FrozenModel):
    session_date: date
    rebuild_profile: HistoricalIdentityRebuildProfile
    source_locator_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_content_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_fetched_at: datetime
    canonical_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_instrument_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_identity_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_resolver_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def binding_fingerprint_reconciles(
        self,
    ) -> "HistoricalIdentityRebuildProfileBindingV1":
        normalize_utc_datetime(self.package_fetched_at)
        expected = historical_identity_profile_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("historical Identity profile binding fingerprint mismatch")
        return self


class HistoricalIdentityRebuildProfileMapV1(_FrozenModel):
    contract_version: Literal[
        "historical-identity-rebuild-profile-map/1.0",
        "historical-identity-rebuild-profile-map/1.1",
    ] = PROFILE_MAP_CONTRACT_VERSION
    generated_at: datetime
    current_census_contract_version: Literal["1.0", "1.1"]
    current_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    legacy_census_contract_version: Literal["1.1"]
    legacy_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    canonical_session_count: int = Field(ge=1)
    bound_session_count: int = Field(ge=0)
    missing_session_dates: tuple[date, ...]
    unbound_identity_mismatch_session_dates: tuple[date, ...] = ()
    profile_counts: tuple[tuple[HistoricalIdentityRebuildProfile, int], ...]
    canonical_session_index_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    discovered_package_inventory_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    bindings: tuple[HistoricalIdentityRebuildProfileBindingV1, ...]
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def map_reconciles(self) -> "HistoricalIdentityRebuildProfileMapV1":
        normalize_utc_datetime(self.generated_at)
        sessions = tuple(item.session_date for item in self.bindings)
        if sessions != tuple(sorted(sessions)) or len(sessions) != len(set(sessions)):
            raise ValueError("profile-map bindings are not a unique ordered set")
        if self.missing_session_dates != tuple(sorted(self.missing_session_dates)):
            raise ValueError("profile-map missing sessions are not ordered")
        if len(self.missing_session_dates) != len(set(self.missing_session_dates)):
            raise ValueError("profile-map missing sessions are not unique")
        if self.unbound_identity_mismatch_session_dates != tuple(
            sorted(self.unbound_identity_mismatch_session_dates)
        ) or len(self.unbound_identity_mismatch_session_dates) != len(
            set(self.unbound_identity_mismatch_session_dates)
        ):
            raise ValueError("profile-map mismatch sessions are not unique and ordered")
        if (
            self.contract_version == LEGACY_PROFILE_MAP_CONTRACT_VERSION
            and self.unbound_identity_mismatch_session_dates
        ):
            raise ValueError("profile-map 1.0 cannot carry mismatch sessions")
        bound = set(sessions)
        missing = set(self.missing_session_dates)
        mismatched = set(self.unbound_identity_mismatch_session_dates)
        if bound & missing or bound & mismatched or missing & mismatched:
            raise ValueError("profile-map session classes overlap")
        if (
            self.bound_session_count != len(self.bindings)
            or self.canonical_session_count
            != self.bound_session_count
            + len(self.missing_session_dates)
            + len(self.unbound_identity_mismatch_session_dates)
        ):
            raise ValueError("profile-map coverage counts differ")
        calculated_counts = tuple(
            (profile, sum(item.rebuild_profile == profile for item in self.bindings))
            for profile in (
                CURRENT_IDENTITY_REBUILD_PROFILE,
                PRE_ETV_IDENTITY_REBUILD_PROFILE,
            )
        )
        if self.profile_counts != calculated_counts:
            raise ValueError("profile-map profile counts differ from bindings")
        fingerprint_exclusions = {"logical_fingerprint"}
        if self.contract_version == LEGACY_PROFILE_MAP_CONTRACT_VERSION:
            fingerprint_exclusions.add("unbound_identity_mismatch_session_dates")
        expected = historical_identity_profile_fingerprint(
            self.model_dump(mode="json", exclude=fingerprint_exclusions)
        )
        if self.logical_fingerprint != expected:
            raise ValueError("historical Identity profile-map fingerprint mismatch")
        return self


def build_historical_identity_rebuild_profile_map(
    *,
    current_census_report_path: Path,
    legacy_census_report_path: Path,
    generated_at: datetime,
) -> HistoricalIdentityRebuildProfileMapV1:
    """Create one exact routing map from complementary full census reports."""

    generated_at = normalize_utc_datetime(generated_at)
    current, current_sha = _read_census_report(current_census_report_path)
    legacy, legacy_sha = _read_census_report(legacy_census_report_path)
    _validate_report_profiles(current=current, legacy=legacy)
    _validate_shared_report_scope(current=current, legacy=legacy)

    bindings: list[HistoricalIdentityRebuildProfileBindingV1] = []
    missing_sessions: list[date] = []
    mismatch_sessions: list[date] = []
    for current_session, legacy_session in zip(current.sessions, legacy.sessions):
        _validate_shared_session(current=current_session, legacy=legacy_session)
        if current_session.status == legacy_session.status == "missing_source":
            _validate_missing_pair(current_session, legacy_session)
            missing_sessions.append(current_session.session_date)
            continue
        if (
            current_session.status
            == legacy_session.status
            == "identity_snapshot_mismatch"
        ):
            _validate_unbound_mismatch_pair(current_session, legacy_session)
            mismatch_sessions.append(current_session.session_date)
            continue
        profile, exact_session, mismatch_session = _select_exact_profile(
            current=current_session,
            legacy=legacy_session,
        )
        _validate_complementary_candidates(
            exact=exact_session,
            mismatch=mismatch_session,
        )
        candidate = exact_session.candidates[0]
        binding_base: dict[str, object] = {
            "session_date": exact_session.session_date,
            "rebuild_profile": profile,
            "source_locator_sha256": candidate.source_locator_sha256,
            "package_manifest_sha256": candidate.package_manifest_sha256,
            "package_content_sha256": candidate.package_content_sha256,
            "package_fetched_at": candidate.fetched_at,
            "canonical_snapshot_fingerprint": (
                exact_session.canonical_snapshot_fingerprint
            ),
            "canonical_instrument_fingerprint": (
                exact_session.canonical_instrument_fingerprint
            ),
            "canonical_identity_fingerprint": (
                exact_session.canonical_identity_fingerprint
            ),
            "canonical_resolver_fingerprint": (
                exact_session.canonical_resolver_fingerprint
            ),
        }
        bindings.append(
            HistoricalIdentityRebuildProfileBindingV1.model_validate(
                {
                    **binding_base,
                    "logical_fingerprint": historical_identity_profile_fingerprint(
                        _json_ready(binding_base)
                    ),
                }
            )
        )

    profile_counts = tuple(
        (profile, sum(item.rebuild_profile == profile for item in bindings))
        for profile in (
            CURRENT_IDENTITY_REBUILD_PROFILE,
            PRE_ETV_IDENTITY_REBUILD_PROFILE,
        )
    )
    map_base: dict[str, object] = {
        "contract_version": PROFILE_MAP_CONTRACT_VERSION,
        "generated_at": generated_at,
        "current_census_contract_version": current.contract_version,
        "current_census_report_sha256": current_sha,
        "legacy_census_contract_version": legacy.contract_version,
        "legacy_census_report_sha256": legacy_sha,
        "canonical_session_count": current.canonical_session_count,
        "bound_session_count": len(bindings),
        "missing_session_dates": tuple(missing_sessions),
        "unbound_identity_mismatch_session_dates": tuple(mismatch_sessions),
        "profile_counts": profile_counts,
        "canonical_session_index_fingerprint": (
            current.canonical_session_index_fingerprint
        ),
        "discovered_package_inventory_fingerprint": (
            current.discovered_package_inventory_fingerprint
        ),
        "bindings": tuple(bindings),
        "external_request_count": 0,
        "canonical_data_write_count": 0,
    }
    return HistoricalIdentityRebuildProfileMapV1.model_validate(
        {
            **map_base,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                _json_ready(map_base)
            ),
        }
    )


def read_historical_identity_rebuild_profile_map(
    path: Path,
) -> HistoricalIdentityRebuildProfileMapV1:
    """Formally reread one immutable owner-only profile map below /tmp."""

    raw = _read_owner_only_tmp_file(path, description="profile map")
    try:
        return HistoricalIdentityRebuildProfileMapV1.model_validate_json(raw)
    except Exception as exc:
        raise HistoricalIdentityRebuildProfileMapError(
            "historical Identity profile map is invalid"
        ) from exc


def profile_binding_for_session(
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    session_date: date,
) -> HistoricalIdentityRebuildProfileBindingV1:
    """Select one explicit binding; missing sessions remain fail-closed."""

    for binding in profile_map.bindings:
        if binding.session_date == session_date:
            return binding
    raise HistoricalIdentityRebuildProfileMapError(
        "session is not bound in the historical Identity profile map"
    )


def write_historical_identity_rebuild_profile_map(
    *,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    output_path: Path,
) -> Path:
    """Atomically write one owner-only profile map below /tmp without replacement."""

    target = _new_tmp_output_path(output_path)
    raw = (
        json.dumps(
            profile_map.model_dump(mode="json"),
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")
    staging = target.parent / f".{target.name}.staging"
    if staging.exists() or staging.is_symlink():
        raise HistoricalIdentityRebuildProfileMapError(
            "profile-map staging path already exists"
        )
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        staging.replace(target)
        directory_descriptor = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            staging.unlink()
        raise
    return target


def historical_identity_profile_fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_census_report(path: Path) -> tuple[_CensusReportV1, str]:
    raw = _read_owner_only_tmp_file(path, description="census report")
    try:
        report = _CensusReportV1.model_validate_json(raw)
    except Exception as exc:
        raise HistoricalIdentityRebuildProfileMapError(
            "historical Identity census report is invalid"
        ) from exc
    return report, hashlib.sha256(raw).hexdigest()


def _validate_report_profiles(
    *,
    current: _CensusReportV1,
    legacy: _CensusReportV1,
) -> None:
    current_is_valid = (
        current.contract_version == "1.0" and current.rebuild_profile is None
    ) or (
        current.contract_version == "1.1"
        and current.rebuild_profile == CURRENT_IDENTITY_REBUILD_PROFILE
    )
    if not current_is_valid:
        raise HistoricalIdentityRebuildProfileMapError(
            "current census report does not use the current profile"
        )
    if (
        legacy.contract_version != "1.1"
        or legacy.rebuild_profile != PRE_ETV_IDENTITY_REBUILD_PROFILE
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "legacy census report does not use the pre-ETV-governance profile"
        )


def _validate_shared_report_scope(
    *,
    current: _CensusReportV1,
    legacy: _CensusReportV1,
) -> None:
    if (
        current.scope != "full_canonical_index"
        or legacy.scope != "full_canonical_index"
        or current.evaluated_session_count != current.canonical_session_count
        or legacy.evaluated_session_count != legacy.canonical_session_count
        or current.unroutable_manifest_count != 0
        or legacy.unroutable_manifest_count != 0
        or current.outside_canonical_session_package_count != 0
        or legacy.outside_canonical_session_package_count != 0
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "profile map requires two complete full-index census reports"
        )
    shared_fields = (
        "canonical_session_count",
        "evaluated_session_count",
        "canonical_session_index_fingerprint",
        "package_root_count",
        "discovered_identity_package_count",
        "ignored_non_identity_package_count",
        "unroutable_manifest_count",
        "outside_canonical_session_package_count",
        "discovered_package_inventory_fingerprint",
    )
    if any(
        getattr(current, name) != getattr(legacy, name) for name in shared_fields
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "census reports do not share one canonical and package inventory scope"
        )
    if tuple(item.session_date for item in current.sessions) != tuple(
        item.session_date for item in legacy.sessions
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "census report session indexes differ"
        )
    expected_index_fingerprint = historical_identity_profile_fingerprint(
        [item.session_date.isoformat() for item in current.sessions]
    )
    if current.canonical_session_index_fingerprint != expected_index_fingerprint:
        raise HistoricalIdentityRebuildProfileMapError(
            "census canonical session-index fingerprint differs from sessions"
        )
    for report in (current, legacy):
        inventory = [
            {
                "session_date": session.session_date.isoformat(),
                "package_manifest_sha256": candidate.package_manifest_sha256,
                "package_content_sha256": candidate.package_content_sha256,
                "source_locator_sha256": candidate.source_locator_sha256,
            }
            for session in report.sessions
            for candidate in session.candidates
        ]
        inventory.sort(
            key=lambda item: (
                item["session_date"],
                item["package_manifest_sha256"],
                item["package_content_sha256"],
                item["source_locator_sha256"],
            )
        )
        if (
            len(inventory) != report.discovered_identity_package_count
            or historical_identity_profile_fingerprint(inventory)
            != report.discovered_package_inventory_fingerprint
        ):
            raise HistoricalIdentityRebuildProfileMapError(
                "census package-inventory fingerprint differs from candidates"
            )
    allowed = {"exact_equivalent", "identity_snapshot_mismatch", "missing_source"}
    if any(
        item.status not in allowed for item in (*current.sessions, *legacy.sessions)
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "census reports contain a blocking failure class"
        )


def _validate_shared_session(
    *,
    current: _CensusSessionV1,
    legacy: _CensusSessionV1,
) -> None:
    shared_fields = (
        "session_date",
        "candidate_count",
        "custody_valid_candidate_count",
        "canonical_snapshot_fingerprint",
        "canonical_instrument_fingerprint",
        "canonical_identity_fingerprint",
        "canonical_resolver_fingerprint",
    )
    if any(
        getattr(current, name) != getattr(legacy, name) for name in shared_fields
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "profile census session custody or canonical evidence differs"
        )


def _validate_missing_pair(
    current: _CensusSessionV1,
    legacy: _CensusSessionV1,
) -> None:
    if (
        current.candidate_count != 0
        or current.custody_valid_candidate_count != 0
        or current.exact_equivalent_candidate_count != 0
        or legacy.exact_equivalent_candidate_count != 0
        or current.candidates
        or legacy.candidates
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "missing census sessions carry candidate evidence"
        )


def _validate_unbound_mismatch_pair(
    current: _CensusSessionV1,
    legacy: _CensusSessionV1,
) -> None:
    if (
        current.candidate_count != 1
        or current.custody_valid_candidate_count != 1
        or current.exact_equivalent_candidate_count != 0
        or legacy.candidate_count != 1
        or legacy.custody_valid_candidate_count != 1
        or legacy.exact_equivalent_candidate_count != 0
        or len(current.candidates) != 1
        or len(legacy.candidates) != 1
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "unbound mismatch session does not have one custody-valid candidate pair"
        )
    current_candidate = current.candidates[0]
    legacy_candidate = legacy.candidates[0]
    common_fields = (
        "source_locator_sha256",
        "package_manifest_sha256",
        "package_content_sha256",
        "fetched_at",
    )
    if any(
        getattr(current_candidate, name) != getattr(legacy_candidate, name)
        for name in common_fields
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "unbound profile candidates do not identify the same source package"
        )
    if (
        current_candidate.status != "identity_snapshot_mismatch"
        or legacy_candidate.status != "identity_snapshot_mismatch"
        or (
            current_candidate.instrument_match,
            current_candidate.identity_match,
            current_candidate.resolver_match,
        )
        == (True, True, True)
        or (
            legacy_candidate.instrument_match,
            legacy_candidate.identity_match,
            legacy_candidate.resolver_match,
        )
        == (True, True, True)
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "unbound profile candidate unexpectedly claims exact equivalence"
        )


def _select_exact_profile(
    *,
    current: _CensusSessionV1,
    legacy: _CensusSessionV1,
) -> tuple[
    HistoricalIdentityRebuildProfile,
    _CensusSessionV1,
    _CensusSessionV1,
]:
    statuses = (current.status, legacy.status)
    if statuses == ("exact_equivalent", "identity_snapshot_mismatch"):
        return CURRENT_IDENTITY_REBUILD_PROFILE, current, legacy
    if statuses == ("identity_snapshot_mismatch", "exact_equivalent"):
        return PRE_ETV_IDENTITY_REBUILD_PROFILE, legacy, current
    raise HistoricalIdentityRebuildProfileMapError(
        "retained session does not have exactly one matching rebuild profile"
    )


def _validate_complementary_candidates(
    *,
    exact: _CensusSessionV1,
    mismatch: _CensusSessionV1,
) -> None:
    if (
        exact.candidate_count != 1
        or exact.custody_valid_candidate_count != 1
        or exact.exact_equivalent_candidate_count != 1
        or mismatch.candidate_count != 1
        or mismatch.custody_valid_candidate_count != 1
        or mismatch.exact_equivalent_candidate_count != 0
        or len(exact.candidates) != 1
        or len(mismatch.candidates) != 1
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "retained session does not have one complementary candidate pair"
        )
    exact_candidate = exact.candidates[0]
    mismatch_candidate = mismatch.candidates[0]
    common_fields = (
        "source_locator_sha256",
        "package_manifest_sha256",
        "package_content_sha256",
        "fetched_at",
    )
    if any(
        getattr(exact_candidate, name) != getattr(mismatch_candidate, name)
        for name in common_fields
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "profile census candidates do not identify the same source package"
        )
    if (
        exact_candidate.status != "exact_equivalent"
        or (
            exact_candidate.instrument_match,
            exact_candidate.identity_match,
            exact_candidate.resolver_match,
        )
        != (True, True, True)
        or mismatch_candidate.status != "identity_snapshot_mismatch"
        or (
            mismatch_candidate.instrument_match,
            mismatch_candidate.identity_match,
            mismatch_candidate.resolver_match,
        )
        != (True, False, True)
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "profile census candidate match flags are not ETV-only complementary"
        )
    canonical = (
        exact.canonical_instrument_fingerprint,
        exact.canonical_identity_fingerprint,
        exact.canonical_resolver_fingerprint,
    )
    if None in canonical or (
        exact_candidate.rebuilt_instrument_fingerprint,
        exact_candidate.rebuilt_identity_fingerprint,
        exact_candidate.rebuilt_resolver_fingerprint,
    ) != canonical:
        raise HistoricalIdentityRebuildProfileMapError(
            "exact profile candidate does not equal canonical family fingerprints"
        )
    if (
        mismatch_candidate.rebuilt_instrument_fingerprint != canonical[0]
        or mismatch_candidate.rebuilt_identity_fingerprint == canonical[1]
        or mismatch_candidate.rebuilt_resolver_fingerprint != canonical[2]
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "non-selected profile differs outside the Provider Identity family"
        )


def _read_owner_only_tmp_file(path: Path, *, description: str) -> bytes:
    temporary_root = Path("/tmp").resolve(strict=True)
    if path.is_symlink():
        raise HistoricalIdentityRebuildProfileMapError(
            f"{description} must not be a symlink"
        )
    resolved = path.resolve(strict=True)
    metadata = resolved.lstat()
    if temporary_root not in resolved.parents or not stat.S_ISREG(metadata.st_mode):
        raise HistoricalIdentityRebuildProfileMapError(
            f"{description} must be a regular file below /tmp"
        )
    if metadata.st_mode & 0o077:
        raise HistoricalIdentityRebuildProfileMapError(
            f"{description} must be owner-only"
        )
    return resolved.read_bytes()


def _new_tmp_output_path(path: Path) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    parent = path.parent.resolve(strict=True)
    if (
        temporary_root not in parent.parents
        or parent.is_symlink()
        or not parent.is_dir()
    ):
        raise HistoricalIdentityRebuildProfileMapError(
            "profile-map output parent must be a non-symlink directory below /tmp"
        )
    target = parent / path.name
    if target.exists() or target.is_symlink():
        raise HistoricalIdentityRebuildProfileMapError(
            "profile-map output path already exists"
        )
    return target


def _json_ready(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return normalize_utc_datetime(value).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    return value
