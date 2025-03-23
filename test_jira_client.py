#!/usr/bin/env python3
"""
Simple test script to diagnose Jira connection issues
"""
import os
import sys
import logging
from dotenv import load_dotenv
from jira import JIRA

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jira-test")

# Load environment variables
load_dotenv()

def test_jira_connection():
    """Test connection to both Jira instances"""
    # Primary Jira 
    primary_jira_host = os.getenv('PRIMARY_JIRA_HOST')
    primary_jira_pat = os.getenv('PRIMARY_JIRA_PAT')
    
    # Secondary Jira
    secondary_jira_host = os.getenv('SECONDARY_JIRA_HOST')
    secondary_jira_pat = os.getenv('SECONDARY_JIRA_PAT')
    
    print("\n=== Testing Jira Connections ===\n")
    
    # Test Primary Jira
    print(f"Testing Primary Jira ({primary_jira_host})...")
    try:
        primary_jira = JIRA(
            server=f"https://{primary_jira_host}",
            token_auth=primary_jira_pat,
            max_retries=1
        )
        # Test connection
        myself = primary_jira.myself()
        print(f"✅ Connected to Primary Jira as {myself['displayName']} ({myself['name']})")
    except Exception as e:
        print(f"❌ Failed to connect to Primary Jira: {str(e)}")
    
    # Test Secondary Jira
    print(f"\nTesting Secondary Jira ({secondary_jira_host})...")
    try:
        secondary_jira = JIRA(
            server=f"https://{secondary_jira_host}",
            token_auth=secondary_jira_pat,
            max_retries=1
        )
        # Test connection
        myself = secondary_jira.myself()
        print(f"✅ Connected to Secondary Jira as {myself['displayName']} ({myself['name']})")
        
        # Try to get a ticket
        ticket_key = "CNV-22134"  # Replace with a valid ticket key
        print(f"\nTrying to get ticket {ticket_key}...")
        issue = secondary_jira.issue(ticket_key)
        print(f"✅ Successfully retrieved ticket: {issue.fields.summary}")
    except Exception as e:
        print(f"❌ Failed: {str(e)}")

if __name__ == "__main__":
    test_jira_connection() 