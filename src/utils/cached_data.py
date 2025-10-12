"""
Cached data fetching utilities using Flask-Caching.
Implements caching for EVault data to improve performance following Dash best practices.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Tuple
from flask_caching import Cache

from src.api import api_client

logger = logging.getLogger(__name__)

# Global cache instance - will be set by setup_cache()
cache: Cache = None


def setup_cache(cache_instance: Cache):
    """
    Setup cache instance for use in data functions.
    
    Args:
        cache_instance: Flask-Caching Cache instance
    """
    global cache
    cache = cache_instance
    logger.info("Cache instance configured for cached data utilities")


def make_cache_key(*args, **kwargs):
    """
    Create intelligent cache keys based on parameters.
    
    Returns:
        String cache key
    """
    # Convert arguments to strings and join them
    key_parts = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            # For lists/tuples, sort and join to ensure consistent keys
            key_parts.append("-".join(sorted(str(x) for x in arg)))
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    return ":".join(key_parts)


# EVault caching using the same approach as collateral vaults
# Cache the processed results at the callback level instead of raw API responses

def cache_evaults_data(data: Dict[str, Any]) -> None:
    """
    Cache processed EVaults data.
    
    Args:
        data: Processed EVaults data to cache
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot cache EVaults data")
        return
    
    try:
        cache_key = "evaults_latest_data"
        cache.set(cache_key, data, timeout=300)  # 5 minutes
        logger.info("EVaults data cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache EVaults data: {e}", exc_info=True)


def get_cached_evaults_data() -> Dict[str, Any]:
    """
    Get cached EVaults data.
    
    Returns:
        Cached data or None if not available
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot get cached EVaults data")
        return None
    
    try:
        cache_key = "evaults_latest_data"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Retrieved EVaults data from cache")
        return cached_data
    except Exception as e:
        logger.error(f"Failed to get cached EVaults data: {e}", exc_info=True)
        return None


def cache_evaults_historical_data(vault_addresses: List[str], data: List[Dict[str, Any]]) -> None:
    """
    Cache processed EVaults historical data.
    
    Args:
        vault_addresses: List of vault addresses (for cache key)
        data: Processed historical data to cache
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot cache EVaults historical data")
        return
    
    try:
        cache_key = f"evaults_historical_data:{make_cache_key(vault_addresses)}"
        cache.set(cache_key, data, timeout=300)  # 5 minutes
        logger.info(f"EVaults historical data cached successfully for {len(vault_addresses)} vaults")
    except Exception as e:
        logger.error(f"Failed to cache EVaults historical data: {e}", exc_info=True)


def get_cached_evaults_historical_data(vault_addresses: List[str]) -> List[Dict[str, Any]]:
    """
    Get cached EVaults historical data.
    
    Args:
        vault_addresses: List of vault addresses
        
    Returns:
        Cached data or None if not available
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot get cached EVaults historical data")
        return None
    
    try:
        cache_key = f"evaults_historical_data:{make_cache_key(vault_addresses)}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved EVaults historical data from cache for {len(vault_addresses)} vaults")
        return cached_data
    except Exception as e:
        logger.error(f"Failed to get cached EVaults historical data: {e}", exc_info=True)
        return None


# Historical data will be handled separately - remove the old implementation for now


def _get_vault_symbol_mapping_impl() -> Dict[str, str]:
    """
    Implementation of vault symbol mapping.
    Only uses cached data - does not fetch fresh data to avoid async issues.
    
    Returns:
        Dict mapping vault address (lowercase) to symbol
    """
    try:
        logger.info("Getting vault symbol mapping from cache...")
        
        # Get EVaults data from cache only - don't fetch fresh to avoid async issues
        evaults_data = get_cached_evaults_data()
        
        if not evaults_data:
            logger.warning("No cached EVaults data available for symbol mapping")
            return {}
        
        if evaults_data.get("error"):
            logger.warning(f"Error in cached EVaults data for symbol mapping: {evaults_data['error']}")
            return {}
        
        # Create mapping of address -> symbol (case-insensitive)
        symbol_mapping = {}
        for metric in evaults_data.get("metrics", []):
            vault_address = metric.vaultAddress.lower()
            symbol = metric.symbol
            symbol_mapping[vault_address] = symbol
        
        logger.info(f"Created symbol mapping for {len(symbol_mapping)} vaults from cache")
        return symbol_mapping
        
    except Exception as e:
        logger.error(f"Failed to create vault symbol mapping from cache: {e}", exc_info=True)
        return {}


def get_vault_symbol_mapping_cached() -> Dict[str, str]:
    """
    Cached version of vault symbol mapping.
    
    Returns:
        Dict mapping vault address (lowercase) to symbol
    """
    if cache is None:
        logger.warning("Cache not initialized, falling back to direct implementation")
        return _get_vault_symbol_mapping_impl()
    
    # Use cache.memoize as a function decorator
    cached_func = cache.memoize(timeout=300)(_get_vault_symbol_mapping_impl)
    return cached_func()


# =======================
# Collateral Vault Caching Functions
# =======================

# Collateral vault caching using a different approach
# We'll cache the processed results at the callback level instead of raw API responses

def cache_collateral_vault_data(data: Dict[str, Any]) -> None:
    """
    Cache processed collateral vault data.
    
    Args:
        data: Processed collateral vault data to cache
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot cache collateral vault data")
        return
    
    try:
        cache_key = "collateral_vault_latest_data"
        cache.set(cache_key, data, timeout=300)  # 5 minutes
        logger.info("Collateral vault data cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache collateral vault data: {e}", exc_info=True)


def get_cached_collateral_vault_data() -> Dict[str, Any]:
    """
    Get cached collateral vault data.
    
    Returns:
        Cached data or None if not available
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot get cached collateral vault data")
        return None
    
    try:
        cache_key = "collateral_vault_latest_data"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Retrieved collateral vault data from cache")
        return cached_data
    except Exception as e:
        logger.error(f"Failed to get cached collateral vault data: {e}", exc_info=True)
        return None


def cache_collateral_vault_block_data(block_number: int, data: Dict[str, Any]) -> None:
    """
    Cache processed collateral vault block data.
    
    Args:
        block_number: Block number
        data: Processed collateral vault data to cache
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot cache collateral vault block data")
        return
    
    try:
        cache_key = f"collateral_vault_block_data:{block_number}"
        cache.set(cache_key, data, timeout=300)  # 5 minutes
        logger.info(f"Collateral vault block data for block {block_number} cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache collateral vault block data: {e}", exc_info=True)


def get_cached_collateral_vault_block_data(block_number: int) -> Dict[str, Any]:
    """
    Get cached collateral vault block data.
    
    Args:
        block_number: Block number
        
    Returns:
        Cached data or None if not available
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot get cached collateral vault block data")
        return None
    
    try:
        cache_key = f"collateral_vault_block_data:{block_number}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved collateral vault block data for block {block_number} from cache")
        return cached_data
    except Exception as e:
        logger.error(f"Failed to get cached collateral vault block data: {e}", exc_info=True)
        return None


def clear_evaults_cache():
    """
    Clear all EVaults-related cache entries.
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot clear EVaults cache")
        return
    
    try:
        # Clear specific cache keys
        cache.delete("evaults_latest_data")
        cache.delete_memoized(_get_vault_symbol_mapping_impl)
        # Clear historical data cache entries (pattern-based)
        cache.delete_many("evaults_historical_data:*")
        logger.info("EVaults cache cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear EVaults cache: {e}", exc_info=True)


def clear_collateral_cache():
    """
    Clear all collateral vault-related cache entries.
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot clear collateral cache")
        return
    
    try:
        # Clear specific cache keys
        cache.delete("collateral_vault_latest_data")
        # Clear all block data cache entries (pattern-based)
        cache.delete_many("collateral_vault_block_data:*")
        logger.info("Collateral vault cache cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear collateral vault cache: {e}", exc_info=True)


def clear_all_vault_caches():
    """
    Clear all vault-related cache entries (EVaults + Collateral).
    """
    clear_evaults_cache()
    clear_collateral_cache()


def clear_all_cache():
    """
    Clear entire cache.
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot clear all cache")
        return
    
    try:
        cache.clear()
        logger.info("All cache cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear all cache: {e}", exc_info=True)


def warm_evaults_cache():
    """
    Pre-populate cache with frequently accessed data.
    """
    if cache is None:
        logger.warning("Cache not initialized, cannot warm cache")
        return
    
    try:
        logger.info("Warming EVaults cache...")
        
        # Pre-fetch EVaults data
        evaults_data = fetch_evaults_data_cached()
        
        # Pre-fetch symbol mapping
        symbol_mapping = get_vault_symbol_mapping_cached()
        
        logger.info(f"Cache warmed with {evaults_data.get('total_vaults', 0)} vaults and {len(symbol_mapping)} symbol mappings")
        
    except Exception as e:
        logger.error(f"Failed to warm EVaults cache: {e}", exc_info=True)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for debugging and monitoring.
    
    Returns:
        Dictionary with cache statistics
    """
    if cache is None:
        return {"error": "Cache not initialized"}
    
    try:
        # Basic cache info
        stats = {
            "cache_type": "filesystem",
            "cache_dir": cache.config.get('CACHE_DIR', 'unknown'),
            "default_timeout": cache.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        return {"error": str(e)}
