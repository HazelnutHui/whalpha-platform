from tip_api.providers.massive.security_evidence_identity_audit import audit_identity_reconciliation


def identity(ticker, status, canonical=None, share=None, composite=None, provider_id=None):
    return {
        "provider_ticker": ticker,
        "resolution_status": status,
        "canonical_instrument_id": canonical,
        "share_class_figi": share,
        "composite_figi": composite,
        "provider_instrument_id": provider_id,
    }


def test_offline_identity_audit_reconciles_resolved_and_expected_unjoined() -> None:
    rows = [
        identity("BCPC", "excluded"),
        identity("BCPC", "resolved", "ID1", "S1", "C1"),
        identity("TPC", "excluded"),
        identity("TPC", "resolved", "ID2", "S2", "C2"),
        identity("UNRES", "unresolved"),
        identity("REJECT", "rejected"),
    ]
    resolver = [
        {"provider_ticker": "BCPC", "canonical_instrument_id": "ID1"},
        {"provider_ticker": "TPC", "canonical_instrument_id": "ID2"},
    ]
    audit = audit_identity_reconciliation(rows, resolver)
    assert audit.total_observations == 6
    assert audit.expected_unjoined_count == 4
    assert (audit.linkage_numerator, audit.linkage_denominator, audit.linkage_ratio) == (2, 2, 1.0)
    assert [item.provider_ticker for item in audit.duplicate_ticker_groups] == ["BCPC", "TPC"]
    assert all(item.resolution_statuses == ("excluded", "resolved") for item in audit.duplicate_ticker_groups)
    assert audit.stable_identifier_collision_count == 0
    assert audit.ticker_ambiguity_count == 0
    assert audit.reconciliation_passed


def test_offline_identity_audit_detects_stable_collision_and_ticker_ambiguity() -> None:
    rows = [
        identity("DUP", "resolved", "ID1", "SAME"),
        identity("DUP", "resolved", "ID2", "SAME"),
    ]
    audit = audit_identity_reconciliation(rows, [])
    assert audit.stable_identifier_collision_count == 1
    assert audit.ticker_ambiguity_count == 2
    assert audit.linkage_numerator == 0
    assert audit.linkage_denominator == 2
