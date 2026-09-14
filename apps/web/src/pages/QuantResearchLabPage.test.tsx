import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { QuantResearchLabPage } from './QuantResearchLabPage';

describe('Quant Research Lab', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?lang=en&view=research');
  });
  afterEach(cleanup);

  it('shows the governed method record without presenting performance', async () => {
    const user = userEvent.setup();
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'Quant Research Lab' })).toBeInTheDocument();
    expect(screen.getByText('DATA BLOCKED')).toBeInTheDocument();
    expect(screen.getByText('METHOD ONLY')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Research input gates' })).toBeInTheDocument();
    expect(screen.getByText('Price history length').parentElement).toHaveTextContent('LENGTH MET');
    expect(screen.getByText('Point-in-time membership').parentElement).toHaveTextContent('INCOMPLETE');
    expect(screen.getByText('Actions & adjustment').parentElement).toHaveTextContent('PARTIAL');
    expect(screen.getByText('Strong-Leader Pullback')).toBeInTheDocument();
    expect(screen.getByText('Not Candidate-eligible')).toBeInTheDocument();
    expect(screen.getByText('No real event study')).toBeInTheDocument();
    expect(screen.queryByText(/Win \/ payoff/)).not.toBeNull();
    expect(screen.queryByText(/annualized return/i)).not.toBeInTheDocument();

    await user.click(screen.getByText(/Inspect complete logic/));
    expect(screen.getByText(/max\(close\[t-20:t-1\]\)/)).toBeInTheDocument();
    expect(screen.getByText('14ff0a8242fda2a7ebe4e0540d114fd4c0b1c821a06c18cf30f9b90070ce31e9')).toBeInTheDocument();
    expect(screen.getByText('ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba')).toBeInTheDocument();
  });

  it('renders the complete research boundary in Chinese', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=zh&view=research');
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: '量化研究实验室' })).toBeInTheDocument();
    expect(screen.getByText('数据尚未达标')).toBeInTheDocument();
    expect(screen.getByText('仅有方法档案')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '研究输入门槛' })).toBeInTheDocument();
    expect(screen.getByText('价格历史长度').parentElement).toHaveTextContent('长度已满足');
    expect(screen.getByText('逐日时点成员资格').parentElement).toHaveTextContent('不完整');
    expect(screen.getByText('强势股回撤')).toBeInTheDocument();
    expect(screen.getByText('不可进入个股候选')).toBeInTheDocument();
    expect(screen.getByText(/股票证据不等于期权表现/)).toBeInTheDocument();
  });

  it('renders natural quantitative-research terminology in Spanish', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=es&view=research');
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'Laboratorio de investigación cuantitativa' })).toBeInTheDocument();
    expect(screen.getByText('DATOS INSUFICIENTES')).toBeInTheDocument();
    expect(screen.getByText('SOLO MÉTODO')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Criterios de admisión de datos' })).toBeInTheDocument();
    expect(screen.getByText('Composición point-in-time').parentElement).toHaveTextContent('INCOMPLETA');
    expect(screen.getByText('No apto para Candidatos')).toBeInTheDocument();
    expect(screen.getByText(/La evidencia de una acción no es rendimiento de opciones/)).toBeInTheDocument();
  });
});
