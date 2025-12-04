"""
Plotly 圖表生成模組 - 專業深色主題

此模組負責：
1. 生成 K 線圖 (Candlestick)
2. 疊加交易標記 (買入/賣出箭頭)
3. 生成績效分析圖表

設計靈感：TradingView, Bloomberg Terminal
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any

# 匯入主題配置
from config.theme import COLORS, TYPOGRAPHY, get_chart_layout_config


def create_trading_chart(ohlc_df: pd.DataFrame,
                         trades_df: pd.DataFrame,
                         symbol: str) -> go.Figure:
    """
    建立整合交易標記的 K 線圖 - 專業深色主題

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
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=(f'{symbol} 價格走勢', '成交量')
    )

    # 1. 加入 K 線圖 - 專業配色
    fig.add_trace(
        go.Candlestick(
            x=ohlc_df['datetime'],
            open=ohlc_df['open'],
            high=ohlc_df['high'],
            low=ohlc_df['low'],
            close=ohlc_df['close'],
            name='K線',
            increasing_line_color=COLORS.CHART_CANDLE_BULL,
            increasing_fillcolor=COLORS.CHART_CANDLE_BULL,
            decreasing_line_color=COLORS.CHART_CANDLE_BEAR,
            decreasing_fillcolor=COLORS.CHART_CANDLE_BEAR,
        ),
        row=1, col=1
    )

    # 2. 加入成交量 - 深色主題配色
    colors = [COLORS.CHART_CANDLE_BEAR if close < open else COLORS.CHART_CANDLE_BULL
              for close, open in zip(ohlc_df['close'], ohlc_df['open'])]

    fig.add_trace(
        go.Bar(
            x=ohlc_df['datetime'],
            y=ohlc_df['volume'],
            name='成交量',
            marker_color=colors,
            opacity=0.6
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
                        size=16,
                        color=COLORS.PROFIT,
                        line=dict(color=COLORS.BG_PRIMARY, width=2)
                    ),
                    hovertemplate='<b>買入</b><br>價格: $%{y:.2f}<br>時間: %{x}<extra></extra>'
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
                        size=16,
                        color=COLORS.LOSS,
                        line=dict(color=COLORS.BG_PRIMARY, width=2)
                    ),
                    hovertemplate='<b>賣出</b><br>價格: $%{y:.2f}<br>時間: %{x}<extra></extra>'
                ),
                row=1, col=1
            )

    # 套用深色主題配置
    layout_config = get_chart_layout_config(f'{symbol} 交易檢討圖')
    # 覆蓋 legend 設定
    layout_config['legend'] = dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS.TEXT_SECONDARY)
    )
    
    fig.update_layout(
        **layout_config,
        xaxis_rangeslider_visible=False,
        height=700,
        showlegend=True
    )

    # 更新子圖標題樣式
    fig.update_annotations(font=dict(color=COLORS.TEXT_PRIMARY, size=14))

    # 更新 X 軸和 Y 軸樣式
    for i in [1, 2]:
        fig.update_xaxes(
            showgrid=True,
            gridcolor=COLORS.CHART_GRID,
            showline=True,
            linecolor=COLORS.BORDER_DEFAULT,
            tickfont=dict(color=COLORS.TEXT_MUTED),
            row=i, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor=COLORS.CHART_GRID,
            showline=True,
            linecolor=COLORS.BORDER_DEFAULT,
            tickfont=dict(color=COLORS.TEXT_MUTED),
            row=i, col=1
        )

    # 移除週末空白
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

    return fig


def create_pnl_by_symbol_chart(pnl_data: Dict[str, float]) -> go.Figure:
    """
    建立按標的分組的盈虧長條圖 - 專業深色主題

    Args:
        pnl_data: 標的代號 -> 盈虧金額的字典

    Returns:
        Plotly Figure 物件
    """
    if not pnl_data:
        return go.Figure()

    # 按盈虧排序
    sorted_data = sorted(pnl_data.items(), key=lambda x: x[1], reverse=True)
    symbols = [item[0] for item in sorted_data]
    pnls = [item[1] for item in sorted_data]

    # 顏色：正值綠色，負值紅色
    colors = [COLORS.PROFIT if pnl >= 0 else COLORS.LOSS for pnl in pnls]

    fig = go.Figure(data=[
        go.Bar(
            x=symbols,
            y=pnls,
            marker_color=colors,
            text=[f'{"+" if pnl >= 0 else ""}${pnl:,.0f}' for pnl in pnls],
            textposition='outside',
            textfont=dict(color=COLORS.TEXT_PRIMARY, size=11),
            hovertemplate='<b>%{x}</b><br>盈虧: $%{y:,.2f}<extra></extra>'
        )
    ])

    layout_config = get_chart_layout_config('各標的盈虧分析')
    fig.update_layout(
        **layout_config,
        height=450,
        showlegend=False,
        xaxis_title='標的代號',
        yaxis_title='總盈虧 ($)',
        yaxis_tickformat='$,.0f',
        bargap=0.3
    )

    # 添加零線
    fig.add_hline(y=0, line_color=COLORS.BORDER_ACCENT, line_width=1, opacity=0.7)

    return fig


def create_pnl_by_hour_chart(hourly_pnl: Dict[int, float]) -> go.Figure:
    """
    建立按時段分組的盈虧長條圖 - 專業深色主題

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

    colors = [COLORS.PROFIT if pnl >= 0 else COLORS.LOSS for pnl in pnls]

    fig = go.Figure(data=[
        go.Bar(
            x=hour_labels,
            y=pnls,
            marker_color=colors,
            text=[f'{"+" if pnl >= 0 else ""}${pnl:,.0f}' for pnl in pnls],
            textposition='outside',
            textfont=dict(color=COLORS.TEXT_PRIMARY, size=10),
            hovertemplate='<b>%{x}</b><br>盈虧: $%{y:,.2f}<extra></extra>'
        )
    ])

    layout_config = get_chart_layout_config('時段盈虧分析（找出魔鬼時刻）')
    fig.update_layout(
        **layout_config,
        height=450,
        showlegend=False,
        xaxis_title='交易時段',
        yaxis_title='總盈虧 ($)',
        yaxis_tickformat='$,.0f',
        bargap=0.2
    )

    # 添加零線
    fig.add_hline(y=0, line_color=COLORS.BORDER_ACCENT, line_width=1, opacity=0.7)

    # 標記最差時段
    if pnls:
        worst_hour_idx = pnls.index(min(pnls))
        fig.add_annotation(
            x=hour_labels[worst_hour_idx],
            y=pnls[worst_hour_idx],
            text="⚠️ 魔鬼時刻",
            showarrow=True,
            arrowhead=2,
            arrowcolor=COLORS.LOSS,
            arrowwidth=2,
            ax=0,
            ay=-40,
            bgcolor=COLORS.LOSS_BG,
            bordercolor=COLORS.LOSS,
            borderwidth=1,
            font=dict(color=COLORS.LOSS, size=12)
        )

    return fig


def create_win_loss_distribution(stats: Dict[str, Any]) -> go.Figure:
    """
    建立勝負分布圓環圖 - 專業深色主題

    Args:
        stats: 包含 wins, losses 等統計數據的字典

    Returns:
        Plotly Figure 物件
    """
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)

    if wins == 0 and losses == 0:
        return go.Figure()

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

    fig = go.Figure(data=[
        go.Pie(
            labels=['獲利交易', '虧損交易'],
            values=[wins, losses],
            marker=dict(
                colors=[COLORS.PROFIT, COLORS.LOSS],
                line=dict(color=COLORS.BG_PRIMARY, width=3)
            ),
            hole=0.55,
            textinfo='label+percent',
            textfont=dict(size=13, color=COLORS.TEXT_PRIMARY),
            hovertemplate='<b>%{label}</b><br>次數: %{value}<br>佔比: %{percent}<extra></extra>'
        )
    ])

    layout_config = get_chart_layout_config('')
    # 覆蓋 legend 設定
    layout_config['legend'] = dict(
        orientation="h",
        yanchor="bottom",
        y=-0.1,
        xanchor="center",
        x=0.5,
        font=dict(color=COLORS.TEXT_SECONDARY)
    )
    
    fig.update_layout(
        **layout_config,
        height=400,
        showlegend=True,
        annotations=[
            dict(
                text=f'<b>{win_rate:.0f}%</b><br>勝率',
                x=0.5, y=0.5,
                font=dict(size=24, color=COLORS.PROFIT if win_rate >= 50 else COLORS.LOSS),
                showarrow=False
            )
        ]
    )

    return fig


def create_cumulative_pnl_chart(trades_df: pd.DataFrame) -> go.Figure:
    """
    建立累計盈虧曲線圖 - 專業深色主題

    Args:
        trades_df: 交易紀錄 DataFrame

    Returns:
        Plotly Figure 物件
    """
    if trades_df.empty:
        return go.Figure()

    df = trades_df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')
    df['cumulative_pnl'] = df['realized_pnl'].cumsum()

    final_pnl = df['cumulative_pnl'].iloc[-1]
    line_color = COLORS.PROFIT if final_pnl >= 0 else COLORS.LOSS
    fill_color = COLORS.PROFIT_BG if final_pnl >= 0 else COLORS.LOSS_BG

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['cumulative_pnl'],
        mode='lines',
        name='累計盈虧',
        line=dict(color=line_color, width=3),
        fill='tozeroy',
        fillcolor=fill_color,
        hovertemplate='<b>日期</b>: %{x|%Y-%m-%d}<br><b>累計盈虧</b>: $%{y:,.2f}<extra></extra>'
    ))

    # 標記峰值和谷底
    max_pnl = df['cumulative_pnl'].max()
    max_idx = df['cumulative_pnl'].idxmax()
    max_date = df.loc[max_idx, 'datetime']

    fig.add_trace(go.Scatter(
        x=[max_date],
        y=[max_pnl],
        mode='markers+text',
        name='峰值',
        marker=dict(color=COLORS.PROFIT, size=12, symbol='star'),
        text=[f'峰值 ${max_pnl:,.0f}'],
        textposition='top center',
        textfont=dict(color=COLORS.PROFIT, size=11),
        hoverinfo='skip'
    ))

    layout_config = get_chart_layout_config('累計盈虧曲線')
    fig.update_layout(
        **layout_config,
        height=400,
        showlegend=False,
        yaxis_title='累計損益 ($)',
        yaxis_tickformat='$,.0f'
    )

    return fig
