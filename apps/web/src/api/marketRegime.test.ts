import { describe, expect, it } from 'vitest';

import { parseMarketRegimePreview } from './marketRegime';
import { marketRegimeFixture } from '../test/marketRegimeFixture';

describe('Market Regime API parser', () => {
  it('accepts the complete stable 16-pair contract', () => {
    const result = parseMarketRegimePreview(marketRegimeFixture());
    expect(result.relationships).toHaveLength(16);
    expect(result.regime.composite.dimensions).toHaveLength(5);
  });

  it('rejects partial, reordered, and non-decimal data', () => {
    const partial = marketRegimeFixture(); partial.relationships.pop();
    expect(() => parseMarketRegimePreview(partial)).toThrow(/incomplete/);
    const reordered = marketRegimeFixture(); reordered.relationships[0].definition.registry_order = 9;
    expect(() => parseMarketRegimePreview(reordered)).toThrow(/ordering/);
    const invalid = marketRegimeFixture(); invalid.relationships[0].current.windows[0].relative_return = 'NaN';
    expect(() => parseMarketRegimePreview(invalid)).toThrow(/decimal/);
  });
});
