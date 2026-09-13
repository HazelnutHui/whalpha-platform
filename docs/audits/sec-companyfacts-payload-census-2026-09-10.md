# SEC Company Facts Payload Census — 2026-09-10

## Scope

Fully read the sealed 2026-09-10 SEC Company Facts snapshot without network,
credentials, `/data` writes, extraction, normalization, analytics,
publication, deployment, or scheduler changes. The final run used clean
revision `11137e6346ffc50e17965755c94fc4c7295f27f4`, eight Dell workers, 159
deterministic batches, and the fixed source range 2021-08-11 through
2026-09-09.

## Result

Every one of 20,343 ZIP members was decompressed, CRC-checked, JSON-parsed,
and classified:

| Member state | Count |
| --- | ---: |
| Populated, structurally admitted | 17,865 |
| Exact empty JSON object | 62 |
| Filename-bound empty-`facts` placeholder | 2,408 |
| Quarantined nonempty member | 8 |
| Total / source total | 20,343 / 20,343 |

All eight quarantines are `cik_filename_mismatch`: the official member name
contains a CIK but the nonempty payload omits its root CIK. They remain
available in immutable source custody and are not silently repaired from the
filename.

| Fact measure | Count |
| --- | ---: |
| Structurally valid source occurrences | 125,418,051 |
| Filed before range | 83,798,644 |
| Filed within range | 41,619,407 |
| Filed after range | 0 |
| Invalid/missing filed date | 0 |
| Unique accessions, all / in range | 463,452 / 172,265 |
| Invalid/missing accessions | 0 |
| Duration / instant facts | 74,903,744 / 50,514,307 |
| Amendment-form occurrences | 3,685,884 |
| Frame-present occurrences | 53,810,820 |
| Malformed fact items | 0 |

The admitted payloads contain 13 namespaces. `us-gaap` contributes
122,042,326 occurrences; `ifrs-full` contributes 2,643,867. Values are
117,686,838 integers and 7,731,213 non-integer numbers. Every admitted fact has
accession, end, filed, form, and value. No unexpected root, concept, or fact
field was observed.

The final mode-`0400` report is 44,560 bytes with physical SHA-256
`8676ae0c5f9a4204faddea7a2c8f8bbeb400a73263b3924040a71ea6bc4bf123`
and logical fingerprint
`e98ea73df73777a937568f643e5aaf55c6a2f11daeebe13be775190ca10a0724`.
Formal reread passed. The SEC provider suite passed 230 tests and the full API
regression passed 2,433 tests with two unchanged dependency deprecation
warnings.

## Corrected classification

An initial contract-1.0 report classified all blank issuer names as
quarantined and therefore grouped 2,408 empty-`facts` placeholders with eight
nonempty CIK anomalies. Inspection proved the former contain zero concepts and
zero fact items. Contract 1.1 separates both empty forms from malformed
populated members. The initial owner-only report is retained as superseded
diagnostic evidence; it is not the current census.

## Alignment decision

Source payload validation is complete, but point-in-time fundamentals are not.
The archive supplies `filed` dates and accessions, not the exact acceptance
timestamps required for a defensible signal-time clock. CIK also identifies a
filer rather than a unique listed security. No fact was normalized or joined,
and no current value was projected backward.

The next bounded fundamentals stages are to retain the official SEC
Submissions bulk source, measure accession/acceptance coverage, preserve every
Company Facts occurrence and revision in a provider-neutral normalized source
family, and join CIK to stable instruments only where dated security evidence
is unambiguous.
