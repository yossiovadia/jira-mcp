# Jira MCP - Modular Structure

This directory contains the modular implementation of the Jira MCP (Model Context Protocol) server.

## Directory Structure

```
jira_mcp/
├── __init__.py                 # Package marker
├── main.py                     # Main entry point
├── config.py                   # Configuration loading and management
├── jira_client/
│   ├── __init__.py             # Package marker
│   ├── client.py               # Jira client initialization
│   └── utils.py                # Jira utility functions
├── ollama_client/
│   ├── __init__.py             # Package marker
│   └── client.py               # Ollama API client
├── tools/
│   ├── __init__.py             # Package marker
│   ├── get_tickets.py          # Ticket retrieval tools
│   ├── ticket_details.py       # Ticket details and analysis tools
│   └── attachments.py          # Attachment handling tools
└── utils/
    ├── __init__.py             # Package marker
    ├── logging.py              # Logging configuration
    ├── security.py             # Security utilities
    └── file_utils.py           # File handling utilities
```

## Usage Examples

### Running as the MCP Server

Start the MCP server to listen for incoming requests:

```bash
# From the project root directory
python -m jira_mcp.main
```

### Using as a Module in Custom Scripts

Import and use the tools programmatically:

```python
# Working with tickets
from jira_mcp.tools.get_tickets import get_my_tickets
from jira_mcp.tools.ticket_details import get_ticket_details, summarize_ticket, analyze_ticket

# Get all tickets assigned to you
tickets = get_my_tickets()
print(tickets)

# Get details about a specific ticket
details = get_ticket_details("PROJ-1234")
print(details)

# Summarize a ticket
summary = summarize_ticket("PROJ-1234")
print(summary)

# Ask a specific question about a ticket
answer = analyze_ticket("PROJ-1234", "What is the current status?")
print(answer)

# Working with attachments
from jira_mcp.tools.attachments import (
    get_ticket_attachments, 
    analyze_attachment,
    analyze_all_attachments,
    cleanup_attachments
)

# Download all attachments
get_ticket_attachments("PROJ-1234")

# Analyze a specific attachment
analysis = analyze_attachment("PROJ-1234", "requirements.txt", "What are the dependencies?")
print(analysis)

# Analyze all attachments at once
all_analysis = analyze_all_attachments("PROJ-1234", "Summarize this content")
print(all_analysis)

# Clean up when done
cleanup_attachments("PROJ-1234")
```

### Using with Cursor AI

Once the MCP server is running, you can use it with Cursor AI by asking questions like:

- "What are my assigned tickets in Jira?"
- "Can you get details for ticket PROJECT-1234?"
- "Summarize ticket PROJECT-5678"
- "Download attachments from ticket PROJECT-9012"
- "Analyze the document.pdf attachment from ticket PROJECT-3456"

## Configuration Management

Configure your environment using environment variables or a `.env` file:

```python
from jira_mcp.config import config

# Access config values
print(f"Attachments directory: {config.attachments_base_dir}")
print(f"Ollama API URL: {config.ollama_api_url}")
print(f"PDF support available: {config.pdf_support}")
```

## Extending with New Tools

To add new tools, create a new module in the `tools` directory, implement your functions, and register them in `tools/__init__.py`:

```python
# my_new_tool.py
from ..utils.logging import logger

def my_new_function(param1, param2):
    """Description of what this tool does
    
    Args:
        param1: Description of param1
        param2: Description of param2
    """
    logger.info(f"Tool called: my_new_function with {param1}, {param2}")
    # Tool implementation
    return "Result of my_new_function"
```

Then register your new tool in `tools/__init__.py`:

```python
# Add to imports
from .my_new_tool import my_new_function

# Add to register_tools function
def register_tools(mcp):
    # ... existing tools
    
    # Register new tool
    mcp.tool()(my_new_function)
    
    return mcp
``` 