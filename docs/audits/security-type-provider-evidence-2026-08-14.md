# Provider Security-Type Evidence Audit: 2026-08-14

- Evidence as-of date: 2026-08-14
- Successful operation time: 2026-08-16 UTC
- Provider: Massive Stocks Basic
- Result: completed provider evidence snapshot

## Controlled Requests

The corrected Phase B1B run made one `/v3/reference/tickers/types` request and 14 point-in-time `/v3/reference/tickers` requests: 15 total, zero retries, no other endpoints. Raw responses and headers were neither printed nor retained.

The preceding failed Phase B1 run used the same request counts. Its old reconciliation incorrectly attached identifier-free excluded `BCPC` and `TPC` observations to resolved instruments by ticker, producing four false ambiguous observations and four canonical evidence conflicts. Phase B1A corrected the identity precedence and denominator before this authorized rerun.

## Publication Integrity

| Dataset | Rows | Content SHA-256 |
| --- | ---: | --- |
| Provider Security Type Catalog | 25 | `48c7106d3e53538159986b6d4a5a18822a4b3c47ae51bcfa0db8423abf19cc0d` |
| Provider Security Observations | 13,110 | `bf19d66846406a8d4b77581a2e4ab385b24bb3755fa07499a7b8b90c958119f4` |
| Canonical Provider Instrument Security Evidence | 9,939 | `d8b7873eae825a2782e23d10b958111f04fb46ee5a77ce279a0404e7610c2568` |

The logical completion fingerprint is `f4ad3b09c5ae605790232b824e1b69208ad3a10571b3b66ea265700114855a12`. Explicit Arrow schemas, deterministic ordering, manifest counts, content fingerprints, Parquet hashes, rereads, logical references, and staging cleanup passed.

## Reconciliation

All 13,110 observations reconcile exactly: 9,939 canonical-mapped plus 3,171 expected-unjoined. Exact duplicates, ambiguous mappings, stable-identifier collisions, malformed observations, and canonical business-key conflicts are all zero. The corrected eligible linkage ratio is 9,939 / 9,939 = 1.0; expected exclusions and unresolved/rejected identities are not linkage-denominator failures.

`BCPC` and `TPC` each retain two distinct observations. The resolved common-share observation joins by Share Class FIGI. The identifier-free `BCPC` structured-product and `TPC` preferred-stock observations remain expected-unjoined and do not enter canonical evidence.

## Provider Type Distribution

The catalog contains 25 codes: ADRC, ADRP, ADRR, ADRW, AGEN, BASKET, BOND, CS, EQLK, ETF, ETN, ETS, ETV, FUND, GDR, IX, LT, NYRS, OS, OTHER, PFD, RIGHT, SP, UNIT, and WARRANT.

The point-in-time observations contain: ADRC 376; CS 5,320; ETF 5,374; ETN 51; ETS 111; ETV 90; FUND 332; PFD 429; RIGHT 122; SP 158; UNIT 306; WARRANT 441. Canonical evidence contains ADRC 372, CS 4,193, and ETF 5,374. Its form distribution is 372 ADR/ADS, 4,193 common shares, and 5,374 fund shares; 5,374 are deterministic ETF exclusions and 4,565 remain quarantine.

Provider type primarily establishes security form. `CS` does not prove an operating issuer or domestic domicile. Catalog codes not yet governed by an explicit rule remain review/quarantine rather than being guessed from descriptions.

## Comparable And Legacy Audit

Across 9,889 comparable instruments, classifications are 5,361 excluded-resolved, one resolved, and 4,527 unknown. Issuer structure is 5,360 ETF, one authoritative closed-end fund, one authoritative operating company, and 4,527 unknown. Candidate Core remains 0 and Candidate Broad remains 1 (AKAN). These are evidence-coverage counts, not estimates of the true listed-equity population.

The unchanged legacy default has 1,864 members: 1,862 quarantine, one authoritative Broad candidate (AKAN), and one authoritative exclusion (VCX). VCX remains the one confirmed legacy-pool contaminant. VXT and BCPC/TPC are absent from the comparable set; AZ is present but remains provider-explicit common-share form with unknown issuer structure and quarantine disposition.

## Production Boundary

The evidence publication does not alter Instrument Master, Provider Identity, Ticker Resolver, EOD bars, or the legacy 1,864 calculations. Core is the accepted future default and Broad the future secondary view, but activation remains deferred pending authoritative issuer-structure and domicile evidence. The production disclosure must therefore remain `Legacy Liquid Screen (Provisional)` with an explicit incomplete-classification warning.
