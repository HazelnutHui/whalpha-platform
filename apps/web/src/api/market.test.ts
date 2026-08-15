import { describe, expect, it } from 'vitest';

import { parseLiquidityMap, parseMovers, parseSummary } from './market';
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
});
