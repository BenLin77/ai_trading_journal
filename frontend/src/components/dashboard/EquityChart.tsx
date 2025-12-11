'use client';

import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EquityCurvePoint } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { useMemo } from 'react';

interface EquityChartProps {
  data: EquityCurvePoint[];
}

export function EquityChart({ data }: EquityChartProps) {
  const { language, theme } = useAppStore();

  const chartData = useMemo(() => {
    if (!data.length) return null;

    const finalPnL = data[data.length - 1]?.cumulative_pnl || 0;
    const maxPnL = Math.max(...data.map(d => d.cumulative_pnl));
    const minPnL = Math.min(...data.map(d => d.cumulative_pnl));
    const maxIdx = data.findIndex(d => d.cumulative_pnl === maxPnL);
    const minIdx = data.findIndex(d => d.cumulative_pnl === minPnL);

    return { finalPnL, maxPnL, minPnL, maxIdx, minIdx };
  }, [data]);

  if (!data.length || !chartData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart_equity_curve', language)}</CardTitle>
        </CardHeader>
        <CardContent className="h-80 flex items-center justify-center text-gray-500">
          {t('status_no_data', language)}
        </CardContent>
      </Card>
    );
  }

  const { finalPnL, maxPnL, minPnL } = chartData;
  const isPositive = finalPnL >= 0;
  const lineColor = isPositive ? '#10b981' : '#ef4444';
  const fillColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

  // Calculate SVG path
  const width = 800;
  const height = 300;
  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const range = maxPnL - minPnL || 1;
  const yScale = (value: number) =>
    padding.top + chartHeight - ((value - minPnL) / range) * chartHeight;
  const xScale = (index: number) =>
    padding.left + (index / (data.length - 1)) * chartWidth;

  const pathData = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.cumulative_pnl)}`)
    .join(' ');

  const areaPath = `${pathData} L ${xScale(data.length - 1)} ${yScale(0)} L ${xScale(0)} ${yScale(0)} Z`;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t('chart_equity_curve', language)}</CardTitle>
        <div className={`text-2xl font-bold ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
          {formatCurrency(finalPnL, true)}
        </div>
      </CardHeader>
      <CardContent>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-80">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = padding.top + chartHeight * ratio;
            const value = maxPnL - ratio * range;
            return (
              <g key={ratio}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke={theme === 'dark' ? '#374151' : '#e5e7eb'}
                  strokeDasharray="4"
                />
                <text
                  x={padding.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  className="text-xs fill-gray-500"
                >
                  {formatCurrency(value)}
                </text>
              </g>
            );
          })}

          {/* Zero line */}
          {minPnL < 0 && maxPnL > 0 && (
            <line
              x1={padding.left}
              y1={yScale(0)}
              x2={width - padding.right}
              y2={yScale(0)}
              stroke={theme === 'dark' ? '#6b7280' : '#9ca3af'}
              strokeWidth={1}
            />
          )}

          {/* Area fill */}
          <path d={areaPath} fill={fillColor} />

          {/* Line */}
          <path
            d={pathData}
            fill="none"
            stroke={lineColor}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Peak marker */}
          <circle
            cx={xScale(chartData.maxIdx)}
            cy={yScale(maxPnL)}
            r={6}
            fill="#10b981"
            stroke={theme === 'dark' ? '#1f2937' : '#ffffff'}
            strokeWidth={2}
          />
          <text
            x={xScale(chartData.maxIdx)}
            y={yScale(maxPnL) - 12}
            textAnchor="middle"
            className="text-xs fill-emerald-500 font-medium"
          >
            Peak {formatCurrency(maxPnL)}
          </text>

          {/* Trough marker (if negative) */}
          {minPnL < 0 && (
            <>
              <circle
                cx={xScale(chartData.minIdx)}
                cy={yScale(minPnL)}
                r={5}
                fill="#ef4444"
                stroke={theme === 'dark' ? '#1f2937' : '#ffffff'}
                strokeWidth={2}
              />
              <text
                x={xScale(chartData.minIdx)}
                y={yScale(minPnL) + 20}
                textAnchor="middle"
                className="text-xs fill-red-500 font-medium"
              >
                Trough {formatCurrency(minPnL)}
              </text>
            </>
          )}
        </svg>
      </CardContent>
    </Card>
  );
}
