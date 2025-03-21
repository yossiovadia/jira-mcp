#!/usr/bin/env python3
"""
Unit tests for the attachment-related functions
"""
import sys
import os
import unittest
import warnings
from unittest.mock import patch, MagicMock, mock_open

# Suppress PyPDF2 deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, message="PyPDF2 is deprecated")

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAttachmentFunctions(unittest.TestCase):
    """Tests for the attachment-related functions"""

    @patch('jira_ollama_mcp.logger')
    @patch('os.makedirs')
    @patch('os.path.getsize')
    def test_get_ticket_attachments(self, mock_getsize, mock_makedirs, mock_logger):
        """Test get_ticket_attachments function with valid attachments."""
        from jira_ollama_mcp import get_ticket_attachments
        
        # Setup mock for issue object
        mock_issue = MagicMock()
        
        # Create mock attachments
        mock_attachment1 = MagicMock()
        mock_attachment1.filename = 'test_file1.txt'
        mock_attachment1.mimeType = 'text/plain'
        mock_attachment1.get.return_value = b'Test content for file 1'
        
        mock_attachment2 = MagicMock()
        mock_attachment2.filename = 'test_file2.pdf'
        mock_attachment2.mimeType = 'application/pdf'
        mock_attachment2.get.return_value = b'PDF content for file 2'
        
        # Set the attachments on the issue
        mock_issue.fields.attachment = [mock_attachment1, mock_attachment2]
        
        # Setup mock for jira object
        mock_jira = MagicMock()
        mock_jira.issue.return_value = mock_issue
        
        # Mock file size calls
        mock_getsize.side_effect = [1024, 2048]  # Sizes in bytes
        
        # Mock open function
        mock_file = MagicMock()
        with patch('builtins.open', mock_open()):
            # Patch the get_jira_client function to return our mock jira
            with patch('jira_ollama_mcp.get_jira_client', return_value=mock_jira):
                # Call the function
                result = get_ticket_attachments('TEST-123')
        
        # Verify the mocks were called correctly
        mock_jira.issue.assert_called_once_with('TEST-123')
        mock_makedirs.assert_called_once()
        
        # Check that the result includes the expected details
        self.assertIn('Downloaded 2 attachment(s)', result)
        self.assertIn('TEST-123', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: get_ticket_attachments for TEST-123")

    @patch('jira_ollama_mcp.logger')
    def test_get_ticket_attachments_no_attachments(self, mock_logger):
        """Test get_ticket_attachments function with no attachments."""
        from jira_ollama_mcp import get_ticket_attachments
        
        # Setup mock for issue object with no attachments
        mock_issue = MagicMock()
        mock_issue.fields = MagicMock()
        delattr(mock_issue.fields, 'attachment')  # Remove attachment attribute
        
        # Setup mock for jira object
        mock_jira = MagicMock()
        mock_jira.issue.return_value = mock_issue
        
        # Patch the get_jira_client function
        with patch('jira_ollama_mcp.get_jira_client', return_value=mock_jira):
            # Call the function
            result = get_ticket_attachments('TEST-123')
        
        # Verify the mock was called correctly
        mock_jira.issue.assert_called_once_with('TEST-123')
        
        # Check that the result includes the expected message
        self.assertIn('No attachments found for ticket TEST-123', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: get_ticket_attachments for TEST-123")

    @patch('jira_ollama_mcp.logger')
    def test_get_ticket_attachments_error(self, mock_logger):
        """Test get_ticket_attachments function with an error."""
        from jira_ollama_mcp import get_ticket_attachments
        
        # Setup mock for jira object with error
        mock_jira = MagicMock()
        mock_jira.issue.side_effect = Exception("Ticket not found")
        
        # Patch the get_jira_client function
        with patch('jira_ollama_mcp.get_jira_client', return_value=mock_jira):
            # Call the function
            result = get_ticket_attachments('INVALID-123')
        
        # Verify the mock was called correctly
        mock_jira.issue.assert_called_once_with('INVALID-123')
        
        # Check that the result includes the error message
        self.assertIn('Error downloading attachments', result)
        self.assertIn('Ticket not found', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: get_ticket_attachments for INVALID-123")
        mock_logger.error.assert_called_once()

    @patch('jira_ollama_mcp.logger')
    @patch('jira_ollama_mcp.ask_ollama')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_analyze_attachment_text_file(self, mock_getsize, mock_exists, mock_ask_ollama, mock_logger):
        """Test analyze_attachment function with a text file."""
        from jira_ollama_mcp import analyze_attachment
        
        # Set up mocks
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # 1KB
        mock_ask_ollama.return_value = "This is a sample analysis of the text file."
        
        # Mock file content
        file_content = "This is a sample text file content for testing."
        
        # Mock open function
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Patch the jira object
            with patch('jira_ollama_mcp.jira', MagicMock()):
                # Call the function
                result = analyze_attachment('TEST-123', 'sample.txt')
        
        # Verify the mock was called correctly
        mock_exists.assert_called_once()
        mock_ask_ollama.assert_called_once()
        
        # Check that the result includes the expected analysis
        self.assertIn('Analysis of \'sample.txt\' from ticket TEST-123', result)
        self.assertIn('This is a sample analysis of the text file.', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: analyze_attachment for TEST-123, file: sample.txt")

    @patch('jira_ollama_mcp.logger')
    @patch('jira_ollama_mcp.ask_ollama')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('jira_ollama_mcp.PDF_SUPPORT', True)
    @patch('jira_ollama_mcp.extract_text_from_pdf')
    def test_analyze_attachment_pdf_file(self, mock_extract_pdf, mock_getsize, mock_exists, mock_ask_ollama, mock_logger):
        """Test analyze_attachment function with a PDF file."""
        from jira_ollama_mcp import analyze_attachment
        
        # Set up mocks
        mock_exists.return_value = True
        mock_getsize.return_value = 5120  # 5KB
        mock_extract_pdf.return_value = "Extracted text content from PDF file."
        mock_ask_ollama.return_value = "This is a sample analysis of the PDF file."
        
        # Patch the jira object
        with patch('jira_ollama_mcp.jira', MagicMock()):
            # Call the function
            result = analyze_attachment('TEST-123', 'sample.pdf')
        
        # Verify the mocks were called correctly
        mock_exists.assert_called_once()
        mock_extract_pdf.assert_called_once()
        mock_ask_ollama.assert_called_once()
        
        # Check that the result includes the expected analysis
        self.assertIn('Analysis of \'sample.pdf\' from ticket TEST-123', result)
        self.assertIn('This is a sample analysis of the PDF file.', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: analyze_attachment for TEST-123, file: sample.pdf")

    @patch('jira_ollama_mcp.logger')
    @patch('os.path.exists')
    def test_analyze_attachment_file_not_found(self, mock_exists, mock_logger):
        """Test analyze_attachment function when file does not exist."""
        from jira_ollama_mcp import analyze_attachment
        
        # Set up mocks
        mock_exists.return_value = False
        
        # Patch the jira object
        with patch('jira_ollama_mcp.jira', MagicMock()):
            # Call the function
            result = analyze_attachment('TEST-123', 'nonexistent.txt')
        
        # Verify the mock was called correctly
        mock_exists.assert_called_once()
        
        # Check that the result includes the expected error message
        self.assertIn('Error: Attachment \'nonexistent.txt\' not found', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: analyze_attachment for TEST-123, file: nonexistent.txt")

    @patch('jira_ollama_mcp.logger')
    @patch('jira_ollama_mcp.get_ticket_attachments')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('jira_ollama_mcp.ask_ollama')
    def test_analyze_all_attachments(self, mock_ask_ollama, mock_isfile, mock_listdir, mock_exists, mock_get_attachments, mock_logger):
        """Test analyze_all_attachments function."""
        from jira_ollama_mcp import analyze_all_attachments
        
        # Set up mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ['file1.txt', 'file2.md']
        mock_isfile.return_value = True
        
        # Mock the individual file analyses
        mock_ask_ollama.side_effect = [
            "Analysis of file1.txt: This is a sample text file.",
            "Analysis of file2.md: This is a markdown file with documentation.",
            "Combined analysis: The documents contain sample text and documentation."
        ]
        
        # Mock file content
        file_content = "This is sample content."
        
        # Mock open function
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Mock os.path.getsize
            with patch('os.path.getsize', return_value=1024):
                # Patch the jira object
                with patch('jira_ollama_mcp.jira', MagicMock()):
                    # Call the function with a question
                    result = analyze_all_attachments('TEST-123', 'What is in these files?')
        
        # Verify the mocks were called correctly
        mock_exists.assert_called()
        # listdir may be called multiple times, at least once
        self.assertGreaterEqual(mock_listdir.call_count, 1)
        # Should be called 3 times: twice for individual files, once for combined analysis
        self.assertEqual(mock_ask_ollama.call_count, 3)
        
        # Check that the result includes the expected analyses
        self.assertIn('Analysis of all attachments from ticket TEST-123', result)
        self.assertIn('Combined analysis', result)
        self.assertIn('file1.txt', result)
        self.assertIn('file2.md', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: analyze_all_attachments for TEST-123")

    @patch('jira_ollama_mcp.logger')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    @patch('os.path.isfile')
    def test_cleanup_attachments_specific_ticket(self, mock_isfile, mock_rmtree, mock_listdir, mock_exists, mock_logger):
        """Test cleanup_attachments function for a specific ticket."""
        from jira_ollama_mcp import cleanup_attachments
        
        # Set up mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ['file1.txt', 'file2.pdf']
        mock_isfile.return_value = True
        
        # Call the function
        result = cleanup_attachments('TEST-123')
        
        # Verify the mocks were called correctly
        # exists is called multiple times
        self.assertGreaterEqual(mock_exists.call_count, 1)
        mock_rmtree.assert_called_once()
        
        # Check that the result includes the expected message
        self.assertIn('Successfully deleted 2 attachment(s) for ticket TEST-123', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: cleanup_attachments for TEST-123")

    @patch('jira_ollama_mcp.logger')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_cleanup_attachments_all_tickets(self, mock_isfile, mock_isdir, mock_rmtree, mock_listdir, mock_exists, mock_logger):
        """Test cleanup_attachments function for all tickets."""
        from jira_ollama_mcp import cleanup_attachments
        
        # Set up mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_isfile.return_value = True
        
        # First listdir returns the ticket directories, the next two are for each ticket's files
        mock_listdir.side_effect = [
            ['TEST-123', 'TEST-456'],  # Directories in attachments/
            ['TEST-123', 'TEST-456'],  # Same list for second loop
            ['file1.txt', 'file2.pdf'],  # Files in TEST-123/ (2 files)
            ['file3.md', 'file4.txt']  # Files in TEST-456/ (2 files)
        ]
        
        # Call the function without a specific ticket key
        result = cleanup_attachments()
        
        # For debugging
        print(f"rmtree calls: {mock_rmtree.call_args_list}")
        print(f"listdir calls: {mock_listdir.call_args_list}")
        
        # Verify the behavior
        self.assertGreaterEqual(mock_exists.call_count, 1)
        self.assertGreaterEqual(mock_listdir.call_count, 3)
        self.assertGreaterEqual(mock_rmtree.call_count, 1)
        
        # Check that the result includes the expected message about 4 files
        self.assertIn('Successfully deleted 4 attachment(s) from 2 ticket(s)', result)
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Tool called: cleanup_attachments for all tickets")

    @patch('jira_ollama_mcp.logger')
    def test_extract_text_from_pdf_with_pdf_support(self, mock_logger):
        """Test the extract_text_from_pdf function with PDF support enabled."""
        from jira_ollama_mcp import extract_text_from_pdf
        
        # Mock the PDF page object
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted text from PDF page"
        
        # Create a mock PDF reader
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [mock_page, mock_page]  # Two pages
        
        with patch('jira_ollama_mcp.PDF_SUPPORT', True):
            with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
                with patch('builtins.open', mock_open()):
                    # Call the function
                    result = extract_text_from_pdf('test.pdf')
        
        # Check the result
        self.assertIn('Extracted text from PDF page', result)
        self.assertIn('Page 1', result)
        self.assertIn('Page 2', result)

if __name__ == '__main__':
    unittest.main() 