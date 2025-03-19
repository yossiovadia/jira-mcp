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

    @patch('simple_jira_tools.jira.search_issues')
    @patch('simple_jira_tools.jira.myself')
    @patch('simple_jira_tools.logger')
    def test_get_my_tickets(self, mock_logger, mock_myself, mock_search_issues):
        """Test get_my_tickets function with tickets."""
        from simple_jira_tools import get_my_tickets
        
        # Mock the JIRA myself() response
        mock_myself.return_value = {'name': 'test.user'}
        
        # Set up the mock issues
        mock_issue1 = MagicMock()
        mock_issue1.key = 'NCSFM-123'
        mock_issue1.fields.summary = 'Test ticket 1'
        mock_issue1.fields.status.name = 'In Progress'
        
        mock_issue2 = MagicMock()
        mock_issue2.key = 'NCSFM-124'
        mock_issue2.fields.summary = 'Test ticket 2'
        mock_issue2.fields.status.name = 'To Do'
        
        mock_search_issues.return_value = [mock_issue1, mock_issue2]
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        mock_search_issues.assert_called_once_with('assignee = "test.user"')
        mock_logger.info.assert_called_with("Tool called: get_my_tickets")
        
        # Check that the result includes the expected details
        self.assertIn('Your assigned tickets', result)
        self.assertIn('NCSFM-123: Test ticket 1 (In Progress)', result)
        self.assertIn('NCSFM-124: Test ticket 2 (To Do)', result)

    @patch('simple_jira_tools.jira.search_issues')
    @patch('simple_jira_tools.jira.myself')
    @patch('simple_jira_tools.logger')
    def test_get_my_tickets_no_tickets(self, mock_logger, mock_myself, mock_search_issues):
        """Test get_my_tickets function with no tickets."""
        from simple_jira_tools import get_my_tickets
        
        # Mock the JIRA myself() response
        mock_myself.return_value = {'name': 'test.user'}
        
        # Set up the mock to return empty list
        mock_search_issues.return_value = []
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        mock_search_issues.assert_called_once_with('assignee = "test.user"')
        mock_logger.info.assert_called_with("Tool called: get_my_tickets")
        
        # Check that the result includes the expected message
        self.assertEqual("You don't have any assigned tickets", result)

    @patch('simple_jira_tools.jira.search_issues')
    @patch('simple_jira_tools.jira.myself')
    @patch('simple_jira_tools.logger')
    def test_get_my_tickets_error(self, mock_logger, mock_myself, mock_search_issues):
        """Test get_my_tickets function with an error."""
        from simple_jira_tools import get_my_tickets
        
        # Mock the JIRA myself() response
        mock_myself.return_value = {'name': 'test.user'}
        
        # Set up the mock to raise an exception
        mock_search_issues.side_effect = Exception("Connection error")
        
        # Call the function
        result = get_my_tickets()
        
        # Verify the mocks were called correctly
        mock_search_issues.assert_called_once_with('assignee = "test.user"')
        mock_logger.info.assert_called_with("Tool called: get_my_tickets")
        mock_logger.error.assert_called_once()
        
        # Check that the result includes the error message
        self.assertIn('Error retrieving tickets', result)
        self.assertIn('Connection error', result)

if __name__ == '__main__':
    unittest.main() 