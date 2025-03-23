#!/usr/bin/env python3
"""
Unit tests for the Jira authentication functionality
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestJiraAuth(unittest.TestCase):
    """Tests for Jira authentication"""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any cached module imports
        if 'jira_mcp.jira_client.client' in sys.modules:
            del sys.modules['jira_mcp.jira_client.client']
        
        # Create patchers
        self.jira_class_patcher = patch('jira.JIRA')
        self.logger_patcher = patch('jira_mcp.jira_client.client.logger')
        self.config_patcher = patch('jira_mcp.jira_client.client.config')
        
        # Start patchers
        self.mock_jira_class = self.jira_class_patcher.start()
        self.mock_logger = self.logger_patcher.start()
        self.mock_config = self.config_patcher.start()
        
        # Set up JIRA mock
        self.mock_jira_instance = MagicMock()
        self.mock_jira_class.return_value = self.mock_jira_instance
        self.mock_jira_instance.myself.return_value = {'displayName': 'Test User', 'name': 'test-user'}
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.jira_class_patcher.stop()
        self.logger_patcher.stop()
        self.config_patcher.stop()

    def test_pat_auth(self):
        """Test that PAT authentication is used when available"""
        # Setup config values
        self.mock_config.primary_jira_host = 'test.jira.com'
        self.mock_config.primary_jira_pat = 'test-pat-token'
        self.mock_config.primary_jira_username = 'test-user'
        self.mock_config.primary_jira_password = 'test-password'
        
        # Set up secondary config to make sure it doesn't cause issues
        self.mock_config.secondary_jira_host = None
        self.mock_config.secondary_jira_pat = None
        self.mock_config.secondary_project_prefixes = []
        self.mock_config.redhat_project_prefixes = []
        
        # Import the module - this should trigger the module-level code
        from jira_mcp.jira_client.client import initialize_jira_clients
        
        # Call initialize method
        initialize_jira_clients()

        # Verify the JIRA client was created with PAT auth - use any_call instead of assert_called_with
        self.mock_jira_class.assert_any_call(
            server='https://test.jira.com',
            token_auth='test-pat-token'
        )
        
        # Verify logging
        self.mock_logger.info.assert_any_call("Initializing Primary Jira with PAT authentication")

    def test_basic_auth_fallback(self):
        """Test that basic authentication is used as fallback when PAT is not available"""
        # Setup config values - no PAT this time
        self.mock_config.primary_jira_host = 'test.jira.com'
        self.mock_config.primary_jira_pat = None
        self.mock_config.primary_jira_username = 'test-user'
        self.mock_config.primary_jira_password = 'test-password'
        
        # Set up secondary config to make sure it doesn't cause issues
        self.mock_config.secondary_jira_host = None
        self.mock_config.secondary_jira_pat = None
        self.mock_config.secondary_project_prefixes = []
        self.mock_config.redhat_project_prefixes = []
        
        # Import the module - this should trigger the module-level code
        from jira_mcp.jira_client.client import initialize_jira_clients
        
        # Call initialize method
        initialize_jira_clients()

        # Verify the JIRA client was created with basic auth - use any_call instead of assert_called_with
        self.mock_jira_class.assert_any_call(
            server='https://test.jira.com',
            basic_auth=('test-user', 'test-password')
        )
        
        # Verify logging
        self.mock_logger.info.assert_any_call("Initializing Primary Jira with basic authentication")

    def test_secondary_jira_initialization(self):
        """Test that secondary Jira is initialized when configured"""
        # Setup config values for both primary and secondary Jira
        self.mock_config.primary_jira_host = 'primary.jira.com'
        self.mock_config.primary_jira_pat = 'primary-pat-token'
        
        self.mock_config.secondary_jira_host = 'secondary.jira.com'
        self.mock_config.secondary_jira_pat = 'secondary-pat-token'
        
        # Import the module - this should trigger the module-level code
        from jira_mcp.jira_client.client import initialize_jira_clients
        
        # Call initialize method
        initialize_jira_clients()

        # Verify both JIRA clients were created
        self.assertEqual(self.mock_jira_class.call_count, 2)
        
        # Verify the calls in order they were made
        call_args_list = self.mock_jira_class.call_args_list
        
        # First call should be for primary Jira
        self.assertEqual(call_args_list[0][1]['server'], 'https://primary.jira.com')
        self.assertEqual(call_args_list[0][1]['token_auth'], 'primary-pat-token')
        
        # Second call should be for secondary Jira
        self.assertEqual(call_args_list[1][1]['server'], 'https://secondary.jira.com')
        self.assertEqual(call_args_list[1][1]['token_auth'], 'secondary-pat-token')
        
        # Verify logging
        self.mock_logger.info.assert_any_call("Initializing Primary Jira with PAT authentication")
        self.mock_logger.info.assert_any_call("Initializing Secondary Jira with PAT authentication")

if __name__ == '__main__':
    unittest.main() 