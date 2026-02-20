"""
Local semantic search — all processing happens on your machine.
No data ever leaves your computer.

Uses sentence-transformers with the all-MiniLM-L6-v2 model (~80 MB,
downloaded once and cached locally by the library).
"""
from __future__ import annotations
import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _cosine_sim(query_emb: np.ndarray, item_embs: np.ndarray) -> np.ndarray:
    q = query_emb / (np.linalg.norm(query_emb) + 1e-9)
    norms = np.linalg.norm(item_embs, axis=1, keepdims=True) + 1e-9
    items_norm = item_embs / norms
    return items_norm @ q


def semantic_search(
    query: str,
    items: list[dict],
    text_fn,
    top_k: int = 8,
    threshold: float = 0.2,
) -> list[tuple[dict, float]]:
    """
    Search items semantically. Returns list of (item, score) sorted by
    descending relevance, filtered to scores above threshold.

    - query: what the user typed
    - items: list of dicts (DB rows)
    - text_fn: callable(item) -> str  builds searchable text for each item
    - top_k: max results to return
    - threshold: minimum similarity score (0-1)
    """
    if not items or not query.strip():
        return []

    model = _get_model()
    texts = [text_fn(item) for item in items]

    query_emb = model.encode(query, convert_to_numpy=True)
    item_embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    scores = _cosine_sim(query_emb, item_embs)

    results = [
        (items[i], float(scores[i]))
        for i in range(len(items))
        if scores[i] >= threshold
    ]
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
