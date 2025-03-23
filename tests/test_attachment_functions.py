#!/usr/bin/env python3
"""
Unit tests for the attachment-related functions
"""
import sys
import os
import unittest
import warnings
import logging
from unittest.mock import patch, MagicMock, mock_open
import shutil

# Suppress PyPDF2 deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, message="PyPDF2 is deprecated")

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from the modules
from jira_mcp.tools.attachments import analyze_attachment, analyze_all_attachments, get_ticket_attachments, cleanup_attachments
from jira_mcp.jira_client import get_jira_client
from jira_mcp.ollama_client import ask_ollama

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestAttachmentFunctions(unittest.TestCase):
    """Tests for the attachment-related functions"""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Define patchers for external dependencies
        self.os_path_exists_patcher = patch('os.path.exists')
        self.os_path_getsize_patcher = patch('os.path.getsize')
        self.os_listdir_patcher = patch('os.listdir')
        self.os_path_isfile_patcher = patch('os.path.isfile')
        self.os_makedirs_patcher = patch('os.makedirs')
        self.shutil_rmtree_patcher = patch('shutil.rmtree')
        
        # Start external patchers
        self.mock_exists = self.os_path_exists_patcher.start()
        self.mock_getsize = self.os_path_getsize_patcher.start()
        self.mock_listdir = self.os_listdir_patcher.start()
        self.mock_isfile = self.os_path_isfile_patcher.start()
        self.mock_makedirs = self.os_makedirs_patcher.start()
        self.mock_rmtree = self.shutil_rmtree_patcher.start()
        
        # Define patchers for internal functions
        self.get_jira_client_patcher = patch('jira_mcp.tools.attachments.get_jira_client')
        self.ask_ollama_patcher = patch('jira_mcp.tools.attachments.ask_ollama')
        
        # Start internal patchers
        self.mock_get_jira_client = self.get_jira_client_patcher.start()
        self.mock_ask_ollama = self.ask_ollama_patcher.start()
        
        # Configure mock return values
        self.mock_jira = MagicMock()
        self.mock_get_jira_client.return_value = self.mock_jira
        self.mock_ask_ollama.return_value = "Mock Ollama response"
        
        # Default the exists check to True to avoid "Not connected to Jira" errors
        self.mock_exists.return_value = True
    
    def tearDown(self):
        """Tear down test fixtures after each test."""
        # Stop all patchers
        self.os_path_exists_patcher.stop()
        self.os_path_getsize_patcher.stop()
        self.os_listdir_patcher.stop()
        self.os_path_isfile_patcher.stop()
        self.os_makedirs_patcher.stop()
        self.shutil_rmtree_patcher.stop()
        self.get_jira_client_patcher.stop()
        self.ask_ollama_patcher.stop()
    
    def test_analyze_attachment_text_file(self):
        """Test analyze_attachment function with a text file."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_getsize.return_value = 1024  # 1KB
        self.mock_ask_ollama.return_value = "Analysis of the text file"
        
        # Mock the file reading
        with patch('jira_mcp.utils.file_utils.read_text_file', return_value="This is a sample text file content for testing."):
            # Call the function 
            result = analyze_attachment('TEST-123', 'sample.txt')
        
        # Verify results
        self.assertIn("Analysis of attachment", result)
        self.assertIn("Analysis of the text file", result)
    
    def test_analyze_attachment_file_not_found(self):
        """Test analyze_attachment function when file does not exist."""
        # Set up mocks - file doesn't exist
        self.mock_exists.return_value = False
        
        # Call the function
        result = analyze_attachment('TEST-123', 'nonexistent.txt')
        
        # Verify results
        self.assertIn("Error: Attachment file", result)
        self.assertIn("not found", result)
    
    def test_analyze_attachment_pdf_file(self):
        """Test analyze_attachment function with a PDF file."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_getsize.return_value = 5120  # 5KB
        self.mock_ask_ollama.return_value = "Analysis of the PDF file"
        
        # Mock the PDF extraction
        with patch('jira_mcp.config.config.pdf_support', True), \
             patch('jira_mcp.utils.file_utils.extract_text_from_pdf', return_value="Extracted text content from PDF file."):
            
            # Call the function
            result = analyze_attachment('TEST-123', 'sample.pdf')
            
            # Verify results
            self.assertIn("Analysis of attachment", result)
            self.assertIn("Analysis of the PDF file", result)
    
    def test_analyze_all_attachments(self):
        """Test analyze_all_attachments function."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ['file1.txt', 'file2.md']
        
        # Mock the analyze_attachment function directly
        with patch('jira_mcp.tools.attachments.analyze_attachment') as mock_analyze_attachment:
            mock_analyze_attachment.side_effect = [
                "Analysis of file1.txt", 
                "Analysis of file2.md"
            ]
            
            # Call the function
            result = analyze_all_attachments('TEST-123', 'What is in these files?')
            
            # Verify it was called for each file
            self.assertEqual(mock_analyze_attachment.call_count, 2)
        
        # Verify results
        self.assertIn("Analysis of all attachments", result)
    
    def test_get_ticket_attachments(self):
        """Test get_ticket_attachments function with valid attachments."""
        # Create mock attachment and issue
        mock_attachment = MagicMock()
        mock_attachment.filename = "test.txt"
        mock_attachment.get.return_value = b"Test content"
        
        mock_issue = MagicMock()
        mock_issue.fields.attachment = [mock_attachment]
        
        # Set up mocks
        self.mock_jira.issue.return_value = mock_issue
        self.mock_getsize.return_value = 12
        
        # Mock the file writing operation
        with patch('builtins.open', mock_open()):
            result = get_ticket_attachments('TEST-123')
        
        # Verify results
        self.assertIn("Downloaded 1 attachment", result)
        self.mock_jira.issue.assert_called_once_with('TEST-123')
    
    def test_get_ticket_attachments_no_attachments(self):
        """Test get_ticket_attachments function with no attachments."""
        # Create mock issue with no attachments
        mock_issue = MagicMock()
        mock_issue.fields.attachment = []
        
        # Set up mocks
        self.mock_jira.issue.return_value = mock_issue
        
        # Call the function
        result = get_ticket_attachments('TEST-123')
        
        # Verify results
        self.assertIn("No attachments found", result)
        self.mock_jira.issue.assert_called_once_with('TEST-123')
    
    def test_get_ticket_attachments_error(self):
        """Test get_ticket_attachments function with an error."""
        # Set up mocks to raise an exception
        self.mock_jira.issue.side_effect = Exception("Test error")
        
        # Call the function
        result = get_ticket_attachments('TEST-123')
        
        # Verify results
        self.assertIn("Error downloading attachments", result)
        self.mock_jira.issue.assert_called_once_with('TEST-123')
    
    def test_cleanup_attachments_specific_ticket(self):
        """Test cleanup_attachments function for a specific ticket."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ['file1.txt', 'file2.pdf']
        self.mock_isfile.return_value = True
        
        # Patch validate_path_safety to return True for this test
        with patch('jira_mcp.tools.attachments.validate_path_safety', return_value=True):
            # Patch the config.attachments_base_dir to return a known value
            with patch('jira_mcp.tools.attachments.config.attachments_base_dir', '/tmp/attachments'):
                # Also patch validate_ticket_key to return True
                with patch('jira_mcp.tools.attachments.validate_ticket_key', return_value=True):
                    # Call the function
                    result = cleanup_attachments('TEST-123')
                    
                    # Check that rmtree was called with the expected path
                    self.mock_rmtree.assert_called_once()
                    
                    # Extract the first positional argument that rmtree was called with
                    call_args = self.mock_rmtree.call_args[0]
                    if call_args:
                        # Just check the path contains what we expect
                        self.assertIn('TEST-123', call_args[0])
        
        # Check the result contains the expected text
        self.assertIn("Successfully deleted", result)
        self.assertIn("TEST-123", result)

if __name__ == '__main__':
    unittest.main() 