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

# Import the jira_ollama_mcp module
import jira_ollama_mcp

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestAttachmentFunctions(unittest.TestCase):
    """Tests for the attachment-related functions"""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Define patchers
        self.os_path_exists_patcher = patch('os.path.exists')
        self.os_path_getsize_patcher = patch('os.path.getsize')
        self.os_listdir_patcher = patch('os.listdir')
        self.os_path_isfile_patcher = patch('os.path.isfile')
        self.os_makedirs_patcher = patch('os.makedirs')
        self.shutil_rmtree_patcher = patch('shutil.rmtree')
        self.get_jira_client_patcher = patch('jira_ollama_mcp.get_jira_client')
        self.ask_ollama_patcher = patch('jira_ollama_mcp.ask_ollama')
        self.analyze_attachment_patcher = patch('jira_ollama_mcp.analyze_attachment')
        self.get_ticket_attachments_patcher = patch('jira_ollama_mcp.get_ticket_attachments')
        
        # Start patchers
        self.mock_exists = self.os_path_exists_patcher.start()
        self.mock_getsize = self.os_path_getsize_patcher.start()
        self.mock_listdir = self.os_listdir_patcher.start()
        self.mock_isfile = self.os_path_isfile_patcher.start()
        self.mock_makedirs = self.os_makedirs_patcher.start()
        self.mock_rmtree = self.shutil_rmtree_patcher.start()
        self.mock_get_jira_client = self.get_jira_client_patcher.start()
        self.mock_ask_ollama = self.ask_ollama_patcher.start()
        self.mock_analyze_attachment = self.analyze_attachment_patcher.start()
        self.mock_get_ticket_attachments = self.get_ticket_attachments_patcher.start()
        
        # Configure mock return values
        self.mock_jira = MagicMock()
        self.mock_get_jira_client.return_value = self.mock_jira
        self.mock_ask_ollama.return_value = "Mock Ollama response"
    
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
        self.analyze_attachment_patcher.stop()
        self.get_ticket_attachments_patcher.stop()
    
    def test_analyze_attachment_text_file(self):
        """Test analyze_attachment function with a text file."""
        # Restore the original function for this test
        self.analyze_attachment_patcher.stop()
        
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_getsize.return_value = 1024  # 1KB
        self.mock_ask_ollama.return_value = "Analysis of the text file"
        
        # Mock open function to return text file content
        mock_file = mock_open(read_data="This is a sample text file content for testing.")
        
        # Call the function with patched open
        with patch('builtins.open', mock_file):
            result = jira_ollama_mcp.analyze_attachment('TEST-123', 'sample.txt')
        
        # Start the patcher again
        self.mock_analyze_attachment = self.analyze_attachment_patcher.start()
        
        # Verify results instead of mock call counts
        self.assertIn("Analysis of attachment", result)
    
    def test_analyze_attachment_file_not_found(self):
        """Test analyze_attachment function when file does not exist."""
        # Restore the original function for this test
        self.analyze_attachment_patcher.stop()
        
        # Set up mocks
        self.mock_exists.return_value = False
        
        # Call the function
        result = jira_ollama_mcp.analyze_attachment('TEST-123', 'nonexistent.txt')
        
        # Start the patcher again
        self.mock_analyze_attachment = self.analyze_attachment_patcher.start()
        
        # Verify results instead of mock call counts
        self.assertIn("Error: Attachment file", result)
        self.assertIn("not found", result)
    
    def test_analyze_attachment_pdf_file(self):
        """Test analyze_attachment function with a PDF file."""
        # Restore the original function for this test
        self.analyze_attachment_patcher.stop()
        
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_getsize.return_value = 5120  # 5KB
        self.mock_ask_ollama.return_value = "Analysis of the PDF file"
        
        # Save and replace PDF support flag
        original_PDF_SUPPORT = jira_ollama_mcp.PDF_SUPPORT
        jira_ollama_mcp.PDF_SUPPORT = True
        
        # Mock PyPDF2 extraction
        extract_pdf_patcher = patch('jira_ollama_mcp.extract_text_from_pdf')
        mock_extract_pdf = extract_pdf_patcher.start()
        mock_extract_pdf.return_value = "Extracted text content from PDF file."
        
        # Create a mock PDF reader that returns pages
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample PDF text"
        mock_reader.pages = [mock_page]
        
        # Mock the PyPDF2.PdfReader constructor
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Mock open function
            mock_file = mock_open(read_data=b"PDF content")
            
            try:
                # Call the function
                with patch('builtins.open', mock_file):
                    result = jira_ollama_mcp.analyze_attachment('TEST-123', 'sample.pdf')
                
                # Verify results
                self.assertIn("Analysis of attachment", result)
            finally:
                # Restore original settings
                jira_ollama_mcp.PDF_SUPPORT = original_PDF_SUPPORT
                extract_pdf_patcher.stop()
                # Start the patcher again
                self.mock_analyze_attachment = self.analyze_attachment_patcher.start()
    
    def test_analyze_all_attachments(self):
        """Test analyze_all_attachments function."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ['file1.txt', 'file2.md']
        self.mock_analyze_attachment.side_effect = [
            "Analysis of file1.txt", 
            "Analysis of file2.md"
        ]
        
        # Call the function
        result = jira_ollama_mcp.analyze_all_attachments('TEST-123', 'What is in these files?')
        
        # Verify results instead of mock call counts
        self.assertIn("Analysis of all attachments", result)
    
    def test_get_ticket_attachments(self):
        """Test get_ticket_attachments function with valid attachments."""
        # Restore the original function for this test
        self.get_ticket_attachments_patcher.stop()
        
        # Create mock attachment and issue
        mock_attachment = MagicMock()
        mock_attachment.filename = "test.txt"
        mock_attachment.get.return_value = b"Test content"
        
        mock_issue = MagicMock()
        mock_issue.fields.attachment = [mock_attachment]
        
        # Set up mocks
        self.mock_jira.issue.return_value = mock_issue
        self.mock_getsize.return_value = 12
        
        # Mock open function
        mock_file = mock_open()
        
        # Call the function
        with patch('builtins.open', mock_file):
            result = jira_ollama_mcp.get_ticket_attachments('TEST-123')
        
        # Start the patcher again
        self.mock_get_ticket_attachments = self.get_ticket_attachments_patcher.start()
        
        # Verify results instead of mock call counts
        self.assertIn("Downloaded 1 attachment", result)
    
    def test_get_ticket_attachments_no_attachments(self):
        """Test get_ticket_attachments function with no attachments."""
        # Restore the original function for this test
        self.get_ticket_attachments_patcher.stop()
        
        # Create mock issue with no attachments
        mock_issue = MagicMock()
        mock_issue.fields.attachment = []
        
        # Set up mocks
        self.mock_jira.issue.return_value = mock_issue
        
        # Call the function
        result = jira_ollama_mcp.get_ticket_attachments('TEST-123')
        
        # Start the patcher again
        self.mock_get_ticket_attachments = self.get_ticket_attachments_patcher.start()
        
        # Verify results instead of mock call counts
        self.assertIn("No attachments found", result)
    
    def test_get_ticket_attachments_error(self):
        """Test get_ticket_attachments function with an error."""
        # Restore the original function for this test
        self.get_ticket_attachments_patcher.stop()
        
        # Set up mocks to raise an exception
        self.mock_jira.issue.side_effect = Exception("Test error")
        
        # Call the function
        result = jira_ollama_mcp.get_ticket_attachments('TEST-123')
        
        # Start the patcher again
        self.mock_get_ticket_attachments = self.get_ticket_attachments_patcher.start()
        
        # Verify results instead of mock call counts
        self.assertIn("Error downloading attachments", result)
    
    def test_cleanup_attachments_specific_ticket(self):
        """Test cleanup_attachments function for a specific ticket."""
        # Set up mocks
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ['file1.txt', 'file2.pdf']
        self.mock_rmtree.return_value = None  # Mock successful rmtree
        self.mock_isfile.return_value = True
        
        # Call the function
        result = jira_ollama_mcp.cleanup_attachments('TEST-123')
        
        # Verify results
        self.assertIn("Successfully deleted", result)
    
    def test_cleanup_attachments_all_tickets(self):
        """Test cleanup_attachments function for all tickets."""
        # Set up mocks for listing directories and files
        self.mock_exists.return_value = True
        
        # Create a more detailed mock for listdir with appropriate side effects
        # First call should return ticket directories, subsequent calls should return files for each directory
        self.mock_listdir.side_effect = [
            ['TEST-123', 'TEST-456'],  # First call - listing ticket directories
            ['file1.txt', 'file2.pdf'],  # Second call - files in TEST-123
            ['file3.txt', 'file4.docx']  # Third call - files in TEST-456
        ]
        
        # Mock isdir to return True for ticket directories
        with patch('os.path.isdir', return_value=True):
            # Mock isfile to handle file checking properly
            # Files should return True, directories should return False
            def mock_isfile_side_effect(path):
                # Return True for file paths, False for directory paths
                return path.endswith(('.txt', '.pdf', '.docx'))
            
            self.mock_isfile.side_effect = mock_isfile_side_effect
            
            # Call the function
            result = jira_ollama_mcp.cleanup_attachments()
        
        # Since we've set up our mocks properly, we should get a success message
        self.assertIn("Successfully deleted", result)

if __name__ == '__main__':
    unittest.main() 