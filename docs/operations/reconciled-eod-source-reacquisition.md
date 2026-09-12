# Reconciled EOD Source Reacquisition

## Purpose

This runbook covers bounded reacquisition of Grouped Daily source packages
that a sealed Reconciled EOD Source Coverage artifact classifies as missing.
It writes only private Dell source custody. It does not write `/data`, build or
apply an edition, run research, publish analytics, deploy the website, or grant
Production authority.

Operational instructions alone do not authorize a provider request.

## Preconditions

1. The unique five-year EOD/Identity writer has stopped.
2. A complete-interval coverage artifact has been built from quiescent
   canonical state and its exact file SHA-256 retained.
3. Every requested date has an exact
   `grouped_daily_source_package_missing` reason. It is either disposition
   `missing` with no other reason, or the narrowly supported disposition
   `invalid` with the additional reason
   `identity_source_custody_unavailable`. The latter closes only the independent
   price-package gap and remains Identity-blocked. Every other invalid or
   conflict date requires separate diagnosis.
4. The repository is clean, and the command uses the project Python wrapper.
5. The package root is exactly
   `/home/hui/.local/state/trading-intelligence-platform/reconciled-eod-source-reacquisition`.

The runner rereads the coverage byte hash, exact canonical EOD and Identity
fingerprints, and same-session Identity-source binding before any request. A
changed canonical binding fails closed.

## Run one bounded batch

Use 1–40 unique ordered dates from the reviewed missing set:

```bash
scripts/dev/run-project-python.sh -m tip_api.services.reconciled_eod_source_reacquisition_cli \
  --data-root /data/trading-intelligence-platform \
  --package-root /home/hui/.local/state/trading-intelligence-platform/reconciled-eod-source-reacquisition \
  --coverage-path <exact-coverage-path> \
  --coverage-file-sha256 <coverage-file-sha256> \
  --session-date <YYYY-MM-DD> \
  --execute
```

Requests are serial and rate-limited. Only transport timeout/unavailable
failures receive the fixed bounded retry sequence. Each completed source
package is immutable, owner-only, credential-free, and formally reread. A
restart reuses a valid completed package without another provider request;
malformed or symlinked custody stops instead of being replaced.

Progress and completion output contain only counts, dates, hashes, provenance,
and bounded failure codes. They must never contain credentials or provider
response bodies.

## Postconditions

After all reviewed gaps are filled, rerun the complete network-free source
coverage census. Candidate construction remains blocked until the new artifact
is `ready_for_candidate_build` with zero missing, invalid, and conflict dates.
Later-observed packages remain visibly classified as `later_reacquisition`.
