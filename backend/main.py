"""
AI Trading Journal - FastAPI Backend

提供 REST API 給 React 前端使用
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os
import sys

# 加入父目錄到 path 以便匯入現有模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import TradingDatabase
from utils.ai_coach import AICoach
from utils.ibkr_flex_query import IBKRFlexQuery
from utils.option_strategies import OptionStrategyDetector, StrategyType, get_strategy_risk_level
from utils.derivatives_support import InstrumentParser
from utils.telegram_notifier import TelegramNotifier
from utils.report_generator import ReportGenerator
from utils.pnl_calculator import PnLCalculator
from utils.logger import get_logger

# 初始化 Logger
logger = get_logger(__name__)

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

# AI 教練實例（延遲初始化，從資料庫讀取設定）
ai_coach = None

def get_ai_coach():
    """取得 AI 教練實例（從資料庫讀取 API Key）"""
    global ai_coach
    
    # 從資料庫或環境變數讀取設定
    gemini_key = db.get_setting('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
    deepseek_key = db.get_setting('DEEPSEEK_API_KEY') or os.getenv('DEEPSEEK_API_KEY')
    ai_provider = db.get_setting('AI_PROVIDER') or os.getenv('AI_PROVIDER', 'auto')
    
    if not gemini_key and not deepseek_key:
        logger.warning("未找到任何 AI API Key (DEEPSEEK_API_KEY 或 GEMINI_API_KEY)")
        return None
    
    try:
        # 優先順序: 1. 明確指定的 provider 2. DeepSeek 優先 3. Gemini 備用
        if ai_provider == 'deepseek' and deepseek_key:
            ai_coach = AICoach(api_key=deepseek_key, provider='deepseek')
            logger.info("AI Coach 使用 DeepSeek")
        elif ai_provider == 'gemini' and gemini_key:
            ai_coach = AICoach(api_key=gemini_key, provider='gemini')
            logger.info("AI Coach 使用 Gemini")
        elif deepseek_key:
            # 預設優先使用 DeepSeek（費用更低）
            ai_coach = AICoach(api_key=deepseek_key, provider='deepseek')
            logger.info("AI Coach 使用 DeepSeek (預設優先)")
        elif gemini_key:
            ai_coach = AICoach(api_key=gemini_key, provider='gemini')
            logger.info("AI Coach 使用 Gemini (備用)")
        return ai_coach
    except Exception as e:
        logger.error(f"AI Coach 初始化失敗: {e}")
        return None


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
    telegram_configured: bool
    telegram_daily_time: str
    telegram_bot_token: str  # 只回傳部分或遮蔽？前端需要顯示
    telegram_chat_id: str


class ConfigValidationRequest(BaseModel):
    config_type: str  # 'ibkr', 'gemini', 'deepseek', 'openai'
    token: Optional[str] = None
    query_id: Optional[str] = None
    positions_query_id: Optional[str] = None


class ConfigValidationResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class SaveConfigRequest(BaseModel):
    ibkr_flex_token: Optional[str] = None
    ibkr_history_query_id: Optional[str] = None
    ibkr_positions_query_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ai_provider: Optional[str] = None  # 'gemini', 'deepseek', 'openai'
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_daily_time: Optional[str] = None  # "HH:MM"
    telegram_enabled: Optional[bool] = None


# ========== Helper Functions ==========

def _calculate_positions_from_trades() -> List[Dict]:
    """從交易記錄計算當前持倉"""
    trades = db.get_trades()
    if not trades:
        return []
    
    parser = InstrumentParser()
    positions_by_symbol = {}
    
    for t in trades:
        symbol = t['symbol']
        action = t['action'].upper()
        quantity = t['quantity']
        price = t['price']

        # 相容處理：歷史資料可能存在兩種格式
        # 1) BUY 正數、SELL 負數
        # 2) BUY 正數、SELL 正數（需要依 action 判斷方向）
        if action in ['SELL', 'SLD'] and quantity > 0:
            qty_change = -quantity
        else:
            qty_change = quantity
        
        if symbol not in positions_by_symbol:
            positions_by_symbol[symbol] = {
                'symbol': symbol,
                'position': 0,
                'total_cost': 0,
                'buy_qty': 0,
                'asset_category': 'OPT' if t.get('instrument_type') == 'option' else 'STK',
                'strike': t.get('strike'),
                'expiry': t.get('expiry'),
                'put_call': 'C' if t.get('option_type') == 'Call' else ('P' if t.get('option_type') == 'Put' else None),
            }
        
        positions_by_symbol[symbol]['position'] += qty_change
        
        # 計算平均成本（只計算買入）
        if qty_change > 0:
            positions_by_symbol[symbol]['total_cost'] += qty_change * price
            positions_by_symbol[symbol]['buy_qty'] += qty_change
    
    # 轉換為持倉列表（只保留有持倉的）
    result = []
    for symbol, pos in positions_by_symbol.items():
        if pos['position'] != 0:  # 有持倉
            avg_cost = pos['total_cost'] / pos['buy_qty'] if pos['buy_qty'] > 0 else 0
            
            # 嘗試取得即時價格
            mark_price = 0
            unrealized_pnl = 0
            parsed = parser.parse_symbol(symbol)
            
            if pos['asset_category'] == 'STK':
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(parsed['underlying'])
                    hist = ticker.history(period="1d")
                    if len(hist) > 0:
                        mark_price = float(hist['Close'].iloc[-1])
                        unrealized_pnl = (mark_price - avg_cost) * pos['position']
                except Exception:
                    pass
            
            result.append({
                'symbol': symbol,
                'position': pos['position'],
                'mark_price': mark_price,
                'average_cost': avg_cost,
                'unrealized_pnl': unrealized_pnl,
                'asset_category': pos['asset_category'],
                'strike': pos.get('strike'),
                'expiry': pos.get('expiry'),
                'put_call': pos.get('put_call'),
            })
    
    return result


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
async def get_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """取得交易統計（支援日期篩選）"""
    trades = db.get_trades()
    
    # 日期篩選
    if start_date or end_date:
        filtered_trades = []
        for t in trades:
            try:
                trade_date_str = t.get('datetime', '')
                if len(trade_date_str) == 8:  # YYYYMMDD format
                    trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
                else:
                    trade_date = datetime.fromisoformat(trade_date_str).date()
                
                if start_date and trade_date < start_date:
                    continue
                if end_date and trade_date > end_date:
                    continue
                filtered_trades.append(t)
            except Exception:
                continue
        trades = filtered_trades
    
    # 計算統計
    if not trades:
        return StatisticsResponse(
            total_trades=0, total_pnl=0, win_rate=0,
            avg_win=0, avg_loss=0, profit_factor=0,
            best_trade=0, worst_trade=0
        )
    
    wins = [t['realized_pnl'] for t in trades if t.get('realized_pnl', 0) > 0]
    losses = [t['realized_pnl'] for t in trades if t.get('realized_pnl', 0) < 0]
    total_pnl = sum(t.get('realized_pnl', 0) for t in trades)
    
    return StatisticsResponse(
        total_trades=len(trades),
        total_pnl=total_pnl,
        win_rate=(len(wins) / len(trades) * 100) if trades else 0,
        avg_win=(sum(wins) / len(wins)) if wins else 0,
        avg_loss=(sum(losses) / len(losses)) if losses else 0,
        profit_factor=(sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0,
        best_trade=max(wins) if wins else 0,
        worst_trade=min(losses) if losses else 0,
    )


@app.get("/api/equity-curve")
async def get_equity_curve(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """取得資金曲線數據（支援日期篩選）"""
    trades = db.get_trades()
    if not trades:
        return {"data": []}
    
    # 按時間排序
    sorted_trades = sorted(trades, key=lambda x: x['datetime'])
    
    # 日期篩選
    if start_date or end_date:
        filtered_trades = []
        for t in sorted_trades:
            try:
                trade_date_str = t.get('datetime', '')
                if len(trade_date_str) == 8:
                    trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
                else:
                    trade_date = datetime.fromisoformat(trade_date_str).date()
                
                if start_date and trade_date < start_date:
                    continue
                if end_date and trade_date > end_date:
                    continue
                filtered_trades.append(t)
            except Exception:
                continue
        sorted_trades = filtered_trades
    
    # 計算累計盈虧
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
    """取得持倉總覽（基於 IBKR 持倉快照或交易記錄計算）"""
    
    # 先嘗試從資料庫取得最新持倉快照
    positions_raw = db.get_latest_positions()
    
    # 始終計算交易記錄推導的持倉，用於補全遺漏的數據（例如 VIX 指數選擇權可能不在持倉快照中）
    calculated_positions = _calculate_positions_from_trades()
    
    if not positions_raw:
        positions_raw = calculated_positions
    else:
        # 建立 calculated_positions 的 symbol -> data 映射
        calc_by_symbol = {p.get('symbol', ''): p for p in calculated_positions}
        
        # 合併邏輯：以 positions_raw (IBKR Snapshot) 為主
        # 1. 如果 IBKR 缺少成本基礎或未實現盈虧，從 calculated_positions 補全
        # 2. 如果 calculated_positions 有但 positions_raw 沒有的 symbol，加入
        snapshot_symbols = set()
        
        for pos in positions_raw:
            symbol = pos.get('symbol', '')
            snapshot_symbols.add(symbol)
            
            # 檢查是否需要從 calculated_positions 補全數據
            calc_pos = calc_by_symbol.get(symbol)
            if calc_pos:
                # 如果 IBKR 沒有返回成本基礎，使用計算的
                if not pos.get('average_cost') or pos.get('average_cost', 0) == 0:
                    pos['average_cost'] = calc_pos.get('average_cost', 0)
                
                # 如果 IBKR 沒有返回未實現盈虧，使用計算的
                if not pos.get('unrealized_pnl') or pos.get('unrealized_pnl', 0) == 0:
                    # 重新計算未實現盈虧
                    mark_price = pos.get('mark_price', 0) or calc_pos.get('mark_price', 0)
                    avg_cost = pos.get('average_cost', 0) or calc_pos.get('average_cost', 0)
                    quantity = pos.get('position', 0)
                    
                    if mark_price > 0 and avg_cost > 0 and quantity != 0:
                        pos['unrealized_pnl'] = (mark_price - avg_cost) * quantity
                        pos['mark_price'] = mark_price
        
        # 加入 calculated_positions 中有但 snapshot 沒有的 symbol
        for calc_pos in calculated_positions:
            symbol = calc_pos.get('symbol', '')
            if symbol and symbol not in snapshot_symbols and calc_pos.get('position', 0) != 0:
                calc_pos['source'] = 'calculated'
                positions_raw.append(calc_pos)
    
    # 使用 OptionStrategyDetector 分析策略
    import pandas as pd
    positions_df = pd.DataFrame(positions_raw) if positions_raw else pd.DataFrame()
    
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
        
        # 優先使用 InstrumentParser 判斷類型（最準確）
        instrument_type = parsed.get('instrument_type', 'stock')
        is_option = instrument_type == 'option'
        
        # 備選：從資料庫欄位判斷
        if not is_option:
            asset_cat = pos.get('asset_category')
            if asset_cat == 'OPT':
                is_option = True
            elif str(pos.get('instrument_type', '')).lower() == 'option':
                is_option = True
        
        quantity = pos.get('position', 0)
        mark_price = pos.get('mark_price', 0)
        avg_cost = pos.get('average_cost', 0)
        unrealized = pos.get('unrealized_pnl', 0)
        
        if is_option:
            # 選擇權
            put_call = pos.get('put_call') or parsed.get('option_type', '')
            if put_call in ['Call', 'call']:
                put_call = 'C'
            elif put_call in ['Put', 'put']:
                put_call = 'P'

            multiplier = int(pos.get('multiplier', 100) or 100)
            grouped_positions[underlying]['options'].append({
                'symbol': symbol,
                'option_type': 'call' if put_call == 'C' else 'put',
                'strike': float(parsed.get('strike') or pos.get('strike', 0) or 0),
                'expiry': parsed.get('expiry') or pos.get('expiry', ''),
                'quantity': int(abs(quantity)),
                'action': 'buy' if quantity > 0 else 'sell',
                'net_quantity': quantity,
                'mark_price': mark_price,
                'unrealized_pnl': unrealized,
                'multiplier': multiplier,
            })
        else:
            # 股票
            grouped_positions[underlying]['stock_quantity'] = quantity
            grouped_positions[underlying]['stock_cost'] = avg_cost
            grouped_positions[underlying]['stock_price'] = mark_price
            grouped_positions[underlying]['stock_value'] = quantity * mark_price
            grouped_positions[underlying]['stock_unrealized'] = unrealized
    
    # 取得已實現盈虧
    pnl_by_symbol = db.get_pnl_by_symbol()
    
    # 建立回應
    positions = []
    total_market_value = 0
    total_unrealized = 0
    
    # 先計算總市值（用於相對風險評估）
    for underlying, data in grouped_positions.items():
        stock_value = data['stock_value']
        options_value = sum(
            o.get('mark_price', 0) * o.get('net_quantity', 0) * float(o.get('multiplier', 100) or 100)
            for o in data['options']
        )
        total_market_value += stock_value + options_value
    
    for underlying, data in grouped_positions.items():
        # 使用新的策略識別模組
        from utils.option_strategies import OptionLeg as StrategyOptionLeg, StockPosition as StrategyStockPosition
        
        # 轉換為策略識別模組的格式
        strategy_options = []
        for o in data['options']:
            qty = o.get('net_quantity', o.get('quantity', 0))
            if o['action'] == 'sell':
                qty = -abs(qty)
            else:
                qty = abs(qty)
            strategy_options.append(StrategyOptionLeg(
                symbol=o['symbol'],
                option_type=o['option_type'],
                strike=o.get('strike', 0),
                expiry=o.get('expiry', ''),
                quantity=qty,
                premium=o.get('mark_price', 0)
            ))
        
        strategy_stock = None
        if data['stock_quantity'] != 0:
            strategy_stock = StrategyStockPosition(
                symbol=underlying,
                quantity=int(data['stock_quantity']),
                avg_cost=data['stock_cost'],
                current_price=data['stock_price']
            )
        
        # 識別策略
        strategy_result = OptionStrategyDetector.detect_strategy(
            strategy_options, strategy_stock, data['stock_price']
        )
        
        strategy = strategy_result.strategy_name
        strategy_description = strategy_result.description
        risk_level = get_strategy_risk_level(strategy_result.strategy_type)
        
        options = data['options']
        
        # 計算市值和未實現盈虧
        stock_value = data['stock_value']
        stock_unrealized = data['stock_unrealized']
        options_value = sum(
            o.get('mark_price', 0) * o.get('net_quantity', 0) * float(o.get('multiplier', 100) or 100)
            for o in options
        )
        options_unrealized = sum(o.get('unrealized_pnl', 0) for o in options)
        
        # total_market_value 已在上面預計算
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
            multiplier = float(o.get('multiplier', 100) or 100)
            
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
        
        # 計算風險等級（多維度評估）
        market_value_for_risk = stock_value if stock_value > 0 else abs(total_delta * data['stock_price'])
        delta_exposure = abs(total_delta * data['stock_price']) if data['stock_price'] > 0 else 0
        
        # 計算相對風險（Delta Exposure 佔總市值的比例）
        total_portfolio_value = total_market_value if total_market_value > 0 else 1
        relative_exposure = delta_exposure / total_portfolio_value
        
        # 計算市值佔比（集中度風險）
        position_concentration = (stock_value + options_value) / total_portfolio_value if total_portfolio_value > 0 else 0
        
        # 風險評估：綜合考慮多個因素
        # 1. Delta 暴露（絕對值）：$5,000 = 中，$15,000 = 高
        # 2. Delta 暴露（相對值）：10% = 中，25% = 高
        # 3. 市值佔比（集中度）：20% = 中，35% = 高
        # 4. 虧損幅度：>15% = 中，>30% = 高
        
        is_high_loss = abs(unrealized_pnl_pct) > 30
        is_medium_loss = abs(unrealized_pnl_pct) > 15
        is_high_concentration = position_concentration > 0.35
        is_medium_concentration = position_concentration > 0.20
        
        if (delta_exposure > 15000 or relative_exposure > 0.25 or 
            is_high_concentration or is_high_loss):
            risk_level = "高"
        elif (delta_exposure > 5000 or relative_exposure > 0.10 or 
              is_medium_concentration or is_medium_loss):
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
    
    # 取得現金餘額（只讀 DB 快照；避免每次都打 IBKR）
    cash_balance = 0
    cash_snapshot = db.get_latest_cash_snapshot()
    if cash_snapshot:
        cash_balance = cash_snapshot.get('total_cash', 0) or 0
    
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
    # 檢查必要設定
    token = _get_config('IBKR_FLEX_TOKEN', '')
    history_qid = _get_config('IBKR_HISTORY_QUERY_ID', '')
    
    if not token or not history_qid:
        raise HTTPException(
            status_code=400, 
            detail="IBKR 尚未設定。請到設定頁面設定 Flex Token 和 Query ID。"
        )
    
    try:
        flex = IBKRFlexQuery(
            token=token,
            history_query_id=history_qid,
            positions_query_id=_get_config('IBKR_POSITIONS_QUERY_ID', ''),
        )
        result = flex.sync_to_database(db)

        # 同步現金快照（寫入 DB；portfolio 只讀 DB）
        try:
            cash_data = flex.get_cash_balance(query_id=history_qid)
            db.upsert_cash_snapshot(
                total_cash=float(cash_data.get('total_cash', 0) or 0),
                total_settled_cash=float(cash_data.get('total_settled_cash', 0) or 0),
                currency='USD',
                snapshot_date=datetime.now().strftime('%Y-%m-%d'),
            )
        except Exception:
            pass
        
        # 重算盈虧
        pnl_calc = PnLCalculator(db)
        pnl_calc.recalculate_all()
        
        return SyncResponse(
            success=True,
            trades_synced=result.get('trades', result.get('trades_synced', 0)),
            positions_synced=result.get('positions', result.get('positions_synced', 0)),
            message="Sync completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/ibkr/cash", response_model=CashBalanceResponse)
async def get_cash_balance():
    """取得現金餘額"""
    cash_snapshot = db.get_latest_cash_snapshot()
    if not cash_snapshot:
        raise HTTPException(status_code=404, detail="No cash snapshot. Please run IBKR sync first.")

    return CashBalanceResponse(
        total_cash=float(cash_snapshot.get('total_cash', 0) or 0),
        currency=str(cash_snapshot.get('currency', 'USD') or 'USD'),
        ending_cash=float(cash_snapshot.get('total_cash', 0) or 0),
        ending_settled_cash=float(cash_snapshot.get('total_settled_cash', 0) or 0),
    )


# ========== AI 分析 ==========

@app.post("/api/ai/chat", response_model=AIAnalysisResponse)
async def ai_chat(request: AIAnalysisRequest):
    """AI 對話（自動包含持倉和統計數據）"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定，請到設定頁面設定 API Key")
    
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
        response = coach.chat(prompt)
        
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
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定，請到設定頁面設定 API Key")
    
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
        response = coach.chat(prompt)
        
        return {"analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 初始化 AI Coach (延遲初始化，避免啟動失敗)
ai_coach = None
try:
    ai_coach = get_ai_coach()
except Exception as e:
    logger.warning(f"AI Coach 初始化警告 (非致命): {e}")


# Scheduler 全域變數 (延遲初始化)
scheduler = None

async def send_daily_report_job():
    """排程任務：發送每日戰情報告"""
    try:
        # 重新從資料庫獲取設定（因為這是排程任務，db session 應該要是新的或 thread-safe）
        # 這裡假設 db 是全域變數且 thread-safe (TradingDatabase 使用 sqlite3，預設 check_same_thread=False)
        
        enabled = db.get_setting('telegram_enabled')
        if enabled != 'true':
            return
            
        token = db.get_setting('telegram_bot_token')
        chat_id = db.get_setting('telegram_chat_id')
        
        if not token or not chat_id:
            logger.info("Telegram 未配置，跳過報告發送")
            return

        # 0. 同步 IBKR 數據 (確保報告最新)
        logger.info("正在同步 IBKR 數據...")
        try:
            flex_token = db.get_setting('ibkr_flex_token')
            history_id = db.get_setting('ibkr_history_query_id')
            positions_id = db.get_setting('ibkr_positions_query_id')
            
            if flex_token:
                flex = IBKRFlexQuery(
                    token=flex_token,
                    history_query_id=history_id,
                    positions_query_id=positions_id
                )
                # 執行同步
                sync_result = flex.sync_to_database(db)
                logger.info(f"IBKR 同步完成: {sync_result}")
            else:
                logger.warning("IBKR Token 未設定，跳過同步")
                
        except Exception as e:
            logger.error(f"IBKR 同步失敗 (繼續生成報告): {e}")

        logger.info(f"開始生成每日報告... (Chat ID: {chat_id})")
        
        # 確保 AI Coach 已初始化
        global ai_coach
        if ai_coach is None:
            ai_coach = get_ai_coach()
            
        if ai_coach is None:
            logger.error("AI Coach 未配置，無法生成報告")
            return
            
        # 重新實例化 ReportGenerator 以確保使用最新的 db 狀態
        generator = ReportGenerator(db, ai_coach)
        report_md = await generator.generate_daily_report()
        
        notifier = TelegramNotifier(token)
        success = notifier.send_message(chat_id, report_md)
        
        if success:
            logger.info("每日報告發送成功")
        else:
            logger.error("每日報告發送失敗")
            
    except Exception as e:
        logger.error(f"每日報告任務執行失敗: {e}")

def update_scheduler_job():
    """根據設定更新排程任務"""
    global scheduler
    if scheduler is None:
        logger.warning("Scheduler 尚未初始化，跳過更新")
        return

    try:
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        # 清除舊任務
        scheduler.remove_all_jobs()
        
        enabled = db.get_setting('telegram_enabled')
        daily_time = db.get_setting('telegram_daily_time')  # "HH:MM"
        
        if enabled == 'true' and daily_time:
            try:
                hour, minute = map(int, daily_time.split(':'))
                # 設定為台灣時間 (Asia/Taipei)
                tz = pytz.timezone('Asia/Taipei')
                
                scheduler.add_job(
                    send_daily_report_job,
                    CronTrigger(hour=hour, minute=minute, timezone=tz),
                    id='daily_report'
                )
                logger.info(f"已排程每日報告: {daily_time} (Asia/Taipei)")
            except ValueError:
                logger.error(f"時間格式錯誤: {daily_time}")
    except Exception as e:
        logger.error(f"更新排程失敗: {e}")

@app.on_event("startup")
async def startup_event():
    global scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.start()
        logger.info("Scheduler 已啟動")
        update_scheduler_job()
    except Exception as e:
        logger.error(f"Scheduler 初始化失敗: {e}")

# ========== API Endpoints ==========

@app.post("/api/telegram/test")
async def test_telegram(request: dict):
    """測試 Telegram 發送"""
    token = request.get('token')
    chat_id = request.get('chat_id')
    
    if not token or not chat_id:
        return {"success": False, "message": "請提供 Token 和 Chat ID"}
        
    try:
        notifier = TelegramNotifier(token)
        message = "🚀 *AI Trading Journal* \n這是一條測試訊息。\n\nTelegram 通知功能設定成功！"
        success = notifier.send_message(chat_id, message)
        
        if success:
            return {"success": True, "message": "發送成功"}
        else:
            return {"success": False, "message": "發送失敗，請檢查 Token 或 Chat ID"}
    except Exception as e:
        return {"success": False, "message": f"發生錯誤: {str(e)}"}


@app.post("/api/telegram/send-daily-report")
async def send_daily_report_manual():
    """手動觸發發送每日戰情報告"""
    token = _get_config('TELEGRAM_BOT_TOKEN', '') or db.get_setting('telegram_bot_token')
    chat_id = _get_config('TELEGRAM_CHAT_ID', '') or db.get_setting('telegram_chat_id')
    
    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="Telegram 尚未設定。請到設定頁面設定 Bot Token 和 Chat ID。")
    
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定，無法生成報告")
    
    try:
        generator = ReportGenerator(db, coach)
        report_md = await generator.generate_daily_report()
        
        notifier = TelegramNotifier(token)
        success = notifier.send_message(chat_id, report_md)
        
        if success:
            return {"success": True, "message": "每日報告已發送到 Telegram"}
        else:
            raise HTTPException(status_code=500, detail="Telegram 發送失敗")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成或發送報告失敗: {str(e)}")


@app.post("/api/telegram/send-plan-alerts")
async def send_plan_alerts():
    """檢查並發送交易計劃警報"""
    token = _get_config('TELEGRAM_BOT_TOKEN', '') or db.get_setting('telegram_bot_token')
    chat_id = _get_config('TELEGRAM_CHAT_ID', '') or db.get_setting('telegram_chat_id')
    
    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="Telegram 尚未設定")
    
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        generator = ReportGenerator(db, coach)
        alerts = await generator.check_all_plan_alerts()
        
        if not alerts:
            return {"success": True, "message": "目前沒有觸發的警報", "alerts_count": 0}
        
        # 組合警報訊息
        header = f"🔔 *交易計劃警報* ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        message = header + "\n\n".join(alerts)
        
        notifier = TelegramNotifier(token)
        success = notifier.send_message(chat_id, message)
        
        if success:
            return {"success": True, "message": f"已發送 {len(alerts)} 條警報", "alerts_count": len(alerts)}
        else:
            raise HTTPException(status_code=500, detail="Telegram 發送失敗")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檢查警報失敗: {str(e)}")


@app.get("/api/telegram/preview-daily-report")
async def preview_daily_report():
    """預覽每日報告（不發送）"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        generator = ReportGenerator(db, coach)
        report_md = await generator.generate_daily_report()
        return {"success": True, "report": report_md}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成報告失敗: {str(e)}")


# ========== 設定 ==========

@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """取得系統設定"""
    return SettingsResponse(
        language=db.get_setting('language', 'zh'),
        theme=db.get_setting('theme', 'system'),
        ibkr_configured=bool(db.get_setting('ibkr_flex_token')),
        ai_configured=bool(db.get_setting('gemini_api_key') or db.get_setting('deepseek_api_key') or db.get_setting('openai_api_key')),
        telegram_configured=bool(db.get_setting('telegram_bot_token') and db.get_setting('telegram_chat_id')),
        telegram_daily_time=db.get_setting('telegram_daily_time', '08:00'),
        telegram_bot_token=db.get_setting('telegram_bot_token', ''),
        telegram_chat_id=db.get_setting('telegram_chat_id', '')
    )


@app.put("/api/settings")
async def update_settings(language: Optional[str] = None, theme: Optional[str] = None):
    """更新系統設定"""
    return {"message": "Settings updated", "language": language, "theme": theme}


def _get_config(key: str, default: str = "") -> str:
    """從資料庫或環境變數取得設定（資料庫優先）"""
    db_value = db.get_setting(key)
    if db_value:
        return db_value
    return os.getenv(key, default)


@app.get("/api/config/status")
async def get_config_status():
    """取得所有設定狀態（從資料庫讀取）"""
    ibkr_token = _get_config("IBKR_FLEX_TOKEN", "")
    ibkr_history_id = _get_config("IBKR_HISTORY_QUERY_ID", "")
    ibkr_positions_id = _get_config("IBKR_POSITIONS_QUERY_ID", "")
    gemini_key = _get_config("GEMINI_API_KEY", "")
    deepseek_key = _get_config("DEEPSEEK_API_KEY", "")
    openai_key = _get_config("OPENAI_API_KEY", "")
    ai_provider = _get_config("AI_PROVIDER", "gemini")
    
    # Telegram Config
    telegram_token = _get_config("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = _get_config("TELEGRAM_CHAT_ID", "")
    telegram_daily_time = _get_config("TELEGRAM_DAILY_TIME", "08:00")
    telegram_enabled = _get_config("TELEGRAM_ENABLED", "false") == "true"
    
    return {
        "ibkr": {
            "configured": bool(ibkr_token and ibkr_history_id),
            "token_set": bool(ibkr_token),
            "token_preview": f"{ibkr_token[:8]}...{ibkr_token[-4:]}" if len(ibkr_token) > 12 else "",
            "history_query_id": ibkr_history_id,
            "positions_query_id": ibkr_positions_id,
        },
        "ai": {
            "configured": bool(gemini_key or deepseek_key or openai_key),
            "provider": ai_provider,
            "gemini_set": bool(gemini_key),
            "deepseek_set": bool(deepseek_key),
            "openai_set": bool(openai_key),
        },
        "telegram": {
            "configured": bool(telegram_token and telegram_chat_id),
            "token_set": bool(telegram_token),
            "chat_id": telegram_chat_id,
            "daily_time": telegram_daily_time,
            "enabled": telegram_enabled
        }
    }


@app.post("/api/config/validate", response_model=ConfigValidationResponse)
async def validate_config(request: ConfigValidationRequest):
    """驗證設定是否有效"""
    
    if request.config_type == "ibkr":
        return await _validate_ibkr_config(request)
    elif request.config_type == "gemini":
        return await _validate_gemini_config(request)
    elif request.config_type == "deepseek":
        return await _validate_deepseek_config(request)
    elif request.config_type == "openai":
        return await _validate_openai_config(request)
    else:
        return ConfigValidationResponse(
            success=False,
            message=f"Unknown config type: {request.config_type}"
        )


async def _validate_ibkr_config(request: ConfigValidationRequest) -> ConfigValidationResponse:
    """驗證 IBKR Flex Query 設定"""
    import requests
    import xml.etree.ElementTree as ET
    
    token = request.token or _get_config("IBKR_FLEX_TOKEN", "")
    query_id = request.query_id or _get_config("IBKR_HISTORY_QUERY_ID", "")
    
    if not token or not query_id:
        return ConfigValidationResponse(
            success=False,
            message="IBKR Token 或 Query ID 未設定"
        )
    
    try:
        # Step 1: 請求報告
        request_url = f"https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest?t={token}&q={query_id}&v=3"
        response = requests.get(request_url, timeout=30)
        
        if response.status_code != 200:
            return ConfigValidationResponse(
                success=False,
                message=f"IBKR API 請求失敗: HTTP {response.status_code}"
            )
        
        # 解析 XML 回應
        root = ET.fromstring(response.text)
        status = root.find('.//Status')
        
        if status is not None and status.text == 'Success':
            reference_code = root.find('.//ReferenceCode')
            return ConfigValidationResponse(
                success=True,
                message="IBKR Flex Query 設定有效！",
                details={
                    "reference_code": reference_code.text if reference_code is not None else None,
                    "query_id": query_id
                }
            )
        else:
            error_msg = root.find('.//ErrorMessage')
            return ConfigValidationResponse(
                success=False,
                message=f"IBKR 驗證失敗: {error_msg.text if error_msg is not None else 'Unknown error'}",
                details={"raw_response": response.text[:500]}
            )
    except ET.ParseError:
        return ConfigValidationResponse(
            success=False,
            message="IBKR 回應格式錯誤，請檢查 Token 和 Query ID"
        )
    except requests.RequestException as e:
        return ConfigValidationResponse(
            success=False,
            message=f"網路連線錯誤: {str(e)}"
        )
    except Exception as e:
        return ConfigValidationResponse(
            success=False,
            message=f"驗證過程發生錯誤: {str(e)}"
        )


async def _validate_gemini_config(request: ConfigValidationRequest) -> ConfigValidationResponse:
    """驗證 Gemini API 設定"""
    import requests
    
    api_key = request.token or _get_config("GEMINI_API_KEY", "")
    
    if not api_key:
        return ConfigValidationResponse(
            success=False,
            message="Gemini API Key 未設定"
        )
    
    try:
        # 測試 API 連線
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = [m.get('name', '').split('/')[-1] for m in data.get('models', [])[:5]]
            return ConfigValidationResponse(
                success=True,
                message="Gemini API 連線成功！",
                details={"available_models": models}
            )
        elif response.status_code == 400:
            return ConfigValidationResponse(
                success=False,
                message="Gemini API Key 無效"
            )
        else:
            return ConfigValidationResponse(
                success=False,
                message=f"Gemini API 錯誤: HTTP {response.status_code}"
            )
    except Exception as e:
        return ConfigValidationResponse(
            success=False,
            message=f"Gemini 驗證失敗: {str(e)}"
        )


async def _validate_deepseek_config(request: ConfigValidationRequest) -> ConfigValidationResponse:
    """驗證 DeepSeek API 設定"""
    import requests
    
    api_key = request.token or _get_config("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        return ConfigValidationResponse(
            success=False,
            message="DeepSeek API Key 未設定"
        )
    
    try:
        # 測試 API 連線
        url = "https://api.deepseek.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = [m.get('id', '') for m in data.get('data', [])[:5]]
            return ConfigValidationResponse(
                success=True,
                message="DeepSeek API 連線成功！",
                details={"available_models": models}
            )
        elif response.status_code == 401:
            return ConfigValidationResponse(
                success=False,
                message="DeepSeek API Key 無效"
            )
        else:
            return ConfigValidationResponse(
                success=False,
                message=f"DeepSeek API 錯誤: HTTP {response.status_code}"
            )
    except Exception as e:
        return ConfigValidationResponse(
            success=False,
            message=f"DeepSeek 驗證失敗: {str(e)}"
        )


async def _validate_openai_config(request: ConfigValidationRequest) -> ConfigValidationResponse:
    """驗證 OpenAI API 設定"""
    import requests
    
    api_key = request.token or _get_config("OPENAI_API_KEY", "")
    
    if not api_key:
        return ConfigValidationResponse(
            success=False,
            message="OpenAI API Key 未設定"
        )
    
    try:
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = [m.get('id', '') for m in data.get('data', []) if 'gpt' in m.get('id', '')][:5]
            return ConfigValidationResponse(
                success=True,
                message="OpenAI API 連線成功！",
                details={"available_models": models}
            )
        elif response.status_code == 401:
            return ConfigValidationResponse(
                success=False,
                message="OpenAI API Key 無效"
            )
        else:
            return ConfigValidationResponse(
                success=False,
                message=f"OpenAI API 錯誤: HTTP {response.status_code}"
            )
    except Exception as e:
        return ConfigValidationResponse(
            success=False,
            message=f"OpenAI 驗證失敗: {str(e)}"
        )


@app.post("/api/config/save")
async def save_config(request: SaveConfigRequest):
    """儲存設定到資料庫（即時生效，不需重啟）"""
    try:
        # 儲存到資料庫
        if request.ibkr_flex_token:
            db.set_setting('IBKR_FLEX_TOKEN', request.ibkr_flex_token)
        if request.ibkr_history_query_id:
            db.set_setting('IBKR_HISTORY_QUERY_ID', request.ibkr_history_query_id)
        if request.ibkr_positions_query_id:
            db.set_setting('IBKR_POSITIONS_QUERY_ID', request.ibkr_positions_query_id)
        if request.gemini_api_key:
            db.set_setting('GEMINI_API_KEY', request.gemini_api_key)
        if request.deepseek_api_key:
            db.set_setting('DEEPSEEK_API_KEY', request.deepseek_api_key)
        if request.openai_api_key:
            db.set_setting('OPENAI_API_KEY', request.openai_api_key)
        if request.ai_provider:
            db.set_setting('AI_PROVIDER', request.ai_provider)
            
        # Telegram Config
        if request.telegram_bot_token:
            db.set_setting('TELEGRAM_BOT_TOKEN', request.telegram_bot_token)
        if request.telegram_chat_id:
            db.set_setting('TELEGRAM_CHAT_ID', request.telegram_chat_id)
        if request.telegram_daily_time:
            db.set_setting('TELEGRAM_DAILY_TIME', request.telegram_daily_time)
        if request.telegram_enabled is not None:
            db.set_setting('TELEGRAM_ENABLED', 'true' if request.telegram_enabled else 'false')
            
        # 更新排程
        update_scheduler_job()
        
        return {"success": True, "message": "設定已儲存，即時生效！"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"儲存設定失敗: {str(e)}")


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
    pnl_by_symbol = db.get_pnl_by_symbol() or {}
    pnl_by_hour_raw = db.get_pnl_by_hour() or {}
    
    # 過濾掉 None key，確保 key 是有效的整數
    pnl_by_hour = {int(k): v for k, v in pnl_by_hour_raw.items() if k is not None}
    
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


# ========== MFE/MAE 分析 ==========

class MFEMAEResponse(BaseModel):
    trade_id: str
    symbol: str
    entry_date: str
    exit_date: Optional[str] = None
    entry_price: float
    exit_price: Optional[float] = None
    mfe: Optional[float] = None
    mae: Optional[float] = None
    mfe_price: Optional[float] = None
    mae_price: Optional[float] = None
    trade_efficiency: Optional[float] = None
    holding_days: Optional[int] = None


@app.get("/api/mfe-mae/stats")
async def get_mfe_mae_stats():
    """取得 MFE/MAE 統計摘要"""
    try:
        # 初始化表格（如果不存在）
        db.init_mfe_mae_table()
        stats = db.get_mfe_mae_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mfe-mae/records")
async def get_mfe_mae_records(symbol: Optional[str] = None):
    """取得 MFE/MAE 記錄列表"""
    try:
        db.init_mfe_mae_table()
        records = db.get_mfe_mae_by_symbol(symbol)
        return {"records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mfe-mae/calculate")
async def calculate_mfe_mae(symbol: Optional[str] = None, recalculate: bool = False):
    """計算所有交易的 MFE/MAE"""
    try:
        from utils.mfe_mae_calculator import MFEMAECalculator
        
        db.init_mfe_mae_table()
        calculator = MFEMAECalculator(db)
        results = calculator.calculate_all_trades(symbol)
        
        return {
            "success": True,
            "calculated_count": len(results),
            "results": results[:20]  # 只返回前 20 筆
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mfe-mae/analysis")
async def get_mfe_mae_analysis():
    """取得 MFE/MAE 效率分析報告"""
    try:
        from utils.mfe_mae_calculator import MFEMAECalculator
        
        db.init_mfe_mae_table()
        calculator = MFEMAECalculator(db)
        analysis = calculator.get_efficiency_analysis()
        
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mfe-mae/running")
async def get_running_mfe_mae():
    """取得未平倉倉位的即時 MFE/MAE（類似 TradesViz 的 Running MFE/MAE）"""
    try:
        from utils.mfe_mae_calculator import MFEMAECalculator
        from utils.derivatives_support import InstrumentParser
        import yfinance as yf
        from datetime import datetime, timedelta
        
        positions = db.get_latest_positions()
        if not positions:
            return {"positions": []}
        
        parser = InstrumentParser()
        results = []
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('position', pos.get('quantity', 0))
            avg_cost = pos.get('avgCost', pos.get('average_cost', 0))
            
            if qty == 0 or avg_cost <= 0:
                continue
            
            parsed = parser.parse_symbol(symbol)
            underlying = parsed.get('underlying', symbol)
            instrument_type = parsed.get('instrument_type', 'stock')
            
            # 只計算股票的 running MFE/MAE
            if instrument_type != 'stock':
                continue
            
            try:
                # 獲取最近 60 天的 OHLC
                ticker = yf.Ticker(underlying)
                hist = ticker.history(period='60d')
                
                if hist.empty:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                high_since_entry = hist['High'].max()
                low_since_entry = hist['Low'].min()
                
                # 計算 running MFE/MAE
                if qty > 0:  # Long
                    running_mfe = ((high_since_entry - avg_cost) / avg_cost) * 100
                    running_mae = ((low_since_entry - avg_cost) / avg_cost) * 100
                    current_pnl = ((current_price - avg_cost) / avg_cost) * 100
                else:  # Short
                    running_mfe = ((avg_cost - low_since_entry) / avg_cost) * 100
                    running_mae = ((avg_cost - high_since_entry) / avg_cost) * 100
                    current_pnl = ((avg_cost - current_price) / avg_cost) * 100
                
                # 計算從峰值回撤
                drawdown_from_peak = running_mfe - current_pnl if running_mfe > 0 else 0
                
                results.append({
                    'symbol': underlying,
                    'quantity': float(qty),
                    'avg_cost': float(avg_cost),
                    'current_price': float(current_price),
                    'current_pnl': round(current_pnl, 2),
                    'running_mfe': round(running_mfe, 2),
                    'running_mae': round(running_mae, 2),
                    'drawdown_from_peak': round(drawdown_from_peak, 2),
                    'efficiency': round(current_pnl / running_mfe, 3) if running_mfe > 0 else 0,
                })
            except Exception as e:
                logger.warning(f"Failed to calculate running MFE/MAE for {underlying}: {e}")
                continue
        
        return {"positions": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mfe-mae/ai-advice")
async def get_mfe_mae_ai_advice(symbol: Optional[str] = None):
    """取得 AI 對 MFE/MAE 的改進建議"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        from utils.mfe_mae_calculator import MFEMAECalculator
        
        db.init_mfe_mae_table()
        calculator = MFEMAECalculator(db)
        context = calculator.generate_ai_context(symbol)
        
        prompt = f"""你是一位專業的交易教練，請根據以下 MFE/MAE 分析數據，提供具體的改進建議：

{context}

**重要提醒：選擇權策略判讀**
- 選擇權經常作為**避險工具**使用（如 Covered Call、Protective Put、Collar 等）
- 當選擇權標的與股票標的相同時（如 ONDS 股票 + ONDS Put），應視為**整體策略**而非獨立交易
- 避險選擇權的「虧損」可能是**預期成本**（如保險費），不應視為交易失敗
- MFE/MAE 對選擇權的意義不同於股票：選擇權本身波動大，要與對應股票持倉一起評估

請回答（不要輸出表格，用列表格式更清晰）：
1. **執行品質評估**（1-10分）：根據 MFE/MAE 數據，評估交易執行的整體品質
2. **主要問題**：識別最大的 2-3 個問題（注意區分真正的問題和避險成本）
3. **具體改進建議**：針對每個問題給出可執行的改進方案
4. **出場策略優化**：根據數據建議更好的出場策略（例如移動停利、分批出場等）
5. **風險控制**：基於 MAE 數據，建議停損策略的調整

請用繁體中文回答，使用 Markdown 格式（避免使用複雜表格）。"""

        response = coach.chat(prompt)
        return {"advice": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NoteDraftRequest(BaseModel):
    date: str
    symbol: Optional[str] = None
    note_type: str = 'daily'

@app.post("/api/notes/ai-draft")
async def generate_note_draft(request: NoteDraftRequest):
    """生成日誌草稿"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        # 獲取當天交易數據作為上下文
        trades = db.get_trades()
        date_trades = [t for t in trades if t['datetime'].startswith(request.date)]
        
        context = ""
        if date_trades:
            pnl = sum(t.get('realized_pnl', 0) for t in date_trades)
            win_count = sum(1 for t in date_trades if t.get('realized_pnl', 0) > 0)
            context = f"當日交易統計: {len(date_trades)} 筆交易, 總盈虧 ${pnl:,.2f}, 勝率 {win_count/len(date_trades)*100:.0f}%"
            
            # 如果有指定標的，加強標的資訊
            if request.symbol:
                symbol_trades = [t for t in date_trades if t['symbol'] == request.symbol]
                if symbol_trades:
                    sym_pnl = sum(t.get('realized_pnl', 0) for t in symbol_trades)
                    context += f"\n標的 {request.symbol} 表現: {len(symbol_trades)} 筆, 盈虧 ${sym_pnl:,.2f}"
            
            # 列出主要交易標的
            symbols = set(t['symbol'] for t in date_trades)
            context += f"\n交易標的: {', '.join(symbols)}"
        else:
            context = "當日無交易記錄。"

        prompt = f"""你是一位交易員的 AI 助手。請根據以下資訊，為一份 '{request.note_type}' 類型的交易日誌寫一個草稿。
日期: {request.date}
標的: {request.symbol or '不限'}
背景資訊:
{context}

請用第一人稱撰寫，包含：
1. 今日市場觀察或交易情緒
2. 表現檢討 (如果有交易)
3. 明日計畫或改進點

請用繁體中文，語氣專業但人性化（可以使用 emoji）。直接輸出日誌內容，不要包含 Markdown 標題（如 # 日誌），因為前端已有標題欄位。"""
    
        response = coach.chat(prompt)
        return {"draft": response}
    except Exception as e:
        logger.error(f"Error generating note draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交易計劃 ==========

class TradePlanRequest(BaseModel):
    symbol: str
    direction: str = 'long'  # 'long' or 'short'
    entry_trigger: Optional[str] = None
    entry_price_min: Optional[float] = None
    entry_price_max: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    position_size: Optional[str] = None
    max_risk_amount: Optional[float] = None
    thesis: Optional[str] = None
    market_condition: Optional[str] = None
    key_levels: Optional[str] = None
    valid_until: Optional[str] = None


class TradePlanUpdateRequest(BaseModel):
    status: Optional[str] = None
    execution_notes: Optional[str] = None
    actual_entry_price: Optional[float] = None
    actual_exit_price: Optional[float] = None
    ai_review: Optional[str] = None
    ai_post_analysis: Optional[str] = None


@app.get("/api/plans")
async def get_trade_plans(status: Optional[str] = None, symbol: Optional[str] = None):
    """取得交易計劃列表"""
    try:
        db.init_trade_plans_table()
        plans = db.get_trade_plans(status=status, symbol=symbol)
        return {"plans": plans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plans/{plan_id}")
async def get_trade_plan(plan_id: int):
    """取得單一交易計劃"""
    try:
        db.init_trade_plans_table()
        plan = db.get_trade_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"plan": plan}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plans")
async def create_trade_plan(request: TradePlanRequest):
    """新增交易計劃"""
    try:
        db.init_trade_plans_table()
        plan_id = db.add_trade_plan(request.model_dump())
        return {"plan_id": plan_id, "message": "Trade plan created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/plans/{plan_id}")
async def update_trade_plan(plan_id: int, request: TradePlanUpdateRequest):
    """更新交易計劃"""
    try:
        db.init_trade_plans_table()
        data = {k: v for k, v in request.model_dump().items() if v is not None}
        success = db.update_trade_plan(plan_id, data)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Plan updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/plans/{plan_id}")
async def delete_trade_plan(plan_id: int):
    """刪除交易計劃"""
    try:
        db.init_trade_plans_table()
        success = db.delete_trade_plan(plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Plan deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AIGeneratePlanRequest(BaseModel):
    symbol: str
    direction: str = 'long'  # 'long' or 'short'


@app.post("/api/plans/ai-generate")
async def generate_ai_trade_plan(request: AIGeneratePlanRequest):
    """
    AI 自動生成交易計劃
    根據當前倉位和 K 線圖數據，生成具體的進出場建議
    """
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        from utils.ai_context_builder import AIContextBuilder
        
        context_builder = AIContextBuilder(db)
        
        # 取得標的上下文
        symbol_context = context_builder.build_symbol_context(
            symbol=request.symbol,
            include_positions=True,
            include_chart=True,
            lookback_days=30
        )
        
        prompt = f"""你是一位專業的交易策略師。請根據以下數據為 {request.symbol} 生成一個完整的交易計劃。

{symbol_context}

**交易方向**: {request.direction}

請生成以下格式的 JSON 回應（只輸出 JSON，不要其他文字）：
```json
{{
    "symbol": "{request.symbol}",
    "direction": "{request.direction}",
    "entry_trigger": "進場觸發條件描述",
    "entry_price_min": 數字,
    "entry_price_max": 數字,
    "target_price": 數字,
    "stop_loss_price": 數字,
    "position_size": "建議部位大小（如：總資金的 5%）",
    "thesis": "交易論點和理由",
    "market_condition": "當前市場環境描述"
}}
```

生成建議時請考慮：
1. 進場價位應在合理的支撐/阻力區間
2. 停損應基於 ATR 設定（建議 1.5-2 倍 ATR）
3. 目標價應有合理的風險報酬比（至少 2:1）
4. 考慮當前趨勢和倉位情況"""

        response = coach.chat(prompt)
        
        # 解析 JSON
        import json
        import re
        
        # 嘗試從回應中提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                plan_data = json.loads(json_match.group())
                return {"plan": plan_data, "raw_response": response}
            except json.JSONDecodeError:
                pass
        
        # 如果無法解析，返回原始回應
        return {"plan": None, "raw_response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plans/{plan_id}/link-trade")
async def link_plan_to_trade(plan_id: int, trade_id: str, actual_entry: float, actual_exit: Optional[float] = None):
    """將交易計劃連結到實際交易"""
    try:
        db.init_trade_plans_table()
        success = db.link_plan_to_trade(plan_id, trade_id, actual_entry, actual_exit)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Plan linked to trade"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plans/{plan_id}/ai-review")
async def get_plan_ai_review(plan_id: int):
    """取得 AI 對交易計劃的評價（包含倉位和 K 線圖上下文）"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        db.init_trade_plans_table()
        plan = db.get_trade_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # 使用 AIContextBuilder 建構完整上下文
        from utils.ai_context_builder import AIContextBuilder
        context_builder = AIContextBuilder(db)
        
        # 取得標的相關上下文（倉位 + K 線圖）
        symbol_context = context_builder.build_symbol_context(
            symbol=plan['symbol'],
            include_positions=True,
            include_chart=True,
            include_gamma=False,  # 未來啟用
            lookback_days=30
        )
        
        prompt = f"""你是一位專業的交易計劃審核者，請評估以下交易計劃。

## 交易計劃詳情
- **標的**: {plan['symbol']}
- **方向**: {plan['direction']}
- **進場觸發條件**: {plan.get('entry_trigger') or '未設定'}
- **進場價格區間**: ${plan.get('entry_price_min') or 'N/A'} - ${plan.get('entry_price_max') or 'N/A'}
- **目標價**: ${plan.get('target_price') or 'N/A'}
- **停損價**: ${plan.get('stop_loss_price') or 'N/A'}
- **風險報酬比**: {plan.get('risk_reward_ratio') or 'N/A'}
- **部位大小**: {plan.get('position_size') or '未設定'}
- **最大風險金額**: ${plan.get('max_risk_amount') or 'N/A'}

### 交易論點
{plan.get('thesis') or '未提供'}

### 市場環境
{plan.get('market_condition') or '未提供'}

{symbol_context}

請提供：
1. **計劃評分** (1-10 分)：整體計劃的完整性和可行性
2. **與現有倉位的關係**：這個計劃如何影響你的整體風險暴露？是加碼、新建還是避險？
3. **進場時機評估**：根據 K 線圖數據，當前價位是否適合進場？
4. **具體價位建議**：
   - 建議進場價位（根據支撐阻力）
   - 建議停損價位（根據 ATR）
   - 建議目標價位（根據阻力位）
5. **風險提醒**：可能被忽略的風險
6. **執行建議**：進入交易時應注意什麼

請用繁體中文回答，使用 Markdown 格式。"""

        response = coach.chat(prompt)
        
        # 儲存 AI 評價
        db.update_trade_plan(plan_id, {'ai_review': response})
        
        return {"review": response}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plans/{plan_id}/ai-post-analysis")
async def get_plan_post_analysis(plan_id: int):
    """取得 AI 對已執行計劃的事後分析"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        db.init_trade_plans_table()
        plan = db.get_trade_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        if plan['status'] != 'executed':
            raise HTTPException(status_code=400, detail="Plan not executed yet")
        
        prompt = f"""你是一位專業的交易教練，請對比這筆交易的「計劃」與「實際執行」，進行事後分析：

## 計劃 vs 實際
- **標的**: {plan['symbol']}
- **計劃進場價**: ${plan.get('entry_price_min') or plan.get('entry_price_max') or 'N/A'}
- **實際進場價**: ${plan.get('actual_entry_price') or 'N/A'}
- **價格偏差**: {plan.get('plan_vs_actual_diff') or 'N/A'}%
- **計劃目標價**: ${plan.get('target_price') or 'N/A'}
- **計劃停損價**: ${plan.get('stop_loss_price') or 'N/A'}
- **實際出場價**: ${plan.get('actual_exit_price') or '尚未出場'}

### 原始交易論點
{plan.get('thesis') or '未提供'}

### 執行備註
{plan.get('execution_notes') or '未提供'}

請分析：
1. **計劃遵循度**：是否按照計劃執行？偏差原因是什麼？
2. **進場時機評估**：進場時機是否正確？
3. **出場時機評估**：（如果已出場）是否按計劃出場？
4. **可以改進的地方**：下次遇到類似情況應該怎麼做？
5. **關鍵教訓**：從這筆交易學到什麼？

請用繁體中文回答，使用 Markdown 格式。"""

        response = coach.chat(prompt)
        
        # 儲存事後分析
        db.update_trade_plan(plan_id, {'ai_post_analysis': response})
        
        return {"analysis": response}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交易日誌筆記 ==========

class TradeNoteRequest(BaseModel):
    note_type: str = 'misc'  # 'daily', 'trade', 'weekly', 'monthly', 'misc'
    date: str
    symbol: Optional[str] = None
    trade_id: Optional[str] = None
    plan_id: Optional[int] = None
    title: Optional[str] = None
    content: str
    mood: Optional[str] = None
    confidence_level: Optional[int] = None
    market_sentiment: Optional[str] = None
    key_observations: Optional[List[str]] = None
    lessons_learned: Optional[str] = None
    action_items: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None


class TradeNoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    confidence_level: Optional[int] = None
    key_observations: Optional[List[str]] = None
    lessons_learned: Optional[str] = None
    action_items: Optional[List[str]] = None
    tags: Optional[List[str]] = None


@app.get("/api/notes")
async def get_trade_notes(
    note_type: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """取得交易日誌筆記列表"""
    try:
        db.init_trade_notes_table()
        notes = db.get_trade_notes(
            note_type=note_type,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {"notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/{note_id}")
async def get_trade_note(note_id: int):
    """取得單一交易日誌筆記"""
    try:
        db.init_trade_notes_table()
        note = db.get_trade_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"note": note}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes")
async def create_trade_note(request: TradeNoteRequest):
    """新增交易日誌筆記"""
    try:
        db.init_trade_notes_table()
        note_id = db.add_trade_note(request.model_dump())
        return {"note_id": note_id, "message": "Note created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AIGenerateNoteRequest(BaseModel):
    note_type: str = 'daily'  # 'daily', 'trade', 'weekly', 'monthly', 'misc'
    date: str
    symbol: Optional[str] = None


@app.post("/api/notes/ai-generate")
async def generate_ai_trade_note(request: AIGenerateNoteRequest):
    """
    AI 自動生成日誌筆記
    根據當前倉位、K 線圖和最近交易生成完整的日誌內容
    """
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        from utils.ai_context_builder import AIContextBuilder
        from datetime import datetime
        
        context_builder = AIContextBuilder(db)
        
        # 投資組合上下文
        portfolio_context = context_builder.get_portfolio_summary()
        
        # 如果有指定標的，取得該標的的 K 線圖
        symbol_context = ""
        if request.symbol:
            symbol_context = context_builder.build_symbol_context(
                symbol=request.symbol,
                include_positions=True,
                include_chart=True,
                lookback_days=14
            )
        
        # 取得當天相關交易
        trades = db.get_trades()
        today_trades = [t for t in trades if t.get('datetime', '').startswith(request.date)]
        
        trades_context = ""
        if today_trades:
            trades_context = f"\n## 今日交易記錄\n"
            total_pnl = 0
            for t in today_trades:
                pnl = t.get('realized_pnl', 0) or 0
                total_pnl += pnl
                trades_context += f"- {t['symbol']}: {t['action']} {t['quantity']} @ ${t['price']:.2f}"
                if pnl != 0:
                    trades_context += f" (盈虧: ${pnl:+,.2f})"
                trades_context += "\n"
            trades_context += f"\n**今日總盈虧**: ${total_pnl:+,.2f}\n"
        
        # 根據筆記類型生成不同內容
        if request.note_type == 'daily':
            note_prompt = "每日交易日誌"
            content_guide = """包含：
1. 今日市場觀察
2. 交易回顧（如果有交易）
3. 執行紀律評估
4. 情緒狀態
5. 明日計劃"""
        elif request.note_type == 'trade':
            note_prompt = f"交易記錄筆記（{request.symbol or '標的'}）"
            content_guide = """包含：
1. 交易動機
2. 進出場執行評估
3. 學到的教訓
4. 下次可以改進的地方"""
        elif request.note_type == 'weekly':
            note_prompt = "週回顧"
            content_guide = """包含：
1. 本週績效總結
2. 最佳/最差交易
3. 執行紀律評分
4. 下週重點"""
        else:
            note_prompt = "交易筆記"
            content_guide = "包含重要觀察和學習心得"
        
        prompt = f"""你是一位交易員的 AI 助手，請幫忙撰寫一份 {note_prompt}。

日期: {request.date}
標的: {request.symbol or '不限'}

{portfolio_context}

{symbol_context}

{trades_context}

請生成以下格式的 JSON 回應（只輸出 JSON，不要其他文字）：
```json
{{
    "title": "筆記標題",
    "content": "完整內容（使用 Markdown 格式，{content_guide}）",
    "mood": "情緒狀態（如：confident/cautious/frustrated/calm/excited）",
    "confidence_level": 數字(1-10),
    "market_sentiment": "市場情緒描述",
    "key_observations": ["觀察1", "觀察2"],
    "lessons_learned": "今日學到的教訓",
    "action_items": ["待辦1", "待辦2"]
}}
```

請用第一人稱撰寫，語氣專業但人性化，可適度使用 emoji。"""

        response = coach.chat(prompt)
        
        # 解析 JSON
        import json
        import re
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                note_data = json.loads(json_match.group())
                # 添加日期和類型
                note_data['date'] = request.date
                note_data['note_type'] = request.note_type
                if request.symbol:
                    note_data['symbol'] = request.symbol
                return {"note": note_data, "raw_response": response}
            except json.JSONDecodeError:
                pass
        
        return {"note": None, "raw_response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/notes/{note_id}")
async def update_trade_note(note_id: int, request: TradeNoteUpdateRequest):
    """更新交易日誌筆記"""
    try:
        db.init_trade_notes_table()
        data = {k: v for k, v in request.model_dump().items() if v is not None}
        success = db.update_trade_note(note_id, data)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"message": "Note updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/notes/{note_id}")
async def delete_trade_note(note_id: int):
    """刪除交易日誌筆記"""
    try:
        db.init_trade_notes_table()
        success = db.delete_trade_note(note_id)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"message": "Note deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/daily-summary/{date}")
async def get_daily_summary(date: str):
    """取得某日的完整摘要"""
    try:
        db.init_trade_notes_table()
        db.init_trade_plans_table()
        summary = db.get_daily_summary(date)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/{note_id}/ai-analyze")
async def analyze_note_with_ai(note_id: int):
    """AI 分析筆記並給出建議"""
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        db.init_trade_notes_table()
        note = db.get_trade_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        
        # 取得相關交易數據
        related_context = ""
        if note.get('symbol'):
            trades = db.get_trades()
            symbol_trades = [t for t in trades if t['symbol'] == note['symbol']]
            if symbol_trades:
                total_pnl = sum(t.get('realized_pnl', 0) for t in symbol_trades)
                related_context = f"\n相關標的 {note['symbol']} 總盈虧: ${total_pnl:,.2f}"
        
        prompt = f"""你是一位專業的交易教練，請分析以下交易日誌並給出建議：

## 日誌資訊
- **類型**: {note['note_type']}
- **日期**: {note['date']}
- **標的**: {note.get('symbol') or 'N/A'}
- **標題**: {note.get('title') or 'N/A'}
- **情緒狀態**: {note.get('mood') or 'N/A'}
- **信心水平**: {note.get('confidence_level') or 'N/A'}/10
- **市場情緒**: {note.get('market_sentiment') or 'N/A'}

### 內容
{note['content']}

### 重要觀察
{note.get('key_observations') or 'N/A'}

### 學到的教訓
{note.get('lessons_learned') or 'N/A'}
{related_context}

請提供：
1. **情緒分析**：從這篇日誌中識別交易者的心理狀態
2. **行為模式**：是否有需要注意的交易行為模式？
3. **改進建議**：基於這篇日誌，給出 2-3 個具體可行的改進建議
4. **正向肯定**：這篇日誌中做得好的地方
5. **後續行動**：建議接下來應該做什麼

請用繁體中文回答，使用 Markdown 格式。保持鼓勵但誠實的語氣。"""

        response = coach.chat(prompt)
        
        # 更新筆記的 AI 建議
        db.update_trade_note(note_id, {
            'ai_summary': response[:500] if len(response) > 500 else response,
            'ai_suggestions': response
        })
        
        return {"analysis": response}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/comprehensive-review")
async def get_comprehensive_ai_review():
    """
    AI 綜合審查：整合 MFE/MAE、交易計劃、日誌筆記、當前倉位和 K 線圖進行全面分析
    """
    coach = get_ai_coach()
    if not coach:
        raise HTTPException(status_code=503, detail="AI 服務未設定")
    
    try:
        from utils.mfe_mae_calculator import MFEMAECalculator
        from utils.ai_context_builder import AIContextBuilder
        
        # 初始化表格
        db.init_mfe_mae_table()
        db.init_trade_plans_table()
        db.init_trade_notes_table()
        
        # 建構 AI 上下文
        context_builder = AIContextBuilder(db)
        
        # 收集 MFE/MAE 數據
        mfe_context = ""
        try:
            calculator = MFEMAECalculator(db)
            mfe_context = calculator.generate_ai_context()
        except Exception:
            mfe_context = "MFE/MAE 數據暫無"
        
        # 投資組合上下文（倉位）
        portfolio_context = context_builder.get_portfolio_summary()
        
        # 主要持倉的 K 線圖分析
        positions = db.get_latest_positions()
        chart_contexts = []
        if positions:
            from utils.derivatives_support import InstrumentParser
            parser = InstrumentParser()
            
            # 取得不重複的 underlying
            underlyings = set()
            for pos in positions:
                parsed = parser.parse_symbol(pos.get('symbol', ''))
                underlying = parsed.get('underlying', pos.get('symbol', ''))
                if underlying:
                    underlyings.add(underlying.upper())
            
            # 只取前 3 個主要持倉的 K 線圖
            for symbol in list(underlyings)[:3]:
                chart_ctx = context_builder.build_symbol_context(
                    symbol=symbol,
                    include_positions=False,  # 已經有 portfolio_context
                    include_chart=True,
                    lookback_days=30
                )
                if chart_ctx:
                    chart_contexts.append(chart_ctx)
        
        chart_context = "\n\n".join(chart_contexts) if chart_contexts else ""
        
        # 交易計劃統計
        all_plans = db.get_trade_plans()
        pending_plans = [p for p in all_plans if p.get('status') == 'pending']
        executed_plans = [p for p in all_plans if p.get('status') == 'executed']
        
        plans_context = f"""## 交易計劃統計
- 總計劃數: {len(all_plans)}
- 待執行: {len(pending_plans)}
- 已執行: {len(executed_plans)}
"""
        if pending_plans:
            plans_context += "\n### 待執行計劃\n"
            for p in pending_plans[:3]:
                plans_context += f"- {p['symbol']} ({p['direction']}): 進場 ${p.get('entry_price_min') or 'N/A'}-${p.get('entry_price_max') or 'N/A'}\n"
        
        if executed_plans:
            avg_diff = sum(p.get('plan_vs_actual_diff', 0) or 0 for p in executed_plans) / len(executed_plans)
            plans_context += f"- 平均計劃偏差: {avg_diff:.1f}%\n"
        
        # 最近筆記
        recent_notes = db.get_trade_notes(limit=5)
        notes_context = "\n## 最近日誌摘要\n"
        for note in recent_notes:
            notes_context += f"- [{note['date']}] {note.get('title') or note['content'][:50]}...\n"
            if note.get('mood'):
                notes_context += f"  情緒: {note['mood']}\n"
        
        # 交易統計
        stats = db.get_trade_statistics()
        stats_context = f"""## 交易績效
- 總交易: {stats.get('total_trades', 0)} 筆
- 勝率: {stats.get('win_rate', 0):.1f}%
- 獲利因子: {stats.get('profit_factor', 0):.2f}
- 總盈虧: ${stats.get('total_pnl', 0):,.2f}
"""
        
        prompt = f"""你是一位資深的交易教練，請根據以下數據對交易者進行全面評估。

{portfolio_context}

{chart_context}

{mfe_context}

{plans_context}

{notes_context}

{stats_context}

請提供全面的分析報告，包含：

## 1. 當前倉位風險評估
根據 K 線圖和倉位數據：
- 目前市場趨勢判斷
- 各持倉的風險暴露程度
- 是否有需要立即調整的倉位？

## 2. 整體表現評估
評估交易者在以下維度的表現（每項 1-10 分）：
- 執行紀律
- 風險管理
- 情緒控制
- 計劃遵循度
- 獲利能力

## 3. 主要問題識別
列出最需要改進的 3 個問題

## 4. 具體操作建議
針對當前持倉，給出具體的操作建議：
- 哪些可以加碼？
- 哪些應該減碼？
- 停損點位建議

## 5. 本週/本月行動計劃
建議接下來應該專注的 2-3 個重點

## 6. 正向鼓勵
肯定做得好的地方，保持動力

請用繁體中文回答，使用 Markdown 格式。語氣要專業但友善。"""

        # 使用 Thinking Model 進行深度分析
        response = coach.analyze(prompt)
        return {"review": response}
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


# ========== 交易檢討：K 線圖 + 買賣點 ==========

class ChartDataResponse(BaseModel):
    """K 線圖數據 + 買賣點"""
    symbol: str
    ohlc: List[Dict[str, Any]]
    trades: List[Dict[str, Any]]
    summary: Dict[str, Any]


@app.get("/api/review/chart/{underlying}")
async def get_review_chart_data(underlying: str, period: str = "1y"):
    """
    獲取交易檢討用的 K 線圖數據和買賣點
    
    - 下載該股票的歷史 K 線數據
    - 合併該 underlying 的所有交易（股票+選擇權）
    - 返回 AI 需要的完整上下文
    """
    try:
        import yfinance as yf
        from datetime import datetime as dt
        parser = InstrumentParser()
        
        # 日期格式化輔助函數
        def format_date(date_val) -> str:
            """確保日期格式為 yyyy-mm-dd"""
            if date_val is None:
                return ""
            if isinstance(date_val, str):
                # 如果是 yyyymmdd 格式
                if len(date_val) == 8 and date_val.isdigit():
                    return f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}"
                # 如果已經是 yyyy-mm-dd 格式
                if len(date_val) >= 10 and date_val[4] == '-':
                    return date_val[:10]
                # 如果包含 T (ISO 格式)
                if 'T' in date_val:
                    return date_val.split('T')[0]
                # 其他格式嘗試解析
                try:
                    parsed_date = dt.fromisoformat(date_val.replace('Z', '+00:00'))
                    return parsed_date.strftime('%Y-%m-%d')
                except:
                    return date_val[:10] if len(date_val) >= 10 else date_val
            # 如果是 datetime 對象
            try:
                return date_val.strftime('%Y-%m-%d')
            except:
                return str(date_val)[:10]
        
        # 1. 獲取 K 線數據（緩存優先，增量更新）
        from datetime import datetime as dt, timedelta
        
        # 檢查緩存中最新的日期
        cached_latest = db.get_ohlc_latest_date(underlying)
        today = dt.now().strftime('%Y-%m-%d')
        
        # 從緩存讀取數據
        cached_data = db.get_ohlc_cache(underlying)
        
        # 決定是否需要從網絡下載
        need_download = False
        download_start = None
        
        if not cached_data:
            # 緩存為空，需要下載全部
            need_download = True
        elif cached_latest and cached_latest < today:
            # 緩存不是最新的，需要增量更新
            need_download = True
            # 從緩存最新日期的次日開始下載
            latest_date = dt.strptime(cached_latest, '%Y-%m-%d')
            download_start = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        if need_download:
            # 處理特殊的 symbol (指數需要加上 ^ 前綴)
            yf_symbol = underlying
            index_symbols = ['VIX', 'SPX', 'NDX', 'DJI', 'RUT', 'IXIC', 'GSPC']
            if underlying.upper() in index_symbols:
                yf_symbol = f'^{underlying.upper()}'
            elif underlying.upper().startswith('VIX'):
                # VIX 相關產品
                yf_symbol = f'^VIX'
            
            ticker = yf.Ticker(yf_symbol)
            
            if download_start:
                # 增量下載（只下載新數據）
                hist = ticker.history(start=download_start)
            else:
                # 全量下載
                hist = ticker.history(period=period)
            
            if not hist.empty:
                new_ohlc = []
                for idx, row in hist.iterrows():
                    new_ohlc.append({
                        "date": idx.strftime('%Y-%m-%d'),
                        "open": round(row['Open'], 2),
                        "high": round(row['High'], 2),
                        "low": round(row['Low'], 2),
                        "close": round(row['Close'], 2),
                        "volume": int(row['Volume'])
                    })
                
                # 保存到緩存
                if new_ohlc:
                    db.save_ohlc_data(underlying, new_ohlc)
                    # 重新讀取完整緩存
                    cached_data = db.get_ohlc_cache(underlying)
        
        # 使用緩存數據
        ohlc_data = cached_data if cached_data else []
        
        if not ohlc_data:
            raise HTTPException(status_code=404, detail=f"No data found for {underlying}")
        
        # 2. 獲取該 underlying 的所有交易（股票 + 選擇權）
        all_trades = db.get_trades()
        underlying_trades = []
        total_realized_pnl = 0
        stock_trades = []
        option_trades = []
        
        for t in all_trades:
            parsed = parser.parse_symbol(t['symbol'])
            if parsed['underlying'].upper() == underlying.upper():
                trade_date = format_date(t.get('datetime') or t.get('date'))
                trade_info = {
                    "date": trade_date,
                    "datetime": str(t.get('datetime', '')),
                    "symbol": t['symbol'],
                    "action": t['action'],
                    "quantity": t['quantity'],
                    "price": t['price'],
                    "realized_pnl": t.get('realized_pnl', 0),
                    "instrument_type": parsed.get('instrument_type', 'stock'),
                    "is_option": parsed.get('instrument_type') == 'option',
                    "strike": parsed.get('strike'),
                    "expiry": parsed.get('expiry'),
                    "option_type": parsed.get('option_type')
                }
                underlying_trades.append(trade_info)
                total_realized_pnl += t.get('realized_pnl', 0)
                
                if parsed.get('instrument_type') == 'option':
                    option_trades.append(trade_info)
                else:
                    stock_trades.append(trade_info)
        
        # 3. 計算摘要統計
        buy_trades = [t for t in underlying_trades if t['action'].upper() in ['BUY', 'BOT']]
        sell_trades = [t for t in underlying_trades if t['action'].upper() in ['SELL', 'SLD']]
        
        summary = {
            "underlying": underlying,
            "current_price": round(hist['Close'].iloc[-1], 2) if len(hist) > 0 else 0,
            "total_trades": len(underlying_trades),
            "stock_trades": len(stock_trades),
            "option_trades": len(option_trades),
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "avg_buy_price": round(sum(t['price'] for t in buy_trades) / len(buy_trades), 2) if buy_trades else 0,
            "avg_sell_price": round(sum(t['price'] for t in sell_trades) / len(sell_trades), 2) if sell_trades else 0,
        }
        
        return {
            "symbol": underlying,
            "ohlc": ohlc_data,
            "trades": underlying_trades,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/symbols/grouped")
async def get_grouped_symbols():
    """
    獲取按 underlying 分組的標的清單
    合併同一 underlying 的股票和選擇權
    """
    parser = InstrumentParser()
    trades = db.get_trades()
    
    underlying_stats = {}
    
    for t in trades:
        parsed = parser.parse_symbol(t['symbol'])
        underlying = parsed['underlying']
        
        if underlying not in underlying_stats:
            underlying_stats[underlying] = {
                "underlying": underlying,
                "stock_trades": 0,
                "option_trades": 0,
                "total_pnl": 0,
                "symbols": set()
            }
        
        underlying_stats[underlying]['symbols'].add(t['symbol'])
        underlying_stats[underlying]['total_pnl'] += t.get('realized_pnl', 0)
        
        if parsed.get('instrument_type') == 'option':
            underlying_stats[underlying]['option_trades'] += 1
        else:
            underlying_stats[underlying]['stock_trades'] += 1
    
    # 轉換 set 為 list，排序
    result = []
    for underlying, stats in underlying_stats.items():
        result.append({
            "underlying": underlying,
            "stock_trades": stats['stock_trades'],
            "option_trades": stats['option_trades'],
            "total_pnl": round(stats['total_pnl'], 2),
            "symbols": sorted(list(stats['symbols']))
        })
    
    # 按交易數量排序
    result.sort(key=lambda x: x['stock_trades'] + x['option_trades'], reverse=True)
    
    return result




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
