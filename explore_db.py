#!/usr/bin/env python3
"""
Interactive database exploration script for Orca project.
This will help you learn SQL and verify your data is correct.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from loguru import logger

def connect_to_database():
    """Connect to the Orca database."""
    try:
        conn = sqlite3.connect('orca.db')
        logger.info("Successfully connected to orca.db")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def show_database_info(conn):
    """Show basic information about the database."""
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n" + "="*50)
    print("DATABASE OVERVIEW")
    print("="*50)
    print(f"Database file: orca.db")
    print(f"Number of tables: {len(tables)}")
    print("\nTables found:")
    for table in tables:
        print(f"  - {table[0]}")
    
    return [table[0] for table in tables]

def explore_table_structure(conn, table_name):
    """Show the structure (columns) of a table."""
    cursor = conn.cursor()
    
    print(f"\n" + "="*50)
    print(f"TABLE STRUCTURE: {table_name}")
    print("="*50)
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print(f"{'Column':<15} {'Type':<15} {'Not Null':<10} {'Primary Key':<12}")
    print("-" * 60)
    for col in columns:
        print(f"{col[1]:<15} {col[2]:<15} {col[3]:<10} {col[5]:<12}")

def show_table_stats(conn, table_name):
    """Show basic statistics about a table."""
    cursor = conn.cursor()
    
    print(f"\n" + "="*50)
    print(f"TABLE STATISTICS: {table_name}")
    print("="*50)
    
    # Count total rows
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    total_rows = cursor.fetchone()[0]
    print(f"Total rows: {total_rows:,}")
    
    if table_name == 'price_data':
        # Show unique symbols
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM price_data;")
        unique_symbols = cursor.fetchone()[0]
        print(f"Unique symbols: {unique_symbols}")
        
        # Show date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_data;")
        date_range = cursor.fetchone()
        print(f"Date range: {date_range[0]} to {date_range[1]}")
        
        # Show unique timeframes
        cursor.execute("SELECT DISTINCT timeframe FROM price_data;")
        timeframes = cursor.fetchall()
        print(f"Timeframes: {[tf[0] for tf in timeframes]}")

def query_price_data(conn, symbol=None, limit=10):
    """Query price data with optional filtering."""
    print(f"\n" + "="*50)
    print("PRICE DATA SAMPLE")
    print("="*50)
    
    if symbol:
        query = """
        SELECT symbol, timestamp, open, high, low, close, volume, turnover, timeframe
        FROM price_data 
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=[symbol, limit])
    else:
        query = """
        SELECT symbol, timestamp, open, high, low, close, volume, turnover, timeframe
        FROM price_data 
        ORDER BY timestamp DESC
        LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=[limit])
    
    if not df.empty:
        print(df.to_string(index=False))
    else:
        print("No data found.")

def show_symbols_summary(conn):
    """Show summary of all symbols in the database."""
    print(f"\n" + "="*50)
    print("SYMBOLS SUMMARY")
    print("="*50)
    
    query = """
    SELECT 
        symbol,
        COUNT(*) as records,
        MIN(timestamp) as first_date,
        MAX(timestamp) as last_date,
        AVG(volume) as avg_volume,
        AVG(turnover) as avg_turnover
    FROM price_data 
    GROUP BY symbol
    ORDER BY records DESC
    """
    
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))

def interactive_menu():
    """Interactive menu for database exploration."""
    conn = connect_to_database()
    if not conn:
        return
    
    tables = show_database_info(conn)
    
    while True:
        print("\n" + "="*50)
        print("INTERACTIVE DATABASE EXPLORER")
        print("="*50)
        print("1. Show table structure")
        print("2. Show table statistics")
        print("3. Query price data (all symbols)")
        print("4. Query price data (specific symbol)")
        print("5. Show symbols summary")
        print("6. Custom SQL query")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            table = input("Enter table name: ").strip()
            if table in tables:
                explore_table_structure(conn, table)
            else:
                print(f"Table '{table}' not found. Available tables: {tables}")
        elif choice == '2':
            table = input("Enter table name: ").strip()
            if table in tables:
                show_table_stats(conn, table)
            else:
                print(f"Table '{table}' not found. Available tables: {tables}")
        elif choice == '3':
            limit = input("Enter number of records to show (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            query_price_data(conn, limit=limit)
        elif choice == '4':
            symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
            limit = input("Enter number of records to show (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            query_price_data(conn, symbol=symbol, limit=limit)
        elif choice == '5':
            show_symbols_summary(conn)
        elif choice == '6':
            sql = input("Enter your SQL query: ").strip()
            try:
                df = pd.read_sql_query(sql, conn)
                print(f"\nQuery returned {len(df)} rows:")
                print(df.to_string(index=False))
            except Exception as e:
                print(f"Error executing query: {e}")
        else:
            print("Invalid choice. Please try again.")
    
    conn.close()
    print("\nDatabase connection closed.")

if __name__ == "__main__":
    interactive_menu() 