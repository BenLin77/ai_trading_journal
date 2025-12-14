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
from utils.option_strategies import OptionStrategyDetector, StrategyType, get_strategy_risk_level
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

# AI 教練實例（延遲初始化，從資料庫讀取設定）
ai_coach = None

def get_ai_coach():
    """取得 AI 教練實例（從資料庫讀取 API Key）"""
    global ai_coach
    
    # 從資料庫讀取設定
    gemini_key = db.get_setting('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
    deepseek_key = db.get_setting('DEEPSEEK_API_KEY') or os.getenv('DEEPSEEK_API_KEY')
    ai_provider = db.get_setting('AI_PROVIDER') or os.getenv('AI_PROVIDER', 'gemini')
    
    if not gemini_key and not deepseek_key:
        return None
    
    try:
        if ai_provider == 'deepseek' and deepseek_key:
            ai_coach = AICoach(api_key=deepseek_key, provider='deepseek')
        elif gemini_key:
            ai_coach = AICoach(api_key=gemini_key, provider='gemini')
        return ai_coach
    except Exception as e:
        print(f"AI Coach 初始化失敗: {e}")
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
        # 合併邏輯：以 positions_raw (IBKR Snapshot) 為主，補全 calculated_positions 中有但 positions_raw 沒有的 symbol
        snapshot_symbols = set(p.get('symbol', '') for p in positions_raw)
        
        for calc_pos in calculated_positions:
            symbol = calc_pos.get('symbol', '')
            # 如果 Snapshot 裡沒有這個 symbol，且計算出的持倉不為 0，則加入
            if symbol and symbol not in snapshot_symbols and calc_pos.get('position', 0) != 0:
                # 標記為來自計算
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
    try:
        flex = IBKRFlexQuery(
            token=_get_config('IBKR_FLEX_TOKEN', ''),
            history_query_id=_get_config('IBKR_HISTORY_QUERY_ID', ''),
            positions_query_id=_get_config('IBKR_POSITIONS_QUERY_ID', ''),
        )
        result = flex.sync_to_database(db)

        # 同步現金快照（寫入 DB；portfolio 只讀 DB）
        try:
            cash_data = flex.get_cash_balance(query_id=_get_config('IBKR_HISTORY_QUERY_ID', ''))
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
            ticker = yf.Ticker(underlying)
            
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
