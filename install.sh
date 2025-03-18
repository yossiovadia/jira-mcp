#!/bin/bash
# Installation script for Jira MCP server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting installation of Jira MCP server...${NC}"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]); then
    echo -e "${RED}Error: Python 3.11 or higher is required. Found Python $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}Found Python $python_version${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install requirements
echo -e "${GREEN}Installing requirements...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Install development requirements if --dev flag is passed
if [ "$1" == "--dev" ]; then
    echo -e "${GREEN}Installing development requirements...${NC}"
    pip install -r requirements-dev.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    if [ -f ".env_example" ]; then
        cp .env_example .env
        echo -e "${YELLOW}Please edit .env file with your Jira credentials.${NC}"
    else
        echo -e "${RED}No .env_example file found. Creating basic .env file...${NC}"
        cat > .env << EOF
JIRA_HOST=jiradc2.ext.net.nokia.com
JIRA_USERNAME=your_username
JIRA_PASSWORD=your_password
EOF
        echo -e "${YELLOW}Please edit .env file with your Jira credentials.${NC}"
    fi
fi

# Make run script executable
chmod +x mcp_with_venv.sh

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}To run the server:${NC}"
echo -e "  ${YELLOW}./mcp_with_venv.sh${NC}"
echo -e "${GREEN}To run tests:${NC}"
echo -e "  ${YELLOW}python tests/run_tests.py${NC}"

# Deactivate virtual environment
deactivate 