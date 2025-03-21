#!/usr/bin/env python3
"""
Jira MCP Server that uses local Ollama instead of Claude
"""
import os
import logging
import json
import httpx
import re
from dotenv import load_dotenv
from jira import JIRA
from mcp.server.fastmcp import FastMCP
import io
import tempfile
import pathlib
from datetime import datetime
import shutil

# Configure logging first, before any functions use it
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='jira_ollama_mcp.log',
    filemode='w'
)
logger = logging.getLogger("jira-ollama")

# Function to get the MCP base path regardless of working directory
def get_mcp_base_path():
    """Returns the base path for MCP resources regardless of working directory"""
    # First check for environment variable with fallback
    if 'MCP_BASE_PATH' in os.environ:
        base_path = os.environ['MCP_BASE_PATH']
        logger.info(f"Using MCP_BASE_PATH from environment: {base_path}")
        return base_path
    
    # Use the script's directory as a fallback
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Using script directory for MCP_BASE_PATH: {script_dir}")
    return script_dir

# Define a constant for the attachments directory
ATTACHMENTS_BASE_DIR = os.path.join(get_mcp_base_path(), "attachments")

# Ensure the base attachments directory exists
os.makedirs(ATTACHMENTS_BASE_DIR, exist_ok=True)
logger.info(f"Attachments directory set to: {ATTACHMENTS_BASE_DIR}")

# Check if the PDF libraries are available
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Load environment variables from the .env file
load_dotenv()

# Create server with the same name that worked in the ultra minimal version
mcp = FastMCP("jira")

# Load Jira configurations
# Primary Jira 
primary_jira_host = os.getenv('PRIMARY_JIRA_HOST')
primary_jira_pat = os.getenv('PRIMARY_JIRA_PAT')
primary_jira_username = os.getenv('PRIMARY_JIRA_USERNAME')
primary_jira_password = os.getenv('PRIMARY_JIRA_PASSWORD')

# Secondary Jira
secondary_jira_host = os.getenv('SECONDARY_JIRA_HOST')
secondary_jira_pat = os.getenv('SECONDARY_JIRA_PAT')

# Backward compatibility - Nokia Jira
nokia_jira_host = os.getenv('NOKIA_JIRA_HOST', primary_jira_host)
nokia_jira_pat = os.getenv('NOKIA_JIRA_PAT', primary_jira_pat)
nokia_jira_username = os.getenv('NOKIA_JIRA_USERNAME', primary_jira_username)
nokia_jira_password = os.getenv('NOKIA_JIRA_PASSWORD', primary_jira_password)

# Backward compatibility - Red Hat Jira
redhat_jira_host = os.getenv('REDHAT_JIRA_HOST', secondary_jira_host)
redhat_jira_pat = os.getenv('REDHAT_JIRA_PAT', secondary_jira_pat)

# Legacy configuration (for backward compatibility)
jira_host = os.getenv('JIRA_HOST', primary_jira_host)
jira_pat = os.getenv('JIRA_PAT', primary_jira_pat)
jira_username = os.getenv('JIRA_USERNAME', primary_jira_username)
jira_password = os.getenv('JIRA_PASSWORD', primary_jira_password)

# Project prefixes for Secondary Jira (for determining which Jira to use)
secondary_project_prefixes = os.getenv('SECONDARY_PROJECT_PREFIXES', 'CNV').split(',')
# Backward compatibility
redhat_project_prefixes = os.getenv('REDHAT_PROJECT_PREFIXES', secondary_project_prefixes)
if isinstance(redhat_project_prefixes, str):
    redhat_project_prefixes = redhat_project_prefixes.split(',')

# Ollama configuration
ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11435')
ollama_model = os.getenv('OLLAMA_MODEL', 'deepseek-r1:14b-qwen-distill-q8_0')
ollama_temperature = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
ollama_context_length = int(os.getenv('OLLAMA_CONTEXT_LENGTH', '32768'))
logger.info(f"Will use Ollama at {ollama_base_url} with model {ollama_model}")
logger.info(f"Ollama parameters: temperature={ollama_temperature}, context_length={ollama_context_length}")

# Initialize Jira clients
nokia_jira = None
redhat_jira = None
primary_jira = None
secondary_jira = None
jira = None  # Default client for backward compatibility

# Helper function to determine which Jira instance to use based on ticket key
def get_jira_client(ticket_key):
    """
    Determine which Jira client to use based on ticket key prefix.
    If the prefix matches a Secondary Jira project, use Secondary Jira.
    Otherwise, use Primary Jira.
    """
    if not ticket_key:
        return None
    
    # Extract project prefix (e.g., "CNV" from "CNV-12345")
    match = re.match(r'^([A-Z]+)-\d+', ticket_key)
    if not match:
        logger.warning(f"Invalid ticket key format: {ticket_key}")
        return primary_jira  # Default to Primary Jira
    
    project_prefix = match.group(1)
    
    # Check if this is a Secondary Jira project
    if project_prefix in secondary_project_prefixes or project_prefix in redhat_project_prefixes:
        logger.info(f"Using Secondary Jira for ticket {ticket_key}")
        return secondary_jira
    else:
        logger.info(f"Using Primary Jira for ticket {ticket_key}")
        return primary_jira

# Initialize Primary Jira
try:
    if primary_jira_pat:
        # Use PAT authentication
        logger.info("Initializing Primary Jira with PAT authentication")
        logger.info(f"Primary Jira host: {primary_jira_host}")
        logger.debug(f"Primary Jira PAT length: {len(primary_jira_pat) if primary_jira_pat else 0}")
        primary_jira = JIRA(
            server=f"https://{primary_jira_host}",
            token_auth=primary_jira_pat
        )
    elif primary_jira_username and primary_jira_password:
        # Fall back to basic authentication
        logger.info("Initializing Primary Jira with basic authentication")
        primary_jira = JIRA(
            server=f"https://{primary_jira_host}",
            basic_auth=(primary_jira_username, primary_jira_password)
        )
    
    if primary_jira:
        # Test connection
        myself = primary_jira.myself()
        logger.info(f"Connected to Primary Jira: {primary_jira_host} as {myself['displayName']} ({myself['name']})")
        
        # Set up for backward compatibility
        nokia_jira = primary_jira
except Exception as e:
    logger.error(f"Error connecting to Primary Jira: {str(e)}")
    primary_jira = None
    nokia_jira = None

# Initialize Secondary Jira
try:
    if secondary_jira_pat:
        # Use PAT authentication for Secondary Jira
        logger.info("Initializing Secondary Jira with PAT authentication")
        logger.info(f"Secondary Jira host: {secondary_jira_host}")
        logger.debug(f"Secondary Jira PAT length: {len(secondary_jira_pat) if secondary_jira_pat else 0}")
        secondary_jira = JIRA(
            server=f"https://{secondary_jira_host}",
            token_auth=secondary_jira_pat
        )
        # Test connection
        myself = secondary_jira.myself()
        logger.info(f"Connected to Secondary Jira: {secondary_jira_host} as {myself['displayName']} ({myself['name']})")
        
        # Set up for backward compatibility
        redhat_jira = secondary_jira
except Exception as e:
    logger.error(f"Error connecting to Secondary Jira: {str(e)}")
    secondary_jira = None
    redhat_jira = None

# Set default Jira client for backward compatibility
jira = primary_jira or nokia_jira

# Log summary status message
if not primary_jira and not secondary_jira:
    logger.warning("Not connected to any Jira instance. Check your credentials and network connection.")

# Function to call Ollama
def ask_ollama(prompt, system_message=None):
    """Send a prompt to Ollama and get a response."""
    try:
        # Create the request data
        data = {
            "model": ollama_model,
            "prompt": prompt,
            "system": system_message if system_message else "",
            "stream": False,  # We want a complete response, not streaming
            "raw": False,     # We want a processed response, not raw output
            "temperature": ollama_temperature,
            "context_length": ollama_context_length
        }
        
        logger.info(f"Sending prompt to Ollama: {prompt[:100]}...")
        
        # Make synchronous request to Ollama
        response = httpx.post(
            f"{ollama_base_url}/api/generate",
            json=data,
            timeout=60.0
        )
        
        # Log the raw response for debugging
        logger.debug(f"Raw Ollama response: {response.text[:500]}...")
        
        if response.status_code == 200:
            try:
                # Try to parse the response as JSON
                result = response.json()
                logger.info("Received response from Ollama")
                
                # Check for different response formats
                if isinstance(result, dict):
                    # The /api/generate endpoint returns a response field
                    if "response" in result:
                        return result["response"]
                    # Fallback to message format if using /api/chat
                    elif "message" in result and isinstance(result["message"], dict):
                        return result["message"].get("content", "No content in response")
                    else:
                        # Return the first string value we find
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 10:
                                return value
                
                # If we're here, we didn't find a good response format, log the full structure
                logger.warning(f"Unexpected Ollama response structure: {result}")
                return str(result)
            except json.JSONDecodeError as je:
                logger.error(f"JSON parsing error: {str(je)}")
                # Try to salvage a response from the text
                raw_text = response.text
                
                # Look for a meaningful text in the response
                if len(raw_text) > 10:
                    # Try to extract just text content if there's JSON-like structure
                    if '"content":' in raw_text:
                        try:
                            start_idx = raw_text.find('"content":') + 11
                            end_idx = raw_text.find('",', start_idx)
                            if end_idx > start_idx:
                                return raw_text[start_idx:end_idx]
                        except:
                            pass
                    
                    # Return the raw text if it's not too long
                    if len(raw_text) < 5000:
                        return f"Raw response (JSON parsing failed): {raw_text}"
                
                return f"Error parsing Ollama response: {str(je)}"
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return f"Error from Ollama API: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        return f"Error calling Ollama: {str(e)}"

@mcp.tool()
def get_my_tickets() -> str:
    """Get all tickets assigned to the current user."""
    logger.info("Tool called: get_my_tickets")
    
    results = []
    
    # Check Nokia Jira
    if nokia_jira:
        try:
            # Use the authenticated user's username for the query
            current_user = nokia_jira.myself()['name']
            jql = f'assignee = "{current_user}"'
            issues = nokia_jira.search_issues(jql)
            
            if issues:
                results.append("Your assigned tickets in Nokia Jira:")
                for issue in issues:
                    results.append(f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})")
                results.append("")  # Empty line for separation
        except Exception as e:
            logger.error(f"Error retrieving Nokia Jira tickets: {str(e)}")
            results.append(f"Error retrieving Nokia Jira tickets: {str(e)}")
    else:
        results.append("Not connected to Nokia Jira")
    
    # Check Red Hat Jira
    if redhat_jira:
        try:
            # Use the authenticated user's username for the query
            current_user = redhat_jira.myself()['name']
            jql = f'assignee = "{current_user}"'
            issues = redhat_jira.search_issues(jql)
            
            if issues:
                results.append("Your assigned tickets in Red Hat Jira:")
                for issue in issues:
                    results.append(f"- {issue.key}: {issue.fields.summary} ({issue.fields.status.name})")
                results.append("")  # Empty line for separation
        except Exception as e:
            logger.error(f"Error retrieving Red Hat Jira tickets: {str(e)}")
            results.append(f"Error retrieving Red Hat Jira tickets: {str(e)}")
    else:
        results.append("Not connected to Red Hat Jira")
    
    if not results:
        return "Error: Not connected to any Jira instance"
    
    return "\n".join(results)

@mcp.tool()
def get_ticket_details(ticket_key: str) -> str:
    """Get detailed information about a specific ticket.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: get_ticket_details for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get the issue details
        issue = jira_client.issue(ticket_key)
        
        # Basic information
        details = f"""
Ticket: {ticket_key}
Summary: {issue.fields.summary}
Status: {issue.fields.status.name}
Priority: {issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else 'Not set'}
Assignee: {issue.fields.assignee.displayName if hasattr(issue.fields, 'assignee') and issue.fields.assignee else 'Unassigned'}
Reporter: {issue.fields.reporter.displayName if hasattr(issue.fields, 'reporter') and issue.fields.reporter else 'Unknown'}
Created: {issue.fields.created}
Updated: {issue.fields.updated}

Description:
{issue.fields.description if issue.fields.description else 'No description provided'}
"""
        
        # Get comments (simplified approach)
        try:
            comments = jira_client.comments(issue)
            if comments:
                details += f"\nComments ({len(comments)}):\n"
                # Show only first 3 comments to keep response size manageable
                for i, comment in enumerate(comments[:3]):
                    details += f"\n--- Comment by {comment.author.displayName} on {comment.created} ---\n{comment.body}\n"
                
                # Add note if we're truncating
                if len(comments) > 3:
                    details += f"\n[...{len(comments) - 3} more comments not shown...]\n"
            else:
                details += "\nNo comments on this ticket."
        except Exception as comment_error:
            logger.error(f"Error retrieving comments: {str(comment_error)}")
            details += f"\nError retrieving comments: {str(comment_error)}"
        
        return details
    except Exception as e:
        logger.error(f"Error retrieving ticket details: {str(e)}")
        return f"Error retrieving ticket details: {str(e)}"

@mcp.tool()
def summarize_ticket(ticket_key: str) -> str:
    """Summarize a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: summarize_ticket for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # First get the ticket details
        ticket_details = get_ticket_details(ticket_key)
        if ticket_details.startswith("Error"):
            return f"Cannot summarize ticket: {ticket_details}"
        
        # Then ask Ollama to summarize it
        logger.info(f"Sending {ticket_key} to Ollama for summarization")
        prompt = f"Please summarize this Jira ticket in a concise way, focusing on the main issue and solution if available:\n\n{ticket_details}"
        system_message = "You are a helpful assistant specialized in summarizing Jira tickets. Keep your response concise and focus on the most important information."
        
        summary = ask_ollama(prompt, system_message)
        if summary and not summary.startswith("Error"):
            return f"Summary of {ticket_key}:\n\n{summary}"
        else:
            logger.error(f"Failed to get summary from Ollama: {summary}")
            return f"Could not generate summary using Ollama. Using built-in summary instead:\n\nTicket {ticket_key} concerns: '{jira_client.issue(ticket_key).fields.summary}'"
    except Exception as e:
        logger.error(f"Error summarizing ticket: {str(e)}")
        return f"Error summarizing ticket: {str(e)}"

@mcp.tool()
def analyze_ticket(ticket_key: str, question: str) -> str:
    """Analyze a Jira ticket by asking a specific question about it.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: A specific question about the ticket
    """
    logger.info(f"Tool called: analyze_ticket for {ticket_key} with question: {question}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # First get the ticket details
        ticket_details = get_ticket_details(ticket_key)
        if ticket_details.startswith("Error"):
            return f"Cannot analyze ticket: {ticket_details}"
        
        # Then ask Ollama to analyze it
        logger.info(f"Sending {ticket_key} to Ollama for analysis of question: {question}")
        prompt = f"Please answer the following question about this Jira ticket:\n\nQuestion: {question}\n\nTicket details:\n{ticket_details}"
        system_message = "You are a helpful assistant specialized in analyzing Jira tickets. Provide specific, accurate answers based only on the information in the ticket."
        
        analysis = ask_ollama(prompt, system_message)
        if analysis and not analysis.startswith("Error"):
            return f"Analysis of {ticket_key} regarding '{question}':\n\n{analysis}"
        else:
            logger.error(f"Failed to get analysis from Ollama: {analysis}")
            # Provide a basic response without Ollama
            try:
                ticket = jira_client.issue(ticket_key)
                return f"Ollama analysis failed. Basic information about {ticket_key}:\n\nSummary: {ticket.fields.summary}\nStatus: {ticket.fields.status.name}\nAssignee: {ticket.fields.assignee.displayName if hasattr(ticket.fields, 'assignee') and ticket.fields.assignee else 'Unassigned'}"
            except:
                return f"Ollama analysis failed and could not retrieve basic ticket information. Please check the ticket manually."
    except Exception as e:
        logger.error(f"Error analyzing ticket: {str(e)}")
        return f"Error analyzing ticket: {str(e)}"

@mcp.tool()
def get_ticket_attachments(ticket_key: str) -> str:
    """Fetch and download all attachments from a Jira ticket to a local directory.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
    """
    logger.info(f"Tool called: get_ticket_attachments for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get the issue
        issue = jira_client.issue(ticket_key)
        
        # Check if there are any attachments
        if not hasattr(issue.fields, 'attachment') or not issue.fields.attachment:
            return f"No attachments found for ticket {ticket_key}"
        
        # Create directory for attachments if it doesn't exist
        attachments_dir = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key)
        os.makedirs(attachments_dir, exist_ok=True)
        
        # Download each attachment
        downloaded_files = []
        for attachment in issue.fields.attachment:
            # Get the attachment data
            attachment_data = attachment.get()
            
            # Clean the filename to avoid any path traversal issues
            safe_filename = os.path.basename(attachment.filename)
            file_path = os.path.join(attachments_dir, safe_filename)
            
            # Save the attachment
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
            support_msg = "PDF files are also supported." if PDF_SUPPORT else "Install PyPDF2 to enable PDF support."
            return f"Downloaded {len(downloaded_files)} attachment(s) from ticket {ticket_key} to the 'attachments/{ticket_key}' directory. {support_msg}"
        else:
            return f"No attachments found for ticket {ticket_key}."
    
    except Exception as e:
        logger.error(f"Error downloading attachments: {str(e)}")
        return f"Error downloading attachments from ticket {ticket_key}: {str(e)}"

# Helper function to extract text from PDF files
def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file."""
    if not PDF_SUPPORT:
        return "PDF extraction is not available. Install PyPDF2 package to enable this feature."
    
    try:
        text = ""
        with open(pdf_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text() or "No text content on this page."
        
        return text if text.strip() else "No extractable text content found in the PDF."
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return f"Error extracting text from PDF: {str(e)}"

@mcp.tool()
def analyze_attachment(ticket_key: str, filename: str, question: str = None) -> str:
    """Analyze a specific attachment from a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        filename: The name of the attachment file to analyze
        question: Optional specific question about the attachment
    """
    logger.info(f"Tool called: analyze_attachment for {ticket_key}, file: {filename}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Construct the path to the attachment
    attachments_dir = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key)
    file_path = os.path.join(attachments_dir, os.path.basename(filename))
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return f"Error: Attachment '{filename}' not found for ticket {ticket_key}. Please run get_ticket_attachments first."
    
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return f"Error: File is too large ({file_size / 1024 / 1024:.1f} MB) for analysis. Maximum size is 10MB."
        
        # Read file content
        file_extension = os.path.splitext(filename)[1].lower()
        file_content = None
        
        # Handle different file types
        try:
            # Handle text files
            if file_extension in ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.ts', '.yml', '.yaml']:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    file_content = f.read()
            # Handle PDF files
            elif file_extension == '.pdf' and PDF_SUPPORT:
                file_content = extract_text_from_pdf(file_path)
            # Handle binary files (could be extended with more formats)
            else:
                return f"The file type '{file_extension}' is not currently supported for content analysis. Supported types include text files and PDFs (if PyPDF2 is installed)."
        except Exception as read_error:
            logger.error(f"Error reading file: {str(read_error)}")
            return f"Error reading file '{filename}': {str(read_error)}"
        
        if not file_content:
            return f"Could not extract content from file '{filename}'"
        
        # Construct prompt based on whether a question was provided
        if question:
            prompt = f"Please analyze this file content from ticket {ticket_key} and answer the following question:\n\nQuestion: {question}\n\nFile: {filename}\n\nContent:\n{file_content[:100000]}"  # Limit content length
            system_message = "You are a helpful assistant specialized in analyzing document contents. Answer the specific question based only on the information in the document."
        else:
            prompt = f"Please analyze this file content from ticket {ticket_key} and provide a summary of its key points or structure:\n\nFile: {filename}\n\nContent:\n{file_content[:100000]}"  # Limit content length
            system_message = "You are a helpful assistant specialized in analyzing document contents. Provide a concise summary of the key information in the document."
        
        # Send to Ollama for analysis
        logger.info(f"Sending attachment from {ticket_key} to Ollama for analysis")
        analysis = ask_ollama(prompt, system_message)
        
        if analysis and not analysis.startswith("Error"):
            if question:
                return f"Analysis of '{filename}' from ticket {ticket_key} regarding '{question}':\n\n{analysis}"
            else:
                return f"Analysis of '{filename}' from ticket {ticket_key}:\n\n{analysis}"
        else:
            logger.error(f"Failed to get analysis from Ollama: {analysis}")
            return f"Could not generate analysis using Ollama for file '{filename}'"
    
    except Exception as e:
        logger.error(f"Error analyzing attachment: {str(e)}")
        return f"Error analyzing attachment '{filename}' from ticket {ticket_key}: {str(e)}"

@mcp.tool()
def analyze_all_attachments(ticket_key: str, question: str = None) -> str:
    """Analyze all attachments from a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: Optional specific question about the attachments
    """
    logger.info(f"Tool called: analyze_all_attachments for {ticket_key}")
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Check if attachments are already downloaded
    attachments_dir = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key)
    if not os.path.exists(attachments_dir) or not os.listdir(attachments_dir):
        # Download attachments if not already present
        download_result = get_ticket_attachments(ticket_key)
        if download_result.startswith("Error") or download_result.startswith("No attachments"):
            return download_result
    
    # Get list of all files in the directory
    attachments = []
    for filename in os.listdir(attachments_dir):
        file_path = os.path.join(attachments_dir, filename)
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(filename)[1].lower()
            # Include supported file types
            if file_ext in ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.ts', '.yml', '.yaml']:
                attachments.append({
                    'filename': filename,
                    'path': file_path,
                    'extension': file_ext,
                    'is_pdf': False
                })
            elif file_ext == '.pdf' and PDF_SUPPORT:
                attachments.append({
                    'filename': filename,
                    'path': file_path,
                    'extension': file_ext,
                    'is_pdf': True
                })
    
    if not attachments:
        support_msg = "PDF files are also supported." if PDF_SUPPORT else "Install PyPDF2 to enable PDF support."
        return f"No supported attachments found for ticket {ticket_key}. Only text-based files are currently supported. {support_msg}"
    
    # Analyze each supported attachment
    results = []
    for attachment in attachments:
        logger.info(f"Analyzing attachment: {attachment['filename']}")
        try:
            # Read file content based on type
            if attachment['is_pdf']:
                file_content = extract_text_from_pdf(attachment['path'])
            else:
                with open(attachment['path'], 'r', encoding='utf-8', errors='replace') as f:
                    file_content = f.read()
            
            # Prepare summary info about the file
            file_size = os.path.getsize(attachment['path'])
            size_kb = file_size / 1024
            file_summary = f"File: {attachment['filename']} ({size_kb:.1f} KB)"
            
            # Create a prompt based on the file
            if question:
                prompt = f"Please analyze this file content from ticket {ticket_key} and answer the following question:\n\nQuestion: {question}\n\n{file_summary}\n\nContent:\n{file_content[:50000]}"  # Limit content length
                system_message = "You are a helpful assistant specialized in analyzing document contents. Answer the specific question based only on the information in the document. Be concise."
            else:
                prompt = f"Please analyze this file content from ticket {ticket_key} and provide a brief summary of its key points:\n\n{file_summary}\n\nContent:\n{file_content[:50000]}"  # Limit content length
                system_message = "You are a helpful assistant specialized in analyzing document contents. Provide a very concise summary (3-5 sentences) of the key information in the document."
            
            # Send to Ollama for analysis
            analysis = ask_ollama(prompt, system_message)
            
            if analysis and not analysis.startswith("Error"):
                results.append({
                    'filename': attachment['filename'],
                    'analysis': analysis
                })
            else:
                results.append({
                    'filename': attachment['filename'],
                    'analysis': "Analysis failed: Could not process with Ollama"
                })
        except Exception as e:
            logger.error(f"Error analyzing attachment {attachment['filename']}: {str(e)}")
            results.append({
                'filename': attachment['filename'],
                'analysis': f"Analysis failed: {str(e)}"
            })
    
    # Compile the results
    if results:
        # Decide on final response format
        if question:
            # If a question was asked, compile a final answer
            combined_prompt = f"I have analyzed {len(results)} attachments from ticket {ticket_key} regarding the question: '{question}'. Here are the individual analyses:\n\n"
            for result in results:
                combined_prompt += f"=== {result['filename']} ===\n{result['analysis']}\n\n"
            combined_prompt += f"Based on ALL the above analyses, provide a comprehensive answer to the question: '{question}'"
            
            system_message = "You are a helpful assistant that synthesizes information from multiple documents. Provide a concise, comprehensive answer to the question based on all the document analyses."
            final_answer = ask_ollama(combined_prompt, system_message)
            
            response = f"Analysis of all attachments from ticket {ticket_key} regarding '{question}':\n\n{final_answer}\n\n"
            response += "--- Individual file analyses ---\n"
            for result in results:
                response += f"\n=== {result['filename']} ===\n{result['analysis']}\n"
            
            return response
        else:
            # Just provide individual summaries
            response = f"Analysis of {len(results)} attachments from ticket {ticket_key}:\n\n"
            for result in results:
                response += f"=== {result['filename']} ===\n{result['analysis']}\n\n"
            
            return response
    else:
        return f"Could not analyze any attachments from ticket {ticket_key}"

@mcp.tool()
def cleanup_attachments(ticket_key: str = None) -> str:
    """Delete downloaded attachments for a specific ticket or all tickets.
    
    Args:
        ticket_key: Optional Jira ticket key (e.g., PROJ-1234). If not provided, will clean up all attachments.
    """
    logger.info(f"Tool called: cleanup_attachments for {ticket_key if ticket_key else 'all tickets'}")
    
    # Use the base attachments directory
    attachments_base_dir = ATTACHMENTS_BASE_DIR
    
    # Create directory if it doesn't exist (though this shouldn't happen)
    if not os.path.exists(attachments_base_dir):
        return "No attachments directory found. Nothing to clean up."
    
    if ticket_key:
        # Delete attachments for a specific ticket
        ticket_dir = os.path.join(attachments_base_dir, ticket_key)
        if not os.path.exists(ticket_dir):
            return f"No attachments found for ticket {ticket_key}. Nothing to clean up."
        
        try:
            # Count the number of files before deletion
            file_count = sum(1 for _ in os.listdir(ticket_dir) if os.path.isfile(os.path.join(ticket_dir, _)))
            
            # Delete the directory and all its contents
            shutil.rmtree(ticket_dir)
            return f"Successfully deleted {file_count} attachment(s) for ticket {ticket_key}."
        except Exception as e:
            logger.error(f"Error cleaning up attachments for ticket {ticket_key}: {str(e)}")
            return f"Error cleaning up attachments for ticket {ticket_key}: {str(e)}"
    else:
        # Delete all attachments
        try:
            # Count tickets and files before deletion
            ticket_count = 0
            file_count = 0
            
            for item in os.listdir(attachments_base_dir):
                item_path = os.path.join(attachments_base_dir, item)
                if os.path.isdir(item_path):
                    ticket_count += 1
                    file_count += sum(1 for _ in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, _)))
            
            # If there's nothing to delete
            if ticket_count == 0:
                return "No attachments found. Nothing to clean up."
            
            # Delete all contents but keep the base directory
            for item in os.listdir(attachments_base_dir):
                item_path = os.path.join(attachments_base_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            return f"Successfully deleted {file_count} attachment(s) from {ticket_count} ticket(s)."
        except Exception as e:
            logger.error(f"Error cleaning up all attachments: {str(e)}")
            return f"Error cleaning up all attachments: {str(e)}"

def main():
    """
    Main entry point for the Jira Ollama MCP server.
    """
    logger.info("Starting Jira Ollama MCP server...")
    
    try:
        # Run the server
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main() 