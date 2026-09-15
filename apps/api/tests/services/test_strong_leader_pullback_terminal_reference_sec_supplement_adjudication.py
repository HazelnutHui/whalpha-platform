from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_adjudication as service,
)
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_supplement_plan as plan,
)


_DOCUMENTS = {
    "REVG": (
        "Each REV share was converted to 0.9809 of a share of Terex common "
        "stock and $8.71 in cash."
    ),
    "SKX": (
        "The Mixed Election Consideration consists of $57.00 and one common "
        "limited liability company unit."
    ),
}


def _inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, omit: str | None = None
) -> None:
    items = []
    source_root = tmp_path / "source=test"
    source_root.mkdir()
    for sequence, registered in enumerate(plan._REQUESTS, start=1):
        item = service.plan.TerminalReferenceSecPlanItemV1.model_validate(
            {
                **registered,
                "request_sequence": sequence,
                "request_url": service.plan._document_url(
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
        (directory / "document.bin").write_text(
            f"<html><body>{body}</body></html>"
        )
    monkeypatch.setattr(
        service.supplement_plan,
        "read_strong_leader_pullback_terminal_reference_sec_supplement_plan",
        lambda **_: SimpleNamespace(
            report=SimpleNamespace(
                items=tuple(items), logical_fingerprint="1" * 64
            ),
            report_sha256="2" * 64,
        ),
    )
    monkeypatch.setattr(
        service.supplement_source,
        "read_strong_leader_pullback_terminal_reference_sec_supplement_source",
        lambda **_: SimpleNamespace(
            output_root=source_root,
            manifest=SimpleNamespace(logical_fingerprint="3" * 64),
            manifest_sha256="4" * 64,
        ),
    )


def test_all_supplemental_fields_match_without_creating_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inputs(tmp_path, monkeypatch)
    result = (
        service
        .adjudicate_strong_leader_pullback_terminal_reference_sec_supplement_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 15, 3, tzinfo=UTC),
        )
    )

    assert result.completion_status == "all_fields_matched"
    assert result.matched_case_count == 2
    assert result.unsupported_case_count == 0
    assert result.source_fact_count == 3
    assert result.terminal_reference_count == 0
    assert result.outcome_count == 0
    assert result.network_request_count == 0


def test_missing_supplemental_language_stays_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inputs(tmp_path, monkeypatch, omit="SKX")
    result = (
        service
        .adjudicate_strong_leader_pullback_terminal_reference_sec_supplement_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            source_root=Path("/unused/source"),
            source_custody_root=Path("/unused"),
            implementation_revision="a" * 40,
            evaluated_at=datetime(2026, 9, 15, 3, tzinfo=UTC),
        )
    )

    assert result.completion_status == "source_fields_unresolved"
    assert result.matched_case_count == 1
    skx = next(item for item in result.cases if item.ticker_locator == "SKX")
    assert skx.completion_status == "unsupported"
    assert skx.fields[0].evidence_text is None
