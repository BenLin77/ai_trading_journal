"""
GEX Sentinel 的 AI 分析服務。

使用 LLM API (Google Gemini) 產生市場結構分析。
"""

import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.models.gex_profile import GEXProfile
from src.models.sentiment import SentimentIndicators

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_structure_analysis(symbol: str, gex_profile: GEXProfile, sentiment: SentimentIndicators) -> str:
    """
    使用 Google Gemini 產生市場結構的 AI 分析。

    Args:
        symbol: 股票代碼
        gex_profile: 計算出的 GEX 指標
        sentiment: 計算出的情緒指標

    Returns:
        str: Markdown 格式的分析文字

    Raises:
        ValueError: 如果缺少 API 金鑰
        RuntimeError: 如果 API 呼叫失敗
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("在環境變數中找不到 GEMINI_API_KEY")

    # 設定 Gemini
    genai.configure(api_key=api_key)
    
    # 選擇模型 - 根據 .env.example 使用 gemini-pro，但尊重函式庫預設值
    # 我們明確使用 'gemini-pro'，因為它在文字生成方面較穩定
    model = genai.GenerativeModel('gemini-pro')

    # 建構提示詞 (Prompt)
    prompt = f"""
你是一位市場結構分析師。請分析 {symbol} 的以下選擇權部位：

**Gamma Exposure (GEX):**
- 淨 GEX: ${gex_profile.net_gex / 1_000_000_000:.2f}B
- 狀態: {gex_profile.gex_state}
- Call 牆 (壓力): ${gex_profile.call_wall if gex_profile.call_wall else 'N/A'}
- Put 牆 (支撐): ${gex_profile.put_wall if gex_profile.put_wall else 'N/A'}
- 最大痛點 (Max Pain): ${gex_profile.max_pain if gex_profile.max_pain else 'N/A'}

**情緒指標:**
- RSI: {sentiment.rsi:.1f}
- Put/Call 比率 (PCR): {sentiment.pcr:.2f}
- IV 百分位數: {sentiment.iv_percentile:.0f}%

請提供：
1. GEX 狀態解讀 (看漲/看跌部位)
2. 牆的顯著性 (支撐/壓力位)
3. 情緒背景 (超買/超賣，選擇權偏斜)
4. 可操作的洞察 (此結構對價格行為的暗示)

請保持回應簡潔 (2-3 段) 並使用繁體中文與 Markdown 格式。
"""

    try:
        logger.info(f"正在為 {symbol} 產生 AI 分析...")
        response = model.generate_content(prompt)
        return response.text
    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Gemini API 錯誤: {e}")
        raise RuntimeError(f"Gemini API 錯誤: {e}")
    except Exception as e:
        logger.error(f"AI 分析期間發生未預期的錯誤: {e}")
        raise RuntimeError(f"無法產生分析: {e}")
