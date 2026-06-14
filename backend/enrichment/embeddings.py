"""Local text embeddings via sentence-transformers (ingestion-side only).

Model loads lazily on first use and is cached for the process lifetime.
Vectors are L2-normalized so sqlite-vec L2 distance ranks like cosine similarity.
"""

from functools import lru_cache

from backend.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def _model():
    # imported lazily: avoids paying the torch import cost at module import time
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(settings.embedding_model)
    # method renamed across versions; prefer new name, fall back to old
    get_dim = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    dim = get_dim()
    if dim != settings.embedding_dim:
        raise ValueError(
            f"embedding_dim mismatch: model '{settings.embedding_model}' outputs {dim}, "
            f"but settings.embedding_dim={settings.embedding_dim} (and the sqlite-vec "
            f"table is fixed at that size). Fix config or model."
        )
    return model


def _zero() -> list[float]:
    return [0.0] * settings.embedding_dim


def embed_text(text: str | None) -> list[float]:
    """Embed one string. Blank -> zero vector (no model call)."""
    if not text or not text.strip():
        return _zero()
    vec = _model().encode(
        text, normalize_embeddings=True, convert_to_numpy=True
    )
    return vec.astype(float).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed many strings in one pass. Blanks map to zero vectors, positions preserved."""
    idx = [i for i, t in enumerate(texts) if t and t.strip()]
    out: list[list[float]] = [_zero() for _ in texts]
    if not idx:
        return out
    vecs = _model().encode(
        [texts[i] for i in idx],
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=32,
    )
    for i, vec in zip(idx, vecs):
        out[i] = vec.astype(float).tolist()
    return out
