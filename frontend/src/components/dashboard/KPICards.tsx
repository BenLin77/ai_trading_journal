'use client';

import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Card, CardContent } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatNumber, cn, getPnLColor } from '@/lib/utils';
import { Statistics, CashBalance } from '@/lib/api';
import { TrendingUp, TrendingDown, Percent, Scale, DollarSign } from 'lucide-react';

interface KPICardsProps {
  statistics: Statistics;
  cashBalance?: CashBalance;
}

export function KPICards({ statistics, cashBalance }: KPICardsProps) {
  const { language } = useAppStore();

  const kpis = [
    {
      label: t('kpi_avg_win', language),
      value: formatCurrency(statistics.avg_win),
      icon: TrendingUp,
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-500/10',
    },
    {
      label: t('kpi_avg_loss', language),
      value: formatCurrency(statistics.avg_loss),
      icon: TrendingDown,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
    },
    {
      label: t('kpi_win_rate', language),
      value: formatPercent(statistics.win_rate),
      icon: Percent,
      color: statistics.win_rate >= 50 ? 'text-emerald-500' : 'text-red-500',
      bgColor: statistics.win_rate >= 50 ? 'bg-emerald-500/10' : 'bg-red-500/10',
    },
    {
      label: t('kpi_profit_factor', language),
      value: statistics.profit_factor.toFixed(2),
      icon: Scale,
      color: statistics.profit_factor >= 1 ? 'text-emerald-500' : 'text-red-500',
      bgColor: statistics.profit_factor >= 1 ? 'bg-emerald-500/10' : 'bg-red-500/10',
    },
    {
      label: t('kpi_cash', language),
      value: cashBalance ? formatCurrency(cashBalance.total_cash) : 'N/A',
      icon: DollarSign,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <Card key={kpi.label}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{kpi.label}</p>
                  <p className={cn('text-2xl font-bold mt-1', kpi.color)}>{kpi.value}</p>
                </div>
                <div className={cn('p-3 rounded-lg', kpi.bgColor)}>
                  <Icon className={cn('h-5 w-5', kpi.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
