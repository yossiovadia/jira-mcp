# Jira MCP Server

A Model Context Protocol (MCP) server for Jira integration that allows AI tools like Cursor to interact with Jira tickets.

## Setup Instructions

1. **Prerequisites**
   - Python 3.11 or higher
   - Virtual environment (recommended)
   - Jira account credentials

2. **Environment Variables**
   Create a `.env` file with the following variables:
   
   **Basic setup (single Jira instance):**
   ```
   PRIMARY_JIRA_HOST=your-jira-host.example.com
   # Option 1: Username/Password Authentication
   PRIMARY_JIRA_USERNAME=your_username
   PRIMARY_JIRA_PASSWORD=your_password
   # Option 2: Personal Access Token Authentication 
   # PRIMARY_JIRA_PAT=your_personal_access_token
   ```
   
   **Advanced setup (multiple Jira instances):**
   
   If you have access to multiple Jira systems, you can configure them all:
   ```
   # Primary Jira Instance
   PRIMARY_JIRA_HOST=your-primary-jira.example.com
   PRIMARY_JIRA_PAT=your_primary_pat
   
   # Secondary Jira Instance
   SECONDARY_JIRA_HOST=your-secondary-jira.example.com
   SECONDARY_JIRA_PAT=your_secondary_pat
   
   # Define which project prefixes belong to secondary Jira
   SECONDARY_PROJECT_PREFIXES=ABC,XYZ
   ```
   
   The system will automatically route requests to the appropriate Jira instance based on the ticket key prefix.

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Cursor**
   The `cursor-mcp-config.json` file is already configured to use the working solution.
   To set up Cursor:
   - Place the `cursor-mcp-config.json` file in the proper Cursor location
   - For macOS: `~/.cursor/mcp-config/cursor-mcp-config.json`
   - Restart Cursor

## Available Tools

The MCP server provides these tools to interact with Jira:

1. **get_my_tickets**: Retrieves all tickets assigned to the current user
2. **get_ticket_details**: Gets detailed information about a specific ticket
3. **summarize_ticket**: Summarizes a Jira ticket using Ollama
4. **analyze_ticket**: Analyzes a ticket by asking a specific question
5. **get_ticket_attachments**: Downloads attachments from a ticket
6. **analyze_attachment**: Analyzes a specific attachment using Ollama
7. **analyze_all_attachments**: Analyzes all attachments from a ticket
8. **cleanup_attachments**: Deletes downloaded attachments

## Usage Examples

Once the MCP server is running and connected to Cursor, you can ask questions like:

- "What are my assigned tickets in Jira?"
- "Can you get details for ticket PROJECT-1234?"
- "Summarize ticket PROJECT-5678"
- "Download attachments from ticket PROJECT-9012"
- "Analyze the document.pdf attachment from ticket PROJECT-3456"

## Files

- `jira_ollama_mcp.py`: The main MCP server implementation with Ollama integration
- `jira_ollama_with_venv.sh`: Shell script to run the MCP server with virtual environment
- `requirements.txt`: Project dependencies
- `.env`: Environment variables for Jira connection
- `cursor-mcp-config.json`: Configuration for Cursor

## Testing

The project includes a test suite for the MCP server functionality:

1. **Running Tests**
   ```bash
   # From the project root
   python -m pytest tests/
   ```

2. **Development Dependencies**
   For running tests, install the development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Test Structure**
   - `/tests`: Contains all unit tests

For more information on testing, see the [tests/README.md](tests/README.md) file.

## Troubleshooting

If you encounter "client closed" errors in Cursor:
1. Make sure the virtual environment is activated correctly
2. Check that all required environment variables are set
3. Verify that Cursor is using the correct configuration file
4. Restart Cursor after making any configuration changes

If you encounter errors related to Jira connections:
1. Verify your Jira credentials are correct
2. Ensure you have appropriate permissions for the tickets you're trying to access
3. If you only have access to one Jira system, only configure that system in your `.env` file
4. Check your VPN connection if Jira is behind a corporate firewall

## GitHub Setup

To clone and set up this project from GitHub:

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/jira-mcp.git
   cd jira-mcp
   ```

2. **Create your environment file**
   Copy the example environment file and add your credentials:
   ```bash
   cp .env_example .env
   # Edit .env with your actual credentials
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   ./jira_ollama_with_venv.sh
   ```

## Contributing

If you want to contribute to this project:

1. Make sure to never commit sensitive data (.env is gitignored)
2. Update requirements.txt if you add new dependencies
3. Test your changes with Cursor before submitting a pull request
4. Add unit tests for any new functionality 