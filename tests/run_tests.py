#!/usr/bin/env python3
"""
Test runner script for Jira MCP integration tests.
Discovers and runs all tests in the tests directory.
"""
import unittest
import os
import sys
import importlib.util

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_tests():
    """
    Discover and run all tests in the tests directory.
    
    Uses pytest if available, with fallback to unittest.
    
    Returns:
        int: 0 if all tests pass, 1 if any test fails
    """
    print("Discovering and running tests...")
    
    # Check if pytest is available
    if importlib.util.find_spec("pytest") is not None:
        print("Using pytest for testing")
        import pytest
        # Run pytest with coverage report
        result = pytest.main([
            "-v",
            os.path.dirname(__file__),
        ])
        return 0 if result == 0 else 1
    else:
        print("Pytest not found, using unittest")
        # Discover tests in the current directory (tests)
        test_loader = unittest.TestLoader()
        test_suite = test_loader.discover(os.path.dirname(__file__), pattern='test_*.py')
        
        # Run the tests
        test_runner = unittest.TextTestRunner(verbosity=2)
        result = test_runner.run(test_suite)
        
        # Return success/failure code
        return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    # Run the tests and exit with the appropriate code
    sys.exit(run_tests()) 