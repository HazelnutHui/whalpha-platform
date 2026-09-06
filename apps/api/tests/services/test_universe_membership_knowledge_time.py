from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.services import universe_membership_knowledge_time as service
from tip_api.services.universe_membership_knowledge_time import (
    UniverseMembershipKnowledgeTimeError,
    assess_universe_membership_knowledge_time,
)


SESSION = date(2026, 8, 14)
NEXT_SESSION = date(2026, 8, 17)
CLOSE = datetime(2026, 8, 14, 20, tzinfo=UTC)
SOURCE_CUTOFF = datetime(2026, 8, 14, 21, tzinfo=UTC)
EVALUATED = datetime(2026, 8, 14, 22, tzinfo=UTC)
NEXT_OPEN = datetime(2026, 8, 17, 13, 30, tzinfo=UTC)
ASSESSED = datetime(2026, 8, 17, 10, tzinfo=UTC)
SOURCE_FINGERPRINT = "c" * 64


class FixedCalendar:
    calendar_id = "XNYS"
    calendar_version = "fixture-1"

    def next_session(self, session_date):
        assert session_date == SESSION
        return NEXT_SESSION

    def session_close(self, session_date):
        assert session_date == SESSION
        return CLOSE

    def session_open(self, session_date):
        assert session_date == NEXT_SESSION
        return NEXT_OPEN


def _publish_membership(root, *, evaluated_at=EVALUATED):
    root.mkdir()
    root.chmod(0o700)
    instrument_id = UUID("11111111-1111-4111-8111-111111111111")
    from tip_api.services.universe_membership_reconstruction import (
        stable_instrument_set_fingerprint,
    )

    record = UniverseMembershipDecisionV1(
        universe_id="primary",
        instrument_id=instrument_id,
        session_date=SESSION,
        methodology_version="fixture-v1",
        origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        disposition=UniverseMembershipDisposition.INCLUDED,
        is_member=True,
        reason_codes=("included",),
        evaluated_base_fingerprint=stable_instrument_set_fingerprint(
            frozenset({instrument_id})
        ),
        source_fingerprints=(SOURCE_FINGERPRINT,),
        source_data_cutoff=SOURCE_CUTOFF,
        evaluated_at=evaluated_at,
        quality_status=QualityStatus.VALID,
    )
    return ParquetHistoricalResearchRepository(
        root,
        created_at=evaluated_at,
    ).publish_universe_membership(
        (record,),
        methodology_version=record.methodology_version,
        session_date=SESSION,
    )


def _source(point_in_time_eligibility="eligible_at_source_observed_at"):
    return SimpleNamespace(
        manifest=SimpleNamespace(
            as_of_date=SESSION,
            logical_fingerprint=SOURCE_FINGERPRINT,
            source_package_fetched_at=SOURCE_CUTOFF,
            contract_version="historical-identity-source-custody/1.1",
            point_in_time_eligibility=point_in_time_eligibility,
        )
    )


def test_direct_daily_source_completed_before_next_open_is_signal_eligible(
    tmp_path,
    monkeypatch,
) -> None:
    membership_root = tmp_path / "membership"
    published = _publish_membership(membership_root)
    monkeypatch.setattr(
        service,
        "read_historical_identity_source_custody",
        lambda **_: _source(),
    )

    result = assess_universe_membership_knowledge_time(
        data_root=tmp_path,
        membership_root=membership_root,
        membership_partition_path=published.partition_path,
        provider="massive",
        assessed_at=ASSESSED,
        calendar=FixedCalendar(),
    )

    assert result.point_in_time_eligibility is PointInTimeEligibility.SIGNAL_ELIGIBLE
    assert result.entry_session_date == NEXT_SESSION
    assert result.next_session_open_at == NEXT_OPEN
    assert result.reason_codes == (
        "source_and_evaluation_completed_before_next_session_open",
    )
    assert len(result.logical_fingerprint) == 64


def test_historical_source_policy_remains_outcome_only(tmp_path, monkeypatch) -> None:
    membership_root = tmp_path / "membership"
    published = _publish_membership(membership_root)
    monkeypatch.setattr(
        service,
        "read_historical_identity_source_custody",
        lambda **_: _source("outcome_reconciliation_only"),
    )

    result = assess_universe_membership_knowledge_time(
        data_root=tmp_path,
        membership_root=membership_root,
        membership_partition_path=published.partition_path,
        provider="massive",
        assessed_at=ASSESSED,
        calendar=FixedCalendar(),
    )

    assert (
        result.point_in_time_eligibility
        is PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
    )
    assert result.reason_codes == (
        "identity_source_outcome_reconciliation_only",
    )


def test_missing_source_fingerprint_binding_is_rejected(tmp_path, monkeypatch) -> None:
    membership_root = tmp_path / "membership"
    published = _publish_membership(membership_root)
    source = _source()
    source.manifest.logical_fingerprint = "d" * 64
    monkeypatch.setattr(
        service,
        "read_historical_identity_source_custody",
        lambda **_: source,
    )

    with pytest.raises(
        UniverseMembershipKnowledgeTimeError,
        match="does not bind",
    ):
        assess_universe_membership_knowledge_time(
            data_root=tmp_path,
            membership_root=membership_root,
            membership_partition_path=published.partition_path,
            provider="massive",
            assessed_at=ASSESSED,
            calendar=FixedCalendar(),
        )


def test_group_writable_temporary_root_is_rejected(tmp_path, monkeypatch) -> None:
    membership_root = tmp_path / "membership"
    published = _publish_membership(membership_root)
    membership_root.chmod(0o770)
    monkeypatch.setattr(
        service,
        "read_historical_identity_source_custody",
        lambda **_: _source(),
    )

    with pytest.raises(
        UniverseMembershipKnowledgeTimeError,
        match="owner-only",
    ):
        assess_universe_membership_knowledge_time(
            data_root=tmp_path,
            membership_root=membership_root,
            membership_partition_path=published.partition_path,
            provider="massive",
            assessed_at=ASSESSED,
            calendar=FixedCalendar(),
        )
