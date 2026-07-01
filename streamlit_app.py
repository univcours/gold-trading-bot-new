@st.cache_data(ttl=5)
def get_current_price(symbol="PAXGUSDT"):
    try:
        # بدلنا الرابط الأساسي لـ api1
        url = "https://api1.binance.com/api/v3/ticker/price"
        params = {"symbol": symbol}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # زدنا فـ timeout
        response = requests.get(url, params=params, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                return float(data['price'])
        return None
            
    except Exception as e:
        print(f"Error: {e}") # باش يبان لينا الخطأ فـ Terminal
        return None
