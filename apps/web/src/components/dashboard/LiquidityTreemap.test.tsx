import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

import { LiquidityTreemap, getTreemapColor, toTreemapData } from './LiquidityTreemap';
import { demoDashboardData } from '../../fixtures/marketDemo';

const dispose = vi.fn();
const setOption = vi.fn();
const resize = vi.fn();

vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => ({ setOption, resize, dispose })),
}));
vi.mock('echarts/charts', () => ({ TreemapChart: {} }));
vi.mock('echarts/components', () => ({ AriaComponent: {}, TooltipComponent: {}, VisualMapComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('LiquidityTreemap', () => {
  it('transforms nodes with positive sizes', () => {
    const data = toTreemapData(demoDashboardData.liquidityMap);
    expect(data[0].name).toBe('TESTA');
    expect(data[0].value).toBeGreaterThan(0);
  });

  it('clamps color scale around fixed return range', () => {
    expect(getTreemapColor(0.50)).toContain('rgb');
    expect(getTreemapColor(-0.50)).toContain('rgb');
  });

  it('initializes and disposes ECharts', () => {
    const { unmount } = render(<LiquidityTreemap liquidityMap={demoDashboardData.liquidityMap} />);
    expect(setOption).toHaveBeenCalledTimes(1);
    unmount();
    expect(dispose).toHaveBeenCalledTimes(1);
  });

  it('renders liquidity metadata limitations', () => {
    const { getByText } = render(<LiquidityTreemap liquidityMap={demoDashboardData.liquidityMap} />);
    expect(getByText('Not Market-Cap Weighted')).toBeInTheDocument();
    expect(getByText('Not Sector Grouped')).toBeInTheDocument();
  });
});
