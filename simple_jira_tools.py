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
    
    # Set up a more detailed result for debugging
    debug_info = []
    
    try:
        # Get the basic issue details
        issue = jira.issue(ticket_key)
        logger.info(f"Successfully retrieved basic issue details for {ticket_key}")
        debug_info.append(f"Successfully retrieved basic issue details for {ticket_key}")
        
        # Format the basic ticket information
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
        
        # Method 1: Try direct REST API call for comments
        try:
            logger.info(f"Attempting direct API call for comments on {ticket_key}")
            debug_info.append(f"Attempting direct API call for comments on {ticket_key}")
            
            # Make a direct API call to get comments
            comments_url = f"/rest/api/2/issue/{ticket_key}/comment"
            comments_data = jira._get_json(comments_url)
            
            total_from_api = comments_data.get('total', 0)
            comments_list = comments_data.get('comments', [])
            total_in_list = len(comments_list)
            
            logger.info(f"Direct API call: 'total' field reports {total_from_api} comments")
            logger.info(f"Direct API call: found {total_in_list} comments in the list")
            debug_info.append(f"Direct API call: 'total' field reports {total_from_api} comments")
            debug_info.append(f"Direct API call: found {total_in_list} comments in the list")
            
            if total_in_list > 0:
                details += f"\nComments ({total_in_list}):\n"
                for i, comment in enumerate(comments_list):
                    comment_id = comment.get('id', 'unknown')
                    author_obj = comment.get('author', {})
                    author = author_obj.get('displayName', author_obj.get('name', 'Unknown'))
                    created = comment.get('created', 'Unknown date')
                    body = comment.get('body', 'No content')
                    
                    # Add only first 3 comments in detail view
                    if i < 3:
                        details += f"\n--- Comment #{i+1} (ID: {comment_id}) by {author} on {created} ---\n{body}\n"
                    
                # Add note if we're truncating
                if total_in_list > 3:
                    details += f"\n[...{total_in_list - 3} more comments not shown...]\n"
            else:
                details += "\nNo comments on this ticket (via direct API)."
                debug_info.append("No comments found in direct API response.")
        except Exception as api_error:
            logger.error(f"Error in direct API call for comments: {str(api_error)}")
            debug_info.append(f"Error in direct API call for comments: {str(api_error)}")
            details += f"\nError retrieving comments via direct API: {str(api_error)}"
        
        # Add debug information to the output
        if debug_info:
            details += "\n\nDEBUG INFO (will be removed in production):\n"
            for info in debug_info:
                details += f"- {info}\n"
                
            # Include raw API response structure
            try:
                comments_url = f"/rest/api/2/issue/{ticket_key}/comment"
                comments_data = jira._get_json(comments_url)
                details += f"\nAPI Response Keys: {', '.join(comments_data.keys())}\n"
                details += f"Total Comments (API): {comments_data.get('total', 'N/A')}\n"
            except Exception as e:
                details += f"\nError getting API details: {str(e)}\n"
        
        return details
    except Exception as e:
        logger.error(f"Error retrieving ticket details: {str(e)}")
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