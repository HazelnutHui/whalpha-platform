import { describe, expect, it } from 'vitest';

import { parseSectorRotation } from './sectorRotation';

const SHA = 'a'.repeat(64);
const TICKERS = ['XLC', 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLK', 'XLU'];

function fixture(): Record<string, unknown> {
  const records = TICKERS.map((ticker, index) => ({
    ticker, sector: `Sector ${index}`, registry_order: index,
    as_of_session: '2026-08-28',
    windows: ([5, 10, 20] as const).map((window) => ({
      window_sessions: window, start_session: '2026-08-01', end_session: '2026-08-28',
      etf_return: '0.02', spy_return: '0.01', relative_return: '0.01',
      relative_rank: index + 1, available_peer_count: 11,
      availability: 'available', missing_reason: null,
    })),
    five_day_relative_acceleration: '0.002', posture: 'leading_improving',
    five_day_leadership_run_sessions: 3, run_reaches_history_start: false,
    availability: 'available', missing_reason: null,
    supporting_fact_codes: ['relative_leadership_20_positive'], counterevidence_codes: [],
    warnings: ['price_return_not_fund_flow'], logical_fingerprint: SHA,
  }));
  const product = {
    schema_version: '1.0', contract_version: 'sector-etf-rotation/1.0',
    calculation_version: 'sector-etf-rotation-v1.0.0',
    parameter_set_id: 'sector-etf-rotation-fixed-registry-1', parameter_fingerprint: SHA,
    as_of_session: '2026-08-28', input_first_session: '2026-07-24',
    input_last_session: '2026-08-28', input_session_count: 26, benchmark_ticker: 'SPY',
    records, theme_status: 'unavailable_no_governed_membership',
    source_history_fingerprint: SHA, warnings: ['price_return_not_fund_flow'],
    logical_fingerprint: SHA,
  };
  return {
    schema_version: '1.0', contract_version: 'sector-etf-rotation-dashboard-snapshot/1.0',
    market_intelligence_contract_version: 'market-intelligence-publication/1.3',
    publication_id: '2026-08-28T120000Z-abcdef0', payload_sha256: SHA,
    payload_logical_fingerprint: SHA,
    source: {
      audit_contract_version: 'sector-etf-rotation-audit/1.0', audit_manifest_sha256: SHA,
      audit_logical_fingerprint: SHA, phase1a_audit_logical_fingerprint: SHA,
      phase1a_manifest_sha256: SHA, product_contract_version: 'sector-etf-rotation/1.0',
      calculation_version: 'sector-etf-rotation-v1.0.0', parameter_fingerprint: SHA,
      history_source_fingerprint: SHA, product_logical_fingerprint: SHA,
      record_count: 11, oracle_mismatch_count: 0,
      theme_status: 'unavailable_no_governed_membership',
    },
    product, language_neutral: true, fixed_sector_etf_proxy_only: true,
    constituent_breadth_unavailable: true, fund_flow_claim_prohibited: true,
    theme_membership_unavailable: true, guest_and_credential_capability_identical: true,
    logical_fingerprint: SHA,
  };
}

describe('Sector Rotation lazy payload validation', () => {
  it('keeps separate windows, fixed registry, and proxy limits', () => {
    const parsed = parseSectorRotation(fixture());
    expect(parsed.records).toHaveLength(11);
    expect(parsed.records[0].windows.map((item) => item.window_sessions)).toEqual([5, 10, 20]);
    expect(parsed.theme_status).toBe('unavailable_no_governed_membership');
    expect(JSON.stringify(parsed)).not.toContain('score');
  });

  it('fails closed on registry, Oracle, or source drift', () => {
    const registry = fixture() as any; registry.product.records[0].ticker = 'FAKE';
    expect(() => parseSectorRotation(registry)).toThrow('registry');
    const oracle = fixture() as any; oracle.source.oracle_mismatch_count = 1;
    expect(() => parseSectorRotation(oracle)).toThrow('Unsupported');
    const lineage = fixture() as any; lineage.source.product_logical_fingerprint = 'b'.repeat(64);
    expect(() => parseSectorRotation(lineage)).toThrow('source binding');
  });
});
