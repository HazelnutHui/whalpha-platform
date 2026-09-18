"""Pure offline inventory, strict reuse census, and warning batch planning."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Iterable

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
)
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
    ChinaAshareOfficialEvidencePriorityPlanV1,
)
from tip_api.contracts.china_ashare.v1.official_evidence_reuse import (
    ChinaAshareLocalEvidenceDescriptorV1,
    ChinaAshareLocalEvidenceInventoryV1,
    ChinaAshareLocalEvidenceKind,
    ChinaAshareOfficialEvidenceReuseCensusV1,
    ChinaAshareOfficialEvidenceReuseDecisionV1,
    ChinaAshareReuseDisposition,
    ChinaAshareWarningBatchRequestV1,
    ChinaAshareWarningCaptureStatus,
    ChinaAshareWarningEvidenceBatchManifestV1,
    build_contract,
)
from tip_api.persistence.china_ashare_cninfo_event_evidence import (
    read_cninfo_event_capture,
    read_cninfo_event_plan,
)
from tip_api.persistence.china_ashare_official_event_documents import (
    completed_official_document_ids,
    read_official_event_document_capture,
    read_official_event_document_plan,
)
from tip_api.persistence.china_ashare_official_event_evidence import (
    completed_official_event_query_ids,
    read_official_event_capture,
    read_official_event_evidence_plan,
)


def build_local_official_evidence_inventory(
    *,
    official_event_plan_roots: Iterable[Path] = (),
    official_document_plan_roots: Iterable[Path] = (),
    cninfo_plan_roots: Iterable[Path] = (),
) -> ChinaAshareLocalEvidenceInventoryV1:
    evidence: list[ChinaAshareLocalEvidenceDescriptorV1] = []
    packages: set[str] = set()
    for root in sorted(official_event_plan_roots, key=str):
        plan = read_official_event_evidence_plan(plan_root=root)
        packages.add(plan.logical_fingerprint)
        query_by_id = {item.query_id: item for item in plan.queries}
        for query_id in completed_official_event_query_ids(plan_root=root):
            capture, _ = read_official_event_capture(plan_root=root, query_id=query_id)
            query = query_by_id[query_id]
            fields = set()
            for announcement in capture.announcements:
                fields.update(("document_id", "document_url", "published_at"))
            evidence.append(_descriptor(
                kind=ChinaAshareLocalEvidenceKind.OFFICIAL_SEARCH_CAPTURE,
                authority=ChinaAshareOfficialEvidenceAuthority.SSE,
                package=plan.logical_fingerprint,
                capture=capture.logical_fingerprint,
                source_security_id=query.source_security_id,
                raw_sha256=capture.raw_sha256,
                publication_clock=min((item.disclosed_at for item in capture.announcements), default=None),
                publication_clock_observed=bool(capture.announcements),
                structured_fields=fields,
                parse_status=str(capture.parse_status),
            ))
    for root in sorted(official_document_plan_roots, key=str):
        plan = read_official_event_document_plan(plan_root=root)
        packages.add(plan.logical_fingerprint)
        spec_by_id = {item.document_id: item for item in plan.documents}
        for document_id in completed_official_document_ids(plan_root=root):
            capture, _, _ = read_official_event_document_capture(plan_root=root, document_id=document_id)
            spec = spec_by_id[document_id]
            fields = set()
            starts = []
            ends = []
            for event in capture.risk_warning_events:
                fields.update(("document_id", "document_url", "event_kind", "published_at", "raw_sha256", "warning_subtype"))
                if event.effective_from is not None:
                    fields.add("effective_from")
                    starts.append(event.effective_from)
                if event.effective_to is not None:
                    fields.add("effective_to")
                    ends.append(event.effective_to)
            evidence.append(_descriptor(
                kind=ChinaAshareLocalEvidenceKind.OFFICIAL_DOCUMENT_CAPTURE,
                authority=ChinaAshareOfficialEvidenceAuthority(str(plan.provider)),
                package=plan.logical_fingerprint,
                capture=capture.logical_fingerprint,
                source_security_id=plan.source_security_id,
                raw_sha256=capture.raw_sha256,
                # Existing V1 only records a date and explicitly says clock time is unknown.
                publication_clock=datetime.combine(spec.published_on, time.min, tzinfo=timezone.utc) if capture.risk_warning_events else None,
                publication_clock_observed=False,
                effective_from=min(starts) if starts else None,
                effective_to=max(ends) if ends else None,
                structured_fields=fields,
                parse_status=str(capture.parse_status),
            ))
    for root in sorted(cninfo_plan_roots, key=str):
        plan = read_cninfo_event_plan(plan_root=root)
        packages.add(plan.logical_fingerprint)
        for query_id in _completed_ids(root / "captures", (item.query_id for item in plan.queries)):
            capture, _ = read_cninfo_event_capture(plan_root=root, query_id=query_id)
            fields = set()
            for announcement in capture.announcements:
                fields.update(("document_id", "document_url", "published_at"))
            evidence.append(_descriptor(
                kind=ChinaAshareLocalEvidenceKind.CNINFO_CAPTURE,
                authority=ChinaAshareOfficialEvidenceAuthority.CNINFO,
                package=plan.logical_fingerprint,
                capture=capture.logical_fingerprint,
                source_security_id=plan.source_security_id,
                raw_sha256=capture.raw_sha256,
                publication_clock=min((item.published_at for item in capture.announcements), default=None),
                publication_clock_observed=bool(capture.announcements),
                structured_fields=fields,
                parse_status=str(capture.parse_status),
            ))
    ordered = tuple(sorted(evidence, key=lambda item: item.evidence_id))
    return build_contract(
        ChinaAshareLocalEvidenceInventoryV1,
        source_package_fingerprints=tuple(sorted(packages)),
        evidence=ordered,
        evidence_count=len(ordered),
        positive_evidence_eligible_count=sum(item.positive_evidence_eligible for item in ordered),
    )


def build_reuse_census(
    *,
    priority_plan_package_fingerprint: str,
    priority_plan: ChinaAshareOfficialEvidencePriorityPlanV1,
    inventory: ChinaAshareLocalEvidenceInventoryV1,
) -> ChinaAshareOfficialEvidenceReuseCensusV1:
    by_security: dict[str, list[ChinaAshareLocalEvidenceDescriptorV1]] = {}
    for item in inventory.evidence:
        if item.source_security_id:
            by_security.setdefault(item.source_security_id, []).append(item)
    decisions = []
    for request in sorted(priority_plan.requests, key=lambda item: item.request_id):
        candidates = tuple(by_security.get(request.source_security_id, ()))
        reusable = tuple(item for item in candidates if _strictly_covers(item, request))
        reasons = []
        if reusable:
            reasons.append("strict_official_evidence_complete")
        else:
            if not candidates:
                reasons.append("no_local_official_candidate")
            else:
                if not any(item.exact_security_binding and item.stable_subject_id == request.stable_subject_id for item in candidates):
                    reasons.append("stable_security_binding_missing")
                if not any(item.publication_clock_observed for item in candidates):
                    reasons.append("publication_clock_missing_or_unobserved")
                if not any(item.effective_from is not None and item.effective_to is not None for item in candidates):
                    reasons.append("effective_interval_missing")
                if not any(set(request.expected_fields).issubset(item.structured_fields) for item in candidates):
                    reasons.append("expected_structured_fields_missing")
                reasons.append("network_required_fail_closed")
        decisions.append(ChinaAshareOfficialEvidenceReuseDecisionV1(
            request_id=request.request_id,
            stable_subject_id=request.stable_subject_id,
            source_security_id=request.source_security_id,
            family=request.family,
            purpose=request.purpose,
            disposition=ChinaAshareReuseDisposition.REUSABLE if reusable else ChinaAshareReuseDisposition.NETWORK_REQUIRED,
            candidate_evidence_ids=tuple(sorted(item.evidence_id for item in candidates)),
            reused_evidence_ids=tuple(sorted(item.evidence_id for item in reusable)),
            reason_codes=tuple(sorted(reasons)),
        ))
    counts = {}
    for decision in decisions:
        counts[str(decision.family)] = counts.get(str(decision.family), 0) + 1
    return build_contract(
        ChinaAshareOfficialEvidenceReuseCensusV1,
        input_priority_plan_package_fingerprint=priority_plan_package_fingerprint,
        input_priority_plan_fingerprint=priority_plan.logical_fingerprint,
        local_evidence_inventory_fingerprint=inventory.logical_fingerprint,
        decisions=tuple(decisions),
        request_count=len(decisions),
        reusable_request_count=sum(item.disposition is ChinaAshareReuseDisposition.REUSABLE for item in decisions),
        network_required_request_count=sum(item.disposition is ChinaAshareReuseDisposition.NETWORK_REQUIRED for item in decisions),
        counts_by_family=tuple(sorted(counts.items())),
    )


def build_warning_batch(
    *,
    priority_plan_package_fingerprint: str,
    priority_plan: ChinaAshareOfficialEvidencePriorityPlanV1,
    census: ChinaAshareOfficialEvidenceReuseCensusV1,
) -> ChinaAshareWarningEvidenceBatchManifestV1:
    unresolved = {
        item.request_id for item in census.decisions
        if item.family is ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING
        and item.disposition is ChinaAshareReuseDisposition.NETWORK_REQUIRED
    }
    requests = []
    source = sorted((item for item in priority_plan.requests if item.request_id in unresolved), key=lambda item: item.request_id)
    for ordinal, item in enumerate(source, 1):
        requests.append(ChinaAshareWarningBatchRequestV1(
            ordinal=ordinal,
            request_id=item.request_id,
            stable_subject_id=item.stable_subject_id,
            source_security_id=item.source_security_id,
            authority=ChinaAshareOfficialEvidenceAuthority.SSE if item.source_security_id.startswith("sh.") else ChinaAshareOfficialEvidenceAuthority.CNINFO,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            expected_fields=item.expected_fields,
        ))
    return build_contract(
        ChinaAshareWarningEvidenceBatchManifestV1,
        input_priority_plan_package_fingerprint=priority_plan_package_fingerprint,
        input_reuse_census_fingerprint=census.logical_fingerprint,
        requests=tuple(requests),
    )


def classify_warning_response(*, http_status: int | None, raw_bytes: bytes | None) -> tuple[ChinaAshareWarningCaptureStatus, str | None]:
    if raw_bytes is None:
        return ChinaAshareWarningCaptureStatus.TRANSPORT_BLOCKED, None
    lowered = raw_bytes[:1_048_576].lower()
    for marker in (b"acw_sc__v2", b"document.cookie", b"enable javascript"):
        if marker in lowered:
            return ChinaAshareWarningCaptureStatus.CHALLENGE_BLOCKED, marker.decode()
    if http_status is None or not 200 <= http_status < 300:
        return ChinaAshareWarningCaptureStatus.HTTP_BLOCKED, None
    return ChinaAshareWarningCaptureStatus.CAPTURED_PENDING_ADJUDICATION, None


def _strictly_covers(item, request) -> bool:
    return bool(
        item.positive_evidence_eligible
        and item.stable_subject_id == request.stable_subject_id
        and item.exact_security_binding
        and item.authority in request.candidate_authorities
        and item.publication_clock_observed
        and item.effective_from is not None
        and item.effective_to is not None
        and item.effective_from <= request.effective_from
        and item.effective_to >= request.effective_to
        and set(request.expected_fields).issubset(item.structured_fields)
    )


def _descriptor(*, kind, authority, package, capture, source_security_id, raw_sha256, publication_clock=None, publication_clock_observed=False, effective_from=None, effective_to=None, structured_fields=(), parse_status):
    identity = {
        "kind": str(kind), "authority": str(authority), "package": package,
        "capture": capture, "source_security_id": source_security_id,
    }
    evidence_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ChinaAshareLocalEvidenceDescriptorV1(
        evidence_id=evidence_id, evidence_kind=kind, authority=authority,
        source_package_fingerprint=package, source_capture_fingerprint=capture,
        source_security_id=source_security_id, stable_subject_id=None,
        exact_security_binding=False, raw_sha256=raw_sha256,
        publication_clock=publication_clock,
        publication_clock_observed=publication_clock_observed,
        effective_from=effective_from, effective_to=effective_to,
        structured_fields=tuple(sorted(set(structured_fields))), parse_status=parse_status,
        positive_evidence_eligible=False,
    )


def _completed_ids(root: Path, ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(item for item in ids if (root / item).exists())
