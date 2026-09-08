from __future__ import annotations

import os
import json
import socket
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    REVIEW_LIMITATION_CODES,
    SOURCE_FIELD_NAMES,
    HistoricalInactiveLifecycleResolutionDecisionV1,
    HistoricalInactiveLifecycleSourceObservationV1,
    inactive_lifecycle_fingerprint,
)
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle_corroboration import (
    HistoricalInactiveLifecycleCorroborationWorkItemV1,
)
from tip_api.services import historical_inactive_lifecycle_corroboration_plan as module
from tip_api.services import historical_inactive_lifecycle_corroboration_plan_cli as cli
from tip_api.services.historical_inactive_lifecycle_corroboration_plan import (
    HistoricalInactiveLifecycleCorroborationPlanError,
    build_historical_inactive_lifecycle_corroboration_plan,
    read_historical_inactive_lifecycle_corroboration_plan,
)


ANCHOR = date(2026, 9, 3)
PLANNED = datetime(2026, 9, 8, 12, tzinfo=UTC)
REVISION = "1" * 40
SHADOW_MANIFEST_SHA256 = "2" * 64
SHADOW_LOGICAL_FINGERPRINT = "3" * 64
SOURCE_PACKAGE_FINGERPRINT = "4" * 64
CANONICAL_HISTORY_FINGERPRINT = "5" * 64


def _observation(
    *,
    row: int,
    ticker: str,
    exchange: str,
    figi: str,
) -> HistoricalInactiveLifecycleSourceObservationV1:
    payload = {field: None for field in SOURCE_FIELD_NAMES}
    payload.update(
        {
            "active": False,
            "ticker": ticker,
            "primary_exchange": exchange,
            "share_class_figi": figi,
            "delisted_utc": "2026-09-02",
            "last_updated_utc": "2026-09-03T08:00:00Z",
        }
    )
    payload_fingerprint = inactive_lifecycle_fingerprint(payload)
    occurrence = {
        "anchor_date": ANCHOR,
        "source_page_sequence": 1,
        "source_row_sequence": row,
        "source_payload_fingerprint": payload_fingerprint,
    }
    return HistoricalInactiveLifecycleSourceObservationV1(
        anchor_date=ANCHOR,
        source_observed_at=PLANNED - timedelta(days=1),
        source_page_sequence=1,
        source_row_sequence=row,
        **payload,
        source_payload_fingerprint=payload_fingerprint,
        source_observation_fingerprint=inactive_lifecycle_fingerprint(occurrence),
    )


def _decision(
    observation: HistoricalInactiveLifecycleSourceObservationV1,
    instrument_id: UUID,
) -> HistoricalInactiveLifecycleResolutionDecisionV1:
    return HistoricalInactiveLifecycleResolutionDecisionV1(
        anchor_date=ANCHOR,
        source_observation_fingerprint=observation.source_observation_fingerprint,
        source_payload_fingerprint=observation.source_payload_fingerprint,
        source_page_sequence=observation.source_page_sequence,
        source_row_sequence=observation.source_row_sequence,
        selected_identity_type="share_class_figi",
        selected_identity_value=observation.share_class_figi,
        identity_resolution_status="resolved",
        canonical_instrument_id=instrument_id,
        canonical_first_observed_date=date(2026, 7, 1),
        canonical_last_observed_date=date(2026, 9, 1),
        effective_date_candidate=date(2026, 9, 2),
        ticker_seen_in_canonical_history=True,
        disposition="review_candidate",
        reason_codes=REVIEW_LIMITATION_CODES,
        source_package_logical_fingerprint=SOURCE_PACKAGE_FINGERPRINT,
        canonical_instrument_history_fingerprint=CANONICAL_HISTORY_FINGERPRINT,
        evaluated_at=PLANNED - timedelta(hours=1),
    )


def _shadow():
    observations = (
        _observation(row=1, ticker="AAA", exchange="XNAS", figi="FIGI-A"),
        _observation(row=2, ticker="BBB", exchange="XNYS", figi="FIGI-B"),
    )
    decisions = (
        _decision(observations[0], UUID("00000000-0000-0000-0000-000000000001")),
        _decision(observations[1], UUID("00000000-0000-0000-0000-000000000002")),
    )
    return SimpleNamespace(
        source_observations=observations,
        decisions=decisions,
        manifest=SimpleNamespace(
            disposition_counts=(("quarantined", 0), ("review_candidate", 2)),
            logical_fingerprint=SHADOW_LOGICAL_FINGERPRINT,
            source_package_record_count=2,
        ),
        manifest_sha256=SHADOW_MANIFEST_SHA256,
    )


def _build(monkeypatch: pytest.MonkeyPatch, plan_path: Path, **kwargs):
    monkeypatch.setattr(
        module,
        "read_historical_inactive_lifecycle_resolution_shadow",
        lambda **_arguments: _shadow(),
    )
    return build_historical_inactive_lifecycle_corroboration_plan(
        shadow_root=plan_path.parent,
        anchor_date=ANCHOR,
        plan_path=plan_path,
        planned_at=kwargs.pop("planned_at", PLANNED),
        implementation_revision=kwargs.pop("implementation_revision", REVISION),
        **kwargs,
    )


def test_builds_complete_fail_closed_candidate_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "plan.json"
    result = _build(monkeypatch, plan_path)

    assert result.status == "plan_created"
    assert result.plan.shadow_review_candidate_count == 2
    assert dict(result.plan.primary_exchange_counts) == {"XNAS": 1, "XNYS": 1}
    assert dict(result.plan.route_counts) == {
        "all_exchange_source_selection_required": 1,
        "nasdaq_daily_list_pilot_required": 1,
    }
    assert dict(result.plan.status_counts) == {
        "documented_source_pilot_required": 1,
        "source_selection_required": 1,
    }
    assert result.plan.point_in_time_eligible_count == 0
    assert result.plan.ticker_locator_retained_count == 0
    assert result.plan.external_request_count == 0
    assert result.plan.canonical_data_write_count == 0
    assert result.plan.acquisition_authorized is False
    assert result.plan.canonical_lifecycle_authorized is False
    assert os.stat(plan_path).st_mode & 0o777 == 0o400
    payload = plan_path.read_text()
    assert "AAA" not in payload
    assert "BBB" not in payload

    reread = read_historical_inactive_lifecycle_corroboration_plan(
        plan_path=plan_path,
        approved_plan_sha256=result.plan_sha256,
    )
    assert reread.plan == result.plan


def test_exact_existing_plan_is_reused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "plan.json"
    first = _build(monkeypatch, plan_path)
    second = _build(monkeypatch, plan_path)

    assert second.status == "already_present"
    assert second.plan_sha256 == first.plan_sha256


def test_existing_different_plan_is_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "plan.json"
    first = _build(monkeypatch, plan_path)
    original = plan_path.read_bytes()

    with pytest.raises(
        HistoricalInactiveLifecycleCorroborationPlanError,
        match="existing lifecycle corroboration plan differs",
    ):
        _build(
            monkeypatch,
            plan_path,
            planned_at=PLANNED + timedelta(seconds=1),
        )

    assert plan_path.read_bytes() == original
    assert read_historical_inactive_lifecycle_corroboration_plan(
        plan_path=plan_path,
        approved_plan_sha256=first.plan_sha256,
    ).plan == first.plan


def test_formal_reader_rejects_mode_and_hash_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "plan.json"
    result = _build(monkeypatch, plan_path)
    plan_path.chmod(0o600)
    with pytest.raises(
        HistoricalInactiveLifecycleCorroborationPlanError,
        match="custody differs",
    ):
        read_historical_inactive_lifecycle_corroboration_plan(plan_path=plan_path)
    plan_path.chmod(0o400)
    with pytest.raises(
        HistoricalInactiveLifecycleCorroborationPlanError,
        match="SHA-256 differs",
    ):
        read_historical_inactive_lifecycle_corroboration_plan(
            plan_path=plan_path,
            approved_plan_sha256="f" * 64,
        )
    assert result.plan_sha256 != "f" * 64


def test_exchange_route_cannot_claim_the_wrong_source_path() -> None:
    with pytest.raises(ValidationError, match="exchange route differs"):
        HistoricalInactiveLifecycleCorroborationWorkItemV1(
            anchor_date=ANCHOR,
            source_observation_fingerprint="1" * 64,
            shadow_decision_fingerprint="2" * 64,
            canonical_instrument_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            primary_exchange="XNAS",
            effective_date_candidate=date(2026, 9, 2),
            canonical_first_observed_date=date(2026, 7, 1),
            canonical_last_observed_date=date(2026, 9, 1),
            source_first_observed_at=PLANNED,
            provider_last_updated_field_present=True,
            route="all_exchange_source_selection_required",
            status="documented_source_pilot_required",
        )


def test_network_is_prohibited_while_shadow_is_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def network_attempt(**_arguments):
        socket.create_connection(("example.invalid", 443))

    monkeypatch.setattr(
        module,
        "read_historical_inactive_lifecycle_resolution_shadow",
        network_attempt,
    )
    with pytest.raises(
        HistoricalInactiveLifecycleCorroborationPlanError,
        match="network is prohibited",
    ):
        build_historical_inactive_lifecycle_corroboration_plan(
            shadow_root=tmp_path,
            anchor_date=ANCHOR,
            plan_path=tmp_path / "plan.json",
            planned_at=PLANNED,
            implementation_revision=REVISION,
        )


def test_nested_symlink_plan_parent_is_rejected(tmp_path: Path) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    (real_parent / "nested").mkdir()
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(
        HistoricalInactiveLifecycleCorroborationPlanError,
        match="contains a symlink",
    ):
        read_historical_inactive_lifecycle_corroboration_plan(
            plan_path=linked_parent / "nested" / "plan.json"
        )


def test_cli_build_reports_aggregate_only_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module,
        "read_historical_inactive_lifecycle_resolution_shadow",
        lambda **_arguments: _shadow(),
    )
    monkeypatch.setattr(cli, "_clean_revision", lambda: REVISION)
    plan_path = tmp_path / "plan.json"

    status = cli.main(
        [
            "build",
            "--shadow-root",
            str(tmp_path),
            "--anchor-date",
            ANCHOR.isoformat(),
            "--plan-path",
            str(plan_path),
            "--planned-at",
            PLANNED.isoformat(),
        ]
    )

    assert status == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "plan_created"
    assert output["shadow_review_candidate_count"] == 2
    assert output["ticker_locator_retained_count"] == 0
    assert output["external_request_count"] == 0
    assert output["canonical_lifecycle_authorized"] is False
