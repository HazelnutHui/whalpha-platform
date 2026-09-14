# Strong-Leader Pullback Terminal Gap Census V4

Run from a clean commit. All inputs are read-only; output is an immutable,
owner-only local evidence package outside `/data`.

```bash
scripts/admin/build-strong-leader-pullback-terminal-gap-census-v4.sh \
  --prior-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3/census=20260914-v3 \
  --prior-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3 \
  --payoff-terms /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms/adjudication=20260914-v1 \
  --payoff-terms-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms \
  --cessation /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-trading-cessation-adjudication/adjudication=20260914-v1 \
  --cessation-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-trading-cessation-adjudication \
  --termination-reasons /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-termination-reason-adjudication/adjudication=20260913-v1 \
  --termination-reasons-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-termination-reason-adjudication \
  --canonical-eod-root /data/trading-intelligence-platform \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4/census=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4 \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Expected result: four added references, 47 documented and 18 remaining
securities. Exact replay must return `already_present`; directory/file modes
must be `0700/0400`; no partial or symlink residue may remain.
