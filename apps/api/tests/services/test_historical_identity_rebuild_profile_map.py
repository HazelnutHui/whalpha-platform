from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.historical_identity_rebuild_profile_map import (
    HistoricalIdentityRebuildProfileMapError,
    build_historical_identity_rebuild_profile_map,
    historical_identity_profile_fingerprint,
    profile_binding_for_session,
    read_historical_identity_rebuild_profile_map,
    write_historical_identity_rebuild_profile_map,
)

NOW = datetime(2026, 9, 4, 21, tzinfo=UTC)
CURRENT_SESSION = date(2026, 9, 1)
LEGACY_SESSION = date(2026, 9, 2)
MISSING_SESSION = date(2026, 9, 3)
SESSIONS = (CURRENT_SESSION, LEGACY_SESSION, MISSING_SESSION)


def _sha(character: str) -> str:
    return character * 64


def _candidate(*, exact: bool, offset: int) -> dict[str, object]:
    return {
        "source_locator_sha256": _sha(str(offset)),
        "package_manifest_sha256": _sha(("a", "b")[offset - 1]),
        "package_content_sha256": _sha(("e", "f")[offset - 1]),
        "fetched_at": "2026-09-04T20:00:00Z",
        "status": "exact_equivalent" if exact else "identity_snapshot_mismatch",
        "rebuilt_instrument_fingerprint": _sha("4"),
        "rebuilt_identity_fingerprint": _sha("5" if exact else "7"),
        "rebuilt_resolver_fingerprint": _sha("6"),
        "instrument_match": True,
        "identity_match": exact,
        "resolver_match": True,
    }


def _session(
    session_date: date,
    *,
    status: str,
    exact: bool | None,
    offset: int,
) -> dict[str, object]:
    candidates = [] if exact is None else [_candidate(exact=exact, offset=offset)]
    return {
        "session_date": session_date.isoformat(),
        "status": status,
        "candidate_count": len(candidates),
        "custody_valid_candidate_count": len(candidates),
        "exact_equivalent_candidate_count": int(exact is True),
        "canonical_snapshot_fingerprint": _sha("3"),
        "canonical_instrument_fingerprint": _sha("4"),
        "canonical_identity_fingerprint": _sha("5"),
        "canonical_resolver_fingerprint": _sha("6"),
        "candidates": candidates,
    }


def _report(*, profile: str, second_exact: bool = True) -> dict[str, object]:
    is_current = profile == "current_v1"
    sessions = [
        _session(
            CURRENT_SESSION,
            status=(
                "exact_equivalent" if is_current else "identity_snapshot_mismatch"
            ),
            exact=is_current,
            offset=1,
        ),
        _session(
            LEGACY_SESSION,
            status=(
                "identity_snapshot_mismatch"
                if is_current or not second_exact
                else "exact_equivalent"
            ),
            exact=False if is_current or not second_exact else True,
            offset=2,
        ),
        _session(
            MISSING_SESSION,
            status="missing_source",
            exact=None,
            offset=3,
        ),
    ]
    statuses = (
        "canonical_identity_unavailable",
        "duplicate_source_review_required",
        "exact_equivalent",
        "identity_snapshot_mismatch",
        "missing_source",
        "package_custody_failed",
    )
    package_inventory = [
        {
            "session_date": item["session_date"],
            "package_manifest_sha256": candidate["package_manifest_sha256"],
            "package_content_sha256": candidate["package_content_sha256"],
            "source_locator_sha256": candidate["source_locator_sha256"],
        }
        for item in sessions
        for candidate in item["candidates"]
    ]
    result: dict[str, object] = {
        "contract_version": "1.0" if is_current else "1.1",
        "scope": "full_canonical_index",
        "evaluated_at": "2026-09-04T20:00:00Z",
        "canonical_session_count": 3,
        "evaluated_session_count": 3,
        "worker_count": 1,
        "canonical_session_index_fingerprint": historical_identity_profile_fingerprint(
            [item.isoformat() for item in SESSIONS]
        ),
        "package_root_count": 1,
        "discovered_identity_package_count": 2,
        "ignored_non_identity_package_count": 0,
        "unroutable_manifest_count": 0,
        "outside_canonical_session_package_count": 0,
        "discovered_package_inventory_fingerprint": (
            historical_identity_profile_fingerprint(package_inventory)
        ),
        "exact_equivalent_session_count": sum(
            item["status"] == "exact_equivalent" for item in sessions
        ),
        "duplicate_source_session_count": 0,
        "status_counts": [
            [status, sum(item["status"] == status for item in sessions)]
            for status in statuses
        ],
        "sessions": sessions,
        "external_request_count": 0,
        "canonical_data_write_count": 0,
    }
    if not is_current:
        result["rebuild_profile"] = profile
    return result


def _write_report(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_profile_map_is_exact_complete_and_formally_reread(tmp_path: Path) -> None:
    current_path = _write_report(tmp_path / "current.json", _report(profile="current_v1"))
    legacy_path = _write_report(
        tmp_path / "legacy.json",
        _report(profile="pre_etv_governance_v1"),
    )

    profile_map = build_historical_identity_rebuild_profile_map(
        current_census_report_path=current_path,
        legacy_census_report_path=legacy_path,
        generated_at=NOW,
    )

    assert profile_map.canonical_session_count == 3
    assert profile_map.bound_session_count == 2
    assert profile_map.missing_session_dates == (MISSING_SESSION,)
    assert profile_map.unbound_identity_mismatch_session_dates == ()
    assert profile_map.contract_version == "historical-identity-rebuild-profile-map/1.1"
    assert dict(profile_map.profile_counts) == {
        "current_v1": 1,
        "pre_etv_governance_v1": 1,
    }
    assert [item.session_date for item in profile_map.bindings] == [
        CURRENT_SESSION,
        LEGACY_SESSION,
    ]
    assert profile_binding_for_session(
        profile_map,
        LEGACY_SESSION,
    ).rebuild_profile == "pre_etv_governance_v1"
    with pytest.raises(HistoricalIdentityRebuildProfileMapError, match="not bound"):
        profile_binding_for_session(profile_map, MISSING_SESSION)

    output = write_historical_identity_rebuild_profile_map(
        profile_map=profile_map,
        output_path=tmp_path / "profile-map.json",
    )
    assert output.stat().st_mode & 0o777 == 0o600
    assert read_historical_identity_rebuild_profile_map(output) == profile_map


def test_profile_map_keeps_dual_mismatch_session_explicitly_unbound(
    tmp_path: Path,
) -> None:
    current_path = _write_report(tmp_path / "current.json", _report(profile="current_v1"))
    legacy_path = _write_report(
        tmp_path / "legacy.json",
        _report(profile="pre_etv_governance_v1", second_exact=False),
    )

    profile_map = build_historical_identity_rebuild_profile_map(
        current_census_report_path=current_path,
        legacy_census_report_path=legacy_path,
        generated_at=NOW,
    )

    assert profile_map.bound_session_count == 1
    assert profile_map.missing_session_dates == (MISSING_SESSION,)
    assert profile_map.unbound_identity_mismatch_session_dates == (LEGACY_SESSION,)
    with pytest.raises(HistoricalIdentityRebuildProfileMapError, match="not bound"):
        profile_binding_for_session(profile_map, LEGACY_SESSION)


def test_profile_map_rejects_group_readable_census_evidence(tmp_path: Path) -> None:
    current_path = _write_report(tmp_path / "current.json", _report(profile="current_v1"))
    legacy_path = _write_report(
        tmp_path / "legacy.json",
        _report(profile="pre_etv_governance_v1"),
    )
    current_path.chmod(0o640)

    with pytest.raises(HistoricalIdentityRebuildProfileMapError, match="owner-only"):
        build_historical_identity_rebuild_profile_map(
            current_census_report_path=current_path,
            legacy_census_report_path=legacy_path,
            generated_at=NOW,
        )
