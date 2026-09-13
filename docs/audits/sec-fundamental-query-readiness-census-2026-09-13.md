# SEC Fundamental Query Readiness Census — 2026-09-13

## Scope

Register and measure the first four exact issuer-level SEC Company Facts
queries without building a daily panel, projecting facts to securities, or
opening strategy outcomes. The run used clean main revision
`37e76cc9f1995b0a8afd4754758c6d1e48228c4c`, all eight normalized source
workers, the sealed 2021-08-11 through 2026-09-09 occurrence ledger, the
completed semantic census, and its bound 2023-11-09 filer/security diagnostic.

The operation was network-free and credential-free. It wrote one owner-only
private census outside canonical `/data` and changed no canonical, Membership,
Candidate, publication, deployment, or scheduler state.

## Registered semantics

The immutable `sec-issuer-fundamentals-first-set-v1` registry contains:

- `us-gaap:Assets` and `us-gaap:StockholdersEquity` as USD instant facts from
  admitted 10-K/10-Q family filings and their expected fiscal periods; and
- `us-gaap:NetIncomeLoss` and `us-gaap:OperatingIncomeLoss` as USD fiscal-year
  duration facts from admitted 10-K family filings, with inclusive 330–400-day
  duration.

Every query requires complete period, filing-clock, source-availability, and
numeric-value evidence. Exact duplicates may collapse. Value, availability,
or same-period-end shape ambiguity is quarantined. Revenue, quarterly-flow
derivation, per-share facts, market capitalization, IFRS forms, and concept
fallbacks remain deliberately unregistered.

Registry logical fingerprint:
`ffb5e1f2be190e1f7ef7a6cde9d4b42778cf194d05a01d6cb5131037d0500ea3`.

## Complete scan result

The census read all 41,619,407 occurrences and targeted exactly 1,569,275
occurrences of the four registered concepts. Every target occurrence received
one sequential eligibility or rejection disposition.

| Query | Concept occurrences | Eligible occurrences | Concept filers | Filers with a clean period | Clean / quarantined periods |
| --- | ---: | ---: | ---: | ---: | ---: |
| Assets | 267,781 | 256,410 | 9,320 | 8,569 | 131,597 / 0 |
| Fiscal-year net income/loss | 476,273 | 71,818 | 9,151 | 7,634 | 37,891 / 140 |
| Fiscal-year operating income/loss | 325,372 | 59,009 | 7,678 | 6,359 | 31,432 / 50 |
| Stockholders' equity | 499,849 | 484,007 | 8,914 | 8,175 | 150,884 / 0 |

The balance-sheet queries retain about 95.75% and 96.83% of their concept
occurrences after joint filtering. The annual-flow occurrence rates are lower,
15.08% and 18.14%, primarily because quarterly and other forms are intentionally
excluded; their clean-filer coverage is still about 83.42% and 82.82% of
filers that report the respective concepts.

The largest explicit rejections were:

| Query | Wrong form | Wrong duration | Wrong unit | Wrong fiscal period | Wrong period shape |
| --- | ---: | ---: | ---: | ---: | ---: |
| Assets | 8,543 | 0 | 2,543 | 285 | 0 |
| Fiscal-year net income/loss | 383,103 | 18,012 | 3,263 | 53 | 24 |
| Fiscal-year operating income/loss | 254,039 | 9,037 | 3,254 | 25 | 8 |
| Stockholders' equity | 12,023 | 0 | 3,286 | 533 | 0 |

No selected query occurrence failed filing-clock, normalization,
source-availability, end-date, or accepted-value gates in this snapshot. No
within-accession duplicate, within-accession value conflict, or same-time
different-value conflict appeared for the selected queries. The annual queries
did contain 69 net-income and 25 operating-income period-end ambiguity groups;
all 190 affected semantic periods were quarantined instead of choosing one
duration by row order.

## Custody, performance, and verification

The completed package is:

`historical-source/sec-fundamental-query-readiness-census/build=20260913-v1`

It contains one mode-`0400`, 5,685-byte `census.json` under a mode-`0700`
directory. File SHA-256 is
`a77ea6150f6946001a8147cde9ad0793f44f6181b041a7a9889fe5073241aa7c`;
logical fingerprint is
`5c803386e37576697fc8652197f932f26b559899cfe6d07c7ce5608d17f06bb8`.
There is no sibling partial or other package member.

The eight-process scan plus built-in transitive formal readback completed in
28.51 seconds, consumed 107.54 aggregate CPU seconds, and reported 543,840 KiB
maximum RSS. A separate formal readback completed in 10.50 seconds at 242,672
KiB maximum RSS and reproduced the complete source/target denominators and
logical fingerprint. The implementation-stage tests passed five cases and the
SEC provider suite passed 247 tests. The complete API suite then passed 2,613
tests with two unchanged dependency deprecation warnings.

## Decision and remaining boundary

The four source queries are ready for a later cutoff-aware issuer selection and
projection census. This statement means only that each has measured clean
source coverage and typed rejection paths.

It does not make the five-year database performance-eligible. The facts remain
issuer-grained; no values were published or projected. ADR 0224's
`single_common_security_per_cik_v1` class and evidence tiers still govern any
future projection, and only 11 of 1,255 retained link sessions meet strict
next-open knowledge time. Membership, lifecycle/terminal outcomes,
action/adjustment semantics, costs, final Historical Coverage, validation, and
holdout gates remain unresolved.
