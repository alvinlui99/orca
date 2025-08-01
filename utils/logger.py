"""
Logging utility module for Orca project.
Handles logging configuration and setup.
"""

import sys
from loguru import logger
from config.config import config


def setup_logging():
    """Setup logging configuration."""
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        level=config.logging.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler
    logger.add(
        config.logging.log_file,
        level=config.logging.log_level,
        rotation=config.logging.log_rotation,
        retention=config.logging.log_retention,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        compression="zip"
    )
    
    logger.info("Logging setup completed")


def get_logger(name: str):
    """Get logger instance for a module."""
    return logger.bind(name=name)


# Setup logging when module is imported
setup_logging() 