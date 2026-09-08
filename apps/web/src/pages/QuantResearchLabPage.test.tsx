import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { QuantResearchLabPage } from './QuantResearchLabPage';

describe('Quant Research Lab', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?lang=en&view=research');
  });
  afterEach(cleanup);

  it('shows research readiness without presenting fixture performance', () => {
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'Quant Research Lab' })).toBeInTheDocument();
    expect(screen.getByText('DATA BLOCKED')).toBeInTheDocument();
    expect(screen.getByText('INPUT GATES')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Research input gates' })).toBeInTheDocument();
    expect(screen.getByText('Price history length').parentElement).toHaveTextContent('LENGTH MET');
    expect(screen.getByText('Point-in-time membership').parentElement).toHaveTextContent('INCOMPLETE');
    expect(screen.queryByText('31 / 252')).not.toBeInTheDocument();
    expect(screen.getByText(/Readiness is not confidence/)).toBeInTheDocument();
    expect(screen.getByText('Strong-Leader Pullback')).toBeInTheDocument();
    expect(screen.getByText('Sealed · not evaluated')).toBeInTheDocument();
    expect(screen.queryByText(/win rate/i)).not.toBeNull();
    expect(screen.queryByText(/annualized return/i)).not.toBeInTheDocument();
  });

  it('renders the complete research boundary in Chinese', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=zh&view=research');
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: '量化研究实验室' })).toBeInTheDocument();
    expect(screen.getByText('数据尚未达标')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '研究输入门槛' })).toBeInTheDocument();
    expect(screen.getByText('价格历史长度').parentElement).toHaveTextContent('长度已满足');
    expect(screen.getByText('逐日时点成员资格').parentElement).toHaveTextContent('不完整');
    expect(screen.getByText('强势股回撤')).toBeInTheDocument();
    expect(screen.getByText(/股票证据不等于期权表现/)).toBeInTheDocument();
  });
});
