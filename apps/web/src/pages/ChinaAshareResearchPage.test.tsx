import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { ChinaAshareResearchPage } from './ChinaAshareResearchPage';

describe('China A-share research foundation', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?lang=en&view=research&universe=china_a_share_research_foundation_v1');
  });
  afterEach(cleanup);

  it('presents a truthful A-share foundation and its market-specific execution boundary', () => {
    render(<I18nProvider><ChinaAshareResearchPage view="research" /></I18nProvider>);

    expect(screen.getByRole('heading', { name: 'A-share research foundation' })).toBeInTheDocument();
    expect(screen.getAllByText('FOUNDATION · NOT ADMITTED').length).toBeGreaterThan(0);
    expect(screen.getByText('Official warning-document adjudication')).toBeInTheDocument();
    expect(screen.getByText('Full-population diagnostic').parentElement).toHaveTextContent('REPLAYED');
    expect(screen.getByText('Daily evidence').parentElement).toHaveTextContent('5,987,288 BARS');
    expect(screen.getByText('Provisional states').parentElement).toHaveTextContent('5,059,363');
    expect(screen.getByText('Warning search').parentElement).toHaveTextContent('492 / 492');
    expect(screen.getByText('Warning search').parentElement).toHaveTextContent('0 adjudicated events');
    expect(screen.getByRole('heading', { name: 'A-share-specific execution layer' })).toBeInTheDocument();
    expect(screen.getByText('T+1 inventory').parentElement).toHaveTextContent('shares bought today cannot be assumed sellable the same day');
    expect(screen.getByText('Locked-limit fills').parentElement).toHaveTextContent('Daily bars cannot claim a queue position');
    expect(screen.getByText('Long-only reality').parentElement).toHaveTextContent('cannot assume universal stock borrow');
    expect(screen.getByRole('heading', { name: 'Research mechanisms tailored to A-shares' })).toBeInTheDocument();
    expect(screen.getByText('Three return layers').parentElement).toHaveTextContent('cannot substitute for one another');
    expect(screen.getByText('Publication-time discipline')).toBeInTheDocument();
    expect(screen.getByText('Complete 13-family admission')).toBeInTheDocument();
    expect(screen.getAllByText(/Fetch and hash the official warning documents/)).toHaveLength(2);
    expect(screen.getByText(/grants no backtest, model, candidate/)).toBeInTheDocument();
  });

  it('keeps the A-share candidate destination empty until both Universe and model admission', () => {
    render(<I18nProvider><ChinaAshareResearchPage view="candidates" /></I18nProvider>);

    expect(screen.getByRole('heading', { name: 'A-share model-driven selection' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'The A-share stock-pool destination is visible—but empty by design' })).toBeInTheDocument();
    expect(screen.getByText('Admitted Universe').parentElement).toHaveTextContent('0');
    expect(screen.getByText('Active rankings').parentElement).toHaveTextContent('0');
    expect(screen.getByText('Validated models').parentElement).toHaveTextContent('0');
    expect(screen.getByText('Governed targets').parentElement).toHaveTextContent('5,409');
    expect(screen.getAllByText(/not a demonstration ranking/).length).toBeGreaterThan(0);
  });

  it('uses precise Chinese terminology for A-share mechanics and readiness', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=zh&view=research&universe=china_a_share_research_foundation_v1');
    render(<I18nProvider><ChinaAshareResearchPage view="research" /></I18nProvider>);

    expect(screen.getByRole('heading', { name: 'A 股量化研究基础' })).toBeInTheDocument();
    expect(screen.getAllByText('基础建设中 · 尚未准入').length).toBeGreaterThan(0);
    expect(screen.getByText('T+1 持仓约束')).toBeInTheDocument();
    expect(screen.getByText('封板成交')).toBeInTheDocument();
    expect(screen.getByText('点时股票池')).toBeInTheDocument();
    expect(screen.getByText('A 股横截面标准化')).toBeInTheDocument();
    expect(screen.getByText('全量诊断').parentElement).toHaveTextContent('重放通过');
    expect(screen.getByText('日频证据').parentElement).toHaveTextContent('5,987,288 条');
    expect(screen.getByText('重建候选状态').parentElement).toHaveTextContent('5,059,363 条');
    expect(screen.queryByText(/不会用示例分数伪装成真实排名/)).not.toBeInTheDocument();
  });

  it('keeps the Spanish view semantically aligned', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=es&view=candidates&universe=china_a_share_research_foundation_v1');
    render(<I18nProvider><ChinaAshareResearchPage view="candidates" /></I18nProvider>);

    expect(screen.getByRole('heading', { name: 'Selección de acciones A basada en modelos' })).toBeInTheDocument();
    expect(screen.getAllByText('BASE · NO ADMITIDA').length).toBeGreaterThan(0);
    expect(screen.getByText('Inventario T+1')).toBeInTheDocument();
    expect(screen.getByText('Universo point-in-time')).toBeInTheDocument();
    expect(screen.getByText(/no puede mostrar rankings/)).toBeInTheDocument();
  });
});
