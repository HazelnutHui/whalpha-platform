from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    build_sec_cash_quality_source_readiness_plan_v1,
)
from tip_api.persistence.quant_research_sec_cash_quality_source_readiness import (
    SecCashQualitySourceReadinessCustodyError,
    publish_sec_cash_quality_source_readiness,
    read_sec_cash_quality_source_readiness,
)
from tip_api.providers.sec.companyfacts_normalized_source import (
    SecCompanyfactsNormalizedSourceResult,
)
from tip_api.services.quant_research_sec_cash_quality_source_readiness_census import (
    independently_verify_sec_cash_quality_source_readiness,
)
from tests.services.test_quant_research_sec_cash_quality_source_readiness_census import (
    _filtered_reader,
    _package,
)


def test_readiness_evidence_atomically_publishes_and_exactly_rereads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, manifest = _package(tmp_path)
    source = SecCompanyfactsNormalizedSourceResult(
        package_path=package,
        manifest=manifest,
    )
    monkeypatch.setattr(
        "tip_api.services.quant_research_sec_cash_quality_source_readiness_census."
        "read_sec_companyfacts_normalized_source",
        _filtered_reader(package, source),
    )
    plan = build_sec_cash_quality_source_readiness_plan_v1(manifest)
    result, verification = independently_verify_sec_cash_quality_source_readiness(
        normalized_package_path=package,
        plan=plan,
    )

    published = publish_sec_cash_quality_source_readiness(
        custody_root=tmp_path / "custody",
        plan=plan,
        result=result,
        verification=verification,
    )
    reread = read_sec_cash_quality_source_readiness(
        package_path=published.package_path
    )
    duplicate = publish_sec_cash_quality_source_readiness(
        custody_root=tmp_path / "custody",
        plan=plan,
        result=result,
        verification=verification,
    )

    assert published.status == "published"
    assert reread.status == "exact_reread_complete"
    assert duplicate.status == "already_present"
    assert reread.plan == plan
    assert reread.result == result
    assert reread.verification == verification
    assert (published.package_path.stat().st_mode & 0o777) == 0o700
    assert all(
        item.stat().st_mode & 0o777 == 0o400
        for item in published.package_path.iterdir()
    )


def test_readiness_evidence_reread_rejects_closed_set_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, manifest = _package(tmp_path)
    source = SecCompanyfactsNormalizedSourceResult(package_path=package, manifest=manifest)
    monkeypatch.setattr(
        "tip_api.services.quant_research_sec_cash_quality_source_readiness_census."
        "read_sec_companyfacts_normalized_source",
        _filtered_reader(package, source),
    )
    plan = build_sec_cash_quality_source_readiness_plan_v1(manifest)
    result, verification = independently_verify_sec_cash_quality_source_readiness(
        normalized_package_path=package,
        plan=plan,
    )
    published = publish_sec_cash_quality_source_readiness(
        custody_root=tmp_path / "custody",
        plan=plan,
        result=result,
        verification=verification,
    )
    extra = published.package_path / "unexpected.json"
    extra.write_bytes(b"{}")
    extra.chmod(0o400)

    with pytest.raises(
        SecCashQualitySourceReadinessCustodyError,
        match="inventory differs",
    ):
        read_sec_cash_quality_source_readiness(package_path=published.package_path)
