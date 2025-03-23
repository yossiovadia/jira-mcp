# Jira MCP - Modular Command Provider

A modular implementation of a Jira Command Provider for interacting with Jira issues and their attachments through a CLI interface.

## Features

- **Ticket Management**: Fetch, summarize, and analyze Jira tickets
- **Attachment Handling**: Download, analyze, and manage attachments from Jira tickets
- **Ollama Integration**: Use Ollama to analyze and summarize ticket content and attachments
- **Security**: Input validation, path sanitization, and secure file handling
- **Modular Architecture**: Easily maintainable and extensible codebase

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd jira-mcp
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. If you're migrating from the monolithic version:
   ```
   python migrate_to_modules.py
   ```

## Configuration

Configure your Jira connections by setting the following environment variables:

```bash
# Primary Jira Connection
export JIRA_SERVER='https://your-jira-instance.atlassian.net'
export JIRA_USERNAME='your-username'
export JIRA_TOKEN='your-api-token'

# Secondary Jira Connection (optional)
export SECONDARY_JIRA_SERVER='https://your-secondary-jira.atlassian.net'
export SECONDARY_JIRA_USERNAME='your-secondary-username'
export SECONDARY_JIRA_TOKEN='your-secondary-api-token'

# Attachments Path (optional)
export MCP_ATTACHMENTS_PATH='/custom/path/for/attachments'
```

## Usage

### Starting the MCP Server

```bash
python -m jira_mcp.main
```

Display help and path information:
```bash
python -m jira_mcp.main --help
python -m jira_mcp.main --print-paths
```

### Available Tools

#### Ticket Management

- `get_my_tickets()`: Retrieve all tickets assigned to you
- `get_ticket_details(ticket_key)`: Get comprehensive details about a ticket
- `summarize_ticket(ticket_key)`: Get an AI-generated summary of a ticket
- `analyze_ticket(ticket_key, question)`: Ask specific questions about a ticket

#### Attachment Handling

- `get_ticket_attachments(ticket_key)`: Download all attachments from a ticket
- `analyze_attachment(ticket_key, filename, question=None)`: Analyze a specific attachment
- `analyze_all_attachments(ticket_key, question=None)`: Analyze all attachments from a ticket
- `cleanup_attachments(ticket_key=None)`: Delete downloaded attachments

### Example Usage

Retrieve your tickets:
```python
result = get_my_tickets()
print(result)
```

Get details about a specific ticket:
```python
result = get_ticket_details("PROJ-1234")
print(result)
```

Download and analyze ticket attachments:
```python
# Download attachments
get_ticket_attachments("PROJ-1234")

# Analyze a specific attachment
result = analyze_attachment("PROJ-1234", "requirements.txt", 
                          "What are the key dependencies?")
print(result)

# Clean up when done
cleanup_attachments("PROJ-1234")
```

## Modular Structure

The codebase is organized into logical modules:

```
jira_mcp/
├── __init__.py                 # Package marker
├── main.py                     # Main entry point
├── config.py                   # Configuration management
├── jira_client/                # Jira API integration
├── ollama_client/              # Ollama API integration
├── tools/                      # Tool implementations
│   ├── get_tickets.py          # Ticket retrieval
│   ├── ticket_details.py       # Ticket analysis
│   └── attachments.py          # Attachment handling
└── utils/                      # Utility functions
    ├── logging.py              # Logging configuration
    ├── security.py             # Security utilities
    └── file_utils.py           # File operations
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Make your changes and commit: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin new-feature`
5. Submit a pull request

## Security Considerations

- All user inputs are validated to prevent path traversal attacks
- Filenames are sanitized before saving
- Path safety validation prevents unauthorized access
- Maximum file size limits are enforced for performance and security 