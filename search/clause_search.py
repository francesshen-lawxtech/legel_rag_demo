"""
條款搜尋入口：支援三種模式，方便面試 demo 對比效果

  mode="hybrid"  ← 預設，BM25 + Vector + RRF
  mode="bm25"    ← 純關鍵字，對照用
  mode="vector"  ← 純語意，對照用
"""
from __future__ import annotations

from rag.retriever import bm25_search, hybrid_search, vector_search


def search_clauses(
    query: str,
    doc_type: str | None = None,
    top_k: int = 5,
    mode: str = "hybrid",
) -> list[dict]:
    if mode == "bm25":
        return bm25_search(query, top_k=top_k, doc_type=doc_type)
    if mode == "vector":
        return vector_search(query, top_k=top_k, doc_type=doc_type)
    return hybrid_search(query, top_k=top_k, doc_type=doc_type)
