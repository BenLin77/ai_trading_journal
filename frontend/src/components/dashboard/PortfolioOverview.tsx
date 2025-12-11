'use client';

import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PortfolioOverview as PortfolioData } from '@/lib/api';
import { formatCurrency, formatPercent, cn, getPnLColor } from '@/lib/utils';
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react';

interface PortfolioOverviewProps {
  portfolio: PortfolioData;
}

// 策略類型對應的顏色
const STRATEGY_COLORS: Record<string, { bg: string; text: string }> = {
  '領口策略': { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400' },
  '備兌看漲': { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-600 dark:text-amber-400' },
  '保護性賣權': { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-600 dark:text-purple-400' },
  '備兌勒式': { bg: 'bg-teal-100 dark:bg-teal-900/30', text: 'text-teal-600 dark:text-teal-400' },
  '純股票持倉': { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400' },
  '熊市看跌價差': { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400' },
  '牛市看跌價差': { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-600 dark:text-emerald-400' },
  '看漲價差': { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-600 dark:text-green-400' },
  '跨式/勒式': { bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-600 dark:text-indigo-400' },
  '賣出跨式/勒式': { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-600 dark:text-orange-400' },
  '純看跌': { bg: 'bg-rose-100 dark:bg-rose-900/30', text: 'text-rose-600 dark:text-rose-400' },
  '純看漲': { bg: 'bg-lime-100 dark:bg-lime-900/30', text: 'text-lime-600 dark:text-lime-400' },
  '選擇權組合': { bg: 'bg-cyan-100 dark:bg-cyan-900/30', text: 'text-cyan-600 dark:text-cyan-400' },
};

export function PortfolioOverview({ portfolio }: PortfolioOverviewProps) {
  const { language } = useAppStore();

  if (!portfolio.positions.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>📊 {t('portfolio_overview', language)}</CardTitle>
        </CardHeader>
        <CardContent className="text-center py-8 text-gray-500">
          {t('status_no_position', language)}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>📊 {t('portfolio_overview', language)}</CardTitle>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Wallet className="h-4 w-4 text-blue-500" />
            <span className="text-gray-500">{t('portfolio_market_value', language)}:</span>
            <span className="font-semibold">{formatCurrency(portfolio.total_market_value)}</span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-500" />
            <span className="text-gray-500">{t('portfolio_unrealized', language)}:</span>
            <span className={cn('font-semibold', getPnLColor(portfolio.total_unrealized_pnl))}>
              {formatCurrency(portfolio.total_unrealized_pnl, true)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-orange-500" />
            <span className="text-gray-500">{t('portfolio_realized', language)}:</span>
            <span className={cn('font-semibold', getPnLColor(portfolio.total_realized_pnl))}>
              {formatCurrency(portfolio.total_realized_pnl, true)}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolio.positions.map((position) => (
            <PositionCard key={position.symbol} position={position} language={language} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface PositionCardProps {
  position: PortfolioData['positions'][0];
  language: 'zh' | 'en';
}

function PositionCard({ position, language }: PositionCardProps) {
  const hasPosition = position.quantity > 0;
  const hasOptions = position.options && position.options.length > 0;
  const strategyColors = position.strategy
    ? STRATEGY_COLORS[position.strategy] || { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400' }
    : null;

  return (
    <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg">{position.symbol}</span>
          {/* 風險等級標籤 */}
          {position.risk_level && (
            <span className={cn(
              'px-2 py-0.5 text-xs font-medium rounded',
              position.risk_level === '高' && 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
              position.risk_level === '中' && 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
              position.risk_level === '低' && 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
            )}>
              {position.risk_level}風險
            </span>
          )}
        </div>
        {position.strategy && strategyColors && (
          <span className={cn('px-2.5 py-1 text-xs font-medium rounded-full', strategyColors.bg, strategyColors.text)}>
            {position.strategy}
          </span>
        )}
      </div>

      {/* Strategy Description */}
      {position.strategy_description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">
          {position.strategy_description}
        </p>
      )}

      {/* Current Price */}
      {position.current_price && position.current_price > 0 && (
        <div className="mb-3">
          <span className="text-sm text-gray-500">
            {language === 'zh' ? '現價: ' : 'Price: '}
          </span>
          <span className="font-semibold">{formatCurrency(position.current_price)}</span>
        </div>
      )}

      {/* Stock Position or Quantity Info */}
      <div className="mb-3 p-2.5 rounded-lg bg-gray-50 dark:bg-gray-900/50">
        <div className="flex items-center gap-2 text-sm">
          <span className="px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded text-xs font-medium">
            {language === 'zh' ? '持倉' : 'Position'}
          </span>
          <span className="font-medium">
            {hasPosition
              ? `${position.quantity.toLocaleString()} ${language === 'zh' ? '股' : 'shares'}`
              : (language === 'zh' ? '無現貨持倉' : 'No stock position')
            }
          </span>
          {position.market_value && position.market_value > 0 && (
            <span className="text-gray-400">
              ({formatCurrency(position.market_value)})
            </span>
          )}
        </div>
        {(position.unrealized_pnl !== undefined && position.unrealized_pnl !== 0) && (
          <div className={cn('text-sm mt-1.5 font-medium', getPnLColor(position.unrealized_pnl || 0))}>
            {language === 'zh' ? '未實現: ' : 'Unrealized: '}
            {`${formatCurrency(position.unrealized_pnl, true)} (${formatPercent(position.unrealized_pnl_pct || 0, true)})`}
          </div>
        )}
      </div>

      {/* Option Legs */}
      {hasOptions && (
        <div className="space-y-2 mb-3">
          {position.options.map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm p-2 rounded-lg bg-gray-50 dark:bg-gray-900/50">
              <span className={cn(
                'w-2.5 h-2.5 rounded-full flex-shrink-0',
                opt.action === 'sell' ? 'bg-red-500' : 'bg-emerald-500'
              )} />
              <span className={cn(
                'font-medium',
                opt.action === 'sell' ? 'text-red-500' : 'text-emerald-500'
              )}>
                {opt.action === 'sell' ? (language === 'zh' ? '賣' : 'Sell') : (language === 'zh' ? '買' : 'Buy')}
              </span>
              <span className="font-medium">
                {opt.option_type === 'call' ? 'Call' : 'Put'} @ ${opt.strike}
              </span>
              <span className="text-gray-600 dark:text-gray-300">
                x {opt.quantity}
              </span>
              {opt.expiry && (
                <span className="text-gray-400 text-xs ml-auto">
                  ({language === 'zh' ? '到期' : 'Exp'}: {opt.expiry})
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Realized P&L */}
      <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">{language === 'zh' ? '已實現' : 'Realized'}:</span>
          <span className={cn('font-bold', getPnLColor(position.realized_pnl))}>
            {formatCurrency(position.realized_pnl, true)}
          </span>
        </div>
      </div>
    </div>
  );
}
