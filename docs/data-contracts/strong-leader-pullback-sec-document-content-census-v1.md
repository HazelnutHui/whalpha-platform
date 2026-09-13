# Strong-Leader Pullback SEC Document Content Census V1

## Purpose

`strong-leader-pullback-sec-document-content-census/1.0` proves that every
document in the frozen 219-request package can be deterministically parsed and
localizes lexical candidates for the eight registered lifecycle field
families. It does not extract or adjudicate lifecycle facts.

## Inputs and binding

The census formally rereads:

- the immutable ADR 0229 plan; and
- the completed ADR 0230 source package and all 219 physical document hashes.

The report retains both plan identities, the source manifest SHA-256, source
logical and artifact-binding fingerprints, the clean implementation revision,
evaluation time, and the exact marker-ruleset fingerprint.

## Document records

Every sequence retains plan identity fields, acceptance time, source bytes and
hash, deterministic decoding and markup profile, normalized text length/hash,
date-token count, amendment-form flag, and one marker record for every required
field.

Markup profiles are `html`, `sec-sgml-html`, or `xhtml-inline-xbrl`. Decoding
is fixed to `utf-8-sig`, `utf-8`, then `windows-1252`. Script and style content
is excluded; all other document text, including inline-XBRL text, remains in
the normalized hash.

Each field marker contains the total regex occurrence count and up to three
bounded normalized-text contexts with offsets and hashes. The report does not
retain full normalized text because the source package is already immutable.

## Semantics

All marker records are `unresolved_lexical_candidate_only`. Zero occurrences
means only “not detected by this registered lexical rule,” not “event absent.”
One or more occurrences means only that later structured extraction or review
has a candidate location, not that the field is matched.

Completion requires 219 ordered records, complete aggregate reconciliation,
canonical JSON bytes, `0700/0400` custody, and zero fact/authority counters.
Network requests, security assignments, lifecycle facts, terminal outcomes,
strategy triggers, forward outcomes, performance metrics, `/data`, Historical
Coverage, admissions, Candidate writes, publications, deployments, and
scheduler changes remain zero.
