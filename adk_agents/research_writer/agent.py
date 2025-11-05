"""Research Writer agent registration for ADK CLI/Web."""

from pathlib import Path
import sys

# Ensure project root is on path so `src.*` absolute imports resolve.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.adk_app.agent import build_agent as _build_agent  # noqa: E402

# ``root_agent`` is what ADK Web looks for when loading the agent bundle.
root_agent = _build_agent()


def build_agent(*args, **kwargs):
    """Expose build_agent for compatibility with other tooling."""
    return _build_agent(*args, **kwargs)
