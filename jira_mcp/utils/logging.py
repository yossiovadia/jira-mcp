"""
Logging configuration for the Jira MCP package
"""
import os
import logging
from datetime import datetime

def configure_logging(log_dir=None, log_level=logging.DEBUG):
    """
    Configure logging for the Jira MCP package
    
    Args:
        log_dir: Optional directory for log files. If None, logs to the current directory
        log_level: Logging level (default: DEBUG)
    
    Returns:
        Logger instance
    """
    # Ensure log directory exists
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"jira_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    else:
        log_file = f"jira_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w'
    )
    
    # Create module logger
    logger = logging.getLogger("jira-mcp")
    
    # Add console handler for INFO level and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger

# Default logger
logger = configure_logging() 