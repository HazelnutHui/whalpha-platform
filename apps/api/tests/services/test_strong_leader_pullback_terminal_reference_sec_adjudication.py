from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_adjudication as service,
)
from tip_api.services import strong_leader_pullback_terminal_reference_sec_plan as plan


_DOCUMENTS = {
    "LNW": (
        "The final day of trading on Nasdaq will be November 12, 2025. "
        "The shares will trade solely on the ASX beginning November 14, 2025."
    ),
    "MTSR": (
        "Each share receives $65.60 in cash and one contingent value right "
        "which may pay up to $20.65."
    ),
    "REVG": (
        "Each share will receive $8.71 in cash and 0.9809 shares of Terex "
        "common stock."
    ),
    "SAND": "Each share receives 0.0625 Royal Gold common shares.",
    "SKX": (
        "Holders may elect $63.00 in cash or $57.00 in cash and one Common "
        "Unit. The market value of each Common Unit was $29.00."
    ),
}


def _inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, omit: str | None = None
) -> None:
    items = []
    source_root = tmp_path / "source=test"
    source_root.mkdir()
    for sequence, registered in enumerate(plan._REQUESTS, start=1):
        item = plan.TerminalReferenceSecPlanItemV1.model_validate(
            {
                **registered,
                "request_sequence": sequence,
                "request_url": plan._document_url(
                    cik=registered["source_cik"],
                    accession=registered["accession_number"],
                    primary_document=registered["requested_document"],
                ),
            }
        )
        items.append(item)
        directory = source_root / f"request={sequence:06d}"
        directory.mkdir()
        body = (
            "unrelated filing text"
            if item.ticker_locator == omit
            else _DOCUMENTS[item.ticker_locator]
        )
        (directory / "document.bin").write_text(f"<html><body>{body}</body></html>")
    monkeypatch.setattr(
        service.plan,
        "read_strong_leader_pullback_terminal_reference_sec_plan",
        lambda **_: SimpleNamespace(
            report=SimpleNamespace(
                items=tuple(items), logical_fingerprint="1" * 64
            ),
            report_sha256="2" * 64,
        ),
    )
    monkeypatch.setattr(
        service.source,
        "read_strong_leader_pullback_terminal_reference_sec_source",
        lambda **_: SimpleNamespace(
            output_root=source_root,
            manifest=SimpleNamespace(logical_fingerprint="3" * 64),
            manifest_sha256="4" * 64,
        ),
    )


def test_all_five_sources_match_without_creating_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inputs(tmp_path, monkeypatch)
    result = service.adjudicate_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 15, 14, tzinfo=UTC),
    )

    assert result.completion_status == "all_fields_matched"
    assert result.matched_case_count == 5
    assert result.unsupported_case_count == 0
    assert result.source_fact_count == 11
    assert result.terminal_reference_count == 0
    assert result.outcome_count == 0
    assert result.performance_metric_count == 0
    assert all(
        field.evidence_text == service._normalize(field.evidence_text)
        for case in result.cases
        for field in case.fields
        if field.evidence_text is not None
    )


def test_missing_source_language_stays_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inputs(tmp_path, monkeypatch, omit="SKX")
    result = service.adjudicate_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 15, 14, tzinfo=UTC),
    )

    assert result.completion_status == "source_fields_unresolved"
    assert result.matched_case_count == 4
    assert result.unsupported_case_count == 1
    skx = next(item for item in result.cases if item.ticker_locator == "SKX")
    assert skx.completion_status == "unsupported"
    assert all(field.evidence_text is None for field in skx.fields)


def test_adjudication_fingerprint_is_tamper_evident(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inputs(tmp_path, monkeypatch)
    result = service.adjudicate_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        source_root=Path("/unused/source"),
        source_custody_root=Path("/unused"),
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 15, 14, tzinfo=UTC),
    )
    payload = result.model_dump(mode="json")
    payload["terminal_reference_count"] = 1

    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackTerminalReferenceSecAdjudicationV1.model_validate(
            payload
        )
