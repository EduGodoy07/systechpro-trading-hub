import pandas as pd
import numpy as np
import backtest as bt
from backtest import run_backtest
import pytest


def make_sample_df():
    dates = pd.date_range('2021-01-01', periods=120, freq='D')
    np.random.seed(1)
    price = np.cumsum(np.random.randn(120)) + 100
    df = pd.DataFrame({'Open': price, 'High': price + 1, 'Low': price - 1, 'Close': price}, index=dates)
    return df


@pytest.mark.skip(reason="Network test - requires yfinance/data download. Skipped by default. Set RUN_NETWORK_TESTS=1 and remove skip to enable.")
def test_run_backtest_short():
    eq, mets = run_backtest(start='2021-01-01', end='2021-06-01')
    assert 'total_return' in mets
    assert 'max_drawdown' in mets
    assert 'sharpe' in mets
    assert len(eq) > 0


def test_run_backtest_with_mock(monkeypatch):
    sample = make_sample_df()

    def fake_download(symbol, start, end):
        return sample

    # Patch the yfinance download used in backtest module
    monkeypatch.setattr(bt.yf, 'download', fake_download)

    eq, mets = bt.run_backtest(start='2021-01-01', end='2021-05-01')
    assert 'total_return' in mets
    assert 'max_drawdown' in mets
    assert 'sharpe' in mets
    assert len(eq) > 0
    # trades DataFrame should exist in metrics
    assert 'trades' in mets
    assert isinstance(mets['trades'], type(pd.DataFrame()))
