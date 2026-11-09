"""Test runner for KiCad-StockCheck."""

import os
import sys
import unittest

repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(repo_root, "tests"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
