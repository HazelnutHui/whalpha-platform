# Market Regime Local Preview Bundle V1

## Status and scope

Contract `market-regime-opportunity-map-preview/1.0` is an implemented local-
development transport for the completed Phase 1a, Phase 1b, and Phase 2
analytics. It is not a Production analytics publication, Dashboard snapshot,
or active pointer.

The builder accepts three explicit audit directories. It never selects a
“latest” `/tmp` directory and never reads the EOD panel. Each source must pass
its formal reader, have zero Oracle mismatches, share one `as_of_session`, and
form this exact lineage:

```text
Phase 1a composite audit
  └── Phase 1b state audit
        └── Phase 2 ETF relationship audit
```

Phase 2 must reference the same Phase 1a and Phase 1b logical fingerprints
supplied to the builder.

## Physical bundle

The output is one caller-owned, mode-`0700`, direct child of `/tmp` containing
exactly two caller-owned mode-`0400` files:

- `market-regime-opportunity-map.json`
- `preview-manifest.json`

Missing or extra files, non-canonical JSON, mode/owner drift, symlinks, nested
paths, traversal, changed hashes, or changed logical fingerprints fail closed.
Existing non-empty targets are never reused. The CLI has no apply operation
and holds an in-process socket guard while reading sources and writing output.

## Logical payload

The payload business key is `as_of_session`. It contains:

- contract and calculation versions plus all three parameter fingerprints;
- the three source audit logical fingerprints;
- fixed public Universe catalog order, default, counts, and membership hashes;
- one complete Phase 1a Composite, current Phase 1b state, state history, and
  explanations for each Universe;
- all 30 registered ETF basket entries;
- all 16 registered pair definitions, current records, and explanations;
- Phase 2 chronological relationship history and exactly 32 contemporaneous
  Universe/pair comparison rows;
- fixed limitations and quality gates.

All arrays preserve contract order. Numeric values remain canonical Decimal
strings. Null remains null; unavailable fields retain their reason codes.
Primary and Secondary analytics are separate records. ETF relationship records
are shared facts and cannot change with Universe selection.

`logical_fingerprint` is SHA-256 over canonical UTF-8 JSON with sorted keys,
compact separators, NFC strings, and the fingerprint field excluded. The
manifest binds payload bytes, SHA-256, logical fingerprint, as-of session, and
source fingerprints. `generated_at` is physical provenance and is excluded
from the manifest logical fingerprint. Consequently, repeated builds with
identical logical inputs have byte-identical payloads even when generated at
different times.

## API boundary

The bundle is read completely and verified once at application startup, then
held as an immutable in-memory view. API requests do not read `/data`, scan the
EOD panel, or recompute Phase 1/2 results. A corrupt configured bundle aborts
startup. Absence of explicit preview configuration leaves the route
unregistered and preserves the existing Production-default application.

This preview transport must never be promoted by copying it into `/data`.
Production analytics publication, immutable release identity, approval plan,
pointer CAS, rollback, and deployment require a separate design and approval.
