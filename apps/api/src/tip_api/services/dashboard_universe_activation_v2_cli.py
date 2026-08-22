"""Default-dry-run publisher for immutable Dashboard Universe Activation V2."""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from tip_api.contracts.market_data.v1.dashboard_universe_activation import SecurityTypeCountV1
from tip_api.contracts.market_data.v2.dashboard_universe_activation import DashboardUniverseActivationRecordV2
from tip_api.persistence.parquet.dashboard_universe_activation import PUBLIC_SECONDARY_ID
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    ParquetDashboardUniverseActivationV2Repository,
    active_pointer_path,
    read_active_dashboard_universe_activation,
    read_completed_dashboard_universe_activation_v2,
    read_dashboard_universe_activation_pointer,
    validate_activation_v2_preflight,
    v2_target_path,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.superseding_full_base import (
    REVISION_ID,
    read_completed_superseding_full_base,
    target_path as superseding_target_path,
)
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID


ROOT = Path("/data/trading-intelligence-platform")
SESSION = date(2026, 8, 19)
PREVIOUS_SESSION = date(2026, 8, 18)
EXPECTED_SOURCE = "51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97"
EXPECTED_CURRENT = "f9018502a57dc859c83ce843872c8119b3fb855980cd143a2da8d0a8bbc1e0ca"
EXPECTED_PRIMARY = "c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978"
EXPECTED_SECONDARY = "2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295"


@dataclass(frozen=True, slots=True)
class ActivationV2Plan:
    records: tuple[DashboardUniverseActivationRecordV2, ...]
    source_path: str
    source_fingerprint: str
    reviewed_security_form_fingerprint: str
    legacy_count: int
    legacy_fingerprint: str
    reviewed_override_count: int
    reviewed_security_form_count: int
    activated_at: datetime
    current_fingerprint: str
    pointer_mode: str


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["--help"], ["-h"]):
        print("Usage: publish-dashboard-universe-activation-v2.sh [--apply]")
        return 0
    if args not in ([], ["--apply"]):
        print("only --apply is accepted", file=sys.stderr)
        return 2
    apply = args == ["--apply"]
    plan = _prepare_plan()
    target = v2_target_path(ROOT, SESSION)
    pointer = active_pointer_path(ROOT)
    result = {
        "mode": "apply" if apply else "dry-run",
        "status": "apply_pending" if apply else "dry_run_ready",
        "analysis_session": SESSION.isoformat(),
        "revision_id": REVISION_ID,
        "source_publication_fingerprint": plan.source_fingerprint,
        "source_publication_path": plan.source_path,
        "current_activation_fingerprint": plan.current_fingerprint,
        "pointer_mode": plan.pointer_mode,
        "planned_target": target.relative_to(ROOT).as_posix(),
        "planned_pointer": pointer.relative_to(ROOT).as_posix(),
        "planned_files": [
            (target / "part-00000.parquet").relative_to(ROOT).as_posix(),
            (target / "manifest.json").relative_to(ROOT).as_posix(),
            pointer.relative_to(ROOT).as_posix(),
        ],
        "planned_inventory_change": {"new_files": 3, "modified_files": 0},
        "default_universe_id": CANDIDATE_A_ID,
        "universes": [
            {
                "universe_id": item.universe_id,
                "display_name": item.display_name,
                "member_count": item.member_count,
                "composition": {entry.provider_type_code: entry.count for entry in item.security_type_composition},
                "membership_fingerprint": item.membership_fingerprint,
            }
            for item in plan.records
        ],
        "legacy_rollback": {
            "schema_version": "1.0",
            "logical_content_fingerprint": plan.current_fingerprint,
            "member_count": plan.legacy_count,
            "membership_fingerprint": plan.legacy_fingerprint,
        },
        "apply_invocations": 0 if not apply else 1,
    }
    if not apply:
        print(json.dumps(result, sort_keys=True))
        return 0
    published = ParquetDashboardUniverseActivationV2Repository(ROOT).publish_and_activate(
        records=plan.records,
        source_publication_path=plan.source_path,
        source_publication_fingerprint=plan.source_fingerprint,
        reviewed_security_form_fingerprint=plan.reviewed_security_form_fingerprint,
        legacy_member_count=plan.legacy_count,
        legacy_membership_fingerprint=plan.legacy_fingerprint,
        trailing_window_start=date(2026, 7, 22),
        trailing_window_end=PREVIOUS_SESSION,
        trailing_window_session_count=20,
        reviewed_override_count=plan.reviewed_override_count,
        reviewed_security_form_count=plan.reviewed_security_form_count,
        activated_at=plan.activated_at,
        expected_current_fingerprint=plan.current_fingerprint,
    )
    completed = read_completed_dashboard_universe_activation_v2(ROOT, analysis_session=SESSION, validate_sources=True)
    active = read_active_dashboard_universe_activation(ROOT, analysis_session=SESSION, validate_sources=True)
    if active.manifest.logical_content_fingerprint != completed.manifest.logical_content_fingerprint:
        raise RuntimeError("activation V2 final active reread failed")
    result.update(
        status="completed",
        content_fingerprint=published.content_fingerprint,
        parquet_sha256=published.parquet_sha256,
        logical_content_fingerprint=published.logical_content_fingerprint,
        pointer_content_fingerprint=published.pointer_content_fingerprint,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _prepare_plan() -> ActivationV2Plan:
    validate_activation_v2_preflight(ROOT, SESSION)
    source = read_completed_superseding_full_base(ROOT, analysis_session=SESSION)
    if source.manifest.logical_content_fingerprint != EXPECTED_SOURCE:
        raise RuntimeError("superseding source fingerprint hard gate failed")
    current = read_active_dashboard_universe_activation(ROOT, analysis_session=SESSION, validate_sources=True)
    if current.manifest.logical_content_fingerprint != EXPECTED_CURRENT:
        raise RuntimeError("current Production activation hard gate failed")
    pointer_mode = "v1_compatibility_fallback" if read_dashboard_universe_activation_pointer(ROOT) is None else "explicit_pointer"
    summaries = {item.policy_id: item for item in source.manifest.policies}
    members = {
        FULL_BASE_A_ID: frozenset(item.instrument_id for item in source.memberships if item.policy_id == FULL_BASE_A_ID),
        FULL_BASE_B_ID: frozenset(item.instrument_id for item in source.memberships if item.policy_id == FULL_BASE_B_ID),
    }
    composition = {
        policy: Counter(item.provider_type_code for item in source.memberships if item.policy_id == policy)
        for policy in (FULL_BASE_A_ID, FULL_BASE_B_ID)
    }
    current_eod = CanonicalEodReadRepository(ROOT).inspect_session(SESSION)
    previous_eod = CanonicalEodReadRepository(ROOT).inspect_session(PREVIOUS_SESSION)
    activated_at = datetime.now(UTC)
    definitions = (
        (
            CANDIDATE_A_ID,
            FULL_BASE_A_ID,
            "Common Shares",
            "Provider-Classified Common Shares (Provisional)",
            "Provider-classified common shares passing price, 20-session median dollar-volume, history, reviewed security-form, and eligibility rules.",
            True,
        ),
        (
            PUBLIC_SECONDARY_ID,
            FULL_BASE_B_ID,
            "Common Shares + ADRs",
            "Provider-Classified Common Shares + ADRs",
            "Adds qualifying American Depositary Receipts under the same quantitative and reviewed eligibility rules.",
            False,
        ),
    )
    records = []
    for public_id, policy_id, short_name, long_name, description, is_default in definitions:
        summary = summaries[policy_id]
        if len(members[policy_id]) != summary.final_count:
            raise RuntimeError("superseding membership count mismatch")
        records.append(
            DashboardUniverseActivationRecordV2(
                activation_id=uuid5(NAMESPACE_URL, f"tip:dashboard-universe-activation-v2:{REVISION_ID}:{SESSION}:{public_id}"),
                analysis_session=SESSION,
                membership_evidence_as_of=source.manifest.membership_evidence_as_of_date,
                activated_at=activated_at,
                universe_id=public_id,
                display_name=short_name,
                long_display_name=long_name,
                description=description,
                is_default=is_default,
                member_count=summary.final_count,
                security_type_composition=tuple(
                    SecurityTypeCountV1(provider_type_code=code, count=count)
                    for code, count in sorted(composition[policy_id].items())
                ),
                membership_fingerprint=summary.membership_fingerprint,
                source_publication_fingerprint=source.manifest.logical_content_fingerprint,
                trailing_liquidity_source_fingerprint=source.manifest.metric_dataset.content_fingerprint,
                reviewed_security_form_fingerprint=source.manifest.reviewed_security_form_dataset.content_fingerprint,
                current_eod_fingerprint=current_eod.content_fingerprint,
                previous_eod_fingerprint=previous_eod.content_fingerprint,
                legacy_rollback_reference=f"market-data/snapshots/dashboard-universe-activation/analysis_session={SESSION.isoformat()}",
                limitations=(
                    "provider security form does not prove issuer domicile",
                    "issuer structure remains incompletely verified",
                    "adjustment factors unverified",
                    "close times volume is a proxy, not fund flow",
                ),
            )
        )
    records_tuple = tuple(records)
    primary, secondary = records_tuple
    if primary.member_count != 1718 or dict((x.provider_type_code, x.count) for x in primary.security_type_composition) != {"CS": 1718} or primary.membership_fingerprint != EXPECTED_PRIMARY:
        raise RuntimeError("Activation V2 Primary hard gate failed")
    if secondary.member_count != 1831 or dict((x.provider_type_code, x.count) for x in secondary.security_type_composition) != {"ADRC": 113, "CS": 1718} or secondary.membership_fingerprint != EXPECTED_SECONDARY:
        raise RuntimeError("Activation V2 Secondary hard gate failed")
    if members[FULL_BASE_A_ID] - members[FULL_BASE_B_ID]:
        raise RuntimeError("Activation V2 Primary subset hard gate failed")
    secondary_types = {item.instrument_id: item.provider_type_code for item in source.memberships if item.policy_id == FULL_BASE_B_ID}
    if any(secondary_types[item] != "ADRC" for item in members[FULL_BASE_B_ID] - members[FULL_BASE_A_ID]):
        raise RuntimeError("Activation V2 Secondary type hard gate failed")
    return ActivationV2Plan(
        records=records_tuple,
        source_path=superseding_target_path(ROOT, SESSION).relative_to(ROOT).as_posix(),
        source_fingerprint=source.manifest.logical_content_fingerprint,
        reviewed_security_form_fingerprint=source.manifest.reviewed_security_form_dataset.content_fingerprint,
        legacy_count=current.manifest.legacy_member_count,
        legacy_fingerprint=current.manifest.legacy_membership_fingerprint,
        reviewed_override_count=current.manifest.reviewed_override_count,
        reviewed_security_form_count=source.manifest.reviewed_security_form_dataset.record_count,
        activated_at=activated_at,
        current_fingerprint=current.manifest.logical_content_fingerprint,
        pointer_mode=pointer_mode,
    )


if __name__ == "__main__":
    raise SystemExit(main())
