#!/bin/bash

# Activate the virtual environment
source ~/jira_analyzer/bin/activate

# Set PYTHONUNBUFFERED for immediate logging
export PYTHONUNBUFFERED=1

# Change to project directory
cd /Users/yovadia/jira-mcp

# Run the Ollama MCP server
# The script will automatically load variables from .env.ollama
python jira_ollama_mcp.py 