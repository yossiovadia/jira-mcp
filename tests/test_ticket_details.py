#!/usr/bin/env python3
"""
Unit tests for the get_ticket_details function
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestTicketDetails(unittest.TestCase):
    """Tests for the get_ticket_details function"""

    @patch('simple_jira_tools.logger')
    def test_get_ticket_details(self, mock_logger):
        """Test get_ticket_details function with a valid ticket."""
        from simple_jira_tools import get_ticket_details
        
        # Setup mock for jira.issue
        mock_issue_obj = MagicMock()
        mock_issue_obj.key = 'NCSFM-123'
        mock_issue_obj.fields.summary = 'Test ticket'
        mock_issue_obj.fields.status.name = 'In Progress'
        mock_issue_obj.fields.priority.name = 'High'
        mock_issue_obj.fields.assignee.displayName = 'John Doe'
        mock_issue_obj.fields.reporter.displayName = 'Jane Smith'
        mock_issue_obj.fields.created = '2023-05-01T10:00:00.000+0000'
        mock_issue_obj.fields.updated = '2023-05-02T15:30:00.000+0000'
        mock_issue_obj.fields.description = 'This is a test ticket'
        
        # Setup mock for jira object
        mock_jira = MagicMock()
        mock_jira.issue.return_value = mock_issue_obj
        mock_jira._get_json.return_value = {
            'total': 2, 
            'comments': [
                {
                    'id': '1',
                    'author': {'displayName': 'Commenter One'},
                    'created': '2023-05-01T11:00:00.000+0000',
                    'body': 'First comment'
                },
                {
                    'id': '2',
                    'author': {'displayName': 'Commenter Two'},
                    'created': '2023-05-01T12:00:00.000+0000',
                    'body': 'Second comment'
                }
            ]
        }
        
        # Patch the jira object
        with patch('simple_jira_tools.jira', mock_jira):
            # Call the function
            result = get_ticket_details('NCSFM-123')
        
        # Verify the mock was called correctly
        mock_jira.issue.assert_called_once_with('NCSFM-123')
        
        # Verify logger was called - using any order since implementation changed
        mock_logger.info.assert_any_call(f"Tool called: get_ticket_details for NCSFM-123")
        
        # Check that the result includes the expected details
        self.assertIn('Ticket: NCSFM-123', result)
        self.assertIn('Summary: Test ticket', result)
        self.assertIn('Status: In Progress', result)
        self.assertIn('Priority: High', result)
        self.assertIn('Assignee: John Doe', result)
        self.assertIn('Reporter: Jane Smith', result)
        self.assertIn('Created: 2023-05-01T10:00:00.000+0000', result)
        self.assertIn('Updated: 2023-05-02T15:30:00.000+0000', result)
        self.assertIn('This is a test ticket', result)
        self.assertIn('Comments (2)', result)
        self.assertIn('Commenter One', result)
        self.assertIn('Commenter Two', result)

    @patch('simple_jira_tools.logger')
    def test_get_ticket_details_error(self, mock_logger):
        """Test get_ticket_details function with an error."""
        from simple_jira_tools import get_ticket_details
        
        # Setup mock for jira object with error
        mock_jira = MagicMock()
        mock_jira.issue.side_effect = Exception("Ticket not found")
        
        # Patch the jira object
        with patch('simple_jira_tools.jira', mock_jira):
            # Call the function
            result = get_ticket_details('INVALID-123')
        
        # Verify the mock was called correctly
        mock_jira.issue.assert_called_once_with('INVALID-123')
        
        # Verify logger was called
        mock_logger.info.assert_called_with(f"Tool called: get_ticket_details for INVALID-123")
        mock_logger.error.assert_called_once()
        
        # Check that the result includes the error message
        self.assertIn('Error retrieving ticket details', result)
        self.assertIn('Ticket not found', result)

if __name__ == '__main__':
    unittest.main() 