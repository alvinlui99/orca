"""
Database module for Orca project.
Handles data storage, retrieval, and management for historical price data.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from loguru import logger

from config.config import config


class DatabaseManager:
    """Database manager for storing and retrieving trading data."""
    
    def __init__(self):
        """Initialize database connection."""
        self.db_path = config.database.db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database and create tables."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Price data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                timeframe TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp, timeframe)
            )
        ''')
        
        # Trading pairs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Copula analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS copula_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_symbol TEXT NOT NULL,
                copula_type TEXT,
                parameters TEXT,
                tail_dependence REAL,
                confidence_level REAL,
                analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trading signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_symbol TEXT NOT NULL,
                signal_type TEXT,
                entry_price REAL,
                exit_price REAL,
                position_size REAL,
                pnl REAL,
                entry_time DATETIME,
                exit_time DATETIME,
                status TEXT DEFAULT 'open',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                total_pnl REAL,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_trades INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("Database tables created successfully")
    
    def insert_price_data(self, df: pd.DataFrame, symbol: str, timeframe: str = '1h'):
        """
        Insert price data into database.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair symbol
            timeframe: Timeframe
        """
        try:
            df_copy = df.copy()
            
            # Keep only the columns that exist in the database table
            expected_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover']
            for col in expected_columns:
                if col not in df_copy.columns:
                    logger.warning(f"Missing column {col} in data for {symbol}")
            
            df_copy['symbol'] = symbol
            df_copy['timeframe'] = timeframe
            df_copy.reset_index(inplace=True)
            
            df_copy.to_sql('price_data', self.conn, if_exists='append', 
                          index=False, method='multi')
            
            logger.info(f"Inserted {len(df_copy)} price records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error inserting price data for {symbol}: {e}")
    
    def get_price_data(self, symbol: str, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None, timeframe: str = '1h') -> pd.DataFrame:
        """
        Get price data from database.
        
        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe
            
        Returns:
            DataFrame with price data
        """
        try:
            query = '''
                SELECT * FROM price_data 
                WHERE symbol = ? AND timeframe = ?
            '''
            params = [symbol, timeframe]
            
            if start_date:
                query += ' AND timestamp >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND timestamp <= ?'
                params.append(end_date)
            
            query += ' ORDER BY timestamp'
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving price data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_price(self, symbol: str, timeframe: str = '1h') -> Optional[Dict]:
        """Get latest price data for a symbol."""
        try:
            query = '''
                SELECT * FROM price_data 
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            '''
            
            df = pd.read_sql_query(query, self.conn, params=[symbol, timeframe])
            
            if not df.empty:
                return df.iloc[0].to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving latest price for {symbol}: {e}")
            return None
    
    def insert_trading_pair(self, symbol: str, category: str):
        """Insert trading pair into database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO trading_pairs (symbol, category)
                VALUES (?, ?)
            ''', (symbol, category))
            self.conn.commit()
            
            logger.info(f"Inserted trading pair: {symbol} ({category})")
            
        except Exception as e:
            logger.error(f"Error inserting trading pair {symbol}: {e}")
    
    def get_trading_pairs(self, category: Optional[str] = None) -> List[str]:
        """Get trading pairs from database."""
        try:
            query = 'SELECT symbol FROM trading_pairs WHERE is_active = 1'
            params = []
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error retrieving trading pairs: {e}")
            return []
    
    def insert_copula_analysis(self, pair_symbol: str, copula_type: str, 
                              parameters: Dict, tail_dependence: float,
                              confidence_level: float):
        """Insert copula analysis results."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO copula_analysis 
                (pair_symbol, copula_type, parameters, tail_dependence, confidence_level)
                VALUES (?, ?, ?, ?, ?)
            ''', (pair_symbol, copula_type, json.dumps(parameters), 
                  tail_dependence, confidence_level))
            self.conn.commit()
            
            logger.info(f"Inserted copula analysis for {pair_symbol}")
            
        except Exception as e:
            logger.error(f"Error inserting copula analysis for {pair_symbol}: {e}")
    
    def get_copula_analysis(self, pair_symbol: str) -> Optional[Dict]:
        """Get latest copula analysis for a pair."""
        try:
            query = '''
                SELECT * FROM copula_analysis 
                WHERE pair_symbol = ?
                ORDER BY analysis_date DESC 
                LIMIT 1
            '''
            
            df = pd.read_sql_query(query, self.conn, params=[pair_symbol])
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    'pair_symbol': row['pair_symbol'],
                    'copula_type': row['copula_type'],
                    'parameters': json.loads(row['parameters']),
                    'tail_dependence': row['tail_dependence'],
                    'confidence_level': row['confidence_level'],
                    'analysis_date': row['analysis_date']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving copula analysis for {pair_symbol}: {e}")
            return None
    
    def insert_trading_signal(self, pair_symbol: str, signal_type: str,
                             entry_price: float, position_size: float,
                             entry_time: datetime):
        """Insert trading signal."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trading_signals 
                (pair_symbol, signal_type, entry_price, position_size, entry_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (pair_symbol, signal_type, entry_price, position_size, entry_time))
            self.conn.commit()
            
            logger.info(f"Inserted trading signal for {pair_symbol}")
            
        except Exception as e:
            logger.error(f"Error inserting trading signal for {pair_symbol}: {e}")
    
    def update_trading_signal(self, signal_id: int, exit_price: float,
                             pnl: float, exit_time: datetime, status: str = 'closed'):
        """Update trading signal with exit information."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE trading_signals 
                SET exit_price = ?, pnl = ?, exit_time = ?, status = ?
                WHERE id = ?
            ''', (exit_price, pnl, exit_time, status, signal_id))
            self.conn.commit()
            
            logger.info(f"Updated trading signal {signal_id}")
            
        except Exception as e:
            logger.error(f"Error updating trading signal {signal_id}: {e}")
    
    def get_open_signals(self) -> List[Dict]:
        """Get open trading signals."""
        try:
            query = '''
                SELECT * FROM trading_signals 
                WHERE status = 'open'
                ORDER BY entry_time DESC
            '''
            
            df = pd.read_sql_query(query, self.conn)
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error retrieving open signals: {e}")
            return []
    
    def close_connection(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager() 