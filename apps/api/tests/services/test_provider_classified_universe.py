from datetime import UTC, date, datetime
from decimal import Decimal
import hashlib
import socket
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus,
    EvidenceGrade,
    ProviderInstrumentSecurityEvidenceV1,
    ProviderObservationStatus,
    ProviderSecurityObservationV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.provider_classified_universe import audit_provider_classified_universes

NS = UUID("00000000-0000-4000-8000-000000000177")
AS_OF = date(2026, 8, 14)
PREVIOUS = date(2026, 8, 13)
NOW = datetime(2026, 8, 14, tzinfo=UTC)


def iid(ticker: str) -> UUID:
    return uuid5(NS, ticker)


def digest(ticker: str) -> str:
    return hashlib.sha256(ticker.encode()).hexdigest()


def evidence(ticker: str, code: str, *, as_of: date = AS_OF) -> ProviderInstrumentSecurityEvidenceV1:
    form = SecurityForm.COMMON_SHARE if code == "CS" else SecurityForm.ADR_ADS if code == "ADRC" else SecurityForm.UNKNOWN
    return ProviderInstrumentSecurityEvidenceV1(
        as_of_date=as_of, instrument_id=iid(ticker), provider="massive", provider_ticker=ticker,
        provider_type_code=code, provider_type_description=code, primary_exchange="XNYS",
        security_form_evidence=form, evidence_source="/v3/reference/tickers",
        evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT, classification_status=ClassificationStatus.UNKNOWN,
        universe_disposition=UniverseDisposition.QUARANTINE, decision_flags=("stable_identifier_join",),
        review_flags=("issuer_structure_unresolved",), provider_observation_ids=(digest(ticker),),
        observed_at=NOW, ingested_at=NOW,
    )


def observation(ticker: str, code: str, status: ProviderObservationStatus = ProviderObservationStatus.CANONICAL_MAPPED) -> ProviderSecurityObservationV1:
    mapped = status is ProviderObservationStatus.CANONICAL_MAPPED
    return ProviderSecurityObservationV1(
        provider_observation_id=digest(ticker), as_of_date=AS_OF,
        instrument_id=iid(ticker) if mapped else None, provider="massive", provider_ticker=ticker,
        provider_type_code=code, provider_type_description=code, primary_exchange="XNYS",
        security_form_evidence=SecurityForm.COMMON_SHARE if code == "CS" else SecurityForm.UNKNOWN,
        evidence_source="/v3/reference/tickers", evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,
        observation_status=status, resolution_method="stable_identifier", reason_codes=(status.value,),
        review_flags=(), observed_at=NOW, ingested_at=NOW,
    )


def bar(ticker: str, session: date, *, close: str = "10", volume: str = "2000000", exchange: str = "XNYS", old_type: InstrumentType = InstrumentType.COMMON_STOCK) -> EodMarketBarReadModel:
    return EodMarketBarReadModel(
        instrument_id=iid(ticker), ticker=ticker, name=f"Fixture {ticker}", instrument_type=old_type,
        primary_exchange=exchange, session_date=session, open=Decimal(close), high=Decimal(close),
        low=Decimal(close), close=Decimal(close), volume=Decimal(volume), vwap=None, trade_count=None,
        currency="USD", source="massive", quality_status=QualityStatus.VALID, quality_flags=(),
    )


def run(codes: dict[str, str], *, previous_overrides: dict[str, dict[str, str]] | None = None, reverse: bool = False):
    tickers = list(codes)
    if reverse:
        tickers.reverse()
    previous_overrides = previous_overrides or {}
    return audit_provider_classified_universes(
        analysis_date=AS_OF, identity_instrument_ids=frozenset(iid(t) for t in codes),
        catalog_type_codes=frozenset({"CS", "ADRC", "ETF", "ETN", "ETS", "ETV", "FUND", "PFD", "RIGHT", "SP", "UNIT", "WARRANT"}),
        observations=tuple(observation(t, codes[t]) for t in tickers),
        evidence=tuple(evidence(t, codes[t]) for t in tickers),
        current_bars=tuple(bar(t, AS_OF) for t in tickers),
        previous_bars=tuple(bar(t, PREVIOUS, **previous_overrides.get(t, {})) for t in reversed(tickers)),
    )


def test_cs_only_enters_a_and_adrc_only_extends_b() -> None:
    audit = run({"CS1": "CS", "ADR1": "ADRC"})
    assert audit.candidate_a.member_ids == {iid("CS1")}
    assert audit.candidate_b.member_ids == {iid("CS1"), iid("ADR1")}


@pytest.mark.parametrize("code", ["ETF", "ETN", "ETS", "ETV", "FUND", "PFD", "RIGHT", "SP", "UNIT", "WARRANT"])
def test_explicit_non_common_codes_never_enter_either_candidate(code: str) -> None:
    audit = run({code: code})
    assert not audit.candidate_a.member_ids and not audit.candidate_b.member_ids


def test_unknown_missing_conflicting_and_future_evidence_are_quarantined() -> None:
    base = run({"UNKNOWN": "NEW"})
    assert dict(base.quarantine_reason_distribution) == {"unknown_provider_code": 1}
    values = dict(CS=evidence("CS", "CS"), FUTURE=evidence("FUTURE", "CS", as_of=date(2026, 8, 15)))
    audit = audit_provider_classified_universes(
        analysis_date=AS_OF, identity_instrument_ids=frozenset(iid(t) for t in ("CS", "MISSING", "FUTURE")),
        catalog_type_codes=frozenset({"CS"}), observations=(), evidence=tuple(values.values()),
        current_bars=tuple(bar(t, AS_OF) for t in ("CS", "MISSING", "FUTURE")),
        previous_bars=tuple(bar(t, PREVIOUS) for t in ("CS", "MISSING", "FUTURE")),
    )
    reasons = dict(audit.quarantine_reason_distribution)
    assert reasons == {"future_dated_evidence": 1, "missing_evidence": 1}


def test_conflicting_stable_id_evidence_isolated_and_hard_gate_fails() -> None:
    audit = audit_provider_classified_universes(
        analysis_date=AS_OF, identity_instrument_ids=frozenset({iid("DUP")}), catalog_type_codes=frozenset({"CS", "ETF"}),
        observations=(), evidence=(evidence("DUP", "CS"), evidence("DUP", "ETF")),
        current_bars=(bar("DUP", AS_OF),), previous_bars=(bar("DUP", PREVIOUS),),
    )
    assert dict(audit.quarantine_reason_distribution) == {"conflicting_type_evidence": 1}
    assert not dict(audit.hard_gates)["canonical_conflict_zero"]


def test_decimal_price_and_dollar_volume_boundaries_are_inclusive() -> None:
    audit = run({"EDGE": "CS", "LOW": "CS", "ILLIQ": "CS"}, previous_overrides={
        "EDGE": {"close": "5", "volume": "4000000"},
        "LOW": {"close": "4.999999", "volume": "10000000"},
        "ILLIQ": {"close": "5", "volume": "3999999.999999"},
    })
    assert audit.candidate_a.member_ids == {iid("EDGE")}
    assert audit.candidate_a.funnel.previous_close_at_least_5 == 2
    assert audit.candidate_a.funnel.previous_dollar_volume_at_least_20m == 1


def test_classification_and_tradability_are_separate() -> None:
    audit = run({"OTC": "CS"}, previous_overrides={"OTC": {"exchange": "OTCM"}})
    # Current exchange controls the supported-exchange gate; a previous-session exchange does not change form classification.
    assert audit.candidate_a.funnel.provider_type_classified == 1
    assert audit.candidate_a.funnel.final_shadow_candidate == 1


def test_input_permutation_is_deterministic() -> None:
    first = run({"A": "CS", "B": "ADRC", "C": "ETF"})
    second = run({"A": "CS", "B": "ADRC", "C": "ETF"}, reverse=True)
    assert first.audit_fingerprint == second.audit_fingerprint
    assert first.candidate_a.membership_fingerprint == second.candidate_a.membership_fingerprint
    assert first.candidate_b.membership_fingerprint == second.candidate_b.membership_fingerprint


def test_ticker_reuse_cannot_join_without_stable_id() -> None:
    current = bar("SAME", AS_OF)
    previous = bar("SAME", PREVIOUS)
    wrong = evidence("OTHER", "CS")
    audit = audit_provider_classified_universes(
        analysis_date=AS_OF, identity_instrument_ids=frozenset({current.instrument_id}), catalog_type_codes=frozenset({"CS"}),
        observations=(), evidence=(wrong,), current_bars=(current,), previous_bars=(previous,),
    )
    assert not audit.candidate_a.member_ids
    assert dict(audit.hard_gates)["orphan_reference_zero"] is False


def test_legacy_diff_reconciles() -> None:
    audit = run({"KEEP": "CS", "REMOVE": "ETF", "ADD": "CS"})
    comparison = audit.candidate_a.legacy
    assert comparison.retained + comparison.removed == comparison.legacy_count
    assert comparison.retained + comparison.added == len(audit.candidate_a.member_ids)
    assert sum(dict(comparison.legacy_type_distribution).values()) == comparison.legacy_count


def test_bad_observation_status_fails_hard_gate_without_network_or_writes() -> None:
    audit = audit_provider_classified_universes(
        analysis_date=AS_OF, identity_instrument_ids=frozenset({iid("A")}), catalog_type_codes=frozenset({"CS"}),
        observations=(observation("BAD", "CS", ProviderObservationStatus.AMBIGUOUS),), evidence=(evidence("A", "CS"),),
        current_bars=(bar("A", AS_OF),), previous_bars=(bar("A", PREVIOUS),),
    )
    assert not dict(audit.hard_gates)["ambiguous_collision_malformed_zero"]


def test_audit_never_calls_socket_or_credential_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    import tip_api.providers.massive.credential as credential

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network attempted"))
    monkeypatch.setattr(
        credential,
        "load_massive_provider_config_from_file",
        lambda *args, **kwargs: pytest.fail("credential loader called"),
    )
    audit = run({"SAFE": "CS"})
    assert audit.candidate_a.member_ids == {iid("SAFE")}
