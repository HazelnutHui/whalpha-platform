from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    SOURCE_FIELD_NAMES,
)
from tip_api.providers.massive.same_day_catchup import (
    FetchArtifactV1,
    FetchPackageManifestV1,
    ValidatedIdentityReferencePackage,
)
from tip_api.services.historical_identity_rebuild_profile_map import (
    CURRENT_IDENTITY_REBUILD_PROFILE,
    PRE_ETV_IDENTITY_REBUILD_PROFILE,
    HistoricalIdentityRebuildProfileBindingV1,
    HistoricalIdentityRebuildProfileMapV1,
    historical_identity_profile_fingerprint,
)
from tip_api.services import historical_identity_source_custody as custody
from tip_api.services import historical_identity_source_apply_plan as apply_plan


SESSION = date(2026, 9, 3)
FETCHED_AT = datetime(2026, 9, 4, 1, tzinfo=UTC)
MATERIALIZED_AT = datetime(2026, 9, 4, 2, tzinfo=UTC)


def _profile_map(
    package_path: Path,
    *,
    package_manifest_sha256: str = "1" * 64,
) -> HistoricalIdentityRebuildProfileMapV1:
    binding_values = {
        "session_date": SESSION.isoformat(),
        "rebuild_profile": CURRENT_IDENTITY_REBUILD_PROFILE,
        "source_locator_sha256": hashlib.sha256(
            str(package_path.resolve()).encode("utf-8")
        ).hexdigest(),
        "package_manifest_sha256": package_manifest_sha256,
        "package_content_sha256": "2" * 64,
        "package_fetched_at": "2026-09-04T01:00:00Z",
        "canonical_snapshot_fingerprint": "3" * 64,
        "canonical_instrument_fingerprint": "4" * 64,
        "canonical_identity_fingerprint": "5" * 64,
        "canonical_resolver_fingerprint": "6" * 64,
    }
    binding = HistoricalIdentityRebuildProfileBindingV1.model_validate(
        {
            **binding_values,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                binding_values
            ),
        }
    )
    map_values = {
        "contract_version": "historical-identity-rebuild-profile-map/1.0",
        "generated_at": "2026-09-04T01:30:00Z",
        "current_census_contract_version": "1.1",
        "current_census_report_sha256": "7" * 64,
        "legacy_census_contract_version": "1.1",
        "legacy_census_report_sha256": "8" * 64,
        "canonical_session_count": 1,
        "bound_session_count": 1,
        "missing_session_dates": (),
        "profile_counts": (
            (CURRENT_IDENTITY_REBUILD_PROFILE, 1),
            (PRE_ETV_IDENTITY_REBUILD_PROFILE, 0),
        ),
        "canonical_session_index_fingerprint": "9" * 64,
        "discovered_package_inventory_fingerprint": (
            historical_identity_profile_fingerprint(
                [
                    {
                        "session_date": SESSION.isoformat(),
                        "package_manifest_sha256": package_manifest_sha256,
                        "package_content_sha256": "2" * 64,
                        "source_locator_sha256": binding.source_locator_sha256,
                    }
                ]
            )
        ),
        "bindings": (binding,),
        "external_request_count": 0,
        "canonical_data_write_count": 0,
    }
    return HistoricalIdentityRebuildProfileMapV1.model_validate(
        {
            **map_values,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                {
                    **map_values,
                    "bindings": [binding.model_dump(mode="json")],
                    "profile_counts": [
                        list(item) for item in map_values["profile_counts"]
                    ],
                    "missing_session_dates": [],
                }
            ),
        }
    )


def _equivalence(*, package_manifest_sha256: str = "1" * 64) -> SimpleNamespace:
    results = [
        {
            "active": True,
            "cik": "0001",
            "composite_figi": "BBG0001",
            "currency_name": "usd",
            "last_updated_utc": "2026-09-03T12:00:00Z",
            "locale": "us",
            "market": "stocks",
            "name": "Alpha Holdings",
            "primary_exchange": "XNYS",
            "share_class_figi": "BBG0011",
            "ticker": "AAA",
            "type": "CS",
        },
        {
            "active": True,
            "currency_name": "usd",
            "last_updated_utc": "2026-09-03T12:00:00Z",
            "locale": "us",
            "market": "stocks",
            "name": "Beta ADR",
            "primary_exchange": "XNAS",
            "share_class_figi": "BBG0022",
            "ticker": "BBB",
            "type": "ADRC",
        },
    ]
    page = {
        "count": 2,
        "request_id": "not-retained",
        "results": results,
        "status": "OK",
    }
    artifact = FetchArtifactV1(
        sequence=1,
        file_name="response-01.json",
        canonical_response_sha256="b" * 64,
        response_bytes=100,
    )
    manifest = FetchPackageManifestV1(
        package_type="identity_reference",
        session_date=SESSION,
        endpoint_class="/v3/reference/tickers",
        adjusted=None,
        request_count=1,
        pagination_complete=True,
        fetched_at=FETCHED_AT,
        artifacts=(artifact,),
        package_content_sha256="2" * 64,
    )
    return SimpleNamespace(
        exact_match=True,
        package=ValidatedIdentityReferencePackage(
            manifest=manifest,
            pages=(page,),
            package_manifest_sha256=package_manifest_sha256,
        ),
        identity=SimpleNamespace(
            snapshot_content_sha256="3" * 64,
            instrument_content_sha256="4" * 64,
            identity_content_sha256="5" * 64,
            resolver_content_sha256="6" * 64,
        ),
    )


def _build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    output_name: str = "candidate",
):
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    package_path = tmp_path / "package"
    package_path.mkdir()
    output_root = tmp_path / output_name
    output_root.mkdir(mode=0o700)
    output_root.chmod(0o700)
    profile_map = _profile_map(package_path)
    monkeypatch.setattr(custody, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_package_equivalence",
        lambda **_: _equivalence(),
    )
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_source_custody_equivalence",
        lambda **_: SimpleNamespace(exact_match=True),
    )
    result = custody.build_historical_identity_source_custody_candidate(
        data_root=data_root,
        package_path=package_path,
        output_root=output_root,
        profile_map=profile_map,
        session_date=SESSION,
        materialized_at=MATERIALIZED_AT,
    )
    return result, output_root, profile_map, package_path, data_root


def test_normalized_custody_preserves_complete_result_facts_without_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, root, profile_map, package_path, data_root = _build(
        tmp_path,
        monkeypatch,
    )

    reread = custody.read_historical_identity_source_custody_candidate(
        root=root,
        provider="massive_stocks_basic",
        session_date=SESSION,
    )
    assert result.status == "published"
    assert reread.manifest.source_field_names == SOURCE_FIELD_NAMES
    assert reread.manifest.record_count == 2
    assert reread.manifest.raw_response_retained is False
    assert reread.manifest.response_url_retained is False
    assert reread.manifest.request_identifier_retained is False
    assert reread.manifest.external_request_count == 0
    assert reread.manifest.canonical_data_write_count == 0
    assert reread.records[0].source_payload()["ticker"] == "AAA"
    assert set(reread.records[0].source_payload()) == set(SOURCE_FIELD_NAMES)
    assert "request_id" not in type(reread.records[0]).model_fields
    assert (reread.partition_path / "manifest.json").stat().st_mode & 0o777 == 0o400
    assert (
        reread.partition_path / "part-00000.parquet"
    ).stat().st_mode & 0o777 == 0o400

    repeated = custody.build_historical_identity_source_custody_candidate(
        data_root=data_root,
        package_path=package_path,
        output_root=root,
        profile_map=profile_map,
        session_date=SESSION,
        materialized_at=datetime(2026, 9, 4, 3, tzinfo=UTC),
    )
    assert repeated.status == "already_present"
    assert repeated.manifest_sha256 == result.manifest_sha256


def test_normalized_custody_is_physically_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _, _, _, _ = _build(tmp_path, monkeypatch, output_name="first")
    second_root = tmp_path / "second"
    second_root.mkdir(mode=0o700)
    second_root.chmod(0o700)
    package_path = tmp_path / "package"
    second = custody.build_historical_identity_source_custody_candidate(
        data_root=tmp_path / "canonical",
        package_path=package_path,
        output_root=second_root,
        profile_map=_profile_map(package_path),
        session_date=SESSION,
        materialized_at=MATERIALIZED_AT,
    )

    assert second.manifest.content_fingerprint == first.manifest.content_fingerprint
    assert second.manifest.parquet_sha256 == first.manifest.parquet_sha256
    assert second.manifest.logical_fingerprint == first.manifest.logical_fingerprint
    assert second.manifest_sha256 == first.manifest_sha256


def test_normalized_custody_rejects_unreviewed_result_field() -> None:
    equivalence = _equivalence()
    page = dict(equivalence.package.pages[0])
    result = dict(page["results"][0])
    result["unreviewed"] = "value"
    page["results"] = [result, page["results"][1]]

    with pytest.raises(
        custody.HistoricalIdentitySourceCustodyError,
        match="unreviewed field",
    ):
        custody._normalize_package_pages(
            pages=(page,),
            package_artifacts=equivalence.package.manifest.artifacts,
            provider="massive_stocks_basic",
            session_date=SESSION,
            observed_at=FETCHED_AT,
        )


def test_normalized_custody_reader_rejects_relaxed_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, root, _, _, _ = _build(tmp_path, monkeypatch)
    (result.partition_path / "manifest.json").chmod(0o600)

    with pytest.raises(
        custody.HistoricalIdentitySourceCustodyError,
        match="owner-read-only",
    ):
        custody.read_historical_identity_source_custody_candidate(
            root=root,
            provider="massive_stocks_basic",
            session_date=SESSION,
        )


def test_normalized_custody_reader_rejects_symlinked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, root, _, _, _ = _build(tmp_path, monkeypatch)
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(root.parent, target_is_directory=True)

    with pytest.raises(
        custody.HistoricalIdentitySourceCustodyError,
        match="symlink",
    ):
        custody.read_historical_identity_source_custody_candidate(
            root=linked_parent / root.name,
            provider="massive_stocks_basic",
            session_date=SESSION,
        )


def test_normalized_custody_reader_rejects_symlinked_internal_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, root, _, _, _ = _build(tmp_path, monkeypatch)
    market_data = root / "market-data"
    real_market_data = root / "real-market-data"
    market_data.rename(real_market_data)
    market_data.symlink_to(real_market_data, target_is_directory=True)

    with pytest.raises(
        custody.HistoricalIdentitySourceCustodyError,
        match="symlink",
    ):
        custody.read_historical_identity_source_custody_candidate(
            root=root,
            provider="massive_stocks_basic",
            session_date=SESSION,
        )


def test_bounded_batch_discovers_exact_profile_inventory_and_resumes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    source_root = tmp_path / "source"
    package_path = source_root / "session" / "identity-package"
    package_path.mkdir(parents=True)
    manifest = _equivalence().package.manifest
    manifest_path = package_path / "package.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json")),
        encoding="utf-8",
    )
    package_manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    profile_map = _profile_map(
        package_path,
        package_manifest_sha256=package_manifest_sha256,
    )
    output_root = tmp_path / "candidate"
    output_root.mkdir(mode=0o700)
    output_root.chmod(0o700)
    monkeypatch.setattr(custody, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_package_equivalence",
        lambda **_: _equivalence(
            package_manifest_sha256=package_manifest_sha256
        ),
    )
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_source_custody_equivalence",
        lambda **_: SimpleNamespace(exact_match=True),
    )

    first = custody.run_historical_identity_source_custody_batch(
        data_root=data_root,
        package_roots=(source_root,),
        output_root=output_root,
        profile_map=profile_map,
        materialized_at=MATERIALIZED_AT,
        maximum_sessions=1,
        workers=1,
    )
    resumed = custody.run_historical_identity_source_custody_batch(
        data_root=data_root,
        package_roots=(source_root,),
        output_root=output_root,
        profile_map=profile_map,
        materialized_at=MATERIALIZED_AT,
        maximum_sessions=1,
        workers=1,
    )

    assert first.completed_before_count == 0
    assert first.selected_session_count == 1
    assert first.completed_after_count == 1
    assert first.remaining_session_count == 0
    assert first.status == "complete"
    assert resumed.completed_before_count == 1
    assert resumed.selected_session_count == 0
    assert resumed.completed_after_count == 1
    assert resumed.status == "complete"


def test_apply_plan_is_complete_inventory_bound_and_no_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, root, profile_map, _, data_root = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    plan_path = tmp_path / "historical-source-apply-plan.json"

    evidence = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=plan_path,
        inventory_reader=lambda _: "a" * 64,
    )

    assert evidence.plan.status == "ready_for_separate_review"
    assert evidence.plan.session_count == 1
    assert evidence.plan.record_count == 2
    assert evidence.plan.inventory_change_file_count == 2
    assert evidence.plan.expected_current_state_fingerprint == "a" * 64
    assert evidence.plan.artifacts[0].sha256 == result.manifest_sha256
    assert evidence.plan.artifacts[1].sha256 == result.manifest.parquet_sha256
    assert evidence.plan.external_request_count == 0
    assert evidence.plan.canonical_data_write_count == 0
    assert evidence.plan.apply_authorized is False
    assert plan_path.stat().st_mode & 0o777 == 0o600

    reread = apply_plan.read_historical_identity_source_apply_plan(
        plan_path=plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        inventory_reader=lambda _: "a" * 64,
    )
    assert reread == evidence

    parallel = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=tmp_path / "parallel-historical-source-apply-plan.json",
        workers=2,
        inventory_reader=lambda _: "a" * 64,
    )
    assert parallel.plan == evidence.plan
    assert parallel.plan_sha256 == evidence.plan_sha256


def test_apply_plan_rejects_existing_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, root, profile_map, _, data_root = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    target = (
        data_root
        / "market-data"
        / "provider-identity-reference-observation"
        / "schema_version=1"
        / "provider=massive_stocks_basic"
        / f"as_of_date={SESSION.isoformat()}"
    )
    target.mkdir(parents=True)

    with pytest.raises(
        apply_plan.HistoricalIdentitySourceApplyPlanError,
        match="no longer absent",
    ):
        apply_plan.build_historical_identity_source_apply_plan(
            data_root=data_root,
            candidate_root=root,
            profile_map=profile_map,
            created_at=MATERIALIZED_AT,
            plan_path=tmp_path / "blocked-plan.json",
            inventory_reader=lambda _: "a" * 64,
        )


def test_apply_plan_reread_rejects_candidate_permission_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, root, profile_map, _, data_root = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    plan_path = tmp_path / "historical-source-apply-plan.json"
    evidence = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=plan_path,
        inventory_reader=lambda _: "a" * 64,
    )
    (result.partition_path / "part-00000.parquet").chmod(0o600)

    with pytest.raises(
        apply_plan.HistoricalIdentitySourceApplyPlanError,
        match="not owner-read-only",
    ):
        apply_plan.read_historical_identity_source_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            inventory_reader=lambda _: "a" * 64,
        )
