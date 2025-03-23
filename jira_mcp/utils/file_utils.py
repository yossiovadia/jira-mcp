"""
File utility functions for the Jira MCP package
"""
import os
import shutil
from .logging import logger
from .security import sanitize_filename, validate_path_safety

# Default supported file extensions
TEXT_FILE_EXTENSIONS = [
    '.txt', '.md', '.py', '.js', '.html', '.css', '.java', 
    '.cpp', '.c', '.h', '.json', '.xml', '.csv', '.log'
]

def setup_attachment_directory(base_dir, ticket_key=None):
    """
    Set up a directory for storing attachments.
    
    Args:
        base_dir: Base directory for attachments
        ticket_key: Optional ticket key to create a subdirectory
        
    Returns:
        str: Path to the attachment directory
    """
    # Create the base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # If a ticket key is provided, create a subdirectory
    if ticket_key:
        attachments_dir = os.path.join(base_dir, ticket_key)
        os.makedirs(attachments_dir, exist_ok=True)
        return attachments_dir
    
    return base_dir

def save_attachment(data, directory, filename):
    """
    Save attachment data to a file.
    
    Args:
        data: Binary attachment data
        directory: Directory to save the file in
        filename: Name of the file
        
    Returns:
        dict: Information about the saved file
    """
    # Sanitize the filename
    safe_filename = sanitize_filename(filename)
    
    # Create the full file path
    file_path = os.path.join(directory, safe_filename)
    
    # Save the file
    with open(file_path, 'wb') as f:
        f.write(data)
    
    # Get file size and MIME type (guessed from extension)
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(safe_filename)[1].lower()
    mime_map = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.pdf': 'application/pdf',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
    }
    mime_type = mime_map.get(ext, 'application/octet-stream')
    
    return {
        'filename': safe_filename,
        'path': file_path,
        'size': file_size,
        'mime_type': mime_type
    }

def read_text_file(file_path, encoding='utf-8'):
    """
    Read a text file safely.
    
    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)
        
    Returns:
        str: File contents or error message
    """
    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text file: {str(e)}")
        return f"Error reading file: {str(e)}"

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file if PDF support is available.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text or error message
    """
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text() or "No text content on this page."
        
        return text if text.strip() else "No extractable text content found in the PDF."
    except ImportError:
        return "PDF extraction is not available. Install PyPDF2 package to enable this feature."
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return f"Error extracting text from PDF: {str(e)}"

def clean_directory(directory, validate_base_dirs=None):
    """
    Delete a directory and all its contents safely.
    
    Args:
        directory: Directory to clean
        validate_base_dirs: List of allowed base directories for safety validation
        
    Returns:
        tuple: (success, message)
    """
    # Security validation
    if validate_base_dirs and not validate_path_safety(directory, validate_base_dirs):
        logger.error(f"Security alert: Attempted to clean directory outside allowed paths: {directory}")
        return False, "Security restriction: Cannot clean directory outside of expected paths"
    
    try:
        # Count files before deletion
        file_count = sum(1 for _ in os.listdir(directory) if os.path.isfile(os.path.join(directory, _)))
        
        # Delete the directory
        shutil.rmtree(directory)
        
        return True, f"Successfully deleted {file_count} file(s) from {directory}"
    except Exception as e:
        logger.error(f"Error cleaning directory {directory}: {str(e)}")
        return False, f"Error cleaning directory: {str(e)}" 