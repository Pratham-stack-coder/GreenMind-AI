"""
Root conftest.py — adds the backend directory to sys.path so that
`import app.*` works regardless of how pytest is invoked (pytest / python -m pytest).
"""
import sys
from pathlib import Path

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
