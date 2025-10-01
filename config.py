"""
Configuration module for Risk Dashboard.
Centralizes all configuration settings and environment variables.
"""

import os
import logging
import logging.handlers
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Main configuration class for the dashboard."""
    
    # API Settings
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://cdf169f4ba-main.idx.sim.io")
    API_KEY: str = os.getenv("API_KEY", "")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    API_MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))
    

    
    # Dashboard Settings
    AUTO_REFRESH_INTERVAL: int = int(os.getenv("AUTO_REFRESH_INTERVAL", "30000"))  # milliseconds
    PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # Development Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: str = os.getenv("LOG_FILE", "risk_dashboard.log")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # UI Settings
    THEME: str = os.getenv("THEME", "light")
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    NUMBER_FORMAT: str = "{:,.2f}"
    
    # API Endpoints
    ENDPOINTS = {
        "evaults_latest": "/api/evaults/latest",
        "evault_metrics": "/api/evault/{address}/metrics",
        "collateral_vaults": "/api/collateralVaults",
        "collateral_latest_snapshots": "/api/collateralVaults/latest-snapshots",
        "collateral_vault_latest": "/api/collateralVaults/{address}/latest-snapshot",
        "collateral_vault_history": "/api/collateralVaults/{address}/history",
        "external_liquidations": "/api/collateralVaults/external-liquidations",
        "internal_liquidations": "/api/collateralVaults/internal-liquidations",
        "chainlink_latest": "/api/chainlink/latest-answers",
        "health": "/api/health",
        "gov_set_caps": "/api/gov-set-caps",
        "gov_set_config_flags": "/api/gov-set-config-flags",
        "gov_set_fee_receiver": "/api/gov-set-fee-receiver",
        "gov_set_governor_admin": "/api/gov-set-governor-admin",
        "gov_set_hook_config": "/api/gov-set-hook-config",
        "gov_set_interest_fee": "/api/gov-set-interest-fee",
        "gov_set_interest_rate_model": "/api/gov-set-interest-rate-model",
        "gov_set_liquidation_cool_off_time": "/api/gov-set-liquidation-cool-off-time",
        "gov_set_ltv": "/api/gov-set-ltv",
        "gov_set_max_liquidation_discount": "/api/gov-set-max-liquidation-discount"
    }
    
    @classmethod
    def get_api_url(cls, endpoint: str, **kwargs) -> str:
        """
        Build full API URL for a given endpoint.
        
        Args:
            endpoint: Key from ENDPOINTS dict
            **kwargs: Parameters to format into the URL
            
        Returns:
            Full API URL
        """
        if endpoint not in cls.ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        
        path = cls.ENDPOINTS[endpoint].format(**kwargs)
        return f"{cls.API_BASE_URL.rstrip('/')}{path}"
    
    @classmethod
    def get_headers(cls) -> dict:
        """Get API request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cls.API_KEY}"
        }


    @classmethod
    def setup_logging(cls) -> None:
        """
        Configure application logging with file and console handlers.
        """
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set specific logger levels
        logging.getLogger("werkzeug").setLevel(logging.WARNING)  # Reduce Flask noise
        logging.getLogger("urllib3").setLevel(logging.WARNING)   # Reduce requests noise
        
        logger.info("Logging system initialized")
        logger.info(f"Log level: {cls.LOG_LEVEL}")
        logger.info(f"Log file: {cls.LOG_FILE}")


# Create singleton instance
config = Config()
