"""
Tool implementations for Jira MCP
"""
# Import all tools for easier access
from .get_tickets import get_my_tickets
from .ticket_details import get_ticket_details, summarize_ticket, analyze_ticket
from .attachments import (
    get_ticket_attachments, 
    analyze_attachment, 
    analyze_all_attachments, 
    cleanup_attachments
)

# Register all tools with the MCP server
def register_tools(mcp):
    """
    Register all tools with the MCP server
    
    Args:
        mcp: The MCP server instance
    """
    # Get tickets tools
    mcp.tool()(get_my_tickets)
    
    # Ticket details tools
    mcp.tool()(get_ticket_details)
    mcp.tool()(summarize_ticket)
    mcp.tool()(analyze_ticket)
    
    # Attachment tools
    mcp.tool()(get_ticket_attachments)
    mcp.tool()(analyze_attachment)
    mcp.tool()(analyze_all_attachments)
    mcp.tool()(cleanup_attachments)
    
    return mcp 