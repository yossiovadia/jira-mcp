# Jira MCP Integration Tests

This directory contains unit tests for the Jira MCP integration.

## Running Tests

To run all tests, use the `run_tests.py` script:

```bash
# From the project root
python tests/run_tests.py
```

Or to make it executable:

```bash
chmod +x tests/run_tests.py
./tests/run_tests.py
```

## Adding New Tests

1. Create a new test file in the `tests` directory with a name that starts with `test_`.
2. Import the necessary modules and the module you want to test.
3. Create a test class that inherits from `unittest.TestCase`.
4. Add test methods that start with `test_`.
5. Use `patch` decorators to mock dependencies.

Example:

```python
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMyFunction(unittest.TestCase):
    @patch('simple_jira_tools.dependency')
    def test_my_function(self, mock_dependency):
        from simple_jira_tools import my_function
        
        # Set up the mock
        mock_dependency.return_value = 'mocked_value'
        
        # Call the function
        result = my_function()
        
        # Verify the mock was called correctly
        mock_dependency.assert_called_once_with()
        
        # Check the result
        self.assertEqual(result, 'expected_value')

if __name__ == '__main__':
    unittest.main()
```

## Development Dependencies

The tests require the following dependencies, which are specified in `requirements-dev.txt`:

- pytest>=7.0.0
- pytest-cov>=4.0.0
- mock>=4.0.0

Install these dependencies using:

```bash
pip install -r requirements-dev.txt
``` 