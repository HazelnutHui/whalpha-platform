import { describe, expect, it } from 'vitest';

import { parseDashboardOverview, parseLiquidityMap, parseMovers, parseSnapshotManifest, parseSummary } from './market';
import { demoDashboardData } from '../fixtures/marketDemo';

function formalDashboardOverview() {
  const overview = structuredClone(demoDashboardData.overview);
  overview.data_status = 'complete';
  return overview;
}

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
    const overview = parseDashboardOverview(formalDashboardOverview());
    expect(overview.default_universe_id).toBe('provider_classified_common_shares_v1');
    expect(overview.universes[0].definition.display_name).toBe('Common Shares');
    expect(overview.governance_status).toBe('provisional_classification');
    expect(overview.sector_benchmarks).toHaveLength(11);
    expect(overview.freshness_status).toBe('stale');
    expect(overview.session_lag).toBe(1);
    expect(overview.universes[0].funnel).toHaveLength(10);
  });

  it('rejects a Funnel stage that does not close', () => {
    const invalid = formalDashboardOverview();
    invalid.universes[0].funnel[0].excluded_count += 1;
    expect(() => parseDashboardOverview(invalid)).toThrow('Funnel stage does not close');
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

  it('validates the formal Funnel snapshot contract', () => {
    const base = {
      snapshot_contract_version: '1.4', release_id: '2026-08-19T120000Z-abcdef0',
      generated_at: '2026-08-23T12:00:00Z', current_session_date: '2026-08-19', previous_session_date: '2026-08-18',
      expected_latest_completed_session: '2026-08-19', actual_latest_completed_session: '2026-08-19', session_lag: 0,
      freshness_status: 'fresh', calendar_id: 'XNYS', freshness_checked_at: '2026-08-23T12:00:00Z', data_status: 'complete',
      overview_file: 'market-overview.json', summary_file: 'market-summary.json', movers_file: 'movers.json', liquidity_map_file: 'liquidity-map.json',
      file_sha256: {}, summary_node_count: 1, mover_gainer_count: 10, mover_loser_count: 10, liquidity_node_count: 100, warning_count: 0,
      universe_definition_id: 'dashboard_universe_activation_v2', universe_version: '2.0', governance_status: 'provisional_classification',
      classification_as_of_date: '2026-08-14', evidence_coverage_status: 'provider_form_complete_issuer_structure_provisional',
      selected_universe_id: 'provider_classified_common_shares_v1',
      available_universe_ids: ['provider_classified_common_shares_v1', 'provider_classified_common_shares_plus_adrs_v1'],
      activation_fingerprint: 'a'.repeat(64), membership_evidence_as_of: '2026-08-14',
      funnel_stage_count: 20, funnel_source_fingerprint: 'b'.repeat(64), is_real_provider_backed: true,
      access_classification: 'private', contains_raw_provider_data: false, contains_credentials: false,
    };
    expect(parseSnapshotManifest(base).funnel_stage_count).toBe(20);
    expect(() => parseSnapshotManifest({ ...base, funnel_stage_count: 19 })).toThrow('Funnel');
  });

  it('validates the formal Snapshot 1.5 review contract', () => {
    const base = {
      snapshot_contract_version: '1.5', dashboard_contract_version: '2.2', release_id: '2026-08-24T045652Z-aee1a6ab0f67',
      generated_at: '2026-08-25T04:56:52Z', current_session_date: '2026-08-24', previous_session_date: '2026-08-21',
      expected_latest_completed_session: '2026-08-25', actual_latest_completed_session: '2026-08-24', session_lag: 1,
      freshness_status: 'stale', calendar_id: 'XNYS', freshness_checked_at: '2026-08-25T04:56:52Z', data_status: 'stale_review',
      overview_file: 'market-overview.json', summary_file: 'market-summary.json', movers_file: 'movers.json', liquidity_map_file: 'liquidity-map.json',
      market_intelligence_file: 'market-regime-overviews.json', file_sha256: { 'market-regime-overviews.json': 'c'.repeat(64) },
      summary_node_count: 2, mover_gainer_count: 20, mover_loser_count: 20, liquidity_node_count: 200, warning_count: 0,
      default_universe_id: 'provider_classified_common_shares_v1', universe_definition_id: 'dashboard_universe_activation_v2', universe_version: '2.0',
      governance_status: 'provisional_classification', classification_as_of_date: '2026-08-14', evidence_coverage_status: 'provider_form_complete_issuer_structure_provisional',
      selected_universe_id: 'provider_classified_common_shares_v1',
      available_universe_ids: ['provider_classified_common_shares_v1', 'provider_classified_common_shares_plus_adrs_v1'],
      activation_fingerprint: 'a'.repeat(64), membership_evidence_as_of: '2026-08-14', funnel_stage_count: 20, funnel_source_fingerprint: 'b'.repeat(64),
      market_intelligence_publication_id: '2026-08-24T043223Z-aee1a6ab0f67', market_intelligence_payload_sha256: 'd'.repeat(64),
      market_intelligence_logical_fingerprint: 'e'.repeat(64), analytics_payload_logical_fingerprint: 'f'.repeat(64),
      review_mode: true, review_contract_version: 'production-review-deployment/1.0', review_approved_as_of_session: '2026-08-24',
      review_expected_latest_session: '2026-08-25', review_expected_lag_sessions: 1,
      is_real_provider_backed: true, access_classification: 'private', contains_raw_provider_data: false, contains_credentials: false,
    };
    expect(parseSnapshotManifest(base).dashboard_contract_version).toBe('2.2');
    expect(() => parseSnapshotManifest({ ...base, dashboard_contract_version: '2.3' })).toThrow('Market Intelligence metadata');
    expect(() => parseSnapshotManifest({ ...base, review_expected_lag_sessions: 2 })).toThrow('review deployment');
    expect(() => parseSnapshotManifest({ ...base, market_intelligence_payload_sha256: 12 })).toThrow('market_intelligence_payload_sha256');
    expect(() => parseSnapshotManifest({ ...base, snapshot_contract_version: '1.6', dashboard_contract_version: '2.3' })).toThrow('Candidate metadata');
    expect(() => parseSnapshotManifest({ ...base, market_intelligence_publication_id: undefined })).toThrow('Market Intelligence metadata');
  });

  it('accepts the explicit stale-review overview and rejects unknown status or contract values', () => {
    const review = formalDashboardOverview();
    review.contract_version = '2.1';
    review.data_status = 'stale_review';
    review.review_mode = true;
    review.review_contract_version = 'production-review-deployment/1.0';
    review.review_approved_as_of_session = review.current_session_date;
    review.review_expected_latest_session = '2026-08-25';
    review.review_expected_lag_sessions = 1;
    review.actual_latest_completed_session = review.current_session_date;
    review.expected_latest_completed_session = '2026-08-25';
    review.session_lag = 1;
    review.freshness_status = 'stale';
    expect(parseDashboardOverview(review).data_status).toBe('stale_review');
    expect(() => parseDashboardOverview({ ...review, data_status: 'unknown_review' })).toThrow('data_status');
    expect(() => parseDashboardOverview({ ...review, contract_version: '2.2' })).toThrow('Unsupported market Dashboard contract');
    expect(() => parseDashboardOverview({ ...review, review_mode: false, review_contract_version: null,
      review_approved_as_of_session: null, review_expected_latest_session: null, review_expected_lag_sessions: null })).toThrow('unexpected review deployment');
  });

  it('rejects synthetic Dashboard responses at the formal API boundary', () => {
    expect(() => parseDashboardOverview({
      ...formalDashboardOverview(),
      data_status: 'synthetic_demo',
    })).toThrow('data_status');
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
