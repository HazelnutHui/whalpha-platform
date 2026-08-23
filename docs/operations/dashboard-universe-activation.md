# Dashboard Universe Activation Operation

1. Verify the workstation identity, clean Git tree, formal trailing-liquidity/review inputs, target absence, and canonical protected inventory.
2. Run `scripts/admin/publish-dashboard-universe-activation.sh` without arguments. Dry-run must exit 0 and write nothing.
3. Run the script once with `--apply`. The command must publish both activation partitions, complete a formal production-root reread, and exit 0.
4. Verify Arrow schema, two rows, composition, fingerprints, Parquet SHA-256, logical references, empty staging, and unchanged canonical inventory.
5. Export the private multi-Universe snapshot, build the frontend and OCI bundle, then use the existing deployment dry-run and reviewed apply workflow.

Never overwrite an existing activation. Any nonzero apply result blocks snapshot generation and deployment. Do not silently fall back to Legacy. Rollback uses the retained prior Dashboard release and Legacy artifacts through the existing deployment mechanism.

## Activation V2 authorization boundary

1. Run `scripts/admin/publish-dashboard-universe-activation-v2.sh --approval-package /tmp/<new-plan>.json`. It must report `dry_run_ready`, the reviewed source fingerprint, 1,718/1,831 planned memberships, target absence, V1 compatibility mode, the frozen artifact hashes, `plan_sha256`, and `expected_active_state_fingerprint` without writing `/data`. The new package is canonical JSON, fsynced, and mode 0444.
2. A later, separately authorized operation may invoke exactly `scripts/admin/publish-dashboard-universe-activation-v2.sh --apply --approved-plan /tmp/<approved-plan>.json --approved-plan-sha256 <approved-plan-sha256> --expected-current-state-fingerprint <approved-current-state-sha256>`. Bare apply and missing approval fields are rejected. Apply must rebuild the byte-identical plan, validate it again under the lock, publish the immutable revision, and atomically replace the pointer only after formal reread.
3. Never retry an uncertain apply. Inspect the original process, immutable target, pointer bytes, and formal active reader instead.
4. A completed target with no pointer is inactive. A pointer to V2 is active even if the invoking shell failed after the pointer switch.
5. If the immutable target is completed but inactive, run `scripts/admin/recover-dashboard-universe-activation-v2.sh` without arguments. After reviewing its target validation and `expected_current_pointer_fingerprint`, a separate authorization may run `--apply --expected-current-pointer-fingerprint <approved-token>`. It only links the existing target and never rewrites it.
6. Rollback requires separate authorization. Run `scripts/admin/rollback-dashboard-universe-activation.sh` without arguments and record its `expected_active_pointer_fingerprint` and rollback target. Apply must use `--apply --expected-active-pointer-fingerprint <approved-sha256>`; any state change after dry-run is rejected without writing.

An absent pointer is the only V1 compatibility fallback. A present but invalid pointer is an integrity failure, not permission to fall back.
