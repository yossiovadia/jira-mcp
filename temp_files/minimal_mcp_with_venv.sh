#!/bin/bash

# Exit on any error
set -e

# Activate the virtual environment
source ~/jira_analyzer/bin/activate

# Set PYTHONUNBUFFERED for immediate logging
export PYTHONUNBUFFERED=1

# Change to project directory
cd /Users/yovadia/jira-mcp

# Run the minimal MCP server
# The script will automatically load variables from .env.minimal
python minimal_jira_mcp.py 