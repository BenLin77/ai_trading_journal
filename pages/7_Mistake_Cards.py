"""
錯誤卡片 (Mistake Cards)

功能：
1. 顯示從 AI 檢討中自動提取的錯誤
2. 錯誤類型統計與分析
3. 常見交易錯誤知識庫 (PTT 鄉民智慧)
4. PTT 發文模板生成
"""

import streamlit as st
import pandas as pd
from database import TradingDatabase
import plotly.express as px

# 頁面配置
st.set_page_config(
    page_title="錯誤卡片",
    page_icon="🃏",
    layout="wide"
)

st.title("🃏 錯誤卡片牆")
st.markdown("紀錄與反思每一次的「學費」，避免重蹈覆轍。")
st.markdown("---")

# 初始化
@st.cache_resource
def init_db():
    return TradingDatabase()

db = init_db()

# 1. 錯誤統計概覽
st.subheader("📊 錯誤分析")

mistake_stats = db.get_mistake_stats()

if not mistake_stats:
    st.info("目前還沒有紀錄到錯誤卡片。請在「交易檢討」頁面與 AI 教練對話，系統會自動偵測並記錄你的交易失誤。")
else:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 繪製長條圖
        df_stats = pd.DataFrame(list(mistake_stats.items()), columns=['錯誤類型', '次數'])
        df_stats = df_stats.sort_values('次數', ascending=True)
        
        fig = px.bar(
            df_stats, 
            x='次數', 
            y='錯誤類型', 
            orientation='h',
            title="錯誤類型排行榜",
            color='次數',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        total_mistakes = sum(mistake_stats.values())
        st.metric("累積錯誤總數", total_mistakes)
        
        most_common = max(mistake_stats, key=mistake_stats.get)
        st.metric("頭號敵人", most_common, f"{mistake_stats[most_common]} 次", delta_color="inverse")

# 2. 錯誤卡片展示
st.markdown("---")
st.subheader("🗂️ 我的錯誤收藏")

mistakes = db.get_mistakes(limit=50)

if mistakes:
    # CSS for cards
    st.markdown("""
    <style>
    .mistake-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #1e1e1e;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .mistake-type {
        background-color: #ff4b4b;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .mistake-pnl {
        color: #ff4b4b;
        font-weight: bold;
        font-size: 1.1em;
    }
    </style>
    """, unsafe_allow_html=True)

    # Grid layout
    cols = st.columns(3)
    
    for i, mistake in enumerate(mistakes):
        with cols[i % 3]:
            pnl_display = f"-${abs(mistake['pnl']):,.2f}" if mistake['pnl'] < 0 else "N/A"
            
            st.markdown(f"""
            <div class="mistake-card">
                <div class="mistake-type">{mistake['error_type']}</div>
                <h4>{mistake['symbol']} <span style="font-size:0.8em; color:#888;">{mistake['date']}</span></h4>
                <p class="mistake-pnl">損失：{pnl_display}</p>
                <p><strong>錯誤：</strong>{mistake['description']}</p>
                <p><strong>AI 建議：</strong>{mistake['ai_analysis']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 回顧操作細節
            with st.expander("🔍 回顧操作細節"):
                # 查詢該標的在該日期的所有交易
                # 注意：這裡假設日期格式為 YYYY-MM-DD
                # 資料庫查詢使用 >= start_date AND <= end_date
                # 為了包含當天所有時間，我們查詢當天
                
                # 簡單處理：直接使用該日期作為開始和結束
                # 如果資料庫 datetime 是 "2023-10-27 09:30:00"，
                # get_trades 的 SQL 是 datetime >= ? AND datetime <= ?
                # 如果傳入 "2023-10-27"，會變成 "2023-10-27" <= "2023-10-27 09:30:00" (True)
                # 但 datetime <= "2023-10-27" 會變成 "2023-10-27 09:30:00" <= "2023-10-27" (False)
                # 所以需要調整結束日期為隔天，或模糊查詢
                
                # 這裡我們先嘗試用模糊查詢的方式，或者在 application level 過濾
                # 為了方便，我們調用 db.get_trades 時，end_date 設為隔天
                try:
                    date_obj = pd.to_datetime(mistake['date'])
                    next_day = (date_obj + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    trades = db.get_trades(
                        symbol=mistake['symbol'],
                        start_date=mistake['date'],
                        end_date=next_day
                    )
                    
                    # 過濾掉隔天的（如果有的話，雖然 get_trades 是 datetime 字串比較）
                    # 嚴格來說應該是 < next_day，但 get_trades 是 <=
                    # 暫時這樣應該足夠顯示當天交易
                    
                    day_trades = [t for t in trades if t['datetime'].startswith(mistake['date'])]
                    
                    if day_trades:
                        df_trades = pd.DataFrame(day_trades)
                        # 選擇顯示欄位
                        display_cols = ['datetime', 'action', 'price', 'quantity', 'realized_pnl']
                        st.dataframe(
                            df_trades[display_cols].style.format({
                                'price': '{:.2f}',
                                'quantity': '{:.0f}',
                                'realized_pnl': '{:.2f}'
                            }),
                            use_container_width=True
                        )
                    else:
                        st.info("查無當日詳細交易紀錄")
                        
                except Exception as e:
                    st.error(f"無法載入交易紀錄: {e}")

else:
    st.write("尚無錯誤紀錄。")

# 3. 鄉民智慧 (Common Mistakes)
st.markdown("---")
st.subheader("📚 鄉民智慧：常見交易錯誤")

with st.expander("📖 查看 PTT 常見交易術語與錯誤", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🩸 心理與紀律
        - **凹單 (Averaging Down/Refusing to Cut)**: 虧損時不願停損，甚至加碼攤平，期待股價回升。通常是畢業的主因。
        - **追高殺低 (FOMO/Panic)**: 看到漲了才買，看到跌了才賣。情緒被市場牽著走。
        - **憑感覺 (No Plan)**: 進場沒有依據，出場沒有規劃。「我覺得會漲」是散戶最貴的一句話。
        - **報復性交易 (Revenge Trading)**: 賠錢後想馬上賺回來，放大槓桿亂做，通常會賠更多。
        """)
    
    with col2:
        st.markdown("""
        ### 🔪 技術與操作
        - **接刀 (Catching a Falling Knife)**: 在股價急跌時進場抄底，結果買在半山腰。
        - **抬轎**: 買在主力出貨的高點，幫別人解套獲利。
        - **過度交易 (Overtrading)**: 頻繁進出，獲利都被手續費吃光，還容易心態炸裂。
        - **畢業**: 本金賠光，被迫離開市場。希望這個詞永遠不會出現在你的卡片牆上。
        """)

st.markdown("---")
st.caption("💡 提示：這些錯誤卡片是由 AI 教練在「交易檢討」過程中自動偵測並建立的。保持誠實的面對錯誤，是成為贏家的第一步。")
