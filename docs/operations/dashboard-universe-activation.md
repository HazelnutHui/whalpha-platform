# Dashboard Universe Activation Operation

1. Verify the workstation identity, clean Git tree, formal trailing-liquidity/review inputs, target absence, and canonical protected inventory.
2. Run `scripts/admin/publish-dashboard-universe-activation.sh` without arguments. Dry-run must exit 0 and write nothing.
3. Run the script once with `--apply`. The command must publish both activation partitions, complete a formal production-root reread, and exit 0.
4. Verify Arrow schema, two rows, composition, fingerprints, Parquet SHA-256, logical references, empty staging, and unchanged canonical inventory.
5. Export the private multi-Universe snapshot, build the frontend and OCI bundle, then use the existing deployment dry-run and reviewed apply workflow.

Never overwrite an existing activation. Any nonzero apply result blocks snapshot generation and deployment. Do not silently fall back to Legacy. Rollback uses the retained prior Dashboard release and Legacy artifacts through the existing deployment mechanism.

## Activation V2 authorization boundary

1. Run `scripts/admin/publish-dashboard-universe-activation-v2.sh` without arguments. It must report `dry_run_ready`, the reviewed source fingerprint, 1,718/1,831 planned memberships, target absence, and V1 compatibility mode without writing `/data`.
2. A later, separately authorized operation may invoke that command once with `--apply`. It publishes the immutable revision first and atomically replaces the active pointer only after formal reread.
3. Never retry an uncertain apply. Inspect the original process, immutable target, pointer bytes, and formal active reader instead.
4. A completed target with no pointer is inactive. A pointer to V2 is active even if the invoking shell failed after the pointer switch.
5. Rollback requires separate authorization. `scripts/admin/rollback-dashboard-universe-activation.sh` is also default-dry-run; its apply mode validates both targets and the expected active fingerprint before atomically swapping references.

An absent pointer is the only V1 compatibility fallback. A present but invalid pointer is an integrity failure, not permission to fall back.
