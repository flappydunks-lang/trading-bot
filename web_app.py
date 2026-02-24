import streamlit as st
import sys
import json
import numpy as np
from pathlib import Path

# Page config
st.set_page_config(
    page_title="FinalAI Trading Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; }
    h1 { color: #00d4ff; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True  # Auto-login (no authentication required)
    st.session_state.username = "User"
    st.session_state.app = None

# Main app
def main_app():
    from Trading import ConfigurationManager, DataManager, TechnicalAnalyzer, UserManager, BacktestEngine, AIAnalyzer, PatternRecognizer, SmartMoneyAnalyzer, VolumeProfileAnalyzer
    
    # Sidebar navigation
    st.sidebar.title(f"🤖 FinalAI Quantum")
    st.sidebar.markdown(f"**Trading Bot v2.0** - No Authentication Required")
    
    st.sidebar.markdown("---")
    
    # Menu options
    page = st.sidebar.radio("Navigation", [
        "Setup Guide",
        "Analyze Stock",
        "Backtesting",
        "News & Intel",
        "Position Manager",
        "Bot Learning Dashboard",
        "AI Trade Advisor",
        "User Management",
        "Settings"
    ])
    
    app = st.session_state.app
    
    # Page routing
    if page == "Setup Guide":
        st.title("🚀 Complete Setup Guide")
        
        st.markdown("""
        ### Welcome! Let's get your trading bot fully configured.
        
        This guide will walk you through getting all the necessary API keys and setting up notifications.
        **Everything is FREE!** ✅
        """)
        
        # Check current API status
        config = ConfigurationManager.load_config()
        has_finnhub = bool(config.get('finnhub_api_key', '').strip())
        has_newsdata = bool(config.get('newsdata_api_key', '').strip())
        has_groq = bool(config.get('groq_api_key', '').strip())
        
        # Status overview
        st.subheader("📋 Current Status")
        col1, col2, col3 = st.columns(3)
        col1.metric("Finnhub API", "✅ Ready" if has_finnhub else "❌ Missing")
        col2.metric("NewsData.IO API", "✅ Ready" if has_newsdata else "❌ Missing")
        col3.metric("Groq AI API", "✅ Ready" if has_groq else "❌ Missing")
        
        st.markdown("---")
        
        # API Setup Instructions
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Finnhub", "📰 NewsData.IO", "🤖 Groq AI", "📱 Telegram Notifications"])
        
        with tab1:
            st.subheader("📈 Finnhub API - Stock News & Data")
            
            st.markdown("""
            **What it does:** Real-time company news, insider trades, analyst ratings, earnings data
            
            **How to get your FREE API key:**
            
            1. **Go to:** [https://finnhub.io/register](https://finnhub.io/register)
            2. **Sign up** with your email (takes 30 seconds)
            3. **Click** on your name (top right) → **Dashboard**
            4. **Copy** your API Key (looks like: `abc123def456...`)
            5. **Paste it below** ⬇️
            """)
            
            with st.form("finnhub_setup"):
                finnhub_key = st.text_input("Paste your Finnhub API Key here:", type="password")
                
                if st.form_submit_button("💾 Save Finnhub Key"):
                    if finnhub_key.strip():
                        config['finnhub_api_key'] = finnhub_key.strip()
                        ConfigurationManager.save_config(config)
                        st.success("✅ Finnhub API key saved!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter a valid API key")
            
            if has_finnhub:
                st.success("✅ Finnhub is already configured!")
        
        with tab2:
            st.subheader("📰 NewsData.IO - Geopolitical & Market News")
            
            st.markdown("""
            **What it does:** Fed decisions, tariffs, OPEC actions, geopolitical events that move markets
            
            **How to get your FREE API key:**
            
            1. **Go to:** [https://newsdata.io/register](https://newsdata.io/register)
            2. **Sign up** with your email
            3. **Verify** your email (check inbox)
            4. **Dashboard** will show your API Key
            5. **Copy** the API Key
            6. **Paste it below** ⬇️
            """)
            
            with st.form("newsdata_setup"):
                newsdata_key = st.text_input("Paste your NewsData.IO API Key here:", type="password")
                
                if st.form_submit_button("💾 Save NewsData Key"):
                    if newsdata_key.strip():
                        config['newsdata_api_key'] = newsdata_key.strip()
                        ConfigurationManager.save_config(config)
                        st.success("✅ NewsData.IO API key saved!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter a valid API key")
            
            if has_newsdata:
                st.success("✅ NewsData.IO is already configured!")
        
        with tab3:
            st.subheader("🤖 Groq AI - Trading Intelligence")
            
            st.markdown("""
            **What it does:** AI-powered stock analysis, trade recommendations, news synthesis
            
            **How to get your FREE API key:**
            
            1. **Go to:** [https://console.groq.com/keys](https://console.groq.com/keys)
            2. **Sign in** with Google/GitHub (instant)
            3. **Click** "Create API Key"
            4. **Name it** "Trading Bot" (or anything)
            5. **Copy** the key (looks like: `gsk_...`)
            6. **Paste it below** ⬇️
            
            ⚠️ **Important:** Copy it now! You can't see it again after closing.
            """)
            
            with st.form("groq_setup"):
                groq_key = st.text_input("Paste your Groq API Key here:", type="password")
                
                if st.form_submit_button("💾 Save Groq Key"):
                    if groq_key.strip():
                        config['groq_api_key'] = groq_key.strip()
                        ConfigurationManager.save_config(config)
                        st.success("✅ Groq AI API key saved!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter a valid API key")
            
            if has_groq:
                st.success("✅ Groq AI is already configured!")
        
        with tab4:
            st.subheader("📱 Telegram Notifications Setup")
            
            st.markdown("""
            **Get real-time trade alerts on your phone!**
            
            ### Step 1: Create Your Telegram Bot
            
            1. **Open Telegram** on your phone
            2. **Search for:** `@BotFather` (official Telegram bot)
            3. **Send:** `/newbot`
            4. **Name your bot:** "My Trading Alerts" (or anything)
            5. **Username:** Must end in `bot` (e.g., `mytradingalerts_bot`)
            6. **Copy** the API Token (looks like: `123456:ABC-DEF...`)
            7. **Paste it below** ⬇️
            
            ### Step 2: Get Your Chat ID
            
            1. **Search for your bot** in Telegram (the username you just created)
            2. **Send:** `/start` to your bot
            3. **Open this link** in your browser: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
               - Replace `<YOUR_BOT_TOKEN>` with the token from step 1
            4. **Look for** `"chat":{"id":123456789`
            5. **Copy** that number (your Chat ID)
            6. **Paste it below** ⬇️
            """)
            
            with st.form("telegram_setup"):
                bot_token = st.text_input("Telegram Bot Token:", type="password")
                chat_id = st.text_input("Your Telegram Chat ID:")
                
                col1, col2 = st.columns(2)
                with col1:
                    notify_trades = st.checkbox("Notify on trades", value=True)
                with col2:
                    notify_news = st.checkbox("Notify on important news", value=True)
                
                if st.form_submit_button("💾 Save Telegram Settings"):
                    if bot_token.strip() and chat_id.strip():
                        config['telegram_bot_token'] = bot_token.strip()
                        config['telegram_chat_id'] = chat_id.strip()
                        config['notify_trades'] = notify_trades
                        config['notify_news'] = notify_news
                        ConfigurationManager.save_config(config)
                        st.success("✅ Telegram notifications configured!")
                        st.info("💡 You'll now receive alerts on your phone!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter both Bot Token and Chat ID")
            
            if config.get('telegram_bot_token'):
                st.success("✅ Telegram is already configured!")
    
    elif page == "Analyze Stock":
        st.title("📊 Stock Analysis - Same as Terminal")
        st.markdown("*Using the exact same 80+ indicators, pattern detection, and analysis as the terminal version*")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            ticker = st.text_input("Enter Ticker Symbol:", "AAPL").upper().strip()
        with col2:
            st.write("")
            st.write("")
            analyze_btn = st.button("📊 Analyze", use_container_width=True)
        
        # Container for results (will appear right below search bar)
        results_container = st.container()
        
        # Container for progress/feedback (will appear below)
        feedback_container = st.container()
        
        if analyze_btn and ticker:
            try:
                with feedback_container:
                    st.info(f"📥 Fetching {ticker} historical data...")
                
                df = DataManager.fetch_data(ticker, period='1y', interval='1d')
                
                if df is None or len(df) == 0:
                    with feedback_container:
                        st.error(f"❌ Could not load data for {ticker}")
                        st.info("💡 Try: AAPL, MSFT, NVDA, GOOGL, TSLA, BTC-USD, ETH-USD")
                else:
                    with feedback_container:
                        st.success(f"✅ Loaded {len(df)} bars from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
                        st.info("🔢 Calculating 80+ technical indicators...")
                    
                    indicators = TechnicalAnalyzer.calculate_indicators(df)
                    
                    if indicators is None:
                        with feedback_container:
                            st.error("❌ Failed to calculate indicators")
                    else:
                        with feedback_container:
                            st.success("✅ Indicators calculated")
                            st.info("📐 Detecting price patterns...")
                        
                        patterns = PatternRecognizer.analyze(df)
                        
                        with feedback_container:
                            st.success("✅ Patterns detected")
                            st.info("💰 Analyzing Smart Money Concepts...") 
                        
                        market_structure = SmartMoneyAnalyzer.analyze(df, ticker)
                        
                        with feedback_container:
                            st.success("✅ Smart Money analysis complete")
                            st.info("📊 Building Volume Profile...")
                        
                        volume_profile = VolumeProfileAnalyzer.analyze(df)
                        
                        with feedback_container:
                            st.success("✅ Analysis Complete!\n")
                        
                        # ========== RESULTS SECTION (Right under search bar) ==========
                        with results_container:
                            st.markdown("---")
                            st.subheader(f"🎯 Analysis Results for {ticker}")
                            
                            # Price Overview
                            st.write(f"**Data Range:** {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({len(df)} bars)")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Current Price", f"${df['Close'].iloc[-1]:.2f}", 
                                        f"{((df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1) * 100:+.2f}%")
                            with col2:
                                st.metric("Day Open", f"${df['Open'].iloc[-1]:.2f}")
                            with col3:
                                st.metric("52W High/Low", 
                                        f"${df['High'].iloc[-250:].max():.2f} / ${df['Low'].iloc[-250:].min():.2f}")
                            
                            st.markdown("### 📊 Technical Indicators (80+)")
                            
                            # Create a detailed indicators table
                            indicators_data = {
                                "Category": [],
                                "Indicator": [],
                                "Value": []
                            }
                            
                            # Price
                            indicators_data["Category"].extend(["Price", "", ""])
                            indicators_data["Indicator"].extend(["Current", "Open/High/Low", "Volume"])
                            indicators_data["Value"].extend([
                                f"${indicators.price:.2f}",
                                f"${indicators.open:.2f} / ${indicators.high:.2f} / ${indicators.low:.2f}",
                                f"{indicators.volume:,.0f}"
                            ])
                            
                            # Trend
                            indicators_data["Category"].extend(["Trend", "", "", ""])
                            indicators_data["Indicator"].extend(["SMA 20/50/200", "EMA 12/26/50", "EMA 8/21/34", "VWAP"])
                            indicators_data["Value"].extend([
                                f"${indicators.sma_20:.2f} / ${indicators.sma_50:.2f} / ${indicators.sma_200:.2f}",
                                f"${indicators.ema_12:.2f} / ${indicators.ema_26:.2f} / ${indicators.ema_50:.2f}",
                                f"${indicators.ema_8:.2f} / ${indicators.ema_21:.2f} / ${indicators.ema_34:.2f}",
                                f"${indicators.vwap:.2f}"
                            ])
                            
                            # Momentum
                            indicators_data["Category"].extend(["Momentum", "", "", ""])
                            indicators_data["Indicator"].extend(["RSI (7/14)", "Stochastic K/D", "MACD", "Williams %R"])
                            indicators_data["Value"].extend([
                                f"{indicators.rsi_7:.1f} / {indicators.rsi_14:.1f}",
                                f"{indicators.stochastic_k:.1f} / {indicators.stochastic_d:.1f}",
                                f"{indicators.macd:.4f}",
                                f"{indicators.williams_r:.1f}"
                            ])
                            
                            # Volatility
                            indicators_data["Category"].extend(["Volatility", "", "", ""])
                            indicators_data["Indicator"].extend(["ATR", "Bollinger Bands", "Keltner Channel", "HMA(20)"])
                            indicators_data["Value"].extend([
                                f"{indicators.atr:.2f} ({indicators.atr_percent:.2f}%)",
                                f"${indicators.bb_upper:.2f} / ${indicators.bb_lower:.2f}",
                                f"${indicators.keltner_upper:.2f} / ${indicators.keltner_middle:.2f} / ${indicators.keltner_lower:.2f}",
                                f"{indicators.hma_20:.2f}"
                            ])
                            
                            # Strength
                            indicators_data["Category"].extend(["Strength", "", ""])
                            indicators_data["Indicator"].extend(["ADX", "+DI / -DI", "CCI"])
                            indicators_data["Value"].extend([
                                f"{indicators.adx:.1f}",
                                f"{indicators.plus_di:.1f} / {indicators.minus_di:.1f}",
                                f"{indicators.cci:.1f}"
                            ])
                            
                            # Volume
                            indicators_data["Category"].extend(["Volume", "", ""])
                            indicators_data["Indicator"].extend(["Volume Ratio", "OBV", "MFI"])
                            indicators_data["Value"].extend([
                                f"{indicators.volume_ratio:.2f}x",
                                f"{indicators.obv:,.0f}",
                                f"{indicators.mfi:.1f}"
                            ])
                            
                            # Regime
                            indicators_data["Category"].extend(["Regime"])
                            indicators_data["Indicator"].extend(["Market Regime / Confidence"])
                            indicators_data["Value"].extend([
                                f"{indicators.market_regime} ({indicators.regime_confidence}%)"
                            ])
                            
                            import pandas as pd
                            indicators_df = pd.DataFrame(indicators_data)
                            st.dataframe(indicators_df, use_container_width=True, hide_index=True)
                            
                            # Patterns
                            if patterns.bullish_patterns or patterns.bearish_patterns or patterns.candlestick_patterns:
                                st.markdown("### 📐 Detected Patterns")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if patterns.bullish_patterns:
                                        st.write("**🟢 Bullish:**")
                                        for p in patterns.bullish_patterns:
                                            st.write(f"  • {p}")
                                with col2:
                                    if patterns.bearish_patterns:
                                        st.write("**🔴 Bearish:**")
                                        for p in patterns.bearish_patterns:
                                            st.write(f"  • {p}")
                                with col3:
                                    if patterns.candlestick_patterns:
                                        st.write("**🕯️ Candlestick:**")
                                        for p in patterns.candlestick_patterns:
                                            st.write(f"  • {p}")
                            
                            # Smart Money
                            st.markdown("### 💰 Smart Money Concepts")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Market Structure", market_structure.structure)
                            with col2:
                                st.metric("Order Blocks", len(market_structure.order_blocks))
                            with col3:
                                st.metric("Fair Value Gaps", len(market_structure.fair_value_gaps))
                            with col4:
                                st.metric("Equilibrium", f"${market_structure.equilibrium:.2f}")
                            
                            # Volume Profile
                            st.markdown("### 📊 Volume Profile")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Point of Control (POC)", f"${volume_profile.poc:.2f}")
                            with col2:
                                st.metric("High Value Area", f"${volume_profile.high:.2f}")
                            with col3:
                                st.metric("Low Value Area", f"${volume_profile.low:.2f}")
                            
                            # Generate chart
                            st.markdown("### 📈 Price Chart with Indicators")
                            try:
                                import plotly.graph_objects as go
                                
                                fig = go.Figure()
                                fig.add_trace(go.Candlestick(
                                    x=df.index,
                                    open=df['Open'],
                                    high=df['High'],
                                    low=df['Low'],
                                    close=df['Close'],
                                    name='Price'
                                ))
                                
                                # Add moving averages
                                fig.add_trace(go.Scatter(x=df.index, y=df.index.map(lambda _: indicators.sma_20),
                                                        mode='lines', name='SMA 20', line=dict(color='blue', width=1)))
                                fig.add_trace(go.Scatter(x=df.index, y=df.index.map(lambda _: indicators.sma_50),
                                                        mode='lines', name='SMA 50', line=dict(color='orange', width=1)))
                                fig.add_trace(go.Scatter(x=df.index, y=df.index.map(lambda _: indicators.sma_200),
                                                        mode='lines', name='SMA 200', line=dict(color='red', width=1)))
                                
                                fig.update_layout(
                                    title=f"{ticker} Technical Analysis",
                                    yaxis_title="Stock Price",
                                    template="plotly_dark",
                                    xaxis_rangeslider_visible=False,
                                    height=500
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.warning(f"Could not generate chart: {str(e)}")
                            
                            st.markdown("---")
                            st.success("✅ **Analysis Complete!** This shows the same comprehensive analysis as the terminal version.")
                            st.info("💡 **Next Steps:** Use the **AI Trade Advisor** tab to get AI-powered trade recommendations")
                            
            except Exception as e:
                with feedback_container:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    with st.expander("📋 Error Details"):
                        st.code(traceback.format_exc())
    
    elif page == "AI Trade Advisor":
        st.title("💬 AI Trade Advisor")
        
        st.markdown("**Ask anything about stocks, trades, or markets - powered by Groq AI + live news data**")
        
        user_question = st.text_area("Ask about stocks or trading:", height=100, placeholder="e.g., Why is NVDA down? Should I buy Tesla? What's happening with oil prices?")
        
        # Container for results (will show right under the question)
        results_container = st.container()
        
        # Container for feedback/progress (will show below results)
        feedback_container = st.container()
        
        if st.button("🧠 Get AI Analysis"):
            if user_question:
                try:
                    config = ConfigurationManager.load_config()
                    groq_key = config.get('groq_api_key', '')
                    finnhub_key = config.get('finnhub_api_key', '')
                    newsdata_key = config.get('newsdata_api_key', '')
                    
                    if not groq_key:
                        with results_container:
                            st.error("⚠️ Please add your Groq API key in the Setup Guide tab first!")
                    else:
                        import re
                        import requests
                        from datetime import datetime, timedelta
                        from openai import OpenAI
                        import yfinance as yf
                        
                        # Extract potential ticker symbols
                        potential_tickers = re.findall(r'\b[A-Z]{1,5}\b', user_question)
                        
                        commodity_map = {
                            'gold': 'GC=F', 'silver': 'SI=F', 'oil': 'CL=F', 'crude oil': 'CL=F',
                            'bitcoin': 'BTC-USD', 'btc': 'BTC-USD',
                            'ethereum': 'ETH-USD', 'eth': 'ETH-USD',
                            'sp500': '^GSPC', 's&p 500': '^GSPC',
                            'nasdaq': '^IXIC', 'dow': '^DJI'
                        }
                        
                        question_lower = user_question.lower()
                        for name, ticker in commodity_map.items():
                            if name in question_lower:
                                potential_tickers.append(ticker)
                        
                        # Fetch prices
                        price_data = {}
                        if potential_tickers:
                            with feedback_container:
                                st.info(f"💰 Fetching LIVE real-time prices for: {', '.join(set(potential_tickers[:5]))}")
                            
                            for ticker in set(potential_tickers[:5]):
                                try:
                                    with feedback_container:
                                        st.write(f"   Fetching {ticker}...")
                                    
                                    stock = yf.Ticker(ticker)
                                    hist_intraday = stock.history(period='1d', interval='1m')
                                    hist_daily = stock.history(period='5d')
                                    
                                    if not hist_intraday.empty:
                                        current_price = hist_intraday['Close'].iloc[-1]
                                        if len(hist_daily) >= 2:
                                            prev_close = hist_daily['Close'].iloc[-2]
                                            change_pct = ((current_price / prev_close) - 1) * 100
                                        else:
                                            prev_close = current_price
                                            change_pct = 0
                                        
                                        info = stock.info
                                        price_data[ticker] = {
                                            'price': current_price,
                                            'change': change_pct,
                                            'name': info.get('longName', ticker),
                                            'currency': info.get('currency', 'USD'),
                                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                                        }
                                        with feedback_container:
                                            st.success(f"✅ Got LIVE price for {ticker}: ${current_price:.2f} (as of {datetime.now().strftime('%H:%M UTC')})")
                                    elif not hist_daily.empty:
                                        current_price = hist_daily['Close'].iloc[-1]
                                        if len(hist_daily) >= 2:
                                            prev_price = hist_daily['Close'].iloc[-2]
                                            change_pct = ((current_price / prev_price) - 1) * 100
                                        else:
                                            change_pct = 0
                                        
                                        info = stock.info
                                        price_data[ticker] = {
                                            'price': current_price,
                                            'change': change_pct,
                                            'name': info.get('longName', ticker),
                                            'currency': info.get('currency', 'USD'),
                                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                                        }
                                        with feedback_container:
                                            st.success(f"✅ Got price for {ticker}: ${current_price:.2f}")
                                    else:
                                        with feedback_container:
                                            st.warning(f"⚠️ No data available for {ticker}")
                                except Exception as e:
                                    with feedback_container:
                                        st.error(f"❌ Error fetching {ticker}: {str(e)}")
                        else:
                            with feedback_container:
                                st.warning("⚠️ No tickers detected in question")
                        
                        news_context = []
                        
                        # Fetch news
                        if newsdata_key:
                            with feedback_container:
                                st.info("📰 Scanning ALL factors that can affect this asset...")
                            
                            try:
                                search_queries = []
                                
                                if 'gold' in user_question.lower():
                                    search_queries.extend(['gold', 'precious metals', 'dollar', 'inflation', 'Fed'])
                                elif 'oil' in user_question.lower() or 'crude' in user_question.lower():
                                    search_queries.extend(['oil', 'crude oil', 'OPEC', 'energy', 'gasoline'])
                                elif 'bitcoin' in user_question.lower() or 'btc' in user_question.lower() or 'crypto' in user_question.lower():
                                    search_queries.extend(['bitcoin', 'cryptocurrency', 'crypto regulation', 'ethereum'])
                                elif potential_tickers:
                                    first_ticker = potential_tickers[0]
                                    if first_ticker == 'GC=F':
                                        search_queries.extend(['gold', 'precious metals', 'dollar', 'inflation'])
                                    elif first_ticker == 'CL=F':
                                        search_queries.extend(['oil', 'OPEC', 'energy', 'gasoline'])
                                    elif first_ticker == 'BTC-USD':
                                        search_queries.extend(['bitcoin', 'cryptocurrency', 'crypto regulation'])
                                    else:
                                        search_queries.append(first_ticker)
                                
                                search_queries.extend(['Federal Reserve', 'interest rates', 'stock market', 'economy'])
                                
                                seen = set()
                                search_queries = [x for x in search_queries if not (x in seen or seen.add(x))]
                                search_queries = search_queries[:8]
                                
                                with feedback_container:
                                    st.write(f"   🔍 Running {len(search_queries)} comprehensive searches...")
                                
                                articles_found = 0
                                
                                for query in search_queries:
                                    try:
                                        url = f"https://newsdata.io/api/1/news?apikey={newsdata_key}&q={query}&language=en&category=business"
                                        with feedback_container:
                                            st.write(f"      • Searching: {query}")
                                        resp = requests.get(url, timeout=10)
                                        
                                        if resp.status_code == 200:
                                            data = resp.json()
                                            articles = data.get('results', [])[:3]
                                            
                                            if articles:
                                                articles_found += len(articles)
                                                for article in articles:
                                                    headline = article.get('title', '')
                                                    if not any(n['headline'] == headline for n in news_context):
                                                        news_context.append({
                                                            'source': f"NewsData - {article.get('source_id', 'Unknown')}",
                                                            'headline': headline,
                                                            'summary': article.get('description', '')[:200] if article.get('description') else '',
                                                            'datetime': article.get('pubDate', 'Recent'),
                                                            'query': query
                                                        })
                                                with feedback_container:
                                                    st.write(f"         ✓ {len(articles)} articles")
                                        else:
                                            with feedback_container:
                                                st.write(f"         ⚠️ No results ({resp.status_code})")
                                    except Exception as e:
                                        with feedback_container:
                                            st.write(f"         ❌ Error: {str(e)}")
                                
                                if articles_found > 0:
                                    with feedback_container:
                                        st.success(f"✅ Found {len(news_context)} unique articles across {len(search_queries)} topics")
                                else:
                                    with feedback_container:
                                        st.warning("⚠️ No articles found from NewsData.IO")
                                        
                            except Exception as e:
                                with feedback_container:
                                    st.error(f"❌ NewsData.IO error: {str(e)}")
                        
                        # Finnhub news
                        if finnhub_key and potential_tickers:
                            with feedback_container:
                                st.info(f"📰 Fetching Finnhub news for tickers...")
                            
                            to_date = datetime.now().strftime('%Y-%m-%d')
                            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                            
                            for ticker in set(potential_tickers[:3]):
                                if ticker in ['GC=F', 'CL=F', 'SI=F', 'BTC-USD', 'ETH-USD', '^GSPC', '^IXIC', '^DJI']:
                                    with feedback_container:
                                        st.write(f"   ⏭️  Skipping {ticker} (commodity/index)")
                                    continue
                                
                                try:
                                    with feedback_container:
                                        st.write(f"   Searching Finnhub for {ticker}...")
                                    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={finnhub_key}"
                                    resp = requests.get(url, timeout=10)
                                    
                                    if resp.status_code == 200:
                                        articles = resp.json()
                                        if articles:
                                            with feedback_container:
                                                st.success(f"✅ Found {len(articles[:3])} articles for {ticker}")
                                            for article in articles[:3]:
                                                news_context.append({
                                                    'source': f'Finnhub - {ticker}',
                                                    'headline': article.get('headline', ''),
                                                    'summary': article.get('summary', '')[:200],
                                                    'datetime': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y-%m-%d %H:%M')
                                                })
                                        else:
                                            with feedback_container:
                                                st.warning(f"⚠️ No Finnhub articles for {ticker}")
                                    else:
                                        with feedback_container:
                                            st.warning(f"⚠️ Finnhub API error for {ticker}: {resp.status_code}")
                                except Exception as e:
                                    with feedback_container:
                                        st.error(f"❌ Error fetching Finnhub for {ticker}: {str(e)}")
                        
                        # Display prices and news FIRST in results_container
                        with results_container:
                            st.markdown("---")
                            st.subheader("📊 Data Analyzed for Recommendation")
                            
                            # Show prices
                            if price_data:
                                st.markdown("### 💰 LIVE Prices")
                                for ticker, data in price_data.items():
                                    arrow = "📈" if data['change'] >= 0 else "📉"
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric(f"{data['name']} ({ticker})", f"${data['price']:.2f}", f"{data['change']:+.2f}%")
                            else:
                                st.warning("⚠️ No price data fetched")
                            
                            # Show articles
                            if news_context:
                                st.markdown(f"### 📰 Recent Articles ({len(news_context)} found)")
                                for i, news in enumerate(news_context, 1):
                                    with st.expander(f"{i}. {news['source']} - {news['headline'][:70]}..."):
                                        st.write(f"**Source:** {news['source']}")
                                        st.write(f"**Time:** {news['datetime']}")
                                        st.write(f"**Headline:** {news['headline']}")
                                        if news['summary']:
                                            st.write(f"**Summary:** {news['summary']}")
                            else:
                                st.info("ℹ️ No articles found - analyzing based on price data only")
                        
                        # Format data for AI
                        price_summary = ""
                        if price_data:
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                            price_summary = f"=== REAL-TIME PRICE DATA (as of {current_time}) ===\n\n"
                            for ticker, data in price_data.items():
                                arrow = "📈" if data['change'] >= 0 else "📉"
                                price_summary += f"{arrow} {data['name']} ({ticker})\n"
                                price_summary += f"   Price: ${data['price']:.2f}\n"
                                price_summary += f"   Change: {data['change']:+.2f}%\n\n"
                        else:
                            price_summary = "No real-time price data was fetched.\n\n"
                        
                        if not news_context:
                            news_summary = "No recent news data available."
                        else:
                            news_summary = "=== RECENT NEWS & MARKET DATA ===\n\n"
                            for i, news in enumerate(news_context, 1):
                                news_summary += f"{i}. [{news['datetime']}] {news['source']}\n"
                                news_summary += f"   {news['headline']}\n"
                                if news['summary']:
                                    news_summary += f"   {news['summary']}\n"
                                news_summary += "\n"
                        
                        today = datetime.now().strftime('%Y-%m-%d')
                        
                        advisor_prompt = f"""You are a trading advisor. Analyze provided data and respond with detailed reasoning.

TODAY: {today}
LIVE DATA

Price Data:
{price_summary}

News:
{news_summary}

User Question: {user_question}

===== RESPOND WITH EXACTLY THIS FORMAT =====

**CURRENT PRICE:** [Show the price(s) you analyzed]

**KEY NEWS FACTORS:** [List 2-3 specific news items that affect the price]

**PRICE ANALYSIS:** [Explain what the price movement and news mean together - 3-4 sentences with reasoning]

**STANCE:** BULLISH or BEARISH or NEUTRAL [with 1 sentence explanation]

**ACTION:** BUY or SELL or HOLD or WATCH [with price target or exit level if relevant]

**RISK LEVEL:** HIGH or MEDIUM or LOW

===== RULES =====
1. CITE SPECIFIC PRICES from the data above
2. MENTION SPECIFIC NEWS HEADLINES in your analysis
3. EXPLAIN YOUR REASONING - why these prices + news = this recommendation
4. NO questions at end
5. NO offers to do more
6. Use exact numbers only
7. Be specific, not vague"""
                        
                        with feedback_container:
                            st.info("🔍 Calling Groq AI for detailed analysis with reasoning...")
                        
                        groq_client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": advisor_prompt}],
                            max_tokens=1000,
                            temperature=0.7
                        )
                        
                        analysis = response.choices[0].message.content
                        
                        lines = analysis.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            if line.strip().endswith('?'):
                                continue
                            if any(line.strip().startswith(x) for x in ['Want', 'Would', 'Should', 'Let', 'Feel', 'Do you', 'What do', "I'd love", "I'd recommend", "I'd suggest"]):
                                continue
                            cleaned_lines.append(line)
                        
                        analysis = '\n'.join(cleaned_lines).strip()
                        
                        # SHOW AI ANALYSIS AFTER data in results_container
                        with results_container:
                            st.markdown("---")
                            st.subheader("🎯 AI Analysis & Recommendation")
                            st.markdown(analysis)
                            st.markdown("---")
                        
                        # Then show success in feedback container
                        with feedback_container:
                            st.success("✅ Analysis Complete with reasoning!")
                    
                except Exception as e:
                    with results_container:
                        st.error(f"❌ Error: {str(e)}")
                    with feedback_container:
                        import traceback
                        with st.expander("📋 Error Details"):
                            st.code(traceback.format_exc())
            else:
                with results_container:
                    st.warning("Please enter a question")
    
# Run app directly (no login required)
main_app()
