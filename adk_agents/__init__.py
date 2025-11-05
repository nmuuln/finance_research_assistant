"""ADK agent registry for the UFE Research Writer project."""

from pathlib import Path
import sys

# Ensure the project root (one level up from this package) is on sys.path so
# imports like `src.*` work when ADK loads agents in isolation.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
