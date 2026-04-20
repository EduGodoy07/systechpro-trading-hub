import pytest
import pandas as pd
import numpy as np
from simple_strategy import compute_indicators, position_size_from_atr


def make_sample_df():
    dates = pd.date_range('2021-01-01', periods=100, freq='D')
    np.random.seed(0)
    price = np.cumsum(np.random.randn(100)) + 100
    df = pd.DataFrame({'Open': price, 'High': price + 1, 'Low': price - 1, 'Close': price}, index=dates)
    return df


def test_compute_indicators_basic():
    df = make_sample_df()
    res = compute_indicators(df)
    assert 'ma_short' in res.columns
    assert 'ma_long' in res.columns
    assert 'rsi' in res.columns
    assert 'atr' in res.columns


def test_position_size_from_atr():
    size = position_size_from_atr(100000, 100, 1.5, risk_per_trade=0.01, min_shares=1, max_shares=1000)
    assert isinstance(size, int)
    assert size >= 1
