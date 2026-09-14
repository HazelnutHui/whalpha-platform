# Strong-Leader Pullback Listed-Consideration Terminal Evidence

This network-disabled operation produces daily gross reference values for the
nine strictly identified listed-stock consideration cases.

Run the repository-aware wrapper with absolute input paths, the canonical EOD
root, owner-only output custody, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-listed-consideration-terminal-evidence.sh \
  --identity-adjudication /absolute/identity/adjudication=... \
  --identity-adjudication-custody-root /absolute/identity \
  --consideration /absolute/consideration/adjudication=... \
  --consideration-custody-root /absolute/consideration \
  --cessation /absolute/cessation/adjudication=... \
  --cessation-custody-root /absolute/cessation \
  --payoff-terms /absolute/payoff-terms/adjudication=... \
  --payoff-terms-custody-root /absolute/payoff-terms \
  --canonical-eod-root /absolute/canonical-data \
  --output-root /absolute/terminal-values/adjudication=... \
  --output-custody-root /absolute/terminal-values \
  --evaluated-at 2026-09-14T04:00:00Z \
  --execute
```

The repository must be clean. All source reports, EOD rows, session-integrity
metadata, point-in-time Identity bindings and any completed output are
formally reread. Exact reruns return `already_present`; a differing report at
the same target fails closed.

The command performs no network request. It does not value an unassigned
security, invent an intraday execution time, adjust or replace the canonical
close, calculate a strategy label or return, write `/data` or Historical
Coverage, admit research, publish, deploy, or change a scheduler.
