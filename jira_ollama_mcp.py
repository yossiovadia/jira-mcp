#!/usr/bin/env python3
"""
Jira MCP Server that uses local Ollama instead of Claude
"""
import os
import logging
import json
import httpx
from dotenv import load_dotenv
from jira import JIRA
from mcp.server.fastmcp import FastMCP

# Configure logging exactly like the working script
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='jira_ollama_mcp.log',
    filemode='w'
)
logger = logging.getLogger("jira-ollama")

# Load environment variables from the Ollama .env file
load_dotenv(".env.ollama")

# Create server with the same name that worked in the ultra minimal version
mcp = FastMCP("jira")

# Connect to Jira using PAT if available, otherwise use basic auth
jira_host = os.getenv('JIRA_HOST')
jira_pat = os.getenv('JIRA_PAT')
jira_username = os.getenv('JIRA_USERNAME')
jira_password = os.getenv('JIRA_PASSWORD')

# Ollama configuration
ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11435')
ollama_model = os.getenv('OLLAMA_MODEL', 'deepseek-r1:14b-qwen-distill-q8_0')
logger.info(f"Will use Ollama at {ollama_base_url} with model {ollama_model}")

# Initialize Jira client
jira = None
try:
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
except Exception as e:
    logger.error(f"Error connecting to Jira: {str(e)}")
    # Don't exit, allow the server to run even without Jira connection

# Function to call Ollama
def ask_ollama(prompt, system_message=None):
    """Send a prompt to Ollama and get a response."""
    try:
        # Create the request data
        data = {
            "model": ollama_model,
            "prompt": prompt,
            "system": system_message if system_message else "",
            "stream": False,  # We want a complete response, not streaming
            "raw": False      # We want a processed response, not raw output
        }
        
        logger.info(f"Sending prompt to Ollama: {prompt[:100]}...")
        
        # Make synchronous request to Ollama
        response = httpx.post(
            f"{ollama_base_url}/api/generate",
            json=data,
            timeout=60.0
        )
        
        # Log the raw response for debugging
        logger.debug(f"Raw Ollama response: {response.text[:500]}...")
        
        if response.status_code == 200:
            try:
                # Try to parse the response as JSON
                result = response.json()
                logger.info("Received response from Ollama")
                
                # Check for different response formats
                if isinstance(result, dict):
                    # The /api/generate endpoint returns a response field
                    if "response" in result:
                        return result["response"]
                    # Fallback to message format if using /api/chat
                    elif "message" in result and isinstance(result["message"], dict):
                        return result["message"].get("content", "No content in response")
                    else:
                        # Return the first string value we find
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 10:
                                return value
                
                # If we're here, we didn't find a good response format, log the full structure
                logger.warning(f"Unexpected Ollama response structure: {result}")
                return str(result)
            except json.JSONDecodeError as je:
                logger.error(f"JSON parsing error: {str(je)}")
                # Try to salvage a response from the text
                raw_text = response.text
                
                # Look for a meaningful text in the response
                if len(raw_text) > 10:
                    # Try to extract just text content if there's JSON-like structure
                    if '"content":' in raw_text:
                        try:
                            start_idx = raw_text.find('"content":') + 11
                            end_idx = raw_text.find('",', start_idx)
                            if end_idx > start_idx:
                                return raw_text[start_idx:end_idx]
                        except:
                            pass
                    
                    # Return the raw text if it's not too long
                    if len(raw_text) < 5000:
                        return f"Raw response (JSON parsing failed): {raw_text}"
                
                return f"Error parsing Ollama response: {str(je)}"
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return f"Error from Ollama API: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        return f"Error calling Ollama: {str(e)}"

@mcp.tool()
def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    logger.info("Tool called: get_my_tickets")
    
    if not jira:
        return "Error: Not connected to Jira"
        
    try:
        # Use the authenticated user's username for the query
        current_user = jira.myself()['name']
        jql = f'assignee = "{current_user}"'
        issues = jira.search_issues(jql)
        
        if not issues:
            return "You don't have any assigned tickets"
        
        tickets_info = "Your assigned tickets:\n\n"
        for issue in issues:
            tickets_info += f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
        
        return tickets_info
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error retrieving tickets: {str(e)}"

@mcp.tool()
def get_ticket_details(ticket_key: str) -> str:
    """Get detailed information about a specific ticket.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: get_ticket_details for {ticket_key}")
    
    if not jira:
        return "Error: Not connected to Jira"
    
    try:
        # Get the issue details
        issue = jira.issue(ticket_key)
        
        # Basic information
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
        
        # Get comments (simplified approach)
        try:
            comments = jira.comments(issue)
            if comments:
                details += f"\nComments ({len(comments)}):\n"
                # Show only first 3 comments to keep response size manageable
                for i, comment in enumerate(comments[:3]):
                    details += f"\n--- Comment by {comment.author.displayName} on {comment.created} ---\n{comment.body}\n"
                
                # Add note if we're truncating
                if len(comments) > 3:
                    details += f"\n[...{len(comments) - 3} more comments not shown...]\n"
            else:
                details += "\nNo comments on this ticket."
        except Exception as comment_error:
            logger.error(f"Error retrieving comments: {str(comment_error)}")
            details += f"\nError retrieving comments: {str(comment_error)}"
        
        return details
    except Exception as e:
        logger.error(f"Error retrieving ticket details: {str(e)}")
        return f"Error retrieving ticket details: {str(e)}"

@mcp.tool()
def summarize_ticket(ticket_key: str) -> str:
    """Summarize a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: summarize_ticket for {ticket_key}")
    
    if not jira:
        return "Error: Not connected to Jira"
    
    try:
        # First get the ticket details
        ticket_details = get_ticket_details(ticket_key)
        if ticket_details.startswith("Error"):
            return f"Cannot summarize ticket: {ticket_details}"
        
        # Then ask Ollama to summarize it
        logger.info(f"Sending {ticket_key} to Ollama for summarization")
        prompt = f"Please summarize this Jira ticket in a concise way, focusing on the main issue and solution if available:\n\n{ticket_details}"
        system_message = "You are a helpful assistant specialized in summarizing Jira tickets. Keep your response concise and focus on the most important information."
        
        summary = ask_ollama(prompt, system_message)
        if summary and not summary.startswith("Error"):
            return f"Summary of {ticket_key}:\n\n{summary}"
        else:
            logger.error(f"Failed to get summary from Ollama: {summary}")
            return f"Could not generate summary using Ollama. Using built-in summary instead:\n\nTicket {ticket_key} concerns: '{jira.issue(ticket_key).fields.summary}'"
    except Exception as e:
        logger.error(f"Error summarizing ticket: {str(e)}")
        return f"Error summarizing ticket: {str(e)}"

@mcp.tool()
def analyze_ticket(ticket_key: str, question: str) -> str:
    """Analyze a Jira ticket by asking a specific question about it.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: A specific question about the ticket
    """
    logger.info(f"Tool called: analyze_ticket for {ticket_key} with question: {question}")
    
    if not jira:
        return "Error: Not connected to Jira"
    
    try:
        # First get the ticket details
        ticket_details = get_ticket_details(ticket_key)
        if ticket_details.startswith("Error"):
            return f"Cannot analyze ticket: {ticket_details}"
        
        # Then ask Ollama to analyze it
        logger.info(f"Sending {ticket_key} to Ollama for analysis of question: {question}")
        prompt = f"Please answer the following question about this Jira ticket:\n\nQuestion: {question}\n\nTicket details:\n{ticket_details}"
        system_message = "You are a helpful assistant specialized in analyzing Jira tickets. Provide specific, accurate answers based only on the information in the ticket."
        
        analysis = ask_ollama(prompt, system_message)
        if analysis and not analysis.startswith("Error"):
            return f"Analysis of {ticket_key} regarding '{question}':\n\n{analysis}"
        else:
            logger.error(f"Failed to get analysis from Ollama: {analysis}")
            # Provide a basic response without Ollama
            try:
                ticket = jira.issue(ticket_key)
                return f"Ollama analysis failed. Basic information about {ticket_key}:\n\nSummary: {ticket.fields.summary}\nStatus: {ticket.fields.status.name}\nAssignee: {ticket.fields.assignee.displayName if hasattr(ticket.fields, 'assignee') and ticket.fields.assignee else 'Unassigned'}"
            except:
                return f"Ollama analysis failed and could not retrieve basic ticket information. Please check the ticket manually."
    except Exception as e:
        logger.error(f"Error analyzing ticket: {str(e)}")
        return f"Error analyzing ticket: {str(e)}"

def main():
    """
    Main entry point for the Jira Ollama MCP server.
    """
    logger.info("Starting Jira Ollama MCP server...")
    
    try:
        # Run the server
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main() 