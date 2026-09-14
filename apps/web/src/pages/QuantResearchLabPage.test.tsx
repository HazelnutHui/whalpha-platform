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
    expect(screen.getByRole('heading', { name: 'Evidence ladder' })).toBeInTheDocument();
    expect(screen.getByText('Method specification').parentElement).toHaveTextContent('FROZEN');
    expect(screen.getByText('Deterministic implementation').parentElement).toHaveTextContent('REPLAYED');
    expect(screen.getByText('Performance-grade admission').parentElement).toHaveTextContent('BLOCKED');
    expect(screen.getByRole('heading', { name: 'Research foundation snapshot' })).toBeInTheDocument();
    expect(screen.getByText('Five-year market base').parentElement).toHaveTextContent('1,255');
    expect(screen.getByText('Historical membership').parentElement).toHaveTextContent('RECONSTRUCTED');
    expect(screen.getByText(/not blended into one readiness percentage/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Method-engineering evidence' })).toBeInTheDocument();
    expect(screen.getAllByText('95.38%')).toHaveLength(2);
    expect(screen.getByText('Declared paths').parentElement).toHaveTextContent('437,402');
    expect(screen.getByText('Computable paths').parentElement).toHaveTextContent('417,209');
    expect(screen.getByText(/not win rate, prediction accuracy, or return/i)).toBeInTheDocument();
    expect(screen.getByText('Strong-Leader Pullback')).toBeInTheDocument();
    expect(screen.getByText('Not Candidate-eligible')).toBeInTheDocument();
    expect(screen.getByText('No real event study')).toBeInTheDocument();
    expect(screen.queryByText(/Win \/ payoff/)).not.toBeNull();
    expect(screen.queryByText(/annualized return/i)).not.toBeInTheDocument();

    await user.click(screen.getByText(/Inspect complete logic/));
    expect(screen.getByText(/max\(close\[t-20:t-1\]\)/)).toBeInTheDocument();
    expect(screen.getByText('4622fb2fe86cc28249f53c89003f450a9e9d19c5696cd4eb865f413140b982c8')).toBeInTheDocument();
    expect(screen.getByText('ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba')).toBeInTheDocument();
    expect(screen.getByText('c082566f283516b9a93d5658832450fb85071a3b59892cb8d922c1f37af34bd8')).toBeInTheDocument();
  });

  it('renders the complete research boundary in Chinese', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=zh&view=research');
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: '量化研究实验室' })).toBeInTheDocument();
    expect(screen.getByText('数据尚未达标')).toBeInTheDocument();
    expect(screen.getByText('仅有方法档案')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '证据阶梯' })).toBeInTheDocument();
    expect(screen.getByText('方法规范').parentElement).toHaveTextContent('已冻结');
    expect(screen.getByText('确定性实现').parentElement).toHaveTextContent('已重放');
    expect(screen.getByText('绩效级数据准入').parentElement).toHaveTextContent('仍阻塞');
    expect(screen.getByRole('heading', { name: '研究基础快照' })).toBeInTheDocument();
    expect(screen.getByText('公司行动').parentElement).toHaveTextContent('4,623 / 4,643');
    expect(screen.getByText(/不会把不同证据强行合成为一个“总完成度”/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '方法工程证据' })).toBeInTheDocument();
    expect(screen.getByText(/不是胜率、预测准确率或收益率/)).toBeInTheDocument();
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
    expect(screen.getByRole('heading', { name: 'Escalera de evidencia' })).toBeInTheDocument();
    expect(screen.getByText('Especificación del método').parentElement).toHaveTextContent('CONGELADA');
    expect(screen.getByText('Admisión para medir rendimiento').parentElement).toHaveTextContent('BLOQUEADA');
    expect(screen.getByRole('heading', { name: 'Resumen de la base de investigación' })).toBeInTheDocument();
    expect(screen.getByText('Ciclo de vida y terminal').parentElement).toHaveTextContent('47 / 65');
    expect(screen.getByText(/no se combinan en un único porcentaje de avance/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Evidencia de ingeniería del método' })).toBeInTheDocument();
    expect(screen.getByText(/no es tasa de acierto, precisión predictiva ni rentabilidad/)).toBeInTheDocument();
    expect(screen.getByText('No apto para Candidatos')).toBeInTheDocument();
    expect(screen.getByText(/La evidencia de una acción no es rendimiento de opciones/)).toBeInTheDocument();
  });
});
