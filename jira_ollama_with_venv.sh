#!/bin/bash

# Change to project directory first
cd /Users/yovadia/jira-mcp

# Activate the virtual environment
source ./venv/bin/activate

# Set PYTHONUNBUFFERED for immediate logging
export PYTHONUNBUFFERED=1

# Run the Ollama MCP server
# The script will automatically load variables from .env.ollama
python jira_ollama_mcp.py 