from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import current_context_report as report


def test_freshness_state_separates_sealed_and_current_operational_views() -> None:
    state = report._freshness_state(
        latest_canonical_session=date(2026, 9, 4),
        snapshot_manifest=SimpleNamespace(
            current_session_date="2026-09-03",
            actual_latest_completed_session="2026-09-03",
            expected_latest_completed_session="2026-09-03",
            session_lag=0,
            freshness_status="fresh",
            calendar_id="XNYS",
            freshness_checked_at="2026-09-03T22:00:00Z",
            release_id="2026-09-03T220000Z-abcdef0",
        ),
        checked_at=datetime(2026, 9, 5, 22, tzinfo=UTC),
    )

    assert state["canonical_operational"] == {
        "actual_latest_completed_session": "2026-09-04",
        "expected_latest_completed_session": "2026-09-04",
        "session_lag": 0,
        "freshness_status": "fresh",
        "calendar_id": "XNYS",
        "checked_at": "2026-09-05T22:00:00Z",
    }
    assert state["active_snapshot_operational"] == {
        "actual_latest_completed_session": "2026-09-03",
        "expected_latest_completed_session": "2026-09-04",
        "session_lag": 1,
        "freshness_status": "stale",
        "calendar_id": "XNYS",
        "checked_at": "2026-09-05T22:00:00Z",
        "release_id": "2026-09-03T220000Z-abcdef0",
    }
    assert state["snapshot_publication_sealed"] == {
        "actual_latest_completed_session": "2026-09-03",
        "expected_latest_completed_session": "2026-09-03",
        "session_lag": 0,
        "freshness_status": "fresh",
        "calendar_id": "XNYS",
        "checked_at": "2026-09-03T22:00:00Z",
        "release_id": "2026-09-03T220000Z-abcdef0",
    }


def test_freshness_state_rejects_malformed_snapshot_session() -> None:
    with pytest.raises(report.CurrentContextReportError, match="malformed"):
        report._freshness_state(
            latest_canonical_session=date(2026, 9, 4),
            snapshot_manifest=SimpleNamespace(current_session_date="latest"),
            checked_at=datetime(2026, 9, 5, 22, tzinfo=UTC),
        )


def test_identity_state_accepts_exact_completed_same_day_manifest(tmp_path: Path) -> None:
    root = tmp_path / "data"
    target = (
        root
        / "market-data/snapshots/instrument-master/as_of_date=2026-08-24"
        / "manifest.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "completion_status": "completed",
                "as_of_date": "2026-08-24",
                "instrument_count": 9968,
                "identity_count": 13131,
                "resolver_count": 9968,
                "snapshot_content_sha256": "a" * 64,
            }
        )
    )

    state = report._identity_state(root, date(2026, 8, 24))

    assert state["instrument_count"] == 9968
    assert state["provider_identity_count"] == 13131
    assert state["logical_fingerprint"] == "a" * 64


def test_identity_state_rejects_wrong_date_or_incomplete_manifest(tmp_path: Path) -> None:
    root = tmp_path / "data"
    target = (
        root
        / "market-data/snapshots/instrument-master/as_of_date=2026-08-24"
        / "manifest.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"completion_status": "partial", "as_of_date": "2026-08-23"}))

    with pytest.raises(report.CurrentContextReportError, match="identity differs"):
        report._identity_state(root, date(2026, 8, 24))


def test_latest_identity_state_is_independent_from_latest_eod(tmp_path: Path) -> None:
    root = tmp_path / "data"
    for day, count in ((date(2026, 8, 26), 9974), (date(2026, 8, 27), 9982)):
        target = (
            root
            / "market-data/snapshots/instrument-master"
            / f"as_of_date={day.isoformat()}"
            / "manifest.json"
        )
        target.parent.mkdir(parents=True)
        target.write_text(
            json.dumps(
                {
                    "completion_status": "completed",
                    "as_of_date": day.isoformat(),
                    "instrument_count": count,
                    "identity_count": count + 3000,
                    "resolver_count": count,
                    "snapshot_content_sha256": "a" * 64,
                }
            )
        )

    state = report._latest_identity_state(root)
    alignment = report._identity_eod_alignment(
        latest_identity_date=date.fromisoformat(state["as_of_date"]),
        latest_eod_session=date(2026, 8, 26),
        eod_bound_identity_date=date(2026, 8, 26),
    )

    assert state["as_of_date"] == "2026-08-27"
    assert state["instrument_count"] == 9982
    assert alignment == {
        "status": "identity_ahead_of_eod",
        "latest_identity_date": "2026-08-27",
        "latest_eod_session": "2026-08-26",
        "eod_bound_identity_date": "2026-08-26",
    }


def test_identity_eod_alignment_rejects_inconsistent_eod_binding() -> None:
    with pytest.raises(report.CurrentContextReportError, match="binding"):
        report._identity_eod_alignment(
            latest_identity_date=date(2026, 8, 27),
            latest_eod_session=date(2026, 8, 26),
            eod_bound_identity_date=date(2026, 8, 25),
        )


def test_inventory_and_residue_report_symlink_without_following_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "data"
    root.mkdir()
    (root / "one.bin").write_bytes(b"123")
    (root / ".publication.staging").mkdir()
    (root / "link").symlink_to(root / "one.bin")
    monkeypatch.setattr(report, "inventory_fingerprint", lambda value: "b" * 64)

    inventory = report._inventory_state(root, include_fingerprint=True)
    residue = report._publication_residue(root)

    assert inventory == {
        "file_count": 1,
        "total_bytes": 3,
        "fingerprint": "b" * 64,
        "fingerprint_skipped": False,
        "symlink_count": 1,
        "symlink_paths": ("link",),
    }
    assert residue == {"count": 1, "paths": (".publication.staging",)}


def test_bundle_checksums_are_bounded_and_exact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    artifact = bundle / "artifact.json"
    artifact.write_text("{}\n")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (bundle / "checksums.sha256").write_text(f"{digest}  ./artifact.json\n")

    assert report._validate_bundle_checksums(bundle) == 1

    artifact.write_text("changed\n")
    with pytest.raises(report.CurrentContextReportError, match="validation failed"):
        report._validate_bundle_checksums(bundle)


def test_main_is_network_guarded_and_outputs_only_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed = {}

    def fake_build_report(
        *,
        full_source_validation: bool,
        full_history_validation: bool,
        include_inventory: bool,
    ):
        observed["full"] = full_source_validation
        observed["history"] = full_history_validation
        observed["inventory"] = include_inventory
        return {"status": "ok"}

    monkeypatch.setattr(report, "build_report", fake_build_report)

    assert report.main(["--skip-inventory"]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok"}
    assert observed == {"full": False, "history": False, "inventory": False}


def test_main_exposes_explicit_full_history_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed = {}

    def fake_build_report(**kwargs):
        observed.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(report, "build_report", fake_build_report)

    assert report.main(["--full-history-validation", "--skip-inventory"]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok"}
    assert observed == {
        "full_source_validation": False,
        "full_history_validation": True,
        "include_inventory": False,
    }


def test_completed_session_dates_separates_index_from_full_history() -> None:
    first = date(2026, 8, 27)
    second = date(2026, 8, 28)

    class Repository:
        def __init__(self) -> None:
            self.index_calls = 0
            self.full_calls = 0

        def list_session_index(self):
            self.index_calls += 1
            return (first, second)

        def list_sessions(self):
            self.full_calls += 1
            return (
                SimpleNamespace(session_date=first),
                SimpleNamespace(session_date=second),
            )

    repository = Repository()
    assert report._completed_session_dates(
        repository, full_history_validation=False
    ) == (first, second)
    assert (repository.index_calls, repository.full_calls) == (1, 0)

    assert report._completed_session_dates(
        repository, full_history_validation=True
    ) == (first, second)
    assert (repository.index_calls, repository.full_calls) == (1, 1)


def test_completed_session_dates_rejects_unordered_index() -> None:
    class Repository:
        def list_session_index(self):
            return (date(2026, 8, 28), date(2026, 8, 27))

    with pytest.raises(report.CurrentContextReportError, match="unique and ordered"):
        report._completed_session_dates(Repository(), full_history_validation=False)


def test_historical_research_readiness_separates_acquired_from_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    sessions = (date(2026, 8, 27), date(2026, 8, 28))
    for session in sessions:
        target = (
            root
            / "market-data/snapshots/instrument-master"
            / f"as_of_date={session.isoformat()}"
            / "manifest.json"
        )
        target.parent.mkdir(parents=True)
        target.write_text(
            json.dumps(
                {
                    "completion_status": "completed",
                    "as_of_date": session.isoformat(),
                    "instrument_count": 10,
                    "identity_count": 12,
                    "resolver_count": 10,
                    "snapshot_content_sha256": "a" * 64,
                }
            )
        )

    state = report._historical_research_readiness(
        root,
        session_dates=sessions,
        history_validation_scope="completion_index_plus_latest_partition",
    )
    families = {item["family"]: item for item in state["families"]}

    assert state["status"] == "data_blocked"
    assert state["canonical_price_depth_satisfied"] is False
    assert families["eod_price_bar"]["partition_count"] == 2
    assert families["point_in_time_identity"]["covered_session_count"] == 2
    assert (
        families["point_in_time_identity_source_observation"]["custody_state"]
        == "absent"
    )
    assert families["universe_membership"]["custody_state"] == "absent"
    assert "daily_point_in_time_membership_absent" in state["blocker_codes"]
    assert (
        "corporate_action_source_observation_absent" in state["blocker_codes"]
    )
    assert (
        "point_in_time_identity_source_observation_absent"
        in state["blocker_codes"]
    )
    assert state["ready_for_strategy_development_review"] is False
    assert state["performance_claims_authorized"] is False


def test_identity_source_observation_inventory_is_layered_and_gap_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "data"
    first = date(2026, 8, 27)
    second = date(2026, 8, 28)
    partition = (
        root
        / "market-data/provider-identity-reference-observation"
        / "schema_version=1/provider=massive_stocks_basic"
        / f"as_of_date={first.isoformat()}"
    )
    partition.mkdir(parents=True)
    partition.chmod(0o755)
    manifest_path = partition / "manifest.json"
    parquet_path = partition / "part-00000.parquet"
    manifest_path.write_text("{}", encoding="utf-8")
    parquet_path.write_bytes(b"parquet")
    manifest_path.chmod(0o644)
    parquet_path.chmod(0o644)
    monkeypatch.setattr(
        report,
        "parse_identity_source_custody_manifest",
        lambda _: SimpleNamespace(
            as_of_date=first,
            provider="massive_stocks_basic",
            dataset_name="provider-identity-reference-observation",
            parquet_file="part-00000.parquet",
            record_count=11,
            source_artifacts=(object(), object()),
        ),
    )

    state = report._identity_source_observation_inventory(
        root,
        session_dates=(first, second),
    )

    assert state == {
        "family": "point_in_time_identity_source_observation",
        "data_family_id": "point_in_time_identity",
        "record_layer": "source_observation",
        "custody_state": (
            "canonical_partitions_observed_not_coverage_validated"
        ),
        "partition_count": 1,
        "manifest_count": 1,
        "parquet_count": 1,
        "covered_session_count": 1,
        "record_count": 11,
        "source_artifact_count": 2,
        "first_session": "2026-08-27",
        "last_session": "2026-08-27",
        "missing_eod_session_dates": ("2026-08-28",),
        "source_only_session_dates": (),
        "validation_scope": "typed_partition_manifests_and_file_custody",
        "research_ready": False,
    }


def test_identity_source_observation_inventory_rejects_inexact_file_custody(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    session = date(2026, 8, 28)
    partition = (
        root
        / "market-data/provider-identity-reference-observation"
        / "schema_version=1/provider=massive_stocks_basic"
        / f"as_of_date={session.isoformat()}"
    )
    partition.mkdir(parents=True)
    partition.chmod(0o755)
    manifest_path = partition / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest_path.chmod(0o644)

    with pytest.raises(report.CurrentContextReportError, match="file set"):
        report._identity_source_observation_inventory(
            root,
            session_dates=(session,),
        )


def test_corporate_action_source_inventory_uses_canonical_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "data"
    relative_partition = (
        "market-data/provider-corporate-action-observation/"
        "schema_version=1/provider_id=massive_stocks_basic/event_year=2026"
    )
    physical = root / relative_partition
    physical.mkdir(parents=True)
    publication_partition = (
        root
        / "market-data/provider-corporate-action-observation-publications"
        / "schema_version=1/provider_id=massive_stocks_basic"
        / f"coverage_id={'a' * 64}"
    )
    publication_partition.mkdir(parents=True)
    marker = publication_partition / "manifest.json"
    marker.write_text("{}", encoding="utf-8")
    publication = SimpleNamespace(
        logical_fingerprint="a" * 64,
        start_date=date(2026, 8, 20),
        end_date=date(2026, 8, 22),
        source_record_count=2,
        resolved_record_count=1,
        quarantined_record_count=1,
        artifacts=(SimpleNamespace(partition_path=relative_partition),),
    )
    monkeypatch.setattr(
        report,
        "read_canonical_corporate_action_source_summary",
        lambda **_kwargs: SimpleNamespace(
            publication=publication,
            publication_path=marker,
        ),
    )

    state = report._canonical_corporate_action_source_inventory(root)

    assert state["custody_state"] == "canonical_bounded_query_snapshot"
    assert state["publication_marker_count"] == 1
    assert state["partition_count"] == 1
    assert state["record_count"] == 2
    assert state["resolved_record_count"] == 1
    assert state["quarantined_record_count"] == 1
    assert state["validation_scope"] == (
        "publication_marker_and_exact_partition_bytes"
    )


def test_historical_research_readiness_does_not_promote_observed_partition(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    session = date(2026, 8, 28)
    identity_manifest = (
        root
        / "market-data/snapshots/instrument-master"
        / f"as_of_date={session.isoformat()}"
        / "manifest.json"
    )
    identity_manifest.parent.mkdir(parents=True)
    identity_manifest.write_text(
        json.dumps(
            {
                "completion_status": "completed",
                "as_of_date": session.isoformat(),
                "instrument_count": 10,
                "identity_count": 12,
                "resolver_count": 10,
                "snapshot_content_sha256": "a" * 64,
            }
        )
    )
    membership = (
        root
        / "market-data/universe-membership/schema_version=1"
        / "methodology_version=test/session_date=2026-08-28"
    )
    membership.mkdir(parents=True)
    (membership / "manifest.json").write_text("{}")

    state = report._historical_research_readiness(
        root,
        session_dates=(session,),
        history_validation_scope="all_completed_partitions",
    )
    families = {item["family"]: item for item in state["families"]}

    assert families["universe_membership"]["custody_state"] == (
        "physical_partitions_without_canonical_publication"
    )
    assert families["universe_membership"]["partition_count"] == 0
    assert families["universe_membership"]["physical_partition_count"] == 1
    assert (
        families["universe_membership"][
            "unpublished_physical_partition_count"
        ]
        == 1
    )
    assert (
        "daily_point_in_time_membership_absent"
        in state["blocker_codes"]
    )


def test_canonical_membership_inventory_requires_and_formally_reads_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "data"
    session = date(2026, 8, 28)
    physical = (
        root
        / "market-data/universe-membership/schema_version=1"
        / "methodology_version=test/session_date=2026-08-28"
    )
    publication = (
        root
        / "market-data/universe-membership-publications/schema_version=1"
        / "policy_id=next-open-v1/methodology_version=test"
        / "session_date=2026-08-28"
    )
    physical.mkdir(parents=True)
    publication.mkdir(parents=True)
    monkeypatch.setattr(
        report,
        "read_canonical_universe_membership",
        lambda **_: SimpleNamespace(
            publication_partition_path=publication,
            membership_partition_path=physical,
            publication=SimpleNamespace(
                session_date=session,
                methodology_version="test",
                logical_fingerprint="a" * 64,
            ),
            records=(object(), object()),
        ),
    )

    state = report._canonical_membership_inventory(
        root,
        session_dates=(date(2026, 8, 27), session),
    )

    assert state["custody_state"] == (
        "canonical_signal_eligible_partitions_observed_not_coverage_validated"
    )
    assert state["partition_count"] == 1
    assert state["physical_partition_count"] == 1
    assert state["publication_marker_count"] == 1
    assert state["unpublished_physical_partition_count"] == 0
    assert state["covered_session_count"] == 1
    assert state["missing_eod_session_count"] == 1
    assert state["record_count"] == 2
    assert state["missing_eod_session_dates"] == ("2026-08-27",)
    assert state["missing_eod_session_range"] == {
        "first": "2026-08-27",
        "last": "2026-08-27",
    }
    assert state["publication_fingerprints"] == ("a" * 64,)


def test_canonical_membership_inventory_bounds_large_missing_date_output(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    sessions = tuple(
        date(2026, 1, day) for day in range(1, 32)
    ) + (date(2026, 2, 1), date(2026, 2, 2))

    state = report._canonical_membership_inventory(
        root,
        session_dates=sessions,
    )

    assert state["missing_eod_session_count"] == 33
    assert state["missing_eod_session_dates"] == ()
    assert state["missing_eod_session_range"] == {
        "first": "2026-01-01",
        "last": "2026-02-02",
    }


def test_historical_research_readiness_reports_missing_same_day_identity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    first = date(2026, 8, 27)
    second = date(2026, 8, 28)
    identity_manifest = (
        root
        / "market-data/snapshots/instrument-master"
        / f"as_of_date={first.isoformat()}"
        / "manifest.json"
    )
    identity_manifest.parent.mkdir(parents=True)
    identity_manifest.write_text(
        json.dumps(
            {
                "completion_status": "completed",
                "as_of_date": first.isoformat(),
                "instrument_count": 10,
                "identity_count": 12,
                "resolver_count": 10,
                "snapshot_content_sha256": "a" * 64,
            }
        )
    )

    state = report._historical_research_readiness(
        root,
        session_dates=(first, second),
        history_validation_scope="completion_index_plus_latest_partition",
    )
    families = {item["family"]: item for item in state["families"]}

    assert families["point_in_time_identity"]["covered_session_count"] == 1
    assert families["point_in_time_identity"]["missing_eod_session_dates"] == (
        "2026-08-28",
    )
    assert "same_session_identity_completion_incomplete" in state["blocker_codes"]


def test_historical_research_readiness_rejects_broken_family_symlink(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    session = date(2026, 8, 28)
    identity_manifest = (
        root
        / "market-data/snapshots/instrument-master"
        / f"as_of_date={session.isoformat()}"
        / "manifest.json"
    )
    identity_manifest.parent.mkdir(parents=True)
    identity_manifest.write_text(
        json.dumps(
            {
                "completion_status": "completed",
                "as_of_date": session.isoformat(),
                "instrument_count": 10,
                "identity_count": 12,
                "resolver_count": 10,
                "snapshot_content_sha256": "a" * 64,
            }
        )
    )
    (root / "market-data/universe-membership").symlink_to(
        tmp_path / "missing-target",
        target_is_directory=True,
    )

    with pytest.raises(report.CurrentContextReportError, match="research root is unsafe"):
        report._historical_research_readiness(
            root,
            session_dates=(session,),
            history_validation_scope="completion_index_plus_latest_partition",
        )


def test_matching_bundle_binds_publication_and_snapshot_but_not_current_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    bundle = repo / "build/oci-dashboard/release"
    bundle.mkdir(parents=True)
    (bundle / "deployment-manifest.json").write_text(
        json.dumps(
            {
                "release_id": "release",
                "git_commit": "a" * 40,
                "market_intelligence_publication_id": "publication",
                "default_locale": "en",
                "supported_locales": ["en", "zh"],
                "contains_credentials": False,
                "contains_raw_provider_data": False,
                "contains_parquet": False,
            }
        )
    )
    monkeypatch.setattr(
        report,
        "validate_snapshot_release",
        lambda path: SimpleNamespace(release_id="snapshot"),
    )
    monkeypatch.setattr(report, "_validate_bundle_checksums", lambda path: 13)

    matches = report._matching_local_bundles(
        repo,
        current_git_head="b" * 40,
        snapshot_release="snapshot",
        market_intelligence_publication="publication",
    )

    assert len(matches) == 1
    assert matches[0]["checksum_file_count"] == 13
    assert matches[0]["supported_locales"] == ["en", "zh"]
    assert matches[0]["bundle_source_commit"] == "a" * 40
    assert matches[0]["matches_current_repository_head"] is False
