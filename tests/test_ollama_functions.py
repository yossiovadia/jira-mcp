#!/usr/bin/env python3
"""
Unit tests for the Ollama integration functions
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestOllamaFunctions(unittest.TestCase):
    """Tests for the Ollama integration functions"""

    @patch('httpx.post')
    def test_ask_ollama(self, mock_post):
        """Test the ask_ollama function."""
        from jira_ollama_mcp import ask_ollama
        
        # Mock the httpx.post response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "This is a test response from Ollama"}
        mock_post.return_value = mock_response
        
        # Test with prompt only
        result = ask_ollama("Test prompt")
        
        # Verify call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args['json']['prompt'], "Test prompt")
        self.assertEqual(call_args['json']['system'], "")
        
        # Verify the result is correct
        self.assertEqual(result, "This is a test response from Ollama")
        
        # Reset the mock for the next test
        mock_post.reset_mock()
        
        # Test with prompt and system message
        result = ask_ollama("Test prompt", "System message")
        
        # Verify call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args['json']['prompt'], "Test prompt")
        self.assertEqual(call_args['json']['system'], "System message")

    @patch('jira_ollama_mcp.ask_ollama')
    @patch('jira_ollama_mcp.get_ticket_details')
    @patch('jira_ollama_mcp.jira')
    def test_summarize_ticket(self, mock_jira, mock_get_ticket_details, mock_ask_ollama):
        """Test the summarize_ticket function."""
        from jira_ollama_mcp import summarize_ticket
        
        # Set up the mocks
        mock_get_ticket_details.return_value = "Ticket details"
        mock_ask_ollama.return_value = "This is a summarized ticket"
        
        # Call the function
        result = summarize_ticket("TEST-123")
        
        # Verify the get_ticket_details was called
        mock_get_ticket_details.assert_called_once_with("TEST-123")
        
        # Verify ask_ollama was called with the right arguments
        mock_ask_ollama.assert_called_once()
        args = mock_ask_ollama.call_args[0]
        self.assertIn("Ticket details", args[0])
        
        # Verify the result contains the summary
        self.assertIn("Summary of TEST-123", result)
        self.assertIn("This is a summarized ticket", result)
        
    @patch('jira_ollama_mcp.ask_ollama')
    @patch('jira_ollama_mcp.get_ticket_details')
    @patch('jira_ollama_mcp.jira')
    def test_analyze_ticket(self, mock_jira, mock_get_ticket_details, mock_ask_ollama):
        """Test the analyze_ticket function."""
        from jira_ollama_mcp import analyze_ticket
        
        # Set up the mocks
        mock_get_ticket_details.return_value = "Ticket details"
        mock_ask_ollama.return_value = "This is an analysis of the ticket"
        
        # Call the function
        result = analyze_ticket("TEST-123", "What is the priority?")
        
        # Verify the get_ticket_details was called
        mock_get_ticket_details.assert_called_once_with("TEST-123")
        
        # Verify ask_ollama was called with the right arguments
        mock_ask_ollama.assert_called_once()
        args = mock_ask_ollama.call_args[0]
        self.assertIn("Ticket details", args[0])
        self.assertIn("What is the priority?", args[0])
        
        # Verify the result contains the analysis
        self.assertIn("Analysis of TEST-123", result)
        self.assertIn("This is an analysis of the ticket", result)

    @patch('httpx.post')
    def test_ask_ollama_error(self, mock_post):
        """Test the ask_ollama function with an error response."""
        from jira_ollama_mcp import ask_ollama
        
        # Mock the httpx.post response for a server error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # Call the function
        result = ask_ollama("Test prompt")
        
        # Verify the result contains the error message
        self.assertIn("Error from Ollama API: 500", result)
        
        # Reset the mock
        mock_post.reset_mock()
        
        # Mock a network error
        mock_post.side_effect = Exception("Network error")
        
        # Call the function
        result = ask_ollama("Test prompt")
        
        # Verify the result contains the error message
        self.assertIn("Error calling Ollama: Network error", result)

if __name__ == '__main__':
    unittest.main() 