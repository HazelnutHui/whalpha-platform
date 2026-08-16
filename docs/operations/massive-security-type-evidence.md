# Massive Security-Type Evidence Operation

## Scope

The bounded operation calls `/v3/reference/tickers/types` once and `/v3/reference/tickers` for one approved as-of date with at most 15 pages. Total requests cannot exceed 16. It uses one 15-second limiter, no concurrency, and no retry.

```bash
scripts/admin/ingest-massive-security-type-evidence.sh \
  --as-of-date 2026-08-14 \
  --data-root /data/trading-intelligence-platform
```

The operator must first verify accepted identity partitions, absent evidence targets/staging, and credential metadata. Credential content must never be sourced or printed.

## Hard Gates

Catalog codes must be unique; raw count must exceed 5,000; canonical-eligible identity linkage must reach 99.9%; stable collisions, canonical business-key conflicts, and ambiguous mappings must be zero. All raw records must reconcile among canonical-mapped observations, expected-unjoined observations, exact duplicates, ambiguous, collision, and malformed categories. Schema, count, fingerprints, reread, logical completion, and staging cleanup must pass.

Any failure ends the authorized run. It does not permit an automatic second request sequence.

## 2026-08-16 Attempt

The first Phase B1 run reached both authorized endpoints successfully and stopped before persistence because four observations were marked ambiguous and the old canonical business key conflicted. Its initial identity-link ratio also used all 13,110 observations as the denominator, incorrectly treating expected exclusions and unresolved/rejected identities as canonical-link failures.

Phase B1A proved that `BCPC` and `TPC` each contain one resolved observation with Share Class FIGI and one identifier-free excluded observation. The old ticker fallback attached each excluded observation to the resolved instrument, then marked both observations in each group conflicting. The corrected result is 9,939 canonical-mapped, 3,171 expected-unjoined, zero ambiguity/collision, and a canonical linkage ratio of 9,939/9,939.

## 2026-08-16 Corrected Run

The separately authorized Phase B1B run made 15 requests and zero retries. It published a 25-code catalog, 13,110 normalized observations, 9,939 canonical evidence records, and one logical completion marker. Reconciliation was 9,939 canonical-mapped plus 3,171 expected-unjoined, with zero ambiguity, collision, malformed record, exact duplicate, or canonical conflict; linkage was 9,939/9,939.

Any future failure writes a sanitized diagnostic, including failures before reconciliation. Diagnostic status is always `failed`, is physically separate from completed evidence, represents unavailable statistics as null, and cannot authorize retry.
