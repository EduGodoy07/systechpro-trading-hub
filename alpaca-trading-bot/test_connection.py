# -*- coding: utf-8 -*-
"""
Test Alpaca API Connection
Run this after adding your API keys to config.py
"""
import alpaca_trade_api as tradeapi
from config import API_KEY, API_SECRET, BASE_URL

def test_connection():
    """Test if Alpaca API credentials work"""
    try:
        # Initialize API
        api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
        
        # Get account info
        account = api.get_account()
        
        print("✅ Connection successful!")
        print(f"\n📊 Account Info:")
        print(f"  - Status: {account.status}")
        print(f"  - Cash: ${float(account.cash):,.2f}")
        print(f"  - Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"  - Buying Power: ${float(account.buying_power):,.2f}")
        
        # Test market data
        print(f"\n📈 Testing market data...")
        barset = api.get_bars("AAPL", tradeapi.TimeFrame.Day, limit=1)
        latest_bar = barset[0]
        print(f"  - AAPL latest close: ${latest_bar.c:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print("\n🔧 Make sure you:")
        print("  1. Created an Alpaca account at https://alpaca.markets")
        print("  2. Got your Paper Trading API keys")
        print("  3. Updated config.py with your keys")
        return False

if __name__ == "__main__":
    test_connection()
