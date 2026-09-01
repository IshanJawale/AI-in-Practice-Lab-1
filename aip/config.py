"""Configuration: model tiers, pricing, and runtime settings.

Everything is driven by environment variables so that the same lab code runs
against a paid API key, a free tier, or a local Ollama model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# Provider key aliases.
#
# NVIDIA calls its credential NVIDIA_API_KEY -- that is the name on the
# dashboard at build.nvidia.com and in NVIDIA's own docs. LiteLLM looks for
# NVIDIA_NIM_API_KEY. Students should not have to know that, so we bridge it
# here. Anything already set explicitly wins.
_KEY_ALIASES = {"NVIDIA_NIM_API_KEY": "NVIDIA_API_KEY"}
for _target, _source in _KEY_ALIASES.items():
    if not os.getenv(_target) and os.getenv(_source):
        os.environ[_target] = os.environ[_source]


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Model tiers
# ---------------------------------------------------------------------------
# Labs never hard-code a model. They ask for a *tier* and let the profile decide.
#
#   SMALL  — high-volume loops: classification, extraction over 200 items,
#            eval judging on cheap tasks. Optimise for cost and throughput.
#   MAIN   — the default for user-facing generation: RAG answers, tool use.
#   LARGE  — reserved for hard reasoning and as the LLM-judge of last resort.
#   EMBED  — the embedding model.
#
# A "profile" binds the four tiers to concrete LiteLLM model strings.
# Choose one with AIP_PROFILE. Add your own freely.

PROFILES: dict[str, dict[str, str]] = {
    "anthropic": {
        "SMALL": "anthropic/claude-haiku-4-5-20251001",
        "MAIN": "anthropic/claude-sonnet-5",
        "LARGE": "anthropic/claude-opus-5",
        # Anthropic has no embedding endpoint; use a local model.
        "EMBED": "local/BAAI/bge-small-en-v1.5",
    },
    "openai": {
        "SMALL": "openai/gpt-4.1-mini",
        "MAIN": "openai/gpt-4.1",
        "LARGE": "openai/gpt-4.1",
        "EMBED": "openai/text-embedding-3-small",
    },
    # VERIFIED WORKING 2026-08-22 against a Gemini free-tier key.
    # Tier assignment is driven by a measured fact, not by version numbers:
    # 3.7-flash spends ~220 invisible "thinking" tokens per call that you pay
    # for as output and CANNOT disable (reasoning_effort=none is rejected;
    # thinking:disabled is ignored). 3.5-flash-lite spends none. So the
    # high-volume tier is flash-lite and the reasoning tier is 3.7-flash.
    "gemini": {  # generous free tier -- the recommended profile for this module
        "SMALL": "gemini/gemini-3.5-flash-lite",   # 10 out tok, ~850 ms, no thinking
        "MAIN": "gemini/gemini-3.7-flash",         # reasoning model, ~220 think tok
        "LARGE": "gemini/gemini-3.5-flash",        # judge: a DIFFERENT family from MAIN
        "EMBED": "gemini/gemini-embedding-001",    # 3072-dim
    },
    # VERIFIED WORKING 2026-08-26 against an NVIDIA developer key.
    # A first-class alternative to `gemini`, and a hedge if that free tier
    # changes. All three chat tiers support response_format AND tool calling,
    # so every lab in the module runs on this profile.
    #
    # Two things to know:
    #   1. Of 83 models the API lists, most 404. These four are the ones that
    #      actually respond. Run `python scripts/list_models.py nvidia` and
    #      probe before trusting any others.
    #   2. The embedding model is ASYMMETRIC -- it takes input_type
    #      "query" or "passage" and returns different vectors for each.
    #      aip.embed handles this; see the note there.
    "nvidia": {
        "SMALL": "nvidia_nim/nvidia/nemotron-3-nano-30b-a3b",    # ~1.0 s
        "MAIN": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b",  # ~0.7 s, fastest
        "LARGE": "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b", # ~3.8 s
        "EMBED": "nvidia_nim/nvidia/nemotron-3-embed-1b",        # 2048-dim, asymmetric
    },
    # NOT VERIFIED. The IDs below were plausible at authoring time and will
    # rot the same way the Gemini ones did. Run `python scripts/list_models.py`
    # before trusting any of them.
    "groq": {  # free tier, very fast, open-weight models
        "SMALL": "groq/llama-3.1-8b-instant",
        "MAIN": "groq/llama-3.3-70b-versatile",
        "LARGE": "groq/llama-3.3-70b-versatile",
        "EMBED": "local/BAAI/bge-small-en-v1.5",
    },
    "ollama": {  # fully local, zero cost, no network
        "SMALL": "ollama/llama3.2:3b",
        "MAIN": "ollama/llama3.1:8b",
        "LARGE": "ollama/llama3.1:8b",
        "EMBED": "local/BAAI/bge-small-en-v1.5",
    },
}

# Price per 1M tokens (input, output), USD. Used for the cost meter only.
# These change; treat them as an estimate and update from the provider's page.
# `aip.cost` falls back to (0, 0) for unknown models, which is correct for
# Ollama and honest (rather than wrong) for anything else.
# Models that are genuinely free at the margin: you own the hardware, so a
# reported cost of $0.00 is CORRECT rather than merely unknown. Anything not
# matching one of these prefixes and absent from PRICES_PER_MTOK is treated as
# *unpriced*, and the cost meter says so instead of printing a confident zero.
FREE_PREFIXES: tuple[str, ...] = ("ollama/", "local/")

# Verified against ai.google.dev/gemini-api/docs/pricing on 2026-08-22 for the
# Gemini entries; the rest are unverified. Re-check before each delivery --
# and note that "output" includes billed-but-invisible thinking tokens.
#
# NVIDIA NIM is deliberately absent: NVIDIA publishes no per-token pricing for
# the developer endpoint and LiteLLM carries no cost entries for these models.
# Rather than invent numbers, the meter reports those calls as unpriced.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "anthropic/claude-haiku-4-5-20251001": (1.00, 5.00),
    "anthropic/claude-sonnet-5": (3.00, 15.00),
    "anthropic/claude-opus-5": (15.00, 75.00),
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-4.1": (2.00, 8.00),
    "openai/text-embedding-3-small": (0.02, 0.00),
    "gemini/gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini/gemini-3.5-flash": (1.50, 9.00),
    "gemini/gemini-3.7-flash": (0.75, 3.75),   # $1.50/$7.50 from 2027-01-01
    "gemini/gemini-3.6-flash": (0.75, 3.75),
    "gemini/gemini-embedding-001": (0.15, 0.00),
    "groq/llama-3.1-8b-instant": (0.05, 0.08),
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
}


@dataclass
class Settings:
    profile: str = field(default_factory=lambda: os.getenv("AIP_PROFILE", "gemini"))
    cache_dir: Path = field(
        default_factory=lambda: Path(os.getenv("AIP_CACHE_DIR", REPO_ROOT / ".aip_cache"))
    )
    trace_dir: Path = field(
        default_factory=lambda: Path(os.getenv("AIP_TRACE_DIR", REPO_ROOT / ".aip_traces"))
    )
    cache_enabled: bool = field(default_factory=lambda: _env_bool("AIP_CACHE", True))
    # AIP_OFFLINE=1 -> serve only from cache; a cache miss raises instead of
    # calling the network. Use this to grade, to demo without wifi, and to
    # guarantee a lab costs nothing.
    offline: bool = field(default_factory=lambda: _env_bool("AIP_OFFLINE", False))
    # Hard ceiling for the whole process, in USD. Trips BudgetExceeded.
    budget_usd: float = field(default_factory=lambda: _env_float("AIP_BUDGET_USD", 2.0))
    max_retries: int = 4
    timeout_s: float = field(default_factory=lambda: _env_float("AIP_TIMEOUT_S", 60.0))
    temperature: float = field(default_factory=lambda: _env_float("AIP_TEMPERATURE", 0.0))

    @property
    def models(self) -> dict[str, str]:
        if self.profile not in PROFILES:
            raise ValueError(
                f"Unknown AIP_PROFILE={self.profile!r}. "
                f"Choose one of {sorted(PROFILES)} or add your own in aip/config.py."
            )
        return PROFILES[self.profile]

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
MODELS = settings.models


def resolve_model(name_or_tier: str | None) -> str:
    """Turn 'SMALL' / 'MAIN' / 'LARGE' / 'EMBED' into a concrete model string.

    Anything that is not a known tier is passed through unchanged, so you can
    always pin an exact model when a lab asks you to compare across providers.
    """
    if name_or_tier is None:
        return settings.models["MAIN"]
    key = name_or_tier.upper()
    if key in settings.models:
        return settings.models[key]
    return name_or_tier
