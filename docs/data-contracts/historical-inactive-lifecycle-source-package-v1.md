# Historical Inactive Lifecycle Source Package V1

Contract: `historical-inactive-lifecycle-source-package/1.0`.

This is a temporary, owner-only source-observation package for one exact
historical Massive `active=false` All Tickers anchor. It is not the canonical
Instrument Lifecycle dataset.

## Physical boundary

- exact `anchor=YYYY-MM-DD` package below an owner-only `/tmp` parent;
- up to 100 immutable pages, 100,000 rows, 8 MiB per page, and 512 MiB of
  sanitized page content;
- 1,000 rows per request, at least 15 seconds between requests, no automatic
  retry;
- atomic checkpoint after every page and formal reread before resume;
- exact request-chain, page, byte-size, hash, count, mode, and file-set gates;
- completed `package.json` and `checkpoint.json` plus immutable sanitized page
  documents.

Top-level provider request IDs and pagination URLs are removed. Credential and
Authorization material is rejected recursively. Credential-free cursor
parameters and their hashes are retained inside owner-only custody so an
interrupted package can resume and its request chain can be verified.

## Semantics

Provider result fields remain source observations. In particular,
`delisted_utc` is a candidate effective date and does not by itself prove last
tradable session, terminal reason, merger terms, successor identity, or source
availability time. Every completed package remains
`outcome_reconciliation_only` until a separate normalizer, stable-identity
resolver, evidence policy, canonical Apply, and Historical Coverage pass.

The fetch operation performs no `/data`, canonical, analytics, publication,
deployment, or scheduler write.
