import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import oci_dashboard_serving_bundle as bundle


RELEASE = "2026-08-29T120000Z-aaaaaaaaaaaa"
COMMIT = "a" * 40
SHA = "b" * 64


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, monkeypatch):
    target = tmp_path / "bundle" / RELEASE
    source = tmp_path / "snapshot"
    for path in (
        target / "dashboard",
        target / "login",
        target / "private-data" / "v1",
        source / "private-data" / "v1",
    ):
        path.mkdir(parents=True, exist_ok=True)
    (target / "dashboard" / "index.html").write_text("dashboard", encoding="utf-8")
    favicon = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (48).to_bytes(4, "big") * 2
    (target / "favicon.png").write_bytes(favicon)
    (target / "dashboard" / "favicon.png").write_bytes(favicon)
    for name in bundle.EXPECTED_LOGIN_FILES:
        (target / "login" / name).write_text(name, encoding="utf-8")
    for root in (target, source):
        (root / "private-data" / "v1" / "manifest.json").write_text(
            '{"snapshot":"exact"}\n', encoding="utf-8"
        )
    snapshot = SimpleNamespace(
        release_id=RELEASE,
        snapshot_contract_version="1.9",
        dashboard_contract_version="2.6",
        market_intelligence_publication_id=RELEASE,
        market_intelligence_payload_sha256=SHA,
        market_intelligence_logical_fingerprint=SHA,
        candidate_analytics_logical_fingerprint=SHA,
        candidate_audit_logical_fingerprint=SHA,
        candidate_strategy_logical_fingerprint=SHA,
        candidate_strategy_audit_logical_fingerprint=SHA,
        current_session_date="2026-08-28",
        previous_session_date="2026-08-27",
    )
    monkeypatch.setattr(bundle, "validate_snapshot_release", lambda _path: snapshot)
    monkeypatch.setattr(bundle, "file_references", lambda _path: (object(),))
    monkeypatch.setattr(bundle, "aggregate_sha", lambda _files: SHA)

    payload = {
        "bundle_contract_version": bundle.CONTRACT_VERSION,
        "release_id": RELEASE,
        "git_commit": COMMIT,
        "source_tree_clean": True,
        "build_timestamp": "2026-08-29T12:00:00Z",
        "frontend_mode": "snapshot",
        "dashboard_base": "/dashboard/",
        "default_locale": "en",
        "supported_locales": ["en", "zh"],
        "guest_and_credential_capability_identical": True,
        "market_intelligence_publication_id": RELEASE,
        "market_intelligence_payload_sha256": SHA,
        "market_intelligence_logical_fingerprint": SHA,
        "snapshot_contract_version": "1.9",
        "dashboard_contract_version": "2.6",
        "snapshot_aggregate_sha256": SHA,
        "snapshot_manifest_sha256": _sha(
            source / "private-data" / "v1" / "manifest.json"
        ),
        "candidate_analytics_logical_fingerprint": SHA,
        "candidate_audit_logical_fingerprint": SHA,
        "candidate_strategy_logical_fingerprint": SHA,
        "candidate_strategy_audit_logical_fingerprint": SHA,
        "current_session_date": "2026-08-28",
        "previous_session_date": "2026-08-27",
        "file_count": 8,
        "contains_credentials": False,
        "contains_raw_provider_data": False,
        "contains_parquet": False,
        "deployment_authorized": False,
    }
    payload["bundle_logical_fingerprint"] = bundle._fingerprint(payload)
    (target / "deployment-manifest.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    files = sorted(
        path for path in target.rglob("*") if path.is_file()
    )
    (target / "checksums.sha256").write_text(
        "".join(
            f"{_sha(path)}  ./{path.relative_to(target).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    return target, source


def test_formal_reader_binds_every_file_to_exact_snapshot(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)

    completed = bundle.read_oci_dashboard_serving_bundle(
        target, expected_snapshot_path=source
    )

    assert completed.deployment_manifest.release_id == RELEASE
    assert completed.checksum_file_count == 9
    assert completed.bundle_logical_fingerprint == completed.deployment_manifest.bundle_logical_fingerprint


def test_unchecksummed_file_fails_closed(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)
    (target / "dashboard" / "extra.js").write_text("changed", encoding="utf-8")

    with pytest.raises(bundle.OciDashboardServingBundleError, match="checksum inventory"):
        bundle.read_oci_dashboard_serving_bundle(
            target, expected_snapshot_path=source
        )


def test_invalid_favicon_fails_closed(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)
    (target / "favicon.png").write_bytes(b"not-a-png")

    with pytest.raises(bundle.OciDashboardServingBundleError, match="favicon"):
        bundle.read_oci_dashboard_serving_bundle(
            target, expected_snapshot_path=source
        )


def test_changed_source_snapshot_fails_closed(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)
    (source / "private-data" / "v1" / "manifest.json").write_text(
        "changed", encoding="utf-8"
    )

    with pytest.raises(bundle.OciDashboardServingBundleError, match="source Snapshot"):
        bundle.read_oci_dashboard_serving_bundle(
            target, expected_snapshot_path=source
        )


def test_symlink_entry_fails_closed(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)
    (target / "dashboard" / "link").symlink_to(target / "dashboard" / "index.html")

    with pytest.raises(bundle.OciDashboardServingBundleError, match="unsafe entry"):
        bundle.read_oci_dashboard_serving_bundle(
            target, expected_snapshot_path=source
        )


def test_demo_marker_fails_closed_before_checksum_trust(tmp_path, monkeypatch) -> None:
    target, source = _fixture(tmp_path, monkeypatch)
    (target / "dashboard" / "index.html").write_text(
        "demoDashboardData", encoding="utf-8"
    )

    with pytest.raises(bundle.OciDashboardServingBundleError, match="demo data"):
        bundle.read_oci_dashboard_serving_bundle(
            target, expected_snapshot_path=source
        )


def test_snapshot_1_11_bundle_requires_visual_and_sector_bindings(
    tmp_path, monkeypatch
) -> None:
    target, _source = _fixture(tmp_path, monkeypatch)
    payload = json.loads((target / "deployment-manifest.json").read_text())
    payload.update(
        snapshot_contract_version="1.11",
        dashboard_contract_version="2.8",
        candidate_visual_context_audit_logical_fingerprint=SHA,
        sector_rotation_product_logical_fingerprint=SHA,
    )
    parsed = bundle.OciDashboardDeploymentManifest.model_validate(payload)
    assert parsed.sector_rotation_product_logical_fingerprint == SHA

    payload.pop("sector_rotation_product_logical_fingerprint")
    with pytest.raises(ValueError, match="fixed boundary"):
        bundle.OciDashboardDeploymentManifest.model_validate(payload)
