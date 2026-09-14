# Strong-Leader Pullback Terminal Payoff Terms

This network-disabled operation normalizes the exact common-share cash, stock,
CVR, election, and unlisted-unit terms for the fixed first-strategy lifecycle
population.

Run the repository-aware wrapper with absolute input paths, owner-only output
custody, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-terminal-payoff-terms.sh \
  --consideration /absolute/consideration/adjudication=... \
  --consideration-custody-root /absolute/consideration \
  --party-relations /absolute/parties/adjudication=... \
  --party-relations-custody-root /absolute/parties \
  --cessation /absolute/cessation/adjudication=... \
  --cessation-custody-root /absolute/cessation \
  --output-root /absolute/payoff-terms/adjudication=... \
  --output-custody-root /absolute/payoff-terms \
  --evaluated-at 2026-09-14T15:00:00Z \
  --execute
```

The repository must be clean. All inputs and completed output are formally
reread. Exact reruns return `already_present`; a differing report at the same
target fails closed.

The command makes no network request and does not value listed stock, CVRs,
holder elections, or unlisted units; assign global identities; calculate
terminal returns; write `/data` or Historical Coverage; admit research;
publish; deploy; or change a scheduler.
