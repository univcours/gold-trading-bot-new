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
    page_title="Gold Trading Bot - Live Order Book",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=5)  # تحديث كل 5 ثواني
def get_klines(symbol="XAUUSDT", interval="1m", limit=500):
    """جلب بيانات الشموع من Binance Futures"""
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    try:
        response = requests.get(base_url + endpoint, params=params, timeout=10)
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        st.error(f"❌ خطأ في جلب الشموع: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3)  # تحديث كل 3 ثواني
def get_order_book(symbol="XAUUSDT", limit=100):
    """جلب الأوردر بوك التفصيلي من Binance Futures"""
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/depth"
    
    params = {
        "symbol": symbol,
        "limit": limit
    }
    
    try:
        response = requests.get(base_url + endpoint, params=params, timeout=10)
        data = response.json()
        
        # تحويل البيانات مع الحفاظ على الترتيب
        bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
        asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
        
        # إضافة عمود المجموع التراكمي
        bids['cumulative'] = bids['quantity'].cumsum()
        asks['cumulative'] = asks['quantity'].cumsum()
        
        # إضافة عمود النسبة المئوية للحجم
        total_bid_vol = bids['quantity'].sum()
        total_ask_vol = asks['quantity'].sum()
        bids['volume_percent'] = (bids['quantity'] / total_bid_vol * 100) if total_bid_vol > 0 else 0
        asks['volume_percent'] = (asks['quantity'] / total_ask_vol * 100) if total_ask_vol > 0 else 0
        
        return bids, asks
    
    except Exception as e:
        st.error(f"❌ خطأ في جلب الأوردر بوك: {e}")
        return pd.DataFrame(), pd.DataFrame()

# ====================== دوال الرسم المتقدمة ======================
def create_candlestick_chart(df, bids, asks):
    """إنشاء شارت الشموع اليابانية مع الأوردر بوك المدمج"""
    
    # إنشاء الشارت مع صفين (شارت رئيسي + حجم)
    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=(
            '📈 Japanese Candlestick',
            '📊 Order Book Depth',
            '💰 Price Levels',
            '📉 Volume',
            '📊 Cumulative Volume',
            '🎯 Volume by Price',
            '📈 Bid-Ask Spread',
            '🔄 Trading Activity',
            '📊 Market Profile'
        ),
        vertical_spacing=0.1,
        horizontal_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3],
        column_widths=[0.45, 0.3, 0.25],
        specs=[
            [{"secondary_y": False}, {"secondary_y": True}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]
        ]
    )

    # ========== الصف الأول ==========
    # 1. الشارت الرئيسي (الشموع اليابانية)
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
            increasing_fillcolor='#00ff00',
            decreasing_fillcolor='#ff0000',
            showlegend=True,
            line_width=1.5
        ),
        row=1, col=1
    )
    
    # إضافة المتوسطات المتحركة
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['SMA_20'],
            mode='lines',
            name='SMA 20',
            line=dict(color='#FFD700', width=1.5, dash='dash'),
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['SMA_50'],
            mode='lines',
            name='SMA 50',
            line=dict(color='#FF6B6B', width=1.5, dash='dash'),
            showlegend=True
        ),
        row=1, col=1
    )

    # 2. الأوردر بوك (المستويات حسب الحجم)
    # عرض الأوردر بوك كـ Bar Chart مع تفصيل المستويات
    
    # Bids
    fig.add_trace(
        go.Bar(
            x=bids['price'],
            y=bids['quantity'],
            name=f'Bids ({len(bids)} levels)',
            marker_color='#00ff00',
            opacity=0.8,
            showlegend=True,
            text=bids['volume_percent'].round(2).astype(str) + '%',
            textposition='outside',
            hovertemplate='Price: $%{x:.2f}<br>Volume: %{y:.2f}<br>%: %{text}<extra></extra>'
        ),
        row=1, col=2,
        secondary_y=False
    )
    
    # Asks
    fig.add_trace(
        go.Bar(
            x=asks['price'],
            y=asks['quantity'],
            name=f'Asks ({len(asks)} levels)',
            marker_color='#ff0000',
            opacity=0.8,
            showlegend=True,
            text=asks['volume_percent'].round(2).astype(str) + '%',
            textposition='outside',
            hovertemplate='Price: $%{x:.2f}<br>Volume: %{y:.2f}<br>%: %{text}<extra></extra>'
        ),
        row=1, col=2,
        secondary_y=True
    )
    
    # 3. عرض أهم المستويات السعرية (الدعم والمقاومة)
    # حساب المستويات الرئيسية
    current_price = df['close'].iloc[-1]
    price_range = df['high'].max() - df['low'].min()
    support_levels = []
    resistance_levels = []
    
    # تحديد المستويات بناءً على الأوردر بوك
    for i in range(5, min(20, len(bids)), 5):
        if bids['price'].iloc[i] < current_price:
            support_levels.append(bids['price'].iloc[i])
    
    for i in range(5, min(20, len(asks)), 5):
        if asks['price'].iloc[i] > current_price:
            resistance_levels.append(asks['price'].iloc[i])
    
    # رسم المستويات
    fig.add_trace(
        go.Scatter(
            x=[df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
            y=[current_price, current_price],
            mode='lines',
            name='Current Price',
            line=dict(color='#FFFFFF', width=2, dash='dash'),
            showlegend=True
        ),
        row=1, col=1
    )
    
    for level in support_levels[:3]:
        fig.add_trace(
            go.Scatter(
                x=[df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
                y=[level, level],
                mode='lines',
                name=f'Support ${level:.2f}',
                line=dict(color='#00ff00', width=1, dash='dot'),
                showlegend=True
            ),
            row=1, col=1
        )
    
    for level in resistance_levels[:3]:
        fig.add_trace(
            go.Scatter(
                x=[df['timestamp'].iloc[0], df['timestamp'].iloc[-1]],
                y=[level, level],
                mode='lines',
                name=f'Resistance ${level:.2f}',
                line=dict(color='#ff0000', width=1, dash='dot'),
                showlegend=True
            ),
            row=1, col=1
        )

    # ========== الصف الثاني ==========
    # 4. الحجم
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
    
    # 5. الحجم التراكمي للأوردر بوك
    fig.add_trace(
        go.Scatter(
            x=bids['price'],
            y=bids['cumulative'],
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
            x=asks['price'],
            y=asks['cumulative'],
            mode='lines+markers',
            name='Cumulative Asks',
            line=dict(color='#ff0000', width=2),
            marker=dict(size=4),
            showlegend=True
        ),
        row=2, col=2
    )
    
    # 6. توزيع الحجم حسب السعر (Volume Profile)
    # إنشاء مجموعات سعرية
    price_bins = np.linspace(df['low'].min(), df['high'].max(), 20)
    volume_by_price = []
    
    for i in range(len(price_bins)-1):
        mask = (df['close'] >= price_bins[i]) & (df['close'] < price_bins[i+1])
        vol_sum = df.loc[mask, 'volume'].sum()
        volume_by_price.append({
            'price_low': price_bins[i],
            'price_high': price_bins[i+1],
            'volume': vol_sum,
            'mid_price': (price_bins[i] + price_bins[i+1]) / 2
        })
    
    vol_df = pd.DataFrame(volume_by_price)
    
    fig.add_trace(
        go.Bar(
            x=vol_df['mid_price'],
            y=vol_df['volume'],
            name='Volume Profile',
            marker_color='#87CEEB',
            opacity=0.6,
            showlegend=True,
            hovertemplate='Price: $%{x:.2f}<br>Volume: %{y:.2f}<extra></extra>'
        ),
        row=2, col=3
    )

    # ========== الصف الثالث ==========
    # 7. Bid-Ask Spread
    spread = asks['price'].iloc[0] - bids['price'].iloc[0]
    spreads = []
    times = df['timestamp'].iloc[-50:]
    
    for i in range(len(times)):
        # محاكاة تغيرات الـ Spread
        simulated_spread = spread + np.random.normal(0, spread*0.05, 1)[0]
        spreads.append(max(simulated_spread, 0.01))
    
    fig.add_trace(
        go.Scatter(
            x=times,
            y=spreads,
            mode='lines+markers',
            name='Spread',
            line=dict(color='#FFD700', width=2),
            marker=dict(size=5),
            showlegend=True,
            fill='tozeroy',
            fillcolor='rgba(255, 215, 0, 0.2)'
        ),
        row=3, col=1
    )
    
    # 8. نشاط التداول (تغير السعر والحجم)
    price_change = df['close'].pct_change() * 100
    volume_change = df['volume'].pct_change() * 100
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=price_change,
            mode='lines',
            name='Price Change %',
            line=dict(color='#FF6B6B', width=1.5),
            showlegend=True
        ),
        row=3, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=volume_change,
            mode='lines',
            name='Volume Change %',
            line=dict(color='#4ECDC4', width=1.5),
            showlegend=True
        ),
        row=3, col=2
    )
    
    # 9. Market Profile (توزيع الصفقات)
    trade_activity = pd.DataFrame({
        'price': df['close'],
        'volume': df['volume'],
        'range': df['high'] - df['low']
    })
    
    fig.add_trace(
        go.Scatter(
            x=trade_activity['price'],
            y=trade_activity['volume'],
            mode='markers',
            name='Market Profile',
            marker=dict(
                size=trade_activity['range'] * 10,
                color=trade_activity['volume'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Volume"),
                opacity=0.7
            ),
            hovertemplate='Price: $%{x:.2f}<br>Volume: %{y:.2f}<br>Range: %{marker.size:.2f}<extra></extra>',
            showlegend=True
        ),
        row=3, col=3
    )

    # ========== تحديث التصميم ==========
    fig.update_layout(
        height=1200,
        template='plotly_dark',
        title_text='📊 XAUUSDT - Live Trading Dashboard with Order Book Depth',
        title_font=dict(size=28, color='white', family='Arial Black'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)'
        ),
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.1)'
    )
    
    # تحديث المحاور
    fig.update_xaxes(title_text="Time", row=1, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Price", row=1, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Price", row=1, col=3, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Time", row=2, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Price", row=2, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Price", row=2, col=3, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Time", row=3, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Time", row=3, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="Price", row=3, col=3, gridcolor='rgba(255,255,255,0.1)')
    
    fig.update_yaxes(title_text="Price (USDT)", row=1, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Volume", row=1, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Cum. Volume", row=2, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Volume", row=2, col=3, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Spread ($)", row=3, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Change (%)", row=3, col=2, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Volume", row=3, col=3, gridcolor='rgba(255,255,255,0.1)')
    
    # إضافة خطوط مرجعية
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=2)
    
    return fig

# ====================== عرض الأوردر بوك التفصيلي ======================
def display_detailed_order_book(bids, asks):
    """عرض الأوردر بوك بشكل تفصيلي مع جميع المستويات"""
    
    st.subheader("📊 Detailed Order Book Levels")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 Bids (Buy Orders)")
        st.dataframe(
            bids.head(20).style.background_gradient(subset=['volume_percent'], cmap='Greens'),
            use_container_width=True,
            height=400
        )
        
        # عرض إحصائيات الـ Bids
        col1a, col1b, col1c = st.columns(3)
        with col1a:
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        with col1b:
            st.metric("Best Bid", f"${bids['price'].iloc[0]:.2f}")
        with col1c:
            st.metric("Bid Levels", len(bids))
    
    with col2:
        st.markdown("### 🔴 Asks (Sell Orders)")
        st.dataframe(
            asks.head(20).style.background_gradient(subset=['volume_percent'], cmap='Reds'),
            use_container_width=True,
            height=400
        )
        
        # عرض إحصائيات الـ Asks
        col2a, col2b, col2c = st.columns(3)
        with col2a:
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
        with col2b:
            st.metric("Best Ask", f"${asks['price'].iloc[0]:.2f}")
        with col2c:
            st.metric("Ask Levels", len(asks))
    
    # عرض تحليل الفروقات
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
    
    # عرض أكبر المستويات حجماً
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
def display_market_stats(df, bids, asks):
    """عرض إحصائيات السوق"""
    
    st.subheader("📈 Live Market Statistics")
    
    current_price = df['close'].iloc[-1]
    price_change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Current Price",
            f"${current_price:.2f}",
            f"{price_change:.2f}%"
        )
    
    with col2:
        st.metric(
            "📊 24h Volume",
            f"${df['volume'].sum():,.2f}"
        )
    
    with col3:
        spread = asks['price'].iloc[0] - bids['price'].iloc[0]
        st.metric(
            "📏 Spread",
            f"${spread:.2f}"
        )
    
    with col4:
        volume_ratio = bids['quantity'].sum() / (asks['quantity'].sum() + 1)
        st.metric(
            "⚖️ Bid/Ask Ratio",
            f"{volume_ratio:.2f}"
        )
    
    # عرض معلومات إضافية
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("Daily High", f"${df['high'].max():.2f}")
    with col6:
        st.metric("Daily Low", f"${df['low'].min():.2f}")
    with col7:
        st.metric("24h High/Low", f"${df['high'].max() - df['low'].min():.2f}")
    with col8:
        trades = int(df['volume'].sum() / 0.01)  # تقدير
        st.metric("Est. Trades", f"{trades:,}")

# ====================== الواجهة الرئيسية ======================
def main():
    # عنوان التطبيق
    st.title("🏆 Professional Gold Trading Bot")
    st.markdown("### 🔥 Live XAUUSDT Analysis with Real-time Order Book")
    st.markdown("---")
    
    # ===== الشريط الجانبي =====
    with st.sidebar:
        st.header("⚙️ Trading Settings")
        
        # إعدادات الفريم
        timeframe = st.selectbox(
            "⏱️ Timeframe",
            ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"],
            index=0
        )
        
        # عدد الشموع
        candle_limit = st.slider(
            "📊 Number of Candles",
            min_value=50,
            max_value=500,
            value=100,
            step=50
        )
        
        # عمق الأوردر بوك
        depth_levels = st.slider(
            "📋 Order Book Depth",
            min_value=20,
            max_value=200,
            value=100,
            step=10
        )
        
        # تحديث تلقائي
        st.divider()
        auto_refresh = st.checkbox("🔄 Auto Refresh (5s)", value=True)
        refresh_time = 5 if auto_refresh else 0
        
        # عرض حالة الاتصال
        st.divider()
        st.info("📡 Connected to Binance Futures")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # زر التحديث اليدوي
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # ===== جلب البيانات =====
    # شريط التقدم
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    status_text = st.empty()
    
    try:
        # جلب الشموع
        status_text.text("🔄 Fetching candlestick data...")
        progress_bar.progress(25)
        
        df = get_klines("XAUUSDT", timeframe, candle_limit)
        
        if df.empty:
            st.error("❌ Failed to fetch candlestick data")
            return
        
        progress_bar.progress(50)
        status_text.text("📊 Fetching order book...")
        
        # جلب الأوردر بوك
        bids, asks = get_order_book("XAUUSDT", depth_levels)
        
        if bids.empty or asks.empty:
            st.error("❌ Failed to fetch order book data")
            return
        
        progress_bar.progress(100)
        status_text.text("✅ Data loaded successfully!")
        
        # إخفاء شريط التقدم بعد التحميل
        time.sleep(0.5)
        progress_placeholder.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return
    
    # ===== عرض البيانات =====
    # إحصائيات السوق
    display_market_stats(df, bids, asks)
    
    st.divider()
    
    # الشارت المتكامل
    st.subheader("📈 Live Candlestick Chart with Order Book")
    fig = create_candlestick_chart(df, bids, asks)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # الأوردر بوك التفصيلي
    display_detailed_order_book(bids, asks)
    
    # ===== تحديث تلقائي =====
    if auto_refresh:
        # عرض عداد التحديث
        st.markdown("---")
        st.caption(f"🔄 Auto-refresh every {refresh_time} seconds")
        
        # استخدام متغير للتحكم في التحديث
        if 'refresh_counter' not in st.session_state:
            st.session_state.refresh_counter = 0
        
        st.session_state.refresh_counter += 1
        
        # إعادة تشغيل التطبيق بعد المدة المحددة
        time.sleep(refresh_time)
        st.rerun()

# ====================== تشغيل التطبيق ======================
if __name__ == "__main__":
    main()
