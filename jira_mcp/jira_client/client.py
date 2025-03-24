"""
Jira client functionality for the Jira MCP package
"""
import re
from jira import JIRA
from ..utils.logging import logger
from ..config import config

# Global Jira client instances
primary_jira = None
secondary_jira = None
nokia_jira = None  # For backward compatibility
redhat_jira = None  # For backward compatibility

def initialize_jira_clients():
    """
    Initialize all configured Jira clients
    
    Returns:
        bool: True if at least one Jira instance was successfully initialized
    """
    global primary_jira, secondary_jira, nokia_jira, redhat_jira
    
    success = False
    
    # Initialize Primary Jira
    try:
        if config.primary_jira_pat:
            # Use Bearer token authentication for Primary Jira
            logger.info("Initializing Primary Jira with Bearer token authentication")
            logger.info(f"Primary Jira host: {config.primary_jira_host}")
            primary_jira = JIRA(
                server=f"https://{config.primary_jira_host}",
                options={
                    'headers': {
                        'Authorization': f'Bearer {config.primary_jira_pat}'
                    }
                }
            )
        elif config.primary_jira_username and config.primary_jira_password:
            # Fall back to basic authentication
            logger.info("Initializing Primary Jira with basic authentication")
            primary_jira = JIRA(
                server=f"https://{config.primary_jira_host}",
                basic_auth=(config.primary_jira_username, config.primary_jira_password)
            )
        
        if primary_jira:
            # Test connection
            myself = primary_jira.myself()
            logger.info(f"Connected to Primary Jira: {config.primary_jira_host} as {myself['displayName']} ({myself['name']})")
            
            # Set up for backward compatibility
            nokia_jira = primary_jira
            success = True
    except Exception as e:
        logger.error(f"Error connecting to Primary Jira: {str(e)}")
        primary_jira = None
        nokia_jira = None
    
    # Initialize Secondary Jira
    try:
        if config.secondary_jira_pat:
            # Use PAT authentication for Secondary Jira
            logger.info("Initializing Secondary Jira with PAT authentication")
            logger.info(f"Secondary Jira host: {config.secondary_jira_host}")
            secondary_jira = JIRA(
                server=f"https://{config.secondary_jira_host}",
                token_auth=config.secondary_jira_pat
            )
            # Test connection
            myself = secondary_jira.myself()
            logger.info(f"Connected to Secondary Jira: {config.secondary_jira_host} as {myself['displayName']} ({myself['name']})")
            
            # Set up for backward compatibility
            redhat_jira = secondary_jira
            success = True
    except Exception as e:
        logger.error(f"Error connecting to Secondary Jira: {str(e)}")
        secondary_jira = None
        redhat_jira = None
    
    # Log summary status message
    if not success:
        logger.warning("Not connected to any Jira instance. Check your credentials and network connection.")
    
    return success

def get_jira_client(ticket_key):
    """
    Determine which Jira client to use based on ticket key prefix.
    If the prefix matches a Secondary Jira project, use Secondary Jira.
    Otherwise, use Primary Jira if the project is in the allowed list.
    
    Args:
        ticket_key: The Jira ticket key to check
        
    Returns:
        JIRA: The appropriate Jira client or None if no clients are initialized
    """
    if not ticket_key:
        return None
    
    # Extract project prefix (e.g., "CNV" from "CNV-12345")
    match = re.match(r'^([A-Z]+)-\d+', ticket_key)
    if not match:
        logger.warning(f"Invalid ticket key format: {ticket_key}")
        return None
    
    project_prefix = match.group(1)
    
    # Check if this is a Secondary Jira project
    if (project_prefix in config.secondary_project_prefixes or 
        project_prefix in config.redhat_project_prefixes):
        logger.info(f"Using Secondary Jira for ticket {ticket_key}")
        return secondary_jira
    else:
        # Check if project is in allowed list for Primary Jira
        if not config.allowed_projects or project_prefix in config.allowed_projects:
            logger.info(f"Using Primary Jira for ticket {ticket_key}")
            return primary_jira
        else:
            logger.warning(f"Project {project_prefix} not in allowed list: {config.allowed_projects}")
            return None

def get_primary_jira():
    """
    Get the primary Jira client instance
    
    Returns:
        JIRA: The primary Jira client or None if not initialized
    """
    return primary_jira

def get_secondary_jira():
    """
    Get the secondary Jira client instance
    
    Returns:
        JIRA: The secondary Jira client or None if not initialized
    """
    return secondary_jira 