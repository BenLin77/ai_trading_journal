"""
AI 教練整合模組

此模組負責：
1. 與 AI API 互動（支援 DeepSeek 或 Google Gemini）
2. 生成交易檢討對話
3. 提供策略建議
4. 生成績效評語

模型選擇策略：
- Thinking Model (深度分析): Gemini 2.5 Flash Thinking / DeepSeek Reasoner
- Fast Model (快速對話): Gemini 2.0 Flash / DeepSeek Chat
"""

import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI 提供商抽象基類"""
    
    @abstractmethod
    def generate_content(self, prompt: str, use_thinking: bool = False) -> str:
        """生成內容
        
        Args:
            prompt: 提示詞
            use_thinking: 是否使用思考型模型（用於深度分析）
        """
        pass
    
    @abstractmethod
    def start_chat(self, history: List[Dict]) -> 'ChatSession':
        """開始對話（使用 Fast Model）"""
        pass


class DeepSeekProvider(AIProvider):
    """DeepSeek API 提供商 - 支援雙模型"""
    
    # 模型配置
    FAST_MODEL = "deepseek-chat"  # 快速對話
    THINKING_MODEL = "deepseek-reasoner"  # 深度推理 (R1)
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        logger.info(f"DeepSeek 初始化完成 (Fast: {self.FAST_MODEL}, Thinking: {self.THINKING_MODEL})")
    
    def generate_content(self, prompt: str, use_thinking: bool = False) -> str:
        model = self.THINKING_MODEL if use_thinking else self.FAST_MODEL
        logger.debug(f"使用模型: {model}, thinking={use_thinking}")
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7 if not use_thinking else 0.0,  # Thinking model 用 0 溫度
            max_tokens=8192 if use_thinking else 4096
        )
        
        # DeepSeek Reasoner 可能有 reasoning_content
        if use_thinking and hasattr(response.choices[0].message, 'reasoning_content'):
            reasoning = response.choices[0].message.reasoning_content
            logger.debug(f"Reasoning 過程: {reasoning[:500]}..." if reasoning else "無 reasoning")
        
        return response.choices[0].message.content
    
    def start_chat(self, history: List[Dict]) -> 'DeepSeekChatSession':
        return DeepSeekChatSession(self.client, self.FAST_MODEL, history)


class DeepSeekChatSession:
    """DeepSeek 聊天會話（使用 Fast Model）"""
    
    def __init__(self, client, model: str, history: List[Dict]):
        self.client = client
        self.model = model
        self.messages = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("parts", [msg.get("content", "")])[0] if isinstance(msg.get("parts"), list) else msg.get("content", "")
            self.messages.append({"role": role, "content": content})
    
    def send_message(self, message: str) -> 'DeepSeekResponse':
        self.messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            max_tokens=4096
        )
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        return DeepSeekResponse(assistant_message)


class DeepSeekResponse:
    """DeepSeek 回應包裝器"""
    def __init__(self, text: str):
        self.text = text


class GeminiProvider(AIProvider):
    """Google Gemini API 提供商 - 支援雙模型"""
    
    # 模型配置
    FAST_MODEL = "gemini-2.0-flash"  # 快速對話
    THINKING_MODEL = "gemini-2.0-flash-thinking-exp-01-21"  # 思考型模型
    
    def __init__(self, api_key: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai
        
        # 初始化 Fast 模型
        self.fast_model = genai.GenerativeModel(self.FAST_MODEL)
        
        # 嘗試初始化 Thinking 模型（兼容舊版本 SDK）
        try:
            # 新版 SDK 支持 ThinkingConfig
            if hasattr(genai, 'ThinkingConfig'):
                self.thinking_model = genai.GenerativeModel(
                    self.THINKING_MODEL,
                    generation_config=genai.GenerationConfig(
                        thinking_config=genai.ThinkingConfig(thinking_budget=8192)
                    )
                )
            else:
                # 舊版 SDK，使用相同模型但不設定 thinking_config
                self.thinking_model = genai.GenerativeModel(self.THINKING_MODEL)
        except Exception as e:
            logger.warning(f"Thinking 模型初始化失敗，使用 Fast 模型替代: {e}")
            self.thinking_model = self.fast_model
            
        logger.info(f"Gemini 初始化完成 (Fast: {self.FAST_MODEL})")
    
    def generate_content(self, prompt: str, use_thinking: bool = False) -> str:
        model = self.thinking_model if use_thinking else self.fast_model
        logger.debug(f"使用模型: {'Thinking' if use_thinking else 'Fast'}")
        
        response = model.generate_content(prompt)
        
        # Thinking model 可能有 thoughts
        if use_thinking and hasattr(response, 'candidates') and response.candidates:
            for part in response.candidates[0].content.parts:

                if hasattr(part, 'thought') and part.thought:
                    logger.debug(f"Thinking 過程: {part.text[:500]}...")
        
        return response.text
    
    def start_chat(self, history: List[Dict]) -> Any:
        return self.fast_model.start_chat(history=history)


class AICoach:
    """AI 交易教練 - 支援多個 AI 提供商，雙模型架構
    
    模型使用策略：
    - Thinking Model: 每日報告、績效評估、策略建議、錯誤分析
    - Fast Model: 一般對話、快速回應
    """

    def __init__(self, api_key: str = None, provider: str = None, logger: Optional[logging.Logger] = None):
        """
        初始化 AI 教練

        Args:
            api_key: API Key（若為 None 則從環境變數讀取）
            provider: 強制使用的提供商 ('deepseek' 或 'gemini')
            logger: 日誌記錄器
        """
        self.provider: AIProvider = None
        self.provider_name: str = ""
        self.logger = logger or logging.getLogger(__name__)
        
        # 嘗試初始化 DeepSeek（優先）
        deepseek_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key and (provider is None or provider == 'deepseek'):
            try:
                self.provider = DeepSeekProvider(deepseek_key)
                self.provider_name = "DeepSeek"
                self.logger.info(f"AI Coach 使用 {self.provider_name}")
                return
            except ImportError:
                pass  # openai 套件未安裝，嘗試 Gemini
            except Exception as e:
                self.logger.warning(f"DeepSeek 初始化失敗: {e}")
        
        # 嘗試初始化 Gemini（備用）
        gemini_key = api_key or os.getenv('GEMINI_API_KEY')
        if gemini_key and (provider is None or provider == 'gemini'):
            try:
                self.provider = GeminiProvider(gemini_key)
                self.provider_name = "Gemini"
                self.logger.info(f"AI Coach 使用 {self.provider_name}")
                return
            except ImportError:
                pass  # google-generativeai 套件未安裝
            except Exception as e:
                self.logger.warning(f"Gemini 初始化失敗: {e}")
        
        # 都失敗了
        raise ValueError(
            "請提供 DEEPSEEK_API_KEY 或 GEMINI_API_KEY 環境變數。\n"
            "DeepSeek: https://platform.deepseek.com/\n"
            "Gemini: https://makersuite.google.com/app/apikey"
        )

    def start_review_session(self,
                             analysis_context: str,
                             trade_data: str,
                             ohlc_summary: str,
                             global_context: str = "") -> str:
        """
        開始交易檢討會話（AI 主動提問）

        Args:
            analysis_context: Python 規則引擎的分析結果
            trade_data: 交易數據摘要
            ohlc_summary: K 線數據摘要
            global_context: 過去的對話記憶摘要（可選）

        Returns:
            AI 的首次提問
        """
        system_prompt = f"""你是一位資深交易教練，專精於日內交易心理分析。
你的任務是幫助交易者從過去的交易中學習，特別關注「情緒」和「心理狀態」對決策的影響。

你的風格：
1. 不批判，而是引導反思
2. 提出開放式問題，讓交易者自己發現問題
3. 特別關注「追高」和「殺低」背後的心理因素
4. 用同理心理解交易者當時的處境

這是你與該交易者過去的互動記憶（請參考此脈絡來提供更個人化的指導）：
{global_context}

現在，請根據以下分析結果，向交易者提出第一個引導性問題。
"""

        user_message = f"""
## Python 分析引擎報告：
{analysis_context}

## 交易數據：
{trade_data}

## K 線數據摘要：
{ohlc_summary}

請根據這些資訊，向交易者提出一個開放式問題，引導他們反思當時的決策和心理狀態。
"""

        return self.provider.generate_content(system_prompt + user_message)

    def continue_conversation(self,
                              chat_history: List[Dict[str, str]],
                              user_message: str) -> str:
        """
        延續交易檢討對話

        Args:
            chat_history: 對話歷史列表，每項包含 role 和 content
            user_message: 使用者的新訊息

        Returns:
            AI 的回應
        """
        # 建立系統提示
        system_context = """你是一位同理心強的交易教練。根據對話歷史，繼續引導交易者反思。
記住：你的目標是幫助他們找到「關鍵教訓」(Key Takeaway)。"""

        # 組合對話歷史
        messages = []
        for msg in chat_history:
            messages.append({
                "role": "user" if msg['role'] == 'user' else "model",
                "parts": [msg['content']]
            })

        # 加入新訊息
        messages.append({
            "role": "user",
            "parts": [user_message]
        })

        chat = self.provider.start_chat(messages[:-1])
        response = chat.send_message(user_message)

        return response.text

    def generate_strategy_advice(self,
                                 position_data: Dict[str, Any],
                                 market_data: Dict[str, Any],
                                 scenario: Dict[str, Any],
                                 recommended_strategies: List[str]) -> str:
        """
        生成選擇權策略建議

        Args:
            position_data: 持倉資訊（持股數、成本）
            market_data: 市場資訊（當前價格、IV）
            scenario: 情境資訊（目標、即將發生的事件）
            recommended_strategies: Python 引擎推薦的策略列表

        Returns:
            詳細的策略分析與建議
        """
        prompt = f"""你是一位資深選擇權策略師。請基於以下資訊，提供詳細的策略建議。

## 當前持倉：
- 持股數：{position_data.get('quantity', 0)}
- 平均成本：${position_data.get('avg_cost', 0)}
- 當前市價：${market_data.get('current_price', 0)}
- 30 天 IV：{market_data.get('iv_30', 'N/A')}%

## 目標與情境：
- 主要目標：{scenario.get('goal', '未指定')}
- 即將發生的事件：{scenario.get('upcoming_events', '無')}

## Python 引擎推薦的策略：
{', '.join(recommended_strategies) if recommended_strategies else '無推薦'}

請提供：
1. 策略比較：詳細比較推薦策略的優缺點
2. IV 影響分析：解釋當前 IV 水平對策略選擇的影響
3. 風險收益權衡：說明每種策略的最大風險與潛在收益
4. 具體建議：基於情境給出你的推薦

請用簡潔、具體的語言回答。
"""

        # 策略建議使用 Thinking Model 進行深度分析
        return self.provider.generate_content(prompt, use_thinking=True)

    def generate_performance_review(self, stats: Dict[str, Any], insights: str) -> str:
        """
        生成績效總評與改進建議

        Args:
            stats: 統計數據（勝率、獲利因子等）
            insights: 數據洞察（例如：最差時段、最弱標的）

        Returns:
            AI 的績效評語與建議
        """
        prompt = f"""你是一位績效教練。請基於以下交易統計，提供坦誠但建設性的績效評估。

## 關鍵績效指標：
- 總盈虧：${stats.get('total_pnl', 0):,.2f}
- 勝率：{stats.get('win_rate', 0):.1f}%
- 平均獲利：${stats.get('avg_win', 0):,.2f}
- 平均虧損：${stats.get('avg_loss', 0):,.2f}
- 獲利因子：{stats.get('profit_factor', 0):.2f}
- 總交易次數：{stats.get('total_trades', 0)}

## 數據洞察：
{insights}

請提供：
1. 核心問題診斷：找出最嚴重的交易缺陷（例如：平均虧損遠大於平均獲利）
2. 風險管理建議：具體的部位控制或停損建議
3. 情緒紀律建議：如何避免情緒化交易
4. 3 個可立即執行的改進行動

請用直接、可執行的語言，不要空泛的鼓勵。
"""

        # 績效評估使用 Thinking Model 進行深度分析
        return self.provider.generate_content(prompt, use_thinking=True)

    def summarize_key_takeaway(self, conversation: str) -> str:
        """
        總結對話中的關鍵教訓
        
        Args:
            conversation: 完整對話內容
            
        Returns:
            簡潔的關鍵教訓摘要
        """
        prompt = f"""請閱讀以下交易檢討對話，用 1-2 句話總結「關鍵教訓」(Key Takeaway)。

對話內容：
{conversation}

請提供簡潔但深刻的總結，聚焦於交易者需要改進的核心行為或心理模式。
"""

        return self.provider.generate_content(prompt)

    def detect_mistakes(self, conversation: str) -> List[Dict[str, Any]]:
        """
        從對話中偵測並提取交易錯誤

        Args:
            conversation: 完整對話內容

        Returns:
            錯誤列表，每項包含 error_type, description, ai_analysis
        """
        prompt = f"""請分析以下交易檢討對話，判斷交易者是否承認或被發現犯了特定的交易錯誤。
如果有的話，請提取出來並格式化為 JSON。

對話內容：
{conversation}

常見錯誤類型參考：
- FOMO (追高)
- Panic Selling (殺低/恐慌)
- Revenge Trading (報復性交易)
- Overtrading (過度交易)
- Averaging Down (凹單/攤平)
- Catching a Falling Knife (接刀)
- No Plan (憑感覺/無計畫)
- Poor Risk Management (部位過大/不止損)

請回傳一個 JSON 列表 (Array of Objects)，格式如下：
[
  {{
    "error_type": "錯誤類型 (請使用上述英文術語或中文)",
    "description": "錯誤的具體描述 (例如：在股價急漲時因為怕錯過而市價追入)",
    "ai_analysis": "簡短的改進建議"
  }}
]

如果沒有發現明顯錯誤，請回傳空列表 []。
**只回傳 JSON 字串，不要有其他文字或 Markdown 標記。**
"""
        try:
            # 錯誤分析使用 Thinking Model
            text = self.provider.generate_content(prompt, use_thinking=True).strip()
            # 清理 markdown 標記
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            import json
            return json.loads(text)
        except Exception as e:
            print(f"Error parsing mistakes: {e}")
            return []

    def get_scaling_advice(self, symbol: str, current_price: float, avg_cost: float, position_size: int, market_data_str: str) -> Dict[str, Any]:
        """
        分析分批建倉與風險管理點位
        """
        prompt = f"""
        Role: Senior Quantitative Trader
        Task: Analyze {symbol} for scaling-in (adding position) and risk management.
        
        Current Market Data:
        - Symbol: {symbol}
        - Current Price: ${current_price}
        - My Avg Cost: ${avg_cost}
        - Position Size: {position_size}
        
        Recent Price Action:
        {market_data_str}
        
        Based on Technical Analysis (Support/Resistance, Volatility, Trend):
        1. Identify the best PRICE LEVEL to ADD to the position (Scale In).
        2. Identify the best PRICE LEVEL to TAKE PROFIT (Target).
        3. Identify the STOP LOSS level.
        
        Output strictly in JSON format (no markdown, no other text):
        {{
            "add_price": "price value (number only)",
            "target_price": "price value (number only)",
            "stop_loss": "price value (number only)",
            "reasoning": "Very brief strategy (max 15 words)"
        }}
        """
        
        try:
            # 點位分析使用 Thinking Model
            text = self.provider.generate_content(prompt, use_thinking=True).strip()
            # 移除可能的 markdown 標記
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            import json
            return json.loads(text.strip())
        except Exception as e:
            print(f"AI Scaling Advice Error: {e}")
            return {
                "add_price": "N/A",
                "target_price": "N/A",
                "stop_loss": "N/A",
                "reasoning": "Analysis failed"
            }

    def get_batch_scaling_advice(self, positions_data: list) -> dict:
        """
        批量分析多個標的的點位建議 (節省 Token)
        positions_data: list of dicts [{'symbol':..., 'current_price':..., 'avg_cost':..., 'position_size':..., 'market_context':...}]
        """
        import json
        
        # 簡化數據以減少 Token (移除過於詳細的歷史數據，只保留摘要)
        prompt_data = []
        for p in positions_data:
            prompt_data.append({
                "symbol": p['symbol'],
                "price": p['current_price'],
                "cost": p['avg_cost'],
                "pos": p['position_size'],
                "trend": p['market_context'][-100:] # 只取最後 100 字元作為趨勢摘要
            })
            
        data_str = json.dumps(prompt_data, indent=2)
        
        prompt = f"""
        Role: Senior Quantitative Trader
        Task: Analyze multiple positions for scaling-in and risk management.
        
        Positions Data:
        {data_str}
        
        For EACH position, based on Technical Analysis:
        1. Best PRICE to ADD (Scale In).
        2. Best PRICE to TAKE PROFIT (Target).
        3. STOP LOSS level.
        
        Output strictly in JSON format (key = symbol):
        {{
            "SYMBOL1": {{
                "add_price": "price (number)",
                "target_price": "price (number)",
                "stop_loss": "price (number)",
                "reasoning": "brief strategy (max 10 words)"
            }},
            ...
        }}
        """
        
        try:
            # 批量點位分析使用 Thinking Model
            text = self.provider.generate_content(prompt, use_thinking=True).strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            return json.loads(text.strip())
        except Exception as e:
            print(f"Batch AI Advice Error: {e}")
            return {}

    def chat(self, prompt: str) -> str:
        """
        通用對話方法 (使用 Fast Model)
        
        Args:
            prompt: 提示詞
            
        Returns:
            AI 回應
        """
        try:
            return self.provider.generate_content(prompt, use_thinking=False)
        except Exception as e:
            return f"AI 對話發生錯誤: {str(e)}"

    def analyze(self, prompt: str) -> str:
        """
        深度分析方法 (使用 Thinking Model)
        
        適用場景：
        - 每日報告生成
        - 綜合審查
        - 策略建議
        - 錯誤分析
        
        Args:
            prompt: 提示詞
            
        Returns:
            AI 深度分析結果
        """
        try:
            return self.provider.generate_content(prompt, use_thinking=True)
        except Exception as e:
            return f"AI 分析發生錯誤: {str(e)}"
