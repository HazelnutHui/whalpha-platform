# Strong-Leader Pullback Trading Cessation Adjudication

This operation performs a network-disabled comparison of bounded SEC
trading-stop statements and formal canonical EOD observations for the fixed
first-strategy lifecycle sample.

Run the repository-aware wrapper with absolute paths, the approved canonical
EOD root, owner-only output custody, a fixed UTC evaluation time, and
`--execute`:

```bash
scripts/admin/adjudicate-strong-leader-pullback-trading-cessation.sh \
  --source-sample /absolute/sample/build=... \
  --source-sample-custody-root /absolute/sample \
  --form25 /absolute/form25/extraction=... \
  --form25-custody-root /absolute/form25 \
  --termination-reasons /absolute/reasons/adjudication=... \
  --termination-reasons-custody-root /absolute/reasons \
  --party-relations /absolute/parties/adjudication=... \
  --party-relations-custody-root /absolute/parties \
  --eod-root /data/trading-intelligence-platform \
  --output-root /absolute/cessation/adjudication=... \
  --output-custody-root /absolute/cessation \
  --evaluated-at 2026-09-14T12:00:00Z \
  --execute
```

The repository must be clean. Input and output custody are formally reread,
output is immutable, and exact reruns return `already_present`. The reader may
take several minutes because it verifies the selected EOD partitions and their
historical Identity snapshots; the operation is finite and reports the exact
selected-session count.

The command makes no network request and does not write `/data`; infer first
tradability or legal delisting effectiveness; normalize terminal payoff;
assign successor identities; admit research; publish; deploy; or change a
scheduler.
