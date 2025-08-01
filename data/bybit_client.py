"""
Bybit API client for data collection and trading operations.
Handles real-time price feeds, historical data, and order management using official pybit SDK.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from loguru import logger
from pybit.unified_trading import HTTP

from config.config import config


class BybitClient:
    """Bybit API client for data collection and trading using official pybit SDK."""
    
    def __init__(self):
        """Initialize Bybit client."""
        self.session = HTTP(
            testnet=config.bybit.testnet,
            api_key=config.bybit.api_key,
            api_secret=config.bybit.api_secret,
        )
        
        logger.info(f"Initialized Bybit client (testnet: {config.bybit.testnet})")
    
    def get_ticker(self, symbol: str, category: str = "linear") -> Dict:
        """Get current ticker for a symbol."""
        try:
            ticker = self.session.get_tickers(category=category, symbol=symbol)
            
            if ticker and 'result' in ticker and 'list' in ticker['result']:
                ticker_data = ticker['result']['list'][0]
                return {
                    'symbol': symbol,
                    'bid': float(ticker_data.get('bid1Price', 0)),
                    'ask': float(ticker_data.get('ask1Price', 0)),
                    'last': float(ticker_data.get('lastPrice', 0)),
                    'volume': float(ticker_data.get('volume24h', 0)),
                    'timestamp': int(ticker_data.get('timestamp', 0))
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {}
    
    def get_ohlcv(self, symbol: str, interval: str = '1', 
                   limit: int = 1000, start_time: Optional[int] = None,
                   category: str = "linear") -> pd.DataFrame:
        """
        Get OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            interval: Timeframe ('1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M')
            limit: Number of candles to fetch (max 1000)
            start_time: Timestamp to fetch from
            category: Product type ('linear', 'inverse', 'spot', 'option')
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            klines = self.session.get_kline(
                category=category,
                symbol=symbol,
                interval=interval,
                limit=limit,
                start=start_time
            )
            
            if klines and 'result' in klines and 'list' in klines['result']:
                data = klines['result']['list']
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                # Convert timestamp to numeric before using pd.to_datetime with unit parameter
                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
                df['symbol'] = symbol
                
                # Convert string values to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                df.set_index('timestamp', inplace=True)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_historical_data(self, symbol: str, interval: str = '60',
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           category: str = "linear") -> pd.DataFrame:
        """
        Get historical data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            interval: Timeframe ('1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M')
            start_date: Start date for data
            end_date: End date for data
            category: Product type ('linear', 'inverse', 'spot', 'option')
            
        Returns:
            DataFrame with historical data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=config.trading.backtest_period_years * 365)
        
        if end_date is None:
            end_date = datetime.now()
        
        all_data = []
        current_date = start_date
        
        chunk_count = 0
        while current_date < end_date:
            try:
                start_timestamp = int(current_date.timestamp() * 1000)
                
                df_chunk = self.get_ohlcv(symbol, interval, limit=1000, 
                                         start_time=start_timestamp, category=category)
                
                if df_chunk.empty:
                    logger.info(f"No more data available for {symbol} at {current_date}")
                    break
                
                all_data.append(df_chunk)
                chunk_count += 1
                
                # Calculate the appropriate time increment based on interval
                # We want to advance by the amount of data we just fetched to avoid overlap
                if interval.isdigit():
                    # Numeric intervals are in minutes
                    minutes = int(interval)
                    # Advance by 1000 candles worth of time (since we fetched 1000 candles)
                    hours = (minutes * 1000) / 60  # Convert minutes to hours
                    current_date = df_chunk.index[-1] + pd.Timedelta(hours=hours)
                elif interval == 'D':
                    # Advance by 1000 days
                    current_date = df_chunk.index[-1] + pd.Timedelta(days=1000)
                elif interval == 'W':
                    # Advance by 1000 weeks
                    current_date = df_chunk.index[-1] + pd.Timedelta(weeks=1000)
                elif interval == 'M':
                    # Advance by approximately 1000 months
                    current_date = df_chunk.index[-1] + pd.Timedelta(days=1000*30)
                else:
                    # Default fallback - advance by 1000 hours
                    current_date = df_chunk.index[-1] + pd.Timedelta(hours=1000)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}")
                break
        
        if all_data:
            combined_df = pd.concat(all_data)
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            logger.info(f"Collected {len(combined_df)} total records for {symbol} in {chunk_count} chunks")
            return combined_df
        
        logger.warning(f"No data collected for {symbol}")
        return pd.DataFrame()
    
    def get_orderbook(self, symbol: str, limit: int = 20, category: str = "linear") -> Dict:
        """Get order book for a symbol."""
        try:
            orderbook = self.session.get_orderbook(
                category=category,
                symbol=symbol,
                limit=limit
            )
            
            if orderbook and 'result' in orderbook:
                return {
                    'symbol': symbol,
                    'bids': orderbook['result'].get('b', []),
                    'asks': orderbook['result'].get('a', []),
                    'timestamp': orderbook['result'].get('ts', 0)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return {}
    
    def get_trading_pairs(self, category: str = "linear") -> List[str]:
        """Get available trading pairs from Bybit."""
        try:
            instruments = self.session.get_instruments_info(category=category)
            
            if instruments and 'result' in instruments and 'list' in instruments['result']:
                symbols = [item['symbol'] for item in instruments['result']['list']]
                return symbols
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching trading pairs: {e}")
            return []
    
    def check_symbols_availability(self, symbols: List[str], category: str = "linear") -> Dict[str, bool]:
        """
        Check availability of multiple symbols on Bybit using get_tickers.
        
        Args:
            symbols: List of symbols to check
            category: Product type ('linear', 'inverse', 'spot', 'option')
            
        Returns:
            Dictionary mapping symbol to availability status
        """
        availability = {}
        
        for symbol in symbols:
            availability[symbol] = self.check_symbol_availability(symbol, category)
        
        available_count = sum(availability.values())
        logger.info(f"Checked {len(symbols)} symbols: {available_count} available")
        return availability
    
    def check_symbol_availability(self, symbol: str, category: str = "linear") -> bool:
        """Check if a single symbol is available for trading using get_tickers."""
        try:
            ticker = self.session.get_tickers(category=category, symbol=symbol)
            
            if ticker and 'result' in ticker and 'list' in ticker['result'] and ticker['result']['list']:
                return True
            else:
                logger.warning(f"Symbol {symbol} not available on Bybit")
                return False
                
        except Exception as e:
            logger.debug(f"Symbol {symbol} not available: {e}")
            return False
    
    def get_account_balance(self, accountType: str = "UNIFIED") -> Dict:
        """Get account balance."""
        try:
            balance = self.session.get_wallet_balance(accountType=accountType)
            
            if balance and 'result' in balance and 'list' in balance['result']:
                account_data = balance['result']['list'][0]
                return {
                    'total': account_data.get('totalWalletBalance', '0'),
                    'free': account_data.get('availableToWithdraw', '0'),
                    'used': account_data.get('totalUsedBalance', '0')
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {}
    
    def place_order(self, symbol: str, side: str, qty: float, 
                   orderType: str = 'Market', price: Optional[float] = None,
                   category: str = "linear") -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading pair
            side: 'Buy' or 'Sell'
            qty: Order quantity
            orderType: 'Market' or 'Limit'
            price: Price for limit orders
            category: Product type ('linear', 'inverse', 'spot', 'option')
            
        Returns:
            Order information
        """
        try:
            order_params = {
                "category": category,
                "symbol": symbol,
                "side": side,
                "orderType": orderType,
                "qty": str(qty)
            }
            
            if price and orderType == 'Limit':
                order_params["price"] = str(price)
            
            order = self.session.place_order(**order_params)
            logger.info(f"Placed {side} order for {qty} {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return {}
    
    def cancel_order(self, symbol: str, orderId: str, category: str = "linear") -> bool:
        """Cancel an order."""
        try:
            result = self.session.cancel_order(
                category=category,
                symbol=symbol,
                orderId=orderId
            )
            logger.info(f"Cancelled order {orderId} for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {orderId}: {e}")
            return False
    
    def get_open_orders(self, symbol: Optional[str] = None, category: str = "linear") -> List[Dict]:
        """Get open orders."""
        try:
            params = {"category": category}
            if symbol:
                params["symbol"] = symbol
            
            orders = self.session.get_open_orders(**params)
            
            if orders and 'result' in orders and 'list' in orders['result']:
                return orders['result']['list']
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    def get_positions(self, category: str = "linear") -> List[Dict]:
        """Get current positions."""
        try:
            positions = self.session.get_positions(category=category)
            
            if positions and 'result' in positions and 'list' in positions['result']:
                return positions['result']['list']
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []


# Global client instance
bybit_client = BybitClient()