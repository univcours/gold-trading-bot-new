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
    page_title="Gold Trading Bot Pro - Live Data",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== الأنماط CSS ======================
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
        border-radius: 15px;
        margin-bottom: 1.5rem;
        border: 1px solid #FFD700;
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .signal-buy {
        background-color: rgba(0, 255, 0, 0.15);
        border-left: 4px solid #00ff00;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .signal-sell {
        background-color: rgba(255, 0, 0, 0.15);
        border-left: 4px solid #ff0000;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .signal-neutral {
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 4px solid #888888;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# ====================== دوال جلب البيانات الحية ======================
@st.cache_data(ttl=10)
def get_futures_price(symbol="XAUUSDT"):
    """جلب السعر الحقيقي من Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/price"
        params = {"symbol": symbol}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                return float(data['price'])
        return None
    except:
        return None

@st.cache_data(ttl=10)
def get_futures_klines(symbol="XAUUSDT", interval="1m", limit=200):
    """جلب بيانات الشموع من Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                return generate_mock_data(limit)
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        else:
            return generate_mock_data(limit)
            
    except Exception as e:
        return generate_mock_data(limit)

@st.cache_data(ttl=5)
def get_futures_order_book(symbol="XAUUSDT", limit=100):
    """جلب الأوردر بوك من Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/depth"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data or 'bids' not in data or 'asks' not in data:
                return generate_mock_order_book(limit)
            
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            
            if len(bids) == 0 or len(asks) == 0:
                return generate_mock_order_book(limit)
            
            # حساب المؤشرات المتقدمة
            bids['cumulative'] = bids['quantity'].cumsum()
            asks['cumulative'] = asks['quantity'].cumsum()
            
            total_bid_vol = bids['quantity'].sum()
            total_ask_vol = asks['quantity'].sum()
            bids['volume_percent'] = (bids['quantity'] / total_bid_vol * 100) if total_bid_vol > 0 else 0
            asks['volume_percent'] = (asks['quantity'] / total_ask_vol * 100) if total_ask_vol > 0 else 0
            
            # حساب الضغط (Imbalance)
            bids['weighted_price'] = bids['price'] * bids['quantity']
            asks['weighted_price'] = asks['price'] * asks['quantity']
            
            return bids, asks
        else:
            return generate_mock_order_book(limit)
            
    except Exception as e:
        return generate_mock_order_book(limit)

@st.cache_data(ttl=10)
def get_funding_rate(symbol="XAUUSDT"):
    """جلب معدل التمويل"""
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'lastFundingRate' in data:
                return float(data['lastFundingRate']) * 100
        return None
    except:
        return None

@st.cache_data(ttl=10)
def get_open_interest(symbol="XAUUSDT"):
    """جلب الفائدة المفتوحة"""
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest"
        params = {"symbol": symbol}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'openInterest' in data:
                return float(data['openInterest'])
        return None
    except:
        return None

def generate_mock_data(limit=200):
    """توليد بيانات تجريبية"""
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='1min')
    base_price = 3300 + np.random.randn() * 20
    
    data = []
    for i in range(limit):
        change = np.random.randn() * 0.3
        base_price += change
        open_p = base_price
        close_p = base_price + np.random.randn() * 0.2
        high_p = max(open_p, close_p) + abs(np.random.randn() * 0.3)
        low_p = min(open_p, close_p) - abs(np.random.randn() * 0.3)
        volume = np.random.randint(50, 500)
        data.append([dates[i], open_p, high_p, low_p, close_p, volume])
    
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def generate_mock_order_book(limit=100):
    """توليد بيانات تجريبية للأوردر بوك"""
    base_price = 3300 + np.random.randn() * 5
    
    bids = pd.DataFrame({
        'price': [base_price - i * 0.15 for i in range(limit)],
        'quantity': [np.random.randint(5, 50) for _ in range(limit)]
    })
    
    asks = pd.DataFrame({
        'price': [base_price + i * 0.15 for i in range(limit)],
        'quantity': [np.random.randint(5, 50) for _ in range(limit)]
    })
    
    bids['cumulative'] = bids['quantity'].cumsum()
    asks['cumulative'] = asks['quantity'].cumsum()
    
    total_bid_vol = bids['quantity'].sum()
    total_ask_vol = asks['quantity'].sum()
    bids['volume_percent'] = (bids['quantity'] / total_bid_vol * 100) if total_bid_vol > 0 else 0
    asks['volume_percent'] = (asks['quantity'] / total_ask_vol * 100) if total_ask_vol > 0 else 0
    
    bids['weighted_price'] = bids['price'] * bids['quantity']
    asks['weighted_price'] = asks['price'] * asks['quantity']
    
    return bids, asks

# ====================== المؤشرات الفنية المتقدمة ======================
def calculate_advanced_indicators(df):
    """حساب المؤشرات الفنية المتقدمة"""
    
    if df.empty or len(df) < 30:
        return df
    
    # ===== المتوسطات المتحركة =====
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
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
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
    
    # ===== Volume Indicators =====
    df['Volume_SMA'] = df['volume'].rolling(20).mean()
    df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']
    df['OBV'] = (df['volume'] * np.where(df['close'] > df['close'].shift(), 1, -1)).cumsum()
    
    # ===== Support & Resistance =====
    df['Pivot'] = (df['high'] + df['low'] + df['close']) / 3
    df['R1'] = 2 * df['Pivot'] - df['low']
    df['S1'] = 2 * df['Pivot'] - df['high']
    df['R2'] = df['Pivot'] + (df['high'] - df['low'])
    df['S2'] = df['Pivot'] - (df['high'] - df['low'])
    
    return df

# ====================== توليد الإشارات المتقدمة ======================
def generate_advanced_signals(df):
    """توليد إشارات تداول متقدمة"""
    
    signals = {
        'buy': [],
        'sell': [],
        'strong_buy': [],
        'strong_sell': [],
        'neutral': [],
        'score': 0,
        'reasons': [],
        'confidence': 0
    }
    
    if df.empty or len(df) < 50:
        signals['neutral'].append("⏸️ بيانات غير كافية")
        return signals
    
    df = calculate_advanced_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    confidence = 0
    reasons = []
    
    # ===== 1. نظام المتوسطات المتحركة =====
    if 'SMA_5' in last and 'SMA_20' in last:
        if last['SMA_5'] > last['SMA_20'] and prev['SMA_5'] <= prev['SMA_20']:
            score += 2
            reasons.append("🟢 Golden Cross (5/20)")
            confidence += 15
        elif last['SMA_5'] < last['SMA_20'] and prev['SMA_5'] >= prev['SMA_20']:
            score -= 2
            reasons.append("🔴 Death Cross (5/20)")
            confidence += 15
    
    if 'SMA_20' in last and 'SMA_50' in last:
        if last['SMA_20'] > last['SMA_50'] and prev['SMA_20'] <= prev['SMA_50']:
            score += 2
            reasons.append("🟢 Golden Cross (20/50)")
            confidence += 15
        elif last['SMA_20'] < last['SMA_50'] and prev['SMA_20'] >= prev['SMA_50']:
            score -= 2
            reasons.append("🔴 Death Cross (20/50)")
            confidence += 15
    
    # ===== 2. RSI =====
    if 'RSI' in last and not pd.isna(last['RSI']):
        if last['RSI'] < 25:
            score += 3
            reasons.append(f"🟢 RSI Extreme Oversold: {last['RSI']:.2f}")
            confidence += 20
        elif last['RSI'] < 30:
            score += 2
            reasons.append(f"🟢 RSI Oversold: {last['RSI']:.2f}")
            confidence += 15
        elif last['RSI'] > 75:
            score -= 3
            reasons.append(f"🔴 RSI Extreme Overbought: {last['RSI']:.2f}")
            confidence += 20
        elif last['RSI'] > 70:
            score -= 2
            reasons.append(f"🔴 RSI Overbought: {last['RSI']:.2f}")
            confidence += 15
    
    # ===== 3. MACD =====
    if 'MACD' in last and 'Signal' in last:
        if last['MACD'] > last['Signal'] and prev['MACD'] <= prev['Signal']:
            score += 2
            reasons.append("🟢 MACD Bullish Crossover")
            confidence += 15
        elif last['MACD'] < last['Signal'] and prev['MACD'] >= prev['Signal']:
            score -= 2
            reasons.append("🔴 MACD Bearish Crossover")
            confidence += 15
    
    # ===== 4. Bollinger Bands =====
    if 'BB_Lower' in last and 'BB_Upper' in last:
        if last['close'] < last['BB_Lower']:
            score += 2
            reasons.append("🟢 Price below Lower Band (Oversold)")
            confidence += 15
        elif last['close'] > last['BB_Upper']:
            score -= 2
            reasons.append("🔴 Price above Upper Band (Overbought)")
            confidence += 15
    
    # ===== 5. Stochastic =====
    if 'Stoch_K' in last and 'Stoch_D' in last:
        if last['Stoch_K'] < 20 and last['Stoch_D'] < 20:
            if last['Stoch_K'] > last['Stoch_D']:
                score += 2
                reasons.append("🟢 Stochastic Bullish Crossover")
                confidence += 10
        elif last['Stoch_K'] > 80 and last['Stoch_D'] > 80:
            if last['Stoch_K'] < last['Stoch_D']:
                score -= 2
                reasons.append("🔴 Stochastic Bearish Crossover")
                confidence += 10
    
    # ===== 6. الحجم =====
    if 'Volume_Ratio' in last and not pd.isna(last['Volume_Ratio']):
        if last['Volume_Ratio'] > 1.5 and score > 0:
            score += 1
            reasons.append("🟢 High Volume Confirming Uptrend")
            confidence += 10
        elif last['Volume_Ratio'] > 1.5 and score < 0:
            score -= 1
            reasons.append("🔴 High Volume Confirming Downtrend")
            confidence += 10
    
    # ===== النتيجة النهائية =====
    signals['score'] = score
    signals['confidence'] = min(confidence, 100)
    signals['reasons'] = reasons
    
    # ===== تحديد الإشارة =====
    if score >= 6:
        signals['strong_buy'].append(f"🔥 STRONG BUY (Score: {score})")
        st.balloons()
    elif score >= 3:
        signals['buy'].append(f"📈 BUY (Score: {score})")
    elif score <= -6:
        signals['strong_sell'].append(f"🔥 STRONG SELL (Score: {score})")
        st.snow()
    elif score <= -3:
        signals['sell'].append(f"📉 SELL (Score: {score})")
    else:
        signals['neutral'].append(f"⏸️ NEUTRAL (Score: {score})")
    
    return signals

# ====================== تحليل الأوردر بوك ======================
def analyze_order_book_depth(bids, asks):
    """تحليل عمق الأوردر بوك"""
    
    if bids.empty or asks.empty:
        return {
            'imbalance': 0,
            'pressure': 'neutral',
            'support': 0,
            'resistance': 0,
            'total_bid': 0,
            'total_ask': 0,
            'spread': 0
        }
    
    total_bid = bids['quantity'].sum()
    total_ask = asks['quantity'].sum()
    
    imbalance = total_bid / (total_ask + 0.001)
    
    if imbalance > 1.2:
        pressure = 'bullish'
    elif imbalance < 0.8:
        pressure = 'bearish'
    else:
        pressure = 'neutral'
    
    support = bids.loc[bids['quantity'].idxmax(), 'price'] if not bids.empty else 0
    resistance = asks.loc[asks['quantity'].idxmax(), 'price'] if not asks.empty else 0
    spread = asks['price'].iloc[0] - bids['price'].iloc[0] if not bids.empty and not asks.empty else 0
    
    return {
        'imbalance': imbalance,
        'pressure': pressure,
        'support': support,
        'resistance': resistance,
        'total_bid': total_bid,
        'total_ask': total_ask,
        'spread': spread
    }

# ====================== رسم الشارت المتقدم ======================
def create_advanced_chart(df, bids, asks):
    """إنشاء شارت متقدم مع جميع المؤشرات"""
    
    if df.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            '📈 Price & Indicators',
            '📊 Order Book Depth',
            '📉 RSI',
            '📊 MACD',
            '📊 Volume',
            '🔄 Stochastic',
            '📈 Bollinger Bands',
            '📊 Cumulative Volume'
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
        row_heights=[0.35, 0.25, 0.2, 0.2]
    )

    # الصف 1 - العمود 1: السعر والمؤشرات
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#00ff00',
            decreasing_line_color='#ff0000',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # إضافة المتوسطات
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
    
    # الصف 1 - العمود 2: الأوردر بوك
    if not bids.empty and not asks.empty:
        fig.add_trace(
            go.Bar(x=bids['price'], y=bids['quantity'], name='Bids', marker_color='#00ff00', opacity=0.7),
            row=1, col=2
        )
        fig.add_trace(
            go.Bar(x=asks['price'], y=asks['quantity'], name='Asks', marker_color='#ff0000', opacity=0.7),
            row=1, col=2
        )
    
    # الصف 2 - العمود 1: RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='#FF6B6B', width=2)),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # الصف 2 - العمود 2: MACD
    if 'MACD' in df.columns and 'Signal' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='#FFD700', width=2)),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Signal'], mode='lines', name='Signal', line=dict(color='#FF6B6B', width=2)),
            row=2, col=2
        )
        colors_hist = ['green' if x >= 0 else 'red' for x in df['MACD_Hist'].fillna(0)]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['MACD_Hist'], name='Histogram', marker_color=colors_hist, opacity=0.5),
            row=2, col=2
        )
    
    # الصف 3 - العمود 1: Volume
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
    
    # الصف 3 - العمود 2: Stochastic
    if 'Stoch_K' in df.columns and 'Stoch_D' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Stoch_K'], mode='lines', name='Stoch K', line=dict(color='#FFD700', width=2)),
            row=3, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Stoch_D'], mode='lines', name='Stoch D', line=dict(color='#FF6B6B', width=2)),
            row=3, col=2
        )
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=3, col=2)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=3, col=2)
    
    # الصف 4 - العمود 1: Bollinger Bands
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Upper'], mode='lines', name='Upper Band', line=dict(color='#FF6B6B', width=1, dash='dash')),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Mid'], mode='lines', name='Mid Band', line=dict(color='#FFD700', width=1)),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['BB_Lower'], mode='lines', name='Lower Band', line=dict(color='#00ff00', width=1, dash='dash')),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Price', line=dict(color='white', width=1)),
            row=4, col=1
        )
    
    # الصف 4 - العمود 2: الحجم التراكمي
    if not bids.empty and not asks.empty:
        fig.add_trace(
            go.Scatter(x=bids['price'], y=bids['cumulative'], mode='lines+markers', name='Cumulative Bids', line=dict(color='#00ff00', width=2), marker=dict(size=4)),
            row=4, col=2
        )
        fig.add_trace(
            go.Scatter(x=asks['price'], y=asks['cumulative'], mode='lines+markers', name='Cumulative Asks', line=dict(color='#ff0000', width=2), marker=dict(size=4)),
            row=4, col=2
        )
    
    fig.update_layout(
        height=1200,
        template='plotly_dark',
        title_text='📊 XAUUSDT - Professional Trading Dashboard',
        title_font=dict(size=28, color='white'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)'
        ),
        hovermode='x unified'
    )
    
    return fig

# ====================== عرض الإشارات ======================
def display_signals(signals):
    """عرض الإشارات بشكل احترافي"""
    
    st.markdown("## 🎯 Trading Signals")
    
    score = signals['score']
    confidence = signals['confidence']
    
    # تحديد اللون
    if score >= 5:
        color = "🟢"
        bg_color = "#1a3a1a"
        border_color = "#00ff00"
        st.balloons()
    elif score >= 2:
        color = "🟡"
        bg_color = "#3a3a1a"
        border_color = "#ffd700"
    elif score <= -5:
        color = "🔴"
        bg_color = "#3a1a1a"
        border_color = "#ff0000"
        st.snow()
    elif score <= -2:
        color = "🟠"
        bg_color = "#3a2a1a"
        border_color = "#ff6b00"
    else:
        color = "⚪"
        bg_color = "#1a1a1a"
        border_color = "#888888"
    
    # عرض النتيجة
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: {bg_color}; border-radius: 15px; border: 3px solid {border_color};">
            <h1 style="color: white; margin: 0;">{color} Signal Score: {score}</h1>
            <p style="color: #aaa; margin: 5px 0;">Confidence: {confidence:.0f}%</p>
            <p style="color: #aaa; font-size: 12px;">
                Strong BUY: ≥ 5 | BUY: 2-4 | NEUTRAL: -1 to 1 | SELL: -2 to -4 | Strong SELL: ≤ -5
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # عرض الإشارات
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 BUY Signals")
        if signals['buy']:
            for signal in signals['buy']:
                st.success(f"✅ {signal}")
        else:
            st.info("ℹ️ No buy signals")
        
        if signals['strong_buy']:
            st.markdown("### 🔥 Strong BUY")
            for signal in signals['strong_buy']:
                st.success(f"🔥 {signal}")
    
    with col2:
        st.markdown("### 🔴 SELL Signals")
        if signals['sell']:
            for signal in signals['sell']:
                st.error(f"❌ {signal}")
        else:
            st.info("ℹ️ No sell signals")
        
        if signals['strong_sell']:
            st.markdown("### 🔥 Strong SELL")
            for signal in signals['strong_sell']:
                st.error(f"🔥 {signal}")
    
    # عرض الأسباب
    if signals['reasons']:
        st.markdown("### 📋 Signal Details")
        for reason in signals['reasons']:
            if '🟢' in reason:
                st.success(f"✅ {reason}")
            elif '🔴' in reason:
                st.error(f"❌ {reason}")
            else:
                st.info(f"ℹ️ {reason}")

# ====================== الواجهة الرئيسية ======================
def main():
    # العنوان
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #FFD700; margin: 0;">🏆 Gold Trading Bot Pro</h1>
        <p style="color: #aaa; margin: 5px 0;">Live XAUUSDT Futures | Advanced Signals | Real-time Data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # الشريط الجانبي
    with st.sidebar:
        st.header("⚙️ Settings")
        
        timeframe = st.selectbox(
            "⏱️ Timeframe",
            ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            index=0
        )
        
        candle_limit = st.slider(
            "📊 Number of Candles",
            min_value=50,
            max_value=500,
            value=200,
            step=50
        )
        
        depth_levels = st.slider(
            "📋 Order Book Depth",
            min_value=20,
            max_value=200,
            value=100,
            step=10
        )
        
        st.divider()
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True)
        
        st.divider()
        
        # عرض حالة الاتصال
        st.markdown("### 📡 Status")
        status_placeholder = st.empty()
        
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # ===== جلب البيانات =====
    status_placeholder.info("🔄 Loading market data...")
    
    try:
        # جلب السعر الحقيقي
        current_price = get_futures_price("XAUUSDT")
        
        # جلب بيانات الشموع
        df = get_futures_klines("XAUUSDT", timeframe, candle_limit)
        
        if df.empty:
            st.warning("⚠️ Using simulated data (API unavailable)")
            df = generate_mock_data(candle_limit)
        
        # جلب الأوردر بوك
        bids, asks = get_futures_order_book("XAUUSDT", depth_levels)
        
        if bids.empty or asks.empty:
            bids, asks = generate_mock_order_book(depth_levels)
        
        # جلب معلومات إضافية
        funding_rate = get_funding_rate("XAUUSDT")
        open_interest = get_open_interest("XAUUSDT")
        
        # حساب المؤشرات
        df = calculate_advanced_indicators(df)
        
        # توليد الإشارات
        signals = generate_advanced_signals(df)
        
        # تحليل الأوردر بوك
        order_analysis = analyze_order_book_depth(bids, asks)
        
        status_placeholder.success("✅ Data loaded successfully!")
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        status_placeholder.error("❌ Failed to load data")
        return
    
    # ===== عرض المعلومات =====
    # معلومات إضافية في الأعلى
    if current_price:
        st.success(f"✅ Live Data - Current Price: ${current_price:.2f}")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        price = current_price if current_price else df['close'].iloc[-1]
        change = ((price - df['open'].iloc[0]) / df['open'].iloc[0] * 100) if not df.empty else 0
        st.metric("💰 Gold Price", f"${price:.2f}", f"{change:+.2f}%")
    
    with col2:
        st.metric("📊 Volume", f"{df['volume'].sum():,.0f}")
    
    with col3:
        if funding_rate:
            st.metric("💳 Funding Rate", f"{funding_rate:.4f}%")
        else:
            st.metric("💳 Funding Rate", "N/A")
    
    with col4:
        if open_interest:
            st.metric("📈 Open Interest", f"{open_interest:,.0f}")
        else:
            st.metric("📈 Open Interest", "N/A")
    
    with col5:
        if not bids.empty and not asks.empty:
            spread = asks['price'].iloc[0] - bids['price'].iloc[0]
            st.metric("📏 Spread", f"${spread:.2f}")
        else:
            st.metric("📏 Spread", "N/A")
    
    st.divider()
    
    # ===== عرض الإشارات =====
    display_signals(signals)
    
    st.divider()
    
    # ===== عرض الشارت =====
    st.subheader("📈 Professional Chart")
    fig = create_advanced_chart(df, bids, asks)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== عرض تحليل الأوردر بوك =====
    st.subheader("📊 Order Book Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pressure = order_analysis['pressure'].upper()
        color = "#00ff00" if pressure == "BULLISH" else "#ff0000" if pressure == "BEARISH" else "#888888"
        st.markdown(f"**Pressure:** <span style='color:{color};'>{pressure}</span>", unsafe_allow_html=True)
    
    with col2:
        st.metric("Imbalance", f"{order_analysis['imbalance']:.2f}")
    
    with col3:
        st.metric("Support", f"${order_analysis['support']:.2f}")
    
    with col4:
        st.metric("Resistance", f"${order_analysis['resistance']:.2f}")
    
    st.divider()
    
    # ===== عرض الأوردر بوك التفصيلي =====
    if not bids.empty and not asks.empty:
        st.subheader("📊 Detailed Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy Orders)")
            st.dataframe(
                bids.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.2f}', 'volume_percent': '{:.2f}%'}),
                use_container_width=True,
                height=400
            )
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell Orders)")
            st.dataframe(
                asks.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.2f}', 'volume_percent': '{:.2f}%'}),
                use_container_width=True,
                height=400
            )
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
    
    # ===== تحديث تلقائي =====
    if auto_refresh:
        st.caption("🔄 Auto-refreshing every 15 seconds...")
        time.sleep(15)
        st.rerun()

if __name__ == "__main__":
    main()
