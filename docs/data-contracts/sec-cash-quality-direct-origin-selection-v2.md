# SEC Cash-Quality Direct-Origin Selection V2

This contract rebuilds issuer endpoint evidence only from ADR 0303's closed
target-occurrence index. The plan is bound to the index's physical SHA-256,
Arrow schema fingerprint, byte size, and row count. It authorizes no normalized
source rescan or network request.

Each coordinate is `(Company Facts CIK, reported fy, fp, period end)`. FY and
Q1 retain their registered duration-start semantics. For Q2 and Q3, the
duration facts' own non-null `start_date` is the origin witness; no separately
labelled Q1 occurrence is required. An origin is selectable only when Assets,
net income, and CFO all have one deterministic latest amendment state and CFO
and net income share an accession. Zero complete origins is blocked. Multiple
complete origins, within-accession conflicts, equal-time accession/value
conflicts, and duration-accession incoherence are quarantined with typed
reasons.

Selected reported-coordinate variants are canonicalized by exact economic key
`(CIK, duration origin, fp, period end)`. A variant supersedes another only
when all three component availability clocks are greater than or equal to the
other variant's clocks. Crossing clocks, latest-clock ties, and conflicting
latest values fail closed. The selected variant retains reported `fy`, exact
values, accessions, source availability, signal-eligible session, and all
source occurrence IDs.

The owner-only package contains canonical endpoint Parquet rows, the input-
bound plan, a fully reconciled disposition result, and forward/reverse replay
verification. Atomic publish, immutable file modes, canonical JSON, byte-
identical Arrow replay, and exact reread are required.

This is issuer source engineering only. It grants no TTM derivation, listed-
security projection, factor, outcome, Validation, Holdout, Candidate,
canonical-research, Production, or Product authority. See
[ADR 0305](../decisions/0305-correct-sec-cash-quality-economic-endpoint-identity.md).
