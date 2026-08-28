"""Test suite for svg-flow-animator. Stdlib `unittest` only -- see tests/README.md."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
