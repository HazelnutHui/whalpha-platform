from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import MassiveTransportUnavailableError
from tip_api.services import historical_inactive_lifecycle_source as module
from tip_api.services.historical_inactive_lifecycle_source import (
    HistoricalInactiveLifecycleSourceError,
    fetch_historical_inactive_lifecycle_source_package,
    read_historical_inactive_lifecycle_source_package,
)


ANCHOR = date(2026, 7, 16)


class FixtureTransport:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[str, object]] = []

    def get_json(self, path: str, *, params: object, **kwargs: object):
        del kwargs
        self.calls.append((path, params))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FixtureLimiter:
    def __init__(self) -> None:
        self.wait_count = 0

    def wait_before_request(self) -> None:
        self.wait_count += 1


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-secret"))


def _clock(count: int = 20, *, start_seconds: int = 0):
    current = datetime(2026, 9, 5, tzinfo=UTC) + timedelta(seconds=start_seconds)
    values = iter(current + timedelta(seconds=index) for index in range(count))
    return lambda: next(values)


def _page(sequence: int, *, final: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "status": "OK",
        "request_id": f"request-{sequence}",
        "results": [
            {
                "ticker": f"OLD{sequence}",
                "active": False,
                "delisted_utc": "2025-01-02",
                "last_updated_utc": "2026-01-03T00:00:00Z",
            }
        ],
    }
    if not final:
        value["next_url"] = (
            "https://api.massive.com/v3/reference/tickers?"
            f"cursor=cursor-{sequence}"
        )
    return value


def test_fetch_streams_pages_to_formally_readable_owner_only_package(
    tmp_path: Path,
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    transport = FixtureTransport([_page(1), _page(2), _page(3, final=True)])
    limiter = FixtureLimiter()

    result = fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=transport,  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=limiter,  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )

    assert result.status == "published"
    assert result.manifest.request_count == 3
    assert result.manifest.record_count == 3
    assert result.manifest.active_false_count == 3
    assert result.manifest.duplicate_ticker_count == 0
    assert dict(result.manifest.field_presence_counts)["delisted_utc"] == 3
    assert limiter.wait_count == 3
    assert len(transport.calls) == 3
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in target.iterdir())
    first = (target / "response-00001.json").read_text(encoding="utf-8")
    assert "request_id" not in first
    assert "next_url" not in first
    assert "fixture-secret" not in first
    assert read_historical_inactive_lifecycle_source_package(
        package_path=target,
        expected_anchor_date=ANCHOR,
    ) == result.manifest


def test_resume_reuses_verified_pages_after_transport_interruption(
    tmp_path: Path,
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    first = FixtureTransport(
        [_page(1), MassiveTransportUnavailableError("secret response body")]
    )
    with pytest.raises(MassiveTransportUnavailableError):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=first,  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    partial = target.parent / f".{target.name}.partial"
    assert (partial / "response-00001.json").is_file()
    resumed = FixtureTransport([_page(2, final=True)])
    result = fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=resumed,  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )

    assert result.status == "recovered_and_published"
    assert result.manifest.request_count == 2
    assert len(resumed.calls) == 1
    assert not partial.exists()


def test_resume_adopts_exact_page_written_before_checkpoint_crash(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    original_write = module._write_checkpoint

    def crash_after_first_page(partial, checkpoint) -> None:
        if checkpoint.artifacts:
            raise RuntimeError("injected checkpoint crash")
        original_write(partial, checkpoint)

    monkeypatch.setattr(module, "_write_checkpoint", crash_after_first_page)
    with pytest.raises(RuntimeError):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=FixtureTransport([_page(1)]),  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
    monkeypatch.setattr(module, "_write_checkpoint", original_write)

    resumed = FixtureTransport([_page(2, final=True)])
    result = fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=resumed,  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )

    assert result.manifest.request_count == 2
    assert len(resumed.calls) == 1


def test_repeated_pagination_cursor_fails_as_loop(tmp_path: Path) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    repeated = _page(1)
    transport = FixtureTransport([repeated, repeated])

    with pytest.raises(HistoricalInactiveLifecycleSourceError, match="loop"):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=transport,  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    assert len(transport.calls) == 2


def test_existing_complete_package_is_reused_without_provider_call(
    tmp_path: Path,
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=FixtureTransport([_page(1, final=True)]),  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )
    reused_transport = FixtureTransport([])

    result = fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=reused_transport,  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )

    assert result.status == "already_present"
    assert reused_transport.calls == []


def test_completed_and_partial_package_coexistence_fails_closed(
    tmp_path: Path,
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=FixtureTransport([_page(1, final=True)]),  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )
    partial = target.parent / f".{target.name}.partial"
    partial.mkdir(mode=0o700)

    with pytest.raises(HistoricalInactiveLifecycleSourceError, match="coexist"):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )


@pytest.mark.parametrize(
    "bad_page",
    (
        {
            "results": [{"ticker": "LIVE", "active": True}],
        },
        {
            "results": [{"ticker": "OLD", "active": False}],
            "next_url": "https://example.com/v3/reference/tickers?cursor=bad",
        },
    ),
)
def test_out_of_scope_rows_or_pagination_fail_before_page_custody(
    tmp_path: Path, bad_page: dict[str, object]
) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"

    with pytest.raises(HistoricalInactiveLifecycleSourceError):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=FixtureTransport([bad_page]),  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    partial = target.parent / f".{target.name}.partial"
    assert not tuple(partial.glob("response-*.json"))


def test_formal_reader_rejects_page_tampering(tmp_path: Path) -> None:
    target = tmp_path / "inactive-lifecycle" / f"anchor={ANCHOR.isoformat()}"
    fetch_historical_inactive_lifecycle_source_package(
        config=_config(),
        transport=FixtureTransport([_page(1, final=True)]),  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )
    page_path = target / "response-00001.json"
    page_path.chmod(0o600)
    payload = json.loads(page_path.read_text(encoding="utf-8"))
    payload["sanitized_response"]["results"][0]["ticker"] = "CHANGED"
    page_path.write_text(json.dumps(payload), encoding="utf-8")
    page_path.chmod(0o400)

    with pytest.raises(HistoricalInactiveLifecycleSourceError):
        read_historical_inactive_lifecycle_source_package(
            package_path=target,
            expected_anchor_date=ANCHOR,
        )


def test_rejects_package_outside_tmp() -> None:
    with pytest.raises(HistoricalInactiveLifecycleSourceError):
        fetch_historical_inactive_lifecycle_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            anchor_date=ANCHOR,
            package_path=Path("/data/inactive-lifecycle")
            / f"anchor={ANCHOR.isoformat()}",
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
