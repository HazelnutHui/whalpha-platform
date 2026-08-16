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

Catalog codes must be unique; raw count must exceed 5,000; identity linkage must reach 99%; stable collisions, mapped business-key conflicts, and ambiguous mappings must be zero; all raw records must reconcile among unique evidence, exact duplicates, ambiguous, unjoined, and malformed categories. Schema, count, fingerprints, reread, and staging cleanup must pass.

Any failure ends the authorized run. It does not permit an automatic second request sequence.

## 2026-08-16 Attempt

The first Phase B1 run stopped before persistence because ambiguous mappings and mapped business-key conflicts were nonzero. Its initial identity-link ratio also used the wrong denominator by treating accepted expected-exclusion identities without canonical IDs as unlinked. The denominator implementation is corrected and tested, but no second live run is authorized by this record.
