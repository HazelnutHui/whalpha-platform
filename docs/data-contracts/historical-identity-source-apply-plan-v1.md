# Historical Identity Source Apply Plan V1

## Purpose and boundary

`historical-identity-source-apply-plan/1.0` is the combined complete-candidate
census and no-write plan for moving normalized historical Identity source
observations from an owner-only `/tmp` root to the fixed Dell `/data` layout.
It has no Apply capability and grants no data, research, publication,
deployment, or scheduler authority.

## Required bindings

The plan binds:

- the validated historical Identity rebuild profile-map fingerprint;
- one ordered summary for every bound session, including profile, row/page
  counts, source and normalized bytes, content/physical/manifest/logical
  fingerprints, and accepted canonical Identity fingerprints;
- exactly two ordered file references per session, mapping immutable candidate
  bytes to the absent canonical target;
- candidate session and file inventory fingerprints;
- complete aggregate counts and date bounds; and
- a fresh whole-`/data` inventory fingerprint.

Plan construction formally reads every candidate partition. The plan reader
then rehashes every referenced source file, verifies owner-read-only custody,
reconciles all paths and aggregates, requires all targets to remain absent, and
requires `/data` to retain the bound pre-state.

## Physical policy

The only target dataset is:

```text
/data/trading-intelligence-platform/market-data/
  provider-identity-reference-observation/
    schema_version=1/provider=massive_stocks_basic/
      as_of_date=YYYY-MM-DD/
        manifest.json
        part-00000.parquet
```

The plan file itself must be a regular `0600` file below `/tmp`, written
atomically without replacement. Candidate directories remain `0700` and files
remain `0400`. Symlinks, extra files, existing targets, or path escape fail
closed.

## Non-authority

`status=ready_for_separate_review` means only that the prospective immutable
copy set is internally reconciled against the observed pre-state. The plan
sets `apply_authorized=false` and records zero canonical writes. A later Apply
uses the separate
[Historical Identity Source Apply V1](historical-identity-source-apply-v1.md)
boundary, including its own reviewed invocation, crash/recovery semantics,
fresh compare-and-swap checks, and post-write formal reread.
