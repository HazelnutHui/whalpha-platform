# Strong-Leader Pullback SEC Party Relation Adjudication

This operation performs network-disabled source-party relation adjudication for
the 61 typed first-strategy transaction cases.

Run the repository-aware wrapper with absolute paths to all prerequisite
packages, owner-only output custody, a fixed UTC evaluation time, and
`--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-sec-party-relations.sh \
  --plan /absolute/plan/build=... \
  --plan-custody-root /absolute/plan \
  --source /absolute/source/source=... \
  --source-custody-root /absolute/source \
  --cover-adjudication /absolute/cover/adjudication=... \
  --cover-adjudication-custody-root /absolute/cover \
  --transaction-events /absolute/events/adjudication=... \
  --transaction-events-custody-root /absolute/events \
  --termination-reasons /absolute/reasons/adjudication=... \
  --termination-reasons-custody-root /absolute/reasons \
  --consideration /absolute/consideration/adjudication=... \
  --consideration-custody-root /absolute/consideration \
  --output-root /absolute/party-relations/adjudication=... \
  --output-custody-root /absolute/party-relations \
  --evaluated-at 2026-09-14T01:00:00Z \
  --execute
```

The repository must be clean, custody must be owned mode `0700`, and a
completed report is immutable. An exact rerun returns `already_present`; a
different report at the same target fails closed.

The command makes no network request and does not assign global counterparty,
successor, or consideration-issuer IDs; infer tradability; calculate terminal
outcomes; write `/data` or Historical Coverage; admit research; publish;
deploy; or change schedulers.
