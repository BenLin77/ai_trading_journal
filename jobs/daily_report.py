"""
每日報告排程任務

執行流程：
1. 呼叫 generate_daily_report_context() 取得數據
2. 將數據格式化為 Markdown 字串 (透過 AI)
3. 呼叫 file_service.save_report_to_markdown 存檔
4. 呼叫 telegram_service.send_message 發送
5. Gateway 模式：確保斷開 IB 連線
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# 重試設定
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_MINUTES = 30


def _create_minimal_report_context():
    """
    創建一個最小的報告上下文
    
    當 Gateway 和資料庫都無法取得數據時使用，
    確保用戶至少收到一個通知。
    """
    from services.report_data_service import ReportContext
    
    return ReportContext(
        report_date=datetime.now().strftime('%Y-%m-%d'),
        portfolio_summary=[],
        yesterday_trades=[],
        pnl_statistics={
            'unrealizedPnL': 0,
            'realizedPnL': 0,
            'totalPnL': 0,
            'netLiquidation': 0
        },
        data_source='FALLBACK'
    )


async def run_daily_report_job(
    db=None,
    ai_coach=None,
    force_send: bool = False,
    retry_count: int = 0
) -> dict:
    """
    執行每日報告任務
    
    Args:
        db: TradingDatabase 實例
        ai_coach: AICoach 實例
        force_send: 是否強制發送（忽略 telegram_enabled 設定）
        retry_count: 當前重試次數
        
    Returns:
        dict: 執行結果 {success, message, report_path, telegram_sent}
    """
    result = {
        'success': False,
        'message': '',
        'report_path': None,
        'telegram_sent': False,
        'file_saved': False
    }
    
    try:
        # 0. 檢查 Telegram 設定
        if not force_send:
            enabled = (db.get_setting('TELEGRAM_ENABLED') or db.get_setting('telegram_enabled')) if db else os.getenv('TELEGRAM_ENABLED', 'false')
            if enabled != 'true':
                result['message'] = 'Telegram 通知未啟用'
                logger.info(result['message'])
                return result
                
        token = (db.get_setting('TELEGRAM_BOT_TOKEN') or db.get_setting('telegram_bot_token')) if db else None
        if not token:
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            
        chat_id = (db.get_setting('TELEGRAM_CHAT_ID') or db.get_setting('telegram_chat_id')) if db else None
        if not chat_id:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # 1. 獲取數據來源設定
        data_source = os.getenv('DATA_SOURCE', 'QUERY').upper()
        logger.info(f"開始每日報告任務 (資料來源: {data_source})")
        
        # 2. 獲取報告上下文數據
        from services.report_data_service import ReportDataService
        
        data_service = ReportDataService(db=db)
        context = None
        
        try:
            context = await data_service.generate_daily_report_context()
            logger.info(f"數據獲取成功: {len(context.portfolio_summary)} 持倉, {len(context.yesterday_trades)} 交易")
        except ConnectionError as e:
            # Gateway 模式連線失敗：嘗試 Fallback 到資料庫
            if data_source == 'GATEWAY':
                logger.warning(f"IB Gateway 連線失敗: {e}")
                logger.info("嘗試 Fallback 到資料庫數據...")
                
                try:
                    # 強制使用 QUERY 模式從資料庫獲取數據
                    fallback_service = ReportDataService(db=db)
                    fallback_service._data_source = 'QUERY'  # 強制使用資料庫
                    context = await fallback_service.generate_daily_report_context()
                    logger.info(f"Fallback 成功: {len(context.portfolio_summary)} 持倉, {len(context.yesterday_trades)} 交易 (來自資料庫)")
                except Exception as fallback_error:
                    logger.error(f"Fallback 到資料庫也失敗: {fallback_error}")
                    # 如果資料庫也沒有數據，嘗試生成一個最小報告
                    context = _create_minimal_report_context()
                    logger.warning("使用最小報告上下文")
            else:
                raise
        except Exception as e:
            logger.error(f"數據獲取失敗: {e}")
            # 嘗試使用最小報告
            context = _create_minimal_report_context()
            logger.warning("使用最小報告上下文")
        
        # 3. 生成 AI 報告
        report_md = await _generate_ai_report(context, ai_coach, db)
        
        if not report_md:
            result['message'] = 'AI 報告生成失敗'
            return result
            
        logger.info("AI 報告生成完成")
        
        # 4. 存檔（獨立處理，不影響 Telegram 發送）
        try:
            from services.file_service import FileService
            
            file_service = FileService()
            report_path = file_service.save_report_to_markdown(
                content=report_md,
                date_str=context.report_date
            )
            result['report_path'] = str(report_path)
            result['file_saved'] = True
            logger.info(f"報告已存檔: {report_path}")
        except Exception as e:
            logger.error(f"存檔失敗 (繼續發送 Telegram): {e}")
            
        # 5. 發送 Telegram（獨立處理，不影響存檔）
        if token and chat_id:
            try:
                from utils.telegram_notifier import TelegramNotifier
                
                notifier = TelegramNotifier(token)
                success = notifier.send_message(chat_id, report_md)
                
                if success:
                    result['telegram_sent'] = True
                    logger.info("Telegram 發送成功")
                else:
                    logger.error("Telegram 發送失敗")
            except Exception as e:
                logger.error(f"Telegram 發送錯誤: {e}")
        else:
            logger.info("未設定 Telegram，跳過發送")
            
        # 6. 設定結果
        result['success'] = result['file_saved'] or result['telegram_sent']
        
        if result['telegram_sent'] and result['file_saved']:
            result['message'] = '報告已發送至 Telegram 並存檔'
        elif result['telegram_sent']:
            result['message'] = '報告已發送至 Telegram (存檔失敗)'
        elif result['file_saved']:
            result['message'] = '報告已存檔 (Telegram 發送失敗或未設定)'
        else:
            result['message'] = '報告生成完成但發送和存檔均失敗'
            
        return result
        
    except Exception as e:
        logger.error(f"每日報告任務執行失敗: {e}")
        result['message'] = f"任務執行失敗: {str(e)}"
        return result


async def _generate_ai_report(context, ai_coach, db=None) -> Optional[str]:
    """
    使用 AI 生成報告 Markdown
    
    Args:
        context: ReportContext 數據
        ai_coach: AICoach 實例
        db: TradingDatabase 實例 (用於獲取額外數據)
        
    Returns:
        str: Markdown 格式報告
    """
    import json
    
    # 檢查是否為 FALLBACK 模式（無數據可用）
    if context.data_source == 'FALLBACK':
        logger.warning("使用 FALLBACK 模式，生成簡化報告")
        return _generate_fallback_report(context)
    
    if not ai_coach:
        logger.error("AI Coach 未設定")
        # 如果 AI 不可用，生成一個基本報告
        return _generate_basic_report(context)
        
    # 構建 AI Prompt (使用用戶提供的專業 prompt)
    prompt = _build_trading_coach_prompt(context, db)
    
    try:
        # 使用 AI 生成報告
        report = ai_coach.analyze(prompt)
        return report
    except Exception as e:
        logger.error(f"AI 生成報告失敗: {e}")
        # AI 失敗時，生成基本報告
        return _generate_basic_report(context)


def _generate_fallback_report(context) -> str:
    """生成 FALLBACK 模式的簡化報告"""
    return f"""**每日倉位總結** - {context.report_date}

⚠️ **注意**: 今日報告數據取得失敗

**可能原因**:
- IB Gateway 未連線或已斷開
- 資料庫中無最新持倉數據
- 今日為非交易日（週末/假日）

**建議操作**:
1. 檢查 IB Gateway 連線狀態
2. 手動執行一次同步
3. 如果問題持續，請檢查系統日誌

---
*此訊息由系統自動發送*
"""


def _generate_basic_report(context) -> str:
    """生成基本報告（AI 不可用時）"""
    report_date = context.report_date
    portfolio = context.portfolio_summary
    trades = context.yesterday_trades
    pnl = context.pnl_statistics
    
    lines = [f"**每日倉位總結** - {report_date}", ""]
    
    # 損益摘要
    lines.append("**損益總覽**")
    lines.append(f"- 未實現損益: ${pnl.get('unrealizedPnL', 0):,.2f}")
    lines.append(f"- 已實現損益: ${pnl.get('realizedPnL', 0):,.2f}")
    lines.append(f"- 總損益: ${pnl.get('totalPnL', 0):,.2f}")
    lines.append("")
    
    # 持倉列表
    if portfolio:
        lines.append(f"**當前持倉** ({len(portfolio)} 筆)")
        for pos in portfolio[:10]:  # 限制顯示前 10 筆
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('quantity', 0)
            pnl_val = pos.get('unrealized_pnl', 0)
            lines.append(f"- {symbol}: {qty} @ ${pnl_val:+,.2f}")
        if len(portfolio) > 10:
            lines.append(f"- ... 及其他 {len(portfolio) - 10} 筆持倉")
    else:
        lines.append("**當前持倉**: 無")
    lines.append("")
    
    # 昨日交易
    if trades:
        lines.append(f"**昨日交易** ({len(trades)} 筆)")
        for trade in trades[:5]:
            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            qty = trade.get('quantity', 0)
            price = trade.get('price', 0)
            lines.append(f"- {symbol}: {side} {qty} @ ${price:.2f}")
        if len(trades) > 5:
            lines.append(f"- ... 及其他 {len(trades) - 5} 筆交易")
    else:
        lines.append("**昨日交易**: 無")
    
    lines.append("")
    lines.append("---")
    lines.append("*此報告為基本模式（AI 服務暫時不可用）*")
    
    return "\n".join(lines)


def _build_trading_coach_prompt(context, db=None) -> str:
    """
    構建交易教練 AI Prompt
    
    使用用戶指定的專業風控官 prompt，結合即時數據。
    """
    import json
    
    # 準備數據
    report_date = context.report_date
    portfolio_summary = context.portfolio_summary
    yesterday_trades = context.yesterday_trades
    pnl_stats = context.pnl_statistics
    
    # 按標的分組持倉
    from collections import defaultdict
    grouped_positions = defaultdict(list)
    
    for pos in portfolio_summary:
        underlying = pos.get('underlying', pos.get('symbol', ''))
        grouped_positions[underlying].append(pos)
        
    # 格式化持倉數據
    formatted_positions = []
    for underlying, positions in grouped_positions.items():
        stock_pos = [p for p in positions if p.get('asset_category') in ['STK', 'stock']]
        option_pos = [p for p in positions if p.get('asset_category') in ['OPT', 'option']]
        
        formatted_positions.append({
            'underlying': underlying,
            'stock': stock_pos[0] if stock_pos else None,
            'options': option_pos,
            'total_unrealized_pnl': sum(p.get('unrealized_pnl', 0) for p in positions)
        })
    
    # 構建上下文 JSON
    context_data = {
        'report_date': report_date,
        'portfolio_summary': formatted_positions,
        'yesterday_trades': yesterday_trades,
        'pnl_statistics': pnl_stats
    }
    
    # 專業風控官 Prompt
    system_prompt = """你是一位專門服務「左側交易 + 右側加碼」混合策略的避險基金風控官。此用戶的交易風格如下：

**用戶交易習慣（核心策略）：**
1. **左側交易建倉**：當價格下跌時，分兩批購買（不是一次 All-in）
2. **停損紀律**：當部位買夠後若繼續下跌，開始執行停損
3. **右側加碼**：若趨勢反轉上漲，找機會加碼
4. **乖離控管**：當價格乖離均線/VWAP 過大時，獲利了結
5. **選擇權保護**：常以 Covered Call / Protective Put 保護現股

**資料來源：**
1. report_date: 報告日期
2. portfolio_summary: 目前手上的部位 (已依照策略自動分組)
3. yesterday_trades: 昨天剛執行的買賣動作
4. pnl_statistics: 損益統計數據
   - unrealizedPnL: 未實現損益（帳面損益）
   - realizedPnL: 已實現損益（當日已平倉交易的實際損益）
   - totalPnL: 總損益

**關鍵定義：**
- 交易狀態 `(已平倉)`：代表該標的已完全出場，請計算實際損益
- 交易狀態 `(開倉)`：代表新建倉位或加碼
- 交易狀態 `(持倉中)`：代表部分平倉或減碼，但仍持有部位

**你的任務 (請依序輸出 Telegram Markdown 報告)：**

### 0. [每日損益總覽 Daily P&L]
**必須在報告最開頭顯示以下資訊：**
- **報告日期**: {report_date}
- **已實現損益**: ${realizedPnL} (當日已平倉交易的實際盈虧)
- **未實現損益**: ${unrealizedPnL} (目前持倉的帳面盈虧)
- **總損益**: ${totalPnL}

### 1. [昨日交易檢討 Action Review]
針對 yesterday_trades 中的每筆交易：
- **已平倉交易**：分析出場原因（停利/停損），計算實際損益
- **開倉交易**：這是首批買入還是第二批加碼？評估進場點位
- **持倉中交易**：減碼策略是否符合乖離控管原則？

### 2. [庫存壓力測試 Portfolio Health]
根據目前持倉進行風險檢視：

**2a. 結構風險 (Ratio Risk)**
- 檢查每檔現股與選擇權的對沖比率
- 標示「裸賣 (Naked Short)」風險部位
- 評估 Collar/Covered Call 的保護覆蓋率

**2b. 加減碼建議（基於技術面概念）**
請根據以下邏輯給出建議：
- **建議加碼條件**：
  - 價格站上 20MA 且部位尚未滿倉
  - 價格回測 VWAP 支撐且出現止跌訊號
  - 左側交易第一批已入場，可評估第二批時機
- **建議減碼/獲利了結條件**：
  - 價格高於 20MA 超過 2 個 ATR（乖離過大）
  - 未實現獲利達 15% 以上且動能減弱
  - 選擇權時間價值衰減至關鍵水位
- **建議停損條件**：
  - 已完成左側建倉但價格跌破關鍵支撐
  - 虧損達初始投入 8-10% 以上

### 3. [今日戰術建議 Tactical Plan]
- 針對目前觀察名單給出具體加碼/減碼價位
- 評估是否需要以選擇權保護現股
- 若有 Naked Short 風險，建議轉為 Spread 或平倉
- 提供具體操作指令（含價位與數量）

### 4. [選擇權部位健檢 Option Health]
- Short Call 是否有 Gamma 風險（接近履約價）
- Short Put 是否需要轉倉或平倉
- 評估整體組合的 Delta 暴露

**輸出格式要求：**
- 使用 Telegram 支援的 Markdown 格式：**粗體**、條列式
- 嚴禁使用 Emoji
- 數字務必精確引用 pnl_statistics 的數據
- 語氣專業、冷靜、數據導向"""
    
    # 組合完整 prompt
    full_prompt = f"""{system_prompt}

===== 數據 =====
{json.dumps(context_data, ensure_ascii=False, default=str, indent=2)}
"""
    
    return full_prompt
