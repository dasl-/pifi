# Tests

This directory contains unit tests for the pifi project.

## Running Tests

First set up the dev environment once (`install/install_dev_dependencies.sh`),
then run the suite through the uv-managed venv so dependencies and pyright
resolve consistently:

```bash
uv run pytest tests/

# Verbose
uv run pytest tests/ -v

# A single file
uv run pytest tests/test_screensavers.py -v
```

`uv run` puts the venv first on PATH, so the subprocess-based tests (which
shell out to `python3 …`) and `test_pyright.py` use the venv interpreter too.
Running a bare `pytest`/`python3` instead uses whatever python is on your PATH,
which may be missing pifi's dependencies.

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
