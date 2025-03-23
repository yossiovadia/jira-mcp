#!/usr/bin/env python3
"""
Unit tests for the ollama-related functions
"""
import sys
import os
import unittest
import logging
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules and functions being tested
from jira_mcp.ollama_client import ask_ollama, is_ollama_available
from jira_mcp.tools.ticket_details import get_ticket_details, summarize_ticket, analyze_ticket

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestDirectOllamaFunctions(unittest.TestCase):
    """Tests for the direct Ollama client functions"""
    
    def test_ask_ollama(self):
        """Test the ask_ollama function works with direct patching"""
        with patch('jira_mcp.ollama_client.client.httpx.post') as mock_post:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Test response"}
            mock_post.return_value = mock_response
            
            # Import after patching
            from jira_mcp.ollama_client import ask_ollama
            
            # Call the function
            result = ask_ollama("Test prompt")
            
            # Verify the result
            self.assertEqual(result, "Test response")
            
            # Verify httpx.post was called with the right URL
            mock_post.assert_called_once()
            self.assertIn('/api/generate', mock_post.call_args[0][0])
            
            # Verify the request data
            request_data = mock_post.call_args[1]['json']
            self.assertEqual(request_data['prompt'], "Test prompt")
    
    def test_ask_ollama_error(self):
        """Test error handling in ask_ollama"""
        with patch('jira_mcp.ollama_client.client.httpx.post') as mock_post:
            # Make the request fail
            mock_post.side_effect = Exception("Connection failed")
            
            # Make sure the cache is empty for this test
            with patch('jira_mcp.ollama_client.client.ollama_cache', {}):
                # Import after patching
                from jira_mcp.ollama_client import ask_ollama
                
                # Call the function - this should invoke our mocked httpx.post
                result = ask_ollama("Test prompt")
                
                # Verify the error is included in the result
                self.assertIn("Error calling Ollama", result)
                self.assertIn("Connection failed", result)

class TestTicketDetailsFunctions(unittest.TestCase):
    """Tests for the ticket details functions that use Ollama"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Patch the imported modules and functions
        self.get_ticket_details_patcher = patch('jira_mcp.tools.ticket_details.get_ticket_details')
        self.ask_ollama_patcher = patch('jira_mcp.tools.ticket_details.ask_ollama')
        self.get_jira_client_patcher = patch('jira_mcp.tools.ticket_details.get_jira_client')
        self.logger_patcher = patch('jira_mcp.tools.ticket_details.logger')
        
        # Start the patchers
        self.mock_get_ticket_details = self.get_ticket_details_patcher.start()
        self.mock_ask_ollama = self.ask_ollama_patcher.start()
        self.mock_get_jira_client = self.get_jira_client_patcher.start()
        self.mock_logger = self.logger_patcher.start()
        
        # Set up common return values
        self.mock_get_ticket_details.return_value = "Detailed info for TEST-123"
        self.mock_ask_ollama.return_value = "Ollama generated response"
        
        # Mock Jira client
        self.mock_jira = MagicMock()
        self.mock_issue = MagicMock()
        self.mock_issue.fields.summary = "Test ticket summary"
        self.mock_issue.fields.status.name = "In Progress"
        self.mock_jira.issue.return_value = self.mock_issue
        self.mock_get_jira_client.return_value = self.mock_jira
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.get_ticket_details_patcher.stop()
        self.ask_ollama_patcher.stop()
        self.get_jira_client_patcher.stop()
        self.logger_patcher.stop()
    
    def test_summarize_ticket(self):
        """Test the summarize_ticket function"""
        # Import the function here to use our mocks
        from jira_mcp.tools.ticket_details import summarize_ticket
        
        # Call the function
        result = summarize_ticket("TEST-123")
        
        # Verify the mocks were called correctly
        self.mock_get_ticket_details.assert_called_once_with("TEST-123")
        self.mock_ask_ollama.assert_called_once()
        
        # Check the result
        self.assertIn("Summary of TEST-123", result)
        self.assertIn("Ollama generated response", result)
    
    def test_analyze_ticket(self):
        """Test the analyze_ticket function"""
        # Import the function here to use our mocks
        from jira_mcp.tools.ticket_details import analyze_ticket
        
        # Call the function
        result = analyze_ticket("TEST-123", "What is the priority?")
        
        # Verify the mocks were called correctly
        self.mock_get_ticket_details.assert_called_once_with("TEST-123")
        self.mock_ask_ollama.assert_called_once()
        
        # Check the prompt contains the question
        prompt_arg = self.mock_ask_ollama.call_args[0][0]
        self.assertIn("What is the priority?", prompt_arg)
        
        # Check the result
        self.assertIn("Analysis of TEST-123", result)
        self.assertIn("Ollama generated response", result)

if __name__ == '__main__':
    unittest.main() 