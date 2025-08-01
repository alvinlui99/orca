"""
Main entry point for Orca project.
Demonstrates Phase 1 functionality: data infrastructure setup.
"""

import os
from datetime import datetime
from loguru import logger

from config.config import config
from data.bybit_client import bybit_client
from data.database import db_manager
from data.data_collector import data_collector
from data.pair_manager import pair_manager
from utils.logger import setup_logging


def phase1():
    """Main function to run Phase 1 data infrastructure."""
    try:
        logger.info("Starting Orca Phase 1: Data Infrastructure")
        
        # Validate configuration
        config.validate_config()
        logger.info("Configuration validated successfully")
        
        # Test Bybit connection
        logger.info("Testing Bybit API connection...")
        
        # Get symbols we care about and check their availability
        all_symbols = pair_manager.get_all_symbols()
        logger.info(f"Checking availability of {len(all_symbols)} symbols on Bybit...")
        symbol_availability = bybit_client.check_symbols_availability(all_symbols)
        available_symbols = [symbol for symbol, available in symbol_availability.items() if available]
        logger.info(f"Found {len(available_symbols)} available symbols out of {len(all_symbols)} checked")
        
        # Test pair manager
        logger.info("Testing pair manager...")
        available_pairs = pair_manager.get_available_pairs(symbol_availability)
        logger.info(f"Found {len(available_pairs)} available pairs for trading")
        
        # Test database connection
        logger.info("Testing database connection...")
        db_manager.get_trading_pairs()
        logger.info("Database connection successful")
        
        # Run data collection pipeline
        logger.info("Running data collection pipeline...")
        results = data_collector.run_data_collection_pipeline()
        
        if results:
            logger.info(f"Data collection completed successfully")
            logger.info(f"Collected data for {len(results.get('collected_symbols', []))} symbols")
            
            # Print summary
            summary = results.get('summary', {})
            for symbol, info in summary.items():
                if 'error' not in info:
                    logger.info(f"{symbol}: {info['total_records']} records from {info['start_date']} to {info['end_date']}")
                else:
                    logger.warning(f"{symbol}: {info['error']}")
        else:
            logger.error("Data collection pipeline failed")
        
        logger.info("Phase 1 completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

def phase2():
    pass

if __name__ == "__main__":
    phase2()