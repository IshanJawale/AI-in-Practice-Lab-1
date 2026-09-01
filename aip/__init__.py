"""
aip — the shared toolkit for AI in Practice I, Module 1: Applied GenAI.

This package is deliberately small and readable. You are expected to open it.
Nothing here is magic; every module is under ~250 lines and is fair game to
modify, extend, or replace in your labs.

    from aip import chat, structured, embed, Budget

Design rules the package follows (and that your lab code should follow too):

1. Provider-agnostic.   Model names are LiteLLM strings. Swapping
                        `anthropic/claude-haiku-4-5-20251001` for
                        `ollama/llama3.1:8b` should require no other change.
2. Everything is cached. Identical requests never cost money twice.
3. Everything is counted. Tokens, cost, and latency are recorded on every call.
4. Everything is traceable. Every call appends a JSONL trace record.
5. Offline-capable.     With AIP_OFFLINE=1, cached responses replay and
                        uncached requests raise loudly rather than spending.
"""

__version__ = "1.0.0"

from aip.config import MODELS, settings, resolve_model
from aip.cost import Budget, BudgetExceeded, Usage
from aip.llm import chat, structured, StructuredOutputError
from aip.embed import embed, embed_batch
from aip.tracing import trace, read_traces

__all__ = [
    "MODELS", "settings", "resolve_model",
    "Budget", "BudgetExceeded", "Usage",
    "chat", "structured", "StructuredOutputError",
    "embed", "embed_batch",
    "trace", "read_traces",
]
