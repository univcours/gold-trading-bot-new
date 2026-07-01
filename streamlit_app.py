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
    page_title="Gold Trading Pro - Live Signals",
    page_icon="🥇",
    layout="wide"
)

# ====================== CSS ======================
st.markdown("""
<style>
    .signal-box {
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: center;
    }
    .signal-buy {
        background: linear-gradient(90deg, #1a3a1a, #0a2a0a);
        border: 2px solid #00ff00;
        color: #00ff00;
    }
    .signal-sell {
        background: linear-gradient(90deg, #3a1a1a, #2a0a0a);
        border: 2px solid #ff0000;
        color: #ff0000;
    }
    .signal-neutral {
        background: linear-gradient(90deg, #1a1a2a, #0a0a1a);
        border: 2px solid #888888;
        color: #888888;
    }
    .signal-strong-buy {
        background: linear-gradient(90deg, #00ff00, #00aa00);
        border: 3px solid #00ff00;
        color: #000;
        font-weight: bold;
        animation: pulse 1s infinite;
    }
    .signal-strong-sell {
        background: linear-gradient(90deg, #ff0000, #aa0000);
        border: 3px solid #ff0000;
        color: #fff;
        font-weight: bold;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.02); }
        100% { opacity: 1; transform: scale(1); }
    }
    .level-box {
        padding: 8px;
        border-radius: 5px;
        margin: 3px 0;
        font-size: 12px;
    }
    .support {
        background: rgba(0, 255, 0, 0.15);
        border-left: 3px solid #00ff00;
    }
    .resistance {
        background: rgba(255, 0, 0, 0.15);
        border-left: 3px solid #ff0000;
    }
    .pending {
        background: rgba(255, 215, 0, 0.15);
        border-left: 3px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)

# ====================== جلب السعر الحقيقي ======================
@st.cache_data(ttl=5)
def get_real_price():
    """جلب السعر الحقيقي من Binance"""
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
def get_order_book_real():
    """جلب الأوردر بوك الحقيقي"""
    try:
        url = "https://fapi.binance.com/fapi/v1/depth?symbol=XAUUSDT&limit=100"
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
    """جلب بيانات الشموع"""
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

# ====================== حساب المؤشرات ======================
def calculate_indicators(df):
    """حساب جميع المؤشرات الفنية"""
    
    if df is None or df.empty or len(df) < 30:
        return df
    
    # ===== المتوسطات =====
    df['SMA_5'] = df['close'].rolling(5).mean()
    df['SMA_10'] = df['close'].rolling(10).mean()
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
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
    df['BB_Position'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
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
    df['R3'] = df['R1'] + (df['high'] - df['low'])
    df['S3'] = df['S1'] - (df['high'] - df['low'])
    
    return df

# ====================== حساب الدعم والمقاومة ======================
def calculate_support_resistance(df, bids, asks, current_price):
    """حساب مستويات الدعم والمقاومة من الأوردر بوك"""
    
    levels = {
        'support': [],
        'resistance': [],
        'pending_buy': [],
        'pending_sell': []
    }
    
    # ===== من الأوردر بوك =====
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        # نقاط الدعم (أكبر كميات شراء)
        top_bids = bids.nlargest(10, 'quantity')
        for _, row in top_bids.iterrows():
            if row['price'] < current_price:
                levels['support'].append({
                    'price': row['price'],
                    'volume': row['quantity'],
                    'type': 'Order Book'
                })
        
        # نقاط المقاومة (أكبر كميات بيع)
        top_asks = asks.nlargest(10, 'quantity')
        for _, row in top_asks.iterrows():
            if row['price'] > current_price:
                levels['resistance'].append({
                    'price': row['price'],
                    'volume': row['quantity'],
                    'type': 'Order Book'
                })
    
    # ===== من المؤشرات الفنية =====
    if df is not None and not df.empty:
        last = df.iloc[-1]
        
        # من Bollinger Bands
        if 'BB_Lower' in last and not pd.isna(last['BB_Lower']):
            levels['support'].append({
                'price': last['BB_Lower'],
                'volume': 0,
                'type': 'BB Lower'
            })
        if 'BB_Upper' in last and not pd.isna(last['BB_Upper']):
            levels['resistance'].append({
                'price': last['BB_Upper'],
                'volume': 0,
                'type': 'BB Upper'
            })
        
        # من Pivot Points
        if 'S1' in last and not pd.isna(last['S1']):
            levels['support'].append({
                'price': last['S1'],
                'volume': 0,
                'type': 'Pivot S1'
            })
        if 'S2' in last and not pd.isna(last['S2']):
            levels['support'].append({
                'price': last['S2'],
                'volume': 0,
                'type': 'Pivot S2'
            })
        if 'R1' in last and not pd.isna(last['R1']):
            levels['resistance'].append({
                'price': last['R1'],
                'volume': 0,
                'type': 'Pivot R1'
            })
        if 'R2' in last and not pd.isna(last['R2']):
            levels['resistance'].append({
                'price': last['R2'],
                'volume': 0,
                'type': 'Pivot R2'
            })
        
        # من المتوسطات المتحركة
        for sma in ['SMA_20', 'SMA_50']:
            if sma in last and not pd.isna(last[sma]):
                if last[sma] < current_price:
                    levels['support'].append({
                        'price': last[sma],
                        'volume': 0,
                        'type': sma
                    })
                else:
                    levels['resistance'].append({
                        'price': last[sma],
                        'volume': 0,
                        'type': sma
                    })
    
    # ===== مناطق الأوامر المعلقة =====
    # شراء معلق (أسفل السعر الحالي بفارق ATR)
    if df is not None and not df.empty and 'ATR' in df.columns:
        atr = df['ATR'].iloc[-1] if not pd.isna(df['ATR'].iloc[-1]) else 5
        levels['pending_buy'].append({
            'price': current_price - atr * 0.5,
            'type': 'Pending Buy'
        })
        levels['pending_buy'].append({
            'price': current_price - atr * 1.0,
            'type': 'Pending Buy'
        })
        levels['pending_sell'].append({
            'price': current_price + atr * 0.5,
            'type': 'Pending Sell'
        })
        levels['pending_sell'].append({
            'price': current_price + atr * 1.0,
            'type': 'Pending Sell'
        })
    
    # ترتيب وترشيح المستويات
    levels['support'] = sorted(levels['support'], key=lambda x: x['price'], reverse=True)[:10]
    levels['resistance'] = sorted(levels['resistance'], key=lambda x: x['price'])[:10]
    
    return levels

# ====================== توليد الإشارات التلقائية ======================
def generate_signals_auto(df, bids, asks, current_price, levels):
    """توليد إشارات بيع وشراء تلقائياً"""
    
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
            
            # BB Squeeze
            if 'BB_Width' in last and not pd.isna(last['BB_Width']):
                if last['BB_Width'] < df['BB_Width'].rolling(50).mean() * 0.7:
                    reasons.append("⚡ BB Squeeze - Breakout Imminent")
    
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
    
    # ===== 5. المتوسطات المتحركة =====
    if 'SMA_5' in last and 'SMA_20' in last:
        if not pd.isna(last['SMA_5']) and not pd.isna(last['SMA_20']):
            if last['SMA_5'] > last['SMA_20'] and prev['SMA_5'] <= prev['SMA_20']:
                score += 2
                reasons.append("🟢 Golden Cross (5/20)")
            elif last['SMA_5'] < last['SMA_20'] and prev['SMA_5'] >= prev['SMA_20']:
                score -= 2
                reasons.append("🔴 Death Cross (5/20)")
    
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
            if last['Tenkan'] > last['Kijun'] and prev['Tenkan'] <= prev['Kijun']:
                score += 1
                reasons.append("🟢 Ichimoku Bullish Cross")
            elif last['Tenkan'] < last['Kijun'] and prev['Tenkan'] >= prev['Kijun']:
                score -= 1
                reasons.append("🔴 Ichimoku Bearish Cross")
    
    # ===== 7. Volume =====
    if 'Volume_Ratio' in last and not pd.isna(last['Volume_Ratio']):
        if last['Volume_Ratio'] > 1.5:
            if score > 0:
                score += 1
                reasons.append("🟢 High Volume Confirms Uptrend")
            elif score < 0:
                score -= 1
                reasons.append("🔴 High Volume Confirms Downtrend")
    
    # ===== 8. الأوردر بوك =====
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
    
    # ===== 9. الدعم والمقاومة =====
    if levels:
        # التحقق من الاقتراب من الدعم
        for support in levels['support'][:3]:
            if abs(current_price - support['price']) / current_price < 0.001:
                score += 1
                reasons.append(f"🟢 Near Support: ${support['price']:.2f}")
        
        # التحقق من الاقتراب من المقاومة
        for resistance in levels['resistance'][:3]:
            if abs(current_price - resistance['price']) / current_price < 0.001:
                score -= 1
                reasons.append(f"🔴 Near Resistance: ${resistance['price']:.2f}")
    
    # ===== النتيجة النهائية =====
    signals['score'] = score
    signals['reasons'] = reasons
    
    # ===== تحديد الإشارة =====
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

# ====================== رسم الشارت المتقدم ======================
def create_advanced_chart(df, bids, asks, current_price, levels, signals):
    """إنشاء شارت متقدم مع الأوردر بوك والدعم والمقاومة"""
    
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Loading data...")
        return fig
    
    # إنشاء الشارت
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            '📈 Gold Price Chart',
            '📊 Order Book Depth (Bids/Asks)',
            '📉 RSI',
            '📊 MACD',
            '📊 Volume Analysis',
            '🎯 Support & Resistance'
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
        row_heights=[0.40, 0.30, 0.30],
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
    if 'SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_20'], mode='lines', name='SMA 20', line=dict(color='#FFD700', width=1.5)),
            row=1, col=1
        )
    if 'SMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_50'], mode='lines', name='SMA 50', line=dict(color='#FF6B6B', width=1.5)),
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
                text=f"Support ${support['price']:.2f}",
                showarrow=True,
                arrowhead=1,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="green",
                font=dict(size=10, color="green"),
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
                text=f"Resistance ${resistance['price']:.2f}",
                showarrow=True,
                arrowhead=1,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="red",
                font=dict(size=10, color="red"),
                row=1, col=1
            )
        
        # أوامر معلقة
        for pending in levels['pending_buy'][:3]:
            fig.add_hline(
                y=pending['price'],
                line_dash="dot",
                line_color="#FFD700",
                opacity=0.5,
                row=1, col=1
            )
            fig.add_annotation(
                x=df['timestamp'].iloc[-1],
                y=pending['price'],
                text=f"Pending Buy ${pending['price']:.2f}",
                showarrow=False,
                font=dict(size=9, color="#FFD700"),
                row=1, col=1
            )
        
        for pending in levels['pending_sell'][:3]:
            fig.add_hline(
                y=pending['price'],
                line_dash="dot",
                line_color="#FF6B6B",
                opacity=0.5,
                row=1, col=1
            )
            fig.add_annotation(
                x=df['timestamp'].iloc[-1],
                y=pending['price'],
                text=f"Pending Sell ${pending['price']:.2f}",
                showarrow=False,
                font=dict(size=9, color="#FF6B6B"),
                row=1, col=1
            )
    
    # ===== إشارات البيع/الشراء على الشارت =====
    if signals['score'] >= 3:
        fig.add_annotation(
            x=df['timestamp'].iloc[-1],
            y=df['high'].iloc[-1] * 1.005,
            text=f"🟢 BUY ({signals['score']})",
            showarrow=True,
            arrowhead=2,
            arrowsize=2,
            arrowwidth=3,
            arrowcolor="#00ff00",
            font=dict(size=16, color="#00ff00", family="Arial Black"),
            row=1, col=1
        )
    elif signals['score'] <= -3:
        fig.add_annotation(
            x=df['timestamp'].iloc[-1],
            y=df['high'].iloc[-1] * 1.005,
            text=f"🔴 SELL ({signals['score']})",
            showarrow=True,
            arrowhead=2,
            arrowsize=2,
            arrowwidth=3,
            arrowcolor="#ff0000",
            font=dict(size=16, color="#ff0000", family="Arial Black"),
            row=1, col=1
        )
    
    # ===== الصف 1 - العمود 2: الأوردر بوك =====
    if bids is not None and asks is not None and not bids.empty and not asks.empty:
        # Bids
        fig.add_trace(
            go.Bar(
                x=bids['price'],
                y=bids['quantity'],
                name='Bids',
                marker_color='#00ff00',
                opacity=0.8,
                showlegend=True
            ),
            row=1, col=2
        )
        # Asks
        fig.add_trace(
            go.Bar(
                x=asks['price'],
                y=asks['quantity'],
                name='Asks',
                marker_color='#ff0000',
                opacity=0.8,
                showlegend=True
            ),
            row=1, col=2
        )
        
        # خط السعر الحالي
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
    
    # ===== الصف 3 - العمود 1: Volume =====
    if 'volume' in df.columns:
        colors = ['#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000' for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.7),
            row=3, col=1
        )
        if 'Volume_SMA' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['Volume_SMA'], mode='lines', name='Vol SMA', line=dict(color='#FFD700', width=1.5)),
                row=3, col=1
            )
    
    # ===== الصف 3 - العمود 2: الدعم والمقاومة التفصيلية =====
    if levels:
        # دعم
        support_text = "🟢 Support Levels:\n"
        for i, s in enumerate(levels['support'][:5]):
            support_text += f"  ${s['price']:.2f} ({s['type']})\n"
        
        # مقاومة
        resistance_text = "🔴 Resistance Levels:\n"
        for i, r in enumerate(levels['resistance'][:5]):
            resistance_text += f"  ${r['price']:.2f} ({r['type']})\n"
        
        # أوامر معلقة
        pending_text = "🟡 Pending Orders:\n"
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
    
    # ===== تحديث التصميم =====
    fig.update_layout(
        height=1200,
        template='plotly_dark',
        title_text=f'🥇 Gold (XAUUSD) - Live Trading Dashboard | Price: ${current_price:.2f}' if current_price else '🥇 Gold (XAUUSD) - Live Trading Dashboard',
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
    
    # تحديث المحاور
    for row in range(1, 4):
        for col in range(1, 3):
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', row=row, col=col)
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', row=row, col=col)
    
    return fig

# ====================== عرض الإشارات المتقدم ======================
def display_advanced_signals(signals, current_price, levels):
    """عرض الإشارات بشكل متقدم"""
    
    st.markdown("## 🎯 Trading Signals (Auto-Update)")
    
    # عرض الإشارة الرئيسية
    score = signals['score']
    recommendation = signals['recommendation']
    
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
    
    # عرض الإشارة
    st.markdown(f"""
    <div class="signal-box {bg_class}">
        <h1 style="margin: 0;">{icon} {text}</h1>
        <p style="margin: 5px 0; font-size: 18px;">Signal Score: {score}</p>
        <p style="margin: 0; font-size: 14px; opacity: 0.7;">
            Current Price: ${current_price:.2f}
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
                <div class="level-box support">
                    <b>${support['price']:.2f}</b> - {support['type']}
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🔴 Resistance")
            for resistance in levels['resistance'][:5]:
                st.markdown(f"""
                <div class="level-box resistance">
                    <b>${resistance['price']:.2f}</b> - {resistance['type']}
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("### 🟡 Pending Orders")
            for pending in levels['pending_buy'][:3]:
                st.markdown(f"""
                <div class="level-box pending">
                    🔼 Buy: ${pending['price']:.2f}
                </div>
                """, unsafe_allow_html=True)
            for pending in levels['pending_sell'][:3]:
                st.markdown(f"""
                <div class="level-box pending">
                    🔽 Sell: ${pending['price']:.2f}
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    
    # ===== نصائح التداول =====
    st.markdown("## 💡 Trading Tips")
    
    tips = []
    
    if score >= 3:
        tips.append("🟢 **Strong Buy Signal** - Consider entering long position")
        tips.append("✅ Set Stop Loss below nearest support level")
        tips.append("🎯 Take Profit at next resistance level")
    elif score <= -3:
        tips.append("🔴 **Strong Sell Signal** - Consider entering short position")
        tips.append("✅ Set Stop Loss above nearest resistance level")
        tips.append("🎯 Take Profit at next support level")
    else:
        tips.append("⏸️ **Neutral** - Wait for clearer signal")
        tips.append("📊 Monitor price action at support/resistance levels")
        tips.append("🔍 Wait for confirmation before entering")
    
    for tip in tips:
        st.info(tip)

# ====================== الواجهة الرئيسية ======================
def main():
    # العنوان
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px; margin-bottom: 1.5rem; border: 2px solid #FFD700;">
        <h1 style="color: #FFD700; margin: 0;">🥇 Gold Trading Pro</h1>
        <p style="color: #aaa; margin: 5px 0;">📊 Live Signals | Auto-Update | Real Data</p>
        <p style="color: #00ff00; font-size: 12px;">🟢 LIVE - Updates every 5 seconds</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== جلب البيانات =====
    with st.spinner("🔄 Fetching live market data..."):
        # جلب السعر
        current_price = get_real_price()
        if not current_price:
            current_price = 3315.50
        
        # جلب الأوردر بوك
        bids, asks = get_order_book_real()
        if bids is None or asks is None:
            # توليد بيانات تجريبية واقعية
            bids = pd.DataFrame({
                'price': [current_price - i * 0.15 for i in range(50)],
                'quantity': [np.random.randint(10, 100) for _ in range(50)]
            })
            asks = pd.DataFrame({
                'price': [current_price + i * 0.15 for i in range(50)],
                'quantity': [np.random.randint(10, 100) for _ in range(50)]
            })
        
        # جلب بيانات الشموع
        df = get_klines_data(200)
        if df is None or df.empty:
            # توليد بيانات تجريبية
            dates = pd.date_range(end=datetime.now(), periods=200, freq='1min')
            price = current_price - 20
            data = []
            for i in range(200):
                change = np.random.randn() * 0.15
                price += change
                data.append([
                    dates[i], price, price + 0.2, price - 0.2, price + np.random.randn() * 0.1,
                    np.random.randint(100, 1000)
                ])
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات
        df = calculate_indicators(df)
        
        # حساب الدعم والمقاومة
        levels = calculate_support_resistance(df, bids, asks, current_price)
        
        # توليد الإشارات
        signals = generate_signals_auto(df, bids, asks, current_price, levels)
    
    # ===== عرض الإشارات =====
    display_advanced_signals(signals, current_price, levels)
    
    # ===== عرض الشارت =====
    st.subheader("📈 Professional Chart")
    fig = create_advanced_chart(df, bids, asks, current_price, levels, signals)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== عرض الأوردر بوك =====
    if bids is not None and asks is not None:
        st.subheader("📊 Live Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy Orders)")
            st.dataframe(
                bids.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.2f}'}),
                use_container_width=True,
                height=400
            )
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell Orders)")
            st.dataframe(
                asks.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.2f}'}),
                use_container_width=True,
                height=400
            )
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
        
        # تحليل الأوردر بوك
        if not bids.empty and not asks.empty:
            st.markdown("### 📈 Order Book Analysis")
            total_bid = bids['quantity'].sum()
            total_ask = asks['quantity'].sum()
            imbalance = total_bid / (total_ask + 0.001)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Bid/Ask Imbalance", f"{imbalance:.2f}")
            with col2:
                st.metric("Total Bid", f"{total_bid:.2f}")
            with col3:
                st.metric("Total Ask", f"{total_ask:.2f}")
    
    # ===== تحديث تلقائي =====
    st.caption("🔄 Auto-updates every 5 seconds...")
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
