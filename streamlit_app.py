import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import numpy as np

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Bot - Live Order Book",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== دوال جلب البيانات الحقيقية ======================
@st.cache_data(ttl=10)
def get_klines(symbol="PAXGUSDT", interval="1m", limit=100):
    """جلب بيانات الشموع الحقيقية من Binance"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                st.warning("⚠️ لا توجد بيانات من Binance، نستعمل بيانات تجريبية")
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
            st.warning(f"⚠️ API Binance مشغول (Status: {response.status_code})، نستعمل بيانات تجريبية")
            return generate_mock_data(limit)
            
    except Exception as e:
        st.warning(f"⚠️ خطأ في الاتصال: {str(e)}، نستعمل بيانات تجريبية")
        return generate_mock_data(limit)

@st.cache_data(ttl=5)
def get_order_book(symbol="PAXGUSDT", limit=50):
    """جلب الأوردر بوك الحقيقي من Binance"""
    try:
        url = "https://api.binance.com/api/v3/depth"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data or 'bids' not in data or 'asks' not in data:
                return generate_mock_order_book(limit)
            
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            
            if len(bids) == 0 or len(asks) == 0:
                return generate_mock_order_book(limit)
            
            bids['cumulative'] = bids['quantity'].cumsum()
            asks['cumulative'] = asks['quantity'].cumsum()
            
            total_bid_vol = bids['quantity'].sum()
            total_ask_vol = asks['quantity'].sum()
            bids['volume_percent'] = (bids['quantity'] / total_bid_vol * 100) if total_bid_vol > 0 else 0
            asks['volume_percent'] = (asks['quantity'] / total_ask_vol * 100) if total_ask_vol > 0 else 0
            
            return bids, asks
        else:
            return generate_mock_order_book(limit)
            
    except Exception as e:
        return generate_mock_order_book(limit)

@st.cache_data(ttl=5)
def get_current_price(symbol="PAXGUSDT"):
    """جلب السعر الحالي للذهب من Binance"""
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": symbol}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                return float(data['price'])
            return None
        return None
            
    except Exception as e:
        return None

def generate_mock_data(limit=100):
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='1min')
    base_price = 2300 + np.random.randn() * 10
    
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
    
    return pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def generate_mock_order_book(limit=50):
    base_price = 2300 + np.random.randn() * 2
    
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
    
    return bids, asks

# ====================== دوال الرسم ======================
def create_candlestick_chart(df, bids, asks):
    if df.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '📈 Japanese Candlestick',
            '📊 Order Book Depth',
            '📉 Volume',
            '📊 Cumulative Volume'
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
        row_heights=[0.6, 0.4]
    )

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
    
    if len(df) >= 20:
        df['SMA_20'] = df['close'].rolling(20).mean()
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['SMA_20'],
                mode='lines',
                name='SMA 20',
                line=dict(color='#FFD700', width=1.5, dash='dash')
            ),
            row=1, col=1
        )
    
    if len(df) >= 50:
        df['SMA_50'] = df['close'].rolling(50).mean()
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['SMA_50'],
                mode='lines',
                name='SMA 50',
                line=dict(color='#FF6B6B', width=1.5, dash='dash')
            ),
            row=1, col=1
        )
    
    if not bids.empty and not asks.empty:
        fig.add_trace(
            go.Bar(
                x=bids['price'].values,
                y=bids['quantity'].values,
                name=f'Bids ({len(bids)} levels)',
                marker_color='#00ff00',
                opacity=0.8,
                showlegend=True
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=asks['price'].values,
                y=asks['quantity'].values,
                name=f'Asks ({len(asks)} levels)',
                marker_color='#ff0000',
                opacity=0.8,
                showlegend=True
            ),
            row=1, col=2
        )

    colors = ['#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7,
            showlegend=True
        ),
        row=2, col=1
    )
    
    if not bids.empty and not asks.empty:
        fig.add_trace(
            go.Scatter(
                x=bids['price'].values,
                y=bids['cumulative'].values,
                mode='lines+markers',
                name='Cumulative Bids',
                line=dict(color='#00ff00', width=2),
                marker=dict(size=4),
                showlegend=True
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=asks['price'].values,
                y=asks['cumulative'].values,
                mode='lines+markers',
                name='Cumulative Asks',
                line=dict(color='#ff0000', width=2),
                marker=dict(size=4),
                showlegend=True
            ),
            row=2, col=2
        )

    fig.update_layout(
        height=800,
        template='plotly_dark',
        title_text='📊 PAXGUSDT (Gold) - Live Trading Dashboard',
        title_font=dict(size=24, color='white'),
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
    
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Price (USDT)", row=1, col=2)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(title_text="Price (USDT)", row=2, col=2)
    
    fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=1, col=2)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Cum. Volume", row=2, col=2)
    
    return fig

# ====================== عرض الأوردر بوك التفصيلي ======================
def display_detailed_order_book(bids, asks):
    if bids.empty or asks.empty:
        st.warning("⚠️ لا توجد بيانات للأوردر بوك")
        return
    
    st.subheader("📊 Order Book Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 Bids (Buy Orders)")
        st.dataframe(
            bids.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.4f}', 'volume_percent': '{:.2f}%'}),
            use_container_width=True,
            height=400
        )
        
        col1a, col1b, col1c = st.columns(3)
        with col1a:
            st.metric("Total Bid Vol", f"{bids['quantity'].sum():.2f}")
        with col1b:
            st.metric("Best Bid", f"${bids['price'].iloc[0]:.2f}")
        with col1c:
            st.metric("Bid Levels", len(bids))
    
    with col2:
        st.markdown("### 🔴 Asks (Sell Orders)")
        st.dataframe(
            asks.head(20).style.format({'price': '${:.2f}', 'quantity': '{:.4f}', 'volume_percent': '{:.2f}%'}),
            use_container_width=True,
            height=400
        )
        
        col2a, col2b, col2c = st.columns(3)
        with col2a:
            st.metric("Total Ask Vol", f"{asks['quantity'].sum():.2f}")
        with col2b:
            st.metric("Best Ask", f"${asks['price'].iloc[0]:.2f}")
        with col2c:
            st.metric("Ask Levels", len(asks))
    
    st.markdown("### 📈 Spread Analysis")
    spread = asks['price'].iloc[0] - bids['price'].iloc[0]
    spread_percent = (spread / ((bids['price'].iloc[0] + asks['price'].iloc[0]) / 2)) * 100
    
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("Current Spread", f"${spread:.2f}")
    with col4:
        st.metric("Spread %", f"{spread_percent:.4f}%")
    with col5:
        st.metric("Mid Price", f"${(bids['price'].iloc[0] + asks['price'].iloc[0]) / 2:.2f}")
    
    st.markdown("### 🎯 Largest Order Levels")
    col6, col7 = st.columns(2)
    
    with col6:
        st.markdown("**Top 5 Bid Levels**")
        top_bids = bids.nlargest(5, 'quantity')[['price', 'quantity', 'volume_percent']]
        st.dataframe(top_bids.style.format({'price': '${:.2f}', 'volume_percent': '{:.2f}%'}))
    
    with col7:
        st.markdown("**Top 5 Ask Levels**")
        top_asks = asks.nlargest(5, 'quantity')[['price', 'quantity', 'volume_percent']]
        st.dataframe(top_asks.style.format({'price': '${:.2f}', 'volume_percent': '{:.2f}%'}))

# ====================== إحصائيات السوق ======================
def display_market_stats(df, bids, asks, current_price):
    st.subheader("📈 Live Market Statistics")
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات")
        return
    
    if current_price:
        price = current_price
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0] * 100)
    else:
        price = df['close'].iloc[-1]
        price_change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 PAXG Price (Gold)", f"${price:.2f}", f"{price_change:+.2f}%")
    
    with col2:
        st.metric("📊 Volume", f"{df['volume'].sum():,.2f}")
    
    with col3:
        if not bids.empty and not asks.empty:
            spread = asks['price'].iloc[0] - bids['price'].iloc[0]
            st.metric("📏 Spread", f"${spread:.2f}")
        else:
            st.metric("📏 Spread", "N/A")
    
    with col4:
        if not bids.empty and not asks.empty:
            ratio = bids['quantity'].sum() / (asks['quantity'].sum() + 1e-8)
            st.metric("⚖️ B/A Ratio", f"{ratio:.2f}")
        else:
            st.metric("⚖️ B/A Ratio", "N/A")
    
    if not df.empty:
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Daily High", f"${df['high'].max():.2f}")
        with col6:
            st.metric("Daily Low", f"${df['low'].min():.2f}")
        with col7:
            st.metric("24h Range", f"${df['high'].max() - df['low'].min():.2f}")
        with col8:
            trades = int(df['volume'].sum() / 0.01)
            st.metric("Est. Trades", f"{trades:,}")

# ====================== الواجهة الرئيسية ======================
def main():
    st.title("🏆 Professional Gold Trading Bot")
    st.markdown("### 🔥 Live PAXGUSDT (Gold) Analysis with Real-time Order Book")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Trading Settings")
        
        timeframe = st.selectbox(
            "⏱️ Timeframe",
            ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            index=0
        )
        
        candle_limit = st.slider(
            "📊 Number of Candles",
            min_value=20,
            max_value=500,
            value=100,
            step=10
        )
        
        depth_levels = st.slider(
            "📋 Order Book Depth",
            min_value=10,
            max_value=100,
            value=50,
            step=5
        )
        
        st.divider()
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True)
        
        st.divider()
        st.info("📡 Connected to Binance")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with st.spinner("🔄 Loading market data..."):
        try:
            current_price = get_current_price("PAXGUSDT")
            
            if current_price:
                st.success(f"✅ السعر الحقيقي لـ PAXG: ${current_price:.2f}")
            else:
                st.warning("⚠️ جاري استعمال بيانات تجريبية")
            
            df = get_klines("PAXGUSDT", timeframe, candle_limit)
            
            if df.empty:
                df = generate_mock_data(candle_limit)
            
            bids, asks = get_order_book("PAXGUSDT", depth_levels)
            
            if bids.empty or asks.empty:
                bids, asks = generate_mock_order_book(depth_levels)
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return
    
    display_market_stats(df, bids, asks, current_price)
    
    st.divider()
    
    st.subheader("📈 Live Candlestick Chart")
    fig = create_candlestick_chart(df, bids, asks)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    display_detailed_order_book(bids, asks)
    
    if auto_refresh:
        st.caption("🔄 Auto-refreshing every 10 seconds...")
        time.sleep(10)
        st.rerun()

if __name__ == "__main__":
    main()
