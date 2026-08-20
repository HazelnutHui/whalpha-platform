import { describe, expect, it } from 'vitest';

import { parseDashboardOverview, parseLiquidityMap, parseMovers, parseSnapshotManifest, parseSummary } from './market';
import { demoDashboardData } from '../fixtures/marketDemo';

describe('market API runtime validation', () => {
  it('validates summary payloads', () => {
    expect(parseSummary(demoDashboardData.overview.universes[0].summary).advancer_count).toBe(136);
  });

  it('rejects malformed summary payloads', () => {
    expect(() => parseSummary({ ...demoDashboardData.overview.universes[0].summary, advancer_count: '136' })).toThrow('advancer_count');
  });

  it('validates movers payloads', () => {
    expect(parseMovers(demoDashboardData.overview.universes[0].movers).top_gainers).toHaveLength(10);
  });

  it('validates liquidity map payloads', () => {
    expect(parseLiquidityMap(demoDashboardData.overview.universes[0].trading_activity_map).nodes[0].ticker).toMatch(/^TEST/);
  });

  it('validates Dashboard V1.1 overview payloads', () => {
    const overview = parseDashboardOverview(demoDashboardData.overview);
    expect(overview.default_universe_id).toBe('provider_classified_common_shares_v1');
    expect(overview.universes[0].definition.display_name).toBe('Common Shares');
    expect(overview.governance_status).toBe('provisional_classification');
    expect(overview.sector_benchmarks).toHaveLength(11);
    expect(overview.freshness_status).toBe('stale');
    expect(overview.session_lag).toBe(1);
  });

  it('requires freshness metadata for snapshot contract 1.1', () => {
    expect(() => parseSnapshotManifest({
      snapshot_contract_version: '1.1',
      release_id: '2026-08-14T120000Z-abcdef0',
      generated_at: '2026-08-15T12:00:00Z',
      current_session_date: '2026-08-14',
      previous_session_date: '2026-08-13',
      data_status: 'complete',
      summary_file: 'market-summary.json',
      movers_file: 'movers.json',
      liquidity_map_file: 'liquidity-map.json',
      file_sha256: {},
      summary_node_count: 1,
      mover_gainer_count: 10,
      mover_loser_count: 10,
      liquidity_node_count: 100,
      warning_count: 0,
      is_real_provider_backed: true,
      access_classification: 'private',
      contains_raw_provider_data: false,
      contains_credentials: false,
    })).toThrow('freshness metadata');
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
      overview_file: 'market-overview.json',
      file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64), 'market-overview.json': 'd'.repeat(64) },
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

  it('requires governance metadata for snapshot contract 1.2', () => {
    expect(() => parseSnapshotManifest({
      snapshot_contract_version: '1.2', release_id: '2026-08-14T120000Z-abcdef0', generated_at: '2026-08-15T12:00:00Z',
      current_session_date: '2026-08-14', previous_session_date: '2026-08-13', data_status: 'complete',
      expected_latest_completed_session: '2026-08-14', actual_latest_completed_session: '2026-08-14', session_lag: 0,
      freshness_status: 'fresh', calendar_id: 'XNYS', freshness_checked_at: '2026-08-15T12:00:00Z',
      summary_file: 'market-summary.json', movers_file: 'movers.json', liquidity_map_file: 'liquidity-map.json', file_sha256: {},
      summary_node_count: 1, mover_gainer_count: 10, mover_loser_count: 10, liquidity_node_count: 100, warning_count: 0,
      is_real_provider_backed: true, access_classification: 'private', contains_raw_provider_data: false, contains_credentials: false,
    })).toThrow('governance metadata');
  });

  it('rejects unsafe static snapshot manifests', () => {
    expect(() => parseSnapshotManifest({ snapshot_contract_version: '1', access_classification: 'public' })).toThrow();
  });
});
