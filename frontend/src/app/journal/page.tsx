'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, MFEMAERecord, MFEMAEAnalysis, TradePlan, TradeNote } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import {
    Loader2,
    BarChart3,
    Target,
    FileText,
    Brain,
    RefreshCw,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    CheckCircle,
    Plus,
    ChevronRight
} from 'lucide-react';

type TabType = 'mfe-mae' | 'plans' | 'notes' | 'ai-review';

export default function JournalPage() {
    const { language } = useAppStore();
    const [activeTab, setActiveTab] = useState<TabType>('mfe-mae');
    const queryClient = useQueryClient();

    const tabs = [
        { id: 'mfe-mae' as TabType, label: language === 'zh' ? '📊 MFE/MAE 分析' : '📊 MFE/MAE Analysis', icon: BarChart3 },
        { id: 'plans' as TabType, label: language === 'zh' ? '🎯 交易計劃' : '🎯 Trade Plans', icon: Target },
        { id: 'notes' as TabType, label: language === 'zh' ? '📝 日誌筆記' : '📝 Notes', icon: FileText },
        { id: 'ai-review' as TabType, label: language === 'zh' ? '🧠 AI 綜合審查' : '🧠 AI Review', icon: Brain },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold">{language === 'zh' ? '📔 交易日誌' : '📔 Trading Journal'}</h1>
                <p className="text-gray-500 mt-1">
                    {language === 'zh' ? 'MFE/MAE 分析、交易計劃與日誌筆記' : 'MFE/MAE Analysis, Trade Plans & Notes'}
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={cn(
                            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium',
                            activeTab === tab.id
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                        )}
                    >
                        <tab.icon className="h-4 w-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'mfe-mae' && <MFEMAETab language={language} />}
            {activeTab === 'plans' && <PlansTab language={language} />}
            {activeTab === 'notes' && <NotesTab language={language} />}
            {activeTab === 'ai-review' && <AIReviewTab language={language} />}
        </div>
    );
}

// ========== MFE/MAE 分析 Tab ==========
function MFEMAETab({ language }: { language: string }) {
    const queryClient = useQueryClient();
    const [aiAdvice, setAiAdvice] = useState<string | null>(null);

    const { data: analysis, isLoading: analysisLoading } = useQuery({
        queryKey: ['mfe-mae-analysis'],
        queryFn: apiClient.getMFEMAEAnalysis,
    });

    const { data: records, isLoading: recordsLoading } = useQuery({
        queryKey: ['mfe-mae-records'],
        queryFn: () => apiClient.getMFEMAERecords(),
    });

    const calculateMutation = useMutation({
        mutationFn: () => apiClient.calculateMFEMAE(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['mfe-mae-analysis'] });
            queryClient.invalidateQueries({ queryKey: ['mfe-mae-records'] });
        },
    });

    const aiAdviceMutation = useMutation({
        mutationFn: () => apiClient.getMFEMAEAIAdvice(),
        onSuccess: (data) => setAiAdvice(data),
    });

    const isLoading = analysisLoading || recordsLoading;

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 控制按鈕 */}
            <div className="flex gap-3">
                <Button
                    onClick={() => calculateMutation.mutate()}
                    disabled={calculateMutation.isPending}
                >
                    {calculateMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                    )}
                    {language === 'zh' ? '重新計算 MFE/MAE' : 'Recalculate MFE/MAE'}
                </Button>
                <Button
                    variant="outline"
                    onClick={() => aiAdviceMutation.mutate()}
                    disabled={aiAdviceMutation.isPending}
                >
                    {aiAdviceMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                        <Brain className="h-4 w-4 mr-2" />
                    )}
                    {language === 'zh' ? 'AI 改進建議' : 'AI Advice'}
                </Button>
            </div>

            {/* 統計卡片 */}
            {analysis && (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <StatCard
                        label={language === 'zh' ? '已分析交易' : 'Analyzed Trades'}
                        value={analysis.total_trades?.toString() || '0'}
                    />
                    <StatCard
                        label={language === 'zh' ? '平均 MFE' : 'Avg MFE'}
                        value={`${(analysis.avg_mfe || 0).toFixed(1)}%`}
                        color="text-emerald-500"
                    />
                    <StatCard
                        label={language === 'zh' ? '平均 MAE' : 'Avg MAE'}
                        value={`${(analysis.avg_mae || 0).toFixed(1)}%`}
                        color="text-red-500"
                    />
                    <StatCard
                        label={language === 'zh' ? '平均效率' : 'Avg Efficiency'}
                        value={`${((analysis.avg_efficiency || 0) * 100).toFixed(0)}%`}
                        color={(analysis.avg_efficiency || 0) > 0.5 ? 'text-emerald-500' : 'text-yellow-500'}
                    />
                    <StatCard
                        label={language === 'zh' ? '高效交易' : 'Efficient'}
                        value={analysis.efficient_count?.toString() || '0'}
                        color="text-emerald-500"
                    />
                    <StatCard
                        label={language === 'zh' ? '低效交易' : 'Inefficient'}
                        value={analysis.inefficient_count?.toString() || '0'}
                        color="text-red-500"
                    />
                </div>
            )}

            {/* MFE/MAE 散點圖 */}
            {records && records.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>{language === 'zh' ? '📈 MFE/MAE 分布圖' : '📈 MFE/MAE Distribution'}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <MFEMAEChart records={records} language={language} />
                    </CardContent>
                </Card>
            )}

            {/* 問題與建議 */}
            {analysis && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                                {language === 'zh' ? '識別的問題' : 'Identified Issues'}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {analysis.issues && analysis.issues.length > 0 ? (
                                <ul className="space-y-2">
                                    {analysis.issues.map((issue, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-sm">
                                            <span className="text-yellow-500">⚠️</span>
                                            <span>{issue}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-emerald-500 flex items-center gap-2">
                                    <CheckCircle className="h-4 w-4" />
                                    {language === 'zh' ? '目前沒有發現明顯問題' : 'No obvious issues found'}
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <TrendingUp className="h-5 w-5 text-blue-500" />
                                {language === 'zh' ? '改進建議' : 'Suggestions'}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {analysis.suggestions && analysis.suggestions.length > 0 ? (
                                <ul className="space-y-2">
                                    {analysis.suggestions.map((suggestion, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-sm">
                                            <span className="text-blue-500">💡</span>
                                            <span>{suggestion}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-gray-500">
                                    {language === 'zh' ? '暫無建議' : 'No suggestions'}
                                </p>
                            )}
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* 交易記錄表格 */}
            {records && records.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>{language === 'zh' ? '📋 MFE/MAE 詳細記錄' : '📋 MFE/MAE Records'}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-gray-200 dark:border-gray-700">
                                        <th className="text-left py-2 px-2">{language === 'zh' ? '標的' : 'Symbol'}</th>
                                        <th className="text-left py-2 px-2">{language === 'zh' ? '進場' : 'Entry'}</th>
                                        <th className="text-right py-2 px-2">MFE</th>
                                        <th className="text-right py-2 px-2">MAE</th>
                                        <th className="text-right py-2 px-2">{language === 'zh' ? '效率' : 'Efficiency'}</th>
                                        <th className="text-right py-2 px-2">{language === 'zh' ? '持倉天數' : 'Days'}</th>
                                        <th className="text-right py-2 px-2">{language === 'zh' ? '實現盈虧' : 'Realized'}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {records.slice(0, 20).map((r, idx) => (
                                        <tr key={idx} className="border-b border-gray-100 dark:border-gray-800">
                                            <td className="py-2 px-2 font-medium">{r.symbol}</td>
                                            <td className="py-2 px-2 text-gray-500">{r.entry_date}</td>
                                            <td className="py-2 px-2 text-right text-emerald-500">
                                                {r.mfe != null ? `+${r.mfe.toFixed(1)}%` : 'N/A'}
                                            </td>
                                            <td className="py-2 px-2 text-right text-red-500">
                                                {r.mae != null ? `${r.mae.toFixed(1)}%` : 'N/A'}
                                            </td>
                                            <td className={cn(
                                                'py-2 px-2 text-right font-medium',
                                                (r.trade_efficiency || 0) > 0.5 ? 'text-emerald-500' : 'text-yellow-500'
                                            )}>
                                                {r.trade_efficiency != null ? `${(r.trade_efficiency * 100).toFixed(0)}%` : 'N/A'}
                                            </td>
                                            <td className="py-2 px-2 text-right text-gray-500">
                                                {r.holding_days ?? 'N/A'}
                                            </td>
                                            <td className={cn(
                                                'py-2 px-2 text-right font-medium',
                                                (r.realized_pnl || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'
                                            )}>
                                                {r.realized_pnl != null ? `${r.realized_pnl.toFixed(1)}%` : 'N/A'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* AI 建議 */}
            {aiAdvice && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Brain className="h-5 w-5 text-purple-500" />
                            {language === 'zh' ? 'AI 改進建議' : 'AI Improvement Advice'}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none">
                            <div className="whitespace-pre-wrap text-sm">{aiAdvice}</div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

// MFE/MAE 視覺化圖表（類似選擇權損益圖）
function MFEMAEChart({ records, language }: { records: MFEMAERecord[]; language: string }) {
    // 過濾有效數據
    const validRecords = records.filter(r => r.mfe != null && r.mae != null);

    if (validRecords.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                {language === 'zh' ? '沒有足夠的數據生成圖表' : 'Not enough data to generate chart'}
            </div>
        );
    }

    // 計算圖表範圍
    const maxMFE = Math.max(...validRecords.map(r => r.mfe || 0));
    const minMAE = Math.min(...validRecords.map(r => r.mae || 0));
    const chartHeight = 300;
    const chartWidth = 600;
    const padding = 50;

    // 計算比例
    const yScale = (chartHeight - padding * 2) / (maxMFE - minMAE || 1);
    const xScale = (chartWidth - padding * 2) / validRecords.length;

    // 生成點位
    const points = validRecords.map((r, i) => ({
        x: padding + i * xScale + xScale / 2,
        mfeY: padding + (maxMFE - (r.mfe || 0)) * yScale,
        maeY: padding + (maxMFE - (r.mae || 0)) * yScale,
        realizedY: padding + (maxMFE - (r.realized_pnl || 0)) * yScale,
        symbol: r.symbol,
        mfe: r.mfe || 0,
        mae: r.mae || 0,
        realized: r.realized_pnl || 0,
        efficiency: r.trade_efficiency || 0,
    }));

    // 生成 MFE 區域路線
    const mfePath = points.map((p, i) =>
        i === 0 ? `M ${p.x} ${p.mfeY}` : `L ${p.x} ${p.mfeY}`
    ).join(' ');

    // 生成 MAE 區域路線
    const maePath = points.map((p, i) =>
        i === 0 ? `M ${p.x} ${p.maeY}` : `L ${p.x} ${p.maeY}`
    ).join(' ');

    // 生成實現盈虧路線
    const realizedPath = points.map((p, i) =>
        i === 0 ? `M ${p.x} ${p.realizedY}` : `L ${p.x} ${p.realizedY}`
    ).join(' ');

    // 零線位置
    const zeroY = padding + maxMFE * yScale;

    return (
        <div className="relative">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto">
                {/* 背景網格 */}
                <defs>
                    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.3" />
                    </pattern>
                </defs>
                <rect x={padding} y={padding} width={chartWidth - padding * 2} height={chartHeight - padding * 2} fill="url(#grid)" />

                {/* MFE 區域（綠色漸變） */}
                <defs>
                    <linearGradient id="mfeGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#10B981" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#10B981" stopOpacity="0.1" />
                    </linearGradient>
                </defs>
                <path
                    d={`${mfePath} L ${points[points.length - 1].x} ${zeroY} L ${points[0].x} ${zeroY} Z`}
                    fill="url(#mfeGradient)"
                />

                {/* MAE 區域（紅色漸變） */}
                <defs>
                    <linearGradient id="maeGradient" x1="0%" y1="100%" x2="0%" y2="0%">
                        <stop offset="0%" stopColor="#EF4444" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#EF4444" stopOpacity="0.1" />
                    </linearGradient>
                </defs>
                <path
                    d={`${maePath} L ${points[points.length - 1].x} ${zeroY} L ${points[0].x} ${zeroY} Z`}
                    fill="url(#maeGradient)"
                />

                {/* 零線 */}
                <line
                    x1={padding}
                    y1={zeroY}
                    x2={chartWidth - padding}
                    y2={zeroY}
                    stroke="#6B7280"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                />

                {/* MFE 線 */}
                <path d={mfePath} fill="none" stroke="#10B981" strokeWidth="2" />

                {/* MAE 線 */}
                <path d={maePath} fill="none" stroke="#EF4444" strokeWidth="2" />

                {/* 實現盈虧線 */}
                <path d={realizedPath} fill="none" stroke="#3B82F6" strokeWidth="3" />

                {/* 數據點 */}
                {points.map((p, i) => (
                    <g key={i}>
                        {/* MFE 點 */}
                        <circle cx={p.x} cy={p.mfeY} r="4" fill="#10B981" />
                        {/* MAE 點 */}
                        <circle cx={p.x} cy={p.maeY} r="4" fill="#EF4444" />
                        {/* 實現盈虧點 */}
                        <circle cx={p.x} cy={p.realizedY} r="5" fill="#3B82F6" stroke="white" strokeWidth="2" />
                    </g>
                ))}

                {/* Y 軸標籤 */}
                <text x={padding - 10} y={padding} textAnchor="end" className="text-xs fill-gray-400">
                    +{maxMFE.toFixed(0)}%
                </text>
                <text x={padding - 10} y={zeroY} textAnchor="end" className="text-xs fill-gray-400">
                    0%
                </text>
                <text x={padding - 10} y={chartHeight - padding} textAnchor="end" className="text-xs fill-gray-400">
                    {minMAE.toFixed(0)}%
                </text>

                {/* 圖例 */}
                <g transform={`translate(${chartWidth - 150}, ${padding})`}>
                    <rect x="0" y="0" width="140" height="70" fill="#1F2937" rx="4" opacity="0.8" />
                    <line x1="10" y1="15" x2="30" y2="15" stroke="#10B981" strokeWidth="2" />
                    <text x="40" y="18" className="text-xs fill-gray-300">MFE (最大浮盈)</text>
                    <line x1="10" y1="35" x2="30" y2="35" stroke="#EF4444" strokeWidth="2" />
                    <text x="40" y="38" className="text-xs fill-gray-300">MAE (最大浮虧)</text>
                    <line x1="10" y1="55" x2="30" y2="55" stroke="#3B82F6" strokeWidth="3" />
                    <text x="40" y="58" className="text-xs fill-gray-300">實現盈虧</text>
                </g>
            </svg>

            {/* 說明文字 */}
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                    {language === 'zh'
                        ? '💡 圖表說明：綠色區域代表 MFE（最大浮盈），紅色區域代表 MAE（最大浮虧），藍色線代表實際實現的盈虧。理想情況下，實現盈虧應該接近 MFE 線。'
                        : '💡 Chart explanation: Green area represents MFE (Max Favorable Excursion), red area represents MAE (Max Adverse Excursion), and blue line represents realized P&L. Ideally, realized P&L should be close to the MFE line.'}
                </p>
            </div>
        </div>
    );
}

// ========== 交易計劃 Tab ==========
function PlansTab({ language }: { language: string }) {
    const [showForm, setShowForm] = useState(false);
    const [selectedPlan, setSelectedPlan] = useState<TradePlan | null>(null);
    const [aiReview, setAiReview] = useState<string | null>(null);
    const queryClient = useQueryClient();

    const { data: plans, isLoading } = useQuery({
        queryKey: ['trade-plans'],
        queryFn: () => apiClient.getTradePlans(),
    });

    const aiReviewMutation = useMutation({
        mutationFn: (planId: number) => apiClient.getPlanAIReview(planId),
        onSuccess: (data) => setAiReview(data),
    });

    const pendingPlans = plans?.filter(p => p.status === 'pending') || [];
    const executedPlans = plans?.filter(p => p.status === 'executed') || [];

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 新增計劃按鈕 */}
            <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                {language === 'zh' ? '新增交易計劃' : 'New Trade Plan'}
            </Button>

            {/* 待執行計劃 */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Target className="h-5 w-5 text-blue-500" />
                        {language === 'zh' ? '待執行計劃' : 'Pending Plans'} ({pendingPlans.length})
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {pendingPlans.length > 0 ? (
                        <div className="space-y-4">
                            {pendingPlans.map((plan) => (
                                <PlanCard
                                    key={plan.plan_id}
                                    plan={plan}
                                    language={language}
                                    onAIReview={() => {
                                        setSelectedPlan(plan);
                                        aiReviewMutation.mutate(plan.plan_id);
                                    }}
                                />
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-500 text-center py-8">
                            {language === 'zh' ? '沒有待執行的交易計劃' : 'No pending trade plans'}
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* 已執行計劃 */}
            {executedPlans.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-emerald-500" />
                            {language === 'zh' ? '已執行計劃' : 'Executed Plans'} ({executedPlans.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {executedPlans.slice(0, 5).map((plan) => (
                                <PlanCard
                                    key={plan.plan_id}
                                    plan={plan}
                                    language={language}
                                    onAIReview={() => {
                                        setSelectedPlan(plan);
                                        aiReviewMutation.mutate(plan.plan_id);
                                    }}
                                />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* AI 評價結果 */}
            {aiReview && selectedPlan && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Brain className="h-5 w-5 text-purple-500" />
                            {language === 'zh' ? `AI 評價: ${selectedPlan.symbol}` : `AI Review: ${selectedPlan.symbol}`}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none">
                            <div className="whitespace-pre-wrap text-sm">{aiReview}</div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 新增計劃表單 Modal */}
            {showForm && (
                <PlanFormModal
                    language={language}
                    onClose={() => setShowForm(false)}
                    onSuccess={() => {
                        setShowForm(false);
                        queryClient.invalidateQueries({ queryKey: ['trade-plans'] });
                    }}
                />
            )}
        </div>
    );
}

function PlanCard({
    plan,
    language,
    onAIReview
}: {
    plan: TradePlan;
    language: string;
    onAIReview: () => void;
}) {
    return (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <span className="font-bold text-lg">{plan.symbol}</span>
                    <span className={cn(
                        'px-2 py-0.5 rounded text-xs',
                        plan.direction === 'long'
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-600'
                    )}>
                        {plan.direction.toUpperCase()}
                    </span>
                    <span className={cn(
                        'px-2 py-0.5 rounded text-xs',
                        plan.status === 'pending' ? 'bg-yellow-100 text-yellow-600' :
                            plan.status === 'executed' ? 'bg-emerald-100 text-emerald-600' :
                                'bg-gray-100 text-gray-600'
                    )}>
                        {plan.status}
                    </span>
                </div>
                <Button variant="outline" size="sm" onClick={onAIReview}>
                    <Brain className="h-4 w-4 mr-1" />
                    AI
                </Button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                    <span className="text-gray-500">{language === 'zh' ? '進場區間' : 'Entry Range'}</span>
                    <p className="font-medium">
                        ${plan.entry_price_min || 'N/A'} - ${plan.entry_price_max || 'N/A'}
                    </p>
                </div>
                <div>
                    <span className="text-gray-500">{language === 'zh' ? '目標價' : 'Target'}</span>
                    <p className="font-medium text-emerald-500">${plan.target_price || 'N/A'}</p>
                </div>
                <div>
                    <span className="text-gray-500">{language === 'zh' ? '停損價' : 'Stop Loss'}</span>
                    <p className="font-medium text-red-500">${plan.stop_loss_price || 'N/A'}</p>
                </div>
                <div>
                    <span className="text-gray-500">{language === 'zh' ? '風險報酬比' : 'R/R'}</span>
                    <p className="font-medium">{plan.risk_reward_ratio || 'N/A'}</p>
                </div>
            </div>

            {plan.thesis && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                    <p className="text-sm text-gray-600 dark:text-gray-400">{plan.thesis}</p>
                </div>
            )}
        </div>
    );
}

function PlanFormModal({
    language,
    onClose,
    onSuccess
}: {
    language: string;
    onClose: () => void;
    onSuccess: () => void;
}) {
    const [formData, setFormData] = useState({
        symbol: '',
        direction: 'long' as 'long' | 'short',
        entry_price_min: '',
        entry_price_max: '',
        target_price: '',
        stop_loss_price: '',
        thesis: '',
        position_size: '',
    });

    const createMutation = useMutation({
        mutationFn: () => apiClient.createTradePlan({
            ...formData,
            entry_price_min: formData.entry_price_min ? parseFloat(formData.entry_price_min) : undefined,
            entry_price_max: formData.entry_price_max ? parseFloat(formData.entry_price_max) : undefined,
            target_price: formData.target_price ? parseFloat(formData.target_price) : undefined,
            stop_loss_price: formData.stop_loss_price ? parseFloat(formData.stop_loss_price) : undefined,
        }),
        onSuccess: onSuccess,
    });

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg">
                <CardHeader>
                    <CardTitle>{language === 'zh' ? '新增交易計劃' : 'New Trade Plan'}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '標的' : 'Symbol'}</label>
                            <input
                                type="text"
                                value={formData.symbol}
                                onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                placeholder="e.g. AAPL"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '方向' : 'Direction'}</label>
                            <select
                                value={formData.direction}
                                onChange={(e) => setFormData({ ...formData, direction: e.target.value as 'long' | 'short' })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                            >
                                <option value="long">Long (做多)</option>
                                <option value="short">Short (做空)</option>
                            </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '進場價 (低)' : 'Entry Min'}</label>
                                <input
                                    type="number"
                                    value={formData.entry_price_min}
                                    onChange={(e) => setFormData({ ...formData, entry_price_min: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                    step="0.01"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '進場價 (高)' : 'Entry Max'}</label>
                                <input
                                    type="number"
                                    value={formData.entry_price_max}
                                    onChange={(e) => setFormData({ ...formData, entry_price_max: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                    step="0.01"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '目標價' : 'Target'}</label>
                                <input
                                    type="number"
                                    value={formData.target_price}
                                    onChange={(e) => setFormData({ ...formData, target_price: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                    step="0.01"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '停損價' : 'Stop Loss'}</label>
                                <input
                                    type="number"
                                    value={formData.stop_loss_price}
                                    onChange={(e) => setFormData({ ...formData, stop_loss_price: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                    step="0.01"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '交易論點' : 'Thesis'}</label>
                            <textarea
                                value={formData.thesis}
                                onChange={(e) => setFormData({ ...formData, thesis: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600 h-24"
                                placeholder={language === 'zh' ? '為什麼要做這筆交易？' : 'Why this trade?'}
                            />
                        </div>

                        <div className="flex gap-3 justify-end">
                            <Button variant="outline" onClick={onClose}>
                                {language === 'zh' ? '取消' : 'Cancel'}
                            </Button>
                            <Button
                                onClick={() => createMutation.mutate()}
                                disabled={!formData.symbol || createMutation.isPending}
                            >
                                {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                                {language === 'zh' ? '建立計劃' : 'Create Plan'}
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

// ========== 日誌筆記 Tab ==========
function NotesTab({ language }: { language: string }) {
    const [showForm, setShowForm] = useState(false);
    const [selectedNote, setSelectedNote] = useState<TradeNote | null>(null);
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
    const queryClient = useQueryClient();

    const { data: notes, isLoading } = useQuery({
        queryKey: ['trade-notes'],
        queryFn: () => apiClient.getTradeNotes({ limit: 50 }),
    });

    const aiAnalysisMutation = useMutation({
        mutationFn: (noteId: number) => apiClient.getNoteAIAnalysis(noteId),
        onSuccess: (data) => setAiAnalysis(data),
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 新增筆記按鈕 */}
            <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                {language === 'zh' ? '新增日誌' : 'New Note'}
            </Button>

            {/* 筆記列表 */}
            <div className="space-y-4">
                {notes && notes.length > 0 ? (
                    notes.map((note) => (
                        <Card key={note.note_id} className="hover:shadow-lg transition-shadow">
                            <CardContent className="pt-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className={cn(
                                                'px-2 py-0.5 rounded text-xs',
                                                note.note_type === 'daily' ? 'bg-blue-100 text-blue-600' :
                                                    note.note_type === 'trade' ? 'bg-emerald-100 text-emerald-600' :
                                                        'bg-gray-100 text-gray-600'
                                            )}>
                                                {note.note_type}
                                            </span>
                                            <span className="text-gray-500 text-sm">{note.date}</span>
                                            {note.symbol && (
                                                <span className="font-medium">{note.symbol}</span>
                                            )}
                                            {note.mood && (
                                                <span className="text-lg">{
                                                    note.mood === 'great' ? '😊' :
                                                        note.mood === 'good' ? '🙂' :
                                                            note.mood === 'neutral' ? '😐' :
                                                                note.mood === 'bad' ? '😟' : '😫'
                                                }</span>
                                            )}
                                        </div>
                                        {note.title && (
                                            <h3 className="font-semibold mb-1">{note.title}</h3>
                                        )}
                                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                            {note.content}
                                        </p>
                                        {note.tags && note.tags.length > 0 && (
                                            <div className="flex flex-wrap gap-1 mt-2">
                                                {note.tags.map((tag, idx) => (
                                                    <span key={idx} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                                                        #{tag}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => {
                                            setSelectedNote(note);
                                            aiAnalysisMutation.mutate(note.note_id);
                                        }}
                                    >
                                        <Brain className="h-4 w-4" />
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))
                ) : (
                    <Card>
                        <CardContent className="flex flex-col items-center justify-center h-48">
                            <FileText className="h-12 w-12 text-gray-300 mb-4" />
                            <p className="text-gray-500">
                                {language === 'zh' ? '還沒有日誌筆記，開始記錄你的交易心得吧！' : 'No notes yet. Start recording your trading insights!'}
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* AI 分析結果 */}
            {aiAnalysis && selectedNote && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Brain className="h-5 w-5 text-purple-500" />
                            {language === 'zh' ? 'AI 分析' : 'AI Analysis'}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none">
                            <div className="whitespace-pre-wrap text-sm">{aiAnalysis}</div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 新增筆記表單 Modal */}
            {showForm && (
                <NoteFormModal
                    language={language}
                    onClose={() => setShowForm(false)}
                    onSuccess={() => {
                        setShowForm(false);
                        queryClient.invalidateQueries({ queryKey: ['trade-notes'] });
                    }}
                />
            )}
        </div>
    );
}

function NoteFormModal({
    language,
    onClose,
    onSuccess
}: {
    language: string;
    onClose: () => void;
    onSuccess: () => void;
}) {
    const [formData, setFormData] = useState({
        note_type: 'daily' as 'daily' | 'trade' | 'weekly' | 'monthly' | 'misc',
        date: new Date().toISOString().split('T')[0],
        symbol: '',
        title: '',
        content: '',
        mood: '',
        confidence_level: 5,
        lessons_learned: '',
    });

    const createMutation = useMutation({
        mutationFn: () => apiClient.createTradeNote({
            ...formData,
            symbol: formData.symbol || undefined,
            title: formData.title || undefined,
            mood: formData.mood || undefined,
            lessons_learned: formData.lessons_learned || undefined,
        }),
        onSuccess: onSuccess,
    });

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <CardHeader>
                    <CardTitle>{language === 'zh' ? '新增日誌' : 'New Note'}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '類型' : 'Type'}</label>
                                <select
                                    value={formData.note_type}
                                    onChange={(e) => setFormData({ ...formData, note_type: e.target.value as typeof formData.note_type })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                >
                                    <option value="daily">每日日誌</option>
                                    <option value="trade">交易筆記</option>
                                    <option value="weekly">週回顧</option>
                                    <option value="monthly">月回顧</option>
                                    <option value="misc">其他</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '日期' : 'Date'}</label>
                                <input
                                    type="date"
                                    value={formData.date}
                                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '標的 (選填)' : 'Symbol (optional)'}</label>
                                <input
                                    type="text"
                                    value={formData.symbol}
                                    onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                    placeholder="e.g. AAPL"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">{language === 'zh' ? '情緒' : 'Mood'}</label>
                                <select
                                    value={formData.mood}
                                    onChange={(e) => setFormData({ ...formData, mood: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                                >
                                    <option value="">-- 選擇 --</option>
                                    <option value="great">😊 很好</option>
                                    <option value="good">🙂 好</option>
                                    <option value="neutral">😐 普通</option>
                                    <option value="bad">😟 不好</option>
                                    <option value="terrible">😫 很差</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '標題 (選填)' : 'Title (optional)'}</label>
                            <input
                                type="text"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '內容' : 'Content'} *</label>
                            <textarea
                                value={formData.content}
                                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600 h-32"
                                placeholder={language === 'zh' ? '今天的交易心得...' : 'Trading thoughts...'}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '信心水平' : 'Confidence'}: {formData.confidence_level}/10</label>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={formData.confidence_level}
                                onChange={(e) => setFormData({ ...formData, confidence_level: parseInt(e.target.value) })}
                                className="w-full"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">{language === 'zh' ? '學到的教訓' : 'Lessons Learned'}</label>
                            <textarea
                                value={formData.lessons_learned}
                                onChange={(e) => setFormData({ ...formData, lessons_learned: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600 h-20"
                            />
                        </div>

                        <div className="flex gap-3 justify-end">
                            <Button variant="outline" onClick={onClose}>
                                {language === 'zh' ? '取消' : 'Cancel'}
                            </Button>
                            <Button
                                onClick={() => createMutation.mutate()}
                                disabled={!formData.content || createMutation.isPending}
                            >
                                {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                                {language === 'zh' ? '儲存' : 'Save'}
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

// ========== AI 綜合審查 Tab ==========
function AIReviewTab({ language }: { language: string }) {
    const [review, setReview] = useState<string | null>(null);

    const reviewMutation = useMutation({
        mutationFn: apiClient.getComprehensiveAIReview,
        onSuccess: (data) => setReview(data),
    });

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="h-6 w-6 text-purple-500" />
                        {language === 'zh' ? 'AI 綜合審查' : 'AI Comprehensive Review'}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-gray-500 mb-4">
                        {language === 'zh'
                            ? 'AI 會綜合分析你的 MFE/MAE 數據、交易計劃和日誌筆記，給出全面的評估和改進建議。'
                            : 'AI will analyze your MFE/MAE data, trade plans, and notes to provide comprehensive assessment and improvement suggestions.'}
                    </p>
                    <Button
                        onClick={() => reviewMutation.mutate()}
                        disabled={reviewMutation.isPending}
                        size="lg"
                    >
                        {reviewMutation.isPending ? (
                            <>
                                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                {language === 'zh' ? '分析中...' : 'Analyzing...'}
                            </>
                        ) : (
                            <>
                                <Brain className="h-5 w-5 mr-2" />
                                {language === 'zh' ? '開始綜合審查' : 'Start Comprehensive Review'}
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {review && (
                <Card>
                    <CardHeader>
                        <CardTitle>{language === 'zh' ? '📋 審查結果' : '📋 Review Results'}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none">
                            <div className="whitespace-pre-wrap">{review}</div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

// ========== 輔助元件 ==========
function StatCard({
    label,
    value,
    color = ''
}: {
    label: string;
    value: string;
    color?: string;
}) {
    return (
        <Card>
            <CardContent className="pt-4 text-center">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className={cn('text-xl font-bold', color)}>{value}</p>
            </CardContent>
        </Card>
    );
}
