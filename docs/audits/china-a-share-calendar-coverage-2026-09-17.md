# China A-Share Pilot Calendar Coverage Audit — 2026-09-17

## Scope

This diagnostic compared the exactly reread five-year daily pilot with the
offline `XSHG` calendar from `exchange-calendars` 4.13.2. It made no provider
request, retained no new upstream payload, wrote no canonical data, and granted
no research, Product, publication, or deployment authority.

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

## Official evidence boundary

SSE and SZSE publish annual closure arrangements. The reviewed official entry
points include the [SSE annual closure archive](https://www.sse.com.cn/disclosure/dealinstruc/closed/),
the [SSE 2021 schedule](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20201224_5286951.shtml),
the [SSE 2026 notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml),
the [SZSE 2021 notice](https://www.szse.cn/disclosure/notice/general/t20201224_583950.html),
and the [SZSE 2026 notice](https://www.szse.cn/disclosure/notice/t20251222_618087.html).
The notices confirm that weekdays are trading days except statutory holidays
and exchange-announced closures, but their exact bytes and the complete
2021–2026 closure-date transcription have not yet entered retained pilot
custody.

Consequently:

- library/source-state alignment is complete for the bounded six-security
  pilot;
- official exchange notice retention is false;
- machine reconciliation against exact official closure dates is false;
- BSE calendar coverage is not evaluated because the BSE daily anchor remains
  quarantined; and
- the calendar family and research backtest admission remain false.

## Verdict

`CALENDAR_LIBRARY_SOURCE_ALIGNMENT_COMPLETE_OFFICIAL_EVIDENCE_PENDING`

The next calendar action is a bounded exact capture of the SSE/SZSE annual
notices and deterministic reconciliation of all weekday closures over the
pilot interval. This is separate from price-limit, action, adjustment, fee,
and historical-Universe qualification.
