"""
TA_Indicator_core.backtest_engine.py

【功能說明】
------------------------------------------------------------
本模組為 AI_Trading_Journal 回測框架的通用技術分析指標工具 (Technical Analysis)，
整合 `ta` (Technical Analysis Library) 庫，支援 VWAP 及絕大多數常見技術指標。
提供統一的介面來調用各種指標並產生交易信號。

【流程與數據流】
------------------------------------------------------------
- 由 IndicatorsBacktester 調用
- 使用 `ta` 庫計算指標數值
- 根據設定的策略 (Strategy) 產生信號

【策略型態】
------------------------------------------------------------
- TA1: Indicator > Threshold -> Long (做多)
- TA2: Indicator > Threshold -> Short (做空)
- TA3: Indicator < Threshold -> Long (做多)
- TA4: Indicator < Threshold -> Short (做空)
- TA5: Price > Indicator -> Long (做多) (例如 Price > VWAP)
- TA6: Price > Indicator -> Short (做空)
- TA7: Price < Indicator -> Long (做多)
- TA8: Price < Indicator -> Short (做空)

【參數說明】
------------------------------------------------------------
- ta_name: 指標名稱 (例如 'vwap', 'rsi', 'macd', 'atr', 'ema', 'sma')
- ta_window: 主要週期參數 (對應 window, n, period 等)
- ta_param2: 次要參數 (視指標而定，例如 std_dev)
- threshold: 閾值 (用於 TA1-TA4)

"""

import logging
import numpy as np
import pandas as pd
import ta
from .IndicatorParams_backtester import IndicatorParams

try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

class TAIndicator:
    """
    通用技術分析指標 (Wrapper for 'ta' library)
    """

    STRATEGY_DESCRIPTIONS = [
        "指標 > 閾值 -> 做多",
        "指標 > 閾值 -> 做空",
        "指標 < 閾值 -> 做多",
        "指標 < 閾值 -> 做空",
        "價格 > 指標 -> 做多",
        "價格 > 指標 -> 做空",
        "價格 < 指標 -> 做多",
        "價格 < 指標 -> 做空",
    ]

    def __init__(self, data, params, logger=None):
        self.data = data
        self.params = params
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._cache = {}

    @staticmethod
    def get_strategy_descriptions():
        """回傳策略描述字典"""
        return {
            f"TA{i + 1}": desc
            for i, desc in enumerate(TAIndicator.STRATEGY_DESCRIPTIONS)
        }

    @classmethod
    def get_params(cls, strat_idx=None, params_config=None):
        """
        產生參數組合
        """
        if params_config is None:
            raise ValueError("params_config 必須提供")

        ta_name = params_config.get("ta_name", "vwap").lower()
        param_list = []

        # 解析範圍參數
        window_range = params_config.get("window_range", "14:14:1")
        threshold_range = params_config.get("threshold_range", "0:0:1")

        # 解析 window_range
        try:
            w_start, w_end, w_step = map(int, window_range.split(":"))
            windows = list(range(w_start, w_end + 1, w_step))
        except:
            windows = [14] # Default

        # 解析 threshold_range (若策略需要)
        thresholds = [0.0]
        if strat_idx in [1, 2, 3, 4]:
            try:
                # 支援浮點數範圍
                t_parts = threshold_range.split(":")
                if len(t_parts) == 3:
                    t_start, t_end, t_step = map(float, t_parts)
                    # 使用 numpy arange 產生浮點數序列，注意精度
                    thresholds = np.arange(t_start, t_end + 0.000001, t_step).tolist()
                else:
                    thresholds = [float(threshold_range)]
            except:
                thresholds = [0.0]

        for w in windows:
            for t in thresholds:
                param = IndicatorParams("TA")
                param.add_param("ta_name", ta_name)
                param.add_param("ta_window", w)
                param.add_param("threshold", t)
                param.add_param("strat_idx", strat_idx)
                param_list.append(param)

        return param_list

    def calculate_indicator(self, ta_name, window):
        """
        使用 `ta` 庫計算指標
        """
        cache_key = (ta_name, window)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 確保數據列存在
        high = self.data['High'] if 'High' in self.data.columns else self.data['Close']
        low = self.data['Low'] if 'Low' in self.data.columns else self.data['Close']
        close = self.data['Close']
        volume = self.data['Volume'] if 'Volume' in self.data.columns else None

        result = None

        try:
            if ta_name == 'vwap':
                if volume is None:
                    raise ValueError("VWAP 需要 Volume 數據")
                # ta.volume.VolumeWeightedAveragePrice
                indicator = ta.volume.VolumeWeightedAveragePrice(
                    high=high, low=low, close=close, volume=volume, window=window
                )
                result = indicator.volume_weighted_average_price()

            elif ta_name == 'rsi':
                # ta.momentum.RSIIndicator
                indicator = ta.momentum.RSIIndicator(close=close, window=window)
                result = indicator.rsi()

            elif ta_name == 'sma':
                # ta.trend.SMAIndicator
                indicator = ta.trend.SMAIndicator(close=close, window=window)
                result = indicator.sma_indicator()

            elif ta_name == 'ema':
                # ta.trend.EMAIndicator
                indicator = ta.trend.EMAIndicator(close=close, window=window)
                result = indicator.ema_indicator()
            
            elif ta_name == 'atr':
                # ta.volatility.AverageTrueRange
                indicator = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=window)
                result = indicator.average_true_range()
                
            elif ta_name == 'macd':
                # MACD通常有多個參數，這裡簡化處理，若需要更複雜控制可擴充
                # 使用 window 作為 slow, window/2 作為 fast? 
                # 或者固定 MACD 參數 (12, 26, 9) ?
                # 這裡暫時使用 window 作為 fast, window*2+2 為 slow
                indicator = ta.trend.MACD(close=close, window_fast=window, window_slow=window*2, window_sign=9)
                result = indicator.macd()
                
            elif ta_name == 'bb_upper':
                indicator = ta.volatility.BollingerBands(close=close, window=window)
                result = indicator.bollinger_hband()
            elif ta_name == 'bb_lower':
                indicator = ta.volatility.BollingerBands(close=close, window=window)
                result = indicator.bollinger_lband()

            else:
                # 嘗試動態尋找
                # 這部分比較複雜，因為 ta 的 API 不完全統一
                # 暫時只支援上述常用指標，後續可擴充
                self.logger.warning(f"尚未完整支援動態調用指標: {ta_name}，嘗試使用 SMA 代替")
                indicator = ta.trend.SMAIndicator(close=close, window=window)
                result = indicator.sma_indicator()

        except Exception as e:
            self.logger.error(f"計算指標 {ta_name} 失敗: {e}")
            # 回傳全零以避免崩潰
            result = pd.Series(0, index=self.data.index)

        # 填補 NaN
        result = result.fillna(0)
        
        self._cache[cache_key] = result
        return result

    def generate_signals(self, predictor=None):
        """
        產生信號
        """
        strat_idx = self.params.get_param("strat_idx", 1)
        ta_name = self.params.get_param("ta_name", "vwap").lower()
        window = self.params.get_param("ta_window", 14)
        threshold = self.params.get_param("threshold", 0.0)

        # 計算指標
        indicator_values = self.calculate_indicator(ta_name, window)
        
        # 獲取比較對象 (通常是 Close Price)
        # 如果有指定 predictor，則使用 predictor，否則使用 Close
        if predictor and predictor in self.data.columns:
            compare_values = self.data[predictor]
        else:
            compare_values = self.data['Close']

        # 確保轉為 numpy array
        ind_arr = indicator_values.values
        price_arr = compare_values.values
        
        # 確保長度一致
        n = len(ind_arr)
        signals = np.zeros(n)

        # 策略邏輯
        # TA1: Indicator > Threshold -> Long
        if strat_idx == 1:
            signals = np.where(ind_arr > threshold, 1.0, 0.0)
            
        # TA2: Indicator > Threshold -> Short
        elif strat_idx == 2:
            signals = np.where(ind_arr > threshold, -1.0, 0.0)
            
        # TA3: Indicator < Threshold -> Long
        elif strat_idx == 3:
            signals = np.where(ind_arr < threshold, 1.0, 0.0)
            
        # TA4: Indicator < Threshold -> Short
        elif strat_idx == 4:
            signals = np.where(ind_arr < threshold, -1.0, 0.0)
            
        # TA5: Price > Indicator -> Long
        elif strat_idx == 5:
            signals = np.where(price_arr > ind_arr, 1.0, 0.0)
            
        # TA6: Price > Indicator -> Short
        elif strat_idx == 6:
            signals = np.where(price_arr > ind_arr, -1.0, 0.0)
            
        # TA7: Price < Indicator -> Long
        elif strat_idx == 7:
            signals = np.where(price_arr < ind_arr, 1.0, 0.0)
            
        # TA8: Price < Indicator -> Short
        elif strat_idx == 8:
            signals = np.where(price_arr < ind_arr, -1.0, 0.0)
            
        # 處理無效區間 (前 window 筆)
        if window > 0:
            signals[:window] = 0
            
        return pd.Series(signals, index=self.data.index)

