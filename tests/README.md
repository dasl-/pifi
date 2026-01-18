# Tests

This directory contains unit tests for the pifi project.

## Running Tests

### Option 1: Run directly with Python (recommended)

```bash
# Run all tests
python3 tests/test_screensaver_interface.py

# Run with verbose output
python3 tests/test_screensaver_interface.py -v
```

### Option 2: Run all tests in the directory

```bash
# Run all test files
python3 -m unittest discover -s tests -p 'test_*.py'

# Run with verbose output
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### Option 3: Run specific test classes or methods

```bash
# Run a specific test class
python3 -m unittest tests.test_screensaver_interface.TestScreensaverInterface

# Run a specific test method
python3 -m unittest tests.test_screensaver_interface.TestScreensaverInterface.test_all_screensavers_inherit_from_screensaver
```

### Option 4: Using pytest (if installed)

```bash
# Install pytest (optional)
pip3 install pytest

# Run all tests
python3 -m pytest tests/

# Run with verbose output
python3 -m pytest tests/ -v

# Run a specific test file
python3 -m pytest tests/test_screensaver_interface.py -v
```

## Test Files

- `test_screensaver_interface.py` - Tests for the Screensaver ABC interface
  - Verifies all screensavers implement the required interface
  - Checks metadata consistency
  - Validates constructor signatures
  - 15 tests total

## Writing New Tests

New test files should:
1. Be named with the pattern `test_*.py`
2. Import `unittest` and use `unittest.TestCase`
3. Use the `setUpModule()` function to configure mocks if needed
4. Be placed in this `tests/` directory

Example:
```python
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)

if __name__ == '__main__':
    unittest.main()
```
