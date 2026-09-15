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

  it('shows the three-layer research boundary without presenting performance', async () => {
    const user = userEvent.setup();
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'Quant Research Lab' })).toBeInTheDocument();
    expect(screen.getByText('FACTOR DISCOVERY V1')).toBeInTheDocument();
    expect(screen.getByText('OUTCOME BLIND')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'From measurement to a decision—without collapsing the evidence.' })).toBeInTheDocument();
    expect(screen.getByText('Factor Discovery').parentElement).toHaveTextContent('CURRENT · OUTCOME BLIND');
    expect(screen.getByText('Model Construction').parentElement).toHaveTextContent('LOCKED');
    expect(screen.getByText('Strategy Expression').parentElement).toHaveTextContent('LOCKED');
    expect(screen.getByText(/A factor is not a model/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Evidence ladder' })).toBeInTheDocument();
    expect(screen.getByText('Three-layer architecture').parentElement).toHaveTextContent('ACCEPTED');
    expect(screen.getAllByText('Factor Catalog V1')[0].parentElement).toHaveTextContent('REGISTERED');
    expect(screen.getByText('Coverage & redundancy').parentElement).toHaveTextContent('REPLAYED');
    expect(screen.getByText('Screening protocol').parentElement).toHaveTextContent('NEXT');
    expect(screen.getByText('Strategy expression & Product').parentElement).toHaveTextContent('LOCKED');
    expect(screen.getByRole('heading', { name: 'Research foundation snapshot' })).toBeInTheDocument();
    expect(screen.getByText('Five-year market base').parentElement).toHaveTextContent('1,255');
    expect(screen.getByText('Historical membership').parentElement).toHaveTextContent('RECONSTRUCTED');
    expect(screen.getByText('Lifecycle & terminal').parentElement).toHaveTextContent('219 + 83');
    expect(screen.getByText(/not blended into one readiness percentage/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Factor qualification V1' })).toBeInTheDocument();
    expect(screen.getByText('95.74%')).toBeInTheDocument();
    expect(screen.getByText('Complete vectors').parentElement).toHaveTextContent('418,756');
    expect(screen.getByText('Pair checks').parentElement).toHaveTextContent('66');
    expect(screen.getByText('Near-duplicate groups').parentElement).toHaveTextContent('0');
    expect(screen.getByText(/No pair crossed the frozen near-duplicate rule/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Method-engineering evidence' })).toBeInTheDocument();
    expect(screen.getByText('95.38%')).toBeInTheDocument();
    expect(screen.getByText('Declared paths').parentElement).toHaveTextContent('437,402');
    expect(screen.getByText('Computable paths').parentElement).toHaveTextContent('417,209');
    expect(screen.getByText(/not win rate, prediction accuracy, or return/i)).toBeInTheDocument();
    expect(screen.getByText(/only registered replacement was rejected/i)).toBeInTheDocument();
    expect(screen.getByText('Strong-Leader Pullback')).toBeInTheDocument();
    expect(screen.getByText('Not Candidate-eligible')).toBeInTheDocument();
    expect(screen.getByText('Pullback replacement').parentElement).toHaveTextContent('Rejected · endpoint instability');
    expect(screen.getByText('Active models').parentElement).toHaveTextContent('None');
    expect(screen.queryByText(/win\/payoff\/PF/i)).not.toBeNull();
    expect(screen.queryByText(/annualized return/i)).not.toBeInTheDocument();

    await user.click(screen.getByText(/Inspect complete logic/));
    expect(screen.getByText(/max\(close\[t-20:t-1\]\)/)).toBeInTheDocument();
    expect(screen.getByText('4622fb2fe86cc28249f53c89003f450a9e9d19c5696cd4eb865f413140b982c8')).toBeInTheDocument();
    expect(screen.getByText('ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba')).toBeInTheDocument();
    expect(screen.getByText('c082566f283516b9a93d5658832450fb85071a3b59892cb8d922c1f37af34bd8')).toBeInTheDocument();

    await user.click(screen.getByText(/Inspect all 12 registered definitions/));
    expect(screen.getByText('20-session relative return versus SPY')).toBeInTheDocument();
    expect(screen.getByText('ln(C[t]/C[t-20]) - ln(B[t]/B[t-20])')).toBeInTheDocument();
  });

  it('renders the complete research boundary in Chinese', () => {
    window.history.replaceState({}, '', '/dashboard/?lang=zh&view=research');
    render(<I18nProvider><QuantResearchLabPage /></I18nProvider>);
    expect(screen.getByRole('heading', { name: '量化研究实验室' })).toBeInTheDocument();
    expect(screen.getByText('因子发现 V1')).toBeInTheDocument();
    expect(screen.getByText('不读取结果')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '从测量到决策，每一层证据都保持独立。' })).toBeInTheDocument();
    expect(screen.getByText('因子发现层').parentElement).toHaveTextContent('当前阶段 · 不读取结果');
    expect(screen.getByText('模型构建层').parentElement).toHaveTextContent('保持锁定');
    expect(screen.getByText('策略表达层').parentElement).toHaveTextContent('保持锁定');
    expect(screen.getByRole('heading', { name: '证据阶梯' })).toBeInTheDocument();
    expect(screen.getByText('三层研究架构').parentElement).toHaveTextContent('已生效');
    expect(screen.getAllByText('因子目录 V1')[0].parentElement).toHaveTextContent('已登记');
    expect(screen.getByText('覆盖与冗余诊断').parentElement).toHaveTextContent('已重放');
    expect(screen.getByText('筛选协议').parentElement).toHaveTextContent('下一步');
    expect(screen.getByRole('heading', { name: '研究基础快照' })).toBeInTheDocument();
    expect(screen.getByText('公司行动').parentElement).toHaveTextContent('4,623 / 4,643');
    expect(screen.getByText(/不会把不同证据强行合成为一个“总完成度”/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '因子资格诊断 V1' })).toBeInTheDocument();
    expect(screen.getByText('完整向量').parentElement).toHaveTextContent('418,756');
    expect(screen.getByText(/这一结论不代表存在预测价值/)).toBeInTheDocument();
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
    expect(screen.getByText('DESCUBRIMIENTO DE FACTORES V1')).toBeInTheDocument();
    expect(screen.getByText('SIN RESULTADOS')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'De la medición a la decisión, sin mezclar las capas de evidencia.' })).toBeInTheDocument();
    expect(screen.getAllByText('Descubrimiento de factores')[0].parentElement).toHaveTextContent('FASE ACTUAL · SIN RESULTADOS');
    expect(screen.getAllByText('Construcción del modelo')[0].parentElement).toHaveTextContent('BLOQUEADA');
    expect(screen.getAllByText('Expresión de estrategia')[0].parentElement).toHaveTextContent('BLOQUEADA');
    expect(screen.getByRole('heading', { name: 'Escalera de evidencia' })).toBeInTheDocument();
    expect(screen.getByText('Arquitectura de tres capas').parentElement).toHaveTextContent('ACEPTADA');
    expect(screen.getAllByText('Catálogo de factores V1')[0].parentElement).toHaveTextContent('REGISTRADO');
    expect(screen.getByText('Cobertura y redundancia').parentElement).toHaveTextContent('REPRODUCIDA');
    expect(screen.getByText('Protocolo de selección').parentElement).toHaveTextContent('SIGUIENTE');
    expect(screen.getByRole('heading', { name: 'Resumen de la base de investigación' })).toBeInTheDocument();
    expect(screen.getByText('Ciclo de vida y terminal').parentElement).toHaveTextContent('219 + 83');
    expect(screen.getByText(/no se combinan en un único porcentaje de avance/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Calificación de factores V1' })).toBeInTheDocument();
    expect(screen.getByText('Vectores completos').parentElement).toHaveTextContent('418.756');
    expect(screen.getByRole('heading', { name: 'Evidencia de ingeniería del método' })).toBeInTheDocument();
    expect(screen.getByText(/no es tasa de acierto, precisión predictiva ni rentabilidad/)).toBeInTheDocument();
    expect(screen.getByText('No apto para Candidatos')).toBeInTheDocument();
    expect(screen.getByText(/La evidencia de una acción no es rendimiento de opciones/)).toBeInTheDocument();
  });
});
