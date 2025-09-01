"""
Logging utilities for the Risk Dashboard.
Provides helper functions for logging and debugging.
"""

import logging
import json
from typing import Any, Dict
from datetime import datetime


def log_function_call(func_name: str, *args, **kwargs) -> None:
    """
    Log function call with arguments.
    
    Args:
        func_name: Name of the function being called
        *args: Positional arguments
        **kwargs: Keyword arguments
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"CALL {func_name}(args={args}, kwargs={kwargs})")


def log_api_response(endpoint: str, response: Any, duration: float = None) -> None:
    """
    Log API response details.
    
    Args:
        endpoint: API endpoint called
        response: Response data
        duration: Request duration in seconds
    """
    logger = logging.getLogger(__name__)
    
    if duration:
        logger.info(f"API {endpoint} completed in {duration:.2f}s")
    
    if isinstance(response, dict):
        if "error" in response:
            logger.error(f"API {endpoint} error: {response['error']}")
        else:
            # Log response structure without full data
            keys = list(response.keys())
            logger.info(f"API {endpoint} response keys: {keys}")
            
            # Log counts if available
            for key in ["latestSnapshots", "vaults", "metrics"]:
                if key in response and isinstance(response[key], list):
                    logger.info(f"API {endpoint} returned {len(response[key])} {key}")


def log_data_processing(operation: str, input_count: int, output_count: int, details: str = None) -> None:
    """
    Log data processing operations.
    
    Args:
        operation: Description of the operation
        input_count: Number of input records
        output_count: Number of output records
        details: Additional details
    """
    logger = logging.getLogger(__name__)
    logger.info(f"DATA {operation}: {input_count} → {output_count} records")
    if details:
        logger.debug(f"DATA {operation} details: {details}")


def log_component_render(component_name: str, props: Dict[str, Any] = None) -> None:
    """
    Log component rendering.
    
    Args:
        component_name: Name of the component being rendered
        props: Component properties
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"RENDER {component_name}")
    if props:
        logger.debug(f"RENDER {component_name} props: {list(props.keys())}")


def log_callback_trigger(callback_name: str, inputs: Dict[str, Any] = None) -> None:
    """
    Log callback trigger.
    
    Args:
        callback_name: Name of the callback
        inputs: Input values that triggered the callback
    """
    logger = logging.getLogger(__name__)
    logger.info(f"CALLBACK {callback_name} triggered")
    if inputs:
        logger.debug(f"CALLBACK {callback_name} inputs: {inputs}")


def log_error_with_context(error: Exception, context: str, additional_data: Dict[str, Any] = None) -> None:
    """
    Log error with additional context.
    
    Args:
        error: Exception that occurred
        context: Context where the error occurred
        additional_data: Additional data for debugging
    """
    logger = logging.getLogger(__name__)
    logger.error(f"ERROR in {context}: {str(error)}", exc_info=True)
    
    if additional_data:
        logger.error(f"ERROR context data: {additional_data}")


def setup_debug_logging() -> None:
    """
    Set up debug-level logging for troubleshooting.
    """
    logging.getLogger().setLevel(logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("Debug logging enabled")


def log_dict_summary(data: Dict[str, Any], name: str = "data") -> None:
    """
    Log a summary of dictionary contents without logging sensitive data.
    
    Args:
        data: Dictionary to summarize
        name: Name for the data in logs
    """
    logger = logging.getLogger(__name__)
    
    if not isinstance(data, dict):
        logger.debug(f"{name} type: {type(data)}")
        return
    
    logger.debug(f"{name} keys: {list(data.keys())}")
    
    for key, value in data.items():
        if isinstance(value, list):
            logger.debug(f"{name}.{key}: list with {len(value)} items")
        elif isinstance(value, dict):
            logger.debug(f"{name}.{key}: dict with {len(value)} keys")
        else:
            logger.debug(f"{name}.{key}: {type(value).__name__}")


def get_current_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
