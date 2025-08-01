"""
Data collector module for Orca project.
Handles data collection pipeline, validation, and cleaning.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from loguru import logger

from config.config import config
from data.bybit_client import bybit_client
from data.database import db_manager
from data.pair_manager import pair_manager


class DataCollector:
    """Data collector for fetching and storing trading data."""
    
    def __init__(self):
        """Initialize data collector."""
        self.bybit_client = bybit_client
        self.db_manager = db_manager
        logger.info("Data collector initialized")
    
    def collect_historical_data(self, symbols: List[str], timeframe: str = '60',
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        """
        Collect historical data for multiple symbols.
        
        Args:
            symbols: List of trading pairs
            timeframe: Timeframe for data
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            Dictionary with symbol as key and DataFrame as value
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Collecting historical data for {symbol}")
            
            try:
                # Check if symbol is available on Bybit
                if not self.bybit_client.check_symbol_availability(symbol):
                    logger.warning(f"Symbol {symbol} not available on Bybit")
                    continue
                
                # Fetch historical data
                df = self.bybit_client.get_historical_data(
                    symbol, timeframe, start_date, end_date, category="linear"
                )
                
                if not df.empty:
                    # Clean and validate data
                    df_clean = self._clean_price_data(df)
                    
                    if not df_clean.empty:
                        # Store in database
                        self.db_manager.insert_price_data(df_clean, symbol, timeframe)
                        results[symbol] = df_clean
                        
                        logger.info(f"Successfully collected {len(df_clean)} records for {symbol}")
                    else:
                        logger.warning(f"No valid data after cleaning for {symbol}")
                else:
                    logger.warning(f"No data collected for {symbol}")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
        
        return results
    
    def collect_realtime_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Collect real-time data for symbols.
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            Dictionary with current ticker data
        """
        results = {}
        
        for symbol in symbols:
            try:
                ticker = self.bybit_client.get_ticker(symbol)
                if ticker:
                    results[symbol] = ticker
                    logger.debug(f"Collected real-time data for {symbol}")
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error collecting real-time data for {symbol}: {e}")
        
        return results
    
    def update_trading_pairs(self):
        """Update trading pairs in database."""
        try:
            # Get all pairs from pair manager
            all_pairs = pair_manager.get_all_pairs()
            
            # Insert pairs into database
            for pair in all_pairs:
                self.db_manager.insert_trading_pair(pair.symbol1, pair.category)
                self.db_manager.insert_trading_pair(pair.symbol2, pair.category)
            
            logger.info(f"Updated {len(all_pairs)} trading pairs in database")
            
        except Exception as e:
            logger.error(f"Error updating trading pairs: {e}")
    
    def validate_data_quality(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Validate data quality for a symbol.
        
        Args:
            df: DataFrame with price data
            symbol: Trading pair symbol
            
        Returns:
            True if data quality is acceptable
        """
        try:
            if df.empty:
                logger.warning(f"Empty dataframe for {symbol}")
                return False
            
            # Check for missing values
            missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns))
            if missing_pct > 0.1:  # More than 10% missing data
                logger.warning(f"Too many missing values for {symbol}: {missing_pct:.2%}")
                return False
            
            # Check for zero or negative prices
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    zero_prices = (df[col] <= 0).sum()
                    if zero_prices > 0:
                        logger.warning(f"Found {zero_prices} zero/negative prices in {col} for {symbol}")
                        return False
            
            # Check for reasonable price ranges
            if 'close' in df.columns:
                price_range = df['close'].max() / df['close'].min()
                if price_range > 1000:  # Suspicious price range
                    logger.warning(f"Suspicious price range for {symbol}: {price_range:.2f}")
                    return False
            
            # Check for reasonable volume
            if 'volume' in df.columns:
                zero_volume = (df['volume'] == 0).sum()
                if zero_volume > len(df) * 0.5:  # More than 50% zero volume
                    logger.warning(f"Too many zero volume records for {symbol}: {zero_volume}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating data quality for {symbol}: {e}")
            return False
    
    def _clean_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean price data.
        
        Args:
            df: Raw price data
            
        Returns:
            Cleaned DataFrame
        """
        try:
            df_clean = df.copy()
            
            # Remove duplicates
            df_clean = df_clean[~df_clean.index.duplicated(keep='first')]
            
            # Handle missing values
            df_clean = df_clean.ffill()  # Forward fill
            df_clean = df_clean.bfill()  # Backward fill
            
            # Remove rows with zero or negative prices
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df_clean.columns:
                    df_clean = df_clean[df_clean[col] > 0]
            
            # Ensure high >= low
            if 'high' in df_clean.columns and 'low' in df_clean.columns:
                df_clean = df_clean[df_clean['high'] >= df_clean['low']]
            
            # Ensure high >= open, close and low <= open, close
            if all(col in df_clean.columns for col in ['high', 'low', 'open', 'close']):
                df_clean = df_clean[
                    (df_clean['high'] >= df_clean['open']) &
                    (df_clean['high'] >= df_clean['close']) &
                    (df_clean['low'] <= df_clean['open']) &
                    (df_clean['low'] <= df_clean['close'])
                ]
            
            # Sort by timestamp
            df_clean = df_clean.sort_index()
            
            return df_clean
            
        except Exception as e:
            logger.error(f"Error cleaning price data: {e}")
            return pd.DataFrame()
    
    def get_data_summary(self, symbols: List[str]) -> Dict:
        """
        Get data summary for symbols.
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            Dictionary with data summary
        """
        summary = {}
        
        for symbol in symbols:
            try:
                # Get latest data from database
                df = self.db_manager.get_price_data(symbol, timeframe='60')
                
                if not df.empty:
                    summary[symbol] = {
                        'start_date': df.index.min(),
                        'end_date': df.index.max(),
                        'total_records': len(df),
                        'missing_values': df.isnull().sum().to_dict(),
                        'price_range': {
                            'min': df['close'].min(),
                            'max': df['close'].max(),
                            'current': df['close'].iloc[-1]
                        },
                        'volume_stats': {
                            'mean': df['volume'].mean(),
                            'max': df['volume'].max(),
                            'current': df['volume'].iloc[-1]
                        }
                    }
                else:
                    summary[symbol] = {'error': 'No data available'}
                    
            except Exception as e:
                summary[symbol] = {'error': str(e)}
        
        return summary
    
    def run_data_collection_pipeline(self):
        """Run complete data collection pipeline."""
        try:
            logger.info("Starting data collection pipeline")
            
            # Print pair summary
            pair_manager.print_pair_summary()
            
            # Get symbols we care about
            all_symbols = pair_manager.get_all_symbols()
            logger.info(f"Checking availability of {len(all_symbols)} symbols on Bybit...")
            
            # Check availability of our specific symbols
            symbol_availability = self.bybit_client.check_symbols_availability(all_symbols)
            available_symbols = [symbol for symbol, available in symbol_availability.items() if available]
            logger.info(f"Found {len(available_symbols)} available symbols out of {len(all_symbols)} checked")
            
            # Validate pairs against available symbols
            available_pairs = pair_manager.get_available_pairs(symbol_availability)
            logger.info(f"Found {len(available_pairs)} available pairs for trading")
            
            # Use only available symbols for data collection
            available_symbols_for_collection = available_symbols
            
            # Collect historical data
            start_date = datetime.now() - timedelta(days=config.trading.backtest_period_years * 365)
            
            results = self.collect_historical_data(
                available_symbols_for_collection, 
                timeframe='60',  # 1 hour in Bybit format
                start_date=start_date
            )
            
            # Generate summary
            summary = self.get_data_summary(available_symbols_for_collection)
            
            logger.info(f"Data collection pipeline completed. Collected data for {len(results)} symbols")
            
            return {
                'collected_symbols': list(results.keys()),
                'available_pairs': [pair.pair_name for pair in available_pairs],
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in data collection pipeline: {e}")
            return {}


# Global data collector instance
data_collector = DataCollector() 