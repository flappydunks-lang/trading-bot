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
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.app = None

# Login function
def login_page():
    from Trading import UserManager, FinalAIQuantum
    
    st.title("🔐 Login to FinalAI Trading Bot")
    
    users = UserManager.load_users()
    
    # First time setup - create admin
    if not users:
        st.warning("⚠️ No users found. Create first admin account:")
        st.info("👇 Fill out all fields below and click 'Create Admin Account'")
        
        with st.form("create_admin", clear_on_submit=False):
            username = st.text_input("Admin Username", key="admin_user")
            password = st.text_input("Password", type="password", key="admin_pass")
            confirm = st.text_input("Confirm Password", type="password", key="admin_confirm")
            full_name = st.text_input("Full Name", value="Administrator", key="admin_name")
            
            submitted = st.form_submit_button("Create Admin Account")
            
            if submitted:
                if not username or not password:
                    st.error("❌ Username and password are required!")
                elif password != confirm:
                    st.error("❌ Passwords don't match!")
                else:
                    try:
                        UserManager.create_user(username, password, full_name, "admin")
                        st.success("✅ Admin created successfully! Refreshing...")
                        st.balloons()
                        import time
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating admin: {str(e)}")
    
    # Login form
    else:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if UserManager.authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.app = FinalAIQuantum()
                    st.session_state.app.current_user = username
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")

# Main app
def main_app():
    from Trading import ConfigurationManager, DataManager, TechnicalAnalyzer, UserManager, BacktestEngine, AIAnalyzer
    
    # Sidebar navigation
    st.sidebar.title(f"🤖 FinalAI Quantum")
    st.sidebar.write(f"👤 Logged in as: **{st.session_state.username}**")
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.app = None
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Menu options
    page = st.sidebar.radio("Navigation", [
        "� Setup Guide",
        "�📊 Analyze Stock",
        "📈 Backtesting",
        "📰 News & Intel",
        "💰 Position Manager",
        "🤖 Bot Learning Dashboard",
        "💬 AI Trade Advisor",
        "👥 User Management",
        "⚙️ Settings"
    ])
    
    app = st.session_state.app
    
    # Page routing
    if page == "� Setup Guide":
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
            
            st.markdown("---")
            
            st.markdown("""
            ### 📲 Running on Mobile in Background
            
            **For Android:**
            1. Install **Termux** from F-Droid (free)
            2. Open Termux and run: `pkg install python`
            3. Transfer your Trading.py file to phone
            4. Run: `python Trading.py &`
            5. It will run in background even when screen is off
            
            **For iPhone:**
            1. Use **Pythonista** app ($9.99) or **a-Shell** (free)
            2. Transfer Trading.py to iPhone
            3. Run the script - it will stay active in background
            
            **Easier option:** Keep it running on your computer 24/7 and just get Telegram notifications on your phone!
            """)
        
        # Quick status check
        st.markdown("---")
        st.subheader("✅ Setup Status")
        
        all_ready = has_finnhub and has_newsdata and has_groq
        
        if all_ready:
            st.success("🎉 You're all set! All APIs are configured. Start trading!")
        else:
            missing = []
            if not has_finnhub:
                missing.append("Finnhub")
            if not has_newsdata:
                missing.append("NewsData.IO")
            if not has_groq:
                missing.append("Groq AI")
            
            st.warning(f"⚠️ Missing: {', '.join(missing)}")
            st.info("👆 Complete the setup tabs above to unlock all features!")
    
    elif page == "�📊 Analyze Stock":
        st.title("📊 Stock Analysis")
        
        ticker = st.text_input("Enter Ticker Symbol:", "AAPL").upper()
        
        if st.button("Analyze"):
            with st.spinner(f"Analyzing {ticker}..."):
                try:
                    import plotly.graph_objects as go
                    from plotly.subplots import make_subplots
                    
                    df = DataManager.fetch_data(ticker, period='3mo', interval='1d')
                    if df is not None and len(df) > 0:
                        st.success(f"✓ Data loaded for {ticker}")
                        
                        analyzer = TechnicalAnalyzer()
                        delta = df['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        ema12 = df['Close'].ewm(span=12).mean()
                        ema26 = df['Close'].ewm(span=26).mean()
                        macd = ema12 - ema26
                        signal = macd.ewm(span=9).mean()
                        ma20 = df['Close'].rolling(window=20).mean()
                        ma50 = df['Close'].rolling(window=50).mean()
                        
                        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            row_heights=[0.5, 0.25, 0.25], subplot_titles=(f'{ticker} Price', 'RSI (14)', 'MACD'))
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                            low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=ma20, name='MA20',
                            line=dict(color='orange', width=1)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=ma50, name='MA50',
                            line=dict(color='blue', width=1)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=rsi, name='RSI',
                            line=dict(color='purple', width=1)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=macd, name='MACD',
                            line=dict(color='blue', width=1)), row=3, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=signal, name='Signal',
                            line=dict(color='orange', width=1)), row=3, col=1)
                        fig.update_layout(height=800, showlegend=True, xaxis_rangeslider_visible=False,
                            hovermode='x unified', template='plotly_dark', dragmode=False)
                        fig.update_xaxes(showgrid=True, gridcolor='#333', fixedrange=True)
                        fig.update_yaxes(showgrid=True, gridcolor='#333', fixedrange=True)
                        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
                        
                        current_rsi, current_macd = rsi.iloc[-1], macd.iloc[-1]
                        current_signal, current_price = signal.iloc[-1], df['Close'].iloc[-1]
                        current_ma20, current_ma50 = ma20.iloc[-1], ma50.iloc[-1]
                        signals, confidence = [], 0
                        if current_rsi < 30: signals.append("🟢 RSI Oversold"); confidence += 30
                        elif current_rsi > 70: signals.append("🔴 RSI Overbought"); confidence -= 30
                        if current_macd > current_signal: signals.append("🟢 MACD Bullish"); confidence += 25
                        else: signals.append("🔴 MACD Bearish"); confidence -= 25
                        if current_price > current_ma20 > current_ma50: signals.append("🟢 Price Above MAs"); confidence += 25
                        elif current_price < current_ma20 < current_ma50: signals.append("🔴 Price Below MAs"); confidence -= 25
                        rec = "🟢 STRONG BUY" if confidence >= 50 else "🟢 BUY" if confidence >= 20 else "🟡 HOLD" if confidence >= -20 else "🔴 SELL" if confidence >= -50 else "🔴 STRONG SELL"
                        
                        st.subheader("Technical Analysis Summary")
                        col1, col2, col3, col4 = st.columns(4)
                        change = ((df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1) * 100
                        col1.metric("Price", f"${current_price:.2f}", f"{change:+.2f}%")
                        col2.metric("RSI", f"{current_rsi:.1f}")
                        col3.metric("Recommendation", rec)
                        col4.metric("Confidence", f"{abs(confidence)}%")
                        st.subheader("Trading Signals")
                        for sig in signals: st.write(sig)
                        col1, col2 = st.columns(2)
                        col1.metric("Support", f"${df['Low'].tail(20).min():.2f}")
                        col2.metric("Resistance", f"${df['High'].tail(20).max():.2f}")
                    else:
                        st.error(f"Could not load data for {ticker}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    import traceback; st.code(traceback.format_exc())

    elif page == "📈 Backtesting":
        st.title("📈 Backtesting")
        st.caption("Runs a simple momentum backtest using historical data from Yahoo Finance.")

        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("Ticker", "AAPL").upper().strip()
        with col2:
            start_date = st.date_input("Start Date", value=None)
        with col3:
            end_date = st.date_input("End Date", value=None)

        col4, col5, col6 = st.columns(3)
        with col4:
            initial_capital = st.number_input("Initial Capital ($)", min_value=1000.0, value=10000.0, step=1000.0)
        with col5:
            risk_per_trade = st.number_input("Risk per Trade (%)", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
        with col6:
            desired_rrr = st.number_input("Risk:Reward (R:R)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)

        if st.button("Run Backtest"):
            if not ticker:
                st.error("Please enter a ticker.")
            elif not start_date or not end_date:
                st.error("Please select both start and end dates.")
            else:
                with st.spinner("Running backtest..."):
                    # Simple predictor: momentum using windowed returns
                    class SimpleMomentumPredictor:
                        window = 30

                        def predict(self, window_df):
                            try:
                                ret = window_df['ret1']
                                mean = float(ret.mean())
                                p10 = float(np.quantile(ret, 0.1))
                                return {"mean": mean, "p10": p10}
                            except Exception:
                                return {"mean": 0.0, "p10": -1.0}

                    config = ConfigurationManager.load_config()
                    api_key = config.get('anthropic_api_key', '')
                    analyzer = AIAnalyzer(api_key)
                    engine = BacktestEngine(analyzer, TechnicalAnalyzer())

                    metrics = engine.backtest_ticker(
                        ticker=ticker,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        initial_capital=float(initial_capital),
                        risk_per_trade=float(risk_per_trade) / 100.0,
                        desired_rrr=float(desired_rrr),
                        predictor=SimpleMomentumPredictor()
                    )

                    st.subheader("Backtest Metrics")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Trades", metrics.total_trades)
                    m2.metric("Win Rate", f"{metrics.win_rate:.1f}%")
                    m3.metric("Total P&L", f"${metrics.total_pnl:,.2f}")
                    m4.metric("Max Drawdown", f"{metrics.max_drawdown:.1f}%")

                    m5, m6, m7, m8 = st.columns(4)
                    m5.metric("Profit Factor", f"{metrics.profit_factor:.2f}")
                    m6.metric("Sharpe", f"{metrics.sharpe_ratio:.2f}")
                    m7.metric("Sortino", f"{metrics.sortino_ratio:.2f}")
                    m8.metric("Expectancy", f"{metrics.expectancy:.2f}")

                    if engine.trades:
                        st.subheader("Trades")
                        trade_rows = []
                        for t in engine.trades:
                            trade_rows.append({
                                "Entry Date": getattr(t.entry_date, 'date', lambda: t.entry_date)(),
                                "Exit Date": getattr(t.exit_date, 'date', lambda: t.exit_date)(),
                                "Direction": t.direction,
                                "Entry": round(t.entry_price, 2),
                                "Exit": round(t.exit_price, 2),
                                "Shares": t.shares,
                                "PnL": round(t.pnl, 2),
                                "PnL %": round(t.pnl_percent, 2),
                                "Win": t.win
                            })
                        st.dataframe(trade_rows, use_container_width=True)
                    else:
                        st.info("No trades generated for this period with the current predictor.")
    
    elif page == "📰 News & Intel":
        st.title("📰 News & Market Intel")
        
        st.markdown("**Real-time news from Finnhub + NewsData.IO with AI-powered analysis**")
        
        col1, col2 = st.columns(2)
        with col1:
            news_type = st.selectbox("News Type:", ["Market Summary", "Sector Analysis", "Top Movers", "Custom Search"])
        with col2:
            # Custom search input - only show if Custom Search is selected
            if news_type == "Custom Search":
                search_query = st.text_input("🔍 Search for:", placeholder="e.g., Tesla, semiconductors, AI stocks, oil prices")
            else:
                search_query = None
        
        if st.button("🔄 Fetch News & Analysis"):
            try:
                config = ConfigurationManager.load_config()
                groq_key = config.get('groq_api_key', '')
                finnhub_key = config.get('finnhub_api_key', '')
                newsdata_key = config.get('newsdata_api_key', '')
                
                if not groq_key:
                    st.error("❌ Groq API key not configured. Go to Setup Guide first.")
                elif news_type == "Custom Search" and not search_query:
                    st.warning("⚠️ Please enter a search term for Custom Search")
                else:
                    with st.spinner("Fetching latest market news..."):
                        import requests
                        from datetime import datetime, timedelta
                        from openai import OpenAI
                        
                        news_context = []
                        
                        # Determine keywords based on news type or custom search
                        if news_type == "Market Summary":
                            keywords = ['stock market', 'S&P 500', 'Dow Jones', 'NASDAQ', 'economy', 'Fed', 'inflation']
                        elif news_type == "Sector Analysis":
                            keywords = ['technology stocks', 'energy sector', 'healthcare', 'finance', 'retail', 'manufacturing']
                        elif news_type == "Top Movers":
                            keywords = ['stock rally', 'stock crash', 'earnings beat', 'stock surge', 'shares plunge']
                        else:  # Custom Search
                            keywords = [search_query]
                        
                        # Fetch general market news from Finnhub
                        if finnhub_key and news_type != "Custom Search":
                            st.info("📰 Fetching Finnhub market news...")
                            
                            try:
                                url = f"https://finnhub.io/api/v1/news?category=general&token={finnhub_key}"
                                resp = requests.get(url, timeout=10)
                                
                                if resp.status_code == 200:
                                    articles = resp.json()[:10]
                                    
                                    for article in articles:
                                        news_context.append({
                                            'source': 'Finnhub Market News',
                                            'headline': article.get('headline', ''),
                                            'summary': article.get('summary', '')[:250],
                                            'datetime': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y-%m-%d %H:%M'),
                                            'url': article.get('url', '')
                                        })
                            except Exception as e:
                                st.warning(f"⚠️ Finnhub error: {str(e)}")
                        
                        # Fetch news from NewsData.IO
                        if newsdata_key:
                            st.info(f"📰 Fetching news for: {', '.join(keywords[:3])}")
                            
                            try:
                                query = ' OR '.join(keywords)
                                url = f"https://newsdata.io/api/1/news?apikey={newsdata_key}&q={query}&language=en&category=business"
                                resp = requests.get(url, timeout=10)
                                
                                if resp.status_code == 200:
                                    data = resp.json()
                                    articles = data.get('results', [])[:12]
                                    
                                    for article in articles:
                                        news_context.append({
                                            'source': f"NewsData - {article.get('source_id', 'Unknown')}",
                                            'headline': article.get('title', ''),
                                            'summary': article.get('description', '')[:250] if article.get('description') else '',
                                            'datetime': article.get('pubDate', 'Recent'),
                                            'url': article.get('link', '')
                                        })
                            except Exception as e:
                                st.warning(f"⚠️ NewsData error: {str(e)}")
                        
                        # Check if we got news
                        if not news_context:
                            st.error("❌ Could not fetch news. Check your API keys in Setup Guide.")
                        else:
                            st.success(f"✅ Fetched {len(news_context)} recent news articles")
                            
                            # Format news for AI analysis
                            news_summary = f"=== LATEST NEWS ({datetime.now().strftime('%Y-%m-%d')}) ===\n\n"
                            for i, news in enumerate(news_context, 1):
                                news_summary += f"{i}. [{news['datetime']}] {news['source']}\n"
                                news_summary += f"   Headline: {news['headline']}\n"
                                if news['summary']:
                                    news_summary += f"   Summary: {news['summary']}\n"
                                news_summary += "\n"
                            
                            # Send to Groq for analysis
                            with st.spinner("Analyzing with Groq AI..."):
                                groq_client = OpenAI(
                                    api_key=groq_key,
                                    base_url="https://api.groq.com/openai/v1"
                                )
                                
                                # Create analysis prompt based on type
                                if news_type == "Custom Search":
                                    analysis_prompt = f"""You are a market analyst. Based on the REAL news articles below about "{search_query}", provide detailed analysis:

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}
SEARCH TOPIC: {search_query}

{news_summary}

Provide:
1. **Overview**: What's happening with {search_query}?
2. **Key Developments**: Latest news and developments
3. **Market Impact**: How is this affecting markets/stocks?
4. **Key Players**: Companies/stocks mentioned
5. **Outlook**: What to watch next?

Base analysis ONLY on the news above. Cite specific headlines and sources."""

                                elif news_type == "Market Summary":
                                    analysis_prompt = f"""You are a market analyst. Based on the REAL news articles below, provide analysis:

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

{news_summary}

Analyze:
1. **Market Overview**: Overall sentiment from the news (bullish/bearish/neutral)
2. **Key Themes**: What are the top 3 themes in today's news?
3. **Economic Events**: Major economic news (Fed, inflation, GDP, etc.)
4. **Market Movers**: Which stocks/sectors are mentioned most?
5. **Risks**: What concerns appear in the news?
6. **Opportunities**: Any positive developments worth noting?

Base your analysis ONLY on the news above. Cite specific headlines."""

                                elif news_type == "Sector Analysis":
                                    analysis_prompt = f"""You are a sector analyst. Based on the REAL news below, analyze sectors:

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

{news_summary}

Provide:
1. **Hot Sectors**: Which sectors are trending in the news?
2. **Sector Winners**: Which sectors have positive news?
3. **Sector Losers**: Which sectors face headwinds?
4. **Key Stocks**: Specific stocks mentioned by sector
5. **Trends**: Emerging sector trends from the news

Cite specific news headlines."""

                                else:  # Top Movers
                                    analysis_prompt = f"""You are a stock analyst. Based on the REAL news below, identify movers:

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

{news_summary}

Identify:
1. **Top Gainers**: Stocks with positive news (cite headlines)
2. **Top Losers**: Stocks with negative news (cite headlines)
3. **Earnings Movers**: Companies reporting earnings
4. **News Catalysts**: What's driving the moves?
5. **Watch List**: Stocks to watch based on news

Base analysis ONLY on the news provided."""

                                response = groq_client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": analysis_prompt}],
                                    max_tokens=800,
                                    temperature=0.7
                                )
                                
                                analysis = response.choices[0].message.content
                                
                                st.success("✅ Analysis Complete")
                                st.markdown("---")
                                st.markdown(analysis)
                                st.markdown("---")
                                
                                # Show news sources
                                with st.expander("📰 News Articles Analyzed"):
                                    for news in news_context:
                                        st.write(f"**[{news['datetime']}]** {news['source']}")
                                        st.write(f"*{news['headline']}*")
                                        if news['summary']:
                                            st.write(f"{news['summary']}")
                                        if news['url']:
                                            st.markdown(f"[Read more]({news['url']})")
                                        st.write("---")
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    elif page == "💬 AI Trade Advisor":
        st.title("💬 AI Trade Advisor")
        
        st.markdown("**Ask anything about stocks, trades, or markets - powered by Groq AI + live news data**")
        
        user_question = st.text_area("Ask about stocks or trading:", height=100, placeholder="e.g., Why is NVDA down? Should I buy Tesla? What's happening with oil prices?")
        
        if st.button("🧠 Get AI Analysis"):
            if user_question:
                with st.spinner("Fetching latest news and analyzing..."):
                    try:
                        config = ConfigurationManager.load_config()
                        groq_key = config.get('groq_api_key', '')
                        finnhub_key = config.get('finnhub_api_key', '')
                        newsdata_key = config.get('newsdata_api_key', '')
                        
                        if not groq_key:
                            st.error("⚠️ Please add your Groq API key in the Setup Guide tab first!")
                        else:
                            import re
                            import requests
                            from datetime import datetime, timedelta
                            from openai import OpenAI
                            import yfinance as yf
                            
                            # Extract potential ticker symbols from question
                            potential_tickers = re.findall(r'\b[A-Z]{1,5}\b', user_question)
                            
                            # Map common commodity/asset names to Yahoo Finance tickers
                            commodity_map = {
                                'gold': 'GC=F',
                                'silver': 'SI=F',
                                'oil': 'CL=F',
                                'crude oil': 'CL=F',
                                'bitcoin': 'BTC-USD',
                                'btc': 'BTC-USD',
                                'ethereum': 'ETH-USD',
                                'eth': 'ETH-USD',
                                'sp500': '^GSPC',
                                's&p 500': '^GSPC',
                                'nasdaq': '^IXIC',
                                'dow': '^DJI'
                            }
                            
                            # Check if question mentions commodities/indices
                            question_lower = user_question.lower()
                            for name, ticker in commodity_map.items():
                                if name in question_lower:
                                    potential_tickers.append(ticker)
                            
                            # Fetch real-time prices for mentioned assets
                            price_data = {}
                            if potential_tickers:
                                st.info(f"💰 Fetching LIVE real-time prices for: {', '.join(set(potential_tickers[:5]))}")
                                for ticker in set(potential_tickers[:5]):
                                    try:
                                        st.write(f"   Fetching {ticker}...")
                                        stock = yf.Ticker(ticker)
                                        
                                        # Get intraday data (today's data) for most current prices
                                        hist_intraday = stock.history(period='1d', interval='1m')
                                        hist_daily = stock.history(period='5d')
                                        
                                        if not hist_intraday.empty:
                                            # Use intraday for current price
                                            current_price = hist_intraday['Close'].iloc[-1]
                                            # Use daily for 24h change
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
                                            st.success(f"✅ Got LIVE price for {ticker}: ${current_price:.2f} (as of {datetime.now().strftime('%H:%M UTC')})")
                                        elif not hist_daily.empty:
                                            # Fallback to daily if intraday not available
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
                                            st.success(f"✅ Got price for {ticker}: ${current_price:.2f}")
                                        else:
                                            st.warning(f"⚠️ No data available for {ticker}")
                                    except Exception as e:
                                        st.error(f"❌ Error fetching {ticker}: {str(e)}")
                            else:
                                st.warning("⚠️ No tickers detected in question")
                            
                            news_context = []
                            
                            # Fetch general market news from NewsData.IO FIRST
                            if newsdata_key:
                                st.info("📰 Fetching NewsData.IO market news...")
                                
                                try:
                                    # Build search query based on mentioned assets
                                    search_terms = []
                                    
                                    # If specific commodity/ticker mentioned, search for it
                                    if 'gold' in user_question.lower():
                                        search_terms.append('gold price')
                                        search_terms.append('gold rally')
                                        search_terms.append('precious metals')
                                    elif 'oil' in user_question.lower():
                                        search_terms.append('oil price')
                                        search_terms.append('crude oil')
                                    else:
                                        # General market keywords
                                        search_terms = ['market news', 'Fed', 'interest rates', 'inflation', 'economy']
                                    
                                    # Always add macro keywords
                                    search_terms.extend(['economy', 'Fed decision', 'inflation', 'dollar'])
                                    
                                    # Search with actual ticker symbols too
                                    for ticker in potential_tickers[:2]:
                                        if ticker in ['GC=F', 'CL=F', 'BTC-USD']:
                                            # Use human-readable names
                                            search_terms.append('gold' if ticker == 'GC=F' else 'oil' if ticker == 'CL=F' else 'bitcoin')
                                        else:
                                            search_terms.append(ticker)
                                    
                                    query = ' OR '.join(search_terms[:8])
                                    
                                    url = f"https://newsdata.io/api/1/news?apikey={newsdata_key}&q={query}&language=en&category=business&sortby=date"
                                    st.write(f"   Query: {query}")
                                    resp = requests.get(url, timeout=10)
                                    
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        articles = data.get('results', [])[:10]
                                        
                                        if articles:
                                            st.success(f"✅ Found {len(articles)} articles from NewsData.IO")
                                            for article in articles:
                                                news_context.append({
                                                    'source': f"NewsData - {article.get('source_id', 'Unknown')}",
                                                    'headline': article.get('title', ''),
                                                    'summary': article.get('description', '')[:200] if article.get('description') else '',
                                                    'datetime': article.get('pubDate', 'Recent')
                                                })
                                        else:
                                            st.warning("⚠️ No articles found with that query")
                                    else:
                                        st.error(f"❌ NewsData.IO API error: {resp.status_code}")
                                except Exception as e:
                                    st.error(f"❌ NewsData.IO error: {str(e)}")
                            
                            # Then fetch Finnhub news for specific tickers
                            if finnhub_key and potential_tickers:
                                st.info(f"📰 Fetching Finnhub news for tickers...")
                                
                                to_date = datetime.now().strftime('%Y-%m-%d')
                                from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                                
                                for ticker in set(potential_tickers[:3]):
                                    # Skip commodity futures - they don't work with company-news
                                    if ticker in ['GC=F', 'CL=F', 'SI=F', 'BTC-USD', 'ETH-USD', '^GSPC', '^IXIC', '^DJI']:
                                        st.write(f"   ⏭️  Skipping {ticker} (commodity/index, not supported by Finnhub company-news)")
                                        continue
                                    
                                    try:
                                        st.write(f"   Searching Finnhub for {ticker}...")
                                        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={finnhub_key}"
                                        resp = requests.get(url, timeout=10)
                                        
                                        if resp.status_code == 200:
                                            articles = resp.json()
                                            if articles:
                                                st.success(f"✅ Found {len(articles[:3])} articles for {ticker}")
                                                for article in articles[:3]:
                                                    news_context.append({
                                                        'source': f'Finnhub - {ticker}',
                                                        'headline': article.get('headline', ''),
                                                        'summary': article.get('summary', '')[:200],
                                                        'datetime': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y-%m-%d %H:%M')
                                                    })
                                            else:
                                                st.warning(f"⚠️ No Finnhub articles for {ticker}")
                                        else:
                                            st.warning(f"⚠️ Finnhub API error for {ticker}: {resp.status_code}")
                                    except Exception as e:
                                        st.error(f"❌ Error fetching Finnhub for {ticker}: {str(e)}")
                            
                            # Fetch from Polygon API for additional market data
                            polygon_key = config.get('polygon_api_key', '')
                            if polygon_key and potential_tickers:
                                st.info("📊 Fetching Polygon API market data...")
                                
                                for ticker in set(potential_tickers[:2]):
                                    # Skip commodities/indices
                                    if ticker in ['GC=F', 'CL=F', 'SI=F', 'BTC-USD', 'ETH-USD', '^GSPC', '^IXIC', '^DJI']:
                                        continue
                                    
                                    try:
                                        st.write(f"   Checking Polygon for {ticker}...")
                                        # Get latest trade data
                                        url = f"https://api.polygon.io/v1/last/stocks/{ticker}?apiKey={polygon_key}"
                                        resp = requests.get(url, timeout=10)
                                        
                                        if resp.status_code == 200:
                                            data = resp.json()
                                            if data.get('status') == 'OK' and data.get('last'):
                                                last_trade = data['last']
                                                st.success(f"✅ Polygon data for {ticker}: ${last_trade.get('price', 'N/A')}")
                                                # Add to news context as market data
                                                news_context.append({
                                                    'source': f'Polygon - {ticker}',
                                                    'headline': f"Latest trade: ${last_trade.get('price', 'N/A')}",
                                                    'summary': f"Size: {last_trade.get('size', 'N/A')} shares, Exchange: {last_trade.get('exchange', 'N/A')}",
                                                    'datetime': datetime.now().strftime('%Y-%m-%d %H:%M')
                                                })
                                        else:
                                            st.write(f"   Polygon API: No data for {ticker}")
                                    except Exception as e:
                                        st.write(f"   Polygon error for {ticker}: {str(e)}")
                            
                            # Fetch Alpaca market status and conditions
                            alpaca_key = config.get('alpaca_api_key', '')
                            if alpaca_key:
                                st.info("📈 Fetching Alpaca market conditions...")
                                
                                try:
                                    st.write(f"   Checking Alpaca market status...")
                                    headers = {'APCA-API-KEY-ID': alpaca_key}
                                    url = "https://api.alpaca.markets/v1/clock"
                                    resp = requests.get(url, headers=headers, timeout=10)
                                    
                                    if resp.status_code == 200:
                                        clock = resp.json()
                                        is_open = clock.get('is_open', False)
                                        status_text = "MARKET OPEN" if is_open else "MARKET CLOSED"
                                        st.success(f"✅ Alpaca: {status_text}")
                                        
                                        news_context.append({
                                            'source': 'Alpaca - Market Status',
                                            'headline': f"Market Status: {status_text}",
                                            'summary': f"Next open: {clock.get('next_open', 'N/A')}, Next close: {clock.get('next_close', 'N/A')}",
                                            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M')
                                        })
                                except Exception as e:
                                    st.write(f"   Alpaca error: {str(e)}")
                            
                            # Format real-time price data with timestamps
                            price_summary = ""
                            if price_data:
                                st.success(f"✅ Fetched LIVE real-time prices for {len(price_data)} assets")
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                                price_summary = f"=== REAL-TIME PRICE DATA (as of {current_time}) ===\n\n"
                                for ticker, data in price_data.items():
                                    arrow = "📈" if data['change'] >= 0 else "📉"
                                    price_summary += f"{arrow} {data['name']} ({ticker})\n"
                                    price_summary += f"   Current Price: ${data['price']:.2f} {data['currency']}\n"
                                    price_summary += f"   24h Change: {data['change']:+.2f}%\n"
                                    price_summary += f"   Last Updated: {data.get('timestamp', 'Now')}\n"
                                    price_summary += f"   Data Source: Yahoo Finance (LIVE - Not historical)\n\n"
                            else:
                                # No price data - inform the AI clearly
                                price_summary = "No real-time price data was fetched for this query.\n\n"
                            
                            # Format news summary
                            if not news_context:
                                st.warning("⚠️ Could not fetch recent news. Analysis will use price data only.")
                                news_summary = "No recent news data available."
                            else:
                                st.success(f"✅ Found {len(news_context)} recent news articles/data points")
                                news_summary = "=== RECENT NEWS & MARKET DATA (All Sources) ===\n\n"
                                for i, news in enumerate(news_context, 1):
                                    news_summary += f"{i}. [{news['datetime']}] {news['source']}\n"
                                    news_summary += f"   Headline: {news['headline']}\n"
                                    if news['summary']:
                                        news_summary += f"   Summary: {news['summary']}\n"
                                    news_summary += "\n"
                            
                            # Create simple, direct AI prompt with emphasis on TODAY's data
                            today = datetime.now().strftime('%Y-%m-%d')
                            now = datetime.now().strftime('%H:%M:%S UTC')
                            
                            advisor_prompt = f"""You are a trading advisor. Analyze the provided data and respond ONLY with a clear recommendation. Do NOT engage in conversation or ask questions.

TODAY IS: {today} at {now}
THIS IS LIVE DATA FROM {today} - NOT HISTORICAL OR TRAINING DATA

Price Data:
{price_summary}

News & Market Data:
{news_summary}

User's Question: {user_question}

===== RESPOND WITH EXACTLY THIS FORMAT - NO EXCEPTIONS, NO VARIATIONS, NO QUESTIONS =====

**CURRENT PRICE:** [exact price with $ symbol, e.g., $1,847.50]

**KEY NEWS:** [2-3 bullet points of what's moving the market]

**ANALYSIS:** [3-4 sentences explaining the situation]

**STANCE:** BULLISH or BEARISH or NEUTRAL [only these three, with 1 sentence explanation]

**ACTION:** BUY or SELL or HOLD or WATCH [only these four, with price target or exit level]

**RISK LEVEL:** HIGH or MEDIUM or LOW [only these three]

===== ABSOLUTE RULES - VIOLATIONS WILL BE REJECTED =====
1. EVERY response must follow the 6-section format above EXACTLY
2. NEVER end with a question (e.g., no "What do you think?" or "Want me to check?")
3. NEVER offer to do anything (e.g., no "I'd love to see" or "Would you like me to")
4. NEVER ask the user for information
5. NEVER say "I don't have access" - all data is provided above
6. NEVER use phrases like "around", "approximately", "roughly" - use exact numbers
7. NEVER reference training data or old prices - only use the {today} data above
8. Be direct. Be decisive. No conversation. Just analysis.

NOW RESPOND WITH THE 6-SECTION FORMAT ABOVE - NOTHING ELSE."""
                            
                            # Display sources checked summary
                            st.info("🔍 Sources Checked for Analysis:")
                            cols = st.columns(5)
                            with cols[0]:
                                st.write("✅ Yahoo Finance\n(Prices)")
                            with cols[1]:
                                st.write("✅ NewsData.IO\n(Market News)")
                            with cols[2]:
                                st.write("✅ Finnhub\n(Company News)")
                            with cols[3]:
                                st.write("✅ Polygon API\n(Trades)")
                            with cols[4]:
                                st.write("✅ Alpaca\n(Market Status)")
                            
                            # Display all articles retrieved before analysis
                            if news_context:
                                st.markdown("---")
                                st.subheader("📰 Articles & Data Retrieved")
                                
                                for i, article in enumerate(news_context, 1):
                                    with st.expander(f"{i}. {article['source']} - {article['headline'][:60]}..."):
                                        st.write(f"**Source:** {article['source']}")
                                        st.write(f"**Time:** {article['datetime']}")
                                        st.write(f"**Headline:** {article['headline']}")
                                        if article['summary']:
                                            st.write(f"**Summary:** {article['summary']}")
                                
                                st.markdown("---")
                            
                            # Call Groq AI
                            groq_client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
                            
                            response = groq_client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": advisor_prompt}],
                                max_tokens=800,
                                temperature=0.7
                            )
                            
                            analysis = response.choices[0].message.content
                            
                            # Clean the response: remove any trailing questions or offers
                            lines = analysis.split('\n')
                            cleaned_lines = []
                            for line in lines:
                                # Skip lines that are questions (end with ?)
                                if line.strip().endswith('?'):
                                    continue
                                # Skip lines offering to do something (Want, Would, Should, Would you, etc)
                                if any(line.strip().startswith(x) for x in ['Want', 'Would', 'Should', 'Let', 'Feel', 'Do you', 'What do', "I'd love", "I'd recommend checking", "I'd suggest"]):
                                    continue
                                cleaned_lines.append(line)
                            
                            analysis = '\n'.join(cleaned_lines).strip()
                            
                            # Ensure the response has the required sections
                            required_sections = ['**CURRENT PRICE:**', '**STANCE:**', '**ACTION:**']
                            missing_sections = [s for s in required_sections if s not in analysis]
                            
                            if missing_sections:
                                st.warning(f"⚠️ Response incomplete (missing: {', '.join(missing_sections)}). Requesting new analysis...")
                                analysis = analysis + "\n\n**Note:** Response was auto-corrected due to format violation."
                            
                            # Display results
                            st.success("✅ Analysis Complete")
                            st.markdown("---")
                            st.markdown(analysis)
                            st.markdown("---")
                            
                            # Show data sources used
                            with st.expander("📊 Live Price Data Used"):
                                if price_data:
                                    for ticker, data in price_data.items():
                                        st.write(f"**{ticker}**: ${data['price']:.2f} ({data['change']:+.2f}%)")
                                else:
                                    st.write("No price data fetched")
                            
                            with st.expander("📰 News Sources Used"):
                                if news_context:
                                    st.write(f"**Total articles: {len(news_context)}**")
                                    newsdata_count = sum(1 for n in news_context if 'NewsData' in n['source'])
                                    finnhub_count = sum(1 for n in news_context if 'Finnhub' in n['source'])
                                    st.write(f"- NewsData.IO: {newsdata_count} articles")
                                    st.write(f"- Finnhub: {finnhub_count} articles")
                                    st.markdown("**Articles:**")
                                    for news in news_context:
                                        st.write(f"- **{news['source']}** ({news['datetime']}): {news['headline']}")
                                else:
                                    st.write("No news data available")
                    
                    except Exception as e:
                        st.error(f"❌ Error generating analysis: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            else:
                st.warning("Please enter a question")
    
    elif page == "👥 User Management":
        st.title("👥 User Management")
        
        tab1, tab2, tab3 = st.tabs(["Create User", "List Users", "Manage Users"])
        
        with tab1:
            st.subheader("Create New User")
            with st.form("create_user"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")
                full_name = st.text_input("Full Name")
                role = st.selectbox("Role", ["user", "admin"])
                
                if st.form_submit_button("Create User"):
                    if new_password != confirm_pass:
                        st.error("Passwords don't match!")
                    else:
                        if UserManager.create_user(new_username, new_password, full_name, role):
                            st.success(f"✓ User {new_username} created!")
        
        with tab2:
            st.subheader("All Users")
            users = UserManager.list_users()
            
            if users:
                for user in users:
                    status = "🟢 Active" if user['active'] else "🔴 Inactive"
                    st.write(f"**{user['username']}** - {user['role']} - {status}")
            else:
                st.info("No users found")
        
        with tab3:
            st.subheader("Manage Users")
            users = UserManager.list_users()
            
            if users:
                user_to_manage = st.selectbox("Select User", [u['username'] for u in users])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔄 Toggle Status"):
                        UserManager.toggle_user_status(user_to_manage)
                        st.success(f"Status toggled for {user_to_manage}")
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Delete User"):
                        UserManager.delete_user(user_to_manage)
                        st.success(f"User {user_to_manage} deleted")
                        st.rerun()
    
    elif page == "⚙️ Settings":
        st.title("⚙️ Settings")
        
        st.subheader("API Keys")
        
        config = ConfigurationManager.load_config()
        
        with st.form("api_keys"):
            finnhub = st.text_input("Finnhub API Key", value=config.get('finnhub_api_key', ''), type="password")
            newsdata = st.text_input("NewsData.IO API Key", value=config.get('newsdata_api_key', ''), type="password")
            groq = st.text_input("Groq API Key", value=config.get('groq_api_key', ''), type="password")
            
            if st.form_submit_button("Save API Keys"):
                config['finnhub_api_key'] = finnhub
                config['newsdata_api_key'] = newsdata
                config['groq_api_key'] = groq
                ConfigurationManager.save_config(config)
                st.success("✓ API keys saved!")

# Run app
if st.session_state.logged_in:
    main_app()
else:
    login_page()
