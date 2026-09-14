# Strong-Leader Pullback Terminal-Population Payoff Policy

## Boundary

This zero-network operation binds the SCS source-local party relation, three
election alternatives, no-valid-election default, and unresolved adjustment
status. It does not value HNI shares or write `/data`.

```bash
scripts/admin/adjudicate-strong-leader-pullback-terminal-population-payoff-policy.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v2 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content/source=20260914-v2 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content \
  --core-adjudication /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication/adjudication=20260914-v1 \
  --core-adjudication-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication \
  --cessation /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication/adjudication=20260914-v1 \
  --cessation-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy/adjudication=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Run from a clean checkout with an existing `0700` output custody root. Verify
all source and upstream hashes, five normalized terms, three alternatives, one
mixed default, exact replay, `0700/0400` modes, and no partial residue. Do not
treat the reference price as a daily terminal market value or the default as
an actual holder election.
