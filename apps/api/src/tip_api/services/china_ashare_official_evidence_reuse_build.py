"""Offline build and independent replay for local evidence reuse custody."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tip_api.persistence.china_ashare_official_evidence_priority_plan import (
    read_china_ashare_official_evidence_priority_plan,
)
from tip_api.persistence.china_ashare_official_evidence_reuse import (
    ChinaAshareOfficialEvidenceReusePackageResultV1,
    publish_china_ashare_official_evidence_reuse_package,
)
from tip_api.services.china_ashare_official_evidence_reuse import (
    build_local_official_evidence_inventory,
    build_reuse_census,
    build_warning_batch,
)


@dataclass(frozen=True, slots=True)
class ChinaAshareOfficialEvidenceReuseBuildResultV1:
    primary: ChinaAshareOfficialEvidenceReusePackageResultV1
    replay: ChinaAshareOfficialEvidenceReusePackageResultV1
    byte_identical: bool


def build_china_ashare_official_evidence_reuse_package(
    *, priority_plan_package: Path, official_event_plan_roots: tuple[Path, ...],
    official_document_plan_roots: tuple[Path, ...], cninfo_plan_roots: tuple[Path, ...],
    custody_root: Path, replay_custody_root: Path,
) -> ChinaAshareOfficialEvidenceReuseBuildResultV1:
    priority = read_china_ashare_official_evidence_priority_plan(package_path=priority_plan_package)
    inventory = build_local_official_evidence_inventory(
        official_event_plan_roots=official_event_plan_roots,
        official_document_plan_roots=official_document_plan_roots,
        cninfo_plan_roots=cninfo_plan_roots,
    )
    census = build_reuse_census(
        priority_plan_package_fingerprint=priority.manifest.logical_fingerprint,
        priority_plan=priority.plan, inventory=inventory,
    )
    warning = build_warning_batch(
        priority_plan_package_fingerprint=priority.manifest.logical_fingerprint,
        priority_plan=priority.plan, census=census,
    )
    primary = publish_china_ashare_official_evidence_reuse_package(
        custody_root=custody_root, inventory=inventory, census=census, warning_batch=warning,
    )
    replay_inventory = build_local_official_evidence_inventory(
        official_event_plan_roots=tuple(reversed(official_event_plan_roots)),
        official_document_plan_roots=tuple(reversed(official_document_plan_roots)),
        cninfo_plan_roots=tuple(reversed(cninfo_plan_roots)),
    )
    replay_census = build_reuse_census(
        priority_plan_package_fingerprint=priority.manifest.logical_fingerprint,
        priority_plan=priority.plan, inventory=replay_inventory,
    )
    replay_warning = build_warning_batch(
        priority_plan_package_fingerprint=priority.manifest.logical_fingerprint,
        priority_plan=priority.plan, census=replay_census,
    )
    replay = publish_china_ashare_official_evidence_reuse_package(
        custody_root=replay_custody_root, inventory=replay_inventory,
        census=replay_census, warning_batch=replay_warning,
    )
    left = {item.name: item.read_bytes() for item in primary.package_path.iterdir()}
    right = {item.name: item.read_bytes() for item in replay.package_path.iterdir()}
    return ChinaAshareOfficialEvidenceReuseBuildResultV1(
        primary=primary, replay=replay, byte_identical=left == right,
    )
