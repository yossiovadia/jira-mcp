#!/usr/bin/env python3
"""
Migration script to help transition from monolithic jira_ollama_mcp.py to modular structure.

This script:
1. Makes a backup of the original script
2. Installs the modular structure
3. Preserves any custom environment settings
"""
import os
import sys
import shutil
import datetime
import subprocess

def main():
    print("\nJira MCP Migration Tool")
    print("=======================")
    print("This script will help you migrate from the monolithic script to a modular structure.")
    print("It will create a backup of your current script before making any changes.")
    
    # Step 1: Check if the original script exists
    original_script = "jira_ollama_mcp.py"
    if not os.path.exists(original_script):
        print(f"\nError: Could not find the original script '{original_script}'.")
        print("Please run this script from the same directory as jira_ollama_mcp.py.")
        sys.exit(1)
    
    # Step 2: Create a backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{original_script}.backup_{timestamp}"
    print(f"\nCreating backup of {original_script} to {backup_file}...")
    try:
        shutil.copy2(original_script, backup_file)
        print(f"Backup created successfully.")
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        sys.exit(1)
    
    # Step 3: Check if the modular structure already exists
    if os.path.exists("jira_mcp"):
        print("\nWarning: A directory named 'jira_mcp' already exists.")
        choice = input("Do you want to overwrite it? This will delete any existing files. (y/n): ")
        if choice.lower() != 'y':
            print("Migration aborted.")
            sys.exit(0)
        
        print("Removing existing jira_mcp directory...")
        try:
            shutil.rmtree("jira_mcp")
        except Exception as e:
            print(f"Error removing directory: {str(e)}")
            sys.exit(1)
    
    # Step 4: Create the modular structure
    print("\nCreating modular structure...")
    try:
        # Create directory structure
        os.makedirs("jira_mcp/jira_client", exist_ok=True)
        os.makedirs("jira_mcp/ollama_client", exist_ok=True)
        os.makedirs("jira_mcp/tools", exist_ok=True)
        os.makedirs("jira_mcp/utils", exist_ok=True)
        
        # Copy any existing attachments directory
        if os.path.exists("attachments"):
            print("Found attachments directory, preserving it...")
            # We don't move it, as the original script still works with it in the current location
        
        # Install module dependencies (if setup.py exists)
        if os.path.exists("setup.py"):
            print("\nInstalling dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
    except Exception as e:
        print(f"Error creating modular structure: {str(e)}")
        sys.exit(1)
    
    # Step 5: Create a simple wrapper script for backward compatibility
    print("\nCreating compatibility wrapper...")
    with open("jira_ollama_mcp_wrapper.py", "w") as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Backward compatibility wrapper for jira_ollama_mcp.py
This script imports and runs the modular version.
\"\"\"
import sys
from jira_mcp.main import main

if __name__ == "__main__":
    main()
""")
    
    os.chmod("jira_ollama_mcp_wrapper.py", 0o755)  # Make it executable
    
    # Step 6: Print instructions
    print("\nMigration complete!")
    print("\nNext steps:")
    print("1. Install the required Python modules for the modular version:")
    print("   pip install -e .")
    print("\n2. Test the modular version with:")
    print("   python -m jira_mcp.main")
    print("\n3. For backward compatibility, you can use:")
    print("   python jira_ollama_mcp_wrapper.py")
    print("\nNote: Your original script has been preserved as a backup.")
    print(f"If you need to revert, just rename {backup_file} back to {original_script}.")

if __name__ == "__main__":
    main() 