from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.providers.china_ashare import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareInstrumentSourceBatchV1,
)
from tip_api.services.china_ashare_pilot_reference import (
    build_default_china_ashare_pilot_plan,
    capture_china_ashare_pilot_reference,
)


NOW = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
OFFICIAL_DATE = date(2026, 9, 17)
SNAPSHOT_DATE = date(2026, 9, 16)


class EmptyOfficialAdapter:
    def get_current_instrument_observations(self, query):
        assert query.as_of_date == OFFICIAL_DATE
        return ()

    def get_lifecycle_observations(self, query):
        assert query.as_of_date == OFFICIAL_DATE
        return ()


class EmptyBaoStockAdapter:
    def get_instrument_snapshot(self, query, *, identity_bindings=()):
        assert query.as_of_date == SNAPSHOT_DATE
        assert identity_bindings == ()
        return ChinaAshareInstrumentSourceBatchV1(
            provider_id=BAOSTOCK_ASHARE_PROVIDER_ID,
            query=query,
            instruments=(),
            source_states=(),
            source_request_count=1,
        )


def test_default_plan_and_capture_remain_bounded_and_fail_closed(
    tmp_path: Path,
) -> None:
    plan = build_default_china_ashare_pilot_plan(
        planned_at=NOW,
        official_reference_as_of_date=OFFICIAL_DATE,
        baostock_snapshot_date=SNAPSHOT_DATE,
    )

    result = capture_china_ashare_pilot_reference(
        custody_root=tmp_path / "china-a-share-research-pilot",
        plan=plan,
        official_adapter=EmptyOfficialAdapter(),
        baostock_adapter=EmptyBaoStockAdapter(),
        created_at=NOW,
    )

    assert len(plan.anchors) == 7
    assert plan.history_start_date == date(2021, 9, 16)
    assert result.quality_report.source_request_count == 7
    assert result.quality_report.reference_evidence_complete is False
    assert result.quality_report.research_backtest_authorized is False
    assert result.manifest.canonical_apply_authorized is False
