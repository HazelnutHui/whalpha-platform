# Strong-Leader Pullback SEC Case Adjudication

This operation performs the first network-disabled, point-in-time field
adjudication over the frozen first-strategy SEC evidence.

Run the repository-aware wrapper with absolute paths to the source sample,
document plan, completed document source, transaction candidates, case
coverage census, owner-only output custody, a fixed UTC evaluation time, and
`--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-sec-cases.sh \
  --source-sample /absolute/sample/build=... \
  --source-sample-custody-root /absolute/sample \
  --plan /absolute/plan/build=... \
  --plan-custody-root /absolute/plan \
  --source /absolute/source/source=... \
  --source-custody-root /absolute/source \
  --transaction /absolute/transaction/extraction=... \
  --transaction-custody-root /absolute/transaction \
  --coverage /absolute/coverage/census=... \
  --coverage-custody-root /absolute/coverage \
  --output-root /absolute/adjudication/adjudication=... \
  --output-custody-root /absolute/adjudication \
  --evaluated-at 2026-09-13T19:00:00Z \
  --execute
```

The repository must be clean, custody must be owned mode `0700`, and a
completed report is immutable. An exact rerun returns `already_present`; a
different report at the same target fails closed.

The command makes no network request and does not authorize a lifecycle fact,
terminal outcome, `/data` write, Historical Coverage write, research
admission, Candidate update, publication, deployment, or scheduler change.
