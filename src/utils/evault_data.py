"""
EVault data fetcher and caching utilities for the Risk Dashboard.
Handles fetching and caching of EVault metrics for price calculations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from threading import Lock

from src.api import api_client
from .pricing import create_evault_price_lookup

logger = logging.getLogger(__name__)


class EVaultDataCache:
    """
    Cache for EVault data with automatic expiration.
    Thread-safe singleton implementation.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EVaultDataCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._cache = {}
            self._cache_timestamp = None
            self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
            self._data_lock = Lock()
            self._initialized = True
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration
    
    def get_evault_data(self) -> Tuple[Dict[str, Any], List[str]]:
        """
        Get EVault data from cache or fetch fresh data if needed.
        
        Returns:
            Tuple of (evault_data_dict, error_messages_list)
        """
        with self._data_lock:
            if self._is_cache_valid() and self._cache:
                logger.debug("Using cached EVault data")
                return self._cache.copy(), []
            
            logger.info("Fetching fresh EVault data")
            return self._fetch_and_cache_data()
    
    def _fetch_and_cache_data(self) -> Tuple[Dict[str, Any], List[str]]:
        """
        Fetch fresh EVault data and update cache.
        
        Returns:
            Tuple of (evault_data_dict, error_messages_list)
        """
        error_messages = []
        
        try:
            # Fetch latest EVault metrics
            response = api_client.get_evaults_latest()
            
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to fetch EVault data: {response['error']}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                return {}, error_messages
            
            # Extract metrics
            metrics = getattr(response, 'latestMetrics', []) or []
            
            if not metrics:
                error_msg = "No EVault metrics returned from API"
                logger.warning(error_msg)
                error_messages.append(error_msg)
                return {}, error_messages
            
            # Create price lookup and data dictionary
            price_lookup, price_errors = create_evault_price_lookup(metrics)
            error_messages.extend(price_errors)
            
            # Create comprehensive data dictionary
            evault_data = {}
            for metric in metrics:
                vault_address = getattr(metric, 'vaultAddress', None)
                if vault_address:
                    evault_data[vault_address] = {
                        'metric': metric,
                        'price': price_lookup.get(vault_address, 0.0),
                        'symbol': getattr(metric, 'symbol', 'UNKNOWN'),
                        'name': getattr(metric, 'name', 'Unknown Token'),
                        'decimals': getattr(metric, 'decimals', '18')
                    }
            
            # Update cache
            self._cache = evault_data
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Cached EVault data for {len(evault_data)} vaults")
            
            return evault_data.copy(), error_messages
            
        except Exception as e:
            error_msg = f"Unexpected error fetching EVault data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            error_messages.append(error_msg)
            return {}, error_messages
    
    def get_vault_price(self, vault_address: str) -> Tuple[float, Optional[str]]:
        """
        Get price for a specific vault address.
        
        Args:
            vault_address: The vault address to get price for
            
        Returns:
            Tuple of (price, error_message). Price is 0.0 if not found.
        """
        evault_data, errors = self.get_evault_data()
        
        if vault_address in evault_data:
            price = evault_data[vault_address]['price']
            if price == 0.0:
                return price, f"Warning: Vault {vault_address} has zero price"
            return price, None
        else:
            error_msg = f"Warning: Vault {vault_address} not found in EVault data"
            return 0.0, error_msg
    
    def get_vault_info(self, vault_address: str) -> Dict[str, Any]:
        """
        Get comprehensive info for a specific vault.
        
        Args:
            vault_address: The vault address to get info for
            
        Returns:
            Dictionary with vault info or empty dict if not found
        """
        evault_data, _ = self.get_evault_data()
        return evault_data.get(vault_address, {})
    
    def clear_cache(self):
        """Manually clear the cache to force fresh data fetch."""
        with self._data_lock:
            self._cache = {}
            self._cache_timestamp = None
            logger.info("EVault data cache cleared")


# Create singleton instance
evault_cache = EVaultDataCache()


def fetch_evault_prices() -> Tuple[Dict[str, float], List[str]]:
    """
    Convenience function to fetch EVault prices.
    
    Returns:
        Tuple of (price_lookup_dict, error_messages_list)
    """
    evault_data, errors = evault_cache.get_evault_data()
    price_lookup = {addr: data['price'] for addr, data in evault_data.items()}
    return price_lookup, errors


def get_vault_prices_for_snapshot(
    credit_vault_address: str, 
    debt_vault_address: str
) -> Tuple[float, float, List[str]]:
    """
    Get prices for credit and debt vaults needed for a collateral snapshot.
    
    Args:
        credit_vault_address: Address of the credit vault
        debt_vault_address: Address of the debt vault
        
    Returns:
        Tuple of (credit_price, debt_price, error_messages_list)
    """
    error_messages = []
    
    # Get credit vault price
    credit_price, credit_error = evault_cache.get_vault_price(credit_vault_address)
    if credit_error:
        error_messages.append(credit_error)
    
    # Get debt vault price
    debt_price, debt_error = evault_cache.get_vault_price(debt_vault_address)
    if debt_error:
        error_messages.append(debt_error)
    
    return credit_price, debt_price, error_messages


def refresh_evault_cache():
    """
    Manually refresh the EVault cache.
    Useful for refresh buttons or periodic updates.
    """
    evault_cache.clear_cache()
    return evault_cache.get_evault_data()
