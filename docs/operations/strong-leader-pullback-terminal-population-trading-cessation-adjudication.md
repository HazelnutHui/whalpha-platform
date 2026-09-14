# Strong-Leader Pullback Terminal-Population Trading Cessation Adjudication

## Boundary

This zero-network operation compares the independently adjudicated SCS Item
3.01 stop boundary with stable-ID canonical EOD presence. It reads `/data` but
cannot modify it or create a terminal outcome.

Run from a clean canonical checkout. The output custody root must already be
owner-only and the exact `adjudication=*` target must be absent or identical.

```bash
scripts/admin/adjudicate-strong-leader-pullback-terminal-population-trading-cessation.sh \
  --core-adjudication /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication/adjudication=20260914-v1 \
  --core-adjudication-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication \
  --eod-root /data/trading-intelligence-platform \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication/adjudication=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify source and completion dates, the prior/final/next EOD presence tuple,
exact hashes, `0700/0400` modes, identical replay, and no partial residue. Keep
the result labeled as a last retained EOD observation, not a legal delisting
date, intraday execution, terminal value, or strategy return.
