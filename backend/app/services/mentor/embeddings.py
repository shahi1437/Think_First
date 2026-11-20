"""Deterministic local semantic embedding generator for PostgreSQL pgvector(256).

Uses multi-granularity token + stem + character trigram signed random projections
(feature hashing into L2-normalized dense 256-dim vectors) so semantic cosine
similarity works reliably in PostgreSQL pgvector without requiring paid API keys.
Can be swapped for an external embedding provider via configuration.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Lightweight domain synonym expansion to strengthen semantic recall for Python concepts
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "range": ("loop", "boundary", "off_by_one", "exclusive", "stop"),
    "indexerror": ("indexing", "bounds", "subscript", "len", "list"),
    "index": ("indexing", "subscript", "position", "zero_based"),
    "none": ("return", "function", "missing_return"),
    "return": ("function", "output", "early_return"),
    "zerodivisionerror": ("runtime", "division", "zero", "exception"),
    "typeerror": ("runtime", "type", "string", "integer", "exception"),
    "nameerror": ("runtime", "undefined", "variable", "typo"),
    "syntaxerror": ("syntax", "colon", "indentation", "parenthesis"),
    "indentationerror": ("syntax", "indentation", "whitespace"),
    "initialization": ("init", "sentinel", "accumulator", "negative", "zero"),
    "negative": ("initialization", "sentinel", "min", "max", "edge_case"),
    "condition": ("conditional", "branch", "comparator", "boolean", "if"),
    "logic": ("algorithm", "trace", "formula", "operator"),
    "boundary": ("loop", "off_by_one", "range", "edge_case"),
    "test": ("edge_case", "testing", "verification", "boundary"),
}


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _hash_feature(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    raw = int.from_bytes(digest, "little")
    idx = raw % dim
    sign = 1.0 if ((raw >> 16) & 1) == 0 else -1.0
    return idx, sign


class LocalSemanticEmbedder:
    """Produces L2-normalized 256-dim dense semantic vectors for pgvector storage & query."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dim = dimensions

    @property
    def dimensions(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec

        for i, tok in enumerate(tokens):
            stemmed = _stem(tok)
            idx, sign = _hash_feature(f"w:{stemmed}", self._dim)
            vec[idx] += sign * 1.4

            # Bigrams capture multi-word CS concepts ("loop boundary", "early return")
            if i + 1 < len(tokens):
                bi = f"bi:{stemmed}_{_stem(tokens[i + 1])}"
                b_idx, b_sign = _hash_feature(bi, self._dim)
                vec[b_idx] += b_sign * 1.1

            # Character trigrams handle typos/morphology ("indexing" <-> "index")
            if len(tok) >= 4:
                padded = f"^{tok}$"
                for j in range(len(padded) - 2):
                    c_idx, c_sign = _hash_feature(f"c:{padded[j : j + 3]}", self._dim)
                    vec[c_idx] += c_sign * 0.25

            # Concept synonym expansion
            for syn in _SYNONYMS.get(tok, ()) or _SYNONYMS.get(stemmed, ()):
                s_idx, s_sign = _hash_feature(f"w:{syn}", self._dim)
                vec[s_idx] += s_sign * 0.65

        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            vec[0] = 1.0
            return vec
        return [round(v / norm, 6) for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
