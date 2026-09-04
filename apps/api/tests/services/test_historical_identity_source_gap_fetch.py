from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import MassiveTransportTimeoutError
from tip_api.services import historical_identity_source_gap_fetch as module
from tip_api.services.historical_identity_source_gap_fetch import (
    HistoricalIdentitySourceGapFetchError,
    HistoricalIdentitySourceGapFetchStoppedError,
    run_historical_identity_source_gap_fetch,
)


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-key"))


def _prepare_runner(monkeypatch, tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    data_root.mkdir()

    class FakeEodRepository:
        def __init__(self, root: Path) -> None:
            assert root == data_root

        def list_session_index(self) -> tuple[date, ...]:
            return (date(2026, 7, 17), date(2026, 7, 20))

    monkeypatch.setattr(module, "_validate_data_root", lambda path: path)
    monkeypatch.setattr(module, "CanonicalEodReadRepository", FakeEodRepository)
    monkeypatch.setattr(module, "_validate_gap_session", lambda **kwargs: None)
    return data_root


def test_fetches_exact_sessions_with_one_shared_limiter_and_formal_reread(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root = _prepare_runner(monkeypatch, tmp_path)
    limiter = object()
    fetch_calls: list[tuple[date, object]] = []
    read_calls: list[date] = []

    def fake_fetch(**kwargs) -> None:
        package_path = kwargs["package_path"]
        package_path.mkdir()
        fetch_calls.append((kwargs["session_date"], kwargs["rate_limiter"]))

    def fake_read(**kwargs) -> object:
        session = kwargs["expected_session"]
        read_calls.append(session)
        return SimpleNamespace(
            request_count=13,
            package_manifest_sha256=session.isoformat().encode().hex().ljust(64, "0")[:64],
            package_content_sha256="b" * 64,
        )

    monkeypatch.setattr(module, "fetch_identity_package", fake_fetch)
    monkeypatch.setattr(module, "read_fetch_package_evidence", fake_read)
    progress: list[tuple[int, int, str]] = []
    sessions = (date(2026, 7, 17), date(2026, 7, 20))
    result = run_historical_identity_source_gap_fetch(
        config=_config(),
        transport=object(),
        data_root=data_root,
        package_root=tmp_path / "packages",
        session_dates=sessions,
        rate_limiter=limiter,  # type: ignore[arg-type]
        progress=lambda completed, total, item: progress.append(
            (completed, total, item.session_date)
        ),
    )

    assert fetch_calls == [(session, limiter) for session in sessions]
    assert read_calls == list(sessions)
    assert progress == [
        (1, 2, "2026-07-17"),
        (2, 2, "2026-07-20"),
    ]
    assert result.status == "complete"
    assert result.fetched_package_count == 2
    assert result.reused_package_count == 0
    assert result.package_request_count == 26
    assert result.provider_request_attempt_count == 0
    assert result.canonical_data_write_count == 0
    assert result.canonical_source_custody_write_count == 0


def test_resume_reuses_formally_readable_package_without_network(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root = _prepare_runner(monkeypatch, tmp_path)
    package_root = tmp_path / "packages"
    package_root.mkdir(mode=0o700)
    session_root = package_root / "session=2026-07-17"
    session_root.mkdir(mode=0o700)
    (session_root / "identity-package").mkdir()
    monkeypatch.setattr(
        module,
        "fetch_identity_package",
        lambda **kwargs: pytest.fail("resume attempted a provider request"),
    )
    monkeypatch.setattr(
        module,
        "read_fetch_package_evidence",
        lambda **kwargs: SimpleNamespace(
            request_count=13,
            package_manifest_sha256="a" * 64,
            package_content_sha256="b" * 64,
        ),
    )

    result = run_historical_identity_source_gap_fetch(
        config=_config(),
        transport=object(),
        data_root=data_root,
        package_root=package_root,
        session_dates=(date(2026, 7, 17),),
    )

    assert result.reused_package_count == 1
    assert result.fetched_package_count == 0
    assert result.provider_request_attempt_count == 0
    assert result.items[0].status == "reused_and_verified"


def test_transient_fetch_failure_retries_inside_same_exact_session(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root = _prepare_runner(monkeypatch, tmp_path)
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
            raise MassiveTransportTimeoutError("secret response text")
        kwargs["package_path"].mkdir()

    class FixtureTransport:
        def get_json(self, *args, **kwargs) -> dict[str, object]:
            del args, kwargs
            return {}

    monkeypatch.setattr(module, "fetch_identity_package", fake_fetch)
    monkeypatch.setattr(
        module,
        "read_fetch_package_evidence",
        lambda **kwargs: SimpleNamespace(
            request_count=13,
            package_manifest_sha256="a" * 64,
            package_content_sha256="b" * 64,
        ),
    )

    result = run_historical_identity_source_gap_fetch(
        config=_config(),
        transport=FixtureTransport(),
        data_root=data_root,
        package_root=tmp_path / "packages",
        session_dates=(date(2026, 7, 17),),
        transient_retry_delays_seconds=(1, 2),
        sleep=sleeps.append,
    )

    assert attempts == 2
    assert sleeps == [1]
    assert result.provider_request_attempt_count == 2
    assert result.transient_retry_count == 1
    assert result.items[0].transient_failure_codes == ("transport_timeout",)


def test_retry_exhaustion_reports_only_bounded_resumable_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root = _prepare_runner(monkeypatch, tmp_path)

    def fake_fetch(**kwargs) -> None:
        kwargs["transport"].get_json(
            "/fixture",
            params={},
            api_key=SecretStr("fixture-key"),
            timeout_seconds=Decimal("1"),
            base_url="https://api.massive.com",
        )
        raise MassiveTransportTimeoutError("secret response text")

    class FixtureTransport:
        def get_json(self, *args, **kwargs) -> dict[str, object]:
            del args, kwargs
            return {}

    monkeypatch.setattr(module, "fetch_identity_package", fake_fetch)

    with pytest.raises(HistoricalIdentitySourceGapFetchStoppedError) as caught:
        run_historical_identity_source_gap_fetch(
            config=_config(),
            transport=FixtureTransport(),
            data_root=data_root,
            package_root=tmp_path / "packages",
            session_dates=(date(2026, 7, 17),),
            transient_retry_delays_seconds=(1, 2),
            sleep=lambda seconds: None,
        )

    assert caught.value.failed_session == date(2026, 7, 17)
    assert caught.value.provider_request_attempt_count == 3
    assert caught.value.transient_retry_count == 2
    assert caught.value.transient_failure_count == 3
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize(
    "sessions",
    (
        (),
        (date(2026, 7, 20), date(2026, 7, 17)),
        (date(2026, 7, 17), date(2026, 7, 17)),
        tuple(date(2026, 1, day) for day in range(1, 26)),
    ),
)
def test_rejects_unbounded_unordered_or_duplicate_session_sets(
    sessions: tuple[date, ...],
) -> None:
    with pytest.raises(HistoricalIdentitySourceGapFetchError):
        module._validate_session_dates(sessions)


def test_rejects_session_that_already_has_canonical_source_custody(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    source_partition = (
        data_root
        / "market-data"
        / "provider-identity-reference-observation"
        / "schema_version=1"
        / "provider=massive_stocks_basic"
        / "as_of_date=2026-07-17"
    )
    source_partition.mkdir(parents=True)
    monkeypatch.setattr(
        module.ParquetInstrumentMasterSnapshotRepository,
        "inspect_snapshot",
        lambda self, session: object(),
    )

    with pytest.raises(HistoricalIdentitySourceGapFetchError, match="already"):
        module._validate_gap_session(
            data_root=data_root,
            canonical_eod_sessions=frozenset({date(2026, 7, 17)}),
            session_date=date(2026, 7, 17),
        )
