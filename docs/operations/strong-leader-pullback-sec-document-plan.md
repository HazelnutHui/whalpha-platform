# Strong-Leader Pullback SEC Document Plan

## Boundary

This command converts the completed SEC lifecycle metadata pilot into an
immutable 219-request plan. It is network-prohibited and does not load the SEC
User-Agent or write any document.

Run from a clean canonical checkout. The private output custody root must
already exist with mode `0700`; the exact `build=*` target must be absent or an
identical completed plan.

```bash
scripts/admin/plan-strong-leader-pullback-sec-documents.sh \
  --pilot /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-lifecycle-pilot/build=20260913-v1 \
  --pilot-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-lifecycle-pilot \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --planned-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Successful output is aggregate-only. Verify 219 requests, 219 unique URLs, 22
batches, zero authority counters, file modes, hashes, and absence of staging
residue.

Do not use shell loops or ad hoc downloads from the plan. Use the separately
governed [SEC Document Source Custody](strong-leader-pullback-sec-document-source.md)
runner, which preserves exact request sequence, bounded batches, rate and size
limits, source response identity, checkpoint recovery, and formal readback.
