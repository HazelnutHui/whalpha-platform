# Strong-Leader Pullback Terminal-Population SEC Source Plan

## Boundary

This command cross-reads the corrected terminal-gap worklist, retained stable-
ID lifecycle lineage, and the existing SEC Submissions snapshot. It creates a
finite source plan with zero network and does not read SEC User-Agent settings.

Run from a clean canonical Dell checkout. The output custody root must already
exist as a real owner-owned mode-`0700` directory; the `plan=*` target must be
absent or contain the identical completed report.

```bash
scripts/admin/plan-strong-leader-pullback-terminal-population-sec-source.sh \
  --terminal-gap-v2 /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2/census=20260914-v2 \
  --terminal-gap-v2-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2 \
  --lifecycle-shadow /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution/build=five-year-20260912-v1 \
  --lifecycle-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution \
  --lifecycle-anchor 2026-07-16 \
  --lifecycle-anchor 2026-09-03 \
  --submissions-package /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions/snapshot=2026-09-10 \
  --submissions-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions \
  --submissions-census-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions-census/five-year-20260910-v1_1 \
  --source-snapshot-date 2026-09-10 \
  --range-start 2021-08-11 \
  --range-end 2026-09-09 \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v2 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan \
  --planned-at 2026-09-14T06:43:39Z \
  --execute
```

Verify the stable-ID case count, request count, forms, boundary relations,
hashes, owner-only modes, and zero authority counters. Do not download the
URLs manually; a later source-custody command must bind and enforce this plan.
