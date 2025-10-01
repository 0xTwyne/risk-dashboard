"""
Logging Configuration for Governance Notification System.
"""

import logging
import logging.handlers
from pathlib import Path

# Import from local config using importlib to avoid naming conflicts
import importlib.util

spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)

LOG_FILE_PATH = local_config.LOG_FILE_PATH
LOG_LEVEL = local_config.LOG_LEVEL
LOG_FORMAT = local_config.LOG_FORMAT
LOG_MAX_BYTES = local_config.LOG_MAX_BYTES
LOG_BACKUP_COUNT = local_config.LOG_BACKUP_COUNT


def setup_logging() -> None:
    """
    Configure logging with file and console handlers.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Ensure log directory exists
    log_path = Path(LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("ape").setLevel(logging.WARNING)
    
    logger.info("=" * 80)
    logger.info("Governance Notification System - Logging Initialized")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Log file: {LOG_FILE_PATH}")
    logger.info("=" * 80)


