#!/usr/bin/env python3
"""
Test file for JIRA authentication using Personal Access Token
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestJiraAuth(unittest.TestCase):
    """Tests for JIRA authentication"""

    def setUp(self):
        """Setup for each test"""
        # Clear cached imports
        if 'simple_jira_tools' in sys.modules:
            del sys.modules['simple_jira_tools']

    @patch('jira.JIRA')
    @patch('logging.getLogger')
    @patch('os.getenv')
    def test_pat_auth(self, mock_getenv, mock_get_logger, mock_jira_class):
        """Test that PAT authentication is used when available"""
        # Setup environment mocks
        def getenv_side_effect(key):
            env_vars = {
                'JIRA_HOST': 'test.jira.com',
                'JIRA_PAT': 'test-pat-token',
                'JIRA_USERNAME': 'test-user',
                'JIRA_PASSWORD': 'test-password'
            }
            return env_vars.get(key)
            
        mock_getenv.side_effect = getenv_side_effect
        
        # Setup logger mock
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup JIRA mock
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        
        # Import the module - this should trigger the JIRA initialization code
        import simple_jira_tools
        
        # Verify PAT authentication was used
        mock_jira_class.assert_called_once_with(
            server='https://test.jira.com',
            token_auth='test-pat-token'
        )
        mock_logger.info.assert_any_call("Using PAT authentication")
        
    @patch('jira.JIRA')
    @patch('logging.getLogger')
    @patch('os.getenv')
    def test_basic_auth_fallback(self, mock_getenv, mock_get_logger, mock_jira_class):
        """Test that basic authentication is used as fallback when PAT is not available"""
        # Setup environment mocks - no PAT this time
        def getenv_side_effect(key):
            env_vars = {
                'JIRA_HOST': 'test.jira.com',
                'JIRA_PAT': None,  # No PAT available
                'JIRA_USERNAME': 'test-user',
                'JIRA_PASSWORD': 'test-password'
            }
            return env_vars.get(key)
            
        mock_getenv.side_effect = getenv_side_effect
        
        # Setup logger mock
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup JIRA mock
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        
        # Import the module - this should trigger the JIRA initialization code
        import simple_jira_tools
        
        # Verify basic authentication was used
        mock_jira_class.assert_called_once_with(
            server='https://test.jira.com',
            basic_auth=('test-user', 'test-password')
        )
        mock_logger.info.assert_any_call("Using basic authentication")

    def test_env_pat_exists(self):
        """Test that PAT exists in the .env file"""
        from dotenv import load_dotenv
        import os
        
        # Load environment variables
        load_dotenv()
        
        # Get PAT from .env file
        jira_pat = os.getenv('JIRA_PAT')
        
        # Verify PAT is available
        self.assertIsNotNone(jira_pat, "PAT is missing from .env file")
        self.assertTrue(len(jira_pat) > 0, "PAT is empty in .env file")

if __name__ == '__main__':
    unittest.main() 