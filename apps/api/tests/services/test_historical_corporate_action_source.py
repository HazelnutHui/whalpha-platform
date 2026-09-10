from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import MassiveTransportUnavailableError
from tip_api.services import historical_corporate_action_source as module
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    HistoricalCorporateActionSourceError,
    fetch_historical_corporate_action_source_package,
    read_historical_corporate_action_source_package,
)


START = date(2025, 6, 23)
END = date(2026, 9, 4)


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
    def __init__(self, interval_seconds: Decimal | None = None) -> None:
        self.wait_count = 0
        if interval_seconds is not None:
            self.interval_seconds = interval_seconds

    def wait_before_request(self) -> None:
        self.wait_count += 1


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-secret"))


def _clock(count: int = 20, *, start_seconds: int = 0):
    current = datetime(2026, 9, 8, tzinfo=UTC) + timedelta(seconds=start_seconds)
    values = iter(current + timedelta(seconds=index) for index in range(count))
    return lambda: next(values)


def _target(tmp_path: Path, kind: CorporateActionSourceKind) -> Path:
    return tmp_path / "corporate-actions" / (
        f"{kind.value}={START.isoformat()}_{END.isoformat()}"
    )


def _split_page(sequence: int, *, final: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "status": "OK",
        "request_id": f"request-{sequence}",
        "results": [
            {
                "adjustment_type": "forward_split",
                "execution_date": f"2026-0{sequence + 1}-02",
                "historical_adjustment_factor": 0.5,
                "id": f"split-{sequence}",
                "split_from": 1,
                "split_to": 2,
                "ticker": "AAA",
            }
        ],
    }
    if not final:
        value["next_url"] = (
            "https://api.massive.com/stocks/v1/splits?"
            f"cursor=cursor-{sequence}&apiKey=must-not-be-retained"
        )
    return value


def _dividend_page(*, extra_field: bool = False) -> dict[str, object]:
    row: dict[str, object] = {
        "cash_amount": 0.25,
        "currency": "USD",
        "declaration_date": "2026-07-15",
        "distribution_type": "recurring",
        "ex_dividend_date": "2026-08-15",
        "frequency": 4,
        "historical_adjustment_factor": 0.9975,
        "id": "dividend-1",
        "pay_date": "2026-08-22",
        "record_date": "2026-08-15",
        "split_adjusted_cash_amount": 0.25,
        "ticker": "AAA",
    }
    if extra_field:
        row["new_provider_field"] = "preserved"
    return {"status": "OK", "request_id": "request-dividend", "results": [row]}


def test_split_fetch_is_resumable_owner_only_and_formally_readable(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)
    transport = FixtureTransport(
        [_split_page(1), _split_page(2), _split_page(3, final=True)]
    )
    limiter = FixtureLimiter()

    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=transport,  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=limiter,  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )

    assert result.status == "published"
    assert result.manifest.request_count == 3
    assert result.manifest.record_count == 3
    assert result.manifest.valid_effective_date_count == 3
    assert result.manifest.invalid_effective_date_count == 0
    assert result.manifest.identity_resolution_status == "not_attempted"
    assert result.manifest.research_eligibility == "source_observation_only"
    assert limiter.wait_count == 3
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in target.iterdir())
    first = (target / "response-00001.json").read_text(encoding="utf-8")
    assert "request_id" not in first
    assert "next_url" not in first
    assert "must-not-be-retained" not in first
    assert "fixture-secret" not in first

    reread = read_historical_corporate_action_source_package(
        package_path=target,
        expected_action_kind=CorporateActionSourceKind.SPLIT,
        expected_start_date=START,
        expected_end_date=END,
    )
    assert reread.manifest == result.manifest
    assert len(reread.pages) == 3


def test_dividend_source_preserves_and_counts_schema_additions(tmp_path: Path) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.DIVIDEND)

    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport([_dividend_page(extra_field=True)]),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.DIVIDEND,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )

    assert result.manifest.record_count == 1
    assert result.manifest.unexpected_field_counts == (("new_provider_field", 1),)
    source = (target / "response-00001.json").read_text(encoding="utf-8")
    assert "new_provider_field" in source
    assert "preserved" in source


def test_paid_interval_and_five_year_page_ceiling_are_recorded(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)
    pages: list[dict[str, object]] = []
    for sequence in range(1, 18):
        page = _split_page(1, final=sequence == 17)
        row = page["results"][0]  # type: ignore[index]
        row["id"] = f"split-{sequence}"  # type: ignore[index]
        if sequence != 17:
            page["next_url"] = (
                "https://api.massive.com/stocks/v1/splits?"
                f"cursor=cursor-{sequence}&apiKey=must-not-be-retained"
            )
        pages.append(page)

    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport(pages),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(Decimal("0.25")),  # type: ignore[arg-type]
        clock=_clock(count=40),
    )

    assert result.manifest.contract_version.endswith("/1.1")
    assert result.manifest.request_count == 17
    assert result.manifest.maximum_page_count == 80
    assert result.manifest.maximum_record_count == 400_000
    assert result.manifest.minimum_request_interval_seconds == "0.25"


def test_resume_rejects_request_interval_drift(tmp_path: Path) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)
    with pytest.raises(MassiveTransportUnavailableError):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport(
                [_split_page(1), MassiveTransportUnavailableError("stopped")]
            ),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=target,
            rate_limiter=FixtureLimiter(Decimal("0.25")),  # type: ignore[arg-type]
            clock=_clock(),
        )

    with pytest.raises(HistoricalCorporateActionSourceError, match="interval differs"):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=target,
            rate_limiter=FixtureLimiter(Decimal("1")),  # type: ignore[arg-type]
            clock=_clock(start_seconds=100),
        )


def test_formal_reader_remains_compatible_with_legacy_manifest(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.DIVIDEND)
    fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport([_dividend_page()]),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.DIVIDEND,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )
    checkpoint_path = target / "checkpoint.json"
    manifest_path = target / "package.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint.pop("request_interval_seconds")
    checkpoint["logical_fingerprint"] = module._fingerprint(
        {key: value for key, value in checkpoint.items() if key != "logical_fingerprint"}
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "contract_version": module.LEGACY_CONTRACT_VERSION,
            "maximum_page_count": module.LEGACY_MAXIMUM_PAGE_COUNT,
            "maximum_record_count": module.LEGACY_MAXIMUM_RECORD_COUNT,
            "minimum_request_interval_seconds": (
                module.LEGACY_REQUEST_INTERVAL_SECONDS
            ),
        }
    )
    manifest["logical_fingerprint"] = module._fingerprint(
        {key: value for key, value in manifest.items() if key != "logical_fingerprint"}
    )
    for path, payload in ((checkpoint_path, checkpoint), (manifest_path, manifest)):
        path.chmod(0o600)
        path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        path.chmod(0o400)

    reread = read_historical_corporate_action_source_package(
        package_path=target,
        expected_action_kind=CorporateActionSourceKind.DIVIDEND,
        expected_start_date=START,
        expected_end_date=END,
    )
    assert reread.manifest.contract_version == module.LEGACY_CONTRACT_VERSION


def test_empty_result_is_a_complete_observation(tmp_path: Path) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.DIVIDEND)
    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport([{"status": "OK", "results": []}]),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.DIVIDEND,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )

    assert result.manifest.request_count == 1
    assert result.manifest.record_count == 0
    assert result.manifest.pagination_complete is True


def test_resume_reuses_verified_page_after_transport_interruption(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)
    with pytest.raises(MassiveTransportUnavailableError):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport(
                [_split_page(1), MassiveTransportUnavailableError("secret body")]
            ),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    partial = target.parent / f".{target.name}.partial"
    assert (partial / "response-00001.json").is_file()
    resumed_transport = FixtureTransport([_split_page(2, final=True)])
    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=resumed_transport,  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )

    assert result.status == "recovered_and_published"
    assert result.manifest.request_count == 2
    assert len(resumed_transport.calls) == 1
    assert not partial.exists()


def test_resume_adopts_exact_page_written_before_checkpoint_crash(
    monkeypatch, tmp_path: Path
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)
    original_write = module._write_checkpoint

    def crash_after_first_page(partial, checkpoint) -> None:
        if checkpoint.artifacts:
            raise RuntimeError("injected checkpoint crash")
        original_write(partial, checkpoint)

    monkeypatch.setattr(module, "_write_checkpoint", crash_after_first_page)
    with pytest.raises(RuntimeError):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([_split_page(1)]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
    monkeypatch.setattr(module, "_write_checkpoint", original_write)

    result = fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport([_split_page(2, final=True)]),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(start_seconds=100),
    )
    assert result.manifest.request_count == 2


@pytest.mark.parametrize(
    "bad_page,match",
    (
        (
            {
                "status": "OK",
                "results": [
                    {
                        "id": "outside",
                        "ticker": "AAA",
                        "execution_date": "2025-06-22",
                    }
                ],
            },
            "out-of-scope",
        ),
        (
            {
                "status": "OK",
                "results": [],
                "next_url": "https://example.com/stocks/v1/splits?cursor=bad",
            },
            "host",
        ),
        ({"status": "ERROR", "results": []}, "not OK"),
        (
            {
                "status": "OK",
                "results": [{"execution_date": "2026-08-01", "api_key": "bad"}],
            },
            "forbidden",
        ),
    ),
)
def test_scope_host_status_and_secret_fail_before_source_custody(
    tmp_path: Path, bad_page: dict[str, object], match: str
) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.SPLIT)

    with pytest.raises(HistoricalCorporateActionSourceError, match=match):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([bad_page]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=target,
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    partial = target.parent / f".{target.name}.partial"
    assert not tuple(partial.glob("response-*.json"))


def test_formal_reader_rejects_page_tampering(tmp_path: Path) -> None:
    target = _target(tmp_path, CorporateActionSourceKind.DIVIDEND)
    fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport([_dividend_page()]),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.DIVIDEND,
        start_date=START,
        end_date=END,
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

    with pytest.raises(HistoricalCorporateActionSourceError, match="custody"):
        read_historical_corporate_action_source_package(
            package_path=target,
            expected_action_kind=CorporateActionSourceKind.DIVIDEND,
            expected_start_date=START,
            expected_end_date=END,
        )


def test_rejects_reversed_current_and_non_tmp_ranges(tmp_path: Path) -> None:
    with pytest.raises(HistoricalCorporateActionSourceError, match="reversed"):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=END,
            end_date=START,
            package_path=tmp_path / "not-used",
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    today = date.today()
    with pytest.raises(HistoricalCorporateActionSourceError, match="historical"):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=today,
            package_path=tmp_path / "not-used",
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )

    with pytest.raises(HistoricalCorporateActionSourceError, match="/tmp"):
        fetch_historical_corporate_action_source_package(
            config=_config(),
            transport=FixtureTransport([]),  # type: ignore[arg-type]
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            package_path=Path("/data")
            / f"split={START.isoformat()}_{END.isoformat()}",
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
