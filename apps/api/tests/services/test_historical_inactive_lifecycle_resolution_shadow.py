from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import shutil

import pytest
from pydantic import SecretStr, ValidationError

from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ProviderTickerResolverV1,
    QualityStatus,
    ResolutionMethod,
    ResolutionStatus,
)
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    REVIEW_LIMITATION_CODES,
    HistoricalInactiveLifecycleResolutionDecisionV1,
    InactiveLifecycleDisposition,
)
from tip_api.ingestion.instrument_identity import (
    canonical_instrument_id_for_identity,
    select_stable_identity,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services import historical_inactive_lifecycle_resolution_shadow as module
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    DECISION_FILE,
    HistoricalInactiveLifecycleResolutionShadowError,
    build_historical_inactive_lifecycle_resolution_shadow,
    read_historical_inactive_lifecycle_resolution_shadow,
)
from tip_api.services.historical_inactive_lifecycle_source import (
    fetch_historical_inactive_lifecycle_source_package,
)


ANCHOR = date(2026, 7, 16)
FIRST = date(2026, 7, 14)
LAST = date(2026, 7, 16)
MATERIALIZED = datetime(2026, 9, 5, 12, tzinfo=UTC)


class _Transport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def get_json(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return self.response


class _Limiter:
    def wait_before_request(self) -> None:
        return None


def _stable_id(figi: str):
    candidate = select_stable_identity(
        share_class_figi=figi,
        composite_figi=None,
        provider_instrument_id=None,
    )
    assert candidate is not None
    return canonical_instrument_id_for_identity(candidate)


def _snapshot_records(session: date, tickers: tuple[tuple[str, str], ...]):
    instruments = []
    identities = []
    resolvers = []
    for ticker, figi in tickers:
        instrument_id = _stable_id(figi)
        ingested_at = datetime.combine(session, datetime.min.time(), tzinfo=UTC)
        instruments.append(
            InstrumentMasterV1(
                instrument_id=instrument_id,
                issuer_id=None,
                instrument_type=InstrumentType.COMMON_STOCK,
                status=InstrumentStatus.ACTIVE,
                ticker=ticker,
                name=f"{ticker} Test",
                primary_exchange="XNYS",
                listing_country="US",
                currency="USD",
                figi=figi,
                cik=None,
                valid_from=session,
                valid_to=None,
                first_trade_date=None,
                last_trade_date=None,
                as_of_date=session,
                source=MASSIVE_PROVIDER_ID,
                source_instrument_id=f"share_class_figi:{figi}",
                ingested_at=ingested_at,
                quality_status=QualityStatus.VALID,
                quality_notes=None,
            )
        )
        identities.append(
            ProviderInstrumentIdentityV1(
                provider=MASSIVE_PROVIDER_ID,
                as_of_date=session,
                provider_ticker=ticker,
                share_class_figi=figi,
                canonical_instrument_id=instrument_id,
                resolution_status=ResolutionStatus.RESOLVED,
                resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
                valid_from=session,
                ingested_at=ingested_at,
                quality_status=QualityStatus.VALID,
            )
        )
        resolvers.append(
            ProviderTickerResolverV1(
                provider=MASSIVE_PROVIDER_ID,
                as_of_date=session,
                provider_ticker=ticker,
                canonical_instrument_id=instrument_id,
                resolution_method=ResolutionMethod.SHARE_CLASS_FIGI.value,
                source_identity_key=f"share_class_figi:{figi}",
                ingested_at=ingested_at,
            )
        )
    return tuple(instruments), tuple(identities), tuple(resolvers)


def _publish_snapshot(
    root: Path, session: date, tickers: tuple[tuple[str, str], ...]
) -> None:
    instruments, identities, resolvers = _snapshot_records(session, tickers)
    ParquetInstrumentMasterSnapshotRepository(root=root).publish_snapshot(
        instruments=instruments,
        identities=identities,
        resolvers=resolvers,
        as_of_date=session,
        provider_id=MASSIVE_PROVIDER_ID,
        quality_summary={},
    )


def _source_rows() -> list[dict[str, object]]:
    return [
        {"ticker": "AAA", "active": False, "share_class_figi": "FIGI-A", "delisted_utc": "2026-07-15"},
        {"ticker": "NOID", "active": False, "delisted_utc": "2026-07-15"},
        {"ticker": "DUP1", "active": False, "share_class_figi": "FIGI-DUP", "delisted_utc": "2026-07-15"},
        {"ticker": "DUP2", "active": False, "share_class_figi": "FIGI-DUP", "delisted_utc": "2026-07-15"},
        {"ticker": "ABSENT", "active": False, "share_class_figi": "FIGI-ABSENT", "delisted_utc": "2026-07-15"},
        {"ticker": "LATE", "active": False, "share_class_figi": "FIGI-LATE", "delisted_utc": "2026-07-15"},
        {"ticker": "WRONG", "active": False, "share_class_figi": "FIGI-TICKER", "delisted_utc": "2026-07-16"},
        {"ticker": "FUTURE", "active": False, "share_class_figi": "FIGI-FUTURE", "delisted_utc": "2026-07-17"},
    ]


def _fixture(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root)
    _publish_snapshot(
        data_root,
        FIRST,
        (
            ("AAA", "FIGI-A"),
            ("LATE", "FIGI-LATE"),
            ("RIGHT", "FIGI-TICKER"),
            ("FUTURE", "FIGI-FUTURE"),
        ),
    )
    _publish_snapshot(
        data_root,
        LAST,
        (
            ("LATE", "FIGI-LATE"),
            ("RIGHT", "FIGI-TICKER"),
            ("FUTURE", "FIGI-FUTURE"),
        ),
    )
    source = tmp_path / "inactive-source" / f"anchor={ANCHOR.isoformat()}"
    fetch_historical_inactive_lifecycle_source_package(
        config=MassiveProviderConfig(api_key=SecretStr("fixture-secret")),
        transport=_Transport({"status": "OK", "results": _source_rows()}),  # type: ignore[arg-type]
        anchor_date=ANCHOR,
        package_path=source,
        rate_limiter=_Limiter(),  # type: ignore[arg-type]
        clock=lambda: MATERIALIZED - timedelta(minutes=1),
    )
    output = tmp_path / "shadow"
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    return data_root, source, output


def test_builds_one_to_one_fail_closed_shadow(monkeypatch, tmp_path: Path) -> None:
    data_root, source, output = _fixture(monkeypatch, tmp_path)

    result = build_historical_inactive_lifecycle_resolution_shadow(
        data_root=data_root,
        source_package_path=source,
        output_root=output,
        anchor_date=ANCHOR,
        materialized_at=MATERIALIZED,
    )

    assert result.status == "published"
    assert dict(result.manifest.disposition_counts) == {
        "quarantined": 7,
        "review_candidate": 1,
    }
    assert result.manifest.source_package_record_count == 8
    assert result.manifest.canonical_history_session_count == 2
    reread = read_historical_inactive_lifecycle_resolution_shadow(
        root=output, anchor_date=ANCHOR
    )
    assert len(reread.source_observations) == len(reread.decisions) == 8
    decisions = {
        row.source_row_sequence: row for row in reread.decisions
    }
    assert decisions[1].disposition is InactiveLifecycleDisposition.REVIEW_CANDIDATE
    assert decisions[1].reason_codes == REVIEW_LIMITATION_CODES
    assert decisions[2].reason_codes == ("missing_stable_security_identifier",)
    assert decisions[3].identity_resolution_status is ResolutionStatus.AMBIGUOUS
    assert decisions[3].reason_codes == ("stable_identifier_collision",)
    assert decisions[4].reason_codes == ("stable_identifier_collision",)
    assert decisions[5].reason_codes == (
        "stable_identifier_absent_from_canonical_history",
    )
    assert decisions[6].reason_codes == (
        "canonical_instrument_seen_after_delisted_date",
    )
    assert decisions[7].reason_codes == (
        "source_ticker_absent_from_canonical_history",
    )
    assert decisions[8].reason_codes == ("delisted_date_after_anchor",)
    assert result.partition_path.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in result.partition_path.iterdir())


def test_parallel_and_serial_canonical_history_are_identical(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_root, _, _ = _fixture(monkeypatch, tmp_path)

    serial = module._read_canonical_history(
        data_root,
        ANCHOR,
        max_workers=1,
    )
    parallel = module._read_canonical_history(
        data_root,
        ANCHOR,
        max_workers=2,
    )

    assert parallel == serial


@pytest.mark.parametrize("workers", [0, 33, True])
def test_canonical_history_worker_count_is_bounded(
    tmp_path: Path,
    workers,
) -> None:
    with pytest.raises(
        HistoricalInactiveLifecycleResolutionShadowError,
        match="worker count",
    ):
        module._read_canonical_history(
            tmp_path,
            ANCHOR,
            max_workers=workers,
        )


def test_existing_exact_shadow_is_reused(monkeypatch, tmp_path: Path) -> None:
    data_root, source, output = _fixture(monkeypatch, tmp_path)
    kwargs = {
        "data_root": data_root,
        "source_package_path": source,
        "output_root": output,
        "anchor_date": ANCHOR,
        "materialized_at": MATERIALIZED,
    }
    first = build_historical_inactive_lifecycle_resolution_shadow(**kwargs)
    second = build_historical_inactive_lifecycle_resolution_shadow(**kwargs)

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.manifest_sha256 == second.manifest_sha256


def test_shadow_accepts_explicit_persistent_source_custody(
    monkeypatch, tmp_path: Path
) -> None:
    data_root, source, output = _fixture(monkeypatch, tmp_path)
    custody_root = tmp_path / "persistent-source"
    custody_root.mkdir(mode=0o700)
    retained = custody_root / source.name
    shutil.copytree(source, retained, copy_function=shutil.copy2)

    result = build_historical_inactive_lifecycle_resolution_shadow(
        data_root=data_root,
        source_package_path=retained,
        source_custody_root=custody_root,
        output_root=output,
        anchor_date=ANCHOR,
        materialized_at=MATERIALIZED,
    )

    assert result.manifest.source_package_record_count == 8
    assert dict(result.manifest.disposition_counts)["review_candidate"] == 1


def test_tampered_shadow_fails_formal_reread(monkeypatch, tmp_path: Path) -> None:
    data_root, source, output = _fixture(monkeypatch, tmp_path)
    result = build_historical_inactive_lifecycle_resolution_shadow(
        data_root=data_root,
        source_package_path=source,
        output_root=output,
        anchor_date=ANCHOR,
        materialized_at=MATERIALIZED,
    )
    decision_path = result.partition_path / DECISION_FILE
    decision_path.chmod(0o600)
    with decision_path.open("ab") as handle:
        handle.write(b"tamper")
    decision_path.chmod(0o400)

    with pytest.raises(HistoricalInactiveLifecycleResolutionShadowError):
        read_historical_inactive_lifecycle_resolution_shadow(
            root=output, anchor_date=ANCHOR
        )


def test_review_candidate_contract_rejects_unverified_gate() -> None:
    candidate = _stable_id("FIGI-A")
    with pytest.raises(ValidationError, match="ticker evidence"):
        HistoricalInactiveLifecycleResolutionDecisionV1(
            anchor_date=ANCHOR,
            source_observation_fingerprint="1" * 64,
            source_payload_fingerprint="2" * 64,
            source_page_sequence=1,
            source_row_sequence=1,
            selected_identity_type="share_class_figi",
            selected_identity_value="FIGI-A",
            identity_resolution_status="resolved",
            canonical_instrument_id=candidate,
            canonical_first_observed_date=FIRST,
            canonical_last_observed_date=FIRST,
            effective_date_candidate=date(2026, 7, 15),
            ticker_seen_in_canonical_history=False,
            disposition="review_candidate",
            reason_codes=REVIEW_LIMITATION_CODES,
            source_package_logical_fingerprint="3" * 64,
            canonical_instrument_history_fingerprint="4" * 64,
            evaluated_at=MATERIALIZED,
        )
