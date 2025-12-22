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
        self.migrate_database()
        self.init_backtest_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """取得資料庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 讓查詢結果可以用欄位名稱存取
        return conn

    def migrate_database(self):
        """檢查並遷移資料庫架構"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 檢查 trades 表的欄位
        cursor.execute("PRAGMA table_info(trades)")
        columns = [row['name'] for row in cursor.fetchall()]

        # 定義新欄位及其類型
        new_columns = {
            'instrument_type': "TEXT DEFAULT 'stock'",
            'strike': "REAL",
            'expiry': "TEXT",
            'option_type': "TEXT",
            'multiplier': "INTEGER DEFAULT 1",
            'underlying': "TEXT"
        }

        for col_name, col_def in new_columns.items():
            if col_name not in columns:
                try:
                    print(f"Migrating database: Adding column {col_name} to trades table...")
                    cursor.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    print(f"Error adding column {col_name}: {e}")

        conn.commit()
        conn.close()

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

        # 建立 Open Positions 表（未平倉快照）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_positions (
                position_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                position REAL NOT NULL,
                mark_price REAL,
                average_cost REAL,
                unrealized_pnl REAL,
                instrument_type TEXT DEFAULT 'stock',
                underlying TEXT,
                strike REAL,
                expiry TEXT,
                option_type TEXT,
                multiplier INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, symbol)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_snapshots (
                snapshot_date TEXT PRIMARY KEY,
                total_cash REAL NOT NULL,
                total_settled_cash REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_snapshot
            ON open_positions(snapshot_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_symbol
            ON open_positions(symbol)
        """)

        # 建立 Settings 表（系統設定）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立 OHLC 緩存表（K 線數據緩存）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlc_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)

        # 建立索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlc_symbol
            ON ohlc_cache(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_date
            ON ohlc_cache(symbol, date)
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
        新增交易紀錄（避免重複，含驗證）

        Args:
            trade_data: 交易數據，應包含 datetime, symbol, action, quantity, price 等欄位

        Returns:
            True 如果成功新增，False 如果交易已存在或驗證失敗
        """
        import logging
        from utils.validators import TradeValidator

        # 1. 驗證並修正資料
        is_valid, errors = TradeValidator.validate_trade(trade_data)
        if not is_valid:
            logging.warning(f"Invalid trade data: {', '.join(errors[:3])}")  # 只記錄前 3 個錯誤
            # 嘗試自動修正
            trade_data = TradeValidator.auto_fix_trade(trade_data)

        # 2. 檢查重複
        trade_id = self.generate_trade_id(trade_data)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade_id,))
        if cursor.fetchone():
            conn.close()
            return False

        # 3. 插入新交易
        try:
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
            logging.info(f"Added trade: {trade_data.get('symbol')} @ {trade_data.get('datetime')}")
            return True

        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to add trade: {str(e)}")
            return False
        finally:
            conn.close()

    def get_trades(self,
                   symbol: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查詢交易紀錄

        Args:
            symbol: 標的代號（可選）
            start_date: 開始日期（可選，支援 YYYY-MM-DD 或 YYYYMMDD 格式）
            end_date: 結束日期（可選，支援 YYYY-MM-DD 或 YYYYMMDD 格式）

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
            # 標準化日期格式為 YYYYMMDD（使用統一工具）
            from utils.datetime_utils import normalize_date
            normalized_start = normalize_date(start_date)
            query += " AND datetime >= ?"
            params.append(normalized_start)

        if end_date:
            # 標準化日期格式為 YYYYMMDD（使用統一工具）
            from utils.datetime_utils import normalize_date
            normalized_end = normalize_date(end_date)
            query += " AND datetime <= ?"
            params.append(normalized_end)

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

    def update_trade_pnl(self, trade_id: str, realized_pnl: float):
        """
        更新交易的已實現盈虧

        Args:
            trade_id: 交易 ID
            realized_pnl: 已實現盈虧金額
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE trades
            SET realized_pnl = ?
            WHERE trade_id = ?
        """, (realized_pnl, trade_id))

        conn.commit()
        conn.close()

    def clear_database(self) -> bool:
        """清空所有交易資料"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trades")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False

    # ========== Open Positions 管理 ==========

    def upsert_open_positions(self, positions: List[Dict[str, Any]], snapshot_date: str = None) -> int:
        """
        更新或插入 Open Positions 快照（覆蓋模式）

        Args:
            positions: 持倉列表，每個元素包含 symbol, position, mark_price, average_cost, unrealized_pnl 等
            snapshot_date: 快照日期（YYYY-MM-DD），預設為今天

        Returns:
            成功插入的記錄數
        """
        from utils.derivatives_support import InstrumentParser

        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')

        conn = self._get_connection()
        cursor = conn.cursor()

        # 刪除舊的同日快照
        cursor.execute("DELETE FROM open_positions WHERE snapshot_date = ?", (snapshot_date,))

        inserted_count = 0
        for pos in positions:
            try:
                # 解析標的類型
                parsed = InstrumentParser.parse_symbol(pos.get('symbol', ''))

                cursor.execute("""
                    INSERT INTO open_positions
                    (snapshot_date, symbol, position, mark_price, average_cost, unrealized_pnl,
                     instrument_type, underlying, strike, expiry, option_type, multiplier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_date,
                    pos.get('symbol'),
                    pos.get('position', 0),
                    pos.get('mark_price'),
                    pos.get('average_cost'),
                    pos.get('unrealized_pnl', 0),
                    parsed.get('instrument_type', 'stock'),
                    pos.get('underlying') or parsed.get('underlying'),
                    pos.get('strike') if pos.get('strike') is not None else parsed.get('strike'),
                    pos.get('expiry') or parsed.get('expiry'),
                    pos.get('option_type') or parsed.get('option_type'),
                    int(pos.get('multiplier')) if pos.get('multiplier') else parsed.get('multiplier', 1)
                ))
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting position {pos.get('symbol')}: {e}")

        conn.commit()
        conn.close()
        return inserted_count

    def get_latest_positions(self) -> List[Dict[str, Any]]:
        """
        取得最新的 Open Positions 快照

        Returns:
            持倉列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 先找到最新的 snapshot_date
        cursor.execute("""
            SELECT MAX(snapshot_date) as latest_date
            FROM open_positions
        """)
        result = cursor.fetchone()
        latest_date = result['latest_date'] if result else None

        if not latest_date:
            conn.close()
            return []

        # 取得該日期的所有持倉
        cursor.execute("""
            SELECT * FROM open_positions
            WHERE snapshot_date = ?
            ORDER BY symbol
        """, (latest_date,))

        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return positions

    def upsert_cash_snapshot(
        self,
        total_cash: float,
        total_settled_cash: float,
        currency: str = 'USD',
        snapshot_date: str = None,
    ) -> None:
        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cash_snapshots (snapshot_date, total_cash, total_settled_cash, currency, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(snapshot_date) DO UPDATE SET
                total_cash = excluded.total_cash,
                total_settled_cash = excluded.total_settled_cash,
                currency = excluded.currency,
                created_at = datetime('now')
        """, (snapshot_date, total_cash, total_settled_cash, currency))
        conn.commit()
        conn.close()

    def get_latest_cash_snapshot(self) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM cash_snapshots
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM cash_snapshots)
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_positions_by_date(self, snapshot_date: str) -> List[Dict[str, Any]]:
        """
        取得指定日期的 Open Positions

        Args:
            snapshot_date: 日期（YYYY-MM-DD）

        Returns:
            持倉列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM open_positions
            WHERE snapshot_date = ?
            ORDER BY symbol
        """, (snapshot_date,))

        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return positions

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

    def get_all_chat_sessions(self) -> List[Dict[str, Any]]:
        """
        取得所有對話會話列表（含統計資訊）
        
        Returns:
            會話列表，每個包含 session_id, message_count, first_message, last_message
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_id,
                COUNT(*) as message_count,
                MIN(timestamp) as first_message,
                MAX(timestamp) as last_message,
                SUM(LENGTH(content)) as total_chars
            FROM chat_history
            GROUP BY session_id
            ORDER BY last_message DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_chat_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        取得特定會話的統計資訊
        
        Args:
            session_id: 會話 ID
            
        Returns:
            統計資訊字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as message_count,
                SUM(LENGTH(content)) as total_chars
            FROM chat_history
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'message_count': row['message_count'] if row else 0,
            'total_chars': row['total_chars'] if row else 0
        }
    
    def archive_chat_session(self, session_id: str, archive_path: str) -> bool:
        """
        將對話會話標記為已存檔
        
        Args:
            session_id: 會話 ID
            archive_path: 存檔路徑
            
        Returns:
            True 如果成功
        """
        # 在 settings 中記錄存檔資訊
        self.set_setting(f'chat_archive_{session_id}', archive_path)
        return True
    
    def delete_old_chat_messages(self, session_id: str, keep_recent: int = 20) -> int:
        """
        刪除舊的對話訊息，保留最近 N 條
        
        Args:
            session_id: 會話 ID
            keep_recent: 保留最近的訊息數量
            
        Returns:
            刪除的訊息數量
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 取得要保留的最舊訊息的 ID
        cursor.execute("""
            SELECT message_id FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET ?
        """, (session_id, keep_recent - 1))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0
        
        cutoff_id = row['message_id']
        
        # 刪除更舊的訊息
        cursor.execute("""
            DELETE FROM chat_history
            WHERE session_id = ? AND message_id < ?
        """, (session_id, cutoff_id))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

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

    # ========== Settings 管理 ==========

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """
        取得設定值

        Args:
            key: 設定鍵名
            default: 預設值

        Returns:
            設定值或預設值
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """
        設定值（新增或更新）

        Args:
            key: 設定鍵名
            value: 設定值
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
        """, (key, value))
        conn.commit()
        conn.close()

    def get_all_settings(self) -> Dict[str, str]:
        """
        取得所有設定

        Returns:
            設定字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        return {row['key']: row['value'] for row in rows}

    def delete_setting(self, key: str) -> None:
        """
        刪除設定

        Args:
            key: 設定鍵名
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    # ========== OHLC 緩存管理 ==========

    def get_ohlc_cache(self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        獲取 OHLC 緩存數據

        Args:
            symbol: 股票代號
            start_date: 開始日期 (yyyy-mm-dd)
            end_date: 結束日期 (yyyy-mm-dd)

        Returns:
            OHLC 數據列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT date, open, high, low, close, volume FROM ohlc_cache WHERE symbol = ?"
        params = [symbol.upper()]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_ohlc_latest_date(self, symbol: str) -> Optional[str]:
        """
        獲取某股票緩存中最新的日期

        Args:
            symbol: 股票代號

        Returns:
            最新日期 (yyyy-mm-dd) 或 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(date) as latest FROM ohlc_cache WHERE symbol = ?",
            (symbol.upper(),)
        )
        row = cursor.fetchone()
        conn.close()

        return row['latest'] if row and row['latest'] else None

    def save_ohlc_data(self, symbol: str, ohlc_data: List[Dict[str, Any]]) -> int:
        """
        保存 OHLC 數據到緩存

        Args:
            symbol: 股票代號
            ohlc_data: OHLC 數據列表，每個 dict 需包含 date, open, high, low, close, volume

        Returns:
            新增或更新的記錄數
        """
        if not ohlc_data:
            return 0

        conn = self._get_connection()
        cursor = conn.cursor()
        count = 0

        for d in ohlc_data:
            try:
                cursor.execute("""
                    INSERT INTO ohlc_cache (symbol, date, open, high, low, close, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(symbol, date) DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume,
                        updated_at = datetime('now')
                """, (
                    symbol.upper(),
                    d['date'],
                    d['open'],
                    d['high'],
                    d['low'],
                    d['close'],
                    d['volume']
                ))
                count += 1
            except Exception as e:
                print(f"Error saving OHLC data: {e}")

        conn.commit()
        conn.close()
        return count

    def delete_ohlc_cache(self, symbol: str) -> int:
        """
        刪除某股票的 OHLC 緩存

        Args:
            symbol: 股票代號

        Returns:
            刪除的記錄數
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ohlc_cache WHERE symbol = ?", (symbol.upper(),))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def get_ohlc_cache_stats(self) -> List[Dict[str, Any]]:
        """
        獲取 OHLC 緩存統計

        Returns:
            每個股票的緩存統計列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                symbol,
                COUNT(*) as count,
                MIN(date) as earliest,
                MAX(date) as latest,
                MAX(updated_at) as last_updated
            FROM ohlc_cache
            GROUP BY symbol
            ORDER BY symbol
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ========== MFE/MAE 分析表 ==========

    def init_mfe_mae_table(self):
        """初始化 MFE/MAE 分析表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_mfe_mae (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                original_symbol TEXT,        -- 原始交易代號（如選擇權完整代號）
                instrument_type TEXT DEFAULT 'stock',  -- 'stock' 或 'option'
                entry_date TEXT NOT NULL,
                exit_date TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL,
                mfe REAL,                    -- Max Favorable Excursion (最大浮盈 %)
                mae REAL,                    -- Max Adverse Excursion (最大浮虧 %)
                mfe_price REAL,              -- MFE 時的價格
                mae_price REAL,              -- MAE 時的價格
                mfe_date TEXT,               -- MFE 發生日期
                mae_date TEXT,               -- MAE 發生日期
                realized_pnl REAL,           -- 實際盈虧
                trade_efficiency REAL,       -- 交易效率 = realized_pnl / MFE
                holding_days INTEGER,        -- 持倉天數
                max_drawdown_from_peak REAL, -- 從最高點回撤
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mfe_mae_symbol
            ON trade_mfe_mae(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mfe_mae_entry_date
            ON trade_mfe_mae(entry_date)
        """)

        # 資料庫遷移：新增缺少的欄位（相容舊版本）
        try:
            cursor.execute("ALTER TABLE trade_mfe_mae ADD COLUMN original_symbol TEXT")
        except Exception:
            pass  # 欄位已存在

        try:
            cursor.execute("ALTER TABLE trade_mfe_mae ADD COLUMN instrument_type TEXT DEFAULT 'stock'")
        except Exception:
            pass  # 欄位已存在

        conn.commit()
        conn.close()

    def upsert_mfe_mae(self, data: Dict[str, Any]) -> int:
        """新增或更新 MFE/MAE 分析記錄"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trade_mfe_mae
            (trade_id, symbol, original_symbol, instrument_type, entry_date, exit_date, entry_price, exit_price,
             mfe, mae, mfe_price, mae_price, mfe_date, mae_date,
             realized_pnl, trade_efficiency, holding_days, max_drawdown_from_peak, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(trade_id) DO UPDATE SET
                original_symbol = excluded.original_symbol,
                instrument_type = excluded.instrument_type,
                exit_date = excluded.exit_date,
                exit_price = excluded.exit_price,
                mfe = excluded.mfe,
                mae = excluded.mae,
                mfe_price = excluded.mfe_price,
                mae_price = excluded.mae_price,
                mfe_date = excluded.mfe_date,
                mae_date = excluded.mae_date,
                realized_pnl = excluded.realized_pnl,
                trade_efficiency = excluded.trade_efficiency,
                holding_days = excluded.holding_days,
                max_drawdown_from_peak = excluded.max_drawdown_from_peak,
                updated_at = datetime('now')
        """, (
            data['trade_id'],
            data['symbol'],
            data.get('original_symbol'),
            data.get('instrument_type', 'stock'),
            data['entry_date'],
            data.get('exit_date'),
            data['entry_price'],
            data.get('exit_price'),
            data.get('mfe'),
            data.get('mae'),
            data.get('mfe_price'),
            data.get('mae_price'),
            data.get('mfe_date'),
            data.get('mae_date'),
            data.get('realized_pnl'),
            data.get('trade_efficiency'),
            data.get('holding_days'),
            data.get('max_drawdown_from_peak')
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def get_mfe_mae_by_symbol(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """取得 MFE/MAE 分析記錄"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT * FROM trade_mfe_mae
                WHERE symbol = ?
                ORDER BY entry_date DESC
            """, (symbol,))
        else:
            cursor.execute("""
                SELECT * FROM trade_mfe_mae
                ORDER BY entry_date DESC
            """)

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_mfe_mae_stats(self) -> Dict[str, Any]:
        """取得 MFE/MAE 統計摘要"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                AVG(mfe) as avg_mfe,
                AVG(mae) as avg_mae,
                AVG(trade_efficiency) as avg_efficiency,
                MAX(mfe) as max_mfe,
                MIN(mae) as max_mae,
                AVG(holding_days) as avg_holding_days,
                SUM(CASE WHEN trade_efficiency > 0.5 THEN 1 ELSE 0 END) as efficient_trades,
                SUM(CASE WHEN trade_efficiency <= 0.5 THEN 1 ELSE 0 END) as inefficient_trades
            FROM trade_mfe_mae
            WHERE mfe IS NOT NULL AND mae IS NOT NULL
        """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return {}

    # ========== 交易計劃表 ==========

    def init_trade_plans_table(self):
        """初始化交易計劃表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,          -- 'long' / 'short'
                status TEXT DEFAULT 'pending',    -- 'pending', 'executed', 'cancelled', 'expired'
                
                -- 進場條件
                entry_trigger TEXT,               -- 觸發條件描述
                entry_price_min REAL,             -- 進場價格區間下限
                entry_price_max REAL,             -- 進場價格區間上限
                
                -- 出場條件
                target_price REAL,                -- 目標價
                stop_loss_price REAL,             -- 停損價
                trailing_stop_pct REAL,           -- 移動停損百分比
                
                -- 部位管理
                position_size TEXT,               -- 預計部位大小
                max_risk_amount REAL,             -- 最大風險金額
                risk_reward_ratio REAL,           -- 風險報酬比
                
                -- 交易論點
                thesis TEXT,                      -- 交易論點/理由
                market_condition TEXT,            -- 市場環境描述
                key_levels TEXT,                  -- 重要價位 JSON
                
                -- 時間相關
                valid_until TEXT,                 -- 計劃有效期
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                
                -- 執行相關
                linked_trade_id TEXT,             -- 關聯到實際交易
                execution_notes TEXT,             -- 執行備註
                actual_entry_price REAL,          -- 實際進場價
                actual_exit_price REAL,           -- 實際出場價
                plan_vs_actual_diff REAL,         -- 計劃與實際差異
                
                -- AI 分析
                ai_review TEXT,                   -- AI 對計劃的評價
                ai_post_analysis TEXT             -- AI 執行後分析
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_symbol
            ON trade_plans(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_status
            ON trade_plans(status)
        """)

        conn.commit()
        conn.close()

    def add_trade_plan(self, data: Dict[str, Any]) -> int:
        """新增交易計劃"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 計算風險報酬比
        risk_reward = None
        if data.get('entry_price_min') and data.get('target_price') and data.get('stop_loss_price'):
            entry = data['entry_price_min']
            target = data['target_price']
            stop = data['stop_loss_price']
            if data.get('direction') == 'long':
                reward = target - entry
                risk = entry - stop
            else:
                reward = entry - target
                risk = stop - entry
            if risk > 0:
                risk_reward = round(reward / risk, 2)

        cursor.execute("""
            INSERT INTO trade_plans
            (symbol, direction, status, entry_trigger, entry_price_min, entry_price_max,
             target_price, stop_loss_price, trailing_stop_pct, position_size, max_risk_amount,
             risk_reward_ratio, thesis, market_condition, key_levels, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['symbol'],
            data.get('direction', 'long'),
            data.get('status', 'pending'),
            data.get('entry_trigger'),
            data.get('entry_price_min'),
            data.get('entry_price_max'),
            data.get('target_price'),
            data.get('stop_loss_price'),
            data.get('trailing_stop_pct'),
            data.get('position_size'),
            data.get('max_risk_amount'),
            risk_reward,
            data.get('thesis'),
            data.get('market_condition'),
            data.get('key_levels'),
            data.get('valid_until')
        ))

        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return plan_id

    def update_trade_plan(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """更新交易計劃"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 動態構建 UPDATE 語句
        allowed_fields = [
            'symbol', 'direction', 'status', 'entry_trigger', 'entry_price_min',
            'entry_price_max', 'target_price', 'stop_loss_price', 'trailing_stop_pct',
            'position_size', 'max_risk_amount', 'risk_reward_ratio', 'thesis',
            'market_condition', 'key_levels', 'valid_until', 'linked_trade_id',
            'execution_notes', 'actual_entry_price', 'actual_exit_price',
            'plan_vs_actual_diff', 'ai_review', 'ai_post_analysis'
        ]

        updates = []
        params = []
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])

        if not updates:
            conn.close()
            return False

        updates.append("updated_at = datetime('now')")
        params.append(plan_id)

        query = f"UPDATE trade_plans SET {', '.join(updates)} WHERE plan_id = ?"
        cursor.execute(query, params)

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_trade_plans(self, status: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """取得交易計劃列表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM trade_plans WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_trade_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """取得單一交易計劃"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_plans WHERE plan_id = ?", (plan_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def link_plan_to_trade(self, plan_id: int, trade_id: str, actual_entry: float, actual_exit: float = None) -> bool:
        """將交易計劃連結到實際交易"""
        plan = self.get_trade_plan(plan_id)
        if not plan:
            return False

        # 計算計劃與實際的差異
        planned_entry = plan.get('entry_price_min') or plan.get('entry_price_max')
        diff = None
        if planned_entry and actual_entry:
            diff = round(((actual_entry - planned_entry) / planned_entry) * 100, 2)

        return self.update_trade_plan(plan_id, {
            'status': 'executed',
            'linked_trade_id': trade_id,
            'actual_entry_price': actual_entry,
            'actual_exit_price': actual_exit,
            'plan_vs_actual_diff': diff
        })

    def delete_trade_plan(self, plan_id: int) -> bool:
        """刪除交易計劃"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_plans WHERE plan_id = ?", (plan_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    # ========== 交易日誌筆記表 ==========

    def init_trade_notes_table(self):
        """初始化交易日誌筆記表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_type TEXT NOT NULL,          -- 'daily', 'trade', 'weekly', 'monthly', 'misc'
                date TEXT NOT NULL,               -- 關聯日期
                symbol TEXT,                      -- 關聯標的 (可選)
                trade_id TEXT,                    -- 關聯交易 ID (可選)
                plan_id INTEGER,                  -- 關聯交易計劃 (可選)
                
                -- 主要內容
                title TEXT,                       -- 標題
                content TEXT NOT NULL,            -- 主要內容 (Markdown)
                
                -- 結構化數據
                mood TEXT,                        -- 情緒狀態
                confidence_level INTEGER,         -- 信心水平 1-10
                market_sentiment TEXT,            -- 市場情緒
                key_observations TEXT,            -- 重要觀察 (JSON array)
                lessons_learned TEXT,             -- 學到的教訓
                action_items TEXT,                -- 待辦事項 (JSON array)
                
                -- 標籤和分類
                tags TEXT,                        -- 標籤 (JSON array)
                category TEXT,                    -- 分類
                
                -- AI 相關
                ai_summary TEXT,                  -- AI 自動摘要
                ai_suggestions TEXT,              -- AI 改進建議
                ai_sentiment_score REAL,          -- AI 情緒評分 -1 to 1
                
                -- 時間戳記
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (trade_id) REFERENCES trades(trade_id),
                FOREIGN KEY (plan_id) REFERENCES trade_plans(plan_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_date
            ON trade_notes(date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_type
            ON trade_notes(note_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_symbol
            ON trade_notes(symbol)
        """)

        conn.commit()
        conn.close()

    def add_trade_note(self, data: Dict[str, Any]) -> int:
        """新增交易日誌筆記"""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        # 處理 JSON 欄位
        key_observations = data.get('key_observations')
        if isinstance(key_observations, list):
            key_observations = json.dumps(key_observations, ensure_ascii=False)

        action_items = data.get('action_items')
        if isinstance(action_items, list):
            action_items = json.dumps(action_items, ensure_ascii=False)

        tags = data.get('tags')
        if isinstance(tags, list):
            tags = json.dumps(tags, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO trade_notes
            (note_type, date, symbol, trade_id, plan_id, title, content,
             mood, confidence_level, market_sentiment, key_observations,
             lessons_learned, action_items, tags, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('note_type', 'misc'),
            data['date'],
            data.get('symbol'),
            data.get('trade_id'),
            data.get('plan_id'),
            data.get('title'),
            data['content'],
            data.get('mood'),
            data.get('confidence_level'),
            data.get('market_sentiment'),
            key_observations,
            data.get('lessons_learned'),
            action_items,
            tags,
            data.get('category')
        ))

        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return note_id

    def update_trade_note(self, note_id: int, data: Dict[str, Any]) -> bool:
        """更新交易日誌筆記"""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        allowed_fields = [
            'note_type', 'date', 'symbol', 'trade_id', 'plan_id', 'title', 'content',
            'mood', 'confidence_level', 'market_sentiment', 'key_observations',
            'lessons_learned', 'action_items', 'tags', 'category',
            'ai_summary', 'ai_suggestions', 'ai_sentiment_score'
        ]

        updates = []
        params = []
        for field in allowed_fields:
            if field in data:
                value = data[field]
                # 處理 JSON 欄位
                if field in ['key_observations', 'action_items', 'tags'] and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            conn.close()
            return False

        updates.append("updated_at = datetime('now')")
        params.append(note_id)

        query = f"UPDATE trade_notes SET {', '.join(updates)} WHERE note_id = ?"
        cursor.execute(query, params)

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_trade_notes(self, 
                        note_type: Optional[str] = None,
                        symbol: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """取得交易日誌筆記列表"""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM trade_notes WHERE 1=1"
        params = []

        if note_type:
            query += " AND note_type = ?"
            params.append(note_type)

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # 解析 JSON 欄位
        result = []
        for row in rows:
            note = dict(row)
            for field in ['key_observations', 'action_items', 'tags']:
                if note.get(field):
                    try:
                        note[field] = json.loads(note[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(note)

        return result

    def get_trade_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """取得單一交易日誌筆記"""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_notes WHERE note_id = ?", (note_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        note = dict(row)
        for field in ['key_observations', 'action_items', 'tags']:
            if note.get(field):
                try:
                    note[field] = json.loads(note[field])
                except (json.JSONDecodeError, TypeError):
                    pass

        return note

    def delete_trade_note(self, note_id: int) -> bool:
        """刪除交易日誌筆記"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_notes WHERE note_id = ?", (note_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_daily_summary(self, date: str) -> Dict[str, Any]:
        """取得某日的完整摘要（筆記 + 交易 + 計劃）"""
        notes = self.get_trade_notes(start_date=date, end_date=date)
        
        # 取得當日交易
        trades = self.get_trades(start_date=date, end_date=date)
        
        # 取得相關計劃
        plans = self.get_trade_plans()
        daily_plans = [p for p in plans if p.get('created_at', '').startswith(date)]

        return {
            'date': date,
            'notes': notes,
            'trades': trades,
            'plans': daily_plans,
            'trade_count': len(trades),
            'total_pnl': sum(t.get('realized_pnl', 0) for t in trades)
        }

    def get_mfe_mae_records(self, limit: int = 20, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        取得 MFE/MAE 記錄
        
        Args:
            limit: 限制返回筆數
            symbol: 篩選標的
            
        Returns:
            MFE/MAE 記錄列表（目前返回空列表，功能待實作）
        """
        # MFE/MAE 計算功能尚未完整實作，返回空列表
        return []
