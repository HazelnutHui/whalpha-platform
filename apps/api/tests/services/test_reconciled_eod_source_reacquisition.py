from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageDisposition,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import MassiveTransportTimeoutError
from tip_api.services import reconciled_eod_source_reacquisition as module
from tip_api.services.reconciled_eod_source_reacquisition import (
    ReconciledEodSourceReacquisitionError,
    ReconciledEodSourceReacquisitionStoppedError,
    run_reconciled_eod_source_reacquisition,
)


SESSION = date(2026, 7, 17)
NOW = datetime(2026, 9, 11, 2, tzinfo=UTC)


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-key"))


def _coverage(*, disposition=ReconciledEodSourceCoverageDisposition.MISSING):
    return SimpleNamespace(
        sessions=(
            SimpleNamespace(
                session_date=SESSION,
                disposition=disposition,
                reason_codes=("grouped_daily_source_package_missing",),
                canonical_eod_fingerprint="a" * 64,
                canonical_identity_fingerprint="b" * 64,
            ),
        )
    )


def _prepare_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    data_root = tmp_path / "data"
    data_root.mkdir()
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    package_root = state_root / "reconciled-eod-source-reacquisition"
    monkeypatch.setattr(module, "APPROVED_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "_validate_sessions_against_coverage",
        lambda **_kwargs: None,
    )
    return data_root, package_root


class _Limiter:
    def __init__(self) -> None:
        self.calls = 0

    def wait_before_request(self) -> None:
        self.calls += 1


class _FixtureTransport:
    def get_json(self, *_args, **_kwargs) -> dict[str, object]:
        return {}


def _evidence() -> object:
    return SimpleNamespace(
        request_count=1,
        package_manifest_sha256="c" * 64,
        package_content_sha256="d" * 64,
        fetched_at=NOW,
    )


def test_fetches_exact_coverage_gap_and_emits_bounded_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, package_root = _prepare_runner(monkeypatch, tmp_path)
    limiter = _Limiter()

    def fake_fetch(**kwargs) -> None:
        kwargs["transport"].get_json(
            "/fixture",
            params={},
            api_key=SecretStr("fixture-key"),
            timeout_seconds=Decimal("1"),
            base_url="https://api.massive.com",
        )
        kwargs["package_path"].mkdir()

    monkeypatch.setattr(module, "fetch_eod_package", fake_fetch)
    monkeypatch.setattr(
        module,
        "read_fetch_package_evidence",
        lambda **_kwargs: _evidence(),
    )
    progress: list[tuple[int, int, str]] = []

    result = run_reconciled_eod_source_reacquisition(
        config=_config(),
        transport=_FixtureTransport(),
        data_root=data_root,
        package_root=package_root,
        coverage=_coverage(),
        session_dates=(SESSION,),
        rate_limiter=limiter,  # type: ignore[arg-type]
        progress=lambda complete, total, item: progress.append(
            (complete, total, item.session_date)
        ),
    )

    assert limiter.calls == 1
    assert progress == [(1, 1, SESSION.isoformat())]
    assert result.status == "complete"
    assert result.fetched_package_count == 1
    assert result.reused_package_count == 0
    assert result.provider_request_attempt_count == 1
    assert result.source_package_write_count == 1
    assert result.canonical_data_write_count == 0
    assert result.production_authority is False


def test_resume_reuses_verified_package_without_provider_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, package_root = _prepare_runner(monkeypatch, tmp_path)
    package = (
        package_root
        / "sessions"
        / f"session_date={SESSION.isoformat()}"
        / "eod-acquisition-package"
    )
    package.mkdir(parents=True)
    package_root.chmod(0o700)
    package.parent.parent.chmod(0o700)
    package.parent.chmod(0o700)
    monkeypatch.setattr(
        module,
        "fetch_eod_package",
        lambda **_kwargs: pytest.fail("resume attempted a provider request"),
    )
    monkeypatch.setattr(
        module,
        "read_fetch_package_evidence",
        lambda **_kwargs: _evidence(),
    )

    result = run_reconciled_eod_source_reacquisition(
        config=_config(),
        transport=_FixtureTransport(),
        data_root=data_root,
        package_root=package_root,
        coverage=_coverage(),
        session_dates=(SESSION,),
    )

    assert result.reused_package_count == 1
    assert result.fetched_package_count == 0
    assert result.provider_request_attempt_count == 0
    assert result.source_package_write_count == 0
    assert result.items[0].status == "reused_and_verified"


def test_transient_failure_retries_then_completes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, package_root = _prepare_runner(monkeypatch, tmp_path)
    attempts = 0
    sleeps: list[float] = []

    def fake_fetch(**kwargs) -> None:
        nonlocal attempts
        attempts += 1
        kwargs["transport"].get_json(
            "/fixture",
            params={},
            api_key=SecretStr("fixture-key"),
            timeout_seconds=Decimal("1"),
            base_url="https://api.massive.com",
        )
        if attempts == 1:
            raise MassiveTransportTimeoutError("private provider response")
        kwargs["package_path"].mkdir()

    monkeypatch.setattr(module, "fetch_eod_package", fake_fetch)
    monkeypatch.setattr(
        module,
        "read_fetch_package_evidence",
        lambda **_kwargs: _evidence(),
    )

    result = run_reconciled_eod_source_reacquisition(
        config=_config(),
        transport=_FixtureTransport(),
        data_root=data_root,
        package_root=package_root,
        coverage=_coverage(),
        session_dates=(SESSION,),
        rate_limiter=_Limiter(),  # type: ignore[arg-type]
        transient_retry_delays_seconds=(1,),
        sleep=sleeps.append,
    )

    assert attempts == 2
    assert sleeps == [1]
    assert result.provider_request_attempt_count == 2
    assert result.transient_retry_count == 1
    assert result.items[0].transient_failure_codes == ("transport_timeout",)


def test_retry_exhaustion_is_typed_and_resumable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, package_root = _prepare_runner(monkeypatch, tmp_path)

    def fail(**kwargs) -> None:
        kwargs["transport"].get_json(
            "/fixture",
            params={},
            api_key=SecretStr("fixture-key"),
            timeout_seconds=Decimal("1"),
            base_url="https://api.massive.com",
        )
        raise MassiveTransportTimeoutError("private provider response")

    monkeypatch.setattr(module, "fetch_eod_package", fail)

    with pytest.raises(
        ReconciledEodSourceReacquisitionStoppedError
    ) as captured:
        run_reconciled_eod_source_reacquisition(
            config=_config(),
            transport=_FixtureTransport(),
            data_root=data_root,
            package_root=package_root,
            coverage=_coverage(),
            session_dates=(SESSION,),
            rate_limiter=_Limiter(),  # type: ignore[arg-type]
            transient_retry_delays_seconds=(1,),
            sleep=lambda _seconds: None,
        )

    assert captured.value.failed_session == SESSION
    assert captured.value.provider_request_attempt_count == 2
    assert captured.value.transient_retry_count == 1
    assert captured.value.transient_failure_count == 2


def test_requires_exact_missing_disposition_and_unchanged_canonical_binding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()

    class FakeRepository:
        def __init__(self, root: Path) -> None:
            assert root == data_root

        def inspect_session(self, session: date) -> object:
            assert session == SESSION
            return SimpleNamespace(
                content_fingerprint="a" * 64,
                identity_snapshot_fingerprint="b" * 64,
            )

    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeRepository)
    monkeypatch.setattr(
        module,
        "read_identity_source_custody_at_data_root",
        lambda **_kwargs: SimpleNamespace(
            manifest=SimpleNamespace(canonical_snapshot_fingerprint="b" * 64)
        ),
    )

    module._validate_sessions_against_coverage(
        data_root=data_root,
        coverage=_coverage(),
        session_dates=(SESSION,),
    )
    with pytest.raises(ReconciledEodSourceReacquisitionError, match="not one"):
        module._validate_sessions_against_coverage(
            data_root=data_root,
            coverage=_coverage(
                disposition=(
                    ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
                )
            ),
            session_dates=(SESSION,),
        )


def test_rejects_unordered_or_oversized_session_request() -> None:
    with pytest.raises(ReconciledEodSourceReacquisitionError, match="1–40"):
        module._validate_session_dates((SESSION, SESSION))
    with pytest.raises(ReconciledEodSourceReacquisitionError, match="1–40"):
        module._validate_session_dates(
            tuple(date(2026, 1, day) for day in range(1, 32))
            + tuple(date(2026, 2, day) for day in range(1, 11))
        )
