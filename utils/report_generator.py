from typing import Dict, List, Optional
from datetime import datetime, timedelta
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
        3. 今日戰術建議 (整合交易計劃)
        4. 選擇權部位健檢
        """
        # 1. 收集數據
        try:
            positions = self.db.get_latest_positions()
        except Exception as e:
            return f"❌ 獲取庫存數據失敗: {str(e)}"
            
        # 1.2 昨日交易
        trades = self.db.get_trades()
        recent_trades = sorted(trades, key=lambda x: x['datetime'], reverse=True)[:10]
        
        # 1.3 損益數據
        pnl_by_symbol = self.db.get_pnl_by_symbol()
        
        # 1.4 現金
        cash = self.db.get_latest_cash_snapshot()
        
        # 1.5 交易計劃 (獲取所有待執行和進行中的計劃)
        trade_plans = self.db.get_trade_plans(status='pending')
        trade_plans += self.db.get_trade_plans(status='active')
        
        # 1.6 MFE/MAE 分析 (獲取最近的數據)
        mfe_mae_records = self.db.get_mfe_mae_records(limit=20)
        
        # 1.7 最近的交易日誌 (獲取過去 7 天的筆記)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        recent_notes = self.db.get_trade_notes(limit=10)
        
        # 2. 構建 Prompt
        context = {
            "positions": positions,
            "recent_trades": recent_trades,
            "pnl": pnl_by_symbol,
            "cash": cash,
            "trade_plans": trade_plans,
            "mfe_mae_records": mfe_mae_records[:10] if mfe_mae_records else [],
            "recent_notes": recent_notes[:5] if recent_notes else [],
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
   - 報告日期: {context['report_date']}
   - 已實現損益: $X (當日已平倉交易的實際盈虧)
   - 未實現損益: $X (目前持倉的帳面盈虧)
   - 總損益: $X

1. **昨日交易檢討 Action Review**
   - 針對 recent_trades 中的每一筆（或重點幾筆），分析其入場邏輯與執行品質。
   - 判斷是否為「好交易」(Good Action) 無論結果盈虧。
   - 如果有 MFE/MAE 數據，評估交易效率（是否過早出場或太晚止損）。

2. **庫存壓力測試 Portfolio Health**
   - 2a. **結構風險 (Ratio Risk)**: 
     - 分析各持倉的風險暴露 (Delta/Gamma)
     - 特別指出 Naked Short 或高風險部位
     - 用 emoji 標記風險等級：🚨嚴重警示 ⚠️需關注 ✅安全
   - 2b. **加減碼建議**: 
     - 根據當前持倉和市場狀態，給出具體建議
     - **加碼條件**: 列出觸發加碼的條件（價格、技術訊號）
     - **減碼/停損條件**: 列出觸發減碼或停損的條件
     - 使用 ATR 或百分比設定具體價位

3. **今日戰術建議 Tactical Plan**
   針對每個持倉標的，給出以下格式的建議：
   
   **[標的代號]** ([風險等級])
   - 指令: Buy/Sell/Hold/Close/Roll
   - 價格警示: $XX.XX
   - 理由: ...
   
   如果有待執行的交易計劃 (trade_plans)，特別標註並給出建議：
   - 計劃標的是否達到進場條件？
   - 計劃設定的停損價是否需要調整？

4. **選擇權部位健檢 Option Health**
   針對每個選擇權持倉：
   - **標的 + 到期日 + 履約價**
   - Gamma 風險評估
   - 價內/價外狀態 + 距離
   - 時間價值衰減影響
   - 建議: Hold/Roll/Close

5. **交易員心態檢視** (如果有最近的日誌筆記)
   - 根據最近的交易日誌，分析交易員的情緒狀態
   - 提醒可能的心理陷阱（貪婪、恐懼、報復性交易）

請確保數字準確，邏輯自洽。若數據不足以判斷，請誠實說明。
"""
        
        # 3. 呼叫 AI (使用 Thinking Model 進行深度分析)
        try:
            response = self.ai_coach.analyze(prompt)
            return response
        except Exception as e:
            return f"❌ AI 生成報告失敗: {str(e)}"
    
    async def generate_trade_plan_alert(self, plan_id: int) -> Optional[str]:
        """
        分析單一交易計劃，判斷是否需要行動
        
        Returns:
            如果需要行動，返回警報訊息；否則返回 None
        """
        plan = self.db.get_trade_plan(plan_id)
        if not plan:
            return None
        
        symbol = plan.get('symbol', '')
        
        # 獲取當前市價 (從最新持倉或需要額外 API call)
        positions = self.db.get_latest_positions()
        current_price = None
        for p in positions:
            if p.get('symbol', '').startswith(symbol):
                current_price = p.get('mark_price') or p.get('last_price')
                break
        
        if not current_price:
            return None  # 無法獲取價格，跳過
        
        # 檢查是否觸發條件
        entry_min = plan.get('entry_price_min')
        entry_max = plan.get('entry_price_max')
        stop_loss = plan.get('stop_loss_price')
        target = plan.get('target_price')
        direction = plan.get('direction', 'long')
        
        alerts = []
        
        # 進場條件檢查 (pending 狀態)
        if plan.get('status') == 'pending':
            if entry_min and entry_max:
                if entry_min <= current_price <= entry_max:
                    alerts.append(f"🎯 **進場訊號**: {symbol} 現價 ${current_price:.2f} 已進入計劃進場區間 (${entry_min} - ${entry_max})")
        
        # 停損/目標檢查 (active 狀態)
        if plan.get('status') in ['active', 'pending']:
            if direction == 'long':
                if stop_loss and current_price <= stop_loss:
                    alerts.append(f"🚨 **停損警報**: {symbol} 現價 ${current_price:.2f} 已跌破停損價 ${stop_loss:.2f}")
                if target and current_price >= target:
                    alerts.append(f"✅ **目標達成**: {symbol} 現價 ${current_price:.2f} 已達到目標價 ${target:.2f}")
            else:  # short
                if stop_loss and current_price >= stop_loss:
                    alerts.append(f"🚨 **停損警報**: {symbol} 現價 ${current_price:.2f} 已突破停損價 ${stop_loss:.2f}")
                if target and current_price <= target:
                    alerts.append(f"✅ **目標達成**: {symbol} 現價 ${current_price:.2f} 已達到目標價 ${target:.2f}")
        
        if alerts:
            return "\n".join(alerts)
        return None
    
    async def check_all_plan_alerts(self) -> List[str]:
        """
        檢查所有交易計劃的警報
        """
        alerts = []
        
        pending_plans = self.db.get_trade_plans(status='pending')
        active_plans = self.db.get_trade_plans(status='active')
        
        for plan in pending_plans + active_plans:
            alert = await self.generate_trade_plan_alert(plan['plan_id'])
            if alert:
                alerts.append(alert)
        
        return alerts
