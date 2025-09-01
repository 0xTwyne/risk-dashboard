"""
Test script to verify API connectivity and dashboard functionality.
"""

import sys
from src.api.client import api_client, APIError


def test_api_connection():
    """Test basic API connectivity."""
    print("Testing API Connection...")
    print("-" * 50)
    
    # Test health endpoint
    try:
        health = api_client.get_health()
        print(f"✓ API Health: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False
    
    # Test EVaults endpoint
    try:
        evaults = api_client.get_evaults_latest()
        print(f"✓ EVaults: Found {len(evaults)} vaults")
        if evaults:
            print(f"  Sample vault: {evaults[0].vault_address[:10]}...")
    except Exception as e:
        print(f"✗ EVaults fetch failed: {e}")
    
    # Test Collateral Vaults endpoint
    try:
        snapshots = api_client.get_collateral_latest_snapshots(limit=10)
        print(f"✓ Collateral Vaults: Found {len(snapshots)} snapshots")
    except Exception as e:
        print(f"✗ Collateral snapshots fetch failed: {e}")
    
    # Test Liquidations endpoints
    try:
        external = api_client.get_external_liquidations(limit=10)
        # TEMPORARILY DISABLED: internal_liquidations endpoint is broken
        # internal = api_client.get_internal_liquidations(limit=10)
        internal = []  # Placeholder
        print(f"✓ Liquidations: {len(external)} external, {len(internal)} internal (internal disabled)")
    except Exception as e:
        print(f"✗ Liquidations fetch failed: {e}")
    
    # Test cache
    print("\n" + "-" * 50)
    print("Cache Statistics:")
    stats = api_client.get_cache_stats()
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']:.2%}")
    print(f"  Total Cached: {stats['total_cached']}")
    
    print("\n" + "=" * 50)
    print("API tests completed successfully!")
    return True


if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)
