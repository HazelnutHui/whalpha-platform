# Security Type Classification Audit: 2026-08-14

- Audit date: 2026-08-15
- Phase: Security Type Governance Phase A
- Data access: read-only canonical Instrument Master and 2026-08-13/14 EOD sessions
- Production integration: blocked

## Scope

The audited Instrument Master contains 9,939 records. The two EOD sessions contain 9,889 stable-ID comparable records. The legacy Dashboard default has 1,864 members. No canonical partition, production snapshot, or deployed site was changed.

## Binary Rule Root Cause

Instrument Master V1 only stores `common_stock` or `etf`. The current Dashboard rule treats every comparable `common_stock` as an operating equity, then applies supported exchange, previous close >= USD 5, and previous close-times-volume >= USD 20 million. This produces 4,529 “common” plus 5,360 ETF/ETP records, exactly reconciling to 9,889. Persisted data does not retain enough issuer-structure, domicile, incorporation, or source-type evidence to resolve the 4,529 non-ETF records.

VCX passed because it was stored as `common_stock`; the legacy rule did not test issuer economic structure.

## Reconciliation

| Dimension | Category | Count |
| --- | --- | ---: |
| Security form | fund_share | 5,360 |
| Security form | common_share | 1 |
| Security form | ordinary_share | 1 |
| Security form | unknown | 4,527 |
| Issuer structure | etf | 5,360 |
| Issuer structure | closed_end_fund | 1 |
| Issuer structure | operating_company | 1 |
| Issuer structure | unknown | 4,527 |
| Listing scope | other | 5,360 |
| Listing scope | us_domestic_primary | 1 |
| Listing scope | us_listed_foreign | 1 |
| Listing scope | unknown | 4,527 |
| Classification status | resolved | 1 |
| Classification status | excluded_resolved | 5,361 |
| Classification status | unknown | 4,527 |
| Classification status | ambiguous | 0 |
| Classification status | malformed | 0 |
| Disposition | candidate_core | 0 |
| Disposition | candidate_us_listed_international | 1 |
| Disposition | excluded | 5,361 |
| Disposition | quarantine | 4,527 |

Both required equations reconcile exactly to 9,889.

Evidence grades are authoritative 2, provider-explicit 5,360, heuristic-flag-only 382, insufficient 4,145, and reviewed-override 0. Heuristics only flag names for review and never assign a positive type.

Provider/canonical cross-check: 5,360 canonical ETF records resolve as ETF/excluded; 4,527 canonical common-stock records remain unknown; one common-stock record resolves as an excluded CEF and one as a foreign operating ordinary share.

## Legacy Membership

Within the 1,864 legacy members:

- authoritative: 2
- heuristic-flag-only: 101
- insufficient: 1,761
- confirmed excluded pollution: 1 (VCX)
- broad international candidate: 1 (AKAN)
- quarantine: 1,862

The classified coverage suitable for candidate eligibility is therefore 1 of 1,864; 1,862 members remain unclassified, and one is confirmed excluded. This is too incomplete for production integration.

## Edge Cases

- VCX / Fundrise Innovation Fund, LLC: authoritative SEC material identifies a registered closed-end management investment company. It is `closed_end_fund`, excluded, and cannot enter breadth, movers, or the activity map.
- AKAN / Akanda Corp.: authoritative SEC material identifies an Ontario foreign private issuer with Nasdaq-listed common shares. It is U.S.-listed foreign, not U.S.-domiciled, excluded from Core, and eligible for Broad subject to trading gates.
- VXT: absent from the audited Instrument Master/comparable set; no classification conclusion.
- AZ: present in the legacy default but lacks authoritative persisted classification evidence; unknown/quarantine. No conclusion is inferred from its name.

Evidence references are the [Fundrise SEC filing](https://www.sec.gov/Archives/edgar/data/1867090/000199937126011950/fundrise-ncsra_033126.htm) and the [Akanda SEC prospectus](https://www.sec.gov/Archives/edgar/data/1888014/000110465922034560/tm2129724-11_424b4.htm). No long excerpts are retained.

## Candidate Universes

Candidate A, Core U.S. Domestic Operating Equities, has 0 final members. Candidate B, Broad U.S.-Listed Operating Equities, has 1 final member (AKAN). Both counts are evidence-limited rather than representative market-universe estimates.

Relative to the legacy 1,864, Candidate A removes all 1,864. Candidate B retains AKAN and removes 1,863. The A/B difference is AKAN. This exceeds the production-change stop threshold and is explained by the missing classification evidence, not by an intentional broad market contraction.

Taxonomy fingerprint: `fefa7344f1f0a5a6f5d9201714b5993ad7332c9106345e198cdcf105709a1def`.

Ruleset fingerprint: `d7c2213c6dd8746a33ba087332726894b483466ea8142ec9ea17fb70ce87f8d8`.

## Point-In-Time Capability

The contract supports 2026-08-12/13/14 and later dates through half-open effective periods and stable IDs. The two reviewed overrides begin on 2026-08-12. This Phase A production count audit uses the 2026-08-13/14 comparable pair; it does not backfill current facts into older dates.

## Conclusion

The taxonomy architecture and quarantine policy are accepted. Neither candidate is ready to replace production. Phase B must first obtain or govern authoritative/effective-dated classification evidence, then the user must choose Core or Broad. The existing production Universe remains unchanged.
