# Strong-Leader Pullback Fixed-Cash Terminal Evidence

This network-disabled operation documents gross nominal cash for the bounded
fixed-cash cases whose cessation timing is already matched.

Run the repository-aware wrapper with absolute input paths, owner-only output
custody, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-fixed-cash-terminal-evidence.sh \
  --consideration /absolute/consideration/adjudication=... \
  --consideration-custody-root /absolute/consideration \
  --cessation /absolute/cessation/adjudication=... \
  --cessation-custody-root /absolute/cessation \
  --payoff-terms /absolute/payoff-terms/adjudication=... \
  --payoff-terms-custody-root /absolute/payoff-terms \
  --output-root /absolute/terminal-cash/adjudication=... \
  --output-custody-root /absolute/terminal-cash \
  --evaluated-at 2026-09-14T18:00:00Z \
  --execute
```

The repository must be clean. All inputs and the completed output are
formally reread. Exact reruns return `already_present`; a differing report at
the same target fails closed.

The command makes no network request. It does not infer an intraday effective
time; value stock, CVRs, elections, or unlisted units; calculate a strategy
label or return; write `/data` or Historical Coverage; admit research;
publish; deploy; or change a scheduler.
