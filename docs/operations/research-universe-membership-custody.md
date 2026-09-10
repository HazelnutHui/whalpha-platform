# Research Universe Membership Custody

## Purpose

This procedure stores later-retrieved, reconstructed daily Membership as
durable research evidence without granting it the stronger next-open authority
of signal-eligible Membership. ADR 0197 is authoritative for the separation.

The research family may support coverage, missingness, lineage, and input-
completeness analysis. It may not support signals, outcomes, performance,
validation, holdout, Candidate activation, Production, or web publication
until a separate decision explicitly changes the relevant authority.

## Physical boundary

Research custody is stored only below:

```text
/data/trading-intelligence-platform/market-data/
  research-universe-membership/
    schema_version=1/
      evidence_tier=reconstructed-latest-vintage-v1/
        methodology_version=<version>/
          session_date=<YYYY-MM-DD>/
```

Each completed partition contains exactly:

- `manifest.json` — original complete-cross-section Membership manifest;
- `part-00000.parquet` — original deterministic decisions; and
- `research-custody.json` — marker binding the prior two files and denying
  stronger authorities.

The existing `universe-membership` and `universe-membership-publications`
families remain reserved for signal-eligible next-open evidence.

## Preflight and execution

The source must be a completed owner-controlled temporary candidate tree with
unique `(methodology_version, session_date)` business keys. Preview first:

```bash
scripts/admin/archive-research-universe-membership.sh \
  --data-root /data/trading-intelligence-platform \
  --candidate-root <absolute-temporary-candidate-root> \
  --workspace-root <governed-historical-workspace> \
  --created-at <UTC-timestamp>
```

Execution adds `--execute`. It creates one owner-only per-session plan in the
governed historical workspace, hashes both candidate artifacts, writes a
complete staging directory, writes the research marker last, atomically
renames the directory, and formally rereads every Parquet row. An exact prior
completion is reusable; a conflicting target, changed candidate, duplicate
business key, symlink, or unsafe path is retained as a per-session failure.

Only one canonical `/data` writer may run at a time. Existing EOD/Identity
Apply currently binds the whole-data inventory, so concurrent family writes
correctly trigger its compare-and-swap stop even when target paths do not
overlap.

## Completion and recovery

A batch completes only when:

1. every intended candidate is either newly applied or exactly reused;
2. failed, overwritten, deleted, and external-request counts are zero;
3. each target passes the research canonical reader;
4. a fresh network-disabled five-year census reports research and signal
   evidence separately; and
5. the dated audit, current context, current status, roadmap, and changelog are
   reconciled.

The Apply never overwrites or deletes a completed target. Unexpected staging
residue is not silently removed or promoted; diagnose it against the retained
plan and candidate. A failed session does not invalidate independently
completed sessions, but it remains missing in the five-year census.

## Warm-up boundary

The five-year evaluation interval begins 2021-09-09. The current Membership
methodology requires 20 prior EOD sessions for trailing liquidity, so
2021-08-11 through 2021-09-08 are separate support custody. They never count as
part of the 1,255-session evaluation interval.
