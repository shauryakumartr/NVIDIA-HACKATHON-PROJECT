"""
Backend.agent wrapper.
Exposes agent interface from project root for backward/cross-module compatibility.
"""
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent import (  # noqa: E402
    generate_why_buy_insight,
    generate_top_5_merits_demerits,
    parse_natural_language_intent,
    chat_with_nemotron,
    TOOLS,
    execute_tool,
    get_nebius_client,
    NEMOTRON_MODEL,
    NEBIUS_BASE_URL,
)

__all__ = [
    "generate_why_buy_insight",
    "generate_top_5_merits_demerits",
    "parse_natural_language_intent",
    "chat_with_nemotron",
    "TOOLS",
    "execute_tool",
    "get_nebius_client",
    "NEMOTRON_MODEL",
    "NEBIUS_BASE_URL",
]
