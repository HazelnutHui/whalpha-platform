from __future__ import annotations

import json

import pytest

from tip_api.persistence.instrument_master import InstrumentMasterSnapshotCorruptionError
from tip_api.services.current_historical_mechanics_evidence import (
    assess_current_historical_mechanics_evidence,
)
from tests.support.eod_read_dataset import publish_completed_eod_dataset


def _inventory(root):
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                path.stat().st_size if path.is_file() else None,
            )
            for path in root.rglob("*")
        )
    )


def test_current_eod_identity_adapts_to_unpublished_evidence_without_writes(
    tmp_path,
) -> None:
    publish_completed_eod_dataset(tmp_path)
    before = _inventory(tmp_path)

    first = assess_current_historical_mechanics_evidence(tmp_path)
    second = assess_current_historical_mechanics_evidence(tmp_path)

    assert first == second
    assert first.status == "mechanics_only"
    assert first.observed_session_count == 1
    assert first.missing_history_session_count == 251
    assert [item.family for item in first.families] == [
        "eod_price_bar",
        "point_in_time_identity",
    ]
    assert all(
        item.validation_status == "validated_not_published"
        and item.publication_exists is False
        for item in first.families
    )
    assert first.evidence_publication_performed is False
    assert first.historical_coverage_publication_performed is False
    assert first.external_request_count == 0
    assert first.production_write_count == 0
    assert _inventory(tmp_path) == before
    assert not (tmp_path / "market-data" / "historical-coverage-evidence").exists()


def test_current_identity_adapter_rejects_snapshot_path_escape(tmp_path) -> None:
    publish_completed_eod_dataset(tmp_path)
    snapshot = (
        tmp_path
        / "market-data"
        / "snapshots"
        / "instrument-master"
        / "as_of_date=2026-08-13"
        / "manifest.json"
    )
    manifest = json.loads(snapshot.read_text(encoding="utf-8"))
    manifest["instrument_partition_path"] = "/outside/canonical/root"
    snapshot.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        InstrumentMasterSnapshotCorruptionError,
        match="partition reference",
    ):
        assess_current_historical_mechanics_evidence(tmp_path)
