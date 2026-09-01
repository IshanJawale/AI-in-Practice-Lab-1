"""Embeddings, cached, with a zero-cost local fallback.

Model strings follow the same convention as aip.llm, with one addition:
`local/<huggingface-id>` runs a sentence-transformers model on your machine.
That is the default for the anthropic / groq / ollama profiles, and it is the
escape hatch if you have no embedding API budget at all.

Local `BAAI/bge-small-en-v1.5` is 133 MB, runs fine on a laptop CPU, and is
good enough that the retrieval labs produce meaningful numbers. It is also a
useful lesson in its own right: for many retrieval problems the embedding
model is not the bottleneck. Your chunking is.
"""
from __future__ import annotations

import base64
import time
from functools import lru_cache

import numpy as np

from aip import cache, cost, tracing
from aip.config import resolve_model, settings


@lru_cache(maxsize=4)
def _local_model(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


# Providers whose embedding models are ASYMMETRIC: they return a different
# vector depending on whether the text is a document being indexed or a query
# being searched, and you must tell them which.
#
# Getting this wrong does not raise. It silently degrades retrieval, which is
# the worst kind of bug and exactly the sort this module exists to teach about.
# Verified empirically on nvidia/nemotron-3-embed-1b: the same string embedded
# as "passage" and as "query" produces different vectors.
ASYMMETRIC_PREFIXES: tuple[str, ...] = ("nvidia_nim/",)


def _supports_input_type(model: str) -> bool:
    return model.startswith(ASYMMETRIC_PREFIXES)


def _embed_uncached(texts: list[str], model: str,
                    input_type: str = "passage") -> list[list[float]]:
    if model.startswith("local/"):
        st = _local_model(model.removeprefix("local/"))
        vecs = st.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    from litellm import embedding

    kwargs = {"model": model, "input": texts, "timeout": settings.timeout_s}
    if _supports_input_type(model):
        kwargs["input_type"] = input_type
    resp = embedding(**kwargs)
    pt = int(getattr(resp.usage, "prompt_tokens", 0) or 0)
    cost.record(
        cost.Usage(model, pt, 0, cost.price_of(model, pt, 0), 0.0, cached=False,
                   calls=1, priced=cost.is_priced(model))
    )
    return [d["embedding"] for d in resp.data]


def _pack(vec) -> dict:
    """Store a vector as base64 float32, not as a JSON list of floats.

    A 3072-dimensional vector is ~60 KB as JSON text and ~16 KB packed. Across
    a warmed corpus cache that is the difference between a 44 MB file nobody
    wants in git and a 12 MB one that makes `AIP_OFFLINE=1` work for everybody.
    """
    return {"b64": base64.b64encode(
        np.asarray(vec, dtype=np.float32).tobytes()).decode("ascii")}


def _unpack(entry: dict) -> list[float]:
    if "b64" in entry:
        return np.frombuffer(base64.b64decode(entry["b64"]), dtype=np.float32).tolist()
    return entry["vector"]          # legacy entries written before packing


def embed_batch(
    texts: list[str],
    *,
    model: str | None = None,
    batch_size: int = 64,
    show_progress: bool = False,
    input_type: str = "passage",
) -> np.ndarray:
    """Embed a list of strings. Returns an (n, d) float32 array, L2-normalised.

    Normalising here means cosine similarity is just a dot product everywhere
    downstream, which keeps `aip.retrieval` simple and fast.

    `input_type` is "passage" when you are indexing a corpus and "query" when
    you are searching it. It is ignored by symmetric providers (Gemini, OpenAI,
    local sentence-transformers) and honoured by asymmetric ones (NVIDIA NIM).
    It is part of the cache key, because a passage vector and a query vector
    for the same text are different vectors and must not collide.
    """
    m = resolve_model(model or "EMBED")
    out: list[list[float] | None] = [None] * len(texts)
    pending: list[int] = []

    it = input_type if _supports_input_type(m) else None
    for i, t in enumerate(texts):
        key = cache.make_key("embed", {"model": m, "text": t, "input_type": it})
        hit = cache.get(key)
        if hit is not None:
            out[i] = _unpack(hit)
        else:
            pending.append(i)

    if pending and settings.offline:
        raise cache.CacheMiss(
            f"AIP_OFFLINE=1 and {len(pending)} texts are not in the embedding cache "
            f"(model={m}, input_type={it}). "
            "Run `python scripts/warm_cache.py` once while online, or use a local/ model "
            "(which needs no network after the first download)."
        )

    with tracing.trace("embed.batch", model=m, n=len(texts), n_uncached=len(pending)):
        for start in range(0, len(pending), batch_size):
            idxs = pending[start : start + batch_size]
            t0 = time.perf_counter()
            vecs = _embed_uncached([texts[i] for i in idxs], m, input_type)
            if show_progress:
                done = min(start + batch_size, len(pending))
                print(
                    f"  embedded {done}/{len(pending)} "
                    f"({(time.perf_counter() - t0) * 1000:.0f} ms/batch)",
                    end="\r",
                )
            for i, v in zip(idxs, vecs):
                out[i] = v
                cache.put(
                    cache.make_key("embed", {"model": m, "text": texts[i],
                                             "input_type": it}),
                    "embed",
                    {"model": m, "text": texts[i][:200], "input_type": it},
                    _pack(v),
                )
        if show_progress and pending:
            print()

    arr = np.asarray(out, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def embed(text: str, *, model: str | None = None,
          input_type: str = "query") -> np.ndarray:
    """Embed a single string. Returns a (d,) float32 array.

    Note the default: a single embed() call is nearly always a SEARCH, so it
    defaults to "query", while embed_batch() defaults to "passage" because it
    is nearly always an indexing pass. Pass it explicitly if you are doing
    something else.
    """
    return embed_batch([text], model=model, input_type=input_type)[0]


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity. Assumes inputs are already L2-normalised (they are,
    if they came from embed/embed_batch)."""
    return a @ b.T
