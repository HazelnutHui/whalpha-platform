# ADR 0095: Share Offline Artifact Custody Across Persistent Analytics

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0094 correctly blocked persistent-workspace execution because the daily
planner derived session directories outside `/tmp` while older analytics
writers and readers enforced direct-child `/tmp` custody independently. A
path-by-path relaxation would duplicate security policy and could allow a
writer and its formal reader to disagree. Legacy reviewed `/tmp` workflows
must also remain usable while the persistent chain is reconciled in stages.

## Decision

Use one shared lexical custody validator for offline analytics artifacts. It
accepts exactly either:

- one absolute direct child of `/tmp`, preserving the reviewed legacy path; or
- one explicitly named artifact directly below
  `<owner-root>/daily-eod/sessions/session_date=YYYY-MM-DD/`.

The persistent workspace, `sessions`, and dated session directories must
already exist, be owned by the executing user, and have mode `0700`. Existing
path components may not be symlinks. The workspace must remain outside `/tmp`
and every Git worktree or repository. Each caller supplies its exact governed
artifact name; an arbitrary sibling name is rejected.

The shared boundary now covers Phase 1a, its Sector ETF Rotation companion,
Phase 1b, Candidate recovery and final audits, Entry Geometry, ETF
Relationships, Market Preview, Strategy Channels, and Candidate Visual
Context. Candidate finalization treats `candidate-work` as a recovery name
only during the internal final reread; the public completed-audit reader still
accepts only `opportunity-candidate` in persistent custody.

A real Dell 2026-08-28 rehearsal completed all nine final analytics
directories under one owner-only persistent session. Every directory was
`0700`, every immutable file was `0400`, and no symlink, partial, pending, or
resume residue remained. Every CLI reported zero Oracle mismatch, zero
external requests, and zero Production writes. The Candidate, Entry Geometry,
ETF Relationship, Strategy Channel, and Visual Context logical fingerprints
were respectively
`39f26ded1dbdd5359eca9d6f3c49dc0b1286531f31a5a61845c0a955ad145412`,
`26b7c16840a0f28776d2d12efc62d320b223ad4c28093de305fb02061fafda9f`,
`7823c298cc6673970d3704530fb46d061f59ec00d064566521cc245398fd602c`,
`54baacaf6b07c680006536296dd58e4b12c858d8e724f339d06c61c5ef99eb48`,
and
`fe1df7fe0d6a05d6e7a7417944c34e5bb7a3a49eda7f1be95dad24fa1bb49510`.

Market Intelligence 1.3 candidate/Plan 1.3 and Snapshot 1.10/Plan 2.5
candidate/plan writers, contracts, and formal plan readers now also accept the
exact persistent session paths. Separate real Dell rehearsals passed with zero
Production writes. The MI rehearsal used the complete persistent analytics
chain. The Snapshot rehearsal used the exact legacy audits bound to the
currently active MI 1.2, because mixing the new persistent audits with that
older active publication correctly failed lineage validation.

At this decision point, Automation Plan 1.7 remained blocked pending one exact
persistent lineage through MI/Snapshot Apply and serving-bundle reread. That
condition was subsequently met; ADR 0096 records the separate reviewed Plan
1.8 removal while preserving all operational authority boundaries.

## Consequences

- Persistent analytics are now physically proven rather than inferred from
  mocked execution.
- Legacy `/tmp` reviews remain backward compatible.
- Exact names and owner-only parents prevent a generic writable workspace.
- The Candidate recovery/final boundary is explicit and testable.
- MI/Snapshot Apply, bundle, publication, deployment, `/data`, provider,
  credential, and scheduler authority are unchanged.
- Repeated full Candidate rereads remain a measured performance problem; this
  decision does not weaken formal verification to hide that cost.

## Alternatives Considered

### Remove the ADR 0094 block after analytics only

Rejected because the same persistent session must still cross MI, Snapshot,
and bundle writer/reader boundaries before an unattended action can be safe.

### Accept any owner-owned absolute directory

Rejected because ownership alone does not bind session, layout, Git exclusion,
or the artifact's operational role.
