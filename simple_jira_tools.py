#!/usr/bin/env python3
"""
Simple Jira MCP Server following the official examples
"""
import os
import logging
from dotenv import load_dotenv
from jira import JIRA
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='simple_jira_tools.log',
    filemode='w'
)
logger = logging.getLogger("jira-tools")

# Load environment variables
load_dotenv()

# Create server
mcp = FastMCP("jira")

# Connect to Jira using PAT if available, otherwise use basic auth
jira_host = os.getenv('JIRA_HOST')
jira_pat = os.getenv('JIRA_PAT')
jira_username = os.getenv('JIRA_USERNAME')
jira_password = os.getenv('JIRA_PASSWORD')

if jira_pat:
    # Use PAT authentication
    logger.info("Using PAT authentication")
    jira = JIRA(
        server=f"https://{jira_host}",
        token_auth=jira_pat
    )
else:
    # Fall back to basic authentication
    logger.info("Using basic authentication")
    jira = JIRA(
        server=f"https://{jira_host}",
        basic_auth=(jira_username, jira_password)
    )
logger.info(f"Connected to Jira: {jira_host}")

@mcp.tool()
def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    logger.info("Tool called: get_my_tickets")
    try:
        # Use the authenticated user's username for the query
        current_user = jira.myself()['name']
        jql = f'assignee = "{current_user}"'
        issues = jira.search_issues(jql)
        
        if not issues:
            return "You don't have any assigned tickets"
        
        ticket_text = "Your assigned tickets:\n\n"
        for issue in issues:
            ticket_text += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
        
        return ticket_text
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error retrieving tickets: {str(e)}"

@mcp.tool()
def get_ticket_details(ticket_key: str) -> str:
    """Get detailed information about a specific ticket.
    
    Args:
        ticket_key: The Jira ticket key (e.g., NCSFM-1234)
    """
    logger.info(f"Tool called: get_ticket_details for {ticket_key}")
    try:
        issue = jira.issue(ticket_key)
        
        details = f"""
Ticket: {ticket_key}
Summary: {issue.fields.summary}
Status: {issue.fields.status.name}
Priority: {issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else 'Not set'}
Assignee: {issue.fields.assignee.displayName if hasattr(issue.fields, 'assignee') and issue.fields.assignee else 'Unassigned'}
Reporter: {issue.fields.reporter.displayName if hasattr(issue.fields, 'reporter') and issue.fields.reporter else 'Unknown'}
Created: {issue.fields.created}
Updated: {issue.fields.updated}

Description:
{issue.fields.description if issue.fields.description else 'No description provided'}
"""
        return details
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error retrieving ticket details: {str(e)}"

def main():
    """
    Main entry point for the Jira MCP server.
    This function starts the MCP server.
    """
    logger.info("Starting Jira MCP server...")
    mcp.run()

if __name__ == "__main__":
    main() 