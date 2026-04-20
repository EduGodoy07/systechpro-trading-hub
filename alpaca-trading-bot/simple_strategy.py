"""Simple strategy utilities: RSI + MA crossover + ATR stops"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import AverageTrueRange
from config import MA_SHORT, MA_LONG, RSI_PERIOD, ATR_PERIOD, ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER, TRADE_QUANTITY


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute MA, RSI, ATR indicators in-place and return df."""
    df = df.copy()
    df['ma_short'] = df['Close'].rolling(MA_SHORT).mean()
    df['ma_long'] = df['Close'].rolling(MA_LONG).mean()

    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(RSI_PERIOD).mean()
    loss = -delta.clip(upper=0).rolling(RSI_PERIOD).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR (using typical price)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(ATR_PERIOD).mean()

    return df


def generate_signal(df: pd.DataFrame) -> str:
    """Generate a simple buy/sell/hold signal based on MA crossover and RSI confirmation."""
    if df['ma_short'].iloc[-1] > df['ma_long'].iloc[-1] and df['ma_short'].iloc[-2] <= df['ma_long'].iloc[-2]:
        # potential buy if RSI not overbought
        if df['rsi'].iloc[-1] < 70:
            return 'buy'
    if df['ma_short'].iloc[-1] < df['ma_long'].iloc[-1] and df['ma_short'].iloc[-2] >= df['ma_long'].iloc[-2]:
        # potential sell/exit
        if df['rsi'].iloc[-1] > 30:
            return 'sell'
    return 'hold'


def calc_sl_tp(price: float, atr: float) -> Tuple[float, float]:
    """Calculate stop-loss and take-profit using ATR multipliers."""
    sl = price - ATR_SL_MULTIPLIER * atr
    tp = price + ATR_TP_MULTIPLIER * atr
    return sl, tp


def position_size_from_atr(account_balance: float, price: float, atr: float, risk_per_trade: float = 0.01, min_shares: int = 1, max_shares: Optional[int] = 1000) -> int:
    """Calculate position size using ATR-based stop distance with min/max caps and rounding.

    - Ensures integer share sizes
    - Applies min_shares and max_shares limits
    - Returns at least 1 share
    """
    if atr is None or atr <= 0:
        return int(max(1, TRADE_QUANTITY))

    dollar_risk = account_balance * risk_per_trade
    stop_distance = ATR_SL_MULTIPLIER * atr
    if stop_distance <= 0:
        return int(max(1, TRADE_QUANTITY))

    raw_size = dollar_risk / stop_distance
    size = int(max(min_shares, np.floor(raw_size)))
    if max_shares is not None:
        size = min(size, max_shares)
    return int(max(1, size))


# Trade report helper
def make_trade_record(entry_date, entry_price, exit_date, exit_price, size, commission, reason):
    pnl = (exit_price - entry_price) * size - commission
    return {
        'entry_date': entry_date,
        'entry_price': entry_price,
        'exit_date': exit_date,
        'exit_price': exit_price,
        'size': size,
        'pnl': pnl,
        'reason': reason,
    }
