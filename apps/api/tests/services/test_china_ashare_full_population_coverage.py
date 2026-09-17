from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    china_ashare_full_population_coverage_report_v1,
)
from tip_api.persistence.china_ashare_full_population_coverage import (
    ChinaAshareFullPopulationCoverageCustodyError,
    publish_china_ashare_full_population_coverage,
    read_china_ashare_full_population_coverage,
)
from tip_api.services.china_ashare_full_population_coverage import (
    ChinaAshareFullPopulationCoverageError,
    verify_china_ashare_full_population_coverage,
)


def test_coverage_report_publishes_and_exactly_rereads(tmp_path: Path) -> None:
    report = china_ashare_full_population_coverage_report_v1()
    root = tmp_path / "coverage"

    published = publish_china_ashare_full_population_coverage(
        custody_root=root, report=report
    )
    reread = read_china_ashare_full_population_coverage(
        package_path=published.package_path
    )
    duplicate = publish_china_ashare_full_population_coverage(
        custody_root=root, report=report
    )

    assert published.status == "published"
    assert reread.status == "exact_reread_complete"
    assert duplicate.status == "already_present"
    assert reread.report == report
    assert published.report_physical_sha256 == reread.report_physical_sha256
    assert (published.package_path.stat().st_mode & 0o777) == 0o700
    assert (published.report_path.stat().st_mode & 0o777) == 0o400


def test_coverage_report_rejects_custody_drift(tmp_path: Path) -> None:
    published = publish_china_ashare_full_population_coverage(
        custody_root=tmp_path / "coverage",
        report=china_ashare_full_population_coverage_report_v1(),
    )
    published.report_path.chmod(0o600)

    with pytest.raises(
        ChinaAshareFullPopulationCoverageCustodyError,
        match="custody differs",
    ):
        read_china_ashare_full_population_coverage(
            package_path=published.package_path
        )


def test_coverage_verifier_rejects_unbound_run_root(tmp_path: Path) -> None:
    with pytest.raises(
        ChinaAshareFullPopulationCoverageError,
        match="run root is invalid",
    ):
        verify_china_ashare_full_population_coverage(
            normalized_run_root=tmp_path / "wrong"
        )
