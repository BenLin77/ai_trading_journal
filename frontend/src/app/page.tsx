'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { KPICards } from '@/components/dashboard/KPICards';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { PortfolioOverview } from '@/components/dashboard/PortfolioOverview';
import { Loader2 } from 'lucide-react';

export default function Dashboard() {
  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['statistics'],
    queryFn: apiClient.getStatistics,
  });

  const { data: equityCurve, isLoading: curveLoading } = useQuery({
    queryKey: ['equity-curve'],
    queryFn: apiClient.getEquityCurve,
  });

  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: apiClient.getPortfolio,
  });

  const { data: cashBalance } = useQuery({
    queryKey: ['cash-balance'],
    queryFn: apiClient.getCashBalance,
    retry: false,
  });

  const isLoading = statsLoading || curveLoading || portfolioLoading;

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      {statistics && <KPICards statistics={statistics} cashBalance={cashBalance} />}

      {/* Equity Curve */}
      {equityCurve && <EquityChart data={equityCurve} />}

      {/* Portfolio Overview */}
      {portfolio && <PortfolioOverview portfolio={portfolio} />}
    </div>
  );
}
