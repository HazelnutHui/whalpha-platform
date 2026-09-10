import { describe, expect, it } from 'vitest';

import { catalogs, loadCatalog, type MessageCatalog, type MessageKey } from './catalog';
import {
  dimensionName,
  familyName,
  pairText,
  reasonText,
  relationshipName,
  stateName,
  universeName,
} from './domain';
import type { Translate } from './I18nProvider';

const translate = (locale: 'en' | 'zh'): Translate => (key: MessageKey, values = {}) =>
  catalogs[locale][key].replace(/\{([A-Za-z0-9_]+)\}/g, (match, value: string) =>
    Object.prototype.hasOwnProperty.call(values, value) ? String(values[value]) : match,
  );
const translateCatalog = (catalog: MessageCatalog): Translate => (key: MessageKey, values = {}) =>
  catalog[key].replace(/\{([A-Za-z0-9_]+)\}/g, (match, value: string) =>
    Object.prototype.hasOwnProperty.call(values, value) ? String(values[value]) : match,
  );

describe('localized analytics domain mappings', () => {
  it('maps every user-visible formal reason code in the frozen preview in both languages', () => {
    const reasons = [
      'state_input_available', 'candidate_band_balanced', 'confirmed_state_held', 'dimension_available',
      'both_five_session_returns_negative', 'both_five_session_returns_positive',
      'positive_correlation_threshold_met', 'five_session_spread_threshold_met', 'opposite_return_signs',
      'no_higher_priority_relationship_rule_met', 'confidence_low',
    ];
    for (const code of reasons) {
      expect(reasonText(translate('en'), code)).not.toBe(catalogs.en['reason.unknown']);
      expect(reasonText(translate('zh'), code)).not.toBe(catalogs.zh['reason.unknown']);
      expect(reasonText(translate('zh'), code)).not.toBe(code);
    }
  });

  it('maps both universes, four regime states, five dimensions, relationship states, and families', () => {
    const zh = translate('zh');
    expect(universeName(zh, 'provider_classified_common_shares_v1')).toBe('普通股');
    expect(universeName(zh, 'provider_classified_common_shares_plus_adrs_v1')).toBe('普通股 + 美国存托凭证');
    for (const state of ['risk_on', 'balanced', 'defensive', 'stress']) expect(stateName(zh, state)).not.toBe(state);
    for (const dimension of ['trend', 'breadth', 'volatility', 'liquidity_participation', 'leadership_dispersion']) expect(dimensionName(zh, dimension)).not.toBe(dimension);
    for (const state of ['synchronous_strengthening', 'synchronous_weakening', 'divergence', 'rotation_candidate', 'relationship_break_candidate', 'neutral']) expect(relationshipName(zh, state)).not.toBe(state);
    for (const family of ['growth_vs_broad', 'style_rotation', 'size_participation', 'cyclical_defensive', 'sector_relative', 'defensive_relative', 'industry_within_growth', 'industry_within_sector', 'credit_risk', 'credit_vs_duration']) expect(familyName(zh, family)).not.toBe(family);
  });

  it('provides localized fixed copy for all 16 preregistered pairs', () => {
    const pairIds = [
      'growth_broad', 'growth_value', 'small_large', 'mid_large', 'consumer_risk', 'technology_defensive',
      'industrial_defensive', 'financial_defensive', 'energy_broad', 'health_broad', 'semis_growth',
      'biotech_health', 'regional_financials', 'software_growth', 'credit_quality', 'credit_duration',
    ];
    for (const pairId of pairIds) {
      for (const field of ['rationale', 'expected', 'forbidden'] as const) {
        const fallback = `UNTRANSLATED ${pairId} ${field}`;
        expect(pairText(translate('en'), pairId, field, fallback)).not.toBe(fallback);
        expect(pairText(translate('zh'), pairId, field, fallback)).not.toBe(fallback);
      }
    }
  });

  it('provides Spanish domain terms for governed market concepts', async () => {
    const spanish = await loadCatalog('es');
    const es = translateCatalog(spanish);
    expect(universeName(es, 'provider_classified_common_shares_v1')).toBe('Acciones ordinarias');
    expect(stateName(es, 'defensive')).toBe('Defensivo');
    expect(dimensionName(es, 'leadership_dispersion')).toBe('Liderazgo / Dispersión');
    expect(relationshipName(es, 'rotation_candidate')).toBe('Candidato de rotación');
    expect(familyName(es, 'credit_vs_duration')).toBe('Crédito frente a duración');
  });
});
