# ADR 0214: Retain the five-year inactive-lifecycle resolution shadow

- Status: Accepted
- Date: 2026-09-12

## Context

ADR 0200 preserved the two complete Massive inactive-listing source anchors in
private Dell custody. ADR 0213 then re-resolved those sources against the full
five-year canonical Instrument history. The resulting six-file shadow is
materially more useful than the earlier 268/303-session diagnostics, but it
existed only under `/tmp` and would be lost on cleanup or restart.

The result is still incomplete lifecycle evidence. It does not prove last
tradable session, terminal reason, successor security, transaction
consideration, or historical source-availability time. Copying it into
canonical `/data` or allowing the builder to write arbitrary persistent paths
would overstate its authority and widen the mutation surface.

## Decision

Keep shadow construction `/tmp`-only. Permit formal reread from persistent
custody only when all of these conditions hold:

- the caller supplies the exact approved Dell private evidence base;
- the shadow root is one direct child named `build=<bounded-id>`;
- the approved base, build root, and complete directory chain are real,
  owner-owned, mode-0700 directories with no symlink;
- all three files in each anchor partition are real, owner-owned, immutable
  mode-0400 files; and
- the existing schema, manifest, artifact hashes, logical fingerprints,
  one-to-one source/decision lineage, and aggregate-count checks all pass.

Archive the completed two-anchor build byte-for-byte through a new staging
directory followed by an atomic rename. Refuse overwrite and compare the exact
relative-path/file-hash inventory with the `/tmp` source before accepting the
persistent copy.

Persistent custody changes durability only. It grants no canonical Lifecycle,
terminal outcome, Membership, Corporate Action, adjustment, Historical
Coverage, research admission, signal, Candidate, performance, Production, or
deployment authority.

## Execution evidence

Implementation revision
`0699d4f6e6febe05c96ab715cfd978c03d86843a` added the restricted persistent
reader and tests for exact-root acceptance and broader/unapproved-root refusal.
The focused suite passed 12 tests; the complete API suite passed 2,540 tests
with two unchanged dependency deprecation warnings.

The retained build contains six files / 9,005,301 bytes. Its exact relative-
path/file-hash list fingerprint is
`10dbda320316af93399f91e707bff615e6800237f99f5ba3d2a82aed9568f004`.
There are no symlinks, partial directories, or staging residue. Formal
persistent reread reproduced both original manifests and logical
fingerprints. See the
[dated audit](../audits/five-year-inactive-lifecycle-resolution-shadow-2026-09-12.md).

## Consequences

- The full-history reconciliation can now be recovered without an eight-minute
  rescan and without reacquiring provider data.
- The earlier short-history shadows remain historical diagnostics and are not
  silently relabeled or overwritten.
- The 2,283 distinct review-candidate instruments are now a durable bounded
  work queue for corroboration, not accepted lifecycle facts.
- Remaining lifecycle and terminal-outcome evidence is still a blocking data
  family for research admission.
