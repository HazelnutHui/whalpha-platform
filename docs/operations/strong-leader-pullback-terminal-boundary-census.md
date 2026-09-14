# Strong-Leader Pullback Terminal Boundary Census

## Boundary

This command implements ADR 0253. It rereads the exact registered Membership
paths and formally validates canonical EOD presence for the blocker census's
89 lifecycle stable IDs. It makes no network request, writes nothing to
`/data`, and does not calculate a return or change research, Candidate, site,
deployment, or scheduler state.

Run from a clean source checkout. The output custody root must already be an
owner-only mode-`0700` directory. The named `census=*` target must be absent or
the exact completed object.

```bash
scripts/admin/build-strong-leader-pullback-terminal-boundary-census.sh \
  --data-root /data/trading-intelligence-platform \
  --development-census /tmp/whalpha-strong-leader-pullback-development-census-20260910T032422Z-1f6447110142 \
  --blocker-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census/build=20260913-v1 \
  --blocker-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-boundary-census/census=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-boundary-census \
  --evaluated-at <UTC-ISO-8601> \
  --execute
```

The complete Membership reread is intentionally finite and may take several
minutes. The EOD path uses a presence-only stable-ID projection after full
partition validation, so it does not materialize millions of unrelated market
values as Python objects.

Successful output reports only aggregate counts and fingerprints. Inspect the
owner-only report for per-ID boundary differences. Do not interpret either
date as a terminal outcome.
