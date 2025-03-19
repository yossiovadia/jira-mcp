#!/usr/bin/env python3
"""
Manual test script for Jira PAT authentication
"""
import os
import logging
from dotenv import load_dotenv
from jira import JIRA

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jira-pat-test")

def test_jira_pat():
    """Test Jira PAT authentication"""
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    jira_host = os.getenv('JIRA_HOST')
    jira_pat = os.getenv('JIRA_PAT')
    
    logger.info(f"Testing connection to Jira host: {jira_host}")
    
    try:
        # Connect to Jira using PAT
        jira = JIRA(
            server=f"https://{jira_host}",
            token_auth=jira_pat
        )
        
        # Get authenticated user info
        user = jira.myself()
        logger.info(f"Authentication successful! Logged in as: {user.get('displayName')} ({user.get('name')})")
        
        # Test getting assigned tickets
        logger.info("Testing JQL query for assigned tickets...")
        jql = f'assignee = "{user["name"]}"'
        issues = jira.search_issues(jql, maxResults=5)
        
        if issues:
            logger.info(f"Found {len(issues)} tickets assigned to you:")
            for issue in issues:
                logger.info(f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})")
        else:
            logger.info("No tickets assigned to you")
            
        assert True  # Authentication was successful
        
    except Exception as e:
        logger.error(f"Error testing PAT authentication: {str(e)}")
        assert False, f"PAT authentication failed: {str(e)}"

if __name__ == "__main__":
    success = test_jira_pat()
    print(f"\nPAT Authentication Test {'Successful' if success else 'Failed'}") 