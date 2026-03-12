"""Karamba - Personal Research Assistant Framework."""
__version__ = "0.1.0"

from .core import KarambaAgent
from .llm import create_llm, LLMConfig

__all__ = [
    "KarambaAgent",
    "create_llm",
    "LLMConfig",
]