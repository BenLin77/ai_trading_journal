"""
Plotly 圖表生成模組

此模組負責：
1. 生成 K 線圖 (Candlestick)
2. 疊加交易標記 (買入/賣出箭頭)
3. 生成績效分析圖表
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any


def create_trading_chart(ohlc_df: pd.DataFrame,
                         trades_df: pd.DataFrame,
                         symbol: str) -> go.Figure:
    """
    建立整合交易標記的 K 線圖

    Args:
        ohlc_df: K 線數據 DataFrame，需包含 datetime, open, high, low, close, volume
        trades_df: 交易紀錄 DataFrame，需包含 datetime, action, price
        symbol: 標的代號

    Returns:
        Plotly Figure 物件
    """
    # 建立子圖：K 線圖 + 成交量
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} 價格走勢', '成交量')
    )

    # 1. 加入 K 線圖
    fig.add_trace(
        go.Candlestick(
            x=ohlc_df['datetime'],
            open=ohlc_df['open'],
            high=ohlc_df['high'],
            low=ohlc_df['low'],
            close=ohlc_df['close'],
            name='K線',
            increasing_line_color='#26A69A',
            decreasing_line_color='#EF5350'
        ),
        row=1, col=1
    )

    # 2. 加入成交量
    colors = ['#EF5350' if close < open else '#26A69A'
              for close, open in zip(ohlc_df['close'], ohlc_df['open'])]

    fig.add_trace(
        go.Bar(
            x=ohlc_df['datetime'],
            y=ohlc_df['volume'],
            name='成交量',
            marker_color=colors,
            opacity=0.5
        ),
        row=2, col=1
    )

    # 3. 加入買入標記（綠色向上箭頭）
    if not trades_df.empty:
        buy_trades = trades_df[trades_df['action'].str.upper().isin(['BUY', 'BOT'])]
        if not buy_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_trades['datetime'],
                    y=buy_trades['price'],
                    mode='markers',
                    name='買入',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color='#26A69A',
                        line=dict(color='white', width=2)
                    )
                ),
                row=1, col=1
            )

        # 4. 加入賣出標記（紅色向下箭頭）
        sell_trades = trades_df[trades_df['action'].str.upper().isin(['SELL', 'SLD'])]
        if not sell_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_trades['datetime'],
                    y=sell_trades['price'],
                    mode='markers',
                    name='賣出',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color='#EF5350',
                        line=dict(color='white', width=2)
                    )
                ),
                row=1, col=1
            )

    # 設定圖表樣式
    fig.update_layout(
        title=f'{symbol} 交易檢討圖',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        height=700,
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # 移除週末空白
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

    return fig


def create_pnl_by_symbol_chart(pnl_data: Dict[str, float]) -> go.Figure:
    """
    建立按標的分組的盈虧長條圖

    Args:
        pnl_data: 標的代號 -> 盈虧金額的字典

    Returns:
        Plotly Figure 物件
    """
    if not pnl_data:
        return go.Figure()

    symbols = list(pnl_data.keys())
    pnls = list(pnl_data.values())

    # 顏色：正值綠色，負值紅色
    colors = ['#26A69A' if pnl >= 0 else '#EF5350' for pnl in pnls]

    fig = go.Figure(data=[
        go.Bar(
            x=symbols,
            y=pnls,
            marker_color=colors,
            text=[f'${pnl:,.2f}' for pnl in pnls],
            textposition='outside'
        )
    ])

    fig.update_layout(
        title='各標的盈虧分析',
        xaxis_title='標的代號',
        yaxis_title='總盈虧 ($)',
        template='plotly_white',
        height=500,
        showlegend=False
    )

    return fig


def create_pnl_by_hour_chart(hourly_pnl: Dict[int, float]) -> go.Figure:
    """
    建立按時段分組的盈虧長條圖

    Args:
        hourly_pnl: 小時 (0-23) -> 盈虧金額的字典

    Returns:
        Plotly Figure 物件
    """
    if not hourly_pnl:
        return go.Figure()

    # 過濾掉 None 鍵值並排序
    hours = sorted([h for h in hourly_pnl.keys() if h is not None and isinstance(h, (int, float))])
    pnls = [hourly_pnl[h] for h in hours]
    hour_labels = [f'{int(h):02d}:00' for h in hours]

    colors = ['#26A69A' if pnl >= 0 else '#EF5350' for pnl in pnls]

    fig = go.Figure(data=[
        go.Bar(
            x=hour_labels,
            y=pnls,
            marker_color=colors,
            text=[f'${pnl:,.0f}' for pnl in pnls],
            textposition='outside'
        )
    ])

    fig.update_layout(
        title='時段盈虧分析（找出魔鬼時刻）',
        xaxis_title='交易時段',
        yaxis_title='總盈虧 ($)',
        template='plotly_white',
        height=500,
        showlegend=False
    )

    # 標記最差時段
    if pnls:
        worst_hour_idx = pnls.index(min(pnls))
        fig.add_annotation(
            x=hour_labels[worst_hour_idx],
            y=pnls[worst_hour_idx],
            text="⚠️ 最差時段",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#FF6B6B",
            bgcolor="#FFE5E5",
            bordercolor="#FF6B6B"
        )

    return fig


def create_win_loss_distribution(stats: Dict[str, Any]) -> go.Figure:
    """
    建立勝負分布圓餅圖

    Args:
        stats: 包含 wins, losses 等統計數據的字典

    Returns:
        Plotly Figure 物件
    """
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)

    if wins == 0 and losses == 0:
        return go.Figure()

    fig = go.Figure(data=[
        go.Pie(
            labels=['獲利交易', '虧損交易'],
            values=[wins, losses],
            marker=dict(colors=['#26A69A', '#EF5350']),
            hole=0.4,
            textinfo='label+percent+value',
            textfont=dict(size=14)
        )
    ])

    fig.update_layout(
        title='交易勝負分布',
        template='plotly_white',
        height=400
    )

    return fig
