import modelRecord from '../modelRecords/quant-research-lab-model-record-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const COPY = {
  en: {
    eyebrow: 'Personal model research · governed registry',
    title: 'Quant Research Lab',
    subtitle: 'The authoritative record of model logic, exact formulas, validation evidence, failure, and lifecycle—not a catalogue of polished backtests.',
    status: 'DATA BLOCKED', statusValue: 'METHOD ONLY',
    statusNote: 'The method is registered and inspectable. No real evaluation, performance claim, or Candidate authority exists.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    readiness: 'Research input gates', readinessItems: [
      ['Price history length', 'LENGTH MET', 'At least 252 contiguous completed sessions are present. A complete research-return basis is not yet released.', 'met'],
      ['Point-in-time membership', 'INCOMPLETE', 'The full interval is not published as daily signal-eligible historical membership.', 'blocked'],
      ['Actions & adjustment', 'PARTIAL', 'Split-only facts and sparse affected-path evidence exist; availability, neutral rows, revisions, and total-return semantics remain incomplete.', 'blocked'],
      ['Security lifecycle', 'INCOMPLETE', 'Cross-venue inactive, terminal, and successor evidence remains incomplete.', 'blocked'],
      ['Costs & sealed evaluation', 'LOCKED', 'Observed costs and one-use real holdout evaluation remain unavailable until the mandatory inputs pass.', 'locked'],
    ],
    owner: 'Research ownership', ownerValue: 'WH Alpha personal quantitative research',
    boundary: 'Authority boundary', boundaryBody: 'The Lab owns research evidence. Stock Candidates may later consume only one to three separately validated and explicitly activated models.',
    registry: 'Registered model', featured: 'Featured research record',
    methodOnly: 'Method only', noCandidate: 'Not Candidate-eligible', notAssessed: 'Market fit not assessed',
    version: 'Version', lifecycleState: 'Lifecycle', evidence: 'Evidence', applicability: 'Applicability',
    oos: 'Out-of-sample observations', nextDecision: 'Next decision', strength: 'Primary strength', weakness: 'Primary weakness',
    inspect: 'Inspect complete logic, formulas, parameters, evaluation, and fingerprints',
    logic: '1 · Logic and decision', features: '2 · Inputs and features', parameters: '3 · Parameters and search budget',
    evaluation: '4 · Evaluation design', gates: '5 · Advancement gates', failure: '6 · Failure, invalidation, and blockers', reproduction: '7 · Reproduction',
    decisionUse: 'Decision use', hypothesis: 'Hypothesis', rationale: 'Economic rationale', signal: 'Signal rule', ranking: 'Ranking rule',
    source: 'Source', cutoff: 'Availability cutoff', lookback: 'Lookback', transform: 'Transform', expected: 'Expected direction', missing: 'Missingness',
    candidates: 'Candidate values', selection: 'Selection',
    split: 'Chronology', outcome: 'Primary outcome', secondary: 'Secondary outcomes', benchmark: 'Benchmark', control: 'Control', inference: 'Inference', multiplicity: 'Multiplicity', costs: 'Cost scenarios', holdout: 'Holdout custody', portfolio: 'Portfolio construction',
    counter: 'Required counterevidence review', invalidation: 'Invalidation conditions', blockers: 'Current blockers', risks: 'Risk disclosures',
    none: 'None', undefined: 'Not defined', sessions: 'sessions', falseValue: 'Not defined',
    lifecycle: 'Promotion path', stages: ['Method registered', 'Data qualification', 'Validation', 'Sealed holdout', 'Validated research', 'Shadow', 'Active'],
    current: 'Current', locked: 'Locked', blocked: 'Blocked by evidence',
    results: 'Results workspace', resultsNote: 'Intentionally unavailable—no synthetic substitute and no implied performance',
    resultCards: [['Net expectancy', 'No real event study'], ['Uncertainty & stability', 'No qualified sample'], ['Win / payoff / PF', 'No qualified sample'], ['Portfolio AR / Sharpe / MDD', 'Portfolio not defined']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '个人模型研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '模型逻辑、完整公式、验证证据、失败记录与生命周期的权威档案，而不是陈列漂亮回测的页面。',
    status: '数据尚未达标', statusValue: '仅有方法档案',
    statusNote: '方法已登记并可完整审阅；目前没有真实评估、绩效主张或候选排名权限。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    readiness: '研究输入门槛', readinessItems: [
      ['价格历史长度', '长度已满足', '已有至少252个连续完成交易日；完整的研究收益口径尚未发布。', 'met'],
      ['逐日时点成员资格', '不完整', '完整区间尚未发布为逐日、可用于信号的历史成员资格。', 'blocked'],
      ['公司行动与复权', '部分完成', '已有拆股事实与稀疏受影响路径证据；可用性、空白行、修订和总回报语义仍不完整。', 'blocked'],
      ['证券生命周期', '不完整', '跨交易所失活、终止与继承关系证据仍不完整。', 'blocked'],
      ['成本与封存评估', '锁定', '在强制输入通过前，不启用实测成本和单次真实样本外评估。', 'locked'],
    ],
    owner: '研究归属', ownerValue: 'WH Alpha 个人量化研究',
    boundary: '权限边界', boundaryBody: '实验室负责研究证据；个股候选未来只能消费一至三个分别通过验证并明确激活的模型。',
    registry: '已登记模型', featured: '当前重点研究档案',
    methodOnly: '仅有方法', noCandidate: '不可进入个股候选', notAssessed: '尚未评估市场适配',
    version: '版本', lifecycleState: '生命周期', evidence: '证据类型', applicability: '当前适配',
    oos: '样本外观察数', nextDecision: '下一项决策', strength: '主要优点', weakness: '主要弱点',
    inspect: '展开审阅完整逻辑、公式、参数、评估设计与指纹',
    logic: '1 · 逻辑与决策用途', features: '2 · 输入与特征', parameters: '3 · 参数与搜索预算',
    evaluation: '4 · 评估设计', gates: '5 · 晋级门槛', failure: '6 · 反面证据、失效条件与阻塞项', reproduction: '7 · 复现信息',
    decisionUse: '决策用途', hypothesis: '研究假设', rationale: '经济逻辑', signal: '触发公式', ranking: '排名规则',
    source: '来源', cutoff: '可用时间界限', lookback: '回看窗口', transform: '变换', expected: '预期方向', missing: '缺失处理',
    candidates: '候选取值', selection: '选择范围',
    split: '时间划分', outcome: '主要结果', secondary: '次要结果', benchmark: '基准', control: '对照组', inference: '推断方法', multiplicity: '多重检验', costs: '成本情景', holdout: '样本外保管', portfolio: '组合构建',
    counter: '必须检查的反面证据', invalidation: '失效条件', blockers: '当前阻塞项', risks: '风险声明',
    none: '无', undefined: '未定义', sessions: '个交易日', falseValue: '尚未定义',
    lifecycle: '晋级路径', stages: ['方法已登记', '数据资格审查', '验证', '封存样本外', '研究验证通过', '影子运行', '正式激活'],
    current: '当前', locked: '锁定', blocked: '受证据阻塞',
    results: '结果工作区', resultsNote: '有意保持不可用——不使用合成替代，也不暗示任何绩效',
    resultCards: [['净期望值', '没有真实事件研究'], ['不确定性与稳定性', '没有合格样本'], ['胜率 / 盈亏比 / PF', '没有合格样本'], ['组合 AR / Sharpe / MDD', '尚未定义组合']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
} as const;

function humanize(value: string): string {
  return value.split('_').join(' ');
}

function RecordList({ items }: { items: readonly string[] }): JSX.Element {
  return <ul className="research-record-list">{items.map((item) => <li key={item}>{humanize(item)}</li>)}</ul>;
}

export function QuantResearchLabPage(): JSX.Element {
  const { locale } = useI18n();
  const c = COPY[locale];
  const modelName = locale === 'zh' ? modelRecord.display_name_zh : modelRecord.display_name;
  const evaluation = modelRecord.evaluation_design;

  return <main className="research-page">
    <section className="research-hero">
      <div className="research-hero-copy"><span className="eyebrow">{c.eyebrow}</span><h1>{c.title}</h1><p>{c.subtitle}</p></div>
      <div className="research-status"><span>{c.status}</span><strong>{c.statusValue}</strong><p>{c.statusNote}</p></div>
      <div className="research-progress-copy"><strong>{c.coverage}</strong><span>{c.coverageNote}</span><small>{c.coverageBoundary}</small></div>
    </section>

    <section className="research-readiness" aria-labelledby="research-readiness-title"><header><span>00</span><h2 id="research-readiness-title">{c.readiness}</h2></header><div>{c.readinessItems.map(([name, state, body, tone]) => <article className={`research-readiness-${tone}`} key={name}><span>{state}</span><strong>{name}</strong><p>{body}</p></article>)}</div></section>

    <section className="research-boundary-grid"><article><span>{c.owner}</span><strong>{c.ownerValue}</strong></article><article><span>{c.boundary}</span><p>{c.boundaryBody}</p></article></section>

    <section className="research-card research-model-registry" aria-labelledby="research-model-title">
      <header><span>01</span><div><h2 id="research-model-title">{c.registry}</h2><p>{c.featured}</p></div></header>
      <article className="research-model-summary">
        <div className="research-model-heading"><div><span>{modelRecord.model_id}</span><h3>{modelName}</h3><p>{modelRecord.hypothesis}</p></div><div className="research-model-badges"><b>{c.methodOnly}</b><b>{c.noCandidate}</b><b>{c.notAssessed}</b></div></div>
        <dl className="research-model-facts">
          <div><dt>{c.version}</dt><dd>{modelRecord.model_version}</dd></div>
          <div><dt>{c.lifecycleState}</dt><dd>{humanize(modelRecord.lifecycle_state)}</dd></div>
          <div><dt>{c.evidence}</dt><dd>{humanize(modelRecord.evidence_scope)}</dd></div>
          <div><dt>{c.applicability}</dt><dd>{humanize(modelRecord.applicability_state)}</dd></div>
          <div><dt>{c.oos}</dt><dd>{modelRecord.out_of_sample_observation_count}</dd></div>
        </dl>
        <div className="research-model-balance"><p><strong>{c.strength}</strong>{modelRecord.primary_strength}</p><p><strong>{c.weakness}</strong>{modelRecord.primary_weakness}</p></div>
        <p className="research-next-decision"><strong>{c.nextDecision}</strong>{modelRecord.next_required_decision}</p>
      </article>

      <details className="research-model-details">
        <summary>{c.inspect}</summary>
        <div className="research-record-section"><h3>{c.logic}</h3><dl className="research-record-ledger">
          {[[c.decisionUse,modelRecord.decision_use],[c.hypothesis,modelRecord.hypothesis],[c.rationale,modelRecord.economic_rationale],[c.signal,modelRecord.signal_rule],[c.ranking,modelRecord.ranking_rule]].map(([term, value]) => <div key={term}><dt>{term}</dt><dd>{value}</dd></div>)}
        </dl></div>

        <div className="research-record-section"><h3>{c.features}</h3><div className="research-feature-grid">{modelRecord.feature_disclosures.map((feature) => <article key={feature.feature_id}><header><span>{humanize(feature.role)}</span><strong>{humanize(feature.feature_id)}</strong></header><code>{feature.exact_formula}</code><dl><div><dt>{c.source}</dt><dd>{feature.source_family} · {feature.source_fields.join(', ')}</dd></div><div><dt>{c.cutoff}</dt><dd>{humanize(feature.availability_cutoff)}</dd></div><div><dt>{c.lookback}</dt><dd>{feature.lookback_sessions} {c.sessions}</dd></div><div><dt>{c.transform}</dt><dd>{humanize(feature.transform)}</dd></div><div><dt>{c.expected}</dt><dd>{humanize(feature.expected_direction)}</dd></div><div><dt>{c.missing}</dt><dd>{humanize(feature.missingness_rule)}</dd></div></dl></article>)}</div></div>

        <div className="research-record-section"><h3>{c.parameters}</h3><div className="research-parameter-records">{modelRecord.parameter_disclosures.map((parameter) => <article key={parameter.parameter_id}><strong>{humanize(parameter.parameter_id)}</strong><p>{parameter.rationale}</p><span>{c.candidates}</span><code>{parameter.candidate_values.join(' | ')}</code><small>{c.selection}: {humanize(parameter.selection_scope)}</small></article>)}</div></div>

        <div className="research-record-section"><h3>{c.evaluation}</h3><dl className="research-record-ledger">
          <div><dt>{c.split}</dt><dd>{humanize(evaluation.split_rule)} · warm-up {evaluation.warmup_sessions} · purge {evaluation.purge_sessions} · embargo {evaluation.embargo_sessions}</dd></div>
          <div><dt>{c.outcome}</dt><dd>{humanize(evaluation.primary_outcome)}</dd></div>
          <div><dt>{c.secondary}</dt><dd>{evaluation.secondary_outcomes.map(humanize).join(' · ')}</dd></div>
          <div><dt>{c.benchmark}</dt><dd>{humanize(evaluation.benchmark)}</dd></div>
          <div><dt>{c.control}</dt><dd>{humanize(evaluation.control)}</dd></div>
          <div><dt>{c.inference}</dt><dd>{humanize(evaluation.inference_method)}</dd></div>
          <div><dt>{c.multiplicity}</dt><dd>{humanize(evaluation.multiplicity_method)} · budget {evaluation.search_budget}</dd></div>
          <div><dt>{c.costs}</dt><dd>{evaluation.cost_scenarios_bps_per_side.join(' / ')} bps per side</dd></div>
          <div><dt>{c.holdout}</dt><dd>{humanize(evaluation.holdout_rule)}</dd></div>
          <div><dt>{c.portfolio}</dt><dd>{evaluation.portfolio_construction_defined ? c.undefined : c.falseValue}</dd></div>
        </dl></div>

        <div className="research-record-section"><h3>{c.gates}</h3><RecordList items={modelRecord.decision_gates} /></div>
        <div className="research-record-section research-record-risk"><h3>{c.failure}</h3><div><article><strong>{c.counter}</strong><RecordList items={modelRecord.counterevidence_requirements} /></article><article><strong>{c.invalidation}</strong><RecordList items={modelRecord.invalidation_conditions} /></article><article><strong>{c.blockers}</strong><RecordList items={modelRecord.blocker_codes} /></article><article><strong>{c.risks}</strong><RecordList items={modelRecord.risk_disclosure_codes} /></article></div></div>
        <div className="research-record-section"><h3>{c.reproduction}</h3><dl className="research-fingerprint-ledger">
          <div><dt>contract</dt><dd><code>{modelRecord.contract_version}</code></dd></div><div><dt>record</dt><dd><code>{modelRecord.logical_fingerprint}</code></dd></div><div><dt>experiment ID</dt><dd><code>{modelRecord.source_experiment_id}</code></dd></div><div><dt>experiment</dt><dd><code>{modelRecord.source_experiment_fingerprint}</code></dd></div><div><dt>features</dt><dd><code>{modelRecord.input_feature_fingerprint}</code></dd></div><div><dt>evaluation</dt><dd><code>{modelRecord.evaluation_policy_fingerprint}</code></dd></div><div><dt>implementation revision</dt><dd>{modelRecord.implementation_revision ?? modelRecord.implementation_revision_reason}</dd></div><div><dt>result publication</dt><dd>{modelRecord.result_publication_id ?? c.none}</dd></div>
        </dl></div>
      </details>
    </section>

    <section className="research-card research-lifecycle"><header><span>02</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'done' : index === 1 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : index === 1 ? c.blocked : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>03</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
