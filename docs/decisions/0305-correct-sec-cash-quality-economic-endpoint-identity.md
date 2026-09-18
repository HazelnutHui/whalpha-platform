# ADR 0305: Correct SEC Cash-Quality Economic Endpoint Identity

## Status

Accepted; V2 selector implemented, corrected TTM build not authorized

## Date

2026-09-18

## Context

ADR 0304's first bounded TTM coverage run reported 55,168
`fiscal_period_endpoint_ambiguous`, 17,702
`quarter_sequence_not_consecutive`, and 9,441
`insufficient_prior_endpoints`. A read-only diagnosis used only ADR 0303's
58.9 MB endpoint package and its target-occurrence index. It did not reread the
41.6-million-occurrence normalized source or access any outcome stage.

Company Facts `fy` is the fiscal focus of the filing that reports a fact. A
later filing can repeat an earlier comparative economic endpoint with the
later filing's `fy`. Therefore `(CIK, fy, fp)` is not an economic-period key.
The package contains 82,440 endpoint variants but only 61,895 exact economic
endpoints keyed by `(CIK, duration origin, fp, period end)`. There are 19,539
repeated-economic-endpoint groups and 20,545 superseded variants. Every group
has one componentwise-latest complete variant; 2,003 groups change at least
one retained value and therefore cannot be deduplicated by value equality.

After this exact-endpoint canonicalization, only 201 `(CIK, origin, fp)` groups
remain genuinely ambiguous across different period ends, covering 413
endpoints. These conflicts remain quarantined.

The corrected package still contains only 434 Q2 and 293 Q3 endpoints. This is
not primarily absence in the retained source index: a bounded alternative
selection over that index found 30,457 Q2 and 29,141 Q3 endpoint candidates
with one directly witnessed YTD origin, all three registered concepts, and
accession-coherent CFO and net income. Another 605 endpoint coordinates have
multiple coherent origins and must remain ambiguous. The large gap was caused
by requiring a separately labelled Q1 fact to witness a Q2/Q3 YTD start date.

## Decision

The next endpoint-selection version will use the following fail-closed order:

1. For Q2 and Q3, use the registered duration facts' own non-null `start_date`
   as the fiscal-origin witness. CFO and net income must resolve under the same
   origin and accession. Assets remains an instant fact at the same end date.
2. Admit an endpoint coordinate only when exactly one origin produces all
   three selected queries. Zero origins is missing; multiple origins is
   ambiguous. Filing labels, calendar assumptions, and nearest-date matching
   are forbidden substitutes.
3. Canonicalize repeated exact economic endpoints by
   `(CIK, origin, fp, end)`. One variant supersedes the others only if its
   availability time is greater than or equal to every other variant for each
   of Assets, net income, and CFO. Ties or crossing component clocks are
   quarantined. Retain the selected variant's reported `fy`, values,
   accessions, clocks, and occurrence IDs, and count every superseded variant.
4. Sequence only the canonical economic endpoints. Within-origin succession
   is Q1, Q2, Q3, FY; cross-origin succession requires the next origin to be
   exactly the prior FY end plus one day. Reported `fy` never proves either
   relation.

The corrected selector must be versioned and bound to ADR 0303's exact target
index SHA-256 and schema. It may rebuild from that owner-only local index and
must not rescan the normalized source. Before any corrected real build, add a
typed disposition result that separately reconciles input variants,
superseded variants, canonical endpoints, origin ambiguity, sequence gaps,
and left-truncated history. Forward/reverse replay and exact reread remain
required.

## Diagnostic disposition

Mapping the three original blocker sets to corrected economic identity gives:

| Original blocker | Superseded variant | True ambiguity | Left-truncated in retained package | Retained-package sequence gap | Sequence-ready |
| --- | ---: | ---: | ---: | ---: | ---: |
| fiscal-period endpoint ambiguous (55,168) | 19,662 | 385 | 19,045 | 15,882 | 194 |
| non-consecutive (17,702) | 230 | 17 | 1,280 | 16,049 | 126 |
| insufficient prior endpoints (9,441) | 649 | 11 | 8,780 | 1 | 0 |

These rows diagnose the old labels; they are not a projected corrected
coverage result. A retained-package sequence gap is not proof that the source
lacks the period, because the target index demonstrates the Q2/Q3 selector
loss described above. Likewise, the old 9,441 count is not a stable estimate
of genuine left truncation because removing comparative duplicates changes
endpoint ordinal positions. Among the 61,895 canonical endpoints, only 267 of
41,330 issuer-origin cycles currently contain all four period labels, while
19,351 contain only FY and Q1. The direct-origin repair must therefore precede
any new TTM coverage census.

No security projection, factor, outcome, Validation, Holdout, Candidate,
canonical-research, or Product authority is granted.

## Implementation

`quant-research-sec-cash-quality-direct-origin-selection/2.0` implements the
decision as a pure, versioned selector. Its plan binds the source endpoint
package and selection-plan fingerprints plus the target index's physical
SHA-256, Arrow schema fingerprint, byte size, and row count. The formal build
refuses any physical or logical mismatch before reading the Parquet table.

The result reconciles endpoint coordinates separately from comparative
variants: every coordinate is either a selected variant or one typed selector
blocker; every selected variant is then canonical, superseded, or a typed
canonicalization blocker. Forward/reverse replay hashes the canonical Arrow
stream. Owner-only atomic custody retains plan, canonical endpoint rows,
result, and verification and requires exact reread.

The bounded V2 build read only the 47,478,659-byte retained target index. From
428,922 observed reported endpoint coordinates, 145,356 produced one complete
direct-origin variant and 283,566 were blocked: 192,908 lacked a required query
at every candidate origin, 89,833 lacked a duration origin, 639 had multiple
complete origins, and 186 had accession-incoherent CFO and net income. Exact
economic canonicalization retained 120,473 endpoints, dispositioned 24,875
comparative variants as superseded, and quarantined eight variants with
crossing component clocks. The retained endpoints comprise 35,455 FY, 28,003
Q1, 29,119 Q2, and 27,896 Q3 observations across the source range.

Forward and reverse results and Arrow hashes were identical. Owner-only exact
reread returned 361,419 query rows. This validates selection custody only; it
does not authorize or report corrected TTM coverage.
