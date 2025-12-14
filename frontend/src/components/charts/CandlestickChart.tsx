'use client';

import { useEffect, useRef } from 'react';
import {
    createChart,
    ColorType,
    IChartApi,
    CandlestickData,
    Time,
    CandlestickSeries,
    createSeriesMarkers
} from 'lightweight-charts';
import { OHLCData, ChartTrade } from '@/lib/api';
import { useAppStore } from '@/lib/store';

interface CandlestickChartProps {
    symbol: string;
    ohlcData: OHLCData[];
    trades: ChartTrade[];
    height?: number;
}

export function CandlestickChart({ symbol, ohlcData, trades, height = 500 }: CandlestickChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const { theme } = useAppStore();

    useEffect(() => {
        if (!chartContainerRef.current || ohlcData.length === 0) return;

        // 清除舊圖表
        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        const isDark = theme === 'dark';

        // 創建圖表
        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: height,
            layout: {
                background: { type: ColorType.Solid, color: isDark ? '#111827' : '#ffffff' },
                textColor: isDark ? '#d1d5db' : '#374151',
            },
            grid: {
                vertLines: { color: isDark ? '#1f2937' : '#e5e7eb' },
                horzLines: { color: isDark ? '#1f2937' : '#e5e7eb' },
            },
            crosshair: {
                mode: 1,
            },
            rightPriceScale: {
                borderColor: isDark ? '#374151' : '#d1d5db',
            },
            timeScale: {
                borderColor: isDark ? '#374151' : '#d1d5db',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        chartRef.current = chart;

        // 添加 K 線圖 - lightweight-charts v5 API
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#10b981',
            downColor: '#ef4444',
            borderUpColor: '#10b981',
            borderDownColor: '#ef4444',
            wickUpColor: '#10b981',
            wickDownColor: '#ef4444',
        });

        // 轉換數據格式
        const chartData: CandlestickData<Time>[] = ohlcData.map((d) => ({
            time: d.date as Time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
        }));

        candlestickSeries.setData(chartData);

        // 日期格式化函數 - 確保格式為 yyyy-mm-dd
        const formatDateForChart = (dateStr: string): string => {
            // 如果已經是 yyyy-mm-dd 格式，直接返回
            if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                return dateStr;
            }
            // 如果是 yyyymmdd 格式，轉換為 yyyy-mm-dd
            if (/^\d{8}$/.test(dateStr)) {
                return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
            }
            // 如果是 ISO 日期格式，提取日期部分
            if (dateStr.includes('T')) {
                return dateStr.split('T')[0];
            }
            // 嘗試解析為 Date 並格式化
            try {
                const d = new Date(dateStr);
                return d.toISOString().split('T')[0];
            } catch {
                return dateStr;
            }
        };

        // 添加買賣點標記 - v5 API: 使用 createSeriesMarkers
        const markers: any[] = [];

        trades.forEach((trade) => {
            const tradeDate = formatDateForChart(trade.date);
            const isBuy = trade.action.toUpperCase().includes('BUY') || trade.action.toUpperCase() === 'BOT';

            markers.push({
                time: tradeDate as Time,
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#10b981' : '#ef4444',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: `${isBuy ? '買' : '賣'} ${trade.is_option ? '選' : ''} ${Math.abs(trade.quantity)}@$${trade.price.toFixed(2)}`,
                size: 2,
            });
        });

        // 按日期排序
        markers.sort((a, b) => (a.time > b.time ? 1 : -1));

        // v5: 使用 createSeriesMarkers 創建 markers primitive
        if (markers.length > 0) {
            createSeriesMarkers(candlestickSeries, markers);
        }

        // 自適應大小
        chart.timeScale().fitContent();

        // 處理視窗大小變化
        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (chartRef.current) {
                chartRef.current.remove();
                chartRef.current = null;
            }
        };
    }, [ohlcData, trades, theme, height]);

    if (ohlcData.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <p className="text-gray-500">無 K 線數據</p>
            </div>
        );
    }

    return (
        <div className="w-full">
            <div className="mb-2 flex items-center justify-between">
                <h3 className="text-lg font-semibold">{symbol} K 線圖</h3>
                <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-emerald-500 rounded-full"></span>
                        買入點
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                        賣出點
                    </span>
                </div>
            </div>
            <div ref={chartContainerRef} className="w-full rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700" />
        </div>
    );
}
