"""
認證服務模組

提供用戶認證、JWT token 管理功能。
用戶資料存儲在資料庫中。
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# JWT 密鑰（從環境變數讀取，否則生成隨機密鑰）
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 天


def hash_password(password: str) -> str:
    """密碼雜湊"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """驗證密碼"""
    return hash_password(password) == password_hash


def init_users_table(db):
    """初始化用戶資料表"""
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    
    # 檢查是否有用戶，如果沒有則創建預設用戶
    existing = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing == 0:
        default_password = os.getenv('DEFAULT_USER_PASSWORD', '!Trade346')
        create_user(db, 'ben', default_password, 'Ben')
        logger.info("已創建預設用戶: ben")


def create_user(db, username: str, password: str, display_name: str) -> Optional[str]:
    """
    創建用戶
    
    Returns:
        user_id 如果成功，否則 None
    """
    user_id = f"user_{username.lower()}"
    password_hash = hash_password(password)
    
    try:
        db.execute('''
            INSERT INTO users (user_id, username, password_hash, display_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username.lower(), password_hash, display_name))
        db.commit()
        logger.info(f"用戶已創建: {username}")
        return user_id
    except Exception as e:
        logger.error(f"創建用戶失敗: {e}")
        return None


def get_user(db, username: str) -> Optional[Dict[str, Any]]:
    """
    獲取用戶（不區分大小寫）
    """
    username_lower = username.lower()
    row = db.execute(
        'SELECT user_id, username, password_hash, display_name, created_at FROM users WHERE username = ?',
        (username_lower,)
    ).fetchone()
    
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'password_hash': row[2],
            'display_name': row[3],
            'created_at': row[4]
        }
    return None


def get_user_by_id(db, user_id: str) -> Optional[Dict[str, Any]]:
    """
    根據 user_id 獲取用戶
    """
    row = db.execute(
        'SELECT user_id, username, password_hash, display_name, created_at FROM users WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'password_hash': row[2],
            'display_name': row[3],
            'created_at': row[4]
        }
    return None


def authenticate_user(db, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    驗證用戶名和密碼
    
    Args:
        db: 資料庫連接
        username: 用戶名（不區分大小寫）
        password: 密碼
        
    Returns:
        用戶資料如果驗證成功，否則 None
    """
    user = get_user(db, username)
    if not user:
        logger.warning(f"登入失敗: 用戶不存在 - {username}")
        return None
    
    if not verify_password(password, user['password_hash']):
        logger.warning(f"登入失敗: 密碼錯誤 - {username}")
        return None
    
    logger.info(f"用戶登入成功: {username}")
    return user


def change_password(db, user_id: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    修改密碼
    
    Returns:
        (success, message)
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False, "用戶不存在"
    
    if not verify_password(old_password, user['password_hash']):
        return False, "舊密碼錯誤"
    
    if len(new_password) < 6:
        return False, "新密碼長度至少 6 個字元"
    
    new_hash = hash_password(new_password)
    try:
        db.execute(
            'UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
            (new_hash, user_id)
        )
        db.commit()
        logger.info(f"用戶密碼已更新: {user_id}")
        return True, "密碼修改成功"
    except Exception as e:
        logger.error(f"修改密碼失敗: {e}")
        return False, "密碼修改失敗"


def create_access_token(user: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    創建 JWT access token
    """
    import jwt
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    
    payload = {
        "sub": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    驗證 JWT token
    
    Returns:
        token payload 如果有效，否則 None
    """
    import jwt
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token 已過期")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"無效的 token: {e}")
        return None


def get_current_user_id(token: str) -> Optional[str]:
    """
    從 token 獲取當前用戶 ID
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None
