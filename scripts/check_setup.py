#!/usr/bin/env python3
"""Environment check. Run this first, and run it again whenever something odd happens.

    make check
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK, BAD, WARN = "  ok  ", " FAIL ", " warn "
problems: list[str] = []


def check(label: str, fn) -> None:
    try:
        detail = fn()
        print(f"[{OK}] {label:<34} {detail or ''}")
    except Exception as exc:                                    # noqa: BLE001
        print(f"[{BAD}] {label:<34} {type(exc).__name__}: {exc}")
        problems.append(label)


def main() -> None:
    print("AI in Practice I - Module 1: environment check\n")

    def _python_version():
        v = sys.version_info
        s = f"{v.major}.{v.minor}.{v.micro}"
        if v < (3, 11):
            raise RuntimeError(
                f"{s} is too old. This module needs 3.11+ — current numpy and "
                f"scipy require 3.12, and pandas/scikit-learn require 3.11. "
                f"Install 3.12 and rebuild: rm -rf .venv && make setup")
        if v >= (3, 15):
            raise RuntimeError(
                f"{s} is newer than litellm supports (it declares <3.15). "
                f"Use 3.12–3.14.")
        if v < (3, 12):
            return f"{s}  (supported; 3.12+ gets you newer numpy/scipy)"
        return s

    check("python 3.11 – 3.14", _python_version)

    for pkg in ("litellm", "pydantic", "numpy", "chromadb", "rank_bm25",
                "sentence_transformers", "dotenv"):
        check(f"import {pkg}", lambda p=pkg: __import__(p).__name__)

    from aip.config import PROFILES, settings

    check("AIP_PROFILE valid", lambda: (
        settings.profile if settings.profile in PROFILES else
        (_ for _ in ()).throw(ValueError(f"unknown; pick one of {sorted(PROFILES)}"))))

    key_env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
               "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY",
               "nvidia": "NVIDIA_API_KEY", "ollama": None}
    needed = key_env.get(settings.profile)
    if needed and not settings.offline:
        check(f"{needed} set", lambda: (
            "***" + (os.getenv(needed) or "")[-4:] if os.getenv(needed) else
            (_ for _ in ()).throw(RuntimeError("missing -- see .env.example"))))

    check("corpus present", lambda: f"{len(list((ROOT/'data/corpus').glob('*.md')))} docs")
    check("ticket data present", lambda: (
        f"{sum(1 for _ in (ROOT/'data/eval/extraction_dev.jsonl').open(encoding='utf-8'))} dev cases"))
    check("golden RAG set present", lambda: (
        f"{sum(1 for _ in (ROOT/'data/eval/rag_golden.jsonl').open(encoding='utf-8'))} questions"))

    from aip import cache
    check("cache writable", lambda: f"{sum(cache.stats().values())} entries")

    print()
    if settings.offline:
        print("AIP_OFFLINE=1 -- replaying cache only, no network, no cost.\n")
    else:
        def live():
            from aip import chat
            t0 = time.perf_counter()
            out = chat("Reply with exactly: READY", tier="SMALL", max_tokens=10)
            return f"{out.strip()[:20]!r} in {(time.perf_counter()-t0)*1000:.0f} ms"
        check("live model call", live)

        def embedding():
            from aip import embed
            v = embed("hello")
            return f"dim={len(v)}"
        check("embedding call", embedding)

    from aip.cost import global_budget, is_priced
    print("\n" + global_budget().report())
    unpriced = [m for m in settings.models.values() if not is_priced(m)]
    if unpriced:
        print(f"note: {len(unpriced)} of your configured models have no published "
              f"per-token price,\n      so the cost meter will report their calls as "
              f"UNPRICED rather than $0.00.")
    print(f"profile={settings.profile}  models={settings.models}")
    print(f"budget ceiling=${settings.budget_usd}  cache={'on' if settings.cache_enabled else 'off'}")

    if problems:
        print(f"\n{len(problems)} problem(s): {', '.join(problems)}")
        print("See SETUP.md. Ask on the course channel if stuck for more than 10 minutes.")
        sys.exit(1)
    print("\nEnvironment is ready.")


if __name__ == "__main__":
    main()
