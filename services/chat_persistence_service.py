"""
AI 對話持久化服務

功能：
1. 將對話歷史保存到資料庫
2. 當對話過長時，自動轉存到 MD 檔案
3. 提供對話摘要功能

使用方式：
    service = ChatPersistenceService(db)
    service.save_message(session_id, role, content)
    service.archive_if_needed(session_id)
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 存檔閾值配置
MAX_MESSAGES_BEFORE_ARCHIVE = 50  # 超過 50 條訊息時觸發存檔
MAX_CHARS_BEFORE_ARCHIVE = 50000  # 超過 50000 字元時觸發存檔
KEEP_RECENT_AFTER_ARCHIVE = 20    # 存檔後保留最近 20 條訊息

# 存檔目錄
CHAT_ARCHIVE_DIR = Path(__file__).parent.parent / "reports" / "chat_archives"


class ChatPersistenceService:
    """AI 對話持久化服務"""
    
    def __init__(self, db):
        """
        初始化服務
        
        Args:
            db: TradingDatabase 實例
        """
        self.db = db
        self._ensure_archive_dir()
    
    def _ensure_archive_dir(self):
        """確保存檔目錄存在"""
        CHAT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    def save_message(self, session_id: str, role: str, content: str) -> bool:
        """
        保存對話訊息
        
        Args:
            session_id: 會話 ID
            role: 角色 (user/assistant)
            content: 訊息內容
            
        Returns:
            True 如果成功
        """
        try:
            self.db.add_chat_message(session_id, role, content)
            
            # 檢查是否需要存檔
            self._check_and_archive(session_id)
            
            return True
        except Exception as e:
            logger.error(f"保存對話訊息失敗: {e}")
            return False
    
    def _check_and_archive(self, session_id: str):
        """
        檢查是否需要存檔，如果需要則執行
        
        Args:
            session_id: 會話 ID
        """
        stats = self.db.get_chat_session_stats(session_id)
        
        message_count = stats.get('message_count', 0)
        total_chars = stats.get('total_chars', 0)
        
        if message_count > MAX_MESSAGES_BEFORE_ARCHIVE or total_chars > MAX_CHARS_BEFORE_ARCHIVE:
            logger.info(f"會話 {session_id} 超過閾值 (訊息: {message_count}, 字元: {total_chars})，執行存檔")
            self.archive_session(session_id)
    
    def archive_session(self, session_id: str, force: bool = False) -> Optional[str]:
        """
        將對話存檔到 MD 檔案
        
        Args:
            session_id: 會話 ID
            force: 強制存檔（忽略閾值）
            
        Returns:
            存檔檔案路徑，或 None 如果失敗
        """
        try:
            # 取得完整對話歷史
            messages = self.db.get_chat_history(session_id)
            
            if not messages:
                return None
            
            # 生成 MD 內容
            md_content = self._generate_markdown(session_id, messages)
            
            # 生成檔名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            short_session = session_id[:8] if len(session_id) > 8 else session_id
            filename = f"chat_{short_session}_{timestamp}.md"
            filepath = CHAT_ARCHIVE_DIR / filename
            
            # 寫入檔案
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"對話已存檔: {filepath}")
            
            # 記錄存檔路徑
            self.db.archive_chat_session(session_id, str(filepath))
            
            # 刪除舊訊息，保留最近的
            deleted = self.db.delete_old_chat_messages(session_id, KEEP_RECENT_AFTER_ARCHIVE)
            logger.info(f"已刪除 {deleted} 條舊訊息，保留最近 {KEEP_RECENT_AFTER_ARCHIVE} 條")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"存檔對話失敗: {e}")
            return None
    
    def _generate_markdown(self, session_id: str, messages: List[Dict]) -> str:
        """
        生成 Markdown 格式的對話記錄
        
        Args:
            session_id: 會話 ID
            messages: 對話訊息列表
            
        Returns:
            Markdown 字串
        """
        lines = [
            f"# AI 對話記錄",
            f"",
            f"**會話 ID**: `{session_id}`",
            f"**匯出時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**訊息數量**: {len(messages)}",
            f"",
            f"---",
            f""
        ]
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # 格式化角色標題
            if role == 'user':
                role_display = "👤 使用者"
            elif role == 'assistant':
                role_display = "🤖 AI 助手"
            else:
                role_display = f"❓ {role}"
            
            lines.append(f"### {role_display}")
            lines.append(f"*{timestamp}*")
            lines.append(f"")
            lines.append(content)
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        
        return "\n".join(lines)
    
    def get_session_history_with_archives(self, session_id: str) -> Dict[str, Any]:
        """
        取得會話歷史（包含存檔資訊）
        
        Args:
            session_id: 會話 ID
            
        Returns:
            包含 messages 和 archives 的字典
        """
        messages = self.db.get_chat_history(session_id)
        
        # 檢查是否有存檔
        archive_path = self.db.get_setting(f'chat_archive_{session_id}')
        
        return {
            'messages': messages,
            'archive_path': archive_path,
            'has_archive': archive_path is not None
        }
    
    def list_all_archives(self) -> List[Dict[str, Any]]:
        """
        列出所有存檔檔案
        
        Returns:
            存檔資訊列表
        """
        archives = []
        
        if CHAT_ARCHIVE_DIR.exists():
            for filepath in CHAT_ARCHIVE_DIR.glob("chat_*.md"):
                stat = filepath.stat()
                archives.append({
                    'filename': filepath.name,
                    'path': str(filepath),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # 按修改時間排序（最新的在前）
        archives.sort(key=lambda x: x['modified'], reverse=True)
        
        return archives


def get_chat_context_for_ai(db, session_id: str, max_messages: int = 20) -> str:
    """
    為 AI 準備對話上下文（包含歷史摘要）
    
    Args:
        db: TradingDatabase 實例
        session_id: 會話 ID
        max_messages: 最大訊息數量
        
    Returns:
        格式化的上下文字串
    """
    messages = db.get_chat_history(session_id)
    
    if not messages:
        return ""
    
    # 如果訊息太多，只取最近的
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    context_parts = ["以下是之前的對話記錄："]
    
    for msg in recent_messages:
        role = "使用者" if msg['role'] == 'user' else "AI"
        content = msg['content']
        
        # 截斷過長的訊息
        if len(content) > 500:
            content = content[:500] + "...(已截斷)"
        
        context_parts.append(f"{role}: {content}")
    
    return "\n".join(context_parts)
