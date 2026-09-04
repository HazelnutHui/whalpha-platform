from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import historical_universe_membership_shadow_batch as module
from tip_api.services.historical_universe_membership_shadow import (
    HistoricalUniverseMembershipIdentityMismatchError,
)
from tip_api.services.historical_universe_membership_shadow_batch import (
    HistoricalUniverseMembershipShadowBatchError,
    _validate_batch_paths,
    run_historical_universe_membership_shadow_batch,
)
from tip_api.services.historical_universe_membership_shadow_batch_cli import (
    _parse_session_packages,
)

FIRST = date(2026, 9, 2)
SECOND = date(2026, 9, 3)
NOW = datetime(2026, 9, 4, 16, tzinfo=UTC)


def test_session_package_parser_is_explicit_and_rejects_duplicates() -> None:
    result = _parse_session_packages(
        [f"{FIRST.isoformat()}=/tmp/first", f"{SECOND.isoformat()}=/tmp/second"]
    )
    assert result == {FIRST: Path("/tmp/first"), SECOND: Path("/tmp/second")}
    with pytest.raises(ValueError, match="duplicate"):
        _parse_session_packages(
            [f"{FIRST.isoformat()}=/tmp/first", f"{FIRST.isoformat()}=/tmp/other"]
        )


def test_batch_paths_must_be_tmp_disjoint_and_bounded(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    package = tmp_path / "package"
    data_root.mkdir()
    package.mkdir()
    output = Path("/tmp") / f"membership-batch-{tmp_path.name}"

    source, target, packages = _validate_batch_paths(
        data_root=data_root,
        output_root=output,
        package_paths={FIRST: package},
    )
    assert source == data_root.resolve()
    assert target == output.resolve()
    assert packages[FIRST] == package.resolve()
    with pytest.raises(HistoricalUniverseMembershipShadowBatchError, match="disjoint"):
        _validate_batch_paths(
            data_root=data_root,
            output_root=data_root / "output",
            package_paths={FIRST: package},
        )


def test_batch_reuses_shared_inputs_and_localizes_package_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data"
    first_package = tmp_path / "first-package"
    second_package = tmp_path / "second-package"
    for path in (data_root, first_package, second_package):
        path.mkdir()
    output_root = Path("/tmp") / f"membership-batch-test-{tmp_path.name}"
    panel = SimpleNamespace(session_reads=(1, 2, 3))
    snapshot = object()
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        module,
        "prepare_historical_universe_membership_eod_panel",
        lambda **kwargs: calls.append(("panel", kwargs["analysis_sessions"])) or panel,
    )
    monkeypatch.setattr(
        module,
        "read_completed_security_evidence_snapshot",
        lambda *args, **kwargs: calls.append(("catalog", kwargs["as_of_date"]))
        or snapshot,
    )

    records = ("row",)
    reconstruction = SimpleNamespace(
        records=records,
        methodology_version="method-v1",
        evaluated_base_count=10,
        included_counts=(("primary", 2),),
        excluded_counts=(("primary", 7),),
        quarantined_counts=(("primary", 1),),
    )

    def build_shadow(**kwargs):
        calls.append(("build", kwargs["session_date"]))
        assert kwargs["eod_panel"] is panel
        assert kwargs["security_snapshot"] is snapshot
        if kwargs["session_date"] == FIRST:
            raise HistoricalUniverseMembershipIdentityMismatchError(
                "fixture source failure"
            )
        return SimpleNamespace(reconstruction=reconstruction)

    monkeypatch.setattr(
        module,
        "build_historical_universe_membership_shadow",
        build_shadow,
    )

    class FakeRepository:
        def __init__(self, root, created_at):
            assert root == output_root.resolve()
            assert created_at == NOW

        def publish_universe_membership(self, values, **kwargs):
            assert values == records
            return SimpleNamespace(
                status="published",
                partition_path=output_root / "partition",
                record_count=1,
                logical_fingerprint="a" * 64,
                physical_sha256="b" * 64,
            )

        def read_universe_membership(self, _path):
            return records

    monkeypatch.setattr(module, "ParquetHistoricalResearchRepository", FakeRepository)

    result = run_historical_universe_membership_shadow_batch(
        data_root=data_root,
        package_paths={SECOND: second_package, FIRST: first_package},
        catalog_as_of_date=date(2026, 8, 14),
        evaluated_at=NOW,
        output_root=output_root,
        calendar=object(),
    )

    assert result.status == "completed_with_source_failures"
    assert result.requested_session_count == 2
    assert result.completed_session_count == 1
    assert result.failed_session_count == 1
    assert result.shared_eod_partition_read_count == 3
    assert [item.session_date for item in result.sessions] == [
        FIRST.isoformat(),
        SECOND.isoformat(),
    ]
    assert result.sessions[0].status == "source_validation_failed"
    assert result.sessions[0].failure_code == "identity_snapshot_mismatch"
    assert result.sessions[1].logical_fingerprint == "a" * 64
    assert [item[0] for item in calls].count("panel") == 1
    assert [item[0] for item in calls].count("catalog") == 1
