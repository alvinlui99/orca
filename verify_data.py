#!/usr/bin/env python3
"""
Quick data verification script for Orca project.
This will quickly check if your data collection was successful.
"""

import sqlite3
import pandas as pd
from loguru import logger

def quick_verification():
    """Quick verification of the collected data."""
    try:
        # Connect to database
        conn = sqlite3.connect('orca.db')
        logger.info("Connected to database for verification")
        
        print("\n" + "="*60)
        print("QUICK DATA VERIFICATION")
        print("="*60)
        
        # 1. Check if price_data table exists and has data
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM price_data;")
        total_records = cursor.fetchone()[0]
        print(f"✓ Total price records: {total_records:,}")
        
        if total_records == 0:
            print("❌ No price data found!")
            return
        
        # 2. Check unique symbols
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM price_data;")
        unique_symbols = cursor.fetchone()[0]
        print(f"✓ Unique symbols: {unique_symbols}")
        
        # 3. Check date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_data;")
        date_range = cursor.fetchone()
        print(f"✓ Date range: {date_range[0]} to {date_range[1]}")
        
        # 4. Check timeframes
        cursor.execute("SELECT DISTINCT timeframe FROM price_data;")
        timeframes = cursor.fetchall()
        print(f"✓ Timeframes: {[tf[0] for tf in timeframes]}")
        
        # 5. Check if turnover column exists and has data
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE turnover IS NOT NULL;")
        turnover_records = cursor.fetchone()[0]
        print(f"✓ Records with turnover data: {turnover_records:,}")
        
        # 6. Show sample of recent data
        print(f"\n" + "="*60)
        print("RECENT DATA SAMPLE (Latest 5 records)")
        print("="*60)
        
        query = """
        SELECT symbol, timestamp, open, high, low, close, volume, turnover, timeframe
        FROM price_data 
        ORDER BY timestamp DESC
        LIMIT 5
        """
        
        df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        
        # 7. Show symbols with most data
        print(f"\n" + "="*60)
        print("TOP 10 SYMBOLS BY RECORD COUNT")
        print("="*60)
        
        query = """
        SELECT symbol, COUNT(*) as records, 
               MIN(timestamp) as first_date, 
               MAX(timestamp) as last_date
        FROM price_data 
        GROUP BY symbol
        ORDER BY records DESC
        LIMIT 10
        """
        
        df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        
        # 8. Data quality checks
        print(f"\n" + "="*60)
        print("DATA QUALITY CHECKS")
        print("="*60)
        
        # Check for null values
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL;")
        null_prices = cursor.fetchone()[0]
        print(f"✓ Records with null prices: {null_prices}")
        
        # Check for zero volumes
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE volume = 0;")
        zero_volumes = cursor.fetchone()[0]
        print(f"✓ Records with zero volume: {zero_volumes}")
        
        # Check for price anomalies (high > low)
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE high < low;")
        price_anomalies = cursor.fetchone()[0]
        print(f"✓ Records with high < low: {price_anomalies}")
        
        print(f"\n" + "="*60)
        print("VERIFICATION COMPLETE")
        print("="*60)
        
        if total_records > 0 and unique_symbols > 0:
            print("✅ Data collection appears successful!")
        else:
            print("❌ Data collection may have issues.")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    quick_verification() 