"""Shared path setup for the HOURS EOH test suite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
