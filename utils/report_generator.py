from typing import Dict, List, Optional
from datetime import datetime
import json
from .ai_coach import AICoach
from database import TradingDatabase
from .ibkr_flex_query import IBKRFlexQuery

class ReportGenerator:
    """每日 AI 戰情報告生成器"""
    
    def __init__(self, db: TradingDatabase, ai_coach: AICoach):
        self.db = db
        self.ai_coach = ai_coach
        
    async def generate_daily_report(self) -> str:
        """
        生成每日戰情報告 Markdown
        
        內容包括：
        0. 每日損益總覽
        1. 昨日交易檢討
        2. 庫存壓力測試
        3. 今日戰術建議
        4. 選擇權部位健檢
        """
        # 1. 收集數據
        # 1.1 庫存數據（強制從 IBKR 計算部分缺失數據，如 VIX）
        try:
            # 這裡簡單使用 db.get_latest_positions()，因為我們假設後端會定期 sync
            # 或者我們可以這裡觸發一次 sync (但可能會慢)
            # 為了效率，讀取快照
            positions = self.db.get_latest_positions()
            
            # 確保包含 VIX 等可能隱藏的持倉 (使用後端 main.py 裡的邏輯複用或重寫)
            # 這裡為了簡單，假設 sync 已經把 VIX 補進去 db 了 (如果是透過 main.py 的 API 觸發的話)
            # 但如果是 pure db read，可能沒有 "calculated" VIX。
            # 理想情況：排程器在跑報告前，先跑一次 sync_ibkr。
        except Exception as e:
            return f"❌ 獲取庫存數據失敗: {str(e)}"
            
        # 1.2 昨日交易
        trades = self.db.get_trades()
        # 篩選昨日交易 (這裡為了演示，如果不嚴格篩選昨日，可以取最近 N 筆)
        recent_trades = sorted(trades, key=lambda x: x['datetime'], reverse=True)[:10]
        
        # 1.3 損益數據
        pnl_by_symbol = self.db.get_pnl_by_symbol()
        
        # 1.4 現金
        cash = self.db.get_latest_cash_snapshot()
        
        # 2. 構建 Prompt
        context = {
            "positions": positions,
            "recent_trades": recent_trades,
            "pnl": pnl_by_symbol,
            "cash": cash,
            "report_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        prompt = f"""
你是一位專業的對沖基金交易教練。請根據以下數據，為我撰寫一份「每日戰情報告」。
目標受眾：專業交易員。
風格：直接、犀利、數據驅動 (No yapping)、風險意識強烈。
格式要求：請使用 Telegram 友好的 Markdown 格式 (避免使用複雜的 table)。

數據：
{json.dumps(context, ensure_ascii=False, default=str)}

請嚴格按照以下結構輸出（標題須一致）：

0. **每日損益總覽 Daily P&L**
   - 報告日期
   - 總結今日/近期損益表現 (基於 realized pnl)。

1. **昨日交易檢討 Action Review**
   - 針對 recent_trades 中的每一筆（或重點幾筆），分析其入場邏輯與執行品質。
   - 判斷是否為「好交易」(Good Action) 無論結果盈虧。

2. **庫存壓力測試 Portfolio Health**
   - 2a. **結構風險 (Ratio Risk)**: 分析各持倉的風險暴露 (Delta/Gamma)，特別指出 Naked Short 或高風險部位。
   - 2b. **加減碼建議**: 根據當前持倉，給出具體的加碼或減碼觸發條件 (例如 VWAP 水位)。

3. **今日戰術建議 Tactical Plan**
   - 針對每個核心持倉，給出今天的操作指令 (Buy, Sell, Hold, Close, Roll)。
   - 設定具體的觀察價位。

4. **選擇權部位健檢 Option Health**
   - 特別針對選擇權持倉 (Short Call/Put)，分析其價內外狀態 (ITM/OTM) 與風險。
   - 給出 Roll over 或止損建議。
   - 再次確認「VIX」部位的狀態（如果有）。

請確保數字準確，邏輯自洽。若數據不足以判斷，請誠實說明。
"""
        
        # 3. 呼叫 AI
        try:
            response = self.ai_coach.chat(prompt)
            return response
        except Exception as e:
            return f"❌ AI 生成報告失敗: {str(e)}"
