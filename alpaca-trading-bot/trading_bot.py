# -*- coding: utf-8 -*-
"""
Alpaca Trading Bot - Fase 1
Strategy: RSI + Moving Average Crossover
"""
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import alpaca_trade_api as tradeapi
from config import API_KEY, API_SECRET, BASE_URL, validate_keys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Trading Bot with RSI + MA Crossover Strategy"""
    
    def __init__(self, symbols=['AAPL'], position_size=0.05, stop_loss_pct=0.02, take_profit_pct=0.05):
        """
        Initialize the trading bot
        
        Args:
            symbols: List of stock symbols to trade
            position_size: Percentage of portfolio per trade (0.05 = 5%)
            stop_loss_pct: Stop loss percentage (0.02 = 2%)
            take_profit_pct: Take profit percentage (0.05 = 5%)
        """
        self.api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
        self.symbols = symbols
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Strategy parameters
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_short = 50
        self.ma_long = 200
        
        logger.info(f"🤖 Trading Bot initialized")
        logger.info(f"📊 Symbols: {symbols}")
        logger.info(f"💰 Position Size: {position_size*100}% per trade")
        logger.info(f"🛡️ Stop Loss: {stop_loss_pct*100}%")
        logger.info(f"🎯 Take Profit: {take_profit_pct*100}%")
    
    def get_account_info(self):
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power)
            }
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return None
    
    def get_historical_data(self, symbol, days=250):
        """
        Get historical price data
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
        """
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            
            bars = self.api.get_bars(
                symbol,
                tradeapi.TimeFrame.Day,
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d')
            ).df
            
            if bars.empty:
                logger.warning(f"⚠️ No data available for {symbol}")
                return None
            
            # Reset index to have timestamp as column
            bars = bars.reset_index()
            return bars
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """
        Calculate technical indicators
        
        Args:
            df: DataFrame with OHLCV data
        """
        try:
            # RSI
            rsi_indicator = RSIIndicator(close=df['close'], window=self.rsi_period)
            df['rsi'] = rsi_indicator.rsi()
            
            # Moving Averages
            sma_short = SMAIndicator(close=df['close'], window=self.ma_short)
            sma_long = SMAIndicator(close=df['close'], window=self.ma_long)
            df['ma_short'] = sma_short.sma_indicator()
            df['ma_long'] = sma_long.sma_indicator()
            
            # MA Crossover signals
            df['ma_cross'] = 0
            df.loc[df['ma_short'] > df['ma_long'], 'ma_cross'] = 1  # Bullish
            df.loc[df['ma_short'] < df['ma_long'], 'ma_cross'] = -1  # Bearish
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error calculating indicators: {e}")
            return None
    
    def generate_signal(self, df):
        """
        Generate trading signal based on strategy
        
        Strategy:
        - BUY: RSI < 30 (oversold) AND MA50 > MA200 (bullish trend)
        - SELL: RSI > 70 (overbought) OR MA50 < MA200 (bearish trend)
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            'buy', 'sell', or 'hold'
        """
        if df is None or df.empty:
            return 'hold'
        
        # Get latest values
        latest = df.iloc[-1]
        rsi = latest['rsi']
        ma_cross = latest['ma_cross']
        
        # Check for valid data
        if pd.isna(rsi) or pd.isna(ma_cross):
            logger.warning("⚠️ Insufficient data for signal generation")
            return 'hold'
        
        # Generate signal
        if rsi < self.rsi_oversold and ma_cross == 1:
            logger.info(f"📈 BUY Signal: RSI={rsi:.2f}, MA Cross=Bullish")
            return 'buy'
        elif rsi > self.rsi_overbought or ma_cross == -1:
            logger.info(f"📉 SELL Signal: RSI={rsi:.2f}, MA Cross={'Bearish' if ma_cross == -1 else 'N/A'}")
            return 'sell'
        else:
            return 'hold'
    
    def get_position(self, symbol):
        """Get current position for symbol"""
        try:
            positions = self.api.list_positions()
            for position in positions:
                if position.symbol == symbol:
                    return {
                        'qty': float(position.qty),
                        'avg_entry_price': float(position.avg_entry_price),
                        'current_price': float(position.current_price),
                        'unrealized_pl': float(position.unrealized_pl),
                        'unrealized_plpc': float(position.unrealized_plpc)
                    }
            return None
        except Exception as e:
            logger.error(f"❌ Error getting position: {e}")
            return None
    
    def calculate_position_size(self, symbol, current_price):
        """Calculate number of shares to buy based on position size"""
        account = self.get_account_info()
        if not account:
            return 0
        
        # Calculate dollar amount to invest
        cash_to_invest = account['cash'] * self.position_size
        
        # Calculate number of shares
        shares = int(cash_to_invest / current_price)
        
        logger.info(f"💵 Cash available: ${account['cash']:.2f}")
        logger.info(f"💰 Investing: ${cash_to_invest:.2f} ({self.position_size*100}% of cash)")
        logger.info(f"📦 Shares to buy: {shares}")
        
        return shares
    
    def place_order(self, symbol, qty, side):
        """
        Place a market order
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: 'buy' or 'sell'
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='day'
            )
            logger.info(f"✅ Order placed: {side.upper()} {qty} shares of {symbol}")
            logger.info(f"📋 Order ID: {order.id}")
            return order
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    def check_stop_loss_take_profit(self, symbol, position):
        """Check if stop loss or take profit is hit"""
        if not position:
            return False
        
        unrealized_plpc = position['unrealized_plpc']
        
        # Check stop loss
        if unrealized_plpc <= -self.stop_loss_pct:
            logger.warning(f"🛑 STOP LOSS hit for {symbol}: {unrealized_plpc*100:.2f}%")
            return True
        
        # Check take profit
        if unrealized_plpc >= self.take_profit_pct:
            logger.info(f"🎯 TAKE PROFIT hit for {symbol}: {unrealized_plpc*100:.2f}%")
            return True
        
        return False
    
    def execute_strategy(self):
        """Execute trading strategy for all symbols"""
        logger.info("\n" + "="*50)
        logger.info(f"🔄 Executing strategy at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*50)
        
        # Check market status
        clock = self.api.get_clock()
        if not clock.is_open:
            logger.info("🔒 Market is closed. Waiting for market open...")
            return
        
        # Get account info
        account = self.get_account_info()
        if account:
            logger.info(f"💰 Portfolio Value: ${account['portfolio_value']:.2f}")
            logger.info(f"💵 Cash: ${account['cash']:.2f}")
        
        # Process each symbol
        for symbol in self.symbols:
            logger.info(f"\n📊 Analyzing {symbol}...")
            
            # Get current position
            position = self.get_position(symbol)
            
            # Check stop loss / take profit
            if position:
                logger.info(f"📍 Current Position: {position['qty']} shares @ ${position['avg_entry_price']:.2f}")
                logger.info(f"📈 Current Price: ${position['current_price']:.2f}")
                logger.info(f"💹 Unrealized P/L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']*100:.2f}%)")
                
                if self.check_stop_loss_take_profit(symbol, position):
                    # Close position
                    self.place_order(symbol, int(position['qty']), 'sell')
                    continue
            
            # Get historical data
            df = self.get_historical_data(symbol)
            if df is None:
                continue
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            if df is None:
                continue
            
            # Generate signal
            signal = self.generate_signal(df)
            
            current_price = df.iloc[-1]['close']
            logger.info(f"💲 Current Price: ${current_price:.2f}")
            logger.info(f"📊 RSI: {df.iloc[-1]['rsi']:.2f}")
            logger.info(f"📈 MA50: ${df.iloc[-1]['ma_short']:.2f}")
            logger.info(f"📉 MA200: ${df.iloc[-1]['ma_long']:.2f}")
            logger.info(f"🎯 Signal: {signal.upper()}")
            
            # Execute trades based on signal
            if signal == 'buy' and not position:
                qty = self.calculate_position_size(symbol, current_price)
                if qty > 0:
                    self.place_order(symbol, qty, 'buy')
            
            elif signal == 'sell' and position:
                self.place_order(symbol, int(position['qty']), 'sell')
    
    def run(self, interval=300):
        """
        Run the trading bot continuously
        
        Args:
            interval: Time between checks in seconds (default: 300 = 5 minutes)
        """
        logger.info("\n🚀 Starting Trading Bot...")
        logger.info(f"⏰ Check interval: {interval} seconds ({interval/60:.1f} minutes)")
        
        try:
            while True:
                try:
                    self.execute_strategy()
                except Exception as e:
                    logger.error(f"❌ Error in strategy execution: {e}")
                
                logger.info(f"\n⏳ Waiting {interval} seconds until next check...\n")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n⛔ Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    # Validate API keys before starting long-running bot
    try:
        validate_keys()
    except Exception as e:
        logger.error(f"❌ {e}")
        raise

    # Create bot with multiple symbols
    bot = TradingBot(
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        position_size=0.05,  # 5% of portfolio per trade
        stop_loss_pct=0.02,  # 2% stop loss
        take_profit_pct=0.05  # 5% take profit
    )
    
    # Run the bot (checks every 5 minutes)
    bot.run(interval=300)
