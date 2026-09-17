# China A-Share Pilot Calendar Coverage Audit — 2026-09-17

## Scope

The first diagnostic compared the exactly reread five-year daily pilot with
the offline `XSHG` calendar from `exchange-calendars` 4.13.2. A bounded
follow-up then retained the exact public SSE/SZSE annual-notice payloads and
machine-reconciled their weekday closures. Neither step wrote canonical data
or granted research, Product, publication, or deployment authority.

## Exact result

- interval: 2021-09-16 through 2026-09-16;
- calendar timezone: `Asia/Shanghai`;
- expected calendar sessions: 1,211;
- source-state union sessions: 1,211;
- bound pilot securities evaluated: six;
- each security contains exactly 1,211 source-state dates;
- missing calendar sessions: zero; and
- unexpected non-calendar state dates: zero.

The diagnostic logical fingerprint is
`1ed79cc8c0d0fedc8e31e3eb114e6639c02c7360747edc9f920d3711383c2ed3`.
It is a reproducible in-memory diagnostic, not an immutable official-calendar
package.

## Official evidence capture

SSE and SZSE publish annual closure arrangements. The reviewed official entry
points include the [SSE annual closure archive](https://www.sse.com.cn/disclosure/dealinstruc/closed/),
the [SSE 2021 schedule](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20201224_5286951.shtml),
the [SSE 2026 notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml),
the [SZSE 2021 notice](https://www.szse.cn/disclosure/notice/general/t20201224_583950.html),
and the [SZSE 2026 notice](https://www.szse.cn/disclosure/notice/t20251222_618087.html).
The bounded follow-up retained all 12 exact annual-notice HTML payloads in an
owner-only immutable package, along with their physical hashes, typed closure
ranges, normalized weekday closures, plan, report, and manifest. The package
contains 16 files / 338,354 bytes and passed a complete byte/hash/schema/mode/
file-set reread.

For the pilot interval, deterministic reconciliation produced:

- 94 official weekday closure dates;
- zero SSE-only or SZSE-only closure dates;
- zero `XSHG` weekday closures absent from official evidence;
- zero official weekday closures absent from `XSHG`; and
- unchanged zero missing/unexpected dates across all six source-state histories.

The report logical fingerprint is
`8cb38cbe307908ffbe6fdb62e1ce9670053d65cd7982daa28a2dcd30fe270ff7`;
the package logical fingerprint is
`55e786a6165fdf747ced32352b055b7daedf550b4870a92875d077b434170f00`.

Consequently, the SSE/SZSE calendar family is reconciled for the exact pilot
interval and population. BSE calendar coverage is not evaluated because its
daily anchor remains quarantined. Price limits, actions, adjustment return
semantics, fees, historical Universe, full-market expansion, and complete
13-family admission remain false; calendar qualification alone grants no
research backtest authority.

## Verdict

`SSE_SZSE_PILOT_CALENDAR_OFFICIAL_EVIDENCE_RECONCILED`

The next foundation action is effective-dated price-limit and trading-rule
qualification. Calendar evidence must not be used to imply those independent
families are complete.
