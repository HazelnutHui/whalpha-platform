# ADR 0200: Retain inactive-lifecycle source anchors privately

- Status: Accepted
- Date: 2026-09-10

## Context

The 2026-07-16 and 2026-09-03 Massive `active=false` All Tickers packages are
the complete retained source observations behind the existing lifecycle
resolution diagnostics.  They contain later-delisted securities and stable
identifier fields that are important to survivorship-bias control, but both
packages existed only below `/tmp`.

Losing them would either discard lineage or require a later re-download that
could contain provider revisions.  Publishing them as canonical Instrument
Lifecycle would be equally incorrect: `delisted_utc` alone does not prove last
tradable session, terminal reason, successor, consideration, or source
availability time.

## Decision

Apply the exact private-custody pattern from ADR 0199 to inactive-lifecycle
source anchors.

- Acquisition remains bounded and `/tmp`-only.
- A complete package may be copied byte-for-byte into one explicitly supplied
  owner-only Dell custody root.
- Persistent reread accepts only an exact direct-child `anchor=YYYY-MM-DD`
  package. Root/package ownership, mode 0700, real paths, immutable mode-0400
  files, request chain, hashes, fields, counts, and natural pagination all
  remain mandatory.
- The disconnected lifecycle resolution shadow may consume that explicit
  root, but still produces only review candidates and quarantine.
- Persistent custody grants no canonical Lifecycle, terminal outcome,
  Corporate Action, Historical Coverage, signal, performance, Production, or
  deployment authority.

## Execution evidence

The two retained anchors contain 52 files / 13,358,318 bytes. Recursive source
comparison found no difference; the relative-path/file-hash list fingerprint
is `e513227f734704ba8e295daea4d18c2d4a08f03f7d40aa29d2403620e88d54c2`.

Formal persistent reread returned:

- 2026-07-16: 24 requests / 23,260 rows, logical fingerprint
  `5b298512378f80fc5e72eb90bf05b588feb91c1ea1caedd802c8d54ac8cee7fb`;
- 2026-09-03: 24 requests / 23,469 rows, logical fingerprint
  `8ae15be74aa8c554ab83075346f93c3d966cec72811d47375f53a91a8734ff98`.

Focused source/CLI/resolution tests passed 18 cases, including exact-root
acceptance and broader-root refusal. The complete API regression passed 2,409
tests; the two warnings are unchanged dependency deprecations.

## Consequences

The original inactive-security observations now survive temporary-directory
loss while their incomplete lifecycle semantics remain explicit.  After the
five-year Identity backfill is quiescent, the later anchor can be re-resolved
against the enlarged stable-ID history without another provider request.
