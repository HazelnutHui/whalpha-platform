# ADR 0283: Reuse Content-Addressed Research Artifacts and Publish Milestones

## Status

Accepted

## Date

2026-09-15

## Context

Dell currently retains about 7 GB of canonical `/data` evidence and about
24 GB of private research and operational state. The workstation has ample
free capacity; raw size is not the current constraint. The avoidable costs are
repeated reconstruction of identical panels, large per-run session copies,
unbounded narrative inspection, and a Product projection that can lag a
completed research milestone.

Factor research must become faster without deleting source evidence, hiding
failed trials, weakening data isolation, or turning the website into a live
backend log. Token efficiency and compute efficiency are governance concerns:
agents should usually consume compact typed summaries, while full artifacts
remain available for targeted audit.

## Decision

1. Keep canonical source evidence immutable and do not copy it into each
   experiment directory.
2. Materialize reusable derived panels only at named boundaries: point-in-time
   population, feature matrix, market-state inputs, nuisance controls, and
   labels. Address each artifact by source fingerprints, schema, cutoff,
   calculation code, and parameters so an exact match is reused rather than
   rebuilt.
3. Keep feature and market-state custody separate from labels. Outcome-blind
   discovery and qualification may read only the former; registered screening
   receives the exact labeled slice declared by its protocol.
4. Treat temporary extracts, logs, caches, immutable evidence, and canonical
   publications as different retention classes. Cleanup requires measured
   duplication, an exact target, and a separate safe operation; this decision
   authorizes no deletion.
5. Profile first. Add bounded process-level parallelism only to deterministic,
   partition-safe hotspots with stable output ordering. Do not introduce a new
   database, microservice, distributed system, or opaque feature store without
   a measured need.
6. Give agents compact machine-readable campaign summaries by default:
   identities, counts, gate decisions, exclusions, and next authority. Read
   full row-level artifacts or long documents only for a named investigation.
7. Publish the Lab at material research milestones only: registered,
   qualified, screened, model locked, validation decided, holdout decided,
   shadow entered, activated, or retired. Intermediate process progress does
   not belong on the public site.
8. A milestone change is incomplete until the same reviewed change set updates
   the typed research record, cumulative ledger, authoritative status/context,
   dated audit, trilingual Lab projection, and tests. Production deployment is
   a separate guarded action; source synchronization is not a claim that the
   public site has already changed.
9. Keep the current result and next authorized boundary expanded. Put formulas,
   parameters, full lineage, hashes, historical campaigns, and limitations in
   accessible disclosure panels. Never hide evidence needed to understand a
   claim.

## Consequences

Research cycles can reuse expensive deterministic inputs and reduce both
compute and context load while preserving exact lineage and falsifiability.
The public Lab becomes a reviewed research ledger, not a misleading real-time
progress meter. The source repository can always state exactly whether a
milestone is implemented, committed, deployed, or merely proposed.

## Rejected alternatives

- delete immutable evidence to make the directory appear smaller;
- rebuild every factor, control, and label panel for every hypothesis;
- let outcome-aware agents inspect all labels during idea generation;
- push every backend progress event directly to the public site;
- add a feature-store service or database before profiling demonstrates need;
- summarize research without retaining formulas, exclusions, failures, and
  reproducibility identities.

