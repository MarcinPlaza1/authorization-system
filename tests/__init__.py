"""
Test package initialization.
This file is required for Python to treat the directory as a package.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root) 