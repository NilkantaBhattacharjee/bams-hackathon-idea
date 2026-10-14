"""Meaning-based search over the glossary and case records, using a local sentence-embedding model.

No data leaves the machine: the model runs locally. If the library or model is unavailable,
search returns no matches and the chat keeps its exact-match behaviour.
"""

from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"
MIN_SCORE = 0.35  # cosine similarity below this is treated as not related


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer  # imported lazily
    return SentenceTransformer(MODEL_NAME)


def available() -> bool:
    try:
        _model()
        return True
    except Exception:
        return False


def _embed(texts: list[str]):
    return _model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)


def glossary_text(entry: dict) -> str:
    return f"{entry['Term']}: {entry.get('Full_Form', '')}. {entry.get('Plain_English_Explanation', '')}"


@lru_cache(maxsize=1)
def _glossary_index(key: str, entries_json: str):
    import json
    import numpy as np
    entries = json.loads(entries_json)
    vectors = _embed([glossary_text(e) for e in entries])
    return entries, np.asarray(vectors)


def search_glossary(query: str, entries: list[dict], top_k: int = 3) -> list[dict]:
    """Glossary entries closest in meaning to the query, best first. Empty if unavailable or unrelated."""
    if not query.strip() or not available():
        return []
    import json
    import numpy as np
    entries_json = json.dumps(entries, sort_keys=True)
    indexed, vectors = _glossary_index(str(hash(entries_json)), entries_json)
    q = _embed([query])[0]
    scores = vectors @ np.asarray(q)
    order = np.argsort(-scores)[:top_k]
    return [
        {**indexed[i], "score": round(float(scores[i]), 3)}
        for i in order if scores[i] >= MIN_SCORE
    ]
