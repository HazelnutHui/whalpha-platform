import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts/core';
import { TreemapChart } from 'echarts/charts';
import { AriaComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ComposeOption } from 'echarts/core';
import type { TreemapSeriesOption } from 'echarts/charts';
import type { TooltipComponentOption, VisualMapComponentOption } from 'echarts/components';

import type { LiquidityMapResponse } from '../../api/types';
import { clamp, formatCompact, formatCurrencyCompact, formatPercent, formatPrice, parseDecimal } from '../../utils/format';

echarts.use([TreemapChart, TooltipComponent, VisualMapComponent, AriaComponent, CanvasRenderer]);

type ChartOption = ComposeOption<TreemapSeriesOption | TooltipComponentOption | VisualMapComponentOption>;

interface Props {
  liquidityMap: LiquidityMapResponse;
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
        formatter: `${node.ticker}\n${formatPercent(node.color_value, { signed: true })}`,
      },
    } as TreemapDatum;
  });
}

export function LiquidityTreemap({ liquidityMap }: Props): JSX.Element {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const summary = `${liquidityMap.nodes.length} liquidity-screened instruments sized by close times volume proxy and colored by close-to-close return.`;
  const data = useMemo(() => toTreemapData(liquidityMap), [liquidityMap]);

  useEffect(() => {
    if (!chartRef.current) {
      return undefined;
    }
    const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' });
    const option: ChartOption = {
      aria: { enabled: true, decal: { show: true } },
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
            `Return: ${formatPercent(node.color_value, { signed: true })}`,
            `Close: ${formatPrice(node.current_close)}`,
            `Volume: ${formatCompact(node.current_volume)}`,
            `Liquidity proxy: ${formatCurrencyCompact(node.size_value)}`,
            `Instrument type: ${node.instrument_type}`,
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
            fontFamily: 'Inter, ui-sans-serif, system-ui',
            fontSize: 12,
            overflow: 'truncate',
          },
          upperLabel: { show: false },
          itemStyle: {
            borderColor: '#10161f',
            borderWidth: 2,
            gapWidth: 2,
          },
          data,
        },
      ],
    };
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data]);

  return (
    <section className="panel liquidity-panel" aria-labelledby="liquidity-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Liquidity Map V1</p>
          <h2 id="liquidity-title">Liquidity concentration</h2>
        </div>
        <div className="legend-copy">
          <span>Size: Close × Volume Proxy</span>
          <span>Color: Close-to-Close Return</span>
          <span>Not Market-Cap Weighted</span>
          <span>Not Sector Grouped</span>
        </div>
      </div>
      {liquidityMap.nodes.length === 0 ? (
        <div className="empty-state">No liquidity map nodes matched the current threshold.</div>
      ) : (
        <div ref={chartRef} className="treemap-canvas" role="img" aria-label={summary} />
      )}
      <p className="chart-summary">{summary}</p>
    </section>
  );
}
