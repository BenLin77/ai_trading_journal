"""
AI 策略顧問模組

此模組負責：
1. 分析回測結果並識別過擬合
2. 根據市場環境建議參數調整
3. 生成自然語言策略報告
"""

import os
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class AIStrategyAdvisor:
    """AI 策略顧問"""

    def __init__(self):
        """初始化 AI 策略顧問"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("未設定 GEMINI_API_KEY 環境變數")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def analyze_parameter_robustness(self, backtest_summary: Dict[str, Any]) -> str:
        """
        分析參數穩健性，識別過擬合

        Args:
            backtest_summary: 回測摘要統計

        Returns:
            AI 分析報告
        """
        overfitting_data = backtest_summary.get('overfitting_analysis', {})
        best_strategy = backtest_summary.get('best_strategy', {})

        prompt = f"""
你是一位資深量化交易分析師，專精於策略回測與過擬合偵測。

**回測摘要：**
- 總策略數：{backtest_summary.get('total_strategies', 0)}
- 變異係數：{overfitting_data.get('variance', 'N/A')}
- 是否過擬合：{overfitting_data.get('is_overfitted', False)}
- 穩定參數組合數：{len(overfitting_data.get('stable_params', []))}
- 不穩定參數組合數：{len(overfitting_data.get('unstable_params', []))}

**最佳策略：**
{best_strategy}

請根據以上數據，進行以下分析：

1. **參數穩健性評估**：這個策略是否有過擬合風險？
2. **參數高原分析**：穩定參數組合的範圍是否足夠廣？
3. **實戰建議**：如果要實盤交易，你會建議：
   - 使用哪個參數組合？
   - 需要注意哪些風險？
   - 如何設定停損與部位管理？

請用繁體中文回答，語氣專業但易懂。
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 分析失敗：{str(e)}"

    def suggest_parameter_adjustment(
        self,
        current_params: Dict[str, Any],
        market_regime: str = "neutral",
        performance_gap: Optional[float] = None
    ) -> str:
        """
        根據市場環境建議參數調整

        Args:
            current_params: 當前參數
            market_regime: 市場環境 (bull, bear, neutral, volatile)
            performance_gap: 回測 vs 實際績效差距 (%)

        Returns:
            參數調整建議
        """
        prompt = f"""
你是一位量化交易策略優化專家。

**當前策略參數：**
{current_params}

**市場環境：**{market_regime}

**績效偏差：**
{f"回測預期 vs 實際表現差距：{performance_gap:.2f}%" if performance_gap else "尚無實盤數據"}

請針對以下情境提供建議：

1. **參數調整建議**：
   - 在 {market_regime} 市場環境下，哪些參數需要調整？
   - 建議調整為多少？為什麼？

2. **市場適應性**：
   - 這組參數在不同市場環境下的適用性如何？
   - 何時應該暫停交易？

3. **風險控制**：
   - 建議的最大部位大小
   - 單筆交易風險上限
   - 連續虧損後的處理方式

請用繁體中文回答，提供具體可執行的建議。
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 建議生成失敗：{str(e)}"

    def generate_strategy_report(
        self,
        strategy_name: str,
        backtest_metrics: Dict[str, Any],
        actual_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成完整的策略分析報告

        Args:
            strategy_name: 策略名稱
            backtest_metrics: 回測績效指標
            actual_metrics: 實際交易績效指標（可選）

        Returns:
            自然語言策略報告
        """
        prompt = f"""
你是一位專業的量化交易報告撰寫員，請為以下策略生成一份詳細的分析報告。

**策略名稱：**{strategy_name}

**回測績效指標：**
- Sharpe Ratio: {backtest_metrics.get('sharpe_ratio', 'N/A')}
- Sortino Ratio: {backtest_metrics.get('sortino_ratio', 'N/A')}
- 最大回撤: {backtest_metrics.get('max_drawdown', 'N/A')}%
- 勝率: {backtest_metrics.get('win_rate', 'N/A')}%
- 獲利因子: {backtest_metrics.get('profit_factor', 'N/A')}
- 總交易次數: {backtest_metrics.get('total_trades', 'N/A')}
- 年化報酬率: {backtest_metrics.get('annual_return', 'N/A')}%

{f'''
**實際交易績效：**
- Sharpe Ratio: {actual_metrics.get('sharpe_ratio', 'N/A')}
- 勝率: {actual_metrics.get('win_rate', 'N/A')}%
- 實際年化報酬: {actual_metrics.get('annual_return', 'N/A')}%
''' if actual_metrics else "（尚無實盤數據）"}

請生成包含以下章節的報告：

## 1. 執行摘要
簡述策略表現與核心發現（3-5 句話）

## 2. 績效分析
- 風險調整後報酬表現如何？
- 與 Buy & Hold 策略比較
- 最大回撤是否在可接受範圍內？

## 3. 交易特性
- 交易頻率是否合理？
- 勝率與獲利因子的搭配是否健康？

## 4. 風險評估
- 主要風險點在哪裡？
- 哪些市場環境下可能失效？

{f'''
## 5. 回測 vs 實盤比較
- 實盤表現是否符合預期？
- 偏差的可能原因？
- 是否需要調整策略？
''' if actual_metrics else ""}

## 6. 實戰建議
- 是否建議實盤交易？
- 建議的資金配置比例
- 需要監控的關鍵指標

請用繁體中文撰寫，語氣專業但平易近人。
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"報告生成失敗：{str(e)}"

    def compare_strategies(self, strategies: List[Dict[str, Any]]) -> str:
        """
        比較多個策略並提供選擇建議

        Args:
            strategies: 策略列表，每個策略包含名稱和績效指標

        Returns:
            策略比較分析
        """
        strategies_text = "\n\n".join([
            f"**策略 {i+1}: {s.get('name', 'Unknown')}**\n"
            f"- Sharpe: {s.get('sharpe_ratio', 'N/A')}\n"
            f"- 最大回撤: {s.get('max_drawdown', 'N/A')}%\n"
            f"- 勝率: {s.get('win_rate', 'N/A')}%\n"
            f"- 年化報酬: {s.get('annual_return', 'N/A')}%"
            for i, s in enumerate(strategies)
        ])

        prompt = f"""
你是一位資深量化交易顧問，客戶請你比較以下幾個策略並提供選擇建議。

{strategies_text}

請提供：

1. **綜合比較**：
   - 哪個策略的風險調整後報酬最佳？
   - 哪個策略的回撤控制最好？
   - 哪個策略的穩定性最高？

2. **適用情境**：
   - 保守型投資者適合哪個？
   - 積極型投資者適合哪個？
   - 不同市場環境下的首選？

3. **組合建議**：
   - 是否建議多策略組合？
   - 如何分配資金比例？

4. **最終建議**：
   給出明確的策略選擇建議與理由。

請用繁體中文回答，提供具體可執行的建議。
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"策略比較失敗：{str(e)}"

    def analyze_performance_degradation(
        self,
        backtest_sharpe: float,
        actual_sharpe: float,
        time_period: str
    ) -> str:
        """
        分析策略績效衰退原因

        Args:
            backtest_sharpe: 回測 Sharpe Ratio
            actual_sharpe: 實際 Sharpe Ratio
            time_period: 實盤交易時間區間

        Returns:
            績效衰退分析
        """
        degradation_pct = ((actual_sharpe - backtest_sharpe) / backtest_sharpe) * 100

        prompt = f"""
你是一位量化交易診斷專家。某個策略在實盤交易中出現績效衰退。

**數據：**
- 回測 Sharpe Ratio: {backtest_sharpe:.2f}
- 實盤 Sharpe Ratio: {actual_sharpe:.2f}
- 績效衰退: {degradation_pct:.2f}%
- 實盤期間: {time_period}

請分析：

1. **衰退程度評估**：
   - 這個衰退幅度是否在正常範圍內？
   - 何時應該認定策略已經失效？

2. **可能原因**：
   - 過擬合（回測參數調過頭）
   - 市場環境變化（趨勢 → 震盪）
   - 執行成本（滑點、手續費被低估）
   - 樣本外數據不足
   - 其他因素

3. **診斷建議**：
   - 需要檢查哪些數據？
   - 如何判斷真正的原因？

4. **應對措施**：
   - 立即停止交易？
   - 調整參數？
   - 縮小部位？
   - 其他建議？

請用繁體中文回答，提供專業且可執行的建議。
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"衰退分析失敗：{str(e)}"
