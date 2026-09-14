from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import strong_leader_pullback_listed_consideration_source_plan as service


def _inputs() -> tuple[object, object, object, object, dict, dict]:
    payoff = []
    parties = []
    cessation = []
    profiles = {}
    identities = {}
    for sequence, spec in sorted(service._CASE_SPECS.items()):
        target_id = service.UUID(int=sequence)
        party_fingerprint = f"{sequence + 100:064x}"
        cessation_fingerprint = f"{sequence + 200:064x}"
        payoff.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                party_relation_fingerprint=party_fingerprint,
                cessation_fingerprint=cessation_fingerprint,
                terminal_candidate_state=(
                    "listed_security_identity_and_market_value_required"
                ),
                listed_equity_issuer_locator=spec.source_party_literal.split(",")[0],
                logical_fingerprint=f"{sequence + 300:064x}",
            )
        )
        parties.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                logical_fingerprint=party_fingerprint,
                resolution_state="matched",
                listed_equity_consideration=True,
                party_definition_text=f"Prefix {spec.source_party_literal} suffix",
            )
        )
        cessation.append(
            SimpleNamespace(
                request_sequence=sequence,
                instrument_id=target_id,
                logical_fingerprint=cessation_fingerprint,
                resolution_state="matched",
                next_exchange_session=spec.canonical_session,
            )
        )
        profiles[sequence] = service._SubmissionProfile(
            member_sha256=f"{sequence + 400:064x}",
            name=spec.sec_name,
            ticker=spec.sec_ticker,
            exchange=spec.sec_exchange,
        )
        instrument = SimpleNamespace(
            instrument_id=spec.canonical_instrument_id,
            ticker=spec.canonical_ticker,
            name=f"Canonical {spec.canonical_ticker}",
            primary_exchange="XNYS",
            cik=spec.cik,
            figi=f"BBG{sequence:09d}",
            source_instrument_id=f"share_class_figi:BBG{sequence:09d}",
            instrument_type=SimpleNamespace(value="common_stock"),
            quality_status=SimpleNamespace(value="valid"),
        )
        integrity = SimpleNamespace(
            content_fingerprint=f"{sequence + 500:064x}",
            identity_snapshot_date=spec.canonical_session,
            identity_snapshot_fingerprint=f"{sequence + 600:064x}",
        )
        identities[sequence] = (integrity, instrument)
    payoff_result = SimpleNamespace(
        report=SimpleNamespace(
            party_relation_report_sha256="2" * 64,
            party_relation_logical_fingerprint="1" * 64,
            cessation_report_sha256="4" * 64,
            cessation_logical_fingerprint="3" * 64,
            decisions=tuple(payoff),
            logical_fingerprint="5" * 64,
        ),
        report_sha256="6" * 64,
    )
    party_result = SimpleNamespace(
        report=SimpleNamespace(decisions=tuple(parties), logical_fingerprint="1" * 64),
        report_sha256="2" * 64,
    )
    cessation_result = SimpleNamespace(
        report=SimpleNamespace(
            decisions=tuple(cessation), logical_fingerprint="3" * 64
        ),
        report_sha256="4" * 64,
    )
    submissions = SimpleNamespace(
        logical_fingerprint="7" * 64,
        archive_sha256="8" * 64,
    )
    return (
        payoff_result,
        party_result,
        cessation_result,
        submissions,
        profiles,
        identities,
    )


def test_freezes_twelve_source_candidates_without_identity_assignment() -> None:
    payoff, parties, cessation, submissions, profiles, identities = _inputs()

    report = service._build_report(
        payoff_terms=payoff,
        parties=parties,
        cessation=cessation,
        submissions=submissions,
        submissions_manifest_sha256="9" * 64,
        profiles=profiles,
        identities=identities,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 20, tzinfo=UTC),
    )

    assert report.planned_source_document_count == 12
    assert report.proposed_stable_instrument_count == 12
    assert report.source_document_count == 0
    assert report.consideration_security_identity_assignment_count == 0
    assert report.decisions[-1].canonical_ticker == "EQR"
    assert report.decisions[-1].submissions_current_ticker == "VMRK"


def test_reads_exact_registration_rows_from_submissions_members(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "submissions.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for spec in service._CASE_SPECS.values():
            payload = {
                "cik": int(spec.cik),
                "name": spec.sec_name,
                "tickers": [spec.sec_ticker],
                "exchanges": [spec.sec_exchange],
                "filings": {
                    "recent": {
                        "form": [spec.registration_form],
                        "filingDate": [spec.registration_filing_date.isoformat()],
                        "acceptanceDateTime": [
                            spec.registration_acceptance_datetime.isoformat().replace(
                                "+00:00", "Z"
                            )
                        ],
                        "accessionNumber": [spec.registration_accession_number],
                        "primaryDocument": [spec.registration_primary_document],
                    }
                },
            }
            output.writestr(
                f"CIK{spec.cik}.json",
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            )

    profiles = service._read_submission_profiles(archive)

    assert len(profiles) == 12
    assert profiles[218].ticker == "VMRK"


def test_report_is_owner_only_immutable_and_idempotent(tmp_path: Path) -> None:
    payoff, parties, cessation, submissions, profiles, identities = _inputs()
    report = service._build_report(
        payoff_terms=payoff,
        parties=parties,
        cessation=cessation,
        submissions=submissions,
        submissions_manifest_sha256="9" * 64,
        profiles=profiles,
        identities=identities,
        implementation_revision="a" * 40,
        evaluated_at=datetime(2026, 9, 14, 20, tzinfo=UTC),
    )
    custody = tmp_path / "evidence"
    custody.mkdir(mode=0o700)

    first = service._write_report(
        output_root=custody / "plan=fixture",
        output_custody_root=custody,
        report=report,
    )
    second = service._write_report(
        output_root=first.output_root,
        output_custody_root=custody,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert (first.output_root / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_network_is_prohibited() -> None:
    import socket

    with service._network_prohibited(), pytest.raises(
        service.StrongLeaderPullbackListedConsiderationSourcePlanError,
        match="network access is prohibited",
    ):
        socket.socket()
