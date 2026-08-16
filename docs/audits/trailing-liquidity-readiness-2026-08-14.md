# Trailing-Liquidity Readiness Audit — 2026-08-14

## Calendar and Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-14
- Previous/liquidity cutoff: 2026-08-13
- Window: 2026-07-17 through 2026-08-13
- Expected sessions: 2026-07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13
- Completed in window: 2026-07-17, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31, 2026-08-03, 2026-08-04, 2026-08-05, 2026-08-06, 2026-08-07, 2026-08-12, 2026-08-13
- Missing: 2 (2026-08-10, 08-11)
- Corrupt/unavailable: 0
- Readiness: `insufficient_history`
- Descriptor fingerprint: `b3bc186afba9320d52fb4ba99a9639f4a9fc35d5a52d7cc1f97ffcebe22eb1e2`

The completed 2026-08-14 partition exists for return analytics but is excluded from this window.

## Session Integrity

| Session | Rows | Content fingerprint | Physical Parquet SHA-256 | Identity date | Identity fingerprint |
| --- | ---: | --- | --- | --- | --- |
| 2026-07-17 | 9,844 | `c1bdf54e0ff421e74ffd5d57fe9e18ddca0dc8ac67d320dac6c06a8f4227b7c6` | `ec733ebc0b4887ca742ffb03d2c2df7bc78a30ec8a1145765b2f44fc2417dba9` | 2026-07-17 | `32af2ffc1538b5cbd261cc5299f27e52e3a6532917d4c3f47a50aaf4e50bccad` |
| 2026-07-20 | 9,858 | `c2cbbb44859abb3c2810a23ceaa0f7e81dcdcd15e8f976fcecb820f1597b3042` | `0d26f1fedb0d29d8b5523c49866eaf59cf90bd600ff066b50d1be90f721a30de` | 2026-07-20 | `39a605a180ddf8a6da63e306d3a8c9197c33a03f7f71d74d89693831a212ab38` |
| 2026-07-21 | 9,846 | `8e11c2e65b6dcdd646dd4075d8f5e87527d23405e50e5979782f638951eb5703` | `bfcb03205ecd92a4e76689522778000d40be9bd4334751415e316c808819d969` | 2026-07-21 | `7f1a8de56c1ed6841be61efdd27859de1c34c696f9b4be5185332ca14007c6b5` |
| 2026-07-22 | 9,847 | `099492742e29c60c4873d00f4bab48710f3801e1a5c0230967b04b022f720063` | `edd697061a6de05effdd49d35441ff2634a96641e04884267a9a11eb1a13a3bc` | 2026-07-22 | `0c8f1572895312c942fff3f530abc94d70d43814ee2e4f465bcc53acb113e571` |
| 2026-07-23 | 9,844 | `97cbb22530fc10bf1711390d7de19e560fbc093fd810c503bf652d3c1d0dcf28` | `f9b9949f61be5eca1113daff4ea9ce629d41004bf38f362a17f7e001583e6747` | 2026-07-23 | `baac3d36b35a03a387d7443408967bef37bb0fc31184850ec0ccb5d1ae537246` |
| 2026-07-24 | 9,833 | `0cd88aa82c3c1707cadaf5a131039dd6606c14046d012359c33a00381135375f` | `a83adb81b7f7d40aad07d7da120e0e57c6fc715119538ae7d61b7598d5db43ab` | 2026-07-24 | `90c78760416d3956c7258508a401f07ffa3719f018a47a399799f45ccfea0891` |
| 2026-07-27 | 9,859 | `85d3c7cb2c2a9dda14ed5ce7edd897cb26b8c76ff1edb7d0f2655baf8615d75e` | `e8f882444f3be9874fa57f90e25e925cdf3d2ebeca4132ffbd3a310c470b5b86` | 2026-07-27 | `45eff526287cd497fa8262343af3c018cf3df543954a4690f351c9e2af5f081c` |
| 2026-07-28 | 9,848 | `cb6f8af12b89dec66d26664917197209545e9d577f55573e85e66aa22857f34c` | `430fb66ad378ac206c4cf968996ec963c32bd19a144bfea64fbaad960a1b1cd1` | 2026-07-28 | `2a02c457a4fd1fc74fb2231765ff7af3cd79f44e82ddbcae678ed85a6fab39c2` |
| 2026-07-29 | 9,851 | `e88e356c3d553dca4e20412051181174f0ad4c05f61e3dfdd3f57c6a5f128b7a` | `c988f791aac67505b6324bd38e4267c7732bb850b18272d4cdd186c680e0dd6b` | 2026-07-29 | `8486b15eec9ac2b354b9270544594277044dcad1bb0dcbd88a414837b76d1b50` |
| 2026-07-30 | 9,855 | `1f943e10a6ff9ee5c03176d8b7c3af078656fdd406749dc54687a13231c8621b` | `2924815ce0d50d49c665655f9c005d750787f820a510153369c4e937bce632c7` | 2026-07-30 | `3750e3625271634f2da5739eee0b7a3604783c6db3eda4ef805a11a15afdd973` |
| 2026-07-31 | 9,853 | `c4999bc6e0be6397cf3562765439540bf6d7b9110f179c8e2b8bba0e28f80530` | `8b9c52cdc2f769696c4bdbceb25f5309ffe1a4f0e6008ef60820ff574c591442` | 2026-07-31 | `1fa2dd339772d529ea97e9be1732b34054ebe41b6cf05befdca9447ecd63b90e` |
| 2026-08-03 | 9,858 | `675c2179d66ad33363d1fea83a8d882a8fd240a6108a3f5bb82e130acdcb7c1a` | `be782b93cd816d9014d5ef8172f34ded813b46a2581eef4e72e9cb9a117b9926` | 2026-08-03 | `8be80efe2ce3a1bbd1f7b0694ab12b9a98a2a846b12f07c353460bf6b554ace5` |
| 2026-08-04 | 9,877 | `ba513ecc74bbb5641236ada4d9a0965a7449e8fb2e71c4f357f4307f8fc28273` | `c90ee2ed00bcc21a8f2322e057f06657223cf9956927e37be4c63135dceee6a1` | 2026-08-04 | `ba9dbd6712729ede900ba5d5634e626de4889d2639d1a2d24f91883cf7fa1a98` |
| 2026-08-05 | 9,869 | `3f8a37fa6e171566f7baa5e8c7ea9e846a04af7ee37cf64a5e25df3e85bcfca5` | `6043cb59db04d09594bf002175b141ef52351c26f688d570da18d74999a187bd` | 2026-08-05 | `a6d6d4f44826063edc3c3cadcc431ddfab7c98dcb8b13c77bcb7564f8eee6bb3` |
| 2026-08-06 | 9,875 | `04ca5378d5b944f5501e2466ef2e0d740ed9e73851ba6c25e55b344437b29822` | `3c0dbd4f71d7eaac73b1bde363004c90fcefced68015c8e90bc3dc7f3ff95bc6` | 2026-08-06 | `0cf49f3234c686c1916bbc38885ee0b08a971139db55a9611acc40297850a2b9` |
| 2026-08-07 | 9,877 | `3dd0f45cf3cdd2116e6f090f0ed2f1cf822d150b8fc2269e3444848f8ea66af0` | `d09d440260a3c2ec711cf1902e7659d63cbceef4d1f6eb2d6f311df047896e59` | 2026-08-07 | `23426651b603fb78ea7399b0cc1ae7f086ccf1cb26fa56e518ab93678f7ba644` |
| 2026-08-12 | 9,900 | `dee4299a4c662af6eb5853aff30af7f261727e57c9de4489cc558441a8638bd3` | `924ae001fea34ec6f82aeca252adbacf176e50818a13dc51053807fdeb5b9aa1` | 2026-08-12 | `ab208fa5c0e2116d818a22c28d369324325b69d9ba05acd29da0028611cf872f` |
| 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` | `e2b7e6b0e79a627a2049e5aff16c98b770579afa8cc8791e2d7514bef05a9481` | 2026-08-13 | `2f4fe6a6c7266fea960449fedc98804b15ae72a65abed4632e8dde2ac4624f95` |

Future identity references, duplicate instrument/session rows, and multiple/non-latest revisions: all zero.

## Candidate Coverage

| Metric | Candidate A: 1,751 CS | Candidate B: 1,864 CS+ADRC |
| --- | ---: | ---: |
| 20/20 | 0 | 0 |
| 19/20 | 0 | 0 |
| 18 observations | 1,742 | 1,854 |
| 17 observations | 1 | 2 |
| 16 observations | 1 | 1 |
| 11 observations | 1 | 1 |
| 9 observations | 2 | 2 |
| 8 observations | 2 | 2 |
| 2 observations | 1 | 1 |
| 1 observation | 1 | 1 |
| Missing previous bar | 0 | 0 |
| Previous price gate pass/fail | 1,751 / 0 | 1,864 / 0 |
| Insufficient history | 1,751 | 1,864 |
| Zero-volume observations | 0 | 0 |
| Fractional-volume observations | 31,434 | 33,463 |
| Non-null 20-session median | 0 | 0 |

Candidate A coverage fingerprint: `9f41883d64c0e3b0b99c13ced25131fb312665e8bb3f45a3ccbb055f25de4885`. Candidate B: `382e779aea1e62cfc253bac993a023f30229e52c3196e03f928d0f5f3d906b51`.

## Planning Result and Boundaries

The successful fifth three-session batch leaves two missing EOD sessions, each requiring same-day identity/resolver acquisition. The updated planning estimate is 30–42 requests, with conservative ceiling 42 and one separately authorized final batch. Plan fingerprint: `ae0f1baea4636b1cbb16fd65316733429fecbca718f7b915ceb9c3e28bf6e1c4`.

The pilot and first five batches added only their authorized same-day identity and EOD partitions. No trailing-liquidity dataset or Dashboard result was created; readiness remains `insufficient_history`, and the analysis-day bar remains excluded.
