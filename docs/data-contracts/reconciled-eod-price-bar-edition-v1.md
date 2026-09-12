# Reconciled EOD Price Bar Edition V1

## Purpose

This contract defines a complete, immutable, explicitly selected research EOD
edition rebuilt from source custody under one frozen provider-mapping rule. It
does not overwrite or implicitly supersede canonical EOD Price Bar V1.

## Status

Session, interval, and Apply-plan manifests are at contract version 1.2.
Deterministic sealing, fail-closed diff classification, formal base
record reread, one-session isolated candidate reconstruction, owner-only
candidate persistence, immutable rerun checks, completed-session formal
reread, bounded/resumable process-parallel session construction, final
interval-marker sealing/reread, exact whole-edition Apply planning, and atomic
Apply execution are implemented. The exact 1,234-session source selection is
sealed and build-ready. A first real 1.0 build stopped safely after 275
sessions and exposed the typed legacy-removal requirement now governed by ADR
0208. The successor 1.1 build retained 300 sessions before exposing a second
source-proven class: exact provider-ticker casing restored inside otherwise
identical source IDs. ADR 0209 and contract 1.2 govern that class. The first
1.2 run retained 1,079 sessions before exposing an incorrect builder input for
a price-only case collision; the existing ADR 0203 classifier now consumes
exact price symbols as designed. A new complete 1.2 construction, an executed
canonical edition, and the edition-only research input adapter remain pending.

## Identity

An edition is keyed by an immutable `edition_id`. A research input must bind
both that ID and the completed interval-manifest fingerprint. A directory name
or latest filesystem entry is not authority.

## Session grain

One session partition contains the complete accepted EOD Price Bar V1
cross-section for one XNYS session and one edition. The Parquet row schema is
the existing EOD Price Bar V1 Arrow schema.

## Required session bindings

Each session manifest records:

- edition ID and edition contract version;
- session date and provider;
- mapper policy ID and implementation revision;
- Grouped Daily source-package manifest and content fingerprints;
- source provenance: retained original or later reacquisition;
- source observation time;
- canonical Identity snapshot date and fingerprint;
- exact Identity-source logical fingerprint;
- rebuilt row count and content fingerprint;
- EOD V1 base row count and fingerprint;
- added, total absent, source-proven expected absent, unexpected absent,
  expected and unexpected provenance-only, economically changed, and unchanged
  key counts;
- quality counts, warnings, and reconciliation disposition; and
- Parquet filename/hash and completion status.

Fingerprints and relative logical paths are evidence. Credentials, headers,
raw response bodies, home paths, and secret locations are forbidden.

## Reconciliation rules

The business key is the EOD Price Bar V1 key. Comparison distinguishes:

1. keys present only in the rebuilt edition;
2. keys present only in EOD V1;
3. shared keys with changed economic fields;
4. shared keys with only declared provenance-time differences; and
5. fully unchanged keys.

ADR 0203 permits the expected repair class to add a previously omitted resolved
bar when the exact Grouped Daily payload contains a case-distinct symbol group
and same-session exact Identity resolves that bar to an existing canonical
stable ID. The price payload, not the Identity payload, defines whether the
legacy price mapper encountered a collision; Identity remains the eligibility
and stable-ID authority. ADR 0208 separately permits removal of a legacy case-
normalized misbinding only when the retained original price package, exact
same-session Identity source, stable-ID mapping, excluded case-distinct symbol, source ID,
timestamp, observation time, OHLCV values, adjusted close, and neutral
adjustment factors all reproduce the error. The contract records that removal
as expected and uses the distinct
`accepted_case_sensitive_reconciliation` disposition. A later-reacquired
price package can never use this exception.

ADR 0209 permits one additional retained-original repair: restoring the exact
provider ticker case inside `source_record_id`. It requires the same business
key and stable ID, complete economic equivalence, identical observation,
quality, revision, and schema fields, the same source timestamp, an exact
mixed-case Identity resolution to that stable ID, absence of the old exact
upper-case ticker, and reproduction of the legacy normalized Resolver binding.
The contract counts the repair as expected provenance-only change and uses the
same typed case-sensitive reconciliation disposition. A timestamp, observation
time, quality, revision, schema, instrument, or economic difference cannot use
this rule.

Any unexpected removal or addition, economic change, or unexpected
retained-source provenance change requires a typed quarantine reason and a
separate decision before the session can enter a completed edition. An
accepted removal is therefore not a generic tolerance or percentage threshold.

## Interval completion

The interval manifest is written last and includes:

- exact evaluation and warm-up bounds;
- exact ordered session set and count;
- every session manifest fingerprint;
- total addition, accepted-absence, and provenance-only counts, plus
  reconciliation counts by disposition and source provenance;
- source-gap and quarantine counts, which must be zero for completion;
- frozen mapper policy and implementation revisions; and
- one deterministic logical fingerprint.

Readers reject an absent, partial, inconsistent, symlinked, or fingerprint-
mismatched interval manifest. They never infer completion from the number of
session directories.

Full-edition validation processes one session at a time and retains only its
manifest evidence. This preserves complete Parquet/schema/content validation
without retaining all five years of rows in memory.

## Candidate custody and Apply

Long-running construction may use exactly one direct child of the fixed Dell
owner-only candidate base. Bounded tests may use an owner-only directory below
`/tmp`. Candidate directories are mode 0700 and files are mode 0600. The
candidate never lives below `/data` and never gains research or Production
authority.

One construction batch contains 1–40 explicitly ordered sessions and uses no
more than four spawned worker processes. It makes zero external requests and
zero canonical writes. Exact completed sessions are resumable only after
formal reread and source-package fingerprint/provenance equivalence. Per-
session failures remain visible and prevent interval completion; successful
partitions are retained for a later bounded rerun. Source selection is a
separate evidence contract and must never use an implicit first match.

Source Coverage 1.0 is that evidence contract. For every exact XNYS session it
records the observed package origins and one of: selected retained original,
selected later reacquisition, missing, invalid, or conflict. A retained
original must bind its formally reread canonical Apply plan, package hashes,
canonical EOD fingerprint, and same-session Identity fingerprint. A later
reacquisition keeps distinct provenance and cannot claim an original Apply
binding. Multiple otherwise eligible original packages are a conflict, not an
automatic precedence choice.

Coverage reports independent blockers cumulatively. In particular, an absent
Grouped Daily package is not hidden when same-session Identity source custody
is also unavailable. The bounded price-source reacquisition runner may close
that exact price-package gap while the session remains Identity-blocked; doing
so does not relax candidate-build readiness or manufacture Identity evidence.

The evaluation backfill and separate warm-up backfill are distinct source
origins even though both can prove retained-original provenance. This keeps the
legacy evaluation workspace immutable and makes source resolution unambiguous.

Coverage keeps the five-year evaluation interval separate from the optional
contiguous warm-up interval. The session inventory begins at the declared
warm-up boundary when present, still requires the evaluation-first session to
be present, and ends at the evaluation-last session. Warm-up rows therefore
support feature construction without being mislabeled as evaluation history.

The complete coverage artifact is immutable, owner-read-only, byte-hashed, and
contains no filesystem paths or response bodies. It is build-ready only when
every declared session has exactly one valid selection. Candidate batches
reread both the artifact byte hash and every selected source binding before
use. The coverage artifact is evidence, not research or Production authority.

The sealed Apply plan binds:

- the plan's exact candidate custody and non-revealing location fingerprint,
  plus the exact target edition path;
- every session manifest and Parquet path, byte count, and SHA-256;
- the final interval-manifest fingerprint;
- total session, record, accepted-addition, accepted-absence, and provenance-
  only change counts;
- the candidate implementation and planner revisions; and
- one full canonical `/data` pre-state fingerprint.

The plan is an owner-read-only file beside the candidate, not an authorization.
Apply additionally requires its byte SHA-256, logical fingerprint, and expected
pre-state fingerprint. It acquires the shared Dell data-writer lock, disables
network access, verifies the complete candidate and inventory binding, copies
all artifacts to one adjacent staging edition, writes the interval manifest
last, and atomically renames the complete directory into its absent target.
The target uses 0755 directories and 0644 files. A formal target reread and an
outside-target inventory comparison follow before success is reported.

An exact completed target may be reused only through the explicit
`verify_then_complete` recovery path. Unknown staging residue is never removed.
Failure cleanup is inode-bound to the staging directory created by that Apply.
No overwrite, deletion, external request, model admission, or website action is
part of this contract.

## Authority

A completed edition is still only a candidate research price family. It gains
no Candidate, Production, Dashboard, publication, or model authority without
the later Historical Coverage and research-admission decisions.
