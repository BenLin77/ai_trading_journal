import requests
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram 通知服務"""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = self.BASE_URL.format(token=token)
        
    def get_me(self) -> Dict[str, Any]:
        """驗證 Token 並獲取 Bot 資訊"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Telegram getMe failed: {e}")
            raise Exception(f"無法連接 Telegram API: {str(e)}")

    def get_updates(self) -> List[Dict[str, Any]]:
        """獲取最新訊息（用於自動抓取 Chat ID）"""
        try:
            response = requests.get(f"{self.base_url}/getUpdates", timeout=10)
            response.raise_for_status()
            result = response.json()
            if not result.get('ok'):
                raise Exception(result.get('description', 'Unknown error'))
            return result.get('result', [])
        except Exception as e:
            logger.error(f"Telegram getUpdates failed: {e}")
            raise

    def send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown') -> bool:
        """
        發送訊息，自動處理長文本切分
        
        Telegram 限制：
        - 單條訊息上限 4096 字元
        - 標題 + 內文需注意 Markdown 格式閉合
        """
        if not text:
            return False
            
        # 簡單切分邏輯：如果超過 4000 字元，按段落切分
        MAX_LENGTH = 4000
        
        messages = []
        if len(text) <= MAX_LENGTH:
            messages.append(text)
        else:
            # 遞迴切分
            current_chunk = ""
            lines = text.split('\n')
            
            for line in lines:
                if len(current_chunk) + len(line) + 1 > MAX_LENGTH:
                    messages.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"
            
            if current_chunk:
                messages.append(current_chunk)
        
        success = True
        for msg in messages:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": msg,
                    # 如果 AI 輸出的 Markdown 不完美（例如包含未轉義的字符），Markdown 模式可能會報錯
                    # 這裡可以做 failover：如果 Markdown 失敗，嘗試純文字
                    "parse_mode": parse_mode
                }
                
                response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=30)
                
                if not response.ok:
                    # 如果是格式錯誤，嘗試純文字發送
                    if "can't parse entities" in response.text:
                        logger.warning("Telegram Markdown parse failed, retrying with plain text")
                        payload.pop("parse_mode")
                        response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=30)
                
                response.raise_for_status()
                # 避免發送太快被限流
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to send Telegram message chunk: {e}")
                success = False
                
        return success
