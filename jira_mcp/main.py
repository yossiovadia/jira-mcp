#!/usr/bin/env python3
"""
Jira MCP Main Entry Point
"""
import os
import sys
from mcp.server.fastmcp import FastMCP
from .utils.logging import logger
from .config import config
from .jira_client import initialize_jira_clients
from .tools import register_tools

# Create server with the same name that worked in the ultra minimal version
mcp = FastMCP("jira")

def main():
    """
    Main entry point for the Jira MCP server.
    """
    # Check for command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--print-paths":
            # Print path information and exit
            print(f"\nJira MCP Path Information:")
            print(f"--------------------------------")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Script location: {__file__}")
            print(f"Attachments directory: {config.attachments_base_dir}")
            print(f"MCP_ATTACHMENTS_PATH environment variable: {'Set to ' + os.environ['MCP_ATTACHMENTS_PATH'] if 'MCP_ATTACHMENTS_PATH' in os.environ else 'Not set'}")
            print(f"\nTo set a custom path: export MCP_ATTACHMENTS_PATH=/your/custom/path")
            sys.exit(0)
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            # Print help message and exit
            print(f"\nJira MCP Help:")
            print(f"--------------------")
            print(f"Usage: python -m jira_mcp.main [options]")
            print(f"\nOptions:")
            print(f"  --help, -h        Show this help message and exit")
            print(f"  --print-paths     Print path information and exit")
            print(f"\nEnvironment Variables:")
            print(f"  MCP_ATTACHMENTS_PATH  Set a custom path for attachments (default: script_directory/attachments)")
            print(f"                        Example: export MCP_ATTACHMENTS_PATH=/your/custom/path")
            print(f"\nAttachments:")
            print(f"  Attachments are stored in {config.attachments_base_dir}")
            print(f"  When running from a different directory, attachments are still stored in this location")
            print(f"  unless you set the MCP_ATTACHMENTS_PATH environment variable.")
            sys.exit(0)
    
    logger.info("Starting Jira MCP server...")
    
    # Log information about paths
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    logger.info(f"Attachments directory: {config.attachments_base_dir}")
    
    # Check if we're running from a different directory and provide a warning
    if not os.path.commonpath([cwd, config.attachments_base_dir]) == cwd:
        logger.warning(f"IMPORTANT: You are running from a different directory ({cwd})")
        logger.warning(f"Attachments will be stored in: {config.attachments_base_dir}")
        logger.warning(f"To change this, set the MCP_ATTACHMENTS_PATH environment variable")
        
        # Print this to stdout as well
        print(f"\n⚠️  IMPORTANT: Running from a different directory ({cwd})")
        print(f"⚠️  Attachments will be stored in: {config.attachments_base_dir}")
        print(f"⚠️  To change this, set MCP_ATTACHMENTS_PATH environment variable\n")
    
    # Add a tip about MCP_ATTACHMENTS_PATH
    if 'MCP_ATTACHMENTS_PATH' not in os.environ:
        logger.info("TIP: You can set the MCP_ATTACHMENTS_PATH environment variable to customize where attachments are stored")
    
    # Initialize Jira clients
    initialize_jira_clients()
    
    # Register tools with MCP
    register_tools(mcp)
    
    try:
        # Run the server
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 