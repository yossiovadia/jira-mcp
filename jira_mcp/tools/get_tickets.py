"""
Tools for retrieving Jira tickets
"""
from ..utils.logging import logger
from ..jira_client.client import primary_jira, secondary_jira

def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    logger.info("Tool called: get_my_tickets")
    
    results = []
    
    # Check Primary Jira
    if primary_jira:
        try:
            # Use the authenticated user's username for the query
            current_user = primary_jira.myself()['name']
            jql = f'assignee = "{current_user}"'
            issues = primary_jira.search_issues(jql)
            
            if issues:
                results.append("Your assigned tickets in Primary Jira:")
                for issue in issues:
                    results.append(f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})")
                results.append("")  # Empty line for separation
        except Exception as e:
            logger.error(f"Error retrieving Primary Jira tickets: {str(e)}")
            results.append(f"Error retrieving Primary Jira tickets: {str(e)}")
    else:
        results.append("Not connected to Primary Jira")
    
    # Check Secondary Jira
    if secondary_jira:
        try:
            # Use the authenticated user's username for the query
            current_user = secondary_jira.myself()['name']
            jql = f'assignee = "{current_user}"'
            issues = secondary_jira.search_issues(jql)
            
            if issues:
                results.append("Your assigned tickets in Secondary Jira:")
                for issue in issues:
                    results.append(f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})")
                results.append("")  # Empty line for separation
        except Exception as e:
            logger.error(f"Error retrieving Secondary Jira tickets: {str(e)}")
            results.append(f"Error retrieving Secondary Jira tickets: {str(e)}")
    else:
        results.append("Not connected to Secondary Jira")
    
    if not results:
        return "Error: Not connected to any Jira instance"
    
    return "\n".join(results) 