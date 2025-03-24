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
import hashlib
import time
from functools import lru_cache

# Configure logging first, before any functions use it
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='jira_ollama_mcp.log',
    filemode='w'
)
logger = logging.getLogger("jira-ollama")

# Load environment variables from the .env file
load_dotenv()

# Get script directory (used as default location for attachments)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set up attachments directory - either from environment variable or default location
ATTACHMENTS_BASE_DIR = os.getenv('MCP_ATTACHMENTS_PATH', os.path.join(SCRIPT_DIR, "attachments"))

# Ensure the attachments directory exists
os.makedirs(ATTACHMENTS_BASE_DIR, exist_ok=True)
logger.info(f"Attachments directory set to: {ATTACHMENTS_BASE_DIR}")

# Check if the PDF libraries are available
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

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
ollama_timeout = float(os.getenv('OLLAMA_TIMEOUT', '120.0'))  # Default timeout of 2 minutes
logger.info(f"Will use Ollama at {ollama_base_url} with model {ollama_model}")
logger.info(f"Ollama parameters: temperature={ollama_temperature}, context_length={ollama_context_length}, timeout={ollama_timeout}s")

# Initialize Jira clients
nokia_jira = None
redhat_jira = None
primary_jira = None
secondary_jira = None
jira = None  # Default client for backward compatibility

# Simple memory cache for Ollama responses
ollama_cache = {}
OLLAMA_CACHE_SIZE = int(os.getenv('OLLAMA_CACHE_SIZE', '50'))  # Maximum cache entries
OLLAMA_CACHE_TTL = int(os.getenv('OLLAMA_CACHE_TTL', '3600'))  # Time to live in seconds (1 hour default)
logger.info(f"Ollama cache configured: size={OLLAMA_CACHE_SIZE}, TTL={OLLAMA_CACHE_TTL}s")

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
    
    # Generate a cache key from the prompt and system message
    cache_key = hashlib.md5((prompt + (system_message or "")).encode()).hexdigest()
    
    # Check if we have a cached response and it's still valid
    if cache_key in ollama_cache:
        timestamp, cached_response = ollama_cache[cache_key]
        if time.time() - timestamp < OLLAMA_CACHE_TTL:
            logger.info(f"Using cached Ollama response for prompt: {prompt[:50]}...")
            return cached_response
        else:
            # Expired, remove from cache
            del ollama_cache[cache_key]
            logger.debug(f"Removed expired cache entry for key: {cache_key}")
    
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
        
        # Make synchronous request to Ollama with timeout
        response = httpx.post(
            f"{ollama_base_url}/api/generate",
            json=data,
            timeout=ollama_timeout  # Use configured timeout
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
                        response_text = result["response"]
                    # Fallback to message format if using /api/chat
                    elif "message" in result and isinstance(result["message"], dict):
                        response_text = result["message"].get("content", "No content in response")
                    else:
                        # Return the first string value we find
                        response_text = None
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 10:
                                response_text = value
                                break
                        if response_text is None:
                            # If we're here, we didn't find a good response format, log the full structure
                            logger.warning(f"Unexpected Ollama response structure: {result}")
                            response_text = str(result)
                else:
                    response_text = str(result)
                
                # Cache the response
                if len(ollama_cache) >= OLLAMA_CACHE_SIZE:
                    # Remove oldest entry if cache is full
                    oldest_key = min(ollama_cache.keys(), key=lambda k: ollama_cache[k][0])
                    del ollama_cache[oldest_key]
                    logger.debug(f"Removed oldest cache entry for key: {oldest_key}")
                
                ollama_cache[cache_key] = (time.time(), response_text)
                logger.debug(f"Added new cache entry for key: {cache_key}")
                
                return response_text
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
        # Directly get the ticket details without circular import
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
        # Directly get the ticket details without circular import
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
    
    # Security: Validate ticket key format to prevent path traversal
    if not re.match(r'^[A-Z]+-\d+$', ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    try:
        # Get issue details from Jira
        issue = jira_client.issue(ticket_key)
        
        # Create attachments directory if it doesn't exist
        attachments_dir = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key)
        os.makedirs(attachments_dir, exist_ok=True)
        
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
            safe_filename = re.sub(r'[\\/*?:"<>|]', "_", attachment.filename)
            # Additional security: ensure filename doesn't contain path components
            safe_filename = os.path.basename(safe_filename)
            
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
            support_msg = "PDF files are also supported." if PDF_SUPPORT else "Install PyPDF2 to enable PDF support."
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
    
    # Security: Validate ticket key format to prevent path traversal
    if not re.match(r'^[A-Z]+-\d+$', ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Security: Validate filename to prevent path traversal
    if os.path.dirname(filename):
        return f"Error: Invalid filename: {filename}. Path traversal is not allowed."
    
    # Allow more characters in filenames, but still prevent dangerous ones
    if not re.match(r'^[a-zA-Z0-9\s._() -]+$', filename):
        return f"Error: Invalid filename: {filename}. Filename contains invalid characters."
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Build the path to the attachment
    file_path = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key, filename)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        logger.error(f"Attachment file not found: {file_path}")
        return f"""Error: Attachment file '{filename}' not found for ticket {ticket_key}.
Expected location: {file_path}

Did you download the attachments first? Use get_ticket_attachments('{ticket_key}') to download.
Note: If you're working in a different project directory, attachments are stored in:
{ATTACHMENTS_BASE_DIR}

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
        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.json', '.xml', '.csv', '.log']:
            # Text file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        elif file_ext == '.pdf':
            # PDF file
            if not PDF_SUPPORT:
                return "Error: PDF processing is not available. Please install PyPDF2 to analyze PDF attachments."
            
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page_num in range(len(pdf_reader.pages)):
                        content += pdf_reader.pages[page_num].extract_text() + "\n\n"
            except Exception as e:
                logger.error(f"Error reading PDF: {str(e)}")
                return f"Error reading PDF file: {str(e)}"
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

@mcp.tool()
def analyze_all_attachments(ticket_key: str, question: str = None) -> str:
    """Analyze all attachments from a Jira ticket using Ollama.
    
    Args:
        ticket_key: The Jira ticket key (e.g., PROJ-1234)
        question: Optional specific question about the attachments
    """
    logger.info(f"Tool called: analyze_all_attachments for {ticket_key}")
    
    # Security: Validate ticket key format to prevent path traversal
    if not re.match(r'^[A-Z]+-\d+$', ticket_key):
        return f"Error: Invalid ticket key format: {ticket_key}"
    
    # Get the appropriate Jira client for this ticket
    jira_client = get_jira_client(ticket_key)
    
    if not jira_client:
        return f"Error: Not connected to Jira for ticket {ticket_key}"
    
    # Build the path to the attachments directory
    attachments_dir = os.path.join(ATTACHMENTS_BASE_DIR, ticket_key)
    
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
{ATTACHMENTS_BASE_DIR}

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
    supported_extensions = [
        '.txt', '.md', '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', 
        '.h', '.json', '.xml', '.csv', '.log'
    ]
    
    # Add PDF if support is available
    if PDF_SUPPORT:
        supported_extensions.append('.pdf')
    
    # Filter to only supported files
    supported_files = [f for f in files if os.path.splitext(f)[1].lower() in supported_extensions]
    
    if not supported_files:
        if PDF_SUPPORT:
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
        return f"No attachments directory found at {attachments_base_dir}. Nothing to clean up."
    
    # Security: Make sure attachments_base_dir is a subdirectory of the script directory
    # or a custom directory specified by environment variable to prevent traversal attacks
    # This is a defense-in-depth measure in case ATTACHMENTS_BASE_DIR is compromised
    expected_base_dirs = [os.path.join(SCRIPT_DIR, "attachments")]
    if 'MCP_ATTACHMENTS_PATH' in os.environ:
        expected_base_dirs.append(os.environ['MCP_ATTACHMENTS_PATH'])
    
    if not any(os.path.normpath(attachments_base_dir) == os.path.normpath(expected) for expected in expected_base_dirs):
        logger.error(f"Security alert: Attempted to clean up directory outside allowed paths: {attachments_base_dir}")
        return f"Error: Security restriction. Cannot clean up directory outside of expected paths."
    
    if ticket_key:
        # Security validation for ticket_key format
        if not re.match(r'^[A-Z]+-\d+$', ticket_key):
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

def main():
    """
    Main entry point for the Jira Ollama MCP server.
    """
    # Check for command-line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--print-paths":
            # Print path information and exit
            print(f"\nJira Ollama MCP Path Information:")
            print(f"--------------------------------")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Script location: {__file__}")
            print(f"Script directory: {SCRIPT_DIR}")
            print(f"Attachments directory: {ATTACHMENTS_BASE_DIR}")
            print(f"MCP_ATTACHMENTS_PATH environment variable: {'Set to ' + os.environ['MCP_ATTACHMENTS_PATH'] if 'MCP_ATTACHMENTS_PATH' in os.environ else 'Not set'}")
            print(f"\nTo set a custom path: export MCP_ATTACHMENTS_PATH=/your/custom/path")
            sys.exit(0)
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            # Print help message and exit
            print(f"\nJira Ollama MCP Help:")
            print(f"--------------------")
            print(f"Usage: python {os.path.basename(__file__)} [options]")
            print(f"\nOptions:")
            print(f"  --help, -h        Show this help message and exit")
            print(f"  --print-paths     Print path information and exit")
            print(f"\nEnvironment Variables:")
            print(f"  MCP_ATTACHMENTS_PATH  Set a custom path for attachments (default: script_directory/attachments)")
            print(f"                        Example: export MCP_ATTACHMENTS_PATH=/your/custom/path")
            print(f"\nAttachments:")
            print(f"  Attachments are stored in {ATTACHMENTS_BASE_DIR}")
            print(f"  When running from a different directory, attachments are still stored in this location")
            print(f"  unless you set the MCP_ATTACHMENTS_PATH environment variable.")
            sys.exit(0)
    
    logger.info("Starting Jira Ollama MCP server...")
    
    # Log information about paths
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    logger.info(f"Script directory: {SCRIPT_DIR}")
    logger.info(f"Attachments directory: {ATTACHMENTS_BASE_DIR}")
    
    # Check if we're running from a different directory and provide a warning
    if not os.path.commonpath([cwd, ATTACHMENTS_BASE_DIR]) == cwd:
        logger.warning(f"IMPORTANT: You are running from a different directory ({cwd})")
        logger.warning(f"Attachments will be stored in: {ATTACHMENTS_BASE_DIR}")
        logger.warning(f"To change this, set the MCP_ATTACHMENTS_PATH environment variable")
        
        # Print this to stdout as well
        print(f"\n⚠️  IMPORTANT: Running from a different directory ({cwd})")
        print(f"⚠️  Attachments will be stored in: {ATTACHMENTS_BASE_DIR}")
        print(f"⚠️  To change this, set MCP_ATTACHMENTS_PATH environment variable\n")
    
    # Add a tip about MCP_ATTACHMENTS_PATH
    if 'MCP_ATTACHMENTS_PATH' not in os.environ:
        logger.info("TIP: You can set the MCP_ATTACHMENTS_PATH environment variable to customize where attachments are stored")
    
    try:
        # Run the server
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main() 