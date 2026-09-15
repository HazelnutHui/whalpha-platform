# Quant Research Factor Qualification V2 Operations

## Scope

This runbook executes the frozen Factor Catalog V2 data/implementation
qualification on Dell. It does not fetch data, construct labels, evaluate
returns, choose parameters, access Validation or Holdout, or publish a model.

## Preconditions

1. Run from a clean, committed canonical revision on Dell.
2. Verify the canonical `/data` root and all source publication roots by their
   existing readers; never alter them.
3. Verify the owner-only output custody directory is a real, non-symlinked
   directory owned by the current user with mode `0700`.
4. Use a new direct child named `report=<bounded-id>` for each retained run.
5. Confirm the protocol and catalog fingerprints match ADR 0279 and ADR 0278.

## Execution

Run the `tip_api.services.quant_research_factor_qualification_v2_cli` module
with the exact canonical data root, Membership shadow root, development census,
canonical split-action publication, canonical split-adjustment publication,
and owner-only output/custody roots.

The runner disables network access, verifies the exact 287-session population,
reads the preceding 126 EOD sessions only as factor warm-up, and logs bounded
progress. It quarantines stock-specific source defects by stable ID and closes
an entire signal session only when the SPY path is defective.

## Verification

1. Reread the report through the formal persistence reader.
2. Confirm all external-request, canonical-write, production-write, outcome-
   read, Validation, Holdout, and activation counts or flags remain zero/false.
3. Record report SHA-256, logical fingerprint, coverage counts, decisions,
   pairwise redundancy, limitations, and terminal status in a dated audit.
4. Execute one full replay to a distinct new report directory.
5. Require identical canonical bytes, SHA-256, and logical fingerprint.

If the replay differs, retain both artifacts, classify the run as rejected,
and do not design an outcome screen. If the status is ready, the next action is
only to register a finite Development screening protocol and append its trials
to a new cumulative ledger version before reading any return.
