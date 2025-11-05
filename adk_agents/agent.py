"""Root agent definition for ADK CLI/web tooling."""

from src.adk_app.agent import build_agent as _build_agent

# ADK's CLI expects a `root_agent` attribute.
root_agent = _build_agent()


def build_agent(*args, **kwargs):
    """Compatibility helper for code that calls build_agent()."""
    return _build_agent(*args, **kwargs)

