from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.contracts.market_data.v1 import HistoricalSourceRequestKind
from tip_api.persistence.historical_source_package import (
    CapturedHistoricalSourceScopeV1,
    HistoricalSourcePackageConflictError,
    HistoricalSourcePackageCorruptionError,
    publish_historical_source_package,
    read_historical_source_package,
)
from tip_api.services.historical_pilot_planner import (
    HistoricalPilotInventoryV1,
    HistoricalPilotRequestV1,
    plan_historical_research_pilot,
)


ACQUIRED_AT = datetime(2026, 8, 30, 18, 0, tzinfo=UTC)


def _plan():
    return plan_historical_research_pilot(
        inventory=HistoricalPilotInventoryV1(
            source_report_id="fixture-inventory",
            inventory_fingerprint="1" * 64,
            completed_eod_sessions=(),
            completed_identity_sessions=(),
        ),
        request=HistoricalPilotRequestV1(
            target_sessions=(date(2026, 7, 14),),
            provider_id="fixture_provider",
        ),
    )


def _package_path(tmp_path: Path, fingerprint: str) -> Path:
    parent = tmp_path / "historical-research-pilot"
    parent.mkdir()
    return parent / f"plan={fingerprint}"


def _captured_scopes() -> tuple[CapturedHistoricalSourceScopeV1, ...]:
    return (
        CapturedHistoricalSourceScopeV1(
            request_kind=HistoricalSourceRequestKind.GROUPED_DAILY,
            logical_endpoint="stocks_grouped_daily_unadjusted",
            scope="2026-07-14",
            responses=({"adjusted": False, "results": [{"T": "ABC"}]},),
        ),
        CapturedHistoricalSourceScopeV1(
            request_kind=HistoricalSourceRequestKind.ACTIVE_ALL_TICKERS,
            logical_endpoint="stocks_reference_all_tickers_active_point_in_time",
            scope="2026-07-14",
            responses=(
                {
                    "results": [{"ticker": "ABC", "active": True}],
                    "next_url": "https://provider.example/v3/reference/tickers?cursor=safe",
                },
            ),
        ),
        CapturedHistoricalSourceScopeV1(
            request_kind=HistoricalSourceRequestKind.SPLITS,
            logical_endpoint="stocks_v1_splits",
            scope="bounded_paginated_collection",
            responses=({"results": []},),
        ),
        CapturedHistoricalSourceScopeV1(
            request_kind=HistoricalSourceRequestKind.DIVIDENDS,
            logical_endpoint="stocks_v1_dividends",
            scope="bounded_paginated_collection",
            responses=({"results": []},),
        ),
    )


def _publish(tmp_path: Path):
    plan = _plan()
    package_path = _package_path(tmp_path, plan.logical_content_fingerprint)
    result = publish_historical_source_package(
        package_path=package_path,
        plan=plan,
        captured_scopes=_captured_scopes(),
        acquired_at=ACQUIRED_AT,
        source_permission_review_fingerprint="2" * 64,
        account_entitlement_evidence_fingerprint="3" * 64,
        lifecycle_coverage_review_fingerprint="4" * 64,
        exact_authorization_acknowledgement_fingerprint="5" * 64,
    )
    return plan, result


def test_historical_source_package_round_trip_is_exact_and_non_authorizing(
    tmp_path: Path,
) -> None:
    plan, published = _publish(tmp_path)
    reread = read_historical_source_package(
        package_path=published.package_path,
        expected_plan_fingerprint=plan.logical_content_fingerprint,
    )
    again = publish_historical_source_package(
        package_path=published.package_path,
        plan=plan,
        captured_scopes=_captured_scopes(),
        acquired_at=ACQUIRED_AT,
        source_permission_review_fingerprint="2" * 64,
        account_entitlement_evidence_fingerprint="3" * 64,
        lifecycle_coverage_review_fingerprint="4" * 64,
        exact_authorization_acknowledgement_fingerprint="5" * 64,
    )

    assert published.status == "published"
    assert reread.manifest == published.manifest
    assert again.status == "already_present"
    assert reread.manifest.total_request_count == 4
    assert reread.manifest.planned_request_ceiling == 27
    assert reread.manifest.source_payload_retention == "temporary_package_only"
    assert reread.manifest.canonical_apply_authorized is False
    assert reread.manifest.publication_authorized is False
    assert reread.manifest.deployment_authorized is False
    assert reread.manifest.scheduler_authorized is False
    assert reread.file_count == 7


def test_historical_source_package_rejects_changed_payload(tmp_path: Path) -> None:
    _, published = _publish(tmp_path)
    artifact = next(published.package_path.glob("staged/grouped-daily/**/*.json"))
    artifact.chmod(0o600)
    artifact.write_text('{"changed":true}\n', encoding="utf-8")
    artifact.chmod(0o400)

    with pytest.raises(
        HistoricalSourcePackageCorruptionError,
        match="artifact custody differs",
    ):
        read_historical_source_package(package_path=published.package_path)


def test_historical_source_package_rejects_unplanned_extra_file(tmp_path: Path) -> None:
    _, published = _publish(tmp_path)
    extra = published.package_path / "extra.json"
    extra.write_text("{}\n", encoding="utf-8")
    extra.chmod(0o400)

    with pytest.raises(HistoricalSourcePackageCorruptionError, match="file set differs"):
        read_historical_source_package(package_path=published.package_path)


def test_historical_source_package_rejects_relaxed_completed_file_mode(
    tmp_path: Path,
) -> None:
    _, published = _publish(tmp_path)
    artifact = next(published.package_path.glob("staged/grouped-daily/**/*.json"))
    artifact.chmod(0o440)

    with pytest.raises(
        HistoricalSourcePackageCorruptionError,
        match="file custody differs",
    ):
        read_historical_source_package(package_path=published.package_path)


def test_historical_source_package_rejects_secret_bearing_payload(
    tmp_path: Path,
) -> None:
    plan = _plan()
    package_path = _package_path(tmp_path, plan.logical_content_fingerprint)
    scopes = list(_captured_scopes())
    scopes[0] = CapturedHistoricalSourceScopeV1(
        request_kind=HistoricalSourceRequestKind.GROUPED_DAILY,
        logical_endpoint="stocks_grouped_daily_unadjusted",
        scope="2026-07-14",
        responses=({"api_key": "must-not-enter-custody"},),
    )

    with pytest.raises(
        HistoricalSourcePackageConflictError,
        match="credential-bearing fields",
    ):
        publish_historical_source_package(
            package_path=package_path,
            plan=plan,
            captured_scopes=tuple(scopes),
            acquired_at=ACQUIRED_AT,
            source_permission_review_fingerprint="2" * 64,
            account_entitlement_evidence_fingerprint="3" * 64,
            lifecycle_coverage_review_fingerprint="4" * 64,
            exact_authorization_acknowledgement_fingerprint="5" * 64,
        )
    assert not package_path.exists()


def test_historical_source_package_requires_every_planned_scope(tmp_path: Path) -> None:
    plan = _plan()
    package_path = _package_path(tmp_path, plan.logical_content_fingerprint)

    with pytest.raises(
        HistoricalSourcePackageConflictError,
        match="differ from the exact pilot plan",
    ):
        publish_historical_source_package(
            package_path=package_path,
            plan=plan,
            captured_scopes=_captured_scopes()[:-1],
            acquired_at=ACQUIRED_AT,
            source_permission_review_fingerprint="2" * 64,
            account_entitlement_evidence_fingerprint="3" * 64,
            lifecycle_coverage_review_fingerprint="4" * 64,
            exact_authorization_acknowledgement_fingerprint="5" * 64,
        )
