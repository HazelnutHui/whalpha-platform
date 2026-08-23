# Dashboard Snapshot V2 Operations

## Safety boundary

The publisher and rollback tools are offline administrator workflows. They do not fetch EOD or provider data. Never run apply while canonical freshness is stale.

```bash
scripts/admin/publish-dashboard-snapshot-v2.sh --help
scripts/admin/rollback-dashboard-snapshot-v2.sh --help
```

Default publication creates only a review candidate under `/tmp`. An approval package additionally requires an explicit persistent `/tmp` output root. Production apply requires all of `--apply`, `--approved-plan`, `--approved-plan-sha256`, and `--expected-current-state-fingerprint`. Bare apply and partial approval arguments return exit code 2.

`--verify-then-link` uses the same approvals and only recovers a completed immutable target left inactive after a confirmed crash boundary. Rollback is independently authorized: dry-run reports the active pointer fingerprint and exact prior release; apply requires that fingerprint through `--expected-active-pointer-fingerprint` and rechecks it under lock.

## Recovery matrix

| Observable state | Meaning | Safe action |
| --- | --- | --- |
| target absent, pointer old/absent | no completed publish | create a new reviewed plan after freshness is restored |
| target completed, pointer old/absent | target rename completed; link did not | formally validate, then separately authorize verify-then-link with the original plan |
| target completed, pointer new | publication active | formal reread; do not replay apply |
| staging only | incomplete operation | fail closed and diagnose; do not treat it as completed |
| malformed/dangling pointer | ambiguous or corrupt active state | fail closed; no compatibility fallback |

OCI packaging must name an explicitly approved immutable release and never discover the newest directory automatically.
