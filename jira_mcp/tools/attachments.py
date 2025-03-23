"""
Tools for managing and analyzing Jira ticket attachments
"""
import os
import re
import shutil
from ..utils.logging import logger
from ..utils.security import validate_ticket_key, sanitize_filename, validate_path_safety
from ..utils.file_utils import setup_attachment_directory, read_text_file, extract_text_from_pdf
from ..jira_client.client import get_jira_client
from ..ollama_client import ask_ollama
from ..config import config

# Default supported file extensions
TEXT_FILE_EXTENSIONS = [
    '.txt', '.md', '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', 
    '.h', '.json', '.xml', '.csv', '.log'
]

def get_ticket_attachments(ticket_key: str) -> str:
    """Fetch and download all attachments from a Jira ticket to a local directory.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: get_ticket_attachments for {ticket_key}")
    
    # Security: Validate ticket key format to prevent path traversal
    if not validate_ticket_key(ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get issue details from Jira
        issue = jira_client.issue(ticket_key)
        
        # Create attachments directory if it doesn't exist
        attachments_dir = setup_attachment_directory(config.attachments_base_dir, ticket_key)
        
        # Initialize a list to track which files were downloaded
        downloaded_files = []
        
        # Check if the issue has attachments field
        if not hasattr(issue.fields, 'attachment'):
            return f"No attachments found for ticket {ticket_key}."
        
        # Download each attachment
        attachments = issue.fields.attachment
        if not attachments:
            return f"No attachments found for ticket {ticket_key}."
        
        for attachment in attachments:
            # Sanitize the filename to prevent path traversal
            safe_filename = sanitize_filename(attachment.filename)
            
            # Get binary data
            attachment_data = attachment.get()
            
            # Create file path
            file_path = os.path.join(attachments_dir, safe_filename)
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(attachment_data)
            
            downloaded_files.append({
                'filename': safe_filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'mime_type': attachment.mimeType if hasattr(attachment, 'mimeType') else 'unknown'
            })
        
        # Return a message about the downloaded files
        if downloaded_files:
            support_msg = "PDF files are also supported." if config.pdf_support else "Install PyPDF2 to enable PDF support."
            return f"""Downloaded {len(downloaded_files)} attachment(s) from ticket {ticket_key}.
Location:
- Relative path: attachments/{ticket_key}
- Absolute path: {attachments_dir}
{support_msg}"""
        else:
            return f"No attachments found for ticket {ticket_key}."
    
    except Exception as e:
        logger.error(f"Error downloading attachments: {str(e)}")
        return f"Error downloading attachments from ticket {ticket_key}: {str(e)}"

def analyze_attachment(ticket_key: str, filename: str, question: str = None) -> str:
    """Analyze a specific attachment from a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        filename: The name of the attachment file to analyze
        question: Optional specific question about the attachment
    """
    logger.info(f"Tool called: analyze_attachment for {ticket_key}, file: {filename}")
    
    # Security: Validate ticket key format to prevent path traversal
    if not validate_ticket_key(ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Security: Validate filename to prevent path traversal
    if os.path.dirname(filename) or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return f"Error: Invalid filename: {filename}. Only alphanumeric characters, dots, underscores and hyphens are allowed."
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Build the path to the attachment
    file_path = os.path.join(config.attachments_base_dir, ticket_key, filename)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        logger.error(f"Attachment file not found: {file_path}")
        return f"""Error: Attachment file '{filename}' not found for ticket {ticket_key}.
Expected location: {file_path}

Did you download the attachments first? Use get_ticket_attachments('{ticket_key}') to download.
Note: If you're working in a different project directory, attachments are stored in:
{config.attachments_base_dir}

You can customize this location by setting the MCP_ATTACHMENTS_PATH environment variable."""
    
    # Check file size
    file_size = os.path.getsize(file_path)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
    if file_size > MAX_FILE_SIZE:
        logger.error(f"Attachment file too large: {file_path} ({file_size} bytes)")
        return f"Error: Attachment file '{filename}' is too large ({file_size} bytes) to analyze. Maximum size allowed is {MAX_FILE_SIZE} bytes."
    
    # Determine file type and read content accordingly
    content = ""
    file_ext = os.path.splitext(filename)[1].lower()
    
    try:
        if file_ext in TEXT_FILE_EXTENSIONS:
            # Text file
            content = read_text_file(file_path)
        elif file_ext == '.pdf':
            # PDF file
            if not config.pdf_support:
                return "Error: PDF processing is not available. Please install PyPDF2 to analyze PDF attachments."
            
            content = extract_text_from_pdf(file_path)
        else:
            return f"Error: Unsupported file type '{file_ext}'. Currently only text files and PDFs are supported."
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return f"Error reading file: {str(e)}"
    
    # Construct the prompt for Ollama
    if question:
        prompt = f"Please analyze the following file and answer this question: {question}\n\nFile content:\n\n{content}"
        system_message = "You are a helpful assistant specialized in analyzing document contents. Answer the question specifically based on the file content provided."
    else:
        prompt = f"Please analyze the following file and provide key insights:\n\n{content}"
        system_message = "You are a helpful assistant specialized in analyzing document contents. Summarize the key points and important information in the provided file."
    
    # Send to Ollama
    try:
        analysis = ask_ollama(prompt, system_message)
        if analysis and not analysis.startswith("Error"):
            return f"Analysis of attachment '{filename}' from {ticket_key}:\n\n{analysis}"
        else:
            logger.error(f"Failed to get analysis from Ollama: {analysis}")
            return f"Could not analyze attachment '{filename}' using Ollama. Please try again later."
    except Exception as e:
        logger.error(f"Error analyzing attachment: {str(e)}")
        return f"Error analyzing attachment: {str(e)}"

def analyze_all_attachments(ticket_key: str, question: str = None) -> str:
    """Analyze all attachments from a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: Optional specific question about the attachments
    """
    logger.info(f"Tool called: analyze_all_attachments for {ticket_key}")
    
    # Security: Validate ticket key format to prevent path traversal
    if not validate_ticket_key(ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Build the path to the attachments directory
    attachments_dir = os.path.join(config.attachments_base_dir, ticket_key)
    
    # If attachments directory doesn't exist, download them first
    if not os.path.exists(attachments_dir):
        logger.info(f"Attachments directory not found for {ticket_key}, attempting to download")
        logger.info(f"Looking for directory: {attachments_dir}")
        download_result = get_ticket_attachments(ticket_key)
        if download_result.startswith("Error"):
            return f"Could not analyze attachments: {download_result}"
        
        # Check again after download attempt
        if not os.path.exists(attachments_dir):
            return f"""Error: Could not find or create attachments directory for {ticket_key}
Expected location: {attachments_dir}

Note: If you're working in a different project directory, attachments are stored in:
{config.attachments_base_dir}

You can customize this location by setting the MCP_ATTACHMENTS_PATH environment variable."""
    
    # Get list of files in the directory
    try:
        files = os.listdir(attachments_dir)
        # Security check - don't process more than a reasonable number of files at once
        MAX_FILES = 20
        if len(files) > MAX_FILES:
            logger.warning(f"Too many files in {ticket_key} attachment directory: {len(files)}")
            return f"Error: Too many attachments ({len(files)}) found for ticket {ticket_key}. Maximum of {MAX_FILES} files can be processed at once."
    except Exception as e:
        logger.error(f"Error listing attachments directory: {str(e)}")
        return f"Error listing attachments: {str(e)}"
    
    if not files:
        return f"No attachments found for ticket {ticket_key}."
    
    # Define supported file types
    supported_extensions = TEXT_FILE_EXTENSIONS.copy()
    
    # Add PDF if support is available
    if config.pdf_support:
        supported_extensions.append('.pdf')
    
    # Filter to only supported files
    supported_files = [f for f in files if os.path.splitext(f)[1].lower() in supported_extensions]
    
    if not supported_files:
        if config.pdf_support:
            return f"No supported attachments found for ticket {ticket_key}. Only text files and PDFs are supported."
        else:
            return f"No supported attachments found for ticket {ticket_key}. Only text files are supported (PDF support not available)."
    
    # Analyze each supported attachment
    analyses = []
    for filename in supported_files:
        logger.info(f"Analyzing attachment: {filename}")
        analysis = analyze_attachment(ticket_key, filename, question)
        
        # Add the analysis result
        analyses.append(f"--- {filename} ---\n{analysis}\n")
    
    # Combine all analyses
    if analyses:
        combined = "\n".join(analyses)
        return f"Analysis of all attachments for {ticket_key}:\n\n{combined}"
    else:
        return f"Could not generate analysis for any attachments in ticket {ticket_key}."

def cleanup_attachments(ticket_key: str = None) -> str:
    """Delete downloaded attachments for a specific ticket or all tickets.
    
    Args:
        ticket_key: Optional Jira ticket key (e.g., PROJ-1234). If not provided, will clean up all attachments.
    """
    logger.info(f"Tool called: cleanup_attachments for {ticket_key if ticket_key else 'all tickets'}")
    
    # Use the base attachments directory
    attachments_base_dir = config.attachments_base_dir
    
    # Create directory if it doesn't exist (though this shouldn't happen)
    if not os.path.exists(attachments_base_dir):
        return f"No attachments directory found at {attachments_base_dir}. Nothing to clean up."
    
    # Security: Make sure attachments_base_dir is a subdirectory of the script directory
    # or a custom directory specified by environment variable to prevent traversal attacks
    # This is a defense-in-depth measure in case ATTACHMENTS_BASE_DIR is compromised
    expected_base_dirs = [os.path.join(config.script_dir, "attachments")]
    if 'MCP_ATTACHMENTS_PATH' in os.environ:
        expected_base_dirs.append(os.environ['MCP_ATTACHMENTS_PATH'])
    
    if not validate_path_safety(attachments_base_dir, expected_base_dirs):
        logger.error(f"Security alert: Attempted to clean up directory outside allowed paths: {attachments_base_dir}")
        return f"Error: Security restriction. Cannot clean up directory outside of expected paths."
    
    if ticket_key:
        # Security validation for ticket_key format
        if not validate_ticket_key(ticket_key):
            return f"Error: Invalid ticket key format: {ticket_key}"
        
        # Delete attachments for a specific ticket
        ticket_dir = os.path.join(attachments_base_dir, ticket_key)
        if not os.path.exists(ticket_dir):
            return f"No attachments found for ticket {ticket_key} at {ticket_dir}. Nothing to clean up."
        
        try:
            # Count files before deletion
            file_count = sum(1 for _ in os.listdir(ticket_dir) if os.path.isfile(os.path.join(ticket_dir, _)))
            
            # Delete the directory
            shutil.rmtree(ticket_dir)
            
            return f"Successfully deleted {file_count} attachment(s) for ticket {ticket_key} from {ticket_dir}."
        except Exception as e:
            logger.error(f"Error deleting attachments for {ticket_key}: {str(e)}")
            return f"Error deleting attachments for ticket {ticket_key}: {str(e)}"
    else:
        # Delete all attachments
        try:
            # Count total files and tickets before deletion
            total_files = 0
            ticket_count = 0
            
            # List all ticket directories
            ticket_dirs = os.listdir(attachments_base_dir)
            for ticket_dir in ticket_dirs:
                ticket_path = os.path.join(attachments_base_dir, ticket_dir)
                if os.path.isdir(ticket_path):
                    ticket_count += 1
                    # Count files in this ticket's directory
                    file_count = sum(1 for _ in os.listdir(ticket_path) if os.path.isfile(os.path.join(ticket_path, _)))
                    total_files += file_count
                    
                    # Delete the ticket directory
                    shutil.rmtree(ticket_path)
            
            if ticket_count > 0:
                return f"Successfully deleted {total_files} attachment(s) from {ticket_count} ticket(s) in {attachments_base_dir}."
            else:
                return f"No ticket attachments found in {attachments_base_dir}. Nothing to clean up."
        except Exception as e:
            logger.error(f"Error deleting all attachments: {str(e)}")
            return f"Error deleting all attachments: {str(e)}" 