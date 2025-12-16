'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { KPICards } from '@/components/dashboard/KPICards';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { PortfolioOverview } from '@/components/dashboard/PortfolioOverview';
import { Loader2, Calendar, Clock } from 'lucide-react';

type DateRange = 'all' | '7d' | '30d' | '90d' | 'ytd' | 'custom';

function getDateRange(range: DateRange): { start_date?: string; end_date?: string } {
  const today = new Date();
  const formatDate = (d: Date) => d.toISOString().split('T')[0];

  switch (range) {
    case '7d':
      const d7 = new Date(today);
      d7.setDate(d7.getDate() - 7);
      return { start_date: formatDate(d7), end_date: formatDate(today) };
    case '30d':
      const d30 = new Date(today);
      d30.setDate(d30.getDate() - 30);
      return { start_date: formatDate(d30), end_date: formatDate(today) };
    case '90d':
      const d90 = new Date(today);
      d90.setDate(d90.getDate() - 90);
      return { start_date: formatDate(d90), end_date: formatDate(today) };
    case 'ytd':
      const ytd = new Date(today.getFullYear(), 0, 1);
      return { start_date: formatDate(ytd), end_date: formatDate(today) };
    case 'all':
    default:
      return {};
  }
}

export default function Dashboard() {
  const { language } = useAppStore();
  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const dateParams = useMemo(() => {
    if (dateRange === 'custom' && customStart && customEnd) {
      return { start_date: customStart, end_date: customEnd };
    }
    return getDateRange(dateRange);
  }, [dateRange, customStart, customEnd]);

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['statistics', dateParams],
    queryFn: () => apiClient.getStatistics(dateParams),
  });

  const { data: equityCurve, isLoading: curveLoading } = useQuery({
    queryKey: ['equity-curve', dateParams],
    queryFn: () => apiClient.getEquityCurve(dateParams),
  });

  const { data: portfolio, isLoading: portfolioLoading, dataUpdatedAt } = useQuery({
    queryKey: ['portfolio'],
    queryFn: apiClient.getPortfolio,
    refetchInterval: 60000, // 每 60 秒自動刷新價格
    refetchIntervalInBackground: false, // 背景時不刷新（省資源）
  });

  const { data: cashBalance } = useQuery({
    queryKey: ['cash-balance'],
    queryFn: apiClient.getCashBalance,
    retry: false,
    refetchInterval: 60000,
  });

  // 更新上次更新時間
  useEffect(() => {
    if (dataUpdatedAt) {
      setLastUpdated(new Date(dataUpdatedAt));
    }
  }, [dataUpdatedAt]);

  const isLoading = statsLoading || curveLoading || portfolioLoading;

  const rangeOptions: { value: DateRange; label: string }[] = [
    { value: 'all', label: language === 'zh' ? '全部' : 'All' },
    { value: '7d', label: language === 'zh' ? '7天' : '7D' },
    { value: '30d', label: language === 'zh' ? '30天' : '30D' },
    { value: '90d', label: language === 'zh' ? '90天' : '90D' },
    { value: 'ytd', label: language === 'zh' ? '今年' : 'YTD' },
    { value: 'custom', label: language === 'zh' ? '自訂' : 'Custom' },
  ];

  return (
    <div className="space-y-6">
      {/* Date Range Selector & Last Updated */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Calendar className="h-4 w-4" />
            <span>{language === 'zh' ? '時間區間' : 'Date Range'}:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {rangeOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDateRange(opt.value)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${dateRange === opt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {dateRange === 'custom' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
              <span className="text-gray-500">~</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
            </div>
          )}
        </div>

        {/* Last Updated Time (auto-refresh every 60s) */}
        {lastUpdated && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <Clock className="h-3.5 w-3.5" />
            <span>
              {language === 'zh' ? '價格更新於 ' : 'Prices updated at '}
              {lastUpdated.toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex h-[calc(100vh-12rem)] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          {statistics && <KPICards statistics={statistics} cashBalance={cashBalance} />}

          {/* Equity Curve */}
          {equityCurve && <EquityChart data={equityCurve} />}

          {/* Portfolio Overview - 傳入 cashBalance 讓持倉總覽顯示現金水位 */}
          {portfolio && <PortfolioOverview portfolio={portfolio} cashBalance={cashBalance} />}
        </>
      )}
    </div>
  );
}
