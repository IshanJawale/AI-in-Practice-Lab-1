"""Chunking strategies.

Chunking is the most under-rated variable in RAG. Students routinely spend a
day swapping embedding models for a 2% gain, having never tried changing the
chunk size, which is often worth 20%.

Four strategies here, deliberately spanning the quality/complexity range:

    fixed_chunks         — N characters, hard cut. The strawman.
    sliding_chunks       — N characters with overlap. The usual default.
    recursive_chunks     — split on the largest natural boundary that fits.
    markdown_chunks      — respect heading structure, prepend heading path.

Lab 3 asks you to measure all four on the same corpus and query set. The
answer is not the same for every corpus, which is the point.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    text: str
    doc_id: str
    chunk_id: str
    meta: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.text)


def fixed_chunks(text: str, doc_id: str, size: int = 800) -> list[Chunk]:
    return [
        Chunk(text[i : i + size], doc_id, f"{doc_id}::f{i // size}", {"strategy": "fixed"})
        for i in range(0, len(text), size)
        if text[i : i + size].strip()
    ]


def sliding_chunks(text: str, doc_id: str, size: int = 800, overlap: int = 150) -> list[Chunk]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    chunks = []
    for n, i in enumerate(range(0, max(len(text), 1), step)):
        piece = text[i : i + size]
        if piece.strip():
            chunks.append(
                Chunk(piece, doc_id, f"{doc_id}::s{n}",
                      {"strategy": "sliding", "start": i, "overlap": overlap})
            )
        if i + size >= len(text):
            break
    return chunks


_SEPARATORS = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]


def _recursive_split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []
    sep = next((s for s in seps if s and s in text), "")
    if not sep:
        return [text[i : i + size] for i in range(0, len(text), size)]
    rest = seps[seps.index(sep) + 1 :]
    out, buf = [], ""
    for part in text.split(sep):
        candidate = (buf + sep + part) if buf else part
        if len(candidate) <= size:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            buf = part if len(part) <= size else ""
            if len(part) > size:
                out.extend(_recursive_split(part, size, rest))
    if buf.strip():
        out.append(buf)
    return [c for c in out if c.strip()]


def recursive_chunks(text: str, doc_id: str, size: int = 800, overlap: int = 100) -> list[Chunk]:
    pieces = _recursive_split(text, size, _SEPARATORS)
    if overlap:
        merged = []
        for i, p in enumerate(pieces):
            prefix = pieces[i - 1][-overlap:] if i else ""
            merged.append((prefix + " " + p).strip() if prefix else p)
        pieces = merged
    return [
        Chunk(p, doc_id, f"{doc_id}::r{i}", {"strategy": "recursive"})
        for i, p in enumerate(pieces)
    ]


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def markdown_chunks(text: str, doc_id: str, size: int = 1200) -> list[Chunk]:
    """Split on headings; prepend the heading path to every chunk.

    The prepended path ("Claims > Reimbursement > Timelines") is a cheap and
    very effective trick: it gives an otherwise context-free chunk enough
    signal for the embedding model to place it correctly, and it gives the
    generator enough context to cite it correctly.
    """
    matches = list(_HEADING.finditer(text))
    if not matches:
        return recursive_chunks(text, doc_id, size)

    sections, path = [], []
    for i, m in enumerate(matches):
        level, title = len(m.group(1)), m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        path = path[: level - 1] + [title]
        if body:
            sections.append((" > ".join(path), body))

    chunks: list[Chunk] = []
    for heading_path, body in sections:
        prefix = f"[{heading_path}]\n"
        room = max(size - len(prefix), 200)
        for piece in _recursive_split(body, room, _SEPARATORS):
            chunks.append(
                Chunk(
                    prefix + piece,
                    doc_id,
                    f"{doc_id}::m{len(chunks)}",
                    {"strategy": "markdown", "heading": heading_path},
                )
            )
    return chunks


STRATEGIES = {
    "fixed": fixed_chunks,
    "sliding": sliding_chunks,
    "recursive": recursive_chunks,
    "markdown": markdown_chunks,
}
