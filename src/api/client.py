"""
API client for the Risk Dashboard.
Handles all API communication with error handling, retries, and caching.
"""

import logging
from typing import Dict, List, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config
from .models import (
    CollateralVaultsSnapshotsResponse,
    CollateralVaultsResponse,
    CollateralVaultHistoryResponse,
    ExternalLiquidationsResponse,
    InternalLiquidationsResponse,
    EVaultMetricsResponse,
    ChainlinkAnswersResponse,
    HealthCheckResponse,
    APIError
)

# Configure logging
logger = logging.getLogger(__name__)


class APIClient:
    """
    Main API client for the Risk Dashboard.
    Handles authentication, retries, and error handling.
    """
    
    def __init__(self):
        self.config = Config()
        self.session = self._create_session()
        
        logger.info("APIClient initialized")
        logger.info(f"API Base URL: {self.config.API_BASE_URL}")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and timeouts."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.API_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(self.config.get_headers())
        
        return session
    

    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout))
    )
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint key from config
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            requests.RequestException: On API errors
        """
        # Build URL
        url = self.config.get_api_url(endpoint)
        
        try:
            logger.info(f"Making {method} request to {url}")
            logger.debug(f"Request params: {params}")
            logger.debug(f"Request headers: {dict(self.session.headers)}")
            
            start_time = time.time()
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.config.API_TIMEOUT
            )
            request_duration = time.time() - start_time
            
            logger.info(f"Request completed in {request_duration:.2f}s - Status: {response.status_code}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            logger.info(f"Response data size: {len(str(data))} characters")
            
            if isinstance(data, dict):
                if "latestSnapshots" in data:
                    logger.info(f"Response contains {len(data['latestSnapshots'])} snapshots")
                elif "vaults" in data:
                    logger.info(f"Response contains {len(data['vaults'])} vaults")
                elif "error" in data:
                    logger.warning(f"API returned error response: {data['error']}")
            
            return data
            
        except requests.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            if e.response.status_code == 404:
                return {"error": "Resource not found"}
            elif e.response.status_code == 400:
                return {"error": "Bad request - check parameters"}
            else:
                return {"error": f"HTTP {e.response.status_code} error"}
                
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
    
    def get_health(self) -> Union[HealthCheckResponse, Dict[str, str]]:
        """Get API health status."""
        try:
            data = self._make_request("GET", "health")
            if "error" in data:
                return data
            return HealthCheckResponse(**data)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"error": str(e)}
    
    def get_collateral_vaults_snapshots(
        self,
        limit: int = 50,
        offset: int = 0,
        can_liquidate: Optional[bool] = None,
        is_externally_liquidated: Optional[bool] = None
    ) -> Union[CollateralVaultsSnapshotsResponse, Dict[str, str]]:
        """
        Get latest position snapshots for collateral vaults.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            can_liquidate: Filter by liquidation status
            is_externally_liquidated: Filter by external liquidation status
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        if can_liquidate is not None:
            params["canLiquidate"] = str(can_liquidate).lower()
        if is_externally_liquidated is not None:
            params["isExternallyLiquidated"] = str(is_externally_liquidated).lower()
        
        logger.info(f"Fetching collateral vaults snapshots with params: {params}")
        
        try:
            data = self._make_request("GET", "collateral_latest_snapshots", params)
            if "error" in data:
                logger.error(f"API returned error for collateral snapshots: {data['error']}")
                return data
            
            response = CollateralVaultsSnapshotsResponse(**data)
            logger.info(f"Successfully fetched {len(response.latestSnapshots)} collateral vault snapshots")
            return response
        except Exception as e:
            logger.error(f"Failed to get collateral vaults snapshots: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_collateral_vaults(
        self,
        limit: int = 50,
        offset: int = 0,
        block_number: Optional[int] = None
    ) -> Union[CollateralVaultsResponse, Dict[str, str]]:
        """
        Get all created collateral vaults.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            block_number: Filter vaults created up to this block number
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        if block_number is not None:
            params["endBlock"] = block_number
        
        try:
            data = self._make_request("GET", "collateral_vaults", params)
            if "error" in data:
                return data
            return CollateralVaultsResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get collateral vaults: {e}")
            return {"error": str(e)}
    
    def get_collateral_vault_history(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Union[CollateralVaultHistoryResponse, Dict[str, str]]:
        """
        Get historical snapshots for a specific collateral vault.
        
        Args:
            address: Collateral vault address
            limit: Number of results to return
            offset: Number of results to skip
            start_block: Start block number filter
            end_block: End block number filter
            start_time: Start time filter (Unix timestamp)
            end_time: End time filter (Unix timestamp)
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        if start_block is not None:
            params["startBlock"] = start_block
        
        if end_block is not None:
            params["endBlock"] = end_block
        
        if start_time is not None:
            params["startTime"] = start_time
        
        if end_time is not None:
            params["endTime"] = end_time
        
        try:
            # Build URL with address parameter
            url = self.config.get_api_url("collateral_vault_history", address=address)
            
            logger.info(f"Making GET request to {url}")
            logger.debug(f"Request params: {params}")
            
            start_time = time.time()
            response = self.session.request(
                method="GET",
                url=url,
                params=params,
                timeout=self.config.API_TIMEOUT
            )
            request_duration = time.time() - start_time
            
            logger.info(f"Request completed in {request_duration:.2f}s - Status: {response.status_code}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            logger.info(f"Response data size: {len(str(data))} characters")
            
            if "error" in data:
                return data
            return CollateralVaultHistoryResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get collateral vault history for {address}: {e}")
            return {"error": str(e)}
    
    def get_external_liquidations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Union[ExternalLiquidationsResponse, Dict[str, str]]:
        """
        Get external liquidation events.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        try:
            data = self._make_request("GET", "external_liquidations", params)
            if "error" in data:
                return data
            return ExternalLiquidationsResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get external liquidations: {e}")
            return {"error": str(e)}
    
    def get_internal_liquidations(
        self,
        limit: int = 50,
        offset: int = 0,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None
    ) -> Union[InternalLiquidationsResponse, Dict[str, str]]:
        """
        Get internal liquidation events.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            start_block: Filter by minimum block number
            end_block: Filter by maximum block number
            start_timestamp: Filter by minimum timestamp
            end_timestamp: Filter by maximum timestamp
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        if start_block is not None:
            params["startBlock"] = start_block
        if end_block is not None:
            params["endBlock"] = end_block
        if start_timestamp is not None:
            params["startTimestamp"] = start_timestamp
        if end_timestamp is not None:
            params["endTimestamp"] = end_timestamp
        
        try:
            data = self._make_request("GET", "internal_liquidations", params)
            if "error" in data:
                return data
            return InternalLiquidationsResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get internal liquidations: {e}")
            return {"error": str(e)}
    
    def get_evaults_latest(self) -> Union[EVaultMetricsResponse, Dict[str, str]]:
        """
        Get latest metrics for all EVaults.
        
        Returns:
            API response or error dict
        """
        try:
            data = self._make_request("GET", "evaults_latest")
            if "error" in data:
                return data
            return EVaultMetricsResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get latest EVaults: {e}")
            return {"error": str(e)}
    
    def get_evault_metrics(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Union[EVaultMetricsResponse, Dict[str, str]]:
        """
        Get historical metrics for specific EVault.
        
        Args:
            address: Vault address
            limit: Number of results to return
            offset: Number of results to skip
            start_block: Filter by minimum block number
            end_block: Filter by maximum block number
            start_time: Filter by minimum timestamp
            end_time: Filter by maximum timestamp
            
        Returns:
            API response or error dict
        """
        params = {"limit": limit, "offset": offset}
        
        if start_block is not None:
            params["startBlock"] = start_block
        if end_block is not None:
            params["endBlock"] = end_block
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        
        try:
            # Build URL with address parameter  
            url = self.config.get_api_url("evault_metrics", address=address)
            
            logger.info(f"Making GET request to {url}")
            logger.debug(f"Request params: {params}")
            
            start_time = time.time()
            response = self.session.request(
                method="GET",
                url=url,
                params=params,
                timeout=self.config.API_TIMEOUT
            )
            request_duration = time.time() - start_time
            
            logger.info(f"Request completed in {request_duration:.2f}s - Status: {response.status_code}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            logger.info(f"Response data size: {len(str(data))} characters")
            logger.debug(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            if "error" in data:
                return data
            return EVaultMetricsResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get EVault metrics for {address}: {e}")
            return {"error": str(e)}
    
    def get_chainlink_latest(self) -> Union[ChainlinkAnswersResponse, Dict[str, str]]:
        """
        Get latest Chainlink price feed updates.
        
        Returns:
            API response or error dict
        """
        try:
            data = self._make_request("GET", "chainlink_latest")
            if "error" in data:
                return data
            return ChainlinkAnswersResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get Chainlink latest: {e}")
            return {"error": str(e)}
    
    def get_gov_set_events(
        self,
        event_type: str,
        vault_address: Optional[str] = None,
        chain_ids: Optional[List[int]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Union[Dict[str, Any], Dict[str, str]]:
        """
        Get governance parameter update events.
        
        Args:
            event_type: Type of gov-set event (e.g., "gov-set-caps", "gov-set-ltv")
            vault_address: Optional vault address filter
            chain_ids: Optional list of chain IDs to filter
            limit: Number of results to return
            offset: Number of results to skip
            
        Returns:
            API response or error dict
        """
        # Map event type to endpoint key
        endpoint_map = {
            "gov-set-caps": "gov_set_caps",
            "gov-set-config-flags": "gov_set_config_flags",
            "gov-set-fee-receiver": "gov_set_fee_receiver",
            "gov-set-governor-admin": "gov_set_governor_admin",
            "gov-set-hook-config": "gov_set_hook_config",
            "gov-set-interest-fee": "gov_set_interest_fee",
            "gov-set-interest-rate-model": "gov_set_interest_rate_model",
            "gov-set-liquidation-cool-off-time": "gov_set_liquidation_cool_off_time",
            "gov-set-ltv": "gov_set_ltv",
            "gov-set-max-liquidation-discount": "gov_set_max_liquidation_discount"
        }
        
        if event_type not in endpoint_map:
            logger.error(f"Unknown gov-set event type: {event_type}")
            return {"error": f"Unknown event type: {event_type}"}
        
        endpoint_key = endpoint_map[event_type]
        
        params = {"limit": min(limit, 100), "offset": offset}
        
        if vault_address:
            params["vaultAddress"] = vault_address
        
        if chain_ids:
            params["chainIds"] = ",".join(map(str, chain_ids))
        
        try:
            logger.info(f"Fetching {event_type} events with params: {params}")
            data = self._make_request("GET", endpoint_key, params)
            
            if "error" in data:
                logger.error(f"API returned error for {event_type}: {data['error']}")
                return data
            
            logger.info(f"Successfully fetched {len(data.get('events', []))} {event_type} events")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get {event_type} events: {e}", exc_info=True)
            return {"error": str(e)}


# Create singleton instance
api_client = APIClient()
