import { afterEach, describe, expect, it, vi } from 'vitest';

import { getMarketRegimePreview, parseMarketRegimePreview } from './marketRegime';
import { marketRegimeFixture } from '../test/marketRegimeFixture';

describe('Market Regime API parser', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });
  it('accepts the complete stable 16-pair contract', () => {
    const result = parseMarketRegimePreview(marketRegimeFixture());
    expect(result.relationships).toHaveLength(16);
    expect(result.relationships[0].change_summary?.current_state_run_session_count).toBe(3);
    expect(result.regime.composite.dimensions).toHaveLength(5);
  });

  it('rejects malformed additive relationship change evidence', () => {
    const payload = marketRegimeFixture();
    payload.relationships[0].change_summary!.windows[0].leadership_change_1 = 'invalid' as 'strengthening';
    expect(() => parseMarketRegimePreview(payload)).toThrow(/window change/);
  });

  it('accepts only coherent stale-review metadata', () => {
    const payload = marketRegimeFixture();
    payload.as_of_session = '2026-08-24';
    payload.relationships.forEach((item) => { item.change_summary!.as_of_session = payload.as_of_session; });
    payload.data_status = 'stale_review';
    payload.review_deployment = {
      contract_version: 'production-review-deployment/1.0', review_mode: true,
      normal_freshness: false, data_status: 'stale_review',
      approved_as_of_session: payload.as_of_session, expected_latest_session: '2026-08-25',
      expected_lag_sessions: 1,
      explicit_user_acknowledgement: 'I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1',
    };
    expect(parseMarketRegimePreview(payload).data_status).toBe('stale_review');
    payload.review_deployment.expected_lag_sessions = 2 as 1;
    expect(() => parseMarketRegimePreview(payload)).toThrow(/review deployment/);
  });

  it('accepts only the exact second stale-review authorization', () => {
    const payload = marketRegimeFixture();
    payload.as_of_session = '2026-08-26';
    payload.relationships.forEach((item) => { item.change_summary!.as_of_session = payload.as_of_session; });
    payload.data_status = 'stale_review';
    payload.review_deployment = {
      contract_version: 'production-review-deployment/1.1', review_mode: true,
      normal_freshness: false, data_status: 'stale_review',
      approved_as_of_session: '2026-08-26', expected_latest_session: '2026-08-27',
      expected_lag_sessions: 1,
      explicit_user_acknowledgement: 'I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1',
    };
    expect(parseMarketRegimePreview(payload).data_status).toBe('stale_review');
    payload.review_deployment.explicit_user_acknowledgement = 'I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1';
    expect(() => parseMarketRegimePreview(payload)).toThrow(/review deployment/);
  });

  it('rejects partial, reordered, and non-decimal data', () => {
    const partial = marketRegimeFixture(); partial.relationships.pop();
    expect(() => parseMarketRegimePreview(partial)).toThrow(/incomplete/);
    const reordered = marketRegimeFixture(); reordered.relationships[0].definition.registry_order = 9;
    expect(() => parseMarketRegimePreview(reordered)).toThrow(/ordering/);
    const invalid = marketRegimeFixture(); invalid.relationships[0].current.windows[0].relative_return = 'NaN';
    expect(() => parseMarketRegimePreview(invalid)).toThrow(/decimal/);
  });

  it('selects the explicit Universe from a Snapshot 1.5 language-neutral envelope', async () => {
    const primary = marketRegimeFixture();
    const secondary = marketRegimeFixture();
    secondary.selected_universe_id = secondary.available_universes[1].universe_id;
    secondary.regime = { ...secondary.regime, definition: secondary.available_universes[1] };
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      schema_version: '1.0',
      contract_version: 'market-regime-snapshot/1.0',
      default_universe_id: primary.selected_universe_id,
      universe_order: [primary.selected_universe_id, secondary.selected_universe_id],
      records: [primary, secondary],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const result = await getMarketRegimePreview(secondary.selected_universe_id);
    expect(result.selected_universe_id).toBe(secondary.selected_universe_id);
    expect(result.relationships).toHaveLength(16);
    expect(fetchMock).toHaveBeenCalledWith(
      '/private-data/v1/market-regime-overviews.json', expect.anything(),
    );
  });
});
