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
from tip_api.services.historical_identity_source_apply_plan import (
    HistoricalIdentitySourceApplyPlanEvidence,
)
from tip_api.services import historical_identity_source_custody as custody
from tip_api.services import historical_identity_source_apply_plan as apply_plan
from tip_api.services import historical_identity_source_apply as source_apply
from tip_api.services import historical_identity_source_apply_cli as source_apply_cli


SESSION = date(2026, 9, 3)
UNBOUND_SESSION = date(2026, 9, 2)
FETCHED_AT = datetime(2026, 9, 4, 1, tzinfo=UTC)
MATERIALIZED_AT = datetime(2026, 9, 4, 2, tzinfo=UTC)


def _profile_map(
    package_path: Path,
    *,
    package_manifest_sha256: str = "1" * 64,
    session_dates: tuple[date, ...] = (SESSION,),
) -> HistoricalIdentityRebuildProfileMapV1:
    source_locator_sha256 = hashlib.sha256(
        str(package_path.resolve()).encode("utf-8")
    ).hexdigest()
    bindings = []
    for session_date in session_dates:
        binding_values = {
            "session_date": session_date.isoformat(),
            "rebuild_profile": CURRENT_IDENTITY_REBUILD_PROFILE,
            "source_locator_sha256": source_locator_sha256,
            "package_manifest_sha256": package_manifest_sha256,
            "package_content_sha256": "2" * 64,
            "package_fetched_at": "2026-09-04T01:00:00Z",
            "canonical_snapshot_fingerprint": "3" * 64,
            "canonical_instrument_fingerprint": "4" * 64,
            "canonical_identity_fingerprint": "5" * 64,
            "canonical_resolver_fingerprint": "6" * 64,
        }
        bindings.append(
            HistoricalIdentityRebuildProfileBindingV1.model_validate(
                {
                    **binding_values,
                    "logical_fingerprint": (
                        historical_identity_profile_fingerprint(binding_values)
                    ),
                }
            )
        )
    map_values = {
        "contract_version": "historical-identity-rebuild-profile-map/1.0",
        "generated_at": "2026-09-04T01:30:00Z",
        "current_census_contract_version": "1.1",
        "current_census_report_sha256": "7" * 64,
        "legacy_census_contract_version": "1.1",
        "legacy_census_report_sha256": "8" * 64,
        "canonical_session_count": len(session_dates),
        "bound_session_count": len(session_dates),
        "missing_session_dates": (),
        "profile_counts": (
            (CURRENT_IDENTITY_REBUILD_PROFILE, len(session_dates)),
            (PRE_ETV_IDENTITY_REBUILD_PROFILE, 0),
        ),
        "canonical_session_index_fingerprint": (
            historical_identity_profile_fingerprint(
                [item.isoformat() for item in session_dates]
            )
        ),
        "discovered_package_inventory_fingerprint": (
            historical_identity_profile_fingerprint(
                [
                    {
                        "session_date": session_date.isoformat(),
                        "package_manifest_sha256": package_manifest_sha256,
                        "package_content_sha256": "2" * 64,
                        "source_locator_sha256": source_locator_sha256,
                    }
                    for session_date in session_dates
                ]
            )
        ),
        "bindings": tuple(bindings),
        "external_request_count": 0,
        "canonical_data_write_count": 0,
    }
    return HistoricalIdentityRebuildProfileMapV1.model_validate(
        {
            **map_values,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                {
                    **map_values,
                    "bindings": [
                        binding.model_dump(mode="json") for binding in bindings
                    ],
                    "profile_counts": [
                        list(item) for item in map_values["profile_counts"]
                    ],
                    "missing_session_dates": [],
                }
            ),
        }
    )


def _equivalence(
    *,
    package_manifest_sha256: str = "1" * 64,
    session_date: date = SESSION,
) -> SimpleNamespace:
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
        session_date=session_date,
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
        match="mode differs",
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


def test_package_discovery_keeps_declared_mismatch_unbound(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    bound_package = source_root / "bound" / "identity-package"
    unbound_package = source_root / "unbound" / "identity-package"
    bound_package.mkdir(parents=True)
    unbound_package.mkdir(parents=True)
    bound_manifest = _equivalence().package.manifest
    unbound_manifest = _equivalence(session_date=UNBOUND_SESSION).package.manifest
    bound_manifest_path = bound_package / "package.json"
    unbound_manifest_path = unbound_package / "package.json"
    bound_manifest_path.write_text(
        json.dumps(bound_manifest.model_dump(mode="json")),
        encoding="utf-8",
    )
    unbound_manifest_path.write_text(
        json.dumps(unbound_manifest.model_dump(mode="json")),
        encoding="utf-8",
    )
    bound_manifest_sha = hashlib.sha256(bound_manifest_path.read_bytes()).hexdigest()
    unbound_manifest_sha = hashlib.sha256(
        unbound_manifest_path.read_bytes()
    ).hexdigest()
    profile_map = _profile_map(
        bound_package,
        package_manifest_sha256=bound_manifest_sha,
    )
    map_values = profile_map.model_dump(mode="json", exclude={"logical_fingerprint"})
    map_values.update(
        {
            "contract_version": "historical-identity-rebuild-profile-map/1.1",
            "canonical_session_count": 2,
            "unbound_identity_mismatch_session_dates": [
                UNBOUND_SESSION.isoformat()
            ],
            "discovered_package_inventory_fingerprint": (
                historical_identity_profile_fingerprint(
                    sorted(
                        (
                            {
                                "session_date": SESSION.isoformat(),
                                "package_manifest_sha256": bound_manifest_sha,
                                "package_content_sha256": "2" * 64,
                                "source_locator_sha256": hashlib.sha256(
                                    str(bound_package.resolve()).encode("utf-8")
                                ).hexdigest(),
                            },
                            {
                                "session_date": UNBOUND_SESSION.isoformat(),
                                "package_manifest_sha256": unbound_manifest_sha,
                                "package_content_sha256": "2" * 64,
                                "source_locator_sha256": hashlib.sha256(
                                    str(unbound_package.resolve()).encode("utf-8")
                                ).hexdigest(),
                            },
                        ),
                        key=lambda item: (
                            item["session_date"],
                            item["package_manifest_sha256"],
                            item["package_content_sha256"],
                            item["source_locator_sha256"],
                        ),
                    )
                )
            ),
        }
    )
    profile_map = HistoricalIdentityRebuildProfileMapV1.model_validate(
        {
            **map_values,
            "logical_fingerprint": historical_identity_profile_fingerprint(
                map_values
            ),
        }
    )
    output_root = tmp_path / "candidate"
    output_root.mkdir(mode=0o700)

    discovered = custody._discover_profile_bound_packages(
        package_roots=(source_root,),
        output_root=output_root,
        profile_map=profile_map,
    )

    assert discovered == {SESSION: bound_package.resolve()}
    with pytest.raises(
        custody.HistoricalIdentitySourceCustodyError,
        match="inventory differs",
    ):
        custody._discover_profile_bound_packages(
            package_roots=(bound_package,),
            output_root=output_root,
            profile_map=profile_map,
        )


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


def test_apply_plan_can_bind_an_explicit_append_only_candidate_subset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_dates = (date(2026, 9, 2), SESSION)
    selected_session = session_dates[1]
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    package_path = tmp_path / "package"
    package_path.mkdir()
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir(mode=0o700)
    candidate_root.chmod(0o700)
    profile_map = _profile_map(package_path, session_dates=session_dates)
    monkeypatch.setattr(custody, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_package_equivalence",
        lambda **kwargs: _equivalence(session_date=kwargs["session_date"]),
    )
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_source_custody_equivalence",
        lambda **_: SimpleNamespace(exact_match=True),
    )
    custody.build_historical_identity_source_custody_candidate(
        data_root=data_root,
        package_path=package_path,
        output_root=candidate_root,
        profile_map=profile_map,
        session_date=selected_session,
        materialized_at=MATERIALIZED_AT,
    )
    existing_unselected_target = (
        data_root
        / "market-data"
        / "provider-identity-reference-observation"
        / "schema_version=1"
        / "provider=massive_stocks_basic"
        / f"as_of_date={session_dates[0].isoformat()}"
    )
    existing_unselected_target.mkdir(parents=True)

    evidence = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=tmp_path / "append-only-plan.json",
        sessions=(selected_session,),
        inventory_reader=lambda _: "a" * 64,
    )

    assert evidence.plan.session_count == 1
    assert evidence.plan.sessions[0].session_date == selected_session
    assert evidence.plan.target_absent_partition_count == 1
    assert all(
        artifact.session_date == selected_session
        for artifact in evidence.plan.artifacts
    )


@pytest.mark.parametrize(
    "sessions",
    (
        (),
        (SESSION, date(2026, 9, 2)),
        (SESSION, SESSION),
        (date(2026, 9, 1),),
    ),
)
def test_apply_plan_rejects_invalid_explicit_session_selection(
    sessions: tuple[date, ...],
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "package"
    package_path.mkdir()
    profile_map = _profile_map(
        package_path,
        session_dates=(date(2026, 9, 2), SESSION),
    )

    with pytest.raises(apply_plan.HistoricalIdentitySourceApplyPlanError):
        apply_plan._selected_bindings(profile_map, sessions)


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


def _apply_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    candidate, root, profile_map, _, data_root = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(source_apply, "APPROVED_DATA_ROOT", data_root.resolve())
    plan_path = tmp_path / "historical-source-apply-plan.json"
    evidence = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=plan_path,
    )
    return candidate, data_root, plan_path, evidence


def _two_session_apply_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    session_dates = (date(2026, 9, 2), SESSION)
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    package_path = tmp_path / "package"
    package_path.mkdir()
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir(mode=0o700)
    candidate_root.chmod(0o700)
    profile_map = _profile_map(
        package_path,
        session_dates=session_dates,
    )
    monkeypatch.setattr(custody, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(apply_plan, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(source_apply, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_package_equivalence",
        lambda **kwargs: _equivalence(session_date=kwargs["session_date"]),
    )
    monkeypatch.setattr(
        custody,
        "inspect_historical_identity_source_custody_equivalence",
        lambda **_: SimpleNamespace(exact_match=True),
    )
    for session_date in session_dates:
        custody.build_historical_identity_source_custody_candidate(
            data_root=data_root,
            package_path=package_path,
            output_root=candidate_root,
            profile_map=profile_map,
            session_date=session_date,
            materialized_at=MATERIALIZED_AT,
        )
    plan_path = tmp_path / "two-session-historical-source-apply-plan.json"
    evidence = apply_plan.build_historical_identity_source_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        profile_map=profile_map,
        created_at=MATERIALIZED_AT,
        plan_path=plan_path,
    )
    return data_root, plan_path, evidence


def _apply(
    *,
    data_root: Path,
    plan_path: Path,
    evidence: HistoricalIdentitySourceApplyPlanEvidence,
    verify_then_complete: bool = False,
    formal_read_workers: int = 1,
):
    return source_apply.apply_approved_historical_identity_source_plan(
        plan_path=plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        expected_current_state_fingerprint=(
            evidence.plan.expected_current_state_fingerprint
        ),
        data_root=data_root,
        verify_then_complete=verify_then_complete,
        formal_read_workers=formal_read_workers,
    )


def _inject_post_publish_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    publish = source_apply._publish_partition

    def interrupted_publish(**kwargs) -> None:
        publish(**kwargs)
        raise source_apply.HistoricalIdentitySourceApplyError(
            "injected failure after completed historical source partition"
        )

    monkeypatch.setattr(source_apply, "_publish_partition", interrupted_publish)


def test_approved_apply_publishes_and_formally_rereads_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, data_root, plan_path, evidence = _apply_fixture(
        tmp_path,
        monkeypatch,
    )

    result = _apply(
        data_root=data_root,
        plan_path=plan_path,
        evidence=evidence,
    )

    target = Path(evidence.plan.artifacts[0].target_path).parent
    assert result.status == "applied"
    assert result.published_partition_count == 1
    assert result.reused_partition_count == 0
    assert result.published_file_count == 2
    assert result.published_bytes == evidence.plan.inventory_change_bytes
    assert result.formal_reread_session_count == 1
    assert result.overwritten_partition_count == 0
    assert result.deleted_partition_count == 0
    assert target.stat().st_mode & 0o777 == 0o755
    assert (target / "manifest.json").stat().st_mode & 0o777 == 0o644
    assert (target / "part-00000.parquet").stat().st_mode & 0o777 == 0o644
    assert candidate.partition_path.exists()

    canonical = custody.read_historical_identity_source_custody(
        data_root=data_root,
        provider="massive_stocks_basic",
        session_date=SESSION,
    )
    assert canonical.manifest == candidate.manifest


def test_approved_apply_cli_requires_and_reports_exact_execution_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)

    exit_code = source_apply_cli.main(
        [
            "--plan-path",
            str(plan_path),
            "--approved-plan-sha256",
            evidence.plan_sha256,
            "--expected-plan-logical-fingerprint",
            evidence.plan.logical_fingerprint,
            "--expected-current-state-fingerprint",
            evidence.plan.expected_current_state_fingerprint,
            "--data-root",
            str(data_root),
            "--formal-read-workers",
            "1",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["status"] == "applied"
    assert report["plan_sha256"] == evidence.plan_sha256
    assert report["session_count"] == 1
    assert report["published_partition_count"] == 1
    assert report["external_request_count"] == 0


def test_approved_apply_rejects_inventory_drift_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)
    unrelated = data_root / "unrelated.txt"
    unrelated.write_text("changed", encoding="utf-8")
    target = Path(evidence.plan.artifacts[0].target_path).parent

    with pytest.raises(
        source_apply.HistoricalIdentitySourceApplyError,
        match="failed formal reread",
    ):
        _apply(
            data_root=data_root,
            plan_path=plan_path,
            evidence=evidence,
        )
    assert not target.exists()


def test_interrupted_apply_reuses_exact_completed_partition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)

    with monkeypatch.context() as fault:
        _inject_post_publish_failure(fault)
        with pytest.raises(
            source_apply.HistoricalIdentitySourceApplyError,
            match="injected failure",
        ):
            _apply(
                data_root=data_root,
                plan_path=plan_path,
                evidence=evidence,
            )

    recovered = _apply(
        data_root=data_root,
        plan_path=plan_path,
        evidence=evidence,
        verify_then_complete=True,
        formal_read_workers=2,
    )
    assert recovered.status == "verified_then_completed"
    assert recovered.published_partition_count == 0
    assert recovered.reused_partition_count == 1
    assert recovered.formal_reread_session_count == 1


def test_interrupted_apply_reuses_completed_and_publishes_absent_partition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _two_session_apply_fixture(
        tmp_path,
        monkeypatch,
    )

    with monkeypatch.context() as fault:
        _inject_post_publish_failure(fault)
        with pytest.raises(
            source_apply.HistoricalIdentitySourceApplyError,
            match="injected failure",
        ):
            _apply(
                data_root=data_root,
                plan_path=plan_path,
                evidence=evidence,
            )

    recovered = _apply(
        data_root=data_root,
        plan_path=plan_path,
        evidence=evidence,
        verify_then_complete=True,
    )
    assert recovered.status == "verified_then_completed"
    assert recovered.session_count == 2
    assert recovered.published_partition_count == 1
    assert recovered.reused_partition_count == 1
    assert recovered.published_file_count == 2
    assert recovered.formal_reread_session_count == 2


def test_ordinary_apply_never_treats_existing_target_as_replayable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)
    _apply(
        data_root=data_root,
        plan_path=plan_path,
        evidence=evidence,
    )

    with pytest.raises(
        source_apply.HistoricalIdentitySourceApplyError,
        match="failed formal reread",
    ):
        _apply(
            data_root=data_root,
            plan_path=plan_path,
            evidence=evidence,
        )


def test_recovery_blocks_partial_target_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)
    target = Path(evidence.plan.artifacts[0].target_path).parent
    target.mkdir(parents=True, mode=0o755)
    partial = target / "manifest.json"
    partial.write_text("partial", encoding="utf-8")
    partial.chmod(0o644)

    with pytest.raises(
        source_apply.HistoricalIdentitySourceApplyError,
        match="failed formal reread",
    ):
        _apply(
            data_root=data_root,
            plan_path=plan_path,
            evidence=evidence,
            verify_then_complete=True,
        )
    assert partial.read_text(encoding="utf-8") == "partial"


def test_recovery_blocks_staging_residue_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, data_root, plan_path, evidence = _apply_fixture(tmp_path, monkeypatch)
    target = Path(evidence.plan.artifacts[0].target_path).parent
    staging = target.parent / (
        f".{target.name}.staging.{evidence.plan.logical_fingerprint[:16]}"
    )
    staging.mkdir(parents=True, mode=0o755)

    with pytest.raises(
        source_apply.HistoricalIdentitySourceApplyError,
        match="staging path already exists",
    ):
        _apply(
            data_root=data_root,
            plan_path=plan_path,
            evidence=evidence,
            verify_then_complete=True,
        )
    assert staging.is_dir()
