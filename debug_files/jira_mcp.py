import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jira import JIRA
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jira_mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("jira")

# Initialize Jira client
try:
    jira = JIRA(
        server=f"https://{os.getenv('JIRA_HOST')}",
        basic_auth=(os.getenv('JIRA_USERNAME'), os.getenv('JIRA_PASSWORD'))
    )
    logger.info("Successfully connected to Jira")
except Exception as e:
    logger.error(f"Failed to connect to Jira: {str(e)}")
    raise

@mcp.tool()
async def get_ticket_creator(ticket_key: str) -> str:
    """Get the creator of a Jira ticket.
    Args:
        ticket_key: The Jira ticket key (e.g., NCSFM-1234)
    """
    try:
        logger.debug(f"Fetching creator for ticket {ticket_key}")
        issue = jira.issue(ticket_key)
        creator = issue.fields.creator.displayName
        response = f"Ticket {ticket_key} was created by {creator}"
        logger.debug(f"Response: {response}")
        return response
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_ticket_comments(ticket_key: str) -> str:
    """Get all comments for a Jira ticket.
    Args:
        ticket_key: The Jira ticket key (e.g., NCSFM-1234)
    """
    try:
        logger.debug(f"Fetching comments for ticket {ticket_key}")
        issue = jira.issue(ticket_key)
        comments = issue.fields.comment.comments
        if not comments:
            return f"No comments found for ticket {ticket_key}"
        
        comment_text = f"Comments for ticket {ticket_key}:\n\n"
        for comment in comments:
            comment_text += f"- {comment.author.displayName} ({comment.created}):\n{comment.body}\n\n"
        
        logger.debug(f"Found {len(comments)} comments")
        return comment_text
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    try:
        logger.debug("Fetching tickets assigned to current user")
        jql = f'assignee = "{os.getenv("JIRA_USERNAME")}"'
        issues = jira.search_issues(jql)
        
        if not issues:
            return "You don't have any assigned tickets"
        
        ticket_text = "Your assigned tickets:\n\n"
        for issue in issues:
            ticket_text += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
        
        logger.debug(f"Found {len(issues)} assigned tickets")
        return ticket_text
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_ticket_details(ticket_key: str) -> str:
    """Get detailed information about a Jira ticket.
    Args:
        ticket_key: The Jira ticket key (e.g., NCSFM-1234)
    """
    try:
        logger.debug(f"Fetching details for ticket {ticket_key}")
        issue = jira.issue(ticket_key)
        details = f"""
Ticket Details for {ticket_key}:
------------------------
Summary: {issue.fields.summary}
Status: {issue.fields.status.name}
Priority: {issue.fields.priority.name if issue.fields.priority else 'Not set'}
Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}
Reporter: {issue.fields.reporter.displayName}
Created: {issue.fields.created}
Updated: {issue.fields.updated}
Description: {issue.fields.description if issue.fields.description else 'No description provided'}
"""
        logger.debug("Successfully fetched ticket details")
        return details
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_dashboard_tickets(dashboard_id: str = "278989") -> str:
    """Get tickets from a specific dashboard.
    Args:
        dashboard_id: The dashboard ID (default: 278989)
    """
    try:
        logger.debug(f"Fetching tickets from dashboard {dashboard_id}")
        # Get dashboard data
        dashboard = jira.dashboard(dashboard_id)
        ticket_text = f"Tickets from Dashboard {dashboard_id}:\n\n"
        
        # Get gadgets and their data
        for gadget in dashboard.gadgets:
            if hasattr(gadget, 'content'):
                ticket_text += f"Gadget: {gadget.title}\n"
                # Add gadget-specific ticket information
                if hasattr(gadget.content, 'issues'):
                    for issue in gadget.content.issues:
                        ticket_text += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
                ticket_text += "\n"
        
        logger.debug("Successfully fetched dashboard tickets")
        return ticket_text
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def search_tickets(query: str) -> str:
    """Search for tickets using JQL.
    Args:
        query: The search query (e.g., 'project = NCSFM AND summary ~ "bug"')
    """
    try:
        logger.debug(f"Searching tickets with query: {query}")
        issues = jira.search_issues(query)
        if not issues:
            return f"No tickets found matching query: {query}"
        
        ticket_text = f"Search Results for '{query}':\n\n"
        for issue in issues:
            ticket_text += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
        
        logger.debug(f"Found {len(issues)} matching tickets")
        return ticket_text
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_recent_project_tickets(project_code: str, hours: int = 24) -> str:
    """Get tickets from a specific project created within the specified time period.
    Args:
        project_code: The project code (e.g., NCSFM)
        hours: The number of hours to look back (default: 24)
    """
    try:
        logger.debug(f"Fetching tickets for project {project_code} in the last {hours} hours")
        
        # Calculate the date X hours ago
        time_ago = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M')
        
        # Get all project tickets created in the specified time period
        jql = f'project = {project_code} AND created >= "{time_ago}" ORDER BY created DESC'
        issues = jira.search_issues(jql)
        
        if not issues:
            return f"No {project_code} tickets were opened in the last {hours} hours."
        
        ticket_text = f"{project_code} tickets opened since {time_ago}:\n\n"
        for issue in issues:
            created_date = issue.fields.created[:19].replace('T', ' ')  # Format the date
            ticket_text += f"- {issue.key}: {issue.fields.summary}\n"
            ticket_text += f"  Status: {issue.fields.status.name}\n"
            ticket_text += f"  Created: {created_date}\n"
            ticket_text += f"  Reporter: {issue.fields.reporter.displayName}\n"
            ticket_text += f"  URL: https://{os.getenv('JIRA_HOST')}/browse/{issue.key}\n\n"
        
        logger.debug(f"Found {len(issues)} recent tickets for project {project_code}")
        return ticket_text
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_all_recent_tickets(hours: int = 24, max_results: int = 50) -> str:
    """Get all tickets created within the specified time period across all projects.
    Args:
        hours: The number of hours to look back (default: 24)
        max_results: Maximum number of results to return (default: 50)
    """
    try:
        logger.debug(f"Fetching all tickets created in the last {hours} hours")
        
        # Calculate the date X hours ago
        time_ago = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M')
        
        # Get all tickets created in the specified time period
        jql = f'created >= "{time_ago}" ORDER BY created DESC'
        issues = jira.search_issues(jql, maxResults=max_results)
        
        if not issues:
            return f"No tickets were opened in the last {hours} hours."
        
        ticket_text = f"All tickets opened since {time_ago} (showing up to {max_results}):\n\n"
        for issue in issues:
            created_date = issue.fields.created[:19].replace('T', ' ')  # Format the date
            ticket_text += f"- {issue.key}: {issue.fields.summary}\n"
            ticket_text += f"  Status: {issue.fields.status.name}\n"
            ticket_text += f"  Created: {created_date}\n"
            ticket_text += f"  Reporter: {issue.fields.reporter.displayName}\n"
            ticket_text += f"  URL: https://{os.getenv('JIRA_HOST')}/browse/{issue.key}\n\n"
        
        logger.debug(f"Found {len(issues)} recent tickets")
        return ticket_text
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    # Determine the transport method
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        # Run as HTTP server
        port = int(os.getenv("PORT", "3000"))
        logger.info(f"Starting Jira MCP server with HTTP transport on port {port}...")
        mcp.run(transport='http', port=port)
    else:
        # Run with stdio transport (default)
        logger.info("Starting Jira MCP server with stdio transport...")
        mcp.run(transport='stdio') 