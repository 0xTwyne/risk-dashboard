import requests
import json

def query_vault_metrics(local=False):
    """Query vault metrics for a specific address"""
    
    # Configuration
    if local:
        base_url = "http://localhost:8787"
        api_key = ""
    else:
        base_url = "https://cdf169f4ba-7e35903394.idx.sim.io"
        api_key = "sim_vBwrxOq53ZmlslKyIzJFFVY9KBYQL3fi"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    eeusdc = "0x9b58505aaa6e15d6a3cb15f533634332a60f29d1"
    collateral_vault_address =  "0xFEB0AE773F2f24Fb1e01F6816Ed936c5c24aA8F1"
    
    # Query parameters
    params = {
        "limit": 1,
        "offset": 0,
        "chainIds": [8453],  # Default to Ethereum mainnet
        # Optional filters - uncomment and modify as needed:
        # "startBlock": "18000000",
        # "endBlock": "19000000", 
        # "startTime": "1640995200",  # Unix timestamp
        # "endTime": "1672531200"     # Unix timestamp
    }
    
    try:
        # Make the request
        # url = f"{base_url}/api/health"
        # url = f"{base_url}/api/evaults/latest"
        # url = f"{base_url}/api/evault/{eeusdc}/metrics"
        # url = f"{base_url}/api/collateralVaults"
        # url = f"{base_url}/api/collateralVaults/latest-snapshots"
        # url = f"{base_url}/api/collateralVaults/{collateral_vault_address}/latest-snapshot"
        url = f"{base_url}/api/collateralVaults/{collateral_vault_address}/history"
        # url = f"{base_url}/api/collateralVaults/external-liquidations"
        # url = f"{base_url}/api/collateralVaults/internal-liquidations"
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse and display results
        data = response.json()
        print(f"Data: {data}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error querying vault metrics: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None
    except KeyError as e:
        print(f"Unexpected response format, missing key: {e}")
        return None

# Execute the query
if __name__ == "__main__":
    result = query_vault_metrics(local=False)