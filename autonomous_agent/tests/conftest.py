"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add autonomous_agent root (parent of src/) so 'from src.xxx' imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
