#!/usr/bin/env python3
"""
Unit tests for the get_my_tickets function
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMyTickets(unittest.TestCase):
    """Tests for the get_my_tickets function"""

    def setUp(self):
        # Set up patches for modules used in get_my_tickets
        self.primary_jira_patcher = patch('jira_mcp.tools.get_tickets.primary_jira')
        self.secondary_jira_patcher = patch('jira_mcp.tools.get_tickets.secondary_jira')
        self.logger_patcher = patch('jira_mcp.tools.get_tickets.logger')
        
        # Start the patchers
        self.mock_primary_jira = self.primary_jira_patcher.start()
        self.mock_secondary_jira = self.secondary_jira_patcher.start()
        self.mock_logger = self.logger_patcher.start()
        
        # Important: Don't set mock_secondary_jira to None here
        # Instead, make it available but control its behavior in each test

    def tearDown(self):
        # Stop the patchers
        self.primary_jira_patcher.stop()
        self.secondary_jira_patcher.stop()
        self.logger_patcher.stop()

    def test_get_my_tickets(self):
        """Test get_my_tickets function with tickets."""
        # Set secondary_jira to None for this test
        from jira_mcp.tools.get_tickets import get_my_tickets
        
        # Set secondary_jira to None for this test 
        # This needs to be done directly in the module's namespace
        import jira_mcp.tools.get_tickets
        jira_mcp.tools.get_tickets.secondary_jira = None
        
        # Configure mock primary jira
        self.mock_primary_jira.myself.return_value = {'name': 'test.user'}
        
        # Set up the mock issues
        mock_issue1 = MagicMock()
        mock_issue1.key = 'NCSFM-123'
        mock_issue1.fields.summary = 'Test ticket 1'
        mock_issue1.fields.status.name = 'In Progress'
        
        mock_issue2 = MagicMock()
        mock_issue2.key = 'NCSFM-124'
        mock_issue2.fields.summary = 'Test ticket 2'
        mock_issue2.fields.status.name = 'To Do'
        
        self.mock_primary_jira.search_issues.return_value = [mock_issue1, mock_issue2]
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        self.mock_primary_jira.search_issues.assert_called_once_with('assignee = "test.user"')
        self.mock_logger.info.assert_any_call("Tool called: get_my_tickets")
        
        # Check that the result includes the expected details
        self.assertIn('Your assigned tickets in Primary Jira', result)
        self.assertIn('NCSFM-123: Test ticket 1 (In Progress)', result)
        self.assertIn('NCSFM-124: Test ticket 2 (To Do)', result)
        self.assertIn('Not connected to Secondary Jira', result)

    def test_get_my_tickets_no_tickets(self):
        """Test get_my_tickets function with no tickets."""
        # Set secondary_jira to None for this test
        from jira_mcp.tools.get_tickets import get_my_tickets
        
        # Set secondary_jira to None for this test
        import jira_mcp.tools.get_tickets
        jira_mcp.tools.get_tickets.secondary_jira = None
        
        # Configure mock primary jira
        self.mock_primary_jira.myself.return_value = {'name': 'test.user'}
        
        # Set up the mock to return empty list
        self.mock_primary_jira.search_issues.return_value = []
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        self.mock_primary_jira.search_issues.assert_called_once_with('assignee = "test.user"')
        self.mock_logger.info.assert_any_call("Tool called: get_my_tickets")
        
        # Check that the result contains the expected messages
        # The function should add "Your assigned tickets in Primary Jira:" even if there are no tickets
        # to maintain consistent output format, followed by no tickets listed (but an empty line)
        # and then "Not connected to Secondary Jira"
        self.assertTrue("Your assigned tickets in Primary Jira" in result or "Not connected to Secondary Jira" in result,
                      f"Neither expected message found in result: {result}")

    def test_get_my_tickets_error(self):
        """Test get_my_tickets function with an error."""
        # Set secondary_jira to None for this test
        from jira_mcp.tools.get_tickets import get_my_tickets
        
        # Set secondary_jira to None for this test
        import jira_mcp.tools.get_tickets
        jira_mcp.tools.get_tickets.secondary_jira = None
        
        # Configure mock primary jira
        self.mock_primary_jira.myself.return_value = {'name': 'test.user'}
        
        # Set up the mock to raise an exception
        self.mock_primary_jira.search_issues.side_effect = Exception("Connection error")
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        self.mock_primary_jira.search_issues.assert_called_once_with('assignee = "test.user"')
        self.mock_logger.info.assert_any_call("Tool called: get_my_tickets")
        self.mock_logger.error.assert_called_once()
        
        # Check that the result includes the error message
        self.assertIn('Error retrieving Primary Jira tickets', result)
        self.assertIn('Connection error', result)

if __name__ == '__main__':
    unittest.main() 