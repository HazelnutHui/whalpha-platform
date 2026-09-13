# SEC Company Facts Semantic Census — 2026-09-13

## Scope

Build and formally reread one complete source-level semantic census for the
retained five-year SEC Company Facts normalized package. The run used clean
main revision `9e04045d33fec6bb0f6293af13c9f54ff1cab086`, eight Dell processes,
the exact 2021-08-11 through 2026-09-09 normalized ledger, and the retained
2023-11-09 common-stock filer/security diagnostic population.

The operation was network-free and credential-free. It wrote one owner-only
private report outside canonical `/data`; it created no daily fact panel,
feature, security projection, analytics, Candidate, performance result,
publication, deployment, or scheduler change.

## Source bindings

| Evidence | Exact identity |
| --- | --- |
| Normalized manifest SHA-256 | `29e9146878b95bb303c7bd486ad607143c4d7a0e4e64cba4220eaee1eb112c19` |
| Normalized logical fingerprint | `e45b6624398767e2d96c5e05f56cbf9e73c79e4651a13927a3256f0a7739d5da` |
| Normalized content fingerprint | `2874d1703dad871ccd0b0b4411f85585be42230ec5ee9bd7da9cc4681d3fac77` |
| Link manifest SHA-256 | `385fed347850a225c53cbc85f68a1d56bcfa8b172982c3d08cddf543e9879f01` |
| Link logical fingerprint | `e7efd0f6b530be218e6c64cea71a8f4fa7be4c2febc55d3098a8681d08c28421` |
| Link source observation | `2026-09-10T16:15:59.206933Z`; `eligible_at_source_observed_at` only |

The normalized package had already passed a complete 41,619,407-row formal
readback. This operation revalidated every artifact's ownership, mode, byte
size, physical SHA-256, Arrow schema, and manifest binding, then streamed every
occurrence exactly once.

## Result

| Measure | Result |
| --- | ---: |
| Occurrences | 41,619,407 |
| Distinct filers with in-range facts | 10,925 |
| Filers with at least one admitted fact | 10,924 |
| Observed filer-scoped concept keys | 2,396,949 |
| Distinct namespace/concept pairs | 11,082 |
| Exact semantic keys | 24,498,347 |
| Clean revision-eligible semantic keys | 24,497,828 |
| Revision-quarantined semantic keys | 519 |
| Semantic keys with a later availability state | 10,635,941 |
| Later revision states | 17,117,677 |
| Consecutive later states with changed value | 886,400 |
| Same-availability conflict buckets | 206 across 116 semantic keys |
| Missing-clock/normalization quarantine keys | 403 |
| Within-accession exact duplicate groups | 0 |
| Within-accession different-value conflicts | 0 |

The exact accession-semantic group count equals the occurrence denominator,
41,619,407, for this source snapshot and exact key definition. This is an
observed result, not a general claim that SEC facts never repeat. The 206
same-availability conflict buckets remain unresolved; the report retains 100
deterministic hashed examples without choosing a value by row order.

All 41,619,004 admitted occurrences have complete duration or instant period
shape and conservative filing clocks; 403 occurrences remain quarantined.
Standard accounting namespaces contribute 41,284,920 occurrences, the
document/entity namespace 150,833, and known SEC specialized namespaces
183,654. No unregistered namespace appeared in this exact interval. Units are
highly heterogeneous, so concept registration must continue to require an
exact unit rather than infer conversion or equivalence.

The bound common-stock diagnostic contains 5,072 instruments: 5,066 admitted
links and six quarantines, representing 5,019 distinct CIKs. Of those CIKs,
4,990 have in-range normalized facts and 29 do not. The most broadly covered
standard concepts begin with `us-gaap:Assets`, operating/financing cash flow,
liabilities and equity, and net income. Coverage rank is discovery evidence,
not feature admission or issuer-to-security projection.

## Runtime, custody, and verification

The eight-process build and its built-in formal readback completed in 246.18
seconds, with 1,740.70 aggregate CPU seconds. The maximum single-process RSS
reported by the command was 1,253,896 KiB; host observation during the parallel
phase was about 10 GiB total, leaving more than 50 GiB available.

The completed package is:

`historical-source/sec-companyfacts-semantic-census/build=20260913-v1`

It contains one mode-`0400`, 288,328-byte `census.json` under a mode-`0700`
directory. File SHA-256 is
`bd1b3d53dc1493a02270f5033e87be1cd58095cbd304db004bdb3ddd0af7e278`;
logical fingerprint is
`8899aeb278f50861952d7308a815c62640a2ec274bb1d614ff07f8ba651e3e21`.
There is no partial or staging residue.

A separate formal reader invocation completed in 10.58 seconds, reproduced
the 41,619,407-row denominator, 24,498,347 semantic keys, 519 revision
quarantines, and the exact logical fingerprint. The implementation-stage SEC
suite passed 245 tests and the complete API suite passed 2,577 tests with two
unchanged dependency deprecation warnings.

## Decision

The source-level semantic census is complete for this exact snapshot and
interval. It does not make fundamentals research-ready. The next bounded step
is to review the measured coverage and register a small first set of exact
concept/unit/period/form query definitions. Complete effective-dated
filer/security links and an explicit share-class projection policy remain
separate prerequisites before any security-level fundamental feature can be
admitted.
