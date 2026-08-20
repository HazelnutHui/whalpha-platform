# Universe Pre-Activation Review Runbook

This is an offline derived shadow operation. It must not access credentials, providers, Git remotes, OCI, or any other network service. Production Universe activation and Dashboard integration are separate operations.

## Preflight

1. Require the approved host, branch, implementation HEAD, and clean worktree.
2. Require all new targets and task-specific staging paths to be absent.
3. Formally reread Trailing Liquidity V1, all referenced EOD/identity inputs, membership evidence, schemas, counts, fingerprints, and physical hashes.
4. Reconstruct Legacy from stable IDs and completed canonical EOD sources.
5. Run offline focused and full tests under the socket guard.

## Commands

The entrypoint has no configuration arguments. A bare invocation is a read-only dry-run:

```bash
scripts/admin/publish-universe-pre-activation-review.sh
```

The single separately authorized publication adds only `--apply`. Unknown or extra arguments return 2. Apply is not retried and existing targets fail closed.

## Postflight

Use the formal reader to validate both component partitions, the last-written logical marker, source references, schemas, counts, fingerprints, and Parquet SHA-256 values. Require task staging and partial targets to be absent and prove the pre-existing protected inventory unchanged. Do not activate a Universe, change Dashboard/API/frontend, create snapshots/bundles, access OCI, or deploy.
