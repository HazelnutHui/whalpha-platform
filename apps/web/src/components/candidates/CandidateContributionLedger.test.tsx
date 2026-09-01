import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import type { CandidateComponent, CandidateItem } from '../../api/opportunityCandidates';
import { I18nProvider } from '../../i18n/I18nProvider';
import { CandidateContributionLedger } from './CandidateContributionLedger';

function component(component_id: string, effective_weight: string, score: string, contribution: string): CandidateComponent {
  return {
    component_id, configured_weight: effective_weight, effective_weight, score, contribution,
    availability: 'available', cap_applied: null, reason_codes: [],
    metrics: [{ metric_id: component_id === 'market_alignment' ? 'regime_score' : 'current_volume_ratio',
      raw_value: component_id === 'market_alignment' ? '52.0000' : '1.2500', raw_unit: component_id === 'market_alignment' ? 'score' : 'ratio',
      normalized_value: score, availability: 'available', missing_reason: null, evidence_type: 'fact',
      source_sessions: ['2026-08-31'], reason_codes: [] }],
  };
}

const item = {
  base_score: '68.0000', configured_weight_available: '100.0000', missingness_penalty: '0.0000',
  components: [
    component('market_alignment', '12.0000', '50.0000', '6.0000'),
    component('etf_sector_alignment', '13.0000', '50.0000', '6.5000'),
    component('stock_relative_strength', '25.0000', '88.0000', '22.0000'),
    component('trend_quality', '18.0000', '75.0000', '13.5000'),
    component('volume_participation', '12.0000', '50.0000', '6.0000'),
    component('volatility_risk', '10.0000', '60.0000', '6.0000'),
    component('liquidity_suitability', '10.0000', '80.0000', '8.0000'),
  ],
} as CandidateItem;

describe('CandidateContributionLedger', () => {
  beforeEach(() => { window.localStorage.clear(); window.history.replaceState({}, '', '/dashboard/?lang=en'); });
  afterEach(cleanup);

  it('reconciles published points and distinguishes largest support from largest weighted shortfall', () => {
    render(<I18nProvider><CandidateContributionLedger item={item} /></I18nProvider>);
    expect(screen.getByText('Seven published contributions sum to 68')).toBeInTheDocument();
    expect(screen.getByText('Largest score support').parentElement).toHaveTextContent('Stock relative strength');
    expect(screen.getByText('Largest weighted shortfall').parentElement).toHaveTextContent('ETF price-proxy alignment');
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Published base score 68 out of 100, split into seven weighted contributions');
    expect(document.querySelectorAll('.candidate-score-segment')).toHaveLength(7);
  });

  it('keeps raw and normalized evidence folded until requested', () => {
    render(<I18nProvider><CandidateContributionLedger item={item} /></I18nProvider>);
    const summary = screen.getByText('Inspect raw inputs and normalized values');
    expect(summary.closest('details')).not.toHaveAttribute('open');
    fireEvent.click(summary);
    expect(screen.getByText('Current Market Regime score')).toBeInTheDocument();
    expect(screen.getAllByText('Normalized 50').length).toBeGreaterThan(0);
  });
});
