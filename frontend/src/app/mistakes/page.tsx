'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, MistakeCard } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn, formatDate } from '@/lib/utils';
import { Loader2, Plus, AlertTriangle, BookOpen, Brain, Heart, X } from 'lucide-react';

const ERROR_TYPES = [
  { value: 'fomo', label: { zh: 'FOMO 追高', en: 'FOMO Chasing' }, icon: '🏃', color: 'bg-red-100 dark:bg-red-900/30' },
  { value: 'no_stop_loss', label: { zh: '未設停損', en: 'No Stop Loss' }, icon: '🛑', color: 'bg-orange-100 dark:bg-orange-900/30' },
  { value: 'overtrading', label: { zh: '過度交易', en: 'Overtrading' }, icon: '📈', color: 'bg-yellow-100 dark:bg-yellow-900/30' },
  { value: 'revenge_trading', label: { zh: '報復性交易', en: 'Revenge Trading' }, icon: '😤', color: 'bg-purple-100 dark:bg-purple-900/30' },
  { value: 'position_sizing', label: { zh: '部位過大', en: 'Position Too Large' }, icon: '📊', color: 'bg-blue-100 dark:bg-blue-900/30' },
  { value: 'early_exit', label: { zh: '過早出場', en: 'Early Exit' }, icon: '🚪', color: 'bg-cyan-100 dark:bg-cyan-900/30' },
  { value: 'other', label: { zh: '其他', en: 'Other' }, icon: '❓', color: 'bg-gray-100 dark:bg-gray-800' },
];

const EMOTIONAL_STATES = [
  { value: 'fear', label: { zh: '恐懼', en: 'Fear' }, emoji: '😰' },
  { value: 'greed', label: { zh: '貪婪', en: 'Greed' }, emoji: '🤑' },
  { value: 'anxiety', label: { zh: '焦慮', en: 'Anxiety' }, emoji: '😟' },
  { value: 'overconfident', label: { zh: '過度自信', en: 'Overconfident' }, emoji: '😎' },
  { value: 'frustrated', label: { zh: '沮喪', en: 'Frustrated' }, emoji: '😤' },
  { value: 'neutral', label: { zh: '平靜', en: 'Neutral' }, emoji: '😐' },
];

export default function MistakesPage() {
  const { language } = useAppStore();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [symbol, setSymbol] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [errorType, setErrorType] = useState('fomo');
  const [description, setDescription] = useState('');
  const [lesson, setLesson] = useState('');
  const [emotionalState, setEmotionalState] = useState('neutral');

  const { data: cards, isLoading } = useQuery({
    queryKey: ['mistake-cards'],
    queryFn: apiClient.getMistakeCards,
  });

  const addMutation = useMutation({
    mutationFn: (card: Omit<MistakeCard, 'id'>) => apiClient.addMistakeCard(card),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mistake-cards'] });
      setShowForm(false);
      resetForm();
    },
  });

  const resetForm = () => {
    setSymbol('');
    setDate(new Date().toISOString().split('T')[0]);
    setErrorType('fomo');
    setDescription('');
    setLesson('');
    setEmotionalState('neutral');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !description || !lesson) return;

    addMutation.mutate({
      symbol,
      date,
      error_type: errorType,
      description,
      lesson,
      emotional_state: emotionalState,
    });
  };

  const getErrorTypeInfo = (type: string) => ERROR_TYPES.find(e => e.value === type) || ERROR_TYPES[ERROR_TYPES.length - 1];
  const getEmotionalInfo = (state: string) => EMOTIONAL_STATES.find(e => e.value === state) || EMOTIONAL_STATES[EMOTIONAL_STATES.length - 1];

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{language === 'zh' ? '🎴 錯誤卡片' : '🎴 Mistake Cards'}</h1>
          <p className="text-gray-500 mt-1">
            {language === 'zh' ? '記錄交易錯誤，從失敗中學習成長' : 'Record trading mistakes and learn from failures'}
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? <X className="h-4 w-4 mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
          {showForm ? (language === 'zh' ? '取消' : 'Cancel') : (language === 'zh' ? '新增錯誤卡片' : 'Add Mistake Card')}
        </Button>
      </div>

      {/* 新增表單 */}
      {showForm && (
        <Card className="border-2 border-blue-200 dark:border-blue-800">
          <CardHeader>
            <CardTitle>{language === 'zh' ? '📝 記錄新的交易錯誤' : '📝 Record New Trading Mistake'}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                    {language === 'zh' ? '標的代號' : 'Symbol'}
                  </label>
                  <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder="AAPL"
                    required
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                    {language === 'zh' ? '日期' : 'Date'}
                  </label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '錯誤類型' : 'Error Type'}
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {ERROR_TYPES.map((et) => (
                    <button
                      key={et.value}
                      type="button"
                      onClick={() => setErrorType(et.value)}
                      className={cn(
                        'px-3 py-2 rounded-lg text-sm transition-colors',
                        errorType === et.value
                          ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30'
                          : et.color
                      )}
                    >
                      {et.icon} {et.label[language]}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '當時的情緒狀態' : 'Emotional State'}
                </label>
                <div className="flex flex-wrap gap-2">
                  {EMOTIONAL_STATES.map((es) => (
                    <button
                      key={es.value}
                      type="button"
                      onClick={() => setEmotionalState(es.value)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-sm transition-colors',
                        emotionalState === es.value
                          ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30'
                          : 'bg-gray-100 dark:bg-gray-800'
                      )}
                    >
                      {es.emoji} {es.label[language]}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  <AlertTriangle className="h-4 w-4 inline mr-1" />
                  {language === 'zh' ? '發生了什麼？' : 'What happened?'}
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={language === 'zh' ? '描述這次錯誤的經過...' : 'Describe what went wrong...'}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 min-h-[80px]"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  <BookOpen className="h-4 w-4 inline mr-1" />
                  {language === 'zh' ? '學到的教訓' : 'Lesson Learned'}
                </label>
                <textarea
                  value={lesson}
                  onChange={(e) => setLesson(e.target.value)}
                  placeholder={language === 'zh' ? '下次應該怎麼做？' : 'What should I do next time?'}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 min-h-[80px]"
                />
              </div>

              <Button type="submit" disabled={addMutation.isPending} className="w-full">
                {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {language === 'zh' ? '儲存錯誤卡片' : 'Save Mistake Card'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* 錯誤卡片列表 */}
      {cards && cards.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cards.map((card) => {
            const errorInfo = getErrorTypeInfo(card.error_type);
            const emotionInfo = getEmotionalInfo(card.emotional_state || 'neutral');

            return (
              <Card key={card.id} className={cn('overflow-hidden', errorInfo.color)}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{errorInfo.icon}</span>
                      <div>
                        <p className="font-bold">{card.symbol}</p>
                        <p className="text-xs text-gray-500">{formatDate(card.date)}</p>
                      </div>
                    </div>
                    <span className="text-xl">{emotionInfo.emoji}</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="inline-block px-2 py-0.5 bg-white/50 dark:bg-black/20 rounded text-xs">
                    {errorInfo.label[language]}
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {language === 'zh' ? '發生的事' : 'What happened'}
                    </p>
                    <p className="text-sm">{card.description}</p>
                  </div>

                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                      <BookOpen className="h-3 w-3" />
                      {language === 'zh' ? '教訓' : 'Lesson'}
                    </p>
                    <p className="text-sm font-medium text-blue-600 dark:text-blue-400">{card.lesson}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Brain className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                {language === 'zh' ? '還沒有錯誤記錄' : 'No mistakes recorded yet'}
              </h3>
              <p className="text-gray-500 text-sm mb-4">
                {language === 'zh'
                  ? '記錄交易錯誤是成長的第一步'
                  : 'Recording trading mistakes is the first step to growth'}
              </p>
              <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                {language === 'zh' ? '記錄第一個錯誤' : 'Record First Mistake'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 統計摘要 */}
      {cards && cards.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{language === 'zh' ? '📊 錯誤類型統計' : '📊 Error Type Statistics'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {ERROR_TYPES.filter(et => et.value !== 'other').map((et) => {
                const count = cards.filter(c => c.error_type === et.value).length;
                return (
                  <div key={et.value} className={cn('p-3 rounded-lg text-center', et.color)}>
                    <span className="text-2xl">{et.icon}</span>
                    <p className="text-sm mt-1">{et.label[language]}</p>
                    <p className="text-xl font-bold">{count}</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
