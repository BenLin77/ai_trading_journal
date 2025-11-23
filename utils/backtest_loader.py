"""
Backtest Loader 模組

此模組負責：
1. 載入 AI_Trading_Journal 的回測結果 (.parquet 格式)
2. 轉換為標準化格式
3. 計算額外績效指標
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import json


class BacktestLoader:
    """AI_Trading_Journal 回測結果載入器"""

    def __init__(self, AI_Trading_Journal_path: str = "."):
        """
        初始化載入器

        Args:
            AI_Trading_Journal_path: AI_Trading_Journal 專案路徑 (預設為當前目錄)
        """
        self.AI_Trading_Journal_path = Path(AI_Trading_Journal_path)
        self.records_path = self.AI_Trading_Journal_path / "records"

    def load_backtest_result(self, file_path: str) -> pd.DataFrame:
        """
        載入單一回測結果檔案

        Args:
            file_path: parquet 檔案路徑

        Returns:
            回測結果 DataFrame
        """
        try:
            df = pd.read_parquet(file_path)
            return df
        except Exception as e:
            raise ValueError(f"無法載入回測結果：{str(e)}")

    def list_available_backtests(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的回測結果

        Returns:
            回測檔案資訊列表
        """
        metricstracker_path = self.records_path / "metricstracker"

        if not metricstracker_path.exists():
            return []

        backtest_files = []
        for file in metricstracker_path.glob("*.parquet"):
            try:
                df = pd.read_parquet(file)
                file_info = {
                    'filename': file.name,
                    'path': str(file),
                    'size': file.stat().st_size,
                    'modified': file.stat().st_mtime,
                    'num_strategies': len(df) if isinstance(df, pd.DataFrame) else 0
                }
                backtest_files.append(file_info)
            except Exception:
                continue

        return sorted(backtest_files, key=lambda x: x['modified'], reverse=True)

    def extract_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        從回測結果中提取績效指標

        Args:
            df: 回測結果 DataFrame

        Returns:
            績效指標字典
        """
        metrics = {}

        # 檢查 DataFrame 結構
        if df.empty:
            return metrics

        # 根據 AI_Trading_Journal 的 DataFrame 結構提取指標
        # 通常包含：Strategy, Sharpe, Sortino, MDD, Win Rate, Profit Factor 等欄位

        for col in df.columns:
            col_lower = col.lower()

            # Sharpe Ratio
            if 'sharpe' in col_lower:
                metrics['sharpe_ratio'] = df[col].max() if not df[col].isna().all() else None

            # Sortino Ratio
            elif 'sortino' in col_lower:
                metrics['sortino_ratio'] = df[col].max() if not df[col].isna().all() else None

            # Max Drawdown
            elif 'drawdown' in col_lower or 'mdd' in col_lower:
                metrics['max_drawdown'] = df[col].min() if not df[col].isna().all() else None

            # Win Rate
            elif 'win' in col_lower and 'rate' in col_lower:
                metrics['win_rate'] = df[col].mean() if not df[col].isna().all() else None

            # Profit Factor
            elif 'profit' in col_lower and 'factor' in col_lower:
                metrics['profit_factor'] = df[col].mean() if not df[col].isna().all() else None

            # Total Return
            elif 'return' in col_lower or 'profit' in col_lower:
                metrics['total_return'] = df[col].sum() if not df[col].isna().all() else None

        return metrics

    def get_best_strategy(self, df: pd.DataFrame, metric: str = 'sharpe') -> Optional[Dict[str, Any]]:
        """
        找出最佳策略組合

        Args:
            df: 回測結果 DataFrame
            metric: 用於排序的指標 (sharpe, sortino, profit_factor)

        Returns:
            最佳策略資訊
        """
        if df.empty:
            return None

        # 根據指標排序
        metric_columns = [col for col in df.columns if metric.lower() in col.lower()]

        if not metric_columns:
            return None

        metric_col = metric_columns[0]
        best_idx = df[metric_col].idxmax()

        if pd.isna(best_idx):
            return None

        best_row = df.loc[best_idx]

        return {
            'strategy': best_row.to_dict(),
            'metric_value': best_row[metric_col],
            'metric_name': metric_col
        }

    def detect_overfitting(self, df: pd.DataFrame, threshold: float = 0.3) -> Dict[str, Any]:
        """
        偵測過度擬合（參數高原分析）

        Args:
            df: 回測結果 DataFrame
            threshold: 績效變異閾值

        Returns:
            過擬合分析結果
        """
        analysis = {
            'is_overfitted': False,
            'variance': None,
            'stable_params': [],
            'unstable_params': []
        }

        if df.empty or len(df) < 3:
            return analysis

        # 找出 Sharpe Ratio 欄位
        sharpe_cols = [col for col in df.columns if 'sharpe' in col.lower()]

        if not sharpe_cols:
            return analysis

        sharpe_col = sharpe_cols[0]
        sharpe_values = df[sharpe_col].dropna()

        if len(sharpe_values) < 3:
            return analysis

        # 計算變異係數 (Coefficient of Variation)
        cv = sharpe_values.std() / sharpe_values.mean() if sharpe_values.mean() != 0 else float('inf')

        analysis['variance'] = cv
        analysis['is_overfitted'] = cv > threshold

        # 找出穩定參數組合（高原區域）
        median_sharpe = sharpe_values.median()
        stable_threshold = median_sharpe * 0.9  # 90% of median

        for idx, row in df.iterrows():
            if row[sharpe_col] >= stable_threshold:
                analysis['stable_params'].append(row.to_dict())
            else:
                analysis['unstable_params'].append(row.to_dict())

        return analysis

    def convert_to_database_format(self, df: pd.DataFrame, strategy_name: str, symbol: str) -> List[Dict[str, Any]]:
        """
        轉換回測結果為資料庫格式

        Args:
            df: 回測結果 DataFrame
            strategy_name: 策略名稱
            symbol: 標的代號

        Returns:
            可存入資料庫的記錄列表
        """
        records = []

        for idx, row in df.iterrows():
            record = {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'start_date': row.get('start_date', ''),
                'end_date': row.get('end_date', ''),
                'parameters': json.dumps(row.to_dict()),
                'sharpe_ratio': self._safe_get_metric(row, 'sharpe'),
                'sortino_ratio': self._safe_get_metric(row, 'sortino'),
                'max_drawdown': self._safe_get_metric(row, 'drawdown', 'mdd'),
                'win_rate': self._safe_get_metric(row, 'win_rate', 'win rate'),
                'profit_factor': self._safe_get_metric(row, 'profit_factor', 'profit factor'),
                'total_trades': self._safe_get_metric(row, 'total_trades', 'trades', 'num_trades'),
                'total_return': self._safe_get_metric(row, 'return', 'profit', 'pnl'),
                'annual_return': self._safe_get_metric(row, 'annual', 'annualized')
            }
            records.append(record)

        return records

    def _safe_get_metric(self, row: pd.Series, *search_terms: str) -> Optional[float]:
        """
        安全取得指標值

        Args:
            row: DataFrame 的一行
            search_terms: 搜尋關鍵字

        Returns:
            指標值或 None
        """
        for term in search_terms:
            matching_cols = [col for col in row.index if term.lower() in col.lower()]
            if matching_cols:
                value = row[matching_cols[0]]
                if pd.notna(value):
                    return float(value)
        return None

    def summarize_backtest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成回測摘要

        Args:
            df: 回測結果 DataFrame

        Returns:
            摘要統計
        """
        summary = {
            'total_strategies': len(df),
            'metrics': {},
            'best_strategy': None,
            'overfitting_analysis': None
        }

        if df.empty:
            return summary

        # 提取所有指標的統計
        for col in df.columns:
            if df[col].dtype in [np.float64, np.int64]:
                summary['metrics'][col] = {
                    'mean': float(df[col].mean()),
                    'median': float(df[col].median()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max())
                }

        # 找出最佳策略
        summary['best_strategy'] = self.get_best_strategy(df)

        # 過擬合分析
        summary['overfitting_analysis'] = self.detect_overfitting(df)

        return summary
