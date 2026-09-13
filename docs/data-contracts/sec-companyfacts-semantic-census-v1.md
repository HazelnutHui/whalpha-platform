# SEC Company Facts Semantic Census V1

## Purpose and grain

`sec-companyfacts-semantic-census/1.0` is one immutable source-level report for
an exact normalized Company Facts package and one explicitly bound
common-stock filer-link diagnostic population. It measures semantic coverage,
duplicates, conflicts, and clean revision behavior without producing features
or a daily panel.

## Keys and conservative classifications

The unit-processing key is:

```text
CIK + namespace + concept + unit
```

The raw semantic fact key adds exact `start_date + end_date`. The
accession-semantic group adds `accession_number`.

- An exact duplicate group has more than one occurrence and one distinct
  `(value_kind, value_text)` within an accession-semantic group.
- A within-accession conflict has more than one distinct value in that group.
- A same-availability conflict has different uniquely valued accessions for
  one semantic key at the same `source_available_at_utc`.
- A clean revision sequence requires every occurrence for the semantic key to
  be normalized and clock-admitted, every accession to be uniquely valued,
  and every availability timestamp to have one value.
- Later-accession revisions count accessions after the first in a clean
  sequence. Value changes compare consecutive unambiguous availability states.

No missing date, clock, unit, value, conflict, or ordering ambiguity is
imputed.

## Report content

The report binds the normalized source manifest SHA-256, source logical and
content fingerprints, exact range, schemas, artifacts, row denominator, build
revision, and the bound filer-link manifest/fingerprint/session.

It records:

- occurrence and distinct filer/concept/semantic-key populations;
- ordered counts for namespace, unit, form, filing year, value kind, period
  shape, filing-clock state, normalization state, and taxonomy class;
- duplicate, conflict, clean-revision, quarantined-revision, and value-change
  counts;
- the common-stock link population's instrument, distinct-CIK, SEC-source
  matched, and missing-CIK counts;
- at most 250 standard accounting concept summaries, ordered by distinct filer
  coverage and then occurrence count; and
- at most 100 deterministic examples for each conflict class, using value
  fingerprints rather than silently selecting a value.

`us-gaap` and `ifrs-full` are standard accounting namespaces. `dei` is a
document/entity namespace. Known SEC specialized namespaces remain a distinct
class. Any other namespace is `unregistered_namespace_review`; it is not
automatically called an issuer extension.

## Physical and authority boundary

The package is a mode-`0700`, owner-only directory containing one mode-`0400`
`census.json`. It is first written to a sibling partial directory and published
by no-overwrite atomic rename after validation. Its logical fingerprint
excludes no semantic result field.

Formal readback validates the complete typed report, exact file set, ownership,
modes, bound input manifest identities, row denominator, count invariants, and
logical fingerprint. Building and reading the report make zero external
requests and grant zero canonical-write, feature, analytics, Membership,
Candidate, research-performance, publication, deployment, or scheduler
authority.
