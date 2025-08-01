"""
Pair manager module for Orca project.
Handles creation and management of trading pairs for statistical arbitrage analysis.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

from config.config import config


@dataclass
class TradingPair:
    """Represents a trading pair for statistical arbitrage."""
    symbol1: str
    symbol2: str
    category: str
    description: str
    
    @property
    def pair_name(self) -> str:
        """Get the pair name for identification."""
        return f"{self.symbol1}_{self.symbol2}"
    
    def __str__(self) -> str:
        return f"{self.pair_name} ({self.category})"


class PairManager:
    """Manages trading pairs for statistical arbitrage."""
    
    def __init__(self):
        """Initialize pair manager."""
        self.pairs = self._create_pairs()
        logger.info(f"Initialized pair manager with {len(self.pairs)} pairs")
    
    def _create_pairs(self) -> List[TradingPair]:
        """Create trading pairs for analysis."""
        pairs = []
        
        # Layer 1 Blockchain Pairs
        layer1_symbols = config.pairs.layer1_pairs
        pairs.extend([
            TradingPair("ETHUSDT", "ADAUSDT", "layer1", "Ethereum vs Cardano"),
            TradingPair("ETHUSDT", "SOLUSDT", "layer1", "Ethereum vs Solana"),
            TradingPair("ADAUSDT", "DOTUSDT", "layer1", "Cardano vs Polkadot"),
        ])
        
        # DeFi Token Pairs
        defi_symbols = config.pairs.defi_pairs
        pairs.extend([
            TradingPair("UNIUSDT", "SUSHIUSDT", "defi", "DEX protocols"),
            TradingPair("AAVEUSDT", "COMPUSDT", "defi", "Lending protocols"),
        ])
        
        # Cross-Ecosystem Pairs
        cross_ecosystem_symbols = config.pairs.cross_ecosystem_pairs
        pairs.extend([
            TradingPair("ETHUSDT", "LINKUSDT", "cross_ecosystem", "Ethereum vs Oracle"),
            TradingPair("SOLUSDT", "RAYUSDT", "cross_ecosystem", "Solana ecosystem"),
        ])
        
        return pairs
    
    def get_all_pairs(self) -> List[TradingPair]:
        """Get all trading pairs."""
        return self.pairs
    
    def get_pairs_by_category(self, category: str) -> List[TradingPair]:
        """Get pairs by category."""
        return [pair for pair in self.pairs if pair.category == category]
    
    def get_layer1_pairs(self) -> List[TradingPair]:
        """Get Layer 1 blockchain pairs."""
        return self.get_pairs_by_category("layer1")
    
    def get_defi_pairs(self) -> List[TradingPair]:
        """Get DeFi token pairs."""
        return self.get_pairs_by_category("defi")
    
    def get_cross_ecosystem_pairs(self) -> List[TradingPair]:
        """Get cross-ecosystem pairs."""
        return self.get_pairs_by_category("cross_ecosystem")
    
    def get_pair_by_name(self, pair_name: str) -> Optional[TradingPair]:
        """Get a specific pair by name."""
        for pair in self.pairs:
            if pair.pair_name == pair_name:
                return pair
        return None
    
    def get_all_symbols(self) -> List[str]:
        """Get all unique symbols used in pairs."""
        symbols = set()
        for pair in self.pairs:
            symbols.add(pair.symbol1)
            symbols.add(pair.symbol2)
        return list(symbols)
    
    def get_symbols_for_pair(self, pair_name: str) -> Tuple[str, str]:
        """Get the two symbols for a specific pair."""
        pair = self.get_pair_by_name(pair_name)
        if pair:
            return pair.symbol1, pair.symbol2
        raise ValueError(f"Pair {pair_name} not found")
    
    def validate_pair_availability(self, symbol_availability: Dict[str, bool]) -> Dict[str, bool]:
        """
        Validate which pairs are available for trading.
        
        Args:
            symbol_availability: Dictionary mapping symbols to availability status
            
        Returns:
            Dictionary mapping pair names to availability status
        """
        validation_results = {}
        
        for pair in self.pairs:
            symbol1_available = symbol_availability.get(pair.symbol1, False)
            symbol2_available = symbol_availability.get(pair.symbol2, False)
            pair_available = symbol1_available and symbol2_available
            
            validation_results[pair.pair_name] = pair_available
            
            if not pair_available:
                logger.warning(f"Pair {pair.pair_name} not available: "
                             f"{pair.symbol1} ({symbol1_available}), "
                             f"{pair.symbol2} ({symbol2_available})")
        
        return validation_results
    
    def get_available_pairs(self, symbol_availability: Dict[str, bool]) -> List[TradingPair]:
        """Get pairs that are available for trading."""
        validation_results = self.validate_pair_availability(symbol_availability)
        return [pair for pair in self.pairs if validation_results[pair.pair_name]]
    
    def get_pair_statistics(self) -> Dict:
        """Get statistics about the trading pairs."""
        stats = {
            'total_pairs': len(self.pairs),
            'layer1_pairs': len(self.get_layer1_pairs()),
            'defi_pairs': len(self.get_defi_pairs()),
            'cross_ecosystem_pairs': len(self.get_cross_ecosystem_pairs()),
            'unique_symbols': len(self.get_all_symbols()),
            'categories': list(set(pair.category for pair in self.pairs))
        }
        return stats
    
    def print_pair_summary(self):
        """Print a summary of all trading pairs."""
        logger.info("=== Trading Pairs Summary ===")
        
        stats = self.get_pair_statistics()
        logger.info(f"Total pairs: {stats['total_pairs']}")
        logger.info(f"Layer 1 pairs: {stats['layer1_pairs']}")
        logger.info(f"DeFi pairs: {stats['defi_pairs']}")
        logger.info(f"Cross-ecosystem pairs: {stats['cross_ecosystem_pairs']}")
        logger.info(f"Unique symbols: {stats['unique_symbols']}")
        
        logger.info("\n=== Layer 1 Pairs ===")
        for pair in self.get_layer1_pairs():
            logger.info(f"  {pair.pair_name}: {pair.description}")
        
        logger.info("\n=== DeFi Pairs ===")
        for pair in self.get_defi_pairs():
            logger.info(f"  {pair.pair_name}: {pair.description}")
        
        logger.info("\n=== Cross-Ecosystem Pairs ===")
        for pair in self.get_cross_ecosystem_pairs():
            logger.info(f"  {pair.pair_name}: {pair.description}")


# Global pair manager instance
pair_manager = PairManager() 