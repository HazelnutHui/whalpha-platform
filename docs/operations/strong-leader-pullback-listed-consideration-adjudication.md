# Strong-Leader Pullback Listed-Consideration Adjudication

This network-disabled operation evaluates the 12 retained 424B3 files against
the exact source plan and terminal-payoff ratios.

```bash
scripts/admin/adjudicate-strong-leader-pullback-listed-consideration.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-source-plan/plan=20260914-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-source-plan \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-listed-consideration-document/source=20260914-v1 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-listed-consideration-document \
  --payoff-terms /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms/adjudication=20260914-v1 \
  --payoff-terms-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-adjudication/adjudication=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-adjudication \
  --evaluated-at 2026-09-14T03:00:00Z \
  --execute
```

Run from a clean canonical checkout. The output and custody roots must be
absolute and owner-only. Exact replay returns `already_present`; changed
content or an altered report at the same target fails closed.

Review resolution counts before opening a residual source task. A matched
identity is not a market value, terminal outcome, return, research admission,
or production result. Never fill a formula-only or wrong-scope case from a
ticker/name match or an inferred price.
