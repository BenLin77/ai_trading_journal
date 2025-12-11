"""
浮動 AI 聊天元件

功能：
1. 右下角浮動按鈕
2. 點擊展開/收合聊天視窗
3. 對話歷史保存到資料庫
"""

import streamlit as st
from datetime import datetime
from typing import Optional


def inject_floating_chat_css():
    """注入浮動聊天按鈕的 CSS 樣式"""
    st.markdown("""
    <style>
    /* 浮動聊天按鈕容器 */
    .floating-chat-container {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 12px;
    }
    
    /* 聊天按鈕 */
    .chat-fab {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .chat-fab:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .chat-fab svg {
        width: 28px;
        height: 28px;
        fill: white;
    }
    
    /* 聊天視窗 */
    .chat-window {
        width: 380px;
        max-height: 500px;
        background: var(--background-color, #1a1a2e);
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    /* 聊天標題 */
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .chat-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
    }
    
    .chat-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 20px;
        opacity: 0.8;
        transition: opacity 0.2s;
    }
    
    .chat-close:hover {
        opacity: 1;
    }
    
    /* 聊天訊息區 */
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        max-height: 350px;
    }
    
    .chat-message {
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        align-items: flex-end;
    }
    
    .chat-message.assistant {
        align-items: flex-start;
    }
    
    .message-bubble {
        max-width: 85%;
        padding: 10px 14px;
        border-radius: 16px;
        font-size: 14px;
        line-height: 1.5;
    }
    
    .chat-message.user .message-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-right-radius: 4px;
    }
    
    .chat-message.assistant .message-bubble {
        background: var(--secondary-background-color, #16213e);
        color: var(--text-color, #e0e0e0);
        border-bottom-left-radius: 4px;
    }
    
    /* 輸入區 */
    .chat-input-area {
        padding: 12px 16px;
        border-top: 1px solid var(--border-color, #2a2a4a);
        display: flex;
        gap: 8px;
    }
    
    .chat-input {
        flex: 1;
        padding: 10px 14px;
        border: 1px solid var(--border-color, #2a2a4a);
        border-radius: 20px;
        background: var(--secondary-background-color, #16213e);
        color: var(--text-color, #e0e0e0);
        font-size: 14px;
        outline: none;
    }
    
    .chat-input:focus {
        border-color: #667eea;
    }
    
    .chat-send {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s;
    }
    
    .chat-send:hover {
        transform: scale(1.05);
    }
    
    .chat-send svg {
        width: 18px;
        height: 18px;
        fill: white;
    }
    
    /* 提示標籤 */
    .chat-tooltip {
        background: white;
        color: #333;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)


def render_floating_chat_button():
    """渲染浮動聊天按鈕（使用 Streamlit 原生元件）"""
    
    # 初始化 session state
    if 'floating_chat_open' not in st.session_state:
        st.session_state.floating_chat_open = False
    if 'floating_chat_messages' not in st.session_state:
        st.session_state.floating_chat_messages = []
    
    # 使用 sidebar 底部或 popover 來實現
    # 由於 Streamlit 限制，我們使用 expander 在側邊欄底部
    pass


def render_ai_chat_sidebar(db, ai_coach):
    """在側邊欄渲染 AI 聊天區塊"""
    
    if ai_coach is None:
        return
    
    # 初始化對話歷史
    if 'global_ai_chat' not in st.session_state:
        st.session_state.global_ai_chat = []
        # 從資料庫載入歷史對話
        try:
            history = db.get_global_chat_history(limit=20)
            if history:
                st.session_state.global_ai_chat = [
                    {'role': msg['role'], 'content': msg['content']}
                    for msg in history
                ]
        except Exception:
            pass
    
    with st.sidebar:
        st.markdown("---")
        
        # 使用 expander 作為聊天視窗
        with st.expander("💬 AI 教練對話", expanded=st.session_state.get('chat_expanded', False)):
            st.session_state.chat_expanded = True
            
            # 顯示對話歷史（最近 10 條）
            messages_to_show = st.session_state.global_ai_chat[-10:]
            
            chat_container = st.container(height=300)
            with chat_container:
                if not messages_to_show:
                    st.caption("👋 有任何交易問題都可以問我！")
                else:
                    for msg in messages_to_show:
                        with st.chat_message(msg['role']):
                            st.markdown(msg['content'])
            
            # 輸入區
            user_input = st.chat_input("詢問 AI 教練...", key="global_ai_input")
            
            if user_input:
                # 加入使用者訊息
                st.session_state.global_ai_chat.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # 儲存到資料庫
                try:
                    db.add_chat_message(
                        session_id='global_chat',
                        role='user',
                        content=user_input
                    )
                except Exception:
                    pass
                
                # 取得 AI 回應
                try:
                    # 構建上下文
                    context = "你是一位資深交易教練，正在與交易者進行對話。請用繁體中文回答，語言直接、具體。\n\n"
                    
                    # 加入最近對話
                    for msg in st.session_state.global_ai_chat[-5:]:
                        role = "交易者" if msg['role'] == 'user' else "AI教練"
                        context += f"{role}: {msg['content']}\n"
                    
                    response = ai_coach.chat(context)
                    
                    st.session_state.global_ai_chat.append({
                        'role': 'assistant',
                        'content': response
                    })
                    
                    # 儲存到資料庫
                    try:
                        db.add_chat_message(
                            session_id='global_chat',
                            role='assistant',
                            content=response
                        )
                    except Exception:
                        pass
                    
                except Exception as e:
                    st.error(f"AI 回應失敗: {e}")
                
                st.rerun()
            
            # 清除對話按鈕
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ 清除", key="clear_global_chat", use_container_width=True):
                    st.session_state.global_ai_chat = []
                    st.rerun()
            with col2:
                if st.button("📋 歷史", key="show_chat_history", use_container_width=True):
                    st.session_state.show_full_history = not st.session_state.get('show_full_history', False)
                    st.rerun()


def render_floating_chat_widget(db, ai_coach):
    """
    渲染浮動聊天小工具
    使用 Streamlit 的 popover 或自定義 HTML/JS
    """
    
    if ai_coach is None:
        return
    
    # 初始化
    if 'fc_messages' not in st.session_state:
        st.session_state.fc_messages = []
        # 載入歷史
        try:
            history = db.get_global_chat_history(limit=20)
            if history:
                st.session_state.fc_messages = [
                    {'role': msg['role'], 'content': msg['content']}
                    for msg in history
                ]
        except Exception:
            pass
    
    # 注入 CSS
    inject_floating_chat_css()
    
    # 使用 st.popover (Streamlit 1.33+)
    try:
        with st.popover("💬 AI 教練", use_container_width=False):
            st.markdown("### 🤖 AI 交易教練")
            st.caption("有任何交易問題都可以問我！")
            
            # 顯示對話
            chat_container = st.container(height=250)
            with chat_container:
                for msg in st.session_state.fc_messages[-8:]:
                    with st.chat_message(msg['role']):
                        st.markdown(msg['content'])
            
            # 輸入
            user_input = st.chat_input("輸入問題...", key="fc_input")
            
            if user_input:
                st.session_state.fc_messages.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # 儲存
                try:
                    db.add_chat_message('global_chat', 'user', user_input)
                except Exception:
                    pass
                
                # AI 回應
                try:
                    context = "你是資深交易教練，用繁體中文簡潔回答。\n\n"
                    for msg in st.session_state.fc_messages[-5:]:
                        role = "User" if msg['role'] == 'user' else "AI"
                        context += f"{role}: {msg['content']}\n"
                    
                    response = ai_coach.chat(context)
                    st.session_state.fc_messages.append({
                        'role': 'assistant',
                        'content': response
                    })
                    
                    try:
                        db.add_chat_message('global_chat', 'assistant', response)
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f"錯誤: {e}")
                
                st.rerun()
            
            if st.button("🗑️ 清除對話", use_container_width=True):
                st.session_state.fc_messages = []
                st.rerun()
                
    except Exception:
        # 如果 popover 不支援，使用側邊欄
        render_ai_chat_sidebar(db, ai_coach)
