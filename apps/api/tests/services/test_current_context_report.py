from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import current_context_report as report


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
