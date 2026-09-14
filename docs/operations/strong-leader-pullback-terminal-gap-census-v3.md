# Strong-Leader Pullback Terminal Gap Census V3

```bash
scripts/admin/build-strong-leader-pullback-terminal-gap-census-v3.sh \
  --prior-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2/census=20260914-v2 \
  --prior-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2 \
  --listed-reference /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-listed-reference/adjudication=20260914-v1 \
  --listed-reference-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-listed-reference \
  --payoff-policy /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy/adjudication=20260914-v1 \
  --payoff-policy-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3/census=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v3 \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Run from a clean commit with an existing owner-only custody root. Verify that
only SCS changed, resulting counts equal 43 documented/22 remaining securities
and 197 documented/105 remaining five-session paths, exact replay returns
`already_present`, modes are `0700/0400`, and no partial or symlink residue
exists.
