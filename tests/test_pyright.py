#!/usr/bin/env python3
"""
Test that pyright reports no errors across the configured scope.

This is a smoke test that wraps the pyright CLI. It depends on pyright being
installed locally — see install/install_dev_dependencies.sh.
"""

import os
import shutil
import subprocess
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPyright(unittest.TestCase):
    def test_pyright_clean(self):
        if shutil.which('pyright') is None:
            self.fail(
                "pyright not installed — run install/install_dev_dependencies.sh"
            )

        result = subprocess.run(
            ['pyright'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            self.fail(
                f"pyright reported errors (exit {result.returncode}):\n\n" +
                f"{result.stdout}\n{result.stderr}"
            )


if __name__ == '__main__':
    unittest.main()
