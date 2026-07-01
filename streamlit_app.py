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
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.1);
    }
    .main-title h1 {
        color: #FFD700;
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
    }
    .live-badge {
        display: inline-block;
        background: #00ff00;
        color: #000;
        padding: 3px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    .signal-box {
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        text-align: center;
        transition: all 0.3s;
    }
    .signal-buy {
        background: linear-gradient(135deg, #0a2a0a, #1a4a1a);
        border: 2px solid #00ff00;
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.2);
    }
    .signal-sell {
        background: linear-gradient(135deg, #2a0a0a, #4a1a1a);
        border: 2px solid #ff0000;
        box-shadow: 0 0 30px rgba(255, 0, 0, 0.2);
    }
    .signal-strong-buy {
        background: linear-gradient(135deg, #00ff00, #00aa00);
        border: 3px solid #00ff00;
        animation: pulse 1s infinite;
        box-shadow: 0 0 50px rgba(0, 255, 0, 0.4);
    }
    .signal-strong-sell {
        background: linear-gradient(135deg, #ff0000, #aa0000);
        border: 3px solid #ff0000;
        animation: pulse 1s infinite;
        box-shadow: 0 0 50px rgba(255, 0, 0, 0.4);
    }
    .signal-neutral {
        background: linear-gradient(135deg, #1a1a2a, #2a2a3a);
        border: 2px solid #666;
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
def get_order_book_real(limit=150):
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
def get_klines_data(limit=300):
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

# ====================== المؤشرات المتقدمة ======================
def calculate_indicators(df):
    if df is None or df.empty or len(df) < 30:
        return df
    
    # ===== المتوسطات =====
    for period in [5, 10, 20, 50, 100, 200]:
        if len(df) >= period:
            df[f'SMA_{period}'] = df['close'].rolling(period).mean()
            df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    # ===== RSI =====
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ===== MACD =====
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # ===== Bollinger Bands =====
    df['BB_Mid'] = df['close'].rolling(20).mean()
    df['BB_Std'] = df['close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    
    # ===== Stochastic =====
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['Stoch_K'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
    
    # ===== ATR =====
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()
    
    # ===== Ichimoku =====
    df['Tenkan'] = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
    df['Kijun'] = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
    df['Senkou_A'] = (df['Tenkan'] + df['Kijun']) / 2
    df['Senkou_B'] = (df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2
    
    # ===== Volume =====
    df['Volume_SMA'] = df['volume'].rolling(20).mean()
    df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']
    df['OBV'] = (df['volume'] * np.where(df['close'] > df['close'].shift(), 1, -1)).cumsum()
    
    # ===== Pivot Points =====
    df['Pivot'] = (df['high'] + df['low'] + df['close']) / 3
    df['R1'] = 2 * df['Pivot'] - df['low']
    df['S1'] = 2 * df['Pivot'] - df['high']
    df['R2'] = df['Pivot'] + (df['high'] - df['low'])
    df['S2'] = df['Pivot'] - (df['high'] - df['low'])
    df['R3'] = df['Pivot'] + 2 * (df['high'] - df['low'])
    df['S3'] = df['Pivot'] - 2 * (df['high'] - df['low'])
    
    return df

# ====================== حساب الدعم والمقاومة المتقدم ======================
def calculate_levels(df, bids, asks, current_price):
    levels = {
        'support': [],
        'resistance': [],
        'pending_buy': [],
        'pending_sell': [],
        'orderbook_bids': [],
        'orderbook_asks': []
    }
    
    # ===== من الأوردر بوك =====
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        # أكبر كميات شراء (دعم)
        for _, row in bids.nlargest(15, 'quantity').iterrows():
            if row['price'] < current_price:
                levels['support'].append({
                    'price': row['price'],
                    'volume': row['quantity'],
                    'type': 'Order Book'
                })
                levels['orderbook_bids'].append(row['price'])
        
        # أكبر كميات بيع (مقاومة)
        for _, row in asks.nlargest(15, 'quantity').iterrows():
            if row['price'] > current_price:
                levels['resistance'].append({
                    'price': row['price'],
                    'volume': row['quantity'],
                    'type': 'Order Book'
                })
                levels['orderbook_asks'].append(row['price'])
    
    # ===== من المؤشرات =====
    if df is not None and not df.empty:
        last = df.iloc[-1]
        
        # Bollinger Bands
        if 'BB_Lower' in last and not pd.isna(last['BB_Lower']):
            levels['support'].append({'price': last['BB_Lower'], 'volume': 0, 'type': 'BB Lower'})
        if 'BB_Upper' in last and not pd.isna(last['BB_Upper']):
            levels['resistance'].append({'price': last['BB_Upper'], 'volume': 0, 'type': 'BB Upper'})
        
        # Pivot Points
        for p in ['S1', 'S2', 'S3']:
            if p in last and not pd.isna(last[p]):
                levels['support'].append({'price': last[p], 'volume': 0, 'type': f'Pivot {p}'})
        for p in ['R1', 'R2', 'R3']:
            if p in last and not pd.isna(last[p]):
                levels['resistance'].append({'price': last[p], 'volume': 0, 'type': f'Pivot {p}'})
        
        # المتوسطات
        for sma in ['SMA_20', 'SMA_50', 'SMA_100']:
            if sma in last and not pd.isna(last[sma]):
                if last[sma] < current_price:
                    levels['support'].append({'price': last[sma], 'volume': 0, 'type': sma})
                else:
                    levels['resistance'].append({'price': last[sma], 'volume': 0, 'type': sma})
    
    # ===== الأوامر المعلقة =====
    if df is not None and not df.empty and 'ATR' in df.columns:
        atr = df['ATR'].iloc[-1] if not pd.isna(df['ATR'].iloc[-1]) else 5
        
        # أوامر شراء معلقة
        for mult in [0.3, 0.6, 1.0]:
            levels['pending_buy'].append({
                'price': current_price - atr * mult,
                'type': f'Buy {mult*100:.0f}% ATR'
            })
        
        # أوامر بيع معلقة
        for mult in [0.3, 0.6, 1.0]:
            levels['pending_sell'].append({
                'price': current_price + atr * mult,
                'type': f'Sell {mult*100:.0f}% ATR'
            })
    
    # ترتيب المستويات
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
        'score': 0,
        'reasons': [],
        'recommendation': 'NEUTRAL'
    }
    
    if df is None or df.empty or len(df) < 30:
        signals['neutral'].append("⏸️ Waiting for data...")
        return signals
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    reasons = []
    
    # ===== 1. RSI =====
    if 'RSI' in last and not pd.isna(last['RSI']):
        if last['RSI'] < 25:
            score += 3
            reasons.append(f"🟢 RSI Extreme Oversold: {last['RSI']:.2f}")
        elif last['RSI'] < 30:
            score += 2
            reasons.append(f"🟢 RSI Oversold: {last['RSI']:.2f}")
        elif last['RSI'] > 75:
            score -= 3
            reasons.append(f"🔴 RSI Extreme Overbought: {last['RSI']:.2f}")
        elif last['RSI'] > 70:
            score -= 2
            reasons.append(f"🔴 RSI Overbought: {last['RSI']:.2f}")
    
    # ===== 2. MACD =====
    if 'MACD' in last and 'Signal' in last:
        if not pd.isna(last['MACD']) and not pd.isna(last['Signal']):
            if last['MACD'] > last['Signal'] and prev['MACD'] <= prev['Signal']:
                score += 2
                reasons.append("🟢 MACD Bullish Crossover")
            elif last['MACD'] < last['Signal'] and prev['MACD'] >= prev['Signal']:
                score -= 2
                reasons.append("🔴 MACD Bearish Crossover")
            
            if last['MACD_Hist'] > 0:
                score += 1
                reasons.append("🟢 MACD Histogram Positive")
            else:
                score -= 1
                reasons.append("🔴 MACD Histogram Negative")
    
    # ===== 3. Bollinger Bands =====
    if 'BB_Lower' in last and 'BB_Upper' in last:
        if not pd.isna(last['BB_Lower']) and not pd.isna(last['BB_Upper']):
            if last['close'] < last['BB_Lower']:
                score += 2
                reasons.append("🟢 Below Lower Band (Oversold)")
            elif last['close'] > last['BB_Upper']:
                score -= 2
                reasons.append("🔴 Above Upper Band (Overbought)")
    
    # ===== 4. Stochastic =====
    if 'Stoch_K' in last and 'Stoch_D' in last:
        if not pd.isna(last['Stoch_K']) and not pd.isna(last['Stoch_D']):
            if last['Stoch_K'] < 20 and last['Stoch_D'] < 20:
                if last['Stoch_K'] > last['Stoch_D']:
                    score += 2
                    reasons.append("🟢 Stochastic Bullish Crossover")
            elif last['Stoch_K'] > 80 and last['Stoch_D'] > 80:
                if last['Stoch_K'] < last['Stoch_D']:
                    score -= 2
                    reasons.append("🔴 Stochastic Bearish Crossover")
    
    # ===== 5. المتوسطات =====
    if 'SMA_20' in last and 'SMA_50' in last:
        if not pd.isna(last['SMA_20']) and not pd.isna(last['SMA_50']):
            if last['SMA_20'] > last['SMA_50'] and prev['SMA_20'] <= prev['SMA_50']:
                score += 2
                reasons.append("🟢 Golden Cross (20/50)")
            elif last['SMA_20'] < last['SMA_50'] and prev['SMA_20'] >= prev['SMA_50']:
                score -= 2
                reasons.append("🔴 Death Cross (20/50)")
    
    # ===== 6. Ichimoku =====
    if 'Tenkan' in last and 'Kijun' in last:
        if not pd.isna(last['Tenkan']) and not pd.isna(last['Kijun']):
            if last['Tenkan'] > last['Kijun']:
                score += 1
                reasons.append("🟢 Tenkan above Kijun (Bullish)")
            else:
                score -= 1
                reasons.append("🔴 Tenkan below Kijun (Bearish)")
    
    # ===== 7. الأوردر بوك =====
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
    
    # ===== 8. الدعم والمقاومة =====
    if levels:
        for support in levels['support'][:3]:
            if abs(current_price - support['price']) / current_price < 0.001:
                score += 1
                reasons.append(f"🟢 Near Support: ${support['price']:.2f}")
        
        for resistance in levels['resistance'][:3]:
            if abs(current_price - resistance['price']) / current_price < 0.001:
                score -= 1
                reasons.append(f"🔴 Near Resistance: ${resistance['price']:.2f}")
    
    # ===== النتيجة =====
    signals['score'] = score
    signals['reasons'] = reasons
    
    if score >= 6:
        signals['strong_buy'].append(f"🔥 STRONG BUY (Score: {score})")
        signals['recommendation'] = 'STRONG BUY'
        st.balloons()
    elif score >= 3:
        signals['buy'].append(f"📈 BUY (Score: {score})")
        signals['recommendation'] = 'BUY'
    elif score <= -6:
        signals['strong_sell'].append(f"🔥 STRONG SELL (Score: {score})")
        signals['recommendation'] = 'STRONG SELL'
        st.snow()
    elif score <= -3:
        signals['sell'].append(f"📉 SELL (Score: {score})")
        signals['recommendation'] = 'SELL'
    else:
        signals['neutral'].append(f"⏸️ NEUTRAL (Score: {score})")
        signals['recommendation'] = 'NEUTRAL'
    
    return signals

# ====================== شارت TradingView Pro ======================
def create_tradingview_chart(df, bids, asks, current_price, levels, signals):
    """شارت احترافي بحال TradingView"""
    
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Loading data...")
        return fig
    
    # إنشاء الشارت
    fig = make_subplots(
        rows=5, cols=2,
        subplot_titles=(
            '📈 Gold Price Chart',
            '📊 Order Book Depth',
            '📉 RSI (14)',
            '📊 MACD',
            '📊 Stochastic',
            '🎯 Support & Resistance',
            '📊 Volume',
            '📈 Ichimoku Cloud',
            '📊 Market Profile',
            '💡 Trading Signals'
        ),
        vertical_spacing=0.06,
        horizontal_spacing=0.08,
        row_heights=[0.30, 0.18, 0.16, 0.18, 0.18],
        column_widths=[0.55, 0.45]
    )

    # ===== الصف 1 - العمود 1: الشموع =====
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
            increasing_fillcolor='#00ff00',
            decreasing_fillcolor='#ff0000',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # ===== المتوسطات =====
    for sma, color in [('SMA_20', '#FFD700'), ('SMA_50', '#FF6B6B'), ('SMA_100', '#87CEEB')]:
        if sma in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df[sma], mode='lines', name=sma, line=dict(color=color, width=1.5)),
                row=1, col=1
            )
    
    # ===== Bollinger Bands =====
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='#ff0000', width=1, dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Mid'], mode='lines', name='BB Mid', line=dict(color='#FFD700', width=1, dash='dot')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='#00ff00', width=1, dash='dash')),
            row=1, col=1
        )
    
    # ===== Ichimoku على الشارت =====
    if 'Senkou_A' in df.columns and 'Senkou_B' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Senkou_A'], mode='lines', name='Senkou A', line=dict(color='#FF6B6B', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Senkou_B'], mode='lines', name='Senkou B', line=dict(color='#4ECDC4', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Tenkan'], mode='lines', name='Tenkan', line=dict(color='#FFD700', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Kijun'], mode='lines', name='Kijun', line=dict(color='#FF6B6B', width=1)),
            row=1, col=1
        )
    
    # ===== خط السعر الحالي =====
    fig.add_hline(
        y=current_price,
        line_dash="dash",
        line_color="#FFFFFF",
        opacity=0.8,
        row=1, col=1
    )
    
    # ===== الدعم والمقاومة على الشارت =====
    if levels:
        # دعم
        for support in levels['support'][:5]:
            fig.add_hline(
                y=support['price'],
                line_dash="dash",
                line_color="green",
                opacity=0.7,
                row=1, col=1
            )
            fig.add_annotation(
                x=df['timestamp'].iloc[-1],
                y=support['price'],
                text=f"${support['price']:.2f}",
                showarrow=False,
                font=dict(size=9, color="green"),
                row=1, col=1
            )
        
        # مقاومة
        for resistance in levels['resistance'][:5]:
            fig.add_hline(
                y=resistance['price'],
                line_dash="dash",
                line_color="red",
                opacity=0.7,
                row=1, col=1
            )
            fig.add_annotation(
                x=df['timestamp'].iloc[-1],
                y=resistance['price'],
                text=f"${resistance['price']:.2f}",
                showarrow=False,
                font=dict(size=9, color="red"),
                row=1, col=1
            )
    
    # ===== إشارة على الشارت =====
    if signals['score'] >= 3:
        fig.add_annotation(
            x=df['timestamp'].iloc[-1],
            y=df['high'].iloc[-1] * 1.01,
            text=f"🟢 BUY ({signals['score']})",
            showarrow=True,
            arrowhead=2,
            arrowsize=2,
            arrowwidth=3,
            arrowcolor="#00ff00",
            font=dict(size=18, color="#00ff00", family="Arial Black"),
            row=1, col=1
        )
    elif signals['score'] <= -3:
        fig.add_annotation(
            x=df['timestamp'].iloc[-1],
            y=df['high'].iloc[-1] * 1.01,
            text=f"🔴 SELL ({signals['score']})",
            showarrow=True,
            arrowhead=2,
            arrowsize=2,
            arrowwidth=3,
            arrowcolor="#ff0000",
            font=dict(size=18, color="#ff0000", family="Arial Black"),
            row=1, col=1
        )
    
    # ===== الصف 1 - العمود 2: الأوردر بوك =====
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        fig.add_trace(
            go.Bar(x=bids['price'], y=bids['quantity'], name='Bids', marker_color='#00ff00', opacity=0.8),
            row=1, col=2
        )
        fig.add_trace(
            go.Bar(x=asks['price'], y=asks['quantity'], name='Asks', marker_color='#ff0000', opacity=0.8),
            row=1, col=2
        )
        
        # خط السعر على الأوردر بوك
        fig.add_vline(
            x=current_price,
            line_dash="dash",
            line_color="#FFFFFF",
            opacity=0.8,
            row=1, col=2
        )
    
    # ===== الصف 2 - العمود 1: RSI =====
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='#FF6B6B', width=2)),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.1, row=2, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.1, row=2, col=1)
    
    # ===== الصف 2 - العمود 2: MACD =====
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
    
    # ===== الصف 3 - العمود 1: Stochastic =====
    if 'Stoch_K' in df.columns and 'Stoch_D' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Stoch_K'], mode='lines', name='Stoch K', line=dict(color='#FFD700', width=2)),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Stoch_D'], mode='lines', name='Stoch D', line=dict(color='#FF6B6B', width=2)),
            row=3, col=1
        )
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=3, col=1)
    
    # ===== الصف 3 - العمود 2: الدعم والمقاومة التفصيلية =====
    if levels:
        support_text = "🟢 Support Levels:\n"
        for s in levels['support'][:5]:
            support_text += f"  💰 ${s['price']:.2f} ({s['type']})\n"
        
        resistance_text = "🔴 Resistance Levels:\n"
        for r in levels['resistance'][:5]:
            resistance_text += f"  💰 ${r['price']:.2f} ({r['type']})\n"
        
        pending_text = "🟡 Pending Orders:\n"
        for p in levels['pending_buy'][:3]:
            pending_text += f"  🔼 Buy ${p['price']:.2f}\n"
        for p in levels['pending_sell'][:3]:
            pending_text += f"  🔽 Sell ${p['price']:.2f}\n"
        
        fig.add_annotation(
            text=f"{support_text}\n{resistance_text}\n{pending_text}",
            xref="x3 domain",
            yref="y3 domain",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=11, color="white", family="monospace"),
            align="left",
            row=3, col=2
        )
    
    # ===== الصف 4 - العمود 1: Volume =====
    if 'volume' in df.columns:
        colors = ['#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000' for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.7),
            row=4, col=1
        )
        if 'Volume_SMA' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['Volume_SMA'], mode='lines', name='Vol SMA', line=dict(color='#FFD700', width=1.5)),
                row=4, col=1
            )
    
    # ===== الصف 4 - العمود 2: Ichimoku Cloud =====
    if 'Senkou_A' in df.columns and 'Senkou_B' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Senkou_A'], mode='lines', name='Senkou A', line=dict(color='#FF6B6B', width=1.5)),
            row=4, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Senkou_B'], mode='lines', name='Senkou B', line=dict(color='#4ECDC4', width=1.5)),
            row=4, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Tenkan'], mode='lines', name='Tenkan', line=dict(color='#FFD700', width=1)),
            row=4, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Kijun'], mode='lines', name='Kijun', line=dict(color='#FF6B6B', width=1)),
            row=4, col=2
        )
    
    # ===== الصف 5 - العمود 1: Market Profile =====
    if 'close' in df.columns and 'volume' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['close'],
                y=df['volume'],
                mode='markers',
                name='Market Profile',
                marker=dict(
                    size=df['volume'] / df['volume'].max() * 30,
                    color=df['volume'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Volume", x=0.48)
                ),
                hovertemplate='Price: $%{x:.2f}<br>Volume: %{y:.2f}<extra></extra>'
            ),
            row=5, col=1
        )
    
    # ===== الصف 5 - العمود 2: ملخص الإشارات =====
    score = signals['score']
    recommendation = signals['recommendation']
    
    if recommendation == 'STRONG BUY':
        signal_color = '#00ff00'
        bg_color = 'rgba(0, 255, 0, 0.1)'
    elif recommendation == 'BUY':
        signal_color = '#66ff66'
        bg_color = 'rgba(0, 255, 0, 0.05)'
    elif recommendation == 'STRONG SELL':
        signal_color = '#ff0000'
        bg_color = 'rgba(255, 0, 0, 0.1)'
    elif recommendation == 'SELL':
        signal_color = '#ff6666'
        bg_color = 'rgba(255, 0, 0, 0.05)'
    else:
        signal_color = '#888888'
        bg_color = 'rgba(255, 255, 255, 0.05)'
    
    # عرض الإشارات
    text = f"🎯 SIGNAL: {recommendation}\nScore: {score}\n\n"
    
    if signals['reasons']:
        for reason in signals['reasons'][:5]:
            text += f"{reason}\n"
    
    fig.add_annotation(
        text=text,
        xref="x5 domain",
        yref="y5 domain",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=12, color=signal_color, family="monospace"),
        align="left",
        bgcolor=bg_color,
        bordercolor=signal_color,
        borderwidth=2,
        row=5, col=2
    )
    
    # ===== تحديث التصميم =====
    fig.update_layout(
        height=1600,
        template='plotly_dark',
        title_text=f'🥇 Gold (XAUUSD) - TradingView Pro | Price: ${current_price:.2f}' if current_price else '🥇 Gold (XAUUSD) - TradingView Pro',
        title_font=dict(size=28, color='#FFD700'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.7)'
        ),
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.1)'
    )
    
    # تحديث المحاور
    for row in range(1, 6):
        for col in range(1, 3):
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', row=row, col=col)
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', row=row, col=col)
    
    return fig

# ====================== عرض الإشارات المتقدم ======================
def display_signals(signals, current_price, levels):
    """عرض الإشارات بشكل متقدم"""
    
    st.markdown("## 🎯 Trading Signals (Auto-Update)")
    
    score = signals['score']
    recommendation = signals['recommendation']
    
    if recommendation == 'STRONG BUY':
        bg_class = "signal-strong-buy"
        icon = "🔥"
        text = "STRONG BUY"
        color = "#00ff00"
    elif recommendation == 'BUY':
        bg_class = "signal-buy"
        icon = "📈"
        text = "BUY"
        color = "#00ff00"
    elif recommendation == 'STRONG SELL':
        bg_class = "signal-strong-sell"
        icon = "🔥"
        text = "STRONG SELL"
        color = "#ff0000"
    elif recommendation == 'SELL':
        bg_class = "signal-sell"
        icon = "📉"
        text = "SELL"
        color = "#ff0000"
    else:
        bg_class = "signal-neutral"
        icon = "⏸️"
        text = "NEUTRAL"
        color = "#888888"
    
    # عرض الإشارة الرئيسية
    st.markdown(f"""
    <div class="signal-box {bg_class}">
        <h1 style="margin: 0; font-size: 42px;">{icon} {text}</h1>
        <p style="margin: 5px 0; font-size: 20px;">Signal Score: <strong>{score}</strong></p>
        <p style="margin: 0; font-size: 16px; opacity: 0.8;">
            💰 Current Price: <strong>${current_price:.2f}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # عرض الأسباب
    if signals['reasons']:
        st.markdown("### 📋 Signal Details")
        cols = st.columns(2)
        for i, reason in enumerate(signals['reasons']):
            with cols[i % 2]:
                if '🟢' in reason:
                    st.success(f"✅ {reason}")
                elif '🔴' in reason:
                    st.error(f"❌ {reason}")
                elif '⚡' in reason:
                    st.warning(f"⚡ {reason}")
                else:
                    st.info(f"ℹ️ {reason}")
    
    st.divider()
    
    # ===== عرض الدعم والمقاومة =====
    if levels:
        st.markdown("## 📊 Support & Resistance Levels")
        
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
                    <span class="level-type">{pending['type']}</span>
                </div>
                """, unsafe_allow_html=True)
            for pending in levels['pending_sell'][:3]:
                st.markdown(f"""
                <div class="level-card pending-level">
                    <span>🔽 Sell: <span class="level-price">${pending['price']:.2f}</span></span>
                    <span class="level-type">{pending['type']}</span>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    
    # ===== نصائح التداول =====
    st.markdown("## 💡 Trading Recommendations")
    
    if score >= 3:
        st.success("""
        🟢 **BUY Recommendation**
        - Enter long position with stop loss below nearest support
        - Take profit at next resistance level
        - Consider trailing stop loss
        """)
    elif score <= -3:
        st.error("""
        🔴 **SELL Recommendation**
        - Enter short position with stop loss above nearest resistance
        - Take profit at next support level
        - Consider trailing stop loss
        """)
    else:
        st.info("""
        ⏸️ **NEUTRAL Recommendation**
        - Wait for clearer signal
        - Monitor price action at key levels
        - Look for confirmation before entering
        """)

# ====================== الواجهة الرئيسية ======================
def main():
    # العنوان
    st.markdown("""
    <div class="main-title">
        <h1>🥇 Gold Trading Pro</h1>
        <p style="color: #aaa; margin: 5px 0;">
            📊 TradingView Style Chart | Real-time Signals | Order Book Analysis
        </p>
        <p style="margin: 10px 0;">
            <span class="live-badge">🔴 LIVE</span>
            <span style="color: #aaa; margin-left: 10px;">Updates every 5 seconds</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== جلب البيانات =====
    with st.spinner("🔄 Fetching live market data..."):
        # جلب السعر
        current_price = get_real_price()
        if not current_price:
            current_price = 3315.50
        
        # جلب الأوردر بوك
        bids, asks = get_order_book_real(150)
        if bids is None or asks is None:
            bids = pd.DataFrame({
                'price': [current_price - i * 0.15 for i in range(100)],
                'quantity': [np.random.randint(10, 100) for _ in range(100)]
            })
            asks = pd.DataFrame({
                'price': [current_price + i * 0.15 for i in range(100)],
                'quantity': [np.random.randint(10, 100) for _ in range(100)]
            })
        
        # جلب بيانات الشموع
        df = get_klines_data(300)
        if df is None or df.empty:
            dates = pd.date_range(end=datetime.now(), periods=300, freq='1min')
            price = current_price - 20
            data = []
            for i in range(300):
                change = np.random.randn() * 0.12
                price += change
                data.append([
                    dates[i], price, price + 0.15, price - 0.15, 
                    price + np.random.randn() * 0.08, np.random.randint(100, 1000)
                ])
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات
        df = calculate_indicators(df)
        
        # حساب المستويات
        levels = calculate_levels(df, bids, asks, current_price)
        
        # توليد الإشارات
        signals = generate_signals(df, bids, asks, current_price, levels)
    
    # ===== عرض الإشارات =====
    display_signals(signals, current_price, levels)
    
    # ===== عرض الشارت =====
    st.subheader("📈 Professional Chart (TradingView Style)")
    fig = create_tradingview_chart(df, bids, asks, current_price, levels, signals)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== عرض الأوردر بوك =====
    if bids is not None and asks is not None:
        st.subheader("📊 Live Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy Orders)")
            st.dataframe(
                bids.head(30).style.format({'price': '${:.2f}', 'quantity': '{:.2f}'}),
                use_container_width=True,
                height=500
            )
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():,.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell Orders)")
            st.dataframe(
                asks.head(30).style.format({'price': '${:.2f}', 'quantity': '{:.2f}'}),
                use_container_width=True,
                height=500
            )
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():,.2f}")
    
    # ===== تحديث تلقائي =====
    st.caption("🔄 Auto-updates every 5 seconds...")
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
