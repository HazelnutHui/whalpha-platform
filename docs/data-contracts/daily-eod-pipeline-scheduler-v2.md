# Daily EOD Pipeline Scheduler V2

## Scope

This contract is a repository-only, network-free planning layer. It identifies
one next review boundary; it grants no execution authority.

## Inputs

- timezone-aware observation time;
- the formally completed contiguous canonical EOD session index;
- the existing scheduler-wake plan 1.1 derived from that index; and
- when canonical EOD is current, one complete automation plan 1.4 for that
  latest canonical session, using a deterministic workspace layout.

The automation plan fingerprint is recomputed from every field. Target,
contract, authority, request, and write fields must match the read-only
boundary.

## Pipeline phases

| Phase | Meaning | Permitted proposal |
| --- | --- | --- |
| `canonical_data` | The oldest missing XNYS session still needs Identity/EOD work | Review at most one data transition |
| `offline_pipeline` | Canonical data is current but a governed offline stage is missing | Review at most one offline transition |
| `manual_review` | MI, Snapshot, or bundle/deployment review is ready | Stop for a separate decision |
| `blocked` | Input contradiction or operator diagnosis is required | Stop and surface reasons |

An enabled candidate changes only a ready proposal from review to invocation.
The planner itself still performs zero coordinator calls.

## Persistent workspace layout

```text
<workspace-root>/
  sessions/
    session_date=YYYY-MM-DD/
      market-regime-phase1a/
      market-regime-phase1b/
      opportunity-candidate/
      entry-geometry/
      etf-relationships/
      market-preview/
      strategy-channels/
      market-intelligence/
      market-intelligence-plan.json
      dashboard-snapshot/
      dashboard-snapshot-plan.json
      serving-bundle/
      acquisition-package/
      canonical-apply-plan.json
      candidate-work/
  journal/
  cache/panels/
```

The layout contract only derives paths; it does not create them. Runtime
provisioning, ownership/mode checks, retention, cleanup, and systemd write
allow-listing remain later operations work.

## Explicit exclusions

- No automatic retry or recovery in one process.
- No credential or external-control read.
- No provider or OCI request.
- No canonical `/data` write.
- No MI/Snapshot Apply or OCI deployment authority.
- No claim that stock outcomes are option returns.
