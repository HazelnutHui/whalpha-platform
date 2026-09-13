# Strong-Leader Pullback SEC Document Plan — 2026-09-13

## Result

ADR 0229's no-request acquisition plan completed from the formally reread SEC
lifecycle metadata pilot. It includes every 219 filing candidate on or after
the last canonical price observation and no earlier candidate. Accessions and
official SEC URLs are one-to-one and unique.

The plan does not download or interpret a document and grants no lifecycle,
terminal-outcome, Historical Coverage, research, Candidate, or Production
authority.

## Exact identity

| Field | Verified value |
| --- | --- |
| Implementation revision | `f132fdf9db36de4166b04dd4130a38654b5fc735` |
| Planned at | `2026-09-13T13:54:48Z` |
| Source pilot SHA-256 | `ba4803207492a00229a0bc1025e17882ece600a8a3f5c97cca5c8645da786059` |
| Source pilot fingerprint | `c68cd6c8b0677091cb467323938c4255525da2106c2c9d859b0bc76497502ad1` |
| Plan SHA-256 | `bb79ec052e7296b1a7234f83d5c91a11097bdb54f9215e8c806e5159ab0d41f7` |
| Plan fingerprint | `fbce15f14b151fc179a5b16d1bdea97a72bf1c57dd025ee91ea56e33fe62c500` |
| Plan size | 174,159 bytes |

The owner-only plan is retained at
`historical-source/strong-leader-pullback-sec-documents/build=20260913-v1`.
Its directory/file modes are `0700/0400`; formal typed and canonical-byte
reread reproduced the exact result.

## Request population

| Measure | Count |
| --- | ---: |
| Planned requests / unique URLs / unique accessions | 219 / 219 / 219 |
| Batches | 22 |
| Full ten-request batches | 21 |
| Final batch requests | 9 |
| On last observation | 139 |
| On provider delisting candidate | 11 |
| After provider delisting candidate | 69 |

The population contains 64 Form 25-NSE, 66 Form 15 family, 62 structured 8-K,
24 tender-response amendment, two proxy-supplement, and one 6-K document.
There are 156 direct lifecycle/transaction-form locators, 62 structured 8-K
lifecycle-item locators, and one post-last-observation foreign report.

## Limits and verification

- HTTPS `GET` is restricted to `www.sec.gov`; queries, fragments, absolute or
  traversal document paths, backslashes, and controls are rejected.
- Rate is capped at two requests per second, retries at two per document, and
  response size at 64 MiB per document.
- The complete API suite passed 2,643 tests in 265.73 seconds with the same two
  dependency deprecation warnings.
- Plan custody contains no symlink, partial, or temporary member.
- External request, credential read, document write, security assignment,
  terminal outcome, canonical write, Historical Coverage, research admission,
  Candidate, publication, deployment, and scheduler-change counts are zero.
- Canonical `/data` remains the previously verified 21,025 files /
  7,397,444,417 bytes with fingerprint
  `b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.

## Next boundary

Implement one resumable source-custody runner that consumes only this plan,
stores each response with exact request/response metadata and hashes, respects
the fixed batches and limits, and formally rereads the completed package.
Document content remains source evidence until a separate field-level
extraction and security-identity decision is reviewed.
