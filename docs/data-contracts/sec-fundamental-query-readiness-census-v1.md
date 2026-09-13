# SEC Fundamental Query Readiness Census V1

## Purpose and scope

`sec-fundamental-query-readiness-census/1.0` measures whether the four queries
in `sec-issuer-fundamentals-first-set-v1` have usable source occurrences under
their exact joint semantics. It is a source-readiness report, not a fundamental
feature table or a backtest input.

The census scans every normalized occurrence once at the Arrow column level,
but converts only the four registered `us-gaap` concepts into query rows. It
does not create a filer-by-security-by-session Cartesian panel.

## Sequential disposition

Every occurrence of a registered concept receives exactly one disposition, in
this order:

1. unit allowed;
2. form allowed;
3. fiscal period allowed for that form;
4. period end present;
5. instant/duration shape valid;
6. annual duration within 330–400 days where required;
7. normalization admitted;
8. filing clock admitted;
9. source availability present; and
10. accepted numeric value present.

Only a row passing every gate is `query_eligible`. Counts for rejected rows
remain visible; no missing or unsupported value is imputed.

## Duplicate and conflict treatment

Eligible rows are evaluated at issuer/query/semantic-period grain.

- identical value and availability rows inside one accession collapse and are
  counted as redundant exact duplicates;
- differing values or availability times inside one accession quarantine that
  semantic period;
- different clean accession values at the same availability time quarantine
  that semantic period; and
- multiple clean duration starts for one period end quarantine every affected
  semantic period rather than choosing a fiscal-year shape heuristically.

`selectable_filer_count` means the filer has at least one clean semantic period
for the query. It does not state that the latest fact is current, projectable to
a security, available at a particular historical cutoff, or fit for research.

## Reproducibility and physical custody

The report binds the deterministic query-registry fingerprint, semantic-census
file and logical fingerprints, normalized-source manifest and content
fingerprints, exact source date range, source snapshot, worker count, complete
occurrence denominator, implementation revision, and evaluation time.

The output is an owner-only mode-`0700` immutable package containing one
mode-`0400` `census.json`. It is written through an exact sibling partial path
and a no-overwrite atomic rename. Formal readback revalidates the complete
semantic census and its inputs before accepting the report binding.

## Authority boundary

The census publishes no fact values. It grants zero authority for a daily
panel, security projection, feature materialization, outcomes, performance,
canonical data, Membership, Candidate, publication, deployment, scheduling,
or external requests. A later query reader and projection census remain
separate governed stages.

Implementation:
`tip_api.providers.sec.fundamental_query_readiness_census`.
