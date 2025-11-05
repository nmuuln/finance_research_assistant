from functools import cache
from pathlib import Path


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@cache
def load_prompt(name: str) -> str:
    """Load a prompt text file from the shared prompts directory."""
    path = _PROMPT_DIR / name
    return path.read_text(encoding="utf-8")


@cache
def get_domain_guard() -> str:
    return load_prompt("domain_guard.txt")


@cache
def get_writer_tone() -> str:
    return load_prompt("writer_tone.txt")


@cache
def get_writer_structure() -> str:
    return load_prompt("writer_structure.txt")

