"""
Data formatting utilities.
"""

from typing import Union, Optional
from datetime import datetime
from decimal import Decimal


def format_address(address: str, short: bool = True) -> str:
    """
    Format Ethereum address for display.
    
    Args:
        address: Ethereum address
        short: Whether to shorten the address
        
    Returns:
        Formatted address
    """
    if not address:
        return ""
    
    address = address.lower()
    if not address.startswith("0x"):
        address = f"0x{address}"
    
    if short and len(address) > 10:
        return f"{address[:6]}...{address[-4:]}"
    
    return address


def format_currency(
    value: Union[str, int, float, Decimal],
    decimals: int = 2,
    symbol: str = "$"
) -> str:
    """
    Format value as currency.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        symbol: Currency symbol
        
    Returns:
        Formatted currency string
    """
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        if decimals == 0:
            return f"{symbol}{value:,.0f}"
        else:
            return f"{symbol}{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return f"{symbol}0.00"


def format_percentage(
    value: Union[str, int, float, Decimal],
    decimals: int = 2
) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Numeric value (already in percentage, not decimal)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        return f"{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return "0.00%"


def format_number(
    value: Union[str, int, float, Decimal],
    decimals: Optional[int] = None,
    compact: bool = False
) -> str:
    """
    Format number for display.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places (None for auto)
        compact: Use compact notation (K, M, B)
        
    Returns:
        Formatted number string
    """
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        if compact:
            if abs(value) >= 1e9:
                return f"{value/1e9:.2f}B"
            elif abs(value) >= 1e6:
                return f"{value/1e6:.2f}M"
            elif abs(value) >= 1e3:
                return f"{value/1e3:.2f}K"
        
        if decimals is None:
            # Auto-detect decimal places
            if value == int(value):
                return f"{int(value):,}"
            else:
                return f"{value:,.2f}"
        elif decimals == 0:
            return f"{int(value):,}"
        else:
            return f"{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return "0"


def format_timestamp(
    timestamp: Union[str, int, float],
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format Unix timestamp for display.
    
    Args:
        timestamp: Unix timestamp (seconds)
        format_str: strftime format string
        
    Returns:
        Formatted datetime string
    """
    try:
        if isinstance(timestamp, str):
            timestamp = int(timestamp)
        
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format_str)
    except (ValueError, TypeError, OSError):
        return ""


def format_block_number(block: Union[str, int]) -> str:
    """
    Format block number for display.
    
    Args:
        block: Block number
        
    Returns:
        Formatted block number
    """
    try:
        if isinstance(block, str):
            block = int(block)
        return f"#{block:,}"
    except (ValueError, TypeError):
        return "#0"


def format_transaction_hash(
    tx_hash: str,
    short: bool = True,
    etherscan_url: Optional[str] = None
) -> str:
    """
    Format transaction hash for display.
    
    Args:
        tx_hash: Transaction hash
        short: Whether to shorten the hash
        etherscan_url: Optional Etherscan base URL for link
        
    Returns:
        Formatted transaction hash (with optional link)
    """
    if not tx_hash:
        return ""
    
    if not tx_hash.startswith("0x"):
        tx_hash = f"0x{tx_hash}"
    
    display = tx_hash
    if short and len(tx_hash) > 10:
        display = f"{tx_hash[:10]}...{tx_hash[-8:]}"
    
    if etherscan_url:
        return f"[{display}]({etherscan_url}/tx/{tx_hash})"
    
    return display


def format_wei_to_ether(
    wei_value: Union[str, int],
    decimals: int = 4
) -> str:
    """
    Convert wei to ether and format.
    
    Args:
        wei_value: Value in wei
        decimals: Number of decimal places
        
    Returns:
        Formatted ether value
    """
    try:
        if isinstance(wei_value, str):
            wei_value = int(wei_value)
        
        ether = wei_value / 10**18
        return f"{ether:.{decimals}f} ETH"
    except (ValueError, TypeError):
        return "0.0000 ETH"
