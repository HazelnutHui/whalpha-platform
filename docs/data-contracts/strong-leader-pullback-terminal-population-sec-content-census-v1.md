# Strong-Leader Pullback Terminal-Population SEC Content Census V1

## Purpose

`strong-leader-pullback-terminal-population-sec-content-census/1.0` proves that
every document in the authoritative corrected-population SEC source package
can be parsed deterministically. It localizes candidates for the same eight
registered lifecycle field families used by the original 219-document census;
it does not extract or adjudicate a fact.

## Inputs and binding

The census formally rereads the immutable source plan and source package. Its
report binds the physical and logical plan identities, source manifest SHA-256,
source logical and artifact-binding fingerprints, clean implementation
revision, evaluation time, and marker-ruleset fingerprint.

Plan item count, source completed-document count, manifest completed-document
count, ordered report record count, form totals, byte totals, parse totals, and
marker totals must reconcile. A mismatch fails before publication.

## Document records

Each record preserves request sequence, stable `instrument_id`, CIK, accession,
form, acceptance time, physical byte count and SHA-256, deterministic decoding,
markup profile, normalized-text length and SHA-256, date-token count, amendment
flag, and all eight marker records.

Decoding order, markup profiles, text normalization, script/style exclusion,
and marker expressions are inherited unchanged from
`strong-leader-pullback-sec-document-content-census/1.0`. Each marker retains
its total occurrence count and at most three bounded contexts. Full normalized
text is not duplicated because immutable source bytes already exist.

## Custody and semantics

The canonical JSON is written exclusively beneath an owner-only `census=*`
directory, atomically published, and formally reread. Directories are `0700`
and the report is `0400`; replay must be identical.

Every marker remains `unresolved_lexical_candidate_only`. Zero occurrences do
not establish absence, and one or more occurrences do not establish a match.
The report authorizes no network request, credential access, security identity,
lifecycle fact, terminal outcome, strategy trigger, forward outcome,
performance metric, parameter selection, `/data`, Historical Coverage,
research admission, Candidate write, publication, deployment, or scheduler
change.
