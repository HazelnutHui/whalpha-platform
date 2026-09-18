from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_endpoint_selection_package import (
    build_sec_cash_quality_endpoint_selection_plan_v1,
    build_sec_cash_quality_ttm_feasibility_plan_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    build_sec_cash_quality_source_readiness_plan_v1,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    publish_sec_cash_quality_endpoint_selection_package,
    publish_sec_cash_quality_ttm_feasibility_plan,
    read_sec_cash_quality_endpoint_selection_package,
    read_sec_cash_quality_ttm_feasibility_plan,
)
from tip_api.providers.sec.companyfacts_normalized_source import (
    SecCompanyfactsNormalizedSourceResult,
)
from tip_api.services.quant_research_sec_cash_quality_source_readiness_census import (
    independently_verify_prepared_sec_cash_quality_source_readiness,
    prepare_sec_cash_quality_target_evidence,
)
from tip_api.services.quant_research_sec_cash_quality_endpoint_selection_build import (
    build_sec_cash_quality_endpoint_selection_tables,
)
from tests.services.test_quant_research_sec_cash_quality_source_readiness_census import (
    _package,
)


def test_endpoint_package_is_ready_only_owner_only_and_exactly_rereads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_package, manifest = _package(tmp_path)
    source = SecCompanyfactsNormalizedSourceResult(
        package_path=source_package,
        manifest=manifest,
    )
    def read_with_filter(**kwargs):
        consumer = kwargs["occurrence_batch_consumer"]
        concepts = kwargs["occurrence_concept_filter"]
        artifact = next(
            item for item in manifest.artifacts if item.artifact_kind == "occurrence"
        )
        for batch in pq.ParquetFile(source_package / artifact.relative_path).iter_batches():
            filtered = batch.filter(
                pc.is_in(
                    batch.column(batch.schema.get_field_index("concept_name")),
                    value_set=pa.array(sorted(concepts)),
                )
            )
            consumer(artifact, filtered)
        return source

    monkeypatch.setattr(
        "tip_api.services.quant_research_sec_cash_quality_source_readiness_census."
        "read_sec_companyfacts_normalized_source",
        read_with_filter,
    )
    readiness_plan = build_sec_cash_quality_source_readiness_plan_v1(manifest)
    prepared = prepare_sec_cash_quality_target_evidence(
        normalized_package_path=source_package,
        plan=readiness_plan,
    )
    readiness_result, verification = (
        independently_verify_prepared_sec_cash_quality_source_readiness(
            normalized_package_path=source_package,
            plan=readiness_plan,
            prepared=prepared,
        )
    )
    plan = build_sec_cash_quality_endpoint_selection_plan_v1(
        readiness_plan=readiness_plan,
        readiness_result=readiness_result,
        readiness_verification=verification,
    )
    target, selected = build_sec_cash_quality_endpoint_selection_tables(
        plan=plan,
        prepared=prepared,
    )

    published = publish_sec_cash_quality_endpoint_selection_package(
        custody_root=tmp_path / "selection-custody",
        plan=plan,
        target_index=target,
        selected_endpoints=selected,
        built_at=datetime(2025, 8, 5, tzinfo=UTC),
    )
    reread = read_sec_cash_quality_endpoint_selection_package(
        package_path=published.package_path
    )
    feasibility = build_sec_cash_quality_ttm_feasibility_plan_v1(
        selection_plan=plan,
        package_manifest=reread.manifest,
    )
    feasibility_result = publish_sec_cash_quality_ttm_feasibility_plan(
        custody_root=tmp_path / "ttm-plan-custody",
        plan=feasibility,
    )
    feasibility_reread = read_sec_cash_quality_ttm_feasibility_plan(
        package_path=feasibility_result.package_path
    )

    assert published.status == "published"
    assert reread.status == "exact_reread_complete"
    assert reread.manifest.target_index_row_count == 5
    assert reread.manifest.selected_endpoint_count == 1
    assert reread.manifest.selected_query_row_count == 3
    assert feasibility.plan_only is True
    assert feasibility.ttm_derivation_authorized is False
    assert feasibility.security_projection_authorized is False
    assert feasibility_result.status == "published"
    assert feasibility_reread.plan == feasibility
