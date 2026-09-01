#!/usr/bin/env python3
"""Ask your provider which models actually exist right now.

    python scripts/list_models.py

Why this script exists: model IDs rot, and they rot silently. The IDs in
aip/config.py were correct when written and were already dead a few months
later -- the API returned 404 with a "no longer available, use X instead"
message. That is the good case. The bad case is a model that still answers but
has been quietly replaced behind an alias, so your evaluation numbers move and
you blame your prompt.

Two habits follow, and they are worth more than this script:
  1. Pin exact model IDs. Never ship an alias like `gemini-flash-latest` in
     anything you will compare numbers across time.
  2. When a metric moves and your code did not, check the model before you
     check your prompt.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aip.config import PRICES_PER_MTOK, PROFILES, settings  # noqa: E402


def gemini() -> None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set")
        return
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200"
    try:
        data = json.load(urllib.request.urlopen(url, timeout=30))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read()[:300].decode(errors='replace')}")
        return

    chat, embed = [], []
    for m in data.get("models", []):
        name = m["name"].removeprefix("models/")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            chat.append(name)
        if "embedContent" in methods:
            embed.append(name)

    print(f"{len(chat)} generateContent models, {len(embed)} embedContent models\n")
    print("generateContent:")
    for n in sorted(chat):
        print(f"  {n}")
    print("\nembedContent:")
    for n in sorted(embed):
        print(f"  {n}")

    print("\nCAVEAT: being listed here does NOT mean your key can call it.")
    print("On a free-tier key the 2.5-* and *-pro-* models are listed and then")
    print("return 404 or 429 on the first real request. Probe before trusting.")


def openai_like(base: str, key_env: str) -> None:
    key = os.getenv(key_env)
    if not key:
        print(f"{key_env} not set")
        return
    req = urllib.request.Request(f"{base}/models",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read()[:300].decode(errors='replace')}")
        return
    for m in sorted(d["id"] for d in data.get("data", [])):
        print(f"  {m}")


def nvidia() -> None:
    """NVIDIA NIM is OpenAI-compatible, so /v1/models works the same way."""
    openai_like("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY")
    print("\nCAVEAT, and it bites hard here: of the ~83 models this lists, most")
    print("return 404 or time out on a developer key. Verified working as of")
    print("2026-08-26: nemotron-3-nano-30b-a3b, nemotron-3-super-120b-a12b,")
    print("nemotron-3-ultra-550b-a55b, and nemotron-3-embed-1b. Probe before")
    print("trusting anything else.")


LISTERS = {
    "gemini": gemini,
    "nvidia": nvidia,
    "openai": lambda: openai_like("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "groq": lambda: openai_like("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "anthropic": lambda: print(
        "Anthropic: GET https://api.anthropic.com/v1/models with the "
        "x-api-key and anthropic-version headers, or see docs.claude.com."),
    "ollama": lambda: os.system("ollama list"),
}


def main() -> None:
    profile = sys.argv[1] if len(sys.argv) > 1 else settings.profile
    print(f"profile: {profile}\n")
    lister = LISTERS.get(profile)
    if not lister:
        print(f"no lister for {profile!r}. Known: {sorted(LISTERS)}")
        return
    lister()

    print("\ncurrently configured in aip/config.py:")
    for tier, model in PROFILES.get(profile, {}).items():
        price = PRICES_PER_MTOK.get(model)
        if price:
            tag = f"${price[0]}/${price[1]} per Mtok"
        elif model.startswith(("ollama/", "local/")):
            tag = "free (runs on your machine)"
        else:
            tag = "UNPRICED -- calls are counted, not costed"
        print(f"  {tier:<6} {model:<44} {tag}")


if __name__ == "__main__":
    main()
