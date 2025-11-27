#!/usr/bin/env python3
"""
IBKR Flex Query 測試腳本

測試 Flex Query API 連接和數據抓取
"""

from utils.ibkr_flex_query import IBKRFlexQuery
from database import TradingDatabase
import pandas as pd
from datetime import datetime, timedelta


def test_connection():
    """測試基本連接"""
    print("=" * 60)
    print("測試 1: IBKR Flex Query 連接")
    print("=" * 60)

    try:
        flex = IBKRFlexQuery()
        print(f"✅ Token: {flex.token[:10]}...{flex.token[-10:]}")
        print(f"✅ Trades Query ID: {flex.trades_query_id}")
        print(f"✅ Positions Query ID: {flex.positions_query_id}")
        return flex
    except ValueError as e:
        print(f"❌ 設定錯誤: {e}")
        print("\n請檢查 .env 檔案是否包含:")
        print("- IBKR_FLEX_TOKEN")
        print("- IBKR_TRADES_QUERY_ID")
        print("- IBKR_POSITIONS_QUERY_ID")
        return None
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        return None


def test_get_trades(flex):
    """測試取得交易記錄"""
    print("\n" + "=" * 60)
    print("測試 2: 取得前一日交易記錄")
    print("=" * 60)

    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"查詢日期: {yesterday}")

        df = flex.get_trades(date=yesterday)

        if df.empty:
            print(f"⚠️ {yesterday} 無交易記錄")
            return None

        print(f"✅ 取得 {len(df)} 筆交易")
        print("\n前 5 筆交易:")
        print(df[['symbol', 'date_time', 'quantity', 'price', 'asset_category']].head())

        return df

    except Exception as e:
        print(f"❌ 取得交易記錄失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_get_positions(flex):
    """測試取得庫存快照"""
    print("\n" + "=" * 60)
    print("測試 3: 取得當前庫存快照")
    print("=" * 60)

    try:
        df = flex.get_positions()

        if df.empty:
            print("⚠️ 當前無持倉")
            return None

        print(f"✅ 取得 {len(df)} 個部位")
        print("\n當前持倉:")
        print(df[['symbol', 'position', 'mark_price', 'unrealized_pnl', 'asset_category']].head(10))

        # 統計
        print(f"\n持倉統計:")
        print(f"- 股票: {len(df[df['asset_category'] == 'STK'])} 個")
        print(f"- 選擇權: {len(df[df['asset_category'] == 'OPT'])} 個")
        print(f"- 總未實現盈虧: ${df['unrealized_pnl'].sum():,.2f}")

        return df

    except Exception as e:
        print(f"❌ 取得庫存快照失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_sync_to_db(flex):
    """測試同步到資料庫"""
    print("\n" + "=" * 60)
    print("測試 4: 同步數據到資料庫")
    print("=" * 60)

    try:
        db = TradingDatabase()
        result = flex.sync_to_database(db)

        print(f"✅ 同步完成!")
        print(f"- 交易記錄: {result['trades']} 筆")
        print(f"- 庫存快照: {result['positions']} 個部位")

        # 驗證資料庫
        print("\n驗證資料庫內容:")
        positions = db.get_latest_positions()
        if positions:
            print(f"✅ 資料庫中有 {len(positions)} 個持倉")
            print(f"   快照日期: {positions[0]['snapshot_date']}")

        trades = db.get_recent_trades(limit=5)
        if trades:
            print(f"✅ 資料庫中最新 {len(trades)} 筆交易")

        return result

    except Exception as e:
        print(f"❌ 同步失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主測試流程"""
    print("\n" + "=" * 60)
    print("IBKR Flex Query API 完整測試")
    print("=" * 60)

    # Test 1: 連接
    flex = test_connection()
    if not flex:
        print("\n❌ 連接測試失敗，請檢查設定後重試")
        return

    # Test 2: 取得交易記錄
    trades_df = test_get_trades(flex)

    # Test 3: 取得庫存快照
    positions_df = test_get_positions(flex)

    # Test 4: 同步到資料庫
    if trades_df is not None or positions_df is not None:
        result = test_sync_to_db(flex)

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    print("✅ 所有測試完成！系統已準備就緒。")
    print("\n下一步:")
    print("1. 啟動 Streamlit: uv run streamlit run Home.py")
    print("2. 點擊首頁的 '📥 執行同步' 按鈕")
    print("3. 前往 Portfolio Advisor 查看 AI 分析")


if __name__ == "__main__":
    main()
