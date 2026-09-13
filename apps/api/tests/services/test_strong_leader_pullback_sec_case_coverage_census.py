from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.services import strong_leader_pullback_sec_case_coverage_census as service


class _Case(SimpleNamespace):
    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "instrument_id": str(self.instrument_id),
            "provider_ticker_locators": self.provider_ticker_locators,
            "cik_locators": self.cik_locators,
            "canonical_last_observed_date": self.canonical_last_observed_date,
            "provider_delist_date_candidate": self.provider_delist_date_candidate,
        }


def _candidate(instrument: int, fields: tuple[str, ...], **values: object) -> SimpleNamespace:
    return SimpleNamespace(
        instrument_id=UUID(int=instrument),
        partial_field_candidates=fields,
        **values,
    )


def _fixture() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    cases = tuple(
        _Case(
            instrument_id=UUID(int=index),
            provider_ticker_locators=(f"T{index}",),
            cik_locators=(f"{index:010d}",),
            canonical_last_observed_date=date(2026, 1, 6),
            provider_delist_date_candidate=date(2026, 1, 7),
        )
        for index in range(1, 65)
    )
    sample = SimpleNamespace(
        report=SimpleNamespace(
            lifecycle_cases=cases,
            logical_fingerprint="1" * 64,
        ),
        report_sha256="2" * 64,
    )
    notice_fields = (
        "source_availability_time_and_revision_history",
        "stable_security_and_listing_identifiers",
        "suspension_and_delisting_status_effective_dates",
    )
    form25_candidates = tuple(
        _candidate(index, notice_fields)
        for index in range(1, 63)
    ) + (
        _candidate(61, notice_fields),
        _candidate(62, notice_fields),
    )
    form15_candidates = tuple(
        _candidate(index, notice_fields, commission_file_number_state="single_candidate")
        for index in range(1, 63)
    ) + tuple(
        _candidate(
            index,
            notice_fields,
            commission_file_number_state=(
                "multiple_candidates" if sequence == 0 else "single_candidate"
            ),
        )
        for sequence, index in enumerate((60, 61, 62, 62))
    )
    transaction_fields = tuple(
        field
        for field in service.LIFECYCLE_REQUIRED_FIELDS
        if field != "bankruptcy_liquidation_or_otc_continuation"
    )
    transaction_candidates = tuple(
        _candidate(
            index,
            transaction_fields,
            structure_state=(
                "foreign_report_referenced_exhibit_only"
                if index == 63
                else "8k_item_2_01_candidate_scope"
            ),
        )
        for index in range(2, 65)
    ) + tuple(
        _candidate(
            ((sequence - 1) % 14) + 2,
            transaction_fields,
            structure_state="tender_amendment_primary_document",
        )
        for sequence in range(1, 27)
    )

    def report(
        candidates: tuple[SimpleNamespace, ...], count_name: str, count: int
    ) -> SimpleNamespace:
        return SimpleNamespace(
            candidates=candidates,
            plan_sha256="3" * 64,
            source_manifest_sha256="4" * 64,
            content_census_sha256="5" * 64,
            logical_fingerprint="6" * 64,
            **{count_name: count},
        )

    form25 = SimpleNamespace(
        report=report(form25_candidates, "form25_document_count", 64),
        report_sha256="7" * 64,
    )
    form15 = SimpleNamespace(
        report=report(form15_candidates, "form15_document_count", 66),
        report_sha256="8" * 64,
    )
    transaction = SimpleNamespace(
        report=report(
            transaction_candidates, "transaction_document_count", 89
        ),
        report_sha256="9" * 64,
    )
    return sample, form25, form15, transaction


def _patch_inputs(
    monkeypatch: pytest.MonkeyPatch,
    sample: SimpleNamespace,
    form25: SimpleNamespace,
    form15: SimpleNamespace,
    transaction: SimpleNamespace,
) -> None:
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_source_acceptance_sample",
        lambda **_: sample,
    )
    monkeypatch.setattr(
        service, "read_strong_leader_pullback_sec_form25_candidates", lambda **_: form25
    )
    monkeypatch.setattr(
        service, "read_strong_leader_pullback_sec_form15_candidates", lambda **_: form15
    )
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_transaction_candidates",
        lambda **_: transaction,
    )


def test_censuses_case_coverage_without_adjudicating_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample, form25, form15, transaction = _fixture()
    _patch_inputs(monkeypatch, sample, form25, form15, transaction)
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    target = custody / "census=fixture"
    result = service.build_strong_leader_pullback_sec_case_coverage_census(
        source_sample_root=Path("/unused/sample"),
        source_sample_custody_root=Path("/unused"),
        form25_root=Path("/unused/form25"),
        form25_custody_root=Path("/unused"),
        form15_root=Path("/unused/form15"),
        form15_custody_root=Path("/unused"),
        transaction_root=Path("/unused/transaction"),
        transaction_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 18, tzinfo=UTC),
    )

    assert result.status == "published"
    assert result.report.lifecycle_case_count == 64
    assert result.report.candidate_document_count == 219
    assert result.report.form25_case_count == 62
    assert result.report.form15_case_count == 62
    assert result.report.transaction_case_count == 63
    assert result.report.adjudicated_field_count == 0
    assert result.report.unsupported_field_count == 512
    assert result.report.referenced_completion_exhibit_body_missing_case_count == 1
    assert all(
        count == 64 for _, count in result.report.field_complete_result_counts
    )
    assert (target / "census.json").stat().st_mode & 0o777 == 0o400

    reread = service.read_strong_leader_pullback_sec_case_coverage_census(
        output_root=target, output_custody_root=custody
    )
    assert reread.report == result.report


def test_candidate_binding_mismatch_stops_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample, form25, form15, transaction = _fixture()
    transaction.report.plan_sha256 = "0" * 64
    _patch_inputs(monkeypatch, sample, form25, form15, transaction)
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    with pytest.raises(
        service.StrongLeaderPullbackSecCaseCoverageCensusError,
        match="bindings differ",
    ):
        service.build_strong_leader_pullback_sec_case_coverage_census(
            source_sample_root=Path("/unused/sample"),
            source_sample_custody_root=Path("/unused"),
            form25_root=Path("/unused/form25"),
            form25_custody_root=Path("/unused"),
            form15_root=Path("/unused/form15"),
            form15_custody_root=Path("/unused"),
            transaction_root=Path("/unused/transaction"),
            transaction_custody_root=Path("/unused"),
            output_root=custody / "census=fixture",
            output_custody_root=custody,
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 13, 18, tzinfo=UTC),
        )


def test_tampered_report_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample, form25, form15, transaction = _fixture()
    _patch_inputs(monkeypatch, sample, form25, form15, transaction)
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)
    target = custody / "census=fixture"
    service.build_strong_leader_pullback_sec_case_coverage_census(
        source_sample_root=Path("/unused/sample"),
        source_sample_custody_root=Path("/unused"),
        form25_root=Path("/unused/form25"),
        form25_custody_root=Path("/unused"),
        form15_root=Path("/unused/form15"),
        form15_custody_root=Path("/unused"),
        transaction_root=Path("/unused/transaction"),
        transaction_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 13, 18, tzinfo=UTC),
    )
    report = target / "census.json"
    report.chmod(0o600)
    report.write_bytes(
        report.read_bytes().replace(b'"lifecycle_fact_count":0', b'"lifecycle_fact_count":1')
    )
    report.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecCaseCoverageCensusError):
        service.read_strong_leader_pullback_sec_case_coverage_census(
            output_root=target, output_custody_root=custody
        )
