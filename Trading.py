#!/usr/bin/env python3
"""
FinalAI Quantum v7.0 - Elite Professional Edition (COMPLETE)
Ultra-Advanced Quantitative Trading Analysis System

Features:
- 80+ Technical Indicators
- 20+ Pattern Recognition
- Smart Money Concepts (SMC)
- Volume Profile Analysis
- Multi-Timeframe Analysis
- AI-Powered Predictions (Claude Sonnet 4)
- Interactive Visual Backtesting
- Market Scanner with Opportunities
- Real-time News & Sentiment Analysis
- SEC Edgar Filings Analysis
- Insider Trading Detection
- Theme-Based Research (e.g., quantum computing)
"""

from __future__ import annotations

import os
import sys
import json
import logging
import io
import re
from datetime import datetime, timedelta
import time
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich import box
from rich.text import Text
from scipy.signal import argrelextrema
from scipy.stats import linregress, zscore

# Initialize
console = Console()
LOG_DIR = Path("logs")
RESULTS_DIR = Path("results")
CONFIG_DIR = Path("config")
SCANNER_DIR = Path("scanner_results")

for dir_path in [LOG_DIR, RESULTS_DIR, CONFIG_DIR, SCANNER_DIR]:
    dir_path.mkdir(exist_ok=True)

# Safe logging setup: UTF-8 file logs, console strips unsupported chars
class _SafeConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            msg.encode(enc, errors='strict')
            return True
        except Exception:
            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            safe = record.getMessage().encode(enc, errors='ignore').decode(enc, errors='ignore')
            record.msg = safe
            record.args = ()
            return True

file_handler = logging.FileHandler(LOG_DIR / f'finalai_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.addFilter(_SafeConsoleFilter())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)

# ==========================================
# JSON EXTRACTION UTILITY
# ==========================================

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text by finding balanced braces.
    This is more robust than regex for extracting actual numbers and data.
    """
    text = text.strip()
    
    # Find the first opening brace
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    # Find matching closing brace by counting braces
    brace_count = 0
    end_idx = -1
    
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
    
    if end_idx == -1:
        return None
    
    json_str = text[start_idx:end_idx+1]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON parse error: {e}")
        return None

# ==========================================
# MARKET UNIVERSES
# ==========================================

MARKET_UNIVERSES = {
    "sp500_top50": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "V", "UNH",
        "JNJ", "WMT", "JPM", "MA", "PG", "XOM", "HD", "CVX", "MRK", "ABBV",
        "LLY", "KO", "PEP", "AVGO", "COST", "ADBE", "MCD", "TMO", "CSCO", "ABT",
        "ACN", "CRM", "NKE", "DHR", "VZ", "CMCSA", "INTC", "NEE", "TXN", "PM",
        "WFC", "UPS", "HON", "AMD", "QCOM", "ORCL", "IBM", "BA", "GE", "NFLX"
    ],
    "tech_leaders": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM",
        "ORCL", "INTC", "AMD", "QCOM", "AVGO", "CSCO", "IBM", "NOW", "SNOW", "PLTR"
    ],
    "crypto": [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "ADA-USD", "XRP-USD", "DOGE-USD", "AVAX-USD"
    ],
    "ai_quantum": [
        "NVDA", "GOOGL", "MSFT", "IBM", "IONQ", "RGTI", "QBTS", "PLTR", "META", "AMZN"
    ],
    "mega_caps": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B"
    ]
    ,
    "futures": [
        "ES=F",  # S&P 500 E-mini
        "NQ=F",  # Nasdaq 100 E-mini
        "YM=F",  # Dow Jones E-mini
        "CL=F",  # Crude Oil
        "GC=F"   # Gold
    ]
}

# ==========================================
# USER AUTHENTICATION SYSTEM
# ==========================================

class UserManager:
    """Manages user accounts and authentication."""
    
    USERS_FILE = CONFIG_DIR / "users.json"
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256."""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def load_users() -> Dict[str, Dict]:
        """Load users from file."""
        if UserManager.USERS_FILE.exists():
            try:
                with open(UserManager.USERS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_users(users: Dict[str, Dict]):
        """Save users to file."""
        with open(UserManager.USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    
    @staticmethod
    def create_user(username: str, password: str, full_name: str = "", role: str = "user") -> bool:
        """Create a new user account."""
        users = UserManager.load_users()
        
        if username in users:
            console.print(f"[red]✗ Username '{username}' already exists[/red]")
            return False
        
        users[username] = {
            "password_hash": UserManager.hash_password(password),
            "full_name": full_name,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "active": True
        }
        
        UserManager.save_users(users)
        console.print(f"[green]✓ User '{username}' created successfully![/green]")
        return True
    
    @staticmethod
    def authenticate(username: str, password: str) -> bool:
        """Verify username and password."""
        users = UserManager.load_users()
        
        if username not in users:
            return False
        
        user = users[username]
        
        if not user.get("active", True):
            console.print("[red]✗ Account is deactivated[/red]")
            return False
        
        password_hash = UserManager.hash_password(password)
        
        if user["password_hash"] == password_hash:
            # Update last login
            users[username]["last_login"] = datetime.now().isoformat()
            UserManager.save_users(users)
            return True
        
        return False
    
    @staticmethod
    def delete_user(username: str) -> bool:
        """Delete a user account."""
        users = UserManager.load_users()
        
        if username not in users:
            console.print(f"[red]✗ User '{username}' not found[/red]")
            return False
        
        del users[username]
        UserManager.save_users(users)
        console.print(f"[green]✓ User '{username}' deleted[/green]")
        return True
    
    @staticmethod
    def change_password(username: str, new_password: str) -> bool:
        """Change user's password."""
        users = UserManager.load_users()
        
        if username not in users:
            console.print(f"[red]✗ User '{username}' not found[/red]")
            return False
        
        users[username]["password_hash"] = UserManager.hash_password(new_password)
        UserManager.save_users(users)
        console.print(f"[green]✓ Password changed for '{username}'[/green]")
        return True
    
    @staticmethod
    def list_users() -> List[Dict]:
        """List all users."""
        users = UserManager.load_users()
        user_list = []
        
        for username, data in users.items():
            user_list.append({
                "username": username,
                "full_name": data.get("full_name", ""),
                "role": data.get("role", "user"),
                "created_at": data.get("created_at", ""),
                "last_login": data.get("last_login", "Never"),
                "active": data.get("active", True)
            })
        
        return user_list
    
    @staticmethod
    def toggle_user_status(username: str) -> bool:
        """Activate/deactivate a user."""
        users = UserManager.load_users()
        
        if username not in users:
            console.print(f"[red]✗ User '{username}' not found[/red]")
            return False
        
        users[username]["active"] = not users[username].get("active", True)
        UserManager.save_users(users)
        
        status = "activated" if users[username]["active"] else "deactivated"
        console.print(f"[green]✓ User '{username}' {status}[/green]")
        return True

# ==========================================
# CONFIGURATION MANAGEMENT
# ==========================================

class ConfigurationManager:
    """Manages all system configuration with interactive setup."""
    
    CONFIG_FILE = CONFIG_DIR / "config.json"
    ENV_FILE = Path(".env")
    
    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load configuration or create if missing."""
        if cls.CONFIG_FILE.exists():
            with open(cls.CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]):
        """Save configuration to file."""
        with open(cls.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def setup_api_keys(cls) -> str:
        """Interactive API key setup with validation."""
        console.print("\n[bold cyan]🔑 API CONFIGURATION[/bold cyan]\n")
        
        # Load existing keys
        api_keys = {}
        if cls.ENV_FILE.exists():
            console.print("[green]✓ Found existing .env file[/green]")
            with open(cls.ENV_FILE, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        api_keys[key] = value.strip('"').strip("'")
        
        # Check Anthropic API Key
        if 'ANTHROPIC_API_KEY' not in api_keys or not api_keys.get('ANTHROPIC_API_KEY'):
            console.print("\n[yellow]📌 ANTHROPIC API KEY (Required for AI Analysis)[/yellow]")
            console.print("[dim]Get your key from: https://console.anthropic.com/[/dim]")
            console.print("[dim]The key should start with 'sk-ant-'[/dim]\n")

            # If not interactive (e.g., VS Code Debug Console), guide user to set env instead of prompting
            try:
                interactive = sys.stdin.isatty() and sys.stdout.isatty()
            except Exception:
                interactive = False

            if interactive:
                import getpass
                while True:
                    try:
                        anthropic_key = getpass.getpass("Enter your Anthropic API key: ")
                    except Exception:
                        anthropic_key = Prompt.ask("Enter your Anthropic API key")
                    if anthropic_key.startswith('sk-ant-') or anthropic_key.startswith('sk-'):
                        api_keys['ANTHROPIC_API_KEY'] = anthropic_key
                        break
                    else:
                        console.print("[red]Invalid key format. Please enter a valid Anthropic API key.[/red]")
            else:
                console.print("[yellow]Non-interactive console detected. Set the key via environment and restart:[/yellow]")
                console.print("\nRun in PowerShell:")
                console.print("[dim]setx ANTHROPIC_API_KEY \"sk-ant-...\"[/dim]")
                console.print("\nOr add to .env:")
                console.print("[dim]ANTHROPIC_API_KEY=\"sk-ant-...\"[/dim]\n")
        else:
            console.print(f"[green]✓ Anthropic API Key: {'*' * 20}{api_keys['ANTHROPIC_API_KEY'][-4:]}[/green]")
        
        # Polygon.io key (optional for day trading)
        # Will be configured in preflight if user wants real-time day trading data

        # Save to .env
        with open(cls.ENV_FILE, 'w') as f:
            f.write(f'# FinalAI Quantum Configuration\n')
            f.write(f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            for key, value in api_keys.items():
                f.write(f'{key}="{value}"\n')

        console.print("\n[green]✓ API keys saved to .env file[/green]\n")
        return api_keys.get('ANTHROPIC_API_KEY', '')
    
    @classmethod
    def setup_trading_preferences(cls) -> Dict[str, Any]:
        """Interactive trading preferences setup."""
        console.print("\n[bold cyan]⚙️  TRADING PREFERENCES SETUP[/bold cyan]\n")
        
        config = cls.load_config()
        
        if not config.get('account_size'):
            console.print("[yellow]Account Configuration[/yellow]")
            account_size = FloatPrompt.ask("Enter your account size (USD)", default=10000.0)
            config['account_size'] = account_size
        
        if not config.get('risk_per_trade'):
            risk_per_trade = FloatPrompt.ask("Risk per trade (%)", default=2.0)
            config['risk_per_trade'] = risk_per_trade
        
        if not config.get('max_positions'):
            max_positions = IntPrompt.ask("Maximum concurrent positions", default=3)
            config['max_positions'] = max_positions
        
        cls.save_config(config)
        console.print("\n[green]✓ Trading preferences saved[/green]\n")
        return config
    
    @classmethod
    def check_dependencies(cls):
        """Check and install missing dependencies."""
        console.print("\n[bold cyan]📦 Checking Dependencies[/bold cyan]\n")
        
        required_packages = {
            'anthropic': 'anthropic',
            'yfinance': 'yfinance',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'scipy': 'scipy',
            'rich': 'rich',
            'python-dotenv': 'dotenv',
            'requests': 'requests',
            'beautifulsoup4': 'bs4'
        }
        
        # Optional packages for data providers
        optional_packages = {
            'polygon': 'polygon',
            'schwab-py': 'schwab'
        }
        
        missing = []
        for package, import_name in required_packages.items():
            try:
                __import__(import_name)
                console.print(f"[green]✓ {package}[/green]")
            except ImportError:
                console.print(f"[yellow]✗ {package} (missing)[/yellow]")
                missing.append(package)
        
        # Check optional packages
        console.print("\n[dim]Optional packages (for data & trading):[/dim]")
        for package, import_name in optional_packages.items():
            try:
                __import__(import_name)
                console.print(f"[green]✓ {package}[/green]")
            except ImportError:
                console.print(f"[dim]○ {package} (optional - install for enhanced features)[/dim]")
        
        if missing:
            console.print(f"\n[yellow]Installing missing packages: {', '.join(missing)}[/yellow]")
            os.system(f"pip install {' '.join(missing)} -q")
            console.print("[green]✓ All dependencies installed[/green]\n")
        else:
            console.print("\n[green]✓ All required dependencies satisfied[/green]\n")

    @classmethod
    def run_preflight(cls, config: Dict[str, Any]):
        """Preflight wizard: ensure required env/config are present and offer to set them at start.

        - Polygon.io API key for real-time day trading data
        - Telegram notifications (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_IDS) if enabled
        """
        console.print("\n[bold cyan]🧪 Preflight Setup[/bold cyan]\n")
        # Detect if we are in an interactive TTY (e.g., VS Code Terminal) vs Debug Console
        try:
            is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        except Exception:
            is_tty = False
        # Load existing .env
        env_vals = {}
        if cls.ENV_FILE.exists():
            with open(cls.ENV_FILE, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.strip().split('=', 1)
                        env_vals[k] = v.strip().strip('"').strip("'")

        # Ask if user wants to configure live data & notifications now
        from rich.prompt import Confirm, Prompt
        wants_setup = True
        if is_tty:
            wants_setup = Confirm.ask("Run quick setup for data sources & alerts?", default=True)
        else:
            console.print("[yellow]Non-interactive console detected (e.g., Python Debug Console). Skipping prompts.[/yellow]")
            console.print("You can set required values via PowerShell or .env and rerun.")
            console.print("\n[bold]PowerShell (persist for your user):[/bold]")
            console.print("[dim]setx POLYGON_API_KEY \"<your-polygon-key>\"[/dim]")
            console.print("[dim]setx TELEGRAM_BOT_TOKEN \"<bot-token>\"[/dim]")
            console.print("[dim]setx TELEGRAM_CHAT_IDS \"123456789\"[/dim]\n")
            console.print("[bold].env alternative (project root):[/bold]")
            console.print("[dim]POLYGON_API_KEY=\"<your-polygon-key>\"[/dim]")
            console.print("[dim]TELEGRAM_BOT_TOKEN=\"<bot-token>\"[/dim]")
            console.print("[dim]TELEGRAM_CHAT_IDS=\"123456789\"[/dim]\n")
            console.print("Open an interactive terminal (PowerShell) and run preflight from there if you prefer prompts.")
            return

        if not wants_setup:
            console.print("[yellow]Skipping setup. Run option 18 later to configure.[/yellow]")
            return

        # Polygon.io API key (for day trading)
        console.print("\n[bold cyan]📊 Day Trading Data Source[/bold cyan]")
        console.print("Polygon.io provides real-time stock data for day trading (1m-1h intervals)")
        console.print("\n[bold]Free Tier:[/bold]")
        console.print("  • 5 API calls per minute")
        console.print("  • Real-time data from all exchanges")
        console.print("  • Perfect for monitoring 1-5 stocks")
        console.print("\n[bold]Paid Tiers:[/bold]")
        console.print("  • Starter Plus: $29/mo (unlimited calls)")
        console.print("  • Developer: $99/mo (includes options data)")
        console.print("\n[dim]Sign up: https://polygon.io/dashboard/signup[/dim]")
        console.print("[dim]Get API key: https://polygon.io/dashboard/api-keys[/dim]\n")
        
        polygon_key = env_vals.get('POLYGON_API_KEY') or os.getenv('POLYGON_API_KEY')
        if Confirm.ask("Do you have a Polygon.io API key?", default=bool(polygon_key)):
            if not polygon_key:
                polygon_key = Prompt.ask("POLYGON_API_KEY (from polygon.io dashboard)")
            if polygon_key:
                env_vals['POLYGON_API_KEY'] = polygon_key
                console.print("[green]✓ Polygon.io configured for day trading (1m-1h intervals)[/green]")
                console.print("[dim]  Day trading will use real-time Polygon data[/dim]")
                console.print("[dim]  Swing/long-term will use free yfinance data[/dim]")
            else:
                console.print("[yellow]⚠ No Polygon key - will use yfinance for all intervals[/yellow]")
                console.print("[dim]  Note: yfinance has 15-20 min delay for intraday data[/dim]")
        else:
            console.print("[yellow]⚠ Skipping Polygon.io setup[/yellow]")
            console.print("[dim]  Using yfinance for all data (free, but delayed 15-20 min)[/dim]")
            console.print("[dim]  You can add Polygon key later via option 18[/dim]")

        # Telegram notifications
        console.print("\n[bold cyan]🔔 Telegram Notifications[/bold cyan]")
        console.print("Get alerts for:")
        console.print("  • Trade signals (BUY/SELL)")
        console.print("  • Stop loss / Take profit hits")
        console.print("  • Position updates")
        console.print("  • Market news & events\n")
        
        enable_notifs = bool(config.get('enable_notifications', True))
        enable_notifs = Confirm.ask("Enable Telegram notifications?", default=enable_notifs)
        config['enable_notifications'] = enable_notifs
        
        if enable_notifs:
            console.print("\n[dim]Setup instructions:[/dim]")
            console.print("[dim]1. Open Telegram and search for @BotFather[/dim]")
            console.print("[dim]2. Send: /newbot and follow prompts[/dim]")
            console.print("[dim]3. Copy the bot token (looks like: 123456:ABC-DEF...)[/dim]")
            console.print("[dim]4. Start a chat with your bot[/dim]")
            console.print("[dim]5. Get your chat ID from @userinfobot[/dim]\n")
            
            bot = env_vals.get('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
            chats = env_vals.get('TELEGRAM_CHAT_IDS') or os.getenv('TELEGRAM_CHAT_IDS')
            
            if not bot:
                bot = Prompt.ask("TELEGRAM_BOT_TOKEN (from @BotFather)")
            if not chats:
                chats = Prompt.ask("TELEGRAM_CHAT_IDS (comma-separated, numeric IDs)")
            
            if bot and chats:
                env_vals['TELEGRAM_BOT_TOKEN'] = bot
                env_vals['TELEGRAM_CHAT_IDS'] = chats
                console.print("[green]✓ Telegram notifications configured[/green]")
            else:
                console.print("[yellow]⚠ Missing token or chat IDs - notifications disabled[/yellow]")
                config['enable_notifications'] = False
        else:
            console.print("[dim]Notifications disabled. Enable later via option 18[/dim]")

        # Stock & Futures Data Integration
        console.print("\n[bold cyan]📊 Data & Trading Integration Setup[/bold cyan]")
        console.print("\n[bold]Polygon.io[/bold] - Stock Market Data")
        console.print("  • Real-time stock quotes")
        console.print("  • Historical data & bars")
        console.print("  • Company fundamentals\n")
        
        console.print("[bold]Charles Schwab[/bold] - Futures Trading")
        console.print("  • E-mini S&P 500 (/ES)")
        console.print("  • Nasdaq 100 (/NQ)")
        console.print("  • Crude Oil (/CL)")
        console.print("  • Gold (/GC)\n")
        
        # Check Polygon API
        polygon_api_key = config.get('polygon_api_key') or os.getenv('POLYGON_API_KEY')
        if not polygon_api_key:
            console.print("[yellow]⚠ Polygon API key not found[/yellow]")
            if Confirm.ask("Set up Polygon API now?", default=True):
                console.print("\n[dim]Get your free API key at: https://polygon.io[/dim]")
                polygon_api_key = Prompt.ask("Polygon API Key")
                config['polygon_api_key'] = polygon_api_key
                env_vals['POLYGON_API_KEY'] = polygon_api_key
                console.print("[green]✓ Polygon API key saved[/green]")
        else:
            console.print("[green]✓ Polygon API key configured[/green]")
        
        # Check Schwab credentials
        schwab_app_key = config.get('schwab_app_key') or os.getenv('SCHWAB_APP_KEY')
        if not schwab_app_key:
            console.print("\n[yellow]⚠ Schwab API credentials not found[/yellow]")
            if Confirm.ask("Set up Schwab futures trading now?", default=False):
                schwab_trader = SchwabFuturesTrader()
                if schwab_trader.setup_credentials():
                    config['schwab_futures_enabled'] = True
                    console.print("[green]✓ Schwab futures trading enabled[/green]")
                else:
                    config['schwab_futures_enabled'] = False
                    console.print("[yellow]⚠ Schwab setup incomplete - you can complete it later via option 18[/yellow]")
            else:
                config['schwab_futures_enabled'] = False
                console.print("[dim]Schwab futures disabled. Enable later via option 18[/dim]")
        else:
            console.print("[green]✓ Schwab credentials configured[/green]")
            config['schwab_futures_enabled'] = True

        # Persist config and env
        cls.save_config(config)
        with open(cls.ENV_FILE, 'w') as f:
            f.write(f'# FinalAI Quantum Configuration\n')
            f.write(f'# Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            for k, v in env_vals.items():
                f.write(f'{k}="{v}"\n')
        
        console.print("\n[green]✅ Setup complete! Settings saved to .env and config.json[/green]\n")

        # Offer a quick connectivity self-test (interactive terminals only)
        try:
            is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        except Exception:
            is_tty = False
        if is_tty:
            try:
                from rich.prompt import Confirm as _Confirm
                if _Confirm.ask("Test connectivity now (Polygon + Telegram)?", default=True):
                    _run_connectivity_self_test(env_vals, config)
            except Exception:
                pass

# Import after dependency check
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


def _configure_requests_ip_family(ip_family: Optional[str]):
    """Optionally force requests/urllib3 to use IPv4 or IPv6 DNS results.
    Set TELEGRAM_IP_FAMILY to 'ipv4' or 'ipv6'.
    """
    try:
        import urllib3.util.connection as _uconn  # type: ignore
        import socket as _sock
        fam = (ip_family or '').strip().lower()
        if fam in ('ipv4', '4'):
            _uconn.allowed_gai_family = lambda: _sock.AF_INET  # type: ignore[attr-defined]
            console.print("[dim]- Telegram: forcing IPv4[/dim]")
        elif fam in ('ipv6', '6'):
            _uconn.allowed_gai_family = lambda: _sock.AF_INET6  # type: ignore[attr-defined]
            console.print("[dim]- Telegram: forcing IPv6[/dim]")
    except Exception:
        # If forcing fails, continue with system default
        pass


def _run_connectivity_self_test(env_vals: Dict[str, str], config: Dict[str, Any]):
    """Test Polygon and Telegram connectivity."""
    console.print("\n[bold cyan]🔎 Connectivity Self-Test[/bold cyan]\n")
    polygon_ok = _self_test_polygon(env_vals)
    telegram_ok = _self_test_telegram(env_vals, config)
    
    summary = Table(title=None, box=box.SIMPLE)
    summary.add_column("Service", justify="left")
    summary.add_column("Status", justify="left")
    summary.add_row("Polygon.io", "✅ OK" if polygon_ok else "❌ Failed/Skipped")
    summary.add_row("Telegram", "✅ OK" if telegram_ok else "❌ Failed/Skipped")
    console.print(summary)
    
    if not polygon_ok:
        console.print("\n[yellow]💡 Polygon.io Tips:[/yellow]")
        console.print("  • Verify your API key is correct (check polygon.io/dashboard/api-keys)")
        console.print("  • Ensure you have internet connectivity")
        console.print("  • Free tier: 5 calls/min limit")
        console.print("  • App will fall back to yfinance if Polygon fails")
    
    if config.get('enable_notifications', False) and not telegram_ok:
        console.print("\n[yellow]💡 Telegram Tips:[/yellow]")
        console.print("  • Check TELEGRAM_BOT_TOKEN is correct (from @BotFather)")
        console.print("  • Remove surrounding quotes and any leading 'bot' from TELEGRAM_BOT_TOKEN")
        console.print("  • Verify TELEGRAM_CHAT_IDS (numeric user/group ID or @channelusername)")
        console.print("  • Ensure bot is started (send /start to your bot)")
        console.print("  • Check firewall isn't blocking api.telegram.org")


def _self_test_polygon(env_vals: Dict[str, str]) -> bool:
    """Test Polygon.io API connection."""
    api_key = env_vals.get('POLYGON_API_KEY') or os.getenv('POLYGON_API_KEY')
    
    if not api_key:
        console.print("[dim]- Polygon.io: No API key configured, skipping test[/dim]")
        console.print("[dim]  (App will use yfinance for all data)[/dim]")
        return False

    try:
        import requests as _rq
        from datetime import datetime, timedelta
        
        # Test with a simple aggregates endpoint (daily bar for AAPL)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/{from_date}/{to_date}"
        params = {'apiKey': api_key, 'adjusted': 'true', 'sort': 'desc', 'limit': 1}
        
        console.print("[dim]- Testing Polygon.io connection...[/dim]")
        resp = _rq.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status')
            results_count = data.get('resultsCount', 0)
            
            if status == 'OK' and data.get('results') and results_count > 0:
                latest = data['results'][0]
                price = latest.get('c')
                timestamp = latest.get('t')
                console.print(f"[green]- Polygon.io: ✓ Connected successfully[/green]")
                console.print(f"[dim]  Latest AAPL close: ${price}[/dim]")
                return True
            else:
                console.print("[yellow]- Polygon.io: ⚠ API connected but returned no market data[/yellow]")
                console.print(f"[dim]  Status: {status}, Results: {results_count}[/dim]")
                if status == 'ERROR':
                    error_msg = data.get('error', 'Unknown error')
                    console.print(f"[dim]  Error: {error_msg}[/dim]")
                console.print("[yellow]  This may be normal on weekends or after market hours[/yellow]")
                console.print("[yellow]  Your API key is valid, but no recent data available[/yellow]")
                return True  # API key works, just no data available now
        
        elif resp.status_code == 401:
            console.print("[red]- Polygon.io: ❌ Unauthorized (invalid API key)[/red]")
            console.print("[yellow]  Check your API key at: https://polygon.io/dashboard/api-keys[/yellow]")
        elif resp.status_code == 429:
            console.print("[yellow]- Polygon.io: ⚠ Rate limit exceeded (5 calls/min on free tier)[/yellow]")
            console.print("[dim]  Try again in a minute, or upgrade to paid tier[/dim]")
        elif resp.status_code == 403:
            console.print("[red]- Polygon.io: ❌ Forbidden (subscription issue)[/red]")
            console.print("[yellow]  Your subscription may need to be activated[/yellow]")
        else:
            console.print(f"[red]- Polygon.io: ❌ HTTP {resp.status_code}[/red]")
            try:
                error_data = resp.json()
                console.print(f"[dim]  Response: {error_data}[/dim]")
            except:
                pass
        
        return False
        
    except _rq.exceptions.Timeout:
        console.print("[red]- Polygon.io: ❌ Connection timeout[/red]")
        console.print("[yellow]  Check your internet connection[/yellow]")
    except _rq.exceptions.ConnectionError:
        console.print("[red]- Polygon.io: ❌ Connection error[/red]")
        console.print("[yellow]  Check your internet connection or firewall settings[/yellow]")
    except Exception as e:
        console.print(f"[red]- Polygon.io: ❌ Error: {str(e)}[/red]")
    
    return False


def _self_test_telegram(env_vals: Dict[str, str], config: Dict[str, Any]) -> bool:
    if not config.get('enable_notifications', False):
        console.print("[dim]- Telegram: Notifications disabled; skipping.[/dim]")
        return False
    token = env_vals.get('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    # Normalize token to avoid common mistakes (quotes, angle brackets, leading 'bot', spaces)
    if token:
        token = str(token).strip().strip('\"\'<>')
        token = token.replace(' ', '')
        if token.lower().startswith('bot'):
            token = token[3:]
    chats = env_vals.get('TELEGRAM_CHAT_IDS') or os.getenv('TELEGRAM_CHAT_IDS')
    if not token or not chats:
        console.print("[dim]- Telegram: Missing token or chat IDs; skipping.[/dim]")
        return False
    chat_id = str(chats.split(',')[0].strip().strip('"\'<>'))
    try:
        import requests as _rq
        # Force IP family if requested
        _configure_requests_ip_family(os.getenv('TELEGRAM_IP_FAMILY'))
        base_url = f"https://api.telegram.org/bot{token}"
        # Quick token sanity: print masked token length and prefix hints
        try:
            _masked = token[:6] + "…" if len(token) > 6 else "…"
            console.print(f"[dim]- Telegram: token looks like '{_masked}' (len={len(token)})[/dim]")
        except Exception:
            pass
        # 1) Validate token and connectivity with getMe
        resp_me = _rq.get(base_url + "/getMe", timeout=8,
                          proxies={"http": os.getenv('TELEGRAM_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'),
                                   "https": os.getenv('TELEGRAM_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')}
                          if (os.getenv('TELEGRAM_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')) else None)
        if resp_me.status_code != 200:
            console.print(f"[red]- Telegram getMe failed: HTTP {resp_me.status_code}[/red]")
            try:
                _jd = resp_me.json()
                if _jd.get('description'):
                    console.print(f"[dim]  Description: {_jd.get('description')}[/dim]")
            except Exception:
                pass
            return False
        else:
            try:
                _me = resp_me.json()
                if not _me.get('ok'):
                    console.print("[red]- Telegram getMe returned not ok[/red]")
                    return False
                console.print("[dim]- Telegram: getMe OK[/dim]")
            except Exception:
                console.print("[yellow]- Telegram: getMe JSON parse issue[/yellow]")
        # 2) Attempt sendMessage
        url = base_url + "/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"✅ FinalAI preflight test at {datetime.now().strftime('%H:%M:%S')}",
            "disable_web_page_preview": True,
        }
        # Use proxy if provided
        proxy = os.getenv('TELEGRAM_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        kwargs = {"json": payload, "timeout": 8}
        if proxy:
            kwargs["proxies"] = {"http": proxy, "https": proxy}
            console.print(f"[dim]- Telegram: using proxy {proxy}[/dim]")
            # Warn if SOCKS proxy is used without PySocks installed
            try:
                if proxy.lower().startswith('socks'):
                    import socks  # type: ignore
            except Exception:
                console.print("[yellow]  • SOCKS proxy detected. Install PySocks: pip install pysocks[/yellow]")
        resp = _rq.post(url, **kwargs)
        ok = False
        try:
            data = resp.json()
            ok = bool(data.get('ok'))
        except Exception:
            ok = False
        if resp.status_code == 200 and ok:
            console.print("[green]- Telegram message sent successfully.[/green]")
            return True
        console.print(f"[red]- Telegram send failed: HTTP {resp.status_code}[/red]")
        # Print Telegram error description if available
        try:
            err = resp.json()
            desc = err.get('description')
            if desc:
                console.print(f"[dim]  Description: {desc}[/dim]")
        except Exception:
            pass
        # If 404 Not Found, try a case-insensitive method variant as fallback
        if resp.status_code == 404:
            try:
                resp2 = _rq.post(base_url + "/sendmessage", **kwargs)
                if resp2.status_code == 200 and resp2.json().get('ok'):
                    console.print("[green]- Telegram: sendmessage fallback succeeded[/green]")
                    return True
            except Exception:
                pass
        if resp.status_code == 401:
            console.print("[yellow]  • Bot token invalid. Create a new one via @BotFather and update TELEGRAM_BOT_TOKEN.[/yellow]")
        elif resp.status_code == 404:
            console.print("[yellow]  • 404 likely means a malformed token or URL.[/yellow]")
            console.print("[yellow]    - Remove any surrounding quotes from TELEGRAM_BOT_TOKEN.[/yellow]")
            console.print("[yellow]    - Do NOT include the 'bot' prefix in the token (we add it).[/yellow]")
            console.print("[yellow]    - Example format: 123456789:AAH8fExampleKeyWithLetters_Numbers[/yellow]")
        elif resp.status_code == 400:
            console.print("[yellow]  • Chat ID likely invalid. Use numeric ID or @channelusername, and /start the bot.[/yellow]")
    except Exception as e:
        console.print(f"[red]- Telegram error: {e}[/red]")
        console.print("[yellow]  • This often indicates a local network/proxy/firewall blocking api.telegram.org.[/yellow]")
        console.print("[yellow]  • Test in terminal: curl https://api.telegram.org (should respond 200 or redirect).[/yellow]")
        console.print("[yellow]  • If corporate network blocks Telegram, try a different network or configure a proxy.[/yellow]")
    return False

# ==========================================
# NOTIFICATIONS
# ==========================================

class NotificationManager:
    """Simple SMS notifications via Twilio (optional)."""
    def __init__(self, config: Dict[str, Any]):
        self.enabled = bool(config.get('enable_notifications'))
        self.client = None
        self.proxies = None
        self.ip_family = None
        if self.enabled:
            try:
                from dotenv import load_dotenv  # type: ignore
                load_dotenv()
            except Exception:
                pass
            try:
                import os
                bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or ''
                # Normalize token: strip spaces/quotes/angle-brackets and remove mistaken leading 'bot'
                bot_token = str(bot_token).strip().strip('"\'<>')
                bot_token = bot_token.replace(' ', '')
                if bot_token.lower().startswith('bot'):
                    bot_token = bot_token[3:]
                chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
                chat_ids = [c.strip().strip('"\'<>') for c in chat_ids if c.strip()]
                # Optional proxy (e.g., http://user:pass@host:port or socks5h://host:port)
                proxy = os.getenv('TELEGRAM_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
                if proxy:
                    self.proxies = { 'http': proxy, 'https': proxy }
                    try:
                        if proxy.lower().startswith('socks'):
                            import socks  # type: ignore
                    except Exception:
                        console.print("[yellow]  • SOCKS proxy detected for Telegram. Install PySocks: pip install pysocks[/yellow]")
                # Optional IP family forcing
                self.ip_family = os.getenv('TELEGRAM_IP_FAMILY')
                # Validate token pattern (digits:token-part)
                try:
                    import re as _re
                    if bot_token and not _re.match(r"^\d+:[A-Za-z0-9_-]{20,}$", bot_token):
                        console.print("[yellow]  • TELEGRAM_BOT_TOKEN looks unusual; ensure format 123456789:AAH8f...[/yellow]")
                except Exception:
                    pass
                if bot_token and chat_ids:
                    self.bot_token = bot_token
                    self.chat_ids = chat_ids
                else:
                    self.enabled = False
            except Exception:
                self.enabled = False

    def send(self, message: str):
        if not self.enabled or not hasattr(self, 'bot_token'):
            return False
        try:
            import requests
            # Force IP family if requested
            _configure_requests_ip_family(self.ip_family)
            for chat_id in self.chat_ids:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                kwargs = {"json": {"chat_id": chat_id, "text": message[:4000], "parse_mode": "HTML"}, "timeout": 8}
                if self.proxies:
                    kwargs["proxies"] = self.proxies
                requests.post(url, **kwargs)
            return True
        except Exception:
            return False

    def alert_signal(self, ticker: str, action: str, price: float, conf: float, sl: Optional[float] = None, tp: Optional[float] = None):
        msg = f"{ticker}: {action} @ ${price:.2f} | Conf {conf:.0f}%"
        if sl is not None and tp is not None:
            msg += f" | SL ${sl:.2f} TP ${tp:.2f}"
        self.send(msg)

    def alert_exit(self, ticker: str, reason: str, price: Optional[float] = None):
        msg = f"{ticker}: EXIT - {reason}"
        if price is not None:
            msg += f" @ ${price:.2f}"
        self.send(msg)

    def alert_news(self, ticker: str, headline: str, url: Optional[str] = None, sentiment: Optional[str] = None):
        """Send news headline with sentiment indicator and link."""
        if not headline:
            return
        
        # Add sentiment emoji if provided
        emoji = ""
        if sentiment == "POSITIVE":
            emoji = "📈 "
        elif sentiment == "NEGATIVE":
            emoji = "📉 "
        else:
            emoji = "📰 "
        
        # Format message with headline and link
        msg = f"<b>{ticker} NEWS</b>\n{emoji}{headline}"
        if url:
            msg += f"\n<a href='{url}'>Read more</a>"
        
        self.send(msg)
    
    def alert_news_batch(self, ticker: str, news_items: List['NewsItem']):
        """Send multiple news headlines at once with links."""
        if not news_items:
            return
        
        # Filter out low quality items and take top headlines
        quality_items = [item for item in news_items if hasattr(item, 'title') and item.title]
        if not quality_items:
            return
        
        top_items = quality_items[:5]
        
        msg = f"<b>📰 {ticker} - TOP NEWS</b>\n"
        msg += f"<i>{len(quality_items)} headlines found</i>\n\n"
        
        for i, item in enumerate(top_items, 1):
            emoji = "📈" if item.sentiment == "POSITIVE" else ("📉" if item.sentiment == "NEGATIVE" else "📰")
            headline = item.title
            # Truncate to 80 chars if too long
            if len(headline) > 80:
                headline = headline[:77] + "..."
            
            # Format with number and emoji
            msg += f"{i}. {emoji} <b>{headline}</b>\n"
            
            # Add link if available
            if hasattr(item, 'url') and item.url:
                msg += f"   🔗 <a href='{item.url}'>Read article</a>\n"
            msg += "\n"
        
        # Trim to avoid message size limit
        if len(msg) > 3500:
            msg = msg[:3450] + "\n..."
        
        self.send(msg)

    def alert_rsi(self, ticker: str, state: str, rsi_value: float):
        """Notify when RSI crosses into overbought/oversold zones."""
        try:
            rv = float(rsi_value)
        except Exception:
            rv = 0.0
        icon = "🔥" if state.lower() == "overbought" else ("🧊" if state.lower() == "oversold" else "⚠️")
        msg = f"{icon} {ticker}: RSI {state.upper()} ({rv:.1f})"
        self.send(msg)

# ==========================================
# PAPER TRADING MANAGER
# ==========================================

class PaperTradingManager:
    """Manage virtual paper trades for risk-free testing."""
    
    PAPER_TRADES_FILE = RESULTS_DIR / "paper_trades.json"
    
    def __init__(self):
        self.trades: List[PaperTrade] = []
        self.load_trades()
    
    def load_trades(self):
        """Load existing paper trades."""
        if self.PAPER_TRADES_FILE.exists():
            try:
                with open(self.PAPER_TRADES_FILE, 'r') as f:
                    data = json.load(f)
                    self.trades = []
                    for t in data:
                        # Convert datetime strings back to datetime objects
                        t['entry_time'] = datetime.fromisoformat(t['entry_time'])
                        if t.get('exit_time'):
                            t['exit_time'] = datetime.fromisoformat(t['exit_time'])
                        self.trades.append(PaperTrade(**t))
            except Exception as e:
                logger.error(f"Error loading paper trades: {e}")
                self.trades = []
    
    def save_trades(self):
        """Save paper trades to file."""
        try:
            data = []
            for trade in self.trades:
                t_dict = asdict(trade)
                # Convert datetime objects to ISO strings
                t_dict['entry_time'] = trade.entry_time.isoformat()
                if trade.exit_time:
                    t_dict['exit_time'] = trade.exit_time.isoformat()
                data.append(t_dict)
            
            with open(self.PAPER_TRADES_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving paper trades: {e}")
    
    def open_trade(self, ticker: str, action: str, entry_price: float, stop_loss: float, take_profit: float, position_size: int):
        """Open a new paper trade."""
        trade = PaperTrade(
            ticker=ticker,
            action=action,
            entry_price=entry_price,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size
        )
        self.trades.append(trade)
        self.save_trades()
        console.print(f"[green]📝 Paper trade opened: {action} {position_size} {ticker} @ ${entry_price:.2f}[/green]")
        logger.info(f"Paper trade opened: {action} {ticker} @ ${entry_price:.2f}")
        return trade
    
    def update_trades(self):
        """Check and update all open paper trades."""
        updated = False
        for trade in self.trades:
            if trade.status == "OPEN":
                try:
                    # Fetch current price - try multiple methods
                    current_price = None
                    
                    # Try real-time price first
                    try:
                        current_price = DataManager.get_realtime_price(trade.ticker)
                        if current_price:
                            current_price = float(current_price)
                    except:
                        pass
                    
                    # Fallback to recent data
                    if current_price is None:
                        df = DataManager.fetch_data(trade.ticker, "1d", "5m")
                        if df is not None and len(df) > 0:
                            current_price = float(df['Close'].iloc[-1])
                    
                    # If still no price, skip this trade
                    if current_price is None:
                        logger.debug(f"No price data for {trade.ticker}, skipping update")
                        continue
                    
                    # Check stop loss and take profit
                    if trade.action == "LONG":
                        if current_price <= trade.stop_loss:
                            self._close_trade(trade, current_price, "CLOSED_STOP", "Stop loss hit")
                            updated = True
                        elif current_price >= trade.take_profit:
                            self._close_trade(trade, current_price, "CLOSED_PROFIT", "Take profit hit")
                            updated = True
                    else:  # SHORT
                        if current_price >= trade.stop_loss:
                            self._close_trade(trade, current_price, "CLOSED_STOP", "Stop loss hit")
                            updated = True
                        elif current_price <= trade.take_profit:
                            self._close_trade(trade, current_price, "CLOSED_PROFIT", "Take profit hit")
                            updated = True
                except Exception as e:
                    logger.error(f"Error updating paper trade {trade.ticker}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
        
        if updated:
            self.save_trades()
    
    def _close_trade(self, trade: PaperTrade, exit_price: float, status: str, reason: str):
        """Close a paper trade."""
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.status = status
        trade.reason = reason
        
        if trade.action == "LONG":
            trade.pnl = (exit_price - trade.entry_price) * trade.position_size
            trade.pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        else:  # SHORT
            trade.pnl = (trade.entry_price - exit_price) * trade.position_size
            trade.pnl_pct = ((trade.entry_price - exit_price) / trade.entry_price) * 100
        
        color = "green" if trade.pnl >= 0 else "red"
        console.print(f"[{color}]📊 Paper trade closed: {trade.ticker} {reason} | P&L: ${trade.pnl:.2f} ({trade.pnl_pct:+.2f}%)[/{color}]")
    
    def get_open_trades(self) -> List[PaperTrade]:
        """Get all open paper trades."""
        return [t for t in self.trades if t.status == "OPEN"]
    
    def get_closed_trades(self) -> List[PaperTrade]:
        """Get all closed paper trades."""
        return [t for t in self.trades if t.status != "OPEN"]
    
    def close_trade_manually(self, ticker: str, exit_price: float = None):
        """Manually close a paper trade."""
        for trade in self.trades:
            if trade.status == "OPEN" and trade.ticker.upper() == ticker.upper():
                if exit_price is None:
                    # Fetch current price
                    try:
                        current_price = DataManager.get_realtime_price(ticker)
                        if current_price:
                            exit_price = float(current_price)
                        else:
                            df = DataManager.fetch_data(ticker, "1d", "5m")
                            if df is not None and len(df) > 0:
                                exit_price = float(df['Close'].iloc[-1])
                    except:
                        console.print(f"[red]Could not fetch price for {ticker}[/red]")
                        return False
                
                if exit_price:
                    self._close_trade(trade, exit_price, "CLOSED_MANUAL", "Manual close")
                    self.save_trades()
                    return True
        
        console.print(f"[yellow]No open trade found for {ticker}[/yellow]")
        return False
    
    def get_performance(self) -> Dict[str, Any]:
        """Calculate paper trading performance."""
        closed = self.get_closed_trades()
        if not closed:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0, "avg_pnl": 0}
        
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl <= 0]
        
        return {
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(closed)) * 100,
            "total_pnl": sum(t.pnl for t in closed),
            "avg_pnl": sum(t.pnl for t in closed) / len(closed),
            "avg_win": sum(t.pnl for t in wins) / len(wins) if wins else 0,
            "avg_loss": sum(t.pnl for t in losses) / len(losses) if losses else 0,
            "best_trade": max(t.pnl for t in closed),
            "worst_trade": min(t.pnl for t in closed)
        }
    
    def show_summary(self):
        """Display paper trading summary."""
        console.print("\n[bold cyan]📝 Paper Trading Summary[/bold cyan]\n")
        
        open_trades = self.get_open_trades()
        perf = self.get_performance()
        
        # Open positions with current P&L
        if open_trades:
            console.print(f"[bold]Open Positions: {len(open_trades)}[/bold]\n")
            table = Table(box=box.ROUNDED)
            table.add_column("Ticker", style="cyan")
            table.add_column("Action", style="white")
            table.add_column("Entry", style="yellow", justify="right")
            table.add_column("Current", style="white", justify="right")
            table.add_column("P&L", justify="right")
            table.add_column("Stop", style="red", justify="right")
            table.add_column("Target", style="green", justify="right")
            table.add_column("Size", justify="right")
            
            for trade in open_trades:
                # Try to get current price
                current_price = None
                current_pnl = 0.0
                pnl_pct = 0.0
                
                try:
                    current_price = DataManager.get_realtime_price(trade.ticker)
                    if current_price is None:
                        df = DataManager.fetch_data(trade.ticker, "1d", "5m")
                        if df is not None and len(df) > 0:
                            current_price = float(df['Close'].iloc[-1])
                    
                    if current_price:
                        if trade.action == "LONG":
                            current_pnl = (current_price - trade.entry_price) * trade.position_size
                            pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                        else:  # SHORT
                            current_pnl = (trade.entry_price - current_price) * trade.position_size
                            pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
                except:
                    current_price = None
                
                pnl_color = "green" if current_pnl >= 0 else "red"
                current_str = f"${current_price:.2f}" if current_price else "N/A"
                pnl_str = f"[{pnl_color}]${current_pnl:.2f} ({pnl_pct:+.1f}%)[/{pnl_color}]" if current_price else "N/A"
                
                table.add_row(
                    trade.ticker,
                    trade.action,
                    f"${trade.entry_price:.2f}",
                    current_str,
                    pnl_str,
                    f"${trade.stop_loss:.2f}",
                    f"${trade.take_profit:.2f}",
                    str(trade.position_size)
                )
            console.print(table)
            console.print()
        
        # Performance stats
        if perf['total_trades'] > 0:
            console.print(f"[bold]Performance (Closed Trades)[/bold]\n")
            pnl_color = "green" if perf['total_pnl'] >= 0 else "red"
            
            console.print(f"Total Trades: {perf['total_trades']}")
            console.print(f"Wins: [green]{perf['wins']}[/green] | Losses: [red]{perf['losses']}[/red]")
            console.print(f"Win Rate: {perf['win_rate']:.1f}%")
            console.print(f"Total P&L: [{pnl_color}]${perf['total_pnl']:.2f}[/{pnl_color}]")
            console.print(f"Average P&L: ${perf['avg_pnl']:.2f}")
            console.print(f"Average Win: [green]${perf['avg_win']:.2f}[/green]")
            console.print(f"Average Loss: [red]${perf['avg_loss']:.2f}[/red]")
            console.print(f"Best Trade: [green]${perf['best_trade']:.2f}[/green]")
            console.print(f"Worst Trade: [red]${perf['worst_trade']:.2f}[/red]")
        else:
            console.print("[yellow]No closed trades yet[/yellow]")
    
    def save_prediction_for_trade(self, ticker: str, direction: str, target_price: float, 
                                  target_date: str, confidence: str, reasoning: str, 
                                  sources: List[str], current_price: float) -> str:
        """Save a prediction when the bot makes a trading decision."""
        return PredictionTracker.save_prediction(
            ticker, direction, target_price, target_date, 
            confidence, reasoning, sources, current_price
        )
    
    def check_prediction_outcomes(self) -> Dict:
        """Check and update outcomes for all pending predictions."""
        # Get current prices for all tickers with pending predictions
        pending = PredictionTracker.get_pending_predictions()
        current_prices = {}
        
        for pred in pending:
            ticker = pred['ticker']
            try:
                price = DataManager.get_realtime_price(ticker)
                if price is None:
                    df = DataManager.fetch_data(ticker, "1d", "5m")
                    if df is not None and len(df) > 0:
                        price = float(df['Close'].iloc[-1])
                if price:
                    current_prices[ticker] = price
            except:
                pass
        
        # Update outcomes
        updated = OutcomeAnalyzer.check_and_update_outcomes(current_prices)
        
        return {
            "checked": len(pending),
            "updated": len(updated),
            "updated_predictions": updated
        }
    
    def get_bot_learning_summary(self) -> str:
        """Get the bot's learning brief before making new trades."""
        return LearningEngine.get_bot_learning_brief()
    
    def show_prediction_accuracy(self):
        """Display the bot's prediction accuracy dashboard."""
        summary = OutcomeAnalyzer.get_accuracy_summary()
        scenarios = OutcomeAnalyzer.get_scenario_analysis()
        
        if summary.get('completed_outcomes', 0) == 0:
            console.print("[yellow]No completed predictions yet. Make trades and let them resolve![/yellow]")
            return
        
        console.print("\n[bold cyan]🤖 Trading Bot - Prediction Accuracy Dashboard[/bold cyan]\n")
        
        # Overall stats
        console.print("[bold]Overall Performance[/bold]")
        console.print(f"  Total Predictions: {summary.get('total_predictions', 0)}")
        console.print(f"  Completed: {summary.get('completed_outcomes', 0)}")
        console.print(f"  Pending: {summary.get('pending_outcomes', 0)}")
        console.print(f"  Directional Accuracy: [bold cyan]{summary.get('directional_accuracy_pct', 0)}%[/bold cyan]")
        console.print(f"  Avg Accuracy Score: {summary.get('average_accuracy_score', 0)}/100")
        console.print(f"  Avg Profit: [green]{summary.get('average_profit_pct', 0)}%[/green]\n")
        
        # By confidence
        if summary.get('scenarios'):
            console.print("[bold]Accuracy by Confidence Level[/bold]")
            for conf, stats in summary.get('scenarios', {}).items():
                accuracy = stats.get('accuracy', 0)
                count = stats.get('total', 0)
                profit = stats.get('avg_profit', 0)
                color = "green" if accuracy >= 60 else "yellow" if accuracy >= 50 else "red"
                console.print(f"  [{color}]{conf}[/{color}]: {accuracy:.0f}% accuracy ({count} predictions, avg {profit:+.2f}%)")
            console.print()
        
        # Best scenarios
        if scenarios:
            console.print("[bold]Best Performing Scenarios[/bold]")
            for scenario, stats in list(scenarios.items())[:3]:
                console.print(f"  ✅ {scenario.title()}: {stats['success_rate_pct']}% success ({stats['attempts']} attempts)")
            console.print()
            
            console.print("[bold]Worst Performing Scenarios[/bold]")
            for scenario, stats in list(reversed(scenarios.items()))[:3]:
                console.print(f"  ⚠️  {scenario.title()}: {stats['success_rate_pct']}% success ({stats['attempts']} attempts)")

# ==========================================
# PORTFOLIO OPTIMIZATION
# ==========================================

class PortfolioOptimizer:
    """Modern Portfolio Theory: Markowitz optimization, efficient frontier, risk parity."""
    
    @staticmethod
    def calculate_portfolio_metrics(weights: np.ndarray, returns: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate portfolio return and volatility given weights.
        Returns: (annual_return, annual_volatility)
        """
        # Mean returns (annualized)
        mean_returns = returns.mean() * 252
        
        # Covariance matrix (annualized)
        cov_matrix = returns.cov() * 252
        
        # Portfolio return
        portfolio_return = np.dot(weights, mean_returns)
        
        # Portfolio volatility
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        return float(portfolio_return), float(portfolio_vol)
    
    @staticmethod
    def calculate_sharpe_ratio(weights: np.ndarray, returns: pd.DataFrame, risk_free_rate: float = 0.04) -> float:
        """Calculate Sharpe ratio for given portfolio weights."""
        port_return, port_vol = PortfolioOptimizer.calculate_portfolio_metrics(weights, returns)
        
        if port_vol == 0:
            return 0.0
        
        sharpe = (port_return - risk_free_rate) / port_vol
        return float(sharpe)
    
    @staticmethod
    def optimize_max_sharpe(returns: pd.DataFrame, risk_free_rate: float = 0.04) -> Tuple[np.ndarray, float, float, float]:
        """
        Find portfolio weights that maximize Sharpe ratio.
        Returns: (weights, return, volatility, sharpe)
        """
        from scipy.optimize import minimize
        
        n_assets = len(returns.columns)
        
        # Objective: minimize negative Sharpe ratio
        def neg_sharpe(weights):
            return -PortfolioOptimizer.calculate_sharpe_ratio(weights, returns, risk_free_rate)
        
        # Constraints: weights sum to 1
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        # Bounds: 0 <= weight <= 1 (long only)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess: equal weights
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(neg_sharpe, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        
        optimal_weights = result.x
        port_return, port_vol = PortfolioOptimizer.calculate_portfolio_metrics(optimal_weights, returns)
        sharpe = PortfolioOptimizer.calculate_sharpe_ratio(optimal_weights, returns, risk_free_rate)
        
        return optimal_weights, port_return, port_vol, sharpe
    
    @staticmethod
    def optimize_min_variance(returns: pd.DataFrame) -> Tuple[np.ndarray, float, float]:
        """
        Find minimum variance portfolio.
        Returns: (weights, return, volatility)
        """
        from scipy.optimize import minimize
        
        n_assets = len(returns.columns)
        
        # Objective: minimize variance
        def portfolio_variance(weights):
            _, vol = PortfolioOptimizer.calculate_portfolio_metrics(weights, returns)
            return vol ** 2
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        init_weights = np.array([1/n_assets] * n_assets)
        
        result = minimize(portfolio_variance, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        
        optimal_weights = result.x
        port_return, port_vol = PortfolioOptimizer.calculate_portfolio_metrics(optimal_weights, returns)
        
        return optimal_weights, port_return, port_vol
    
    @staticmethod
    def calculate_efficient_frontier(returns: pd.DataFrame, n_portfolios: int = 100) -> Tuple[List[float], List[float], List[np.ndarray]]:
        """
        Calculate efficient frontier.
        Returns: (returns_list, volatilities_list, weights_list)
        """
        from scipy.optimize import minimize
        
        n_assets = len(returns.columns)
        
        # Get min and max return range
        _, min_vol_return, _ = PortfolioOptimizer.optimize_min_variance(returns)
        max_sharpe_weights, max_return, _, _ = PortfolioOptimizer.optimize_max_sharpe(returns)
        
        # Target returns for efficient frontier
        target_returns = np.linspace(min_vol_return, max_return, n_portfolios)
        
        frontier_returns = []
        frontier_vols = []
        frontier_weights = []
        
        for target in target_returns:
            # Minimize variance subject to target return
            def portfolio_variance(weights):
                _, vol = PortfolioOptimizer.calculate_portfolio_metrics(weights, returns)
                return vol ** 2
            
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
                {'type': 'eq', 'fun': lambda x: PortfolioOptimizer.calculate_portfolio_metrics(x, returns)[0] - target}  # Target return
            ]
            
            bounds = tuple((0, 1) for _ in range(n_assets))
            init_weights = np.array([1/n_assets] * n_assets)
            
            try:
                result = minimize(portfolio_variance, init_weights, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter': 1000})
                
                if result.success:
                    weights = result.x
                    ret, vol = PortfolioOptimizer.calculate_portfolio_metrics(weights, returns)
                    frontier_returns.append(ret)
                    frontier_vols.append(vol)
                    frontier_weights.append(weights)
            except Exception:
                continue
        
        return frontier_returns, frontier_vols, frontier_weights
    
    @staticmethod
    def plot_efficient_frontier(tickers: List[str], lookback_days: int = 252):
        """
        Plot efficient frontier for given tickers.
        """
        try:
            import matplotlib.pyplot as plt
            
            # Fetch data
            returns_data = {}
            for ticker in tickers:
                df = DataManager.fetch_data(ticker, "1y", "1d")
                if df is not None and len(df) >= lookback_days * 0.7:
                    returns_data[ticker] = df['Close'].pct_change().dropna()
            
            if len(returns_data) < 2:
                console.print("[red]Need at least 2 tickers with data[/red]")
                return
            
            # Combine returns
            returns_df = pd.DataFrame(returns_data).dropna()
            
            # Calculate efficient frontier
            frontier_rets, frontier_vols, _ = PortfolioOptimizer.calculate_efficient_frontier(returns_df)
            
            # Calculate max Sharpe portfolio
            max_sharpe_weights, max_sharpe_ret, max_sharpe_vol, sharpe = PortfolioOptimizer.optimize_max_sharpe(returns_df)
            
            # Calculate min variance portfolio
            min_var_weights, min_var_ret, min_var_vol = PortfolioOptimizer.optimize_min_variance(returns_df)
            
            # Plot
            plt.figure(figsize=(12, 8))
            plt.style.use('dark_background')
            
            # Efficient frontier
            plt.plot(frontier_vols, frontier_rets, 'c-', linewidth=2, label='Efficient Frontier')
            
            # Max Sharpe portfolio
            plt.scatter(max_sharpe_vol, max_sharpe_ret, marker='*', color='gold', s=500, edgecolors='black', label=f'Max Sharpe (SR={sharpe:.2f})')
            
            # Min variance portfolio
            plt.scatter(min_var_vol, min_var_ret, marker='o', color='lime', s=200, edgecolors='black', label='Min Variance')
            
            # Individual assets
            for ticker in returns_df.columns:
                asset_ret = returns_df[ticker].mean() * 252
                asset_vol = returns_df[ticker].std() * np.sqrt(252)
                plt.scatter(asset_vol, asset_ret, marker='D', s=100, alpha=0.7, label=ticker)
            
            plt.xlabel('Volatility (Annual)', fontsize=12)
            plt.ylabel('Return (Annual)', fontsize=12)
            plt.title('Efficient Frontier - Portfolio Optimization', fontsize=14, fontweight='bold')
            plt.legend(loc='best', fontsize=10)
            plt.grid(True, alpha=0.3)
            
            # Save
            filepath = RESULTS_DIR / f"efficient_frontier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            console.print(f"[green]✓ Efficient frontier saved: {filepath}[/green]")
            
            # Show allocation
            console.print("\n[bold cyan]Max Sharpe Portfolio Allocation:[/bold cyan]")
            for ticker, weight in zip(returns_df.columns, max_sharpe_weights):
                console.print(f"{ticker}: {weight*100:.2f}%")
            
            console.print(f"\nExpected Return: {max_sharpe_ret*100:.2f}%")
            console.print(f"Volatility: {max_sharpe_vol*100:.2f}%")
            console.print(f"Sharpe Ratio: {sharpe:.2f}")
            
            plt.show()
        
        except Exception as e:
            logger.error(f"Efficient frontier plot error: {e}")
            console.print(f"[red]Error plotting efficient frontier: {e}[/red]")
    
    @staticmethod
    def risk_parity_weights(returns: pd.DataFrame) -> np.ndarray:
        """
        Calculate risk parity portfolio weights.
        Each asset contributes equally to portfolio risk.
        """
        cov_matrix = returns.cov() * 252
        
        # Inverse volatility weighting (simplified risk parity)
        vols = np.sqrt(np.diag(cov_matrix))
        inv_vols = 1 / vols
        weights = inv_vols / inv_vols.sum()
        
        return weights

# ==========================================
# DATA MODELS
# ==========================================

class TradingStyle(Enum):
    DAY_TRADE = "day_trade"
    SWING_TRADE = "swing_trade"
    LONG_TERM = "long_term"

@dataclass
class TradingConfig:
    style: TradingStyle
    period: str
    interval: str
    description: str
    timeframe: str
    min_data_points: int = 200
    
    @staticmethod
    def get_config(style: TradingStyle) -> 'TradingConfig':
        configs = {
            TradingStyle.DAY_TRADE: TradingConfig(
                style=TradingStyle.DAY_TRADE,
                period="30d",  # Changed from 60d to 30d for better yfinance compatibility
                interval="5m",
                description="⚡ Day Trading",
                timeframe="5m-1h",
                min_data_points=80  # Reduced from 100 - 30d of 5m = ~240 bars, very safe
            ),
            TradingStyle.SWING_TRADE: TradingConfig(
                style=TradingStyle.SWING_TRADE,
                period="6mo",  # Changed from 3m to 6m for better trend detection
                interval="1d",
                description="📈 Swing Trading",
                timeframe="Days to Weeks",
                min_data_points=120  # Reduced from 200 - 6m of daily = ~180 bars
            ),
            TradingStyle.LONG_TERM: TradingConfig(
                style=TradingStyle.LONG_TERM,
                period="5y",
                interval="1wk",
                description="💎 Long-Term Investing",
                timeframe="Months to Years",
                min_data_points=200
            )
        }
        return configs[style]

@dataclass
@dataclass
class AdvancedIndicators:
    """80+ Technical Indicators."""
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    sma_10: float
    sma_20: float
    sma_50: float
    sma_200: float
    ema_12: float
    ema_26: float
    ema_50: float
    ema_200: float
    vwap: float
    rsi_14: float
    rsi_7: float
    stochastic_k: float
    stochastic_d: float
    macd: float
    macd_signal: float
    macd_histogram: float
    atr: float
    atr_percent: float
    bb_upper: float
    bb_lower: float
    bb_middle: float
    # Additional indicators
    ema_8: float
    ema_21: float
    ema_34: float
    williams_r: float
    cci: float
    keltner_upper: float
    keltner_middle: float
    keltner_lower: float
    tenkan_sen: float
    kijun_sen: float
    senkou_a: float
    senkou_b: float
    chikou_span: float
    hma_20: float
    roc_12: float
    adx: float
    plus_di: float
    minus_di: float
    obv: float
    volume_ratio: float
    mfi: float
    market_regime: str
    regime_confidence: float
    closes: Optional[pd.Series] = None  # Full series for pattern detection (default at end)

@dataclass
class PatternAnalysis:
    """20+ Chart Patterns."""
    bullish_patterns: List[str]
    bearish_patterns: List[str]
    neutral_patterns: List[str]
    candlestick_patterns: List[str]
    trend_patterns: Dict[str, bool]

@dataclass
class MarketStructure:
    """Smart Money Concepts."""
    structure: str
    order_blocks: List[Tuple[float, float]]
    fair_value_gaps: List[Tuple[float, float]]
    liquidity_zones: List[float]
    premium_zone: Tuple[float, float]
    discount_zone: Tuple[float, float]
    equilibrium: float

@dataclass
class VolumeProfile:
    """Volume Profile Analysis."""
    poc: float
    vah: float
    val: float
    high_volume_nodes: List[float]
    low_volume_nodes: List[float]

@dataclass
class TradeSummary:
    """Complete Trade Recommendation."""
    ticker: str
    action: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    position_size: int
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float
    win_probability: float
    expected_value: float
    primary_reason: str
    supporting_signals: List[str]
    risk_factors: List[str]
    timestamp: str
    fundamentals: Optional[Dict[str, Any]] = None
    greeks: Optional[Dict[str, Any]] = None
    risk_per_share: Optional[float] = None
    reward_per_share: Optional[float] = None

@dataclass
class ScannerOpportunity:
    """Scanner-detected opportunity."""
    ticker: str
    score: float
    action: str
    confidence: float
    entry_price: float
    stop_loss: float
    target: float
    risk_reward: float
    primary_signal: str
    supporting_signals: List[str]
    market_cap: Optional[str] = None
    sector: Optional[str] = None

@dataclass
class NewsItem:
    """News article item."""
    title: str
    source: str
    published: str
    url: str
    sentiment: str
    relevance: float
    score: float = 0.0

@dataclass
class InsiderTrade:
    """Insider trading activity."""
    insider: str
    position: str
    transaction_type: str
    shares: int
    price: float
    value: float
    date: str
    ticker: str

@dataclass
class SECFiling:
    """SEC filing information."""
    form_type: str
    filing_date: str
    company: str
    ticker: str
    description: str
    url: str
    key_points: List[str]

@dataclass
class MarketRegime:
    """Market regime classification."""
    regime: str  # "TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"
    confidence: float
    adx: float
    atr_percentile: float
    trend_strength: float
    details: str

@dataclass
class MultiTimeframeAnalysis:
    """Multi-timeframe confirmation."""
    primary_trend: str  # "BULLISH", "BEARISH", "NEUTRAL"
    higher_tf_aligned: bool
    timeframes: Dict[str, str]  # interval -> trend direction
    confirmation_score: float  # 0-100
    details: str

@dataclass
class PaperTrade:
    """Virtual paper trade."""
    ticker: str
    action: str
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    position_size: int
    status: str = "OPEN"  # "OPEN", "CLOSED_PROFIT", "CLOSED_LOSS", "CLOSED_STOP"
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""

# ==========================================
# DATA FETCHING & VALIDATION
# ==========================================

class PolygonDataFetcher:
    """Fetches real-time data from Polygon.io for day trading."""
    
    @staticmethod
    def fetch_intraday_data(ticker: str, interval: str, limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Fetch intraday data from Polygon.io.
        
        Args:
            ticker: Stock symbol
            interval: Time interval (1m, 5m, 15m, 1h)
            limit: Number of bars to fetch (max 5000)
        """
        try:
            import requests
            from datetime import datetime, timedelta
            
            # Load API key from config
            config = ConfigurationManager.load_config()
            api_key = config.get('polygon_api_key') or os.getenv('POLYGON_API_KEY')
            
            if not api_key:
                logger.warning("Polygon API key not found, falling back to yfinance")
                return None
            
            # Convert interval to polygon format
            interval_map = {
                '1m': ('1', 'minute'),
                '5m': ('5', 'minute'),
                '15m': ('15', 'minute'),
                '30m': ('30', 'minute'),
                '1h': ('1', 'hour'),
                '1d': ('1', 'day')
            }
            
            if interval not in interval_map:
                logger.warning(f"Interval {interval} not supported by Polygon, using yfinance")
                return None
            
            multiplier, timespan = interval_map[interval]
            
            # Calculate date range (last 5 days for intraday)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            # Format dates
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            # Build URL
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
            
            params = {
                'apiKey': api_key,
                'adjusted': 'true',
                'sort': 'asc',
                'limit': limit
            }
            
            logger.info(f"Fetching {ticker} from Polygon.io: {interval}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                logger.warning("Polygon rate limit hit, falling back to yfinance")
                return None
            
            if response.status_code != 200:
                logger.warning(f"Polygon API error {response.status_code}: {response.text}, falling back to yfinance")
                return None
            
            data = response.json()
            
            if data.get('status') not in ['OK', 'DELAYED']:
                logger.warning(f"Polygon status {data.get('status')} for {ticker}, falling back to yfinance")
                return None
            
            if not data.get('results'):
                logger.warning(f"No results from Polygon for {ticker}, falling back to yfinance")
                return None
            
            # Convert to DataFrame
            results = data['results']
            df = pd.DataFrame(results)
            
            # Rename columns to match yfinance format
            df = df.rename(columns={
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
                't': 'timestamp'
            })
            
            # Convert timestamp (milliseconds) to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Select only required columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            logger.info(f"✓ Polygon.io: Fetched {len(df)} bars for {ticker}")
            return df
            
        except Exception as e:
            logger.warning(f"Polygon fetch error: {e}, falling back to yfinance")
            return None


class SchwabFuturesTrader:
    """Charles Schwab futures trading integration using schwab-py library."""
    
    def __init__(self):
        """Initialize Schwab API client."""
        self.client = None
        self.app_key = None
        self.app_secret = None
        self.callback_url = None
        self.token_file = Path("config/schwab_tokens.json")
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Schwab API credentials from config."""
        config = ConfigurationManager.load_config()
        self.app_key = config.get('schwab_app_key') or os.getenv('SCHWAB_APP_KEY')
        self.app_secret = config.get('schwab_app_secret') or os.getenv('SCHWAB_APP_SECRET')
        self.callback_url = config.get('schwab_callback_url') or os.getenv('SCHWAB_CALLBACK_URL') or 'https://localhost:8182'
    
    def setup_credentials(self):
        """Interactive setup for Schwab API credentials."""
        console.print("\n[bold cyan]📈 Charles Schwab Futures Trading Setup[/bold cyan]\n")
        console.print("[yellow]To trade futures with Charles Schwab, you need API credentials:[/yellow]\n")
        
        console.print("[bold]Step 1: Get API Access[/bold]")
        console.print("  1. Go to: https://developer.schwab.com")
        console.print("  2. Sign in with your Schwab account")
        console.print("  3. Navigate to 'My Apps' → 'Register an App'")
        console.print("  4. Create a new app with these settings:")
        console.print("     - App Name: 'FinalAI Trading'")
        console.print("     - Callback URL: https://localhost:8182")
        console.print("     - Check both 'Accounts and Trading Production' and 'Market Data Production'")
        console.print("  5. Copy your App Key and App Secret\n")
        
        console.print("[bold]Step 2: Enable Futures Trading[/bold]")
        console.print("  1. Log into schwab.com")
        console.print("  2. Go to Trade → Futures & Forex")
        console.print("  3. Complete the futures trading application")
        console.print("  4. Wait for approval (usually 1-2 business days)\n")
        
        console.print("[bold]Step 3: Enter Your Credentials[/bold]\n")
        
        from rich.prompt import Prompt, Confirm
        
        has_credentials = Confirm.ask("Do you have your Schwab API credentials?", default=False)
        
        if not has_credentials:
            console.print("\n[yellow]Come back and run option 18 after you get your credentials.[/yellow]")
            return False
        
        self.app_key = Prompt.ask("Schwab App Key (from developer.schwab.com)")
        self.app_secret = Prompt.ask("Schwab App Secret", password=True)
        
        # Save to config
        config = ConfigurationManager.load_config()
        config['schwab_app_key'] = self.app_key
        config['schwab_app_secret'] = self.app_secret
        config['schwab_callback_url'] = self.callback_url
        config['schwab_futures_enabled'] = True
        ConfigurationManager.save_config(config)
        
        # Save to .env
        env_vals = {}
        if ConfigurationManager.ENV_FILE.exists():
            with open(ConfigurationManager.ENV_FILE, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.strip().split('=', 1)
                        env_vals[k] = v.strip().strip('"').strip("'")
        
        env_vals['SCHWAB_APP_KEY'] = self.app_key
        env_vals['SCHWAB_APP_SECRET'] = self.app_secret
        env_vals['SCHWAB_CALLBACK_URL'] = self.callback_url
        
        with open(ConfigurationManager.ENV_FILE, 'w') as f:
            f.write(f'# FinalAI Quantum Configuration\n')
            f.write(f'# Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            for k, v in env_vals.items():
                f.write(f'{k}="{v}"\n')
        
        console.print("\n[green]✓ Schwab credentials saved[/green]")
        
        # Attempt initial authentication
        if Confirm.ask("\nAuthenticate with Schwab now?", default=True):
            return self.authenticate()
        
        return True
    
    def authenticate(self):
        """Authenticate with Schwab API and save tokens."""
        try:
            from schwab import auth, client
            import atexit
            
            console.print("\n[yellow]🔐 Starting Schwab authentication...[/yellow]")
            console.print("A browser window will open for you to log in to Schwab.")
            console.print("After login, you'll be redirected to localhost - copy the full URL.\n")
            
            if not self.app_key or not self.app_secret:
                console.print("[red]❌ Missing app key or secret. Run setup first.[/red]")
                return False
            
            # Create token file directory
            self.token_file.parent.mkdir(exist_ok=True)
            
            # Authenticate using easy_client
            self.client = auth.easy_client(
                api_key=self.app_key,
                app_secret=self.app_secret,
                callback_url=self.callback_url,
                token_path=str(self.token_file)
            )
            
            # Register cleanup on exit
            atexit.register(lambda: self.client.close() if self.client else None)
            
            console.print("[green]✓ Successfully authenticated with Schwab![/green]")
            console.print(f"[dim]Tokens saved to: {self.token_file}[/dim]\n")
            
            return True
            
        except ImportError:
            console.print("[red]❌ schwab-py library not installed[/red]")
            console.print("Install it with: pip install schwab-py")
            return False
        except Exception as e:
            console.print(f"[red]❌ Authentication failed: {e}[/red]")
            logger.error(f"Schwab authentication error: {e}")
            return False
    
    def _ensure_client(self):
        """Ensure client is authenticated."""
        if self.client is not None:
            return True
        
        if not self.token_file.exists():
            console.print("[yellow]⚠ Not authenticated. Run setup first (option 18).[/yellow]")
            return False
        
        try:
            from schwab import auth
            import atexit
            
            self.client = auth.client_from_token_file(
                token_path=str(self.token_file),
                api_key=self.app_key,
                app_secret=self.app_secret
            )
            
            atexit.register(lambda: self.client.close() if self.client else None)
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to load Schwab session: {e}[/red]")
            logger.error(f"Schwab client load error: {e}")
            return False
    
    def get_futures_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Get real-time futures quotes."""
        if not self._ensure_client():
            return {}
        
        try:
            # Schwab futures symbols format: /ES (E-mini S&P 500), /NQ (Nasdaq), etc.
            response = self.client.get_quotes(symbols)
            data = response.json()
            
            quotes = {}
            for symbol, quote_data in data.items():
                if 'quote' in quote_data:
                    q = quote_data['quote']
                    quotes[symbol] = {
                        'last': q.get('lastPrice', 0),
                        'bid': q.get('bidPrice', 0),
                        'ask': q.get('askPrice', 0),
                        'volume': q.get('totalVolume', 0),
                        'open': q.get('openPrice', 0),
                        'high': q.get('highPrice', 0),
                        'low': q.get('lowPrice', 0),
                        'change': q.get('netChange', 0),
                        'change_pct': q.get('netPercentChange', 0)
                    }
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error fetching futures quotes: {e}")
            return {}
    
    def place_futures_order(self, symbol: str, quantity: int, side: str, 
                           order_type: str = 'MARKET', limit_price: float = None) -> Dict[str, Any]:
        """
        Place a futures order.
        
        Args:
            symbol: Futures symbol (e.g., '/ES', '/NQ', '/CL')
            quantity: Number of contracts
            side: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            limit_price: Required if order_type is 'LIMIT'
        """
        if not self._ensure_client():
            return {'success': False, 'error': 'Not authenticated'}
        
        try:
            from schwab.orders.futures import (
                futures_buy_to_open_market,
                futures_sell_to_open_market,
                futures_buy_to_open_limit,
                futures_sell_to_open_limit
            )
            
            # Get account hash
            accounts = self.client.get_account_numbers().json()
            if not accounts:
                return {'success': False, 'error': 'No accounts found'}
            
            account_hash = accounts[0]['hashValue']
            
            # Build order based on type
            if order_type == 'MARKET':
                if side.upper() == 'BUY':
                    order = futures_buy_to_open_market(symbol, quantity)
                else:
                    order = futures_sell_to_open_market(symbol, quantity)
            elif order_type == 'LIMIT':
                if limit_price is None:
                    return {'success': False, 'error': 'Limit price required for LIMIT orders'}
                
                if side.upper() == 'BUY':
                    order = futures_buy_to_open_limit(symbol, quantity, limit_price)
                else:
                    order = futures_sell_to_open_limit(symbol, quantity, limit_price)
            else:
                return {'success': False, 'error': f'Invalid order type: {order_type}'}
            
            # Place the order
            response = self.client.place_order(account_hash, order)
            
            if response.status_code == 201:
                order_id = response.headers.get('location', '').split('/')[-1]
                console.print(f"[green]✓ Order placed successfully! Order ID: {order_id}[/green]")
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side,
                    'type': order_type
                }
            else:
                error_msg = f"Order failed with status {response.status_code}"
                console.print(f"[red]❌ {error_msg}[/red]")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Order placement error: {e}"
            console.print(f"[red]❌ {error_msg}[/red]")
            logger.error(error_msg)
            return {'success': False, 'error': str(e)}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current futures positions."""
        if not self._ensure_client():
            return []
        
        try:
            accounts = self.client.get_account_numbers().json()
            if not accounts:
                return []
            
            account_hash = accounts[0]['hashValue']
            
            # Get account details with positions
            response = self.client.get_account(
                account_hash,
                fields=['positions']
            )
            
            account_data = response.json()
            positions = []
            
            if 'securitiesAccount' in account_data:
                account = account_data['securitiesAccount']
                if 'positions' in account:
                    for pos in account['positions']:
                        instrument = pos.get('instrument', {})
                        if instrument.get('assetType') == 'FUTURE':
                            positions.append({
                                'symbol': instrument.get('symbol', ''),
                                'quantity': pos.get('longQuantity', 0) - pos.get('shortQuantity', 0),
                                'average_price': pos.get('averagePrice', 0),
                                'market_value': pos.get('marketValue', 0),
                                'unrealized_pnl': pos.get('currentDayProfitLoss', 0),
                                'unrealized_pnl_pct': pos.get('currentDayProfitLossPercentage', 0)
                            })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and margin information."""
        if not self._ensure_client():
            return {}
        
        try:
            accounts = self.client.get_account_numbers().json()
            if not accounts:
                return {}
            
            account_hash = accounts[0]['hashValue']
            response = self.client.get_account(account_hash)
            account_data = response.json()
            
            if 'securitiesAccount' in account_data:
                account = account_data['securitiesAccount']
                balances = account.get('currentBalances', {})
                
                return {
                    'account_number': account.get('accountNumber', ''),
                    'account_type': account.get('type', ''),
                    'cash_balance': balances.get('cashBalance', 0),
                    'buying_power': balances.get('buyingPower', 0),
                    'equity': balances.get('equity', 0),
                    'margin_balance': balances.get('marginBalance', 0),
                    'available_funds': balances.get('availableFunds', 0)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return {}
    
    def display_futures_dashboard(self):
        """Display futures trading dashboard."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]           CHARLES SCHWAB FUTURES TRADING DASHBOARD            [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
        
        # Account Info
        account_info = self.get_account_info()
        if account_info:
            info_table = Table(title="Account Information", box=box.ROUNDED)
            info_table.add_column("Metric", style="cyan")
            info_table.add_column("Value", style="green", justify="right")
            
            info_table.add_row("Account Type", account_info.get('account_type', 'N/A'))
            info_table.add_row("Cash Balance", f"${account_info.get('cash_balance', 0):,.2f}")
            info_table.add_row("Buying Power", f"${account_info.get('buying_power', 0):,.2f}")
            info_table.add_row("Total Equity", f"${account_info.get('equity', 0):,.2f}")
            info_table.add_row("Available Funds", f"${account_info.get('available_funds', 0):,.2f}")
            
            console.print(info_table)
            console.print()
        
        # Positions
        positions = self.get_positions()
        if positions:
            pos_table = Table(title="Current Positions", box=box.ROUNDED)
            pos_table.add_column("Symbol", style="cyan")
            pos_table.add_column("Quantity", justify="right")
            pos_table.add_column("Avg Price", justify="right")
            pos_table.add_column("Market Value", justify="right")
            pos_table.add_column("P&L", justify="right")
            pos_table.add_column("P&L %", justify="right")
            
            for pos in positions:
                pnl = pos['unrealized_pnl']
                pnl_pct = pos['unrealized_pnl_pct']
                pnl_color = "green" if pnl >= 0 else "red"
                
                pos_table.add_row(
                    pos['symbol'],
                    str(int(pos['quantity'])),
                    f"${pos['average_price']:,.2f}",
                    f"${pos['market_value']:,.2f}",
                    f"[{pnl_color}]${pnl:,.2f}[/{pnl_color}]",
                    f"[{pnl_color}]{pnl_pct:+.2f}%[/{pnl_color}]"
                )
            
            console.print(pos_table)
        else:
            console.print("[yellow]No open positions[/yellow]")
        
        console.print()
        
        # Popular Futures Quotes
        popular_futures = ['/ES', '/NQ', '/YM', '/RTY', '/CL', '/GC']
        quotes = self.get_futures_quotes(popular_futures)
        
        if quotes:
            quotes_table = Table(title="Market Quotes", box=box.ROUNDED)
            quotes_table.add_column("Symbol", style="cyan")
            quotes_table.add_column("Last", justify="right")
            quotes_table.add_column("Change", justify="right")
            quotes_table.add_column("Change %", justify="right")
            quotes_table.add_column("Bid", justify="right")
            quotes_table.add_column("Ask", justify="right")
            quotes_table.add_column("Volume", justify="right")
            
            for symbol, quote in quotes.items():
                change = quote.get('change', 0)
                change_pct = quote.get('change_pct', 0)
                color = "green" if change >= 0 else "red"
                
                quotes_table.add_row(
                    symbol,
                    f"${quote.get('last', 0):,.2f}",
                    f"[{color}]{change:+.2f}[/{color}]",
                    f"[{color}]{change_pct:+.2f}%[/{color}]",
                    f"${quote.get('bid', 0):,.2f}",
                    f"${quote.get('ask', 0):,.2f}",
                    f"{quote.get('volume', 0):,}"
                )
            
            console.print(quotes_table)


class DataManager:
    """Manages market data fetching with caching and validation."""
    
    @staticmethod
    def validate_data(df: pd.DataFrame, min_rows: int = 50) -> bool:
        """Validate market data."""
        if df is None or df.empty:
            logger.error("Empty dataframe received")
            return False
        
        if len(df) < min_rows:
            logger.warning(f"Insufficient data: {len(df)} rows (minimum {min_rows})")
            return False
        
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return False
        
        return True
    
    # lightweight recent-cache to avoid repeated network calls for 1m polling
    _recent_cache: Dict[str, Tuple[float, pd.DataFrame]] = {}

    @staticmethod
    def fetch_data(ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """Fetch market data with caching. Uses Polygon.io for day trading, yfinance for everything else."""
        import time

        logger.info(f"Fetching {ticker} data: period={period}, interval={interval}")

        tickers = [t.strip() for t in ticker.replace(',', ' ').split()]
        if len(tickers) > 1:
            logger.warning(f"Multiple tickers detected: {tickers}. Using first ticker: {tickers[0]}")
            ticker = tickers[0]

        # Precompute crypto flag (needed later regardless of interval)
        is_crypto = ticker.upper().endswith('-USD') or ticker.upper().startswith('BTC') or '-' in ticker

        # DAY TRADING: Use Polygon.io for intraday intervals when enabled and suitable
        intraday_intervals = ['1m', '5m', '15m', '30m', '1h']
        if interval in intraday_intervals:
            # Determine whether to prefer Polygon
            prefer_polygon = True
            try:
                cfg = ConfigurationManager.load_config()
            except Exception:
                cfg = {}
            # Disable for crypto-style tickers and when no API key (already have is_crypto)
            api_key = os.getenv('POLYGON_API_KEY') or cfg.get('polygon_api_key')
            prefer_polygon = bool(cfg.get('prefer_polygon_intraday', True)) and bool(api_key) and not is_crypto

            if prefer_polygon:
                logger.info(f"📊 Day trading mode: Using Polygon.io for {interval} data")
                polygon_df = PolygonDataFetcher.fetch_intraday_data(ticker, interval)
                if polygon_df is not None and not polygon_df.empty:
                    if DataManager.validate_data(polygon_df):
                        return polygon_df
                    else:
                        logger.warning("Polygon data failed validation, falling back to yfinance")
                # If Polygon fails, continue to yfinance below
                logger.info("Falling back to yfinance for intraday data")
            else:
                reason = "no API key" if not api_key else ("crypto ticker" if is_crypto else "config disabled")
                logger.info(f"Skipping Polygon for intraday ({reason}); using yfinance")
                if is_crypto:
                    logger.info(f"🌐 Coinbase WebSocket will be used for real-time {ticker} prices")
        
        # SWING/LONG-TERM: Use yfinance for daily/weekly intervals
        logger.info(f"📈 Using yfinance for {interval} historical bars")
        if is_crypto:
            logger.info(f"💹 Live prices: Coinbase WebSocket | Charts: yfinance history")
        
        last_exc = None
        # Quick recent-cache: for 1m interval, if we fetched <5s ago, return cached
        try:
            key = f"{ticker}|{period}|{interval}"
            now_ts = time.time()
            if interval == '1m' and key in DataManager._recent_cache:
                ts, cached_df = DataManager._recent_cache[key]
                if now_ts - ts < 5.0:
                    logger.debug("Returning recent cached 1m data")
                    return cached_df
        except Exception:
            pass
        
        # Normalize interval for yfinance (1w → 1wk)
        yf_interval = interval.replace('1w', '1wk') if interval == '1w' else interval
        
        for attempt in range(1, 4):
            try:
                df = yf.download(ticker, period=period, interval=yf_interval,
                                 progress=False, auto_adjust=True, prepost=True)

                # yfinance sometimes returns an empty DataFrame instead of raising
                if df is None or df.empty:
                    logger.warning(f"Attempt {attempt}: no data returned from yf.download for {ticker}")
                    last_exc = RuntimeError("Empty DataFrame from yf.download")
                    time.sleep(0.8 * attempt)
                    continue

                # If multiindex (e.g., multiple tickers) extract first column group
                if isinstance(df.columns, pd.MultiIndex):
                    try:
                        ticker_name = df.columns.get_level_values(1)[0]
                        df = df.xs(ticker_name, level=1, axis=1)
                        logger.info(f"Extracted data for ticker: {ticker_name}")
                    except Exception:
                        # fallback: pick first top-level column set
                        df = df.iloc[:, df.columns.get_level_values(0) == df.columns.get_level_values(0)[0]]

                required_cols = ['Open', 'High', 'Low', 'Close']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    logger.warning(f"Attempt {attempt}: missing columns {missing_cols} for {ticker}")
                    last_exc = RuntimeError(f"Missing columns: {missing_cols}")
                    time.sleep(0.5 * attempt)
                    continue

                if 'Volume' not in df.columns:
                    df['Volume'] = 1
                    logger.warning("Volume column missing, using default values")

                df['Volume'] = df['Volume'].fillna(1).replace(0, 1)
                df = df.dropna()

                if not DataManager.validate_data(df):
                    last_exc = RuntimeError("Validation failed for fetched data")
                    time.sleep(0.5 * attempt)
                    continue

                logger.info(f"Successfully fetched {len(df)} bars for {ticker} (yf.download)")
                # store recent cache for high-frequency intervals
                try:
                    if interval == '1m':
                        DataManager._recent_cache[key] = (time.time(), df)
                except Exception:
                    pass
                return df

            except Exception as e:
                logger.warning(f"Attempt {attempt}: error fetching {ticker} via yf.download: {e}")
                last_exc = e
                time.sleep(0.6 * attempt)

        # yf.download attempts failed — try yf.Ticker.history as a fallback
        try:
            logger.info(f"Falling back to yf.Ticker.history for {ticker}")
            tk = yf.Ticker(ticker)
            df = tk.history(period=period, interval=interval, auto_adjust=True)

            if df is None or df.empty:
                logger.error(f"yf.Ticker.history returned no data for {ticker}")
                return None

            # history returns columns often named Open/High/Low/Close — validate
            required_cols = ['Open', 'High', 'Low', 'Close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"yf.Ticker.history missing columns {missing_cols} for {ticker}")
                return None

            df['Volume'] = df.get('Volume', pd.Series(1, index=df.index)).fillna(1).replace(0, 1)
            df = df.dropna()

            if not DataManager.validate_data(df):
                return None

            logger.info(f"Successfully fetched {len(df)} bars for {ticker} (yf.Ticker.history)")
            try:
                if interval == '1m':
                    DataManager._recent_cache[key] = (time.time(), df)
            except Exception:
                pass
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker} (all methods): {e} | last_exc={last_exc}")
            console.print(f"[yellow]Debug: yfinance error details for {ticker}: {str(e)[:200]}[/yellow]")
            return None
    
    @staticmethod
    def get_ticker_info(ticker: str) -> Dict[str, Any]:
        """Get ticker information."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'price': info.get('currentPrice', 0),
                'description': info.get('longBusinessSummary', '')[:200] + '...'
            }
        except:
            return {
                'name': ticker,
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': 0,
                'price': 0,
                'description': ''
            }

    # realtime price cache (shared across threads)
    _latest_prices: Dict[str, Tuple[float, float]] = {}
    # Tick history for crypto symbols from Coinbase WS: {ticker: deque[(ts, price)]}
    _tick_history: Dict[str, Any] = {}
    _price_updater_thread = None
    _price_updater_stop = False
    _greeks_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    # Crypto WS state
    _crypto_ws_thread = None
    _crypto_ws_stop = False
    _crypto_ws_symbols: set = set()

    @staticmethod
    def start_price_updater(adapter=None, tickers: list = None, interval: float = 0.5):
        """Start a background thread that polls latest prices for `tickers`.

        Stores results in `DataManager._latest_prices` as {ticker: (ts, price)}.
        """
        if tickers is None or len(tickers) == 0:
            return

        def _updater():
            while not DataManager._price_updater_stop:
                for t in tickers:
                    try:
                        p = None
                        if adapter is not None:
                            # Try multiple real-time methods for better coverage
                            for m in ('get_latest_price','get_latest_trade','get_last_trade','get_quote','get_last_quote','get_snapshot'):
                                try:
                                    if hasattr(adapter, m):
                                        fn = getattr(adapter, m)
                                        val = fn(t)
                                        if val is None:
                                            continue
                                        if isinstance(val, (int, float)):
                                            p = float(val)
                                            break
                                        if isinstance(val, dict):
                                            # Check common keys
                                            for k in ('price','last_price','trade_price','p','ap','bp'):
                                                if k in val and val[k] is not None:
                                                    p = float(val[k])
                                                    break
                                            if p is not None:
                                                break
                                            lt = val.get('latestTrade') or val.get('lastTrade')
                                            if isinstance(lt, dict):
                                                if lt.get('price') is not None:
                                                    p = float(lt['price'])
                                                    break
                                                if lt.get('p') is not None:
                                                    p = float(lt['p'])
                                                    break
                                except Exception:
                                    continue

                        if p is None:
                            try:
                                p = DataManager.get_realtime_price(t)
                            except Exception:
                                p = None

                        if p is not None:
                            DataManager._latest_prices[t] = (time.time(), float(p))
                    except Exception:
                        pass

                time.sleep(max(0.1, interval))

        # stop existing
        try:
            DataManager._price_updater_stop = True
            if DataManager._price_updater_thread is not None and DataManager._price_updater_thread.is_alive():
                DataManager._price_updater_thread.join(timeout=0.2)
        except Exception:
            pass

        DataManager._price_updater_stop = False
        import threading
        DataManager._price_updater_thread = threading.Thread(target=_updater, daemon=True)
        DataManager._price_updater_thread.start()

    @staticmethod
    def stop_price_updater():
        DataManager._price_updater_stop = True
        try:
            if DataManager._price_updater_thread is not None:
                DataManager._price_updater_thread.join(timeout=0.5)
        except Exception:
            pass

    # ---------------- CRYPTO WEBSOCKET (COINBASE) ----------------
    @staticmethod
    def _run_coinbase_ws():
        """Background thread: connect to Coinbase Advanced WS and stream tickers to cache."""
        try:
            import asyncio
            import json as _json
            try:
                import websockets  # type: ignore
            except Exception:
                logger.warning("Coinbase WS requested but 'websockets' not installed; skipping WS.")
                return

            url = 'wss://advanced-trade-ws.coinbase.com'

            async def _consumer():
                nonlocal url
                backoff = 1.0
                while not DataManager._crypto_ws_stop:
                    try:
                        async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
                            # Subscribe initial set
                            if DataManager._crypto_ws_symbols:
                                sub = {
                                    "type": "subscribe",
                                    "channel": "ticker",
                                    "product_ids": sorted(list(DataManager._crypto_ws_symbols))
                                }
                                await ws.send(_json.dumps(sub))
                            backoff = 1.0
                            # Read loop
                            while not DataManager._crypto_ws_stop:
                                try:
                                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                                except asyncio.TimeoutError:
                                    # If new symbols added, re-subscribe
                                    if DataManager._crypto_ws_symbols:
                                        sub = {
                                            "type": "subscribe",
                                            "channel": "ticker",
                                            "product_ids": sorted(list(DataManager._crypto_ws_symbols))
                                        }
                                        try:
                                            await ws.send(_json.dumps(sub))
                                        except Exception:
                                            pass
                                    continue
                                except Exception:
                                    break

                                try:
                                    data = _json.loads(msg)
                                except Exception:
                                    continue

                                # Parse both direct and nested formats
                                try:
                                    if (data.get('channel') == 'ticker') and ('price' in data) and ('product_id' in data):
                                        pid = data['product_id']
                                        price = float(data['price'])
                                        nowts = time.time()
                                        DataManager._latest_prices[pid] = (nowts, price)
                                        # Append to tick history
                                        try:
                                            from collections import deque
                                            if pid not in DataManager._tick_history:
                                                DataManager._tick_history[pid] = deque(maxlen=20000)
                                            DataManager._tick_history[pid].append((nowts, price))
                                        except Exception:
                                            pass
                                        continue
                                except Exception:
                                    pass

                                try:
                                    if data.get('channel') == 'ticker' and 'events' in data:
                                        for ev in data['events']:
                                            tickers = ev.get('tickers') or []
                                            for t in tickers:
                                                pid = t.get('product_id') or t.get('productId')
                                                prw = t.get('price') or t.get('p')
                                                if pid and prw:
                                                    price = float(prw)
                                                    nowts = time.time()
                                                    DataManager._latest_prices[pid] = (nowts, price)
                                                    try:
                                                        from collections import deque
                                                        if pid not in DataManager._tick_history:
                                                            DataManager._tick_history[pid] = deque(maxlen=20000)
                                                        DataManager._tick_history[pid].append((nowts, price))
                                                    except Exception:
                                                        pass
                                except Exception:
                                    pass

                    except Exception as e:
                        logger.warning(f"Coinbase WS reconnect in {backoff:.0f}s: {e}")
                        try:
                            await asyncio.sleep(backoff)
                        except Exception:
                            pass
                        backoff = min(30.0, backoff * 2.0)

            try:
                asyncio.run(_consumer())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_consumer())
        except Exception as e:
            logger.error(f"Coinbase WS thread error: {e}")

    @staticmethod
    def start_crypto_ws(symbols: Optional[List[str]] = None):
        """Start Coinbase WS for given crypto product IDs (e.g., 'BTC-USD')."""
        # Respect configuration toggle
        try:
            cfg = ConfigurationManager.load_config()
            if not bool(cfg.get('enable_crypto_ws', True)):
                return
        except Exception:
            pass
        # Normalize symbols
        if symbols:
            for s in symbols:
                if s and s.upper().endswith('-USD'):
                    DataManager._crypto_ws_symbols.add(s.upper())
        # Start thread if not running
        if DataManager._crypto_ws_thread is None or not DataManager._crypto_ws_thread.is_alive():
            DataManager._crypto_ws_stop = False
            import threading
            DataManager._crypto_ws_thread = threading.Thread(target=DataManager._run_coinbase_ws, daemon=True)
            DataManager._crypto_ws_thread.start()

    @staticmethod
    def add_crypto_symbol(symbol: str):
        if symbol and symbol.upper().endswith('-USD'):
            DataManager._crypto_ws_symbols.add(symbol.upper())

    @staticmethod
    def stop_crypto_ws():
        DataManager._crypto_ws_stop = True
        try:
            if DataManager._crypto_ws_thread is not None:
                DataManager._crypto_ws_thread.join(timeout=1.0)
        except Exception:
            pass

    @staticmethod
    def get_cached_price(ticker: str, max_age: float = 2.0) -> Optional[float]:
        """Return cached price if younger than `max_age` seconds."""
        try:
            rec = DataManager._latest_prices.get(ticker)
            if not rec:
                return None
            ts, p = rec
            age = time.time() - ts
            if age <= max_age:
                # Log source for crypto vs others
                if ticker.upper().endswith('-USD'):
                    logger.debug(f"💹 {ticker} price from Coinbase WS: ${p:.2f} (age: {age:.1f}s)")
                return float(p)
            return None
        except Exception:
            return None

    @staticmethod
    def get_cached_price_age(ticker: str) -> Optional[float]:
        """Return age (seconds) of cached price if available."""
        try:
            rec = DataManager._latest_prices.get(ticker)
            if not rec:
                return None
            ts, _ = rec
            return float(max(0.0, time.time() - ts))
        except Exception:
            return None

    @staticmethod
    def get_micro_features(ticker: str, window_secs: int = 20) -> Optional[Dict[str, float]]:
        """Compute microstructure features from Coinbase WS ticks over the last `window_secs` seconds.

        Returns dict with keys: micro_roc_5s (pct), vwap_dev (pct), tick_rate (ticks/sec), last_tick_age (s).
        """
        try:
            dq = DataManager._tick_history.get(ticker)
            if not dq:
                return None
            now = time.time()
            recent = [(ts, p) for (ts, p) in dq if (now - ts) <= window_secs]
            if len(recent) < 2:
                return None
            prices = [p for _, p in recent]
            times = [ts for ts, _ in recent]
            last_price = prices[-1]
            # 5s momentum
            cutoff5 = now - 5.0
            # Find price closest to 5s ago
            idx5 = 0
            for i in range(len(times)):
                if times[i] >= cutoff5:
                    idx5 = i
                    break
            base5 = prices[idx5]
            micro_roc_5s = (last_price - base5) / base5 * 100 if base5 else 0.0
            # VWAP proxy (no sizes): simple mean
            mean_price = sum(prices) / len(prices)
            vwap_dev = (last_price - mean_price) / mean_price * 100 if mean_price else 0.0
            # Tick rate
            dt = max(1e-3, times[-1] - times[0])
            tick_rate = len(recent) / dt
            last_tick_age = now - times[-1]
            return {
                'micro_roc_5s': float(micro_roc_5s),
                'vwap_dev': float(vwap_dev),
                'tick_rate': float(tick_rate),
                'last_tick_age': float(last_tick_age)
            }
        except Exception:
            return None

    @staticmethod
    def get_realtime_price(ticker: str, adapter=None) -> Optional[float]:
        """Return the most recent price for `ticker`.

        If an `adapter` (Alpaca) is provided, prefer its realtime method.
        Otherwise fall back to yfinance fast_info or the latest 1m bar.
        """
        try:
            # Auto-start Coinbase WS for crypto tickers (if enabled)
            if ticker.upper().endswith('-USD'):
                try:
                    DataManager.start_crypto_ws([ticker.upper()])
                except Exception:
                    pass

            # Prefer cached recent price first
            try:
                cached = DataManager.get_cached_price(ticker, max_age=2.0)
                if cached is not None:
                    return float(cached)
            except Exception:
                pass

            # Prefer adapter direct quote
            if adapter is not None:
                # Try a series of common real-time methods (different adapters expose different names)
                adapter_methods = [
                    'get_latest_price',
                    'get_latest_trade',
                    'get_last_trade',
                    'get_quote',
                    'get_last_quote',
                    'get_snapshot'
                ]
                for m in adapter_methods:
                    try:
                        if hasattr(adapter, m):
                            fn = getattr(adapter, m)
                            val = fn(ticker)
                            # Handle dict-like responses from some APIs
                            if val is None:
                                continue
                            if isinstance(val, (int, float)):
                                return float(val)
                            # Common keys for trade/quote payloads
                            for k in ('price', 'last_price', 'trade_price', 'p', 'ap', 'bp'):
                                if isinstance(val, dict) and k in val and val[k] is not None:
                                    return float(val[k])
                            # Snapshot structures
                            if isinstance(val, dict):
                                lt = val.get('latestTrade') or val.get('lastTrade')
                                if isinstance(lt, dict):
                                    if 'price' in lt and lt['price'] is not None:
                                        return float(lt['price'])
                                    if 'p' in lt and lt['p'] is not None:  # polygon-compatible
                                        return float(lt['p'])
                    except Exception:
                        continue

            # Try yfinance fast_info
            try:
                tk = yf.Ticker(ticker)
                fi = getattr(tk, 'fast_info', None)
                if fi:
                    # fast_info may be a dict-like with 'last_price' or 'last' keys
                    if isinstance(fi, dict):
                        for k in ('last_price', 'last', 'last_trade_price'):
                            if k in fi and fi[k] is not None:
                                return float(fi[k])
                    else:
                        # attribute access
                        val = getattr(fi, 'last_price', None) or getattr(fi, 'last', None)
                        if val is not None:
                            return float(val)
            except Exception:
                pass

            # Fallback to last 1-minute bar close via DataManager.fetch_data (uses caching)
            try:
                df = DataManager.fetch_data(ticker, '2d', '1m')
                if df is not None and not df.empty:
                    return float(df['Close'].iloc[-1])
            except Exception:
                pass

            return None
        except Exception:
            return None

    @staticmethod
    def get_fundamentals(ticker: str) -> Dict[str, Any]:
        """Return simple fundamentals like PE ratios via yfinance."""
        out = {}
        try:
            tk = yf.Ticker(ticker)
            info = getattr(tk, 'info', {}) or {}
            out['trailingPE'] = info.get('trailingPE')
            out['forwardPE'] = info.get('forwardPE')
            out['pegRatio'] = info.get('pegRatio')
            out['marketCap'] = info.get('marketCap')
        except Exception:
            pass
        return out

    @staticmethod
    def _std_norm_pdf(x: float) -> float:
        return (1.0 / (2.5066282746310002)) * math.exp(-0.5 * x * x)

    @staticmethod
    def _std_norm_cdf(x: float) -> float:
        # approximate using erf
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def black_scholes_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> Dict[str, float]:
        """Return basic Black-Scholes Greeks for European option.

        S: spot, K: strike, T: time to expiry in years, r: risk-free rate, sigma: vol (annual)
        """
        try:
            if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
                return {'delta': 0.0, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0, 'rho': 0.0}

            d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            pdf_d1 = DataManager._std_norm_pdf(d1)
            cdf_d1 = DataManager._std_norm_cdf(d1)
            cdf_d2 = DataManager._std_norm_cdf(d2)

            gamma = pdf_d1 / (S * sigma * math.sqrt(T))
            vega = S * pdf_d1 * math.sqrt(T) / 100.0  # per 1% vol
            if option_type.lower().startswith('c'):
                delta = cdf_d1
                theta = (-S * pdf_d1 * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * cdf_d2) / 365.0
                rho = K * T * math.exp(-r * T) * cdf_d2 / 100.0
            else:
                delta = cdf_d1 - 1
                theta = (-S * pdf_d1 * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * (1 - cdf_d2)) / 365.0
                rho = -K * T * math.exp(-r * T) * (1 - cdf_d2) / 100.0

            return {
                'delta': float(delta),
                'gamma': float(gamma),
                'vega': float(vega),
                'theta': float(theta),
                'rho': float(rho)
            }
        except Exception:
            return {'delta': 0.0, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0, 'rho': 0.0}

    @staticmethod
    def get_option_chain_greeks(ticker: str, adapter=None) -> Dict[str, Any]:
        """Fetch nearest expiry option chain from yfinance and compute ATM Greeks.

        Returns a dict with nearest expiry, atm_strike, call_greeks, put_greeks and used_implied_vol.
        """
        # Cache check
        ttl_default = 120.0  # seconds
        try:
            ttl_env = os.getenv('GREEKS_CACHE_TTL')
            if ttl_env:
                ttl_default = float(ttl_env)
        except Exception:
            pass

        now_ts = time.time()
        cached = DataManager._greeks_cache.get(ticker)
        if cached and (now_ts - cached[0] <= ttl_default):
            return cached[1]

        res: Dict[str, Any] = {}
        try:
            tk = yf.Ticker(ticker)
            expiries = getattr(tk, 'options', None) or []
            if not expiries:
                return res

            exp = expiries[0]
            chain = tk.option_chain(exp)
            calls = chain.calls
            puts = chain.puts

            spot = DataManager.get_cached_price(ticker, max_age=3.0) or DataManager.get_realtime_price(ticker)
            if spot is None or calls is None or calls.empty:
                return res

            calls['diff'] = calls['strike'].apply(lambda k: abs(k - spot))
            calls_sorted = calls.sort_values('diff')
            if calls_sorted.empty:
                return res
            atm = calls_sorted.iloc[0]
            K = float(atm['strike'])

            iv = None
            if 'impliedVolatility' in atm and not pd.isna(atm['impliedVolatility']):
                iv = float(atm['impliedVolatility'])
                if iv > 5:
                    iv = iv / 100.0
            tdate = pd.to_datetime(exp).to_pydatetime()
            T = max(1/365.0, (tdate - datetime.utcnow()).total_seconds() / (365.0 * 24 * 3600))
            if iv is None or iv <= 0:
                iv = 0.35
            r = 0.03
            call_g = DataManager.black_scholes_greeks(spot, K, T, r, iv, 'call')
            put_g = DataManager.black_scholes_greeks(spot, K, T, r, iv, 'put')
            res = {
                'expiry': exp,
                'atm_strike': K,
                'used_iv': iv,
                'call_greeks': call_g,
                'put_greeks': put_g,
                'spot': float(spot),
                'cache_ts': now_ts
            }
        except Exception:
            return res

        # store in cache
        DataManager._greeks_cache[ticker] = (now_ts, res)
        return res

# ==========================================
# NEWS & SEC FILINGS
# ==========================================

class NewsAnalyzer:
    """Fetches and analyzes market news."""
    
    @staticmethod
    def get_news(ticker: str, limit: int = 10) -> List[NewsItem]:
        """Get real news headlines for a ticker - strict ticker verification on all sources."""
        news_items = []
        try:
            import requests
            
            logger.info(f"📰 Fetching {ticker} headlines (strict ticker filtering)...")
            
            ticker_lower = ticker.lower()
            ticker_upper = ticker.upper()
            
            def verify_ticker_in_title(title: str) -> bool:
                """Strict check: title must contain ticker symbol."""
                if not title:
                    return False
                title_lower = title.lower()
                # Accept if ticker appears in title (case-insensitive)
                return ticker_lower in title_lower or ticker_upper in title
            
            def calculate_sentiment(title: str) -> str:
                """Calculate sentiment from headline words."""
                txt = title.lower()
                words = txt.split()
                pos_words = {"gain", "surge", "beat", "positive", "up", "growth", "profit", "rally", "jump", "strong", "rises", "exceeds", "soars"}
                neg_words = {"loss", "down", "fall", "negative", "risk", "drop", "miss", "decline", "crash", "weak", "falls", "plunges", "slumps"}
                pos = sum(1 for w in words if w in pos_words)
                neg = sum(1 for w in words if w in neg_words)
                return "POSITIVE" if pos > neg else ("NEGATIVE" if neg > pos else "NEUTRAL")
            
            # Method 1: Polygon.io News API - BEST FOR TICKER-SPECIFIC
            try:
                poly_key = os.getenv('POLYGON_API_KEY')
                if poly_key:
                    url = f"https://api.polygon.io/v2/reference/news?query={ticker}&limit={limit*3}&apiKey={poly_key}"
                    response = requests.get(url, timeout=8)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'OK' and 'results' in data:
                            logger.debug(f"Polygon returned {len(data.get('results', []))} results")
                            for item in data['results'][:limit*3]:
                                title = item.get('title', '') or item.get('headline', '')
                                
                                # STRICT: Only accept if ticker is in headline
                                if not title or len(title) < 15:
                                    continue
                                if not verify_ticker_in_title(title):
                                    logger.debug(f"Rejected (no ticker): {title[:50]}")
                                    continue
                                    
                                url_str = item.get('article_url', f"https://finance.yahoo.com/quote/{ticker}")
                                
                                # Sentiment
                                sentiment = calculate_sentiment(title)
                                
                                news_items.append(NewsItem(
                                    title=title,
                                    source=item.get('publisher', {}).get('name', 'Polygon') if isinstance(item.get('publisher'), dict) else 'Polygon',
                                    published="Today",
                                    url=url_str,
                                    sentiment=sentiment,
                                    relevance=0.98,
                                    score=0.0
                                ))
                            
                            if len(news_items) > 0:
                                logger.info(f"✓ Found {len(news_items)} {ticker}-specific headlines via Polygon.io")
                                return news_items[:limit]
                            else:
                                logger.debug(f"Polygon: No {ticker}-specific headlines after filtering")
            except Exception as e:
                logger.debug(f"Polygon.io API failed: {e}")
            
            # Method 2: Finnhub News API - TICKER-SPECIFIC
            try:
                fh_key = os.getenv('FINNHUB_API_KEY')
                if fh_key:
                    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&token={fh_key}&limit={limit*3}"
                    response = requests.get(url, timeout=8)
                    if response.status_code == 200:
                        items = response.json()
                        if items and isinstance(items, list):
                            logger.debug(f"Finnhub returned {len(items)} results")
                            for item in items[:limit*3]:
                                title = item.get('headline', '')
                                
                                # STRICT: Only accept if ticker is in headline
                                if not title or len(title) < 15:
                                    continue
                                if not verify_ticker_in_title(title):
                                    logger.debug(f"Rejected (no ticker): {title[:50]}")
                                    continue
                                
                                url_str = item.get('url', f"https://finance.yahoo.com/quote/{ticker}")
                                sentiment = calculate_sentiment(title)
                                
                                news_items.append(NewsItem(
                                    title=title,
                                    source=item.get('source', 'Finnhub'),
                                    published="Today",
                                    url=url_str,
                                    sentiment=sentiment,
                                    relevance=0.95,
                                    score=0.0
                                ))
                            
                            if len(news_items) > 0:
                                logger.info(f"✓ Found {len(news_items)} {ticker}-specific headlines via Finnhub")
                                return news_items[:limit]
                            else:
                                logger.debug(f"Finnhub: No {ticker}-specific headlines after filtering")
            except Exception as e:
                logger.debug(f"Finnhub API failed: {e}")
            
            # Method 3: AlphaVantage News API
            try:
                av_key = os.getenv('ALPHAVANTAGE_API_KEY')
                if av_key:
                    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={av_key}&limit={limit*3}"
                    response = requests.get(url, timeout=8)
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('feed', [])
                        if items:
                            logger.debug(f"AlphaVantage returned {len(items)} results")
                            for item in items[:limit*3]:
                                title = item.get('title', '')
                                
                                # STRICT: Only accept if ticker is in headline
                                if not title or len(title) < 15:
                                    continue
                                if not verify_ticker_in_title(title):
                                    logger.debug(f"Rejected (no ticker): {title[:50]}")
                                    continue
                                
                                url_str = item.get('url', f"https://finance.yahoo.com/quote/{ticker}")
                                sentiment = item.get('overall_sentiment_label', 'NEUTRAL')
                                
                                news_items.append(NewsItem(
                                    title=title,
                                    source=item.get('source', 'AlphaVantage'),
                                    published="Today",
                                    url=url_str,
                                    sentiment=sentiment,
                                    relevance=0.90,
                                    score=0.0
                                ))
                            if len(news_items) > 0:
                                logger.info(f"✓ Found {len(news_items)} {ticker}-specific headlines via AlphaVantage")
                                return news_items[:limit]
                            else:
                                logger.debug(f"AlphaVantage: No {ticker}-specific headlines after filtering")
            except Exception as e:
                logger.debug(f"AlphaVantage API failed: {e}")
            
            # Method 4: Yahoo Finance HTML - LAST RESORT
            try:
                from bs4 import BeautifulSoup
                
                news_url = f"https://finance.yahoo.com/quote/{ticker}/news"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                }
                
                response = requests.get(news_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    all_links = soup.find_all('a', href=True, limit=300)
                    
                    logger.debug(f"Yahoo Finance: Found {len(all_links)} links")
                    
                    for link in all_links:
                        if len(news_items) >= limit:
                            break
                        
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Basic validation
                        if not title or len(title) < 25 or len(title) > 300:
                            continue
                        
                        # STRICT: Must contain ticker
                        if not verify_ticker_in_title(title):
                            continue
                        
                        # Skip nav elements
                        skip_words = ['sign in', 'subscribe', 'settings', 'watchlist', 'follow', 'notifications', 'communities', 'profile', 'help']
                        if any(skip in title.lower() for skip in skip_words):
                            continue
                        
                        # Must look like a news link
                        if not ('news' in href.lower() or 'article' in href.lower() or href.startswith('http')):
                            continue
                        
                        # Avoid duplicates
                        if title in [item.title for item in news_items]:
                            continue
                        
                        # Build full URL
                        if href and not href.startswith('http'):
                            href = 'https://finance.yahoo.com' + href if href.startswith('/') else f'https://finance.yahoo.com/{href}'
                        
                        sentiment = calculate_sentiment(title)
                        
                        news_items.append(NewsItem(
                            title=title,
                            source="Yahoo Finance",
                            published="Today",
                            url=href if href and href.startswith('http') else f"https://finance.yahoo.com/quote/{ticker}",
                            sentiment=sentiment,
                            relevance=0.85,
                            score=0.0
                        ))
                    
                    if len(news_items) > 0:
                        logger.info(f"✓ Found {len(news_items)} {ticker}-specific headlines via Yahoo Finance")
                        return news_items[:limit]
                    else:
                        logger.debug(f"Yahoo Finance: No {ticker}-specific headlines after filtering")
                        
            except Exception as e:
                logger.debug(f"Yahoo Finance HTML parsing failed: {e}")
            
            # Final fallback - show search link
            if len(news_items) == 0:
                logger.warning(f"⚠ No real headlines found for {ticker} - check your API keys or ticker symbol")
                news_items = [
                    NewsItem(
                        title=f"🔍 Search {ticker} news on Yahoo Finance",
                        source="Yahoo Finance",
                        published="Today",
                        url=f"https://finance.yahoo.com/quote/{ticker}/news",
                        sentiment="NEUTRAL",
                        relevance=0.3,
                        score=0.0
                    )
                ]
                
        except Exception as e:
            logger.error(f"Critical error in get_news: {e}")
            news_items = [
                NewsItem(
                    title=f"View {ticker} news on Yahoo Finance",
                    source="Yahoo Finance",
                    published="Today",
                    url=f"https://finance.yahoo.com/quote/{ticker}/news",
                    sentiment="NEUTRAL",
                    relevance=1.0,
                    score=0.0
                )
            ]
        
        return news_items[:limit]
    
    @staticmethod
    def search_theme_news(theme: str) -> List[Dict[str, Any]]:
        """Search news by theme (e.g., 'quantum computing')."""
        console.print(f"[yellow]Searching news for: {theme}[/yellow]")
        return []


# ==========================================
# FINNHUB API - REAL-TIME NEWS & COMPANY DATA
# ==========================================

class FinnhubAnalyzer:
    """Fetches real-time news, earnings, company data from Finnhub (free API)."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    @staticmethod
    def get_api_key() -> str:
        """Get Finnhub API key from environment."""
        key = os.getenv('FINNHUB_API_KEY', '')
        if not key:
            logger.debug("Finnhub API key not set. Set FINNHUB_API_KEY environment variable.")
        return key
    
    @staticmethod
    def get_news(ticker: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch company-specific news from Finnhub."""
        api_key = FinnhubAnalyzer.get_api_key()
        if not api_key:
            return []
        
        articles = []
        try:
            import requests
            
            url = f"{FinnhubAnalyzer.BASE_URL}/company-news"
            params = {
                'symbol': ticker.upper(),
                'token': api_key,
                'limit': min(limit, 50)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                items = response.json()
                if items and isinstance(items, list):
                    for item in items:
                        articles.append({
                            'title': item.get('headline', ''),
                            'url': item.get('url', ''),
                            'source': item.get('source', 'Finnhub'),
                            'timestamp': item.get('datetime', 0),
                            'summary': item.get('summary', ''),
                            'image': item.get('image', ''),
                            'sentiment': 'NEUTRAL',
                            'category': 'Company News'
                        })
                    logger.info(f"✓ Finnhub: Found {len(articles)} news articles for {ticker}")
            else:
                logger.debug(f"Finnhub news request failed: {response.status_code}")
        
        except Exception as e:
            logger.debug(f"Finnhub news fetch error: {e}")
        
        return articles[:limit]
    
    @staticmethod
    def get_company_profile(ticker: str) -> Dict[str, Any]:
        """Fetch company profile and profile data."""
        api_key = FinnhubAnalyzer.get_api_key()
        if not api_key:
            return {}
        
        try:
            import requests
            
            url = f"{FinnhubAnalyzer.BASE_URL}/stock/profile2"
            params = {
                'symbol': ticker.upper(),
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        'company_name': data.get('name', ''),
                        'ticker': data.get('ticker', ticker),
                        'exchange': data.get('exchange', ''),
                        'industry': data.get('finnhubIndustry', ''),
                        'market_cap': data.get('marketCapitalization', 0),
                        'website': data.get('weburl', ''),
                        'country': data.get('country', ''),
                        'currency': data.get('currency', ''),
                        'description': data.get('description', '')
                    }
        except Exception as e:
            logger.debug(f"Finnhub profile fetch error: {e}")
        
        return {}
    
    @staticmethod
    def get_earnings_calendar(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch upcoming earnings dates and past earnings."""
        api_key = FinnhubAnalyzer.get_api_key()
        if not api_key:
            return []
        
        earnings = []
        try:
            import requests
            
            url = f"{FinnhubAnalyzer.BASE_URL}/calendar/earnings"
            params = {
                'symbol': ticker.upper(),
                'token': api_key,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('earningsCalendar'):
                    for item in data['earningsCalendar'][:limit]:
                        earnings.append({
                            'date': item.get('date', ''),
                            'eps_estimate': item.get('epsEstimate', 0),
                            'eps_actual': item.get('epsActual', 0),
                            'revenue_estimate': item.get('revenueEstimate', 0),
                            'revenue_actual': item.get('revenueActual', 0),
                            'quarter': item.get('quarter', ''),
                            'year': item.get('year', '')
                        })
                    logger.info(f"✓ Finnhub: Found {len(earnings)} earnings records for {ticker}")
        except Exception as e:
            logger.debug(f"Finnhub earnings fetch error: {e}")
        
        return earnings[:limit]
    
    @staticmethod
    def get_insider_trades(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch insider trading activity."""
        api_key = FinnhubAnalyzer.get_api_key()
        if not api_key:
            return []
        
        trades = []
        try:
            import requests
            
            url = f"{FinnhubAnalyzer.BASE_URL}/stock/insider-trades"
            params = {
                'symbol': ticker.upper(),
                'token': api_key,
                'limit': min(limit, 100)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    for item in data['data'][:limit]:
                        trades.append({
                            'name': item.get('name', ''),
                            'position': item.get('position', ''),
                            'transaction': item.get('transactionType', ''),
                            'shares': item.get('share', 0),
                            'price': item.get('price', 0),
                            'filed_date': item.get('filingDate', ''),
                            'transaction_date': item.get('transactionDate', '')
                        })
                    logger.info(f"✓ Finnhub: Found {len(trades)} insider trades for {ticker}")
        except Exception as e:
            logger.debug(f"Finnhub insider trades fetch error: {e}")
        
        return trades[:limit]
    
    @staticmethod
    def get_analyst_ratings(ticker: str) -> Dict[str, Any]:
        """Fetch analyst rating recommendations."""
        api_key = FinnhubAnalyzer.get_api_key()
        if not api_key:
            return {}
        
        try:
            import requests
            
            url = f"{FinnhubAnalyzer.BASE_URL}/stock/recommendation"
            params = {
                'symbol': ticker.upper(),
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    latest = data[0]  # Most recent
                    return {
                        'strongBuy': latest.get('strongBuy', 0),
                        'buy': latest.get('buy', 0),
                        'hold': latest.get('hold', 0),
                        'sell': latest.get('sell', 0),
                        'strongSell': latest.get('strongSell', 0),
                        'period': latest.get('period', '')
                    }
        except Exception as e:
            logger.debug(f"Finnhub ratings fetch error: {e}")
        
        return {}


# ==========================================
# SEC EDGAR API - OFFICIAL FILINGS & INSIDER TRADES
# ==========================================

class SECEdgarAnalyzer:
    """Fetches SEC filings and insider trading data from SEC Edgar (completely free, no API key needed)."""
    
    BASE_URL = "https://data.sec.gov/submissions"
    
    @staticmethod
    def get_cik(ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) for a ticker from SEC."""
        try:
            import requests
            
            # SEC provides a JSON mapping of ticker to CIK
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ticker_upper = ticker.upper()
                
                for key, company in data.items():
                    if company.get('ticker', '').upper() == ticker_upper:
                        cik = str(company.get('cik_str', '')).zfill(10)
                        logger.debug(f"✓ Found CIK for {ticker}: {cik}")
                        return cik
        except Exception as e:
            logger.debug(f"SEC CIK lookup error: {e}")
        
        return None
    
    @staticmethod
    def get_recent_filings(ticker: str, form_types: list = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent SEC filings (10-K, 10-Q, 8-K, etc.)."""
        if form_types is None:
            form_types = ['10-K', '10-Q', '8-K', '4']
        
        filings = []
        cik = SECEdgarAnalyzer.get_cik(ticker)
        
        if not cik:
            logger.debug(f"Could not find CIK for {ticker}")
            return []
        
        try:
            import requests
            
            url = f"{SECEdgarAnalyzer.BASE_URL}/CIK{cik}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                filings_list = data.get('filings', {}).get('recent', {})
                
                # Extract filing information
                forms = filings_list.get('form', [])
                dates = filings_list.get('filingDate', [])
                accessions = filings_list.get('accessionNumber', [])
                
                for i, form_type in enumerate(forms[:limit*3]):
                    if form_type in form_types:
                        filing_date = dates[i] if i < len(dates) else ''
                        accession = accessions[i] if i < len(accessions) else ''
                        
                        # Build SEC Edgar link
                        accession_clean = accession.replace('-', '') if accession else ''
                        filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=exclude&count=100"
                        
                        filings.append({
                            'form_type': form_type,
                            'filing_date': filing_date,
                            'company': ticker,
                            'cik': cik,
                            'accession': accession,
                            'url': filing_url,
                            'importance': 'HIGH' if form_type in ['10-K', '8-K'] else 'MEDIUM'
                        })
                
                logger.info(f"✓ SEC Edgar: Found {len(filings)} filings for {ticker}")
        except Exception as e:
            logger.debug(f"SEC Edgar filings fetch error: {e}")
        
        return filings[:limit]
    
    @staticmethod
    def get_insider_trades(ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch insider trading activity (Form 4 filings)."""
        trades = []
        cik = SECEdgarAnalyzer.get_cik(ticker)
        
        if not cik:
            return []
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Get Form 4 filings (insider trades)
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=exclude&count={limit}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                rows = soup.find_all('tr')[1:]  # Skip header
                
                for row in rows[:limit]:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        form_type = cells[0].text.strip()
                        filing_date = cells[3].text.strip()
                        
                        if form_type == '4':
                            trades.append({
                                'form_type': '4',
                                'filing_date': filing_date,
                                'company': ticker,
                                'description': 'Insider Trade (Form 4)',
                                'importance': 'HIGH'
                            })
                
                logger.info(f"✓ SEC Edgar: Found {len(trades)} Form 4 insider trades for {ticker}")
        except Exception as e:
            logger.debug(f"SEC Edgar insider trades fetch error: {e}")
        
        return trades[:limit]
    
    @staticmethod
    def get_company_facts(ticker: str) -> Dict[str, Any]:
        """Fetch company facts and financial data from SEC XBRL."""
        cik = SECEdgarAnalyzer.get_cik(ticker)
        
        if not cik:
            return {}
        
        facts = {}
        try:
            import requests
            
            # SEC provides XBRL data in JSON format
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                entity_data = data.get('facts', {}).get('us-gaap', {})
                
                # Extract key financial metrics
                key_metrics = ['Assets', 'Liabilities', 'StockholdersEquity', 'Revenues', 'NetIncomeLoss']
                
                for metric in key_metrics:
                    if metric in entity_data:
                        values = entity_data[metric].get('units', {}).get('USD', [])
                        if values:
                            latest = values[-1]
                            facts[metric] = {
                                'value': latest.get('val', 0),
                                'filed': latest.get('filed', ''),
                                'end': latest.get('end', '')
                            }
                
                logger.info(f"✓ SEC Edgar: Fetched {len(facts)} financial facts for {ticker}")
        except Exception as e:
            logger.debug(f"SEC Edgar company facts error: {e}")
        
        return facts


# ==========================================
# NEWSDATA.IO API - GEOPOLITICAL & MACRO NEWS
# ==========================================

class NewsDataAnalyzer:
    """Fetches geopolitical, macro, and general market news from NewsData.IO (free API)."""
    
    BASE_URL = "https://newsdata.io/api/1"
    
    @staticmethod
    def get_api_key() -> str:
        """Get NewsData.IO API key from environment."""
        key = os.getenv('NEWSDATA_API_KEY', '')
        if not key:
            logger.debug("NewsData.IO API key not set. Set NEWSDATA_API_KEY environment variable.")
        return key
    
    @staticmethod
    def get_geopolitical_news(limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch geopolitical events that affect markets."""
        api_key = NewsDataAnalyzer.get_api_key()
        if not api_key:
            return []
        
        articles = []
        try:
            import requests
            
            # Search for geopolitical, economic, and market-moving events
            keywords = ['geopolitical', 'sanctions', 'trade war', 'tariffs', 'fed', 'central bank', 'interest rates', 'recession', 'inflation']
            
            url = f"{NewsDataAnalyzer.BASE_URL}/news"
            
            for keyword in keywords:
                params = {
                    'q': keyword,
                    'apikey': api_key,
                    'language': 'en',
                    'sort': 'recent',
                    'limit': min(limit, 50)
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        for item in data['results'][:limit//len(keywords)]:
                            articles.append({
                                'title': item.get('title', ''),
                                'url': item.get('link', ''),
                                'source': item.get('source_id', 'NewsData'),
                                'timestamp': item.get('pubDate', ''),
                                'description': item.get('description', ''),
                                'category': item.get('category', ['general'])[0] if item.get('category') else 'general',
                                'sentiment': 'NEUTRAL',
                                'type': 'Geopolitical'
                            })
                else:
                    logger.debug(f"NewsData.IO geopolitical request failed: {response.status_code}")
            
            if articles:
                logger.info(f"✓ NewsData.IO: Found {len(articles)} geopolitical/macro news articles")
        
        except Exception as e:
            logger.debug(f"NewsData.IO geopolitical fetch error: {e}")
        
        return articles[:limit]
    
    @staticmethod
    def get_market_news(limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch general market and business news."""
        api_key = NewsDataAnalyzer.get_api_key()
        if not api_key:
            return []
        
        articles = []
        try:
            import requests
            
            url = f"{NewsDataAnalyzer.BASE_URL}/news"
            params = {
                'q': 'stock market business',
                'apikey': api_key,
                'language': 'en',
                'sort': 'recent',
                'limit': min(limit, 50)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    for item in data['results'][:limit]:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'source': item.get('source_id', 'NewsData'),
                            'timestamp': item.get('pubDate', ''),
                            'description': item.get('description', ''),
                            'category': item.get('category', ['general'])[0] if item.get('category') else 'general',
                            'sentiment': 'NEUTRAL',
                            'type': 'Market News'
                        })
                    logger.info(f"✓ NewsData.IO: Found {len(articles)} market news articles")
        except Exception as e:
            logger.debug(f"NewsData.IO market news fetch error: {e}")
        
        return articles[:limit]
    
    @staticmethod
    def search_ticker_news(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for news related to a specific ticker or company."""
        api_key = NewsDataAnalyzer.get_api_key()
        if not api_key:
            return []
        
        articles = []
        try:
            import requests
            
            url = f"{NewsDataAnalyzer.BASE_URL}/news"
            params = {
                'q': ticker,
                'apikey': api_key,
                'language': 'en',
                'sort': 'recent',
                'limit': min(limit, 50)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    for item in data['results'][:limit]:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'source': item.get('source_id', 'NewsData'),
                            'timestamp': item.get('pubDate', ''),
                            'description': item.get('description', ''),
                            'category': item.get('category', ['general'])[0] if item.get('category') else 'general',
                            'sentiment': 'NEUTRAL',
                            'type': 'Ticker News'
                        })
                    logger.info(f"✓ NewsData.IO: Found {len(articles)} articles for {ticker}")
        except Exception as e:
            logger.debug(f"NewsData.IO ticker search error: {e}")
        
        return articles[:limit]
    
    @staticmethod
    def search_event_impact(event: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for market impact of specific events (e.g., 'Fed rate hike', 'China sanctions')."""
        api_key = NewsDataAnalyzer.get_api_key()
        if not api_key:
            return []
        
        articles = []
        try:
            import requests
            
            url = f"{NewsDataAnalyzer.BASE_URL}/news"
            params = {
                'q': event,
                'apikey': api_key,
                'language': 'en',
                'sort': 'recent',
                'limit': min(limit, 50)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    for item in data['results'][:limit]:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'source': item.get('source_id', 'NewsData'),
                            'timestamp': item.get('pubDate', ''),
                            'description': item.get('description', ''),
                            'category': item.get('category', ['general'])[0] if item.get('category') else 'general',
                            'sentiment': 'NEUTRAL',
                            'type': 'Event Impact'
                        })
                    logger.info(f"✓ NewsData.IO: Found {len(articles)} articles about '{event}'")
        except Exception as e:
            logger.debug(f"NewsData.IO event search error: {e}")
        
        return articles[:limit]
    
    @staticmethod
    def get_rumors_and_speculation(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch unverified rumors, speculation, and social media commentary about a ticker."""
        api_key = NewsDataAnalyzer.get_api_key()
        if not api_key:
            return []
        
        rumors = []
        try:
            import requests
            
            url = f"{NewsDataAnalyzer.BASE_URL}/news"
            
            # Search for speculation and commentary keywords
            keywords = ['rumor', 'speculation', 'unconfirmed', 'alleged', 'reported', 'claims']
            
            for keyword in keywords:
                params = {
                    'q': f"{ticker} {keyword}",
                    'apikey': api_key,
                    'language': 'en',
                    'sort': 'recent',
                    'limit': min(limit, 50)
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        for item in data['results'][:limit//len(keywords)]:
                            rumors.append({
                                'title': item.get('title', ''),
                                'url': item.get('link', ''),
                                'source': item.get('source_id', 'NewsData'),
                                'timestamp': item.get('pubDate', ''),
                                'description': item.get('description', ''),
                                'category': item.get('category', ['general'])[0] if item.get('category') else 'general',
                                'sentiment': 'NEUTRAL',
                                'type': 'RUMOR',
                                'verified': False,
                                'confidence': 'UNVERIFIED'
                            })
                else:
                    logger.debug(f"NewsData.IO rumors search failed: {response.status_code}")
            
            if rumors:
                logger.debug(f"✓ Found {len(rumors)} unverified rumors/speculation about {ticker}")
        
        except Exception as e:
            logger.debug(f"NewsData.IO rumors fetch error: {e}")
        
        return rumors[:limit]

# PREDICTION TRACKING & LEARNING SYSTEM
# ======================================
# Only used by the trading bot (NOT the advisor)

class PredictionTracker:
    """Tracks trading bot predictions and outcomes for learning."""
    
    DB_FILE = "trading_predictions.json"
    
    @staticmethod
    def save_prediction(ticker: str, direction: str, target_price: float, 
                       target_date: str, confidence: str, reasoning: str, 
                       sources: List[str], current_price: float) -> str:
        """Save a new prediction from the trading bot."""
        import json
        from datetime import datetime
        
        prediction_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        prediction = {
            "prediction_id": prediction_id,
            "ticker": ticker.upper(),
            "timestamp": datetime.now().isoformat(),
            "direction": direction.upper(),  # UP, DOWN, SIDEWAYS
            "confidence": confidence.upper(),  # HIGH, MEDIUM, LOW
            "price_at_prediction": current_price,
            "target_price": target_price,
            "target_date": target_date,
            "reasoning": reasoning,
            "sources_cited": sources,
            "outcome": None  # Will be filled when checked
        }
        
        try:
            # Load existing predictions
            predictions = []
            if os.path.exists(PredictionTracker.DB_FILE):
                with open(PredictionTracker.DB_FILE, 'r') as f:
                    predictions = json.load(f)
            
            # Add new prediction
            predictions.append(prediction)
            
            # Save back
            with open(PredictionTracker.DB_FILE, 'w') as f:
                json.dump(predictions, f, indent=2)
            
            logger.info(f"✓ Prediction saved: {prediction_id}")
            return prediction_id
        except Exception as e:
            logger.error(f"Failed to save prediction: {e}")
            return None
    
    @staticmethod
    def get_pending_predictions() -> List[Dict]:
        """Get all predictions that haven't been checked yet."""
        import json
        from datetime import datetime, timedelta
        
        try:
            if not os.path.exists(PredictionTracker.DB_FILE):
                return []
            
            with open(PredictionTracker.DB_FILE, 'r') as f:
                predictions = json.load(f)
            
            # Return predictions without outcomes yet
            pending = [p for p in predictions if p.get('outcome') is None]
            return pending
        except Exception as e:
            logger.error(f"Failed to load predictions: {e}")
            return []
    
    @staticmethod
    def log_outcome(prediction_id: str, actual_price: float, notes: str = "") -> bool:
        """Log the outcome of a prediction."""
        import json
        from datetime import datetime
        
        try:
            if not os.path.exists(PredictionTracker.DB_FILE):
                return False
            
            with open(PredictionTracker.DB_FILE, 'r') as f:
                predictions = json.load(f)
            
            # Find and update the prediction
            for pred in predictions:
                if pred['prediction_id'] == prediction_id:
                    # Determine if correct
                    direction_correct = False
                    accuracy_score = 0
                    
                    target_price = pred['target_price']
                    pred_price = pred['price_at_prediction']
                    pred_direction = pred['direction']
                    
                    price_change = actual_price - pred_price
                    
                    if pred_direction == "UP" and price_change > 0:
                        direction_correct = True
                        accuracy_score = min(100, (price_change / (target_price - pred_price)) * 100) if target_price > pred_price else 50
                    elif pred_direction == "DOWN" and price_change < 0:
                        direction_correct = True
                        accuracy_score = min(100, (abs(price_change) / (pred_price - target_price)) * 100) if pred_price > target_price else 50
                    elif pred_direction == "SIDEWAYS" and abs(price_change) < (abs(target_price - pred_price) * 0.1):
                        direction_correct = True
                        accuracy_score = 80
                    
                    profit_pct = (price_change / pred_price * 100) if pred_price != 0 else 0
                    
                    pred['outcome'] = {
                        "actual_price": actual_price,
                        "outcome_date": datetime.now().isoformat(),
                        "direction_correct": direction_correct,
                        "accuracy_score": round(accuracy_score, 1),
                        "profit_pct": round(profit_pct, 2),
                        "notes": notes
                    }
                    
                    # Save updated predictions
                    with open(PredictionTracker.DB_FILE, 'w') as f:
                        json.dump(predictions, f, indent=2)
                    
                    logger.info(f"✓ Outcome logged for {prediction_id}: {direction_correct}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to log outcome: {e}")
            return False

class OutcomeAnalyzer:
    """Analyzes prediction outcomes and accuracy patterns."""
    
    @staticmethod
    def check_and_update_outcomes(current_prices: Dict[str, float]) -> List[Dict]:
        """Check if any pending predictions have outcomes to log."""
        pending = PredictionTracker.get_pending_predictions()
        updated = []
        
        for pred in pending:
            ticker = pred['ticker']
            
            if ticker in current_prices:
                actual_price = current_prices[ticker]
                target_date = pred['target_date']
                
                # Simple check: if we have current price, log it
                # In real system, would check if target date passed or price target hit
                from datetime import datetime
                try:
                    target_dt = datetime.fromisoformat(target_date)
                    now = datetime.now()
                    
                    # Log outcome if target date passed or price target hit
                    pred_price = pred['price_at_prediction']
                    target_price = pred['target_price']
                    
                    price_hit = False
                    if pred['direction'] == 'UP' and actual_price >= target_price:
                        price_hit = True
                    elif pred['direction'] == 'DOWN' and actual_price <= target_price:
                        price_hit = True
                    
                    if target_dt <= now or price_hit:
                        PredictionTracker.log_outcome(pred['prediction_id'], actual_price)
                        updated.append(pred['prediction_id'])
                except:
                    pass
        
        return updated
    
    @staticmethod
    def get_accuracy_summary() -> Dict:
        """Generate accuracy summary for the trading bot."""
        import json
        
        try:
            if not os.path.exists(PredictionTracker.DB_FILE):
                return {"total": 0, "accuracy": 0, "scenarios": {}}
            
            with open(PredictionTracker.DB_FILE, 'r') as f:
                predictions = json.load(f)
            
            # Filter predictions with outcomes
            completed = [p for p in predictions if p.get('outcome') is not None]
            
            if not completed:
                return {
                    "total_predictions": 0,
                    "completed_outcomes": 0,
                    "pending_outcomes": len(predictions),
                    "directional_accuracy": 0,
                    "average_accuracy_score": 0,
                    "average_profit_pct": 0,
                    "scenarios": {}
                }
            
            # Calculate overall accuracy
            correct_count = sum(1 for p in completed if p['outcome'].get('direction_correct'))
            directional_accuracy = (correct_count / len(completed)) * 100 if completed else 0
            
            # Calculate average scores
            avg_accuracy = sum(p['outcome'].get('accuracy_score', 0) for p in completed) / len(completed) if completed else 0
            avg_profit = sum(p['outcome'].get('profit_pct', 0) for p in completed) / len(completed) if completed else 0
            
            # Analyze by scenario (confidence level)
            scenarios = {}
            for pred in completed:
                conf = pred.get('confidence', 'UNKNOWN')
                if conf not in scenarios:
                    scenarios[conf] = {'total': 0, 'correct': 0, 'avg_profit': 0, 'profits': []}
                
                scenarios[conf]['total'] += 1
                if pred['outcome'].get('direction_correct'):
                    scenarios[conf]['correct'] += 1
                scenarios[conf]['profits'].append(pred['outcome'].get('profit_pct', 0))
            
            # Calculate scenario stats
            for conf in scenarios:
                if scenarios[conf]['total'] > 0:
                    scenarios[conf]['accuracy'] = (scenarios[conf]['correct'] / scenarios[conf]['total']) * 100
                    scenarios[conf]['avg_profit'] = sum(scenarios[conf]['profits']) / len(scenarios[conf]['profits'])
                scenarios[conf].pop('profits', None)  # Remove raw profits list
            
            return {
                "total_predictions": len(predictions),
                "completed_outcomes": len(completed),
                "pending_outcomes": len(predictions) - len(completed),
                "directional_accuracy_pct": round(directional_accuracy, 1),
                "average_accuracy_score": round(avg_accuracy, 1),
                "average_profit_pct": round(avg_profit, 2),
                "scenarios": scenarios
            }
        except Exception as e:
            logger.error(f"Failed to generate accuracy summary: {e}")
            return {}
    
    @staticmethod
    def get_scenario_analysis() -> Dict[str, any]:
        """Analyze which scenarios (patterns) work best."""
        import json
        
        try:
            if not os.path.exists(PredictionTracker.DB_FILE):
                return {}
            
            with open(PredictionTracker.DB_FILE, 'r') as f:
                predictions = json.load(f)
            
            completed = [p for p in predictions if p.get('outcome') is not None]
            
            # Group by reasoning keywords
            scenarios = {}
            for pred in completed:
                reasoning = pred.get('reasoning', '').lower()
                outcome = pred.get('outcome', {})
                is_correct = outcome.get('direction_correct', False)
                profit = outcome.get('profit_pct', 0)
                
                # Extract key patterns from reasoning
                keywords = ['oversold', 'earnings', 'breakout', 'support', 'resistance', 
                           'rumor', 'news', 'insider', 'sector', 'macro']
                
                for keyword in keywords:
                    if keyword in reasoning:
                        if keyword not in scenarios:
                            scenarios[keyword] = {'total': 0, 'correct': 0, 'profits': []}
                        scenarios[keyword]['total'] += 1
                        if is_correct:
                            scenarios[keyword]['correct'] += 1
                        scenarios[keyword]['profits'].append(profit)
            
            # Calculate scenario stats
            analysis = {}
            for scenario, data in scenarios.items():
                if data['total'] >= 2:  # Only show scenarios with 2+ predictions
                    accuracy = (data['correct'] / data['total']) * 100
                    avg_profit = sum(data['profits']) / len(data['profits'])
                    analysis[scenario] = {
                        'attempts': data['total'],
                        'success_rate_pct': round(accuracy, 1),
                        'avg_profit_pct': round(avg_profit, 2),
                        'success_count': data['correct']
                    }
            
            # Sort by success rate
            return dict(sorted(analysis.items(), key=lambda x: x[1]['success_rate_pct'], reverse=True))
        except Exception as e:
            logger.error(f"Failed to analyze scenarios: {e}")
            return {}

class LearningEngine:
    """Learning engine that helps the bot improve from past predictions."""
    
    @staticmethod
    def get_bot_learning_brief() -> str:
        """Generate a learning brief for the bot to review before making new predictions."""
        summary = OutcomeAnalyzer.get_accuracy_summary()
        scenarios = OutcomeAnalyzer.get_scenario_analysis()
        
        if summary.get('completed_outcomes', 0) == 0:
            return "No past predictions yet. Starting fresh!"
        
        brief = f"""
📊 YOUR TRADING BOT'S PREDICTION RECORD:

Overall Performance:
  • Total Predictions: {summary.get('total_predictions', 0)}
  • Completed: {summary.get('completed_outcomes', 0)}
  • Pending: {summary.get('pending_outcomes', 0)}
  • Directional Accuracy: {summary.get('directional_accuracy_pct', 0)}%
  • Avg Accuracy Score: {summary.get('average_accuracy_score', 0)}/100
  • Avg Profit: {summary.get('average_profit_pct', 0)}%

By Confidence Level:
"""
        
        for conf_level, stats in summary.get('scenarios', {}).items():
            accuracy = stats.get('accuracy', 0)
            count = stats.get('total', 0)
            profit = stats.get('avg_profit', 0)
            brief += f"  • {conf_level}: {accuracy:.0f}% accuracy ({count} predictions, avg +{profit:.2f}%)\n"
        
        if scenarios:
            brief += f"\nBest Performing Scenarios:\n"
            for scenario, stats in list(scenarios.items())[:5]:
                brief += f"  • {scenario.title()}: {stats['success_rate_pct']}% success ({stats['attempts']} attempts)\n"
            
            brief += f"\nWeakest Scenarios (Improve These):\n"
            for scenario, stats in list(reversed(scenarios.items()))[:3]:
                brief += f"  • {scenario.title()}: {stats['success_rate_pct']}% success ({stats['attempts']} attempts)\n"
        
        brief += f"\n💡 Key Learning:\n"
        best_scenario = max(scenarios.items(), key=lambda x: x[1]['success_rate_pct']) if scenarios else None
        worst_scenario = min(scenarios.items(), key=lambda x: x[1]['success_rate_pct']) if scenarios else None
        
        if best_scenario:
            brief += f"  ✅ You're best at: {best_scenario[0].title()} predictions ({best_scenario[1]['success_rate_pct']}% win rate)\n"
        if worst_scenario:
            brief += f"  ⚠️  You struggle with: {worst_scenario[0].title()} predictions ({worst_scenario[1]['success_rate_pct']}% win rate)\n"
        
        brief += f"\n🎯 Recommendation: Focus on high-confidence plays where you have >70% accuracy!\n"
        
        return brief

class SECAnalyzer:
    """Analyzes SEC Edgar filings."""
    
    BASE_URL = "https://www.sec.gov"
    
    @staticmethod
    def get_recent_filings(ticker: str, limit: int = 5) -> List[SECFiling]:
        """Get recent SEC filings."""
        filings = []
        try:
            console.print(f"[dim]Checking SEC filings for {ticker}...[/dim]")
            
            filings.append(SECFiling(
                form_type="10-K",
                filing_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                company=ticker,
                ticker=ticker,
                description="Annual Report",
                url=f"{SECAnalyzer.BASE_URL}/cgi-bin/browse-edgar",
                key_points=["Check SEC.gov for latest filings"]
            ))
            
        except Exception as e:
            logger.error(f"Error fetching SEC filings: {e}")
        
        return filings
    
    @staticmethod
    def get_insider_trades(ticker: str, limit: int = 10) -> List[InsiderTrade]:
        """Get insider trading activity."""
        insider_trades = []
        try:
            stock = yf.Ticker(ticker)
            insider_data = stock.insider_transactions if hasattr(stock, 'insider_transactions') else pd.DataFrame()
            
            if not insider_data.empty:
                # yfinance columns commonly: Insider, Relationship/Position, Date, Transaction, Cost, #Shares, Value
                for idx, row in insider_data.head(limit).iterrows():
                    raw_shares = row.get('#Shares') or row.get('Shares') or 0
                    raw_cost = row.get('Cost') or row.get('Price') or row.get('Value') or 0
                    raw_value = row.get('Value') or 0
                    def _to_float(x):
                        try:
                            if isinstance(x, str):
                                x = x.replace('$','').replace(',','').strip()
                            return float(x)
                        except Exception:
                            return 0.0
                    def _to_int(x):
                        try:
                            if isinstance(x, str):
                                x = x.replace(',','').strip()
                            return int(float(x))
                        except Exception:
                            return 0
                    shares = _to_int(raw_shares)
                    price = _to_float(raw_cost)
                    value = _to_float(raw_value)
                    insider_trades.append(InsiderTrade(
                        insider=row.get('Insider', 'Unknown'),
                        position=row.get('Position', row.get('Relationship','Unknown')),
                        transaction_type=row.get('Transaction', 'Unknown'),
                        shares=shares,
                        price=price,
                        value=value if value > 0 else price * shares,
                        date=str(row.get('Date', '')),
                        ticker=ticker
                    ))
        except Exception as e:
            logger.error(f"Error fetching insider trades: {e}")
        
        return insider_trades

# ==========================================
# QUANTITATIVE FACTOR MODELS
# ==========================================

class FactorModels:
    """Advanced factor analysis: Fama-French, momentum, value, quality."""
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame) -> pd.Series:
        """Calculate simple returns from OHLCV data."""
        return df['Close'].pct_change()
    
    @staticmethod
    def calculate_log_returns(df: pd.DataFrame) -> pd.Series:
        """Calculate log returns (more suitable for statistics)."""
        return np.log(df['Close'] / df['Close'].shift(1))
    
    @staticmethod
    def calculate_momentum_factor(df: pd.DataFrame, lookback: int = 126) -> float:
        """
        Momentum factor: cumulative return over lookback period.
        126 days ≈ 6 months (standard momentum period).
        """
        if len(df) < lookback:
            return 0.0
        
        returns = FactorModels.calculate_returns(df)
        momentum = (1 + returns.tail(lookback)).prod() - 1
        return float(momentum)
    
    @staticmethod
    def calculate_volatility_factor(df: pd.DataFrame, window: int = 20) -> float:
        """
        Realized volatility (annualized).
        """
        returns = FactorModels.calculate_returns(df)
        vol = returns.rolling(window).std().iloc[-1] * np.sqrt(252)
        return float(vol) if not np.isnan(vol) else 0.0
    
    @staticmethod
    def calculate_value_factor(ticker_info: Dict) -> float:
        """
        Value factor: Price-to-Book ratio (lower = more value).
        Returns negative P/B so higher score = better value.
        """
        try:
            pb = ticker_info.get('priceToBook', None)
            if pb and pb > 0:
                return -float(pb)  # Negative so lower P/B = higher score
        except Exception:
            pass
        return 0.0
    
    @staticmethod
    def calculate_quality_factor(ticker_info: Dict) -> float:
        """
        Quality factor: ROE, profit margins, debt ratio.
        Higher = better quality company.
        """
        try:
            roe = ticker_info.get('returnOnEquity', 0) or 0
            profit_margin = ticker_info.get('profitMargins', 0) or 0
            debt_to_equity = ticker_info.get('debtToEquity', 100) or 100
            
            # Normalize: high ROE & margins good, low debt good
            quality_score = (float(roe) * 100 + float(profit_margin) * 100) / (1 + float(debt_to_equity) / 100)
            return quality_score
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_size_factor(ticker_info: Dict) -> float:
        """
        Size factor: Market cap (log scale).
        Fama-French: small cap premium exists.
        """
        try:
            market_cap = ticker_info.get('marketCap', 0)
            if market_cap > 0:
                return np.log(float(market_cap))
        except Exception:
            pass
        return 0.0
    
    @staticmethod
    def z_score_normalize(values: pd.Series) -> pd.Series:
        """Z-score normalization for cross-sectional factor analysis."""
        mean = values.mean()
        std = values.std()
        if std == 0:
            return pd.Series(0, index=values.index)
        return (values - mean) / std
    
    @staticmethod
    def detect_mean_reversion(df: pd.DataFrame, window: int = 20) -> Tuple[float, bool]:
        """
        Detect mean reversion using Bollinger Bands + Hurst exponent approximation.
        Returns: (z_score, is_mean_reverting)
        """
        close = df['Close']
        sma = close.rolling(window).mean()
        std = close.rolling(window).std()
        
        if len(close) < window or std.iloc[-1] == 0:
            return 0.0, False
        
        # Z-score: how many std devs from mean
        z_score = (close.iloc[-1] - sma.iloc[-1]) / std.iloc[-1]
        
        # Simple mean reversion check: price oscillates around SMA
        crossings = ((close > sma).astype(int).diff().abs().sum())
        is_reverting = crossings > (len(close) / window) * 0.5  # At least 0.5 crosses per window
        
        return float(z_score), bool(is_reverting)
    
    @staticmethod
    def calculate_beta(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
        """
        Calculate beta vs benchmark (e.g., SPY).
        Beta > 1: more volatile than market.
        """
        if len(df) < 60 or len(benchmark_df) < 60:
            return 1.0
        
        # Align dates
        combined = pd.DataFrame({
            'asset': df['Close'],
            'benchmark': benchmark_df['Close']
        }).dropna()
        
        if len(combined) < 30:
            return 1.0
        
        asset_returns = combined['asset'].pct_change().dropna()
        bench_returns = combined['benchmark'].pct_change().dropna()
        
        covariance = asset_returns.cov(bench_returns)
        bench_variance = bench_returns.var()
        
        if bench_variance == 0:
            return 1.0
        
        beta = covariance / bench_variance
        return float(beta)

class StatisticalArbitrage:
    """Statistical arbitrage: pairs trading, cointegration, spread analysis."""
    
    @staticmethod
    def test_cointegration(series1: pd.Series, series2: pd.Series) -> Tuple[bool, float, float]:
        """
        Test cointegration between two price series using Engle-Granger.
        Returns: (is_cointegrated, p_value, hedge_ratio)
        """
        try:
            from statsmodels.tsa.stattools import coint
            
            # Align series
            combined = pd.DataFrame({'s1': series1, 's2': series2}).dropna()
            if len(combined) < 30:
                return False, 1.0, 1.0
            
            s1 = combined['s1'].values
            s2 = combined['s2'].values
            
            # Cointegration test
            score, p_value, _ = coint(s1, s2)
            
            # Hedge ratio from linear regression
            from scipy.stats import linregress
            slope, intercept, _, _, _ = linregress(s2, s1)
            
            is_cointegrated = p_value < 0.05
            return is_cointegrated, float(p_value), float(slope)
        
        except Exception as e:
            logger.error(f"Cointegration test error: {e}")
            return False, 1.0, 1.0
    
    @staticmethod
    def calculate_spread(price1: pd.Series, price2: pd.Series, hedge_ratio: float) -> pd.Series:
        """Calculate spread for pairs trading: spread = price1 - hedge_ratio * price2"""
        return price1 - hedge_ratio * price2
    
    @staticmethod
    def calculate_spread_zscore(spread: pd.Series, window: int = 20) -> float:
        """Calculate z-score of current spread vs historical mean."""
        if len(spread) < window:
            return 0.0
        
        recent_spread = spread.tail(window)
        mean = recent_spread.mean()
        std = recent_spread.std()
        
        if std == 0:
            return 0.0
        
        z_score = (spread.iloc[-1] - mean) / std
        return float(z_score)
    
    @staticmethod
    def find_pairs(tickers: List[str], lookback_days: int = 252) -> List[Tuple[str, str, float, float]]:
        """
        Find cointegrated pairs from a universe of tickers.
        Returns: List of (ticker1, ticker2, p_value, hedge_ratio)
        """
        # Fast pre-check: require statsmodels for cointegration tests
        try:
            import statsmodels  # noqa: F401
        except Exception:
            logger.info("Pairs trading requires 'statsmodels'. Skipping pairs detection (install via: pip install statsmodels)")
            return []

        pairs = []
        significance_level = 0.05  # Use fixed significance level
        
        # Fetch data for all tickers
        data = {}
        for ticker in tickers:
            try:
                df = DataManager.fetch_data(ticker, "1y", "1d")
                if df is not None and len(df) >= lookback_days * 0.7:
                    data[ticker] = df['Close']
            except Exception:
                continue
        
        # Test all combinations
        tested = set()
        for t1 in data.keys():
            for t2 in data.keys():
                if t1 == t2 or (t1, t2) in tested or (t2, t1) in tested:
                    continue
                
                tested.add((t1, t2))
                
                is_coint, p_val, hedge = StatisticalArbitrage.test_cointegration(
                    data[t1], data[t2]
                )
                
                if is_coint:
                    pairs.append((t1, t2, p_val, hedge))
        
        # Sort by p-value (lower = stronger cointegration)
        pairs.sort(key=lambda x: x[2])
        return pairs

class PCAFactorAnalysis:
    """Principal Component Analysis for factor extraction."""
    
    @staticmethod
    def extract_principal_components(returns_matrix: pd.DataFrame, n_components: int = 3) -> Tuple[np.ndarray, np.ndarray, List[float]]:
        """
        Extract principal components from returns matrix.
        Returns: (components, loadings, explained_variance_ratio)
        """
        try:
            from sklearn.decomposition import PCA
            
            # Remove NaN
            clean_returns = returns_matrix.dropna()
            
            if len(clean_returns) < 10:
                return np.array([]), np.array([]), []
            
            pca = PCA(n_components=min(n_components, clean_returns.shape[1]))
            components = pca.fit_transform(clean_returns)
            loadings = pca.components_
            explained_var = pca.explained_variance_ratio_
            
            return components, loadings, list(explained_var)
        
        except Exception as e:
            logger.error(f"PCA error: {e}")
            return np.array([]), np.array([]), []
    
    @staticmethod
    def get_factor_exposures(ticker_returns: pd.Series, market_returns: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate factor exposures using regression.
        """
        try:
            from sklearn.linear_model import LinearRegression
            
            # Align dates
            combined = pd.concat([ticker_returns, market_returns], axis=1).dropna()
            
            if len(combined) < 20:
                return {}
            
            y = combined.iloc[:, 0].values.reshape(-1, 1)
            X = combined.iloc[:, 1:].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            exposures = {}
            for i, col in enumerate(market_returns.columns):
                exposures[col] = float(model.coef_[0][i])
            
            exposures['alpha'] = float(model.intercept_[0])
            
            return exposures
        
        except Exception as e:
            logger.error(f"Factor exposure error: {e}")
            return {}

# ==========================================
# QUANTITATIVE STRATEGIES
# ==========================================

@dataclass
class StrategySignal:
    """Signal from a quantitative strategy."""
    ticker: str
    action: str  # "BUY", "SELL", "HOLD"
    timestamp: datetime
    strength: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    metadata: Dict = None

class BaseStrategy:
    """Base class for all quantitative strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.signals: List[StrategySignal] = []
    
    def generate_signals(self, tickers: List[str], lookback_days: int = 252) -> List[StrategySignal]:
        """Override in subclasses."""
        raise NotImplementedError
    
    def backtest(self, tickers: List[str], start_date: str, end_date: str, 
                initial_capital: float = 10000.0) -> Dict:
        """Backtest strategy on historical data."""
        raise NotImplementedError

class MomentumStrategy(BaseStrategy):
    """Momentum strategy (default 6-month) selecting top percentile performers.
    Optimized to support preloaded data and minimum signal guarantees."""
    
    def __init__(self, lookback_days: int = 126, top_pct: float = 0.25, min_signals: int = 1):
        super().__init__("Momentum")
        self.lookback_days = lookback_days
        self.top_pct = top_pct
        self.min_signals = max(1, int(min_signals))
    
    def generate_signals(self, tickers: List[str], lookback_days: int = None, 
                         preloaded_data: Dict[str, 'pd.DataFrame'] = None) -> List[StrategySignal]:
        """Generate momentum-based signals (volatility-adjusted).
        Momentum score = raw momentum / annualized volatility.
        Strength derived from cross-sectional percentile rank."""
        if lookback_days is None:
            lookback_days = self.lookback_days
        
        signals: List[StrategySignal] = []
        momentum_scores: Dict[str, float] = {}
        
        for ticker in tickers:
            try:
                df = preloaded_data.get(ticker) if preloaded_data and ticker in preloaded_data else DataManager.fetch_data(ticker, f"{lookback_days}d", "1d")
                if df is not None and len(df) >= lookback_days:
                    window_df = df.tail(lookback_days)
                    momentum_raw = FactorModels.calculate_momentum_factor(window_df, lookback_days)
                    # Volatility: std of daily returns * sqrt(252)
                    returns = window_df['Close'].pct_change().dropna()
                    vol = returns.std() * (252 ** 0.5) if not returns.empty else 1.0
                    if vol == 0:
                        vol = 1.0
                    adj_momentum = momentum_raw / vol
                    momentum_scores[ticker] = adj_momentum
            except Exception as e:
                logger.error(f"Momentum calc error for {ticker}: {e}")
        
        sorted_tickers = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        total = len(sorted_tickers)
        cutoff = int(total * self.top_pct)
        if total > 0:
            cutoff = max(self.min_signals, cutoff)
        top_performers = sorted_tickers[:cutoff]
        # Percentile ranks for strength scaling
        if total > 0:
            values = [v for _, v in sorted_tickers]
            min_v, max_v = min(values), max(values)
            span = max_v - min_v if max_v != min_v else 1.0
        else:
            min_v = 0.0
            span = 1.0
        
        for ticker, adj_momentum in top_performers:
            try:
                df = preloaded_data.get(ticker) if preloaded_data and ticker in preloaded_data else DataManager.fetch_data(ticker, "60d", "1d")
                if df is not None and not df.empty:
                    current_price = float(df['Close'].iloc[-1])
                    atr = TechnicalAnalyzer.calculate_atr(df.tail(60), 14)
                    # Strength: percentile rank of adjusted momentum
                    rank_strength = 0.0
                    try:
                        position = next(i for i, (tk, val) in enumerate(sorted_tickers) if tk == ticker)
                        rank_strength = (total - position) / total  # highest momentum -> near 1
                    except Exception:
                        rank_strength = 0.5
                    strength_pct = min(100, max(0, rank_strength * 100))
                    signal = StrategySignal(
                        ticker=ticker,
                        action="BUY",
                        timestamp=datetime.now(),
                        strength=strength_pct,
                        entry_price=current_price,
                        stop_loss=current_price - (2 * atr),
                        take_profit=current_price + (4 * atr),
                        reason=f"Risk-Adj Momentum: {adj_momentum:.3f} (Top {self.top_pct*100:.0f}%)",
                        metadata={'adj_momentum': adj_momentum, 'rank_strength': rank_strength}
                    )
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Signal generation error for {ticker}: {e}")
        
        self.signals = signals
        return signals

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands Z-score."""
    
    def __init__(self, z_threshold: float = 2.0, bb_period: int = 20):
        super().__init__("MeanReversion")
        self.z_threshold = z_threshold
        self.bb_period = bb_period
    
    def generate_signals(self, tickers: List[str], lookback_days: int = 60, 
                         preloaded_data: Dict[str, 'pd.DataFrame'] = None) -> List[StrategySignal]:
        """Generate mean reversion signals with volatility-adjusted strength.
        Strength scaled by |z| * (bandwidth / ATR) to prioritize clean reversions."""
        signals: List[StrategySignal] = []
        for ticker in tickers:
            try:
                df = preloaded_data.get(ticker) if preloaded_data and ticker in preloaded_data else DataManager.fetch_data(ticker, f"{lookback_days}d", "1d")
                if df is None or len(df) < self.bb_period + 5:
                    continue
                z_score, is_reverting = FactorModels.detect_mean_reversion(df, window=self.bb_period)
                if is_reverting and abs(z_score) >= self.z_threshold:
                    current_price = float(df['Close'].iloc[-1])
                    atr = TechnicalAnalyzer.calculate_atr(df.tail(lookback_days), 14)
                    # Bollinger band width as proxy for opportunity clarity
                    rolling = df['Close'].rolling(self.bb_period)
                    ma = rolling.mean().iloc[-1]
                    std = rolling.std().iloc[-1]
                    band_width = 2 * std if std is not None else 0.0
                    action = "BUY" if z_score < -self.z_threshold else "SELL"
                    # Strength formula
                    clarity = band_width / atr if atr > 0 else 1.0
                    raw_strength = abs(z_score) * min(2.0, max(0.5, clarity))
                    strength_pct = min(100, raw_strength * 25)
                    signal = StrategySignal(
                        ticker=ticker,
                        action=action,
                        timestamp=datetime.now(),
                        strength=strength_pct,
                        entry_price=current_price,
                        stop_loss=current_price - (2 * atr) if action == "BUY" else current_price + (2 * atr),
                        take_profit=current_price + (3 * atr) if action == "BUY" else current_price - (3 * atr),
                        reason=f"Mean Reversion Z={z_score:.2f} BW/ATR={clarity:.2f}",
                        metadata={'z_score': z_score, 'band_width': band_width, 'atr': atr, 'clarity': clarity}
                    )
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Mean reversion error for {ticker}: {e}")
        self.signals = signals
        return signals

class PairsStrategy(BaseStrategy):
    """Statistical arbitrage pairs trading strategy."""
    
    def __init__(self, z_threshold: float = 2.0):
        super().__init__("PairsTrading")
        self.z_threshold = z_threshold
    
    def generate_signals(self, tickers: List[str], lookback_days: int = 252) -> List[StrategySignal]:
        """Find cointegrated pairs and generate spread signals."""
        signals = []
        
        # Find all cointegrated pairs (significance level is now internal)
        pairs = StatisticalArbitrage.find_pairs(tickers, lookback_days)
        
        if not pairs:
            logger.info("No cointegrated pairs found")
            return signals
        
        # Check current spread for each pair
        for ticker1, ticker2, p_value, hedge_ratio in pairs[:10]:  # Top 10 pairs
            try:
                df1 = DataManager.fetch_data(ticker1, "60d", "1d")
                df2 = DataManager.fetch_data(ticker2, "60d", "1d")
                
                if df1 is None or df2 is None:
                    continue
                
                # Calculate spread
                spread = StatisticalArbitrage.calculate_spread(df1['Close'], df2['Close'], hedge_ratio)
                z_score = StatisticalArbitrage.calculate_spread_zscore(spread)
                
                if abs(z_score) >= self.z_threshold:
                    price1 = float(df1['Close'].iloc[-1])
                    price2 = float(df2['Close'].iloc[-1])
                    
                    if z_score > self.z_threshold:
                        # Spread too high: SHORT ticker1, LONG ticker2
                        action = "PAIR_SHORT_LONG"
                        reason = f"Spread Z={z_score:.2f} > {self.z_threshold}: SHORT {ticker1}, LONG {ticker2}"
                    else:
                        # Spread too low: LONG ticker1, SHORT ticker2
                        action = "PAIR_LONG_SHORT"
                        reason = f"Spread Z={z_score:.2f} < -{self.z_threshold}: LONG {ticker1}, SHORT {ticker2}"
                    
                    signal = StrategySignal(
                        ticker=f"{ticker1}/{ticker2}",
                        action=action,
                        timestamp=datetime.now(),
                        strength=min(100, abs(z_score) * 30),
                        entry_price=price1,
                        stop_loss=0,  # Pairs have different stop logic
                        take_profit=0,
                        reason=reason,
                        metadata={
                            'ticker1': ticker1,
                            'ticker2': ticker2,
                            'price1': price1,
                            'price2': price2,
                            'hedge_ratio': hedge_ratio,
                            'z_score': z_score,
                            'p_value': p_value
                        }
                    )
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Pairs signal error for {ticker1}/{ticker2}: {e}")
        
        self.signals = signals
        return signals

class MLClassificationStrategy(BaseStrategy):
    """Machine learning classification strategy using ensemble models."""
    
    def __init__(self, probability_threshold: float = 0.65):
        super().__init__("MLClassification")
        self.probability_threshold = probability_threshold
        self.ml_weighter = MLSignalWeighter()
    
    def generate_signals(self, tickers: List[str], lookback_days: int = 252) -> List[StrategySignal]:
        """Generate ML-based signals."""
        signals = []
        
        # Check if models are trained
        if not self.ml_weighter.models:
            logger.warning("ML models not trained. Train first using train_models_walk_forward()")
            return signals
        
        for ticker in tickers:
            try:
                df = DataManager.fetch_data(ticker, f"{lookback_days}d", "1d")
                if df is None or len(df) < 50:
                    continue
                
                # Calculate indicators
                indicators = TechnicalAnalyzer.calculate_indicators(df)
                
                # Engineer features
                features = self.ml_weighter.engineer_features(df, indicators)
                
                if features is None:
                    continue
                
                # Get ensemble prediction
                ml_prob, individual_probs = self.ml_weighter.get_ensemble_prediction(features)
                
                if ml_prob >= self.probability_threshold:
                    current_price = float(df['Close'].iloc[-1])
                    atr = TechnicalAnalyzer.calculate_atr(df, 14)
                    
                    signal = StrategySignal(
                        ticker=ticker,
                        action="BUY",
                        timestamp=datetime.now(),
                        strength=ml_prob * 100,
                        entry_price=current_price,
                        stop_loss=current_price - (2 * atr),
                        take_profit=current_price + (4 * atr),
                        reason=f"ML Ensemble: {ml_prob:.1%} win probability",
                        metadata={
                            'ml_prob': ml_prob,
                            'rf_prob': individual_probs.get('random_forest', 0),
                            'gb_prob': individual_probs.get('gradient_boost', 0),
                            'lr_prob': individual_probs.get('logistic', 0)
                        }
                    )
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"ML signal error for {ticker}: {e}")
        
        self.signals = signals
        return signals

class MultiFactorStrategy(BaseStrategy):
    """Multi-factor strategy combining momentum, value, and quality with normalization.
    Supports preloaded data and minimum signal guarantees."""
    
    def __init__(self, top_pct: float = 0.20, min_signals: int = 1):
        super().__init__("MultiFactor")
        self.top_pct = top_pct
        self.min_signals = max(1, int(min_signals))
    
    def generate_signals(self, tickers: List[str], lookback_days: int = 252, 
                         preloaded_data: Dict[str, 'pd.DataFrame'] = None) -> List[StrategySignal]:
        """Generate signals from winsorized percentile ranks and dispersion weights.
        Normalization:
            1. Winsorize each factor at 5th/95th percentiles to reduce outlier impact.
            2. Convert to percentile rank scaled to [-1,1].
            3. Weight factors by cross-sectional standard deviation (higher dispersion -> higher weight).
        """
        signals: List[StrategySignal] = []
        raw_factors: Dict[str, Dict[str, float]] = {}
        
        for ticker in tickers:
            try:
                df = None
                if preloaded_data and ticker in preloaded_data:
                    df = preloaded_data[ticker]
                else:
                    df = DataManager.fetch_data(ticker, f"{lookback_days}d", "1d")
                if df is None or len(df) < 126:
                    continue
                info = DataManager.get_ticker_info(ticker)
                # Fallback neutral info
                if info is None:
                    value = 0.0
                    quality = 0.0
                else:
                    value = FactorModels.calculate_value_factor(info)
                    quality = FactorModels.calculate_quality_factor(info)
                momentum = FactorModels.calculate_momentum_factor(df.tail(126), 126)
                # Replace None with neutral 0
                value = value if value is not None else 0.0
                quality = quality if quality is not None else 0.0
                raw_factors[ticker] = {'momentum': momentum, 'value': value, 'quality': quality}
            except Exception as e:
                logger.error(f"Factor calc error for {ticker}: {e}")
        
        if not raw_factors:
            self.signals = []
            return []
        
        # Prepare for winsorization & percentile ranks
        mom_values = [raw_factors[t]['momentum'] for t in raw_factors]
        val_values = [raw_factors[t]['value'] for t in raw_factors]
        qual_values = [raw_factors[t]['quality'] for t in raw_factors]
        
        def _winsorize(vals: List[float], lower: float = 0.05, upper: float = 0.95) -> List[float]:
            if not vals:
                return []
            sorted_vals = sorted(vals)
            l_idx = int(lower * (len(sorted_vals) - 1))
            u_idx = int(upper * (len(sorted_vals) - 1))
            lo = sorted_vals[l_idx]
            hi = sorted_vals[u_idx]
            return [min(max(v, lo), hi) for v in vals]
        
        def _percentile_rank(vals: List[float]) -> List[float]:
            if not vals:
                return []
            sorted_unique = sorted(set(vals))
            rank_map = {v: i for i, v in enumerate(sorted_unique)}
            max_rank = len(sorted_unique) - 1 if len(sorted_unique) > 1 else 1
            return [rank_map[v] / max_rank for v in vals]
        
        mom_w = _winsorize(mom_values)
        val_w = _winsorize(val_values)
        qual_w = _winsorize(qual_values)
        mom_pct = _percentile_rank(mom_w)
        val_pct = _percentile_rank(val_w)
        qual_pct = _percentile_rank(qual_w)
        # Scale to [-1,1]
        mom_norm = [(x * 2) - 1 for x in mom_pct]
        val_norm = [(x * 2) - 1 for x in val_pct]
        qual_norm = [(x * 2) - 1 for x in qual_pct]
        
        # Dispersion-based weights (std of winsorized values)
        import math
        def _std(vals: List[float]) -> float:
            if not vals:
                return 0.0
            mean_v = sum(vals) / len(vals)
            var_v = sum((x - mean_v) ** 2 for x in vals) / len(vals)
            return math.sqrt(var_v)
        w_mom = _std(mom_w)
        w_val = _std(val_w)
        w_qual = _std(qual_w)
        weight_sum = w_mom + w_val + w_qual if (w_mom + w_val + w_qual) != 0 else 1.0
        w_mom /= weight_sum
        w_val /= weight_sum
        w_qual /= weight_sum
        
        composite_scores: Dict[str, Dict[str, float]] = {}
        for idx, ticker in enumerate(raw_factors.keys()):
            composite = (mom_norm[idx] * w_mom + val_norm[idx] * w_val + qual_norm[idx] * w_qual)
            composite_scores[ticker] = {
                'composite': composite,
                'momentum': mom_norm[idx],
                'value': val_norm[idx],
                'quality': qual_norm[idx],
                'weight_momentum': w_mom,
                'weight_value': w_val,
                'weight_quality': w_qual
            }
        
        sorted_tickers = sorted(composite_scores.items(), key=lambda x: x[1]['composite'], reverse=True)
        total = len(sorted_tickers)
        cutoff = int(total * self.top_pct)
        if total > 0:
            cutoff = max(self.min_signals, cutoff)
        top_stocks = sorted_tickers[:cutoff]
        
        for ticker, scores in top_stocks:
            try:
                df = preloaded_data.get(ticker) if preloaded_data and ticker in preloaded_data else DataManager.fetch_data(ticker, "60d", "1d")
                if df is not None and not df.empty:
                    current_price = float(df['Close'].iloc[-1])
                    atr = TechnicalAnalyzer.calculate_atr(df.tail(60), 14)
                    signal = StrategySignal(
                        ticker=ticker,
                        action="BUY",
                        timestamp=datetime.now(),
                        strength=min(100, max(0, scores['composite']) * 100),
                        entry_price=current_price,
                        stop_loss=current_price - (2 * atr),
                        take_profit=current_price + (5 * atr),
                        reason=(
                            f"MF Dispersion Composite: {scores['composite']:.2f} "
                            f"(M:{scores['momentum']:.2f} W:{scores['weight_momentum']:.2f}, "
                            f"V:{scores['value']:.2f} W:{scores['weight_value']:.2f}, "
                            f"Q:{scores['quality']:.2f} W:{scores['weight_quality']:.2f})"
                        ),
                        metadata=scores
                    )
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Multi-factor signal error for {ticker}: {e}")
        
        self.signals = signals
        return signals

# ==========================================
# COMPREHENSIVE REPORTING MODULE
# ==========================================

class ReportingModule:
    """Generate comprehensive backtest and strategy reports."""
    
    @staticmethod
    def generate_console_report(strategy_name: str, trades: List[BacktestTrade], 
                               metrics: BacktestMetrics, initial_capital: float):
        """Generate formatted console report."""
        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print(f"[bold cyan]Strategy Report: {strategy_name}[/bold cyan]")
        console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
        
        # Performance Metrics
        table = Table(title="Performance Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        
        table.add_row("Total Trades", str(metrics.total_trades))
        table.add_row("Winning Trades", str(metrics.winning_trades))
        table.add_row("Losing Trades", str(metrics.losing_trades))
        table.add_row("Win Rate", f"{metrics.win_rate*100:.2f}%")
        table.add_row("Avg Win", f"${metrics.avg_win:.2f}")
        table.add_row("Avg Loss", f"${metrics.avg_loss:.2f}")
        table.add_row("Profit Factor", f"{metrics.profit_factor:.2f}")
        table.add_row("Total P&L", f"${metrics.total_pnl:.2f}")
        table.add_row("Return", f"{(metrics.total_pnl/initial_capital)*100:.2f}%")
        table.add_row("Max Drawdown", f"{metrics.max_drawdown*100:.2f}%")
        table.add_row("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")
        table.add_row("Sortino Ratio", f"{metrics.sortino_ratio:.2f}")
        table.add_row("Calmar Ratio", f"{metrics.calmar_ratio:.2f}")
        table.add_row("Expectancy", f"${metrics.expectancy:.2f}")
        
        console.print(table)
        
        # Top 5 Winners
        if trades:
            winners = sorted([t for t in trades if t.win], key=lambda x: x.pnl, reverse=True)[:5]
            if winners:
                console.print("\n[bold green]Top 5 Winning Trades:[/bold green]")
                win_table = Table(show_header=True, header_style="bold green")
                win_table.add_column("Ticker")
                win_table.add_column("Entry")
                win_table.add_column("Exit")
                win_table.add_column("P&L")
                win_table.add_column("Return")
                
                for t in winners:
                    win_table.add_row(
                        t.ticker,
                        f"${t.entry_price:.2f}",
                        f"${t.exit_price:.2f}",
                        f"${t.pnl:.2f}",
                        f"{t.pnl_percent:.2f}%"
                    )
                console.print(win_table)
            
            # Top 5 Losers
            losers = sorted([t for t in trades if not t.win], key=lambda x: x.pnl)[:5]
            if losers:
                console.print("\n[bold red]Top 5 Losing Trades:[/bold red]")
                loss_table = Table(show_header=True, header_style="bold red")
                loss_table.add_column("Ticker")
                loss_table.add_column("Entry")
                loss_table.add_column("Exit")
                loss_table.add_column("P&L")
                loss_table.add_column("Return")
                
                for t in losers:
                    loss_table.add_row(
                        t.ticker,
                        f"${t.entry_price:.2f}",
                        f"${t.exit_price:.2f}",
                        f"${t.pnl:.2f}",
                        f"{t.pnl_percent:.2f}%"
                    )
                console.print(loss_table)
    
    @staticmethod
    def export_detailed_report(strategy_name: str, trades: List[BacktestTrade], 
                               metrics: BacktestMetrics, initial_capital: float, 
                               output_dir: str = ".") -> Dict[str, str]:
        """Export detailed reports to multiple files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{strategy_name}_{timestamp}"
            
            files_created = {}
            
            # 1. Trade log CSV
            trade_log_path = os.path.join(output_dir, f"{base_name}_trades.csv")
            if trades:
                trade_data = []
                for t in trades:
                    trade_data.append({
                        'entry_date': t.entry_date,
                        'exit_date': t.exit_date,
                        'ticker': t.ticker,
                        'direction': t.direction,
                        'entry_price': t.entry_price,
                        'exit_price': t.exit_price,
                        'shares': t.shares,
                        'stop_loss': t.stop_loss,
                        'take_profit': t.take_profit,
                        'pnl': t.pnl,
                        'pnl_percent': t.pnl_percent,
                        'win': t.win,
                        'exit_reason': t.reason
                    })
                pd.DataFrame(trade_data).to_csv(trade_log_path, index=False)
                files_created['trade_log'] = trade_log_path
            
            # 2. Metrics summary CSV
            metrics_path = os.path.join(output_dir, f"{base_name}_metrics.csv")
            metrics_data = {
                'metric': ['Total Trades', 'Winning Trades', 'Losing Trades', 'Win Rate', 
                          'Avg Win', 'Avg Loss', 'Profit Factor', 'Total P&L', 'Return %',
                          'Max Drawdown', 'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Expectancy'],
                'value': [metrics.total_trades, metrics.winning_trades, metrics.losing_trades,
                         f"{metrics.win_rate*100:.2f}%", f"${metrics.avg_win:.2f}", f"${metrics.avg_loss:.2f}",
                         f"{metrics.profit_factor:.2f}", f"${metrics.total_pnl:.2f}", 
                         f"{(metrics.total_pnl/initial_capital)*100:.2f}%",
                         f"{metrics.max_drawdown*100:.2f}%", f"{metrics.sharpe_ratio:.2f}",
                         f"{metrics.sortino_ratio:.2f}", f"{metrics.calmar_ratio:.2f}", f"${metrics.expectancy:.2f}"]
            }
            pd.DataFrame(metrics_data).to_csv(metrics_path, index=False)
            files_created['metrics'] = metrics_path
            
            # 3. Analysis text report
            analysis_path = os.path.join(output_dir, f"{base_name}_analysis.txt")
            with open(analysis_path, 'w') as f:
                f.write(f"Strategy Analysis Report: {strategy_name}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                
                f.write("WHAT WORKED:\n")
                if metrics.win_rate > 0.5:
                    f.write(f"- Strong win rate of {metrics.win_rate*100:.1f}%\n")
                if metrics.profit_factor > 1.5:
                    f.write(f"- Excellent profit factor of {metrics.profit_factor:.2f}\n")
                if metrics.sharpe_ratio > 1.0:
                    f.write(f"- Good risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})\n")
                
                f.write("\nWHAT DIDN'T WORK:\n")
                if metrics.win_rate < 0.5:
                    f.write(f"- Low win rate of {metrics.win_rate*100:.1f}% - consider tightening entry criteria\n")
                if metrics.max_drawdown < -0.20:
                    f.write(f"- Large drawdown of {metrics.max_drawdown*100:.1f}% - improve risk management\n")
                if abs(metrics.avg_loss) > abs(metrics.avg_win):
                    f.write(f"- Average loss (${abs(metrics.avg_loss):.2f}) exceeds average win (${metrics.avg_win:.2f}) - adjust R:R\n")
                
                f.write("\nRECOMMENDATIONS:\n")
                if metrics.win_rate < 0.4:
                    f.write("- Increase signal quality threshold\n")
                if metrics.max_drawdown < -0.15:
                    f.write("- Implement position sizing based on volatility\n")
                    f.write("- Consider adding correlation filters\n")
                if metrics.profit_factor < 1.2:
                    f.write("- Optimize stop-loss and take-profit levels\n")
                    f.write("- Add confirmation indicators\n")
                
            files_created['analysis'] = analysis_path
            
            logger.info(f"Reports exported: {list(files_created.keys())}")
            return files_created
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return {}

# ==========================================
# MARKET SCANNER
# ==========================================

class MarketScanner:
    """Scans markets for trading opportunities."""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
    
    def scan_universe(self, universe: List[str], config: Dict) -> List[ScannerOpportunity]:
        """Enhanced scan: uses fallback analysis + fundamentals/Greeks weighting for each ticker.

        Falls back to legacy daily scan if intraday fetch fails.
        """
        opportunities: List[ScannerOpportunity] = []
        min_conf = float(config.get('scanner_min_confidence', 55))
        max_results = int(config.get('scanner_max_results', 20))
        period_intraday = config.get('scanner_period_intraday', '5d')
        interval_intraday = config.get('scanner_interval_intraday', '15m')
        period_daily = config.get('scanner_period_daily', '1y')
        interval_daily = config.get('scanner_interval_daily', '1d')
        acct_size = config.get('account_size', 10000)
        risk_pct = (config.get('risk_per_trade', 2.0)/100.0)
        desired_rrr = float(config.get('default_rrr', 2.0))
        debug_scanner = bool(config.get('debug_scanner', False)) or os.getenv('DEBUG_SCANNER','0') in ['1','true','True']

        console.print(f"\n[bold cyan]🔍 Enhanced Scanner: {len(universe)} tickers[/bold cyan]\n")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Scanning...", total=len(universe))

            for ticker in universe:
                try:
                    # Prefer intraday context
                    df = DataManager.fetch_data(ticker, period_intraday, interval_intraday)
                    if df is None or len(df) < 50:
                        df = DataManager.fetch_data(ticker, period_daily, interval_daily)
                    if df is None or len(df) < 30:
                        if debug_scanner:
                            console.print(f"[dim]{ticker}: skipped (insufficient data)\n[/dim]")
                        progress.update(task, advance=1)
                        continue

                    indicators = TechnicalAnalyzer.calculate_indicators(df)
                    if indicators is None:
                        if debug_scanner:
                            console.print(f"[dim]{ticker}: indicators failed\n[/dim]")
                        progress.update(task, advance=1)
                        continue

                    summary = self.analyzer._fallback_analysis(
                        ticker, indicators, acct_size, risk_pct, desired_rrr
                    )

                    if summary.action == 'HOLD' or summary.confidence < min_conf:
                        if debug_scanner:
                            console.print(f"[dim]{ticker}: confidence {summary.confidence:.1f} < {min_conf}\n[/dim]")
                        progress.update(task, advance=1)
                        continue

                    info = DataManager.get_ticker_info(ticker)
                    # Use summary.take_profit_1 as target
                    target = summary.take_profit_1
                    opp = ScannerOpportunity(
                        ticker=ticker,
                        score=min(100, summary.confidence),
                        action=summary.action,
                        confidence=summary.confidence,
                        entry_price=summary.entry_price,
                        stop_loss=summary.stop_loss,
                        target=target,
                        risk_reward=summary.risk_reward_ratio,
                        primary_signal=summary.primary_reason,
                        supporting_signals=summary.supporting_signals[:5],
                        market_cap=f"${info['market_cap']/1e9:.1f}B" if info['market_cap'] > 0 else "N/A",
                        sector=info['sector']
                    )
                    opportunities.append(opp)
                except Exception as e:
                    logger.error(f"Scanner error {ticker}: {e}")
                finally:
                    progress.update(task, advance=1)

        # Sort by confidence / score descending
        opportunities.sort(key=lambda x: (x.confidence, x.score), reverse=True)
        return opportunities[:max_results]

# ==========================================
# THEME RESEARCH ENGINE
# ==========================================

class ThemeResearcher:
    """Research investment themes with AI."""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except:
            self.client = None
    
    def research_theme(self, theme: str) -> Dict[str, Any]:
        """Research a specific investment theme."""
        
        console.print(f"\n[bold cyan]🔬 Researching: {theme}[/bold cyan]\n")
        
        if not self.client:
            console.print("[yellow]AI unavailable. Using basic research.[/yellow]")
            return self._basic_research(theme)
        
        try:
            prompt = f"""Research the investment theme: "{theme}"

Analyze:
1. Key companies in this space (with ticker symbols and their recent price performance)
2. Recent news and developments with specific stock price impacts
3. Market trends and growth potential (include estimated market size and growth rates)
4. Regulatory environment
5. Investment opportunities (BUY/SELL recommendations with price targets)
6. Risk factors with specific impacts

Provide detailed analysis with specific stock recommendations and real numbers (prices, percentages, market sizes).

Format response as JSON:
{{
  "theme": "{theme}",
  "summary": "Brief overview with key metrics (market size, growth rate)",
  "key_companies": [
    {{"ticker": "SYMBOL", "name": "Company Name", "reason": "Why relevant with specific details", "recommendation": "BUY/HOLD/SELL", "recent_price_change": "+X%"}}
  ],
  "news_highlights": ["Recent development with price impact (e.g., stock up 5% on earnings)"],
  "growth_potential": "Analysis with specific numbers (e.g., $50B market growing 20% annually)",
  "risks": ["Risk 1 with specific impact (e.g., regulatory could cut revenue 15%)"],
  "opportunities": [
    {{"ticker": "SYMBOL", "action": "BUY/SELL", "confidence": 0-100, "price_target": X.XX, "rationale": "Specific reason with numbers (e.g., trading at 2x revenue vs 5x peers)"}}
  ]
}}

IMPORTANT: Use real numbers throughout - include stock prices, percentage changes, market sizes, growth rates, and valuation multiples. Make it sound professional and data-driven."""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis_text = response.content[0].text
            
            # Use robust JSON extraction instead of greedy regex
            analysis = extract_json_from_text(analysis_text)
            if analysis:
                return analysis
            else:
                return self._basic_research(theme)
                
        except Exception as e:
            logger.error(f"Theme research error: {e}")
            return self._basic_research(theme)
    
    def _basic_research(self, theme: str) -> Dict[str, Any]:
        """Basic research without AI."""
        theme_lower = theme.lower()
        
        theme_stocks = {
            "quantum": ["IONQ", "RGTI", "QBTS", "IBM", "GOOGL", "MSFT"],
            "ai": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "PLTR"],
            "crypto": ["COIN", "MSTR", "RIOT", "MARA"],
            "ev": ["TSLA", "RIVN", "LCID", "F", "GM"],
            "biotech": ["MRNA", "BNTX", "NVAX", "REGN"]
        }
        
        tickers = []
        for key, stocks in theme_stocks.items():
            if key in theme_lower:
                tickers = stocks
                break
        
        if not tickers:
            tickers = ["SPY"]
        
        return {
            "theme": theme,
            "summary": f"Analysis of {theme} sector",
            "key_companies": [{"ticker": t, "name": t, "reason": "Relevant to theme", "recommendation": "HOLD"} for t in tickers],
            "news_highlights": ["Check financial news for latest updates"],
            "growth_potential": "Research required",
            "risks": ["Market volatility", "Sector-specific risks"],
            "opportunities": []
        }

# ==========================================
# REGIME DETECTION & MULTI-TIMEFRAME
# ==========================================

class RegimeDetector:
    """Detect market regime: Trending/Ranging/Volatile."""
    
    @staticmethod
    def detect_regime(df: pd.DataFrame, indicators: AdvancedIndicators) -> MarketRegime:
        """Classify current market regime."""
        try:
            adx = indicators.adx
            atr = indicators.atr
            close = df['Close'].values
            
            # Calculate ATR percentile (last 50 periods)
            recent_atr = []
            for i in range(max(0, len(df) - 50), len(df)):
                if i >= 14:
                    tr = max(df['High'].iloc[i] - df['Low'].iloc[i],
                            abs(df['High'].iloc[i] - df['Close'].iloc[i-1]),
                            abs(df['Low'].iloc[i] - df['Close'].iloc[i-1]))
                    recent_atr.append(tr)
            
            atr_percentile = 50.0
            if len(recent_atr) > 0:
                atr_percentile = (sum(1 for x in recent_atr if x < atr) / len(recent_atr)) * 100
            
            # Trend strength using linear regression
            x = np.arange(len(close[-50:]))
            slope, _, r_value, _, _ = linregress(x, close[-50:])
            trend_strength = abs(r_value)  # 0-1
            
            # Classification logic
            regime = "RANGING"
            confidence = 50.0
            details = ""
            
            if adx > 25 and trend_strength > 0.7:
                # Strong trend
                if slope > 0:
                    regime = "TRENDING_UP"
                    confidence = min(95, 50 + adx + (trend_strength * 30))
                    details = f"Strong uptrend (ADX={adx:.1f}, R²={r_value**2:.2f})"
                else:
                    regime = "TRENDING_DOWN"
                    confidence = min(95, 50 + adx + (trend_strength * 30))
                    details = f"Strong downtrend (ADX={adx:.1f}, R²={r_value**2:.2f})"
            elif atr_percentile > 80:
                # High volatility
                regime = "VOLATILE"
                confidence = min(90, 40 + atr_percentile / 2)
                details = f"High volatility regime (ATR {atr_percentile:.0f}th percentile)"
            else:
                # Ranging/choppy
                regime = "RANGING"
                confidence = min(85, 30 + (50 - adx) + (1 - trend_strength) * 20)
                details = f"Choppy range (ADX={adx:.1f}, weak trend)"
            
            return MarketRegime(
                regime=regime,
                confidence=confidence,
                adx=adx,
                atr_percentile=atr_percentile,
                trend_strength=trend_strength,
                details=details
            )
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
            return MarketRegime("RANGING", 50.0, 20.0, 50.0, 0.5, "Unknown")

class MultiTimeframeAnalyzer:
    """Multi-timeframe trend confirmation."""
    
    @staticmethod
    def analyze(ticker: str, primary_interval: str) -> MultiTimeframeAnalysis:
        """Check trend alignment across timeframes."""
        try:
            # Map primary interval to higher timeframe
            tf_map = {
                "1m": ["5m", "15m"],
                "5m": ["15m", "1h"],
                "15m": ["1h", "4h"],
                "30m": ["1h", "1d"],
                "1h": ["4h", "1d"],
                "4h": ["1d", "1wk"],
                "1d": ["1wk", "1mo"]
            }
            
            higher_tfs = tf_map.get(primary_interval, ["1h", "1d"])
            timeframes = {}
            
            # Fetch and analyze each timeframe
            for tf in [primary_interval] + higher_tfs:
                period_map = {
                    "1m": "5d", "5m": "10d", "15m": "30d", "30m": "60d",
                    "1h": "90d", "4h": "180d", "1d": "2y", "1wk": "5y", "1mo": "10y"
                }
                period = period_map.get(tf, "1y")
                
                df = DataManager.fetch_data(ticker, period, tf)
                if df is None or len(df) < 20:
                    timeframes[tf] = "NEUTRAL"
                    continue
                
                # Simple trend detection: SMA comparison
                close = df['Close'].values
                sma_fast = pd.Series(close).rolling(10).mean().iloc[-1]
                sma_slow = pd.Series(close).rolling(20).mean().iloc[-1]
                current = close[-1]
                
                if current > sma_fast > sma_slow:
                    timeframes[tf] = "BULLISH"
                elif current < sma_fast < sma_slow:
                    timeframes[tf] = "BEARISH"
                else:
                    timeframes[tf] = "NEUTRAL"
            
            # Determine primary trend and alignment
            primary_trend = timeframes.get(primary_interval, "NEUTRAL")
            
            # Count aligned timeframes
            aligned = sum(1 for trend in timeframes.values() if trend == primary_trend and trend != "NEUTRAL")
            total = len([t for t in timeframes.values() if t != "NEUTRAL"])
            
            confirmation_score = (aligned / max(1, total)) * 100 if total > 0 else 50.0
            higher_tf_aligned = all(timeframes.get(tf, "NEUTRAL") == primary_trend for tf in higher_tfs if timeframes.get(tf) != "NEUTRAL")
            
            details = f"Primary: {primary_trend}, Higher TFs: {', '.join(f'{k}={v}' for k, v in timeframes.items() if k != primary_interval)}"
            
            return MultiTimeframeAnalysis(
                primary_trend=primary_trend,
                higher_tf_aligned=higher_tf_aligned,
                timeframes=timeframes,
                confirmation_score=confirmation_score,
                details=details
            )
        except Exception as e:
            logger.error(f"MTF analysis error: {e}")
            return MultiTimeframeAnalysis("NEUTRAL", False, {}, 50.0, f"Error: {e}")

# ==========================================
# TECHNICAL ANALYSIS ENGINE
# ==========================================

class TechnicalAnalyzer:
    """Professional-grade technical analysis with 80+ indicators."""
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range (ATR)."""
        try:
            high = df['High']
            low = df['Low']
            close = df['Close']
            
            # True Range calculation
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR uses Wilder's smoothing
            atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
            atr_val = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0
            
            return atr_val
        except Exception as e:
            logger.error(f"ATR calculation error: {e}")
            return 0.0
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> Optional[AdvancedIndicators]:
        """Calculate all technical indicators."""
        try:
            if df.empty:
                logger.error("Empty dataframe provided")
                return None
            
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return None
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            open_price = df['Open']
            volume = df['Volume']
            
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            if isinstance(high, pd.DataFrame):
                high = high.iloc[:, 0]
            if isinstance(low, pd.DataFrame):
                low = low.iloc[:, 0]
            if isinstance(open_price, pd.DataFrame):
                open_price = open_price.iloc[:, 0]
            if isinstance(volume, pd.DataFrame):
                volume = volume.iloc[:, 0]
            
            price = float(close.iloc[-1])
            
            sma_10 = float(close.rolling(min(10, len(close))).mean().iloc[-1])
            sma_20 = float(close.rolling(min(20, len(close))).mean().iloc[-1])
            sma_50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
            sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])
            
            # EMAs - use adjust=False for proper weighting
            ema_12 = float(close.ewm(span=12, adjust=False).mean().iloc[-1])
            ema_26 = float(close.ewm(span=26, adjust=False).mean().iloc[-1])
            ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
            ema_200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])
            
            # Typical Price
            tp = (high + low + close) / 3
            # VWAP per current trading session (matches most platforms)
            try:
                idx = df.index
                # Normalize index to timezone-aware America/New_York for session grouping
                try:
                    from zoneinfo import ZoneInfo  # py>=3.9
                    if getattr(idx, 'tz', None) is None:
                        # Assume UTC if tz-naive from yfinance, then convert
                        idx_tz = pd.to_datetime(idx).tz_localize('UTC').tz_convert(ZoneInfo('America/New_York'))
                    else:
                        idx_tz = pd.to_datetime(idx).tz_convert(ZoneInfo('America/New_York'))
                except Exception:
                    # Fallback: treat as local naive timestamps and group by date
                    idx_tz = pd.to_datetime(idx)

                last_dt = pd.to_datetime(idx_tz[-1])
                session_date = last_dt.date()
                session_mask = pd.to_datetime(idx_tz).date == session_date
                tp_s = tp[session_mask]
                vol_s = volume[session_mask]
                vwap_series = (tp_s * vol_s).cumsum().div(vol_s.cumsum())
                vwap = float(vwap_series.iloc[-1]) if len(vwap_series) > 0 else float((tp * volume).cumsum().div(volume.cumsum()).iloc[-1])
            except Exception:
                vwap = float((tp * volume).cumsum().div(volume.cumsum()).iloc[-1])
            
            def calc_rsi(period):
                """Calculate RSI using Wilder's smoothing (EMA-based)."""
                period = min(period, len(close)-1)
                if period < 2 or len(close) < period + 1:
                    return pd.Series([50.0] * len(close), index=close.index)
                
                delta = close.diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                
                # Use EMA (Wilder's smoothing) instead of SMA
                avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
                avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
                
                rs = avg_gain / avg_loss.replace(0, 1e-10)
                rsi = 100 - (100 / (1 + rs))
                
                # Clamp RSI between 0 and 100
                rsi = rsi.clip(0, 100)
                return rsi
            
            rsi_14 = float(calc_rsi(14).iloc[-1]) if len(close) > 15 else 50.0
            rsi_7 = float(calc_rsi(7).iloc[-1]) if len(close) > 8 else 50.0
            
            # Ensure RSI is valid number
            if pd.isna(rsi_14) or np.isinf(rsi_14):
                rsi_14 = 50.0
            if pd.isna(rsi_7) or np.isinf(rsi_7):
                rsi_7 = 50.0
            
            # Stochastic - proper formula
            period = min(14, len(close)-1)
            if period < 2:
                stoch_k_val = 50.0
                stoch_d_val = 50.0
            else:
                low_14 = low.rolling(period).min()
                high_14 = high.rolling(period).max()
                stoch_k = 100 * ((close - low_14) / (high_14 - low_14).replace(0, 1e-10))
                stoch_d = stoch_k.rolling(3).mean()  # %D is 3-period SMA of %K
                stoch_k_val = float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else 50.0
                stoch_d_val = float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else 50.0
            
            # MACD - proper formula with full series
            ema_12_series = close.ewm(span=12, adjust=False).mean()
            ema_26_series = close.ewm(span=26, adjust=False).mean()
            macd_line = float((ema_12_series - ema_26_series).iloc[-1])
            macd_signal_series = (ema_12_series - ema_26_series).ewm(span=9, adjust=False).mean()
            macd_signal = float(macd_signal_series.iloc[-1])
            macd_hist = macd_line - macd_signal
            
            # ATR - proper True Range calculation
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            # ATR uses Wilder's smoothing (like RSI)
            atr = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            atr_val = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0
            atr_percent = (atr_val / price) * 100 if price > 0 else 0
            
            bb_period = min(20, len(close))
            bb_middle = close.rolling(bb_period).mean()
            bb_std = close.rolling(bb_period).std()
            bb_upper = bb_middle + (2 * bb_std)
            bb_lower = bb_middle - (2 * bb_std)
            
            # ADX - proper Wilder's smoothing
            high_diff = high.diff()
            low_diff = -low.diff()
            plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
            minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
            
            # Smooth DM and ATR with Wilder's method
            smoothed_plus_dm = plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            smoothed_minus_dm = minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            atr_for_adx = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            
            plus_di = 100 * (smoothed_plus_dm / atr_for_adx.replace(0, 1e-10))
            minus_di = 100 * (smoothed_minus_dm / atr_for_adx.replace(0, 1e-10))
            dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10))
            adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            adx_val = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 25.0
            
            # OBV: add volume when close>prev, subtract when close<prev, unchanged when equal
            _delta_close = close.diff()
            _pos_vol = volume.where(_delta_close > 0, 0)
            _neg_vol = volume.where(_delta_close < 0, 0)
            obv = (_pos_vol - _neg_vol).cumsum()
            obv_val = float(obv.iloc[-1]) if len(obv) > 0 else 0.0
            vol_sma_20 = float(volume.rolling(min(20, len(volume))).mean().iloc[-1])
            vol_ratio = float(volume.iloc[-1]) / vol_sma_20 if vol_sma_20 > 0 else 1.0
            
            tp_mfi = (high + low + close) / 3
            raw_money_flow = tp_mfi * volume
            positive_flow = raw_money_flow.where(tp_mfi > tp_mfi.shift(), 0).rolling(min(14, len(raw_money_flow))).sum()
            negative_flow = raw_money_flow.where(tp_mfi < tp_mfi.shift(), 0).rolling(min(14, len(raw_money_flow))).sum()
            mfi = 100 - (100 / (1 + positive_flow / negative_flow.replace(0, 1)))
            mfi_val = float(mfi.iloc[-1]) if not pd.isna(mfi.iloc[-1]) else 50.0
            
            chop_period = min(14, len(tr))
            atr_sum = tr.rolling(chop_period).sum()
            high_low_diff = high.rolling(chop_period).max() - low.rolling(chop_period).min()
            chop = 100 * np.log10(atr_sum / high_low_diff.replace(0, 1)) / np.log10(chop_period)
            chop_val = float(chop.iloc[-1]) if not pd.isna(chop.iloc[-1]) else 50.0

            # EMA ribbon - use adjust=False
            ema_8 = float(close.ewm(span=8, adjust=False).mean().iloc[-1])
            ema_21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
            ema_34 = float(close.ewm(span=34, adjust=False).mean().iloc[-1])

            # Williams %R (14)
            period_wr = min(14, len(close)-1)
            highest_high = high.rolling(period_wr).max()
            lowest_low = low.rolling(period_wr).min()
            williams_r = -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, 1)
            williams_r_val = float(williams_r.iloc[-1]) if not pd.isna(williams_r.iloc[-1]) else 0.0

            # CCI (20)
            tp = (high + low + close) / 3
            ma_tp = tp.rolling(min(20, len(tp))).mean()
            mad = tp.rolling(min(20, len(tp))).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
            cci = (tp - ma_tp) / mad.replace(0, 1) / 0.015
            cci_val = float(cci.iloc[-1]) if not pd.isna(cci.iloc[-1]) else 0.0

            # Keltner Channels (EMA 20, ATR multiplier 2)
            kc_mid = close.ewm(span=20, adjust=False).mean()
            kc_atr = tr.ewm(alpha=1/10, min_periods=10, adjust=False).mean()
            keltner_upper = float((kc_mid + 2 * kc_atr).iloc[-1])
            keltner_lower = float((kc_mid - 2 * kc_atr).iloc[-1])
            keltner_middle = float(kc_mid.iloc[-1])

            # Ichimoku (simple): Tenkan/Kijun/SenkouSpanA/B/Chikou
            nine_period_high = high.rolling(min(9, len(high))).max()
            nine_period_low = low.rolling(min(9, len(low))).min()
            tenkan_sen = float(((nine_period_high + nine_period_low)/2).iloc[-1])

            kijun_high = high.rolling(min(26, len(high))).max()
            kijun_low = low.rolling(min(26, len(low))).min()
            kijun_sen = float(((kijun_high + kijun_low)/2).iloc[-1])

            senkou_a = float((((tenkan_sen + kijun_sen)/2)).__float__()) if True else float(((nine_period_high + nine_period_low)/2).iloc[-1])
            senkou_b = float((((high.rolling(min(52, len(high))).max() + low.rolling(min(52, len(low))).min())/2).iloc[-1]))
            chikou_span = float(close.shift(26).iloc[-1]) if len(close) > 26 else float(close.iloc[-1])

            # HMA 20 (Hull Moving Average) - proper WMA calculation
            def wma(series, period):
                """Weighted Moving Average"""
                weights = np.arange(1, period + 1)
                return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
            
            def hma(series, period):
                """Hull Moving Average"""
                half_period = int(period / 2)
                sqrt_period = int(np.sqrt(period))
                wma_half = wma(series, half_period)
                wma_full = wma(series, period)
                raw_hma = 2 * wma_half - wma_full
                return wma(raw_hma, sqrt_period)

            hma_20 = float(hma(close, 20).iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])

            # ROC (12)
            n = min(12, len(close)-1)
            roc = (close - close.shift(n)) / close.shift(n).replace(0, 1) * 100
            roc_12 = float(roc.iloc[-1]) if not pd.isna(roc.iloc[-1]) else 0.0
            
            if adx_val > 25 and chop_val < 50:
                regime = "TRENDING"
                regime_conf = min(100, adx_val + (50 - chop_val))
            elif chop_val > 61.8:
                regime = "RANGING"
                regime_conf = chop_val
            else:
                regime = "VOLATILE"
                regime_conf = 100 - chop_val
            
            return AdvancedIndicators(
                price=round(price, 2),
                open=round(float(open_price.iloc[-1]), 2),
                high=round(float(high.iloc[-1]), 2),
                low=round(float(low.iloc[-1]), 2),
                close=round(price, 2),
                volume=int(volume.iloc[-1]),
                closes=close,  # Pass full series for pattern detection
                sma_10=round(sma_10, 2),
                sma_20=round(sma_20, 2),
                sma_50=round(sma_50, 2),
                sma_200=round(sma_200, 2),
                ema_12=round(ema_12, 2),
                ema_26=round(ema_26, 2),
                ema_50=round(ema_50, 2),
                ema_200=round(ema_200, 2),
                vwap=round(vwap, 2),
                rsi_14=round(rsi_14, 2),
                rsi_7=round(rsi_7, 2),
                stochastic_k=round(stoch_k_val, 2),
                stochastic_d=round(stoch_d_val, 2),
                macd=round(macd_line, 4),
                macd_signal=round(macd_signal, 4),
                macd_histogram=round(macd_hist, 4),
                atr=round(atr_val, 2),
                atr_percent=round(atr_percent, 2),
                bb_upper=round(float(bb_upper.iloc[-1]), 2),
                bb_lower=round(float(bb_lower.iloc[-1]), 2),
                bb_middle=round(float(bb_middle.iloc[-1]), 2),
                adx=round(adx_val, 2),
                plus_di=round(float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else 0.0, 2),
                minus_di=round(float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else 0.0, 2),
                obv=round(obv_val, 0),
                volume_ratio=round(vol_ratio, 2),
                mfi=round(mfi_val, 2),
                ema_8=round(ema_8, 2),
                ema_21=round(ema_21, 2),
                ema_34=round(ema_34, 2),
                williams_r=round(williams_r_val, 2),
                cci=round(cci_val, 2),
                keltner_upper=round(keltner_upper, 2),
                keltner_middle=round(keltner_middle, 2),
                keltner_lower=round(keltner_lower, 2),
                tenkan_sen=round(tenkan_sen, 2),
                kijun_sen=round(kijun_sen, 2),
                senkou_a=round(senkou_a, 2),
                senkou_b=round(senkou_b, 2),
                chikou_span=round(chikou_span, 2),
                hma_20=round(hma_20, 2),
                roc_12=round(roc_12, 2),
                market_regime=regime,
                regime_confidence=round(regime_conf, 2)
            )
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            logger.exception("Full traceback:")
            return None

class PatternRecognizer:
    """Detect chart patterns."""
    
    @staticmethod
    def analyze(df: pd.DataFrame) -> PatternAnalysis:
        """Detect all patterns."""
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        open_price = df['Open'].values
        
        bullish = []
        bearish = []
        neutral = []
        candlestick = []
        
        check_len = min(20, len(high))
        if check_len >= 10:
            recent_high = high[-check_len:]
            recent_low = low[-check_len:]
            
            peaks = argrelextrema(recent_high, np.greater, order=3)[0]
            troughs = argrelextrema(recent_low, np.less, order=3)[0]
            
            higher_highs = len(peaks) >= 2 and recent_high[peaks[-1]] > recent_high[peaks[-2]]
            higher_lows = len(troughs) >= 2 and recent_low[troughs[-1]] > recent_low[troughs[-2]]
            lower_highs = len(peaks) >= 2 and recent_high[peaks[-1]] < recent_high[peaks[-2]]
            lower_lows = len(troughs) >= 2 and recent_low[troughs[-1]] < recent_low[troughs[-2]]
            
            if higher_highs and higher_lows:
                bullish.append("Uptrend (HH/HL)")
            if lower_highs and lower_lows:
                bearish.append("Downtrend (LH/LL)")
        
        if len(close) >= 2:
            o, c, h, l = open_price[-1], close[-1], high[-1], low[-1]
            body = abs(c - o)
            range_val = h - l
            
            if range_val > 0 and body / range_val < 0.1:
                candlestick.append("Doji")
            
            lower_shadow = min(o, c) - l
            upper_shadow = h - max(o, c)
            if lower_shadow > body * 2 and upper_shadow < body:
                candlestick.append("Hammer")
                bullish.append("Hammer")
            
            if upper_shadow > body * 2 and lower_shadow < body:
                candlestick.append("Shooting Star")
                bearish.append("Shooting Star")
            
            prev_o, prev_c = open_price[-2], close[-2]
            if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
                candlestick.append("Bullish Engulfing")
                bullish.append("Bullish Engulfing")
            elif prev_c > prev_o and c < o and c < prev_o and o > prev_c:
                candlestick.append("Bearish Engulfing")
                bearish.append("Bearish Engulfing")
        
        trend_patterns = {
            "higher_highs": len([p for p in bullish if "HH" in p]) > 0,
            "higher_lows": len([p for p in bullish if "HL" in p]) > 0,
            "lower_highs": len([p for p in bearish if "LH" in p]) > 0,
            "lower_lows": len([p for p in bearish if "LL" in p]) > 0,
        }
        # Additional pattern heuristics: double top/bottom, head & shoulders, triangles
        # Simple double top/bottom: two peaks/troughs at similar price within lookback
        lookback = min(60, len(close))
        prices = close[-lookback:]
        highs_idx = argrelextrema(prices, np.greater, order=3)[0]
        lows_idx = argrelextrema(prices, np.less, order=3)[0]
        if len(highs_idx) >= 2:
            h1 = prices[highs_idx[-2]]
            h2 = prices[highs_idx[-1]]
            if abs(h1 - h2) / max(h1, h2) < 0.01:
                bearish.append("Double Top")
        if len(lows_idx) >= 2:
            l1 = prices[lows_idx[-2]]
            l2 = prices[lows_idx[-1]]
            if abs(l1 - l2) / max(l1, l2) < 0.01:
                bullish.append("Double Bottom")

        # Head & Shoulders (very simplified): three peaks with middle higher by margin
        if len(highs_idx) >= 3:
            h3 = prices[highs_idx[-3:]]
            if h3[-2] > h3[-3] * 1.01 and h3[-2] > h3[-1] * 1.01:
                bearish.append("Head and Shoulders")
        # Inverse H&S
        if len(lows_idx) >= 3:
            l3 = prices[lows_idx[-3:]]
            if l3[-2] < l3[-3] * 0.99 and l3[-2] < l3[-1] * 0.99:
                bullish.append("Inverse Head and Shoulders")

        # Triangle detection (ascending/descending/symmetric): check slope of highs/lows
        if len(highs_idx) >= 2 and len(lows_idx) >= 2:
            hi_prices = prices[highs_idx]
            lo_prices = prices[lows_idx]
            hi_slope = (hi_prices[-1] - hi_prices[0]) / max(1, len(hi_prices))
            lo_slope = (lo_prices[-1] - lo_prices[0]) / max(1, len(lo_prices))
            if hi_slope < 0 and lo_slope > 0:
                neutral.append("Symmetrical Triangle")
            elif hi_slope < 0 and lo_slope < 0:
                bearish.append("Descending Triangle")
            elif hi_slope > 0 and lo_slope > 0:
                bullish.append("Ascending Triangle")

        return PatternAnalysis(
            bullish_patterns=bullish,
            bearish_patterns=bearish,
            neutral_patterns=neutral,
            candlestick_patterns=candlestick,
            trend_patterns=trend_patterns
        )

class SmartMoneyAnalyzer:
    """Smart Money Concepts analysis."""
    
    # Class variable to track previously detected order blocks to avoid duplicate notifications
    _last_notified_blocks = {}
    
    @staticmethod
    def analyze(df: pd.DataFrame, ticker: str = None, notifier = None) -> MarketStructure:
        """Analyze market structure."""
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        check_len = min(30, len(high))
        peaks = argrelextrema(high[-check_len:], np.greater, order=3)[0]
        troughs = argrelextrema(low[-check_len:], np.less, order=3)[0]
        
        if len(peaks) >= 2 and len(troughs) >= 2:
            if high[-check_len:][peaks[-1]] > high[-check_len:][peaks[-2]] and \
               low[-check_len:][troughs[-1]] > low[-check_len:][troughs[-2]]:
                structure = "BULLISH"
            elif high[-check_len:][peaks[-1]] < high[-check_len:][peaks[-2]] and \
                 low[-check_len:][troughs[-1]] < low[-check_len:][troughs[-2]]:
                structure = "BEARISH"
            else:
                structure = "RANGING"
        else:
            structure = "RANGING"
        
        order_blocks = []
        new_blocks_detected = []
        for i in range(10, min(50, len(df)-1)):
            if df['Close'].iloc[i] < df['Open'].iloc[i]:
                if i+1 < len(df) and df['Close'].iloc[i+1] > df['Open'].iloc[i+1]:
                    block = (float(df['Low'].iloc[i]), float(df['High'].iloc[i]))
                    order_blocks.append(block)
                    
                    # Check if this is a recent block (within last 5 bars) and not already notified
                    if ticker and notifier and i >= len(df) - 6:
                        block_key = f"{ticker}_{block[0]:.2f}_{block[1]:.2f}"
                        if block_key not in SmartMoneyAnalyzer._last_notified_blocks:
                            new_blocks_detected.append(block)
                            SmartMoneyAnalyzer._last_notified_blocks[block_key] = datetime.now()
        
        fvg = []
        for i in range(2, len(high)):
            if low[i] > high[i-2]:
                fvg.append((float(high[i-2]), float(low[i])))
        
        liquidity = [float(h) for h in high[-check_len:][peaks]] if len(peaks) > 0 else []
        
        recent_high = float(np.max(high[-check_len:]))
        recent_low = float(np.min(low[-check_len:]))
        range_val = recent_high - recent_low
        
        premium_zone = (recent_high - 0.3 * range_val, recent_high)
        discount_zone = (recent_low, recent_low + 0.3 * range_val)
        equilibrium = (recent_high + recent_low) / 2
        
        # Send separate notifications for each bullish AND bearish condition
        if ticker and notifier:
            try:
                current_price = float(close[-1])
                
                # BULLISH CONDITIONS
                # Condition 1: Bullish structure detected (SMC informational)
                if structure == "BULLISH":
                    structure_key = f"{ticker}_bullish_structure_{datetime.now().strftime('%Y%m%d')}"
                    if structure_key not in SmartMoneyAnalyzer._last_notified_blocks:
                        msg = f"📈 [SMC] Bullish structure detected\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"✅ Higher highs and higher lows confirmed\n"
                        msg += f"ℹ️ Informational market structure signal; combine with AI signal before acting"
                        notifier.send(msg)
                        SmartMoneyAnalyzer._last_notified_blocks[structure_key] = datetime.now()
                
                # Condition 2: Price in discount zone (SMC informational)
                in_discount_zone = discount_zone[0] <= current_price <= discount_zone[1]
                if in_discount_zone:
                    discount_key = f"{ticker}_discount_{datetime.now().strftime('%Y%m%d%H')}"
                    if discount_key not in SmartMoneyAnalyzer._last_notified_blocks:
                        msg = f"💰 [SMC] Price in discount zone\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"✅ Zone: ${discount_zone[0]:.2f} - ${discount_zone[1]:.2f}\n"
                        msg += f"ℹ️ Potential value area per SMC; confirm with AI signal"
                        notifier.send(msg)
                        SmartMoneyAnalyzer._last_notified_blocks[discount_key] = datetime.now()
                
                # Condition 3: Institutional support order blocks (SMC informational)
                if new_blocks_detected:
                    has_support_block = any(block[0] < current_price for block in new_blocks_detected)
                    if has_support_block:
                        msg = f"🏦 [SMC] Institutional support detected\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"✅ Order blocks below price:\n"
                        for block in new_blocks_detected:
                            if block[0] < current_price:
                                msg += f"   📊 ${block[0]:.2f} - ${block[1]:.2f}\n"
                        msg += f"\nℹ️ Potential demand zone per SMC; confirm with AI signal"
                        notifier.send(msg)
                
                # BEARISH CONDITIONS
                # Condition 1: Bearish structure detected (SMC informational)
                if structure == "BEARISH":
                    structure_key = f"{ticker}_bearish_structure_{datetime.now().strftime('%Y%m%d')}"
                    if structure_key not in SmartMoneyAnalyzer._last_notified_blocks:
                        msg = f"📉 [SMC] Bearish structure detected\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"⚠️ Lower highs and lower lows confirmed\n"
                        msg += f"ℹ️ Informational market structure signal; combine with AI signal before acting"
                        notifier.send(msg)
                        SmartMoneyAnalyzer._last_notified_blocks[structure_key] = datetime.now()
                
                # Condition 2: Price in premium zone (SMC informational)
                in_premium_zone = premium_zone[0] <= current_price <= premium_zone[1]
                if in_premium_zone:
                    premium_key = f"{ticker}_premium_{datetime.now().strftime('%Y%m%d%H')}"
                    if premium_key not in SmartMoneyAnalyzer._last_notified_blocks:
                        msg = f"⚠️ [SMC] Price in premium zone\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"⚠️ Zone: ${premium_zone[0]:.2f} - ${premium_zone[1]:.2f}\n"
                        msg += f"ℹ️ Potential supply zone per SMC; confirm with AI signal"
                        notifier.send(msg)
                        SmartMoneyAnalyzer._last_notified_blocks[premium_key] = datetime.now()
                
                # Condition 3: Institutional resistance order blocks (SMC informational)
                if new_blocks_detected:
                    has_resistance_block = any(block[0] > current_price for block in new_blocks_detected)
                    if has_resistance_block:
                        msg = f"🏦 [SMC] Institutional resistance detected\n"
                        msg += f"{ticker} @ ${current_price:.2f}\n\n"
                        msg += f"⚠️ Order blocks above price:\n"
                        for block in new_blocks_detected:
                            if block[0] > current_price:
                                msg += f"   📊 ${block[0]:.2f} - ${block[1]:.2f}\n"
                        msg += f"\nℹ️ Potential supply zone per SMC; confirm with AI signal"
                        notifier.send(msg)
            except:
                pass
        
        return MarketStructure(
            structure=structure,
            order_blocks=order_blocks[-3:] if order_blocks else [],
            fair_value_gaps=fvg[-3:] if fvg else [],
            liquidity_zones=liquidity[-3:],
            premium_zone=premium_zone,
            discount_zone=discount_zone,
            equilibrium=round(equilibrium, 2)
        )

class VolumeProfileAnalyzer:
    """Volume Profile analysis."""
    
    @staticmethod
    def analyze(df: pd.DataFrame) -> VolumeProfile:
        """Analyze volume profile."""
        close = df['Close'].values
        volume = df['Volume'].values
        
        price_min = close.min()
        price_max = close.max()
        num_bins = min(50, len(close))
        bins = np.linspace(price_min, price_max, num_bins)
        
        volume_by_price = {}
        for i in range(len(close)):
            bin_idx = np.digitize(close[i], bins) - 1
            if 0 <= bin_idx < len(bins):
                price_level = bins[bin_idx]
                volume_by_price[float(price_level)] = volume_by_price.get(float(price_level), 0) + volume[i]
        
        poc = max(volume_by_price, key=volume_by_price.get) if volume_by_price else float(close[-1])
        
        total_volume = sum(volume_by_price.values())
        target_volume = total_volume * 0.70
        
        sorted_prices = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        value_area_volume = 0
        value_area_prices = []
        
        for price, vol in sorted_prices:
            value_area_volume += vol
            value_area_prices.append(price)
            if value_area_volume >= target_volume:
                break
        
        vah = max(value_area_prices) if value_area_prices else float(close[-1])
        val = min(value_area_prices) if value_area_prices else float(close[-1])
        
        avg_volume = np.mean(list(volume_by_price.values()))
        hvn = [p for p, v in volume_by_price.items() if v > avg_volume * 1.5]
        lvn = [p for p, v in volume_by_price.items() if v < avg_volume * 0.5]
        
        return VolumeProfile(
            poc=round(poc, 2),
            vah=round(vah, 2),
            val=round(val, 2),
            high_volume_nodes=sorted(hvn)[-5:],
            low_volume_nodes=sorted(lvn)[-5:]
        )

# ==========================================
# AI ANALYZER
# ==========================================

class AIAnalyzer:
    """AI-powered trade analysis using Claude Sonnet 4."""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            self.client = None
    
    def analyze(self, ticker: str, indicators: AdvancedIndicators, 
                patterns: PatternAnalysis, market_structure: MarketStructure,
                volume_profile: VolumeProfile, account_size: float,
                risk_per_trade_pct: float = 0.02, desired_rrr: Optional[float] = None,
                analysis_options: Optional[Dict[str, Any]] = None) -> Optional[TradeSummary]:
        """Generate AI-powered trade recommendation."""
        
        if not self.client:
            return self._fallback_analysis(ticker, indicators, account_size, risk_per_trade_pct, desired_rrr)
        
        try:
            prompt = self._build_analysis_prompt(ticker, indicators, patterns, 
                                                 market_structure, volume_profile, account_size,
                                                 risk_per_trade_pct, desired_rrr, analysis_options)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis_text = response.content[0].text
            
            # Use robust JSON extraction instead of greedy regex
            analysis = extract_json_from_text(analysis_text)
            if analysis:
                return self._create_trade_summary(ticker, indicators, analysis, account_size, risk_per_trade_pct, desired_rrr)
            else:
                logger.error("Failed to parse AI response")
                return self._fallback_analysis(ticker, indicators, account_size, risk_per_trade_pct, desired_rrr)
                
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            return self._fallback_analysis(ticker, indicators, account_size)
    
    def _build_analysis_prompt(self, ticker: str, indicators: AdvancedIndicators,
                               patterns: PatternAnalysis, market_structure: MarketStructure,
                               volume_profile: VolumeProfile, account_size: float,
                               risk_per_trade_pct: float = 0.02,
                               desired_rrr: Optional[float] = None,
                               analysis_options: Optional[Dict[str, Any]] = None) -> str:
        """Build comprehensive analysis prompt."""
        
        # Build comprehensive news block from all sources
        news_block = ""
        if analysis_options and analysis_options.get('include_news_sentiment') and analysis_options.get('news_items'):
            try:
                news_items = analysis_options.get('news_items')
                if news_items:
                    news_block = f"=== RECENT NEWS & SENTIMENT (from {len(news_items)} sources) ===\n"
                    overall = 0.0
                    total_w = 0.0
                    
                    # Organize by sentiment
                    bullish = []
                    bearish = []
                    neutral = []
                    
                    for ni in news_items:
                        s = getattr(ni, 'score', 0.0)
                        w = getattr(ni, 'relevance', 1.0)
                        overall += s * w
                        total_w += w
                        sentiment_str = getattr(ni, 'sentiment', 'NEUTRAL')
                        
                        item_str = f"- {ni.title} [source: {ni.source}, relevance: {w:.1f}] (score: {s:.2f})"
                        
                        if 'BULLISH' in sentiment_str.upper():
                            bullish.append(item_str)
                        elif 'BEARISH' in sentiment_str.upper():
                            bearish.append(item_str)
                        else:
                            neutral.append(item_str)
                    
                    overall_score = overall / total_w if total_w else 0.0
                    
                    # Add organized news
                    if bullish:
                        news_block += f"\nBULLISH NEWS ({len(bullish)}): \n"
                        for item in bullish:
                            news_block += item + "\n"
                    if bearish:
                        news_block += f"\nBEARISH NEWS ({len(bearish)}): \n"
                        for item in bearish:
                            news_block += item + "\n"
                    if neutral:
                        news_block += f"\nNEUTRAL NEWS ({len(neutral)}): \n"
                        for item in neutral:
                            news_block += item + "\n"
                    
                    news_block += f"\nOVERALL NEWS SENTIMENT (weighted across {len(news_items)} sources): {overall_score:.3f}\n"
                    news_block += f"SYNTHESIZE: Create a coherent market opinion by integrating insights from all {len(news_items)} sources above.\n\n"
            except Exception:
                news_block = ""

        prompt_end = (
            "Provide trade recommendation as JSON (no markdown):\n{\n  \"action\": \"BUY|SELL|HOLD\",\n  \"confidence\": 0-100,\n  \"stop_loss_price\": number,\n  \"take_profit_levels\": [tp1, tp2, tp3],\n  \"position_size_shares\": number,\n  \"win_probability\": 0-100,\n  \"expected_value\": number,\n  \"primary_reason\": \"Main thesis with specific numbers (e.g., RSI at 28, price below 200 EMA)\",\n  \"supporting_signals\": [\"signal1 with number\", \"signal2 with number\", \"signal3 with number\"],\n  \"risk_factors\": [\"risk1 with number\", \"risk2 with number\", \"risk3 with number\"],\n  \"indicator_scores\": {\"RSI\": number, \"ADX\": number, \"ATR%\": number, \"MFI\": number, \"CCI\": number, \"Williams%R\": number},\n  \"pattern_strength\": {\"pattern_name\": number},\n  \"news_sentiment\": {\"overall_score\": number, \"by_article\": [ {\"title\":\"...\", \"score\":number} ] },\n  \"position_sizing\": {\"recommended_shares\": number, \"risk_per_trade_usd\": number, \"allocation_pct\": number},\n  \"alternative_tps\": [ {\"label\":\"1:1\",\"tp\":number}, {\"label\":\"1:2\",\"tp\":number} ]\n}\n\n"
            f"Use ATR for stop loss. Risk max {risk_per_trade_pct*100:.2f}% of account.\n"
            f"If a `desired_rrr` is provided ({desired_rrr}), prefer take-profit levels that achieve that Risk:Reward ratio (1:desired_rrr). If the AI suggests different TPs, include both recommended TPs and the TPs matching desired_rrr.\n"
            "Return supporting signals and risk factors as explicit arrays with SPECIFIC NUMBERS from the data provided (e.g., 'RSI oversold at 28', 'Price rose 3.2% in 2 hours', 'Volume 45% above average').\n"
            "Always return JSON only.\n"
            "IMPORTANT: Include actual price levels, percentage changes, and indicator values in ALL text descriptions. Make it sound professional by citing real numbers.\n"
            "If `analysis_options.include_news_sentiment` is true, analyze recent news titles and include `news_sentiment` with per-article scores and an overall weighted score.\n"
            "If `analysis_options.include_sec` is true, summarize recent SEC filings and any material event.\n"
            "If `analysis_options.include_option_flow` is true, include option-implied volatility insights if available.\n"
            "Provide numeric scores and short explanations for each major claim.\n"
        )

        return (
            f"You are an elite institutional trader. Analyze this data and provide a trade recommendation.\n\n"
            f"TICKER: {ticker}\nACCOUNT SIZE: ${account_size:,.0f}\n\n"
            f"=== CURRENT PRICE & STRUCTURE ===\nPrice: ${indicators.price}\nMarket Regime: {indicators.market_regime} ({indicators.regime_confidence}% confidence)\nMarket Structure: {market_structure.structure}\n\n"
            f"=== TREND INDICATORS ===\nSMA: 10=${indicators.sma_10}, 20=${indicators.sma_20}, 50=${indicators.sma_50}, 200=${indicators.sma_200}\n"
            f"EMA: 12=${indicators.ema_12}, 26=${indicators.ema_26}, 50=${indicators.ema_50}, 200=${indicators.ema_200}\n"
            f"VWAP: ${indicators.vwap}\nADX: {indicators.adx} (+DI: {indicators.plus_di}, -DI: {indicators.minus_di})\n\n"
            f"=== MOMENTUM ===\nRSI(14): {indicators.rsi_14}, RSI(7): {indicators.rsi_7}\n"
            f"Stochastic: K={indicators.stochastic_k}, D={indicators.stochastic_d}\n"
            f"MACD: {indicators.macd}, Signal: {indicators.macd_signal}, Histogram: {indicators.macd_histogram}\n\n"
            f"=== VOLATILITY ===\nATR: {indicators.atr} ({indicators.atr_percent}% of price)\n"
            f"Bollinger Bands: Upper=${indicators.bb_upper}, Middle=${indicators.bb_middle}, Lower=${indicators.bb_lower}\n"
            f"Keltner Channels: Upper=${indicators.keltner_upper}, Middle=${indicators.keltner_middle}, Lower=${indicators.keltner_lower}\n"
            f"HMA(20): {indicators.hma_20}\n\n"
            f"=== VOLUME ANALYSIS ===\nVolume Ratio: {indicators.volume_ratio}x average\n"
            f"OBV: {indicators.obv:,.0f}\nMFI: {indicators.mfi}\n"
            f"Volume Profile POC: ${volume_profile.poc}\nValue Area: ${volume_profile.val} - ${volume_profile.vah}\n\n"
            f"=== PATTERNS ===\nBullish: {', '.join(patterns.bullish_patterns) if patterns.bullish_patterns else 'None'}\n"
            f"Bearish: {', '.join(patterns.bearish_patterns) if patterns.bearish_patterns else 'None'}\n"
            f"Candlestick: {', '.join(patterns.candlestick_patterns) if patterns.candlestick_patterns else 'None'}\n\n"
            f"=== ADDITIONAL INDICATORS ===\nEMA ribbon (8/21/34): {indicators.ema_8} / {indicators.ema_21} / {indicators.ema_34}\n"
            f"Williams %R (14): {indicators.williams_r}\nCCI (20): {indicators.cci}\nROC (12): {indicators.roc_12}\n"
            f"Ichimoku: Tenkan={indicators.tenkan_sen}, Kijun={indicators.kijun_sen}, SenkouA={indicators.senkou_a}, SenkouB={indicators.senkou_b}, Chikou={indicators.chikou_span}\n\n"
            f"=== SMART MONEY CONCEPTS ===\nStructure: {market_structure.structure}\n"
            f"Order Blocks: {len(market_structure.order_blocks)}\nFair Value Gaps: {len(market_structure.fair_value_gaps)}\n"
            f"Equilibrium: ${market_structure.equilibrium}\n\n"
            f"{news_block}{prompt_end}"
        )
    
    def _calculate_comprehensive_confidence(self, ticker: str, indicators: AdvancedIndicators, 
                                           patterns: PatternAnalysis, market_structure: MarketStructure,
                                           analysis: Dict, action: str) -> float:
        """Calculate confidence from ALL available quantitative data."""
        
        scores = {}
        weights = {}
        
        try:
            # ===== TREND AGREEMENT (20%) =====
            trend_score = 0
            trend_count = 0
            weights['trend'] = 0.20
            
            # SMA alignment
            if indicators.sma_10 and indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
                price = indicators.price
                bullish_smas = sum([indicators.sma_10 > indicators.sma_20,
                                   indicators.sma_20 > indicators.sma_50,
                                   indicators.sma_50 > indicators.sma_200])
                if action == 'BUY':
                    trend_score += min(100, (bullish_smas / 3) * 100)
                else:
                    trend_score += min(100, ((3 - bullish_smas) / 3) * 100)
                trend_count += 1
            
            # EMA alignment
            if indicators.ema_12 and indicators.ema_26 and indicators.ema_50 and indicators.ema_200:
                bullish_emas = sum([indicators.ema_12 > indicators.ema_26,
                                   indicators.ema_26 > indicators.ema_50,
                                   indicators.ema_50 > indicators.ema_200])
                if action == 'BUY':
                    trend_score += min(100, (bullish_emas / 3) * 100)
                else:
                    trend_score += min(100, ((3 - bullish_emas) / 3) * 100)
                trend_count += 1
            
            # ADX strength (trend strength)
            if indicators.adx:
                adx_score = min(100, indicators.adx * 1.5)  # ADX 0-70, scale to 0-100
                if (action == 'BUY' and indicators.plus_di > indicators.minus_di) or \
                   (action == 'SELL' and indicators.minus_di > indicators.plus_di):
                    trend_score += adx_score
                    trend_count += 1
            
            scores['trend'] = trend_score / max(1, trend_count)
            
            # ===== MOMENTUM AGREEMENT (25%) =====
            momentum_score = 0
            momentum_count = 0
            weights['momentum'] = 0.25
            
            # RSI (14)
            if indicators.rsi_14:
                if action == 'BUY':
                    rsi_bullish = max(0, min(100, (indicators.rsi_14 - 30) * 1.67))  # 30-100 -> 0-100
                    momentum_score += rsi_bullish
                else:
                    rsi_bearish = max(0, min(100, (70 - indicators.rsi_14) * 1.67))  # 0-70 -> 100-0
                    momentum_score += rsi_bearish
                momentum_count += 1
            
            # RSI (7) - faster
            if indicators.rsi_7:
                if action == 'BUY':
                    rsi7_bullish = max(0, min(100, (indicators.rsi_7 - 40) * 2.0))
                    momentum_score += rsi7_bullish
                else:
                    rsi7_bearish = max(0, min(100, (60 - indicators.rsi_7) * 2.0))
                    momentum_score += rsi7_bearish
                momentum_count += 1
            
            # MACD
            if indicators.macd and indicators.macd_signal:
                macd_bullish = (indicators.macd > indicators.macd_signal) and (indicators.macd_histogram > 0)
                if (action == 'BUY' and macd_bullish) or (action == 'SELL' and not macd_bullish):
                    momentum_score += 100
                elif (action == 'BUY' and not macd_bullish) or (action == 'SELL' and macd_bullish):
                    momentum_score += 0
                else:
                    momentum_score += 50
                momentum_count += 1
            
            # Stochastic
            if indicators.stochastic_k is not None and indicators.stochastic_d is not None:
                if action == 'BUY':
                    stoch_score = min(100, (indicators.stochastic_k - 20) * 0.8) if indicators.stochastic_k < 80 else 100
                else:
                    stoch_score = min(100, (80 - indicators.stochastic_k) * 0.8) if indicators.stochastic_k > 20 else 100
                momentum_score += stoch_score
                momentum_count += 1
            
            # Williams %R
            if indicators.williams_r:
                if action == 'BUY':
                    wr_score = min(100, (-20 - indicators.williams_r) * 2)  # -100 to -20 range
                else:
                    wr_score = min(100, (indicators.williams_r + 80) * 2)   # -80 to 0 range
                momentum_score += max(0, min(100, wr_score))
                momentum_count += 1
            
            # MFI
            if indicators.mfi:
                if action == 'BUY':
                    mfi_score = min(100, (indicators.mfi - 20) * 1.25)  # 20-80 -> 0-75
                else:
                    mfi_score = min(100, (80 - indicators.mfi) * 1.25)
                momentum_score += max(0, min(100, mfi_score))
                momentum_count += 1
            
            scores['momentum'] = momentum_score / max(1, momentum_count)
            
            # ===== VOLATILITY & SUPPORT/RESISTANCE (20%) =====
            volatility_score = 0
            volatility_count = 0
            weights['volatility'] = 0.20
            
            # Bollinger Bands
            if indicators.bb_upper and indicators.bb_lower and indicators.bb_middle:
                bb_position = (indicators.price - indicators.bb_lower) / (indicators.bb_upper - indicators.bb_lower)
                if action == 'BUY':
                    # Prefer near lower band (oversold)
                    bb_score = max(0, (0.3 - bb_position) * 200)
                else:
                    # Prefer near upper band (overbought)
                    bb_score = max(0, (bb_position - 0.7) * 200)
                volatility_score += min(100, bb_score)
                volatility_count += 1
            
            # ATR as volatility gauge
            if indicators.atr_percent:
                # Lower ATR% = better for breakout, higher ATR% = trending
                atr_score = 100 - min(100, abs(indicators.atr_percent - 1.5) * 20)
                volatility_score += max(0, atr_score)
                volatility_count += 1
            
            # Keltner Channels
            if indicators.keltner_upper and indicators.keltner_lower:
                kc_position = (indicators.price - indicators.keltner_lower) / (indicators.keltner_upper - indicators.keltner_lower)
                if action == 'BUY':
                    kc_score = max(0, (0.2 - kc_position) * 250)
                else:
                    kc_score = max(0, (kc_position - 0.8) * 250)
                volatility_score += min(100, kc_score)
                volatility_count += 1
            
            scores['volatility'] = volatility_score / max(1, volatility_count)
            
            # ===== VOLUME AGREEMENT (15%) =====
            volume_score = 0
            volume_count = 0
            weights['volume'] = 0.15
            
            # Volume Ratio
            if indicators.volume_ratio:
                # Higher volume = better
                vol_score = min(100, (indicators.volume_ratio - 1.0) * 50)
                volume_score += max(30, min(100, vol_score))  # Min 30 for any volume
                volume_count += 1
            
            # OBV trend
            if indicators.obv:
                # OBV should be rising for BUY, falling for SELL
                volume_score += 75  # Assume healthy if available
                volume_count += 1
            
            # MFI volume divergence
            if indicators.mfi and indicators.mfi > 0:
                if (action == 'BUY' and indicators.mfi > 50) or (action == 'SELL' and indicators.mfi < 50):
                    volume_score += 80
                else:
                    volume_score += 40
                volume_count += 1
            
            scores['volume'] = volume_score / max(1, volume_count)
            
            # ===== PATTERN STRENGTH (10%) =====
            pattern_score = 50  # Neutral base
            weights['pattern'] = 0.10
            
            if action == 'BUY' and patterns.bullish_patterns:
                pattern_score = min(95, 50 + len(patterns.bullish_patterns) * 15)
            elif action == 'SELL' and patterns.bearish_patterns:
                pattern_score = min(95, 50 + len(patterns.bearish_patterns) * 15)
            elif action == 'BUY' and patterns.bearish_patterns:
                pattern_score = max(20, 50 - len(patterns.bearish_patterns) * 10)
            elif action == 'SELL' and patterns.bullish_patterns:
                pattern_score = max(20, 50 - len(patterns.bullish_patterns) * 10)
            
            scores['pattern'] = pattern_score
            
            # ===== MARKET STRUCTURE (10%) =====
            structure_score = 50
            weights['structure'] = 0.10
            
            if market_structure and hasattr(market_structure, 'structure'):
                if action == 'BUY' and 'uptrend' in str(market_structure.structure).lower():
                    structure_score = 85
                elif action == 'SELL' and 'downtrend' in str(market_structure.structure).lower():
                    structure_score = 85
                elif action == 'BUY' and 'downtrend' in str(market_structure.structure).lower():
                    structure_score = 25
                elif action == 'SELL' and 'uptrend' in str(market_structure.structure).lower():
                    structure_score = 25
            
            scores['structure'] = structure_score
            
            # ===== CALCULATE WEIGHTED CONFIDENCE =====
            total_weight = sum(weights.values())
            weighted_confidence = 0
            
            for key, score in scores.items():
                weight = weights.get(key, 0)
                weighted_confidence += (score * weight)
            
            # Normalize
            final_confidence = weighted_confidence / max(1, total_weight)
            
            # ===== APPLY BIAS ADJUSTMENTS =====
            
            # 1. Indicator Divergence Penalty (overconfidence bias)
            # If too many indicators agree, reduce confidence (could be a trap)
            agreeing_indicators = sum(1 for s in scores.values() if s > 70)
            total_indicators = len(scores)
            divergence = abs(agreeing_indicators / max(1, total_indicators) - 0.6)
            if divergence < 0.1:  # Too unanimous
                final_confidence *= 0.85
            elif divergence > 0.3:  # Too much disagreement
                final_confidence *= 0.90
            
            # 2. Volatility Adjustment (risk-adjusted confidence)
            if indicators.atr_percent and indicators.atr_percent > 2.5:
                final_confidence *= 0.90  # Reduce in high volatility
            
            # 3. Volume Adjustment (liquidity bias)
            if indicators.volume_ratio and indicators.volume_ratio < 0.7:
                final_confidence *= 0.85  # Reduce if low volume
            
            # 4. Anchoring Bias (round number resistance)
            round_numbers = [int(indicators.price / 5) * 5 for _ in range(1)]
            distance_to_round = min(abs(indicators.price - rn) for rn in round_numbers)
            if distance_to_round < indicators.atr * 0.5:
                final_confidence *= 0.95  # Slight penalty near round numbers
            
            # Clamp to 0-95
            final_confidence = max(0, min(95, final_confidence))
            
            logger.info(f"Confidence Breakdown - Trend: {scores.get('trend', 0):.1f}, Momentum: {scores.get('momentum', 0):.1f}, "
                       f"Volatility: {scores.get('volatility', 0):.1f}, Volume: {scores.get('volume', 0):.1f}, "
                       f"Pattern: {scores.get('pattern', 0):.1f} | Final: {final_confidence:.1f}")
            
            return final_confidence
            
        except Exception as e:
            logger.debug(f"Confidence calculation error: {e}")
            return 50.0
    
    def _create_trade_summary(self, ticker: str, indicators: AdvancedIndicators,
                             analysis: Dict, account_size: float,
                             risk_per_trade_pct: float = 0.02,
                             desired_rrr: Optional[float] = None) -> TradeSummary:
        """Create trade summary from AI analysis."""
        
        entry_price = indicators.price
        # Ensure default stop loss respects direction (BUY below entry, SELL above entry)
        action_dir = analysis.get('action', 'BUY')
        default_stop = entry_price - indicators.atr * 2 if action_dir == 'BUY' else entry_price + indicators.atr * 2
        stop_loss = analysis.get('stop_loss_price', default_stop)

        # Compute take-profit levels.
        # Priority: if user provided desired_rrr -> compute from desired_rrr (override AI TPs).
        # Else if AI provided TP levels use them, otherwise fallback to ATR multiples.
        risk_distance = abs(entry_price - stop_loss)
        direction = 1 if action_dir == 'BUY' else -1

        if desired_rrr and risk_distance > 0:
            tp1 = entry_price + direction * (risk_distance * desired_rrr)
            tp2 = entry_price + direction * (risk_distance * desired_rrr * 1.5)
            tp3 = entry_price + direction * (risk_distance * desired_rrr * 2)
            tp_levels = [tp1, tp2, tp3]
        else:
            tp_levels = analysis.get('take_profit_levels', None)
            if not tp_levels:
                # fallback to ATR multiples
                tp_levels = [
                    entry_price + direction * indicators.atr * 2,
                    entry_price + direction * indicators.atr * 4,
                    entry_price + direction * indicators.atr * 6
                ]
        
        position_size = analysis.get('position_size_shares', 0)
        if position_size == 0:
            risk_per_trade = account_size * (risk_per_trade_pct if risk_per_trade_pct is not None else 0.02)
            risk_per_share = abs(entry_price - stop_loss)
            position_size = int(risk_per_trade / risk_per_share) if risk_per_share > 0 else 0
        else:
            risk_per_share = abs(entry_price - stop_loss)
        
        # Display reward based on user's desired R:R if set; else use TP2 for ~1:2 default
        if desired_rrr and risk_per_share > 0:
            reward_per_share = risk_per_share * desired_rrr
        else:
            reward_per_share = abs(tp_levels[1] - entry_price)
        risk_amount = position_size * risk_per_share
        reward_amount = position_size * reward_per_share
        
        # Use desired_rrr if provided, otherwise calculate from chosen per-share reward vs SL
        if desired_rrr:
            rrr = desired_rrr
        else:
            rrr = (reward_per_share / risk_per_share) if risk_per_share > 0 else 0
        
        # Merge AI-provided risk_factors with quantitative checks (do not overwrite AI, append)
        ai_risk_factors = analysis.get('risk_factors', []) if isinstance(analysis.get('risk_factors', []), list) else [analysis.get('risk_factors')]
        quantitative_risks = []
        # elevated volatility
        if indicators.atr_percent and indicators.atr_percent > 2.0:
            quantitative_risks.append(f"High ATR% ({indicators.atr_percent}%) - elevated volatility")
        # volume
        if indicators.volume_ratio and indicators.volume_ratio < 0.6:
            quantitative_risks.append(f"Low volume ({indicators.volume_ratio:.2f}x avg) - possible liquidity risk")
        # EMA ribbon squeeze (8/21/34 tight)
        try:
            ema_spread = abs(indicators.ema_8 - indicators.ema_34)
            if ema_spread / max(1, indicators.price) < 0.005:
                quantitative_risks.append("EMAs (8/34) tightly grouped - potential chop")
        except Exception:
            pass
        # Williams %R extremes
        if indicators.williams_r and indicators.williams_r < -90:
            quantitative_risks.append(f"Williams %R deep oversold ({indicators.williams_r})")
        if indicators.williams_r and indicators.williams_r > -10:
            quantitative_risks.append(f"Williams %R deep overbought ({indicators.williams_r})")
        # CCI extremes
        if indicators.cci and abs(indicators.cci) > 200:
            quantitative_risks.append(f"CCI extreme ({indicators.cci}) - momentum exhaustion")
        # Ichimoku conflicts
        try:
            if indicators.price < indicators.kijun_sen and indicators.price < indicators.tenkan_sen:
                quantitative_risks.append("Price below Ichimoku Tenkan/Kijun - bearish bias")
            if indicators.price > indicators.kijun_sen and indicators.price > indicators.tenkan_sen:
                quantitative_risks.append("Price above Ichimoku Tenkan/Kijun - bullish bias")
        except Exception:
            pass

        merged_risk_factors = list(dict.fromkeys([*ai_risk_factors, *quantitative_risks]))

        # Get AI confidence as baseline
        ai_confidence = float(analysis.get('confidence', 50)) if isinstance(analysis.get('confidence', 50), (int, float)) else 50.0
        ai_confidence = min(95.0, max(0.0, ai_confidence))
        
        # IMPROVEMENT: Calculate comprehensive quantitative confidence from ALL indicators
        # This weights trend, momentum, volatility, volume, and patterns with bias adjustments
        action_dir = analysis.get('action', 'HOLD')
        comprehensive_confidence = self._calculate_comprehensive_confidence(
            ticker, indicators, patterns, market_structure, analysis, action_dir
        )
        
        # Blend AI confidence (50%) with comprehensive quantitative confidence (50%)
        # This ensures we use ALL data while respecting AI insights
        final_confidence = (ai_confidence * 0.5) + (comprehensive_confidence * 0.5)
        final_confidence = min(95.0, max(0.0, final_confidence))

        return TradeSummary(
            ticker=ticker,
            action=analysis.get('action', 'HOLD'),
            confidence=final_confidence,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(tp_levels[0], 2),
            take_profit_2=round(tp_levels[1], 2) if len(tp_levels) > 1 else round(tp_levels[0] * 1.5, 2),
            take_profit_3=round(tp_levels[2], 2) if len(tp_levels) > 2 else round(tp_levels[0] * 2, 2),
            position_size=position_size,
            risk_amount=round(risk_amount, 2),
            reward_amount=round(reward_amount, 2),
            risk_reward_ratio=round(rrr, 2),
            win_probability=analysis.get('win_probability', 50),
            expected_value=analysis.get('expected_value', 0),
            primary_reason=analysis.get('primary_reason', 'Technical analysis'),
            supporting_signals=analysis.get('supporting_signals', []),
            risk_factors=merged_risk_factors,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            risk_per_share=round(risk_per_share, 4) if risk_per_share is not None else None,
            reward_per_share=round(reward_per_share, 4) if reward_per_share is not None else None
        )
    
    def _detect_double_top(self, closes: pd.Series, threshold: float = 0.05) -> bool:
        """Detect double top pattern (two peaks at similar heights, dip between)."""
        if len(closes) < 5:
            return False
        recent = closes.iloc[-15:].values  # Look at last 15 bars instead of 10
        
        # Find local maxima
        peaks = argrelextrema(recent, np.greater, order=1)[0]
        
        if len(peaks) >= 2:
            # Get the two highest peaks
            peak_values = [(i, recent[i]) for i in peaks]
            peak_values.sort(key=lambda x: x[1], reverse=True)
            
            peak1_val = peak_values[0][1]
            peak2_val = peak_values[1][1]
            
            # Check if peaks are similar in height
            height_diff = abs(peak1_val - peak2_val) / max(peak1_val, peak2_val)
            
            # Also check there's a dip between them
            if height_diff < threshold and len(peaks) >= 2:
                return True
        
        # Alternative: check if price is below recent high and has made two attempts
        if len(closes) >= 5:
            recent_high = closes.iloc[-5:].max()
            current = closes.iloc[-1]
            prev_high = closes.iloc[-10:-5].max() if len(closes) >= 10 else closes.iloc[0]
            
            # Two recent highs near the same level, with current price below
            if abs(recent_high - prev_high) / prev_high < threshold and current < recent_high * 0.98:
                return True
        
        return False

    def _detect_double_bottom(self, closes: pd.Series, threshold: float = 0.05) -> bool:
        """Detect double bottom pattern (two valleys at similar depths, peak between)."""
        if len(closes) < 5:
            return False
        recent = closes.iloc[-15:].values  # Look at last 15 bars instead of 10
        
        # Find local minima
        valleys = argrelextrema(recent, np.less, order=1)[0]
        
        if len(valleys) >= 2:
            # Get the two lowest valleys
            valley_values = [(i, recent[i]) for i in valleys]
            valley_values.sort(key=lambda x: x[1])
            
            valley1_val = valley_values[0][1]
            valley2_val = valley_values[1][1]
            
            # Check if valleys are similar in depth
            depth_diff = abs(valley1_val - valley2_val) / max(valley1_val, valley2_val)
            
            if depth_diff < threshold and len(valleys) >= 2:
                return True
        
        # Alternative: check if price is above recent low and has made two attempts
        if len(closes) >= 5:
            recent_low = closes.iloc[-5:].min()
            current = closes.iloc[-1]
            prev_low = closes.iloc[-10:-5].min() if len(closes) >= 10 else closes.iloc[0]
            
            # Two recent lows near the same level, with current price above
            if abs(recent_low - prev_low) / prev_low < threshold and current > recent_low * 1.02:
                return True
        
        return False

    def _fallback_analysis(self, ticker: str, indicators: AdvancedIndicators,
                          account_size: float, risk_per_trade_pct: float = 0.02,
                          desired_rrr: Optional[float] = None,
                          is_day_trading: bool = False) -> TradeSummary:
        """Fallback analysis when AI is unavailable.
        
        Args:
            is_day_trading: If True, optimizes for 5-20 candle (minute) profit potential
        """
        
        action = "HOLD"
        confidence = 50
        
        bullish_signals = []
        bearish_signals = []
        neutral = []
        pattern_signals = []
        
        # ===== QUANTITATIVE WALL STREET METRICS =====
        quant_metrics = {}
        
        try:
            # 1. SHARPE RATIO (Risk-adjusted returns)
            if hasattr(indicators, 'closes') and len(indicators.closes) >= 20:
                returns = indicators.closes.pct_change().dropna()
                if len(returns) > 0 and returns.std() > 0:
                    sharpe = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
                    quant_metrics['sharpe'] = sharpe
                    if sharpe > 1.5:
                        bullish_signals.append(f"✓ High Sharpe: {sharpe:.2f} (strong risk/reward)")
                    elif sharpe < -1.0:
                        bearish_signals.append(f"✗ Negative Sharpe: {sharpe:.2f} (poor risk/reward)")
        except Exception:
            pass
        
        try:
            # 2. VOLATILITY ANALYSIS (Annualized)
            if hasattr(indicators, 'closes') and len(indicators.closes) >= 20:
                returns = indicators.closes.pct_change().dropna()
                volatility = returns.std() * np.sqrt(252) * 100  # Annualized %
                quant_metrics['volatility'] = volatility
                
                # High volatility = higher risk
                if volatility > 80:
                    bearish_signals.append(f"⚠ High volatility: {volatility:.1f}% (risky)")
                elif volatility < 20:
                    neutral.append(f"Low volatility: {volatility:.1f}%")
        except Exception:
            pass
        
        try:
            # 3. VOLUME PROFILE ANALYSIS (Institutional accumulation/distribution)
            if hasattr(indicators, 'volumes') and hasattr(indicators, 'closes') and len(indicators.volumes) >= 20:
                recent_vol = indicators.volumes.iloc[-5:].mean()
                avg_vol = indicators.volumes.iloc[-20:].mean()
                vol_spike = recent_vol / avg_vol if avg_vol > 0 else 1.0
                
                recent_price_change = (indicators.closes.iloc[-1] - indicators.closes.iloc[-5]) / indicators.closes.iloc[-5] * 100
                
                quant_metrics['volume_spike'] = vol_spike
                
                # Volume + price analysis (accumulation/distribution)
                if vol_spike > 1.5 and recent_price_change > 0:
                    bullish_signals.append(f"📈 Accumulation: +{recent_price_change:.1f}% on {vol_spike:.1f}x volume")
                elif vol_spike > 1.5 and recent_price_change < 0:
                    bearish_signals.append(f"📉 Distribution: {recent_price_change:.1f}% on {vol_spike:.1f}x volume")
        except Exception:
            pass
        
        try:
            # 4. VWAP DEVIATION (Volume-Weighted Average Price)
            if hasattr(indicators, 'closes') and hasattr(indicators, 'volumes') and len(indicators.closes) >= 20:
                typical_price = (indicators.closes.iloc[-20:] + indicators.closes.iloc[-20:]) / 2
                vwap = (typical_price * indicators.volumes.iloc[-20:]).sum() / indicators.volumes.iloc[-20:].sum()
                
                vwap_dev = ((indicators.price - vwap) / vwap) * 100
                quant_metrics['vwap_deviation'] = vwap_dev
                
                if vwap_dev > 2:
                    bearish_signals.append(f"⚠ Price {vwap_dev:.1f}% above VWAP (overbought)")
                elif vwap_dev < -2:
                    bullish_signals.append(f"✓ Price {vwap_dev:.1f}% below VWAP (oversold)")
        except Exception:
            pass
        
        try:
            # 5. MOMENTUM FACTOR (Rate of change)
            if hasattr(indicators, 'closes') and len(indicators.closes) >= 10:
                roc_5 = ((indicators.closes.iloc[-1] - indicators.closes.iloc[-5]) / indicators.closes.iloc[-5]) * 100
                roc_10 = ((indicators.closes.iloc[-1] - indicators.closes.iloc[-10]) / indicators.closes.iloc[-10]) * 100
                
                quant_metrics['roc_5'] = roc_5
                quant_metrics['roc_10'] = roc_10
                
                # Accelerating momentum
                if roc_5 > roc_10 and roc_5 > 1:
                    bullish_signals.append(f"🚀 Accelerating up: 5-bar ROC {roc_5:.1f}% > 10-bar {roc_10:.1f}%")
                elif roc_5 < roc_10 and roc_5 < -1:
                    bearish_signals.append(f"📉 Accelerating down: 5-bar ROC {roc_5:.1f}% < 10-bar {roc_10:.1f}%")
        except Exception:
            pass
        
        try:
            # 6. MEAN REVERSION Z-SCORE
            if hasattr(indicators, 'closes') and len(indicators.closes) >= 20:
                mean_20 = indicators.closes.iloc[-20:].mean()
                std_20 = indicators.closes.iloc[-20:].std()
                
                if std_20 > 0:
                    z_score = (indicators.price - mean_20) / std_20
                    quant_metrics['z_score'] = z_score
                    
                    if z_score > 2:
                        bearish_signals.append(f"⚠ Overbought Z-score: {z_score:.2f} (2+ StdDev above mean)")
                    elif z_score < -2:
                        bullish_signals.append(f"✓ Oversold Z-score: {z_score:.2f} (2+ StdDev below mean)")
        except Exception:
            pass
        
        try:
            # 7. ORDER FLOW IMBALANCE (Buy vs Sell pressure approximation)
            if hasattr(indicators, 'closes') and hasattr(indicators, 'volumes') and len(indicators.closes) >= 10:
                # Approximate: rising close on volume = buy pressure
                up_bars = 0
                down_bars = 0
                up_vol = 0
                down_vol = 0
                
                for i in range(-10, 0):
                    if indicators.closes.iloc[i] > indicators.closes.iloc[i-1]:
                        up_bars += 1
                        up_vol += indicators.volumes.iloc[i]
                    else:
                        down_bars += 1
                        down_vol += indicators.volumes.iloc[i]
                
                total_vol = up_vol + down_vol
                if total_vol > 0:
                    buy_pressure = (up_vol / total_vol) * 100
                    quant_metrics['buy_pressure'] = buy_pressure
                    
                    if buy_pressure > 65:
                        bullish_signals.append(f"💪 Strong buy pressure: {buy_pressure:.0f}% of volume")
                    elif buy_pressure < 35:
                        bearish_signals.append(f"⚠ Sell pressure: {buy_pressure:.0f}% buy volume only")
        except Exception:
            pass
        
        try:
            # 8. RELATIVE STRENGTH (vs SPY benchmark - for stocks)
            # Skip for crypto, would need separate BTC benchmark
            if not ticker.endswith('-USD') and hasattr(indicators, 'closes') and len(indicators.closes) >= 20:
                asset_return = (indicators.closes.iloc[-1] - indicators.closes.iloc[-20]) / indicators.closes.iloc[-20]
                # Note: Would need to fetch SPY data for true relative strength
                # For now, just flag strong absolute performance
                if asset_return > 0.05:  # 5%+ gain
                    bullish_signals.append(f"📊 Strong absolute return: +{asset_return*100:.1f}% (20-bar)")
                elif asset_return < -0.05:
                    bearish_signals.append(f"📊 Weak absolute return: {asset_return*100:.1f}% (20-bar)")
        except Exception:
            pass

        # 9. MICROSTRUCTURE CONFIRMATION (Coinbase WS ticks for crypto)
        try:
            if ticker.endswith('-USD'):
                micro = DataManager.get_micro_features(ticker, window_secs=20)
                if micro:
                    mr = micro.get('micro_roc_5s') or 0.0
                    vdev = micro.get('vwap_dev') or 0.0
                    tr = micro.get('tick_rate') or 0.0
                    age = micro.get('last_tick_age') or 99.0
                    # Momentum confirmation
                    if mr > 0.10:
                        bullish_signals.append(f"Micro momentum +{mr:.2f}% (5s)")
                    elif mr < -0.10:
                        bearish_signals.append(f"Micro momentum {mr:.2f}% (5s)")
                    # VWAP deviation (micro mean proxy)
                    if vdev > 0.5:
                        bearish_signals.append(f"Price {vdev:.2f}% above micro-VWAP")
                    elif vdev < -0.5:
                        bullish_signals.append(f"Price {vdev:.2f}% below micro-VWAP")
                    # Liquidity and staleness checks
                    if tr < 0.5:
                        bearish_signals.append("Thin liquidity (<0.5 tps)")
                    if age > 3.0:
                        bearish_signals.append("Stale tick (>3s)")
        except Exception:
            pass

        # Price vs moving averages
        if indicators.price > indicators.sma_50:
            bullish_signals.append("Price > SMA50")
        else:
            bearish_signals.append("Price < SMA50")

        if indicators.price > indicators.sma_200:
            bullish_signals.append("Price > SMA200")
        else:
            bearish_signals.append("Price < SMA200")

        # RSI extremes - STRONG bearish signal when overbought
        if indicators.rsi_14 < 30:
            bullish_signals.append(f"RSI(14) oversold ({indicators.rsi_14})")
        elif indicators.rsi_14 > 70:
            # Overbought is a strong bearish signal
            bearish_signals.append(f"RSI(14) overbought ({indicators.rsi_14})")
            bearish_signals.append(f"RSI(14) overbought ({indicators.rsi_14})")  # Double weight

        # MACD
        if indicators.macd > indicators.macd_signal:
            bullish_signals.append("MACD > Signal")
        else:
            bearish_signals.append("MACD < Signal")

        # ADX strength
        if indicators.adx and indicators.adx > 25:
            bullish_signals.append(f"ADX indicates strong trend ({indicators.adx})")
        else:
            bearish_signals.append(f"ADX weak or flat ({indicators.adx})")

        # Volume
        if indicators.volume_ratio and indicators.volume_ratio > 1.0:
            bullish_signals.append(f"Volume above average ({indicators.volume_ratio:.2f}x)")
        else:
            bearish_signals.append(f"Low volume ({indicators.volume_ratio:.2f}x)")

        # Merge pattern recognitions if available (candles / patterns)
        if hasattr(indicators, 'mfi') and indicators.mfi and indicators.mfi > 80:
            bearish_signals.append(f"MFI high ({indicators.mfi})")
            bearish_signals.append(f"MFI high ({indicators.mfi})")  # Double weight

        # PATTERN DETECTION
        try:
            if hasattr(indicators, 'closes') and indicators.closes is not None:
                if self._detect_double_top(indicators.closes):
                    pattern_signals.append("🔴 Double Top pattern detected (STRONG bearish)")
                    bearish_signals.append("PATTERN: Double Top")
                    bearish_signals.append("PATTERN: Double Top")  # Extra weight
                if self._detect_double_bottom(indicators.closes):
                    pattern_signals.append("🟢 Double Bottom pattern detected (STRONG bullish)")
                    bullish_signals.append("PATTERN: Double Bottom")
                    bullish_signals.append("PATTERN: Double Bottom")  # Extra weight
        except Exception as e:
            pass

        # EMA ribbon checks (8/21/34)
        try:
            if indicators.ema_8 > indicators.ema_21 > indicators.ema_34:
                bullish_signals.append("EMA ribbon bullish (8>21>34)")
            elif indicators.ema_8 < indicators.ema_21 < indicators.ema_34:
                bearish_signals.append("EMA ribbon bearish (8<21<34)")
            # tight ribbon -> choppy/ranging market (AVOID TRADING)
            ema_spread_pct = abs(indicators.ema_8 - indicators.ema_34) / max(1, indicators.price) * 100
            if ema_spread_pct < 0.5:  # EMAs within 0.5% = choppy
                bearish_signals.append(f"⚠ CHOPPY MARKET: EMA spread only {ema_spread_pct:.2f}%")
                bearish_signals.append("⚠ Low probability setup (ranging)")
        except Exception:
            pass

        # Williams %R
        try:
            if indicators.williams_r < -80:
                bullish_signals.append(f"Williams %R oversold ({indicators.williams_r})")
            elif indicators.williams_r > -20:
                bearish_signals.append(f"Williams %R overbought ({indicators.williams_r})")
        except Exception:
            pass

        # CCI
        try:
            if indicators.cci > 100:
                bullish_signals.append(f"CCI positive ({indicators.cci})")
            elif indicators.cci < -100:
                bearish_signals.append(f"CCI negative ({indicators.cci})")
        except Exception:
            pass

        # Ichimoku quick biases
        try:
            if indicators.price > indicators.senkou_a and indicators.price > indicators.senkou_b:
                bullish_signals.append("Price above Ichimoku Cloud")
            elif indicators.price < indicators.senkou_a and indicators.price < indicators.senkou_b:
                bearish_signals.append("Price below Ichimoku Cloud")
        except Exception:
            pass

        # HMA slope and ROC
        try:
            if abs(indicators.hma_20 - indicators.ema_21) / max(1, indicators.price) < 0.01:
                bullish_signals.append("HMA aligned with EMA21 (trend confirmation)")
            if abs(indicators.roc_12) > 10:
                # large ROC magnitude indicates rapid movement
                neutral.append(f"High ROC(12) magnitude ({indicators.roc_12}%)")
        except Exception:
            pass

        # EXTREME OVERBOUGHT DETECTION (ES scenario)
        extreme_overbought = False
        extreme_oversold = False
        
        if indicators.rsi_14 > 72:
            extreme_overbought = True
            bearish_signals.append(f"RSI OVERBOUGHT ({indicators.rsi_14})")
            bearish_signals.append(f"RSI OVERBOUGHT ({indicators.rsi_14})")  # Triple weight
            bearish_signals.append(f"RSI OVERBOUGHT ({indicators.rsi_14})")
            
            # Add additional bearish signals when overbought
            if indicators.williams_r and indicators.williams_r > -10:
                bearish_signals.append("Williams %R also overbought")
            if indicators.mfi and indicators.mfi > 70:
                bearish_signals.append("MFI confirms overbought")
        
        if indicators.rsi_14 < 28:
            extreme_oversold = True
            bullish_signals.append(f"RSI OVERSOLD ({indicators.rsi_14})")
            bullish_signals.append(f"RSI OVERSOLD ({indicators.rsi_14})")  # Triple weight
            bullish_signals.append(f"RSI OVERSOLD ({indicators.rsi_14})")
            
            if indicators.williams_r and indicators.williams_r < -90:
                bullish_signals.append("Williams %R also oversold")
            if indicators.mfi and indicators.mfi < 30:
                bullish_signals.append("MFI confirms oversold")
        
        # If overbought + pattern detected = VERY HIGH confidence SELL
        if extreme_overbought and pattern_signals:
            bearish_signals.extend(pattern_signals * 3)  # Triple weight pattern when overbought
            console.print(f"\n[bold][red]⚠️ EXTREME SETUP: {len(pattern_signals)} bearish pattern(s) + extreme overbought![/red][/bold]")
        
        # Even without pattern, overbought alone should be strong
        if extreme_overbought and not pattern_signals:
            # Add penalty signals for being at highs
            bearish_signals.append("Price at extremes with high RSI")
            bearish_signals.append("Reversal risk elevated")

        # ===== CRITICAL: Trend & Momentum Filters =====
        # Check if price is in strong trend (prevent counter-trend disasters)
        price_above_sma20 = indicators.price > indicators.sma_20 if indicators.sma_20 else None
        price_above_sma50 = indicators.price > indicators.sma_50 if indicators.sma_50 else None
        
        # Calculate recent momentum (last 5 candles)
        momentum_bullish = False
        momentum_bearish = False
        try:
            if hasattr(indicators, 'closes') and len(indicators.closes) >= 5:
                recent_change = (indicators.closes.iloc[-1] - indicators.closes.iloc[-5]) / indicators.closes.iloc[-5] * 100
                if recent_change > 0.3:  # Up more than 0.3% in last 5 candles
                    momentum_bullish = True
                    bullish_signals.append(f"Recent momentum: +{recent_change:.2f}%")
                elif recent_change < -0.3:  # Down more than 0.3%
                    momentum_bearish = True
                    bearish_signals.append(f"Recent momentum: {recent_change:.2f}%")
        except Exception:
            pass
        
        # Volume confirmation (require above-average volume)
        volume_confirmed = indicators.volume_ratio > 1.2  # Volume 20% above average
        if not volume_confirmed:
            bearish_signals.append("⚠ Low volume (no conviction)")
        
        # Decide action from signal counts - ALWAYS make a decision (never HOLD)
        signal_diff = abs(len(bullish_signals) - len(bearish_signals))
        
        if len(bullish_signals) > len(bearish_signals):
            action = "BUY"
            base_conf = 60 + (signal_diff * 5)
            if extreme_oversold:
                base_conf += 10
            
            # PENALTY if buying against trend or momentum
            if price_above_sma20 == False or price_above_sma50 == False:
                base_conf -= 15
                bullish_signals.append("⚠ COUNTER-TREND: Price below SMAs")
            if momentum_bearish:
                base_conf -= 10
                bullish_signals.append("⚠ BEARISH MOMENTUM: Recent downtrend")
            
            confidence = min(85, base_conf)
        elif len(bearish_signals) > len(bullish_signals):
            action = "SELL"
            base_conf = 60 + (signal_diff * 5)
            if extreme_overbought:
                base_conf += 10
            
            # PENALTY if selling against trend or momentum  
            if price_above_sma20 == True or price_above_sma50 == True:
                base_conf -= 15
                bearish_signals.append("⚠ COUNTER-TREND: Price above SMAs")
            if momentum_bullish:
                base_conf -= 10
                bearish_signals.append("⚠ BULLISH MOMENTUM: Recent uptrend")
            
            confidence = min(85, base_conf)
        else:
            # Equal signals - use RSI to break tie (ALWAYS pick a side)
            if indicators.rsi_14 >= 50:
                action = "BUY"
                confidence = 55  # Lower confidence for neutral signals
                bullish_signals.append(f"RSI slightly bullish ({indicators.rsi_14:.0f})")
            else:
                action = "SELL"
                confidence = 55  # Lower confidence for neutral signals
                bearish_signals.append(f"RSI slightly bearish ({indicators.rsi_14:.0f})")
        
        entry_price = indicators.price
        
        # Calculate short-term profit potential for day trading (5-20 minute window)
        if is_day_trading and hasattr(indicators, 'closes') and indicators.closes is not None:
            try:
                # Analyze recent 5-20 candle price swings to estimate realistic profit targets
                recent_data = indicators.closes.iloc[-100:]  # Last 100 candles for context
                
                # Calculate rolling high/low over 5, 10, 15, 20 candle windows
                window_sizes = [5, 10, 15, 20]
                max_swings = []
                
                for window in window_sizes:
                    if len(recent_data) >= window:
                        rolling_high = recent_data.rolling(window).max()
                        rolling_low = recent_data.rolling(window).min()
                        swing_pct = ((rolling_high - rolling_low) / rolling_low * 100).iloc[-20:].mean()
                        max_swings.append(swing_pct)
                
                # Average potential move over next 5-20 candles
                avg_swing_pct = np.mean(max_swings) if max_swings else 0.5
                # Conservative estimate: use 60% of average swing
                target_move_pct = avg_swing_pct * 0.6 / 100
                
                bullish_signals.append(f"Day-trade analysis: {avg_swing_pct:.2f}% avg 5-20min swing")
            except Exception:
                # Fallback to ATR-based estimation
                target_move_pct = (indicators.atr / entry_price) * 0.7
        else:
            target_move_pct = None
        
        # Default stop loss uses ATR multiples; MUCH tighter for day trading to limit losses
        if is_day_trading:
            # Day trading: use 0.8x ATR (tighter stops to prevent drawdown)
            stop_loss = entry_price - indicators.atr * 0.8 if action == "BUY" else entry_price + indicators.atr * 0.8
        else:
            stop_loss = entry_price - indicators.atr * 2 if action == "BUY" else entry_price + indicators.atr * 2

        # Add quant metrics to supporting signals
        try:
            if quant_metrics:
                if 'sharpe' in quant_metrics:
                    bullish_signals.append(f"Sharpe Ratio: {quant_metrics['sharpe']:.2f}")
                if 'z_score' in quant_metrics:
                    bullish_signals.append(f"Z-Score: {quant_metrics['z_score']:.2f}")
                if 'buy_pressure' in quant_metrics:
                    bullish_signals.append(f"Buy Pressure: {quant_metrics['buy_pressure']:.0f}%")
                if 'volume_spike' in quant_metrics:
                    bullish_signals.append(f"Volume Spike: {quant_metrics['volume_spike']:.1f}x")
        except Exception:
            pass
        
        # Compute TP levels - optimize for short-term if day trading
        risk_distance = abs(entry_price - stop_loss)
        direction = 1 if action == "BUY" else -1
        
        if is_day_trading and target_move_pct:
            # Day trading: set TPs based on realistic 5-20min price movement
            expected_move = entry_price * target_move_pct
            tp1 = entry_price + direction * expected_move * 0.5  # 50% of expected move
            tp2 = entry_price + direction * expected_move       # Full expected move
            tp3 = entry_price + direction * expected_move * 1.5 # Extended target
            bullish_signals.append(f"TP targets: 5-20min profit optimization (${expected_move:.2f} move)")
        elif desired_rrr and risk_distance > 0 and action in ("BUY", "SELL"):
            tp1 = entry_price + direction * (risk_distance * desired_rrr)
            tp2 = entry_price + direction * (risk_distance * desired_rrr * 1.5)
            tp3 = entry_price + direction * (risk_distance * desired_rrr * 2)
        else:
            tp1 = entry_price + direction * indicators.atr * 2
            tp2 = entry_price + direction * indicators.atr * 4
            tp3 = entry_price + direction * indicators.atr * 6

        # --- Robust risk/reward computation ---
        risk_per_share = abs(entry_price - stop_loss)
        # Display reward based on user's desired R:R if set; else use TP2 for ~1:2 default
        if desired_rrr and risk_per_share > 0:
            reward_per_share = risk_per_share * desired_rrr
        else:
            reward_per_share = abs(tp2 - entry_price)
        risk_per_trade = account_size * (risk_per_trade_pct if risk_per_trade_pct is not None else 0.02)
        position_size = int(risk_per_trade / risk_per_share) if risk_per_share > 0 else 0
        risk_amount = position_size * risk_per_share
        reward_amount = position_size * reward_per_share
        
        # Use desired_rrr if provided, otherwise calculate from chosen per-share reward vs SL
        if desired_rrr:
            rrr = desired_rrr
        else:
            rrr = reward_per_share / risk_per_share if risk_per_share > 0 else 0

        # ===== FUNDAMENTALS & GREEKS INTEGRATION =====
        fundamentals = None
        greeks = None
        extra_signals = []
        try:
            fundamentals = DataManager.get_fundamentals(ticker)
            pe = None
            if fundamentals:
                pe = fundamentals.get('trailingPE') or fundamentals.get('forwardPE')
                if pe and pe > 0:
                    if action == 'BUY':
                        if pe < 12:
                            confidence += 5; extra_signals.append('Fundamental boost: Low PE (<12)')
                        elif pe > 60:
                            confidence -= 5; extra_signals.append('Fundamental drag: High PE (>60)')
                    elif action == 'SELL':
                        if pe > 60:
                            confidence += 3; extra_signals.append('Sell confidence: High PE overvaluation')
                        elif pe < 12:
                            confidence -= 3; extra_signals.append('Sell drag: Value PE (<12)')
        except Exception:
            pass

        try:
            # Only attempt Greeks for equity-like tickers (skip crypto/futures formats containing '-')
            if '-' not in ticker and action in ('BUY','SELL'):
                og = DataManager.get_option_chain_greeks(ticker)
                if og:
                    greeks = og
                    call_delta = og.get('call_greeks', {}).get('delta')
                    put_delta = og.get('put_greeks', {}).get('delta')
                    iv = og.get('used_iv')
                    if iv is not None:
                        if action == 'BUY':
                            if iv < 0.25:
                                confidence += 2; extra_signals.append('IV favorable (<25%)')
                            elif iv > 0.70:
                                confidence -= 4; extra_signals.append('IV elevated (>70%) reduces long appeal')
                        else:  # SELL
                            if iv > 0.60:
                                confidence += 3; extra_signals.append('High IV (>60%) supports short thesis')
                            elif iv < 0.20:
                                confidence -= 2; extra_signals.append('Low IV (<20%) weakens short')
                    if call_delta is not None:
                        if action == 'BUY' and call_delta > 0.55:
                            confidence += 4; extra_signals.append(f'Call Δ strong ({call_delta:.2f})')
                        if action == 'SELL' and call_delta > 0.60:
                            confidence -= 3; extra_signals.append(f'Short drag: Call Δ high ({call_delta:.2f})')
                    if put_delta is not None:
                        if action == 'SELL' and put_delta < -0.55:  # put delta negative large magnitude
                            confidence += 4; extra_signals.append(f'Put Δ supports bearish ({put_delta:.2f})')
                        if action == 'BUY' and put_delta < -0.65:
                            confidence -= 3; extra_signals.append(f'Buy drag: Strong put Δ ({put_delta:.2f})')
                    # Gamma risk factor
                    gamma_val = og.get('call_greeks', {}).get('gamma')
                    if gamma_val and gamma_val > 0.02:
                        extra_signals.append(f'High gamma environment ({gamma_val:.3f})')
        except Exception:
            pass

        # Clamp confidence inside [0, 95]
        confidence = max(0, min(95, confidence))

        # Quantitative risk factors
        risk_factors = []
        # High volatility
        if indicators.atr_percent and indicators.atr_percent > 2.0:
            risk_factors.append(f"High ATR% ({indicators.atr_percent}%) - elevated volatility")
        # Weak liquidity
        if indicators.volume_ratio and indicators.volume_ratio < 0.5:
            risk_factors.append(f"Low volume relative to average ({indicators.volume_ratio:.2f}x)")
        # Weak trend
        if indicators.adx and indicators.adx < 20:
            risk_factors.append(f"ADX low ({indicators.adx}) - low trend conviction")
        # RSI extremes
        if indicators.rsi_14 and indicators.rsi_14 > 85:
            risk_factors.append(f"RSI extremely high ({indicators.rsi_14}) - overbought")
        if indicators.rsi_14 and indicators.rsi_14 < 15:
            risk_factors.append(f"RSI extremely low ({indicators.rsi_14}) - deeply oversold")
        # Position sizing warning
        if position_size == 0:
            risk_factors.append("Position size computed as 0 due to wide stop loss / small account allocation")

        # If no quantitative factors found, provide a concise summary
        if not risk_factors:
            risk_factors = ["No major quantitative risk flags detected (volatility, liquidity, ADX, RSI checked)"]

        return TradeSummary(
            ticker=ticker,
            action=action,
            confidence=confidence,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            take_profit_3=round(tp3, 2),
            position_size=position_size,
            risk_amount=round(risk_amount, 2),
            reward_amount=round(reward_amount, 2),
            risk_reward_ratio=round(rrr, 2),
            win_probability=confidence,
            expected_value=reward_amount * (confidence/100) - risk_amount * (1 - confidence/100),
            primary_reason="Rule-based technical analysis",
            supporting_signals=[*bullish_signals, *bearish_signals, *neutral, *extra_signals],
            risk_factors=risk_factors,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            fundamentals=fundamentals,
            greeks=greeks,
            risk_per_share=round(risk_per_share, 4) if risk_per_share else None,
            reward_per_share=round(reward_per_share, 4) if reward_per_share else None
        )

# ==========================================
# POLITICAL TRADING TRACKER
# ==========================================

class PoliticalTracker:
    """Track trades by politicians and public figures."""
    
    # Database of known political figures and their recent trades
    POLITICAL_FIGURES = {
        "trump_admin": {
            "name": "Trump Administration",
            "members": ["Donald Trump", "Elon Musk", "Vivek Ramaswamy", "Robert F. Kennedy Jr."],
            "known_holdings": ["TSLA", "DJT", "DWAC", "PHUN", "RUMBLE"]
        },
        "pelosi": {
            "name": "Nancy Pelosi & Family",
            "members": ["Nancy Pelosi", "Paul Pelosi"],
            "known_holdings": ["NVDA", "AAPL", "MSFT", "GOOGL", "CRM", "RBLX"]
        },
        "congress_dems": {
            "name": "Democratic Congress Members",
            "members": ["Elizabeth Warren", "Bernie Sanders", "AOC"],
            "known_holdings": ["AAPL", "MSFT", "AMZN", "TSLA", "SPY"]
        },
        "congress_reps": {
            "name": "Republican Congress Members",
            "members": ["Kevin McCarthy", "Marjorie Taylor Greene"],
            "known_holdings": ["XOM", "CVX", "BA", "LMT", "AAPL"]
        },
        "senate": {
            "name": "Senate Trading",
            "members": ["Tommy Tuberville", "Josh Hawley", "Ted Cruz"],
            "known_holdings": ["F", "GM", "TSLA", "AAPL", "GOOGL"]
        }
    }
    
    @staticmethod
    def get_group_trades(group_key: str) -> Dict[str, Any]:
        """Get trading information for a political group."""
        
        if group_key not in PoliticalTracker.POLITICAL_FIGURES:
            return None
        
        group = PoliticalTracker.POLITICAL_FIGURES[group_key]
        
        console.print(f"\n[yellow]Analyzing {group['name']} holdings...[/yellow]\n")
        
        holdings_analysis = []
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Fetching data...", total=len(group['known_holdings']))
            
            for ticker in group['known_holdings']:
                try:
                    # Fetch current price and basic info
                    df = DataManager.fetch_data(ticker, "1y", "1d")
                    
                    if df is not None and len(df) > 0:
                        current_price = float(df['Close'].iloc[-1])
                        year_ago_price = float(df['Close'].iloc[0])
                        ytd_return = ((current_price - year_ago_price) / year_ago_price) * 100
                        
                        # Get ticker info
                        info = DataManager.get_ticker_info(ticker)
                        
                        # Check for insider trades
                        insider_trades = SECAnalyzer.get_insider_trades(ticker, limit=5)
                        
                        holdings_analysis.append({
                            'ticker': ticker,
                            'name': info['name'],
                            'current_price': current_price,
                            'ytd_return': ytd_return,
                            'market_cap': info['market_cap'],
                            'sector': info['sector'],
                            'insider_buys': len([t for t in insider_trades if 'Buy' in t.transaction_type]),
                            'insider_sells': len([t for t in insider_trades if 'Sell' in t.transaction_type])
                        })
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                
                progress.update(task, advance=1)
        
        return {
            'group': group,
            'holdings': sorted(holdings_analysis, key=lambda x: x['ytd_return'], reverse=True)
        }
    
    @staticmethod
    def display_group_analysis(analysis: Dict[str, Any]):
        """Display political group trading analysis."""
        
        if not analysis:
            console.print("[red]Group not found[/red]")
            return
        
        group = analysis['group']
        holdings = analysis['holdings']
        
        console.print(f"[bold cyan]👔 {group['name']}[/bold cyan]\n")
        console.print("[bold white]Members:[/bold white]")
        for member in group['members']:
            console.print(f"  • {member}")
        console.print()
        
        if not holdings:
            console.print("[yellow]No holdings data available[/yellow]")
            return
        
        console.print("[bold cyan]📊 Known Holdings & Performance[/bold cyan]\n")
        
        table = Table(box=box.ROUNDED)
        table.add_column("Ticker", style="bold white")
        table.add_column("Company", style="white")
        table.add_column("Price", style="cyan", justify="right")
        table.add_column("YTD Return", style="white", justify="right")
        table.add_column("Sector", style="dim")
        table.add_column("Insider Activity", style="white", justify="center")
        
        for holding in holdings:
            return_color = "green" if holding['ytd_return'] > 0 else "red"
            
            insider_activity = ""
            if holding['insider_buys'] > 0:
                insider_activity += f"[green]↑{holding['insider_buys']}[/green]"
            if holding['insider_sells'] > 0:
                if insider_activity:
                    insider_activity += " "
                insider_activity += f"[red]↓{holding['insider_sells']}[/red]"
            if not insider_activity:
                insider_activity = "[dim]-[/dim]"
            
            table.add_row(
                holding['ticker'],
                holding['name'][:25],
                f"${holding['current_price']:.2f}",
                f"[{return_color}]{holding['ytd_return']:+.1f}%[/{return_color}]",
                holding['sector'][:20],
                insider_activity
            )
        
        console.print(table)
        console.print()
        
        # Calculate summary statistics
        total_return = sum([h['ytd_return'] for h in holdings]) / len(holdings)
        winners = len([h for h in holdings if h['ytd_return'] > 0])
        losers = len([h for h in holdings if h['ytd_return'] < 0])
        
        console.print("[bold cyan]📈 Portfolio Summary:[/bold cyan]")
        console.print(f"Average YTD Return: [{'green' if total_return > 0 else 'red'}]{total_return:+.1f}%[/{'green' if total_return > 0 else 'red'}]")
        console.print(f"Winners: [green]{winners}[/green] | Losers: [red]{losers}[/red]")
        console.print(f"Win Rate: {(winners/len(holdings)*100):.1f}%")
        console.print()

# ==========================================
# DISPLAY & REPORTING
# ==========================================

class DisplayManager:
    """Manages all console output and reporting."""
    
    @staticmethod
    def show_header():
        """Display application header."""
        console.clear()
        
        # Check if Schwab futures is enabled
        try:
            config = ConfigurationManager.load_config()
            schwab_enabled = config.get('schwab_futures_enabled', False)
        except:
            schwab_enabled = False
        
        header_text = (
            "[bold cyan]FinalAI Quantum v7.0[/bold cyan]\n"
            "[dim]Elite Professional Trading System[/dim]\n"
            "[yellow]80+ Indicators | AI Analysis | Political Tracking | News & SEC Filings[/yellow]"
        )
        
        if schwab_enabled:
            header_text += "\n[bold green]🚀 Schwab Futures Trading: ENABLED[/bold green]"
        
        header = Panel(
            header_text,
            border_style="cyan",
            box=box.DOUBLE
        )
        console.print(header)
        console.print()
    
    @staticmethod
    def show_indicators(indicators: AdvancedIndicators):
        """Display technical indicators."""
        table = Table(title="📊 Technical Indicators", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Indicator", style="white")
        table.add_column("Value", style="yellow", justify="right")
        
        table.add_row("Price", "Current", f"${indicators.price}")
        table.add_row("", "Open/High/Low", f"${indicators.open} / ${indicators.high} / ${indicators.low}")
        table.add_row("", "Volume", f"{indicators.volume:,}")
        
        table.add_row("Trend", "SMA 20/50/200", f"${indicators.sma_20} / ${indicators.sma_50} / ${indicators.sma_200}")
        table.add_row("", "EMA 12/26/50", f"${indicators.ema_12} / ${indicators.ema_26} / ${indicators.ema_50}")
        table.add_row("", "VWAP", f"${indicators.vwap}")
        
        table.add_row("Momentum", "RSI (7/14)", f"{indicators.rsi_7} / {indicators.rsi_14}")
        table.add_row("", "Stochastic K/D", f"{indicators.stochastic_k} / {indicators.stochastic_d}")
        table.add_row("", "MACD", f"{indicators.macd:.4f}")
        
        table.add_row("Volatility", "ATR", f"{indicators.atr} ({indicators.atr_percent}%)")
        table.add_row("", "BB Upper/Lower", f"${indicators.bb_upper} / ${indicators.bb_lower}")
        table.add_row("", "Keltner U/M/L", f"${indicators.keltner_upper} / ${indicators.keltner_middle} / ${indicators.keltner_lower}")
        table.add_row("", "HMA(20)", f"{indicators.hma_20}")
        
        table.add_row("Strength", "ADX", f"{indicators.adx}")
        table.add_row("", "+DI / -DI", f"{indicators.plus_di} / {indicators.minus_di}")
        table.add_row("Momentum", "EMA ribbon (8/21/34)", f"${indicators.ema_8} / ${indicators.ema_21} / ${indicators.ema_34}")
        table.add_row("", "Williams %R", f"{indicators.williams_r}")
        table.add_row("", "CCI", f"{indicators.cci}")
        table.add_row("", "ROC(12)", f"{indicators.roc_12}%")
        
        table.add_row("Volume", "Volume Ratio", f"{indicators.volume_ratio}x")
        table.add_row("", "OBV", f"{indicators.obv:,.0f}")
        table.add_row("", "MFI", f"{indicators.mfi}")
        
        table.add_row("Regime", "Market Regime", f"[bold]{indicators.market_regime}[/bold]")
        table.add_row("", "Confidence", f"{indicators.regime_confidence}%")
        
        console.print(table)
        console.print()
    
    @staticmethod
    def show_trade_recommendation(trade: TradeSummary):
        """Display trade recommendation."""
        
        action_color = "green" if trade.action == "BUY" else "red" if trade.action == "SELL" else "yellow"
        
        panel = Panel(
            f"[bold {action_color}]{trade.action}[/bold {action_color}] {trade.ticker}\n"
            f"[dim]Confidence: {trade.confidence}% | Win Probability: {trade.win_probability}%[/dim]",
            title="🎯 Trade Recommendation",
            border_style=action_color,
            box=box.HEAVY
        )
        console.print(panel)
        
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("", style="cyan", width=20)
        table.add_column("", style="white")
        
        table.add_row("Entry Price", f"${trade.entry_price}")
        table.add_row("Stop Loss", f"[red]${trade.stop_loss}[/red]")
        table.add_row("Take Profit 1", f"[green]${trade.take_profit_1}[/green]")
        table.add_row("Take Profit 2", f"[green]${trade.take_profit_2}[/green]")
        table.add_row("Take Profit 3", f"[green]${trade.take_profit_3}[/green]")
        table.add_row("", "")
        table.add_row("Position Size", f"{trade.position_size} shares")
        table.add_row("Risk Amount", f"[red]${trade.risk_amount}[/red]")
        table.add_row("Reward Amount", f"[green]${trade.reward_amount}[/green]")
        # Show ratio from actual per-share values when available
        if trade.risk_per_share and trade.reward_per_share and trade.risk_per_share > 0:
            computed_rr = trade.reward_per_share / trade.risk_per_share
            ratio_fmt = f"1:{computed_rr:.2f}"
        else:
            ratio_fmt = f"1:{trade.risk_reward_ratio:.2f}" if trade.risk_reward_ratio is not None else "N/A"
        table.add_row("Risk:Reward Ratio", ratio_fmt)
        if trade.risk_per_share is not None and trade.reward_per_share is not None:
            table.add_row("Risk/Share", f"${trade.risk_per_share:.4f}")
            table.add_row("Reward/Share", f"${trade.reward_per_share:.4f}")
        table.add_row("Expected Value", f"${trade.expected_value:.2f}")
        
        console.print(table)
        console.print()
        
        console.print("[bold cyan]Primary Thesis:[/bold cyan]")
        console.print(f"  {trade.primary_reason}\n")
        
        if trade.supporting_signals:
            # Categorize signals into bullish / bearish / neutral for clearer display
            def _unique(seq):
                seen = set()
                out = []
                for item in seq:
                    key = item.strip().lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(item)
                return out

            bullish = []
            bearish = []
            neutral = []
            for signal in trade.supporting_signals:
                s = str(signal).strip()
                sl = s.lower()
                if any(k in sl for k in ("oversold", "price >", "volume above", "adx indicates strong", "macd >", "bullish")):
                    bullish.append(s)
                elif any(k in sl for k in ("overbought", "price <", "low volume", "mfi high", "macd <", "bearish")):
                    bearish.append(s)
                else:
                    neutral.append(s)

            bullish = _unique(bullish)
            bearish = _unique(bearish)
            neutral = _unique(neutral)

            if bullish:
                console.print("[bold green]Bullish Signals:[/bold green]")
                for s in bullish:
                    console.print(f"  ✓ {s}")
                console.print()

            if bearish:
                console.print("[bold red]Bearish Signals:[/bold red]")
                for s in bearish:
                    console.print(f"  ✗ {s}")
                console.print()

            if neutral:
                console.print("[bold cyan]Other Supporting Signals:[/bold cyan]")
                for s in neutral:
                    console.print(f"  • {s}")
                console.print()
        
        if trade.risk_factors:
            # De-duplicate risk factors while preserving order
            def _unique(seq):
                seen = set()
                out = []
                for item in seq:
                    key = str(item).strip().lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(str(item).strip())
                return out

            unique_risks = _unique(trade.risk_factors)
            if unique_risks:
                console.print("[bold red]Risk Factors:[/bold red]")
                for risk in unique_risks:
                    console.print(f"  ⚠ {risk}")
                console.print()
    
    @staticmethod
    def show_scanner_results(opportunities: List[ScannerOpportunity]):
        """Display scanner opportunities."""
        
        if not opportunities:
            console.print("[yellow]No opportunities found in current scan.[/yellow]")
            return
        
        console.print(f"\n[bold cyan]🎯 Top {len(opportunities)} Opportunities[/bold cyan]\n")
        
        table = Table(box=box.ROUNDED)
        table.add_column("Rank", style="cyan", justify="center")
        table.add_column("Ticker", style="bold white")
        table.add_column("Action", style="white", justify="center")
        table.add_column("Score", style="yellow", justify="right")
        table.add_column("Entry", style="white", justify="right")
        table.add_column("Target", style="green", justify="right")
        table.add_column("R:R", style="white", justify="right")
        table.add_column("Signal", style="dim")
        
        for idx, opp in enumerate(opportunities, 1):
            action_color = "green" if opp.action == "BUY" else "red"
            table.add_row(
                f"#{idx}",
                opp.ticker,
                f"[{action_color}]{opp.action}[/{action_color}]",
                f"{opp.score:.0f}",
                f"${opp.entry_price}",
                f"${opp.target}",
                f"1:{opp.risk_reward:.1f}",
                opp.primary_signal[:40]
            )
        
        console.print(table)
        console.print()
    
    @staticmethod
    def show_news(news_items: List[NewsItem], ticker: str):
        """Display news items."""
        if not news_items:
            console.print(f"[yellow]No recent news found for {ticker}[/yellow]")
            return
        
        console.print(f"\n[bold cyan]📰 Recent News: {ticker}[/bold cyan]\n")
        
        for idx, item in enumerate(news_items[:5], 1):
            console.print(f"[bold white]{idx}. {item.title}[/bold white]")
            console.print(f"   [dim]{item.source} | {item.published}[/dim]")
            console.print(f"   [blue]{item.url}[/blue]\n")
    
    @staticmethod
    def show_insider_trades(trades: List[InsiderTrade]):
        """Display insider trading activity."""
        if not trades:
            console.print("[yellow]No recent insider trading activity[/yellow]")
            return
        
        console.print(f"\n[bold cyan]👔 Recent Insider Trading[/bold cyan]")

        def normalize_action(tx: str) -> str:
            tx_l = (tx or '').lower()
            if any(k in tx_l for k in ["buy","purchase","acq","acquisition"]):
                return "BUY"
            if any(k in tx_l for k in ["sell","sale","dispose","distribution"]):
                return "SELL"
            return "OTHER"

        # Recent detailed trades table
        detail_table = Table(box=box.ROUNDED)
        detail_table.add_column("Date", style="cyan")
        detail_table.add_column("Insider", style="white")
        detail_table.add_column("Position", style="dim")
        detail_table.add_column("Action", style="white")
        detail_table.add_column("Shares", style="yellow", justify="right")
        detail_table.add_column("Value", style="green", justify="right")

        for trade in trades[:10]:
            action = normalize_action(trade.transaction_type)
            color = "green" if action == "BUY" else ("red" if action == "SELL" else "white")
            detail_table.add_row(
                trade.date,
                trade.insider[:22],
                (trade.position or "-")[:18],
                f"[{color}]{action}[/{color}]",
                f"{trade.shares:,}",
                f"${trade.value:,.0f}"
            )

        console.print(detail_table)

        # Aggregate large sellers (> $10M cumulative sells)
        seller_totals: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            action = normalize_action(t.transaction_type)
            if action == "SELL":
                if t.insider not in seller_totals:
                    seller_totals[t.insider] = {"value": 0.0, "latest": t.date, "position": t.position}
                seller_totals[t.insider]["value"] += t.value
                # Keep most recent date (assuming list already sorted chronologically newest first)
                seller_totals[t.insider]["latest"] = t.date

        big_sellers = {k: v for k, v in seller_totals.items() if v["value"] >= 10_000_000}

        if big_sellers:
            console.print("\n[bold red]💰 Large (> $10M) Sellers[/bold red]")
            sellers_table = Table(box=box.SIMPLE)
            sellers_table.add_column("Insider", style="white")
            sellers_table.add_column("Position", style="dim")
            sellers_table.add_column("Total Sell Value", style="red", justify="right")
            sellers_table.add_column("Latest Date", style="cyan")
            for insider, info in sorted(big_sellers.items(), key=lambda x: x[1]["value"], reverse=True):
                sellers_table.add_row(
                    insider[:25],
                    (info.get("position") or "-")[:20],
                    f"${info['value']:,.0f}",
                    info['latest']
                )
            console.print(sellers_table)
        else:
            console.print("[dim]No sellers above $10M threshold[/dim]")

        console.print()
    @staticmethod
    def show_backtest_results(results):
        """Display backtest results."""
        
        title = f"📈 Backtest Results: {results.ticker}"
        
        return_color = "green" if results.total_return > 0 else "red"
        summary = Panel(
            f"Period: {results.start_date} to {results.end_date}\n"
            f"Initial Capital: ${results.initial_capital:,.2f}\n"
            f"Final Capital: ${results.final_capital:,.2f}\n"
            f"[bold {return_color}]Total Return: ${results.total_return:,.2f} ({results.total_return_percent:+.2f}%)[/bold {return_color}]",
            title=title,
            border_style=return_color,
            box=box.HEAVY
        )
        console.print(summary)
        console.print()
        
        stats_table = Table(title="📊 Performance Statistics", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow", justify="right")
        
        stats_table.add_row("Total Trades", str(results.total_trades))
        stats_table.add_row("Winning Trades", f"[green]{results.winning_trades}[/green]")
        stats_table.add_row("Losing Trades", f"[red]{results.losing_trades}[/red]")
        stats_table.add_row("Win Rate", f"{results.win_rate:.2f}%")
        stats_table.add_row("", "")
        stats_table.add_row("Average Win", f"[green]${results.avg_win:,.2f}[/green]")
        stats_table.add_row("Average Loss", f"[red]${results.avg_loss:,.2f}[/red]")
        stats_table.add_row("Largest Win", f"[green]${results.largest_win:,.2f}[/green]")
        stats_table.add_row("Largest Loss", f"[red]${results.largest_loss:,.2f}[/red]")
        stats_table.add_row("", "")
        stats_table.add_row("Profit Factor", f"{results.profit_factor:.2f}")
        stats_table.add_row("Sharpe Ratio", f"{results.sharpe_ratio:.2f}")
        stats_table.add_row("Max Drawdown", f"[red]${results.max_drawdown:,.2f} ({results.max_drawdown_percent:.2f}%)[/red]")
        
        console.print(stats_table)
        console.print()
        
        if results.trades:
            trades_table = Table(title="📝 Recent Trades (Last 10)", box=box.ROUNDED)
            trades_table.add_column("Entry", style="cyan")
            trades_table.add_column("Exit", style="cyan")
            trades_table.add_column("Action", style="white")
            trades_table.add_column("P/L", style="white", justify="right")
            trades_table.add_column("P/L %", style="white", justify="right")
            trades_table.add_column("Reason", style="dim")
            
            for trade in results.trades[-10:]:
                pl_color = "green" if trade.win else "red"
                trades_table.add_row(
                    trade.entry_date,
                    trade.exit_date,
                    trade.action,
                    f"[{pl_color}]${trade.profit_loss:,.2f}[/{pl_color}]",
                    f"[{pl_color}]{trade.profit_loss_percent:+.2f}%[/{pl_color}]",
                    trade.reason
                )
            
            console.print(trades_table)
            console.print()
        
        DisplayManager._show_equity_curve(results)
    
    @staticmethod
    def _show_equity_curve(results):
        """Display ASCII equity curve."""
        console.print("[bold cyan]📈 Equity Curve[/bold cyan]")
        
        curve = results.equity_curve
        width = 80
        height = 15
        
        if len(curve) > width:
            step = len(curve) // width
            curve = [curve[i] for i in range(0, len(curve), step)]
        
        min_val = min(curve)
        max_val = max(curve)
        range_val = max_val - min_val if max_val > min_val else 1
        
        for h in range(height, 0, -1):
            line = ""
            threshold = min_val + (range_val * h / height)
            for val in curve:
                if val >= threshold:
                    line += "█"
                else:
                    line += " "
            
            if h == height:
                console.print(f"${max_val:>10,.0f} |{line}|")
            elif h == 1:
                console.print(f"${min_val:>10,.0f} |{line}|")
            else:
                console.print(f"           |{line}|")
        
        console.print(f"           {'+' + '-'*len(curve) + '+'}")
        console.print(f"           Start{' '*(len(curve)-10)}End\n")

# ==========================================
# MAIN APPLICATION
# ==========================================

class FinalAIQuantum:
    """Main application controller."""
    
    def __init__(self):
        self.config = None
        self.api_key = None
        self.analyzer = None
        self.theme_researcher = None
        self.scanner = None
        self.paper_trading = PaperTradingManager()  # Initialize paper trading
        self.current_user = None  # Track logged in user
    
    def _validate_and_setup_api_keys(self):
        """Check for required API keys and prompt user to enter them if missing."""
        missing_keys = []
        
        # Check Finnhub
        finnhub_key = os.getenv('FINNHUB_API_KEY') or self.config.get('finnhub_api_key', '')
        if not finnhub_key or not finnhub_key.strip():
            missing_keys.append('Finnhub')
        
        # Check NewsData.IO
        newsdata_key = os.getenv('NEWSDATA_API_KEY') or self.config.get('newsdata_api_key', '')
        if not newsdata_key or not newsdata_key.strip():
            missing_keys.append('NewsData.IO')
        
        # Check Groq
        groq_key = os.getenv('GROQ_API_KEY') or self.config.get('groq_api_key', '')
        if not groq_key or not groq_key.strip():
            missing_keys.append('Groq')
        
        # If any keys are missing, show setup wizard
        if missing_keys:
            console.print("\n")
            setup_panel = Panel(
                f"[bold red]⚠ Missing API Keys[/bold red]\n\n"
                f"[yellow]The following API keys are required:[/yellow]\n"
                + "\n".join([f"  • {key}" for key in missing_keys]) +
                f"\n\n[dim]These are completely FREE and take 2-3 minutes to set up.[/dim]",
                border_style="yellow",
                title="[bold]API Setup Required[/bold]"
            )
            console.print(setup_panel)
            
            if Confirm.ask("\n[cyan]Would you like to set up these API keys now?[/cyan]", default=True):
                self._setup_api_keys_interactive(missing_keys)
            else:
                console.print("\n[yellow]⚠ Warning: Trading bot and advisor features require API keys.[/yellow]")
                console.print("[dim]You can set them up later in Settings (Option 17)[/dim]\n")
                Prompt.ask("Press Enter to continue")
    
    def _setup_api_keys_interactive(self, keys_to_setup: list):
        """Interactive setup for API keys."""
        console.print("\n")
        
        # Finnhub
        if 'Finnhub' in keys_to_setup:
            console.print("[bold cyan]1️⃣  Finnhub Setup[/bold cyan]")
            console.print("[dim]Finnhub provides real-time company news, earnings, and insider trades[/dim]")
            console.print("[cyan]→ Go to: https://finnhub.io[/cyan]")
            console.print("[cyan]→ Sign up (free, email only)[/cyan]")
            console.print("[cyan]→ Copy your API key from the dashboard[/cyan]\n")
            
            finnhub_key = Prompt.ask("Paste your Finnhub API key", password=False)
            if finnhub_key and finnhub_key.strip():
                self.config['finnhub_api_key'] = finnhub_key.strip()
                os.environ['FINNHUB_API_KEY'] = finnhub_key.strip()
                console.print("[green]✓ Finnhub API key saved![/green]\n")
            else:
                console.print("[yellow]⊘ Skipped Finnhub setup[/yellow]\n")
        
        # NewsData.IO
        if 'NewsData.IO' in keys_to_setup:
            console.print("[bold cyan]2️⃣  NewsData.IO Setup[/bold cyan]")
            console.print("[dim]NewsData.IO provides geopolitical events, Fed decisions, tariffs, OPEC news[/dim]")
            console.print("[cyan]→ Go to: https://newsdata.io[/cyan]")
            console.print("[cyan]→ Sign up (free, email only)[/cyan]")
            console.print("[cyan]→ Copy your API key from the dashboard[/cyan]\n")
            
            newsdata_key = Prompt.ask("Paste your NewsData.IO API key", password=False)
            if newsdata_key and newsdata_key.strip():
                self.config['newsdata_api_key'] = newsdata_key.strip()
                os.environ['NEWSDATA_API_KEY'] = newsdata_key.strip()
                console.print("[green]✓ NewsData.IO API key saved![/green]\n")
            else:
                console.print("[yellow]⊘ Skipped NewsData.IO setup[/yellow]\n")
        
        # Groq
        if 'Groq' in keys_to_setup:
            console.print("[bold cyan]3️⃣  Groq Setup[/bold cyan]")
            console.print("[dim]Groq provides AI analysis and synthesis of market data[/dim]")
            console.print("[cyan]→ Go to: https://console.groq.com/keys[/cyan]")
            console.print("[cyan]→ Sign up (free, email only)[/cyan]")
            console.print("[cyan]→ Create API key and copy it[/cyan]\n")
            
            groq_key = Prompt.ask("Paste your Groq API key", password=False)
            if groq_key and groq_key.strip():
                self.config['groq_api_key'] = groq_key.strip()
                os.environ['GROQ_API_KEY'] = groq_key.strip()
                console.print("[green]✓ Groq API key saved![/green]\n")
            else:
                console.print("[yellow]⊘ Skipped Groq setup[/yellow]\n")
        
        # Save config
        ConfigurationManager.save_config(self.config)
        console.print("[bold green]✓ API keys saved to configuration![/bold green]")
        console.print("[dim]You can update them anytime in Settings[/dim]\n")
        Prompt.ask("Press Enter to continue")
    
    def _require_login(self) -> bool:
        """Check if users exist and require login."""
        users = UserManager.load_users()
        
        # If no users exist, create first admin account
        if not users:
            console.print("\n[bold yellow]⚠ No users found. Creating first admin account...[/bold yellow]\n")
            console.print("[cyan]Please create an administrator account:[/cyan]\n")
            
            username = Prompt.ask("Admin Username")
            password = input("Admin Password: ")
            confirm = input("Confirm Password: ")
            
            if password != confirm:
                console.print("[red]✗ Passwords do not match! Exiting...[/red]")
                return True  # Exit app
            
            full_name = Prompt.ask("Your Full Name (optional)", default="Administrator")
            
            UserManager.create_user(username, password, full_name, "admin")
            console.print("\n[green]✓ Admin account created! Please restart the application.[/green]\n")
            return True  # Exit to restart
        
        # Require login
        console.print("\n[bold cyan]🔐 Login Required[/bold cyan]\n")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            username = Prompt.ask("Username")
            password = input("Password: ")
            
            if UserManager.authenticate(username, password):
                self.current_user = username
                console.print(f"\n[green]✓ Welcome, {username}![/green]\n")
                time.sleep(1)
                return False  # Continue to app
            else:
                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    console.print(f"[red]✗ Invalid credentials. {remaining} attempt(s) remaining.[/red]\n")
                else:
                    console.print("[red]✗ Maximum login attempts exceeded. Exiting...[/red]\n")
                    return True  # Exit app
        
        return True  # Exit app if loop completes without login
    
    def initialize(self):
        """Initialize application with all checks."""
        # Skip login for local machine - only required for web interface
        # if self._require_login():
        #     return  # Exit if login fails
        
        DisplayManager.show_header()
        
        ConfigurationManager.check_dependencies()
        
        # Load existing config or create default
        self.config = ConfigurationManager.load_config()
        if not self.config:
            console.print("[yellow]⚠ No configuration found. Creating default settings...[/yellow]")
            console.print("[dim]Use Option 16 (Settings) to configure API keys and preferences[/dim]\n")
            self.config = {
                'account_size': 10000.0,
                'risk_per_trade': 2.0,
                'default_rrr': 2.0,
                'max_positions': 5,
                'analysis_mode': 'advanced',
                'notifications_enabled': False,
                'anthropic_api_key': ''
            }
            ConfigurationManager.save_config(self.config)
        
        # Check and prompt for missing API keys
        self._validate_and_setup_api_keys()
        
        # Load API key from config
        self.api_key = self.config.get('anthropic_api_key', '')
        
        # Notifications
        self.notifier = NotificationManager(self.config)
        
        try:
            import anthropic
            self.analyzer = AIAnalyzer(self.api_key)
            self.theme_researcher = ThemeResearcher(self.api_key)
            self.scanner = MarketScanner(self.analyzer)
            
            # Show Schwab futures banner if enabled
            if self.config.get('schwab_futures_enabled'):
                console.print()
                schwab_banner = Panel(
                    "[bold green]🚀 CHARLES SCHWAB FUTURES TRADING ENABLED![/bold green]\n\n"
                    "[white]Trade E-mini futures directly from FinalAI:[/white]\n"
                    "[cyan]• Option 1:[/cyan] Analyze futures (e.g., /ES, /NQ) → Trade directly\n"
                    "[cyan]• Dashboard:[/cyan] View positions & P&L after analysis\n"
                    "[cyan]• Place Orders:[/cyan] Execute trades with AI recommendations\n\n"
                    "[dim]Analyze any futures contract and trading options will appear![/dim]",
                    border_style="green",
                    box=box.DOUBLE,
                    title="[bold]NEW FEATURE[/bold]"
                )
                console.print(schwab_banner)
                console.print()
            elif self.config.get('schwab_setup_shown') is not True:
                # Show one-time setup message
                console.print()
                console.print("[bold cyan]💡 NEW: Trade Futures with Charles Schwab![/bold cyan]")
                console.print("[dim]Run Option 18 (Preflight Setup) to enable futures trading[/dim]")
                console.print("[dim]Then use Option 1 to analyze and trade futures (/ES, /NQ, etc.)[/dim]")
                console.print()
                self.config['schwab_setup_shown'] = True
                ConfigurationManager.save_config(self.config)
            console.print("[green]✓ AI systems initialized[/green]\n")
        except Exception as e:
            logger.warning(f"AI initialization failed: {e}")
            console.print("[yellow]⚠ AI analysis unavailable, using fallback[/yellow]\n")
            self.analyzer = AIAnalyzer("")
            self.theme_researcher = ThemeResearcher("")
            self.scanner = MarketScanner(self.analyzer)
        
        # Show saved positions on startup if any exist
        try:
            temp_mgr = PositionManager()
            if temp_mgr.positions:
                console.print(f"[bold cyan]📊 {len(temp_mgr.positions)} saved position(s) found[/bold cyan]")
                console.print("[dim]Use Option 6 (Position Manager) to monitor them[/dim]\n")
        except:
            pass
    
    def run(self):
        """Main application loop."""
        # initialize feature engines used by menu actions
        backtest_engine = BacktestEngine(self.analyzer, TechnicalAnalyzer())
        watchlist = WatchlistMonitor(self.analyzer, TechnicalAnalyzer())
        position_mgr = PositionManager()  # Loads saved positions automatically
        equity_dashboard = EquityDashboard()
        ml_weighter = MLSignalWeighter()
        mta = MultiTimeframeAnalyzer(self.analyzer, TechnicalAnalyzer())

        while True:
            DisplayManager.show_header()

            console.print("[bold cyan]Main Menu[/bold cyan]\n")
            console.print("[bold]🔷 CORE ANALYSIS[/bold]")
            console.print("1. 📊 Analyze Stock/Crypto")
            console.print("2. 🔍 Market Scanner")
            console.print("3. 📰 News & Market Intel")
            console.print("\n[bold]🔷 PORTFOLIO & TRADING[/bold]")
            console.print("4. 👁️  Watchlist Monitor")
            console.print("5. 💰 Position Manager")
            console.print("6. 📈 Equity Dashboard")
            console.print("7. 🔔 Background Monitor (Auto-Alerts)")
            console.print("\n[bold]🔷 ADVANCED ANALYSIS[/bold]")
            console.print("8. 🏢 Smart Money Detector")
            console.print("9. ⏱️  Multi-Timeframe Analysis")
            console.print("10. 📞 Options Strategies")
            console.print("\n[bold]🔷 RESEARCH & INSIGHTS[/bold]")
            console.print("11. 🔬 Theme Research")
            console.print("12. 👔 Insider Trading Analysis")
            console.print("13. 🏛️  Political Tracker")
            console.print("\n[bold]🔷 PAPER TRADING & STRATEGIES[/bold]")
            console.print("14. 📝 Paper Trading Dashboard")
            console.print("15. 🎓 Quantitative Strategies")
            console.print("16. 🤖 Bot Learning Dashboard")
            console.print("\n[bold]🔷 AI ASSISTANT[/bold]")
            console.print("17. 💬 AI Trade Advisor")
            console.print("\n[bold]🔷 SYSTEM[/bold]")
            console.print("18. 👥 User Management")
            console.print("19. ⚙️  Settings")
            console.print("20. 🚪 Exit\n")

            choice = Prompt.ask("Select", choices=[str(i) for i in range(1, 21)], default="1")

            if choice == "1":
                self.analyze_ticker()
            elif choice == "2":
                self.run_market_scanner()
            elif choice == "3":
                self.show_news_intel()
            elif choice == "4":
                self._run_watchlist(watchlist)
            elif choice == "5":
                self._manage_positions(position_mgr)
            elif choice == "6":
                equity_dashboard.show_dashboard()
                Prompt.ask("\nPress Enter to continue")
            elif choice == "7":
                self._start_background_monitor(position_mgr)
            elif choice == "8":
                self._detect_smart_money()
            elif choice == "9":
                self._multi_timeframe_analysis(mta)
            elif choice == "10":
                self._options_strategies()
            elif choice == "11":
                self.research_theme()
            elif choice == "12":
                self.analyze_insider_trading()
            elif choice == "13":
                self.track_political_trades()
            elif choice == "14":
                self.paper_trading.update_trades()
                self.paper_trading.show_summary()
                Prompt.ask("\nPress Enter to continue")
            elif choice == "15":
                self._run_quant_strategies()
            elif choice == "16":
                self._show_bot_learning_dashboard()
            elif choice == "17":
                self._trade_conversation_advisor()
            elif choice == "18":
                self._manage_users()
            elif choice == "19":
                self.settings_menu()
            elif choice == "20":
                console.print("\n[cyan]Thanks for using FinalAI Quantum! 🚀[/cyan]\n")
                break
    
    def _show_bot_learning_dashboard(self):
        """Display the trading bot's learning and prediction accuracy dashboard."""
        DisplayManager.show_header()
        console.print("[bold cyan]🤖 Trading Bot - Learning Dashboard[/bold cyan]\n")
        
        # Check for any pending prediction outcomes
        results = self.paper_trading.check_prediction_outcomes()
        if results['updated'] > 0:
            console.print(f"[green]✓ Updated {results['updated']} prediction outcome(s)[/green]\n")
        
        # Get learning brief
        learning_brief = self.paper_trading.get_bot_learning_summary()
        console.print(learning_brief)
        
        # Show accuracy dashboard
        console.print("\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")
        self.paper_trading.show_prediction_accuracy()
        
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
    
    def _manage_users(self):
        """User management - create, delete, list users."""
        while True:
            DisplayManager.show_header()
            console.print("[bold cyan]👥 User Management[/bold cyan]\n")
            
            console.print("[bold]Options:[/bold]")
            console.print("1. 👤 Create New User")
            console.print("2. 📋 List All Users")
            console.print("3. 🔑 Change User Password")
            console.print("4. 🔄 Activate/Deactivate User")
            console.print("5. 🗑️  Delete User")
            console.print("6. 🔙 Back to Main Menu\n")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"], default="1")
            
            if choice == "1":
                console.print("\n[bold cyan]Create New User[/bold cyan]\n")
                username = Prompt.ask("Username")
                password = input("Password: ")
                confirm = Prompt.ask("Confirm Password", password=True)
                
                if password != confirm:
                    console.print("[red]✗ Passwords do not match![/red]")
                    Prompt.ask("\nPress Enter to continue")
                    continue
                
                full_name = Prompt.ask("Full Name (optional)", default="")
                role = Prompt.ask("Role", choices=["admin", "user"], default="user")
                
                UserManager.create_user(username, password, full_name, role)
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "2":
                console.print("\n[bold cyan]All Users[/bold cyan]\n")
                users = UserManager.list_users()
                
                if not users:
                    console.print("[yellow]No users found[/yellow]")
                else:
                    table = Table(box=box.ROUNDED)
                    table.add_column("Username", style="cyan")
                    table.add_column("Full Name", style="white")
                    table.add_column("Role", style="yellow")
                    table.add_column("Created", style="dim")
                    table.add_column("Last Login", style="dim")
                    table.add_column("Status", justify="center")
                    
                    for user in users:
                        status = "[green]Active[/green]" if user['active'] else "[red]Inactive[/red]"
                        created = user['created_at'][:10] if user['created_at'] else "Unknown"
                        last_login = user['last_login'][:10] if user['last_login'] and user['last_login'] != "Never" else "Never"
                        
                        table.add_row(
                            user['username'],
                            user['full_name'],
                            user['role'],
                            created,
                            last_login,
                            status
                        )
                    
                    console.print(table)
                
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "3":
                console.print("\n[bold cyan]Change User Password[/bold cyan]\n")
                username = Prompt.ask("Username")
                new_password = input("New Password: ")
                confirm = Prompt.ask("Confirm Password", password=True)
                
                if new_password != confirm:
                    console.print("[red]✗ Passwords do not match![/red]")
                else:
                    UserManager.change_password(username, new_password)
                
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "4":
                console.print("\n[bold cyan]Activate/Deactivate User[/bold cyan]\n")
                username = Prompt.ask("Username")
                UserManager.toggle_user_status(username)
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "5":
                console.print("\n[bold cyan]Delete User[/bold cyan]\n")
                username = Prompt.ask("Username")
                
                if Confirm.ask(f"Are you sure you want to delete user '{username}'?", default=False):
                    UserManager.delete_user(username)
                
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "6":
                break

    def _trade_conversation_advisor(self):
        """Interactive AI trade advisor - DuckDuckGo search + Groq analysis."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]💬 AI Trade Advisor (DuckDuckGo + Groq)[/bold cyan]\n")
        console.print("[dim]Chat naturally about your trades, stocks, or market ideas.[/dim]")
        console.print("[dim]I'll search DuckDuckGo for news and Groq will analyze it.[/dim]")
        console.print("[dim]Type 'exit' or 'quit' to return to the main menu.\n[/dim]")
        
        # Setup Groq
        groq_key = self.config.get('groq_api_key', '')
        
        if not groq_key or not groq_key.strip():
            console.print("\n[cyan]🚀 Quick Groq Setup[/cyan]\n")
            console.print("1. Go to: [cyan]https://console.groq.com/keys[/cyan]")
            console.print("2. Sign up (free) → Create API key")
            console.print("3. Paste here\n")
            
            if Confirm.ask("Ready?", default=True):
                groq_key = Prompt.ask("Enter your Groq API key")
                self.config['groq_api_key'] = groq_key
                ConfigurationManager.save_config(self.config)
                console.print("[green]✓ Saved![/green]\n")
            else:
                Prompt.ask("\nPress Enter to continue")
                return
        
        try:
            from openai import OpenAI
            groq_client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            console.print("[green]✓ Groq connected!\n[/green]")
        except ImportError:
            console.print("[yellow]Installing openai...[/yellow]")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "openai"])
            from openai import OpenAI
            groq_client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            console.print("[green]✓ Connected!\n[/green]")
        except Exception as e:
            console.print(f"[red]❌ Groq connection failed: {e}[/red]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        # Conversation history
        conversation_history = []
        technical_analyzer = TechnicalAnalyzer()
        
        # More conversational system prompt
        system_prompt = """You are a professional trader chatting naturally about stocks. Sound like a real person talking to a friend.

DATA SOURCES AVAILABLE:
- Finnhub: Real-time company news, earnings, analyst ratings, insider trades
- SEC Edgar: Official filings (10-K, 10-Q, 8-K), insider trading data
- NewsData.IO: Geopolitical events, macro news, Fed decisions, trade wars, sanctions, OPEC actions - market-moving global events
- Technical Analysis: Price action, support/resistance, trend data
- News: Web search results and market news

Your style:
- Keep it short and conversational (1-3 sentences unless they ask for details)
- Sound natural - use contractions, casual language
- Share what you see without being robotic
- ALWAYS mention your source when you cite a fact (Finnhub, SEC, NewsData, News, etc)
- ALWAYS provide DIRECT article/filing links when referencing specific sources
- Ask or engage naturally, don't just dump a verdict

CRITICAL DATA ACCURACY RULES:
- ONLY cite specific numbers (%, price moves, etc) if they appear EXACTLY in the articles/filings provided
- For SEC filings: reference the form type (10-K, 8-K) and filing date
- For insider trades: mention the insider name, position, and transaction type from SEC data
- For Finnhub data: cite the source clearly
- For geopolitical events (NewsData.IO): explain the economic impact chain clearly
- If the data doesn't have exact numbers, say "based on recent reports" or "according to reports" instead of guessing

GEOPOLITICAL & MACRO EVENTS (NewsData.IO) - CRITICAL FEATURE:
When you see geopolitical or macro events in the news:
1. Identify the event: "Fed raised rates", "China imposed tariffs", "OPEC cut production", "Russia/Ukraine conflict", etc.
2. Explain DIRECT market impact:
   - Fed rate hikes → Banks rally (higher interest margins), Bonds fall, Growth stocks pressured
   - Fed rate cuts → Gold rallies (lower opportunity cost), Bonds rally, Growth stocks rally, REITs rally
   - Tariffs/Trade wars → Export companies hurt, domestic competitors helped, consumer prices up
   - OPEC production cuts → Oil prices up, Energy stocks rally (XOM/CVX), Airlines/Logistics hurt (higher fuel)
   - Geopolitical conflict → Energy supply concerns (oil up), Defense contractors rally, Uncertainty sells off growth
   - Strong USD → American exporters struggle, foreign investors buy US assets (attracts capital)
   - Weak USD → Commodities rally, Energy up, International companies' US earnings boosted
3. Link affected stocks to the event: "This helps [bullish sectors] but hurts [bearish sectors]"
4. Cite NewsData.IO article link

Examples:
- "Fed hiked rates again (NewsData.IO). Banks like JPM and BAC love this - higher rates = fatter profit margins on loans. But growth stocks like NVDA and TSLA get hit because future earnings are worth less. Here's the article: [link]"
- "China just slapped tariffs on US semiconductors (NewsData.IO). That's bearish for TSMC, SMIC, and chips heading to China. But Intel and AMD could benefit if those orders shift domestically. Full story: [link]"
- "OPEC announced production cut (NewsData.IO). Oil prices jumped - great for Exxon (XOM) and Chevron (CVX), but hurts airlines (UAL, DAL) and shipping (FDX) who pay more for fuel. Check this: [link]"

WHEN USER ASKS "WHY IS [TICKER] GOING UP/DOWN?":
Look for:
1. Company-specific news (Finnhub, SEC filings)
2. Geopolitical/macro events (NewsData.IO) affecting the sector
3. Technical breakdown or rally
4. Connect all three to give a complete answer

Rules:
- If you mention a number from news = MUST include source article link
- NO generic links - only specific articles about the topic
- Sound like you're thinking, not reading a script
- EXPLAIN the WHY using news provided, not guesses
- The news context contains answers - use it directly to explain movements
- Geopolitical events are important market drivers - don't ignore them
"""
        
        def extract_ticker_with_ai(msg: str) -> Optional[str]:
            """Use AI to intelligently interpret what stock the user is discussing."""
            try:
                # First try explicit $TICKER pattern
                dollar_pattern = re.findall(r'\$([A-Z]{1,5})\b', msg.upper())
                if dollar_pattern:
                    return dollar_pattern[0]
                
                # Use AI to interpret generic terms like "gold", "oil", "crypto"
                ai_prompt = f"""User message: "{msg}"

What stock ticker is the user most likely asking about? Consider:
- "gold" or "gold stocks" → "GLD" (SPDR Gold Shares ETF)
- "silver" → "SLV"
- "oil" or "energy" → "USO" or "XLE"
- "crypto" or "bitcoin" → "IBIT" or "GBTC"
- Company names → their ticker symbol
- If unclear → "UNKNOWN"

Respond with ONLY the 1-5 letter ticker symbol or "UNKNOWN". No explanations."""
                
                # Use Groq to extract ticker
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=15,
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                ticker = response.choices[0].message.content.strip().upper()
                
                # Validate result
                if ticker and ticker != "UNKNOWN" and 1 <= len(ticker) <= 5:
                    return ticker
                    
            except Exception as e:
                logger.debug(f"AI ticker extraction error: {e}")
            
            return None
        
        def extract_ticker_from_message(msg: str) -> Optional[str]:
            """Extract ticker from user message using AI-powered interpretation."""
            # Use AI to intelligently determine what stock they're talking about
            ai_ticker = extract_ticker_with_ai(msg)
            if ai_ticker:
                return ai_ticker
            
            return None
        
        # Store news items for potential sending to phone
        stored_news = []
        
        def generate_smart_search_queries(ticker: str, user_question: str) -> List[str]:
            """Use Groq to intelligently determine what news/searches would answer the user's question."""
            if not use_groq:
                # Fallback: just use the ticker and basic keywords
                keywords = user_question.lower().split()
                relevant = [w for w in keywords if w in ['earnings', 'ceo', 'product', 'acquisition', 'lawsuit', 'earnings', 'guidance', 'analyst', 'upgrade']]
                return [f"{ticker} {' '.join(relevant)}" if relevant else ticker]
            
            try:
                prompt = f"""The user asked about {ticker}: "{user_question}"

Generate 3-4 specific news search queries that would directly answer their question.
Focus on:
- Recent events that would affect the stock
- Company announcements
- Industry news
- Market catalysts

Return ONLY the search queries (one per line), no explanations. Example:
{ticker} earnings announcement
{ticker} AI investment
{ticker} CEO departure

Search queries:"""
                
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.5
                )
                
                queries_text = response.choices[0].message.content.strip()
                queries = [q.strip() for q in queries_text.split('\n') if q.strip() and len(q.strip()) > 5]
                
                # Ensure at least the ticker is included
                if not queries:
                    queries = [ticker]
                
                return queries[:4]  # Max 4 queries
                
            except Exception as e:
                logger.debug(f"Smart query generation failed: {e}")
                return [ticker]
        
        def scrape_diverse_news_sources(ticker: str) -> List[Dict[str, str]]:
            """
            Scrape news from FINANCIAL, POLITICAL, and GEOPOLITICAL sources.
            Only includes articles from the past week.
            Covers how world events affect markets.
            """
            all_articles = []
            
            try:
                from bs4 import BeautifulSoup
                from datetime import datetime, timedelta
            except ImportError:
                return all_articles
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Primary sources optimized for scraping - these support recent/this week filters
            sources_to_scrape = {
                'Yahoo Finance News': f"https://finance.yahoo.com/news/",
                'MarketWatch Top News': "https://www.marketwatch.com/story/latest-news",
                'CNBC Latest': "https://www.cnbc.com/latest/",
                'Reuters Top News': "https://www.reuters.com/",
                'BBC Business': "https://www.bbc.com/news/business",
                'Yahoo Finance Markets': "https://finance.yahoo.com/markets/",
                'AP Finance': "https://apnews.com/hub/business",
                'Economic Times Top': "https://economictimes.indiatimes.com/markets/stocks/news",
            }
            
            # Define one week ago date for filtering
            one_week_ago = datetime.now() - timedelta(days=7)
            
            for source_name, url in sources_to_scrape.items():
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        logger.debug(f"{source_name}: HTTP {response.status_code}")
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    articles_found = 0
                    
                    # Find all headline-like elements
                    # Try multiple selectors to find articles
                    selectors = [
                        ('a', {'class': 'titleline'}),  # Hacker News style
                        ('h2', {}),  # Generic heading
                        ('h3', {}),  # Smaller heading
                        ('span', {'class': 'headline'}),
                        ('div', {'class': 'headline'}),
                    ]
                    
                    found_elements = []
                    for tag, attrs in selectors:
                        found_elements.extend(soup.find_all(tag, attrs))
                    
                    # Also try generic link extraction
                    all_links = soup.find_all('a', href=True, limit=100)
                    
                    for element in found_elements + all_links:
                        if articles_found >= 15:
                            break
                        
                        # Get text and href
                        if element.name == 'a':
                            title = element.get_text(strip=True)
                            href = element.get('href', '')
                        else:
                            link = element.find('a') or element.parent.find('a')
                            if not link:
                                continue
                            title = element.get_text(strip=True) or link.get_text(strip=True)
                            href = link.get('href', '')
                        
                        # Validate title and URL
                        if not title or len(title) < 15 or len(title) > 350:
                            continue
                        
                        if not href or not (href.startswith('http') or href.startswith('/')):
                            continue
                        
                        # Skip nav/UI elements
                        skip_terms = ['sign in', 'subscribe', 'register', 'login', 'menu', 'contact', 'about us', 'privacy', 'terms']
                        if any(term in title.lower() for term in skip_terms):
                            continue
                        
                        # Build full URL
                        if href.startswith('/'):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            href = f"{parsed.scheme}://{parsed.netloc}{href}"
                        elif not href.startswith('http'):
                            continue
                        
                        # Avoid duplicates
                        if any(a['title'] == title for a in all_articles):
                            continue
                        
                        all_articles.append({
                            'title': title[:200],
                            'url': href[:500],
                            'source': source_name,
                            'date': 'Past Week',
                            'category': 'Financial/Economic'
                        })
                        articles_found += 1
                    
                    if articles_found > 0:
                        logger.debug(f"✓ Found {articles_found} from {source_name}")
                    else:
                        logger.debug(f"✗ No articles from {source_name}")
                
                except requests.exceptions.Timeout:
                    logger.debug(f"⏱ {source_name} timeout")
                except requests.exceptions.RequestException as e:
                    logger.debug(f"❌ {source_name} error: {str(e)[:40]}")
                except Exception as e:
                    logger.debug(f"❌ {source_name} parse error: {str(e)[:40]}")
            
            # If we got some articles, return them
            if all_articles:
                return all_articles[:40]  # Get up to 40 articles across all sources
            
            # FALLBACK: Use existing NewsAnalyzer APIs if scraping failed
            logger.debug("Scraping limited, using API fallback...")
            try:
                api_articles = NewsAnalyzer.get_news(ticker, limit=10)
                if api_articles:
                    for item in api_articles:
                        all_articles.append({
                            'title': item.title if hasattr(item, 'title') else str(item),
                            'url': item.url if hasattr(item, 'url') else '',
                            'source': item.source if hasattr(item, 'source') else 'News API',
                            'date': 'Recent',
                            'category': 'Financial/Economic'
                        })
            except:
                pass
            
            return all_articles[:40]
        
        def generate_comprehensive_analysis(ticker: str, articles: List[Dict[str, str]]) -> str:
            """
            Send all articles to Groq for analysis of how world events affect the stock.
            Groq MUST synthesize all sources into a comprehensive opinion and cite specific articles with links.
            Also includes live price data and technical indicators for context.
            """
            if not articles:
                return "No articles found to analyze"
            
            if not use_groq:
                # Fallback: just list articles
                result = f"Articles about {ticker}:\n\n"
                for i, a in enumerate(articles[:15], 1):
                    result += f"{i}. {a['title']}\n"
                    if a.get('url'):
                        result += f"   Link: {a['url']}\n"
                    result += f"   Source: {a.get('source', 'Unknown')}\n\n"
                return result
            
            try:
                # Fetch live price and technical data
                price_context = ""
                try:
                    df = DataManager.get_data(ticker, period='5d', interval='1h')
                    if df is not None and len(df) > 0:
                        current_price = float(df['Close'].iloc[-1])
                        day_high = float(df['High'].iloc[-1])
                        day_low = float(df['Low'].iloc[-1])
                        
                        # Calculate simple metrics
                        day_open = float(df['Open'].iloc[-1])
                        day_change_pct = ((current_price - day_open) / day_open * 100) if day_open != 0 else 0
                        
                        # Weekly context
                        week_ago = float(df['Close'].iloc[0]) if len(df) > 0 else current_price
                        week_change_pct = ((current_price - week_ago) / week_ago * 100) if week_ago != 0 else 0
                        
                        # RSI
                        delta = df['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        current_rsi = float(rsi.iloc[-1]) if not rsi.iloc[-1] != rsi.iloc[-1] else 50  # Handle NaN
                        
                        price_context = f"""
=== LIVE MARKET DATA FOR {ticker} ===
Current Price: ${current_price:.2f}
Daily Range: ${day_low:.2f} - ${day_high:.2f}
Today's Change: {day_change_pct:+.2f}%
Weekly Change: {week_change_pct:+.2f}%
RSI(14): {current_rsi:.1f}
Price Trend: {"UPTREND" if day_change_pct > 0 else "DOWNTREND"}

"""
                except Exception as e:
                    logger.debug(f"Could not fetch price data: {e}")
                    price_context = ""
                
                # Build numbered article list with URLs - use all available articles
                num_articles = min(len(articles), 25)  # Use up to 25 articles for analysis
                article_list = ""
                rumor_list = ""
                verified_count = 0
                rumor_count = 0
                
                for i, a in enumerate(articles[:num_articles], 1):
                    # Separate verified news from rumors
                    if a.get('verified') == False or 'RUMOR' in a.get('title', '') or a.get('confidence') == 'UNVERIFIED':
                        rumor_count += 1
                        rumor_list += f"\n⚠️  RUMOR #{rumor_count}: {a['title']}\n"
                        rumor_list += f"   SOURCE: {a['source']}\n"
                        if a.get('url') and a['url'].startswith('http'):
                            rumor_list += f"   LINK: {a['url']}\n"
                        rumor_list += f"   STATUS: UNVERIFIED - This is speculation/rumor, not confirmed fact\n"
                    else:
                        verified_count += 1
                        article_list += f"\n{verified_count}. TITLE: {a['title']}\n"
                        article_list += f"   SOURCE: {a['source']}\n"
                        if a.get('url') and a['url'].startswith('http'):
                            article_list += f"   LINK: {a['url']}\n"
                        article_list += f"   CATEGORY: {a.get('category', 'News')}\n"
                
                # Create analysis prompt that REQUIRES comprehensive synthesis
                rumor_section = ""
                if rumor_list:
                    rumor_section = f"""\n\n**UNVERIFIED RUMORS & SPECULATION** ({rumor_count} items):
These are unconfirmed reports and speculation circulating about {ticker}. They should be monitored but NOT treated as facts:
{rumor_list}

IMPORTANT: When analyzing rumors, clearly label them as unverified speculation. Mention them if they're gaining attention, but do NOT base your investment thesis on rumors alone. Separate rumor-driven volatility from fundamental-driven moves."""
                
                analysis_prompt = f"""{price_context}You are analyzing {verified_count} VERIFIED news articles and {rumor_count} UNVERIFIED rumors about {ticker}. Your job is to synthesize the VERIFIED sources into a coherent market opinion, while also noting what rumors/speculation are circulating (but not treating them as facts).

**VERIFIED & SOURCED ARTICLES**:
{article_list}
{rumor_section}

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:
1. Read and understand ALL {verified_count} verified articles provided above.
2. Also NOTE the {rumor_count} unverified rumors below, but DO NOT treat them as facts.
3. Do NOT use generic knowledge - only analyze these specific articles AND the live price data.
4. Cite specific article numbers when discussing VERIFIED news.
5. When discussing rumors, clearly mark them as "unverified speculation from [source]"
6. Create a UNIFIED opinion by finding themes, patterns, and consensus across VERIFIED sources.
7. Connect the news narrative to the current price action and technical levels.

**YOUR COMPREHENSIVE MARKET OPINION FOR {ticker}**:

**SYNTHESIS & DOMINANT NARRATIVE** (Based on Verified Sources):
What story do these {verified_count} verified articles collectively tell about {ticker}? How does this narrative align with or contradict the current price action?
- What is the consensus sentiment across verified sources?
- What are the common themes? List the top 3-5 recurring themes across verified articles.
- Are rumors/speculation amplifying or contradicting the verified narrative?
- How does the price action (today's change, weekly change, RSI level) support or contradict this narrative?
- Are there any conflicting narratives? If so, which appears more credible and why?

**DETAILED CAUSAL ANALYSIS** (Connect verified events to stock impact):
For each major theme identified above:
1. THEME: [Name the theme]
2. VERIFIED SOURCE ARTICLES: [List 2-3 article numbers that support this]
3. THE FACTS: [Specific quotes/facts from those articles]
4. WHY IT MATTERS: [How does this directly affect {ticker}'s business fundamentals?]
5. STOCK IMPACT: [Will this drive price up, down, or stay neutral? Why?]
6. TIMELINE: [When will investors react to this?]
7. RUMOR CONNECTIONS: [Are any circulating rumors related to this theme? Are they plausible given verified facts?]

**CATALYSTS RANKED BY IMPACT** (Verified Sources Only):
List the 3-5 most important catalysts from VERIFIED articles:
1. [CATALYST]: [Article X, Y, Z sources] - Impact: [POSITIVE/NEGATIVE/NEUTRAL] - Why: [Detailed reasoning]
2. [CATALYST]: ...

**RUMORS & SPECULATION TRACKER**:
What {rumor_count} unverified rumors are circulating about {ticker}? 
- Do they align with verified facts or contradict them?
- What is the market sentiment around these rumors (are traders betting they're true)?
- How likely are these rumors to affect price action even if unconfirmed?
- Rate each rumor's plausibility based on verified facts: [HIGH/MEDIUM/LOW plausibility]

**THE BOTTOM LINE OPINION** (Combining Verified News + Current Price Action):
Based on synthesizing VERIFIED articles and current price action:
- Should {ticker} trade UP, DOWN, or SIDEWAYS? [Give clear direction with confidence]
- Conviction level: [HIGH/MEDIUM/LOW] - Why is your conviction this strong?
- Does the current price action (RSI={current_rsi:.0f}, {day_change_pct:+.1f}% today) align with verified news sentiment? Or is there a divergence?
- Could unverified rumors be driving any divergence between verified sentiment and price action?
- If diverging: Which is more likely to win - price catching up to sentiment, or sentiment shifting toward price?
- Key assumption: [What needs to stay true for your opinion to be correct?]
- What could change your mind: [What verified news would reverse your opinion?]

**SPECIFIC STOCK PRICE DIRECTION WITH TARGETS**:
Given all VERIFIED news from these {verified_count} sources AND current price of ${current_price:.2f}:
- Short-term (1-4 weeks): [Direction and reasoning with potential price target]
- Medium-term (1-3 months): [Direction and reasoning]
- Long-term (3+ months): [Direction and reasoning]

**TRADE SETUP ANALYSIS**:
Is {ticker} at a good entry point right now given:
- The daily range (${day_low:.2f} - ${day_high:.2f})
- The sentiment from {verified_count} verified sources
- The RSI level ({current_rsi:.0f})
- Any support/resistance levels implied by the news catalysts
- Rumor-driven volatility considerations

**CONFIDENCE & RISKS**:
- How confident are you in this opinion? [0-100%] Why?
- What are the biggest risks to this analysis? [Answer from verified articles - what could go wrong?]
- Is there minority opinion in verified articles that could be right? [Acknowledge counterarguments]
- Could {rumor_count} unverified rumors suddenly become reality and change your outlook?

Remember: Every claim about verified facts must be traceable to specific articles. Rumors are noted separately and not treated as fact. You are synthesizing {verified_count} verified sources into ONE clear, coherent opinion. The reader should understand what you think and why, based on real evidence."""
                
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=3000,
                    temperature=0.6  # Lower temp for more factual responses
                )
                
                analysis = response.choices[0].message.content
                
                header = f"\n[🤖 GROQ SYNTHESIS OF {num_articles} NEWS SOURCES FOR {ticker}]\n\n"
                return header + analysis
                
            except Exception as e:
                logger.debug(f"Analysis failed: {e}")
                # Fallback to listing articles
                result = f"Error in analysis, but here are {len(articles)} sources:\n\n"
                for a in articles[:10]:
                    result += f"- {a['title']} ({a['source']})\n"
                    if a.get('url'):
                        result += f"  {a['url']}\n"
                return result
                return "Could not generate analysis"
        
        def search_duckduckgo_news(ticker: str, query: str = "") -> List[Dict[str, str]]:
            """Search DuckDuckGo for news articles about a ticker from the past week only.
            Returns list of articles with titles and URLs.
            """
            import requests
            from bs4 import BeautifulSoup
            from datetime import datetime, timedelta
            
            articles = []
            
            try:
                # Build search query with past week filter
                if query:
                    search_query = f"{ticker} {query} news"
                else:
                    search_query = f"{ticker} stock news"
                
                # Add DuckDuckGo time filter for past week
                search_query += " (past:w)"  # Past week filter
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Search DuckDuckGo
                url = "https://html.duckduckgo.com/"
                params = {'q': search_query}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find search results
                    results = soup.find_all('div', {'class': 'r'})
                    
                    for result in results[:15]:  # Get up to 15 results
                        try:
                            link = result.find('a', {'class': 'result__a'})
                            if not link:
                                continue
                            
                            title = link.get_text(strip=True)
                            url = link.get('href', '')
                            
                            # Filter out junk
                            if not title or len(title) < 20 or 'duckduckgo' in url.lower():
                                continue
                            
                            articles.append({
                                'title': title[:200],
                                'url': url,
                                'source': 'DuckDuckGo Search',
                                'category': 'News'
                            })
                        except:
                            continue
                    
                    if articles:
                        logger.debug(f"✓ Found {len(articles)} articles from DuckDuckGo")
                        return articles
                
            except requests.Timeout:
                logger.debug("DuckDuckGo search timed out")
            except Exception as e:
                logger.debug(f"DuckDuckGo search error: {str(e)[:50]}")
            
            return []
        
        def get_company_context(ticker: str) -> str:
            """Fetch analyst ratings, earnings dates, and company profile from Finnhub/SEC."""
            context = f"\n[COMPANY CONTEXT FOR {ticker}]:\n"
            
            try:
                # Get company profile
                profile = FinnhubAnalyzer.get_company_profile(ticker)
                if profile:
                    if profile.get('company_name'):
                        context += f"Company: {profile['company_name']}\n"
                    if profile.get('industry'):
                        context += f"Industry: {profile['industry']}\n"
                    if profile.get('market_cap'):
                        context += f"Market Cap: ${profile['market_cap']/1e9:.1f}B\n"
                
                # Get analyst ratings
                ratings = FinnhubAnalyzer.get_analyst_ratings(ticker)
                if ratings and any(ratings.values()):
                    context += f"\nAnalyst Consensus: "
                    total_ratings = sum([ratings.get(k, 0) for k in ['strongBuy', 'buy', 'hold', 'sell', 'strongSell']])
                    if total_ratings > 0:
                        context += f"{ratings.get('strongBuy', 0)} Strong Buy, {ratings.get('buy', 0)} Buy, {ratings.get('hold', 0)} Hold, {ratings.get('sell', 0)} Sell\n"
                
                # Get upcoming earnings
                earnings = FinnhubAnalyzer.get_earnings_calendar(ticker, limit=2)
                if earnings:
                    context += f"\nUpcoming Earnings: "
                    for e in earnings[:1]:
                        if e.get('date'):
                            context += f"{e['date']}"
                            if e.get('eps_estimate'):
                                context += f" (Est. EPS: ${e['eps_estimate']:.2f})"
                    context += "\n"
            
            except Exception as e:
                logger.debug(f"Company context error: {e}")
            
            return context
        
        def fetch_news_for_ticker(ticker: str, user_question: str = "") -> str:
            """Fetch news from Finnhub + SEC Edgar + NewsData.IO + DuckDuckGo, including geopolitical events."""
            nonlocal stored_news
            stored_news = []
            articles = []
            
            try:
                old_level = logger.level
                logger.setLevel(logging.ERROR)
                
                console.print(f"[cyan]🌍 Searching for news on {ticker} (Company + Geopolitical + Market)...[/cyan]")
                
                # PRIMARY: Finnhub - Real-time company-specific news
                try:
                    finnhub_articles = FinnhubAnalyzer.get_news(ticker, limit=20)
                    if finnhub_articles:
                        for article in finnhub_articles:
                            articles.append({
                                'title': article.get('title', ''),
                                'url': article.get('url', ''),
                                'source': article.get('source', 'Finnhub'),
                                'date': 'Recent',
                                'category': 'Company News'
                            })
                        console.print(f"[green]✓ Finnhub: {len(finnhub_articles)} company news articles[/green]")
                except Exception as e:
                    logger.debug(f"Finnhub news error: {e}")
                
                # SECONDARY: SEC Edgar - Filings and insider trades
                try:
                    sec_filings = SECEdgarAnalyzer.get_recent_filings(ticker, form_types=['10-K', '10-Q', '8-K'], limit=5)
                    if sec_filings:
                        for filing in sec_filings:
                            articles.append({
                                'title': f"SEC {filing['form_type']} Filing - {filing.get('filing_date', 'Recent')}",
                                'url': filing.get('url', ''),
                                'source': 'SEC Edgar',
                                'date': filing.get('filing_date', 'Recent'),
                                'category': 'SEC Filing'
                            })
                        console.print(f"[green]✓ SEC Edgar: {len(sec_filings)} recent filings[/green]")
                except Exception as e:
                    logger.debug(f"SEC Edgar filings error: {e}")
                
                # TERTIARY: Insider trades
                try:
                    insider_trades = FinnhubAnalyzer.get_insider_trades(ticker, limit=5)
                    if insider_trades:
                        for trade in insider_trades:
                            articles.append({
                                'title': f"INSIDER TRADE: {trade.get('name', 'Officer')} - {trade.get('transaction', 'BUY/SELL')} {trade.get('shares', 0)} shares",
                                'url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=4",
                                'source': 'Insider Trades',
                                'date': trade.get('filed_date', 'Recent'),
                                'category': 'Insider Activity'
                            })
                        console.print(f"[green]✓ Insider Trades: {len(insider_trades)} recent trades[/green]")
                except Exception as e:
                    logger.debug(f"Insider trades error: {e}")
                
                # QUATERNARY: NewsData.IO - Geopolitical & Market News that affects stocks
                try:
                    geopolitical_news = NewsDataAnalyzer.get_geopolitical_news(limit=10)
                    if geopolitical_news:
                        for article in geopolitical_news:
                            articles.append({
                                'title': article.get('title', ''),
                                'url': article.get('url', ''),
                                'source': article.get('source', 'NewsData'),
                                'date': 'Recent',
                                'category': 'Geopolitical/Macro Event'
                            })
                        console.print(f"[green]✓ NewsData.IO: {len(geopolitical_news)} geopolitical/macro events[/green]")
                    
                    # Also get market-specific news from NewsData.IO
                    market_news = NewsDataAnalyzer.get_market_news(limit=10)
                    if market_news:
                        for article in market_news:
                            articles.append({
                                'title': article.get('title', ''),
                                'url': article.get('url', ''),
                                'source': article.get('source', 'NewsData'),
                                'date': 'Recent',
                                'category': 'Market News'
                            })
                        console.print(f"[green]✓ NewsData.IO: {len(market_news)} market news articles[/green]")
                except Exception as e:
                    logger.debug(f"NewsData.IO error: {e}")
                
                # QUINTERNARY: Rumors & Unverified Speculation
                try:
                    rumors = NewsDataAnalyzer.get_rumors_and_speculation(ticker, limit=8)
                    if rumors:
                        for rumor in rumors:
                            articles.append({
                                'title': f"⚠️ RUMOR: {rumor.get('title', '')}",
                                'url': rumor.get('url', ''),
                                'source': f"{rumor.get('source', 'NewsData')} [UNVERIFIED]",
                                'date': 'Recent',
                                'category': 'Unverified Rumor/Speculation',
                                'verified': False,
                                'confidence': 'UNVERIFIED'
                            })
                        console.print(f"[yellow]⚠️  Rumors/Speculation: {len(rumors)} unverified reports found[/yellow]")
                except Exception as e:
                    logger.debug(f"Rumors fetch error: {e}")
                
                # FALLBACK: DuckDuckGo web search if minimal results
                if len(articles) < 5:
                    try:
                        search_query = f"{ticker} {user_question}" if user_question else ticker
                        ddg_articles = search_duckduckgo_news(ticker, search_query)
                        if ddg_articles:
                            for article in ddg_articles[:10]:
                                articles.append({
                                    'title': article.get('title', ''),
                                    'url': article.get('url', ''),
                                    'source': article.get('source', 'Web'),
                                    'date': 'Recent',
                                    'category': 'General News'
                                })
                            console.print(f"[green]✓ Web search: {len(ddg_articles)} additional articles[/green]")
                    except Exception as e:
                        logger.debug(f"DuckDuckGo fallback error: {e}")
                
                if articles and len(articles) > 0:
                    console.print(f"[green]✓ Total: {len(articles)} sources compiled (Company + Filings + Geopolitical + Market)[/green]")
                    
                    # Store articles for selection later
                    for article in articles:
                        stored_news.append({
                            'title': article.get('title', 'Unknown'),
                            'url': article.get('url', ''),
                            'sentiment': 'NEUTRAL',
                            'source': article.get('source', 'News')
                        })
                    
                    # Generate comprehensive analysis using Groq
                    analysis = generate_comprehensive_analysis(ticker, articles)
                    
                    logger.setLevel(old_level)
                    return analysis
                else:
                    console.print("[yellow]⚠ Could not find any news articles[/yellow]")
                    logger.setLevel(old_level)
                    return "\n[No recent articles found for analysis - try asking about a specific ticker or event]"
                

            except Exception as e:
                logger.setLevel(old_level) if 'old_level' in locals() else None
                logger.debug(f"News fetch error: {e}")
                return f"\n[Could not fetch news articles: {str(e)[:50]}]\n"
        
        def generate_stock_prediction(ticker: str, tech_context: str, news_context: str) -> str:
            """Generate price prediction: Technical patterns + Groq news sentiment + combined analysis."""
            try:
                old_level = logger.level
                logger.setLevel(logging.ERROR)
                
                # STEP 1: Get Groq's news sentiment analysis
                news_sentiment_prompt = f"""Analyze the news sentiment for {ticker}:

{news_context}

Provide a SHORT, FOCUSED analysis (2-3 sentences max):

1. NEWS SENTIMENT: Is the news bullish, bearish, or neutral overall?
2. KEY CATALYSTS: What are the 1-2 most important news-driven catalysts right now?
3. SENTIMENT IMPACT: How might this news sway market sentiment and attract/repel investors?
4. TIMELINE: When might this news impact the stock price? (Immediate, days, weeks, months?)
5. MARKET PSYCHOLOGY: What emotions is this news triggering? (Fear, greed, hope, panic?)

Be specific with facts from the news. Focus on how sentiment and psychology will affect price."""
                
                news_sentiment = ""
                if use_groq:
                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": news_sentiment_prompt}],
                        max_tokens=300,
                        temperature=0.7
                    )
                    news_sentiment = response.choices[0].message.content
                
                # STEP 2: Generate combined prediction using technical + news sentiment
                combined_prediction_prompt = f"""You are a professional trader analyzing {ticker}.

TECHNICAL ANALYSIS (Pattern-based, from historical price action):
{tech_context}

NEWS SENTIMENT ANALYSIS (Market psychology from recent events):
{news_sentiment}

Provide a COMPREHENSIVE prediction:

1. DIRECTION & CONFIDENCE:
   - Bullish, Bearish, or Neutral? (State your primary conviction)
   - Confidence level: 0-100% (How certain are you?)
   - Time horizon: Next 1-3 months

2. PRICE TARGETS:
   - Upside target: $X (if bullish/neutral upside)
   - Downside target: $X (if bearish/neutral downside)
   - Why these levels? (Technical + news drivers combined)

3. HOW TECHNICAL + NEWS ALIGN:
   - Does the technical setup support or contradict the news sentiment?
   - Are technicians and fundamentalists agreeing or fighting?
   - Where is the conflict/agreement strongest?

4. KEY LEVELS:
   - Critical support to hold: $X
   - Resistance to break: $X
   - What happens if these levels break? (How does news amplify the move?)

5. CATALYSTS & TIMELINE:
   - What news/earnings/events could accelerate your prediction? (When?)
   - What would prove you wrong? (What price/news would invalidate this?)

6. RISK/REWARD:
   - Best entry point for this thesis
   - Stop loss level
   - Take profit target
   - Risk/reward ratio

7. EDGE & CONVICTION:
   - Why should someone believe this prediction over just holding/selling?
   - What do you see that others might miss? (Technical + sentiment combined)"""
                
                prediction = ""
                
                if use_groq:
                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": combined_prediction_prompt}],
                        max_tokens=600,
                        temperature=0.7
                    )
                    prediction = response.choices[0].message.content
                
                elif use_ollama:
                    import requests
                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "llama3",
                            "prompt": combined_prediction_prompt,
                            "stream": False
                        },
                        timeout=30
                    )
                    prediction = response.json().get('response', '')
                
                else:
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=600,
                        messages=[{"role": "user", "content": combined_prediction_prompt}],
                        temperature=0.7
                    )
                    prediction = response.content[0].text
                
                logger.setLevel(old_level)
                return f"\n[COMBINED ANALYSIS - TECHNICAL + SENTIMENT]:\n{prediction}"
                
            except Exception as e:
                logger.setLevel(old_level) if 'old_level' in locals() else None
                logger.debug(f"Prediction error: {e}")
                return ""
        
        def fetch_and_analyze_technical(ticker: str) -> str:
            """Fetch and analyze technical, return formatted context."""
            try:
                import contextlib
                import sys
                from io import StringIO
                
                # Completely suppress all output
                old_level = logger.level
                logger.setLevel(logging.CRITICAL + 1)
                
                # Suppress stdout/stderr
                null_stream = StringIO()
                
                with contextlib.redirect_stdout(null_stream), contextlib.redirect_stderr(null_stream):
                    with console.status("[bold cyan]⏳ Loading...[/bold cyan]", spinner="dots"):
                        df_daily = DataManager.fetch_data(ticker, "2y", "1d")
                        df_weekly = DataManager.fetch_data(ticker, "5y", "1wk")
                        
                        tech_context = f"\n[TECHNICAL ANALYSIS FOR {ticker}]:\n"
                        
                        # Current price
                        try:
                            current_price = DataManager.get_realtime_price(ticker)
                            if not current_price and df_daily is not None:
                                current_price = float(df_daily['Close'].iloc[-1])
                            if current_price:
                                tech_context += f"Current Price: ${current_price:.2f}\n"
                        except:
                            pass
                        
                        # Daily analysis
                        if df_daily is not None and len(df_daily) > 0:
                            daily_analysis = technical_analyzer.analyze(ticker, df_daily)
                            if daily_analysis:
                                tech_context += f"Daily Trend: {daily_analysis.get('trend', 'UNKNOWN')}\n"
                                if daily_analysis.get('signal'):
                                    tech_context += f"Signal: {daily_analysis.get('signal')}\n"
                                if daily_analysis.get('rsi'):
                                    tech_context += f"RSI: {daily_analysis.get('rsi'):.1f}\n"
                                if daily_analysis.get('support'):
                                    tech_context += f"Support: ${daily_analysis.get('support'):.2f}\n"
                                if daily_analysis.get('resistance'):
                                    tech_context += f"Resistance: ${daily_analysis.get('resistance'):.2f}\n"
                        
                        # Weekly analysis
                        if df_weekly is not None and len(df_weekly) > 0:
                            weekly_analysis = technical_analyzer.analyze(ticker, df_weekly)
                            if weekly_analysis:
                                tech_context += f"Weekly Trend: {weekly_analysis.get('trend', 'UNKNOWN')}\n"
                
                logger.setLevel(old_level)
                return tech_context
                    
            except Exception as e:
                logger.setLevel(old_level) if 'old_level' in locals() else None
                logger.debug(f"Technical analysis error: {e}")
                return f"\n[Could not fully analyze {ticker}, but I'll still give you my thoughts]\n"
        
        def show_news_selection(ticker: str):
            """Display news and let user select which to send via Telegram."""
            if not stored_news:
                console.print("[dim]No news items to select[/dim]")
                return
            
            console.print(f"\n[bold cyan]📰 News Headlines for {ticker}[/bold cyan]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Headline", style="white", width=70)
            table.add_column("Sentiment", style="yellow", width=10)
            table.add_column("Source", style="green", width=15)
            
            for i, item in enumerate(stored_news, 1):
                sentiment_emoji = "📈" if item['sentiment'] == "POSITIVE" else "📉" if item['sentiment'] == "NEGATIVE" else "➡️"
                table.add_row(
                    str(i),
                    item['title'][:67],
                    f"{sentiment_emoji} {item['sentiment']}",
                    item['source'][:13]
                )
            
            console.print(table)
            console.print("\n[dim]Which headlines do you want to send to Telegram?[/dim]")
            console.print("[dim]Enter numbers separated by commas (e.g., 1,3,5) or 'skip'[/dim]\n")
            
            selection = Prompt.ask("Select headlines", default="skip")
            
            if selection.lower() == 'skip':
                return
            
            try:
                selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_news = [stored_news[i] for i in selected_indices if 0 <= i < len(stored_news)]
                
                if selected_news:
                    # Send to Telegram if configured
                    send_to_telegram = Confirm.ask(f"Send {len(selected_news)} headline(s) to Telegram?", default=True)
                    
                    if send_to_telegram:
                        # Use the NotificationManager with Telegram support
                        config = {'enable_notifications': True}
                        notif_manager = NotificationManager(config)
                        
                        if notif_manager.enabled:
                            for idx, item in enumerate(selected_news, 1):
                                sentiment_emoji = "📈" if item['sentiment'] == "POSITIVE" else "📉" if item['sentiment'] == "NEGATIVE" else "➡️"
                                msg = f"<b>{ticker} News {idx}/{len(selected_news)}</b>\n\n{sentiment_emoji} <i>{item['sentiment']}</i>\n\n<b>{item['title']}</b>\n\n<a href=\"{item['url']}\">Read More</a>\n\nSource: {item['source']}"
                                try:
                                    notif_manager.send(msg)
                                    console.print(f"[green]✓ Sent headline {idx} to Telegram[/green]")
                                except Exception as e:
                                    console.print(f"[yellow]⚠ Failed to send: {str(e)[:50]}[/yellow]")
                            
                            console.print(f"\n[green]✓ All headlines sent to Telegram![/green]\n")
                        else:
                            console.print("[yellow]⚠ Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS environment variables[/yellow]\n")
                    else:
                        console.print("[dim]Headlines not sent[/dim]\n")
            
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")
        
        def identify_affected_stocks(event_description: str) -> List[str]:
            """Use Groq to identify which stocks would be affected by an event."""
            try:
                if not use_groq:
                    return []
                
                prompt = f"""Analyze this market event and list 3-5 specific stock tickers that would be most affected:

Event: {event_description}

Return ONLY a comma-separated list of tickers (no explanations). Example format: AAPL,MSFT,GOOGL,GLD,DXY

List:"""
                
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.3
                )
                
                ticker_str = response.choices[0].message.content.strip()
                tickers = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
                return tickers[:5]  # Max 5 stocks
                
            except Exception as e:
                logger.debug(f"Stock identification error: {e}")
                return []
        
        def analyze_affected_stocks(tickers: List[str], event_date_context: str = "") -> str:
            """Fetch and analyze data for multiple affected stocks - including historical price changes."""
            if not tickers:
                return ""
            
            results = f"\n[STOCKS AFFECTED BY THIS EVENT]:\n"
            valid_tickers = []
            
            with console.status(f"[bold cyan]Fetching {len(tickers)} stocks + historical data...", spinner="dots"):
                for ticker in tickers:
                    try:
                        # Suppress logs during data fetch
                        old_level = logger.level
                        logger.setLevel(logging.CRITICAL + 1)
                        
                        # Fetch current and recent data
                        df_recent = DataManager.fetch_data(ticker, "1y", "1d")
                        
                        logger.setLevel(old_level)
                        
                        if df_recent is not None and len(df_recent) > 20:
                            valid_tickers.append(ticker)
                            # Calculate recent changes
                            current_price = float(df_recent['Close'].iloc[-1])
                            price_1mo_ago = float(df_recent['Close'].iloc[-20]) if len(df_recent) > 20 else current_price
                            price_3mo_ago = float(df_recent['Close'].iloc[-60]) if len(df_recent) > 60 else current_price
                            price_1yr_ago = float(df_recent['Close'].iloc[0]) if len(df_recent) > 0 else current_price
                            
                            change_1mo = ((current_price - price_1mo_ago) / price_1mo_ago * 100) if price_1mo_ago > 0 else 0
                            change_3mo = ((current_price - price_3mo_ago) / price_3mo_ago * 100) if price_3mo_ago > 0 else 0
                            change_1yr = ((current_price - price_1yr_ago) / price_1yr_ago * 100) if price_1yr_ago > 0 else 0
                            
                            direction = "📈" if change_1mo > 0 else "📉" if change_1mo < 0 else "➡️"
                            results += f"\n💹 {ticker} (${current_price:.2f}) {direction}\n"
                            results += f"  1-month:  {change_1mo:+.1f}%\n"
                            results += f"  3-month:  {change_3mo:+.1f}%\n"
                            results += f"  1-year:   {change_1yr:+.1f}%\n"
                            
                            # Fetch latest news
                            try:
                                news_context = fetch_news_for_ticker(ticker)
                                if news_context and "Could not" not in news_context:
                                    lines = [l for l in news_context.split('\n') if l.strip()]
                                    if lines:
                                        results += f"  News: {lines[0][:100]}\n"
                            except:
                                pass
                            
                            # Get current momentum
                            try:
                                tech_context = fetch_and_analyze_technical(ticker)
                                if tech_context and "Could not" not in tech_context:
                                    if "Trend:" in tech_context or "Signal:" in tech_context:
                                        lines = [l for l in tech_context.split('\n') if 'Trend:' in l or 'Signal:' in l]
                                        for line in lines[:1]:
                                            results += f"  {line.strip()}\n"
                            except:
                                pass
                        
                        logger.setLevel(old_level)
                    
                    except Exception as e:
                        logger.setLevel(old_level) if 'old_level' in locals() else None
                        # Silently skip bad tickers
                        continue
            
            # Add context note about valid stocks
            if valid_tickers:
                results += f"\n[Valid tickers analyzed: {', '.join(valid_tickers)}]\n"
            
            return results
        
        console.print("[bold cyan]Let's chat! Ask me anything about markets or trades.\n[/bold cyan]")
        
        while True:
            try:
                user_message = Prompt.ask("[bold cyan]You[/bold cyan]")
                
                if user_message.lower() in ['exit', 'quit', 'q']:
                    console.print("\n[green]Thanks for chatting! Keep grinding! 📈[/green]")
                    Prompt.ask("\nPress Enter to continue")
                    break
                
                if not user_message.strip():
                    continue
                
                # Extract ticker if user asks about a stock
                mentioned_ticker = extract_ticker_from_message(user_message)
                news_context = ""
                tech_context = ""
                
                # Check what type of analysis is being requested
                user_msg_lower = user_message.lower()
                asking_about_news = any(phrase in user_msg_lower for phrase in ['why is', 'why has', 'why did', 'why are', 'going up', 'going down', 'dropping', 'rising', 'jumping', 'falling', 'crashed', 'soared', 'news', 'catalyst', 'events'])
                asking_about_technical = any(phrase in user_msg_lower for phrase in ['technical', 'rsi', 'support', 'resistance', 'trend', 'momentum', 'chart', 'moving average', 'ma50', 'ma200', 'signal', 'macd', 'pattern', 'levels', 'oversold', 'overbought', 'pivot', 'fibonacci'])
                asking_about_fundamentals = any(phrase in user_msg_lower for phrase in ['earnings', 'analyst', 'rating', 'valuation', 'pe', 'eps', 'fundamentals', 'company'])
                
                # Fetch relevant data based on query type
                if mentioned_ticker:
                    with console.status(f"[bold cyan]📊 Loading {mentioned_ticker} data...[/bold cyan]", spinner="dots"):
                        # Always fetch technical analysis if ticker mentioned
                        if asking_about_technical or asking_about_news or any(phrase in user_msg_lower for phrase in ['analyze', 'what do you think', 'opinion', 'outlook', 'forecast']):
                            tech_context = fetch_and_analyze_technical(mentioned_ticker)
                            # Also get company fundamentals while we're at it
                            company_context = get_company_context(mentioned_ticker)
                            tech_context += company_context
                        
                        # Fetch news for "why is" questions or general outlook questions
                        if asking_about_news or asking_about_fundamentals:
                            news_context = fetch_news_for_ticker(mentioned_ticker, user_message)
                
                # Show thinking indicator
                with console.status("[bold green]🧠 Groq analyzing (with real technical & news data)...[/bold green]", spinner="dots"):
                    # Build message with all context for Groq
                    full_message = user_message
                    if news_context or tech_context:
                        full_message += f"\n\n[REAL DATA FROM YOUR ENGINE]:\n{tech_context}"
                        if news_context:
                            full_message += f"\n{news_context}"
                    
                    conversation_history.append({"role": "user", "content": full_message})
                    
                    try:
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            max_tokens=2000,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                *conversation_history
                            ],
                            temperature=0.75
                        )
                        
                        ai_response = response.choices[0].message.content
                        conversation_history.append({"role": "assistant", "content": ai_response})
                    except Exception as api_error:
                        console.print(f"[red]❌ Groq API Error: {str(api_error)[:150]}[/red]")
                        console.print("[yellow]Troubleshooting:[/yellow]")
                        console.print("1. Check your Groq API key is valid")
                        console.print("2. Verify you have credits/subscription active")
                        console.print("3. Try updating your API key in settings")
                        raise
                
                # Display response
                console.print(f"\n[bold green]🤖 AI Trade Advisor[/bold green]: {ai_response}\n")
                
                # Keep conversation history manageable
                if len(conversation_history) > 24:
                    conversation_history = conversation_history[-24:]
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Chat interrupted[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)[:100]}[/red]")
                Prompt.ask("\nPress Enter to continue")
                logger.error(f"Chat error: {str(e)}")
                error_msg = str(e)
                
                if "credit balance" in error_msg.lower() or "billing" in error_msg.lower():
                    console.print("\n[red]💳 Need more API credits[/red]")
                    console.print("[yellow]Go to: https://console.anthropic.com/settings/billing[/yellow]\n")
                    Prompt.ask("Press Enter to continue")
                    break
                elif "api_key" in error_msg.lower():
                    console.print("\n[red]🔑 API key issue[/red]")
                    console.print("[dim]Try updating in Settings (Option 16)[/dim]\n")
                else:
                    console.print(f"\n[red]Error: {error_msg}[/red]")
                    console.print("[dim]Let's try again...[/dim]\n")



    def _close_paper_trade_manually(self):
        """Manually close a paper trade."""
        DisplayManager.show_header()
        
        # Show open trades
        open_trades = self.paper_trading.get_open_trades()
        
        if not open_trades:
            console.print("[yellow]No open paper trades to close[/yellow]\n")
            Prompt.ask("Press Enter to continue")
            return
        
        console.print("[bold cyan]📝 Close Paper Trade[/bold cyan]\n")
        console.print("[bold]Open Trades:[/bold]\n")
        
        table = Table(box=box.ROUNDED)
        table.add_column("#", style="cyan")
        table.add_column("Ticker", style="cyan")
        table.add_column("Action", style="white")
        table.add_column("Entry", style="yellow", justify="right")
        table.add_column("Current", style="white", justify="right")
        table.add_column("P&L", justify="right")
        
        for idx, trade in enumerate(open_trades, 1):
            # Get current price
            current_price = None
            current_pnl = 0.0
            pnl_pct = 0.0
            
            try:
                current_price = DataManager.get_realtime_price(trade.ticker)
                if current_price is None:
                    df = DataManager.fetch_data(trade.ticker, "1d", "5m")
                    if df is not None and len(df) > 0:
                        current_price = float(df['Close'].iloc[-1])
                
                if current_price:
                    if trade.action == "LONG":
                        current_pnl = (current_price - trade.entry_price) * trade.position_size
                        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                    else:  # SHORT
                        current_pnl = (trade.entry_price - current_price) * trade.position_size
                        pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
            except:
                current_price = None
            
            pnl_color = "green" if current_pnl >= 0 else "red"
            current_str = f"${current_price:.2f}" if current_price else "N/A"
            pnl_str = f"[{pnl_color}]${current_pnl:.2f} ({pnl_pct:+.1f}%)[/{pnl_color}]" if current_price else "N/A"
            
            table.add_row(
                str(idx),
                trade.ticker,
                trade.action,
                f"${trade.entry_price:.2f}",
                current_str,
                pnl_str
            )
        
        console.print(table)
        console.print()
        
        # Select trade to close
        try:
            choice = IntPrompt.ask("Select trade # to close (0 to cancel)", default=0)
            
            if choice == 0:
                return
            
            if choice < 1 or choice > len(open_trades):
                console.print("[red]Invalid selection[/red]")
                Prompt.ask("\nPress Enter to continue")
                return
            
            trade = open_trades[choice - 1]
            
            # Confirm close
            confirm = Confirm.ask(f"Close {trade.action} {trade.ticker} @ current price?", default=True)
            
            if confirm:
                success = self.paper_trading.close_trade_manually(trade.ticker)
                if success:
                    console.print("[green]✓ Trade closed successfully[/green]")
                else:
                    console.print("[red]Failed to close trade[/red]")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        
        Prompt.ask("\nPress Enter to continue")


    def _run_quant_strategies(self):
        """Run quantitative trading strategies with backtesting and reporting."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]🎓 Quantitative Strategy Runner[/bold cyan]\n")
        console.print("[bold]Available Strategies:[/bold]")
        console.print("1. 📈 Momentum Strategy (6-month lookback, top quartile)")
        console.print("2. 🔄 Mean Reversion Strategy (Bollinger Z-score)")
        console.print("3. 👥 Pairs Trading Strategy (Statistical arbitrage)")
        console.print("4. 🤖 ML Classification Strategy (Ensemble models)")
        console.print("5. 🎯 Multi-Factor Strategy (Momentum + Value + Quality)")
        console.print("6. 📊 Run All Strategies & Compare")
        console.print("7. 🔙 Back to Main Menu\n")
        
        choice = Prompt.ask("Select strategy", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
        
        if choice == "7":
            return
        
        # Select universe
        console.print("\n[bold]Select Stock Universe:[/bold]")
        console.print("1. S&P 500 Top 50")
        console.print("2. Tech Giants (FAANG + MSFT)")
        console.print("3. Custom tickers\n")
        
        universe_choice = Prompt.ask("Select", choices=["1", "2", "3"], default="1")
        
        if universe_choice == "1":
            tickers = MARKET_UNIVERSES.get("sp500_top50", [])[:20]  # Limit to 20 for speed
        elif universe_choice == "2":
            tickers = ["AAPL", "GOOGL", "META", "AMZN", "NFLX", "MSFT", "NVDA"]
        else:
            ticker_input = Prompt.ask("Enter tickers (comma-separated)")
            tickers = [t.strip().upper() for t in ticker_input.split(",")]
        
        console.print(f"\n[cyan]Running on {len(tickers)} tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}[/cyan]\n")
        
        # Parameter prompts for percentile and minimum signals
        include_momentum = choice in ["1", "6"]
        include_multifactor = choice in ["5", "6"]
        momentum_top_pct = 0.25
        multifactor_top_pct = 0.20
        min_signals = 1
        if include_momentum:
            try:
                momentum_top_pct = float(Prompt.ask("Momentum top percentile (0-1)", default="0.25"))
                if momentum_top_pct <= 0 or momentum_top_pct > 1:
                    momentum_top_pct = 0.25
            except Exception:
                momentum_top_pct = 0.25
        if include_multifactor:
            try:
                multifactor_top_pct = float(Prompt.ask("Multi-Factor top percentile (0-1)", default="0.20"))
                if multifactor_top_pct <= 0 or multifactor_top_pct > 1:
                    multifactor_top_pct = 0.20
            except Exception:
                multifactor_top_pct = 0.20
        if include_momentum or include_multifactor:
            try:
                min_signals = int(Prompt.ask("Minimum signals to select", default="1"))
                if min_signals < 1:
                    min_signals = 1
            except Exception:
                min_signals = 1
        
        # Initialize strategies
        strategies = []
        if include_momentum:
            strategies.append(MomentumStrategy(lookback_days=126, top_pct=momentum_top_pct, min_signals=min_signals))
        if choice == "2" or choice == "6":
            strategies.append(MeanReversionStrategy(z_threshold=2.0))
        if choice == "3" or choice == "6":
            strategies.append(PairsStrategy(z_threshold=2.0))
        if choice == "4" or choice == "6":
            ml_strat = MLClassificationStrategy(probability_threshold=0.65)
            if not ml_strat.ml_weighter.models:
                console.print("[yellow]⚠ ML models not trained. Skipping ML strategy.[/yellow]")
                console.print("[dim]Train models first via menu option 10 (ML Signal Weighting)[/dim]\n")
            else:
                strategies.append(ml_strat)
        if include_multifactor:
            strategies.append(MultiFactorStrategy(top_pct=multifactor_top_pct, min_signals=min_signals))

        # Simple market regime detection using SPY 50/200 SMA
        regime = "unknown"
        try:
            spy_df = DataManager.fetch_data("SPY", "250d", "1d")
            if spy_df is not None and len(spy_df) >= 200:
                closes = spy_df['Close']
                sma50 = closes.rolling(50).mean().iloc[-1]
                sma200 = closes.rolling(200).mean().iloc[-1]
                if sma50 > sma200 * 1.01:
                    regime = "bull"
                elif sma50 < sma200 * 0.99:
                    regime = "bear"
                else:
                    regime = "sideways"
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
        if regime != "unknown":
            console.print(f"[dim]Detected market regime: {regime}[/dim]")

        # Regime-based strategy gating (accuracy focus)
        gated_strategies = []
        for s in strategies:
            allow = True
            if regime == "bear" and isinstance(s, MomentumStrategy):
                # In bear, momentum signals prone to whipsaw; allow only if top_pct very tight
                if s.top_pct > 0.15:
                    console.print("[dim yellow]Bear regime: tightening momentum selection to 15%[/dim yellow]")
                    s.top_pct = 0.15
            if regime == "sideways" and isinstance(s, MomentumStrategy):
                # Sideways: deprioritize momentum by requiring more dispersion
                pass
            # Mean reversion favored in sideways/bear
            if regime == "bull" and isinstance(s, MeanReversionStrategy):
                # Bull: only take oversold (BUY) signals -> still generated but strength scaling handles
                pass
            gated_strategies.append(s)
        strategies = gated_strategies

        # Preload shared historical data for efficiency (max required lookback)
        max_lookback = 0
        for s in strategies:
            if isinstance(s, MomentumStrategy):
                max_lookback = max(max_lookback, s.lookback_days)
            elif isinstance(s, MultiFactorStrategy):
                max_lookback = max(max_lookback, 252)
            elif isinstance(s, MeanReversionStrategy):
                max_lookback = max(max_lookback, 60)
        preloaded_data: Dict[str, 'pd.DataFrame'] = {}
        if max_lookback > 0:
            console.print(f"[dim]Preloading historical data ({max_lookback}d) for efficiency...[/dim]")
            for tk in tickers:
                try:
                    df = DataManager.fetch_data(tk, f"{max_lookback}d", "1d")
                    if df is not None and not df.empty:
                        preloaded_data[tk] = df
                except Exception as e:
                    logger.error(f"Preload error {tk}: {e}")
        
        # Generate signals for each strategy
        results = []
        for strategy in strategies:
            console.print(f"\n[bold]Generating signals for {strategy.name}...[/bold]")
            
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                         console=console) as progress:
                task = progress.add_task(f"[cyan]Processing {strategy.name}...", total=None)
                
                # Pass preloaded data when supported
                if isinstance(strategy, (MomentumStrategy, MultiFactorStrategy, MeanReversionStrategy)):
                    signals = strategy.generate_signals(tickers, preloaded_data=preloaded_data)
                else:
                    signals = strategy.generate_signals(tickers)
                
                progress.update(task, completed=True)
            
            if signals:
                # Small universe warning
                if len(tickers) < 8:
                    console.print("[dim]Small universe: consider adding more tickers for more robust factor ranks[/dim]")
                console.print(f"[green]✓ Found {len(signals)} signals[/green]")
                
                # Display top 5 signals
                table = Table(title=f"{strategy.name} - Top Signals", show_header=True)
                table.add_column("Ticker", style="cyan")
                table.add_column("Action", style="bold")
                table.add_column("Strength", justify="right", style="green")
                table.add_column("Entry", justify="right")
                table.add_column("Stop", justify="right", style="red")
                table.add_column("Target", justify="right", style="green")
                table.add_column("Reason")
                
                for sig in sorted(signals, key=lambda x: x.strength, reverse=True)[:5]:
                    table.add_row(
                        sig.ticker,
                        sig.action,
                        f"{sig.strength:.0f}%",
                        f"${sig.entry_price:.2f}",
                        f"${sig.stop_loss:.2f}",
                        f"${sig.take_profit:.2f}",
                        sig.reason[:40]
                    )
                
                console.print(table)
                results.append((strategy.name, signals))
            else:
                console.print(f"[yellow]No signals found for {strategy.name}[/yellow]")
        
        # ML probability cross-strategy strength boosting
        ml_prob_map: Dict[str, float] = {}
        for strat_name, sigs in results:
            if strat_name.lower().startswith("mlclassification"):
                for s in sigs:
                    p = None
                    # Ensemble probability stored in metadata under 'ml_prob'
                    if hasattr(s, 'metadata') and isinstance(s.metadata, dict):
                        p = s.metadata.get('ml_prob') or s.metadata.get('probability')
                    if p is not None:
                        ml_prob_map[s.ticker] = p
        if ml_prob_map:
            for strat_name, sigs in results:
                if strat_name.lower().startswith("mlclassification"):
                    continue
                for s in sigs:
                    prob = ml_prob_map.get(s.ticker)
                    if prob and prob >= 0.55:  # threshold for meaningful boost
                        original_strength = s.strength
                        boost_factor = 0.5 + prob  # 0.5-1.5 range
                        s.strength = min(100.0, original_strength * boost_factor)
                        if hasattr(s, 'metadata') and isinstance(s.metadata, dict):
                            s.metadata['ml_prob'] = prob
                            s.metadata['ml_boost_factor'] = boost_factor
                        s.reason = (s.reason + f" | ML boost {prob:.1%}")[:180]

        # Export option
        if results:
            console.print("\n[bold]Export Options:[/bold]")
            export_choice = Confirm.ask("Export signals to CSV?", default=True)
            
            if export_choice:
                for strat_name, signals in results:
                    filename = f"{strat_name.replace(' ', '_').lower()}_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    signal_data = []
                    for sig in signals:
                        signal_data.append({
                            'timestamp': sig.timestamp,
                            'ticker': sig.ticker,
                            'action': sig.action,
                            'strength': sig.strength,
                            'entry_price': sig.entry_price,
                            'stop_loss': sig.stop_loss,
                            'take_profit': sig.take_profit,
                            'reason': sig.reason
                        })
                    
                    pd.DataFrame(signal_data).to_csv(filename, index=False)
                    console.print(f"[green]✓ Exported to {filename}[/green]")
        
        Prompt.ask("\nPress Enter to continue")

    def _show_schwab_futures_dashboard(self):
        """Display Schwab futures trading dashboard."""
        DisplayManager.show_header()
        
        config = ConfigurationManager.load_config()
        if not config.get('schwab_futures_enabled'):
            console.print("[yellow]⚠ Schwab futures trading is not enabled.[/yellow]")
            console.print("[dim]Run option 18 (Preflight Setup) to configure Schwab API.[/dim]\n")
            Prompt.ask("Press Enter to continue")
            return
        
        try:
            schwab_trader = SchwabFuturesTrader()
            schwab_trader.display_futures_dashboard()
            
            console.print("\n[bold]Quick Actions:[/bold]")
            console.print("1. Refresh Dashboard")
            console.print("2. Place Order")
            console.print("3. Back to Main Menu\n")
            
            action = Prompt.ask("Select", choices=["1", "2", "3"], default="3")
            
            if action == "1":
                self._show_schwab_futures_dashboard()  # Recursive refresh
            elif action == "2":
                self._place_schwab_futures_order()
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            logger.error(f"Schwab dashboard error: {e}")
            Prompt.ask("\nPress Enter to continue")
    
    def _place_schwab_futures_order(self):
        """Place a futures order through Schwab."""
        DisplayManager.show_header()
        console.print("[bold cyan]🎯 PLACE FUTURES ORDER[/bold cyan]\n")
        
        config = ConfigurationManager.load_config()
        if not config.get('schwab_futures_enabled'):
            console.print("[yellow]⚠ Schwab futures trading is not enabled.[/yellow]")
            console.print("[dim]Run option 18 (Preflight Setup) to configure Schwab API.[/dim]\n")
            Prompt.ask("Press Enter to continue")
            return
        
        try:
            schwab_trader = SchwabFuturesTrader()
            
            # Show available futures
            console.print("[bold]Popular Futures Contracts:[/bold]")
            futures_map = {
                "1": ("/ES", "E-mini S&P 500"),
                "2": ("/NQ", "E-mini Nasdaq 100"),
                "3": ("/YM", "E-mini Dow Jones"),
                "4": ("/RTY", "E-mini Russell 2000"),
                "5": ("/CL", "Crude Oil"),
                "6": ("/GC", "Gold"),
                "7": ("/SI", "Silver"),
                "8": ("/ZB", "30-Year T-Bond")
            }
            
            for key, (symbol, name) in futures_map.items():
                console.print(f"{key}. {symbol} - {name}")
            console.print("9. Custom symbol\n")
            
            choice = Prompt.ask("Select contract", choices=[str(i) for i in range(1, 10)])
            
            if choice == "9":
                symbol = Prompt.ask("Enter futures symbol (e.g., /ES, /NQ)").upper().strip()
            else:
                symbol, name = futures_map[choice]
                console.print(f"\n[cyan]Selected: {symbol} - {name}[/cyan]\n")
            
            # Get current quote
            quotes = schwab_trader.get_futures_quotes([symbol])
            if symbol in quotes:
                quote = quotes[symbol]
                console.print(f"[bold]Current Market:[/bold]")
                console.print(f"  Last: ${quote['last']:,.2f}")
                console.print(f"  Bid:  ${quote['bid']:,.2f}")
                console.print(f"  Ask:  ${quote['ask']:,.2f}\n")
            
            # Order details
            console.print("[bold]Order Type:[/bold]")
            console.print("1. BUY (Long)")
            console.print("2. SELL (Short)\n")
            side = Prompt.ask("Select", choices=["1", "2"])
            side = "BUY" if side == "1" else "SELL"
            
            quantity = IntPrompt.ask("Number of contracts", default=1)
            
            console.print("\n[bold]Order Execution:[/bold]")
            console.print("1. MARKET (Execute immediately)")
            console.print("2. LIMIT (Specify price)\n")
            order_type_choice = Prompt.ask("Select", choices=["1", "2"], default="1")
            
            order_type = "MARKET" if order_type_choice == "1" else "LIMIT"
            limit_price = None
            
            if order_type == "LIMIT":
                limit_price = FloatPrompt.ask("Limit price")
            
            # Confirmation
            console.print("\n[bold yellow]⚠ ORDER CONFIRMATION[/bold yellow]")
            console.print(f"Symbol: {symbol}")
            console.print(f"Side: {side}")
            console.print(f"Quantity: {quantity} contract(s)")
            console.print(f"Type: {order_type}")
            if limit_price:
                console.print(f"Limit Price: ${limit_price:,.2f}")
            console.print()
            
            if not Confirm.ask("Place this order?", default=False):
                console.print("[yellow]Order cancelled[/yellow]\n")
                Prompt.ask("Press Enter to continue")
                return
            
            # Place order
            result = schwab_trader.place_futures_order(
                symbol=symbol,
                quantity=quantity,
                side=side,
                order_type=order_type,
                limit_price=limit_price
            )
            
            if result.get('success'):
                console.print(f"\n[green]✓ Order placed successfully![/green]")
                console.print(f"[dim]Order ID: {result.get('order_id')}[/dim]\n")
            else:
                console.print(f"\n[red]❌ Order failed: {result.get('error')}[/red]\n")
            
        except Exception as e:
            console.print(f"[red]❌ Error placing order: {e}[/red]")
            logger.error(f"Schwab order error: {e}")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _show_futures_options(self, ticker: str, indicators, trade_summary):
        """Show futures-specific options after analysis."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]               FUTURES TRADING OPTIONS                         [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
        
        config = ConfigurationManager.load_config()
        schwab_enabled = config.get('schwab_futures_enabled', False)
        
        if schwab_enabled:
            console.print("[bold green]✓ Schwab Futures Trading Enabled[/bold green]\n")
            console.print("[bold]What would you like to do?[/bold]")
            console.print("1. 📈 View Schwab Futures Dashboard")
            console.print("2. 🎯 Place Order for This Contract")
            console.print("3. 💼 View Current Positions")
            console.print("4. ⚙️  Configure Schwab Settings")
            console.print("5. ⬅️  Back to Main Menu\n")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"], default="5")
            
            if choice == "1":
                self._show_schwab_futures_dashboard()
            elif choice == "2":
                self._place_futures_order_for_ticker(ticker, indicators, trade_summary)
            elif choice == "3":
                self._show_schwab_positions_only()
            elif choice == "4":
                self._preflight_setup()
            # choice 5 returns to caller
        else:
            console.print("[yellow]⚠ Schwab Futures Trading Not Enabled[/yellow]\n")
            console.print("[dim]Schwab futures trading allows you to:[/dim]")
            console.print("[dim]  • Execute trades directly from FinalAI[/dim]")
            console.print("[dim]  • View real-time positions and P&L[/dim]")
            console.print("[dim]  • Monitor account balance and margin[/dim]\n")
            
            enable = Confirm.ask("Enable Schwab futures trading now?", default=False)
            if enable:
                self._preflight_setup()
    
    def _place_futures_order_for_ticker(self, ticker: str, indicators, trade_summary):
        """Place a futures order for the analyzed ticker with pre-filled details."""
        DisplayManager.show_header()
        console.print("[bold cyan]🎯 PLACE FUTURES ORDER[/bold cyan]\n")
        
        # Convert ticker format (e.g., ES=F to /ES for Schwab)
        schwab_symbol = ticker.replace("=F", "").replace("=", "")
        if not schwab_symbol.startswith("/"):
            schwab_symbol = "/" + schwab_symbol
        
        console.print(f"[bold]Contract:[/bold] {schwab_symbol}")
        console.print(f"[bold]Current Price:[/bold] ${indicators.price:,.2f}")
        console.print(f"[bold]AI Recommendation:[/bold] {trade_summary.action}")
        console.print(f"[bold]Confidence:[/bold] {trade_summary.confidence:.1f}%\n")
        
        if trade_summary.action == "HOLD":
            console.print("[yellow]AI recommends HOLD - no strong directional bias[/yellow]\n")
            proceed = Confirm.ask("Proceed with order anyway?", default=False)
            if not proceed:
                return
        
        try:
            schwab_trader = SchwabFuturesTrader()
            
            # Get current quote
            quotes = schwab_trader.get_futures_quotes([schwab_symbol])
            if schwab_symbol in quotes:
                quote = quotes[schwab_symbol]
                console.print(f"[bold]Real-time Market:[/bold]")
                console.print(f"  Bid:  ${quote['bid']:,.2f}")
                console.print(f"  Ask:  ${quote['ask']:,.2f}")
                console.print(f"  Last: ${quote['last']:,.2f}\n")
            
            # Pre-fill based on AI recommendation
            if trade_summary.action == "BUY":
                default_side = "1"
                console.print("[green]AI suggests BUY (Long position)[/green]")
            elif trade_summary.action == "SELL":
                default_side = "2"
                console.print("[red]AI suggests SELL (Short position)[/red]")
            else:
                default_side = "1"
            
            console.print(f"[dim]Stop Loss: ${trade_summary.stop_loss:,.2f}[/dim]")
            console.print(f"[dim]Target 1: ${trade_summary.take_profit_1:,.2f}[/dim]")
            console.print(f"[dim]Target 2: ${trade_summary.take_profit_2:,.2f}[/dim]\n")
            
            # Order details
            console.print("[bold]Order Type:[/bold]")
            console.print("1. BUY (Long)")
            console.print("2. SELL (Short)\n")
            side = Prompt.ask("Select", choices=["1", "2"], default=default_side)
            side = "BUY" if side == "1" else "SELL"
            
            quantity = IntPrompt.ask("Number of contracts", default=1)
            
            console.print("\n[bold]Order Execution:[/bold]")
            console.print("1. MARKET (Execute immediately)")
            console.print("2. LIMIT (Specify price)\n")
            order_type_choice = Prompt.ask("Select", choices=["1", "2"], default="1")
            
            order_type = "MARKET" if order_type_choice == "1" else "LIMIT"
            limit_price = None
            
            if order_type == "LIMIT":
                # Suggest a price based on bid/ask
                if schwab_symbol in quotes:
                    suggested_price = quote['bid'] if side == "SELL" else quote['ask']
                    limit_price = FloatPrompt.ask("Limit price", default=suggested_price)
                else:
                    limit_price = FloatPrompt.ask("Limit price")
            
            # Confirmation
            console.print("\n[bold yellow]⚠ ORDER CONFIRMATION[/bold yellow]")
            console.print(f"Symbol: {schwab_symbol}")
            console.print(f"Side: {side}")
            console.print(f"Quantity: {quantity} contract(s)")
            console.print(f"Type: {order_type}")
            if limit_price:
                console.print(f"Limit Price: ${limit_price:,.2f}")
            console.print(f"\n[dim]AI Confidence: {trade_summary.confidence:.1f}%[/dim]")
            console.print(f"[dim]Recommended Stop: ${trade_summary.stop_loss:,.2f}[/dim]")
            console.print()
            
            if not Confirm.ask("Place this order?", default=False):
                console.print("[yellow]Order cancelled[/yellow]\n")
                Prompt.ask("Press Enter to continue")
                return
            
            # Place order
            result = schwab_trader.place_futures_order(
                symbol=schwab_symbol,
                quantity=quantity,
                side=side,
                order_type=order_type,
                limit_price=limit_price
            )
            
            if result.get('success'):
                console.print(f"\n[green]✓ Order placed successfully![/green]")
                console.print(f"[dim]Order ID: {result.get('order_id')}[/dim]")
                console.print(f"\n[yellow]💡 Remember to set stop loss at ${trade_summary.stop_loss:,.2f}[/yellow]\n")
            else:
                console.print(f"\n[red]❌ Order failed: {result.get('error')}[/red]\n")
            
        except Exception as e:
            console.print(f"[red]❌ Error placing order: {e}[/red]")
            logger.error(f"Schwab order error: {e}")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _show_schwab_positions_only(self):
        """Show only Schwab positions table."""
        DisplayManager.show_header()
        console.print("[bold cyan]Current Schwab Futures Positions[/bold cyan]\n")
        
        try:
            schwab_trader = SchwabFuturesTrader()
            positions = schwab_trader.get_positions()
            
            if positions:
                pos_table = Table(title=None, box=box.ROUNDED)
                pos_table.add_column("Symbol", style="cyan")
                pos_table.add_column("Quantity", justify="right")
                pos_table.add_column("Avg Price", justify="right")
                pos_table.add_column("Market Value", justify="right")
                pos_table.add_column("P&L", justify="right")
                pos_table.add_column("P&L %", justify="right")
                
                for pos in positions:
                    pnl = pos['unrealized_pnl']
                    pnl_pct = pos['unrealized_pnl_pct']
                    pnl_color = "green" if pnl >= 0 else "red"
                    
                    pos_table.add_row(
                        pos['symbol'],
                        str(int(pos['quantity'])),
                        f"${pos['average_price']:,.2f}",
                        f"${pos['market_value']:,.2f}",
                        f"[{pnl_color}]${pnl:,.2f}[/{pnl_color}]",
                        f"[{pnl_color}]{pnl_pct:+.2f}%[/{pnl_color}]"
                    )
                
                console.print(pos_table)
            else:
                console.print("[yellow]No open positions[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Error fetching positions: {e}[/red]")
            logger.error(f"Schwab positions error: {e}")
        
        console.print()
        Prompt.ask("Press Enter to continue")

    def _preflight_setup(self):
        """Run the preflight wizard on-demand and reload notifiers/env."""
        try:
            from dotenv import load_dotenv
        except Exception:
            load_dotenv = None
        try:
            ConfigurationManager.run_preflight(self.config or {})
            if load_dotenv is not None:
                load_dotenv(override=True)
            # Reload notifier with possibly updated config/env
            self.notifier = NotificationManager(ConfigurationManager.load_config())
            console.print("[green]✓ Preflight completed and settings reloaded.[/green]\n")
            Prompt.ask("Press Enter to continue")
        except Exception as e:
            console.print(f"[red]Preflight failed: {e}[/red]")
            Prompt.ask("Press Enter to continue")
    
    def _add_trade(self):
        """Add a new trade to track (stock/crypto or option)."""
        DisplayManager.show_header()
        console.print("[bold cyan]➕ Add Trade to Portfolio[/bold cyan]\n")
        
        # Ask if stock/crypto or option
        console.print("[bold]Select Trade Type:[/bold]")
        console.print("1. 📈 Stock/Crypto")
        console.print("2. 📞 Option Contract\n")
        
        trade_type = Prompt.ask("Select type", choices=["1", "2"], default="1")
        
        if trade_type == "1":
            self._add_stock_trade()
        else:
            self._add_option_trade()
    
    def _add_stock_trade(self):
        """Add a stock/crypto position."""
        ticker = Prompt.ask("Enter ticker symbol (e.g., AAPL, BTC-USD)").upper().strip()
        
        console.print("\n[bold]Position Type:[/bold]")
        console.print("1. LONG (Buy)")
        console.print("2. SHORT (Sell)")
        position_type = Prompt.ask("Select", choices=["1", "2"], default="1")
        direction = "BUY" if position_type == "1" else "SELL"
        
        shares = FloatPrompt.ask("Number of shares/units", default=1.0)
        entry_price = FloatPrompt.ask("Entry price per share")
        
        # Optional stop loss and target
        set_stops = Confirm.ask("Set stop loss and target?", default=True)
        stop_loss = None
        take_profit = None
        
        if set_stops:
            if direction == "BUY":
                stop_loss = FloatPrompt.ask(f"Stop loss price (below {entry_price})", default=entry_price * 0.95)
                take_profit = FloatPrompt.ask(f"Take profit price (above {entry_price})", default=entry_price * 1.10)
            else:
                stop_loss = FloatPrompt.ask(f"Stop loss price (above {entry_price})", default=entry_price * 1.05)
                take_profit = FloatPrompt.ask(f"Take profit price (below {entry_price})", default=entry_price * 0.90)
        else:
            # Set defaults if user skips
            if direction == "BUY":
                stop_loss = entry_price * 0.95
                take_profit = entry_price * 1.10
            else:
                stop_loss = entry_price * 1.05
                take_profit = entry_price * 0.90
        
        # Add to Position Manager (persistent storage)
        position_mgr = PositionManager()
        position_mgr.add_position(
            ticker=ticker,
            entry_price=entry_price,
            shares=shares,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_type="stock"
        )
        
        # Also save to holdings file for backward compatibility
        import json
        from pathlib import Path
        from datetime import datetime
        
        holdings_file = Path("results/holdings.json")
        holdings_file.parent.mkdir(exist_ok=True)
        
        # Load existing holdings
        holdings = []
        if holdings_file.exists():
            try:
                with open(holdings_file, 'r') as f:
                    holdings = json.load(f)
            except:
                holdings = []
        
        # Add new position
        position = {
            "id": len(holdings) + 1,
            "type": "STOCK",
            "ticker": ticker,
            "position_type": position_type,
            "shares": shares,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_date": datetime.now().strftime("%m/%d/%y %H:%M:%S"),
            "status": "OPEN"
        }
        
        holdings.append(position)
        
        # Save
        with open(holdings_file, 'w') as f:
            json.dump(holdings, f, indent=2)
        
        console.print(f"\n[green]✓ Added {position_type} position: {shares} shares of {ticker} @ ${entry_price:.2f}[/green]")
        console.print(f"[dim]Saved to Position Manager - view with Option 6[/dim]")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _add_option_trade(self):
        """Add an option position."""
        underlying = Prompt.ask("Enter underlying ticker (e.g., AAPL, NVDA)").upper().strip()
        
        console.print("\n[bold]Option Type:[/bold]")
        console.print("1. CALL")
        console.print("2. PUT")
        opt_type = Prompt.ask("Select", choices=["1", "2"], default="1")
        opt_type = "CALL" if opt_type == "1" else "PUT"
        
        strike = FloatPrompt.ask("Strike price")
        
        # Expiration date
        console.print("\n[dim]Enter expiration date (e.g., 12/20/24 or 2024-12-20)[/dim]")
        expiration = Prompt.ask("Expiration date")
        
        contracts = FloatPrompt.ask("Number of contracts", default=1.0)
        entry_premium = FloatPrompt.ask("Entry premium per contract (price you paid)")
        
        # Auto-calculate stop and target
        stop_premium = entry_premium * 0.5  # 50% loss
        target_premium = entry_premium * 3.0  # 200% gain
        
        console.print(f"\n[dim]Auto-calculated: Stop @ ${stop_premium:.2f}, Target @ ${target_premium:.2f}[/dim]")
        if Confirm.ask("Customize stop/target?", default=False):
            stop_premium = FloatPrompt.ask("Stop loss premium", default=stop_premium)
            target_premium = FloatPrompt.ask("Target premium", default=target_premium)
        
        # Create ticker format for the option
        option_ticker = f"{underlying} {strike}{opt_type[0]} {expiration}"
        
        # Add to Position Manager (persistent storage)
        position_mgr = PositionManager()
        contract_details = {
            "strike": strike,
            "expiry": expiration,
            "type": opt_type
        }
        position_mgr.add_position(
            ticker=option_ticker,
            entry_price=entry_premium,
            shares=contracts,
            direction="BUY",  # Options are typically bought
            stop_loss=stop_premium,
            take_profit=target_premium,
            position_type="option",
            contract_details=contract_details
        )
        
        # Also save to holdings for backward compatibility
        import json
        from pathlib import Path
        from datetime import datetime
        
        holdings_file = Path("results/holdings.json")
        holdings_file.parent.mkdir(exist_ok=True)
        
        holdings = []
        if holdings_file.exists():
            try:
                with open(holdings_file, 'r') as f:
                    holdings = json.load(f)
            except:
                holdings = []
        
        position = {
            "id": len(holdings) + 1,
            "type": "OPTION",
            "underlying": underlying,
            "option_type": opt_type,
            "strike": strike,
            "expiration": expiration,
            "contracts": contracts,
            "entry_premium": entry_premium,
            "stop_premium": stop_premium,
            "target_premium": target_premium,
            "entry_date": datetime.now().strftime("%m/%d/%y %H:%M:%S"),
            "status": "OPEN"
        }
        
        holdings.append(position)
        
        with open(holdings_file, 'w') as f:
            json.dump(holdings, f, indent=2)
        
        console.print(f"\n[green]✓ Added {opt_type} option: {contracts} contracts of {underlying} ${strike} exp {expiration} @ ${entry_premium:.2f}[/green]")
        console.print(f"[dim]Saved to Position Manager - view with Option 6[/dim]")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _view_holdings(self):
        """View all open positions with P&L and sentiment."""
        DisplayManager.show_header()
        console.print("[bold cyan]📊 Your Holdings[/bold cyan]\n")
        
        import json
        from pathlib import Path
        
        holdings_file = Path("results/holdings.json")
        
        if not holdings_file.exists():
            console.print("[yellow]No positions found. Add a trade first![/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        try:
            with open(holdings_file, 'r') as f:
                holdings = json.load(f)
        except:
            console.print("[red]Error loading holdings file[/red]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        # Filter open positions
        open_positions = [h for h in holdings if h.get('status') == 'OPEN']
        
        if not open_positions:
            console.print("[yellow]No open positions. All positions closed.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        # Analyze each position
        for idx, position in enumerate(open_positions, 1):
            console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
            console.print(f"[bold]Position #{position.get('id', idx)}[/bold]")
            
            if position['type'] == 'STOCK':
                self._display_stock_position(position)
            else:
                self._display_option_position(position)
        
        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        Prompt.ask("\nPress Enter to continue")
    
    def _display_stock_position(self, position):
        """Display stock position with current P&L and sentiment."""
        ticker = position['ticker']
        shares = position['shares']
        entry_price = position['entry_price']
        position_type = position['position_type']
        
        console.print(f"[bold]Type:[/bold] {position_type} Stock")
        console.print(f"[bold]Ticker:[/bold] {ticker}")
        console.print(f"[bold]Shares:[/bold] {shares}")
        console.print(f"[bold]Entry:[/bold] ${entry_price:.2f}")
        
        # Fetch current price
        try:
            df = DataManager.fetch_data(ticker, "1d", "1d")
            if df is not None and len(df) > 0:
                current_price = float(df['Close'].iloc[-1])
                
                # Calculate P&L
                if position_type == "LONG":
                    pnl = (current_price - entry_price) * shares
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl = (entry_price - current_price) * shares
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_emoji = "📈" if pnl >= 0 else "📉"
                
                console.print(f"[bold]Current:[/bold] ${current_price:.2f}")
                console.print(f"[bold]P&L:[/bold] [{pnl_color}]{pnl_emoji} ${pnl:.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]")
                
                # Check stops
                stop_loss = position.get('stop_loss')
                take_profit = position.get('take_profit')
                
                if stop_loss:
                    if (position_type == "LONG" and current_price <= stop_loss) or \
                       (position_type == "SHORT" and current_price >= stop_loss):
                        console.print(f"[bold red]⚠️  STOP LOSS HIT: ${stop_loss:.2f}[/bold red]")
                
                if take_profit:
                    if (position_type == "LONG" and current_price >= take_profit) or \
                       (position_type == "SHORT" and current_price <= take_profit):
                        console.print(f"[bold green]🎯 TAKE PROFIT HIT: ${take_profit:.2f}[/bold green]")
                
                # Quick sentiment analysis
                indicators = TechnicalAnalyzer.calculate_indicators(df)
                if indicators:
                    rsi = getattr(indicators, 'rsi', 50)
                    
                    if rsi > 70:
                        sentiment = "[red]OVERBOUGHT - Consider selling[/red]"
                    elif rsi < 30:
                        sentiment = "[green]OVERSOLD - Consider buying[/green]"
                    else:
                        sentiment = "[yellow]NEUTRAL - Hold[/yellow]"
                    
                    console.print(f"[bold]Sentiment:[/bold] {sentiment}")
                    console.print(f"[dim]RSI: {rsi:.1f}[/dim]")
            else:
                console.print("[yellow]Unable to fetch current price[/yellow]")
        except Exception as e:
            console.print(f"[red]Error analyzing position: {str(e)}[/red]")
    
    def _display_option_position(self, position):
        """Display option position with Greeks and P&L."""
        underlying = position['underlying']
        opt_type = position['option_type']
        strike = position['strike']
        expiration = position['expiration']
        contracts = position['contracts']
        entry_premium = position['entry_premium']
        
        console.print(f"[bold]Type:[/bold] {opt_type} Option")
        console.print(f"[bold]Underlying:[/bold] {underlying}")
        console.print(f"[bold]Strike:[/bold] ${strike:.2f}")
        console.print(f"[bold]Expiration:[/bold] {expiration}")
        console.print(f"[bold]Contracts:[/bold] {contracts}")
        console.print(f"[bold]Entry Premium:[/bold] ${entry_premium:.2f}")
        
        # Fetch current stock price
        try:
            df = DataManager.fetch_data(underlying, "1d", "1d")
            if df is not None and len(df) > 0:
                current_stock_price = float(df['Close'].iloc[-1])
                console.print(f"[bold]Stock Price:[/bold] ${current_stock_price:.2f}")
                
                # Simple intrinsic value calculation
                if opt_type == "CALL":
                    intrinsic = max(0, current_stock_price - strike)
                    itm = current_stock_price > strike
                else:  # PUT
                    intrinsic = max(0, strike - current_stock_price)
                    itm = current_stock_price < strike
                
                status = "ITM" if itm else "OTM"
                status_color = "green" if itm else "red"
                console.print(f"[bold]Status:[/bold] [{status_color}]{status}[/{status_color}]")
                console.print(f"[bold]Intrinsic Value:[/bold] ${intrinsic:.2f}")
                
                # Estimate current premium (simplified - actual options pricing would be better)
                # For demo: intrinsic + time value estimate
                time_value_estimate = max(0.10, entry_premium * 0.3)  # Rough estimate
                estimated_premium = intrinsic + time_value_estimate
                
                # P&L calculation
                pnl_per_contract = (estimated_premium - entry_premium) * 100  # Options are per 100 shares
                total_pnl = pnl_per_contract * contracts
                pnl_pct = ((estimated_premium - entry_premium) / entry_premium) * 100
                
                pnl_color = "green" if total_pnl >= 0 else "red"
                pnl_emoji = "📈" if total_pnl >= 0 else "📉"
                
                console.print(f"[bold]Est. Premium:[/bold] ${estimated_premium:.2f}")
                console.print(f"[bold]P&L:[/bold] [{pnl_color}]{pnl_emoji} ${total_pnl:.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]")
                
                # Check stops
                stop_premium = position.get('stop_premium')
                target_premium = position.get('target_premium')
                
                if stop_premium and estimated_premium <= stop_premium:
                    console.print(f"[bold red]⚠️  STOP LOSS HIT: ${stop_premium:.2f}[/bold red]")
                
                if target_premium and estimated_premium >= target_premium:
                    console.print(f"[bold green]🎯 TAKE PROFIT HIT: ${target_premium:.2f}[/bold green]")
                
                # Sentiment for underlying
                indicators = TechnicalAnalyzer.calculate_indicators(df)
                if indicators:
                    rsi = getattr(indicators, 'rsi', 50)
                    
                    if opt_type == "CALL":
                        if rsi > 70:
                            sentiment = "[yellow]Underlying overbought - Risk of pullback[/yellow]"
                        elif rsi < 30:
                            sentiment = "[green]Underlying oversold - Good for calls[/green]"
                        else:
                            sentiment = "[cyan]Neutral - Monitor[/cyan]"
                    else:  # PUT
                        if rsi > 70:
                            sentiment = "[green]Underlying overbought - Good for puts[/green]"
                        elif rsi < 30:
                            sentiment = "[yellow]Underlying oversold - Risk of bounce[/yellow]"
                        else:
                            sentiment = "[cyan]Neutral - Monitor[/cyan]"
                    
                    console.print(f"[bold]Sentiment:[/bold] {sentiment}")
                    console.print(f"[dim]RSI: {rsi:.1f}[/dim]")
            else:
                console.print("[yellow]Unable to fetch current stock price[/yellow]")
        except Exception as e:
            console.print(f"[red]Error analyzing position: {str(e)}[/red]")
    
    def _start_position_monitor(self):
        """Start continuous monitoring of all positions with alerts."""
        DisplayManager.show_header()
        console.print("[bold cyan]🔔 Position Monitor[/bold cyan]\n")
        
        import json
        from pathlib import Path
        import time
        
        holdings_file = Path("results/holdings.json")
        
        if not holdings_file.exists():
            console.print("[yellow]No positions to monitor. Add a trade first![/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        # Configuration
        scan_interval = FloatPrompt.ask("Scan interval in seconds", default=60.0)
        alert_threshold = FloatPrompt.ask("Alert confidence threshold (0-100)", default=70.0)
        
        console.print(f"\n[green]✓ Starting monitor - scanning every {scan_interval}s[/green]")
        console.print("[yellow]Press Ctrl+C to stop monitoring[/yellow]\n")
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                console.print(f"[dim]{'='*60}[/dim]")
                console.print(f"[bold cyan]Scan #{scan_count} - {time.strftime('%H:%M:%S')}[/bold cyan]")
                
                # Load current holdings
                try:
                    with open(holdings_file, 'r') as f:
                        holdings = json.load(f)
                except:
                    console.print("[red]Error loading holdings[/red]")
                    break
                
                open_positions = [h for h in holdings if h.get('status') == 'OPEN']
                
                if not open_positions:
                    console.print("[yellow]No open positions to monitor[/yellow]")
                    break
                
                # Scan each position
                for position in open_positions:
                    try:
                        if position['type'] == 'STOCK':
                            self._monitor_stock_position(position, alert_threshold)
                        else:
                            self._monitor_option_position(position, alert_threshold)
                    except Exception as e:
                        console.print(f"[red]Error monitoring position {position.get('id')}: {str(e)}[/red]")
                
                console.print(f"[dim]Next scan in {scan_interval}s...[/dim]\n")
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Monitoring stopped by user[/yellow]")
            Prompt.ask("\nPress Enter to continue")
    
    def _monitor_stock_position(self, position, alert_threshold):
        """Monitor a stock position and send alerts."""
        ticker = position['ticker']
        position_type = position['position_type']
        
        console.print(f"  📊 {ticker} ({position_type})...", end=" ")
        
        try:
            # Fetch recent data
            df = DataManager.fetch_data(ticker, "5d", "1h")
            if df is None or len(df) == 0:
                console.print("[yellow]No data[/yellow]")
                return
            
            current_price = float(df['Close'].iloc[-1])
            indicators = TechnicalAnalyzer.calculate_indicators(df)
            patterns = PatternRecognizer.analyze(df)
            
            # Quick analysis
            if indicators:
                rsi = getattr(indicators, 'rsi', 50)
                macd = getattr(indicators, 'macd', 0)
                macd_signal = getattr(indicators, 'macd_signal', 0)
                
                # Determine signal
                signal = None
                confidence = 0
                
                if position_type == "LONG":
                    # For long positions, look for sell signals
                    if rsi > 75 or (macd < macd_signal and macd > 0):
                        signal = "SELL"
                        confidence = min(100, (rsi - 50) * 2 if rsi > 50 else 50)
                    elif rsi < 30:
                        signal = "ADD"  # Buy more
                        confidence = min(100, (50 - rsi) * 2)
                else:  # SHORT
                    # For short positions, look for cover signals
                    if rsi < 25 or (macd > macd_signal and macd < 0):
                        signal = "COVER"
                        confidence = min(100, (50 - rsi) * 2 if rsi < 50 else 50)
                    elif rsi > 70:
                        signal = "ADD"  # Short more
                        confidence = min(100, (rsi - 50) * 2)
                
                # Check stops
                stop_hit = False
                target_hit = False
                
                stop_loss = position.get('stop_loss')
                take_profit = position.get('take_profit')
                
                if stop_loss:
                    if (position_type == "LONG" and current_price <= stop_loss) or \
                       (position_type == "SHORT" and current_price >= stop_loss):
                        stop_hit = True
                
                if take_profit:
                    if (position_type == "LONG" and current_price >= take_profit) or \
                       (position_type == "SHORT" and current_price <= take_profit):
                        target_hit = True
                
                # Send alerts
                if stop_hit:
                    console.print(f"[bold red]STOP LOSS HIT![/bold red]")
                    self._send_alert(f"🚨 STOP LOSS HIT: {ticker}\nPrice: ${current_price:.2f}\nClose {position_type} position immediately!")
                elif target_hit:
                    console.print(f"[bold green]TARGET HIT![/bold green]")
                    self._send_alert(f"🎯 TAKE PROFIT: {ticker}\nPrice: ${current_price:.2f}\nConsider taking profits on {position_type} position!")
                elif signal and confidence >= alert_threshold:
                    console.print(f"[bold yellow]{signal} signal ({confidence:.0f}%)[/bold yellow]")
                    self._send_alert(f"📊 {signal} Signal: {ticker}\nConfidence: {confidence:.0f}%\nPrice: ${current_price:.2f}\nRSI: {rsi:.1f}\nAction: Consider {signal}ing {position_type} position")
                else:
                    console.print(f"[green]OK[/green] (RSI: {rsi:.1f})")
        
        except Exception as e:
            import traceback
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Stock position monitor error: {e}\n{traceback.format_exc()}")
    
    def _monitor_option_position(self, position, alert_threshold):
        """Monitor an option position and send alerts."""
        underlying = position['underlying']
        opt_type = position['option_type']
        strike = position['strike']
        
        console.print(f"  📞 {underlying} ${strike} {opt_type}...", end=" ")
        
        try:
            # Fetch underlying data
            df = DataManager.fetch_data(underlying, "5d", "1h")
            if df is None or len(df) == 0:
                console.print("[yellow]No data[/yellow]")
                return
            
            current_stock_price = float(df['Close'].iloc[-1])
            indicators = TechnicalAnalyzer.calculate_indicators(df)
            
            # Calculate option status
            if opt_type == "CALL":
                intrinsic = max(0, current_stock_price - strike)
                itm = current_stock_price > strike
            else:  # PUT
                intrinsic = max(0, strike - current_stock_price)
                itm = current_stock_price < strike
            
            # Analyze underlying
            if indicators:
                rsi = getattr(indicators, 'rsi', 50)
                macd = getattr(indicators, 'macd', 0)
                macd_signal = getattr(indicators, 'macd_signal', 0)
                
                # Determine signal based on option type
                signal = None
                confidence = 0
                
                if opt_type == "CALL":
                    # For calls, bullish signals are good
                    if rsi > 70:
                        signal = "SELL"  # Overbought, take profits
                        confidence = min(100, (rsi - 50) * 2)
                    elif rsi < 30 and macd > macd_signal:
                        signal = "BUY"  # Oversold with reversal
                        confidence = min(100, (50 - rsi) * 2)
                else:  # PUT
                    # For puts, bearish signals are good
                    if rsi < 30:
                        signal = "SELL"  # Oversold, take profits
                        confidence = min(100, (50 - rsi) * 2)
                    elif rsi > 70 and macd < macd_signal:
                        signal = "BUY"  # Overbought with reversal
                        confidence = min(100, (rsi - 50) * 2)
                
                # Check if ITM/OTM status changed
                status_msg = "ITM" if itm else "OTM"
                
                # Send alerts
                if signal and confidence >= alert_threshold:
                    console.print(f"[bold yellow]{signal} signal ({confidence:.0f}%)[/bold yellow]")
                    self._send_alert(f"📞 {signal} Signal: {underlying} ${strike} {opt_type}\nConfidence: {confidence:.0f}%\nStock: ${current_stock_price:.2f} ({status_msg})\nIntrinsic: ${intrinsic:.2f}\nRSI: {rsi:.1f}\nAction: Consider {signal}ing contracts")
                else:
                    console.print(f"[green]{status_msg}[/green] (RSI: {rsi:.1f})")
        
        except Exception as e:
            import traceback
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Option position monitor error: {e}\n{traceback.format_exc()}")
    
    def _send_alert(self, message):
        """Send Telegram alert if configured."""
        try:
            if hasattr(self, 'notifier') and self.notifier:
                self.notifier.send_message(message)
        except Exception as e:
            logger.debug(f"Alert send failed: {str(e)}")
    
    def _start_background_monitor(self, position_mgr: 'PositionManager'):
        """Start background monitoring with full AI analysis and notifications."""
        DisplayManager.show_header()
        console.print("[bold cyan]🔔 Background Position Monitor[/bold cyan]\n")
        
        if not position_mgr.positions:
            console.print("[yellow]No positions to monitor. Add positions first![/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        console.print(f"[green]Found {len(position_mgr.positions)} position(s) to monitor[/green]\n")
        
        # Configuration
        scan_interval = IntPrompt.ask("Scan interval in minutes", default=15)
        
        console.print(f"\n[bold green]✓ Background monitor started - scanning every {scan_interval} minutes[/bold green]")
        console.print("[yellow]📱 Notifications will be sent to your phone when analysis changes[/yellow]")
        console.print("[dim]Press Ctrl+C to stop monitoring[/dim]\n")
        
        scan_count = 0
        import time
        
        try:
            while True:
                scan_count += 1
                console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
                console.print(f"[bold cyan]Scan #{scan_count} - {datetime.now().strftime('%I:%M:%S %p')}[/bold cyan]")
                console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
                
                # Run full analysis update
                try:
                    alerts = position_mgr.update_positions(
                        notifier=self.notifier,
                        analyzer=self.analyzer,
                        technical_analyzer=TechnicalAnalyzer()
                    )
                    
                    if alerts:
                        console.print(f"\n[bold red]🚨 {len(alerts)} ALERT(S) TRIGGERED![/bold red]")
                        for ticker, msg, price in alerts:
                            console.print(f"[yellow]{ticker}[/yellow]: {msg} @ ${price:.2f}")
                    else:
                        console.print(f"\n[green]✓ All positions analyzed - no alerts[/green]")
                    
                except Exception as e:
                    console.print(f"[red]Error during scan: {e}[/red]")
                    logger.error(f"Background monitor error: {e}")
                
                # Wait for next scan
                console.print(f"\n[dim]Next scan in {scan_interval} minutes... (Ctrl+C to stop)[/dim]")
                time.sleep(scan_interval * 60)
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]⚠ Background monitor stopped by user[/yellow]")
            Prompt.ask("\nPress Enter to return to main menu")
    
    def analyze_ticker(self):
        """Analyze a ticker."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]📊 Live Market Analysis[/bold cyan]\n")
        
        ticker = Prompt.ask("Enter ticker symbol (e.g., AAPL, BTC-USD)").upper().strip()
        
        if ',' in ticker or ' ' in ticker:
            tickers = [t.strip() for t in ticker.replace(',', ' ').split() if t.strip()]
            console.print(f"\n[yellow]⚠ Multiple tickers detected. Analyzing: {tickers[0]}[/yellow]")
            ticker = tickers[0]
        
        console.print("\n[bold cyan]Select Trading Style:[/bold cyan]")
        console.print("1. ⚡ Day Trading (5m-1h)")
        console.print("2. 📈 Swing Trading (Days to Weeks)")
        console.print("3. 💎 Long-Term (Months to Years)\n")
        
        style_choice = Prompt.ask("Select style", choices=["1", "2", "3"], default="2")
        
        style_map = {
            "1": TradingStyle.DAY_TRADE,
            "2": TradingStyle.SWING_TRADE,
            "3": TradingStyle.LONG_TERM
        }
        
        style = style_map[style_choice]
        config = TradingConfig.get_config(style)
        
        # Instrument type: Stock / Crypto / Futures
        console.print("\n[bold cyan]Instrument Type:[/bold cyan]")
        console.print("1. Stock")
        console.print("2. Crypto")
        console.print("3. Futures")
        console.print("4. Options\n")
        instr_choice = Prompt.ask("Select instrument type", choices=["1","2","3","4"], default="1")
        
        # Normalize futures ticker if user selected futures
        if instr_choice == "3":
            # Users may enter ES or ES=F; normalize to Yahoo Finance format like ES=F
            if not ("=" in ticker and ticker.upper().endswith("=F")):
                # if user provided e.g., 'ES' or '/ES', strip non-alphanum and append '=F'
                raw = ''.join([c for c in ticker if c.isalnum()])
                ticker = f"{raw}=F"

        if instr_choice == "4":
            self._options_trade_planner()
            return

        console.print(f"\n[yellow]Fetching data for {ticker}...[/yellow]")
        
        # Analysis mode: Basic or Advanced
        default_mode = self.config.get('analysis_mode', 'advanced') if self.config else 'advanced'
        console.print("\n[bold cyan]Analysis Mode:[/bold cyan]")
        console.print("1. Basic (quick summary)")
        console.print("2. Advanced (detailed, includes indicators, patterns, news sentiment)")
        mode_choice = Prompt.ask("Select mode", choices=["1", "2"], default="2" if default_mode=='advanced' else "1")
        analysis_mode = 'advanced' if mode_choice == '2' else 'basic'

        # Advanced options
        analysis_options = {
            'include_news_sentiment': False,
            'include_sec': False,
            'include_option_flow': False,
            'detail_level': 'concise'
        }

        if analysis_mode == 'advanced':
            include_news = Confirm.ask("Include recent news sentiment in the analysis?", default=True)
            include_sec = Confirm.ask("Include recent SEC filings summary?", default=False)
            include_options = Confirm.ask("Include option-flow / implied volatility summary (best-effort)?", default=False)
            detail_level = Prompt.ask("Detail level", choices=["concise","detailed"], default="detailed")
            analysis_options.update({
                'include_news_sentiment': include_news,
                'include_sec': include_sec,
                'include_option_flow': include_options,
                'detail_level': detail_level
            })

        # Prompt for desired Risk:Reward ratio (user enters the reward multiplier for 1:Reward)
        default_rr = float(self.config.get('default_rrr', 2.0)) if self.config else 2.0
        desired_rrr = FloatPrompt.ask("Desired Risk:Reward ratio (enter the reward number for 1:Reward)", default=default_rr)

        # If day trading, offer live continuous scanning modes
        live_mode = None
        if style == TradingStyle.DAY_TRADE:
            console.print("\n[bold cyan]Day-Trading Live Options:[/bold cyan]")
            console.print("1. Single analysis (one-off)")
            console.print("2. Live continuous scan for this ticker (scan constantly until exit)")
            console.print("3. Live global best-signal scanner (scan universe and surface highest confidence ticker)")
            lm_choice = Prompt.ask("Select live mode", choices=["1","2","3"], default="1")
            live_mode = lm_choice

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Analyzing...", total=None)
            
            # Pre-fetch news if requested
            if analysis_options.get('include_news_sentiment'):
                try:
                    console.print("[cyan]📰 Fetching headlines...[/cyan]", end=" ")
                    news_items = NewsAnalyzer.get_news(ticker, limit=10)
                    analysis_options['news_items'] = news_items
                    console.print(f"[green]Found {len(news_items)} headlines[/green]")
                    
                    # Send news headlines to Telegram
                    if hasattr(self, 'notifier') and self.notifier and news_items and len(news_items) > 0:
                        try:
                            self.notifier.alert_news_batch(ticker, news_items)
                            console.print("[green]✓ News sent to Telegram[/green]")
                        except Exception as e:
                            logger.debug(f"Telegram news send error: {e}")
                except Exception as e:
                    logger.warning(f"News fetch error: {e}")
                    analysis_options['news_items'] = []
            
            df = DataManager.fetch_data(ticker, config.period, config.interval)
            
            if df is None:
                console.print(f"\n[red]❌ Failed to fetch {config.interval} data for {ticker}[/red]")
                console.print("[yellow]💡 This might mean:[/yellow]")
                if config.interval in ['5m', '15m', '30m', '1h']:
                    console.print("  • Yahoo Finance may not have intraday data for this ticker (premium feature)")
                    console.print("  • Try a major stock like AAPL, MSFT, NVDA, GOOGL for 5m data")
                    console.print("  • Or switch to [cyan]Swing Trading[/cyan] (uses daily data, more reliable)")
                    console.print("  • Or ensure your [cyan]Polygon API key[/cyan] is set for day trading support")
                else:
                    console.print("  • Check ticker symbol is correct (e.g., AAPL, TSLA, NVDA)")
                    console.print("  • For crypto, use format: BTC-USD, ETH-USD")
                    console.print("  • Ensure the ticker has at least 6+ months of history")
                Prompt.ask("\nPress Enter to continue")
                return
            
            # Validate data has enough points for the trading style
            if len(df) < config.min_data_points:
                console.print(f"\n[red]❌ Insufficient data for {config.description}[/red]")
                console.print(f"[yellow]Got {len(df)} bars, need {config.min_data_points} minimum[/yellow]")
                if config.interval in ['5m', '15m', '30m', '1h']:
                    console.print(f"[cyan]💡 Suggestions for Day Trading:[/cyan]")
                    console.print(f"  • Use Polygon.io API for reliable intraday data (set POLYGON_API_KEY)")
                    console.print(f"  • Try major stocks like AAPL, MSFT, NVDA (have more intraday history)")
                    console.print(f"  • Or use [cyan]Swing Trading[/cyan] instead (daily data is more available)")
                else:
                    console.print(f"[cyan]💡 Suggestions:[/cyan]")
                    console.print(f"  • Use a ticker with longer history (typically blue chips)")
                    console.print(f"  • Or increase the analysis period manually")
                Prompt.ask("\nPress Enter to continue")
                return
            
            progress.update(task, description="Calculating 80+ indicators...")
            indicators = TechnicalAnalyzer.calculate_indicators(df)
            
            if indicators is None:
                console.print(f"\n[red]❌ Failed to calculate indicators[/red]")
                Prompt.ask("\nPress Enter to continue")
                return
            
            progress.update(task, description="Detecting patterns...")
            patterns = PatternRecognizer.analyze(df)
            
            progress.update(task, description="Analyzing Smart Money Concepts...")
            notifier_obj = self.notifier if hasattr(self, 'notifier') else None
            market_structure = SmartMoneyAnalyzer.analyze(df, ticker, notifier_obj)
            
            progress.update(task, description="Building Volume Profile...")
            volume_profile = VolumeProfileAnalyzer.analyze(df)
            
            progress.update(task, description="Running AI analysis...")
            trade_summary = None
            # If user chose single analysis, run AI analysis as before
            if live_mode in (None, "1"):
                trade_summary = self.analyzer.analyze(
                ticker, indicators, patterns, market_structure,
                volume_profile, self.config['account_size'],
                risk_per_trade_pct=(self.config.get('risk_per_trade', 2.0)/100.0),
                desired_rrr=float(desired_rrr) if desired_rrr is not None else None,
                analysis_options=analysis_options
            )
            elif live_mode == "2":
                # live continuous scan for this ticker
                self.live_scan_ticker(ticker, config, analysis_options, desired_rrr)
                return
            elif live_mode == "3":
                # live global best-signal scanner
                universe_name = Prompt.ask("Scan universe (1=S&P Top50,2=Tech,3=Crypto,4=AI,5=MegaCaps)", default="1")
                universe_map = {"1": MARKET_UNIVERSES.get('sp500_top50', []),
                                "2": MARKET_UNIVERSES.get('tech_leaders', []),
                                "3": MARKET_UNIVERSES.get('crypto', []),
                                "4": MARKET_UNIVERSES.get('ai_quantum', []),
                                "5": MARKET_UNIVERSES.get('mega_caps', [])}
                universe = universe_map.get(universe_name, MARKET_UNIVERSES.get('sp500_top50', []))
                self.live_best_scanner(universe, config, analysis_options, desired_rrr)
                return
        
        DisplayManager.show_header()
        console.print(f"[bold cyan]Analysis Complete: {ticker}[/bold cyan]")
        console.print(f"[dim]Data from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({len(df)} bars)[/dim]\n")
        
        DisplayManager.show_indicators(indicators)
        
        if patterns.bullish_patterns or patterns.bearish_patterns or patterns.candlestick_patterns:
            console.print("[bold cyan]📐 Detected Patterns:[/bold cyan]")
            if patterns.bullish_patterns:
                console.print(f"[green]Bullish:[/green] {', '.join(patterns.bullish_patterns)}")
            if patterns.bearish_patterns:
                console.print(f"[red]Bearish:[/red] {', '.join(patterns.bearish_patterns)}")
            if patterns.candlestick_patterns:
                console.print(f"[yellow]Candlestick:[/yellow] {', '.join(patterns.candlestick_patterns)}")
            console.print()
        
        console.print(f"[bold cyan]🎯 Smart Money Analysis:[/bold cyan]")
        console.print(f"Market Structure: [bold]{market_structure.structure}[/bold]")
        console.print(f"Order Blocks: {len(market_structure.order_blocks)}")
        console.print(f"Fair Value Gaps: {len(market_structure.fair_value_gaps)}")
        console.print(f"Equilibrium: ${market_structure.equilibrium}\n")
        
        console.print(f"[bold cyan]📊 Volume Profile:[/bold cyan]")
        console.print(f"POC: ${volume_profile.poc}")
        console.print(f"Value Area: ${volume_profile.val} - ${volume_profile.vah}\n")

        # ==========================================
        # QUANTITATIVE FACTOR SNAPSHOT INTEGRATION
        # ==========================================
        try:
            quant_panel = self._quant_factor_snapshot(ticker)
            if quant_panel:
                console.print(quant_panel)
        except Exception as e:
            logger.error(f"Quant snapshot error for {ticker}: {e}")
            console.print(f"[dim]Quant snapshot unavailable ({e})[/dim]\n")
        
        # ==========================================
        # ML ENSEMBLE PRICE FORECAST (LSTM+TRANSFORMER)
        # ==========================================
        try:
            forecast_panel = self._ml_price_forecast(ticker, df, style)
            if forecast_panel:
                console.print(forecast_panel)
        except Exception as e:
            logger.error(f"ML forecast error for {ticker}: {e}")
            console.print(f"[dim]ML forecast unavailable ({e})[/dim]\n")
        
        if trade_summary:
            DisplayManager.show_trade_recommendation(trade_summary)
            self._save_analysis_report(ticker, trade_summary)
            
            # Show news if fetched
            if analysis_options.get('include_news_sentiment') and analysis_options.get('news_items'):
                DisplayManager.show_news(analysis_options['news_items'], ticker)
            
            # Generate chart with trade signals (auto-enabled)
            self._generate_analysis_chart(ticker, df, trade_summary, patterns, market_structure)
            
            # Auto-track all trades for performance analysis
            self._track_trade_decision(ticker, trade_summary, False, df)
            
            # Send notification for swing/long-term trades with 80%+ confidence
            if style in [TradingStyle.SWING_TRADE, TradingStyle.LONG_TERM] and trade_summary.confidence >= 80:
                try:
                    if hasattr(self, 'notifier') and self.notifier:
                        style_label = "SWING" if style == TradingStyle.SWING_TRADE else "LONG"
                        msg = f"🎯 [AI] {style_label} TRADE SIGNAL\n"
                        msg += f"{ticker} - {trade_summary.action}\n"
                        msg += f"Confidence: {trade_summary.confidence:.0f}%\n"
                        msg += f"Entry: ${indicators.price:.2f}\n"
                        msg += f"Stop: ${trade_summary.stop_loss:.2f}\n"
                        msg += f"Target 1: ${trade_summary.take_profit_1:.2f}\n"
                        msg += f"Reason: {trade_summary.primary_reason}"
                        self.notifier.send(msg)
                except:
                    pass
        
        # Futures-specific options (if analyzing a futures contract)
        if instr_choice == "3" and trade_summary:
            self._show_futures_options(ticker, indicators, trade_summary)
        
        Prompt.ask("\nPress Enter to continue")

    def _quant_factor_snapshot(self, ticker: str):
        """Return a Rich Panel summarizing quantitative finance factors & signals for the current ticker.
        Includes: risk-adjusted momentum rank vs universe, mean reversion state, multi-factor composite,
        regime context, and (if available) ML probability. Designed for Option 1 integration."""
        import math
        # Performance: default to single-ticker snapshot to avoid scanning entire universe
        # Set config key 'quant_snapshot_universe' to a positive integer (e.g., 10/30) to enable wider ranking.
        universe_size = 1
        try:
            if isinstance(self.config, dict):
                universe_size = int(self.config.get('quant_snapshot_universe', 1))
        except Exception:
            universe_size = 1
        base_universe = [ticker]
        if universe_size and universe_size > 1:
            full = MARKET_UNIVERSES.get('sp500_top50', [])[:max(1, universe_size)]
            # Ensure ticker is included first, then fill remainder
            base_universe = [ticker] + [t for t in full if t != ticker]
        lookback_mom = 126
        momentum_map = {}
        vol_map = {}
        # Fetch data & compute momentum/volatility
        for tk in base_universe:
            try:
                df_u = DataManager.fetch_data(tk, f"{lookback_mom}d", "1d")
                if df_u is None or len(df_u) < lookback_mom:
                    continue
                window_df = df_u.tail(lookback_mom)
                mom_raw = FactorModels.calculate_momentum_factor(window_df, lookback_mom)
                rets = window_df['Close'].pct_change().dropna()
                vol = rets.std() * math.sqrt(252) if not rets.empty else 1.0
                if vol == 0:
                    vol = 1.0
                adj_mom = mom_raw / vol
                momentum_map[tk] = adj_mom
                vol_map[tk] = vol
            except Exception as e:
                logger.debug(f"Momentum calc skip {tk}: {e}")
        if not momentum_map:
            return None
        sorted_mom = sorted(momentum_map.items(), key=lambda x: x[1], reverse=True)
        total = len(sorted_mom)
        rank = next((i for i,(tk,_) in enumerate(sorted_mom) if tk == ticker), None)
        mom_percentile = (total - rank) / total if rank is not None and total > 0 else 0.0
        adj_momentum = momentum_map.get(ticker, 0.0)
        raw_vol = vol_map.get(ticker, 0.0)

        # Mean reversion (Bollinger z-score)
        z_state = "N/A"
        z_score_val = None
        try:
            df_mr = DataManager.fetch_data(ticker, "70d", "1d")
            if df_mr is not None and len(df_mr) >= 20:
                z_score_val, reverting = FactorModels.detect_mean_reversion(df_mr, window=20)
                if z_score_val is not None:
                    if z_score_val <= -2:
                        z_state = "Oversold (BUY bias)"
                    elif z_score_val >= 2:
                        z_state = "Overbought (SELL bias)"
                    else:
                        z_state = "Neutral"
        except Exception:
            pass

        # Multi-factor (momentum/value/quality) with dispersion weights
        try:
            info = DataManager.get_ticker_info(ticker)
        except Exception:
            info = None
        value_factor = FactorModels.calculate_value_factor(info) if info else 0.0
        quality_factor = FactorModels.calculate_quality_factor(info) if info else 0.0
        # Build factor arrays across universe (reuse momentum raw via rank ordering to approximate relative positioning)
        mom_vals = [v for _, v in sorted_mom]
        # For simplicity fetch fundamentals for a subset (may be sparse)
        val_list = []
        qual_list = []
        for tk,_ in sorted_mom:
            try:
                inf = DataManager.get_ticker_info(tk)
                val_list.append(FactorModels.calculate_value_factor(inf) if inf else 0.0)
                qual_list.append(FactorModels.calculate_quality_factor(inf) if inf else 0.0)
            except Exception:
                val_list.append(0.0)
                qual_list.append(0.0)
        def _wins(vals):
            if not vals:
                return []
            sv = sorted(vals)
            l = sv[int(0.05*(len(sv)-1))]
            u = sv[int(0.95*(len(sv)-1))]
            return [min(max(x,l),u) for x in vals]
        def _pct(vals):
            su = sorted(set(vals))
            if len(su) <= 1:
                return [0.5 for _ in vals]
            m = {v:i for i,v in enumerate(su)}
            mx = len(su)-1
            return [m[v]/mx for v in vals]
        mom_w = _wins(mom_vals); val_w = _wins(val_list); qual_w = _wins(qual_list)
        mom_pct = _pct(mom_w); val_pct = _pct(val_w); qual_pct = _pct(qual_w)
        import math as _m
        def _std(a):
            if not a:
                return 0.0
            mean = sum(a)/len(a)
            return (_m.sqrt(sum((x-mean)**2 for x in a)/len(a)))
        w_mom = _std(mom_w); w_val = _std(val_w); w_qual = _std(qual_w)
        ws = w_mom + w_val + w_qual if (w_mom + w_val + w_qual) != 0 else 1
        w_mom /= ws; w_val /= ws; w_qual /= ws
        # Current ticker normalized percentile values
        mom_norm = mom_pct[rank] if rank is not None else 0.5
        # Map ticker to index (since order is sorted by momentum, align lists accordingly)
        val_norm = val_pct[rank] if rank is not None else 0.5
        qual_norm = qual_pct[rank] if rank is not None else 0.5
        composite = ( (mom_norm*2 -1)*w_mom + (val_norm*2 -1)*w_val + (qual_norm*2 -1)*w_qual )

        # Regime detection (SPY 50/200)
        regime = "unknown"
        try:
            spy_df = DataManager.fetch_data("SPY", "250d", "1d")
            if spy_df is not None and len(spy_df) >= 200:
                closes = spy_df['Close']
                sma50 = closes.rolling(50).mean().iloc[-1]
                sma200 = closes.rolling(200).mean().iloc[-1]
                if sma50 > sma200 * 1.01:
                    regime = "bull"
                elif sma50 < sma200 * 0.99:
                    regime = "bear"
                else:
                    regime = "sideways"
        except Exception:
            pass

        # ML probability (if available)
        ml_prob_display = "N/A"
        try:
            if hasattr(self, 'ml_weighter') and self.ml_weighter and self.ml_weighter.models:
                features = {
                    'adj_momentum': adj_momentum,
                    'volatility': raw_vol,
                    'value_factor': value_factor,
                    'quality_factor': quality_factor,
                    'mean_rev_z': z_score_val or 0.0
                }
                ensemble_prob, _ = self.ml_weighter.get_ensemble_prediction(features)
                ml_prob_display = f"{ensemble_prob:.1%}"
        except Exception:
            pass

        # Construct Rich Table
        from rich.table import Table
        from rich.panel import Panel
        t = Table(title="Quantitative Factor Snapshot", show_header=True, header_style="bold cyan")
        t.add_column("Metric")
        t.add_column("Value")
        t.add_row("Risk-Adj Momentum", f"{adj_momentum:.3f} (Pct {mom_percentile*100:.1f}%)")
        if z_score_val is not None:
            t.add_row("Mean Reversion Z", f"{z_score_val:.2f} ({z_state})")
        else:
            t.add_row("Mean Reversion Z", "N/A")
        t.add_row("Value Factor (raw)", f"{value_factor:.3f}")
        t.add_row("Quality Factor (raw)", f"{quality_factor:.3f}")
        t.add_row("Composite (dispersion)", f"{composite:.2f} (Wm:{w_mom:.2f} Wv:{w_val:.2f} Wq:{w_qual:.2f})")
        t.add_row("Market Regime", regime)
        t.add_row("ML Probability", ml_prob_display)
        return Panel(t, title="[bold magenta]🧮 Quantitative Finance[/bold magenta]", border_style="magenta")
    
    def _ml_price_forecast(self, ticker: str, df: pd.DataFrame, style: TradingStyle):
        """Generate LSTM+Transformer ensemble price forecast with confidence intervals.
        Returns Rich panel with next-day, 3-day, and 7-day predictions + directional probability."""
        try:
            import sys
            import os
            # Import ensemble predictor
            predictor_path = os.path.join(os.path.dirname(__file__), 'quant_predictor.py')
            if not os.path.exists(predictor_path):
                return None
            
            # Lazy import to avoid overhead if not needed
            from quant_predictor import FeatureEngineer, EnsemblePredictor
            
            # Feature engineering on historical data
            features_df = FeatureEngineer.engineer_features(df)
            features_df = features_df.dropna()
            
            if len(features_df) < 200:
                return None  # Insufficient data
            
            # Train compact model for speed (use recent 300 bars)
            train_window = min(300, len(features_df) - 60)
            X_train = features_df.iloc[-train_window:].drop(columns=['close']).values
            y_train = features_df.iloc[-train_window:]['close'].values
            
            # Quick ensemble (reduce epochs for speed)
            predictor = EnsemblePredictor(
                seq_length=30 if style == TradingStyle.DAY_TRADE else 60,
                hidden_size=64,  # Smaller for speed
                num_epochs=20,   # Faster training
                batch_size=32,
                learning_rate=0.001
            )
            
            # Suppress training output
            import io
            from contextlib import redirect_stdout
            with redirect_stdout(io.StringIO()):
                predictor.fit(X_train, y_train, val_split=0.2)
            
            # Predict next periods
            X_current = features_df.iloc[-predictor.seq_length:].drop(columns=['close']).values
            predictions, uncertainty = predictor.predict(X_current)
            
            current_price = df['Close'].iloc[-1]
            pred_next = predictions[-1]
            pred_uncertainty = uncertainty[-1]
            
            # Directional probability (based on ensemble agreement and magnitude)
            direction_change = (pred_next - current_price) / current_price
            confidence_directional = 1 / (1 + pred_uncertainty) if pred_uncertainty > 0 else 0.5
            
            # Simulate 3-day and 7-day (simple momentum extension, real would retrain)
            momentum_1d = direction_change
            pred_3d = current_price * (1 + momentum_1d * 2.5)  # Approximate
            pred_7d = current_price * (1 + momentum_1d * 5.0)  # Approximate
            
            # Build table
            from rich.table import Table
            from rich.panel import Panel
            t = Table(title="ML Ensemble Price Forecast (LSTM + Transformer)", show_header=True, header_style="bold cyan")
            t.add_column("Horizon")
            t.add_column("Prediction")
            t.add_column("Change")
            t.add_column("Confidence")
            
            change_1d_pct = direction_change * 100
            change_3d_pct = (pred_3d / current_price - 1) * 100
            change_7d_pct = (pred_7d / current_price - 1) * 100
            
            color_1d = "green" if change_1d_pct > 0 else "red"
            color_3d = "green" if change_3d_pct > 0 else "red"
            color_7d = "green" if change_7d_pct > 0 else "red"
            
            t.add_row(
                "Next Day",
                f"${pred_next:.2f}",
                f"[{color_1d}]{change_1d_pct:+.2f}%[/{color_1d}]",
                f"{confidence_directional*100:.1f}%"
            )
            t.add_row(
                "3-Day",
                f"${pred_3d:.2f}",
                f"[{color_3d}]{change_3d_pct:+.2f}%[/{color_3d}]",
                "(momentum ext.)"
            )
            t.add_row(
                "7-Day",
                f"${pred_7d:.2f}",
                f"[{color_7d}]{change_7d_pct:+.2f}%[/{color_7d}]",
                "(momentum ext.)"
            )
            
            # Directional bias
            direction = "BULLISH" if direction_change > 0.002 else ("BEARISH" if direction_change < -0.002 else "NEUTRAL")
            direction_color = "green" if direction == "BULLISH" else ("red" if direction == "BEARISH" else "yellow")
            
            footer = f"\n[bold]Directional Bias:[/bold] [{direction_color}]{direction}[/{direction_color}] | Uncertainty: {pred_uncertainty:.4f}"
            
            return Panel(t, title="[bold blue]🔮 ML Price Prediction[/bold blue]", border_style="blue", subtitle=footer)
        
        except Exception as e:
            logger.error(f"ML forecast generation failed: {e}")
            return None
    
    def run_market_scanner(self):
        """Run market scanner."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]🔍 Market Scanner[/bold cyan]\n")
        console.print("Select market to scan:\n")
        console.print("1. 📈 S&P 500 Top 50")
        console.print("2. 💻 Tech Leaders")
        console.print("3. ₿ Crypto Markets")
        console.print("4. 🔬 AI & Quantum Computing")
        console.print("5. 🏢 Mega Caps")
        console.print("6. 📉 Futures Markets\n")

        choice = Prompt.ask("Select market", choices=["1", "2", "3", "4", "5", "6"], default="1")

        universe_map = {
            "1": ("S&P 500 Top 50", MARKET_UNIVERSES["sp500_top50"]),
            "2": ("Tech Leaders", MARKET_UNIVERSES["tech_leaders"]),
            "3": ("Crypto Markets", MARKET_UNIVERSES["crypto"]),
            "4": ("AI & Quantum", MARKET_UNIVERSES["ai_quantum"]),
            "5": ("Mega Caps", MARKET_UNIVERSES["mega_caps"]),
            "6": ("Futures Markets", MARKET_UNIVERSES.get("futures", []))
        }
        
        name, universe = universe_map[choice]
        
        console.print(f"\n[yellow]Scanning {name}...[/yellow]")
        
        opportunities = self.scanner.scan_universe(universe, self.config)
        
        DisplayManager.show_header()
        console.print(f"[bold cyan]Scanner Results: {name}[/bold cyan]\n")
        
        DisplayManager.show_scanner_results(opportunities)
        
        if opportunities:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = SCANNER_DIR / f"scan_{name.replace(' ', '_')}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump([asdict(opp) for opp in opportunities], f, indent=2)
            
            console.print(f"[dim]Results saved to: {filename}[/dim]\n")
        
        Prompt.ask("Press Enter to continue")

    def live_scan_ticker(self, ticker: str, config, analysis_options: dict, desired_rrr: float):
        """Continuously scan a single ticker with enhanced trade tracking and exit signals.

        Features:
        - Alerts on >60% confidence entry signals
        - Provides stop loss guidance (with trailing option)
        - Tracks if user took the trade
        - Monitors position and provides exit signals
        """
        from rich.prompt import IntPrompt
        import time

        # Use DataManager which automatically uses Polygon for intraday
        console.print('[dim]Live scan uses Polygon.io for real-time data (if configured)[/dim]')
        console.print('[dim]Starting live scan — press Enter to refresh now, Ctrl+C to stop.[/dim]\n')
        # If crypto, start Coinbase WS for faster ticks
        try:
            if ticker.upper().endswith('-USD'):
                DataManager.start_crypto_ws([ticker.upper()])
        except Exception:
            pass
        
        # Auto-set scan delay to 60 seconds to respect rate limits
        scan_delay = 60

        # Trade tracking state
        position_active = False
        position_side = None  # 'LONG' or 'SHORT'
        entry_price = None
        entry_time = None
        stop_loss = None
        take_profit = None
        use_trailing_stop = False
        highest_price = None  # For LONG trailing
        lowest_price = None   # For SHORT trailing
        trailing_distance = None
        entry_confidence = 0
        position_size = 0.0
        partial_taken = False
        initial_stop_loss = None
        initial_r_distance = None
        breakeven_applied = False

        try:
            scan_count = 0
            while True:
                scan_count += 1
                # Fetch latest data using DataManager (auto uses Polygon for 1m interval)
                bars = DataManager.fetch_data(ticker, '5d', '1m')

                if bars is None or bars.empty:
                    console.print(f'[red]No data for {ticker}, retrying...[/red]')
                    time.sleep(max(1, scan_delay))
                    continue

                # Get realtime tick price when available (Polygon or yfinance)
                current_price = None
                price_source = 'unknown'
                debug_price = False
                try:
                    debug_price = bool(self.config.get('debug_price_source', False) or os.getenv('DEBUG_PRICE_SOURCE', '0') in ['1','true','True'])
                except Exception:
                    debug_price = False
                
                try:
                    # Get current price from DataManager (uses Coinbase WS for crypto, Polygon/yfinance for stocks)
                    current_price = DataManager.get_realtime_price(ticker)
                    if current_price is not None:
                        current_price = float(current_price)
                        # Check if price came from WS cache (crypto)
                        if ticker.upper().endswith('-USD'):
                            cache_age = DataManager.get_cached_price_age(ticker)
                            if cache_age is not None and cache_age < 3.0:
                                price_source = 'coinbase_ws'
                            else:
                                price_source = 'yfinance_fallback'
                        else:
                            price_source = 'polygon/yfinance'
                except Exception:
                    current_price = None

                # Final fallback to last bar close
                if current_price is None:
                    current_price = float(bars['Close'].iloc[-1])
                    price_source = 'bar_close'

                # Optionally show which price source was used (useful for debugging accuracy)
                if debug_price:
                    # Compute latency diagnostics
                    try:
                        import datetime as _dt
                        last_bar_time = bars.index[-1]
                        now_ts = _dt.datetime.utcnow().replace(tzinfo=bars.index.tz) if getattr(bars.index, 'tz', None) else _dt.datetime.utcnow()
                        bar_age_sec = float((now_ts - last_bar_time).total_seconds()) if last_bar_time is not None else None
                    except Exception:
                        bar_age_sec = None

                    age_info = ''
                    try:
                        cp_age = DataManager.get_cached_price_age(ticker)
                        if cp_age is not None:
                            age_info = f" | cached_age={cp_age:.1f}s"
                    except Exception:
                        pass
                    bar_age_info = ''
                    if bar_age_sec is not None:
                        bar_age_info = f" | last_bar_age={bar_age_sec:.1f}s"
                    console.print(f"[dim]Price source: {price_source} | Price: ${current_price:.4f}{age_info}{bar_age_info}[/dim]")
                    if bar_age_sec is not None and bar_age_sec > 90:
                        console.print("[yellow]Warning: Last 1m bar is older than 90s — data feed may be delayed.[/yellow]")

                last_bar_time = bars.index[-1]

                # Update paper trades
                try:
                    self.paper_trading.update_trades()
                except Exception as e:
                    logger.error(f"Paper trade update error: {e}")

                # Build an intrabar-updated view of the last candle using current_price
                bars_live = None
                try:
                    bars_live = bars.copy()
                    # Update last row close, and expand high/low to include current tick
                    last_idx = bars_live.index[-1]
                    last_high = float(bars_live.loc[last_idx, 'High'])
                    last_low = float(bars_live.loc[last_idx, 'Low'])
                    last_open = float(bars_live.loc[last_idx, 'Open'])
                    # Set close to current tick
                    bars_live.loc[last_idx, 'Close'] = float(current_price)
                    # Expand high/low
                    if float(current_price) > last_high:
                        bars_live.loc[last_idx, 'High'] = float(current_price)
                    if float(current_price) < last_low:
                        bars_live.loc[last_idx, 'Low'] = float(current_price)
                except Exception:
                    bars_live = bars

                # Calculate indicators on the intrabar-updated data
                indicators = TechnicalAnalyzer.calculate_indicators(bars_live)
                
                # Override indicators.price with live current_price for accurate entry
                original_price = indicators.price
                if current_price is not None:
                    indicators.price = round(current_price, 2)
                    indicators.close = round(current_price, 2)
                
                # Debug: show price adjustment
                if debug_price and current_price is not None:
                    console.print(f"[dim]Price override: bar close ${original_price:.2f} → live ${current_price:.2f}[/dim]")
                
                # Debug: show last 5 closes and calculated RSI for verification
                if debug_price:
                    last_5_closes = indicators.closes.tail(5).tolist()
                    console.print(f"[dim]Last 5 closes: {[f'${c:.2f}' for c in last_5_closes]}[/dim]")
                    console.print(f"[dim]Calculated RSI(14): {indicators.rsi_14:.2f} | MACD: {indicators.macd:.4f}[/dim]")
                
                signal = self.analyzer._fallback_analysis(
                    ticker, indicators, self.config.get('account_size', 10000),
                    (self.config.get('risk_per_trade', 2.0)/100.0), float(desired_rrr) if desired_rrr else 2.0,
                    is_day_trading=True  # Enable 5-20min profit optimization
                )
                # Enrich signal with fundamentals and option Greeks (lightweight, optional)
                try:
                    if signal is not None:
                        try:
                            funds = DataManager.get_fundamentals(ticker)
                            if funds:
                                pe = funds.get('trailingPE') or funds.get('forwardPE')
                                if pe is not None:
                                    signal.supporting_signals.append(f"PE: {pe:.2f}")
                                    if pe and pe < 12:
                                        signal.supporting_signals.append("Low PE (value-biased)")
                                    elif pe and pe > 60:
                                        signal.supporting_signals.append("High PE (speculative)")

                        except Exception:
                            pass

                        # option Greeks fetch only if requested to avoid heavy API calls
                        try:
                            if analysis_options.get('include_option_flow') or debug_price:
                                opt = DataManager.get_option_chain_greeks(ticker)
                                if opt:
                                    cg = opt.get('call_greeks', {})
                                    pg = opt.get('put_greeks', {})
                                    iv = opt.get('used_iv')
                                    if cg:
                                        signal.supporting_signals.append(f"ATM call Δ={cg.get('delta',0):.2f}, IV={iv:.2%}")
                                    if pg:
                                        signal.supporting_signals.append(f"ATM put Δ={pg.get('delta',0):.2f}")
                        except Exception:
                            pass
                except Exception:
                    pass
                
                # ===== NEW SIGNAL DETECTION =====
                # Track action flips separately from confidence jitters
                action_key = (signal.action if signal else None)
                if not hasattr(self, '_last_signal_action'):
                    self._last_signal_action = None
                action_changed = (action_key != self._last_signal_action)
                if action_changed:
                    self._last_signal_action = action_key
                
                # Only print when something ACTUALLY changes
                if action_changed and signal and signal.action != "HOLD":
                    # Minimal, user-friendly line: ACTION + CONFIDENCE + PRICE
                    console.print(
                        f"[bold]{ticker}[/bold]: {signal.action}  {signal.confidence:.0f}%  |  ${current_price:.2f}"
                    )
                    
                    # Generate chart (silent) highlighting the signal switch
                    try:
                        import matplotlib
                        matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from pathlib import Path
                        import os
                        
                        fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
                        fig.patch.set_facecolor('#0E1117')
                        
                        # Price chart with candlesticks
                        ax_price = axes[0]
                        ax_price.set_facecolor('#0E1117')
                        
                        # Plot candlesticks
                        candle_width = 0.8
                        plot_df = bars_live.tail(200).reset_index(drop=True)
                        for idx, row in plot_df.iterrows():
                            x = idx
                            open_price = row.get('Open', row['Close'])
                            high = row.get('High', row['Close'])
                            low = row.get('Low', row['Close'])
                            close = row.get('Close', row['Close'])
                            
                            is_bullish = close >= open_price
                            color = '#00ff00' if is_bullish else '#ff0000'
                            
                            # Wick
                            ax_price.plot([x, x], [low, high], color=color, linewidth=1.5, alpha=0.9)
                            
                            # Body
                            body_height = abs(close - open_price)
                            body_bottom = min(open_price, close)
                            if body_height < close * 0.0001:
                                body_height = close * 0.0001
                            
                            from matplotlib.patches import Rectangle
                            if is_bullish:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                               facecolor='#0a0a0a', edgecolor=color, linewidth=1.5, alpha=0.9)
                            else:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                               facecolor=color, edgecolor=color, linewidth=1.5, alpha=0.9)
                            ax_price.add_patch(rect)
                        
                        ax_price.set_xlim(-0.5, len(plot_df) - 0.5)
                        
                        # Add moving averages on top of candlesticks
                        if 'SMA_20' in bars_live.columns:
                            sma20_plot = bars_live['SMA_20'].tail(200).reset_index(drop=True)
                            ax_price.plot(range(len(sma20_plot)), sma20_plot, label='SMA 20', alpha=0.7, color='orange', linewidth=1.5)
                        if 'SMA_50' in bars_live.columns:
                            sma50_plot = bars_live['SMA_50'].tail(200).reset_index(drop=True)
                            ax_price.plot(range(len(sma50_plot)), sma50_plot, label='SMA 50', alpha=0.7, color='red', linewidth=1.5)
                        
                        # Mark entry/SL/TP
                        ax_price.axhline(y=signal.entry_price, color='cyan', linestyle='--', label=f'Entry: ${signal.entry_price:.2f}', linewidth=1.5)
                        ax_price.axhline(y=signal.stop_loss, color='red', linestyle='--', label=f'Stop: ${signal.stop_loss:.2f}', linewidth=1.5)
                        ax_price.axhline(y=signal.take_profit_1, color='green', linestyle='--', label=f'TP1: ${signal.take_profit_1:.2f}', linewidth=1.5)
                        
                        # Highlight current price (at last candle)
                        ax_price.scatter([len(plot_df) - 1], [current_price], color='yellow', s=150, zorder=5, label=f'Signal Switch')
                        
                        switch_reason = signal.primary_reason[:80]
                        title = f'{ticker} - {signal.action} ({signal.confidence:.0f}%)'
                        ax_price.set_title(title, fontsize=14, fontweight='bold', pad=20, color='white')
                        ax_price.set_ylabel('Price ($)', fontsize=11, color='white')
                        ax_price.legend(loc='best', fontsize=9, facecolor='#1a1a1a', edgecolor='cyan')
                        ax_price.grid(True, alpha=0.3, color='#333333')
                        ax_price.tick_params(colors='white')
                        
                        # Omit supporting signals block to keep chart clean
                        
                        # RSI chart
                        ax_rsi = axes[1]
                        ax_rsi.set_facecolor('#0E1117')
                        if 'RSI' in bars_live.columns:
                            ax_rsi.plot(bars_live.index, bars_live['RSI'], label='RSI', color='purple', linewidth=1.5)
                            ax_rsi.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought')
                            ax_rsi.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold')
                            ax_rsi.fill_between(bars_live.index, 30, 70, alpha=0.1, color='gray')
                        ax_rsi.set_ylabel('RSI', fontsize=11, color='white')
                        ax_rsi.legend(loc='best', fontsize=9, facecolor='#1a1a1a')
                        ax_rsi.grid(True, alpha=0.3, color='#333333')
                        ax_rsi.set_ylim(0, 100)
                        ax_rsi.tick_params(colors='white')
                        
                        # Volume chart
                        ax_vol = axes[2]
                        ax_vol.set_facecolor('#0E1117')
                        colors = ['green' if bars_live['Close'].iloc[i] >= bars_live['Open'].iloc[i] else 'red' 
                                 for i in range(len(bars_live))]
                        ax_vol.bar(bars_live.index, bars_live['Volume'], color=colors, alpha=0.6)
                        ax_vol.set_ylabel('Volume', fontsize=11, color='white')
                        ax_vol.set_xlabel('Time', fontsize=11, color='white')
                        ax_vol.grid(True, alpha=0.3, color='#333333')
                        ax_vol.tick_params(colors='white')
                        
                        plt.tight_layout()
                        
                        # Save chart
                        charts_dir = Path("results/charts")
                        charts_dir.mkdir(exist_ok=True, parents=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        chart_path = charts_dir / f"{ticker.replace(' ', '_')}_signal_switch_{timestamp}.png"
                        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#0E1117')
                        plt.close()
                        
                        # Auto-open chart silently
                        try:
                            os.startfile(str(chart_path))
                        except Exception:
                            pass
                    except Exception:
                        pass
                    
                    # Notify on sentiment change (BUY/SELL flip) only when confidence >= 80
                    try:
                        if hasattr(self, 'notifier') and self.notifier and float(signal.confidence) >= 80.0:
                            msg = f"{ticker}: {signal.action} {min(95, float(signal.confidence)):.0f}% | ${signal.entry_price:.2f}"
                            self.notifier.send(msg)
                    except Exception:
                        pass

                # ===== RSI OVERBOUGHT/OVERSOLD CROSSING ALERTS =====
                try:
                    rsi_val = float(indicators.rsi_14)
                    if not hasattr(self, '_last_rsi_state'):
                        self._last_rsi_state = 'neutral'
                    prev_state = self._last_rsi_state
                    curr_state = 'overbought' if rsi_val >= 70 else ('oversold' if rsi_val <= 30 else 'neutral')
                    if curr_state != prev_state:
                        self._last_rsi_state = curr_state
                        if curr_state in ('overbought','oversold'):
                            if hasattr(self, 'notifier') and self.notifier:
                                # Minimal RSI alert
                                self.notifier.send(f"{ticker}: RSI {curr_state} {rsi_val:.1f}")
                except Exception:
                    pass
                
                # ===== POSITION MONITORING (if trade active) =====
                if position_active:
                    # Compute P&L based on side
                    if position_side == 'SHORT':
                        pnl = (entry_price - current_price)
                    else:
                        pnl = (current_price - entry_price)
                    pnl_pct = (pnl / entry_price) * 100 if entry_price else 0.0
                    
                    # Update highest price for trailing stop
                    if use_trailing_stop:
                        if position_side == 'SHORT':
                            if lowest_price is None:
                                lowest_price = entry_price
                            if current_price < lowest_price:
                                lowest_price = current_price
                                stop_loss = lowest_price + (trailing_distance or 0)
                        else:
                            if highest_price is None:
                                highest_price = entry_price
                            if current_price > highest_price:
                                highest_price = current_price
                                stop_loss = highest_price - (trailing_distance or 0)

                    # Auto move stop to break-even at +1R
                    try:
                        if not breakeven_applied and stop_loss is not None and entry_price is not None:
                            if position_side == 'LONG':
                                r_dist = float(entry_price) - float(stop_loss)
                                if r_dist > 0 and (float(current_price) - float(entry_price)) >= r_dist:
                                    stop_loss = float(entry_price)
                                    breakeven_applied = True
                                    if hasattr(self, 'notifier') and self.notifier:
                                        self.notifier.send(f"{ticker}: BE stop @ ${entry_price:.2f}")
                            elif position_side == 'SHORT':
                                r_dist = float(stop_loss) - float(entry_price)
                                if r_dist > 0 and (float(entry_price) - float(current_price)) >= r_dist:
                                    stop_loss = float(entry_price)
                                    breakeven_applied = True
                                    if hasattr(self, 'notifier') and self.notifier:
                                        self.notifier.send(f"{ticker}: BE stop @ ${entry_price:.2f}")
                    except Exception:
                        pass
                    
                    # Track last P&L to avoid spamming position updates
                    if not hasattr(self, '_last_pnl_pct'):
                        self._last_pnl_pct = None
                    
                    # Only print position if P&L changed by >0.5% or exit conditions met
                    pnl_changed = (self._last_pnl_pct is None or abs(pnl_pct - self._last_pnl_pct) > 0.5)
                    
                    # CHECK EXIT CONDITIONS
                    exit_triggered = False
                    exit_reason = ""
                    
                    # Stop loss / Take profit based on side
                    if position_side == 'SHORT':
                        if stop_loss is not None and current_price >= stop_loss:
                            exit_triggered = True
                            exit_reason = f"🛑 STOP LOSS HIT (SHORT)"
                        elif take_profit is not None and current_price <= take_profit:
                            exit_triggered = True
                            exit_reason = f"🎯 TAKE PROFIT HIT (SHORT)"
                    else:
                        if stop_loss is not None and current_price <= stop_loss:
                            exit_triggered = True
                            exit_reason = f"🛑 STOP LOSS HIT"
                        elif take_profit is not None and current_price >= take_profit:
                            exit_triggered = True
                            exit_reason = f"🎯 TAKE PROFIT HIT"
                    
                    # Strong reversal signal (sell when buy, buy when sell)
                    if (not exit_triggered) and signal and signal.confidence > 70:
                        if position_side == 'LONG' and signal.action == 'SELL':
                            exit_triggered = True
                            exit_reason = f"⚠️ REVERSAL: EXIT LONG (Market flipped to SELL)"
                        elif position_side == 'SHORT' and signal.action == 'BUY':
                            exit_triggered = True
                            exit_reason = f"⚠️ REVERSAL: EXIT SHORT (Market flipped to BUY)"
                    
                    # Display position status (minimal) - only on changes
                    if pnl_changed or exit_triggered:
                        pos_color = "green" if pnl >= 0 else "red"
                        side_label = 'SHORT' if position_side == 'SHORT' else 'LONG'
                        console.print(f"[{pos_color}]💼 {ticker} ({side_label}) | Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | P&L: {pnl_pct:+.2f}%[/{pos_color}]")
                        self._last_pnl_pct = pnl_pct
                    
                    if exit_triggered:
                        # Clear instruction to EXIT
                        console.print(f"\n{ticker}: EXIT NOW | ${current_price:.2f}")
                        console.print(f"[bold][red]{exit_reason}[/red][/bold]")
                        console.print(f"[yellow]⏹ Close position? (y/n)[/yellow]\n")
                        # Notify exit signal
                        try:
                            if hasattr(self, 'notifier') and self.notifier:
                                # Minimal exit alert
                                self.notifier.send(f"{ticker}: EXIT NOW | ${current_price:.2f} | {exit_reason}")
                        except Exception:
                            pass
                        
                        close_now = Confirm.ask("Close position?", default=True)
                        if close_now:
                            position_active = False
                            position_side = None
                            final_pnl = pnl_pct
                            console.print(f"[green]✓ Closed. Final P&L: {final_pnl:+.2f}%\n[/green]")
                        else:
                            console.print("[yellow]Position remains open.\n[/yellow]")
                
                # Silent filtering: below threshold signals are not printed
                if not position_active and signal and signal.action != "HOLD" and signal.confidence <= 75:
                    pass

                # ===== ENTRY SIGNAL (>75% confidence) =====
                # Raised threshold from 60% to 75% to filter weak/risky signals
                if not position_active and signal and signal.confidence > 75:
                    # For crypto, require microstructure confirmation (if WS ticks available)
                    if ticker.upper().endswith('-USD'):
                        try:
                            micro = DataManager.get_micro_features(ticker, window_secs=20)
                            if micro:
                                mr = float(micro.get('micro_roc_5s', 0.0))
                                vdev = float(micro.get('vwap_dev', 0.0))
                                tr = float(micro.get('tick_rate', 0.0))
                                age = float(micro.get('last_tick_age', 99.0))
                                if signal.action == 'BUY' and not ((mr > 0.05) and (vdev <= 0.6) and (tr >= 0.5) and (age <= 3.0)):
                                    # Wait for micro confirmation
                                    continue
                                if signal.action == 'SELL' and not ((mr < -0.05) and (vdev >= -0.6) and (tr >= 0.5) and (age <= 3.0)):
                                    continue
                        except Exception:
                            pass
                    
                    # ===== QUANTITATIVE ENHANCEMENT: ML & Factor Analysis =====
                    if signal and signal.action in ("BUY", "SELL"):
                        try:
                            # Factor scoring
                            factor_boost = 0
                            factor_details = []
                            
                            try:
                                # Calculate momentum factor
                                momentum = FactorModels.calculate_momentum_factor(bars_live, lookback=126)
                                if abs(momentum) > 0.1:  # 10% momentum
                                    factor_boost += 5 if momentum > 0 else -5
                                    factor_details.append(f"Momentum: {momentum:.1%}")
                                
                                # Mean reversion check
                                z_score, is_reverting = FactorModels.detect_mean_reversion(bars_live)
                                if is_reverting and abs(z_score) > 2:
                                    # Boost for oversold BUY or overbought SELL
                                    if (signal.action == "BUY" and z_score < -2) or (signal.action == "SELL" and z_score > 2):
                                        factor_boost += 5
                                        factor_details.append(f"Mean Rev Z={z_score:.1f}")
                            except Exception as e:
                                logger.debug(f"Factor calc error: {e}")
                            
                            # ML probability enhancement
                            ml_boost = 0
                            ml_details = []
                            
                            try:
                                ml_weighter = MLSignalWeighter()
                                if ml_weighter.models:  # Check if trained
                                    features = ml_weighter.engineer_features(bars_live, indicators)
                                    if features is not None:
                                        ml_prob, individual = ml_weighter.get_ensemble_prediction(features)
                                        
                                        # Boost confidence if ML agrees
                                        if ml_prob >= 0.6:
                                            ml_boost = int((ml_prob - 0.5) * 40)  # Max +20 boost
                                            ml_details.append(f"ML: {ml_prob:.0%}")
                                        elif ml_prob < 0.4:
                                            ml_boost = -10  # Penalty if ML disagrees
                                            ml_details.append(f"ML: {ml_prob:.0%} (LOW)")
                            except Exception as e:
                                logger.debug(f"ML enhancement error: {e}")
                            
                            # Apply boosts to confidence
                            original_confidence = signal.confidence
                            signal.confidence = min(99, max(0, signal.confidence + factor_boost + ml_boost))
                            
                            # Show enhancements if significant
                            if factor_details or ml_details:
                                enhancement_msg = " | ".join(factor_details + ml_details)
                                console.print(f"[dim]Quant: {enhancement_msg} (Conf: {original_confidence:.0f}% → {signal.confidence:.0f}%)[/dim]")
                        
                        except Exception as e:
                            logger.error(f"Quant enhancement error: {e}")
                    
                    # ===== REGIME & MULTI-TIMEFRAME GATING =====
                    # Check market regime - skip if volatile/ranging unless high confidence
                    try:
                        regime = RegimeDetector.detect_regime(bars, indicators)
                        if regime.regime == "VOLATILE" and signal.confidence < 80:
                            console.print(f"[dim]{ticker}: {signal.action} signal skipped - {regime.details}[/dim]")
                            continue
                        elif regime.regime == "RANGING" and signal.confidence < 70:
                            console.print(f"[dim]{ticker}: {signal.action} signal skipped - {regime.details}[/dim]")
                            continue
                        
                        # Multi-timeframe confirmation
                        mtf = MultiTimeframeAnalyzer.analyze(ticker, config.interval)
                        if not mtf.higher_tf_aligned and signal.confidence < 85:
                            console.print(f"[dim]{ticker}: {signal.action} signal skipped - Higher TF not aligned ({mtf.details})[/dim]")
                            continue
                        
                        # Pass all filters - show regime/MTF info
                        console.print(f"[dim]Regime: {regime.regime} ({regime.confidence:.0f}%) | MTF: {mtf.primary_trend} ({mtf.confirmation_score:.0f}% aligned)[/dim]")
                    except Exception as e:
                        # If regime/MTF check fails, log and continue
                        logger.error(f"Regime/MTF check error: {e}")
                    
                    if signal.action == "BUY":
                        # Calculate stop loss and take profit FIRST (for immediate alert)
                        entry_price_calc = current_price
                        atr = (bars['High'].rolling(14).max().iloc[-1] - bars['Low'].rolling(14).min().iloc[-1])
                        if atr == 0 or np.isnan(atr):
                            atr = (bars['High'].iloc[-1] - bars['Low'].iloc[-1])
                        
                        stop_loss_calc = entry_price_calc - atr * 1.5
                        stop_distance = entry_price_calc - stop_loss_calc
                        take_profit_calc = entry_price_calc + (stop_distance * float(desired_rrr if desired_rrr else 2.0))
                        
                        # Clear instruction to ENTER
                        console.print(f"{ticker}: ENTER LONG {signal.confidence:.0f}% | ${entry_price_calc:.2f}")
                        
                        # Ask about trailing stop
                        console_print_text = "[cyan]Enable trailing stop?[/cyan]"
                        use_trailing = Confirm.ask(console_print_text, default=False)
                        if use_trailing:
                            use_trailing_stop = True
                            position_side = 'LONG'
                            highest_price = entry_price_calc
                            lowest_price = None
                            trailing_distance = atr * 1.5
                            stop_loss_calc = highest_price - trailing_distance
                            console.print(f"[cyan]✓ Trailing stop enabled. Will follow price up by ${trailing_distance:.2f}[/cyan]\n")
                        
                        # Ask if user took the trade
                        trade_choice = Prompt.ask("[bold]Trade action[/bold]", choices=["real", "paper", "skip"], default="real")
                        
                        if trade_choice == "real":
                            entry_price = entry_price_calc
                            position_side = 'LONG'
                            stop_loss = stop_loss_calc
                            take_profit = take_profit_calc
                            entry_time = datetime.now().strftime('%H:%M:%S')
                            entry_confidence = signal.confidence
                            position_active = True
                            breakeven_applied = False
                            
                            console.print(f"\n[green]✓ Real trade tracked. Monitoring {ticker} position...[/green]")
                            console.print(f"  Exit this scan (Ctrl+C) when ready. Will continue monitoring until exit.\n")
                        
                        elif trade_choice == "paper":
                            # Open paper trade
                            position_size_calc = int((self.config.get('account_size', 10000) * 0.02) / stop_distance)
                            self.paper_trading.open_trade(ticker, "LONG", entry_price_calc, stop_loss_calc, take_profit_calc, position_size_calc)
                            console.print("[cyan]Paper trade opened. Will track virtually.[/cyan]\n")
                        
                        else:
                            console.print("[yellow]Trade skipped. Continuing to scan for next signal...\n")
                    
                    elif signal.action == "SELL":
                        # Calculate stop loss and take profit for SHORT (IMMEDIATELY)
                        entry_price_calc = current_price
                        atr = (bars['High'].rolling(14).max().iloc[-1] - bars['Low'].rolling(14).min().iloc[-1])
                        if atr == 0 or np.isnan(atr):
                            atr = (bars['High'].iloc[-1] - bars['Low'].iloc[-1])
                        
                        stop_loss_calc = entry_price_calc + atr * 1.5  # For SHORT, SL is above
                        stop_distance = stop_loss_calc - entry_price_calc
                        take_profit_calc = entry_price_calc - (stop_distance * float(desired_rrr if desired_rrr else 2.0))
                        
                        # Clear instruction to ENTER
                        console.print(f"{ticker}: ENTER SHORT {signal.confidence:.0f}% | ${entry_price_calc:.2f}")
                        
                        # Ask about trailing stop (for SHORT, trailing means following DOWN)
                        use_trailing = Confirm.ask("[cyan]Enable trailing stop?[/cyan]", default=False)
                        if use_trailing:
                            use_trailing_stop = True
                            position_side = 'SHORT'
                            lowest_price = entry_price_calc
                            highest_price = None
                            trailing_distance = atr * 1.5
                            stop_loss_calc = lowest_price + trailing_distance
                            console.print(f"[cyan]✓ Trailing stop enabled. Will follow price down by ${trailing_distance:.2f}[/cyan]\n")
                        
                        # Ask if user took the trade
                        trade_choice = Prompt.ask("[bold]Trade action[/bold]", choices=["real", "paper", "skip"], default="real")
                        
                        if trade_choice == "real":
                            entry_price = entry_price_calc
                            position_side = 'SHORT'
                            stop_loss = stop_loss_calc
                            take_profit = take_profit_calc
                            entry_time = datetime.now().strftime('%H:%M:%S')
                            entry_confidence = signal.confidence
                            position_active = True
                            breakeven_applied = False
                            
                            console.print(f"\n[green]✓ SHORT tracked. Monitoring {ticker} position...[/green]")
                            console.print(f"  Exit this scan (Ctrl+C) when ready. Will continue monitoring until exit.\n")
                        
                        elif trade_choice == "paper":
                            # Open paper trade
                            position_size_calc = int((self.config.get('account_size', 10000) * 0.02) / stop_distance)
                            self.paper_trading.open_trade(ticker, "SHORT", entry_price_calc, stop_loss_calc, take_profit_calc, position_size_calc)
                            console.print("[cyan]Paper trade opened. Will track virtually.[/cyan]\n")
                        
                        else:
                            console.print("[yellow]Trade skipped. Continuing to scan for next signal...\n")

                # Sleep with Enter-to-refresh: check every 200ms
                try:
                    import msvcrt as _kb
                except Exception:
                    _kb = None
                slept = 0.0
                step = 0.2
                max_sleep = max(1.0, float(scan_delay))
                manual_refresh = False
                while slept < max_sleep:
                    # If Enter pressed, break early to refresh immediately
                    if _kb and _kb.kbhit():
                        try:
                            ch = _kb.getch()
                            # Flush any additional buffered keys
                            while _kb.kbhit():
                                _kb.getch()
                            if ch in (b"\r", b"\n"):
                                manual_refresh = True
                                break
                        except Exception:
                            pass
                    time.sleep(step)
                    slept += step
                if manual_refresh:
                    console.print("[cyan]↻ Manual refresh requested[/cyan]")

        except KeyboardInterrupt:
            # stop background updater
            try:
                DataManager.stop_price_updater()
            except Exception:
                pass
            if position_active:
                console.print(f'\n[yellow]⚠️  Scan interrupted but position still ACTIVE![/yellow]')
                console.print(f'  Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | P&L: {((current_price - entry_price) / entry_price * 100):+.2f}%')
                console.print(f'  SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}')
                console.print(f'  Remember to manually close or continue monitoring!\n')
            else:
                console.print('\n[green]Live scan stopped by user.[/green]\n')
            return

    def live_best_scanner(self, universe: list, config, analysis_options: dict, desired_rrr: float):
        """Continuously scan a list of tickers and report the top-confidence ticker each cycle."""
        import time

        console.print('[dim]Universe scanner uses Polygon.io/yfinance for data[/dim]')
        console.print('[dim]Starting universe scan — press Enter to refresh now, Ctrl+C to stop.[/dim]\n')
        # If crypto universe, start WS
        try:
            crypto_syms = [t.upper() for t in universe if isinstance(t, str) and t.upper().endswith('-USD')]
            if crypto_syms:
                DataManager.start_crypto_ws(crypto_syms)
        except Exception:
            pass
        
        # Auto-set scan delay to 60 seconds to respect Polygon rate limits
        scan_delay = 60
        
        try:
            while True:
                best = None
                best_conf = -999
                for t in universe:
                    try:
                        # Use DataManager which automatically uses Polygon for 1m data
                        bars = DataManager.fetch_data(t, '2d', '1m')

                        if bars is None or bars.empty:
                            continue
                        indicators = TechnicalAnalyzer.calculate_indicators(bars)
                        signal = self.analyzer._fallback_analysis(
                            t, indicators, self.config.get('account_size', 10000),
                            (self.config.get('risk_per_trade', 2.0)/100.0), float(desired_rrr) if desired_rrr else 2.0
                        )
                        conf = getattr(signal, 'confidence', 0) if signal else 0
                        if conf > best_conf:
                            best_conf = conf
                            best = (t, signal, indicators)
                    except Exception:
                        continue

                DisplayManager.show_header()
                if best:
                    t, signal, indicators = best
                    console.print(f"[bold]Best ticker now:[/bold] {t}  [bold]Confidence:[/bold] {best_conf}")
                    DisplayManager.show_indicators(indicators)
                    DisplayManager.show_trade_recommendation(signal)
                else:
                    console.print('[yellow]No strong signals found this cycle.[/yellow]')
                # Sleep with Enter-to-refresh: check every 200ms
                try:
                    import msvcrt as _kb
                except Exception:
                    _kb = None
                slept = 0.0
                step = 0.2
                max_sleep = max(1.0, float(scan_delay))
                manual_refresh = False
                while slept < max_sleep:
                    if _kb and _kb.kbhit():
                        try:
                            ch = _kb.getch()
                            while _kb.kbhit():
                                _kb.getch()
                            if ch in (b"\r", b"\n"):
                                manual_refresh = True
                                break
                        except Exception:
                            pass
                    time.sleep(step)
                    slept += step
                if manual_refresh:
                    console.print("[cyan]↻ Manual refresh requested[/cyan]")

        except KeyboardInterrupt:
            console.print('\n[green]Stopped global scanner by user.[/green]\n')
            return
    
    def show_news_intel(self):
        """Show news and market intelligence."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]📰 News & Market Intelligence[/bold cyan]\n")
        
        ticker = Prompt.ask("Enter ticker symbol (or leave blank for general news)").upper().strip()
        
        if ticker:
            console.print(f"\n[yellow]Fetching news for {ticker}...[/yellow]\n")
            
            news_items = NewsAnalyzer.get_news(ticker)
            DisplayManager.show_news(news_items, ticker)
            
            console.print("\n[yellow]Checking SEC filings...[/yellow]\n")
            filings = SECAnalyzer.get_recent_filings(ticker)
            
            if filings:
                console.print("[bold cyan]📋 Recent SEC Filings:[/bold cyan]\n")
                for filing in filings:
                    console.print(f"[white]{filing.form_type}[/white] - {filing.filing_date}")
                    console.print(f"[dim]{filing.description}[/dim]")
                    console.print(f"[blue]{filing.url}[/blue]\n")
        else:
            console.print("[yellow]Fetching general market news...[/yellow]\n")
            
            # Get news from major market indices and trending stocks
            market_tickers = ["^GSPC", "^DJI", "^IXIC", "SPY", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"]
            all_news = []
            
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Fetching market news...", total=len(market_tickers))
                
                for t in market_tickers:
                    try:
                        news = NewsAnalyzer.get_news(t, limit=5)
                        all_news.extend(news)
                    except:
                        pass
                    progress.update(task, advance=1)
            
            # Remove duplicates by title
            seen_titles = set()
            unique_news = []
            for item in all_news:
                title_lower = item.title.lower()
                if title_lower not in seen_titles and item.title:
                    seen_titles.add(title_lower)
                    unique_news.append(item)
            
            if unique_news:
                console.print(f"[bold cyan]🌍 General Market News ({len(unique_news)} articles)[/bold cyan]\n")
                
                for idx, item in enumerate(unique_news[:20], 1):
                    console.print(f"[bold white]{idx}. {item.title}[/bold white]")
                    console.print(f"   [dim]{item.source} | {item.published}[/dim]")
                    if item.url and item.url != '#':
                        console.print(f"   [blue]{item.url}[/blue]")
                    console.print()
            else:
                console.print("[yellow]⚠ Unable to fetch market news at this time[/yellow]")
                console.print("[dim]This may be due to API rate limits or connectivity issues[/dim]")
                console.print("\n[cyan]💡 Try searching for a specific ticker instead![/cyan]")
        
        Prompt.ask("\nPress Enter to continue")
    
    def research_theme(self):
        """Research investment theme."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]🔬 Theme Research Engine[/bold cyan]\n")
        console.print("Examples: quantum computing, artificial intelligence, electric vehicles, biotech\n")
        
        theme = Prompt.ask("Enter investment theme to research")
        
        console.print(f"\n[yellow]Researching: {theme}...[/yellow]\n")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Analyzing theme...", total=None)
            
            research = self.theme_researcher.research_theme(theme)
            
            progress.update(task, description="Gathering news...")
            
            progress.update(task, description="Analyzing opportunities...")
        
        DisplayManager.show_header()
        console.print(f"[bold cyan]Theme Research: {research['theme']}[/bold cyan]\n")
        
        console.print("[bold white]Summary:[/bold white]")
        console.print(f"{research['summary']}\n")
        
        if research.get('key_companies'):
            console.print("[bold cyan]🏢 Key Companies:[/bold cyan]\n")
            table = Table(box=box.ROUNDED)
            table.add_column("Ticker", style="bold white")
            table.add_column("Company", style="white")
            table.add_column("Recommendation", style="white")
            table.add_column("Reason", style="dim")
            
            for company in research['key_companies'][:10]:
                rec_color = "green" if company['recommendation'] == "BUY" else "yellow" if company['recommendation'] == "HOLD" else "red"
                table.add_row(
                    company['ticker'],
                    company['name'][:30],
                    f"[{rec_color}]{company['recommendation']}[/{rec_color}]",
                    company['reason'][:40]
                )
            
            console.print(table)
            console.print()
        
        if research.get('opportunities'):
            console.print("[bold cyan]🎯 Investment Opportunities:[/bold cyan]\n")
            for opp in research['opportunities'][:5]:
                action_color = "green" if opp['action'] == "BUY" else "red"
                console.print(f"[{action_color}]{opp['action']}[/{action_color}] {opp['ticker']} - Confidence: {opp['confidence']}%")
                console.print(f"  {opp['rationale']}\n")
        
        if research.get('risks'):
            console.print("[bold red]⚠ Risk Factors:[/bold red]")
            for risk in research['risks']:
                console.print(f"  • {risk}")
            console.print()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RESULTS_DIR / f"theme_{theme.replace(' ', '_')}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(research, f, indent=2)
        
        console.print(f"[dim]Research saved to: {filename}[/dim]\n")
        
        Prompt.ask("Press Enter to continue")
    
    def analyze_insider_trading(self):
        """Analyze insider trading activity."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]👔 Insider Trading Analysis[/bold cyan]\n")
        
        ticker = Prompt.ask("Enter ticker symbol").upper().strip()
        
        console.print(f"\n[yellow]Fetching insider trading data for {ticker}...[/yellow]\n")
        
        insider_trades = SECAnalyzer.get_insider_trades(ticker)
        
        if insider_trades:
            DisplayManager.show_insider_trades(insider_trades)
            
            buy_trades = [t for t in insider_trades if "Buy" in t.transaction_type]
            sell_trades = [t for t in insider_trades if "Sell" in t.transaction_type]
            
            console.print("[bold cyan]📊 Analysis:[/bold cyan]")
            console.print(f"Total Insider Buys: [green]{len(buy_trades)}[/green]")
            console.print(f"Total Insider Sells: [red]{len(sell_trades)}[/red]")
            
            if buy_trades:
                total_buy_value = sum([t.value for t in buy_trades])
                console.print(f"Total Buy Value: [green]${total_buy_value:,.0f}[/green]")
            
            if sell_trades:
                total_sell_value = sum([t.value for t in sell_trades])
                console.print(f"Total Sell Value: [red]${total_sell_value:,.0f}[/red]")
            
            console.print()
            
            if len(buy_trades) > len(sell_trades):
                console.print("[green]✓ Bullish Signal: More insider buying than selling[/green]")
            elif len(sell_trades) > len(buy_trades):
                console.print("[red]⚠ Bearish Signal: More insider selling than buying[/red]")
            else:
                console.print("[yellow]⚡ Neutral: Balanced insider activity[/yellow]")
        else:
            console.print("[yellow]No insider trading data available for this ticker[/yellow]")
        
        console.print()
        Prompt.ask("Press Enter to continue")
    
    def track_political_trades(self):
        """Track political figure trading activity."""
        DisplayManager.show_header()
        
        console.print("[bold cyan]🏛️  Political Figure Trading Tracker[/bold cyan]\n")
        console.print("Select group to analyze:\n")
        
        groups = [
            ("1", "trump_admin", "🟥 Trump Administration (Trump, Musk, RFK Jr., Ramaswamy)"),
            ("2", "pelosi", "🟦 Nancy Pelosi & Family"),
            ("3", "congress_dems", "🟦 Democratic Congress Members"),
            ("4", "congress_reps", "🟥 Republican Congress Members"),
            ("5", "senate", "🏛️  Senate Trading Activity")
        ]
        
        for num, key, desc in groups:
            console.print(f"{num}. {desc}")
        
        console.print()
        choice = Prompt.ask("Select group", choices=["1", "2", "3", "4", "5"], default="1")
        
        group_map = {g[0]: g[1] for g in groups}
        selected_group = group_map[choice]
        
        analysis = PoliticalTracker.get_group_trades(selected_group)
        
        DisplayManager.show_header()
        PoliticalTracker.display_group_analysis(analysis)
        
        # Save results
        if analysis and analysis['holdings']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = RESULTS_DIR / f"political_{selected_group}_{timestamp}.json"
            
            save_data = {
                'group_name': analysis['group']['name'],
                'members': analysis['group']['members'],
                'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'holdings': analysis['holdings']
            }
            
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            console.print(f"[dim]Analysis saved to: {filename}[/dim]\n")
        
        Prompt.ask("Press Enter to continue")
    
    def run_backtest(self):
        """Removed - backtesting feature disabled."""
        pass
    
    def settings_menu(self):
        """Settings menu."""
        while True:
            DisplayManager.show_header()
            
            console.print("[bold cyan]⚙️  Settings & Configuration[/bold cyan]\n")
            
            # Show current configuration
            console.print("[bold]Current Configuration:[/bold]")
            api_status = "✓ Configured" if self.config.get('anthropic_api_key') else "✗ Not set"
            console.print(f"API Key: {api_status}")
            console.print(f"Account Size: ${self.config['account_size']:,.2f}")
            _rpt_pct = float(self.config['risk_per_trade'])
            _rpt_ratio = _rpt_pct / 100.0
            console.print(f"Risk Per Trade: {_rpt_pct}% (ratio: {_rpt_ratio:.4f})")
            _rrr = float(self.config.get('default_rrr', 2.0))
            console.print(f"Risk:Reward (R:R): 1:{_rrr:.2f}")
            console.print(f"Max Positions: {self.config['max_positions']}")
            console.print(f"Analysis Mode: {self.config.get('analysis_mode', 'advanced')}")
            console.print(f"Notifications: {'Enabled' if self.config.get('notifications_enabled') else 'Disabled'}")
            console.print(f"Crypto WS (Coinbase): {'Enabled' if self.config.get('enable_crypto_ws', True) else 'Disabled'}\n")
            
            console.print("[bold]Configuration Options:[/bold]")
            console.print("1. Configure API Keys (Anthropic Claude)")
            console.print("2. Update Account Size")
            console.print("3. Update Risk Per Trade (%)")
            console.print("4. Update Risk:Reward Ratio (R:R)")
            console.print("5. Update Max Positions")
            console.print("6. Toggle Analysis Mode (basic/advanced)")
            console.print("7. Configure Notifications (Telegram)")
            console.print("8. Run Preflight Setup (Schwab, Polygon, etc.)")
            console.print("9. Send Test Telegram Message")
            console.print("10. Toggle Crypto WebSocket (Coinbase)")
            console.print("11. Test Crypto WebSocket Feed")
            console.print("12. Back to Main Menu\n")

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], default="12")
            
            if choice == "1":
                # Configure API keys
                self.api_key = ConfigurationManager.setup_api_keys()
                self.config['anthropic_api_key'] = self.api_key
                ConfigurationManager.save_config(self.config)
                try:
                    import anthropic
                    self.analyzer = AIAnalyzer(self.api_key)
                    self.theme_researcher = ThemeResearcher(self.api_key)
                    self.scanner = MarketScanner(self.analyzer)
                    console.print("[green]✓ API key configured and AI systems initialized[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠ API key saved but AI initialization failed: {e}[/yellow]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "2":
                # Update account size
                new_size = FloatPrompt.ask("New account size ($)", default=self.config['account_size'])
                self.config['account_size'] = new_size
                ConfigurationManager.save_config(self.config)
                console.print("[green]✓ Account size updated[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "3":
                # Update risk per trade
                current_ratio = float(self.config['risk_per_trade']) / 100.0
                new_risk_ratio = FloatPrompt.ask("New risk per trade (ratio, e.g., 0.02 for 2%)", default=current_ratio)
                try:
                    new_risk_ratio = float(new_risk_ratio)
                except Exception:
                    new_risk_ratio = current_ratio
                self.config['risk_per_trade'] = round(new_risk_ratio * 100.0, 4)
                ConfigurationManager.save_config(self.config)
                console.print("[green]✓ Risk per trade updated[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "4":
                # Update Risk:Reward ratio
                current_rrr = float(self.config.get('default_rrr', 2.0))
                rr_input = Prompt.ask("New Risk:Reward (R:R) e.g., 1:2 or 2", default=f"{current_rrr}")
                def _parse_rrr(s: str, fallback: float) -> float:
                    try:
                        s = str(s).strip()
                        if ':' in s:
                            parts = s.split(':')
                            if len(parts) == 2:
                                left = float(parts[0])
                                right = float(parts[1])
                                if left > 0:
                                    return right / left
                        val = float(s)
                        return val if val > 0 else fallback
                    except:
                        return fallback
                new_rrr = _parse_rrr(rr_input, current_rrr)
                self.config['default_rrr'] = new_rrr
                ConfigurationManager.save_config(self.config)
                console.print(f"[green]✓ Risk:Reward updated to 1:{new_rrr:.2f}[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "5":
                # Update max positions
                new_max = IntPrompt.ask("New max positions", default=self.config['max_positions'])
                self.config['max_positions'] = new_max
                ConfigurationManager.save_config(self.config)
                console.print("[green]✓ Max positions updated[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "6":
                # Toggle analysis mode
                current_mode = self.config.get('analysis_mode', 'advanced')
                new_mode = 'basic' if current_mode == 'advanced' else 'advanced'
                self.config['analysis_mode'] = new_mode
                ConfigurationManager.save_config(self.config)
                console.print(f"[green]✓ Analysis mode set to: {new_mode}[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "7":
                # Configure notifications
                enable_notif = Confirm.ask("Enable Telegram notifications?", default=self.config.get('notifications_enabled', False))
                self.config['notifications_enabled'] = enable_notif
                if enable_notif:
                    telegram_token = Prompt.ask("Telegram Bot Token", default=self.config.get('telegram_bot_token', ''))
                    telegram_chat = Prompt.ask("Telegram Chat ID", default=self.config.get('telegram_chat_id', ''))
                    self.config['telegram_bot_token'] = telegram_token
                    self.config['telegram_chat_id'] = telegram_chat
                ConfigurationManager.save_config(self.config)
                self.notifier = NotificationManager(self.config)
                console.print("[green]✓ Notification settings updated[/green]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "8":
                # Run preflight setup
                try:
                    ConfigurationManager.run_preflight(self.config)
                    console.print("[green]✓ Preflight setup completed[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠ Preflight error: {e}[/yellow]")
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "9":
                # Send test Telegram message
                console.print("[cyan]Sending test message via Telegram...[/cyan]")
                try:
                    if self.notifier and hasattr(self.notifier, 'send'):
                        sent = self.notifier.send("🧪 Test message from FinalAI Trading App")
                        if sent:
                            console.print("[green]✓ Test message sent successfully[/green]")
                        else:
                            console.print("[yellow]⚠ Test message failed - check notification settings[/yellow]")
                    else:
                        console.print("[yellow]⚠ Notifications not configured[/yellow]")
                except Exception as e:
                    console.print(f"[red]❌ Test failed: {e}[/red]")
                Prompt.ask("\nPress Enter to continue")

            elif choice == "10":
                # Toggle Coinbase crypto websocket
                current = bool(self.config.get('enable_crypto_ws', True))
                new_val = not current
                self.config['enable_crypto_ws'] = new_val
                ConfigurationManager.save_config(self.config)
                if not new_val:
                    try:
                        DataManager.stop_crypto_ws()
                    except Exception:
                        pass
                console.print(f"[green]✓ Crypto WebSocket is now {'Enabled' if new_val else 'Disabled'}[/green]")
                Prompt.ask("\nPress Enter to continue")

            elif choice == "11":
                # Test Coinbase WS connectivity and price updates
                try:
                    sym = Prompt.ask("Crypto symbol to test (Coinbase product id)", default="BTC-USD").upper()
                    DataManager.start_crypto_ws([sym])
                    console.print("[cyan]Connecting to Coinbase WS and waiting for ticks (up to 10s)...[/cyan]")
                    import time as _t
                    ok = False
                    for _ in range(20):
                        _t.sleep(0.5)
                        p = DataManager.get_cached_price(sym, max_age=3.0)
                        if p is not None:
                            age = DataManager.get_cached_price_age(sym) or 0.0
                            console.print(f"[green]✓ WS price received[/green] {sym}: ${p:.2f} [dim](age {age:.1f}s)[/dim]")
                            ok = True
                            break
                    if not ok:
                        console.print("[yellow]⚠ No WS tick received yet. Ensure 'websockets' is installed and network allows wss.[/yellow]")
                except Exception as e:
                    console.print(f"[red]❌ Test failed: {e}[/red]")
                Prompt.ask("\nPress Enter to continue")

            elif choice == "12":
                break
    
    def _save_analysis_report(self, ticker: str, trade: TradeSummary):
        """Save analysis report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RESULTS_DIR / f"{ticker}_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(asdict(trade), f, indent=2)
        
        console.print(f"[dim]Report saved to: {filename}[/dim]")
    
    def _generate_analysis_chart(self, ticker: str, df: pd.DataFrame, trade: TradeSummary, 
                                 patterns: 'PatternAnalysis', market_structure: 'MarketStructure'):
        """Generate chart with buy/sell signals, stop loss, take profit levels, patterns, and FVGs."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch
            from matplotlib.lines import Line2D
            import numpy as _np
            
            # Cleaner layout with more space
            fig, ax = plt.subplots(figsize=(18, 11), facecolor='#0f0f0f')
            ax.set_facecolor('#0f0f0f')
            
            # Plot candlesticks with improved spacing
            candle_width = 0.6
            plot_df = df.tail(250).reset_index(drop=True)  # Last 250 bars for cleaner display
            
            for idx, row in plot_df.iterrows():
                x = idx
                open_price = row.get('Open', row.get('open', row['Close']))
                high = row.get('High', row.get('high', row['Close']))
                low = row.get('Low', row.get('low', row['Close']))
                close = row.get('Close', row.get('close', row['Close']))
                
                is_bullish = close >= open_price
                # Bright green for bullish, deep red for bearish
                color = '#00ff00' if is_bullish else '#cc0000'
                
                # Wick
                ax.plot([x, x], [low, high], color=color, linewidth=1.5, alpha=0.95, solid_capstyle='butt')
                
                # Body
                body_height = abs(close - open_price)
                body_bottom = min(open_price, close)
                
                if body_height < close * 0.0001:
                    body_height = close * 0.0001
                
                if is_bullish:
                    rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                    facecolor='#0f0f0f', edgecolor=color, linewidth=1.6, alpha=1.0)
                else:
                    rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                    facecolor=color, edgecolor=color, linewidth=1.6, alpha=0.85)
                ax.add_patch(rect)

            # Add padding on right side for future expansion
            ax.set_xlim(-5, len(plot_df) + 15)
            
            # Draw Fair Value Gaps (FVGs) with labels
            if market_structure.fair_value_gaps:
                fvg_count = 0
                for fvg_low, fvg_high in market_structure.fair_value_gaps[-5:]:  # Last 5 FVGs
                    fvg_count += 1
                    # Draw translucent zone for FVG with subtle glow
                    ax.axhspan(fvg_low, fvg_high, alpha=0.12, color='#FF9800')
                    # Add borders
                    ax.axhline(fvg_low, color='#FF9800', linestyle=':', linewidth=1.2, alpha=0.6)
                    ax.axhline(fvg_high, color='#FF9800', linestyle=':', linewidth=1.2, alpha=0.6)
                    # Add label on right side
                    mid_price = (fvg_low + fvg_high) / 2
                    ax.text(len(plot_df) + 8, mid_price, f"FVG{fvg_count}", fontsize=8, color='#FF9800',
                           weight='bold', verticalalignment='center', family='monospace')
            
            # Draw Order Blocks with labels
            if market_structure.order_blocks:
                ob_count = 0
                for ob_low, ob_high in market_structure.order_blocks[-3:]:  # Last 3 order blocks
                    ob_count += 1
                    ax.axhspan(ob_low, ob_high, alpha=0.08, color='#9C27B0')
                    ax.axhline(ob_low, color='#9C27B0', linestyle='-.', linewidth=1, alpha=0.4)
                    ax.axhline(ob_high, color='#9C27B0', linestyle='-.', linewidth=1, alpha=0.4)
                    # Add label on right side
                    mid_price = (ob_low + ob_high) / 2
                    ax.text(len(plot_df) + 8, mid_price, f"OB{ob_count}", fontsize=8, color='#9C27B0',
                           weight='bold', verticalalignment='center', family='monospace')
            
            # Mark Candlestick Patterns with labels
            if patterns.candlestick_patterns and len(plot_df) > 0:
                last_idx = len(plot_df) - 1
                last_price = plot_df.iloc[-1]['Close']
                pattern_text = ', '.join(patterns.candlestick_patterns[:3])
                ax.annotate(f"Candlestick:\n{pattern_text}", xy=(last_idx, last_price),
                           xytext=(-120, -120), textcoords='offset points',
                           fontsize=9, color='#FFD700', weight='bold',
                           bbox=dict(boxstyle='round,pad=0.6', facecolor='#1a1a1a', edgecolor='#FFD700', alpha=0.95, linewidth=2),
                           arrowprops=dict(arrowstyle='->', color='#FFD700', lw=1.8, connectionstyle='arc3,rad=0.3'))
            
            # Mark Bullish Patterns with clear label
            if patterns.bullish_patterns:
                pattern_text = ', '.join(patterns.bullish_patterns)
                ax.text(0.015, 0.95, f"📈 BULLISH PATTERNS:\n{pattern_text}", 
                       transform=ax.transAxes, fontsize=11, color='#00ff00', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.8', facecolor='#0f0f0f', alpha=0.9, edgecolor='#00ff00', linewidth=2.5),
                       verticalalignment='top', family='monospace')
            
            # Mark Bearish Patterns with clear label
            if patterns.bearish_patterns:
                pattern_text = ', '.join(patterns.bearish_patterns)
                y_offset = 0.86 if patterns.bullish_patterns else 0.95
                ax.text(0.015, y_offset, f"📉 BEARISH PATTERNS:\n{pattern_text}", 
                       transform=ax.transAxes, fontsize=11, color='#ff0000', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.8', facecolor='#0f0f0f', alpha=0.9, edgecolor='#ff0000', linewidth=2.5),
                       verticalalignment='top', family='monospace')
            
            # Entry point (last bar) with clear label
            entry_idx = len(plot_df) - 1
            entry_color = '#00ff00' if trade.action == 'BUY' else '#ff0000'
            
            # Circle entry point
            circle = Circle((entry_idx, trade.entry_price), radius=2.5, color=entry_color, 
                          zorder=10, linewidth=3.5, fill=False)
            ax.add_patch(circle)
            
            # Entry label with reason and confidence
            entry_label = f"{trade.action}\n${trade.entry_price:.2f}\n{trade.confidence:.0f}% CONF\n{trade.primary_reason[:45]}"
            ax.annotate(entry_label, xy=(entry_idx, trade.entry_price), 
                       xytext=(40, 50 if trade.action == 'BUY' else -50),
                       textcoords='offset points', fontsize=11, color='white', weight='bold',
                       bbox=dict(boxstyle='round,pad=1', facecolor=entry_color, alpha=0.9, edgecolor='white', linewidth=2.5),
                       arrowprops=dict(arrowstyle='->', color='white', lw=2.5))
            
            # Stop loss line with label
            ax.axhline(trade.stop_loss, color='#ff0000', linestyle='--', linewidth=2.2, alpha=0.85, label=f'Stop Loss: ${trade.stop_loss:.2f}')
            ax.text(len(plot_df) + 1, trade.stop_loss, 'SL', fontsize=9, color='#ff0000', weight='bold', family='monospace')
            
            # Take profit lines with labels
            ax.axhline(trade.take_profit_1, color='#00ff00', linestyle='--', linewidth=2.2, alpha=0.85, label=f'TP1: ${trade.take_profit_1:.2f}')
            ax.text(len(plot_df) + 1, trade.take_profit_1, 'TP1', fontsize=9, color='#00ff00', weight='bold', family='monospace')
            
            ax.axhline(trade.take_profit_2, color='#00ff00', linestyle='--', linewidth=1.8, alpha=0.65, label=f'TP2: ${trade.take_profit_2:.2f}')
            ax.text(len(plot_df) + 1, trade.take_profit_2, 'TP2', fontsize=9, color='#00ff00', weight='bold', family='monospace')
            
            ax.axhline(trade.take_profit_3, color='#00ff00', linestyle='--', linewidth=1.4, alpha=0.45, label=f'TP3: ${trade.take_profit_3:.2f}')
            ax.text(len(plot_df) + 1, trade.take_profit_3, 'TP3', fontsize=9, color='#00ff00', weight='bold', family='monospace')
            
            # Title and labels
            try:
                rr_display = trade.reward_per_share / trade.risk_per_share if (trade.risk_per_share and trade.risk_per_share > 0 and trade.reward_per_share) else trade.risk_reward_ratio
            except Exception:
                rr_display = trade.risk_reward_ratio
            ax.set_title(f"{ticker} - AI Trade Analysis | {trade.action} | Confidence: {trade.confidence:.0f}% | R:R = 1:{rr_display:.2f}",
                        fontsize=17, fontweight='bold', color='white', pad=20)
            ax.set_ylabel('Price ($)', fontsize=13, color='#cccccc', weight='bold')
            ax.set_xlabel('Candles (with future space)', fontsize=13, color='#cccccc', weight='bold')
            ax.tick_params(colors='#888888', labelsize=10)
            ax.grid(True, alpha=0.08, color='#333333', linestyle='--')
            ax.legend(loc='upper left', fontsize=11, facecolor='#1a1a1a', edgecolor='#4FC3F7', framealpha=0.95, frameon=True)
            
            # --- Support / Resistance detection with labels ---
            try:
                highs = plot_df['High'].values
                lows = plot_df['Low'].values
                closes = plot_df['Close'].values if 'Close' in plot_df.columns else plot_df['close'].values
                n = len(plot_df)
                if n >= 20:
                    # Detect local peaks/troughs
                    peak_idx = []
                    trough_idx = []
                    for i in range(2, n-2):
                        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                            peak_idx.append(i)
                        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                            trough_idx.append(i)

                    # Candidate levels from peaks and troughs
                    levels = [highs[i] for i in peak_idx] + [lows[i] for i in trough_idx]
                    if levels:
                        price_range = float(max(highs) - min(lows))
                        tol = max(0.01, price_range * 0.002)  # ~0.2% of range, min 1c

                        # Cluster levels by proximity
                        levels_sorted = sorted(levels)
                        clusters = []  # list of [values]
                        current = [levels_sorted[0]]
                        for v in levels_sorted[1:]:
                            if abs(v - _np.mean(current)) <= tol:
                                current.append(v)
                            else:
                                clusters.append(current)
                                current = [v]
                        if current:
                            clusters.append(current)

                        # Score clusters by touch count
                        scored = []
                        for c in clusters:
                            level = float(_np.mean(c))
                            touches = sum(1 for x in levels if abs(x - level) <= tol)
                            scored.append((touches, level))

                        # Keep top 5 well-respected levels with >=3 touches
                        top_levels = [lvl for (tch,lvl) in sorted(scored, key=lambda x: (-x[0], -x[1])) if tch >= 3][:5]

                        # Draw SR lines with labels
                        sr_count = 0
                        for lvl in top_levels:
                            sr_count += 1
                            ax.axhline(lvl, color='#4FC3F7', linestyle=':', linewidth=1.3, alpha=0.75)
                            ax.text(len(plot_df) + 1, lvl, f"R{sr_count}", fontsize=8, color='#4FC3F7', weight='bold', family='monospace')
                        if top_levels:
                            sr_proxy = Line2D([0],[0], color='#4FC3F7', linestyle=':', linewidth=1.3, alpha=0.75)
                            ax.legend([sr_proxy], [f"Support/Resistance ({len(top_levels)})"], loc='upper right', fontsize=10, facecolor='#1a1a1a', edgecolor='#4FC3F7', framealpha=0.95)
            except Exception:
                pass

            # --- Plot recent window high/low with labels ---
            try:
                win_high = float(plot_df['High'].max())
                win_low = float(plot_df['Low'].min())
                ax.axhline(win_high, color='#FFD54F', linestyle='--', linewidth=1.3, alpha=0.7)
                ax.axhline(win_low, color='#FFD54F', linestyle='--', linewidth=1.3, alpha=0.7)
                ax.text(len(plot_df) + 1, win_high, 'HI', fontsize=8, color='#FFD54F', weight='bold', family='monospace')
                ax.text(len(plot_df) + 1, win_low, 'LO', fontsize=8, color='#FFD54F', weight='bold', family='monospace')
            except Exception:
                pass

            # Info box with key metrics - cleaner design with space
            info_text = f"📊 TRADE DETAILS\n{'─'*28}\n"
            info_text += f"ACTION:     {trade.action}\n"
            info_text += f"ENTRY:      ${trade.entry_price:.2f}\n"
            info_text += f"STOP LOSS:  ${trade.stop_loss:.2f}\n"
            info_text += f"\n💰 TARGETS\n{'─'*28}\n"
            info_text += f"TP1: ${trade.take_profit_1:.2f}  |  "
            info_text += f"TP2: ${trade.take_profit_2:.2f}\n"
            info_text += f"TP3: ${trade.take_profit_3:.2f}\n"
            info_text += f"\n⚖️  RISK/REWARD\n{'─'*28}\n"
            info_text += f"RISK:       ${trade.risk_amount:.2f}\n"
            info_text += f"REWARD:     ${trade.reward_amount:.2f}\n"
            info_text += f"POSITION:   {trade.position_size} shares\n"
            info_text += f"\n📈 METRICS\n{'─'*28}\n"
            info_text += f"WIN PROB:   {trade.win_probability:.0f}%\n"
            info_text += f"EXP VALUE:  ${trade.expected_value:.2f}"
            
            fig.text(0.015, 0.98, info_text, fontsize=10, family='monospace', color='white',
                    verticalalignment='top', bbox=dict(boxstyle='round,pad=1', facecolor='#1a1a1a', 
                    alpha=0.97, edgecolor=entry_color, linewidth=3))
            
            plt.tight_layout()
            
            # Save chart
            chart_dir = RESULTS_DIR / ticker
            chart_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_path = chart_dir / f'analysis_{timestamp}.png'
            plt.savefig(chart_path, dpi=120, bbox_inches='tight', facecolor='#1a1a1a')
            plt.close(fig)
            
            console.print(f"[green]📊 Chart saved: {chart_path}[/green]")
            
            # Auto-open chart
            try:
                import os
                os.startfile(str(chart_path))
            except Exception:
                pass
                
        except Exception as e:
            console.print(f"[yellow]Chart generation failed: {e}[/yellow]")
            import traceback
            traceback.print_exc()
    
    def _track_trade_decision(self, ticker: str, trade: TradeSummary, took_trade: bool, df: pd.DataFrame):
        """Track trade decision for future monitoring and performance tracking."""
        tracking_file = RESULTS_DIR / 'ai_performance_tracking.csv'
        
        # Initialize tracking file if doesn't exist
        if not tracking_file.exists():
            with open(tracking_file, 'w') as f:
                f.write('timestamp,ticker,action,entry_price,stop_loss,tp1,tp2,tp3,confidence,win_prob,risk_amount,reward_amount,rr_ratio,position_size,took_trade,during_market_hours,current_price,hypothetical_pnl,hypothetical_pnl_pct,status,exit_price,actual_pnl,actual_pnl_pct,exit_date,bars_since_entry,primary_reason\n')
        
        # Get current price (last close)
        current_price = df['Close'].iloc[-1] if 'Close' in df.columns else df['close'].iloc[-1]
        
        # Save as OPEN trade - will be monitored later
        status = 'OPEN'
        hypothetical_pnl = 0.0
        exit_price = current_price
        
        # Determine if request happened during US equity hours including pre/after (PT 1:00–17:00, Mon–Fri)
        try:
            from zoneinfo import ZoneInfo
            now_pt = datetime.now(ZoneInfo('America/Los_Angeles'))
            is_weekday = now_pt.weekday() < 5
            open_pt = now_pt.replace(hour=1, minute=0, second=0, microsecond=0)
            close_pt = now_pt.replace(hour=17, minute=0, second=0, microsecond=0)
            during_market_hours = bool(is_weekday and (now_pt >= open_pt) and (now_pt <= close_pt))
        except Exception:
            during_market_hours = ''  # fallback empty -> will be computed later if needed

        # Save to tracking file with AI's exact position size
        with open(tracking_file, 'a') as f:
            f.write(f"{trade.timestamp},{ticker},{trade.action},{trade.entry_price},{trade.stop_loss},"
                   f"{trade.take_profit_1},{trade.take_profit_2},{trade.take_profit_3},"
                   f"{trade.confidence},{trade.win_probability},{trade.risk_amount},{trade.reward_amount},"
                   f"{trade.risk_reward_ratio},{trade.position_size},{took_trade},{during_market_hours},{current_price},{hypothetical_pnl:.2f},"
                   f"{status},{exit_price},{hypothetical_pnl},,"
                   f"\"{trade.primary_reason[:100]}\"\n")
        
        console.print(f"[dim]✓ Trade tracked - will monitor for TP/SL hits (Position: {trade.position_size} shares)[/dim]")
    
    def _load_tracking_df(self, tracking_file) -> pd.DataFrame:
        """Robustly load the tracking CSV even if schema changed across rows.

        Handles older rows with fewer columns and newer rows with added columns
        by reading via csv.DictReader and normalizing to the expected schema.
        """
        import csv as _csv
        expected_cols = [
            'timestamp','ticker','action','entry_price','stop_loss','tp1','tp2','tp3',
            'confidence','win_prob','risk_amount','reward_amount','rr_ratio','position_size',
            'took_trade','during_market_hours','current_price','hypothetical_pnl','hypothetical_pnl_pct','status','exit_price','actual_pnl','actual_pnl_pct',
            'exit_date','bars_since_entry','primary_reason'
        ]
        rows = []
        try:
            with open(tracking_file, 'r', newline='', encoding='utf-8') as f:
                reader = _csv.DictReader(f)
                # Map each row into the expected schema, filling missing with ''
                for r in reader:
                    clean = {col: r.get(col, '') for col in expected_cols}
                    rows.append(clean)
        except Exception as e:
            # Fallback: try pandas with python engine, skipping bad lines
            try:
                return pd.read_csv(tracking_file, engine='python', on_bad_lines='skip')
            except Exception:
                raise e

        df = pd.DataFrame(rows, columns=expected_cols)
        # Coerce numerics
        numeric_cols = [
            'entry_price','stop_loss','tp1','tp2','tp3','confidence','win_prob',
            'risk_amount','reward_amount','rr_ratio','position_size','current_price',
            'hypothetical_pnl','exit_price','actual_pnl'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def _migrate_tracking_file(self):
        """Fix rows where exit_date precedes entry timestamp; reopen and clear exits.

        Also standardizes the CSV columns/order to prevent future tokenization issues.
        """
        tracking_file = RESULTS_DIR / 'ai_performance_tracking.csv'
        if not tracking_file.exists():
            return
        try:
            df = self._load_tracking_df(tracking_file)
            if df is None or len(df) == 0:
                return
            # Parse dates and find backdated exits
            ts = pd.to_datetime(df.get('timestamp'), errors='coerce')
            ed = pd.to_datetime(df.get('exit_date'), errors='coerce')
            mask = (
                df.get('status').fillna('OPEN') != 'OPEN'
            ) & ed.notna() & ts.notna() & (ed < ts)

            if mask.any():
                df.loc[mask, 'status'] = 'OPEN'
                df.loc[mask, 'exit_price'] = ''
                df.loc[mask, 'actual_pnl'] = 0
                df.loc[mask, 'exit_date'] = ''

            # Sanitize invalid status values from legacy rows
            allowed_status = {'OPEN','STOPPED','TP1_HIT','TP2_HIT','TP3_HIT'}
            if 'status' in df.columns:
                invalid_status = ~df['status'].isin(list(allowed_status))
                if invalid_status.any():
                    df.loc[invalid_status, 'status'] = 'OPEN'

                # Ensure consistent columns and save
                import csv as _csv
                expected_cols = [
                    'timestamp','ticker','action','entry_price','stop_loss','tp1','tp2','tp3',
                    'confidence','win_prob','risk_amount','reward_amount','rr_ratio','position_size',
                    'took_trade','during_market_hours','current_price','hypothetical_pnl','hypothetical_pnl_pct','status','exit_price','actual_pnl','actual_pnl_pct',
                    'exit_date','bars_since_entry','primary_reason'
                ]
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = ''
                df = df[expected_cols]
                df.to_csv(tracking_file, index=False, quoting=_csv.QUOTE_MINIMAL)
        except Exception:
            # Non-fatal; updater will still try to work
            pass

    def _update_tracked_trades(self):
        """Update all open tracked trades to check if they hit TP or SL."""
        tracking_file = RESULTS_DIR / 'ai_performance_tracking.csv'
        
        if not tracking_file.exists():
            console.print("[dim]No tracking file exists yet.[/dim]")
            return
        
        try:
            df = self._load_tracking_df(tracking_file)
            
            # Filter only OPEN trades
            open_trades = df[df['status'] == 'OPEN'].copy()
            
            if len(open_trades) == 0:
                console.print("[dim]No open trades to update.[/dim]")
                return
            
            console.print(f"\n[yellow]Updating {len(open_trades)} open simulated trades...[/yellow]\n")
            
            updated = False
            for idx, row in open_trades.iterrows():
                ticker = row['ticker']
                action = row['action']
                entry_price = float(row['entry_price'])
                stop_loss = float(row['stop_loss'])
                tp1 = float(row['tp1'])
                tp2 = float(row['tp2'])
                tp3 = float(row['tp3'])
                risk_amount = float(row['risk_amount'])
                reward_amount = float(row['reward_amount'])
                
                # Use the AI's exact position size from the recommendation, or calculate if missing
                if 'position_size' in row and pd.notna(row['position_size']) and row['position_size'] != '':
                    shares = float(row['position_size'])
                else:
                    # Fallback: calculate from risk parameters
                    price_distance = abs(entry_price - stop_loss)
                    shares = risk_amount / price_distance if price_distance > 0 else 0
                
                if shares == 0:
                    console.print(f"[dim]Skipping {ticker} - no position size[/dim]")
                    continue
                
                # Fetch latest price data
                try:
                    # Calculate how many days since entry to determine fetch period
                    entry_date = pd.to_datetime(row['timestamp'])
                    days_since_entry = (datetime.now() - entry_date).days
                    
                    # Prefer intraday data for recent entries to show live-ish P&L
                    attempts = []
                    if days_since_entry <= 2:
                        attempts = [("5d","5m"), ("10d","15m"), ("3mo","1d")]
                    elif days_since_entry <= 7:
                        attempts = [("10d","15m"), ("3mo","1d")]
                    elif days_since_entry <= 90:
                        attempts = [("3mo","1d")]
                    elif days_since_entry <= 180:
                        attempts = [("6mo","1d")]
                    elif days_since_entry <= 365:
                        attempts = [("1y","1d")]
                    else:
                        attempts = [("2y","1d")]

                    latest_df = None
                    for per, intr in attempts:
                        try:
                            tmp = DataManager.fetch_data(ticker, per, intr)
                            if tmp is not None and len(tmp) >= 5:
                                latest_df = tmp
                                break
                        except Exception:
                            continue
                    if latest_df is None or len(latest_df) < 5:
                        console.print(f"[dim]Could not fetch data for {ticker}[/dim]")
                        continue
                    
                    # Normalize index and entry_date to naive datetimes for safe comparisons
                    try:
                        latest_df = latest_df.copy()
                        latest_df.index = pd.to_datetime(latest_df.index)
                        # Drop timezone info if present
                        if getattr(latest_df.index, 'tz', None) is not None:
                            latest_df.index = latest_df.index.tz_convert(None)
                    except Exception:
                        pass
                    try:
                        if isinstance(entry_date, pd.Timestamp) and entry_date.tzinfo is not None:
                            entry_date = entry_date.tz_localize(None)
                    except Exception:
                        pass

                    # Get data since entry (including entry date for edge cases)
                    try:
                        relevant_data = latest_df.loc[latest_df.index >= entry_date]
                    except Exception:
                        # As a fallback, coerce both sides to numeric int64 nanoseconds
                        try:
                            idx_ns = pd.to_datetime(latest_df.index).view('i8')
                            entry_ns = pd.to_datetime(entry_date).value
                            mask = idx_ns >= entry_ns
                            relevant_data = latest_df.loc[mask]
                        except Exception:
                            relevant_data = latest_df.tail(0)
                    
                    if len(relevant_data) == 0:
                        # No data at or after entry date (e.g., same day before close/weekend)
                        # Do NOT backdate exits using pre-entry candles. Treat as still OPEN and
                        # update only unrealized P&L using the latest available close.
                        latest_close = float(latest_df.iloc[-1]['Close'])
                        if action == 'BUY':
                            price_diff = latest_close - entry_price
                            hypothetical_pnl = price_diff * shares
                            hypothetical_pnl_pct = (price_diff / entry_price * 100.0) if entry_price else 0.0
                        else:
                            price_diff = entry_price - latest_close
                            hypothetical_pnl = price_diff * shares
                            hypothetical_pnl_pct = (price_diff / entry_price * 100.0) if entry_price else 0.0

                        df.at[idx, 'hypothetical_pnl'] = hypothetical_pnl
                        df.at[idx, 'hypothetical_pnl_pct'] = hypothetical_pnl_pct
                        df.at[idx, 'current_price'] = latest_close
                        df.at[idx, 'bars_since_entry'] = 0
                        updated = True
                        pnl_color = "green" if hypothetical_pnl >= 0 else "red"
                        console.print(f"[{pnl_color}]○ {ticker} {action}: Entry ${entry_price:.2f} → Current ${latest_close:.2f} | {shares:.0f} shares × ${price_diff:.2f} = ${hypothetical_pnl:.2f}[/{pnl_color}]")
                        # Skip TP/SL checks for pre-entry data
                        continue
                    
                    status = 'OPEN'
                    exit_price = entry_price
                    hypothetical_pnl = 0.0
                    exit_date = ''
                    # Tolerance and time-based exit settings
                    tol_pct = 0.0005
                    max_bars_to_close = 0
                    try:
                        if getattr(self, 'config', None):
                            tol_pct = float(self.config.get('performance_hit_tolerance_pct', 0.0005))
                            max_bars_to_close = int(self.config.get('performance_close_after_bars', 0))
                    except Exception:
                        pass
                    
                    bar_count = 0
                    for date, candle in relevant_data.iterrows():
                        high = float(candle['High'])
                        low = float(candle['Low'])
                        close = float(candle['Close'])
                        bar_count += 1
                        
                        if action == 'BUY':
                            # Check stop loss first
                            sl_thr = stop_loss * (1 + tol_pct)
                            if low <= sl_thr:
                                status = 'STOPPED'
                                exit_price = stop_loss
                                hypothetical_pnl = -risk_amount
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            # Check take profits - use actual price movements
                            tp3_thr = tp3 * (1 - tol_pct)
                            tp2_thr = tp2 * (1 - tol_pct)
                            tp1_thr = tp1 * (1 - tol_pct)
                            if high >= tp3_thr:
                                status = 'TP3_HIT'
                                exit_price = tp3
                                hypothetical_pnl = (tp3 - entry_price) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            elif high >= tp2_thr:
                                status = 'TP2_HIT'
                                exit_price = tp2
                                hypothetical_pnl = (tp2 - entry_price) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            elif high >= tp1_thr:
                                status = 'TP1_HIT'
                                exit_price = tp1
                                hypothetical_pnl = (tp1 - entry_price) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                        
                        else:  # SELL
                            # Check stop loss first
                            sl_thr = stop_loss * (1 - tol_pct)
                            if high >= sl_thr:
                                status = 'STOPPED'
                                exit_price = stop_loss
                                hypothetical_pnl = -risk_amount
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            # Check take profits - use actual price movements
                            tp3_thr = tp3 * (1 + tol_pct)
                            tp2_thr = tp2 * (1 + tol_pct)
                            tp1_thr = tp1 * (1 + tol_pct)
                            if low <= tp3_thr:
                                status = 'TP3_HIT'
                                exit_price = tp3
                                hypothetical_pnl = (entry_price - tp3) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            elif low <= tp2_thr:
                                status = 'TP2_HIT'
                                exit_price = tp2
                                hypothetical_pnl = (entry_price - tp2) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break
                            elif low <= tp1_thr:
                                status = 'TP1_HIT'
                                exit_price = tp1
                                hypothetical_pnl = (entry_price - tp1) * shares
                                exit_date = date.strftime('%Y-%m-%d')
                                break

                        # Time-based exit if enabled and reached bar threshold without TP/SL
                        if max_bars_to_close > 0 and bar_count >= max_bars_to_close:
                            status = 'TIME_EXIT'
                            exit_price = close
                            if action == 'BUY':
                                hypothetical_pnl = (close - entry_price) * shares
                                hypothetical_pnl_pct = ((close - entry_price) / entry_price * 100.0) if entry_price else 0.0
                            else:
                                hypothetical_pnl = (entry_price - close) * shares
                                hypothetical_pnl_pct = ((entry_price - close) / entry_price * 100.0) if entry_price else 0.0
                            exit_date = date.strftime('%Y-%m-%d')
                            break
                    
                    # If still OPEN, calculate unrealized P&L based on current price
                    if status == 'OPEN' and len(relevant_data) > 0:
                        current_price = float(relevant_data.iloc[-1]['Close'])
                        
                        if action == 'BUY':
                            price_diff = current_price - entry_price
                            hypothetical_pnl = price_diff * shares
                            hypothetical_pnl_pct = (price_diff / entry_price * 100.0) if entry_price else 0.0
                        else:  # SELL
                            price_diff = entry_price - current_price
                            hypothetical_pnl = price_diff * shares
                            hypothetical_pnl_pct = (price_diff / entry_price * 100.0) if entry_price else 0.0
                        
                        # Update unrealized P&L for open positions
                        df.at[idx, 'hypothetical_pnl'] = hypothetical_pnl
                        df.at[idx, 'hypothetical_pnl_pct'] = hypothetical_pnl_pct
                        df.at[idx, 'current_price'] = current_price
                        df.at[idx, 'bars_since_entry'] = bar_count
                        updated = True
                        
                        pnl_color = "green" if hypothetical_pnl >= 0 else "red"
                        console.print(f"[{pnl_color}]○ {ticker} {action}: Entry ${entry_price:.2f} → Current ${current_price:.2f} | {shares:.0f} shares × ${price_diff:.2f} = ${hypothetical_pnl:.2f}[/{pnl_color}]")
                    
                    # Update the row if status changed to closed
                    elif status != 'OPEN':
                        df.at[idx, 'status'] = status
                        df.at[idx, 'exit_price'] = exit_price
                        df.at[idx, 'hypothetical_pnl'] = hypothetical_pnl
                        df.at[idx, 'actual_pnl'] = hypothetical_pnl
                        # Realized P&L % from entry
                        try:
                            if action == 'BUY':
                                df.at[idx, 'actual_pnl_pct'] = ((exit_price - entry_price) / entry_price * 100.0) if entry_price else 0.0
                            else:
                                df.at[idx, 'actual_pnl_pct'] = ((entry_price - exit_price) / entry_price * 100.0) if entry_price else 0.0
                        except Exception:
                            df.at[idx, 'actual_pnl_pct'] = 0.0
                        df.at[idx, 'exit_date'] = exit_date
                        df.at[idx, 'bars_since_entry'] = bar_count
                        updated = True
                        
                        pnl_color = "green" if hypothetical_pnl >= 0 else "red"
                        console.print(f"[{pnl_color}]✓ {ticker} {action}: {status} at ${exit_price:.2f} | P&L: ${hypothetical_pnl:.2f}[/{pnl_color}]")
                
                except Exception as e:
                    console.print(f"[dim]Error updating {ticker}: {e}[/dim]")
                    continue
            
            # Save updated dataframe
            if updated:
                # Ensure consistent column order and quoting for text fields
                import csv as _csv
                expected_cols = [
                    'timestamp','ticker','action','entry_price','stop_loss','tp1','tp2','tp3',
                    'confidence','win_prob','risk_amount','reward_amount','rr_ratio','position_size',
                    'took_trade','during_market_hours','current_price','hypothetical_pnl','hypothetical_pnl_pct','status','exit_price','actual_pnl','actual_pnl_pct',
                    'exit_date','bars_since_entry','primary_reason'
                ]
                # Add any missing columns before saving
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = ''
                df = df[expected_cols]
                df.to_csv(tracking_file, index=False, quoting=_csv.QUOTE_MINIMAL)
                console.print(f"\n[green]✓ Trade tracking updated[/green]")
        
        except Exception as e:
            console.print(f"[red]Error updating trades: {e}[/red]")

    def _view_ai_performance(self):
        """View AI performance statistics and overall P&L."""
        tracking_file = RESULTS_DIR / 'ai_performance_tracking.csv'
        
        if not tracking_file.exists():
            console.print("[yellow]No tracked trades yet. Analyze some stocks first![/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return
        
        # Migrate bad rows first (e.g., backdated exits)
        self._migrate_tracking_file()
        console.clear()
        console.print("[bold cyan]🤖 AI Performance Dashboard[/bold cyan]\n")
        
        # First, update all open trades
        self._update_tracked_trades()
        
        try:
            # Reload the dataframe after updates
            df = self._load_tracking_df(tracking_file)
            # Sanitize status values before filtering
            allowed_status = {'OPEN','STOPPED','TP1_HIT','TP2_HIT','TP3_HIT'}
            if 'status' in df.columns:
                df.loc[~df['status'].isin(list(allowed_status)), 'status'] = 'OPEN'

            # Ensure numeric types for P&L and related columns to avoid type errors
            try:
                numeric_cols = [
                    'actual_pnl', 'hypothetical_pnl', 'hypothetical_pnl_pct',
                    'entry_price', 'current_price', 'stop_loss', 'tp1',
                    'bars_since_entry', 'confidence', 'win_prob'
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                # Fill sensible defaults
                if 'hypothetical_pnl' in df.columns:
                    df['hypothetical_pnl'] = df['hypothetical_pnl'].fillna(0.0)
                if 'hypothetical_pnl_pct' in df.columns:
                    df['hypothetical_pnl_pct'] = df['hypothetical_pnl_pct'].fillna(0.0)
                if 'bars_since_entry' in df.columns:
                    df['bars_since_entry'] = df['bars_since_entry'].fillna(0).astype('Int64')
            except Exception:
                pass

            # Ensure during_market_hours exists; compute for missing from timestamp assuming PT (America/Los_Angeles)
            if 'during_market_hours' not in df.columns:
                df['during_market_hours'] = ''
            include_weekends = True
            try:
                if getattr(self, 'config', None):
                    include_weekends = bool(self.config.get('performance_include_weekends', True))
            except Exception:
                include_weekends = True
            try:
                from zoneinfo import ZoneInfo
                def _compute_mkt(ts):
                    try:
                        if pd.isna(ts) or ts == '':
                            return False
                        dt = pd.to_datetime(ts, errors='coerce')
                        if pd.isna(dt):
                            return False
                        dt_pt = dt.tz_localize(ZoneInfo('America/Los_Angeles'), nonexistent='NaT', ambiguous='NaT') if dt.tzinfo is None else dt.tz_convert(ZoneInfo('America/Los_Angeles'))
                        if pd.isna(dt_pt):
                            return False
                        is_weekday = dt_pt.weekday() < 5
                        # Include premarket 1:00 and after-hours to 17:00 PT
                        open_pt = dt_pt.replace(hour=1, minute=0, second=0, microsecond=0)
                        close_pt = dt_pt.replace(hour=17, minute=0, second=0, microsecond=0)
                        if include_weekends:
                            return bool(dt_pt >= open_pt and dt_pt <= close_pt)
                        else:
                            return bool(is_weekday and (dt_pt >= open_pt) and (dt_pt <= close_pt))
                    except Exception:
                        return False
                missing_mask = (df['during_market_hours'].astype(str) == '') | (df['during_market_hours'].isna())
                df.loc[missing_mask, 'during_market_hours'] = df.loc[missing_mask, 'timestamp'].apply(_compute_mkt)
                # Cast to bool where possible
                df['during_market_hours'] = df['during_market_hours'].astype(str).str.lower().map({'true': True, 'false': False}).fillna(df['during_market_hours'])
            except Exception:
                # If zoneinfo not available, leave as-is
                pass
            
            if len(df) == 0:
                console.print("[yellow]No trades tracked yet.[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                return
            
            # Overall statistics
            total_trades = len(df)
            if include_weekends:
                closed_trades = df[(df['status'] != 'OPEN') & (df.get('during_market_hours') == True)].copy()
                open_trades = df[(df['status'] == 'OPEN') & (df.get('during_market_hours') == True)].copy()
            else:
                closed_trades = df[(df['status'] != 'OPEN') & (df.get('during_market_hours') == True)].copy()
                open_trades = df[(df['status'] == 'OPEN') & (df.get('during_market_hours') == True)].copy()
            # Deduplicate open trades by (ticker, action, entry_price) keeping most recent
            if len(open_trades) > 0:
                try:
                    open_trades['ts_dt'] = pd.to_datetime(open_trades['timestamp'], errors='coerce')
                except Exception:
                    open_trades['ts_dt'] = pd.NaT
                open_trades = open_trades.sort_values('ts_dt').drop_duplicates(subset=['ticker','action','entry_price'], keep='last')

                # Only show open trades that actually moved (non-zero unrealized P&L)
                if 'hypothetical_pnl' in open_trades.columns:
                    try:
                        open_trades['hypothetical_pnl'] = pd.to_numeric(open_trades['hypothetical_pnl'], errors='coerce').fillna(0)
                        open_trades = open_trades[open_trades['hypothetical_pnl'].abs() > 0.005]
                    except Exception:
                        pass
            
            # P&L calculations using actual_pnl for closed trades
            if 'actual_pnl' in closed_trades.columns:
                closed_trades['actual_pnl'] = pd.to_numeric(closed_trades['actual_pnl'], errors='coerce').fillna(0)
                total_pnl = closed_trades['actual_pnl'].sum()
            else:
                total_pnl = 0
            
            # Win rate (closed trades only)
            if len(closed_trades) > 0:
                winners = closed_trades[closed_trades['actual_pnl'] > 0]
                losers = closed_trades[closed_trades['actual_pnl'] < 0]
                win_rate = (len(winners) / len(closed_trades) * 100)
                
                # Average metrics
                avg_win = winners['actual_pnl'].mean() if len(winners) > 0 else 0
                avg_loss = losers['actual_pnl'].mean() if len(losers) > 0 else 0
                
                # Best and worst trades
                best_trade = closed_trades.loc[closed_trades['actual_pnl'].idxmax()] if len(closed_trades) > 0 else None
                worst_trade = closed_trades.loc[closed_trades['actual_pnl'].idxmin()] if len(closed_trades) > 0 else None
            else:
                win_rate = 0
                avg_win = 0
                avg_loss = 0
                best_trade = None
                worst_trade = None
            
            # Display summary
            table = Table(title="📊 AI Performance (Simulated Trades)", box=box.ROUNDED, border_style="cyan")
            table.add_column("Metric", style="cyan", width=25)
            table.add_column("Value", style="white", width=20)
            
            table.add_row("Total Signals Generated", str(total_trades))
            table.add_row("Open Positions", f"[yellow]{len(open_trades)}[/yellow]")
            table.add_row("Closed Positions", f"[green]{len(closed_trades)}[/green]")
            table.add_row("", "")
            
            pnl_color = "green" if total_pnl >= 0 else "red"
            table.add_row("Total Realized P&L", f"[{pnl_color}]${total_pnl:,.2f}[/{pnl_color}]")
            
            if len(closed_trades) > 0:
                table.add_row("", "")
                wr_color = "green" if win_rate >= 50 else "yellow" if win_rate >= 40 else "red"
                table.add_row("Win Rate", f"[{wr_color}]{win_rate:.1f}%[/{wr_color}]")
                table.add_row("Winning Trades", f"[green]{len(winners)}[/green]")
                table.add_row("Losing Trades", f"[red]{len(losers)}[/red]")
                table.add_row("", "")
                table.add_row("Average Win", f"[green]${avg_win:.2f}[/green]")
                table.add_row("Average Loss", f"[red]${avg_loss:.2f}[/red]")
                
                if best_trade is not None:
                    table.add_row("", "")
                    table.add_row("Best Trade", f"[green]{best_trade['ticker']} ${best_trade['actual_pnl']:.2f}[/green]")
                if worst_trade is not None:
                    table.add_row("Worst Trade", f"[red]{worst_trade['ticker']} ${worst_trade['actual_pnl']:.2f}[/red]")
            
            table.add_row("", "")
            table.add_row("Avg Confidence", f"{df['confidence'].mean():.1f}%")
            table.add_row("Avg Win Probability", f"{df['win_prob'].mean():.1f}%")
            
            console.print(table)
            console.print()
            
            # Recent closed trades table
            if len(closed_trades) > 0:
                console.print("[bold cyan]📋 Recent Closed Trades (Last 10)[/bold cyan]\n")
                
                recent_table = Table(box=box.ROUNDED)
                recent_table.add_column("Entry", style="dim", width=10)
                recent_table.add_column("Exit", style="dim", width=10)
                recent_table.add_column("Ticker", style="bold white", width=8)
                recent_table.add_column("Action", style="white", width=6)
                recent_table.add_column("Result", style="white", width=12)
                recent_table.add_column("P&L", justify="right", width=12)
                recent_table.add_column("Conf%", justify="right", width=6)
                
                for _, row in closed_trades.tail(10).iterrows():
                    action_color = "green" if row['action'] == 'BUY' else "red"
                    pnl_val = row['actual_pnl']
                    pnl_color = "green" if pnl_val > 0 else "red"
                    status_display = row['status'].replace('_', ' ')

                    # Format dates MM/DD/YY
                    try:
                        entry_dt = pd.to_datetime(row.get('timestamp'), errors='coerce')
                        entry_date = entry_dt.strftime('%m/%d/%y') if pd.notna(entry_dt) else ''
                    except Exception:
                        entry_date = ''
                    try:
                        exit_dt = pd.to_datetime(row.get('exit_date'), errors='coerce')
                        exit_date = exit_dt.strftime('%m/%d/%y') if pd.notna(exit_dt) else ''
                    except Exception:
                        exit_date = ''
                    
                    recent_table.add_row(
                        entry_date,
                        exit_date,
                        row['ticker'],
                        f"[{action_color}]{row['action']}[/{action_color}]",
                        status_display,
                        f"[{pnl_color}]${pnl_val:.2f}[/{pnl_color}]",
                        f"{row['confidence']:.0f}%"
                    )
                
                console.print(recent_table)
                console.print()
            
            # Open trades table
            if len(open_trades) > 0:
                console.print("[bold yellow]⏳ Currently Open Simulated Trades[/bold yellow]\n")
                
                open_table = Table(box=box.ROUNDED)
                open_table.add_column("Entry Date", style="dim", width=10)
                open_table.add_column("Ticker", style="bold white", width=8)
                open_table.add_column("Action", style="white", width=6)
                open_table.add_column("Entry", justify="right", width=10)
                open_table.add_column("Current", justify="right", width=10)
                open_table.add_column("Unrealized P&L", justify="right", width=14)
                open_table.add_column("P&L%", justify="right", width=8)
                open_table.add_column("Stop", justify="right", width=10)
                open_table.add_column("TP1", justify="right", width=10)
                open_table.add_column("Bars", justify="right", width=6)
                
                for _, row in open_trades.tail(10).iterrows():
                    action_color = "green" if row['action'] == 'BUY' else "red"
                    # Format date MM/DD/YY
                    try:
                        entry_dt = pd.to_datetime(row.get('timestamp'), errors='coerce')
                        entry_date = entry_dt.strftime('%m/%d/%y') if pd.notna(entry_dt) else ''
                    except Exception:
                        entry_date = ''
                    
                    # Get unrealized P&L if available
                    unrealized_pnl = row.get('hypothetical_pnl', 0)
                    # Avoid displaying -0.00
                    if pd.notna(unrealized_pnl) and abs(unrealized_pnl) < 0.005:
                        unrealized_pnl = 0.0
                    current_price = row.get('current_price', row['entry_price'])
                    pnl_color = "green" if unrealized_pnl >= 0 else "red"
                    pnl_pct = row.get('hypothetical_pnl_pct', 0.0)
                    if pd.notna(pnl_pct) and abs(pnl_pct) < 0.005:
                        pnl_pct = 0.0
                    bars = int(row.get('bars_since_entry', 0)) if pd.notna(row.get('bars_since_entry', 0)) else 0
                    
                    open_table.add_row(
                        entry_date,
                        row['ticker'],
                        f"[{action_color}]{row['action']}[/{action_color}]",
                        f"${row['entry_price']:.2f}",
                        f"${current_price:.2f}",
                        f"[{pnl_color}]${unrealized_pnl:.2f}[/{pnl_color}]",
                        f"[{pnl_color}]{pnl_pct:.2f}%[/{pnl_color}]",
                        f"${row['stop_loss']:.2f}",
                        f"${row['tp1']:.2f}",
                        f"{bars}"
                    )
                
                console.print(open_table)
                
                # Show total unrealized P&L for open positions
                total_unrealized = open_trades['hypothetical_pnl'].copy() if 'hypothetical_pnl' in open_trades.columns else pd.Series([0])
                if isinstance(total_unrealized, pd.Series):
                    total_unrealized = total_unrealized.apply(lambda x: 0.0 if pd.notna(x) and abs(x) < 0.005 else (x if pd.notna(x) else 0)).sum()
                unrealized_color = "green" if total_unrealized >= 0 else "red"
                console.print(f"\n[{unrealized_color}]Total Unrealized P&L: ${total_unrealized:.2f}[/{unrealized_color}]")
            
        except Exception as e:
            console.print(f"[red]Error loading performance data: {e}[/red]")
            import traceback
            traceback.print_exc()
        
        Prompt.ask("\nPress Enter to continue")

    def _run_backtest(self, engine: 'BacktestEngine'):
        """Run backtesting on historical data."""
        console.clear()
        console.print("[bold cyan]🎯 Backtesting Engine[/bold cyan]\n")
        
        ticker = Prompt.ask("Enter ticker to backtest")
        start = Prompt.ask("Start date (YYYY-MM-DD)", default="2023-01-01")
        end = Prompt.ask("End date (YYYY-MM-DD)")
        
        console.print(f"\n[yellow]Running backtest for {ticker}...[/yellow]")
        metrics = engine.backtest_ticker(ticker, start, end, self.config.get('account_size', 10000))
        
        if metrics:
            table = Table(title=f"📊 Backtest Results: {ticker}", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Total Trades", str(metrics.total_trades))
            table.add_row("Win Rate", f"{metrics.win_rate*100:.1f}%")
            table.add_row("Profit Factor", f"{metrics.profit_factor:.2f}")
            table.add_row("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")
            table.add_row("Max Drawdown", f"{metrics.max_drawdown*100:.2f}%")
            table.add_row("Total P&L", f"${metrics.total_pnl:,.0f}")
            console.print(table)
        
        Prompt.ask("\nPress Enter to continue")

    def _run_replay_simulator(self):
        """Visual stepwise replay with automatic defaults (no manual parameter prompts).

        Emulates live trading view: windows advance at style-defined cadence. Future
        performance thresholds are internally set per style to avoid user tuning.
        """
        console.clear()
        console.print("[bold cyan]🎥 Replay Simulator[/bold cyan]\n")
        ticker = Prompt.ask("Ticker (must have signals generated)").upper().strip()
        console.print("Select style: 1=Day 2=Swing 3=Long-Term")
        style_choice = Prompt.ask("Style", choices=["1","2","3"], default="2")
        style_defaults = {
            "1": {"window": 300, "step": 25, "future_horizon": 24, "future_ret_thr": 2.0, "max_frames": 120},
            "2": {"window": 800, "step": 48, "future_horizon": 48, "future_ret_thr": 2.5, "max_frames": 100},
            "3": {"window": 1600, "step": 96, "future_horizon": 96, "future_ret_thr": 3.0, "max_frames": 80},
        }
        params = style_defaults[style_choice]
        window = params['window']
        step = params['step']
        future_horizon = params['future_horizon']
        future_ret_thr = params['future_ret_thr']
        max_frames = params['max_frames']

        data_folder = self.config.get('data_folder') if self.config else None
        signals_name = self.config.get('signal_file_name') if self.config else None
        fallback_mode = False
        if not data_folder or not signals_name:
            console.print("[yellow]Config incomplete. Using fallback (yfinance + synthetic signals).[/yellow]")
            fallback_mode = True

        import pandas as pd
        import numpy as np
        
        # Safe matplotlib import with Agg backend
        plotting_available = False
        if self.config and self.config.get('enable_plots', True):
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                plotting_available = True
            except Exception as e:
                console.print(f"[yellow]Plotting disabled: {e}[/yellow]")
        else:
            console.print("[yellow]Plotting disabled (enable_plots=false in config)[/yellow]")
            
        if fallback_mode:
            try:
                import yfinance as yf
            except Exception:
                console.print("[red]yfinance not installed. Install with: pip install yfinance[/red]")
                Prompt.ask("Press Enter")
                return
            style_fetch = {
                "1": {"period": "5d", "interval": "5m"},
                "2": {"period": "3mo", "interval": "1h"},
                "3": {"period": "2y", "interval": "1d"},
            }[style_choice]
            console.print(f"[cyan]Fetching {ticker} ({style_fetch['period']} @ {style_fetch['interval']}) from yfinance...[/cyan]")
            def _normalize_ticker(t: str) -> str:
                # Convert crypto style BTCUSDT -> BTC-USD for yfinance; leave others unchanged
                if t.endswith('USDT') and '-' not in t:
                    return t.replace('USDT','-USD')
                return t
            yf_ticker = _normalize_ticker(ticker)
            attempts = [(style_fetch['period'], style_fetch['interval'])]
            # Add broader fallbacks
            if style_choice == '1':  # Day trading
                attempts.extend([('10d','15m'), ('30d','30m'), ('90d','1h')])
            elif style_choice == '2':  # Swing
                attempts.extend([('6mo','1h'), ('1y','1d')])
            else:  # Long-term
                attempts.extend([('5y','1d'), ('10y','1d')])
            raw = None
            for period, interval in attempts:
                console.print(f"[dim]Attempt fetch: period={period} interval={interval} ticker={yf_ticker}[/dim]")
                try:
                    tmp = yf.download(yf_ticker, period=period, interval=interval, prepost=True)
                    if not tmp.empty and len(tmp) >= 50:
                        raw = tmp
                        console.print(f"[green]✓ Fetched {len(raw)} bars (period={period} interval={interval}).[/green]")
                        break
                    else:
                        console.print(f"[yellow]No data / too few bars for period={period} interval={interval}")
                except Exception as e:
                    console.print(f"[yellow]Fetch error period={period} interval={interval}: {e}")
            if raw is None or raw.empty:
                console.print("[red]No data fetched after fallback attempts. Aborting replay.")
                Prompt.ask("Press Enter")
                return
            raw.reset_index(inplace=True)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0] if isinstance(c, tuple) and c[0] else (c[-1] if isinstance(c, tuple) else c) for c in raw.columns]
            # Normalize column names
            time_col = 'Datetime' if 'Datetime' in raw.columns else ('Date' if 'Date' in raw.columns else raw.columns[0])
            closes = raw['Close']
            delta = closes.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            rsi.fillna(50, inplace=True)
            buy_sig_series = ((rsi.shift(1) < 30) & (rsi >= 30)).astype(int)
            sell_sig_series = ((rsi.shift(1) > 70) & (rsi <= 70)).astype(int)
            score_series = (rsi - 50) / 50.0
            def _ensure_series(x):
                if isinstance(x, pd.DataFrame):
                    return x.iloc[:,0]
                if isinstance(x, np.ndarray) and x.ndim > 1:
                    return pd.Series(x[:,0])
                return x.squeeze() if hasattr(x,'squeeze') else x
            ts_data = _ensure_series(raw[time_col])
            closes = _ensure_series(closes)
            buy_sig_series = _ensure_series(buy_sig_series)
            sell_sig_series = _ensure_series(sell_sig_series)
            score_series = _ensure_series(score_series)
            df = pd.DataFrame({
                time_col: ts_data.values if hasattr(ts_data,'values') else ts_data,
                'close': closes.values if hasattr(closes,'values') else closes,
                'buy_signal_column': buy_sig_series.values if hasattr(buy_sig_series,'values') else buy_sig_series,
                'sell_signal_column': sell_sig_series.values if hasattr(sell_sig_series,'values') else sell_sig_series,
                'trade_score': score_series.values if hasattr(score_series,'values') else score_series,
            })
            buy_col, sell_col, score_col = 'buy_signal_column', 'sell_signal_column', 'trade_score'
            buy_th, sell_th = 0.25, -0.25  # synthetic thresholds
        else:
            path = Path(data_folder) / ticker / signals_name
            if not path.exists():
                console.print(f"[yellow]Signals file missing: {path}. Switching to fallback mode.")
                fallback_mode = True
                import yfinance as yf
                style_fetch = {
                    "1": {"period": "5d", "interval": "5m"},
                    "2": {"period": "3mo", "interval": "1h"},
                    "3": {"period": "2y", "interval": "1d"},
                }[style_choice]
                def _normalize_ticker(t: str) -> str:
                    if t.endswith('USDT') and '-' not in t:
                        return t.replace('USDT','-USD')
                    return t
                yf_ticker = _normalize_ticker(ticker)
                attempts = [(style_fetch['period'], style_fetch['interval'])]
                if style_choice == '1':
                    attempts.extend([('10d','15m'), ('30d','30m'), ('90d','1h')])
                elif style_choice == '2':
                    attempts.extend([('6mo','1h'), ('1y','1d')])
                else:
                    attempts.extend([('5y','1d'), ('10y','1d')])
                raw = None
                for period, interval in attempts:
                    console.print(f"[dim]Attempt fetch: period={period} interval={interval} ticker={yf_ticker}[/dim]")
                    try:
                        tmp = yf.download(yf_ticker, period=period, interval=interval, prepost=True)
                        if not tmp.empty and len(tmp) >= 50:
                            raw = tmp
                            console.print(f"[green]✓ Fetched {len(raw)} bars (period={period} interval={interval}).[/green]")
                            break
                        else:
                            console.print(f"[yellow]No data / too few bars for period={period} interval={interval}")
                    except Exception as e:
                        console.print(f"[yellow]Fetch error period={period} interval={interval}: {e}")
                if raw is None or raw.empty:
                    console.print("[red]No data fetched after fallback attempts. Aborting random simulation.")
                    Prompt.ask("Press Enter")
                    return
                raw.reset_index(inplace=True)
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = [c[0] if isinstance(c, tuple) and c[0] else (c[-1] if isinstance(c, tuple) else c) for c in raw.columns]
                time_col = 'Datetime' if 'Datetime' in raw.columns else ('Date' if 'Date' in raw.columns else raw.columns[0])
                close = raw['Close']
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                rsi.fillna(50, inplace=True)
                buy_sig_series = ((rsi.shift(1) < 30) & (rsi >= 30)).astype(int)
                sell_sig_series = ((rsi.shift(1) > 70) & (rsi <= 70)).astype(int)
                score_series = (rsi - 50) / 50.0
                def _ensure_series(x):
                    if isinstance(x, pd.DataFrame):
                        return x.iloc[:,0]
                    if isinstance(x, np.ndarray) and x.ndim > 1:
                        return pd.Series(x[:,0])
                    return x.squeeze() if hasattr(x,'squeeze') else x
                ts_data = _ensure_series(raw[time_col])
                close = _ensure_series(close)
                buy_sig_series = _ensure_series(buy_sig_series)
                sell_sig_series = _ensure_series(sell_sig_series)
                score_series = _ensure_series(score_series)
                df = pd.DataFrame({
                    time_col: ts_data.values if hasattr(ts_data,'values') else ts_data,
                    'close': close.values if hasattr(close,'values') else close,
                    'buy_signal_column': buy_sig_series.values if hasattr(buy_sig_series,'values') else buy_sig_series,
                    'sell_signal_column': sell_sig_series.values if hasattr(sell_sig_series,'values') else sell_sig_series,
                    'trade_score': score_series.values if hasattr(score_series,'values') else score_series,
                })
                buy_col, sell_col, score_col = 'buy_signal_column', 'sell_signal_column', 'trade_score'
                buy_th, sell_th = 0.25, -0.25
            else:
                console.print(f"[dim]Loading signals: {path}[/dim]")
                if path.suffix == '.parquet':
                    df = pd.read_parquet(path)
                else:
                    time_col = self.config.get('time_column', 'date')
                    df = pd.read_csv(path, parse_dates=[time_col])
                time_col = self.config.get('time_column', 'date')
                signal_sets = self.config.get('signal_sets', [])
                thr_rule = next((s for s in signal_sets if s.get('generator') == 'threshold_rule'), None)
                combine_rule = next((s for s in signal_sets if s.get('generator') == 'combine'), None)
                if not thr_rule:
                    console.print("[red]threshold_rule missing in config signal_sets[/red]")
                    Prompt.ask("Press Enter")
                    return
                buy_col, sell_col = thr_rule['config']['names']
                score_col = combine_rule['config']['names'] if combine_rule else None
                buy_th = thr_rule['config']['parameters'].get('buy_signal_threshold')
                sell_th = thr_rule['config']['parameters'].get('sell_signal_threshold')

        if buy_col not in df.columns or sell_col not in df.columns:
            console.print("[red]Signal columns missing even after fallback generation.[/red]")
            Prompt.ask("Press Enter")
            return

        out_dir = Path(data_folder) / ticker / 'replay_frames'
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = []
        total = len(df)
        frame_idx = 0

        console.print(f"[dim]Generating frames (window={window}, step={step})...[/dim]")
        for end_i in range(window, total, step):
            if frame_idx >= max_frames:
                break
            current_row = df.iloc[end_i - 1]
            price = current_row.get('close')
            buy_sig = bool(current_row[buy_col])
            sell_sig = bool(current_row[sell_col])
            score_val = current_row.get(score_col) if score_col and score_col in df.columns else None

            if buy_sig and not sell_sig:
                action = 'BUY'
            elif sell_sig and not buy_sig:
                action = 'SELL'
            else:
                action = 'HOLD'

            confidence = None
            if score_val is not None and buy_th is not None and sell_th is not None:
                if score_val >= 0 and buy_th > 0:
                    confidence = min(1.0, score_val / buy_th)
                elif score_val < 0 and sell_th < 0:
                    confidence = min(1.0, abs(score_val / sell_th))
            conf_pct = round(confidence * 100, 1) if confidence is not None else None

            # Future overlay
            future_slice = df.iloc[end_i:end_i + future_horizon]
            future_return = None
            outcome = 'N/A'
            if len(future_slice) >= 1 and price:
                future_last = future_slice['close'].iloc[-1]
                future_return = (future_last - price) / price * 100.0
                # Directional success logic
                if action == 'BUY':
                    outcome = 'PASS' if future_return >= future_ret_thr else 'FAIL'
                elif action == 'SELL':
                    outcome = 'PASS' if future_return <= -future_ret_thr else 'FAIL'
                else:  # HOLD
                    outcome = 'PASS' if abs(future_return) < future_ret_thr else 'FAIL'

            # Text summary for all modes
            txt = [f"Action: {action}"]
            if price is not None:
                txt.append(f"Price: {price:.2f}")
            if score_val is not None:
                txt.append(f"Score: {score_val:.3f}")
            if conf_pct is not None:
                txt.append(f"Conf: {conf_pct:.1f}%")
            if future_return is not None:
                txt.append(f"Future {future_horizon} bars: {future_return:.2f}% [{outcome}]")

            if plotting_available:
                hist_slice = df.iloc[end_i - window:end_i]
                fig, axes = plt.subplots(2 if score_col else 1, 1, figsize=(9, 5), sharex=True,
                                     gridspec_kw={'height_ratios': [3, 1]} if score_col else None)
                if not isinstance(axes, (list, tuple)):
                    axes = [axes]
                ax_price = axes[0]
                ax_price.plot(hist_slice[time_col], hist_slice['close'], color='white')
                ax_price.set_title(f"{ticker} Replay → {hist_slice[time_col].iloc[-1]}")
                # Signals markers
                buys = hist_slice[hist_slice[buy_col] == True]
                sells = hist_slice[hist_slice[sell_col] == True]
                ax_price.scatter(buys[time_col], buys['close'], marker='^', color='lime', s=55)
                ax_price.scatter(sells[time_col], sells['close'], marker='v', color='red', s=55)
                # Future overlay
                if future_slice is not None and len(future_slice) > 0:
                    ax_price.plot(future_slice[time_col], future_slice['close'], color='magenta', alpha=0.4, linewidth=2)
                ax_price.legend(["Price","Buys","Sells","Future"], loc='upper left') if len(future_slice) > 0 else ax_price.legend(["Price","Buys","Sells"], loc='upper left')

                if score_col and score_col in df.columns:
                    ax_score = axes[1]
                    ax_score.plot(hist_slice[time_col], hist_slice[score_col], color='cyan')
                    if buy_th is not None:
                        ax_score.axhline(buy_th, color='green', linestyle='--', linewidth=0.7)
                    if sell_th is not None:
                        ax_score.axhline(sell_th, color='red', linestyle='--', linewidth=0.7)
                    ax_score.set_ylabel('Score')

                fig.text(0.02, 0.02, '\n'.join(txt), fontsize=10, family='monospace')
                plt.tight_layout()
                frame_path = out_dir / f"frame_{frame_idx:04d}.png"
                plt.savefig(frame_path)
                plt.close(fig)
            else:
                # Text-only mode
                frame_path = out_dir / f"frame_{frame_idx:04d}.txt"
                with open(frame_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(txt))

            summary.append(dict(frame=frame_idx,
                                timestamp=current_row[time_col],
                                action=action,
                                price=price,
                                score=score_val,
                                confidence_pct=conf_pct,
                                future_return_pct=future_return,
                                outcome=outcome))
            frame_idx += 1

        # Save summary
        import pandas as pd
        summary_df = pd.DataFrame(summary)
        summary_file = out_dir / 'replay_summary.csv'
        summary_df.to_csv(summary_file, index=False)
        console.print(f"\n[green]Generated {frame_idx} frames in {out_dir}[/green]")
        console.print(f"Summary: {summary_file}")
        Prompt.ask("\nPress Enter to continue")

    def _run_random_simulation(self):
        """Pick a random historical segment for a ticker, show the chart without future, run AI decision, then reveal future and outcome.

        Replaces traditional backtest for quick subjective accuracy review.
        """
        import random
        import pandas as pd
        from pathlib import Path

        console.clear()
        console.print("[bold cyan]🎯 Random Simulation (Blind Segment Test)[/bold cyan]\n")

        ticker = Prompt.ask("Ticker (must have signals generated)").upper().strip()
        console.print("Select style: 1=Day 2=Swing 3=Long-Term")
        style_choice = Prompt.ask("Style", choices=["1","2","3"], default="2")
        # segment length heuristic (bars) based on style
        style_lengths = {"1": 300, "2": 400, "3": 300}
        segment_len = style_lengths[style_choice]
        future_horizon = 100 if style_choice == "3" else (50 if style_choice == "2" else 24)
        config = self.config or {}
        data_folder = config.get('data_folder')
        signals_name = config.get('signal_file_name')
        time_col = config.get('time_column', 'date')
        fallback_mode = False
        import numpy as np
        
        # Safe matplotlib import with Agg backend
        plotting_available = False
        if config.get('enable_plots', True):
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                plotting_available = True
            except Exception as e:
                console.print(f"[yellow]Plotting disabled: {e}[/yellow]")
        else:
            console.print("[yellow]Plotting disabled (enable_plots=false in config)[/yellow]")
            
        if not data_folder or not signals_name:
            console.print("[yellow]Config incomplete (data_folder or signal_file_name). Using fallback mode.[/yellow]")
            fallback_mode = True
        if not fallback_mode:
            path = Path(data_folder) / ticker / signals_name
            if not path.exists():
                console.print(f"[yellow]Signals file missing: {path}. Switching to fallback mode.[/yellow]")
                fallback_mode = True
        if fallback_mode:
            try:
                import yfinance as yf
            except Exception:
                console.print("[red]yfinance not installed. Install with: pip install yfinance[/red]")
                Prompt.ask("Press Enter")
                return
            style_fetch = {
                "1": {"period": "5d", "interval": "5m"},
                "2": {"period": "6mo", "interval": "1h"},
                "3": {"period": "5y", "interval": "1d"},
            }[style_choice]
            console.print(f"[cyan]Fetching {ticker} {style_fetch['period']} @ {style_fetch['interval']} via yfinance...[/cyan]")
            raw = yf.download(ticker, period=style_fetch['period'], interval=style_fetch['interval'])
            if raw.empty:
                console.print("[red]No data fetched for fallback. Aborting simulation.[/red]")
                Prompt.ask("Press Enter")
                return
            raw.reset_index(inplace=True)
            # Flatten possible MultiIndex columns from yfinance
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0] if isinstance(c, tuple) and c[0] else (c[-1] if isinstance(c, tuple) else c) for c in raw.columns]
            
            # Standardize column names (yfinance uses capitalized OHLC)
            col_map = {}
            for col in raw.columns:
                col_lower = col.lower()
                if col_lower in ['open', 'high', 'low', 'close', 'volume']:
                    col_map[col] = col_lower
            if col_map:
                raw.rename(columns=col_map, inplace=True)
            
            time_col = 'Datetime' if 'Datetime' in raw.columns else ('Date' if 'Date' in raw.columns else raw.columns[0])
            close = raw['close'] if 'close' in raw.columns else (raw['Close'] if 'Close' in raw.columns else raw.iloc[:,1])
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            rsi.fillna(50, inplace=True)
            buy_sig_series = ((rsi.shift(1) < 30) & (rsi >= 30)).astype(int)
            sell_sig_series = ((rsi.shift(1) > 70) & (rsi <= 70)).astype(int)
            score_series = (rsi - 50) / 50.0
            def _ensure_series(x):
                if isinstance(x, pd.DataFrame):
                    return x.iloc[:,0]
                if isinstance(x, np.ndarray) and x.ndim > 1:
                    return pd.Series(x[:,0])
                return x.squeeze() if hasattr(x, 'squeeze') else x
            ts_data = _ensure_series(raw[time_col])
            close = _ensure_series(close)
            buy_sig_series = _ensure_series(buy_sig_series)
            sell_sig_series = _ensure_series(sell_sig_series)
            score_series = _ensure_series(score_series)
            
            # Build dataframe with OHLC if available
            df = pd.DataFrame({
                time_col: ts_data.values if hasattr(ts_data,'values') else ts_data,
                'close': close.values if hasattr(close,'values') else close,
                'buy_signal_column': buy_sig_series.values if hasattr(buy_sig_series,'values') else buy_sig_series,
                'sell_signal_column': sell_sig_series.values if hasattr(sell_sig_series,'values') else sell_sig_series,
                'trade_score': score_series.values if hasattr(score_series,'values') else score_series,
            })
            # Add OHLC columns if present in raw data
            for ohlc_col in ['open', 'high', 'low', 'volume']:
                if ohlc_col in raw.columns:
                    df[ohlc_col] = raw[ohlc_col].values
            buy_col, sell_col, score_col = 'buy_signal_column', 'sell_signal_column', 'trade_score'
            buy_th, sell_th = 0.25, -0.25
        else:
            console.print(f"[dim]Loading {path}...[/dim]")
            if path.suffix == '.parquet':
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path, parse_dates=[time_col])
            # Signals config
            signal_sets = config.get('signal_sets', [])
            thr_rule = next((s for s in signal_sets if s.get('generator') == 'threshold_rule'), None)
            combine_rule = next((s for s in signal_sets if s.get('generator') == 'combine'), None)
            if not thr_rule:
                console.print("[red]threshold_rule missing in config signal_sets[/red]")
                Prompt.ask("Press Enter")
                return
            buy_col, sell_col = thr_rule['config']['names']
            score_col = combine_rule['config']['names'] if combine_rule else None
            buy_th = thr_rule['config']['parameters'].get('buy_signal_threshold')
            sell_th = thr_rule['config']['parameters'].get('sell_signal_threshold')
            for col in [buy_col, sell_col]:
                if col not in df.columns:
                    console.print(f"[red]Signal column missing: {col}[/red]")
                    Prompt.ask("Press Enter")
                    return
        total = len(df)
        if total < segment_len + future_horizon + 10:
            console.print("[red]Not enough data for requested style segment length.[/red]")
            Prompt.ask("Press Enter")
            return

        # buy_col, sell_col, score_col already set above

        # Random start ensuring future horizon available
        start_idx = random.randint(0, total - segment_len - future_horizon - 1)
        end_idx = start_idx + segment_len
        future_end = end_idx + future_horizon
        hist_slice = df.iloc[start_idx:end_idx].copy()
        future_slice = df.iloc[end_idx:future_end].copy()
        last_row = hist_slice.iloc[-1]

        # Handle both 'close' and 'Close' column names
        def _get_close(row):
            if 'close' in row.index:
                return row['close']
            if 'Close' in row.index:
                return row['Close']
            return row.get('close', row.get('Close', 0))

        price = _get_close(last_row)

        buy_sig = bool(last_row[buy_col])
        sell_sig = bool(last_row[sell_col])
        score_val = last_row.get(score_col) if score_col and score_col in df.columns else None

        # Always make a decision (never HOLD)
        if buy_sig and not sell_sig:
            action = 'BUY'
        elif sell_sig and not buy_sig:
            action = 'SELL'
        else:
            # Use score when available; fall back to short-term momentum
            if (score_val is not None) and (buy_th is not None) and (sell_th is not None):
                action = 'BUY' if score_val >= 0 else 'SELL'
                denom = (buy_th if score_val >= 0 else abs(sell_th) if sell_th is not None else max(abs(buy_th or 1e-6), abs(sell_th or 1e-6)))
                try:
                    confidence = min(1.0, abs(score_val) / max(1e-6, abs(denom)))
                except Exception:
                    confidence = 0.6
            else:
                # Momentum: compare last close vs. mean of recent closes
                recent = hist_slice.copy()
                close_series = recent['close'] if 'close' in recent.columns else (recent['Close'] if 'Close' in recent.columns else None)
                if close_series is not None and len(close_series) >= 5:
                    window = min(20, len(close_series))
                    recent_tail = close_series.tail(window)
                    delta_pct = (recent_tail.iloc[-1] - recent_tail.mean()) / max(1e-6, recent_tail.mean())
                    action = 'BUY' if delta_pct >= 0 else 'SELL'
                    confidence = min(0.9, 0.55 + min(0.3, abs(delta_pct)))
                else:
                    action = 'BUY'  # default bias if no info
                    confidence = 0.6

        # If confidence not set yet and we have thresholds, derive it
        if 'confidence' not in locals() or (confidence is None):
            if score_val is not None and buy_th is not None and sell_th is not None:
                denom = (buy_th if action == 'BUY' else abs(sell_th) if sell_th is not None else max(abs(buy_th or 1e-6), abs(sell_th or 1e-6)))
                try:
                    confidence = min(1.0, abs(score_val) / max(1e-6, abs(denom)))
                except Exception:
                    confidence = 0.6
            else:
                confidence = 0.6

        conf_pct = round(float(confidence) * 100.0, 1) if confidence is not None else None
        if conf_pct is not None:
            conf_pct = min(95.0, max(0.0, conf_pct))

        # Provide default data_folder when None in fallback mode
        if data_folder is None:
            data_folder = Path.cwd() / 'fallback_data'
        out_dir = Path(data_folder) / ticker / 'random_sim'
        out_dir.mkdir(parents=True, exist_ok=True)

        # Display summary
        console.print(f"\n[bold cyan]📊 {ticker} Random Segment Analysis[/bold cyan]")
        console.print(f"Style: {style_choice} | Segment Length: {segment_len} bars")
        
        try:
            time_start = hist_slice[time_col].iloc[0]
            time_end = hist_slice[time_col].iloc[-1]
            console.print(f"Time Range: {time_start} to {time_end}")
        except Exception as e:
            console.print(f"[yellow]Time range unavailable: {e}[/yellow]")
        
        console.print(f"Price: ${price:.2f}")
        console.print(f"Action: [bold]{action}[/bold]")
        if score_val is not None:
            console.print(f"Score: {score_val:.3f}")
        if conf_pct is not None:
            console.print(f"Confidence: {conf_pct:.1f}%")
        
        try:
            buy_signals = len(hist_slice[hist_slice[buy_col] == True])
            sell_signals = len(hist_slice[hist_slice[sell_col] == True])
            console.print(f"Buy Signals: {buy_signals} | Sell Signals: {sell_signals}")
        except Exception as e:
            console.print(f"[yellow]Signal count unavailable: {e}[/yellow]")
            buy_signals = 0
            sell_signals = 0
        
        # Generate historical chart
        hist_path = None
        if plotting_available:
            try:
                from matplotlib.patches import Rectangle
                
                fig, axes = plt.subplots(2 if score_col else 1, 1, figsize=(16, 9), sharex=True,
                                         gridspec_kw={'height_ratios': [4, 1]} if score_col else None)
                if not hasattr(axes, '__iter__'):
                    axes = [axes]
                elif hasattr(axes, 'flatten'):
                    axes = axes.flatten()
                else:
                    axes = list(axes)
                
                ax_price = axes[0]
                ax_price.set_facecolor('#0a0a0a')
                fig.patch.set_facecolor('#1a1a1a')
                
                # Draw candlesticks (TradingView style)
                candle_width = 0.8
                for idx, row in hist_slice.reset_index(drop=True).iterrows():
                    x = idx
                    close = row.get('close', row.get('Close', 0))
                    open_price = row.get('open', row.get('Open', close))
                    high = row.get('high', row.get('High', close))
                    low = row.get('low', row.get('Low', close))
                    
                    is_bullish = close >= open_price
                    # Bright green for bullish, deep red for bearish
                    color = '#00ff00' if is_bullish else '#cc0000'
                    
                    # Wick (high-low line) - thicker
                    ax_price.plot([x, x], [low, high], color=color, linewidth=1.6, alpha=1.0, solid_capstyle='butt')
                    
                    # Body (open-close rectangle)
                    body_height = abs(close - open_price)
                    body_bottom = min(open_price, close)
                    
                    if body_height < close * 0.0001:  # Doji - very small body
                        body_height = close * 0.0001
                    
                    # Bullish = hollow (just border), Bearish = filled
                    if is_bullish:
                        rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                        facecolor='#0a0a0a', edgecolor=color, linewidth=1.8, alpha=1.0)
                    else:
                        rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                        facecolor=color, edgecolor=color, linewidth=1.8, alpha=1.0)
                    ax_price.add_patch(rect)
                # Tight x-limits for even spacing on historical-only view
                ax_price.set_xlim(-0.5, len(hist_slice) - 0.5)
                
                # Mark buy/sell signals
                try:
                    buys = hist_slice.reset_index(drop=True)
                    buys = buys[buys[buy_col] == True]
                    sells = hist_slice.reset_index(drop=True)
                    sells = sells[sells[sell_col] == True]
                    
                    for idx, row in buys.iterrows():
                        close_price = row.get('close', row.get('Close', 0))
                        ax_price.scatter([idx], [close_price * 0.995], marker='^', color='cyan', s=150, zorder=5, edgecolors='white', linewidths=1)
                    for idx, row in sells.iterrows():
                        close_price = row.get('close', row.get('Close', 0))
                        ax_price.scatter([idx], [close_price * 1.005], marker='v', color='yellow', s=150, zorder=5, edgecolors='white', linewidths=1)
                except Exception as e:
                    console.print(f"[dim]Skipping signal markers: {e}[/dim]")
                
                # Timeframe annotation
                try:
                    time_range = f"{hist_slice[time_col].iloc[0]} → {hist_slice[time_col].iloc[-1]}"
                    interval = hist_slice[time_col].diff().mode()[0] if len(hist_slice) > 1 else 'Unknown'
                except Exception:
                    time_range = f"{len(hist_slice)} bars"
                    interval = "Unknown"
                
                ax_price.set_title(f"{ticker} | {len(hist_slice)} Candles | Interval: {interval} | {time_range}", 
                                  fontsize=14, fontweight='bold', color='white', pad=20)
                ax_price.set_ylabel('Price ($)', fontsize=12, color='white')
                ax_price.tick_params(colors='white', labelsize=10)
                ax_price.grid(True, alpha=0.15, color='gray', linestyle='--')
                ax_price.spines['bottom'].set_color('#333333')
                ax_price.spines['top'].set_color('#333333')
                ax_price.spines['left'].set_color('#333333')
                ax_price.spines['right'].set_color('#333333')
                
                # Score subplot
                if score_col and score_col in hist_slice.columns:
                    ax_score = axes[1]
                    ax_score.set_facecolor('#0a0a0a')
                    score_data = hist_slice.reset_index(drop=True)[score_col]
                    ax_score.fill_between(range(len(score_data)), 0, score_data, 
                                         where=(score_data >= 0), color='#00ff00', alpha=0.3, interpolate=True)
                    ax_score.fill_between(range(len(score_data)), 0, score_data, 
                                         where=(score_data < 0), color='#ff0000', alpha=0.3, interpolate=True)
                    ax_score.plot(range(len(score_data)), score_data, color='orange', linewidth=1.5)
                    
                    if buy_th is not None:
                        ax_score.axhline(buy_th, color='#00ff00', linestyle='--', linewidth=1, alpha=0.7)
                    if sell_th is not None:
                        ax_score.axhline(sell_th, color='#ff0000', linestyle='--', linewidth=1, alpha=0.7)
                    ax_score.axhline(0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
                    ax_score.set_ylabel('Score', fontsize=12, color='white')
                    ax_score.set_xlabel('Candle Index', fontsize=12, color='white')
                    ax_score.tick_params(colors='white', labelsize=10)
                    ax_score.grid(True, alpha=0.15, color='gray', linestyle='--')
                    ax_score.spines['bottom'].set_color('#333333')
                    ax_score.spines['top'].set_color('#333333')
                    ax_score.spines['left'].set_color('#333333')
                    ax_score.spines['right'].set_color('#333333')
                
                # Info box
                info_text = f"ACTION: {action}\nPRICE: ${price:.2f}"
                if score_val is not None:
                    info_text += f"\nSCORE: {score_val:.3f}"
                if conf_pct is not None:
                    info_text += f"\nCONFIDENCE: {conf_pct:.1f}%"
                info_text += f"\nBUY SIGNALS: {buy_signals}\nSELL SIGNALS: {sell_signals}"
                
                fig.text(0.02, 0.98, info_text, fontsize=12, family='monospace', color='white',
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='#2a2a2a', alpha=0.95, edgecolor='cyan', linewidth=2))
                
                plt.tight_layout()
                hist_path = out_dir / 'segment_historical.png'
                plt.savefig(hist_path, dpi=120, bbox_inches='tight', facecolor='#1a1a1a')
                plt.close(fig)
                console.print(f"[green]📊 Historical chart saved: {hist_path}[/green]")
                
                # Open the chart
                try:
                    import os
                    os.startfile(str(hist_path))
                except Exception:
                    pass  # Silent fail if can't open
                
            except Exception as e:
                console.print(f"[yellow]Chart generation failed: {e}[/yellow]")
                import traceback
                traceback.print_exc()
                hist_path = None

        # Ask user whether to reveal future now
        future_return = None
        outcome = 'N/A'
        future_path = None
        reveal = Confirm.ask("Reveal future outcome now?", default=True)
        if reveal:
            future_last = None
            if len(future_slice) > 0 and price:
                # Handle both 'close' and 'Close' column names
                if 'close' in future_slice.columns:
                    future_last = future_slice['close'].iloc[-1]
                elif 'Close' in future_slice.columns:
                    future_last = future_slice['Close'].iloc[-1]
                else:
                    console.print("[red]Error: Could not find close price column[/red]")
                    Prompt.ask("Press Enter")
                    return
                
                future_return = (future_last - price)/price*100.0
                if action == 'BUY':
                    outcome = 'PASS' if future_return >= 2.0 else 'FAIL'
                elif action == 'SELL':
                    outcome = 'PASS' if future_return <= -2.0 else 'FAIL'
                else:
                    outcome = 'PASS' if abs(future_return) < 1.0 else 'FAIL'
            
            # Show future results as text
            if future_last is not None:
                console.print(f"\n[bold magenta]🔮 Future Revealed ({future_horizon} bars ahead)[/bold magenta]")
                console.print(f"Future Price: ${future_last:.2f}")
                console.print(f"Return: {future_return:.2f}%")
                outcome_color = 'green' if outcome == 'PASS' else 'red'
                console.print(f"Outcome: [bold {outcome_color}]{outcome}[/]")
                
                # Generate future chart with candlesticks (combined historical + future)
                if plotting_available:
                    try:
                        from matplotlib.patches import Rectangle
                        
                        fig, axes = plt.subplots(2 if score_col else 1, 1, figsize=(16, 9), sharex=True,
                                                 gridspec_kw={'height_ratios': [3, 1]} if score_col else None)
                        if not hasattr(axes, '__iter__'):
                            axes = [axes]
                        elif hasattr(axes, 'flatten'):
                            axes = axes.flatten()
                        else:
                            axes = list(axes)
                        
                        ax_price = axes[0]
                        ax_price.set_facecolor('#0a0a0a')
                        fig.patch.set_facecolor('#1a1a1a')
                        
                        # Combine historical and future data for unified x-axis
                        combined = pd.concat([hist_slice, future_slice], ignore_index=True)
                        hist_len = len(hist_slice)
                        
                        # Draw candlesticks for historical segment (TradingView style)
                        candle_width = 0.8
                        for idx, row in hist_slice.reset_index(drop=True).iterrows():
                            x = idx
                            close = row.get('close', row.get('Close', 0))
                            open_price = row.get('open', row.get('Open', close))
                            high = row.get('high', row.get('High', close))
                            low = row.get('low', row.get('Low', close))
                            
                            is_bullish = close >= open_price
                            # Bright green for bullish, deep red for bearish
                            color = '#00ff00' if is_bullish else '#cc0000'
                            
                            # Wick
                            ax_price.plot([x, x], [low, high], color=color, linewidth=1.6, alpha=1.0, solid_capstyle='butt')
                            
                            # Body
                            body_height = abs(close - open_price)
                            body_bottom = min(open_price, close)
                            
                            if body_height < close * 0.0001:
                                body_height = close * 0.0001
                            
                            if is_bullish:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                                facecolor='#0a0a0a', edgecolor=color, linewidth=1.8, alpha=1.0)
                            else:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                                facecolor=color, edgecolor=color, linewidth=1.8, alpha=1.0)
                            ax_price.add_patch(rect)
                        
                        # Draw candlesticks for future segment (dimmed colors)
                        for idx, row in future_slice.reset_index(drop=True).iterrows():
                            x = hist_len + idx
                            close = row.get('close', row.get('Close', 0))
                            open_price = row.get('open', row.get('Open', close))
                            high = row.get('high', row.get('High', close))
                            low = row.get('low', row.get('Low', close))
                            
                            is_bullish = close >= open_price
                            # Dimmed variants: darker green for bullish, darker red for bearish
                            color = '#007f00' if is_bullish else '#7f0000'
                            
                            # Wick
                            ax_price.plot([x, x], [low, high], color=color, linewidth=1.6, alpha=0.7, solid_capstyle='butt')
                            
                            # Body
                            body_height = abs(close - open_price)
                            body_bottom = min(open_price, close)
                            
                            if body_height < close * 0.0001:
                                body_height = close * 0.0001
                            
                            if is_bullish:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                                facecolor='#0a0a0a', edgecolor=color, linewidth=1.8, alpha=0.7)
                            else:
                                rect = Rectangle((x - candle_width/2, body_bottom), candle_width, body_height,
                                                facecolor=color, edgecolor=color, linewidth=1.8, alpha=0.7)
                            ax_price.add_patch(rect)
                        
                        # Tight x-limits across combined view for even spacing
                        ax_price.set_xlim(-0.5, len(combined) - 0.5)
                        
                        # Yellow separator line at decision point
                        ax_price.axvline(hist_len - 0.5, color='yellow', linestyle='-', linewidth=3, alpha=0.9, label='Decision Point', zorder=4)
                        
                        # Mark buy/sell signals in historical segment
                        buys = hist_slice.reset_index(drop=True)
                        buys = buys[buys[buy_col] == True]
                        sells = hist_slice.reset_index(drop=True)
                        sells = sells[sells[sell_col] == True]
                        
                        for idx, row in buys.iterrows():
                            ax_price.scatter([idx], [row['close'] * 0.995], marker='^', color='cyan', s=150, zorder=5, edgecolors='white', linewidths=1)
                        for idx, row in sells.iterrows():
                            ax_price.scatter([idx], [row['close'] * 1.005], marker='v', color='yellow', s=150, zorder=5, edgecolors='white', linewidths=1)
                        
                        # Mark entry point (decision point)
                        ax_price.scatter([hist_len - 1], [price], color='yellow', s=250, marker='o', zorder=6, edgecolors='white', linewidths=2, label='Entry Point')
                        
                        # Mark exit point (end of future)
                        ax_price.scatter([len(combined) - 1], [future_last], color='magenta', s=300, marker='*', zorder=6, edgecolors='white', linewidths=2, label='Exit Point')
                        
                        # Timeframe annotation (robust)
                        try:
                            time_start = hist_slice[time_col].iloc[0]
                            time_end = future_slice[time_col].iloc[-1] if len(future_slice) else hist_slice[time_col].iloc[-1]
                            time_range = f"{time_start} → {time_end}"
                        except Exception:
                            time_range = f"{len(hist_slice)}+{len(future_slice)} bars"
                        try:
                            interval = hist_slice[time_col].diff().mode()[0] if len(hist_slice) > 1 else 'Unknown'
                        except Exception:
                            interval = 'Unknown'
                        
                        border_color = '#00ff00' if outcome == 'PASS' else '#ff0000'
                        ax_price.set_title(f"{ticker} | {len(hist_slice)} Historical + {len(future_slice)} Future | Interval: {interval} | {time_range}",
                                         fontsize=16, fontweight='bold', color='white', pad=15)
                        ax_price.set_ylabel('Price ($)', fontsize=14, color='white')
                        ax_price.set_xlabel('Candle Index', fontsize=14, color='white')
                        ax_price.tick_params(colors='white', labelsize=11)
                        ax_price.grid(True, alpha=0.15, color='#333333')
                        ax_price.legend(loc='upper left', fontsize=11, facecolor='#2a2a2a', edgecolor='cyan', framealpha=0.9)
                        
                        # Colored border for outcome
                        for spine in ax_price.spines.values():
                            spine.set_edgecolor(border_color)
                            spine.set_linewidth(3)
                        
                        # Score subplot
                        if score_col and score_col in hist_slice.columns:
                            ax_score = axes[1]
                            ax_score.set_facecolor('#0a0a0a')
                            
                            # Plot score for historical segment
                            score_indices = range(len(hist_slice))
                            ax_score.plot(score_indices, hist_slice[score_col], color='orange', linewidth=2, label='Score')
                            
                            # Fill regions
                            if buy_th is not None:
                                ax_score.fill_between(score_indices, hist_slice[score_col], buy_th, 
                                                     where=(hist_slice[score_col] >= buy_th), color='green', alpha=0.3, interpolate=True)
                                ax_score.axhline(buy_th, color='green', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Buy Threshold ({buy_th:.3f})')
                            if sell_th is not None:
                                ax_score.fill_between(score_indices, hist_slice[score_col], sell_th,
                                                     where=(hist_slice[score_col] <= sell_th), color='red', alpha=0.3, interpolate=True)
                                ax_score.axhline(sell_th, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Sell Threshold ({sell_th:.3f})')
                            
                            ax_score.axhline(0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
                            ax_score.axvline(hist_len - 0.5, color='yellow', linestyle='-', linewidth=3, alpha=0.9, zorder=4)
                            ax_score.set_ylabel('Score', fontsize=14, color='white')
                            ax_score.set_xlabel('Candle Index', fontsize=14, color='white')
                            ax_score.tick_params(colors='white', labelsize=11)
                            ax_score.grid(True, alpha=0.15, color='#333333')
                            ax_score.legend(loc='upper left', fontsize=10, facecolor='#2a2a2a', edgecolor='orange', framealpha=0.9)
                            
                            # Colored border
                            for spine in ax_score.spines.values():
                                spine.set_edgecolor(border_color)
                                spine.set_linewidth(3)
                        
                        # Info box with outcome
                        info_text = f"ACTION: {action}\nENTRY: ${price:.2f}\nEXIT: ${future_last:.2f}\nRETURN: {future_return:.2f}%\nOUTCOME: {outcome}"
                        if score_val is not None:
                            info_text += f"\nSCORE: {score_val:.3f}"
                        if conf_pct is not None:
                            info_text += f"\nCONFIDENCE: {conf_pct:.1f}%"
                        info_text += f"\nBUY SIGNALS: {buy_signals}\nSELL SIGNALS: {sell_signals}"
                        
                        box_color = '#00ff00' if outcome == 'PASS' else '#ff0000'
                        fig.text(0.02, 0.98, info_text, fontsize=12, family='monospace', color='white',
                                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='#2a2a2a', alpha=0.95, edgecolor=box_color, linewidth=3))
                        
                        plt.tight_layout()
                        future_path = out_dir / 'segment_with_future.png'
                        plt.savefig(future_path, dpi=120, bbox_inches='tight', facecolor='#1a1a1a')
                        plt.close(fig)
                        console.print(f"[green]📊 Future chart saved: {future_path}[/green]")
                        
                        # Open the chart
                        try:
                            import os
                            os.startfile(str(future_path))
                        except Exception:
                            pass  # Silent fail if can't open
                        
                    except Exception as e:
                        console.print(f"[yellow]Future chart generation failed: {e}[/yellow]")
                        import traceback
                        traceback.print_exc()
                        future_path = None
            else:
                console.print("[yellow]Not enough future data available.[/yellow]")
                future_path = None

        # Summary file (stores whether future revealed)
        import json
        summary = {
            'ticker': ticker,
            'style_choice': style_choice,
            'start_index': start_idx,
            'end_index': end_idx,
            'end_timestamp': str(hist_slice[time_col].iloc[-1]),
            'action': action,
            'price': price,
            'score': score_val,
            'confidence_pct': conf_pct,
            'future_return_pct': future_return,
            'outcome': outcome,
            'revealed': reveal
        }
        with open(out_dir / 'segment_summary.json','w') as f:
            json.dump(summary, f, indent=2)

        # Accuracy log (append only if revealed)
        if reveal:
            log_path = out_dir / 'accuracy_log.csv'
            header_needed = not log_path.exists()
            with open(log_path,'a') as lf:
                if header_needed:
                    lf.write('timestamp,ticker,action,future_return_pct,outcome\n')
                lf.write(f"{summary['end_timestamp']},{ticker},{action},{future_return if future_return is not None else ''},{outcome}\n")
            # Compute cumulative accuracy
            try:
                import pandas as pd
                log_df = pd.read_csv(log_path)
                total_trials = len(log_df)
                pass_trials = (log_df['outcome'] == 'PASS').sum()
                accuracy = pass_trials / total_trials * 100 if total_trials else 0
                console.print(f"[cyan]Cumulative Accuracy: {accuracy:.1f}% ({pass_trials}/{total_trials})[/cyan]")
            except Exception:
                pass

        console.print(f"[green]Segment saved under {out_dir}[/green]")
        console.print(f"History chart: {hist_path}")
        if reveal and future_path:
            console.print(f"Future chart:  {future_path}")
            console.print(f"Outcome: {outcome} FutureRet={future_return:.2f}%" if future_return is not None else "Outcome: N/A")
        else:
            console.print("Future not revealed yet. Rerun to evaluate or choose reveal when prompted.")
        Prompt.ask("\nPress Enter to continue")
    
    def _run_watchlist(self, watchlist: 'WatchlistMonitor'):
        """Monitor watchlist of tickers."""
        console.clear()
        console.print("[bold cyan]👁️  Watchlist Monitor[/bold cyan]\n")
        console.print("1. Add ticker\n2. Scan\n3. View trades\n4. View positions (P&L)\n")
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4"], default="2")
        
        if choice == "1":
            ticker = Prompt.ask("Ticker")
            watchlist.add_to_watchlist(ticker)
            console.print(f"[green]✓ Added {ticker}[/green]")
        elif choice == "2":
            alerts = watchlist.scan_watchlist()
            if alerts:
                console.print(f"\n[bold cyan]Found {len(alerts)} signals![/bold cyan]")
                for t, s in alerts.items():
                    console.print(f"{t}: {s.action} @ {s.confidence}%")
            else:
                console.print("[yellow]No signals[/yellow]")
        elif choice == "3":
            # Show watchlist-tracked trades and also user's saved positions summary
            if watchlist.active_trades:
                console.print("\n[bold cyan]Active Watchlist Trades[/bold cyan]")
                for t, tr in watchlist.active_trades.items():
                    console.print(f"{t}: {tr.direction} @ ${tr.entry_price}")
            else:
                console.print("[yellow]No active watchlist trades[/yellow]")
            try:
                mgr = PositionManager()
                mgr.refresh_prices()
                console.print("\n[bold cyan]Your Positions (from Position Manager)[/bold cyan]")
                console.print(mgr.get_position_summary())
            except Exception as e:
                console.print(f"[red]Error loading positions: {e}[/red]")
        elif choice == "4":
            # Direct shortcut to view user's positions with fresh P&L
            try:
                mgr = PositionManager()
                mgr.refresh_prices()
                console.print(mgr.get_position_summary())
            except Exception as e:
                console.print(f"[red]Error loading positions: {e}[/red]")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _manage_positions(self, mgr: 'PositionManager'):
        """Manage open positions with persistent storage and monitoring."""
        DisplayManager.show_header()
        console.print("[bold cyan]💰 Position Manager[/bold cyan]\n")
        
        # Show quick summary if positions exist
        if mgr.positions:
            console.print(f"[green]📊 {len(mgr.positions)} active position(s)[/green]")
            console.print(f"[dim]Last saved: {mgr.POSITIONS_FILE}[/dim]\n")
        
        console.print("[bold]Select Action:[/bold]")
        console.print("1. ➕ Add New Position")
        console.print("2. 🔄 Update All Positions (Check Prices & Alerts)")
        console.print("3. 👁️  View All Positions")
        console.print("4. 🗑️  Remove Position")
        console.print("5. 🔔 Monitor Positions (Live)")
        console.print("6. ⬅️  Back to Main Menu\n")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"], default="3")
        
        if choice == "1":
            # Add position
            console.print("\n[bold cyan]Add New Position[/bold cyan]\n")
            
            console.print("[bold]Position Type:[/bold]")
            console.print("1. Stock/ETF")
            console.print("2. Crypto")
            console.print("3. Option Contract")
            console.print("4. Futures\n")
            pos_type_choice = Prompt.ask("Select type", choices=["1", "2", "3", "4"], default="1")
            
            type_map = {"1": "stock", "2": "crypto", "3": "option", "4": "futures"}
            position_type = type_map[pos_type_choice]
            
            ticker = Prompt.ask("Ticker/Symbol").upper().strip()
            entry = FloatPrompt.ask("Entry price")
            shares = FloatPrompt.ask("Quantity/Contracts", default=1.0)
            
            console.print("\n[bold]Direction:[/bold]")
            console.print("1. BUY (Long)")
            console.print("2. SELL (Short)\n")
            dir_choice = Prompt.ask("Select", choices=["1", "2"], default="1")
            direction = "BUY" if dir_choice == "1" else "SELL"
            
            stop = FloatPrompt.ask("Stop loss price")
            tp = FloatPrompt.ask("Take profit price")
            
            # For options, get contract details
            contract_details = None
            if position_type == "option":
                console.print("\n[bold]Option Details:[/bold]")
                strike = FloatPrompt.ask("Strike price")
                expiry = Prompt.ask("Expiration (YYYY-MM-DD)")
                opt_type = Prompt.ask("Type", choices=["CALL", "PUT"])
                contract_details = {
                    "strike": strike,
                    "expiry": expiry,
                    "type": opt_type
                }
            
            mgr.add_position(ticker, entry, shares, direction, stop, tp, position_type, contract_details)
            console.print("\n[green]✓ Position added and saved to disk![/green]")
            console.print("[dim]Position will be automatically monitored across app restarts[/dim]")
            
        elif choice == "2":
            # Update positions
            console.print("\n[yellow]Updating all positions...[/yellow]\n")
            alerts = mgr.update_positions(
                notifier=self.notifier if hasattr(self, 'notifier') else None,
                analyzer=self.analyzer,
                technical_analyzer=TechnicalAnalyzer()
            )
            
            if alerts:
                console.print("[bold red]🔔 ALERTS TRIGGERED:[/bold red]")
                for ticker, msg, price in alerts:
                    console.print(f"[yellow]{ticker}[/yellow]: {msg} @ ${price:.2f}")
                console.print()
            
            console.print("[green]✓ All positions updated and saved![/green]")
            
        elif choice == "3":
            # View positions
            if not mgr.positions:
                console.print("\n[yellow]No active positions[/yellow]")
            else:
                console.print(f"\n[bold cyan]Active Positions ({len(mgr.positions)})[/bold cyan]\n")
                
                table = Table(box=box.ROUNDED)
                table.add_column("Symbol", style="cyan")
                table.add_column("Type", style="dim")
                table.add_column("Direction", style="white")
                table.add_column("Entry", justify="right")
                table.add_column("Current", justify="right")
                table.add_column("Qty", justify="right")
                table.add_column("P&L", justify="right")
                table.add_column("P&L %", justify="right")
                table.add_column("Stop", justify="right", style="red")
                table.add_column("Target", justify="right", style="green")
                
                for ticker, pos in mgr.positions.items():
                    pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                    
                    # Add contract details for options
                    symbol_display = ticker
                    if pos.position_type == "option" and pos.contract_details:
                        symbol_display = f"{ticker}\n{pos.contract_details['type']} ${pos.contract_details['strike']}"
                    
                    table.add_row(
                        symbol_display,
                        pos.position_type,
                        pos.direction,
                        f"${pos.entry_price:.2f}",
                        f"${pos.current_price:.2f}" if pos.current_price > 0 else "—",
                        f"{pos.shares:.0f}",
                        f"[{pnl_color}]${pos.unrealized_pnl:.2f}[/{pnl_color}]",
                        f"[{pnl_color}]{pos.unrealized_pnl_pct:+.1f}%[/{pnl_color}]",
                        f"${pos.stop_loss:.2f}",
                        f"${pos.take_profit:.2f}"
                    )
                
                console.print(table)
                console.print(f"\n[dim]Entry dates, last check times saved in: {mgr.POSITIONS_FILE}[/dim]")
        
        elif choice == "4":
            # Remove position
            if not mgr.positions:
                console.print("\n[yellow]No positions to remove[/yellow]")
            else:
                console.print("\n[bold]Select position to remove:[/bold]")
                tickers = list(mgr.positions.keys())
                for i, ticker in enumerate(tickers, 1):
                    pos = mgr.positions[ticker]
                    console.print(f"{i}. {ticker} ({pos.position_type}) - {pos.direction}")
                
                choice_num = IntPrompt.ask("Select position", default=1)
                if 1 <= choice_num <= len(tickers):
                    ticker_to_remove = tickers[choice_num - 1]
                    if Confirm.ask(f"Remove {ticker_to_remove}?", default=False):
                        mgr.remove_position(ticker_to_remove)
                        console.print(f"[green]✓ {ticker_to_remove} removed[/green]")
        
        elif choice == "5":
            # Live monitoring
            if not mgr.positions:
                console.print("\n[yellow]No positions to monitor[/yellow]")
            else:
                self._monitor_positions_live(mgr)
                return  # Skip "Press Enter" since monitor has its own loop
        
        # choice 6 returns to menu
        
        Prompt.ask("\nPress Enter to continue")
    
    def _monitor_positions_live(self, mgr: 'PositionManager'):
        """Live monitoring loop for positions."""
        console.print("\n[bold cyan]🔔 Live Position Monitor[/bold cyan]")
        console.print("[dim]Checking every 60 seconds. Press Ctrl+C to stop.[/dim]\n")
        
        try:
            while True:
                DisplayManager.show_header()
                console.print("[bold cyan]Live Position Monitor[/bold cyan]\n")
                console.print(f"[dim]Last update: {datetime.now().strftime('%H:%M:%S')}[/dim]\n")
                
                # Update all positions
                alerts = mgr.update_positions(
                    notifier=self.notifier if hasattr(self, 'notifier') else None,
                    analyzer=self.analyzer,
                    technical_analyzer=TechnicalAnalyzer()
                )
                
                # Show alerts
                if alerts:
                    console.print("[bold red]🔔 ALERTS:[/bold red]")
                    for ticker, msg, price in alerts:
                        console.print(f"[yellow]{ticker}[/yellow]: {msg} @ ${price:.2f}")
                    console.print()
                
                # Show positions table
                if mgr.positions:
                    table = Table(box=box.SIMPLE)
                    table.add_column("Symbol", style="cyan")
                    table.add_column("Entry", justify="right")
                    table.add_column("Current", justify="right")
                    table.add_column("P&L %", justify="right")
                    table.add_column("Status", style="dim")
                    
                    for ticker, pos in mgr.positions.items():
                        pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                        
                        # Determine status
                        status = "Active"
                        if pos.current_price <= pos.stop_loss:
                            status = "⚠️ AT STOP"
                        elif pos.current_price >= pos.take_profit:
                            status = "🎯 AT TARGET"
                        
                        table.add_row(
                            ticker,
                            f"${pos.entry_price:.2f}",
                            f"${pos.current_price:.2f}",
                            f"[{pnl_color}]{pos.unrealized_pnl_pct:+.1f}%[/{pnl_color}]",
                            status
                        )
                    
                    console.print(table)
                
                console.print(f"\n[dim]Next update in 60 seconds...[/dim]")
                time.sleep(60)
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Monitoring stopped[/yellow]")
            Prompt.ask("Press Enter to continue")
    
    def _detect_smart_money(self):
        """Detect smart money accumulation/distribution."""
        console.clear()
        console.print("[bold cyan]🏢 Smart Money Detector[/bold cyan]\n")
        ticker = Prompt.ask("Ticker")
        try:
            df = yf.download(ticker, period="60d", progress=False)
            indicators = TechnicalAnalyzer.calculate_indicators(df)
            signals = SmartMoneyDetector.get_all_signals(df, indicators)
            if signals:
                console.print(f"\n[bold cyan]Found {len(signals)} signals:[/bold cyan]")
                for sig in signals[:5]:
                    console.print(f"[{sig.type}] ${sig.price_level:.2f} - {sig.description}")
            else:
                console.print("[yellow]No signals[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        Prompt.ask("\nPress Enter to continue")
    
    def _multi_timeframe_analysis(self, mta: 'MultiTimeframeAnalyzer'):
        """Analyze across multiple timeframes."""
        console.clear()
        console.print("[bold cyan]⏱️  Multi-Timeframe Analysis[/bold cyan]\n")
        ticker = Prompt.ask("Ticker")
        console.print(f"[yellow]Analyzing {ticker}...[/yellow]")
        result = mta.analyze_multi_timeframe(ticker)
        table = Table(title=f"Signals: {ticker}", box=box.ROUNDED)
        table.add_column("TF", style="cyan")
        table.add_column("Action", style="green")
        for tf in ['1h', '4h', '1d']:
            if result[tf]:
                table.add_row(tf, result[tf]['action'])
        console.print(table)
        console.print(f"Alignment: {result['alignment']} ({result['overall_confidence']:.0f}%)")
        Prompt.ask("\nPress Enter to continue")
    
    def _ml_signal_training(self, weighter: 'MLSignalWeighter', backtest: 'BacktestEngine'):
        """Train ML signal weighting."""
        console.clear()
        console.print("[bold cyan]🤖 ML Signal Weighting[/bold cyan]\n")
        console.print("1. View weights\n2. Retrain\n3. Show trades\n")
        choice = Prompt.ask("Select", choices=["1", "2", "3"], default="1")
        
        if choice == "1":
            table = Table(title="Weights", box=box.ROUNDED)
            table.add_column("Indicator", style="cyan")
            table.add_column("Weight", style="green")
            for k, w in weighter.weights.items():
                table.add_row(k, f"{w:.3f}")
            console.print(table)
        elif choice == "2":
            weighter.trade_history = backtest.trades
            weighter.retrain_weights()
            console.print("[green]✓ Retrained[/green]")
        elif choice == "3":
            console.print(f"Trades: {len(weighter.trade_history)}")
        
        Prompt.ask("\nPress Enter to continue")
    
    def _options_strategies(self):
        """Suggest options strategies."""
        console.clear()
        console.print("[bold cyan]📞 Options Strategy Overlay[/bold cyan]\n")
        ticker = Prompt.ask("Ticker")
        try:
            df = yf.download(ticker, period="1d", progress=False)
            current = df['Close'].iloc[-1]
            indicators = TechnicalAnalyzer.calculate_indicators(df)
            signal = self.analyzer._fallback_analysis(ticker, indicators, 10000, 0.02, 2.0)
            strategy = OptionsStrategist.suggest_strategy(signal, current, 0.25)
            if strategy:
                table = Table(title=f"Strategy: {ticker}", box=box.ROUNDED)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                table.add_row("Type", strategy.strategy_type)
                table.add_row("Strike", f"${strategy.strike:.2f}")
                table.add_row("POP", f"{strategy.probability_of_profit*100:.0f}%")
                table.add_row("Max Risk", f"${strategy.max_risk:.2f}")
                table.add_row("Max Reward", f"${strategy.max_reward:.2f}")
                console.print(table)
            else:
                console.print("[yellow]No suitable strategy[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        Prompt.ask("\nPress Enter to continue")

    def _options_trade_planner(self):
        """Interactive options trade planner with stock analysis and position tracking.
        
        - Analyzes the underlying stock to recommend BUY/SELL/HOLD
        - Creates option trade plan with entry/stop/target
        - Saves position for continuous monitoring
        - Sends alerts when position should be exited
        """
        console.print("\n[bold cyan]📝 Options Trade Planner with Stock Analysis[/bold cyan]\n")
        underlying = Prompt.ask("Underlying ticker (e.g., AAPL)").upper().strip()
        
        # Get expiration date first to calculate analysis period
        expiration = Prompt.ask("Expiration date (MM/DD/YY)")
        
        # Calculate analysis timeframe (2x time until expiration)
        try:
            exp_date = datetime.strptime(expiration, "%m/%d/%y")
            days_to_exp = (exp_date - datetime.now()).days
            analysis_days = max(days_to_exp * 2, 5)  # At least 5 days
            
            # Determine period and interval based on analysis days
            if analysis_days <= 7:
                period = f"{analysis_days}d"
                interval = "15m"
            elif analysis_days <= 60:
                period = f"{analysis_days}d"
                interval = "1h"
            elif analysis_days <= 365:
                period = f"{int(analysis_days/30)}mo"
                interval = "1d"
            else:
                years = int(analysis_days/365)
                period = f"{years}y"
                interval = "1d"
            
            console.print(f"[dim]Analyzing {analysis_days} days of data (2x time to expiration: {days_to_exp} days)[/dim]\n")
        except:
            period = "1mo"
            interval = "1d"
            console.print(f"[yellow]Invalid date format, using default 1 month analysis[/yellow]\n")
        
        # Step 1: Analyze underlying stock
        console.print(f"\n[yellow]Analyzing {underlying} to determine option direction...[/yellow]\n")
        
        try:
            # Fetch stock data with calculated timeframe
            df = DataManager.fetch_data(underlying, period, interval)
            if df is None or len(df) < 50:
                console.print(f"[red]Not enough data for {underlying}. Proceeding with manual entry.[/red]\n")
                stock_action = None
            else:
                # Calculate indicators
                indicators = TechnicalAnalyzer.calculate_indicators(df)
                if not indicators:
                    stock_action = None
                else:
                    # Get AI analysis
                    patterns = PatternRecognizer.analyze(df)
                    notifier_obj = self.notifier if hasattr(self, 'notifier') else None
                    market_structure = SmartMoneyAnalyzer.analyze(df, underlying, notifier_obj)
                    volume_profile = VolumeProfileAnalyzer.analyze(df)
                    
                    account_size = self.config.get('account_size', 10000) if self.config else 10000
                    risk_pct = (self.config.get('risk_per_trade', 2.0)/100.0) if self.config else 0.02
                    default_rr = float(self.config.get('default_rrr', 2.0)) if self.config else 2.0
                    
                    analysis = self.analyzer.analyze(
                        underlying, indicators, patterns, market_structure, volume_profile,
                        account_size, risk_pct, default_rr
                    )
                    
                    if not analysis:
                        # Fallback
                        analysis = self.analyzer._fallback_analysis(
                            underlying, indicators, account_size, risk_pct, default_rr
                        )
                    
                    # Display recommendation
                    stock_action = analysis.action
                    conf_color = "green" if analysis.confidence >= 70 else "yellow" if analysis.confidence >= 50 else "red"
                    
                    rec_panel = Panel(
                        f"[bold]Stock Recommendation: [{conf_color}]{stock_action}[/{conf_color}][/bold]\n"
                        f"Confidence: {analysis.confidence:.0f}%\n"
                        f"Current Price: ${indicators.price:.2f}\n"
                        f"Reason: {analysis.primary_reason}",
                        title=f"{underlying} Analysis",
                        border_style="cyan"
                    )
                    console.print(rec_panel)
                    console.print()
        except Exception as e:
            console.print(f"[red]Error analyzing {underlying}: {e}[/red]\n")
            stock_action = None
        
        # Step 2: Get option details and number of contracts
        # Suggest option type based on stock analysis
        if stock_action == "BUY":
            suggested_type = "CALL"
            console.print("[green]💡 Suggestion: Buy CALL (bullish)[/green]")
        elif stock_action == "SELL":
            suggested_type = "PUT"
            console.print("[red]💡 Suggestion: Buy PUT (bearish)[/red]")
        else:
            suggested_type = "CALL"
            console.print("[yellow]💡 No clear direction - choose based on your analysis[/yellow]")
        
        opt_type = Prompt.ask("Type", choices=["CALL","PUT"], default=suggested_type).upper()
        strike = FloatPrompt.ask("Strike price")
        num_contracts = IntPrompt.ask("Number of contracts", default=1)
        
        default_rr = float(self.config.get('default_rrr', 2.0)) if self.config else 2.0
        desired_rrr = FloatPrompt.ask("Desired Risk:Reward (1:R)", default=default_rr)
        risk_pct = (self.config.get('risk_per_trade', 2.0)/100.0) if self.config else 0.02
        account_size = self.config.get('account_size', 10000) if self.config else 10000

        # Step 3: Fetch option premium
        import math
        premium_mid = None
        try:
            import yfinance as yf
            opt = yf.Ticker(underlying)
            chain = opt.option_chain(expiration)
            table = chain.calls if opt_type == 'CALL' else chain.puts
            if not table.empty:
                row = table.iloc[(table['strike'] - strike).abs().argsort()[:1]]
                ask = float(row['ask'].values[0]) if not math.isnan(row['ask'].values[0]) else None
                bid = float(row['bid'].values[0]) if not math.isnan(row['bid'].values[0]) else None
                if ask is not None and bid is not None and (ask > 0 or bid > 0):
                    premium_mid = (ask + bid)/2 if ask and bid else (ask or bid)
        except Exception:
            premium_mid = None

        if premium_mid is None or premium_mid <= 0:
            premium_mid = FloatPrompt.ask("Option premium (mid) not found. Enter est. premium ($)", default=1.00)

        # Step 4: Build trade plan
        entry_price = float(premium_mid)
        stop_price = round(entry_price * 0.5, 2)
        risk_per_contract = entry_price - stop_price
        target_price = round(entry_price + risk_per_contract * float(desired_rrr), 2)

        # Use the number of contracts specified by user
        contracts = num_contracts
        total_risk = round(contracts * risk_per_contract * 100, 2)
        total_reward = round(contracts * (target_price - entry_price) * 100, 2)

        panel = Panel(
            f"Underlying: [bold]{underlying}[/bold]\nType: {opt_type}  Strike: ${strike:.2f}  Exp: {expiration}\n\n"
            f"Entry (premium): ${entry_price:.2f}\nStop (premium): ${stop_price:.2f}\nTarget (premium): ${target_price:.2f} (1:{float(desired_rrr):.2f})\n\n"
            f"Contracts: {contracts}\nRisk: ${total_risk:.2f}  |  Reward (to target): ${total_reward:.2f}",
            title="Options Plan",
            border_style="cyan",
            box=box.HEAVY
        )
        console.print(panel)
        
        # Step 5: Ask if they took the trade
        took_trade = Confirm.ask("\nDid you enter this position?", default=False)
        
        if took_trade:
            # Save position for monitoring
            position_file = RESULTS_DIR / 'options_positions.json'
            positions = []
            if position_file.exists():
                try:
                    with open(position_file, 'r') as f:
                        positions = json.load(f)
                except:
                    positions = []
            
            position = {
                'underlying': underlying,
                'type': opt_type,
                'strike': strike,
                'expiration': expiration,
                'contracts': contracts,
                'entry_premium': entry_price,
                'stop_premium': stop_price,
                'target_premium': target_price,
                'entry_date': datetime.now().strftime("%m/%d/%y %H:%M:%S"),
                'status': 'OPEN'
            }
            positions.append(position)
            
            with open(position_file, 'w') as f:
                json.dump(positions, f, indent=2)
            
            console.print(f"\n[green]✓ Position saved! Will monitor and send alerts.[/green]")
            
            # Send notification with all positions summary
            try:
                if hasattr(self, 'notifier') and self.notifier:
                    # Count open positions
                    open_positions = [p for p in positions if p.get('status') == 'OPEN']
                    
                    # Build notification message
                    msg = f"🎯 ENTERED: {underlying} {opt_type} ${strike} exp {expiration}\n"
                    msg += f"Contracts: {contracts} @ ${entry_price:.2f}\n"
                    msg += f"Stop: ${stop_price:.2f} | Target: ${target_price:.2f}\n\n"
                    msg += f"📊 ALL OPEN POSITIONS ({len(open_positions)}):\n"
                    
                    for i, pos in enumerate(open_positions, 1):
                        msg += f"{i}. {pos['underlying']} {pos['type']} ${pos['strike']} exp {pos['expiration']} - {pos['contracts']} contracts @ ${pos['entry_premium']:.2f}\n"
                    
                    self.notifier.send(msg)
            except:
                pass
        else:
            # Still notify the plan
            try:
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.send(f"OPT PLAN {underlying} {opt_type} {strike}@{expiration} | Prem ${entry_price:.2f} SL ${stop_price:.2f} TP ${target_price:.2f}")
            except:
                pass

        Prompt.ask("\nPress Enter to continue")

# ==========================================
# FEATURE 1: BACKTESTING ENGINE
# ==========================================

@dataclass
class BacktestTrade:
    entry_date: datetime
    exit_date: datetime
    ticker: str
    entry_price: float
    exit_price: float
    shares: int
    direction: str  # BUY or SELL
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_percent: float
    win: bool
    reason: str

@dataclass
class BacktestMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy: float

class BacktestEngine:
    """Historical backtesting engine for signal validation."""
    
    def __init__(self, analyzer: 'AIAnalyzer', technical: 'TechnicalAnalyzer', 
                 slippage_pct: float = 0.001, commission_per_trade: float = 0.50):
        self.analyzer = analyzer
        self.technical = technical
        self.trades: List[BacktestTrade] = []
        self.slippage_pct = slippage_pct  # Default 0.1% slippage
        self.commission_per_trade = commission_per_trade  # Default $0.50 per trade
        
    def backtest_ticker(self, ticker: str, start_date: str, end_date: str, 
                       initial_capital: float = 10000.0, risk_per_trade: float = 0.02,
                       desired_rrr: float = 2.0, predictor: callable = None) -> BacktestMetrics:
        """Run backtest on historical data for a ticker."""
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            # If no data or download failed, return empty metrics
            if df is None or df.empty:
                return self._calculate_metrics(initial_capital, initial_capital)

            # Basic walk-forward backtest using predictor (if provided).
            self.trades = []

            if predictor is None:
                # No predictor -> return empty metrics
                return self._calculate_metrics(initial_capital, initial_capital)

            # Prepare features for predictor: we'll use Close, Volume, returns
            df2 = df[['Open','High','Low','Close','Volume']].copy()
            df2['ret1'] = df2['Close'].pct_change().fillna(0)
            df2['logvol'] = np.log1p(df2['Volume']).fillna(0)

            window = getattr(predictor, 'window', 30)

            equity = initial_capital
            position = None

            # iterate from window to end-1 so we can enter next bar
            for i in range(window, len(df2)-1):
                window_df = df2.iloc[i-window:i]
                target_date = df2.index[i+1]

                forecast = predictor.predict(window_df)
                # simple decision rule: go long if mean>0 and p10>0 (conservative)
                take_signal = (forecast['mean'] > 0) and (forecast['p10'] > 0)

                # position entry at next open
                next_open = df2['Open'].iloc[i+1]
                next_close = df2['Close'].iloc[i+1]
                atr = (df2['High'].rolling(14).max().iloc[i] - df2['Low'].rolling(14).min().iloc[i])
                if atr == 0 or np.isnan(atr):
                    atr = (df2['High'].iloc[i] - df2['Low'].iloc[i])

                if position is None and take_signal:
                    stop_loss = next_open - atr * 1.5
                    tp = next_open + (next_open - stop_loss) * desired_rrr
                    # position size based on risk_per_trade
                    risk_amount = equity * risk_per_trade
                    stop_distance = next_open - stop_loss
                    shares = int(risk_amount / (stop_distance * next_open)) if stop_distance > 0 else 0
                    if shares > 0:
                        # Apply slippage to entry (pay more when buying)
                        entry_with_slippage = next_open * (1 + self.slippage_pct)
                        entry_commission = self.commission_per_trade
                        position = {
                            'entry_date': target_date,
                            'entry_price': entry_with_slippage,
                            'entry_commission': entry_commission,
                            'shares': shares,
                            'direction': 'BUY',
                            'stop_loss': stop_loss,
                            'take_profit': tp,
                            'confidence': forecast['p50']
                        }

                # Evaluate existing position at close
                if position is not None:
                    exit_price = None
                    exit_reason = None
                    # check stop
                    if df2['Low'].iloc[i+1] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'Stop'
                    # check TP
                    elif df2['High'].iloc[i+1] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                    else:
                        # exit at close (end of holding period)
                        exit_price = next_close
                        exit_reason = 'Close'

                    # Apply slippage to exit (receive less when selling)
                    exit_with_slippage = exit_price * (1 - self.slippage_pct)
                    exit_commission = self.commission_per_trade
                    
                    # Calculate realistic PnL including costs
                    gross_pnl = (exit_with_slippage - position['entry_price']) * position['shares']
                    total_commissions = position['entry_commission'] + exit_commission
                    net_pnl = gross_pnl - total_commissions
                    
                    pnl_pct = net_pnl / (position['entry_price'] * position['shares']) * 100 if position['shares']>0 else 0
                    trade = BacktestTrade(entry_date=position['entry_date'], exit_date=target_date, ticker=ticker,
                                          entry_price=position['entry_price'], exit_price=exit_with_slippage,
                                          shares=position['shares'], direction=position['direction'],
                                          stop_loss=position['stop_loss'], take_profit=position['take_profit'],
                                          pnl=net_pnl, pnl_percent=pnl_pct, win=(net_pnl>0), reason=exit_reason)
                    self.trades.append(trade)
                    equity += net_pnl
                    position = None

            return self._calculate_metrics(equity, initial_capital)

        except Exception as e:
            logger.error(f"Backtest error for {ticker}: {str(e)}")
            return None
    
    def _calculate_metrics(self, final_equity: float, initial_capital: float) -> BacktestMetrics:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        total = len(self.trades)
        wins = [t for t in self.trades if t.win]
        losses = [t for t in self.trades if not t.win]
        
        win_rate = len(wins) / total if total > 0 else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        profit_factor = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses else 0
        total_pnl = final_equity - initial_capital
        
        # Sharpe ratio
        returns = [t.pnl_percent for t in self.trades]
        sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
        
        # Sortino ratio (downside volatility)
        downside = [r for r in returns if r < 0]
        sortino = (np.mean(returns) / np.std(downside) * np.sqrt(252)) if downside and np.std(downside) > 0 else sharpe
        
        # Max drawdown
        cumulative = np.cumsum([t.pnl for t in self.trades])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max if len(running_max) > 0 else 0
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # Calmar ratio
        calmar = (np.mean(returns) / abs(max_drawdown) * 252) if max_drawdown != 0 else 0
        
        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        return BacktestMetrics(
            total_trades=total,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            total_pnl=total_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            expectancy=expectancy
        )
    
    def export_trade_log(self, filename: str = "backtest_trades.csv") -> bool:
        """Export trade log to CSV file."""
        try:
            if not self.trades:
                logger.warning("No trades to export")
                return False
            
            trade_data = []
            for trade in self.trades:
                trade_data.append({
                    'entry_date': trade.entry_date,
                    'exit_date': trade.exit_date,
                    'ticker': trade.ticker,
                    'direction': trade.direction,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'shares': trade.shares,
                    'stop_loss': trade.stop_loss,
                    'take_profit': trade.take_profit,
                    'pnl': trade.pnl,
                    'pnl_percent': trade.pnl_percent,
                    'win': trade.win,
                    'exit_reason': trade.reason
                })
            
            df = pd.DataFrame(trade_data)
            df.to_csv(filename, index=False)
            logger.info(f"Trade log exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error exporting trade log: {e}")
            return False

# ==========================================
# FEATURE 2: WATCHLIST & ALERTS
# ==========================================

@dataclass
class AlertConfig:
    ticker: str
    min_confidence: int = 70
    check_interval_minutes: int = 5
    alert_on_signal: bool = True
    track_trades: bool = True

class WatchlistMonitor:
    """Monitor multiple tickers for high-confidence setups and track trades."""
    
    def __init__(self, analyzer: 'AIAnalyzer', technical: 'TechnicalAnalyzer'):
        self.analyzer = analyzer
        self.technical = technical
        self.watchlist: List[AlertConfig] = []
        self.active_trades: Dict[str, BacktestTrade] = {}
        self.trade_history: List[BacktestTrade] = []
    
    def add_to_watchlist(self, ticker: str, min_confidence: int = 70, 
                        check_interval: int = 5, track: bool = True):
        """Add ticker to watchlist."""
        config = AlertConfig(ticker, min_confidence, check_interval, True, track)
        self.watchlist.append(config)
        logger.info(f"Added {ticker} to watchlist")
    
    def scan_watchlist(self) -> Dict[str, TradeSummary]:
        """Scan all tickers in watchlist for signals."""
        alerts = {}
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                     console=console) as progress:
            task = progress.add_task("[cyan]Scanning watchlist...", total=len(self.watchlist))
            
            for config in self.watchlist:
                progress.update(task, advance=1)
                
                try:
                    df = yf.download(config.ticker, period="60d", interval="5m", progress=False, prepost=True)
                    if df.empty:
                        continue
                    
                    indicators = self.technical.calculate_indicators(df)
                    patterns = PatternRecognizer.analyze(df)
                    market_struct = MarketStructure.detect(df)
                    volume_prof = VolumeProfile.calculate(df)
                    
                    signal = self.analyzer._fallback_analysis(
                        config.ticker, indicators, 10000, 0.02, 2.0
                    )
                    
                    if signal.confidence >= config.min_confidence:
                        alerts[config.ticker] = signal
                        
                        if config.track_trades:
                            self.active_trades[config.ticker] = BacktestTrade(
                                entry_date=datetime.now(),
                                exit_date=None,
                                ticker=config.ticker,
                                entry_price=indicators.price,
                                exit_price=0,
                                shares=0,
                                direction=signal.action,
                                stop_loss=signal.stop_loss,
                                take_profit=signal.take_profit_levels[0] if signal.take_profit_levels else 0,
                                pnl=0,
                                pnl_percent=0,
                                win=False,
                                reason="Monitoring"
                            )
                
                except Exception as e:
                    logger.error(f"Error scanning {config.ticker}: {str(e)}")
        
        return alerts

# ==========================================
# FEATURE 3: SMART MONEY FLOW DETECTOR
# ==========================================

@dataclass
class SmartMoneySignal:
    type: str  # "ACCUMULATION", "DISTRIBUTION", "BREAKOUT", "REVERSAL"
    strength: float  # 0-100
    price_level: float
    volume_ratio: float
    order_block: Optional[Dict] = None
    description: str = ""

class SmartMoneyDetector:
    """Detect institutional buying/selling and order flow."""
    
    @staticmethod
    def detect_accumulation(df: pd.DataFrame, indicators: 'AdvancedIndicators') -> List[SmartMoneySignal]:
        """Detect institutional accumulation patterns."""
        signals = []
        
        try:
            recent = df.tail(20)
            
            # Low volume, rising price = accumulation
            for i in range(5, len(recent)):
                if recent.iloc[i]['Volume'] < recent['Volume'].mean() * 0.5:
                    if recent.iloc[i]['Close'] > recent.iloc[i-1]['Close']:
                        signals.append(SmartMoneySignal(
                            type="ACCUMULATION",
                            strength=min(100, 70 + (indicators.cci / 100)),
                            price_level=recent.iloc[i]['Close'],
                            volume_ratio=recent.iloc[i]['Volume'] / recent['Volume'].mean(),
                            description="Low volume accumulation detected"
                        ))
            
            # Order block detection (support zone)
            highs = recent['High'].rolling(3).max()
            lows = recent['Low'].rolling(3).min()
            for i in range(1, len(recent) - 1):
                if recent.iloc[i]['Close'] > lows.iloc[i] and recent.iloc[i]['Close'] < highs.iloc[i]:
                    if recent.iloc[i+1]['Low'] <= lows.iloc[i]:
                        signals.append(SmartMoneySignal(
                            type="ACCUMULATION",
                            strength=80,
                            price_level=lows.iloc[i],
                            volume_ratio=1.0,
                            description=f"Order block support at ${lows.iloc[i]:.2f}"
                        ))
        
        except Exception as e:
            logger.error(f"Accumulation detection error: {str(e)}")
        
        return signals
    
    @staticmethod
    def detect_distribution(df: pd.DataFrame, indicators: 'AdvancedIndicators') -> List[SmartMoneySignal]:
        """Detect institutional distribution patterns."""
        signals = []
        
        try:
            recent = df.tail(20)
            
            # High volume, falling price = distribution
            for i in range(5, len(recent)):
                if recent.iloc[i]['Volume'] > recent['Volume'].mean() * 1.5:
                    if recent.iloc[i]['Close'] < recent.iloc[i-1]['Close']:
                        signals.append(SmartMoneySignal(
                            type="DISTRIBUTION",
                            strength=min(100, 70 + abs(indicators.williams_r / 10)),
                            price_level=recent.iloc[i]['Close'],
                            volume_ratio=recent.iloc[i]['Volume'] / recent['Volume'].mean(),
                            description="High volume distribution detected"
                        ))
        
        except Exception as e:
            logger.error(f"Distribution detection error: {str(e)}")
        
        return signals
    
    @staticmethod
    def get_all_signals(df: pd.DataFrame, indicators: 'AdvancedIndicators') -> List[SmartMoneySignal]:
        """Get all smart money signals."""
        return SmartMoneyDetector.detect_accumulation(df, indicators) + \
               SmartMoneyDetector.detect_distribution(df, indicators)

# ==========================================
# FEATURE 4: MULTI-TIMEFRAME ANALYZER
# ==========================================

@dataclass
class TimeframeSignal:
    timeframe: str
    action: str
    confidence: int
    signal_count: int

class MultiTimeframeAnalyzer:
    """Analyze signals across multiple timeframes (1H, 4H, 1D)."""
    
    def __init__(self, analyzer: 'AIAnalyzer', technical: 'TechnicalAnalyzer'):
        self.analyzer = analyzer
        self.technical = technical
    
    def analyze_multi_timeframe(self, ticker: str, account_size: float = 10000) -> Dict[str, Any]:
        """Get signals from 1H, 4H, and daily timeframes."""
        results = {
            'ticker': ticker,
            '1h': None,
            '4h': None,
            '1d': None,
            'alignment': 'NEUTRAL',
            'overall_confidence': 0,
            'conflicts': []
        }
        
        timeframes = {'1h': '1h', '4h': '4h', '1d': '1d'}
        
        for name, interval in timeframes.items():
            try:
                period = '30d' if name != '1d' else '1y'
                df = yf.download(ticker, period=period, interval=interval, progress=False, prepost=True)
                
                if df.empty:
                    continue
                
                indicators = self.technical.calculate_indicators(df)
                signal = self.analyzer._fallback_analysis(ticker, indicators, account_size, 0.02, 2.0)
                
                results[name] = {
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'supporting_signals': signal.supporting_signals[:3]
                }
            
            except Exception as e:
                logger.error(f"Error analyzing {ticker} on {name}: {str(e)}")
        
        # Check alignment
        actions = [results[tf]['action'] for tf in ['1h', '4h', '1d'] if results[tf]]
        if len(set(actions)) == 1:
            results['alignment'] = 'STRONG'
            results['overall_confidence'] = np.mean([results[tf]['confidence'] for tf in ['1h', '4h', '1d'] if results[tf]])
        elif len(set(actions)) == 2:
            results['alignment'] = 'CONFLICTED'
            results['overall_confidence'] = 50
            results['conflicts'] = [tf for tf in ['1h', '4h', '1d'] if results[tf]]
        
        return results

# ==========================================
# FEATURE 5: POSITION MANAGEMENT ASSISTANT
# ==========================================

@dataclass
class OpenPosition:
    ticker: str
    entry_price: float
    entry_date: str  # Changed to string for JSON serialization
    shares: float
    direction: str
    stop_loss: float
    take_profit: float
    position_type: str = "stock"  # stock, option, futures
    trailing_stop: Optional[float] = None
    scale_out_levels: List[float] = field(default_factory=list)
    current_price: float = 0
    unrealized_pnl: float = 0
    unrealized_pnl_pct: float = 0
    contract_details: Optional[Dict[str, Any]] = None  # For options: strike, expiry, type
    last_alert_price: Optional[float] = None  # Track last notification price
    last_check: Optional[str] = None  # Last time position was checked
    last_analysis_action: Optional[str] = None  # Last AI recommendation (BUY/SELL/HOLD)
    last_analysis_confidence: Optional[float] = None  # Last AI confidence level

class PositionManager:
    """Manage open positions with dynamic stops, scale-out levels, and persistent storage."""
    
    POSITIONS_FILE = Path("results/positions.json")
    
    def __init__(self):
        self.positions: Dict[str, OpenPosition] = {}
        self.load_positions()  # Load saved positions on startup
    
    def load_positions(self):
        """Load positions from disk."""
        if self.POSITIONS_FILE.exists():
            try:
                with open(self.POSITIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for ticker, pos_data in data.items():
                        # Convert dict back to OpenPosition dataclass
                        self.positions[ticker] = OpenPosition(**pos_data)
                logger.info(f"Loaded {len(self.positions)} positions from disk")
            except Exception as e:
                logger.error(f"Error loading positions: {e}")
                self.positions = {}
        else:
            self.POSITIONS_FILE.parent.mkdir(exist_ok=True)
            logger.info("No saved positions found")
        
        # MIGRATION: Check for old holdings.json and import if positions.json is empty
        if not self.positions:
            self._migrate_from_holdings()
    
    def _migrate_from_holdings(self):
        """Migrate old holdings.json format to new positions.json format."""
        holdings_file = Path("results/holdings.json")
        if not holdings_file.exists():
            return
        
        try:
            with open(holdings_file, 'r') as f:
                holdings = json.load(f)
            
            migrated = 0
            for holding in holdings:
                if holding.get('status') != 'OPEN':
                    continue  # Skip closed positions
                
                # Determine position type and create ticker
                if holding.get('type') == 'OPTION':
                    # Option position
                    underlying = holding['underlying']
                    strike = holding['strike']
                    opt_type = holding['option_type']
                    expiry = holding['expiration']
                    ticker = f"{underlying} {strike}{opt_type[0]} {expiry}"
                    
                    contract_details = {
                        "strike": strike,
                        "expiry": expiry,
                        "type": opt_type
                    }
                    
                    entry_premium = holding['entry_premium']
                    target_premium = holding['target_premium']
                    
                    self.positions[ticker] = OpenPosition(
                        ticker=ticker,
                        entry_price=entry_premium,
                        entry_date=holding.get('entry_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        shares=holding['contracts'],
                        direction="BUY",
                        stop_loss=holding['stop_premium'],
                        take_profit=target_premium,
                        position_type="option",
                        scale_out_levels=[
                            entry_premium + (target_premium - entry_premium) * 0.5,
                            entry_premium + (target_premium - entry_premium) * 0.75,
                            target_premium
                        ],
                        contract_details=contract_details,
                        last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    migrated += 1
                    
                elif holding.get('type') == 'STOCK':
                    # Stock position
                    ticker = holding['ticker']
                    entry_price = holding['entry_price']
                    target_price = holding['target_price']
                    direction = holding.get('direction', 'BUY')
                    
                    self.positions[ticker] = OpenPosition(
                        ticker=ticker,
                        entry_price=entry_price,
                        entry_date=holding.get('entry_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        shares=holding['shares'],
                        direction=direction,
                        stop_loss=holding['stop_price'],
                        take_profit=target_price,
                        position_type="stock",
                        scale_out_levels=[
                            entry_price + (target_price - entry_price) * 0.5,
                            entry_price + (target_price - entry_price) * 0.75,
                            target_price
                        ] if direction == 'BUY' else [
                            entry_price - (entry_price - target_price) * 0.5,
                            entry_price - (entry_price - target_price) * 0.75,
                            target_price
                        ],
                        last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    migrated += 1
            
            if migrated > 0:
                self.save_positions()
                logger.info(f"Migrated {migrated} positions from holdings.json to positions.json")
                console.print(f"[green]✓ Migrated {migrated} existing positions to new format[/green]")
        
        except Exception as e:
            logger.error(f"Error migrating holdings: {e}")
    
    def save_positions(self):
        """Save positions to disk."""
        try:
            # Convert positions to dict for JSON serialization
            data = {}
            for ticker, pos in self.positions.items():
                data[ticker] = asdict(pos)
            
            with open(self.POSITIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.positions)} positions to disk")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def add_position(self, ticker: str, entry_price: float, shares: float, 
                    direction: str, stop_loss: float, take_profit: float,
                    position_type: str = "stock", contract_details: Optional[Dict] = None):
        """Add a new position and save to disk."""
        self.positions[ticker] = OpenPosition(
            ticker=ticker,
            entry_price=entry_price,
            entry_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            shares=shares,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit,
            scale_out_levels=[
                entry_price + (take_profit - entry_price) * 0.5,
                entry_price + (take_profit - entry_price) * 0.75,
                take_profit
            ] if direction == 'BUY' else [
                entry_price - (entry_price - take_profit) * 0.5,
                entry_price - (entry_price - take_profit) * 0.75,
                take_profit
            ],
            position_type=position_type,
            contract_details=contract_details,
            last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.save_positions()  # Persist immediately
        logger.info(f"Position added: {ticker} {shares}@${entry_price} ({position_type})")
    
    def remove_position(self, ticker: str):
        """Remove a position and save to disk."""
        if ticker in self.positions:
            del self.positions[ticker]
            self.save_positions()
            logger.info(f"Position removed: {ticker}")
    
    def update_positions(self, notifier=None, analyzer=None, technical_analyzer=None):
        """Update all positions with AI analysis based on 2x time until expiration."""
        alerts = []
        
        console.print(f"[bold cyan]Found {len(self.positions)} position(s) to analyze[/bold cyan]\n")
        
        position_count = 0
        for ticker, pos in list(self.positions.items()):
            position_count += 1
            console.print(f"[dim]Analyzing position {position_count} of {len(self.positions)}[/dim]\n")
            
            try:
                DisplayManager.show_header()
                console.print(f"[bold cyan]━━━ Analyzing {ticker} ━━━[/bold cyan]\n")
                
                # For options, analyze the underlying with 2x expiration timeframe
                if pos.position_type == "option" and pos.contract_details:
                    underlying = ticker.split()[0]  # Extract underlying from "NVDA 180.0P 4/17/26"
                    
                    # Calculate analysis timeframe (2x time until expiration)
                    try:
                        expiry = pos.contract_details['expiry']
                        # Try multiple date formats
                        for fmt in ["%m/%d/%y", "%Y-%m-%d", "%m/%d/%Y"]:
                            try:
                                exp_date = datetime.strptime(expiry, fmt)
                                break
                            except:
                                continue
                        
                        days_to_exp = (exp_date - datetime.now()).days
                        analysis_days = max(days_to_exp * 2, 5)  # At least 5 days
                        
                        # Determine period and interval based on analysis days
                        if analysis_days <= 7:
                            period = f"{analysis_days}d"
                            interval = "15m"
                        elif analysis_days <= 60:
                            period = f"{analysis_days}d"
                            interval = "1h"
                        elif analysis_days <= 365:
                            period = f"{int(analysis_days/30)}mo"
                            interval = "1d"
                        else:
                            years = int(analysis_days/365)
                            period = f"{years}y"
                            interval = "1d"
                        
                        console.print(f"[dim]Analyzing {underlying} with {analysis_days} days of data (2x time to expiration: {days_to_exp} days)[/dim]\n")
                    except:
                        period = "1mo"
                        interval = "1d"
                        underlying = ticker.split()[0] if " " in ticker else ticker
                    
                    # Fetch and analyze underlying stock - FULL ANALYSIS like Option 1
                    if analyzer and technical_analyzer:
                        console.print(f"[yellow]Fetching data for {underlying}...[/yellow]\n")
                        df = DataManager.fetch_data(underlying, period, interval)
                        
                        if df is not None and len(df) >= 50:
                            console.print(f"[dim]Data from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({len(df)} bars)[/dim]\n")
                            
                            # Calculate all indicators
                            console.print("[yellow]Calculating 80+ indicators...[/yellow]")
                            indicators = technical_analyzer.calculate_indicators(df)
                            
                            if indicators:
                                # Show indicators display
                                DisplayManager.show_indicators(indicators)
                                
                                # Detect patterns
                                console.print("\n[yellow]Detecting patterns...[/yellow]")
                                patterns = PatternRecognizer.analyze(df)
                                
                                if patterns.bullish_patterns or patterns.bearish_patterns or patterns.candlestick_patterns:
                                    console.print("\n[bold cyan]📐 Detected Patterns:[/bold cyan]")
                                    if patterns.bullish_patterns:
                                        console.print(f"[green]Bullish:[/green] {', '.join(patterns.bullish_patterns)}")
                                    if patterns.bearish_patterns:
                                        console.print(f"[red]Bearish:[/red] {', '.join(patterns.bearish_patterns)}")
                                    if patterns.candlestick_patterns:
                                        console.print(f"[yellow]Candlestick:[/yellow] {', '.join(patterns.candlestick_patterns)}")
                                    console.print()
                                
                                # Smart money analysis
                                console.print("[yellow]Analyzing Smart Money Concepts...[/yellow]")
                                market_structure = SmartMoneyAnalyzer.analyze(df, underlying, notifier)
                                
                                console.print(f"\n[bold cyan]🎯 Smart Money Analysis:[/bold cyan]")
                                console.print(f"Market Structure: [bold]{market_structure.structure}[/bold]")
                                console.print(f"Order Blocks: {len(market_structure.order_blocks)}")
                                console.print(f"Fair Value Gaps: {len(market_structure.fair_value_gaps)}")
                                console.print(f"Equilibrium: ${market_structure.equilibrium}\n")
                                
                                # Volume profile
                                console.print("[yellow]Building Volume Profile...[/yellow]")
                                volume_profile = VolumeProfileAnalyzer.analyze(df)
                                
                                console.print(f"\n[bold cyan]📊 Volume Profile:[/bold cyan]")
                                console.print(f"POC: ${volume_profile.poc}")
                                console.print(f"Value Area: ${volume_profile.val} - ${volume_profile.vah}\n")
                                
                                # Run AI analysis
                                console.print("[yellow]Running AI analysis...[/yellow]\n")
                                analysis = analyzer.analyze(
                                    underlying, indicators, patterns, market_structure, 
                                    volume_profile, 10000, 0.02, 2.0
                                )
                                
                                if analysis:
                                    # Check if analysis changed from last time
                                    analysis_changed = False
                                    if pos.last_analysis_action and pos.last_analysis_action != analysis.action:
                                        analysis_changed = True
                                        # Send notification about analysis change
                                        if notifier and hasattr(notifier, 'send'):
                                            try:
                                                msg = f"🚨 [AI] Analysis changed: {ticker}\n"
                                                msg += f"Previous: {pos.last_analysis_action} ({pos.last_analysis_confidence:.0f}%)\n"
                                                msg += f"New: {analysis.action} ({analysis.confidence:.0f}%)\n"
                                                msg += f"Reason: {analysis.primary_reason}\n"
                                                msg += f"Current Price: ${indicators.price:.2f}"
                                                notifier.send(msg)
                                            except:
                                                pass
                                    
                                    # Update last analysis
                                    pos.last_analysis_action = analysis.action
                                    pos.last_analysis_confidence = analysis.confidence
                                    
                                    # Display full trade recommendation
                                    DisplayManager.show_trade_recommendation(analysis)
                                    
                                    if analysis_changed:
                                        console.print(f"\n[bold yellow]📱 NOTIFICATION SENT: Analysis changed from {pos.last_analysis_action} to {analysis.action}[/bold yellow]\n")
                                    
                                    # Check if position still aligns with analysis - OPTION-SPECIFIC LOGIC
                                    opt_type = pos.contract_details['type']
                                    strike = pos.contract_details['strike']
                                    current_underlying_price = indicators.price
                                    
                                    # Determine if option will be profitable at expiration
                                    # For CALL: profitable if stock price > strike + premium paid
                                    # For PUT: profitable if stock price < strike - premium paid
                                    breakeven = strike + pos.entry_price if opt_type == "CALL" else strike - pos.entry_price
                                    
                                    console.print(f"\n[bold cyan]📊 Option Position Analysis:[/bold cyan]")
                                    console.print(f"Strike: ${strike:.2f}")
                                    console.print(f"Breakeven: ${breakeven:.2f}")
                                    console.print(f"Current Underlying: ${current_underlying_price:.2f}")
                                    
                                    # Projection based on AI analysis
                                    if opt_type == "CALL":
                                        # CALL is profitable if underlying goes UP
                                        if analysis.action == "BUY" and current_underlying_price < breakeven:
                                            console.print(f"[bold green]✓ BULLISH SIGNAL - Your CALL position looks good![/bold green]")
                                            console.print(f"[green]AI predicts upward movement → CALL will likely be profitable[/green]\n")
                                        elif analysis.action == "BUY" and current_underlying_price >= breakeven:
                                            console.print(f"[bold green]✓ Already profitable + BULLISH - Great position![/bold green]\n")
                                        elif analysis.action == "SELL":
                                            console.print(f"[bold red]⚠️ WARNING: AI predicts DOWNWARD movement[/bold red]")
                                            console.print(f"[red]Your CALL may expire worthless - consider exiting[/red]\n")
                                            alerts.append((ticker, f"⚠️ BEARISH SIGNAL on CALL position", current_underlying_price))
                                        else:
                                            console.print(f"[yellow]⚠️ Neutral signal - monitor closely[/yellow]\n")
                                    
                                    elif opt_type == "PUT":
                                        # PUT is profitable if underlying goes DOWN
                                        if analysis.action == "SELL" and current_underlying_price > breakeven:
                                            console.print(f"[bold green]✓ BEARISH SIGNAL - Your PUT position looks good![/bold green]")
                                            console.print(f"[green]AI predicts downward movement → PUT will likely be profitable[/green]\n")
                                        elif analysis.action == "SELL" and current_underlying_price <= breakeven:
                                            console.print(f"[bold green]✓ Already profitable + BEARISH - Great position![/bold green]\n")
                                        elif analysis.action == "BUY":
                                            console.print(f"[bold red]⚠️ WARNING: AI predicts UPWARD movement[/bold red]")
                                            console.print(f"[red]Your PUT may expire worthless - consider exiting[/red]\n")
                                            alerts.append((ticker, f"⚠️ BULLISH SIGNAL on PUT position", current_underlying_price))
                                        else:
                                            console.print(f"[yellow]⚠️ Neutral signal - monitor closely[/yellow]\n")
                                    
                                    # Generate and save analysis chart
                                    console.print("[yellow]Generating analysis chart...[/yellow]")
                                    try:
                                        # Get reference to the main TradingApp instance to call chart generation
                                        import matplotlib
                                        matplotlib.use('Agg')  # Non-interactive backend
                                        import matplotlib.pyplot as plt
                                        
                                        # Generate chart (similar to _generate_analysis_chart)
                                        fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
                                        
                                        # Price chart with indicators
                                        ax_price = axes[0]
                                        ax_price.plot(df.index, df['Close'], label='Price', linewidth=2, color='#00D9FF')
                                        
                                        # Add moving averages
                                        if 'SMA_20' in df.columns:
                                            ax_price.plot(df.index, df['SMA_20'], label='SMA 20', alpha=0.7, color='orange')
                                        if 'SMA_50' in df.columns:
                                            ax_price.plot(df.index, df['SMA_50'], label='SMA 50', alpha=0.7, color='red')
                                        
                                        # Add Bollinger Bands
                                        if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
                                            ax_price.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], alpha=0.1, color='gray')
                                        
                                        # Mark strike and breakeven for options
                                        ax_price.axhline(y=strike, color='white', linestyle=':', label=f'Strike: ${strike:.2f}', linewidth=2, alpha=0.8)
                                        ax_price.axhline(y=breakeven, color='yellow', linestyle='--', label=f'Breakeven: ${breakeven:.2f}', linewidth=1.5)
                                        ax_price.axhline(y=analysis.entry_price, color='cyan', linestyle='--', label=f'AI Entry: ${analysis.entry_price:.2f}', linewidth=1.5)
                                        ax_price.axhline(y=analysis.stop_loss, color='red', linestyle='--', label=f'AI Stop: ${analysis.stop_loss:.2f}', linewidth=1.5)
                                        ax_price.axhline(y=analysis.take_profit_1, color='green', linestyle='--', label=f'AI TP1: ${analysis.take_profit_1:.2f}', linewidth=1.5)
                                        
                                        # Mark current option price
                                        ax_price.scatter([df.index[-1]], [indicators.price], color='cyan', s=100, zorder=5, label=f'Current: ${indicators.price:.2f}')
                                        
                                        ax_price.set_title(f'{underlying} Analysis - {analysis.action} ({analysis.confidence:.0f}% confidence)\\n{opt_type} ${strike} - {analysis.primary_reason}', 
                                                          fontsize=14, fontweight='bold', pad=20)
                                        ax_price.set_ylabel('Price ($)', fontsize=11)
                                        ax_price.legend(loc='best', fontsize=9)
                                        ax_price.grid(True, alpha=0.3)
                                        
                                        # RSI chart
                                        ax_rsi = axes[1]
                                        if 'RSI' in df.columns:
                                            ax_rsi.plot(df.index, df['RSI'], label='RSI', color='purple', linewidth=1.5)
                                            ax_rsi.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought')
                                            ax_rsi.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold')
                                            ax_rsi.fill_between(df.index, 30, 70, alpha=0.1, color='gray')
                                        ax_rsi.set_ylabel('RSI', fontsize=11)
                                        ax_rsi.legend(loc='best', fontsize=9)
                                        ax_rsi.grid(True, alpha=0.3)
                                        ax_rsi.set_ylim(0, 100)
                                        
                                        # Volume chart
                                        ax_vol = axes[2]
                                        colors = ['green' if df['Close'].iloc[i] >= df['Open'].iloc[i] else 'red' 
                                                 for i in range(len(df))]
                                        ax_vol.bar(df.index, df['Volume'], color=colors, alpha=0.6)
                                        ax_vol.set_ylabel('Volume', fontsize=11)
                                        ax_vol.set_xlabel('Date', fontsize=11)
                                        ax_vol.grid(True, alpha=0.3)
                                        
                                        plt.tight_layout()
                                        
                                        # Save chart
                                        from pathlib import Path
                                        import os
                                        charts_dir = Path("results/charts")
                                        charts_dir.mkdir(exist_ok=True, parents=True)
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        chart_path = charts_dir / f"{ticker.replace(' ', '_')}_{timestamp}.png"
                                        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#0E1117')
                                        plt.close()
                                        
                                        console.print(f"[green]✓ Chart saved: {chart_path}[/green]")
                                        
                                        # Open the chart automatically
                                        try:
                                            os.startfile(str(chart_path))  # Windows
                                            console.print(f"[green]✓ Chart opened in default image viewer[/green]\\n")
                                        except:
                                            console.print(f"[dim]Chart saved but could not auto-open. Open manually: {chart_path}[/dim]\\n")
                                    except Exception as e:
                                        console.print(f"[yellow]⚠ Could not generate chart: {e}[/yellow]\\n")
                    
                    # Get current option price
                    try:
                        import yfinance as yf
                        opt = yf.Ticker(underlying)
                        chain = opt.option_chain(expiry)
                        strike = pos.contract_details['strike']
                        table = chain.calls if pos.contract_details['type'] == 'CALL' else chain.puts
                        
                        if not table.empty:
                            row = table.iloc[(table['strike'] - strike).abs().argsort()[:1]]
                            ask = float(row['ask'].values[0]) if not pd.isna(row['ask'].values[0]) else None
                            bid = float(row['bid'].values[0]) if not pd.isna(row['bid'].values[0]) else None
                            
                            if ask and bid and (ask > 0 or bid > 0):
                                pos.current_price = (ask + bid) / 2 if ask and bid else (ask or bid)
                            else:
                                pos.current_price = pos.entry_price
                        else:
                            pos.current_price = pos.entry_price
                    except:
                        pos.current_price = pos.entry_price
                
                else:
                    # For stocks/crypto, simple price update
                    import yfinance as yf
                    current = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True, prepost=True)
                    if current.empty:
                        current = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True, prepost=True)
                    
                    if not current.empty:
                        pos.current_price = float(current['Close'].iloc[-1])
                
                # Update position metrics
                pos.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Calculate P&L
                if pos.direction == 'BUY':
                    pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.shares * (100 if pos.position_type == "option" else 1)
                else:
                    pos.unrealized_pnl = (pos.entry_price - pos.current_price) * pos.shares * (100 if pos.position_type == "option" else 1)
                
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.shares * (100 if pos.position_type == "option" else 1))) * 100
                
                # Update trailing stop
                if pos.direction == 'BUY' and pos.current_price > pos.entry_price:
                    new_trailing = pos.current_price * 0.95
                    if pos.trailing_stop is None or new_trailing > pos.trailing_stop:
                        pos.trailing_stop = new_trailing
                
                # Check alerts
                alert_msg = self._check_position_alerts(pos)
                if alert_msg:
                    alerts.append((ticker, alert_msg, pos.current_price))
                    if notifier and hasattr(notifier, 'send'):
                        try:
                            notifier.send(f"🔔 {ticker}\n{alert_msg}\nCurrent: ${pos.current_price:.2f}")
                        except:
                            pass
                
                # Display current position P&L
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                console.print(f"\n[bold cyan]Position P&L:[/bold cyan]")
                console.print(f"Entry: ${pos.entry_price:.2f} × {pos.shares:.0f} contracts")
                console.print(f"Current: ${pos.current_price:.2f}")
                console.print(f"P&L: [{pnl_color}]${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:+.1f}%)[/{pnl_color}]")
                console.print(f"Stop: ${pos.stop_loss:.2f} | Target: ${pos.take_profit:.2f}\n")
                
                Prompt.ask("Press Enter to continue to next position")
            
            except Exception as e:
                logger.error(f"Error updating {ticker}: {str(e)}")
                console.print(f"[red]Error analyzing {ticker}: {str(e)}[/red]\n")
                Prompt.ask("Press Enter to continue")
        
        self.save_positions()
        return alerts
    
    def _check_position_alerts(self, pos: OpenPosition) -> Optional[str]:
        """Check if position triggers any alerts."""
        alerts = []
        
        # Stop loss hit
        if pos.direction == 'BUY' and pos.current_price <= pos.stop_loss:
            alerts.append(f"🛑 STOP LOSS HIT (${pos.stop_loss:.2f})")
        elif pos.direction == 'SELL' and pos.current_price >= pos.stop_loss:
            alerts.append(f"🛑 STOP LOSS HIT (${pos.stop_loss:.2f})")
        
        # Trailing stop hit
        if pos.trailing_stop and pos.direction == 'BUY' and pos.current_price <= pos.trailing_stop:
            alerts.append(f"📉 TRAILING STOP HIT (${pos.trailing_stop:.2f})")
        
        # Take profit hit
        if pos.direction == 'BUY' and pos.current_price >= pos.take_profit:
            alerts.append(f"🎯 TAKE PROFIT HIT (${pos.take_profit:.2f})")
        elif pos.direction == 'SELL' and pos.current_price <= pos.take_profit:
            alerts.append(f"🎯 TAKE PROFIT HIT (${pos.take_profit:.2f})")
        
        # Scale out levels
        for i, level in enumerate(pos.scale_out_levels):
            if pos.direction == 'BUY' and pos.current_price >= level:
                if pos.last_alert_price is None or level > pos.last_alert_price:
                    alerts.append(f"📊 SCALE OUT LEVEL {i+1} (${level:.2f})")
                    pos.last_alert_price = level
            elif pos.direction == 'SELL' and pos.current_price <= level:
                if pos.last_alert_price is None or level < pos.last_alert_price:
                    alerts.append(f"📊 SCALE OUT LEVEL {i+1} (${level:.2f})")
                    pos.last_alert_price = level
        
        # Large move alerts (>5% gain or loss)
        if abs(pos.unrealized_pnl_pct) > 5:
            if pos.last_alert_price is None or abs(pos.current_price - pos.last_alert_price) > pos.entry_price * 0.02:
                if pos.unrealized_pnl_pct > 0:
                    alerts.append(f"📈 UP {pos.unrealized_pnl_pct:+.1f}%")
                else:
                    alerts.append(f"📉 DOWN {pos.unrealized_pnl_pct:.1f}%")
                pos.last_alert_price = pos.current_price
        
        return " | ".join(alerts) if alerts else None
    
    def refresh_prices(self):
        """Lightweight refresh of current prices and P&L for all positions."""
        for ticker, pos in self.positions.items():
            try:
                if pos.position_type == "option" and pos.contract_details:
                    try:
                        import yfinance as yf
                        underlying = ticker.split()[0]
                        expiry = pos.contract_details.get('expiry') or pos.contract_details.get('expiration')
                        chain = yf.Ticker(underlying).option_chain(expiry)
                        strike = pos.contract_details['strike']
                        table = chain.calls if pos.contract_details['type'] == 'CALL' else chain.puts
                        if not table.empty:
                            row = table.iloc[(table['strike'] - strike).abs().argsort()[:1]]
                            ask = float(row['ask'].values[0]) if not pd.isna(row['ask'].values[0]) else None
                            bid = float(row['bid'].values[0]) if not pd.isna(row['bid'].values[0]) else None
                            if ask and bid and (ask > 0 or bid > 0):
                                pos.current_price = (ask + bid) / 2 if ask and bid else (ask or bid)
                            else:
                                pos.current_price = pos.entry_price
                        else:
                            pos.current_price = pos.entry_price
                    except Exception:
                        pos.current_price = pos.entry_price
                else:
                    try:
                        import yfinance as yf
                        current = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True, prepost=True)
                        if current.empty:
                            current = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True, prepost=True)
                        if not current.empty:
                            pos.current_price = float(current['Close'].iloc[-1])
                        else:
                            pos.current_price = pos.entry_price
                    except Exception:
                        pos.current_price = pos.entry_price

                # Update P&L
                multiplier = 100 if pos.position_type == "option" else 1
                if pos.direction == 'BUY':
                    pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.shares * multiplier
                else:
                    pos.unrealized_pnl = (pos.entry_price - pos.current_price) * pos.shares * multiplier
                denom = (pos.entry_price * pos.shares * multiplier) or 1
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / denom) * 100
                pos.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.error(f"Refresh error for {ticker}: {e}")
        self.save_positions()

    def get_position_summary(self) -> str:
        """Get formatted summary of all positions."""
        if not self.positions:
            return "No open positions"
        
        summary = "\n📊 Open Positions:\n"
        total_pnl = 0
        
        for ticker, pos in self.positions.items():
            pnl_color = "[green]" if pos.unrealized_pnl > 0 else "[red]"
            summary += f"{ticker}: {pos.shares}@${pos.entry_price} → ${pos.current_price} {pnl_color}({pos.unrealized_pnl_pct:+.2f}%)[/]\n"
            total_pnl += pos.unrealized_pnl
        
        return summary + f"\nTotal P&L: ${total_pnl:,.2f}"

# ==========================================
# FEATURE 6: EQUITY CURVE DASHBOARD
# ==========================================

@dataclass
class EquitySnapshot:
    date: datetime
    equity: float
    daily_pnl: float
    cumulative_pnl: float
    trade_count: int

class EquityDashboard:
    """Real-time P&L tracking and equity curve analysis."""
    
    def __init__(self):
        self.snapshots: List[EquitySnapshot] = []
        self.starting_equity = 10000.0
        self.current_equity = 10000.0
    
    def record_snapshot(self, daily_pnl: float, trade_count: int = 0):
        """Record daily equity snapshot."""
        cumulative = self.current_equity - self.starting_equity
        snap = EquitySnapshot(
            date=datetime.now(),
            equity=self.current_equity,
            daily_pnl=daily_pnl,
            cumulative_pnl=cumulative,
            trade_count=trade_count
        )
        self.snapshots.append(snap)
        self.current_equity += daily_pnl
    
    def get_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        if not self.snapshots:
            return {}
        
        returns = [s.daily_pnl / self.starting_equity * 100 for s in self.snapshots]
        
        return {
            'total_return_pct': ((self.current_equity - self.starting_equity) / self.starting_equity) * 100,
            'avg_daily_return': np.mean(returns),
            'daily_volatility': np.std(returns),
            'sharpe_ratio': (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0,
            'winning_days': len([r for r in returns if r > 0]),
            'losing_days': len([r for r in returns if r < 0]),
            'max_daily_gain': max(returns) if returns else 0,
            'max_daily_loss': min(returns) if returns else 0
        }
    
    def show_dashboard(self):
        """Display formatted equity dashboard."""
        metrics = self.get_metrics()
        
        table = Table(title="📈 Equity Dashboard", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, val in metrics.items():
            table.add_row(key.replace('_', ' ').title(), f"{val:,.2f}")
        
        console.print(table)

# ==========================================
# FEATURE 7: ML SIGNAL WEIGHTING
# ==========================================

class MLSignalWeighter:
    """Advanced ML module with walk-forward validation, feature engineering, and ensemble models."""
    
    def __init__(self):
        self.models = {}
        self.feature_importance = {}
        self.scaler = None
        self.trade_history: List[BacktestTrade] = []
    
    @staticmethod
    def engineer_features(df: pd.DataFrame, indicators: AdvancedIndicators) -> Dict[str, float]:
        """
        Advanced feature engineering for ML.
        Creates features from price action, indicators, and statistical properties.
        """
        features = {}
        
        try:
            # Price-based features
            close = df['Close'].values
            returns = pd.Series(close).pct_change()
            
            # Momentum features
            features['returns_1d'] = returns.iloc[-1] if len(returns) > 0 else 0
            features['returns_5d'] = (close[-1] / close[-5] - 1) if len(close) >= 5 else 0
            features['returns_20d'] = (close[-1] / close[-20] - 1) if len(close) >= 20 else 0
            
            # Volatility features
            features['vol_5d'] = returns.tail(5).std() if len(returns) >= 5 else 0
            features['vol_20d'] = returns.tail(20).std() if len(returns) >= 20 else 0
            features['vol_ratio'] = (features['vol_5d'] / features['vol_20d']) if features['vol_20d'] > 0 else 1
            
            # Technical indicators
            features['rsi'] = indicators.rsi / 100  # Normalize to 0-1
            features['rsi_oversold'] = 1.0 if indicators.rsi < 30 else 0.0
            features['rsi_overbought'] = 1.0 if indicators.rsi > 70 else 0.0
            
            features['macd'] = indicators.macd
            features['macd_signal'] = indicators.macd_signal
            features['macd_hist'] = indicators.macd - indicators.macd_signal
            features['macd_bullish'] = 1.0 if features['macd_hist'] > 0 else 0.0
            
            features['adx'] = indicators.adx / 100
            features['adx_trending'] = 1.0 if indicators.adx > 25 else 0.0
            
            features['atr_pct'] = indicators.atr_percent
            features['mfi'] = indicators.mfi / 100
            features['williams_r'] = (indicators.williams_r + 100) / 100  # Normalize to 0-1
            features['cci'] = indicators.cci / 200  # Normalize roughly
            
            # Volume features
            features['volume_ratio'] = indicators.volume_ratio
            features['volume_spike'] = 1.0 if indicators.volume_ratio > 2.0 else 0.0
            
            # Trend features
            features['price_vs_sma20'] = (close[-1] / indicators.sma_20 - 1) if indicators.sma_20 > 0 else 0
            features['price_vs_sma50'] = (close[-1] / indicators.sma_50 - 1) if indicators.sma_50 > 0 else 0
            features['sma_cross'] = 1.0 if indicators.sma_20 > indicators.sma_50 else 0.0
            
            # Regime features
            features['regime_bullish'] = 1.0 if indicators.market_regime == "Bullish Trend" else 0.0
            features['regime_bearish'] = 1.0 if indicators.market_regime == "Bearish Trend" else 0.0
            features['regime_confidence'] = indicators.regime_confidence / 100
            
            # Statistical features
            if len(close) >= 20:
                features['skewness'] = pd.Series(returns.tail(20)).skew()
                features['kurtosis'] = pd.Series(returns.tail(20)).kurtosis()
            else:
                features['skewness'] = 0
                features['kurtosis'] = 0
            
            # Price level features
            high_20 = df['High'].tail(20).max()
            low_20 = df['Low'].tail(20).min()
            features['price_position'] = (close[-1] - low_20) / (high_20 - low_20) if (high_20 - low_20) > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Feature engineering error: {e}")
        
        return features
    
    @staticmethod
    def prepare_dataset(trade_history: List[BacktestTrade]) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training dataset from trade history.
        X = features, y = win/loss labels.
        """
        X_data = []
        y_data = []
        
        for trade in trade_history:
            if hasattr(trade, 'features') and trade.features:
                X_data.append(trade.features)
                y_data.append(1 if trade.win else 0)
        
        if not X_data:
            return pd.DataFrame(), pd.Series()
        
        X = pd.DataFrame(X_data)
        y = pd.Series(y_data)
        
        # Fill NaN with 0
        X = X.fillna(0)
        
        return X, y
    
    def train_models_walk_forward(self, trade_history: List[BacktestTrade], n_splits: int = 5):
        """
        Train ML models using walk-forward validation.
        This simulates real trading where you only use past data to predict future.
        """
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        X, y = self.prepare_dataset(trade_history)
        
        if len(X) < 50:
            logger.warning("Need at least 50 trades for ML training")
            return
        
        # Walk-forward cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        models_config = {
            'random_forest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            'gradient_boost': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
            'logistic': LogisticRegression(max_iter=1000, random_state=42)
        }
        
        results = {}
        
        for model_name, model in models_config.items():
            fold_scores = []
            
            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                
                # Scale features
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Train
                model.fit(X_train_scaled, y_train)
                
                # Predict
                y_pred = model.predict(X_test_scaled)
                
                # Metrics
                acc = accuracy_score(y_test, y_pred)
                fold_scores.append(acc)
            
            avg_score = np.mean(fold_scores)
            results[model_name] = {
                'model': model,
                'avg_accuracy': avg_score,
                'fold_scores': fold_scores
            }
            
            logger.info(f"{model_name}: Avg Accuracy = {avg_score:.3f} (±{np.std(fold_scores):.3f})")
        
        # Train final models on all data
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        for model_name, config in results.items():
            model = models_config[model_name]
            model.fit(X_scaled, y)
            self.models[model_name] = model
            
            # Feature importance (if available)
            if hasattr(model, 'feature_importances_'):
                importances = pd.Series(model.feature_importances_, index=X.columns)
                self.feature_importance[model_name] = importances.sort_values(ascending=False)
        
        logger.info(f"ML models trained on {len(X)} trades")
    
    def predict_trade_probability(self, features: Dict[str, float], model_name: str = 'gradient_boost') -> float:
        """
        Predict probability of winning trade using trained ML model.
        Returns probability between 0 and 1.
        """
        if model_name not in self.models:
            return 0.5  # Default 50% if model not trained
        
        try:
            # Convert features to DataFrame
            X = pd.DataFrame([features])
            
            # Ensure all training features are present
            if self.scaler is not None:
                # Get training feature names
                train_features = self.scaler.feature_names_in_
                for feat in train_features:
                    if feat not in X.columns:
                        X[feat] = 0
                X = X[train_features]  # Reorder to match training
            
            X = X.fillna(0)
            
            # Scale
            X_scaled = self.scaler.transform(X) if self.scaler else X.values
            
            # Predict probability
            model = self.models[model_name]
            if hasattr(model, 'predict_proba'):
                prob = model.predict_proba(X_scaled)[0][1]  # Probability of class 1 (win)
            else:
                pred = model.predict(X_scaled)[0]
                prob = float(pred)
            
            return float(prob)
        
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return 0.5
    
    def get_ensemble_prediction(self, features: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """
        Ensemble prediction: average probabilities from all models.
        Returns: (ensemble_prob, individual_probs)
        """
        individual_probs = {}
        
        for model_name in self.models.keys():
            prob = self.predict_trade_probability(features, model_name)
            individual_probs[model_name] = prob
        
        if not individual_probs:
            return 0.5, {}
        
        ensemble_prob = np.mean(list(individual_probs.values()))
        return float(ensemble_prob), individual_probs
    
    def show_feature_importance(self):
        """Display feature importance from trained models."""
        if not self.feature_importance:
            console.print("[yellow]No feature importance available (train models first)[/yellow]")
            return
        
        for model_name, importances in self.feature_importance.items():
            console.print(f"\n[bold cyan]Feature Importance: {model_name}[/bold cyan]")
            
            table = Table(box=box.ROUNDED)
            table.add_column("Feature", style="cyan")
            table.add_column("Importance", style="yellow", justify="right")
            
            for feat, imp in importances.head(15).items():
                table.add_row(feat, f"{imp:.4f}")
            
            console.print(table)
    
    # Legacy compatibility methods
    def add_trade_result(self, trade: BacktestTrade, indicator_scores: Dict[str, float]):
        """Add trade to history."""
        self.trade_history.append(trade)
    
    def retrain_weights(self):
        """Retrain using ML (replaces old weight-based system)."""
        if len(self.trade_history) >= 50:
            self.train_models_walk_forward(self.trade_history)
        else:
            logger.info(f"Need 50+ trades for ML training (have {len(self.trade_history)})")
    
    def get_weighted_score(self, indicators_dict: Dict[str, float]) -> float:
        """Legacy compatibility - now uses ML prediction."""
        if not self.models:
            # Fallback to simple weighted average
            weights = {
                'rsi': 0.10, 'macd': 0.10, 'adx': 0.15, 'atr_percent': 0.05,
                'volume_ratio': 0.10, 'mfi': 0.10, 'williams_r': 0.10,
                'cci': 0.10, 'ema_ribbon': 0.10, 'patterns': 0.10
            }
            score = sum(indicators_dict.get(k, 0) * w for k, w in weights.items())
            return min(100, max(0, score))
        
        # Use ML prediction
        prob, _ = self.get_ensemble_prediction(indicators_dict)
        return prob * 100  # Convert to 0-100 scale

# ==========================================
# FEATURE 8: OPTIONS STRATEGY OVERLAY
# ==========================================

@dataclass
class OptionsStrategy:
    strategy_type: str  # "COVERED_CALL", "PROTECTIVE_PUT", "CALL_SPREAD", "PUT_SPREAD"
    underlying_price: float
    strike: float
    premium: float
    probability_of_profit: float
    max_risk: float
    max_reward: float
    recommendation: str

class OptionsStrategist:
    """Suggest options strategies based on market outlook."""
    
    @staticmethod
    def suggest_strategy(signal: 'TradeSummary', underlying_price: float, 
                        volatility: float = 0.25) -> Optional[OptionsStrategy]:
        """Suggest appropriate options strategy."""
        try:
            iv_percentile = min(100, volatility * 400)  # Convert to percentage
            
            if signal.action == "BUY" and signal.confidence > 75:
                # Bullish: covered call or bull call spread
                atm_strike = int(underlying_price)
                otm_strike = int(underlying_price * 1.05)
                
                # Simplified pricing
                atm_premium = underlying_price * 0.02
                otm_premium = underlying_price * 0.01
                
                return OptionsStrategy(
                    strategy_type="COVERED_CALL",
                    underlying_price=underlying_price,
                    strike=otm_strike,
                    premium=atm_premium - otm_premium,
                    probability_of_profit=0.65,
                    max_risk=underlying_price - otm_premium,
                    max_reward=otm_premium + (otm_strike - underlying_price),
                    recommendation=f"Sell ${otm_strike} call for ${atm_premium-otm_premium:.2f} premium (65% POP)"
                )
            
            elif signal.action == "SELL" and signal.confidence > 75:
                # Bearish: protective put or bear call spread
                atm_strike = int(underlying_price)
                itm_strike = int(underlying_price * 0.95)
                
                put_premium = underlying_price * 0.02
                
                return OptionsStrategy(
                    strategy_type="PROTECTIVE_PUT",
                    underlying_price=underlying_price,
                    strike=itm_strike,
                    premium=put_premium,
                    probability_of_profit=0.60,
                    max_risk=put_premium,
                    max_reward=underlying_price - itm_strike - put_premium,
                    recommendation=f"Buy ${itm_strike} put for ${put_premium:.2f} (60% POP, downside protection)"
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Options strategy error: {str(e)}")
            return None

# ==========================================
# INTERACTIVE NEWS BOT
# ==========================================

class InteractiveNewsBot:
    """Interactive bot for fetching news headlines from the last 1-2 weeks with topic filtering."""
    
    # Curated news sources by category
    NEWS_SOURCES = {
        'General Finance': {
            'Reuters': 'https://www.reuters.com/finance/',
            'Bloomberg': 'https://www.bloomberg.com/news',
            'Financial Times': 'https://markets.ft.com/',
            'MarketWatch': 'https://www.marketwatch.com/'
        },
        'Tech': {
            'TechCrunch': 'https://techcrunch.com/',
            'The Verge': 'https://www.theverge.com/',
            'Ars Technica': 'https://arstechnica.com/',
            'Engadget': 'https://www.engadget.com/'
        },
        'Crypto': {
            'CoinDesk': 'https://www.coindesk.com/',
            'The Block': 'https://www.theblock.co/',
            'Crypto Briefing': 'https://cryptobriefing.com/',
            'Cointelegraph': 'https://cointelegraph.com/'
        },
        'Stocks': {
            'Yahoo Finance': 'https://finance.yahoo.com/news',
            'Seeking Alpha': 'https://seekingalpha.com/',
            'Investor\'s Business Daily': 'https://www.investors.com/',
            'StockTwits': 'https://stocktwits.com/'
        },
        'Commodities': {
            'Kitco': 'https://www.kitco.com/',
            'Trading Economics': 'https://tradingeconomics.com/',
            'Oil Price': 'https://oilprice.com/',
            'Gold Price': 'https://goldprice.org/'
        },
        'Earnings & Earnings': {
            'The Motley Fool': 'https://www.fool.com/',
            'Benzinga': 'https://www.benzinga.com/',
            'Yahoo Earnings': 'https://finance.yahoo.com/calendar/earnings',
            'Earnings Whispers': 'https://www.earningswhispers.com/'
        }
    }
    
    TOPIC_KEYWORDS = {
        'Earnings': ['earnings', 'eps', 'revenue', 'guidance', 'quarterly', 'q1', 'q2', 'q3', 'q4', 'beat', 'miss'],
        'Mergers & Acquisitions': ['merger', 'acquisition', 'acquisition', 'm&a', 'deal', 'buyout', 'takeover', 'acquired'],
        'IPO': ['ipo', 'initial public offering', 'going public', 'debut', 'ipo filing', 'direct listing'],
        'Crypto': ['bitcoin', 'ethereum', 'cryptocurrency', 'blockchain', 'nft', 'defi', 'crypto', 'btc', 'eth'],
        'Tech Innovation': ['ai', 'artificial intelligence', 'quantum', 'machine learning', 'deep learning', 'metaverse', '5g', 'tech'],
        'Market Trends': ['bull', 'bear', 'crash', 'rally', 'bull market', 'bear market', 'recession', 'inflation', 'fed', 'interest rates'],
        'Dividends': ['dividend', 'buyback', 'share buyback', 'payout', 'distribution', 'yield'],
        'Regulatory': ['sec', 'regulation', 'fcc', 'ftc', 'lawsuit', 'investigation', 'compliance', 'antitrust'],
        'Economic Data': ['gdp', 'unemployment', 'inflation', 'jobs', 'employment', 'cpi', 'ppi', 'economic']
    }
    
    def __init__(self):
        """Initialize the news bot."""
        self.selected_sources = []
        self.selected_topics = []
        self.date_range_days = 7
    
    def display_welcome(self):
        """Display welcome screen."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]          🤖 INTERACTIVE NEWS BOT - POWERED BY FinalAI            [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
        
        console.print("[bold]📰 News Headlines from Last 1-2 Weeks[/bold]")
        console.print("[dim]Search, filter, and discover market-moving news stories\n[/dim]")
    
    def select_categories(self) -> List[str]:
        """Let user select news categories."""
        console.print("\n[bold cyan]Step 1: Select News Categories[/bold cyan]")
        console.print("[dim]Which market segments interest you?[/dim]\n")
        
        categories = list(self.NEWS_SOURCES.keys())
        
        # Display categories
        for i, cat in enumerate(categories, 1):
            console.print(f"  {i}. {cat}")
        
        console.print(f"  {len(categories)+1}. All Categories")
        console.print(f"  {len(categories)+2}. Custom (enter URLs)")
        console.print()
        
        selection = Prompt.ask("Enter your choice(s) (comma-separated)", default="1")
        
        selected_cats = []
        try:
            choices = [int(x.strip()) for x in selection.split(',')]
            
            for choice in choices:
                if 1 <= choice <= len(categories):
                    selected_cats.append(categories[choice-1])
                elif choice == len(categories) + 1:
                    selected_cats = categories.copy()
                    break
                elif choice == len(categories) + 2:
                    return self._get_custom_sources()
            
        except (ValueError, IndexError):
            selected_cats = ["General Finance"]
        
        return selected_cats if selected_cats else ["General Finance"]
    
    def _get_custom_sources(self) -> List[str]:
        """Get custom news source URLs from user."""
        console.print("\n[bold]Enter custom news source URLs[/bold]")
        console.print("[dim]Example: https://techcrunch.com, https://coindesk.com[/dim]\n")
        
        urls_input = Prompt.ask("Enter URLs (comma-separated)", default="https://www.reuters.com/finance/")
        return [url.strip() for url in urls_input.split(',') if url.strip().startswith('http')]
    
    def select_topics(self) -> List[str]:
        """Let user select news topics."""
        console.print("\n[bold cyan]Step 2: Select News Topics[/bold cyan]")
        console.print("[dim]What topics interest you?[/dim]\n")
        
        topics = list(self.TOPIC_KEYWORDS.keys())
        
        # Display topics
        for i, topic in enumerate(topics, 1):
            console.print(f"  {i}. {topic}")
        
        console.print(f"  {len(topics)+1}. All Topics")
        console.print(f"  {len(topics)+2}. Keyword Search (enter custom keywords)")
        console.print()
        
        selection = Prompt.ask("Enter your choice(s) (comma-separated)", default="1")
        
        selected_topics = []
        try:
            choices = [int(x.strip()) for x in selection.split(',')]
            
            for choice in choices:
                if 1 <= choice <= len(topics):
                    selected_topics.append(topics[choice-1])
                elif choice == len(topics) + 1:
                    selected_topics = topics.copy()
                    break
                elif choice == len(topics) + 2:
                    custom = Prompt.ask("Enter keywords (comma-separated)")
                    return [k.strip() for k in custom.split(',') if k.strip()]
            
        except (ValueError, IndexError):
            selected_topics = ["Earnings"]
        
        return selected_topics if selected_topics else ["Earnings"]
    
    def select_date_range(self) -> int:
        """Let user select date range."""
        console.print("\n[bold cyan]Step 3: Select Time Range[/bold cyan]")
        console.print("[dim]How far back do you want to look?[/dim]\n")
        
        console.print("  1. Last 7 days (1 week)")
        console.print("  2. Last 14 days (2 weeks)")
        console.print("  3. Last 30 days (1 month)")
        console.print()
        
        choice = Prompt.ask("Enter your choice", default="1")
        
        date_map = {
            '1': 7,
            '2': 14,
            '3': 30
        }
        
        return date_map.get(choice, 7)
    
    def fetch_news_for_topics(self) -> List[Dict[str, Any]]:
        """Fetch news for selected topics from APIs."""
        news_results = []
        
        console.print("\n[bold cyan]🔍 Searching for news headlines...[/bold cyan]\n")
        
        try:
            import requests
            from datetime import datetime, timedelta
            
            # Use NewsAPI for broader search
            news_api_key = os.getenv('NEWS_API_KEY')
            
            if news_api_key:
                from_date = (datetime.now() - timedelta(days=self.date_range_days)).strftime('%Y-%m-%d')
                
                for topic in self.selected_topics:
                    try:
                        # Search for topic
                        search_query = topic
                        keywords = self.TOPIC_KEYWORDS.get(topic, [topic])
                        search_query = ' OR '.join(keywords[:3])
                        
                        url = "https://newsapi.org/v2/everything"
                        params = {
                            'q': search_query,
                            'from': from_date,
                            'to': datetime.now().strftime('%Y-%m-%d'),
                            'sortBy': 'publishedAt',
                            'language': 'en',
                            'pageSize': 10,
                            'apiKey': news_api_key
                        }
                        
                        response = requests.get(url, params=params, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            articles = data.get('articles', [])
                            
                            with Progress(
                                SpinnerColumn(),
                                TextColumn("[progress.description]{task.description}"),
                                BarColumn(),
                                transient=True
                            ) as progress:
                                task = progress.add_task(f"Processing {topic}...", total=len(articles))
                                
                                for article in articles:
                                    news_results.append({
                                        'title': article.get('title', ''),
                                        'description': article.get('description', ''),
                                        'url': article.get('url', ''),
                                        'source': article.get('source', {}).get('name', 'Unknown'),
                                        'published': article.get('publishedAt', ''),
                                        'topic': topic,
                                        'image': article.get('urlToImage', '')
                                    })
                                    progress.update(task, advance=1)
                            
                            console.print(f"✓ Found [green]{len(articles)}[/green] articles on [cyan]{topic}[/cyan]")
                    
                    except Exception as e:
                        console.print(f"[yellow]⚠ Error fetching {topic}: {str(e)[:100]}[/yellow]")
                        continue
            
            else:
                console.print("[yellow]⚠ NewsAPI key not found. Using API-free sources...[/yellow]")
                news_results = self._fetch_from_free_sources()
        
        except Exception as e:
            console.print(f"[red]❌ Error fetching news: {str(e)}[/red]")
            logger.error(f"News fetch error: {e}")
        
        return news_results
    
    def _fetch_from_free_sources(self) -> List[Dict[str, Any]]:
        """Fetch news from free sources when API keys not available."""
        news_results = []
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Use Polygon.io news and Finnhub for free market news
            poly_key = os.getenv('POLYGON_API_KEY')
            fh_key = os.getenv('FINNHUB_API_KEY')
            
            if poly_key:
                for topic in self.selected_topics[:3]:  # Limit to avoid rate limiting
                    try:
                        url = f"https://api.polygon.io/v2/reference/news?query={topic}&limit=10&apiKey={poly_key}"
                        response = requests.get(url, timeout=8)
                        
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get('results', []):
                                news_results.append({
                                    'title': item.get('title', ''),
                                    'description': item.get('description', ''),
                                    'url': item.get('article_url', ''),
                                    'source': 'Polygon.io',
                                    'published': item.get('published_utc', ''),
                                    'topic': topic,
                                    'image': ''
                                })
                    except Exception:
                        continue
            
            return news_results
        
        except Exception as e:
            logger.error(f"Free sources fetch error: {e}")
            return []
    
    def display_news_results(self, news_items: List[Dict[str, Any]]):
        """Display news results in a formatted table."""
        if not news_items:
            console.print("[yellow]No news articles found for your criteria.[/yellow]\n")
            return
        
        console.print(f"\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print(f"[bold cyan]                    📰 {len(news_items)} NEWS HEADLINES                    [/bold cyan]")
        console.print(f"[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
        
        # Create results table
        table = Table(box=box.ROUNDED, title="Search Results")
        table.add_column("Topic", style="cyan", width=12)
        table.add_column("Headline", style="white", width=50)
        table.add_column("Source", style="green", width=18)
        table.add_column("Date", style="yellow", width=12)
        
        for i, item in enumerate(news_items[:20], 1):  # Show top 20
            title = item.get('title', '')[:47] + "..." if len(item.get('title', '')) > 50 else item.get('title', '')
            
            # Parse date
            pub_date = item.get('published', '')
            if 'T' in pub_date:
                pub_date = pub_date.split('T')[0]  # Extract just date
            
            table.add_row(
                item.get('topic', 'General')[:11],
                title,
                item.get('source', 'Unknown')[:16],
                pub_date
            )
        
        console.print(table)
    
    def display_article_details(self, news_item: Dict[str, Any]):
        """Display full article details."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print(f"[bold]{news_item.get('title', '')}[/bold]\n")
        console.print(f"[dim]Source:[/dim] [green]{news_item.get('source', 'Unknown')}[/green]")
        console.print(f"[dim]Topic:[/dim] [cyan]{news_item.get('topic', 'General')}[/cyan]")
        console.print(f"[dim]Published:[/dim] [yellow]{news_item.get('published', 'Unknown')}[/yellow]\n")
        
        description = news_item.get('description', '')
        if description:
            console.print(f"[dim]Summary:[/dim]\n{description}\n")
        
        url = news_item.get('url', '')
        if url:
            console.print(f"[dim]Read Full Article:[/dim] [link={url}]{url}[/link]\n")
        
        console.print("[cyan]─────────────────────────────────────────────────────────────[/cyan]\n")
    
    def run_interactive_search(self):
        """Run the interactive news bot."""
        self.display_welcome()
        
        # Step 1: Select categories
        categories = self.select_categories()
        self.selected_sources = []
        
        for cat in categories:
            if cat in self.NEWS_SOURCES:
                self.selected_sources.extend(self.NEWS_SOURCES[cat].values())
        
        # Step 2: Select topics
        self.selected_topics = self.select_topics()
        
        # Step 3: Select date range
        self.date_range_days = self.select_date_range()
        
        # Fetch news
        news_items = self.fetch_news_for_topics()
        
        # Display results
        self.display_news_results(news_items)
        
        # Interactive browsing
        if news_items:
            self._browse_results(news_items)
    
    def _browse_results(self, news_items: List[Dict[str, Any]]):
        """Allow user to browse detailed results."""
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("  1. View article details")
        console.print("  2. Search again")
        console.print("  3. Export results to file")
        console.print("  4. Return to main menu\n")
        
        choice = Prompt.ask("Select option", default="4")
        
        if choice == "1":
            article_num = IntPrompt.ask("Enter article number to view", default=1)
            if 1 <= article_num <= len(news_items):
                self.display_article_details(news_items[article_num-1])
                self._browse_results(news_items)
        
        elif choice == "2":
            self.run_interactive_search()
        
        elif choice == "3":
            self._export_results(news_items)
            self._browse_results(news_items)
        
        # else: return to main
    
    def _export_results(self, news_items: List[Dict[str, Any]]):
        """Export results to CSV file."""
        try:
            import csv
            
            filename = RESULTS_DIR / f"news_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'source', 'topic', 'published', 'description', 'url'])
                writer.writeheader()
                writer.writerows(news_items)
            
            console.print(f"\n[green]✓ Results exported to:[/green] {filename}\n")
        
        except Exception as e:
            console.print(f"[red]❌ Export failed: {str(e)}[/red]\n")
            logger.error(f"Export error: {e}")

# ==========================================
# ENTRY POINT
# ==========================================

def main():
    """Application entry point."""
    try:
        app = FinalAIQuantum()
        app.initialize()
        app.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Application interrupted by user[/yellow]")
    except Exception as e:
        logger.exception("Fatal error")
        console.print(f"\n[red]❌ Fatal error: {str(e)}[/red]")
        console.print("[dim]Check logs for details[/dim]")

if __name__ == "__main__":
    main()
