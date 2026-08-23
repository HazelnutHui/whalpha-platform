# Dashboard Universe Activation V2

Activation V2 is an immutable, revisioned two-row catalog plus a separately stored active pointer. The first supported revision is `authoritative-security-form-v2` for analysis session 2026-08-19. It is strictly sourced from completed superseding full-base publication `51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97`.

The immutable target is:

`market-data/snapshots/dashboard-universe-activation-v2/revision=authoritative-security-form-v2/analysis_session=2026-08-19`

It contains one explicit-schema Parquet file and a last-written manifest. The active pointer is the single JSON file `market-data/snapshots/dashboard-universe-activation-active/active.json`. Its `active` and `rollback` references bind schema version, revision, session, normalized logical path, and logical fingerprint. The pointer also binds the sole default and the two public catalog IDs.

Publication first writes and formally rereads the immutable target. Only then may it atomically replace the pointer under an exclusive data-root lock and compare-and-swap guard. A crash before target rename leaves no target. A crash after target publication leaves a completed but inactive target. A crash after pointer replacement is diagnosed by formally reading the pointer; it must never be retried blindly.

The primary publisher never accepts a bare `--apply`. Its dry-run may write a read-only approval package under `/tmp`; the canonical JSON plan freezes the activation timestamp and IDs and binds the current activation/pointer state, source publication and fingerprints, exact catalog and memberships, absolute target paths, rollback reference, Parquet/manifest/pointer bytes and SHA-256 values, planned pointer fingerprint, and its own SHA-256. Apply requires the approved file, its approved digest, and the approved current-state fingerprint. It rebuilds the entire plan and, under the lock, revalidates current state and every source before any production directory is created. The published Parquet, manifest, and pointer must then match the approved bytes exactly.

Every newly created directory is fsynced together with its parent directory entry before publication continues. The immutable target file and manifest, staging directory, target rename parent, pointer staging file, and pointer rename parent retain their separate fsync gates. A completed-but-inactive target is recovered only by the default-dry-run verify-then-link operation: it formally rereads every immutable artifact and source reference, then apply requires the exact approved current-pointer CAS token and writes only the pointer.

When no pointer exists, the active reader formally reads Activation V1 for backward compatibility. A malformed, unsafe, inconsistent, or dangling pointer fails closed and never falls back to V1. All runtime Activation consumers call the active reader.

Rollback is a separate default-dry-run operation. Dry-run reports the active pointer content fingerprint and exact prior completed target. Apply requires that caller-supplied fingerprint, rereads it under the lock, validates both references, and then atomically swaps `active` and `rollback`. Publication does not automatically roll back, and rollback cannot overwrite either immutable target.

The V2 catalog has a contract-defined order independent of lexical IDs: `Common Shares` is first and remains the sole default; `Common Shares + ADRs` is second. Legacy remains hidden. The planned source-derived memberships are 1,718 CS and 1,831 total (1,718 CS + 113 ADRC). These values remain inactive until a separate bounded activation authorization executes the V2 publisher with `--apply`.
