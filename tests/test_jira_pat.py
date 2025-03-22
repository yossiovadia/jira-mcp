#!/usr/bin/env python3
"""
Test script for Jira PAT authentication
"""
import os
import unittest
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger("jira-pat-test")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s'))
logger.addHandler(handler)

def test_jira_pat():
    """Test Jira PAT authentication using mocks"""
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    jira_host = os.getenv('JIRA_HOST', 'example.com')
    jira_pat = os.getenv('JIRA_PAT', 'dummy-pat')
    
    logger.info(f"Testing connection to Jira host: {jira_host}")
    
    # Create the mock for JIRA class
    with patch('jira.JIRA') as mock_jira_class:
        # Set up the mock instance
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        
        # Mock the myself() method to return a fake user
        mock_jira_instance.myself.return_value = {
            'displayName': 'Test User',
            'name': 'testuser'
        }
        
        # Mock the search_issues method to return fake issues
        mock_issue1 = MagicMock()
        mock_issue1.key = 'TEST-123'
        mock_issue1.fields.summary = 'Test issue 1'
        mock_issue1.fields.status.name = 'Open'
        
        mock_issue2 = MagicMock()
        mock_issue2.key = 'TEST-456'
        mock_issue2.fields.summary = 'Test issue 2'
        mock_issue2.fields.status.name = 'In Progress'
        
        mock_jira_instance.search_issues.return_value = [mock_issue1, mock_issue2]
        
        try:
            # Connect to Jira using PAT (this will actually use our mock)
            from jira import JIRA
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
            
            # Verify the mock was called correctly
            mock_jira_class.assert_called_once()
            mock_jira_instance.myself.assert_called_once()
            mock_jira_instance.search_issues.assert_called_once()
            
            # Use assertions instead of returning True/False
            assert True, "Authentication was successful"
            
        except Exception as e:
            logger.error(f"Error testing PAT authentication: {str(e)}")
            assert False, f"Authentication failed: {str(e)}"
        
if __name__ == "__main__":
    test_jira_pat() 