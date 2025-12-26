"""
API 速率限制與成本控制模組

安全措施 #2 & #8:
- Rate Limit: 防止 API 被濫用
- 成本控制: 限制 AI API 的使用量，防止超額費用
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
from functools import wraps
from collections import defaultdict
import threading
from dataclasses import dataclass, field

# 從環境變數讀取限額設定
AI_DAILY_LIMIT = int(os.getenv('AI_DAILY_LIMIT', '100'))  # 每日 AI 請求上限
AI_HOURLY_LIMIT = int(os.getenv('AI_HOURLY_LIMIT', '20'))  # 每小時 AI 請求上限
API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '60'))  # 每分鐘 API 請求上限


@dataclass
class RateLimitState:
    """速率限制狀態"""
    requests: list = field(default_factory=list)
    daily_ai_calls: int = 0
    hourly_ai_calls: int = 0
    last_daily_reset: datetime = field(default_factory=datetime.now)
    last_hourly_reset: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """
    簡易速率限制器（In-Memory）
    
    生產環境建議使用 Redis 作為狀態存儲
    """
    
    def __init__(self):
        self._states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = threading.Lock()
        self._global_ai_daily = 0
        self._global_ai_hourly = 0
        self._last_global_daily_reset = datetime.now()
        self._last_global_hourly_reset = datetime.now()
    
    def _cleanup_old_requests(self, state: RateLimitState, window_seconds: int = 60):
        """清理過期的請求記錄"""
        now = time.time()
        state.requests = [t for t in state.requests if now - t < window_seconds]
    
    def _check_daily_reset(self):
        """檢查是否需要重置每日計數"""
        now = datetime.now()
        if now.date() > self._last_global_daily_reset.date():
            self._global_ai_daily = 0
            self._last_global_daily_reset = now
    
    def _check_hourly_reset(self):
        """檢查是否需要重置每小時計數"""
        now = datetime.now()
        if now - self._last_global_hourly_reset > timedelta(hours=1):
            self._global_ai_hourly = 0
            self._last_global_hourly_reset = now
    
    def check_rate_limit(self, identifier: str, limit: int = API_RATE_LIMIT, window_seconds: int = 60) -> tuple[bool, int]:
        """
        檢查一般 API 速率限制
        
        Args:
            identifier: 用戶識別符（IP 或 user_id）
            limit: 時間窗口內允許的最大請求數
            window_seconds: 時間窗口（秒）
            
        Returns:
            (is_allowed, remaining): 是否允許請求，以及剩餘配額
        """
        with self._lock:
            state = self._states[identifier]
            self._cleanup_old_requests(state, window_seconds)
            
            if len(state.requests) >= limit:
                return False, 0
            
            state.requests.append(time.time())
            remaining = limit - len(state.requests)
            return True, remaining
    
    def check_ai_limit(self) -> tuple[bool, Dict[str, int]]:
        """
        檢查 AI API 使用限額
        
        Returns:
            (is_allowed, stats): 是否允許請求，以及使用統計
        """
        with self._lock:
            self._check_daily_reset()
            self._check_hourly_reset()
            
            stats = {
                'daily_used': self._global_ai_daily,
                'daily_limit': AI_DAILY_LIMIT,
                'daily_remaining': AI_DAILY_LIMIT - self._global_ai_daily,
                'hourly_used': self._global_ai_hourly,
                'hourly_limit': AI_HOURLY_LIMIT,
                'hourly_remaining': AI_HOURLY_LIMIT - self._global_ai_hourly,
            }
            
            if self._global_ai_daily >= AI_DAILY_LIMIT:
                return False, stats
            
            if self._global_ai_hourly >= AI_HOURLY_LIMIT:
                return False, stats
            
            return True, stats
    
    def record_ai_call(self):
        """記錄一次 AI API 呼叫"""
        with self._lock:
            self._check_daily_reset()
            self._check_hourly_reset()
            self._global_ai_daily += 1
            self._global_ai_hourly += 1
    
    def get_ai_usage_stats(self) -> Dict[str, int]:
        """取得 AI API 使用統計"""
        with self._lock:
            self._check_daily_reset()
            self._check_hourly_reset()
            
            return {
                'daily_used': self._global_ai_daily,
                'daily_limit': AI_DAILY_LIMIT,
                'daily_remaining': AI_DAILY_LIMIT - self._global_ai_daily,
                'hourly_used': self._global_ai_hourly,
                'hourly_limit': AI_HOURLY_LIMIT,
                'hourly_remaining': AI_HOURLY_LIMIT - self._global_ai_hourly,
            }


# 全域單例
rate_limiter = RateLimiter()


def rate_limit(limit: int = API_RATE_LIMIT, window_seconds: int = 60):
    """
    速率限制裝飾器
    
    用法：
        @rate_limit(limit=30, window_seconds=60)
        async def my_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Request, HTTPException
            
            # 嘗試從 kwargs 取得 request
            request = kwargs.get('request')
            if not request:
                # 從 args 尋找 Request 物件
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                # 使用客戶端 IP 作為識別符
                client_ip = request.client.host if request.client else 'unknown'
                identifier = f"{client_ip}:{func.__name__}"
                
                is_allowed, remaining = rate_limiter.check_rate_limit(identifier, limit, window_seconds)
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Too Many Requests",
                            "message": f"請求過於頻繁，請在 {window_seconds} 秒後重試",
                            "retry_after": window_seconds
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def ai_rate_limit():
    """
    AI API 使用限額裝飾器
    
    用法：
        @ai_rate_limit()
        async def ai_chat_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import HTTPException
            
            is_allowed, stats = rate_limiter.check_ai_limit()
            
            if not is_allowed:
                if stats['daily_remaining'] <= 0:
                    message = f"已達每日 AI 使用上限 ({stats['daily_limit']} 次)，請明天再試"
                else:
                    message = f"已達每小時 AI 使用上限 ({stats['hourly_limit']} 次)，請稍後再試"
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "AI Rate Limit Exceeded",
                        "message": message,
                        "stats": stats
                    }
                )
            
            # 執行原函數
            result = await func(*args, **kwargs)
            
            # 成功後記錄使用
            rate_limiter.record_ai_call()
            
            return result
        return wrapper
    return decorator
