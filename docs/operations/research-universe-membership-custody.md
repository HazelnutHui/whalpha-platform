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

For a rolling five-year continuation, use the dedicated resumable builder
before the archive preview. It freezes one owner-read-only plan, separates
source-unavailable dates, groups only adjacent sessions in batches of at most
five, and uses at most four Dell worker processes. Every worker has network
access disabled and writes only a disjoint `/tmp` batch root. `--batch-limit`
supports a bounded pilot and safe continuation with the same plan:

```bash
scripts/dev/run-project-python.sh \
  -m tip_api.services.five_year_research_membership_continuation_cli \
  --data-root /data/trading-intelligence-platform \
  --candidate-root <absolute-owner-only-/tmp-root> \
  --catalog-as-of-date <catalog-date> \
  --evaluated-at <frozen-UTC-timestamp> \
  --code-revision <40-character-commit> \
  --workers 4 \
  --batch-limit <optional-positive-count> \
  --execute
```

The candidate remains reconstructed latest-vintage evidence. Completing this
builder or its archive never grants signal, validation, holdout, performance,
Candidate, Production, or web authority.

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

ADR 0206 supersedes the earlier fixed-window wording. With canonical EOD ending
2026-09-11, the active rolling source target is 1,255 XNYS sessions from
2021-09-13 through 2026-09-11. Its first 20 sessions, through 2021-10-08, are
outcome-free feature warm-up; the earliest eligible signal/performance session
for a 20-session strategy is 2021-10-11. No unavailable pre-window history is
silently projected into the target.
