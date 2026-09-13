# Strong-Leader Pullback SEC Lifecycle Pilot

## Boundary

This network-prohibited operation inventories SEC filing locators for the
frozen 64-case first-strategy lifecycle sample. It reads no credential, makes
no request, and writes only one immutable owner-only report outside `/data`.

Run it only from a clean canonical checkout after formally verifying the
source sample, SEC Submissions package, and matching payload census. The
output custody root must already exist at mode `0700`; the exact `build=*`
target must be absent or bytewise equivalent.

```bash
scripts/admin/pilot-strong-leader-pullback-sec-lifecycle.sh \
  --sample /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample/build=20260913-v1 \
  --sample-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample \
  --submissions-package /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions/snapshot=2026-09-10 \
  --submissions-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions \
  --submissions-census-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions-census/five-year-20260910-v1_1 \
  --source-snapshot-date 2026-09-10 \
  --range-start 2021-08-11 \
  --range-end 2026-09-09 \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-lifecycle-pilot/build=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-lifecycle-pilot \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Successful CLI output is aggregate-only. Individual filing locators remain in
the private report. Verify directory/file modes, report SHA-256 and logical
fingerprint, zero partial targets, and zero authority counters after the run.

The next step is not automatic document ingestion. First use the pilot's
aggregate result to freeze an exact bounded document subset and source-content
contract. Filing metadata must never be promoted directly to last-trade,
delisting reason, successor, consideration, or terminal-return facts.
