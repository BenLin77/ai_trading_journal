'use client';

import { useState, useRef, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';
import { MessageCircle, X, Send, Loader2, Sparkles } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

// 簡易 Markdown 解析器
function parseMarkdown(text: string): React.ReactNode {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  let listType: 'ul' | 'ol' | null = null;
  
  const flushList = () => {
    if (listItems.length > 0 && listType) {
      const ListTag = listType;
      elements.push(
        <ListTag key={elements.length} className={listType === 'ul' ? 'list-disc pl-5 my-2' : 'list-decimal pl-5 my-2'}>
          {listItems.map((item, i) => (
            <li key={i} className="my-0.5">{parseInline(item)}</li>
          ))}
        </ListTag>
      );
      listItems = [];
      listType = null;
    }
  };
  
  const parseInline = (line: string): React.ReactNode => {
    // 處理粗體 **text** 和 __text__
    const parts: React.ReactNode[] = [];
    let remaining = line;
    let key = 0;
    
    while (remaining.length > 0) {
      const boldMatch = remaining.match(/\*\*(.+?)\*\*|__(.+?)__/);
      if (boldMatch && boldMatch.index !== undefined) {
        if (boldMatch.index > 0) {
          parts.push(<span key={key++}>{remaining.slice(0, boldMatch.index)}</span>);
        }
        parts.push(
          <strong key={key++} className="font-bold text-blue-600 dark:text-blue-400">
            {boldMatch[1] || boldMatch[2]}
          </strong>
        );
        remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      } else {
        parts.push(<span key={key++}>{remaining}</span>);
        break;
      }
    }
    
    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // 標題
    if (line.startsWith('### ')) {
      flushList();
      elements.push(<h5 key={elements.length} className="text-sm font-bold mt-3 mb-1">{parseInline(line.slice(4))}</h5>);
    } else if (line.startsWith('## ')) {
      flushList();
      elements.push(<h4 key={elements.length} className="text-base font-bold mt-3 mb-2">{parseInline(line.slice(3))}</h4>);
    } else if (line.startsWith('# ')) {
      flushList();
      elements.push(<h3 key={elements.length} className="text-lg font-bold mt-3 mb-2">{parseInline(line.slice(2))}</h3>);
    }
    // 無序列表
    else if (line.match(/^[-*]\s+/)) {
      if (listType !== 'ul') {
        flushList();
        listType = 'ul';
      }
      listItems.push(line.replace(/^[-*]\s+/, ''));
    }
    // 有序列表
    else if (line.match(/^\d+\.\s+/)) {
      if (listType !== 'ol') {
        flushList();
        listType = 'ol';
      }
      listItems.push(line.replace(/^\d+\.\s+/, ''));
    }
    // 分隔線
    else if (line.match(/^---+$/)) {
      flushList();
      elements.push(<hr key={elements.length} className="my-3 border-gray-300 dark:border-gray-600" />);
    }
    // 空行
    else if (line.trim() === '') {
      flushList();
    }
    // 一般段落
    else {
      flushList();
      elements.push(<p key={elements.length} className="my-2">{parseInline(line)}</p>);
    }
  }
  
  flushList();
  return <>{elements}</>;
}

// 範例問題
const EXAMPLE_QUESTIONS = {
  zh: [
    { icon: '📊', text: '分析我的持倉風險' },
    { icon: '📈', text: '我的勝率如何提升？' },
    { icon: '💡', text: '給我一些交易建議' },
    { icon: '🎯', text: '哪些標的表現最好？' },
  ],
  en: [
    { icon: '📊', text: 'Analyze my portfolio risk' },
    { icon: '📈', text: 'How to improve my win rate?' },
    { icon: '💡', text: 'Give me trading suggestions' },
    { icon: '🎯', text: 'Which stocks perform best?' },
  ],
};

export function AIChat() {
  const { language, chatOpen, setChatOpen, chatMessages, addChatMessage } = useAppStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const chatMutation = useMutation({
    mutationFn: (message: string) => apiClient.aiChat(message),
    onSuccess: (data) => {
      addChatMessage({ role: 'assistant', content: data.response });
    },
    onError: (error: Error) => {
      addChatMessage({ 
        role: 'assistant', 
        content: language === 'zh' 
          ? `抱歉，發生錯誤：${error.message}` 
          : `Sorry, an error occurred: ${error.message}` 
      });
    },
  });

  const handleSend = (message?: string) => {
    const msg = message || input.trim();
    if (!msg || chatMutation.isPending) return;

    addChatMessage({ role: 'user', content: msg });
    chatMutation.mutate(msg);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    if (chatOpen) {
      inputRef.current?.focus();
    }
  }, [chatOpen]);

  const examples = EXAMPLE_QUESTIONS[language as keyof typeof EXAMPLE_QUESTIONS] || EXAMPLE_QUESTIONS.en;

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className={cn(
          'fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all',
          chatOpen
            ? 'bg-gray-600 hover:bg-gray-700'
            : 'bg-blue-600 hover:bg-blue-700'
        )}
      >
        {chatOpen ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          <MessageCircle className="h-6 w-6 text-white" />
        )}
      </button>

      {/* Chat Panel - 更大的視窗 */}
      <div
        className={cn(
          'fixed z-50 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-2xl transition-all duration-300 flex flex-col',
          // 桌面版：右下角，寬度 600px，高度 70vh
          'bottom-24 right-6 w-[600px] h-[70vh] max-h-[800px]',
          // 手機版：全螢幕
          'max-sm:inset-4 max-sm:bottom-20 max-sm:w-auto max-sm:h-auto',
          chatOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3 shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-500" />
            <h3 className="font-semibold">{t('ai_chat_title', language)}</h3>
          </div>
          <button
            onClick={() => setChatOpen(false)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatMessages.length === 0 ? (
            // 沒有對話時顯示範例問題
            <div className="h-full flex flex-col items-center justify-center">
              <div className="text-center mb-6">
                <Sparkles className="h-12 w-12 text-blue-500 mx-auto mb-3" />
                <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                  {language === 'zh' ? 'AI 交易助手' : 'AI Trading Assistant'}
                </h4>
                <p className="text-gray-500 text-sm mt-1">
                  {language === 'zh' 
                    ? '我可以分析你的持倉、提供交易建議' 
                    : 'I can analyze your portfolio and provide trading advice'}
                </p>
              </div>
              
              <div className="w-full max-w-md space-y-2">
                <p className="text-xs text-gray-400 text-center mb-3">
                  {language === 'zh' ? '試試這些問題：' : 'Try these questions:'}
                </p>
                {examples.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q.text)}
                    disabled={chatMutation.isPending}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
                  >
                    <span className="text-xl">{q.icon}</span>
                    <span className="text-sm text-gray-700 dark:text-gray-300">{q.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // 有對話時顯示訊息
            chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex',
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                <div
                  className={cn(
                    'max-w-[85%] rounded-lg px-4 py-3',
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                  )}
                >
                  {msg.role === 'assistant' ? (
                    // AI 回應使用 Markdown 解析
                    <div className="text-sm leading-relaxed">
                      {parseMarkdown(msg.content)}
                    </div>
                  ) : (
                    // 用戶訊息直接顯示
                    <span className="text-sm">{msg.content}</span>
                  )}
                </div>
              </div>
            ))
          )}
          {chatMutation.isPending && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                <span className="text-sm text-gray-500">
                  {language === 'zh' ? '思考中...' : 'Thinking...'}
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 shrink-0">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('ai_chat_placeholder', language)}
              rows={1}
              className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none max-h-32"
              disabled={chatMutation.isPending}
              style={{ minHeight: '42px' }}
            />
            <Button
              size="icon"
              onClick={() => handleSend()}
              disabled={!input.trim() || chatMutation.isPending}
              className="h-[42px] w-[42px]"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
