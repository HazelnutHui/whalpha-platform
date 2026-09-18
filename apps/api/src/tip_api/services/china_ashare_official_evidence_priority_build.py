"""Build and independently persist a deterministic offline evidence plan."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from tip_api.persistence.china_ashare_conservative_reconstruction_package import (
    read_china_ashare_conservative_reconstruction_package,
)
from tip_api.persistence.china_ashare_official_evidence_priority_plan import (
    ChinaAshareOfficialEvidencePriorityPackageResultV1,
    publish_china_ashare_official_evidence_priority_plan,
)
from tip_api.services.china_ashare_official_evidence_priority_plan import (
    plan_china_ashare_official_evidence_priority,
)


class ChinaAshareOfficialEvidencePriorityBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareOfficialEvidencePriorityReplayResultV1:
    primary: ChinaAshareOfficialEvidencePriorityPackageResultV1
    replay: ChinaAshareOfficialEvidencePriorityPackageResultV1
    forward_reverse_identical: bool
    byte_identical: bool
    physical_hashes_identical: bool
    physical_sha256s: tuple[tuple[str, str], ...]


def build_and_replay_china_ashare_official_evidence_priority_plan(
    *, input_package_path: Path, output_custody_root: Path,
    replay_custody_root: Path,
) -> ChinaAshareOfficialEvidencePriorityReplayResultV1:
    if output_custody_root.expanduser().resolve() == (
        replay_custody_root.expanduser().resolve()
    ):
        raise ChinaAshareOfficialEvidencePriorityBuildError(
            "official evidence replay custody must be independent"
        )
    source = read_china_ashare_conservative_reconstruction_package(
        package_path=input_package_path
    )
    forward = plan_china_ashare_official_evidence_priority(
        reconstruction_package=source,
        reverse_candidate_input=False,
    )
    reverse = plan_china_ashare_official_evidence_priority(
        reconstruction_package=source,
        reverse_candidate_input=True,
    )
    if forward != reverse:
        raise ChinaAshareOfficialEvidencePriorityBuildError(
            "forward and reverse official evidence plans differ"
        )
    primary = publish_china_ashare_official_evidence_priority_plan(
        custody_root=output_custody_root,
        plan=forward,
    )
    replay = publish_china_ashare_official_evidence_priority_plan(
        custody_root=replay_custody_root,
        plan=reverse,
    )
    primary_files = _files(primary.package_path)
    replay_files = _files(replay.package_path)
    if primary_files != replay_files:
        raise ChinaAshareOfficialEvidencePriorityBuildError(
            "official evidence priority physical replay differs"
        )
    hashes = tuple(
        (name, hashlib.sha256(payload).hexdigest())
        for name, payload in primary_files
    )
    return ChinaAshareOfficialEvidencePriorityReplayResultV1(
        primary=primary,
        replay=replay,
        forward_reverse_identical=True,
        byte_identical=True,
        physical_hashes_identical=True,
        physical_sha256s=hashes,
    )


def _files(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (item.relative_to(root).as_posix(), item.read_bytes())
        for item in sorted(root.rglob("*"))
        if item.is_file() and not item.is_symlink()
    )
