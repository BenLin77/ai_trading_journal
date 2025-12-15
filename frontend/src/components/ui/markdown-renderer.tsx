'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

/**
 * 通用 Markdown 渲染組件
 * 支援 AI 回應的格式化顯示
 */
export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
    if (!content) return null;

    return (
        <div className={cn('prose prose-sm dark:prose-invert max-w-none', className)}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // 標題樣式
                    h1: ({ children }) => (
                        <h1 className="text-xl font-bold mt-4 mb-2 text-gray-900 dark:text-gray-100">
                            {children}
                        </h1>
                    ),
                    h2: ({ children }) => (
                        <h2 className="text-lg font-semibold mt-4 mb-2 text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700 pb-1">
                            {children}
                        </h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="text-base font-semibold mt-3 mb-1 text-gray-700 dark:text-gray-300">
                            {children}
                        </h3>
                    ),
                    h4: ({ children }) => (
                        <h4 className="text-sm font-semibold mt-2 mb-1 text-gray-600 dark:text-gray-400">
                            {children}
                        </h4>
                    ),
                    // 段落
                    p: ({ children }) => (
                        <p className="my-2 text-gray-700 dark:text-gray-300 leading-relaxed">
                            {children}
                        </p>
                    ),
                    // 列表
                    ul: ({ children }) => (
                        <ul className="list-disc list-inside my-2 space-y-1 text-gray-700 dark:text-gray-300">
                            {children}
                        </ul>
                    ),
                    ol: ({ children }) => (
                        <ol className="list-decimal list-inside my-2 space-y-1 text-gray-700 dark:text-gray-300">
                            {children}
                        </ol>
                    ),
                    li: ({ children }) => (
                        <li className="ml-2">{children}</li>
                    ),
                    // 強調
                    strong: ({ children }) => (
                        <strong className="font-semibold text-gray-900 dark:text-gray-100">
                            {children}
                        </strong>
                    ),
                    em: ({ children }) => (
                        <em className="italic text-gray-600 dark:text-gray-400">{children}</em>
                    ),
                    // 程式碼
                    code: ({ children }) => (
                        <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-emerald-600 dark:text-emerald-400">
                            {children}
                        </code>
                    ),
                    pre: ({ children }) => (
                        <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto my-2">
                            {children}
                        </pre>
                    ),
                    // 引用
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-emerald-500 pl-4 my-2 italic text-gray-600 dark:text-gray-400">
                            {children}
                        </blockquote>
                    ),
                    // 分隔線
                    hr: () => (
                        <hr className="my-4 border-gray-200 dark:border-gray-700" />
                    ),
                    // 連結
                    a: ({ href, children }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 dark:text-blue-400 hover:underline"
                        >
                            {children}
                        </a>
                    ),
                    // 表格
                    table: ({ children }) => (
                        <div className="overflow-x-auto my-2">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                {children}
                            </table>
                        </div>
                    ),
                    th: ({ children }) => (
                        <th className="px-3 py-2 bg-gray-100 dark:bg-gray-800 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {children}
                        </th>
                    ),
                    td: ({ children }) => (
                        <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                            {children}
                        </td>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
