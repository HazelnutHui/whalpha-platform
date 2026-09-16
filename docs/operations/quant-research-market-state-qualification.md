# Quant Research Market-State Qualification Operations

## Scope

This runbook executes the outcome-blind Market-State Vector qualification on
the research workstation. It does not fetch data, write `/data`, read returns,
register Campaign Three, select thresholds, publish a model, deploy, or trade.

## Preconditions

1. Use a clean, committed canonical source revision.
2. Reread the exact EOD, reconstructed Membership, development census,
   split-action, split-adjustment, and optional five-year split-extension roots
   through their formal readers.
3. Use a real, non-symlinked, owner-only `0700` output custody directory.
4. Select a new direct child named `report=<bounded-id>` for each execution.
5. Keep the first report unchanged before starting the replay.

## Execution

Run `tip_api.services.quant_research_market_state_qualification_cli` with:

- canonical data root;
- reconstructed Membership shadow root;
- frozen development census root;
- canonical split-action and split-adjustment publication roots;
- the exact committed source revision;
- one new output report root and its custody root; and
- when required for the pre-canonical source window, the private historical
  split candidate root and its custody root.

The runner disables network access, verifies the exact 287-session XNYS
partition, reads the preceding 20 sessions only as warm-up, reconciles every
stable ID once, and emits bounded progress. It reads no factor-return label.

For the second full run, use another new report directory and pass the first
report directory as `--reference-report-root`. A replay mismatch is terminal;
both reports remain retained for diagnosis.

## Verification

1. Reread both reports through the formal persistence reader.
2. Require canonical-byte and logical-identity equality.
3. Confirm external requests, Development outcome reads, `/data` writes, and
   Production writes are all zero.
4. Confirm required limitations and every source identity are present.
5. Record coverage, temporal diagnostics, redundancy, status, and custody in a
   dated audit.
6. If ready, proceed only to finite outcome-blind Campaign Three hypothesis and
   protocol design. If rejected, do not lower gates after seeing the result.
