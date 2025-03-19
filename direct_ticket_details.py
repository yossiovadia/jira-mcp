#!/usr/bin/env python3
"""
Direct script to call the get_ticket_details function without going through MCP
"""

import sys
from simple_jira_tools import get_ticket_details

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python direct_ticket_details.py TICKET_KEY")
        sys.exit(1)
    
    ticket_key = sys.argv[1]
    print(f"Getting details for ticket {ticket_key}...")
    
    # Call the function directly
    details = get_ticket_details(ticket_key)
    
    # Print the results
    print("\n" + "="*80)
    print(details)
    print("="*80) 