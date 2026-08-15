import { describe, expect, it } from 'vitest';

import { parseLiquidityMap, parseMovers, parseSnapshotManifest, parseSummary } from './market';
import { demoDashboardData } from '../fixtures/marketDemo';

describe('market API runtime validation', () => {
  it('validates summary payloads', () => {
    expect(parseSummary(demoDashboardData.summary).advancer_count).toBe(136);
  });

  it('rejects malformed summary payloads', () => {
    expect(() => parseSummary({ ...demoDashboardData.summary, advancer_count: '136' })).toThrow('advancer_count');
  });

  it('validates movers payloads', () => {
    expect(parseMovers(demoDashboardData.movers).top_gainers).toHaveLength(10);
  });

  it('validates liquidity map payloads', () => {
    expect(parseLiquidityMap(demoDashboardData.liquidityMap).nodes[0].ticker).toMatch(/^TEST/);
  });

  it('validates static snapshot manifests', () => {
    const manifest = parseSnapshotManifest({
      snapshot_contract_version: '1',
      release_id: '2026-08-13T120000Z-abcdef0',
      generated_at: '2026-08-15T12:00:00Z',
      current_session_date: '2026-08-13',
      previous_session_date: '2026-08-12',
      data_status: 'complete',
      summary_file: 'market-summary.json',
      movers_file: 'movers.json',
      liquidity_map_file: 'liquidity-map.json',
      file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64) },
      summary_node_count: 1,
      mover_gainer_count: 10,
      mover_loser_count: 10,
      liquidity_node_count: 300,
      warning_count: 4,
      is_real_provider_backed: true,
      access_classification: 'private',
      contains_raw_provider_data: false,
      contains_credentials: false,
    });
    expect(manifest.snapshot_contract_version).toBe('1');
  });

  it('rejects unsafe static snapshot manifests', () => {
    expect(() => parseSnapshotManifest({ snapshot_contract_version: '1', access_classification: 'public' })).toThrow();
  });
});
