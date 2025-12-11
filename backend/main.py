"""
AI Trading Journal - FastAPI Backend

提供 REST API 給 React 前端使用
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import os
import sys

# 加入父目錄到 path 以便匯入現有模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import TradingDatabase
from utils.pnl_calculator import PnLCalculator
from utils.ai_coach import AICoach
from utils.ibkr_flex_query import IBKRFlexQuery
from utils.option_strategy_detector import OptionStrategyDetector
from utils.derivatives_support import InstrumentParser

from dotenv import load_dotenv
# 載入父目錄的 .env 檔案
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

app = FastAPI(
    title="AI Trading Journal API",
    description="交易日誌系統 API",
    version="2.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料庫實例 - 使用父目錄的資料庫
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = TradingDatabase(os.path.join(parent_dir, 'trading_journal.db'))

# AI 教練實例
try:
    ai_coach = AICoach()
except Exception:
    ai_coach = None


# ========== Pydantic Models ==========

class TradeResponse(BaseModel):
    id: int
    symbol: str
    datetime: str
    action: str
    quantity: float
    price: float
    commission: float
    realized_pnl: float
    notes: Optional[str] = None


class StatisticsResponse(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    best_trade: float
    worst_trade: float


class OptionLegResponse(BaseModel):
    symbol: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiry: str
    quantity: int
    action: str  # 'buy' or 'sell'


class PositionResponse(BaseModel):
    symbol: str
    underlying: str
    quantity: float
    avg_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    realized_pnl: float
    strategy: Optional[str] = None
    strategy_description: Optional[str] = None
    options: List[OptionLegResponse] = []
    # Greek 風險指標
    risk_level: Optional[str] = None  # "低", "中", "高"
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None


class PortfolioOverviewResponse(BaseModel):
    positions: List[PositionResponse]
    total_market_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    cash_balance: float


class CashBalanceResponse(BaseModel):
    total_cash: float
    currency: str
    ending_cash: float
    ending_settled_cash: float


class AIAnalysisRequest(BaseModel):
    symbol: Optional[str] = None
    message: str
    session_id: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    response: str
    session_id: str


class SyncResponse(BaseModel):
    success: bool
    trades_synced: int
    positions_synced: int
    message: str


class SettingsResponse(BaseModel):
    language: str
    theme: str
    ibkr_configured: bool
    ai_configured: bool


# ========== API Endpoints ==========

@app.get("/")
async def root():
    return {"message": "AI Trading Journal API", "version": "2.0.0"}


@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "database": "connected",
        "ai": "available" if ai_coach else "unavailable",
        "ibkr": "configured" if os.getenv("IBKR_FLEX_TOKEN") else "not_configured"
    }


# ========== 交易相關 ==========

@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trades(
    symbol: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
):
    """取得交易記錄"""
    trades = db.get_trades()
    
    # 過濾
    if symbol:
        trades = [t for t in trades if t['symbol'] == symbol]
    
    if start_date:
        trades = [t for t in trades if datetime.fromisoformat(t['datetime']).date() >= start_date]
    
    if end_date:
        trades = [t for t in trades if datetime.fromisoformat(t['datetime']).date() <= end_date]
    
    # 排序（最新的在前）
    trades = sorted(trades, key=lambda x: x['datetime'], reverse=True)[:limit]
    
    return [TradeResponse(**t) for t in trades]


@app.get("/api/trades/symbols")
async def get_symbols():
    """取得所有交易過的標的"""
    symbols = db.get_all_symbols()
    return {"symbols": symbols}


@app.get("/api/trades/pnl-by-symbol")
async def get_pnl_by_symbol():
    """取得各標的盈虧"""
    pnl = db.get_pnl_by_symbol()
    return {"pnl_by_symbol": pnl}


# ========== 統計相關 ==========

@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """取得交易統計"""
    stats = db.get_trade_statistics()
    # 確保所有欄位都有預設值
    return StatisticsResponse(
        total_trades=stats.get('total_trades', 0),
        total_pnl=stats.get('total_pnl', 0),
        win_rate=stats.get('win_rate', 0),
        avg_win=stats.get('avg_win', 0),
        avg_loss=stats.get('avg_loss', 0),
        profit_factor=stats.get('profit_factor', 0),
        best_trade=stats.get('best_trade', 0),
        worst_trade=stats.get('worst_trade', 0),
    )


@app.get("/api/equity-curve")
async def get_equity_curve():
    """取得資金曲線數據"""
    trades = db.get_trades()
    if not trades:
        return {"data": []}
    
    # 按時間排序並計算累計盈虧
    sorted_trades = sorted(trades, key=lambda x: x['datetime'])
    cumulative = 0
    curve_data = []
    
    for t in sorted_trades:
        cumulative += t.get('realized_pnl', 0)
        curve_data.append({
            "datetime": t['datetime'],
            "cumulative_pnl": cumulative,
            "symbol": t['symbol']
        })
    
    return {"data": curve_data}


# ========== 持倉相關 ==========

@app.get("/api/portfolio", response_model=PortfolioOverviewResponse)
async def get_portfolio():
    """取得持倉總覽（基於 IBKR 持倉快照或交易記錄）"""
    
    # 先嘗試從資料庫取得最新持倉快照
    positions_raw = db.get_latest_positions()
    
    # 如果沒有持倉快照，使用 IBKR 實際數據（臨時方案）
    if not positions_raw:
        # 2024-12-11 IBKR 實際持倉截圖
        positions_raw = [
            {'symbol': 'SMCI', 'position': 410, 'mark_price': 33.19, 'average_cost': 41.38, 
             'unrealized_pnl': -3357.11, 'asset_category': 'STK'},
            {'symbol': 'SMR', 'position': 780, 'mark_price': 19.68, 'average_cost': 19.27, 
             'unrealized_pnl': 320.99, 'asset_category': 'STK'},
            {'symbol': 'NVTS', 'position': 80, 'mark_price': 8.83, 'average_cost': 8.00, 
             'unrealized_pnl': 66.20, 'asset_category': 'STK'},
            {'symbol': 'ONDS', 'position': 2550, 'mark_price': 8.54, 'average_cost': 7.18, 
             'unrealized_pnl': 3491.65, 'asset_category': 'STK'},
            {'symbol': 'SMR 250116C22', 'position': -2, 'mark_price': 1.47, 'average_cost': 1.26, 
             'unrealized_pnl': -37.66, 'asset_category': 'OPT', 'put_call': 'C', 'strike': 22.0, 
             'expiry': '2026-01-16'},
        ]
    
    # 使用 OptionStrategyDetector 分析策略
    import pandas as pd
    positions_df = pd.DataFrame(positions_raw)
    
    # 按 underlying 分組持倉
    parser = InstrumentParser()
    grouped_positions = {}
    
    for pos in positions_raw:
        symbol = pos.get('symbol', '')
        parsed = parser.parse_symbol(symbol)
        underlying = parsed['underlying']
        
        if underlying not in grouped_positions:
            grouped_positions[underlying] = {
                'stock_quantity': 0,
                'stock_cost': 0,
                'stock_price': 0,
                'stock_value': 0,
                'stock_unrealized': 0,
                'options': [],
                'realized_pnl': 0
            }
        
        asset_cat = pos.get('asset_category', 'STK')
        quantity = pos.get('position', 0)
        mark_price = pos.get('mark_price', 0)
        avg_cost = pos.get('average_cost', 0)
        unrealized = pos.get('unrealized_pnl', 0)
        
        if asset_cat == 'STK':
            grouped_positions[underlying]['stock_quantity'] = quantity
            grouped_positions[underlying]['stock_cost'] = avg_cost
            grouped_positions[underlying]['stock_price'] = mark_price
            grouped_positions[underlying]['stock_value'] = quantity * mark_price
            grouped_positions[underlying]['stock_unrealized'] = unrealized
        elif asset_cat == 'OPT':
            grouped_positions[underlying]['options'].append({
                'symbol': symbol,
                'option_type': 'call' if pos.get('put_call') == 'C' else 'put',
                'strike': float(pos.get('strike', 0)) if pos.get('strike') else 0,
                'expiry': pos.get('expiry', ''),
                'quantity': int(abs(quantity)),
                'action': 'buy' if quantity > 0 else 'sell',
                'net_quantity': quantity,
                'mark_price': mark_price,
                'unrealized_pnl': unrealized
            })
    
    # 取得已實現盈虧
    pnl_by_symbol = db.get_pnl_by_symbol()
    
    # 建立回應
    positions = []
    total_market_value = 0
    total_unrealized = 0
    
    for underlying, data in grouped_positions.items():
        # 計算策略類型
        strategy = None
        strategy_description = None
        
        has_stock = data['stock_quantity'] > 0
        options = data['options']
        
        # 分類選擇權
        long_calls = [o for o in options if o['option_type'] == 'call' and o['action'] == 'buy']
        short_calls = [o for o in options if o['option_type'] == 'call' and o['action'] == 'sell']
        long_puts = [o for o in options if o['option_type'] == 'put' and o['action'] == 'buy']
        short_puts = [o for o in options if o['option_type'] == 'put' and o['action'] == 'sell']
        
        # 識別策略
        if has_stock:
            if short_calls and long_puts:
                strategy = "領口策略"
                strategy_description = "持有正股 + 買 Put + 賣 Call，鎖定風險區間"
            elif short_calls and not long_puts:
                strategy = "備兌看漲"
                strategy_description = "持有正股，賣出看漲期權收取權利金"
            elif long_puts and not short_calls:
                strategy = "保護性賣權"
                strategy_description = "持有正股，買入賣權保護下跌風險"
            elif short_calls and short_puts:
                strategy = "備兌勒式"
                strategy_description = "持有正股，賣出看漲+賣權收取權利金"
            else:
                strategy = "純股票持倉"
                strategy_description = "持有正股，無選擇權保護"
        elif options:
            if long_puts and short_puts and not long_calls and not short_calls:
                if any(o['strike'] > p['strike'] for o in long_puts for p in short_puts):
                    strategy = "熊市看跌價差"
                    strategy_description = "買高履約價 Put + 賣低履約價 Put，看跌但限制風險"
                else:
                    strategy = "牛市看跌價差"
                    strategy_description = "賣高履約價 Put + 買低履約價 Put，看漲收取權利金"
            elif long_calls and short_calls and not long_puts and not short_puts:
                strategy = "看漲價差"
                strategy_description = "買低履約價 Call + 賣高履約價 Call"
            elif long_calls and long_puts:
                strategy = "跨式/勒式"
                strategy_description = "買入 Call + Put，預期大幅波動"
            elif short_calls and short_puts:
                strategy = "賣出跨式/勒式"
                strategy_description = "賣出 Call + Put，預期小幅波動"
            elif long_puts and not long_calls and not short_calls and not short_puts:
                strategy = "純看跌"
                strategy_description = "買入賣權，看跌或避險"
            elif long_calls and not long_puts and not short_calls and not short_puts:
                strategy = "純看漲"
                strategy_description = "買入買權，看漲"
            else:
                strategy = "選擇權組合"
                strategy_description = "自訂選擇權策略"
        
        # 計算市值和未實現盈虧
        stock_value = data['stock_value']
        stock_unrealized = data['stock_unrealized']
        options_value = sum(o.get('mark_price', 0) * o.get('net_quantity', 0) * 100 for o in options)
        options_unrealized = sum(o.get('unrealized_pnl', 0) for o in options)
        
        total_market_value += stock_value + options_value
        total_unrealized += stock_unrealized + options_unrealized
        
        # 轉換選擇權腿
        option_legs = []
        for o in options:
            option_legs.append(OptionLegResponse(
                symbol=o['symbol'],
                option_type=o['option_type'],
                strike=o['strike'],
                expiry=o['expiry'],
                quantity=o['quantity'],
                action=o['action']
            ))
        
        # 計算股票的報酬率
        if data['stock_quantity'] > 0 and data['stock_cost'] > 0:
            cost_basis = data['stock_cost'] * data['stock_quantity']
            unrealized_pnl_pct = (stock_unrealized / cost_basis * 100) if cost_basis > 0 else 0
        else:
            unrealized_pnl_pct = 0
        
        # 計算 Greek 和風險等級
        # 股票 Delta = 1.0（完全跟隨標的價格）
        # 選擇權 Delta/Gamma/Vega/Theta 從選擇權腿計算
        total_delta = data['stock_quantity']  # 股票 delta = 股數
        total_gamma = 0.0
        total_vega = 0.0
        total_theta = 0.0
        
        for o in options:
            opt_qty = o.get('net_quantity', o.get('quantity', 0))
            if o['action'] == 'sell':
                opt_qty = -abs(opt_qty)
            multiplier = 100  # 標準選擇權 multiplier
            
            # 簡化的 Greek 估算（實際應從選擇權定價模型計算）
            # Delta: Call ≈ 0.5, Put ≈ -0.5（ATM）
            # 調整 ITM/OTM
            stock_price = data['stock_price']
            strike = o.get('strike', 0)
            is_call = o['option_type'] == 'call'
            
            if stock_price > 0 and strike > 0:
                moneyness = stock_price / strike
                if is_call:
                    delta_per = 0.7 if moneyness > 1.1 else (0.3 if moneyness < 0.9 else 0.5)
                else:
                    delta_per = -0.7 if moneyness < 0.9 else (-0.3 if moneyness > 1.1 else -0.5)
            else:
                delta_per = 0.5 if is_call else -0.5
            
            # 計算總 Greek（考慮數量和方向）
            total_delta += delta_per * opt_qty * multiplier
            total_gamma += 0.02 * abs(opt_qty) * multiplier  # 簡化估算
            total_vega += 0.1 * abs(opt_qty) * multiplier
            total_theta += -0.05 * abs(opt_qty) * multiplier  # Theta 通常是負的
        
        # 計算風險等級（基於 Delta 暴露）
        market_value_for_risk = stock_value if stock_value > 0 else abs(total_delta * data['stock_price'])
        delta_exposure = abs(total_delta * data['stock_price']) if data['stock_price'] > 0 else 0
        
        if delta_exposure > 50000:
            risk_level = "高"
        elif delta_exposure > 20000:
            risk_level = "中"
        else:
            risk_level = "低"
        
        positions.append(PositionResponse(
            symbol=underlying,
            underlying=underlying,
            quantity=int(data['stock_quantity']),
            avg_cost=data['stock_cost'],
            current_price=data['stock_price'],
            market_value=stock_value,
            unrealized_pnl=stock_unrealized + options_unrealized,
            unrealized_pnl_pct=unrealized_pnl_pct,
            realized_pnl=pnl_by_symbol.get(underlying, 0),
            strategy=strategy,
            strategy_description=strategy_description,
            options=option_legs,
            risk_level=risk_level,
            delta=round(total_delta, 2),
            gamma=round(total_gamma, 4),
            vega=round(total_vega, 2),
            theta=round(total_theta, 2)
        ))
    
    # 取得現金餘額
    cash_balance = 0
    try:
        flex = IBKRFlexQuery()
        cash_data = flex.get_cash_balance()
        cash_balance = cash_data.get('total_cash', 0)
    except Exception:
        pass
    
    return PortfolioOverviewResponse(
        positions=positions,
        total_market_value=total_market_value,
        total_unrealized_pnl=total_unrealized,
        total_realized_pnl=sum(p.realized_pnl for p in positions),
        cash_balance=cash_balance
    )


# ========== IBKR 同步 ==========

@app.post("/api/ibkr/sync", response_model=SyncResponse)
async def sync_ibkr():
    """同步 IBKR 數據"""
    try:
        flex = IBKRFlexQuery()
        result = flex.sync_to_database(db)
        
        # 重算盈虧
        pnl_calc = PnLCalculator(db)
        pnl_calc.recalculate_all()
        
        return SyncResponse(
            success=True,
            trades_synced=result.get('trades_synced', 0),
            positions_synced=result.get('positions_synced', 0),
            message="Sync completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ibkr/cash", response_model=CashBalanceResponse)
async def get_cash_balance():
    """取得現金餘額"""
    try:
        flex = IBKRFlexQuery()
        cash_data = flex.get_cash_balance()
        
        return CashBalanceResponse(
            total_cash=cash_data.get('total_cash', 0),
            currency=cash_data.get('currency', 'USD'),
            ending_cash=cash_data.get('ending_cash', 0),
            ending_settled_cash=cash_data.get('ending_settled_cash', 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== AI 分析 ==========

@app.post("/api/ai/chat", response_model=AIAnalysisResponse)
async def ai_chat(request: AIAnalysisRequest):
    """AI 對話（自動包含持倉和統計數據）"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        # 構建完整的上下文資訊
        context_parts = []
        
        # 1. 取得當前持倉
        positions = db.get_latest_positions()
        if positions:
            positions_summary = "📊 當前持倉:\n"
            for p in positions:
                symbol = p.get('symbol', '')
                qty = p.get('position', 0)
                price = p.get('mark_price', 0)
                pnl = p.get('unrealized_pnl', 0)
                positions_summary += f"  - {symbol}: {qty} 張/股 @ ${price:.2f}, 未實現: ${pnl:.2f}\n"
            context_parts.append(positions_summary)
        else:
            # 使用硬編碼的持倉（臨時方案）
            context_parts.append("""📊 當前持倉:
  - SMCI: 410 股 @ $33.19, 未實現: -$3,357.11
  - SMR: 780 股 @ $19.68, 未實現: +$320.99
  - NVTS: 80 股 @ $8.83, 未實現: +$66.20
  - ONDS: 2,550 股 @ $8.54, 未實現: +$3,491.65
  - SMR 250116C22 (做空): -2 張 @ $1.47, 未實現: -$37.66
""")
        
        # 2. 取得交易統計
        stats = db.get_trade_statistics()
        if stats:
            stats_summary = f"""📈 績效統計:
  - 總交易: {stats.get('total_trades', 0)} 筆
  - 總盈虧: ${stats.get('total_pnl', 0):,.2f}
  - 勝率: {stats.get('win_rate', 0):.1f}%
  - 獲利因子: {stats.get('profit_factor', 0):.2f}
  - 平均獲利: ${stats.get('avg_win', 0):,.2f}
  - 平均虧損: ${stats.get('avg_loss', 0):,.2f}
"""
            context_parts.append(stats_summary)
        
        # 3. 如果有指定標的，取得該標的的詳細交易記錄
        if request.symbol:
            trades = db.get_trades()
            symbol_trades = [t for t in trades if t['symbol'] == request.symbol]
            if symbol_trades:
                symbol_context = f"\n📋 {request.symbol} 交易記錄: {len(symbol_trades)} 筆\n"
                total_pnl = sum(t.get('realized_pnl', 0) for t in symbol_trades)
                symbol_context += f"  - 該標的總盈虧: ${total_pnl:,.2f}"
                context_parts.append(symbol_context)
        
        # 組合完整 context
        full_context = "\n".join(context_parts)
        
        # 組合提示詞
        prompt = f"""你是一位專業的交易教練，請根據以下用戶的持倉和交易數據，提供分析和建議。

{full_context}

用戶問題: {request.message}

請用繁體中文回答，提供具體、可執行的建議。"""
        
        # 取得 AI 回應
        response = ai_coach.chat(prompt)
        
        # 生成 session_id
        session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return AIAnalysisResponse(
            response=response,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/ai/analyze-portfolio")
async def analyze_portfolio():
    """AI 分析整體投資組合"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        trades = db.get_trades()
        stats = db.get_trade_statistics()
        pnl_by_symbol = db.get_pnl_by_symbol()
        
        # 準備分析數據
        summary = f"""
        Portfolio Summary:
        - Total Trades: {stats.get('total_trades', 0)}
        - Total P&L: ${stats.get('total_pnl', 0):,.2f}
        - Win Rate: {stats.get('win_rate', 0):.1f}%
        - Profit Factor: {stats.get('profit_factor', 0):.2f}
        
        Top Performers:
        """
        
        sorted_pnl = sorted(pnl_by_symbol.items(), key=lambda x: x[1], reverse=True)
        for symbol, pnl in sorted_pnl[:5]:
            summary += f"\n- {symbol}: ${pnl:,.2f}"
        
        prompt = f"{summary}\n\nPlease provide a comprehensive analysis of this portfolio."
        response = ai_coach.chat(prompt)
        
        return {"analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 設定 ==========

@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """取得系統設定"""
    return SettingsResponse(
        language="zh",
        theme="dark",
        ibkr_configured=bool(os.getenv("IBKR_FLEX_TOKEN")),
        ai_configured=ai_coach is not None
    )


@app.put("/api/settings")
async def update_settings(language: Optional[str] = None, theme: Optional[str] = None):
    """更新系統設定"""
    # 這裡可以存到資料庫或設定檔
    return {"message": "Settings updated", "language": language, "theme": theme}


# ========== 資料庫維護 ==========

@app.post("/api/maintenance/recalculate-pnl")
async def recalculate_pnl():
    """重新計算盈虧"""
    try:
        pnl_calc = PnLCalculator(db)
        pnl_calc.recalculate_all()
        return {"message": "P&L recalculated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/maintenance/clear-database")
async def clear_database():
    """清空資料庫"""
    try:
        db.clear_database()
        return {"message": "Database cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 績效報告 ==========

class PerformanceReportResponse(BaseModel):
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    best_trade: float
    worst_trade: float
    pnl_by_symbol: Dict[str, float]
    pnl_by_hour: Dict[int, float]
    warnings: List[str]


@app.get("/api/report/performance", response_model=PerformanceReportResponse)
async def get_performance_report():
    """取得績效報告"""
    stats = db.get_trade_statistics()
    pnl_by_symbol = db.get_pnl_by_symbol()
    pnl_by_hour = db.get_pnl_by_hour()
    
    # 生成警告
    warnings = []
    if stats.get('avg_loss', 0) > stats.get('avg_win', 0) * 1.5:
        warnings.append("風險警告：平均虧損顯著大於平均獲利，建議改善停損紀律")
    if stats.get('win_rate', 0) < 40:
        warnings.append("勝率偏低，考慮優化進場時機")
    if len(pnl_by_hour) > 0:
        worst_hour = min(pnl_by_hour.items(), key=lambda x: x[1], default=(0, 0))
        if worst_hour[1] < 0:
            warnings.append(f"注意：{worst_hour[0]}:00 附近是虧損較多的時段")
    
    return PerformanceReportResponse(
        total_trades=stats.get('total_trades', 0),
        wins=stats.get('wins', 0),
        losses=stats.get('losses', 0),
        win_rate=stats.get('win_rate', 0),
        total_pnl=stats.get('total_pnl', 0),
        avg_win=stats.get('avg_win', 0),
        avg_loss=stats.get('avg_loss', 0),
        profit_factor=stats.get('profit_factor', 0),
        best_trade=stats.get('best_trade', 0),
        worst_trade=stats.get('worst_trade', 0),
        pnl_by_symbol=pnl_by_symbol or {},
        pnl_by_hour=pnl_by_hour or {},
        warnings=warnings
    )


@app.post("/api/report/ai-review")
async def get_ai_performance_review():
    """AI 績效評語"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        stats = db.get_trade_statistics()
        pnl_by_symbol = db.get_pnl_by_symbol()
        
        # 組合洞察
        insights = []
        if pnl_by_symbol:
            sorted_pnl = sorted(pnl_by_symbol.items(), key=lambda x: x[1])
            if sorted_pnl:
                insights.append(f"最差標的: {sorted_pnl[0][0]} (${sorted_pnl[0][1]:,.2f})")
                insights.append(f"最佳標的: {sorted_pnl[-1][0]} (${sorted_pnl[-1][1]:,.2f})")
        
        review = ai_coach.generate_performance_review(
            stats=stats,
            insights="; ".join(insights)
        )
        
        return {"review": review}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 策略模擬 ==========

class StrategySimulationRequest(BaseModel):
    asset_type: str  # stock, option, futures
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    iv: Optional[float] = None
    upcoming_events: Optional[str] = None
    goal: str  # add_position, take_profit, hedge, spread


class StrategyRecommendation(BaseModel):
    strategy: str
    description: str
    risk_level: str
    expected_return: str


@app.post("/api/strategy/simulate")
async def simulate_strategy(request: StrategySimulationRequest):
    """策略模擬與建議"""
    recommendations = []
    
    iv = request.iv or 25.0
    goal = request.goal
    asset_type = request.asset_type
    
    # 根據目標和 IV 推薦策略
    if goal == "add_position":
        if iv > 30:
            recommendations.append(StrategyRecommendation(
                strategy="Sell Cash-Secured Put",
                description="IV 偏高，賣出 Put 可賺取較高權利金",
                risk_level="中等",
                expected_return="權利金收入"
            ))
        else:
            recommendations.append(StrategyRecommendation(
                strategy="Direct Buy",
                description="IV 正常，直接買入股票",
                risk_level="標準",
                expected_return="股價上漲收益"
            ))
    elif goal == "take_profit":
        recommendations.append(StrategyRecommendation(
            strategy="Covered Call",
            description="賣出 Covered Call 鎖定利潤",
            risk_level="低",
            expected_return="權利金 + 有限上漲空間"
        ))
        recommendations.append(StrategyRecommendation(
            strategy="Trailing Stop",
            description="設定追蹤止損，讓獲利奔跑",
            risk_level="中等",
            expected_return="保護利潤同時捕捉更多上漲"
        ))
    elif goal == "hedge":
        recommendations.append(StrategyRecommendation(
            strategy="Buy Protective Put",
            description="買入保護性 Put 對沖下跌風險",
            risk_level="低",
            expected_return="限制最大虧損"
        ))
        if iv > 25:
            recommendations.append(StrategyRecommendation(
                strategy="Collar Strategy",
                description="買 Put + 賣 Call，零成本對沖",
                risk_level="低",
                expected_return="鎖定價格區間"
            ))
    elif goal == "spread":
        if iv > 30:
            recommendations.append(StrategyRecommendation(
                strategy="Iron Condor",
                description="高 IV 環境賺取時間價值",
                risk_level="中等",
                expected_return="權利金收入"
            ))
        else:
            recommendations.append(StrategyRecommendation(
                strategy="Calendar Spread",
                description="利用時間價值差異獲利",
                risk_level="中等",
                expected_return="近期時間價值衰減"
            ))
    
    return {"recommendations": [r.model_dump() for r in recommendations]}


@app.post("/api/strategy/ai-advice")
async def get_ai_strategy_advice(request: StrategySimulationRequest):
    """AI 策略深度分析"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        position_data = {
            'asset_type': request.asset_type,
            'symbol': request.symbol,
            'quantity': request.quantity,
            'avg_cost': request.avg_cost,
        }
        
        market_data = {
            'current_price': request.current_price,
            'iv': request.iv or 25.0,
        }
        
        scenario = {
            'upcoming_events': request.upcoming_events or '',
            'goal': request.goal,
        }
        
        advice = ai_coach.generate_strategy_advice(
            position_data=position_data,
            market_data=market_data,
            scenario=scenario,
            recommended_strategies=[]
        )
        
        return {"advice": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 選擇權顧問 ==========

class OptionsAdviceRequest(BaseModel):
    symbol: str
    current_price: float
    market_view: str  # bullish, bearish, neutral, volatile
    time_horizon: str  # 1-2週, 3-4週, 1-2個月, 3個月以上
    risk_tolerance: str  # conservative, moderate, aggressive
    capital: float
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None


@app.post("/api/options/advice")
async def get_options_advice(request: OptionsAdviceRequest):
    """AI 選擇權策略建議"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        context = f"""
標的: {request.symbol}
當前價格: ${request.current_price:.2f}
市場看法: {request.market_view}
時間範圍: {request.time_horizon}
風險承受度: {request.risk_tolerance}
可用資金: ${request.capital:,.0f}
"""
        if request.fifty_two_week_high:
            context += f"\n52週高點: ${request.fifty_two_week_high:.2f}"
        if request.fifty_two_week_low:
            context += f"\n52週低點: ${request.fifty_two_week_low:.2f}"
        if request.beta:
            context += f"\nBeta: {request.beta}"
        
        prompt = f"""
你是一位資深選擇權交易顧問。請根據以下資訊，提供詳細的選擇權策略建議：

{context}

請提供：

## 1. 推薦策略（至少 3 個）

對於每個策略，包含：
- **策略名稱**（中英文）
- **適合原因**（為什麼適合這個市場看法）
- **建議履約價** (Strike Price)
- **建議到期日**（根據時間範圍）
- **預估成本/權利金**
- **最大獲利**
- **最大虧損**
- **損益平衡點**

## 2. Greeks 影響

簡單說明 Delta、Gamma、Theta、Vega 對這些策略的影響。

## 3. 風險提醒

- 需要注意的關鍵風險
- 停損建議

請用繁體中文回答。
"""
        
        response = ai_coach.model.generate_content(prompt)
        return {"advice": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Portfolio AI 顧問 ==========

class PortfolioAnalysisRequest(BaseModel):
    include_reports: bool = True


@app.post("/api/portfolio/ai-analysis")
async def get_portfolio_ai_analysis(request: PortfolioAnalysisRequest):
    """AI 投資組合分析"""
    if not ai_coach:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        trades = db.get_trades()
        positions = db.get_latest_positions()
        stats = db.get_trade_statistics()
        
        # 載入研究報告
        reports_content = ""
        if request.include_reports:
            import glob
            reports_dir = os.path.join(parent_dir, 'reports')
            report_files = glob.glob(os.path.join(reports_dir, '*.md'))
            for rf in report_files[:5]:  # 最多 5 個報告
                try:
                    with open(rf, 'r', encoding='utf-8') as f:
                        reports_content += f"\n\n--- {os.path.basename(rf)} ---\n{f.read()}"
                except Exception:
                    pass
        
        # 組合分析提示
        portfolio_summary = f"""
投資組合摘要：
- 總交易筆數: {stats.get('total_trades', 0)}
- 總盈虧: ${stats.get('total_pnl', 0):,.2f}
- 勝率: {stats.get('win_rate', 0):.1f}%
- 獲利因子: {stats.get('profit_factor', 0):.2f}
- 持倉數量: {len(positions) if positions else 0}
"""
        
        if positions:
            portfolio_summary += "\n當前持倉:\n"
            for pos in positions[:10]:
                portfolio_summary += f"- {pos.get('symbol')}: {pos.get('position')} 股, 市值 ${pos.get('mark_price', 0) * pos.get('position', 0):,.2f}\n"
        
        prompt = f"""
你是一位專業的投資組合顧問。請分析以下投資組合並提供建議：

{portfolio_summary}

{f"研究報告摘要:{reports_content[:3000]}" if reports_content else ""}

請提供：

## 1. 持倉風險分析
- 集中度風險
- 相關性風險
- 部門暴露

## 2. 調整建議
- 應該增加/減少的部位
- 再平衡建議

## 3. 避險策略
- 當前市場環境下的避險建議
- 選擇權策略建議

## 4. 整體評分 (1-10分)
- 分散度
- 風險控制
- 獲利能力

請用繁體中文回答。
"""
        
        response = ai_coach.model.generate_content(prompt)
        return {"analysis": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 策略實驗室 (回測) ==========

@app.get("/api/lab/backtests")
async def list_backtests():
    """列出可用的回測結果"""
    try:
        from utils.backtest_loader import BacktestLoader
        loader = BacktestLoader()
        backtests = loader.list_available_backtests()
        return {"backtests": backtests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lab/backtest/{filename}")
async def get_backtest_result(filename: str):
    """取得回測結果"""
    try:
        from utils.backtest_loader import BacktestLoader
        loader = BacktestLoader()
        
        # 找到對應的回測檔案
        backtests = loader.list_available_backtests()
        target = next((b for b in backtests if b['name'] == filename), None)
        
        if not target:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        df = loader.load_backtest_result(target['path'])
        summary = loader.analyze_backtest_summary(df)
        
        return {
            "data": df.to_dict('records')[:100],  # 限制回傳筆數
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 錯誤卡片 ==========

class MistakeCardRequest(BaseModel):
    symbol: str
    date: str
    error_type: str
    description: str
    lesson: str
    emotional_state: Optional[str] = None


@app.get("/api/mistakes")
async def get_mistake_cards():
    """取得所有錯誤卡片"""
    try:
        cards = db.get_mistake_cards()
        return {"cards": cards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mistakes")
async def add_mistake_card(request: MistakeCardRequest):
    """新增錯誤卡片"""
    try:
        card_id = db.add_mistake_card(
            symbol=request.symbol,
            date=request.date,
            error_type=request.error_type,
            description=request.description,
            lesson=request.lesson,
            emotional_state=request.emotional_state
        )
        return {"id": card_id, "message": "Mistake card added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 市場數據 ==========

@app.get("/api/market/quote/{symbol}")
async def get_market_quote(symbol: str):
    """取得即時報價"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        current_price = float(hist['Close'].iloc[-1]) if len(hist) > 0 else 0
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "previous_close": info.get('previousClose'),
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow'),
            "beta": info.get('beta'),
            "market_cap": info.get('marketCap'),
            "pe_ratio": info.get('trailingPE'),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/history/{symbol}")
async def get_market_history(symbol: str, period: str = "1mo"):
    """取得歷史價格"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        data = []
        for idx, row in hist.iterrows():
            data.append({
                "date": idx.strftime('%Y-%m-%d'),
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": row['Volume']
            })
        
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
