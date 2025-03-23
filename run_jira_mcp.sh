#!/bin/bash

# Set script directory as the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -e .
else
    # Activate virtual environment
    source venv/bin/activate
fi

# Set PYTHONUNBUFFERED for immediate logging
export PYTHONUNBUFFERED=1

# Check for command line arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    python -m jira_mcp.main --help
    exit 0
elif [ "$1" == "--print-paths" ]; then
    python -m jira_mcp.main --print-paths
    exit 0
fi

# Print banner
echo "======================================================"
echo "  Jira MCP Server - Modular Version"
echo "======================================================"
echo "Starting server..."
echo ""

# Run the Jira MCP server
python -m jira_mcp.main

# Deactivate virtual environment on exit
deactivate 