"""
Embedding utility：優先使用 Ollama bge-m3，自動 fallback 至 sentence-transformers。
與 fin-intel-query-core 使用相同的 Ollama endpoint 設計。
"""
from __future__ import annotations
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")

_st_model = None


def _load_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        print("[embedding] Ollama 不可用，改用 sentence-transformers (multilingual-MiniLM)")
        _st_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _st_model


def _embed_ollama(text: str) -> list[float]:
    import requests
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def get_embedding(text: str) -> list[float]:
    try:
        return _embed_ollama(text)
    except Exception:
        return _load_st_model().encode(text).tolist()


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """批次 embedding，供 ETL step 4 使用。"""
    try:
        import requests
        results = []
        for text in texts:
            resp = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBEDDING_MODEL, "input": text},
                timeout=30,
            )
            resp.raise_for_status()
            results.append(resp.json()["embeddings"][0])
        return results
    except Exception:
        model = _load_st_model()
        return model.encode(texts, batch_size=16, show_progress_bar=True).tolist()
