from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from tip_api.services import current_historical_pilot_baseline as service


NOW = datetime(2026, 8, 30, 20, 0, tzinfo=UTC)
SESSIONS = tuple(date(2026, 7, day) for day in (17, 20, 21, 22))


def _patch_current_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "assess_current_historical_mechanics_evidence",
        lambda root: SimpleNamespace(logical_content_fingerprint="b" * 64),
    )
    monkeypatch.setattr(
        service,
        "_current_sessions",
        lambda root, mechanics: (SESSIONS, SESSIONS),
    )
    monkeypatch.setattr(
        service,
        "_historical_partition_counts",
        lambda root: (0, 0, 0, 0, 0),
    )
    monkeypatch.setattr(service, "inventory_fingerprint", lambda root: "a" * 64)
    monkeypatch.setattr(service, "_clean_main_revision", lambda root: "1" * 40)
    monkeypatch.setattr(
        service,
        "_file_set_fingerprint",
        lambda root, paths: "c" * 64,
    )
    monkeypatch.setattr(service, "PERMISSION_EVIDENCE_FINGERPRINT", "c" * 64)


def test_current_baseline_is_exact_blocked_and_non_authorizing(
    tmp_path,
    monkeypatch,
) -> None:
    data = tmp_path / "data"
    repository = tmp_path / "repository"
    data.mkdir()
    repository.mkdir()
    _patch_current_evidence(monkeypatch)

    first = service.assess_current_historical_pilot_baseline(
        data_root=data,
        repository_root=repository,
        reviewed_at=NOW,
    )
    second = service.assess_current_historical_pilot_baseline(
        data_root=data,
        repository_root=repository,
        reviewed_at=NOW,
    )

    assert first == second
    assert first.status == "blocked"
    assert first.target_sessions == ("2026-07-14", "2026-07-15", "2026-07-16")
    assert first.planned_request_ceiling == 75
    assert first.estimated_transport_seconds_at_ceiling == 1_125
    by_kind = {item.kind: item for item in first.requests}
    assert by_kind["grouped_daily"].request_ceiling == 3
    assert by_kind["active_all_tickers"].request_ceiling == 60
    assert by_kind["inactive_all_tickers"].request_ceiling == 6
    assert by_kind["splits"].request_ceiling == 2
    assert by_kind["dividends"].request_ceiling == 4
    assert by_kind["ticker_events_experimental"].request_ceiling == 0
    assert first.source_permission_assessment_statuses == (
        "blocked_by_permission",
    ) * 3
    assert first.unresolved_gate_ids == (
        "account_endpoint_entitlement",
        "equal_capability_source_permission",
        "lifecycle_source_coverage",
    )
    assert first.required_user_acknowledgement is None
    assert not any(
        (
            first.acquisition_authorized,
            first.apply_authorized,
            first.publication_authorized,
            first.deployment_authorized,
            first.scheduler_authorized,
        )
    )
    assert first.external_request_count == 0
    assert first.data_write_count == 0


def test_current_baseline_rejects_naive_time(tmp_path, monkeypatch) -> None:
    data = tmp_path / "data"
    repository = tmp_path / "repository"
    data.mkdir()
    repository.mkdir()
    _patch_current_evidence(monkeypatch)

    with pytest.raises(service.CurrentHistoricalPilotBaselineError, match="timezone"):
        service.assess_current_historical_pilot_baseline(
            data_root=data,
            repository_root=repository,
            reviewed_at=NOW.replace(tzinfo=None),
        )


def test_absent_historical_families_are_exact_zero(tmp_path) -> None:
    assert service._historical_partition_counts(tmp_path) == (0, 0, 0, 0, 0)


def test_inventory_size_rejects_symlink(tmp_path) -> None:
    target = tmp_path / "target"
    target.write_text("evidence", encoding="utf-8")
    (tmp_path / "link").symlink_to(target)

    with pytest.raises(service.CurrentHistoricalPilotBaselineError, match="symlink"):
        service._inventory_size(tmp_path)
