"""
Tools for retrieving and analyzing Jira ticket details
"""
from ..utils.logging import logger
from ..jira_client.client import get_jira_client
from ..ollama_client import ask_ollama

def get_ticket_details(ticket_key: str) -> str:
    """Get detailed information about a specific ticket.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: get_ticket_details for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get the issue details
        issue = jira_client.issue(ticket_key)
        
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
            comments = jira_client.comments(issue)
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

def summarize_ticket(ticket_key: str) -> str:
    """Summarize a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: summarize_ticket for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get the ticket details
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
            return f"Could not generate summary using Ollama. Using built-in summary instead:\n\nTicket {ticket_key} concerns: '{jira_client.issue(ticket_key).fields.summary}'"
    except Exception as e:
        logger.error(f"Error summarizing ticket: {str(e)}")
        return f"Error summarizing ticket: {str(e)}"

def analyze_ticket(ticket_key: str, question: str) -> str:
    """Analyze a Jira ticket by asking a specific question about it.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: A specific question about the ticket
    """
    logger.info(f"Tool called: analyze_ticket for {ticket_key} with question: {question}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get the ticket details
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
                ticket = jira_client.issue(ticket_key)
                return f"Ollama analysis failed. Basic information about {ticket_key}:\n\nSummary: {ticket.fields.summary}\nStatus: {ticket.fields.status.name}\nAssignee: {ticket.fields.assignee.displayName if hasattr(ticket.fields, 'assignee') and ticket.fields.assignee else 'Unassigned'}"
            except:
                return f"Ollama analysis failed and could not retrieve basic ticket information. Please check the ticket manually."
    except Exception as e:
        logger.error(f"Error analyzing ticket: {str(e)}")
        return f"Error analyzing ticket: {str(e)}" 