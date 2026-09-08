from __future__ import annotations

import os
import socket
import stat
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services import historical_family_evidence_apply as apply_service
from tip_api.services import historical_family_evidence_publication_plan as plan_service
from tests.support.eod_read_dataset import publish_completed_eod_dataset


@contextmanager
def _new_plan_path():
    path = Path("/tmp") / f"whalpha-family-evidence-apply-test-{uuid4().hex}.json"
    staging = path.with_name(f".{path.name}.staging")
    try:
        yield path
    finally:
        for candidate in (path, staging):
            if os.path.lexists(candidate) and not candidate.is_dir():
                candidate.chmod(0o600, follow_symlinks=False)
                candidate.unlink()


@contextmanager
def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "canonical"
    publish_completed_eod_dataset(data_root)
    approved = data_root.resolve()
    monkeypatch.setattr(plan_service, "APPROVED_DATA_ROOT", approved)
    monkeypatch.setattr(apply_service, "APPROVED_DATA_ROOT", approved)
    with _new_plan_path() as plan_path:
        evidence = (
            plan_service.build_current_historical_family_evidence_publication_plan(
                data_root=approved,
                plan_path=plan_path,
            )
        )
        yield data_root, plan_path, evidence


def _apply(data_root: Path, plan_path: Path, evidence, **kwargs):
    return apply_service.apply_approved_current_historical_family_evidence_plan(
        plan_path=plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        expected_family_set_fingerprint=evidence.plan.family_set_fingerprint,
        data_root=data_root,
        **kwargs,
    )


def _target(data_root: Path, item) -> Path:
    return (data_root / item.target_path).parent


def test_apply_publishes_eod_then_identity_and_formally_rereads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        publish = apply_service._publish_family_target
        observed: list[str] = []

        def ordered_publish(**kwargs) -> None:
            item = kwargs["item"]
            observed.append(item.family.value)
            if item.family.value == "point_in_time_identity":
                assert _target(data_root, evidence.plan.families[0]).is_dir()
            publish(**kwargs)

        monkeypatch.setattr(
            apply_service,
            "_publish_family_target",
            ordered_publish,
        )
        result = _apply(data_root, plan_path, evidence)

        assert observed == ["eod_price_bar", "point_in_time_identity"]
        assert result.status == "applied"
        assert result.published_families == tuple(observed)
        assert result.reused_families == ()
        assert result.published_file_count == 2
        assert result.published_bytes == evidence.plan.inventory_change_bytes
        assert result.formal_reread_family_count == 2
        assert result.external_request_count == 0
        assert result.overwritten_partition_count == 0
        assert result.deleted_partition_count == 0
        assert result.historical_coverage_authorized is False
        assert result.research_development_authorized is False
        assert result.research_performance_authorized is False
        assert result.post_state_fingerprint == inventory_fingerprint(data_root)
        for item in evidence.plan.families:
            target = _target(data_root, item)
            manifest = data_root / item.target_path
            assert stat.S_IMODE(target.stat().st_mode) == 0o755
            assert stat.S_IMODE(manifest.stat().st_mode) == 0o644


def test_eod_only_interruption_recovers_without_rewriting_eod(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        publish = apply_service._publish_family_target

        def interrupt_after_eod(**kwargs) -> None:
            publish(**kwargs)
            if kwargs["item"].family.value == "eod_price_bar":
                raise apply_service.HistoricalFamilyEvidenceApplyError(
                    "injected interruption"
                )

        with monkeypatch.context() as fault:
            fault.setattr(
                apply_service,
                "_publish_family_target",
                interrupt_after_eod,
            )
            with pytest.raises(
                apply_service.HistoricalFamilyEvidenceApplyError,
                match="injected interruption",
            ):
                _apply(data_root, plan_path, evidence)

        eod_target = _target(data_root, evidence.plan.families[0])
        identity_target = _target(data_root, evidence.plan.families[1])
        eod_inode = eod_target.stat().st_ino
        assert eod_target.is_dir()
        assert not identity_target.exists()

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="failed formal reread",
        ):
            _apply(data_root, plan_path, evidence)

        recovered = _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
        assert recovered.status == "verified_then_completed"
        assert recovered.published_families == ("point_in_time_identity",)
        assert recovered.reused_families == ("eod_price_bar",)
        assert recovered.published_file_count == 1
        assert recovered.published_bytes == (
            evidence.plan.families[1].evidence_manifest_bytes
        )
        assert eod_target.stat().st_ino == eod_inode
        assert identity_target.is_dir()


def test_completed_apply_recovery_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        _apply(data_root, plan_path, evidence)
        before = inventory_fingerprint(data_root)
        inodes = tuple(
            _target(data_root, item).stat().st_ino
            for item in evidence.plan.families
        )

        recovered = _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )

        assert recovered.published_families == ()
        assert recovered.reused_families == (
            "eod_price_bar",
            "point_in_time_identity",
        )
        assert recovered.published_file_count == 0
        assert recovered.published_bytes == 0
        assert inventory_fingerprint(data_root) == before
        assert tuple(
            _target(data_root, item).stat().st_ino
            for item in evidence.plan.families
        ) == inodes


def test_recovery_without_completed_prefix_refuses_to_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        before = inventory_fingerprint(data_root)

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="failed formal reread",
        ):
            _apply(
                data_root,
                plan_path,
                evidence,
                verify_then_complete=True,
            )

        assert inventory_fingerprint(data_root) == before
        assert all(
            not _target(data_root, item).exists()
            for item in evidence.plan.families
        )


def test_recovery_rejects_identity_without_eod_and_preserves_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        identity = evidence.plan.families[1]
        apply_service._publish_family_target(
            root=data_root,
            item=identity,
            plan_fingerprint=evidence.plan.logical_fingerprint,
        )
        identity_target = _target(data_root, identity)
        before = inventory_fingerprint(data_root)

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="failed formal reread",
        ):
            _apply(
                data_root,
                plan_path,
                evidence,
                verify_then_complete=True,
            )

        assert identity_target.is_dir()
        assert not _target(data_root, evidence.plan.families[0]).exists()
        assert inventory_fingerprint(data_root) == before


def test_recovery_rejects_corrupt_eod_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        eod = evidence.plan.families[0]
        apply_service._publish_family_target(
            root=data_root,
            item=eod,
            plan_fingerprint=evidence.plan.logical_fingerprint,
        )
        manifest = data_root / eod.target_path
        manifest.write_bytes(manifest.read_bytes() + b"drift")
        corrupted = manifest.read_bytes()

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="failed formal reread",
        ):
            _apply(
                data_root,
                plan_path,
                evidence,
                verify_then_complete=True,
            )

        assert manifest.read_bytes() == corrupted
        assert not _target(data_root, evidence.plan.families[1]).exists()


def test_recovery_preserves_and_rejects_staging_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        eod, identity = evidence.plan.families
        apply_service._publish_family_target(
            root=data_root,
            item=eod,
            plan_fingerprint=evidence.plan.logical_fingerprint,
        )
        target = _target(data_root, identity)
        staging = apply_service._staging_path(
            target,
            evidence.plan.logical_fingerprint,
        )
        staging.mkdir(parents=True, mode=0o755)

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="failed formal reread",
        ):
            _apply(
                data_root,
                plan_path,
                evidence,
                verify_then_complete=True,
            )

        assert staging.is_dir()
        assert not target.exists()


def test_pre_rename_failure_removes_only_apply_owned_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        eod = evidence.plan.families[0]
        target = _target(data_root, eod)
        staging = apply_service._staging_path(
            target,
            evidence.plan.logical_fingerprint,
        )

        def rejected_bytes(_evidence):
            raise apply_service.HistoricalFamilyEvidenceApplyError(
                "injected byte failure"
            )

        monkeypatch.setattr(
            apply_service,
            "historical_dataset_coverage_evidence_bytes",
            rejected_bytes,
        )
        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="injected byte failure",
        ):
            _apply(data_root, plan_path, evidence)

        assert not staging.exists()
        assert not target.exists()


def test_outside_inventory_drift_is_detected_and_completed_targets_recover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        calls = 0

        def drifting_inventory(_root: Path, _exclusions: tuple[Path, ...]) -> str:
            nonlocal calls
            calls += 1
            return ("a" if calls == 1 else "b") * 64

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="outside planned targets changed",
        ):
            _apply(
                data_root,
                plan_path,
                evidence,
                outside_inventory_reader=drifting_inventory,
            )

        assert all(
            _target(data_root, item).is_dir()
            for item in evidence.plan.families
        )
        recovered = _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
        assert recovered.published_file_count == 0
        assert len(recovered.reused_families) == 2


def test_exact_execution_binding_mismatch_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fixture(tmp_path, monkeypatch) as (data_root, plan_path, evidence):
        before = inventory_fingerprint(data_root)

        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="execution binding differs",
        ):
            apply_service.apply_approved_current_historical_family_evidence_plan(
                plan_path=plan_path,
                approved_plan_sha256=evidence.plan_sha256,
                expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
                expected_family_set_fingerprint="0" * 64,
                data_root=data_root,
            )

        assert inventory_fingerprint(data_root) == before
        assert all(
            not _target(data_root, item).exists()
            for item in evidence.plan.families
        )


def test_apply_network_guard_blocks_dns_and_restores() -> None:
    original = socket.getaddrinfo
    with apply_service._network_prohibited():
        with pytest.raises(
            apply_service.HistoricalFamilyEvidenceApplyError,
            match="network access is disabled",
        ):
            socket.getaddrinfo("localhost", 80)
    assert socket.getaddrinfo is original
