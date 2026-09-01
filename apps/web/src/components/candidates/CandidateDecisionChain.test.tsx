import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import type { CandidateItem } from '../../api/opportunityCandidates';
import { I18nProvider } from '../../i18n/I18nProvider';
import { CandidateDecisionChain } from './CandidateDecisionChain';

const baseItem = {
  primary_driver_ticker: 'SMH', driver_correlation_20: '0.6700', relationship_kind: 'price_derived_exposure_proxy',
  components: [
    { component_id: 'market_alignment', score: '48.9000', contribution: '5.8680' },
    { component_id: 'etf_sector_alignment', score: '62.0000', contribution: '8.0600' },
    { component_id: 'stock_relative_strength', score: '84.0000', contribution: '21.0000' },
    { component_id: 'trend_quality', score: '76.0000', contribution: '13.6800' },
  ],
  entry_geometry: {
    review_posture: 'monitor_for_trigger', technical_setup: 'breakout_watch', extension_risk: 'moderate',
    technical_invalidation_codes: ['candidate_state_invalidated', 'trend_component_below_50', 'close_below_reference_support_requires_reunderwrite'],
  },
} as CandidateItem;

describe('CandidateDecisionChain', () => {
  beforeEach(() => { window.localStorage.clear(); window.history.replaceState({}, '', '/dashboard/?lang=en'); });
  afterEach(cleanup);

  it('links only published facts and labels the ETF relationship as a price proxy', () => {
    render(<I18nProvider><CandidateDecisionChain item={baseItem} /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'From market context to trade review' })).toBeInTheDocument();
    expect(screen.getByText('SMH')).toBeInTheDocument();
    expect(screen.getByText(/Price-derived, not sector membership/)).toBeInTheDocument();
    expect(screen.getByText('Relative strength 84 · Trend 76')).toBeInTheDocument();
    expect(screen.getByText('Monitor for trigger')).toBeInTheDocument();
    expect(screen.getByText(/close below the descriptive reference support/)).toBeInTheDocument();
    expect(screen.getByText(/not a taxonomy or fund-flow claim/)).toBeInTheDocument();
  });

  it('fails closed rather than inferring a sector when no registered proxy qualifies', () => {
    const item = { ...baseItem, primary_driver_ticker: null, driver_correlation_20: null, relationship_kind: null } as CandidateItem;
    render(<I18nProvider><CandidateDecisionChain item={item} /></I18nProvider>);
    expect(screen.getByText(/No registered ETF met the fixed direction/)).toBeInTheDocument();
    expect(screen.queryByText(/sector membership\./)).not.toBeInTheDocument();
  });
});
