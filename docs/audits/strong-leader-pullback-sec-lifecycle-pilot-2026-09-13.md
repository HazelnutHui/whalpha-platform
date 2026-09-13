# Strong-Leader Pullback SEC Lifecycle Pilot — 2026-09-13

## Result

ADR 0228's outcome-blind SEC metadata pilot completed over all 64 frozen
first-strategy lifecycle cases. Every CIK root member and all 42 referenced
historical shards passed formal source binding and structural read. Every case
has at least one filing candidate on or after its last canonical price
observation.

This result narrows official-document discovery. It does **not** establish a
listed-security identity, last tradable date, delisting reason, successor,
consideration, terminal return, Historical Coverage, or research admission.

## Exact binding

| Field | Verified value |
| --- | --- |
| Implementation revision | `6aaba2fe953f6b60ff28eb99ebe0618c7a30adfa` |
| Evaluated at | `2026-09-13T13:42:15Z` |
| Source sample SHA-256 | `17a1c177be65693786a410c1c2107c499e34a88960541a24339644e12ba01416` |
| Source sample fingerprint | `f29da6a170f873b20a4ee57141cf1dc975f5a8f3a840dc19dc115283828c1a5a` |
| SEC Submissions manifest SHA-256 | `816915bce637b5ab11b1056d20f150321afbe6f5a755f384cecba45e68905d3b` |
| SEC Submissions source fingerprint | `188863129a5dfc5324d337d23d67597cc048696dfbc2bc0e6b73a254344631b2` |
| SEC Submissions archive SHA-256 | `6c7963d599a4b40da0bc361af5e332a8d80e73c4ed3a66bd629a4e9fc8163338` |
| Payload-census SHA-256 | `6ab8e3970cf05b4af964833d82af93aa9444a372f1cb79ffa5a378c811e2c249` |
| Payload-census fingerprint | `bfa416ca41003e163932b8c0185386ea4fd5d9a461146274918dfbadb7c41004` |
| Pilot SHA-256 | `ba4803207492a00229a0bc1025e17882ece600a8a3f5c97cca5c8645da786059` |
| Pilot fingerprint | `c68cd6c8b0677091cb467323938c4255525da2106c2c9d859b0bc76497502ad1` |

The private report is retained at
`historical-evidence/strong-leader-pullback-sec-lifecycle-pilot/build=20260913-v1`.
It is 1,204,695 bytes; its directory/file modes are `0700/0400`.

## Coverage result

| Measure | Count |
| --- | ---: |
| Frozen lifecycle cases / unique CIKs | 64 / 64 |
| Root / referenced historical-shard members | 64 / 42 |
| Source filing rows read | 91,640 |
| Filing rows inside the declared census range | 27,137 |
| Retained lifecycle-document candidates | 2,144 |
| Candidates before the last price observation | 1,925 |
| Candidates on the last price observation | 139 |
| Candidates on the provider delisting candidate | 11 |
| Candidates after the provider delisting candidate | 69 |
| On-or-after-last candidates | 219 |

The 219 transition-period candidates include 64 Form 25-NSE rows, 66 Form 15
family rows, 62 structured 8-K rows, 24 tender-response amendments, two proxy
supplements, and one post-last-observation 6-K. At the case level, 62 have a
Form 25 family candidate, 62 have a Form 15 family candidate, and 61 have a
structured 8-K candidate. Form presence is therefore informative but neither
uniform nor sufficient for a terminal fact.

Across the full five-year range, candidate categories contain 1,308 direct
lifecycle/transaction forms, 835 structured 8-K lifecycle-item rows, and one
post-last-observation foreign report. Pre-transition transaction documents
remain retained because they may later explain acquirer, predecessor,
consideration, or termination context; they are not ranked or interpreted.

## Corrections exposed by the real source

The first temporary diagnostic stopped safely on two incorrect assumptions
before any durable result existed:

1. an EDGAR accession prefix is not required to equal the Submissions member
   CIK; accession and filer identity now remain separate; and
2. `primaryDocument` may be a safe relative path rather than only a basename.

Both rules were corrected narrowly and regression-tested. A later command was
also found to have an `evaluated_at` value ahead of Dell UTC. Its one unreferenced
1.2 MB private output was exactly verified and deleted, then rebuilt under the
same path with the correct observed time above. No canonical artifact was
deleted or overwritten.

## Verification and authority

- 12 directly related SEC/sample tests passed during focused verification.
- The complete API suite passed 2,639 tests in 265.20 seconds with the same two
  dependency deprecation warnings.
- Formal post-write typed/canonical-byte reread reproduced all counts, hashes,
  and fingerprints.
- Pilot custody contains zero symlink, partial, or temporary member.
- The canonical `/data` inventory remains 21,025 files / 7,397,444,417 bytes,
  fingerprint
  `b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`,
  with zero symlinks and zero publication residue.
- Document request, credential read, security assignment, terminal outcome,
  trigger, forward outcome, metric, parameter choice, canonical write,
  Historical Coverage, research admission, Candidate write, publication,
  deployment, and scheduler-change counts are all zero.

## Next boundary

The next useful stage is to freeze and acquire a bounded set of SEC primary
documents from these retained locators, beginning with the 219 transition-
period candidates. Document content must still be mapped to the exact security
and field, retain source availability/revision evidence, and distinguish
matched, absent, unsupported, and conflicting results. No full-market SEC scan
or strategy outcome access is justified. Because this metadata pilot did not
change a mandatory lifecycle fact family, the rejected development-admission
decision must not be rerun yet.
