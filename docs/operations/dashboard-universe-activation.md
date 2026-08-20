# Dashboard Universe Activation Operation

1. Verify the workstation identity, clean Git tree, formal trailing-liquidity/review inputs, target absence, and canonical protected inventory.
2. Run `scripts/admin/publish-dashboard-universe-activation.sh` without arguments. Dry-run must exit 0 and write nothing.
3. Run the script once with `--apply`. The command must publish both activation partitions, complete a formal production-root reread, and exit 0.
4. Verify Arrow schema, two rows, composition, fingerprints, Parquet SHA-256, logical references, empty staging, and unchanged canonical inventory.
5. Export the private multi-Universe snapshot, build the frontend and OCI bundle, then use the existing deployment dry-run and reviewed apply workflow.

Never overwrite an existing activation. Any nonzero apply result blocks snapshot generation and deployment. Do not silently fall back to Legacy. Rollback uses the retained prior Dashboard release and Legacy artifacts through the existing deployment mechanism.
