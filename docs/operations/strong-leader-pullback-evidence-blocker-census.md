# Strong-Leader Pullback Evidence Blocker Census

## Boundary

This command builds ADR 0221's outcome-blind action/lifecycle intersection from
already retained Dell evidence. It makes no network request and writes neither
`/data` nor analytics, Candidate, website, deployment, or scheduler state.

Run from a clean source checkout. The output custody root must already exist as
an owner-only mode-`0700` directory, and the named `build=*` target must be
absent or the exact already-completed object.

```bash
scripts/dev/run-project-python.sh -m \
  tip_api.services.strong_leader_pullback_evidence_blocker_census_cli \
  --development-census /tmp/whalpha-strong-leader-pullback-development-census-20260910T032422Z-1f6447110142 \
  --admission-decision /tmp/whalpha-strong-leader-pullback-development-admission-20260910T040933Z-bd358defe390 \
  --resolution-shadow /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-resolution-shadow/build=20260913-v2 \
  --resolution-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-resolution-shadow \
  --unresolved-census /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-unresolved-census/build=20260913-v2 \
  --unresolved-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-unresolved-census \
  --residual-census /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-residual-evidence-census/build=20260913-v1 \
  --residual-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-residual-evidence-census \
  --lifecycle-shadow /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution/build=five-year-20260912-v1 \
  --lifecycle-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution \
  --lifecycle-anchor 2026-07-16 \
  --lifecycle-anchor 2026-09-03 \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census/build=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census \
  --evaluated-at 2026-09-13T00:00:00Z \
  --execute
```

The unresolved-candidate package is validated as an immutable output and bound
to the separately formal-reread Resolution Shadow. This deliberately avoids
repeating the already sealed 1,253-session Resolver scan in every downstream
diagnostic; it does not weaken or replace that census's original full-source
validation.

Successful CLI output is aggregate-only. Inspect the manifest for exact source
bindings, path counts, action identity class, lifecycle crossings, hashes, and
all-zero authority counters. Individual unassigned candidate rows must not be
used as identity assignments.
