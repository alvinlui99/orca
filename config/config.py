"""
Configuration module for Orca project.
Handles API credentials, database settings, and trading parameters.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class BybitConfig:
    """Bybit API configuration."""
    api_key: str = os.getenv('BYBIT_API_KEY', '')
    api_secret: str = os.getenv('BYBIT_API_SECRET', '')
    testnet: bool = os.getenv('BYBIT_TESTNET', 'True').lower() == 'true'

@dataclass
class DatabaseConfig:
    """Database configuration."""
    db_path: str = os.getenv('DB_PATH', 'orca.db')
    db_type: str = os.getenv('DB_TYPE', 'sqlite')  # sqlite or postgresql
    
    # PostgreSQL settings (for future cloud migration)
    pg_host: str = os.getenv('PG_HOST', 'localhost')
    pg_port: int = int(os.getenv('PG_PORT', '5432'))
    pg_database: str = os.getenv('PG_DATABASE', 'orca')
    pg_user: str = os.getenv('PG_USER', '')
    pg_password: str = os.getenv('PG_PASSWORD', '')

@dataclass
class TradingConfig:
    """Trading parameters configuration."""
    # Position sizing
    max_position_size: float = 0.10  # 10% of portfolio per pair
    
    # Risk management
    max_leverage: int = 10
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.10  # 10% take profit
    
    # Performance targets
    target_annual_return: float = 0.10  # 10% annual return
    
    # Backtesting
    backtest_period_years: int = 2
    
    # Signal parameters
    copula_confidence_level: float = 0.95
    min_correlation_threshold: float = 0.7

@dataclass
class PairsConfig:
    """Trading pairs configuration."""
    
    # Layer 1 Blockchain Pairs
    layer1_pairs: List[str] = None
    
    # DeFi Token Pairs  
    defi_pairs: List[str] = None
    
    # Cross-Ecosystem Pairs
    cross_ecosystem_pairs: List[str] = None
    
    def __post_init__(self):
        if self.layer1_pairs is None:
            self.layer1_pairs = [
                'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOTUSDT'
            ]
        if self.defi_pairs is None:
            self.defi_pairs = [
                'UNIUSDT', 'SUSHIUSDT', 'AAVEUSDT', 'COMPUSDT', 'CRVUSDT', 'BALUSDT', 'SNXUSDT'
            ]
        if self.cross_ecosystem_pairs is None:
            self.cross_ecosystem_pairs = [
                'LINKUSDT', 'RAYUSDT'
            ]

@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', 'orca.log')
    log_rotation: str = '1 day'
    log_retention: str = '30 days'

class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.bybit = BybitConfig()
        self.database = DatabaseConfig()
        self.trading = TradingConfig()
        self.pairs = PairsConfig()
        self.logging = LoggingConfig()
    
    def get_all_pairs(self) -> List[str]:
        """Get all trading pairs."""
        return (self.pairs.layer1_pairs + 
                self.pairs.defi_pairs + 
                self.pairs.cross_ecosystem_pairs)
    
    def validate_config(self) -> bool:
        """Validate configuration settings."""
        if not self.bybit.api_key or not self.bybit.api_secret:
            raise ValueError("Bybit API credentials not configured")
        
        if self.trading.max_position_size <= 0 or self.trading.max_position_size > 1:
            raise ValueError("Invalid position size configuration")
        
        return True

# Global configuration instance
config = Config() 