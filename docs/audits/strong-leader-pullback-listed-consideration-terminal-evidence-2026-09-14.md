# Strong-Leader Pullback Listed-Consideration Terminal Evidence Audit — 2026-09-14

## Scope and authority

The network-disabled builder formally reread the strict listed-consideration
identity decisions, common-share consideration decisions, cessation timing,
payoff terms, and nine required canonical EOD/Identity sessions. It calculated
one gross daily reference terminal value only for each of the nine identities
that passed the prior four-element registration-document gate.

The result is not an execution price, legal settlement value, strategy outcome
or return. The three unassigned identities remain excluded. No `/data` or
Historical Coverage record, research admission, Candidate result, publication,
deployment, or scheduler state was changed.

## Exact bindings

- Implementation revision:
  `13d70c13ab907ae906c10209ed6a6206ceff8481`
- Identity-adjudication report SHA-256:
  `b23dd9fa6e308cf12f2adfead289f0fd967cc73fed93702c264e6bfdf530ed60`
- Identity-adjudication logical fingerprint:
  `b2f44efe02269331b890300f86389e84c471b578d581b9045a959af3b4d4bb09`
- Consideration report SHA-256:
  `834bf44dbc512c70a0722af18fab282c7b885dd881dbf48c126dd01ae0e00120`
- Cessation report SHA-256:
  `694e8b01274fdcad9bef2e0178e805df994f2526c190598b665e965541c2fae9`
- Payoff-terms report SHA-256:
  `f0b2e805a46e9f2b3e88432d1c5aa6a8782d095ffdda5790cb8894639d2be1a9`
- Ruleset fingerprint:
  `e99db96e41066526d5e60910efa9998efba86cdb0c21030532fe77dfcff23f0b`
- Report SHA-256:
  `18e47df490acca529aa3eaebdfaba70c989669ecb83e52a377d6885200913f2c`
- Report logical fingerprint:
  `a7bb1a87258e08ddb71b9add9ab7936dd2005522640bae124eebf665a1fbf9ef`

## Results

The exact calculation is `cash + ratio × consideration-security close` on the
target's first absent exchange session:

| Sequence | Session | Ratio | Cash | Close | Gross reference value |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 2026-02-02 | 1.818500 | 0.61 | 22.5700000000 | 41.6535450000000000 |
| 14 | 2025-10-01 | 11.000000 | 0.00 | 19.5900000000 | 215.4900000000000000 |
| 35 | 2025-08-04 | 1.152300 | 10.00 | 10.5000000000 | 22.0991500000000000 |
| 40 | 2025-11-28 | 0.344000 | 0.00 | 71.6200000000 | 24.6372800000000000 |
| 95 | 2026-01-09 | 1.436000 | 0.00 | 12.8400000000 | 18.4382400000000000 |
| 107 | 2026-07-22 | 0.140000 | 0.00 | 311.7000000000 | 43.6380000000000000 |
| 178 | 2025-10-20 | 1.950000 | 0.00 | 15.8400000000 | 30.8880000000000000 |
| 197 | 2025-09-02 | 0.915000 | 0.00 | 27.0300000000 | 24.7324500000000000 |
| 218 | 2026-08-17 | 2.793000 | 0.00 | 63.6600000000 | 177.8023800000000000 |

All nine canonical rows are USD, latest revision 1, and `valid`. Every row
retains `adjustment_factors_unverified`; the builder neither concealed that
limitation nor substituted an adjusted price. Canonical partition creation
time remains reconstruction custody time, not signal knowledge.

Sequences 158 and 184 remain excluded because their retained registration
documents do not prove the final exchange ratio. Sequence 174 remains excluded
because the retained 424B3 covers senior notes rather than the merger share
registration.

## Reproducibility

The 30,493-byte report is held in one `0700` directory with one `0400` file.
No symlink or partial/staging member remains. Exact replay returned
`already_present` with zero network requests and identical physical and logical
fingerprints.

Four focused tests, 24 linked tests, and the complete 2,718-test API suite
passed. The two warnings are unchanged dependency deprecations in the
authentication and TestClient paths.

## Next bounded gate

Freeze a replacement-source plan only for sequences 158, 174, and 184. It must
target exact transaction-registration evidence that proves the consideration
security and final ratio. These three cases may remain quarantined if no such
source is available; they do not invalidate the nine documented reference
values.

After the residual decision, reassess only the first strategy's remaining
mandatory lifecycle, action/adjustment, cost, and Historical Coverage gaps.
Do not open outcomes or run a real backtest until the research-admission gate
passes.
