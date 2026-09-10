# ADR 0199: Retain complete corporate-action source packages privately

- Status: Accepted
- Date: 2026-09-10

## Context

The exact five-year split and dividend acquisitions, their annual
cross-checks, and complete repeats first land in owner-only `/tmp` packages.
That isolation is appropriate during network acquisition, but `/tmp` is not a
durable evidence boundary.  The repeat also proved that five Massive split
action IDs can change while the complete non-ID payload remains identical.
Keeping only one normalized result would discard the evidence needed to
explain that source revision.

Copying temporary packages into canonical `/data` before stable-ID resolution
would overstate their authority and would conflict with the active canonical
EOD/Identity writer.  Re-downloading after a reboot is avoidable and can itself
produce a later source vintage rather than recover the original observation.

## Decision

1. Network acquisition remains restricted to an exact owner-only `/tmp`
   target with the existing finite page, byte, interval, sanitization,
   checkpoint, and formal-reread rules.
2. After completion and formal reread, exact source packages and their diff
   evidence may be copied byte-for-byte into an explicitly selected Dell
   owner-only historical-source state directory.
3. The source-package reader may reread a completed persistent copy only when
   the caller supplies its exact direct parent.  The root and package must be
   real, owner-held, mode 0700 directories; nested, broader, renamed,
   symlinked, or mode-drifted paths fail closed.  Files retain mode 0400 and all
   existing manifest, pagination, physical-hash, logical-fingerprint, scope,
   and aggregate checks.
4. A resolution-shadow caller may pass this same explicit custody root.  The
   resulting normalized records remain bound to the package manifests and
   exact-date Identity evidence; the storage location grants no semantic
   authority.
5. Persistent private custody is not canonical Corporate Action, Adjustment
   Ledger, Historical Coverage, signal-time evidence, analytics, publication,
   deployment, or scheduler state.  It never resolves provider-ID changes by
   first-non-null selection.
6. Retained packages may be retired only after a later append-only canonical
   source-observation/revision boundary transitively binds both vintages and a
   separately verified backup exists.  This ADR does not authorize deletion.

## Execution evidence

The first retained tree contains 193 files / 252,132,705 bytes.  Recursive
comparison against the acquisition roots found no difference; all 22
directories are mode 0700 and all 193 files are mode 0400.  The relative-path
and file-hash list fingerprint is
`4da1a226d7a47aa78871cd4295495839af043e4d94fa89b214893d9e5fad156b`.

The new reader formally reread all 16 retained baseline, annual, and repeat
packages.  They contain 726,726 rows across overlapping observations; the
declared full range remains 242,242 rows per complete vintage.  Focused source
and resolution tests passed 24 cases, including exact-root acceptance and
broader-root refusal.  The complete API regression passed 2,407 tests; the two
warnings are unchanged dependency deprecations.

## Consequences

- A reboot or temporary-directory cleanup no longer forces re-acquisition or
  silently changes the observed source vintage.
- Raw evidence remains private and separate from normalized canonical facts.
- Later stable-ID resolution can consume the retained repeat packages without
  treating `/tmp` as durable storage.
- Disk use increases by about 252 MB, which is immaterial relative to the Dell
  data volume and preserves materially different source evidence.

## Rejected alternatives

- **Keep only `/tmp`:** leaves a completed source family dependent on an
  intentionally non-durable location.
- **Publish raw pages directly into canonical `/data`:** conflates source
  recovery custody with canonical semantic authority.
- **Keep only the latest repeat:** loses the evidence of provider-ID
  instability.
- **Allow an arbitrary persistent path:** weakens containment and makes a
  mistaken broad or symlinked root harder to detect.
