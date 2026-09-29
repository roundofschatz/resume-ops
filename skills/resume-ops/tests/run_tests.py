#!/usr/bin/env python3
"""Run every test file in this folder:  python tests/run_tests.py"""
import sys
import unittest
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
suite = unittest.defaultTestLoader.discover(str(here), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
