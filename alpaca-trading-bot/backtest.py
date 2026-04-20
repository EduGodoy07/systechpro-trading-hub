# -*- coding: utf-8 -*-
"""
Backtesting Script for Trading Strategy
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from simple_strategy import compute_indicators, generate_signal, calc_sl_tp, position_size_from_atr, make_trade_record
from config import STOCK_SYMBOL, SLIPPAGE, COMMISSION, MAX_TRADES_PER_DAY, DRAWDOWN_LIMIT


def run_backtest(symbol: str = STOCK_SYMBOL, start: str = '2020-01-01', end: str = None, account_balance: float = 100000.0):
    end = end or datetime.now().strftime('%Y-%m-%d')
    df = yf.download(symbol, start=start, end=end)
    if df.empty:
        raise ValueError('No data downloaded for symbol')

    df = compute_indicators(df)

    balance = account_balance
    position = 0
    entry_price = 0.0
    entry_date = None
    equity_curve = []
    trades_today = 0
    last_date = None
    trades = []

    for i in range(len(df.index)):
        current_date = df.index[i].date()
        if last_date is None or current_date != last_date:
            trades_today = 0
            last_date = current_date

        if i < max(50, 60):
            equity_curve.append(balance + position * df['Close'].iloc[i])
            continue

        # early stop if drawdown exceeded
        current_equity = balance + position * df['Close'].iloc[i]
        peak_equity = max(equity_curve) if equity_curve else current_equity
        if peak_equity > 0 and (peak_equity - current_equity) / peak_equity > DRAWDOWN_LIMIT:
            print('Drawdown limit exceeded. Stopping backtest.')
            break

        window = df.iloc[: i + 1]
        signal = generate_signal(window)
        price = df['Close'].iloc[i]
        atr = df['atr'].iloc[i] if 'atr' in df.columns else None

        # apply slippage to execution price
        if signal == 'buy':
            exec_price = price * (1 + SLIPPAGE)
        elif signal == 'sell':
            exec_price = price * (1 - SLIPPAGE)
        else:
            exec_price = price

        # check trades per day
        if trades_today >= MAX_TRADES_PER_DAY:
            signal = 'hold'

        if signal == 'buy' and position == 0 and trades_today < MAX_TRADES_PER_DAY:
            size = position_size_from_atr(balance, price, atr)
            cost = exec_price * size + COMMISSION
            if cost <= balance:
                position = size
                entry_price = exec_price
                entry_date = df.index[i]
                balance -= cost
                trades_today += 1
        elif signal == 'sell' and position > 0:
            proceeds = exec_price * position - COMMISSION
            balance += proceeds
            trades.append(make_trade_record(entry_date, entry_price, df.index[i], exec_price, position, COMMISSION, 'signal_exit'))
            position = 0
            entry_price = 0
            entry_date = None
            trades_today += 1

        # check SL/TP intraday simplistic: if low <= sl -> exit, if high >= tp -> exit
        if position > 0:
            sl, tp = calc_sl_tp(entry_price, atr if atr is not None else 0)
            low = df['Low'].iloc[i]
            high = df['High'].iloc[i]
            exited = False
            if low <= sl:
                # hit stop loss
                exit_price = sl * (1 - SLIPPAGE)
                balance += exit_price * position - COMMISSION
                trades.append(make_trade_record(entry_date, entry_price, df.index[i], exit_price, position, COMMISSION, 'stop_loss'))
                position = 0
                entry_price = 0
                entry_date = None
                trades_today += 1
                exited = True
            elif high >= tp:
                exit_price = tp * (1 - SLIPPAGE)
                balance += exit_price * position - COMMISSION
                trades.append(make_trade_record(entry_date, entry_price, df.index[i], exit_price, position, COMMISSION, 'take_profit'))
                position = 0
                entry_price = 0
                entry_date = None
                trades_today += 1
                exited = True

        equity_curve.append(balance + position * df['Close'].iloc[i])

    equity = pd.Series(equity_curve, index=df.index[: len(equity_curve)])
    returns = equity.pct_change().fillna(0)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    cum_returns = (1 + returns).cumprod() - 1
    max_drawdown = (cum_returns.cummax() - cum_returns).max()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

    trades_df = pd.DataFrame(trades)

    metrics = {
        'start_balance': account_balance,
        'end_balance': equity.iloc[-1] if len(equity) > 0 else balance,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe,
        'num_trades': len(trades_df),
        'trades': trades_df,
    }
    return equity, metrics


if __name__ == '__main__':
    eq, mets = run_backtest()
    print('Metrics:', {k: v for k, v in mets.items() if k != 'trades'})
    if 'trades' in mets:
        print(mets['trades'].head())
