"""
AI Analysis Service for GEX Sentinel.

Generates market structure analysis using LLM API (Google Gemini).
"""

import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.models.gex_profile import GEXProfile
from src.models.sentiment import SentimentIndicators

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_structure_analysis(symbol: str, gex_profile: GEXProfile, sentiment: SentimentIndicators) -> str:
    """
    Generate AI analysis of market structure using Google Gemini.

    Args:
        symbol: Ticker symbol
        gex_profile: Calculated GEX metrics
        sentiment: Calculated sentiment indicators

    Returns:
        str: Markdown-formatted analysis text

    Raises:
        ValueError: If API key is missing
        RuntimeError: If API call fails
    """
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY not found in environment variables")

    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Select model - using gemini-pro as per .env.example, but respecting library defaults
    # We'll use 'gemini-pro' explicitly as it's stable for text generation
    model = genai.GenerativeModel('gemini-pro')

    # Construct prompt
    prompt = f"""
You are a market structure analyst. Analyze the following options positioning for {symbol}:

**Gamma Exposure (GEX):**
- Net GEX: ${gex_profile.net_gex / 1_000_000_000:.2f}B
- State: {gex_profile.gex_state}
- Call Wall: ${gex_profile.call_wall if gex_profile.call_wall else 'N/A'}
- Put Wall: ${gex_profile.put_wall if gex_profile.put_wall else 'N/A'}
- Max Pain: ${gex_profile.max_pain if gex_profile.max_pain else 'N/A'}

**Sentiment:**
- RSI: {sentiment.rsi:.1f}
- PCR: {sentiment.pcr:.2f}
- IV Percentile: {sentiment.iv_percentile:.0f}%

Provide:
1. Interpretation of GEX state (bullish/bearish positioning)
2. Significance of walls (support/resistance levels)
3. Sentiment context (overbought/oversold, options skew)
4. Actionable insight (what this structure suggests for price action)

Keep the response concise (2-3 paragraphs) and use Markdown formatting.
"""

    try:
        logger.info(f"Generating AI analysis for {symbol}...")
        response = model.generate_content(prompt)
        return response.text
    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Gemini API error: {e}")
        raise RuntimeError(f"Gemini API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during AI analysis: {e}")
        raise RuntimeError(f"Failed to generate analysis: {e}")
