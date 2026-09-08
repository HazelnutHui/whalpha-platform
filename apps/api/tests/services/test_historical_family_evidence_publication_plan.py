from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.persistence.historical_research import HistoricalResearchCorruptionError
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.services import historical_family_evidence_publication_plan as service
from tests.support.eod_read_dataset import publish_completed_eod_dataset


def _inventory(root: Path) -> tuple[tuple[str, int | None], ...]:
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                path.stat().st_size if path.is_file() else None,
            )
            for path in root.rglob("*")
        )
    )


@contextmanager
def _new_plan_path():
    path = Path("/tmp") / f"whalpha-family-evidence-test-{uuid4().hex}.json"
    staging = path.with_name(f".{path.name}.staging")
    try:
        yield path
    finally:
        for candidate in (path, staging):
            if os.path.lexists(candidate) and not candidate.is_dir():
                candidate.chmod(0o600, follow_symlinks=False)
                candidate.unlink()


def _prepare(monkeypatch, tmp_path: Path) -> None:
    publish_completed_eod_dataset(tmp_path)
    monkeypatch.setattr(service, "APPROVED_DATA_ROOT", tmp_path.resolve())


def test_build_and_reread_exact_two_family_plan_without_canonical_writes(
    monkeypatch,
    tmp_path,
) -> None:
    _prepare(monkeypatch, tmp_path)
    before = _inventory(tmp_path)

    with _new_plan_path() as plan_path:
        built = service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=plan_path,
        )
        reread = service.read_current_historical_family_evidence_publication_plan(
            plan_path=plan_path,
            approved_plan_sha256=built.plan_sha256,
        )

        assert reread == built
        assert stat.S_IMODE(plan_path.stat().st_mode) == 0o400
        assert [item.family.value for item in built.plan.families] == [
            "eod_price_bar",
            "point_in_time_identity",
        ]
        assert built.plan.inventory_change_file_count == 2
        assert built.plan.target_absent_count == 2
        assert built.plan.recovery_policy == "verify_exact_then_complete"
        assert built.plan.canonical_data_write_count == 0
        assert built.plan.apply_authorized is False
        assert built.plan.historical_coverage_authorized is False
        assert all(
            item.expected_target_state == "absent"
            for item in built.plan.families
        )

    assert _inventory(tmp_path) == before
    assert not (tmp_path / "market-data" / "historical-coverage-evidence").exists()


def test_plan_is_deterministic_for_unchanged_sources(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)

    with _new_plan_path() as first_path, _new_plan_path() as second_path:
        first = service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=first_path,
        )
        second = service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=second_path,
        )

        assert first.plan == second.plan
        assert first.plan_sha256 == second.plan_sha256
        assert first_path.read_bytes() == second_path.read_bytes()


def test_reread_rejects_source_byte_drift(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)

    with _new_plan_path() as plan_path:
        built = service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=plan_path,
        )
        reference = built.plan.families[0].evidence.artifacts[0].payload_files[0]
        source = tmp_path / reference.path
        original_mode = stat.S_IMODE(source.stat().st_mode)
        source.chmod(0o600)
        source.write_bytes(source.read_bytes() + b"drift")
        source.chmod(original_mode)

        with pytest.raises(
            HistoricalResearchCorruptionError,
            match="physical file hash differs",
        ):
            service.read_current_historical_family_evidence_publication_plan(
                plan_path=plan_path,
                approved_plan_sha256=built.plan_sha256,
            )


def test_reread_rejects_target_collision(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)

    with _new_plan_path() as plan_path:
        built = service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=plan_path,
        )
        ParquetHistoricalCoverageRepository(tmp_path).publish_dataset_evidence(
            built.plan.families[0].evidence
        )

        with pytest.raises(
            service.HistoricalFamilyEvidencePublicationPlanError,
            match="no longer absent",
        ):
            service.read_current_historical_family_evidence_publication_plan(
                plan_path=plan_path,
                approved_plan_sha256=built.plan_sha256,
            )


def test_reread_rejects_wrong_approved_plan_sha(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)

    with _new_plan_path() as plan_path:
        service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=plan_path,
        )

        with pytest.raises(
            service.HistoricalFamilyEvidencePublicationPlanError,
            match="SHA-256 differs",
        ):
            service.read_current_historical_family_evidence_publication_plan(
                plan_path=plan_path,
                approved_plan_sha256="0" * 64,
            )


def test_build_rejects_plan_outside_direct_tmp_without_writes(
    monkeypatch,
    tmp_path,
) -> None:
    _prepare(monkeypatch, tmp_path)
    before = _inventory(tmp_path)
    rejected_path = tmp_path / "plan.json"

    with pytest.raises(
        service.HistoricalFamilyEvidencePublicationPlanError,
        match="outside direct /tmp custody",
    ):
        service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=rejected_path,
        )

    assert not rejected_path.exists()
    assert _inventory(tmp_path) == before


def test_reread_rejects_noncanonical_plan_bytes(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)

    with _new_plan_path() as plan_path:
        service.build_current_historical_family_evidence_publication_plan(
            data_root=tmp_path.resolve(),
            plan_path=plan_path,
        )
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_path.chmod(0o600)
        plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        plan_path.chmod(0o400)

        with pytest.raises(
            service.HistoricalFamilyEvidencePublicationPlanError,
            match="bytes are not canonical",
        ):
            service.read_current_historical_family_evidence_publication_plan(
                plan_path=plan_path,
            )
