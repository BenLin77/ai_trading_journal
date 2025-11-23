"""
SQLite 資料庫管理模組

此模組負責：
1. 初始化資料庫和資料表
2. 管理交易紀錄 (Trades)
3. 管理交易日誌 (Journal)
4. 管理 AI 對話紀錄 (Chat_History)
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
import hashlib


class TradingDatabase:
    """交易日誌資料庫管理類"""

    def __init__(self, db_path: str = "trading_journal.db"):
        """
        初始化資料庫連接

        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = db_path
        self.init_database()
        self.init_backtest_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """取得資料庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 讓查詢結果可以用欄位名稱存取
        return conn

    def init_database(self):
        """初始化資料庫結構"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 建立 Trades 表（支援股票、選擇權、期貨）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                datetime TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                commission REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                notes TEXT,
                instrument_type TEXT DEFAULT 'stock',
                strike REAL,
                expiry TEXT,
                option_type TEXT,
                multiplier INTEGER DEFAULT 1,
                underlying TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立 Journal 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                thesis TEXT,
                mood TEXT,
                key_takeaway TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立 Chat_History 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立索引以提升查詢效能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol
            ON trades(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_datetime
            ON trades(datetime)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_session
            ON chat_history(session_id)
        """)

        # 建立 Mistakes 表（錯誤卡片）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                mistake_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                error_type TEXT NOT NULL,
                description TEXT,
                pnl REAL,
                ai_analysis TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
            )
        """)

        conn.commit()
        conn.close()

    def generate_trade_id(self, trade_data: Dict[str, Any]) -> str:
        """
        生成唯一的交易 ID

        使用交易的關鍵欄位生成 hash，確保相同交易不會重複匯入

        Args:
            trade_data: 交易數據字典

        Returns:
            唯一的交易 ID
        """
        key_string = f"{trade_data['datetime']}_{trade_data['symbol']}_{trade_data['action']}_{trade_data['quantity']}_{trade_data['price']}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def add_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        新增交易紀錄（避免重複）

        Args:
            trade_data: 交易數據，應包含 datetime, symbol, action, quantity, price 等欄位

        Returns:
            True 如果成功新增，False 如果交易已存在
        """
        trade_id = self.generate_trade_id(trade_data)

        conn = self._get_connection()
        cursor = conn.cursor()

        # 檢查是否已存在
        cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade_id,))
        if cursor.fetchone():
            conn.close()
            return False

        # 插入新交易（包含選擇權/期貨欄位）
        cursor.execute("""
            INSERT INTO trades
            (trade_id, datetime, symbol, action, quantity, price, commission, realized_pnl, notes,
             instrument_type, strike, expiry, option_type, multiplier, underlying)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id,
            trade_data.get('datetime'),
            trade_data.get('symbol'),
            trade_data.get('action'),
            trade_data.get('quantity'),
            trade_data.get('price'),
            trade_data.get('commission', 0),
            trade_data.get('realized_pnl', 0),
            trade_data.get('notes', ''),
            trade_data.get('instrument_type', 'stock'),
            trade_data.get('strike'),
            trade_data.get('expiry'),
            trade_data.get('option_type'),
            trade_data.get('multiplier', 1),
            trade_data.get('underlying')
        ))

        conn.commit()
        conn.close()
        return True

    def get_trades(self,
                   symbol: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查詢交易紀錄

        Args:
            symbol: 標的代號（可選）
            start_date: 開始日期（可選）
            end_date: 結束日期（可選）

        Returns:
            交易紀錄列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND datetime >= ?"
            params.append(start_date)

        if end_date:
            query += " AND datetime <= ?"
            params.append(end_date)

        query += " ORDER BY datetime"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_symbols(self) -> List[str]:
        """
        取得所有交易過的標的代號

        Returns:
            標的代號列表（已排序且去重）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM trades ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        return symbols

    def add_journal_entry(self,
                          trade_date: str,
                          symbol: str,
                          thesis: str = "",
                          mood: str = "",
                          key_takeaway: str = "") -> int:
        """
        新增交易日誌

        Args:
            trade_date: 交易日期
            symbol: 標的代號
            thesis: 交易論點
            mood: 當時心情
            key_takeaway: 關鍵教訓

        Returns:
            新增的日誌 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO journal (trade_date, symbol, thesis, mood, key_takeaway)
            VALUES (?, ?, ?, ?, ?)
        """, (trade_date, symbol, thesis, mood, key_takeaway))

        journal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return journal_id

    def get_journal_entries(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查詢交易日誌

        Args:
            symbol: 標的代號（可選）

        Returns:
            日誌列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT * FROM journal
                WHERE symbol = ?
                ORDER BY trade_date DESC
            """, (symbol,))
        else:
            cursor.execute("SELECT * FROM journal ORDER BY trade_date DESC")

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_chat_message(self, session_id: str, role: str, content: str):
        """
        儲存 AI 對話訊息

        Args:
            session_id: 會話 ID
            role: 訊息角色（user 或 assistant）
            content: 訊息內容
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        取得特定會話的對話紀錄

        Args:
            session_id: 會話 ID

        Returns:
            對話紀錄列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_global_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        取得跨所有會話的最近對話紀錄（用於建立長期記憶）

        Args:
            limit: 限制回傳的訊息數量

        Returns:
            對話紀錄列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM (
                SELECT * FROM chat_history
                ORDER BY timestamp DESC
                LIMIT ?
            ) ORDER BY timestamp ASC
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_trade_statistics(self) -> Dict[str, Any]:
        """
        計算全局交易統計數據

        Returns:
            包含各項統計指標的字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 總盈虧
        cursor.execute("SELECT SUM(realized_pnl) as total_pnl FROM trades")
        total_pnl = cursor.fetchone()[0] or 0

        # 勝率計算
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as wins,
                COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losses,
                COUNT(*) as total_trades
            FROM trades
            WHERE realized_pnl != 0
        """)
        row = cursor.fetchone()
        wins = row[0] or 0
        losses = row[1] or 0
        total_trades = row[2] or 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # 平均獲利與虧損
        cursor.execute("""
            SELECT
                AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl END) as avg_win,
                AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl END) as avg_loss
            FROM trades
        """)
        row = cursor.fetchone()
        avg_win = row[0] or 0
        avg_loss = abs(row[1] or 0)

        # 獲利因子
        cursor.execute("""
            SELECT
                SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) as gross_profit,
                ABS(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END)) as gross_loss
            FROM trades
        """)
        row = cursor.fetchone()
        gross_profit = row[0] or 0
        gross_loss = row[1] or 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

        conn.close()

        return {
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses
        }

    def get_pnl_by_symbol(self) -> Dict[str, float]:
        """
        計算每個標的的總盈虧

        Returns:
            標的代號 -> 總盈虧的字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol, SUM(realized_pnl) as pnl
            FROM trades
            GROUP BY symbol
            ORDER BY pnl DESC
        """)

        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result

    def get_pnl_by_hour(self) -> Dict[int, float]:
        """
        計算每個時段的總盈虧（用於找出「魔鬼時刻」）

        Returns:
            小時 (0-23) -> 總盈虧的字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                CAST(strftime('%H', datetime) AS INTEGER) as hour,
                SUM(realized_pnl) as pnl
            FROM trades
            GROUP BY hour
            ORDER BY hour
        """)

        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result

    def add_mistake(self,
                    symbol: str,
                    date: str,
                    error_type: str,
                    description: str,
                    pnl: float = 0.0,
                    ai_analysis: str = "",
                    trade_id: Optional[str] = None) -> int:
        """
        新增錯誤卡片

        Args:
            symbol: 標的代號
            date: 交易日期
            error_type: 錯誤類型 (如 'FOMO', '凹單')
            description: 錯誤描述
            pnl: 損失金額 (負數)
            ai_analysis: AI 分析建議
            trade_id: 關聯的交易 ID

        Returns:
            新增的 mistake_id
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO mistakes
            (trade_id, symbol, date, error_type, description, pnl, ai_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade_id, symbol, date, error_type, description, pnl, ai_analysis))

        mistake_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return mistake_id

    def get_mistakes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        取得錯誤卡片列表

        Args:
            limit: 限制數量

        Returns:
            錯誤卡片列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM mistakes
            ORDER BY date DESC, created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_mistake_stats(self) -> Dict[str, int]:
        """
        取得錯誤類型統計

        Returns:
            錯誤類型 -> 次數 的字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT error_type, COUNT(*) as count
            FROM mistakes
            GROUP BY error_type
            ORDER BY count DESC
        """)

        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result

    def init_backtest_tables(self):
        """初始化回測相關資料表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 建立回測結果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                backtest_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                parameters TEXT,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                profit_factor REAL,
                total_trades INTEGER,
                total_return REAL,
                annual_return REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立策略對比表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_comparison (
                comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id TEXT NOT NULL,
                actual_trade_period TEXT,
                backtest_sharpe REAL,
                actual_sharpe REAL,
                performance_gap REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (backtest_id) REFERENCES backtest_results(backtest_id)
            )
        """)

        # 建立索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_backtest_symbol
            ON backtest_results(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_backtest_strategy
            ON backtest_results(strategy_name)
        """)

        conn.commit()
        conn.close()

    def add_backtest_result(self, backtest_data: Dict[str, Any]) -> str:
        """
        新增回測結果

        Args:
            backtest_data: 回測數據字典

        Returns:
            backtest_id
        """
        import hashlib
        from datetime import datetime

        # 生成唯一 ID
        key_string = f"{backtest_data['strategy_name']}_{backtest_data['symbol']}_{backtest_data['start_date']}_{datetime.now().isoformat()}"
        backtest_id = hashlib.md5(key_string.encode()).hexdigest()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO backtest_results
            (backtest_id, strategy_name, symbol, start_date, end_date, parameters,
             sharpe_ratio, sortino_ratio, max_drawdown, win_rate, profit_factor,
             total_trades, total_return, annual_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            backtest_id,
            backtest_data['strategy_name'],
            backtest_data['symbol'],
            backtest_data['start_date'],
            backtest_data['end_date'],
            str(backtest_data.get('parameters', {})),
            backtest_data.get('sharpe_ratio'),
            backtest_data.get('sortino_ratio'),
            backtest_data.get('max_drawdown'),
            backtest_data.get('win_rate'),
            backtest_data.get('profit_factor'),
            backtest_data.get('total_trades'),
            backtest_data.get('total_return'),
            backtest_data.get('annual_return')
        ))

        conn.commit()
        conn.close()
        return backtest_id

    def get_backtest_results(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查詢回測結果

        Args:
            symbol: 標的代號（可選）

        Returns:
            回測結果列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT * FROM backtest_results
                WHERE symbol = ?
                ORDER BY created_at DESC
            """, (symbol,))
        else:
            cursor.execute("SELECT * FROM backtest_results ORDER BY created_at DESC")

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
