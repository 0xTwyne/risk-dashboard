"""
Vault Address Collection.
Collects all Twyne and related Euler vault addresses for monitoring.
"""

import json
import logging
from typing import List, Set
from pathlib import Path
from ape import networks, Contract

from src.api import api_client
# Import from local config using importlib to avoid naming conflicts
import importlib.util

spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)

CONTRACTS = local_config.CONTRACTS
DEFAULT_CHAIN_ID = local_config.DEFAULT_CHAIN_ID


def load_abi(contract_name: str) -> dict:
    """
    Load ABI from the abis/ directory.
    
    Args:
        contract_name: Name of the contract (e.g., 'EVault', 'VaultManager')
        
    Returns:
        Contract ABI as dictionary
        
    Raises:
        FileNotFoundError: If ABI file doesn't exist
        json.JSONDecodeError: If ABI file is invalid JSON
    """
    # Get the project root directory (parent of gov-set-notis)
    project_root = Path(__file__).parent.parent
    abi_path = project_root / "abis" / f"{contract_name}.json"
    
    if not abi_path.exists():
        raise FileNotFoundError(f"ABI file not found: {abi_path}")
    
    with open(abi_path, 'r') as f:
        abi = json.load(f)
    
    logger.debug(f"Loaded ABI for {contract_name} from {abi_path}")
    return abi

logger = logging.getLogger(__name__)


def get_twyne_vaults_from_api(chain_id: int = DEFAULT_CHAIN_ID) -> List[str]:
    """
    Fetch all Twyne EVaults (symbols starting with 'ee') from API.
    
    Args:
        chain_id: Chain ID to filter vaults
        
    Returns:
        List of Twyne vault addresses
    """
    try:
        logger.info(f"Fetching Twyne vaults from API for chain {chain_id}...")
        
        # Fetch all EVaults
        response = api_client.get_evaults_latest()
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error fetching EVaults: {response['error']}")
            return []
        
        # Extract metrics
        metrics = response.latestMetrics or []
        
        # Filter for Twyne vaults (symbols starting with "ee") and matching chain
        twyne_vaults = []
        for metric in metrics:
            # Check if it's a Twyne vault (case-sensitive)
            if metric.symbol.startswith("ee"):
                # Check chain ID
                if int(metric.chainId) == chain_id:
                    twyne_vaults.append(metric.vaultAddress)
        
        logger.info(f"Found {len(twyne_vaults)} Twyne vaults on chain {chain_id}")
        return twyne_vaults
        
    except Exception as e:
        logger.error(f"Error fetching Twyne vaults from API: {e}", exc_info=True)
        return []


def get_euler_vaults_for_twyne_vault(
    twyne_vault_address: str,
    chain_id: int = DEFAULT_CHAIN_ID
) -> Set[str]:
    """
    For a given Twyne vault, get associated Euler vaults using Ape framework.
    
    This function:
    1. Calls TwyneEVault.asset() to get a single address
    2. Calls VaultManager.targetVaultLength() to get N
    3. Loops i in range(N): calls VaultManager.allowedTargetVaultList(twyneVault, i)
    
    Args:
        twyne_vault_address: Address of Twyne EVault
        chain_id: Chain ID
        
    Returns:
        Set of Euler vault addresses
    """
    euler_vaults = set()
    
    try:
        # Get contract addresses and RPC from config
        if chain_id not in CONTRACTS:
            logger.error(f"Chain ID {chain_id} not configured in CONTRACTS")
            return euler_vaults
        
        config = CONTRACTS[chain_id]
        vault_manager_address = config.get("VAULT_MANAGER")
        rpc_url = config.get("RPC_URL")
        
        if not vault_manager_address or vault_manager_address.startswith("PLACEHOLDER"):
            logger.error(f"VaultManager address not configured for chain {chain_id}")
            return euler_vaults
        
        if not rpc_url or rpc_url.startswith("PLACEHOLDER"):
            logger.error(f"RPC URL not configured for chain {chain_id}")
            return euler_vaults
        
        logger.info(f"Fetching Euler vaults for Twyne vault {twyne_vault_address} on chain {chain_id}")
        
        # Connect to network using Ape
        with networks.parse_network_choice(f"ethereum:mainnet:{rpc_url}"):
            # Load contracts with ABIs from local files
            try:
                evault_abi = load_abi("EVault")
                vault_manager_abi = load_abi("VaultManager")
                
                twyne_evault = Contract(twyne_vault_address, abi=evault_abi)
                vault_manager = Contract(vault_manager_address, abi=vault_manager_abi)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load ABI: {e}")
                return euler_vaults
            
            # Step 1: Get asset from Twyne EVault
            asset_address = twyne_evault.asset()
            logger.info(f"  Asset for {twyne_vault_address}: {asset_address}")
            euler_vaults.add(asset_address)
            
            # Step 2: Get target vault count from VaultManager (requires intermediate vault address)
            target_vault_count = vault_manager.targetVaultLength(twyne_vault_address)
            logger.info(f"  Target vault count: {target_vault_count}")
            
            # Step 3: Get all allowed target vaults
            for i in range(target_vault_count):
                target_vault = vault_manager.allowedTargetVaultList(twyne_vault_address, i)
                logger.info(f"  Target vault {i}: {target_vault}")
                euler_vaults.add(target_vault)
        
        logger.info(f"Found {len(euler_vaults)} Euler vaults for Twyne vault {twyne_vault_address}")
        return euler_vaults
        
    except Exception as e:
        logger.error(f"Error fetching Euler vaults for {twyne_vault_address}: {e}", exc_info=True)
        logger.info(f"Skipping Euler vaults for {twyne_vault_address}, continuing with others")
        return euler_vaults


def get_all_monitored_vaults(chain_id: int = DEFAULT_CHAIN_ID) -> Set[str]:
    """
    Get complete set of vaults to monitor (Twyne + Euler).
    
    Args:
        chain_id: Chain ID to get vaults for
        
    Returns:
        Set of all unique vault addresses to monitor
    """
    all_vaults = set()
    
    try:
        logger.info(f"Collecting all monitored vaults for chain {chain_id}...")
        
        # Step 1: Get Twyne vaults from API
        twyne_vaults = get_twyne_vaults_from_api(chain_id)
        
        if not twyne_vaults:
            logger.warning(f"No Twyne vaults found for chain {chain_id}")
            return all_vaults
        
        # Add Twyne vaults to monitoring set
        all_vaults.update(twyne_vaults)
        logger.info(f"Added {len(twyne_vaults)} Twyne vaults to monitoring set")
        
        # Step 2: For each Twyne vault, get associated Euler vaults
        total_euler_vaults = set()
        
        for twyne_vault in twyne_vaults:
            euler_vaults = get_euler_vaults_for_twyne_vault(twyne_vault, chain_id)
            total_euler_vaults.update(euler_vaults)
        
        # Add Euler vaults to monitoring set
        all_vaults.update(total_euler_vaults)
        logger.info(f"Added {len(total_euler_vaults)} unique Euler vaults to monitoring set")
        
        logger.info(f"Total vaults to monitor: {len(all_vaults)}")
        return all_vaults
        
    except Exception as e:
        logger.error(f"Error collecting monitored vaults: {e}", exc_info=True)
        return all_vaults


