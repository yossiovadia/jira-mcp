"""
Security utility functions for the Jira MCP package
"""
import os
import re
from .logging import logger

def validate_ticket_key(ticket_key):
    """
    Validate a Jira ticket key format to prevent path traversal attacks.
    
    Args:
        ticket_key: The Jira ticket key to validate
        
    Returns:
        bool: True if the ticket key is valid, False otherwise
    """
    return bool(re.match(r'^[A-Z]+-\d+$', ticket_key))

def sanitize_filename(filename):
    """
    Sanitize a filename to prevent path traversal attacks while preserving spaces and parentheses.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        str: The sanitized filename
    """
    # Remove dangerous characters but preserve spaces and parentheses
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Ensure we only get the basename
    sanitized = os.path.basename(sanitized)
    return sanitized

def validate_path_safety(path, base_dirs):
    """
    Validate that a path is contained within one of the base directories.
    
    Args:
        path: The path to validate
        base_dirs: List of allowed base directories
        
    Returns:
        bool: True if the path is safe, False otherwise
    """
    normalized_path = os.path.normpath(path)
    return any(
        os.path.commonpath([normalized_path, os.path.normpath(base_dir)]) == os.path.normpath(base_dir)
        for base_dir in base_dirs
    )

def is_allowed_file_extension(filename, allowed_extensions):
    """
    Check if a file has an allowed extension.
    
    Args:
        filename: The filename to check
        allowed_extensions: List of allowed extensions (with dot, e.g. ['.txt', '.pdf'])
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions

def check_file_size(file_path, max_size_bytes):
    """
    Check if a file exceeds a maximum size.
    
    Args:
        file_path: Path to the file
        max_size_bytes: Maximum allowed size in bytes
        
    Returns:
        bool: True if the file size is within limits, False otherwise
    """
    try:
        size = os.path.getsize(file_path)
        return size <= max_size_bytes
    except Exception as e:
        logger.error(f"Error checking file size: {str(e)}")
        return False 