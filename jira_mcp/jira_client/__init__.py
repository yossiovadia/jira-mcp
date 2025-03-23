"""
Jira client module for the Jira MCP
"""
from .client import initialize_jira_clients, get_jira_client, get_primary_jira, get_secondary_jira

# Re-export for simpler imports
__all__ = ['initialize_jira_clients', 'get_jira_client', 'get_primary_jira', 'get_secondary_jira'] 