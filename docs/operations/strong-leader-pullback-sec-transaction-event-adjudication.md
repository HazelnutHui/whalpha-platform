# Strong-Leader Pullback SEC Transaction Event Adjudication

This operation performs network-disabled, typed transaction-completion and
event-date adjudication for the 61 common-equity cases already matched to an
in-window SEC Form 8-K.

Run the repository-aware wrapper with absolute paths to the document plan,
completed source, transaction candidates, cover adjudication, owner-only
output custody, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-sec-transaction-events.sh \
  --plan /absolute/plan/build=... \
  --plan-custody-root /absolute/plan \
  --source /absolute/source/source=... \
  --source-custody-root /absolute/source \
  --transaction /absolute/transaction/extraction=... \
  --transaction-custody-root /absolute/transaction \
  --cover-adjudication /absolute/cover/adjudication=... \
  --cover-adjudication-custody-root /absolute/cover \
  --output-root /absolute/events/adjudication=... \
  --output-custody-root /absolute/events \
  --evaluated-at 2026-09-13T21:30:00Z \
  --execute
```

The repository must be clean, custody must be owned mode `0700`, and a
completed report is immutable. An exact rerun returns `already_present`; a
different report at the same target fails closed.

The command makes no network request and does not adjudicate listing
termination reason, consideration, parties, first/last tradability, lifecycle
facts, terminal outcomes, `/data`, Historical Coverage, research admission,
Candidate, publication, deployment, or scheduler state.
