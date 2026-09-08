from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import SecretStr

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalDatasetFamily,
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ProviderTickerResolverV1,
    ResolutionMethod,
    ResolutionStatus,
    build_historical_dataset_coverage_evidence,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services import historical_corporate_action_resolution_shadow as module
from tip_api.services.historical_corporate_action_resolution_shadow import (
    HistoricalCorporateActionResolutionShadowError,
    build_historical_corporate_action_resolution_shadow,
    read_historical_corporate_action_resolution_shadow,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    fetch_historical_corporate_action_source_package,
)


START = date(2026, 8, 20)
MISSING = date(2026, 8, 21)
END = date(2026, 8, 22)
OBSERVED_AT = datetime(2026, 9, 1, tzinfo=UTC)
MATERIALIZED_AT = datetime(2026, 9, 2, tzinfo=UTC)
AAA_ID = UUID("11111111-1111-4111-8111-111111111111")


class FixtureTransport:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def get_json(self, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return self.payload


class NoWait:
    def wait_before_request(self) -> None:
        return None


def _config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr("fixture-secret"))


def _instrument(session: date) -> InstrumentMasterV1:
    return InstrumentMasterV1(
        instrument_id=AAA_ID,
        instrument_type=InstrumentType.COMMON_STOCK,
        status=InstrumentStatus.ACTIVE,
        ticker="AAA",
        name="AAA Test",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        figi="FIGIAAA",
        valid_from=START,
        as_of_date=session,
        source=MASSIVE_PROVIDER_ID,
        source_instrument_id="share_class_figi:FIGIAAA",
        ingested_at=OBSERVED_AT,
        quality_status=QualityStatus.VALID,
    )


def _identity(session: date) -> ProviderInstrumentIdentityV1:
    return ProviderInstrumentIdentityV1(
        provider=MASSIVE_PROVIDER_ID,
        as_of_date=session,
        provider_ticker="AAA",
        share_class_figi="FIGIAAA",
        canonical_instrument_id=AAA_ID,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
        valid_from=START,
        ingested_at=OBSERVED_AT,
        quality_status=QualityStatus.VALID,
    )


def _resolver(session: date) -> ProviderTickerResolverV1:
    return ProviderTickerResolverV1(
        provider=MASSIVE_PROVIDER_ID,
        as_of_date=session,
        provider_ticker="AAA",
        canonical_instrument_id=AAA_ID,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI.value,
        source_identity_key="share_class_figi:FIGIAAA",
        ingested_at=OBSERVED_AT,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_reference(root: Path, path: Path) -> HistoricalCoverageFileReferenceV1:
    return HistoricalCoverageFileReferenceV1(
        path=path.relative_to(root).as_posix(),
        physical_sha256=_sha(path),
    )


def _identity_evidence(root: Path) -> Path:
    artifacts = []
    for session in (START, END):
        result = ParquetInstrumentMasterSnapshotRepository(
            root, created_at=OBSERVED_AT
        ).publish_snapshot(
            instruments=(_instrument(session),),
            identities=(_identity(session),),
            resolvers=(_resolver(session),),
            as_of_date=session,
            provider_id=MASSIVE_PROVIDER_ID,
            quality_summary={},
        )
        payload_paths = sorted(
            path
            for partition in (
                result.instrument_partition_path,
                result.identity_partition_path,
                result.resolver_partition_path,
            )
            for path in (
                partition / "manifest.json",
                partition / "part-00000.parquet",
            )
        )
        artifacts.append(
            HistoricalCoverageArtifactEvidenceV1(
                completion_manifest=_file_reference(
                    root, result.snapshot_manifest_path
                ),
                payload_files=tuple(
                    _file_reference(root, path) for path in payload_paths
                ),
                first_session=session,
                last_session=session,
                record_count=1,
                logical_fingerprint=result.snapshot_content_sha256,
            )
        )
    evidence = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
        sessions=(START, END),
        artifacts=tuple(artifacts),
        record_count=2,
        quarantined_record_count=0,
        created_at=OBSERVED_AT,
    )
    return ParquetHistoricalCoverageRepository(root).publish_dataset_evidence(
        evidence
    ).evidence_path


def _split_payloads() -> list[dict[str, object]]:
    return [
        {
            "adjustment_type": "forward_split",
            "execution_date": START.isoformat(),
            "historical_adjustment_factor": 0.5,
            "id": "split-resolved",
            "split_from": 1,
            "split_to": 2,
            "ticker": "AAA",
        },
        {
            "adjustment_type": "reverse_split",
            "execution_date": MISSING.isoformat(),
            "historical_adjustment_factor": 2,
            "id": "split-no-identity-date",
            "split_from": 2,
            "split_to": 1,
            "ticker": "AAA",
        },
    ]


def _dividend_payloads() -> list[dict[str, object]]:
    return [
        {
            "cash_amount": 0.25,
            "currency": "USD",
            "distribution_type": "recurring",
            "ex_dividend_date": END.isoformat(),
            "frequency": 4,
            "id": "dividend-resolved",
            "ticker": "AAA",
        },
        {
            "cash_amount": 0.10,
            "currency": "USD",
            "distribution_type": "special",
            "ex_dividend_date": END.isoformat(),
            "frequency": 0,
            "id": "dividend-unresolved",
            "ticker": "BBB",
        },
    ]


def _source_package(
    tmp_path: Path,
    kind: CorporateActionSourceKind,
    rows: list[dict[str, object]],
) -> Path:
    target = tmp_path / "sources" / f"{kind.value}={START}_{END}"
    fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport({"status": "OK", "results": rows}),  # type: ignore[arg-type]
        action_kind=kind,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=NoWait(),  # type: ignore[arg-type]
        clock=lambda: OBSERVED_AT,
    )
    return target


def _inputs(monkeypatch, tmp_path: Path) -> dict[str, object]:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root)
    return {
        "data_root": data_root,
        "split_source_package_path": _source_package(
            tmp_path, CorporateActionSourceKind.SPLIT, _split_payloads()
        ),
        "dividend_source_package_path": _source_package(
            tmp_path, CorporateActionSourceKind.DIVIDEND, _dividend_payloads()
        ),
        "identity_evidence_path": _identity_evidence(data_root),
        "output_root": tmp_path / "corporate-action-shadow",
        "start_date": START,
        "end_date": END,
        "materialized_at": MATERIALIZED_AT,
    }


def test_builds_exact_event_date_one_to_one_owner_only_shadow(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)

    result = build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]

    assert result.status == "published"
    assert result.manifest.source_record_count == 4
    assert result.manifest.mapped_record_count == 4
    assert result.manifest.identity_session_available_record_count == 3
    assert result.manifest.identity_session_unavailable_record_count == 1
    assert result.manifest.used_identity_session_count == 2
    assert dict(result.manifest.resolution_status_counts) == {
        "resolved": 2,
        "unresolved": 2,
    }
    assert dict(result.manifest.record_status_counts) == {
        "active": 2,
        "quarantined": 2,
    }
    assert dict(result.manifest.quality_flag_counts) == {
        "event_date_identity_unavailable": 1,
        "source_available_time_unavailable": 4,
        "unresolved_ticker": 1,
    }
    by_id = {item.source_action_id: item for item in result.records}
    assert by_id["split-resolved"].instrument_id == AAA_ID
    assert by_id["dividend-resolved"].instrument_id == AAA_ID
    assert "event_date_identity_unavailable" in by_id[
        "split-no-identity-date"
    ].quality_flags
    assert "unresolved_ticker" in by_id["dividend-unresolved"].quality_flags
    assert all(item.ingested_at == MATERIALIZED_AT for item in result.records)
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert not tuple(result.output_root.rglob("*.tmp"))
    assert not tuple(path for path in result.output_root.rglob("*") if path.is_symlink())
    assert all(
        path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o400)
        for path in result.output_root.rglob("*")
    )

    reread = read_historical_corporate_action_resolution_shadow(
        output_root=result.output_root
    )
    assert reread.manifest == result.manifest
    assert reread.records == result.records


def test_all_rows_can_remain_quarantined_when_no_event_date_has_identity(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    all_missing_root = tmp_path / "all-missing"
    all_missing_root.mkdir()
    split_path = _source_package(
        all_missing_root,
        CorporateActionSourceKind.SPLIT,
        [_split_payloads()[1]],
    )
    dividend_path = _source_package(
        all_missing_root,
        CorporateActionSourceKind.DIVIDEND,
        [],
    )
    inputs.update(
        split_source_package_path=split_path,
        dividend_source_package_path=dividend_path,
        output_root=tmp_path / "all-missing-shadow",
    )

    result = build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]

    assert result.manifest.source_record_count == 1
    assert result.manifest.used_identity_session_count == 0
    assert result.manifest.identity_session_unavailable_record_count == 1
    assert dict(result.manifest.resolution_status_counts) == {"unresolved": 1}
    assert result.records[0].record_status.value == "quarantined"


def test_exact_rerun_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    first = build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]
    second = build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]

    assert first.manifest == second.manifest
    assert second.status == "already_present"


def test_unrepresentable_source_row_stops_without_output(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    malformed_target = tmp_path / "malformed" / f"split={START}_{END}"
    fetch_historical_corporate_action_source_package(
        config=_config(),
        transport=FixtureTransport(
            {
                "status": "OK",
                "results": [
                    {
                        "adjustment_type": "unsupported",
                        "execution_date": START.isoformat(),
                        "id": "unsupported",
                        "ticker": "AAA",
                    }
                ],
            }
        ),  # type: ignore[arg-type]
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        package_path=malformed_target,
        rate_limiter=NoWait(),  # type: ignore[arg-type]
        clock=lambda: OBSERVED_AT,
    )
    inputs["split_source_package_path"] = malformed_target

    with pytest.raises(
        HistoricalCorporateActionResolutionShadowError,
        match="preserve every source row",
    ):
        build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]
    assert not Path(inputs["output_root"]).exists()


def test_identity_evidence_tampering_stops_before_shadow(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence_path = Path(inputs["identity_evidence_path"])
    evidence_path.chmod(0o600)
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["record_count"] = 999
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalCorporateActionResolutionShadowError):
        build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]
    assert not Path(inputs["output_root"]).exists()


def test_formal_reader_rejects_partition_tampering(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    result = build_historical_corporate_action_resolution_shadow(**inputs)  # type: ignore[arg-type]
    artifact = result.manifest.artifacts[0]
    parquet = result.output_root / artifact.partition_path / "part-00000.parquet"
    parquet.chmod(0o600)
    parquet.write_bytes(parquet.read_bytes() + b"tamper")
    parquet.chmod(0o400)

    with pytest.raises(HistoricalCorporateActionResolutionShadowError):
        read_historical_corporate_action_resolution_shadow(
            output_root=result.output_root
        )
