'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import {
  FileText,
  Download,
  Calendar,
  Archive,
  ChevronDown,
  ChevronUp,
  Eye,
  Loader2
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

interface Report {
  filename: string;
  path: string;
  date: string;
  size: number;
  modified: string;
}

interface ReportsResponse {
  reports: Report[];
  total: number;
}

// 使用相對路徑，透過 Next.js rewrites 代理到後端

export default function DailyReportsPage() {
  const { language } = useAppStore();
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [expandedReport, setExpandedReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);

  // 設置默認日期範圍（最近 30 天）
  useEffect(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    setEndDate(end.toISOString().split('T')[0]);
    setStartDate(start.toISOString().split('T')[0]);
  }, []);

  // 獲取報告列表
  const { data: reportsData, isLoading, refetch } = useQuery<ReportsResponse>({
    queryKey: ['daily-reports', startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      params.append('limit', '100');

      const res = await fetch(`/api/reports?${params}`);
      if (!res.ok) throw new Error('Failed to fetch reports');
      return res.json();
    },
    enabled: !!startDate && !!endDate,
  });

  // 載入報告內容
  const loadReportContent = async (filename: string) => {
    if (expandedReport === filename) {
      setExpandedReport(null);
      setReportContent(null);
      return;
    }

    setLoadingContent(true);
    setExpandedReport(filename);

    try {
      const res = await fetch(`/api/reports/${filename}`);
      if (!res.ok) throw new Error('Failed to fetch report content');
      const data = await res.json();
      setReportContent(data.content);
    } catch (error) {
      console.error('Failed to load report:', error);
      setReportContent('載入失敗');
    } finally {
      setLoadingContent(false);
    }
  };

  // 下載單一報告
  const downloadReport = (filename: string) => {
    window.open(`/api/reports/${filename}/download`, '_blank');
  };

  // 批量下載 ZIP
  const downloadZip = () => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    window.open(`/api/reports/download/zip?${params}`, '_blank');
  };

  // 格式化檔案大小
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // 快速選擇日期範圍
  const setQuickRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    setEndDate(end.toISOString().split('T')[0]);
    setStartDate(start.toISOString().split('T')[0]);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">
          {language === 'zh' ? '📄 每日報告管理' : '📄 Daily Reports'}
        </h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh'
            ? '查看、下載和管理每日交易報告'
            : 'View, download and manage daily trading reports'}
        </p>
      </div>

      {/* 日期範圍選擇器 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            {language === 'zh' ? '日期範圍' : 'Date Range'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            {/* 快速選擇按鈕 */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuickRange(7)}
              >
                {language === 'zh' ? '最近 7 天' : 'Last 7 days'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuickRange(30)}
              >
                {language === 'zh' ? '最近 30 天' : 'Last 30 days'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuickRange(90)}
              >
                {language === 'zh' ? '最近 3 個月' : 'Last 3 months'}
              </Button>
            </div>

            {/* 日期輸入 */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
              <span className="text-gray-500">~</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>

            {/* 批量下載按鈕 */}
            <Button
              onClick={downloadZip}
              disabled={!reportsData?.reports?.length}
              className="ml-auto"
            >
              <Archive className="h-4 w-4 mr-2" />
              {language === 'zh'
                ? `打包下載 (${reportsData?.total || 0} 個)`
                : `Download ZIP (${reportsData?.total || 0})`}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 報告列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {language === 'zh' ? '報告列表' : 'Report List'}
            {reportsData?.total ? (
              <span className="text-sm font-normal text-gray-500">
                ({reportsData.total} {language === 'zh' ? '份' : 'reports'})
              </span>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : reportsData?.reports?.length ? (
            <div className="space-y-3">
              {reportsData.reports.map((report) => (
                <div
                  key={report.filename}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
                >
                  {/* 報告標題列 */}
                  <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50">
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-blue-500" />
                      <div>
                        <p className="font-medium">{report.date}</p>
                        <p className="text-sm text-gray-500">
                          {formatSize(report.size)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => loadReportContent(report.filename)}
                      >
                        {expandedReport === report.filename ? (
                          <>
                            <ChevronUp className="h-4 w-4 mr-1" />
                            {language === 'zh' ? '收合' : 'Collapse'}
                          </>
                        ) : (
                          <>
                            <Eye className="h-4 w-4 mr-1" />
                            {language === 'zh' ? '預覽' : 'Preview'}
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => downloadReport(report.filename)}
                      >
                        <Download className="h-4 w-4 mr-1" />
                        {language === 'zh' ? '下載' : 'Download'}
                      </Button>
                    </div>
                  </div>

                  {/* 報告內容預覽 */}
                  {expandedReport === report.filename && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                      {loadingContent ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                        </div>
                      ) : reportContent ? (
                        <div className="prose dark:prose-invert max-w-none">
                          <MarkdownRenderer content={reportContent} />
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>
                {language === 'zh'
                  ? '這個日期範圍內沒有報告'
                  : 'No reports in this date range'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 使用說明 */}
      <Card>
        <CardHeader>
          <CardTitle>
            {language === 'zh' ? '💡 使用說明' : '💡 Tips'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-gray-600 dark:text-gray-400">
            <li>
              {language === 'zh'
                ? '每日報告會在排程時間自動生成並發送到 Telegram'
                : 'Daily reports are automatically generated and sent to Telegram at scheduled time'}
            </li>
            <li>
              {language === 'zh'
                ? '可以使用「打包下載」功能將多個報告打包成 ZIP 檔案'
                : 'Use "Download ZIP" to package multiple reports into a single ZIP file'}
            </li>
            <li>
              {language === 'zh'
                ? '下載的 Markdown 檔案可以提供給其他 AI 進行分析'
                : 'Downloaded Markdown files can be provided to other AI for analysis'}
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
