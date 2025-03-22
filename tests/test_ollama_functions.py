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

# Import the jira_ollama_mcp module
import jira_ollama_mcp

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestOllamaFunctions(unittest.TestCase):
    """Tests for the Ollama integration functions"""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Save original functions
        self.original_ask_ollama = jira_ollama_mcp.ask_ollama
        self.original_get_ticket_details = jira_ollama_mcp.get_ticket_details
        
        # Set up patchers
        self.ask_ollama_patcher = patch('jira_ollama_mcp.ask_ollama')
        self.get_ticket_details_patcher = patch('jira_ollama_mcp.get_ticket_details')
        self.get_jira_client_patcher = patch('jira_ollama_mcp.get_jira_client')
        
        # Start patchers
        self.mock_ask_ollama = self.ask_ollama_patcher.start()
        self.mock_get_ticket_details = self.get_ticket_details_patcher.start()
        self.mock_get_jira_client = self.get_jira_client_patcher.start()
        
        # Set up mock returns
        self.mock_ask_ollama.return_value = "Test Ollama response"
        self.mock_get_ticket_details.return_value = "Test ticket details"
        self.mock_jira = MagicMock()
        self.mock_get_jira_client.return_value = self.mock_jira
    
    def tearDown(self):
        """Tear down test fixtures after each test."""
        # Stop all patchers
        self.ask_ollama_patcher.stop()
        self.get_ticket_details_patcher.stop()
        self.get_jira_client_patcher.stop()
        
        # Restore original functions
        jira_ollama_mcp.ask_ollama = self.original_ask_ollama
        jira_ollama_mcp.get_ticket_details = self.original_get_ticket_details
    
    def test_ask_ollama(self):
        """Test the ask_ollama function."""
        # Override the default return value for this test
        self.mock_ask_ollama.return_value = "Specific test response"
        
        # Call the function
        result = jira_ollama_mcp.ask_ollama("Test prompt")
        
        # Verify the mock was called with the right arguments
        self.mock_ask_ollama.assert_called_once_with("Test prompt")
        self.assertEqual(result, "Specific test response")
    
    def test_ask_ollama_error(self):
        """Test error handling in ask_ollama."""
        # Configure the mock to raise an exception
        self.mock_ask_ollama.side_effect = Exception("Test error")
        
        # Create a wrapper to catch exceptions
        def call_with_error_handling():
            try:
                return jira_ollama_mcp.ask_ollama("Test prompt")
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Call the wrapper
        result = call_with_error_handling()
        
        # Verify the result contains the error
        self.assertIn("Error", result)
        self.assertIn("Test error", result)
    
    def test_summarize_ticket(self):
        """Test the summarize_ticket function."""
        # Set up return values
        self.mock_get_ticket_details.return_value = "Details of TEST-123"
        self.mock_ask_ollama.return_value = "This is a summary of TEST-123"
        
        # Call the function
        result = jira_ollama_mcp.summarize_ticket("TEST-123")
        
        # Verify the mocks were called correctly
        self.mock_get_ticket_details.assert_called_once_with("TEST-123")
        self.mock_ask_ollama.assert_called_once()
        
        # Check the result
        self.assertIn("Summary of TEST-123", result)
        self.assertIn("This is a summary of TEST-123", result)
    
    def test_analyze_ticket(self):
        """Test the analyze_ticket function."""
        # Set up return values
        self.mock_get_ticket_details.return_value = "Details of TEST-123"
        self.mock_ask_ollama.return_value = "Analysis of ticket TEST-123 regarding the question"
        
        # Call the function
        result = jira_ollama_mcp.analyze_ticket("TEST-123", "What is the priority?")
        
        # Verify the mocks were called correctly
        self.mock_get_ticket_details.assert_called_once_with("TEST-123")
        self.mock_ask_ollama.assert_called_once()
        
        # Check the result
        self.assertIn("Analysis of TEST-123", result)
        self.assertIn("Analysis of ticket TEST-123", result)

if __name__ == '__main__':
    unittest.main() 