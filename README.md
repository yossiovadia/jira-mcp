# Jira MCP Server

A Model Context Protocol (MCP) server for Jira integration that allows AI tools like Cursor to interact with Jira tickets.

## Setup Instructions

1. **Prerequisites**
   - Python 3.11 or higher
   - Virtual environment (recommended)
   - Jira account credentials

2. **Environment Variables**
   Create a `.env` file with the following variables:
   ```
   JIRA_HOST=jiradc2.ext.net.nokia.com
   JIRA_USERNAME=your_username
   JIRA_PASSWORD=your_password
   ```

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

## Usage Examples

Once the MCP server is running and connected to Cursor, you can ask questions like:

- "What are my assigned tickets in Jira?"
- "Can you get details for ticket NCSFM-21544?"
- "Show me my current Jira tickets"

## Files

- `simple_jira_tools.py`: The main MCP server implementation
- `mcp_with_venv.sh`: Shell script to run the MCP server with virtual environment
- `jira_mcp.py`: The original Jira MCP implementation with extended functionality
- `requirements.txt`: Project dependencies
- `.env`: Environment variables for Jira connection
- `cursor-mcp-config.json`: Configuration for Cursor

## Testing

The project includes a test suite for the MCP server functionality:

1. **Running Tests**
   ```bash
   # From the project root
   python tests/run_tests.py
   ```

2. **Development Dependencies**
   For running tests, install the development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Test Structure**
   - `/tests`: Contains all unit tests
   - `run_tests.py`: Script to discover and run all tests
   - `test_my_tickets.py`: Tests for the get_my_tickets function
   - `test_ticket_details.py`: Tests for the get_ticket_details function

For more information on testing, see the [tests/README.md](tests/README.md) file.

## Troubleshooting

If you encounter "client closed" errors in Cursor:
1. Make sure the virtual environment is activated correctly
2. Check that all required environment variables are set
3. Verify that Cursor is using the correct configuration file
4. Restart Cursor after making any configuration changes 

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
   python -m venv jira_analyzer
   source jira_analyzer/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   ./mcp_with_venv.sh
   ```

## Contributing

If you want to contribute to this project:

1. Make sure to never commit sensitive data (.env is gitignored)
2. Update requirements.txt if you add new dependencies
3. Test your changes with Cursor before submitting a pull request
4. Add unit tests for any new functionality 