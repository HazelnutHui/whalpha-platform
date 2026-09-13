# ADR 0215: Adopt the retained FINRA and SEC research foundation

- Status: Accepted
- Date: 2026-09-12

## Context

An earlier Dell worktree diverged from main at revision
`1710e5528f054404423ff3d7257803139b796e54` and completed a coherent sequence
of FINRA and SEC data-foundation work on 2026-09-10. Its code, tests, contracts,
audits, and persistent owner-only artifacts remained available, but the branch
was never reconciled after main independently continued EOD repair, website,
and lifecycle work.

The branch also used local ADR numbers 0202–0211. Main later assigned those
same numbers to different accepted EOD decisions. Copying those branch-local
ADR filenames into main would silently corrupt the decision index; ignoring
the branch would strand about 6.85 GB of formally governed source and derived
evidence and invite duplicate work.

## Decision

Adopt the data-only implementation through branch revision
`0bc1dad21ae3099b88d9a0c17068329b32bcef36` into main under this single
integration decision. Preserve its detailed contracts, operations guides, and
dated audits. Treat its original colliding ADR files as branch-history
evidence only; the following rules are authoritative in main:

1. FINRA OTC Daily List is retained as official OTC corroboration only. It
   does not establish complete major-exchange lifecycle, stable identity,
   availability time, successor, consideration, last trade, or terminal
   return.
2. FINRA/Massive split and dividend overlap is a candidate-only census. Exact
   date/symbol/numeric agreement does not resolve `instrument_id`, and opaque
   event/revision codes are not promoted to a final-state rule.
3. SEC Company Facts and Submissions bulk archives are immutable current
   source snapshots. Their exact payloads, accessions, filed dates, acceptance
   timestamps, amendments, conflicts, and missing records remain explicit.
4. Daily filing availability uses the first XNYS open strictly after the
   conservative retained SEC acceptance boundary. Conflicting acceptance
   values use the latest value; missing clocks remain quarantined.
5. Every admitted Company Facts occurrence is preserved in a sparse revision
   ledger. No current-value overwrite, historical backfill of a later filing,
   implicit unit conversion, taxonomy synonym, quarterly derivation, or
   all-concept daily Cartesian panel is allowed.
6. CIK identifies a filer, not a listed security. Daily filer-to-security link
   decisions use stable `instrument_id`, preserve multi-security CIKs, and do
   not authorize issuer-fact projection to every share class.
7. Point-in-time fundamental queries must register exact concepts, units,
   period and form semantics, cutoff, security projection, and revision
   selection before materializing model features.

The final branch-only public-entry commit is excluded because main contains a
newer deployed landing and application hierarchy. Authority documents from the
old branch are not copied wholesale; current context, status, roadmap, and
changelog are reconciled to main's newer EOD and Production state.

## Accepted evidence

- FINRA: 62 monthly packages / 68,714 rows for 2021-08-11 through 2026-09-09;
  four repeated identifiers remain eight distinct occurrences.
- FINRA/Massive action census: 2,298 unique numeric split candidates and 8,205
  unique numeric dividend candidates, with zero stable-ID resolution.
- SEC Company Facts: 20,343 members, 125,418,051 occurrences, and 41,619,407
  five-year occurrences across 172,265 accessions; eight anomalous member roots
  remain quarantined.
- SEC Submissions: 989,553 members / 27,217,476 filing rows; 172,262 of 172,265
  target accessions match, with three missing, 107 acceptance conflicts, and 15
  filed-date disagreements retained.
- Filing clocks: 172,265 rows, 172,262 admitted and three quarantined.
- Normalized Company Facts: 41,619,407 occurrences, of which 41,619,004 inherit
  admitted clocks and 403 remain quarantined.
- Filer/security pilot: one session / 8,201 stable-ID decisions, including 150
  multi-security CIK groups; issuer projection remains unauthorized.

The imported 129 focused tests passed both before and after integration. The
existing sealed census, filing-clock, and link readers reproduced their
recorded logical fingerprints from main. The complete 41.6-million-occurrence
formal reread also passed in 2,508.68 seconds and is recorded separately in the
integration audit; it is a low-frequency integrity path, not a routine recovery
step.
The complete main API suite passed with 2,574 tests and two pre-existing
dependency deprecation warnings after adoption.

## Consequences

- Main again contains the code required to recover and interpret the retained
  FINRA/SEC state; no duplicate acquisition or normalization is required.
- The five-year database is materially closer to a professional point-in-time
  foundation, but neither lifecycle nor fundamental research admission is
  complete.
- The next fundamental step is a source-level semantic/conflict census and a
  small registered concept/query layer, followed by a complete effective-dated
  filer/security link build. It is not a broad daily fact expansion.
- The next action/lifecycle step remains stable-ID resolution and terminal
  corroboration. FINRA evidence may strengthen matched OTC cases but cannot
  replace an all-exchange lifecycle source.
