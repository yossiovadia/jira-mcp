#!/usr/bin/env python3
import json
import subprocess
import sys

def send_request(method, params):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    # Start the MCP server process
    process = subprocess.Popen(
        ["python", "jira_ollama_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send the request
    print(f"Sending request: {json.dumps(request)}")
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # Get the response
    response_line = process.stdout.readline()
    
    # Terminate the process
    process.terminate()
    process.wait()
    
    # Parse and return the response
    try:
        return json.loads(response_line)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON: {response_line}")
        stderr_output = process.stderr.read()
        print(f"STDERR: {stderr_output}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_mcp_client.py <method> [param1=value1 param2=value2 ...]")
        sys.exit(1)
    
    method = sys.argv[1]
    params = {}
    
    # Parse parameters from command-line arguments
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            params[key] = value
    
    # Send the request and get the response
    response = send_request(method, params)
    
    # Pretty-print the response
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    main() 