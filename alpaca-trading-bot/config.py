# Try to load dotenv if available, but avoid hard failure when the package is not installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # define a no-op load_dotenv so code that calls it won't fail
    def load_dotenv():
        return None

import os
from typing import Optional

# Load Alpaca API keys from environment variables for safety
API_KEY = os.getenv('APCA_API_KEY_ID') or os.getenv('API_KEY')
API_SECRET = os.getenv('APCA_API_SECRET_KEY') or os.getenv('API_SECRET')

# Alpaca Base URL (paper by default)
BASE_URL = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

# Trading Parameters (can be overridden via env)
STOCK_SYMBOL = os.getenv('STOCK_SYMBOL', 'AAPL')  # Stock to trade
TRADE_QUANTITY = int(os.getenv('TRADE_QUANTITY', '1'))     # Number of shares per trade

# Strategy parameters (defaults can be tuned via env)
MA_SHORT = int(os.getenv('MA_SHORT', '20'))
MA_LONG = int(os.getenv('MA_LONG', '50'))
RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
ATR_PERIOD = int(os.getenv('ATR_PERIOD', '14'))
ATR_SL_MULTIPLIER = float(os.getenv('ATR_SL_MULTIPLIER', '2.0'))
ATR_TP_MULTIPLIER = float(os.getenv('ATR_TP_MULTIPLIER', '3.0'))

# Risk management
MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '5'))
DRAWDOWN_LIMIT = float(os.getenv('DRAWDOWN_LIMIT', '0.15'))  # 15% drawdown
SAFE_TRADING_START = os.getenv('SAFE_TRADING_START', '09:45')  # HH:MM local/market time
SAFE_TRADING_END = os.getenv('SAFE_TRADING_END', '15:50')

# Execution assumptions
SLIPPAGE = float(os.getenv('SLIPPAGE', '0.001'))  # 0.1% default slippage
COMMISSION = float(os.getenv('COMMISSION', '0.0'))  # default commission per trade

# Helper: validate keys at runtime
def validate_keys(raise_on_missing: bool = True) -> bool:
    """Return True if API keys are present. Optionally raise an error when missing."""
    present = bool(API_KEY and API_SECRET)
    if not present and raise_on_missing:
        raise RuntimeError(
            "Alpaca API keys not set. Set environment variables APCA_API_KEY_ID and APCA_API_SECRET_KEY or update config.py"
        )
    return present
