"""
資料匯出模組

支援多種格式匯出：CSV、Excel、JSON
"""

import pandas as pd
from datetime import datetime
from io import BytesIO
from typing import Literal


class DataExporter:
    """數據匯出工具類"""

    @staticmethod
    def export_trades(
        trades_df: pd.DataFrame,
        format: Literal['csv', 'excel', 'json'] = 'csv',
        filename: str = None
    ) -> tuple[bytes, str, str]:
        """
        匯出交易數據

        Args:
            trades_df: 交易 DataFrame
            format: 匯出格式 (csv/excel/json)
            filename: 檔案名稱（不含副檔名）

        Returns:
            (檔案內容, 檔案名稱, MIME類型) 的 tuple
        """
        if filename is None:
            filename = f"trades_{datetime.now():%Y%m%d_%H%M%S}"

        if format == 'csv':
            data = trades_df.to_csv(index=False).encode('utf-8-sig')
            mime = 'text/csv'
            filename = f"{filename}.csv"

        elif format == 'excel':
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 交易紀錄工作表
                trades_df.to_excel(writer, index=False, sheet_name='交易紀錄')

                # 統計摘要工作表
                summary_df = DataExporter._create_summary_sheet(trades_df)
                summary_df.to_excel(writer, index=False, sheet_name='統計摘要')

            data = output.getvalue()
            mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"{filename}.xlsx"

        elif format == 'json':
            data = trades_df.to_json(
                orient='records',
                indent=2,
                date_format='iso'
            ).encode('utf-8')
            mime = 'application/json'
            filename = f"{filename}.json"

        else:
            raise ValueError(f"不支援的格式: {format}")

        return data, filename, mime

    @staticmethod
    def _create_summary_sheet(trades_df: pd.DataFrame) -> pd.DataFrame:
        """建立統計摘要表"""
        summary_data = {
            '指標': [
                '總交易次數',
                '獲利交易次數',
                '虧損交易次數',
                '勝率 (%)',
                '總盈虧',
                '平均獲利',
                '平均虧損',
                '最大獲利',
                '最大虧損',
                '賺賠比'
            ],
            '數值': []
        }

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['realized_pnl'] > 0])
        losses = len(trades_df[trades_df['realized_pnl'] < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['realized_pnl'].sum()
        avg_win = trades_df[trades_df['realized_pnl'] > 0]['realized_pnl'].mean() if wins > 0 else 0
        avg_loss = abs(trades_df[trades_df['realized_pnl'] < 0]['realized_pnl'].mean()) if losses > 0 else 0
        max_win = trades_df['realized_pnl'].max()
        max_loss = trades_df['realized_pnl'].min()
        risk_reward = avg_win / avg_loss if avg_loss > 0 else 0

        summary_data['數值'] = [
            total_trades,
            wins,
            losses,
            f"{win_rate:.2f}",
            f"${total_pnl:,.2f}",
            f"${avg_win:,.2f}",
            f"${avg_loss:,.2f}",
            f"${max_win:,.2f}",
            f"${max_loss:,.2f}",
            f"{risk_reward:.2f}"
        ]

        return pd.DataFrame(summary_data)

    @staticmethod
    def export_journal(
        journal_df: pd.DataFrame,
        format: Literal['csv', 'excel', 'json'] = 'csv'
    ) -> tuple[bytes, str, str]:
        """
        匯出交易日誌

        Args:
            journal_df: 日誌 DataFrame
            format: 匯出格式

        Returns:
            (檔案內容, 檔案名稱, MIME類型)
        """
        filename = f"journal_{datetime.now():%Y%m%d_%H%M%S}"

        if format == 'csv':
            data = journal_df.to_csv(index=False).encode('utf-8-sig')
            mime = 'text/csv'
            filename = f"{filename}.csv"

        elif format == 'excel':
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                journal_df.to_excel(writer, index=False, sheet_name='交易日誌')
            data = output.getvalue()
            mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"{filename}.xlsx"

        elif format == 'json':
            data = journal_df.to_json(
                orient='records',
                indent=2,
                date_format='iso'
            ).encode('utf-8')
            mime = 'application/json'
            filename = f"{filename}.json"

        return data, filename, mime
