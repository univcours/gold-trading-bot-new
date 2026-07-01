import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime, timedelta
import numpy as np
import json

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Pro - Advanced",
    page_icon="🥇",
    layout="wide"
)

# ====================== CSS ======================
st.markdown("""
<style>
    .main-title {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #0a0a1a, #1a1a2e, #0a0a1a);
        border-radius: 15px;
        margin-bottom: 1.5rem;
        border: 2px solid #FFD700;
    }
    .main-title h1 {
        color: #FFD700;
        margin: 0;
        font-size: 2.5rem;
    }
    .status-offline {
        display: inline-block;
        background: #ff0000;
        color: #fff;
        padding: 5px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 16px;
        animation: blink 1s infinite;
    }
    .status-online {
        display: inline-block;
        background: #00ff00;
        color: #000;
        padding: 5px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 16px;
        animation: blink 1s infinite;
    }
    .status-waiting {
        display: inline-block;
        background: #FFD700;
        color: #000;
        padding: 5px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 16px;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .signal-box {
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        text-align: center;
    }
    .signal-buy {
        background: linear-gradient(135deg, #0a2a0a, #1a4a1a);
        border: 2px solid #00ff00;
    }
    .signal-sell {
        background: linear-gradient(135deg, #2a0a0a, #4a1a1a);
        border: 2px solid #ff0000;
    }
    .signal-strong-buy {
        background: linear-gradient(135deg, #00ff00, #00aa00);
        border: 3px solid #00ff00;
        animation: pulse 1s infinite;
    }
    .signal-strong-sell {
        background: linear-gradient(135deg, #ff0000, #aa0000);
        border: 3px solid #ff0000;
        animation: pulse 1s infinite;
    }
    .signal-neutral {
        background: linear-gradient(135deg, #1a1a2a, #2a2a3a);
        border: 2px solid #666;
    }
    .signal-waiting {
        background: linear-gradient(135deg, #2a2a1a, #3a3a2a);
        border: 2px solid #FFD700;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    .level-card {
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .support-level {
        background: rgba(0, 255, 0, 0.1);
        border-left: 4px solid #00ff00;
    }
    .resistance-level {
        background: rgba(255, 0, 0, 0.1);
        border-left: 4px solid #ff0000;
    }
    .pending-level {
        background: rgba(255, 215, 0, 0.1);
        border-left: 4px solid #FFD700;
    }
    .level-price {
        font-weight: bold;
        font-size: 16px;
    }
    .level-type {
        color: #888;
        font-size: 11px;
    }
    .waiting-box {
        padding: 40px;
        text-align: center;
        background: rgba(255, 215, 0, 0.05);
        border-radius: 15px;
        border: 2px dashed #FFD700;
    }
    .waiting-box h2 {
        color: #FFD700;
    }
    .waiting-box p {
        color: #aaa;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=5)
def get_real_price():
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=XAUUSDT"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
    except:
        pass
    return None

@st.cache_data(ttl=5)
def get_order_book_real(limit=100):
    try:
        url = f"https://fapi.binance.com/fapi/v1/depth?symbol=XAUUSDT&limit={limit}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            return bids, asks
    except:
        pass
    return None, None

@st.cache_data(ttl=10)
def get_klines_data(limit=200):
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {
            "symbol": "XAUUSDT",
            "interval": "1m",
            "limit": limit
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except:
        pass
    return None

def check_internet_connection():
    """التحقق من الاتصال بالإنترنت"""
    try:
        requests.get("https://fapi.binance.com/fapi/v1/ping", timeout=2)
        return True
    except:
        return False

# ====================== المؤشرات ======================
def calculate_indicators(df):
    if df is None or df.empty or len(df) < 30:
        return df
    
    # ===== المتوسطات =====
    for period in [5, 10, 20, 50]:
        if len(df) >= period:
            df[f'SMA_{period}'] = df['close'].rolling(period).mean()
    
    # ===== EMA =====
    if len(df) >= 12:
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    else:
        df['EMA_12'] = df['close']
    
    if len(df) >= 26:
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    else:
        df['EMA_26'] = df['close']
    
    # ===== MACD =====
    if len(df) >= 26:
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']
    else:
        df['MACD'] = 0
        df['Signal'] = 0
        df['MACD_Hist'] = 0
    
    # ===== RSI =====
    if len(df) >= 14:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
    else:
        df['RSI'] = 50
    
    # ===== Bollinger =====
    if len(df) >= 20:
        df['BB_Mid'] = df['close'].rolling(20).mean()
        df['BB_Std'] = df['close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    else:
        df['BB_Mid'] = df['close']
        df['BB_Upper'] = df['close'] * 1.02
        df['BB_Lower'] = df['close'] * 0.98
    
    # ===== Stochastic =====
    if len(df) >= 14:
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
    else:
        df['Stoch_K'] = 50
        df['Stoch_D'] = 50
    
    # ===== ATR =====
    if len(df) >= 14:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(14).mean()
    else:
        df['ATR'] = 5
    
    # ===== Volume =====
    if len(df) >= 20:
        df['Volume_SMA'] = df['volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']
    else:
        df['Volume_SMA'] = df['volume']
        df['Volume_Ratio'] = 1
    
    # ===== Pivot =====
    df['Pivot'] = (df['high'] + df['low'] + df['close']) / 3
    df['R1'] = 2 * df['Pivot'] - df['low']
    df['S1'] = 2 * df['Pivot'] - df['high']
    
    return df

# ====================== حساب المستويات ======================
def calculate_levels(df, bids, asks, current_price):
    levels = {
        'support': [],
        'resistance': [],
        'pending_buy': [],
        'pending_sell': []
    }
    
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        for _, row in bids.nlargest(10, 'quantity').iterrows():
            if row['price'] < current_price:
                levels['support'].append({'price': row['price'], 'volume': row['quantity'], 'type': 'Order Book'})
        
        for _, row in asks.nlargest(10, 'quantity').iterrows():
            if row['price'] > current_price:
                levels['resistance'].append({'price': row['price'], 'volume': row['quantity'], 'type': 'Order Book'})
    
    if df is not None and not df.empty:
        last = df.iloc[-1]
        
        if 'BB_Lower' in last and not pd.isna(last['BB_Lower']):
            levels['support'].append({'price': last['BB_Lower'], 'volume': 0, 'type': 'BB Lower'})
        if 'BB_Upper' in last and not pd.isna(last['BB_Upper']):
            levels['resistance'].append({'price': last['BB_Upper'], 'volume': 0, 'type': 'BB Upper'})
        
        if 'S1' in last and not pd.isna(last['S1']):
            levels['support'].append({'price': last['S1'], 'volume': 0, 'type': 'Pivot S1'})
        if 'R1' in last and not pd.isna(last['R1']):
            levels['resistance'].append({'price': last['R1'], 'volume': 0, 'type': 'Pivot R1'})
        
        for sma in ['SMA_20', 'SMA_50']:
            if sma in last and not pd.isna(last[sma]):
                if last[sma] < current_price:
                    levels['support'].append({'price': last[sma], 'volume': 0, 'type': sma})
                else:
                    levels['resistance'].append({'price': last[sma], 'volume': 0, 'type': sma})
    
    if df is not None and not df.empty and 'ATR' in df.columns:
        atr = df['ATR'].iloc[-1] if not pd.isna(df['ATR'].iloc[-1]) else 5
        
        for mult in [0.3, 0.6, 1.0]:
            levels['pending_buy'].append({'price': current_price - atr * mult, 'type': f'Buy {mult*100:.0f}% ATR'})
            levels['pending_sell'].append({'price': current_price + atr * mult, 'type': f'Sell {mult*100:.0f}% ATR'})
    
    levels['support'] = sorted(levels['support'], key=lambda x: x['price'], reverse=True)[:10]
    levels['resistance'] = sorted(levels['resistance'], key=lambda x: x['price'])[:10]
    
    return levels

# ====================== توليد الإشارات ======================
def generate_signals(df, bids, asks, current_price, levels):
    signals = {
        'buy': [],
        'sell': [],
        'strong_buy': [],
        'strong_sell': [],
        'neutral': [],
        'waiting': [],
        'score': 0,
        'reasons': [],
        'recommendation': 'WAITING'
    }
    
    if df is None or df.empty or len(df) < 30:
        signals['waiting'].append("⏳ Waiting for live data...")
        signals['recommendation'] = 'WAITING'
        return signals
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    reasons = []
    
    # ===== RSI =====
    if 'RSI' in last and not pd.isna(last['RSI']):
        if last['RSI'] < 30:
            score += 2
            reasons.append(f"🟢 RSI Oversold: {last['RSI']:.2f}")
        elif last['RSI'] > 70:
            score -= 2
            reasons.append(f"🔴 RSI Overbought: {last['RSI']:.2f}")
    
    # ===== MACD =====
    if 'MACD' in last and 'Signal' in last:
        if not pd.isna(last['MACD']) and not pd.isna(last['Signal']):
            if last['MACD'] > last['Signal']:
                score += 1
                reasons.append("🟢 MACD Bullish")
            else:
                score -= 1
                reasons.append("🔴 MACD Bearish")
    
    # ===== Bollinger =====
    if 'BB_Lower' in last and 'BB_Upper' in last:
        if not pd.isna(last['BB_Lower']) and not pd.isna(last['BB_Upper']):
            if last['close'] < last['BB_Lower']:
                score += 2
                reasons.append("🟢 Below Lower Band")
            elif last['close'] > last['BB_Upper']:
                score -= 2
                reasons.append("🔴 Above Upper Band")
    
    # ===== SMA =====
    if 'SMA_20' in last and 'SMA_50' in last:
        if not pd.isna(last['SMA_20']) and not pd.isna(last['SMA_50']):
            if last['SMA_20'] > last['SMA_50']:
                score += 1
                reasons.append("🟢 SMA 20 > SMA 50")
            else:
                score -= 1
                reasons.append("🔴 SMA 20 < SMA 50")
    
    # ===== الأوردر بوك =====
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        total_bid = bids['quantity'].sum()
        total_ask = asks['quantity'].sum()
        imbalance = total_bid / (total_ask + 0.001)
        
        if imbalance > 1.2:
            score += 1
            reasons.append(f"🟢 Order Book Bullish (Ratio: {imbalance:.2f})")
        elif imbalance < 0.8:
            score -= 1
            reasons.append(f"🔴 Order Book Bearish (Ratio: {imbalance:.2f})")
    
    signals['score'] = score
    signals['reasons'] = reasons
    
    if score >= 5:
        signals['strong_buy'].append(f"🔥 STRONG BUY (Score: {score})")
        signals['recommendation'] = 'STRONG BUY'
        st.balloons()
    elif score >= 2:
        signals['buy'].append(f"📈 BUY (Score: {score})")
        signals['recommendation'] = 'BUY'
    elif score <= -5:
        signals['strong_sell'].append(f"🔥 STRONG SELL (Score: {score})")
        signals['recommendation'] = 'STRONG SELL'
        st.snow()
    elif score <= -2:
        signals['sell'].append(f"📉 SELL (Score: {score})")
        signals['recommendation'] = 'SELL'
    else:
        signals['neutral'].append(f"⏸️ NEUTRAL (Score: {score})")
        signals['recommendation'] = 'NEUTRAL'
    
    return signals

# ====================== شارت ======================
def create_chart(df, bids, asks, current_price, levels, signals):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="⏳ Waiting for Live Data...",
            template='plotly_dark',
            annotations=[{
                'text': '🔴 No Internet Connection<br>Waiting for data...',
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': {'size': 24, 'color': '#FFD700'}
            }]
        )
        return fig
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            '📈 Gold Price Chart',
            '📊 Order Book Depth',
            '📉 RSI',
            '📊 MACD',
            '📊 Volume',
            '🎯 Support & Resistance'
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
        row_heights=[0.40, 0.30, 0.30],
        column_widths=[0.55, 0.45]
    )

    # Price
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='XAUUSD',
            increasing_line_color='#00ff00',
            decreasing_line_color='#ff0000',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # SMA
    for sma, color in [('SMA_20', '#FFD700'), ('SMA_50', '#FF6B6B')]:
        if sma in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df[sma], mode='lines', name=sma, line=dict(color=color, width=1.5)),
                row=1, col=1
            )
    
    # BB
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='#ff0000', width=1, dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='#00ff00', width=1, dash='dash')),
            row=1, col=1
        )
    
    # Levels
    if levels:
        for support in levels['support'][:5]:
            fig.add_hline(y=support['price'], line_dash="dash", line_color="green", opacity=0.7, row=1, col=1)
        for resistance in levels['resistance'][:5]:
            fig.add_hline(y=resistance['price'], line_dash="dash", line_color="red", opacity=0.7, row=1, col=1)
    
    # Order Book
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        fig.add_trace(
            go.Bar(x=bids['price'], y=bids['quantity'], name='Bids', marker_color='#00ff00', opacity=0.8),
            row=1, col=2
        )
        fig.add_trace(
            go.Bar(x=asks['price'], y=asks['quantity'], name='Asks', marker_color='#ff0000', opacity=0.8),
            row=1, col=2
        )
        fig.add_vline(x=current_price, line_dash="dash", line_color="#FFFFFF", opacity=0.8, row=1, col=2)
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='#FF6B6B', width=2)),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # MACD
    if 'MACD' in df.columns and 'Signal' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='#FFD700', width=2)),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Signal'], mode='lines', name='Signal', line=dict(color='#FF6B6B', width=2)),
            row=2, col=2
        )
        colors_hist = ['#00ff00' if x >= 0 else '#ff0000' for x in df['MACD_Hist'].fillna(0)]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['MACD_Hist'], name='Histogram', marker_color=colors_hist, opacity=0.5),
            row=2, col=2
        )
    
    # Volume
    if 'volume' in df.columns:
        colors = ['#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000' for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.7),
            row=3, col=1
        )
    
    # Summary
    if levels:
        support_text = "🟢 Support:\n"
        for s in levels['support'][:5]:
            support_text += f"  💰 ${s['price']:.2f}\n"
        
        resistance_text = "🔴 Resistance:\n"
        for r in levels['resistance'][:5]:
            resistance_text += f"  💰 ${r['price']:.2f}\n"
        
        pending_text = "🟡 Pending:\n"
        for p in levels['pending_buy'][:3]:
            pending_text += f"  Buy ${p['price']:.2f}\n"
        for p in levels['pending_sell'][:3]:
            pending_text += f"  Sell ${p['price']:.2f}\n"
        
        fig.add_annotation(
            text=f"{support_text}\n{resistance_text}\n{pending_text}",
            xref="x3 domain",
            yref="y3 domain",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=12, color="white"),
            align="left",
            row=3, col=2
        )
    
    fig.update_layout(
        height=1100,
        template='plotly_dark',
        title_text=f'🥇 Gold (XAUUSD) - Live Trading | Price: ${current_price:.2f}' if current_price else '🥇 Gold (XAUUSD) - Waiting for Data',
        title_font=dict(size=24, color='#FFD700'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.7)'
        ),
        hovermode='x unified'
    )
    
    return fig

# ====================== عرض الإشارات ======================
def display_signals(signals, current_price, levels, is_online):
    st.markdown("## 🎯 Trading Signals")
    
    # ===== حالة الاتصال =====
    if is_online:
        st.markdown(f'<span class="status-online">🟢 ONLINE - Live Data</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="status-offline">🔴 OFFLINE - Waiting for connection...</span>', unsafe_allow_html=True)
    
    score = signals['score']
    recommendation = signals['recommendation']
    
    # ===== عرض الإشارة =====
    if recommendation == 'WAITING':
        bg_class = "signal-waiting"
        icon = "⏳"
        text = "WAITING FOR DATA"
        st.markdown(f"""
        <div class="waiting-box">
            <h2>⏳ Waiting for Live Data</h2>
            <p>🔴 No internet connection or Binance API unavailable</p>
            <p>⏰ The system will automatically connect when data becomes available</p>
            <p style="font-size: 14px; color: #888;">Retrying every 5 seconds...</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if recommendation == 'STRONG BUY':
        bg_class = "signal-strong-buy"
        icon = "🔥"
        text = "STRONG BUY"
    elif recommendation == 'BUY':
        bg_class = "signal-buy"
        icon = "📈"
        text = "BUY"
    elif recommendation == 'STRONG SELL':
        bg_class = "signal-strong-sell"
        icon = "🔥"
        text = "STRONG SELL"
    elif recommendation == 'SELL':
        bg_class = "signal-sell"
        icon = "📉"
        text = "SELL"
    else:
        bg_class = "signal-neutral"
        icon = "⏸️"
        text = "NEUTRAL"
    
    st.markdown(f"""
    <div class="signal-box {bg_class}">
        <h1 style="margin: 0; font-size: 36px;">{icon} {text}</h1>
        <p style="margin: 5px 0; font-size: 18px;">Signal Score: <strong>{score}</strong></p>
        <p style="margin: 0; font-size: 16px; opacity: 0.8;">💰 Price: <strong>${current_price:.2f}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if signals['reasons']:
        st.markdown("### 📋 Signal Details")
        for reason in signals['reasons']:
            if '🟢' in reason:
                st.success(f"✅ {reason}")
            elif '🔴' in reason:
                st.error(f"❌ {reason}")
            else:
                st.info(f"ℹ️ {reason}")
    
    st.divider()
    
    if levels:
        st.markdown("## 📊 Support & Resistance")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🟢 Support")
            for support in levels['support'][:5]:
                st.markdown(f"""
                <div class="level-card support-level">
                    <span class="level-price">${support['price']:.2f}</span>
                    <span class="level-type">{support['type']}</span>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🔴 Resistance")
            for resistance in levels['resistance'][:5]:
                st.markdown(f"""
                <div class="level-card resistance-level">
                    <span class="level-price">${resistance['price']:.2f}</span>
                    <span class="level-type">{resistance['type']}</span>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("### 🟡 Pending Orders")
            for pending in levels['pending_buy'][:3]:
                st.markdown(f"""
                <div class="level-card pending-level">
                    <span>🔼 Buy: <span class="level-price">${pending['price']:.2f}</span></span>
                </div>
                """, unsafe_allow_html=True)
            for pending in levels['pending_sell'][:3]:
                st.markdown(f"""
                <div class="level-card pending-level">
                    <span>🔽 Sell: <span class="level-price">${pending['price']:.2f}</span></span>
                </div>
                """, unsafe_allow_html=True)

# ====================== الواجهة الرئيسية ======================
def main():
    st.markdown("""
    <div class="main-title">
        <h1>🥇 Gold Trading Pro</h1>
        <p style="color: #aaa; margin: 5px 0;">📊 Real-time Signals | Order Book | Auto-Update</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== التحقق من الاتصال =====
    is_online = check_internet_connection()
    
    if not is_online:
        st.warning("🔴 **No Internet Connection!** Waiting for data...")
        st.info("⏳ The system will automatically connect when the internet is available")
        
        # عرض حالة الانتظار
        st.markdown("""
        <div class="waiting-box">
            <h2>⏳ Waiting for Connection</h2>
            <p style="font-size: 20px;">🔴 Binance API Unavailable</p>
            <p>📡 Please check your internet connection</p>
            <p style="font-size: 14px; color: #888;">Auto-retrying every 5 seconds...</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ===== شارت انتظار =====
        fig = go.Figure()
        fig.update_layout(
            title="⏳ Waiting for Live Data...",
            template='plotly_dark',
            height=600,
            annotations=[{
                'text': '🔴 No Internet Connection<br>Waiting for Binance API...',
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': {'size': 28, 'color': '#FFD700'}
            }]
        )
        st.plotly_chart(fig, use_container_width=True)
        
        time.sleep(5)
        st.rerun()
        return
    
    # ===== جلب البيانات =====
    with st.spinner("🔄 Loading market data..."):
        current_price = get_real_price()
        
        if current_price is None:
            st.warning("⚠️ Binance API temporarily unavailable. Retrying...")
            st.markdown("""
            <div class="waiting-box">
                <h2>⏳ Waiting for Data</h2>
                <p>🔄 Binance API is responding slowly</p>
                <p>⏰ The system will retry automatically</p>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(3)
            st.rerun()
            return
        
        bids, asks = get_order_book_real(100)
        if bids is None or asks is None:
            bids = pd.DataFrame({'price': [], 'quantity': []})
            asks = pd.DataFrame({'price': [], 'quantity': []})
        
        df = get_klines_data(200)
        if df is None or df.empty:
            st.warning("⚠️ No candlestick data available. Waiting for data...")
            time.sleep(3)
            st.rerun()
            return
        
        # ===== حساب كلشي =====
        df = calculate_indicators(df)
        levels = calculate_levels(df, bids, asks, current_price)
        signals = generate_signals(df, bids, asks, current_price, levels)
    
    # ===== العرض =====
    display_signals(signals, current_price, levels, is_online)
    
    st.subheader("📈 Live Chart")
    fig = create_chart(df, bids, asks, current_price, levels, signals)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        st.subheader("📊 Order Book")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🟢 Bids")
            st.dataframe(bids.head(30), use_container_width=True)
        with col2:
            st.markdown("### 🔴 Asks")
            st.dataframe(asks.head(30), use_container_width=True)
    else:
        st.info("⏳ Waiting for Order Book data...")
    
    st.caption("🔄 Auto-updates every 5 seconds...")
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
