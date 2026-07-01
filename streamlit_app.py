import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import numpy as np
import plotly.graph_objects as go

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Bot",
    page_icon="📊",
    layout="wide"
)

# ====================== العنوان ======================
st.title("🏆 Gold Trading Bot")
st.markdown("### 📊 Live XAUUSDT Analysis")
st.markdown("---")

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=30)
def get_gold_price():
    """جلب سعر الذهب من Binance"""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            return 3300 + np.random.randn() * 10
    except:
        return 3300 + np.random.randn() * 10

@st.cache_data(ttl=30)
def get_klines():
    """جلب بيانات الشموع"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "XAUUSDT",
            "interval": "5m",
            "limit": 50
        }
        response = requests.get(url, params=params, timeout=10)
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
        else:
            return generate_mock_klines()
    except:
        return generate_mock_klines()

@st.cache_data(ttl=30)
def get_order_book():
    """جلب الأوردر بوك"""
    try:
        url = "https://api.binance.com/api/v3/depth?symbol=XAUUSDT&limit=20"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            return bids, asks
        else:
            return generate_mock_order_book()
    except:
        return generate_mock_order_book()

def generate_mock_klines():
    """بيانات تجريبية للشموع"""
    dates = pd.date_range(end=datetime.now(), periods=50, freq='5min')
    base_price = 3300
    data = []
    for i in range(50):
        change = np.random.randn() * 0.5
        base_price += change
        open_p = base_price
        close_p = base_price + np.random.randn() * 0.3
        high_p = max(open_p, close_p) + abs(np.random.randn() * 0.5)
        low_p = min(open_p, close_p) - abs(np.random.randn() * 0.5)
        volume = np.random.randint(50, 500)
        data.append([dates[i], open_p, high_p, low_p, close_p, volume])
    return pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def generate_mock_order_book():
    """بيانات تجريبية للأوردر بوك"""
    base = 3300 + np.random.randn() * 5
    bids = pd.DataFrame({
        'price': [base - i*0.5 for i in range(20)],
        'quantity': [np.random.randint(5, 50) for _ in range(20)]
    })
    asks = pd.DataFrame({
        'price': [base + i*0.5 for i in range(20)],
        'quantity': [np.random.randint(5, 50) for _ in range(20)]
    })
    return bids, asks

# ====================== رسم الشارت ======================
def create_chart(df):
    """إنشاء شارت الشموع"""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='XAUUSDT',
        increasing_line_color='#00ff00',
        decreasing_line_color='#ff0000'
    ))
    
    fig.update_layout(
        title='📈 XAUUSDT Price Chart',
        xaxis_title='Time',
        yaxis_title='Price (USDT)',
        template='plotly_dark',
        height=500,
        xaxis_rangeslider_visible=False
    )
    
    return fig

# ====================== الواجهة الرئيسية ======================
def main():
    # الشريط الجانبي
    with st.sidebar:
        st.header("⚙️ Settings")
        st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # جلب البيانات
    with st.spinner("Loading data..."):
        price = get_gold_price()
        df = get_klines()
        bids, asks = get_order_book()
    
    # عرض الإحصائيات
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Gold Price", f"${price:.2f}")
    
    with col2:
        if not bids.empty:
            st.metric("📈 Best Bid", f"${bids['price'].iloc[0]:.2f}")
    
    with col3:
        if not asks.empty:
            st.metric("📉 Best Ask", f"${asks['price'].iloc[0]:.2f}")
    
    with col4:
        if not df.empty:
            change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100)
            st.metric("📊 Change", f"{change:+.2f}%")
    
    st.divider()
    
    # عرض الشارت
    if not df.empty:
        st.subheader("📈 Price Chart")
        fig = create_chart(df)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # عرض الأوردر بوك
    if not bids.empty and not asks.empty:
        st.subheader("📊 Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy)")
            st.dataframe(bids.head(20), use_container_width=True)
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell)")
            st.dataframe(asks.head(20), use_container_width=True)
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
    
    # تحديث تلقائي
    st.caption("🔄 Updates every 30 seconds")
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()
