#!/usr/bin/env python3
"""
MCP server for Jira integration using the FastMCP class
"""
import os
import logging
from dotenv import load_dotenv
from jira import JIRA
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jira_fastmcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create the MCP server
mcp = FastMCP("jira")
logger.info("Initialized FastMCP server: jira")

# Connect to Jira
try:
    jira = JIRA(
        server=f"https://{os.getenv('JIRA_HOST')}",
        basic_auth=(os.getenv('JIRA_USERNAME'), os.getenv('JIRA_PASSWORD'))
    )
    logger.info(f"Successfully connected to Jira: {os.getenv('JIRA_HOST')}")
except Exception as e:
    logger.error(f"Failed to connect to Jira: {str(e)}")
    raise

@mcp.tool()
async def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    logger.info("Tool called: get_my_tickets")
    try:
        jql = f'assignee = "{os.getenv("JIRA_USERNAME")}"'
        issues = jira.search_issues(jql)
        
        if not issues:
            logger.info("No tickets found")
            return "You don't have any assigned tickets"
        
        ticket_text = "Your assigned tickets:\n\n"
        for issue in issues:
            ticket_text += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
        
        logger.info(f"Found {len(issues)} tickets")
        return ticket_text
    except Exception as e:
        logger.error(f"Error in get_my_tickets: {str(e)}")
        return f"Error retrieving tickets: {str(e)}"

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server with stdio transport")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        raise 