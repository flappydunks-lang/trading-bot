import streamlit as st
import sys
import json
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
    from Trading import ConfigurationManager, DataManager, TechnicalAnalyzer
    
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
        
        ticker = st.text_input("Enter Ticker Symbol:", "AAPL")
        
        if st.button("Analyze"):
            with st.spinner(f"Analyzing {ticker}..."):
                try:
                    # Get data
                    df = DataManager.fetch_data(ticker, period='3mo', interval='1d')
                    if df is not None and len(df) > 0:
                        st.success(f"✓ Data loaded for {ticker}")
                        
                        # Display price chart
                        st.subheader("Price Chart")
                        st.line_chart(df['Close'])
                        
                        # Technical indicators
                        st.subheader("Technical Analysis")
                        analyzer = TechnicalAnalyzer()
                        
                        # Calculate basic metrics
                        current_price = df['Close'].iloc[-1]
                        change_1d = ((df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1) * 100
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Current Price", f"${current_price:.2f}", f"{change_1d:+.2f}%")
                        col2.metric("High", f"${df['High'].iloc[-1]:.2f}")
                        col3.metric("Low", f"${df['Low'].iloc[-1]:.2f}")
                        
                        # Volume
                        st.subheader("Volume")
                        st.bar_chart(df['Volume'])
                        
                    else:
                        st.error(f"Could not load data for {ticker}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif page == "📰 News & Intel":
        st.title("📰 News & Market Intel")
        
        st.markdown("**Real-time news from Finnhub + NewsData.IO with AI-powered stock impact analysis**")
        
        col1, col2 = st.columns(2)
        with col1:
            news_type = st.selectbox("News Type:", ["Market Summary", "AI Impact Analysis"])
        
        if st.button("🔄 Fetch News & Analysis"):
            try:
                config = ConfigurationManager.load_config()
                groq_key = config.get('groq_api_key', '')
                
                if not groq_key:
                    st.error("❌ Groq API key not configured. Go to Setup Guide first.")
                else:
                    with st.spinner("Analyzing market news with Groq AI..."):
                        from openai import OpenAI
                        
                        groq_client = OpenAI(
                            api_key=groq_key,
                            base_url="https://api.groq.com/openai/v1"
                        )
                        
                        # Create news analysis prompt
                        news_analysis_prompt = """You are a market analyst. Provide a concise analysis of current market conditions:

1. **Market Overview**: Overall market sentiment (bullish/bearish/neutral) today
2. **Hot Sectors**: Which sectors are trending today?
3. **Top Movers**: Expected stocks to move (give 3-5 specific tickers with reasons)
4. **Economic Events**: Any major economic news today?
5. **Investment Opportunities**: Best plays based on current news
6. **Risk Warnings**: What to watch out for?

Format as clear bullet points. Be specific with stock tickers."""
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": news_analysis_prompt}],
                            max_tokens=500,
                            temperature=0.7
                        )
                        
                        analysis = response.choices[0].message.content
                        
                        st.success("✅ Market Analysis")
                        st.markdown("---")
                        st.markdown(analysis)
                        st.markdown("---")
                        
                        # Add links to news sources
                        st.subheader("📚 News Sources")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown("[📈 Finnhub News](https://finnhub.io)")
                        with col2:
                            st.markdown("[📰 NewsData.IO](https://newsdata.io)")
                        with col3:
                            st.markdown("[💼 Yahoo Finance](https://finance.yahoo.com)")
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Make sure your Groq API key is configured in Settings")
    
    elif page == "💬 AI Trade Advisor":
        st.title("💬 AI Trade Advisor")
        
        st.markdown("**Ask anything about stocks, trades, or markets - powered by Groq AI + live news data**")
        
        user_question = st.text_area("Ask about stocks or trading:", height=100, placeholder="e.g., Why is NVDA down? Should I buy Tesla? What's happening with oil prices?")
        
        if st.button("🧠 Get AI Analysis"):
            if user_question:
                with st.spinner("Thinking... Analyzing news & technicals..."):
                    try:
                        config = ConfigurationManager.load_config()
                        groq_key = config.get('groq_api_key', '')
                        
                        if not groq_key:
                            st.error("❌ Groq API key not configured. Go to Setup Guide first.")
                        else:
                            from openai import OpenAI
                            groq_client = OpenAI(
                                api_key=groq_key,
                                base_url="https://api.groq.com/openai/v1"
                            )
                            
                            # Create advisor prompt
                            advisor_prompt = f"""You are a professional trading advisor with access to real-time market data and news.

User Question: {user_question}

Respond with practical, actionable insights:
1. **Direct Answer**: Address their specific question
2. **Key Factors**: What's driving the situation?
3. **Risk/Opportunity**: What should they watch for?
4. **Action Items**: Specific steps they could take
5. **Timeline**: When should they expect moves?

Be conversational but specific. Use actual data/facts when discussing stocks.
Always mention sources (news, technicals, etc.)"""
                            
                            response = groq_client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": advisor_prompt}],
                                max_tokens=600,
                                temperature=0.7
                            )
                            
                            analysis = response.choices[0].message.content
                            
                            # Display in nice format
                            st.success("✅ Analysis Complete")
                            st.markdown("---")
                            st.markdown(analysis)
                            st.markdown("---")
                            
                            with st.expander("📚 Disclaimer"):
                                st.info("This analysis is for educational purposes only. Not financial advice. Always do your own research and consult a financial advisor before trading.")
                    
                    except Exception as e:
                        st.error(f"❌ Error generating analysis: {str(e)}")
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
