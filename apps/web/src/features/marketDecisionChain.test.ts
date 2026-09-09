import { describe, expect, it } from 'vitest';

import type { CandidateListItem, OpportunityCandidateResponse } from '../api/opportunityCandidates';
import type { SectorRotationResponse } from '../api/sectorRotation';
import { marketRegimeFixture, PRIMARY_UNIVERSE, SECONDARY_UNIVERSE } from '../test/marketRegimeFixture';
import { buildMarketDecisionChain } from './marketDecisionChain';

const PUBLICATION_ID = '2026-08-21T120000Z-abcdef012345';

function rotation(): SectorRotationResponse {
  const tickers = ['XLC', 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLK', 'XLU'];
  return {
    publication_id: PUBLICATION_ID,
    payload_sha256: '1'.repeat(64), payload_logical_fingerprint: '2'.repeat(64),
    audit_logical_fingerprint: '3'.repeat(64), parameter_fingerprint: '4'.repeat(64),
    history_source_fingerprint: '5'.repeat(64), product_logical_fingerprint: '6'.repeat(64),
    snapshot_logical_fingerprint: '7'.repeat(64), as_of_session: '2026-08-21', input_session_count: 26,
    theme_status: 'unavailable_no_governed_membership', warnings: [],
    records: tickers.map((ticker, index) => ({
      ticker, sector: `Sector ${index}`, registry_order: index, as_of_session: '2026-08-21',
      windows: ([5, 10, 20] as const).map((window, windowIndex) => ({
        window_sessions: window, start_session: '2026-07-17', end_session: '2026-08-21',
        etf_return: '0.0200', spy_return: '0.0100', relative_return: String((11 - index + windowIndex) / 1000),
        relative_rank: index + 1, available_peer_count: 11, availability: 'available' as const, missing_reason: null,
      })) as any,
      five_day_relative_acceleration: '0.0020', posture: 'leading_improving' as const,
      five_day_leadership_run_sessions: 3, run_reaches_history_start: false,
      availability: 'available' as const, missing_reason: null, supporting_fact_codes: [],
      counterevidence_codes: [], warnings: [], logical_fingerprint: String(index).padStart(64, '0'),
    })),
  };
}

function candidate(index: number): CandidateListItem {
  const instrumentId = `${String(index).padStart(8, '0')}-1111-4111-8111-111111111111`;
  return {
    instrument_id: instrumentId, ticker: `NAME${index}`, security_type: 'CS', base_score: String(90 - index),
    latest_price: '100.0000', median_dollar_volume_20: '50000000.0000', data_quality_status: 'passed',
    score_logical_fingerprint: String(index + 1).padStart(64, '0'), entry_geometry_logical_fingerprint: 'a'.repeat(64),
    confidence: { source_completeness: '1.0000', history_completeness: '1.0000', relationship_support: '0.0000', state_confirmation_support: '1.0000', confirmation_session_count: 2, confidence: '1.0000', disclaimer: 'data_support_not_success_probability' },
    state: { final_stage: index % 2 ? 'prepare' : 'watch' },
    risk_dispositions: ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({ risk_mode, eligible: true, risk_adjusted_rank: index + 1, rejection_reason_codes: [] })) as any,
    entry_summary: { review_posture: 'monitor_for_trigger', technical_setup: 'breakout_watch', extension_risk: index % 2 ? 'moderate' : 'low', reference_support_distance_pct: '0.0200' },
    detail_shard_id: 'u0-0', detail_file: 'opportunity-candidate-details-u0-0.json',
  };
}

function candidateResponse(universeId = PRIMARY_UNIVERSE): OpportunityCandidateResponse {
  const candidates = Array.from({ length: 10 }, (_, index) => candidate(index));
  return {
    as_of_session: '2026-08-21', default_universe_id: PRIMARY_UNIVERSE, selected_universe_id: universeId,
    universe_order: [PRIMARY_UNIVERSE, SECONDARY_UNIVERSE], risk_mode_order: ['conservative', 'balanced', 'aggressive'],
    source: {}, warnings: [], logical_fingerprint: 'b'.repeat(64),
    publication_contract_version: 'opportunity-candidate-publication/1.1',
    snapshot_contract_version: 'opportunity-candidate-summary-snapshot/1.0', publication_id: PUBLICATION_ID,
    detail_files: ['opportunity-candidate-details-u0-0.json'],
    universe: {
      universe_id: universeId, universe_member_count: 1718, membership_fingerprint: 'c'.repeat(64),
      bar_covered_member_count: 1716, missing_member_count: 2, quality_counts: {}, stage_counts: {},
      candidate_batch_logical_fingerprint: 'd'.repeat(64), candidates,
      risk_modes: ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({
        risk_mode, eligible_count: 10, rejected_count: 0, display_cap: 50,
        displayed_instrument_ids: candidates.map((item) => item.instrument_id), logical_fingerprint: 'e'.repeat(64),
      })) as any,
    },
  };
}

describe('market-to-candidate decision chain', () => {
  it('keeps market, ETF proxy, and Candidate ranks separate while selecting a concise view', () => {
    const result = buildMarketDecisionChain(marketRegimeFixture(), rotation(), candidateResponse(), 20);
    expect(result.confirmed_market_state).toBe('balanced');
    expect(result.sector_proxies.map((item) => item.ticker)).toEqual(['XLC', 'XLY', 'XLP', 'XLE', 'XLF']);
    expect(result.candidates).toHaveLength(8);
    expect(result.candidates[0].balanced_rank).toBe(1);
    expect(result.candidates[0].item.ticker).toBe('NAME0');
    expect(result.balanced_display_count).toBe(10);
  });

  it('fails closed when session, publication, or Universe bindings differ', () => {
    const wrongSession = candidateResponse(); wrongSession.as_of_session = '2026-08-20';
    expect(() => buildMarketDecisionChain(marketRegimeFixture(), rotation(), wrongSession, 20)).toThrow('sessions');
    const wrongPublication = candidateResponse(); wrongPublication.publication_id = 'other';
    expect(() => buildMarketDecisionChain(marketRegimeFixture(), rotation(), wrongPublication, 20)).toThrow('publications');
    expect(() => buildMarketDecisionChain(marketRegimeFixture(), rotation(), candidateResponse(SECONDARY_UNIVERSE), 20)).toThrow('Universes');
  });
});
