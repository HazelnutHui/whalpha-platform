"""Freeze a survivorship-reduced SSE/SZSE five-year source population."""

from __future__ import annotations

import json
from datetime import date, datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAshareBaoStockBasicRecordV1,
    ChinaAshareFiveYearPopulationReportV1,
    ChinaAshareOfficialPopulationSourceKind,
    ChinaAsharePopulationDisposition,
    ChinaAsharePopulationOccurrenceV1,
    baostock_basic_set_fingerprint,
    build_five_year_population_report,
    build_population_occurrence,
    official_population_row_fingerprint,
    population_occurrence_set_fingerprint,
)
from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    ChinaAshareIdentityLifecyclePackageResultV1,
)


def build_five_year_population(
    *,
    identity_lifecycle_package: ChinaAshareIdentityLifecyclePackageResultV1,
    baostock_basic_records: tuple[ChinaAshareBaoStockBasicRecordV1, ...],
    interval_start: date,
    interval_end: date,
    evaluated_at: datetime,
) -> tuple[
    tuple[ChinaAsharePopulationOccurrenceV1, ...],
    ChinaAshareFiveYearPopulationReportV1,
]:
    if interval_end < interval_start:
        raise ValueError("population interval is reversed")
    official_rows = _official_rows(identity_lifecycle_package)
    basic = {item.source_security_id: item for item in baostock_basic_records}
    if len(basic) != len(baostock_basic_records):
        raise ValueError("BaoStock security-basic rows are duplicated")
    occurrences = []
    for row in official_rows:
        source_id = row["source_security_id"]
        provider = basic.get(source_id)
        reasons = {"exact_official_source_row_retained"}
        in_interval = row["listing_date"] <= interval_end and (
            row["official_delist_date"] is None
            or row["official_delist_date"] >= interval_start
        )
        if not in_interval:
            disposition = ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
            reasons.add("listed_occurrence_outside_target_interval")
        elif not row["official_a_share_proven"] and not row[
            "requires_baostock_a_share_crosscheck"
        ]:
            disposition = ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
            reasons.add("official_row_is_not_a_share")
        elif row["requires_baostock_a_share_crosscheck"] and provider is None:
            disposition = ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
            reasons.add("a_share_security_form_not_crosschecked")
        elif provider is None:
            disposition = ChinaAsharePopulationDisposition.QUARANTINED
            reasons.add("baostock_security_basic_missing")
        elif row["board"] is ChinaAshareBoard.UNKNOWN:
            disposition = ChinaAsharePopulationDisposition.QUARANTINED
            reasons.add("official_board_evidence_missing")
        else:
            disposition = ChinaAsharePopulationDisposition.RESOLVED
            reasons.update(
                (
                    "a_share_common_stock_crosschecked",
                    "official_board_and_listing_date_primary",
                    "stable_listed_occurrence_resolved",
                )
            )
        if provider is not None:
            reasons.add("baostock_security_basic_crosschecked")
            if provider.listing_date != row["listing_date"]:
                reasons.add("cross_source_listing_date_conflict_official_primary")
            if (
                row["official_delist_date"] is not None
                and provider.out_date is not None
                and provider.out_date != row["official_delist_date"]
            ):
                reasons.add("provider_last_date_differs_from_official_delist_date")
        occurrences.append(
            build_population_occurrence(
                source_security_id=source_id,
                current_or_terminal_name=row["name"],
                exchange=row["exchange"],
                board=row["board"],
                listing_date=row["listing_date"],
                official_delist_date=row["official_delist_date"],
                baostock_out_date=None if provider is None else provider.out_date,
                official_source_kind=row["source_kind"],
                official_source_fingerprint=row["source_fingerprint"],
                baostock_basic_fingerprint=(
                    None if provider is None else provider.logical_fingerprint
                ),
                disposition=disposition,
                reason_codes=tuple(sorted(reasons)),
            )
        )
    ordered = tuple(
        sorted(
            occurrences,
            key=lambda item: (
                item.source_security_id,
                item.listing_date,
                item.official_source_kind.value,
            ),
        )
    )
    keys = tuple(
        (item.source_security_id, item.listing_date, item.official_source_kind.value)
        for item in ordered
    )
    if keys != tuple(sorted(set(keys))):
        raise ValueError("official population occurrences are duplicated")
    resolved = tuple(
        item
        for item in ordered
        if item.disposition is ChinaAsharePopulationDisposition.RESOLVED
    )
    quarantined = tuple(
        item
        for item in ordered
        if item.disposition is ChinaAsharePopulationDisposition.QUARANTINED
    )
    outside = tuple(
        item
        for item in ordered
        if item.disposition is ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
    )
    current_kinds = {
        ChinaAshareOfficialPopulationSourceKind.SSE_MAIN_CURRENT,
        ChinaAshareOfficialPopulationSourceKind.SSE_STAR_CURRENT,
        ChinaAshareOfficialPopulationSourceKind.SZSE_A_CURRENT,
    }
    report = build_five_year_population_report(
        evaluated_at=evaluated_at,
        interval_start=interval_start,
        interval_end=interval_end,
        official_identity_package_fingerprint=(
            identity_lifecycle_package.manifest.logical_fingerprint
        ),
        baostock_basic_set_fingerprint=baostock_basic_set_fingerprint(
            baostock_basic_records
        ),
        official_candidate_count=len(ordered),
        expansion_target_count=len(resolved) + len(quarantined),
        resolved_count=len(resolved),
        quarantined_count=len(quarantined),
        outside_scope_count=len(outside),
        current_resolved_count=sum(
            item.official_source_kind in current_kinds for item in resolved
        ),
        delisted_resolved_count=sum(
            item.official_source_kind not in current_kinds for item in resolved
        ),
        cross_source_listing_date_conflict_count=sum(
            "cross_source_listing_date_conflict_official_primary"
            in item.reason_codes
            for item in ordered
        ),
        unresolved_board_count=sum(
            "official_board_evidence_missing" in item.reason_codes for item in ordered
        ),
        occurrence_set_fingerprint=population_occurrence_set_fingerprint(ordered),
        population_frozen=bool(resolved or quarantined),
        full_market_expansion_authorized=bool(resolved or quarantined),
        reason_codes=(
            "bounded_five_year_sse_szse_population",
            "current_and_delisted_official_rows_retained",
            "later_retrieved_population_not_as_operated",
            "quarantined_occurrences_remain_capture_targets",
            "research_backtest_not_authorized",
        ),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    return ordered, report


def _official_rows(
    package: ChinaAshareIdentityLifecyclePackageResultV1,
) -> tuple[dict[str, Any], ...]:
    by_kind = {
        item.artifact_kind: package.package_path / PurePosixPath(item.relative_path)
        for item in package.manifest.raw_artifacts
    }
    rows = []
    for kind, exchange, board in (
        (
            ChinaAshareOfficialPopulationSourceKind.SSE_MAIN_CURRENT,
            ChinaAshareExchange.SSE,
            ChinaAshareBoard.SSE_MAIN,
        ),
        (
            ChinaAshareOfficialPopulationSourceKind.SSE_STAR_CURRENT,
            ChinaAshareExchange.SSE,
            ChinaAshareBoard.STAR,
        ),
    ):
        document = json.loads(by_kind[kind.value].read_bytes())
        for raw in document["result"]:
            code = _code(raw.get("A_STOCK_CODE"))
            if not code:
                continue
            rows.append(
                _row(
                    source_security_id=f"sh.{code}",
                    name=str(raw.get("SEC_NAME_CN") or raw.get("COMPANY_ABBR") or "").strip(),
                    exchange=exchange,
                    board=board,
                    listing_date=_date(raw.get("LIST_DATE")),
                    official_delist_date=None,
                    source_kind=kind,
                    official_a_share_proven=True,
                    requires_baostock_a_share_crosscheck=False,
                    raw=raw,
                )
            )
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pandas is required for official population evidence") from exc
    current = pd.read_excel(BytesIO(by_kind["szse_a_current"].read_bytes()))
    for raw in current.to_dict(orient="records"):
        code = _code(raw.get("A股代码"))
        if not code:
            continue
        board = {
            "主板": ChinaAshareBoard.SZSE_MAIN,
            "创业板": ChinaAshareBoard.CHINEXT,
        }.get(str(raw.get("板块") or "").strip(), ChinaAshareBoard.UNKNOWN)
        rows.append(
            _row(
                source_security_id=f"sz.{code}",
                name=str(raw.get("A股简称") or "").strip(),
                exchange=ChinaAshareExchange.SZSE,
                board=board,
                listing_date=_date(raw.get("A股上市日期")),
                official_delist_date=None,
                source_kind=ChinaAshareOfficialPopulationSourceKind.SZSE_A_CURRENT,
                official_a_share_proven=True,
                requires_baostock_a_share_crosscheck=False,
                raw=raw,
            )
        )
    document = json.loads(by_kind["sse_delist"].read_bytes())
    for raw in document["result"]:
        stock_type = str(raw.get("STOCK_TYPE") or "").strip()
        a_share = stock_type in {"1", "8"}
        code = _code(
            raw.get("A_STOCK_CODE") if a_share else raw.get("B_STOCK_CODE")
        )
        if not code:
            continue
        board = {
            "1": ChinaAshareBoard.SSE_MAIN,
            "2": ChinaAshareBoard.STAR,
        }.get(str(raw.get("LIST_BOARD") or "").strip(), ChinaAshareBoard.UNKNOWN)
        if not a_share:
            board = ChinaAshareBoard.UNKNOWN
        rows.append(
            _row(
                source_security_id=f"sh.{code}",
                name=str(raw.get("COMPANY_ABBR") or raw.get("SEC_NAME_CN") or "").strip(),
                exchange=ChinaAshareExchange.SSE,
                board=board,
                listing_date=_date(raw.get("LIST_DATE")),
                official_delist_date=_date(raw.get("DELIST_DATE")),
                source_kind=ChinaAshareOfficialPopulationSourceKind.SSE_DELIST,
                official_a_share_proven=a_share,
                requires_baostock_a_share_crosscheck=False,
                raw=raw,
            )
        )
    terminal = pd.read_excel(BytesIO(by_kind["szse_delist"].read_bytes()))
    for raw in terminal.to_dict(orient="records"):
        code = _code(raw.get("证券代码"))
        if not code:
            continue
        rows.append(
            _row(
                source_security_id=f"sz.{code}",
                name=str(raw.get("证券简称") or "").strip(),
                exchange=ChinaAshareExchange.SZSE,
                board=ChinaAshareBoard.UNKNOWN,
                listing_date=_date(raw.get("上市日期")),
                official_delist_date=_date(raw.get("终止上市日期")),
                source_kind=ChinaAshareOfficialPopulationSourceKind.SZSE_DELIST,
                official_a_share_proven=False,
                requires_baostock_a_share_crosscheck=True,
                raw=raw,
            )
        )
    return tuple(rows)


def _row(**values: Any) -> dict[str, Any]:
    raw = values.pop("raw")
    normalized = {
        "board": values["board"].value,
        "exchange": values["exchange"].value,
        "listing_date": values["listing_date"].isoformat(),
        "name": values["name"],
        "official_delist_date": (
            None
            if values["official_delist_date"] is None
            else values["official_delist_date"].isoformat()
        ),
        "source_kind": values["source_kind"].value,
        "official_a_share_proven": values["official_a_share_proven"],
        "source_security_id": values["source_security_id"],
        "source_row": {str(key): _json_value(value) for key, value in raw.items()},
    }
    return {
        **values,
        "source_fingerprint": official_population_row_fingerprint(normalized),
    }


def _code(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().split(".", 1)[0]
    if not text or text.lower() in {"nan", "none"}:
        return ""
    normalized = text.zfill(6)
    if len(normalized) != 6 or not normalized.isdigit():
        raise ValueError("official population security code is invalid")
    return normalized


def _date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    compact = text.split(".", 1)[0].replace("-", "")[:8]
    if len(compact) != 8 or not compact.isdigit():
        raise ValueError("official population date is invalid")
    return datetime.strptime(compact, "%Y%m%d").date()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    return None if text.lower() in {"nan", "nat", "none"} else text
