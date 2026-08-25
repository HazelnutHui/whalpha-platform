import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts/core';
import { TreemapChart } from 'echarts/charts';
import { AriaComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ComposeOption } from 'echarts/core';
import type { TreemapSeriesOption } from 'echarts/charts';
import type { TooltipComponentOption, VisualMapComponentOption } from 'echarts/components';

import type { LiquidityMapNodeResponse, LiquidityMapResponse } from '../../api/types';
import { clamp, formatCompact, formatCurrencyCompact, formatPercent, formatPrice, parseDecimal } from '../../utils/format';
import { useI18n } from '../../i18n/I18nProvider';

echarts.use([TreemapChart, TooltipComponent, VisualMapComponent, AriaComponent, CanvasRenderer]);

type ChartOption = ComposeOption<TreemapSeriesOption | TooltipComponentOption | VisualMapComponentOption>;

interface Props {
  liquidityMap: LiquidityMapResponse;
  highlightedTicker?: string | null;
  onSelectNode?: (node: LiquidityMapNodeResponse) => void;
}

interface TreemapDatum {
  name: string;
  value: number;
  colorValue: number;
  node: LiquidityMapResponse['nodes'][number];
}

export function getTreemapColor(returnRatio: number): string {
  const clamped = clamp(returnRatio, -0.05, 0.05);
  if (Math.abs(clamped) < 0.0001) {
    return '#566274';
  }
  if (clamped > 0) {
    const intensity = clamped / 0.05;
    return `rgb(${Math.round(44 + 24 * (1 - intensity))}, ${Math.round(132 + 44 * intensity)}, ${Math.round(100 + 30 * intensity)})`;
  }
  const intensity = Math.abs(clamped) / 0.05;
  return `rgb(${Math.round(138 + 34 * intensity)}, ${Math.round(62 + 12 * (1 - intensity))}, ${Math.round(72 + 12 * (1 - intensity))})`;
}

export function toTreemapData(liquidityMap: LiquidityMapResponse): TreemapDatum[] {
  return liquidityMap.nodes.map((node) => {
    const size = parseDecimal(node.size_value, `${node.ticker} size`);
    const color = parseDecimal(node.color_value, `${node.ticker} return`);
    if (size <= 0) {
      throw new Error(`Invalid liquidity size for ${node.ticker}`);
    }
    return {
      name: node.ticker,
      value: size,
      colorValue: color,
      node,
      itemStyle: { color: getTreemapColor(color) },
      label: {
        formatter: node.rank <= 15 ? `${node.ticker}\n${formatPercent(node.color_value, { signed: true })}` : node.rank <= 40 ? node.ticker : '',
      },
    } as TreemapDatum;
  });
}

export function LiquidityTreemap({ liquidityMap, highlightedTicker, onSelectNode }: Props): JSX.Element {
  const { t } = useI18n();
  const chartRef = useRef<HTMLDivElement | null>(null);
  const summary = t('dashboard.treemapAria', { count: liquidityMap.nodes.length });
  const data = useMemo(() => toTreemapData(liquidityMap), [liquidityMap]);

  useEffect(() => {
    if (!chartRef.current) {
      return undefined;
    }
    const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' });
    const option: ChartOption = {
      aria: { enabled: true, decal: { show: false } },
      tooltip: {
        confine: true,
        formatter: (params: unknown) => {
          const param = params as { data?: TreemapDatum };
          const node = param.data?.node;
          if (!node) {
            return '';
          }
          return [
            `<strong>${node.ticker}</strong>`,
            node.name,
            t('dashboard.tooltipReturn', { value: formatPercent(node.color_value, { signed: true }) }),
            t('dashboard.tooltipClose', { value: formatPrice(node.current_close) }),
            t('dashboard.tooltipVolume', { value: formatCompact(node.current_volume) }),
            t('dashboard.tooltipActivity', { value: formatCurrencyCompact(node.size_value) }),
            t('dashboard.tooltipRank', { value: node.rank }),
            t('dashboard.tooltipType', { value: node.instrument_type }),
            node.quality_flags.includes('unverified_price_discontinuity') ? t('dashboard.tooltipReview') : '',
          ].join('<br/>');
        },
      },
      visualMap: {
        type: 'continuous',
        min: -0.05,
        max: 0.05,
        show: false,
      },
      series: [
        {
          type: 'treemap',
          roam: false,
          breadcrumb: { show: false },
          nodeClick: false,
          animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
          label: {
            color: '#f4f7fb',
            fontFamily: 'Inter, ui-sans-serif, system-ui, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
            fontSize: 12,
            overflow: 'break',
          },
          upperLabel: { show: false },
          itemStyle: {
            borderColor: '#10161f',
            borderWidth: 2,
            gapWidth: 2,
          },
          data: data.map((item) => ({
            ...item,
            itemStyle: {
              ...(item as unknown as { itemStyle: object }).itemStyle,
              borderColor: highlightedTicker === item.node.ticker ? '#f4f7fb' : '#10161f',
              borderWidth: highlightedTicker === item.node.ticker ? 4 : 2,
            },
          })),
        },
      ],
    };
    chart.setOption(option);
    const clickHandler = (params: unknown) => {
      const param = params as { data?: TreemapDatum };
      if (param.data?.node) {
        onSelectNode?.(param.data.node);
      }
    };
    if ('on' in chart && typeof chart.on === 'function') {
      chart.on('click', clickHandler);
    }
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data, highlightedTicker, onSelectNode, t]);

  return (
    <div>
      <div className="return-legend" aria-label={t('dashboard.treemapLegend')}>
        <span>≤−5%</span><span>−2%</span><span>0%</span><span>+2%</span><span>≥+5%</span>
      </div>
      {liquidityMap.nodes.length === 0 ? (
        <div className="empty-state">{t('dashboard.treemapEmpty')}</div>
      ) : (
        <div ref={chartRef} className="treemap-canvas" role="img" aria-label={summary} />
      )}
      <p className="chart-summary">{t('dashboard.treemapSummary')}</p>
    </div>
  );
}
