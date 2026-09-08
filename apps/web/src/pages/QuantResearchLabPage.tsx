import { useI18n } from '../i18n/I18nProvider';

const COPY = {
  en: {
    eyebrow: 'Personal model research · preregistered', title: 'Quant Research Lab',
    subtitle: 'A governed workspace for turning a personal trading hypothesis into a reproducible, falsifiable experiment—not a catalogue of polished backtests.',
    status: 'DATA BLOCKED', statusValue: 'INPUT GATES', statusNote: 'Price depth now clears the minimum length floor. The complete point-in-time research panel does not.',
    coverage: 'Family-specific readiness', coverageNote: 'Do not collapse unlike data families into one percentage.', coverageBoundary: 'Readiness is not confidence, win rate, model progress, or evidence that the hypothesis works.',
    readiness: 'Research input gates', readinessItems: [
      ['Price history length', 'LENGTH MET', 'At least 252 contiguous completed sessions are present. Adjusted research returns are not yet released.', 'met'],
      ['Point-in-time membership', 'INCOMPLETE', 'The full historical interval is not published as signal-eligible daily membership.', 'blocked'],
      ['Corporate actions & adjustment', 'INCOMPLETE', 'Source observations exist, but canonical action and adjustment ledgers are absent.', 'blocked'],
      ['Security lifecycle', 'INCOMPLETE', 'Cross-venue inactive, terminal and successor evidence is not complete.', 'blocked'],
      ['Costs & sealed evaluation', 'LOCKED', 'Realistic costs and one-use holdout evaluation remain unavailable until upstream inputs pass.', 'locked'],
    ],
    owner: 'Research ownership', ownerValue: 'WH Alpha personal quantitative research',
    boundary: 'Research-stage model', boundaryBody: 'Parameters and conclusions are personal research. They may decay or fail in a different market. Nothing here is investment advice, an order instruction, or an option-return forecast.',
    lifecycle: 'Research lifecycle', stages: ['Hypothesis registered', 'Data qualification', 'Validation', 'Sealed holdout', 'Research release'],
    current: 'Current', locked: 'Locked', blocked: 'Blocked by canonical history',
    hypothesisEyebrow: 'First experiment family', hypothesis: 'Strong-Leader Pullback',
    hypothesisBody: 'Test whether already-strong stocks that reset without breaking trend subsequently outperform comparable eligible leaders. The research asks when a pullback is useful—not whether a familiar indicator looks attractive.',
    why: 'Why this comes first', whyBody: 'It directly addresses the practical failure mode you care about: chasing an extended leader and suffering an immediate reversal. It also has an observable same-session comparison group.',
    design: 'Preregistered test design',
    population: 'Population', populationBody: 'Effective-dated Primary Universe membership only; no present-day survivor list.',
    split: 'Chronology', splitBody: '50% development · 25% validation · 25% sealed holdout',
    hygiene: 'Leakage controls', hygieneBody: '20-session warm-up · 5-session purge · 5-session embargo',
    outcome: 'Outcome', outcomeBody: 'Underlying-stock forward return at 1/3/5 sessions; 3-session is primary.',
    control: 'Control', controlBody: 'Eligible leaders that did not signal in the same session.',
    grid: 'Fixed parameter family', gridBody: '2 × 3 × 2 × 2 = 24 combinations. No silent post-result tuning.',
    reset: 'Leadership gate', resetValue: '2 choices', trend: 'ATR pullback band', trendValue: '3 choices', participation: 'Recovery trigger', participationValue: '2 choices', trigger: 'Volume contraction cap', triggerValue: '2 choices',
    gates: 'Advancement gates', gatesIntro: 'A result advances only when every relevant gate is satisfied. A high average alone is insufficient.',
    gateItems: [
      ['Complete family', 'All 24 combinations have complete validation evidence and coverage.'],
      ['Multiplicity', 'Holm-adjusted family-wise threshold ≤ 0.10.'],
      ['Economic value', 'Median excess return remains positive after a 25 bps cost assumption.'],
      ['Regime support', 'Any reported regime cell contains at least 60 observations.'],
      ['Sealed confirmation', 'Selected holdout confidence-interval lower bound is above zero.'],
    ],
    blockers: 'Why results are unavailable', blockerItems: [
      'Price length alone is insufficient; the complete point-in-time research panel is not published.',
      'Daily signal-eligible membership must exist across the research interval.',
      'Canonical corporate-action, lifecycle and adjustment decisions need auditable ledgers.',
      'Single-use holdout custody must be durable before holdout evaluation.',
    ],
    future: 'Results workspace', futureNote: 'Reserved structure—no synthetic substitute',
    resultCards: [['Effect distribution', 'Awaiting qualified observations'], ['Regime stability', 'Awaiting minimum cell coverage'], ['Parameter robustness', 'Awaiting full 24-combination validation'], ['Holdout confirmation', 'Sealed · not evaluated']],
    interpret: 'How to interpret future evidence', interpretBody: 'The eventual output will show effect size, uncertainty, costs, sample coverage, parameter sensitivity, supporting evidence, counterevidence and invalidation conditions. It will not reduce research to a single score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'This experiment studies underlying-stock returns. Options require a separate expression layer with contemporaneous quotes, IV, Greeks, spreads, open interest, expiry and event risk.',
  },
  zh: {
    eyebrow: '个人模型研究 · 预登记', title: '量化研究实验室',
    subtitle: '把个人交易假设转化为可复现、可证伪实验的受控工作区，而不是陈列看似漂亮的回测结果。',
    status: '数据尚未达标', statusValue: '输入门槛', statusNote: '价格历史长度现已达到最低门槛，但完整的时点正确研究面板仍未就绪。',
    coverage: '按数据族分别判断', coverageNote: '不同数据族不能压缩成一个百分比。', coverageBoundary: '准备度不代表信心、胜率、模型进度，也不证明研究假设有效。',
    readiness: '研究输入门槛', readinessItems: [
      ['价格历史长度', '长度已满足', '已有至少252个连续完成交易日；经过完整复权治理的研究收益尚未发布。', 'met'],
      ['逐日时点成员资格', '不完整', '完整历史区间尚未发布为可用于信号的逐日成员资格。', 'blocked'],
      ['公司行动与复权', '不完整', '已有来源观察，但规范公司行动账本和复权账本仍不存在。', 'blocked'],
      ['证券生命周期', '不完整', '跨交易所的失活、终止和继承关系证据尚不完整。', 'blocked'],
      ['成本与封存评估', '锁定', '真实成本和单次样本外评估要等上游输入全部通过后才可启用。', 'locked'],
    ],
    owner: '研究归属', ownerValue: 'WH Alpha 个人量化研究',
    boundary: '研究阶段模型', boundaryBody: '参数与结论属于个人研究，可能随市场变化而衰减或失效。这里不是投资建议、下单指令，也不预测期权收益。',
    lifecycle: '研究生命周期', stages: ['假设已登记', '数据资格审查', '验证', '封存样本外检验', '研究发布'],
    current: '当前', locked: '锁定', blocked: '受规范历史数据阻塞',
    hypothesisEyebrow: '首个实验族', hypothesis: '强势股回撤',
    hypothesisBody: '检验保持趋势的强势股在适度回撤后，是否优于同一交易日内其他合格强势股。研究的问题是“什么样的回撤有用”，而不是熟悉的指标看起来是否漂亮。',
    why: '为什么先研究它', whyBody: '它直接对应你最重视的实际失败模式：追入过度延伸的强势股后立即回撤；同时也能构建同日、同类的可观察对照组。',
    design: '预登记检验设计',
    population: '研究总体', populationBody: '只使用当日有效的Primary Universe成员，绝不拿今天的幸存者名单倒推历史。',
    split: '时间顺序', splitBody: '50%开发 · 25%验证 · 25%封存样本外',
    hygiene: '防泄漏措施', hygieneBody: '20日预热 · 5日净化间隔 · 5日禁运间隔',
    outcome: '研究结果', outcomeBody: '标的股票未来1/3/5日收益，3日为主要期限。',
    control: '对照组', controlBody: '同一交易日符合领导股资格、但未触发信号的股票。',
    grid: '固定参数族', gridBody: '2 × 3 × 2 × 2 = 24组，不允许看到结果后悄悄调参。',
    reset: '领导力门槛', resetValue: '2档', trend: 'ATR回撤区间', trendValue: '3档', participation: '价格恢复触发', participationValue: '2档', trigger: '缩量上限', triggerValue: '2档',
    gates: '晋级门槛', gatesIntro: '只有相关门槛全部满足，结果才可以晋级；仅有较高平均收益远远不够。',
    gateItems: [
      ['完整实验族', '24组参数必须都有完整验证证据和覆盖。'],
      ['多重检验', 'Holm校正后的族错误率阈值不高于0.10。'],
      ['经济价值', '扣除25个基点成本假设后，中位超额收益仍为正。'],
      ['市场环境覆盖', '任何单独报告的市场环境至少有60个观察值。'],
      ['封存确认', '入选方案在样本外的置信区间下界必须高于零。'],
    ],
    blockers: '为什么现在没有结果', blockerItems: [
      '仅有足够长的价格历史还不够；完整的时点正确研究面板尚未发布。',
      '研究区间内必须具有逐日、可用于信号的时点成员记录。',
      '规范公司行动、证券生命周期与复权决策必须有可审计账本。',
      '在评估样本外结果前，必须建立可持久执行的单次解封机制。',
    ],
    future: '结果工作区', futureNote: '仅预留结构，不使用合成替代数据',
    resultCards: [['效应分布', '等待合格观察值'], ['市场环境稳定性', '等待达到最小分组样本'], ['参数稳健性', '等待完整24组验证'], ['样本外确认', '已封存 · 尚未评估']],
    interpret: '未来如何解释结果', interpretBody: '未来将同时展示效应大小、不确定性、成本、样本覆盖、参数敏感性、支持证据、反面证据和失效条件，不会把研究压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '本实验研究标的股票收益。期权必须由独立表达层处理，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
} as const;

export function QuantResearchLabPage(): JSX.Element {
  const { locale } = useI18n();
  const c = COPY[locale];
  return <main className="research-page">
    <section className="research-hero">
      <div className="research-hero-copy"><span className="eyebrow">{c.eyebrow}</span><h1>{c.title}</h1><p>{c.subtitle}</p></div>
      <div className="research-status"><span>{c.status}</span><strong>{c.statusValue}</strong><p>{c.statusNote}</p></div>
      <div className="research-progress-copy"><strong>{c.coverage}</strong><span>{c.coverageNote}</span><small>{c.coverageBoundary}</small></div>
    </section>

    <section className="research-readiness" aria-labelledby="research-readiness-title"><header><span>00</span><h2 id="research-readiness-title">{c.readiness}</h2></header><div>{c.readinessItems.map(([name, state, body, tone]) => <article className={`research-readiness-${tone}`} key={name}><span>{state}</span><strong>{name}</strong><p>{body}</p></article>)}</div></section>

    <section className="research-boundary-grid">
      <article><span>{c.owner}</span><strong>{c.ownerValue}</strong></article>
      <article><span>{c.boundary}</span><p>{c.boundaryBody}</p></article>
    </section>

    <section className="research-card research-lifecycle"><header><span>01</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'done' : index === 1 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : index === 1 ? c.blocked : c.locked}</small></li>)}</ol></section>

    <section className="research-two-column">
      <article className="research-card research-hypothesis"><span>{c.hypothesisEyebrow}</span><h2>{c.hypothesis}</h2><p>{c.hypothesisBody}</p><div><strong>{c.why}</strong><p>{c.whyBody}</p></div></article>
      <article className="research-card"><header><span>02</span><h2>{c.design}</h2></header><dl className="research-design-list">{[[c.population,c.populationBody],[c.split,c.splitBody],[c.hygiene,c.hygieneBody],[c.outcome,c.outcomeBody],[c.control,c.controlBody]].map(([term, body]) => <div key={term}><dt>{term}</dt><dd>{body}</dd></div>)}</dl></article>
    </section>

    <section className="research-card"><header><span>03</span><div><h2>{c.grid}</h2><p>{c.gridBody}</p></div></header><div className="research-parameter-grid">{[[c.reset,c.resetValue],[c.trend,c.trendValue],[c.participation,c.participationValue],[c.trigger,c.triggerValue]].map(([label,value], index) => <article key={label}><span>0{index + 1}</span><strong>{label}</strong><b>{value}</b></article>)}</div></section>

    <section className="research-two-column">
      <article className="research-card"><header><span>04</span><div><h2>{c.gates}</h2><p>{c.gatesIntro}</p></div></header><ol className="research-gates">{c.gateItems.map(([name, body]) => <li key={name}><i>✓</i><div><strong>{name}</strong><p>{body}</p></div></li>)}</ol></article>
      <article className="research-card research-blockers"><header><span>05</span><h2>{c.blockers}</h2></header><ul>{c.blockerItems.map((item) => <li key={item}>{item}</li>)}</ul></article>
    </section>

    <section className="research-card research-results"><header><span>06</span><div><h2>{c.future}</h2><p>{c.futureNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
