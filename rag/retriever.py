"""
Hybrid Retriever：BM25（SQLite FTS5）+ 向量搜尋（ChromaDB）→ RRF 合併

為什麼兩種都要？
  BM25   精確：「民法第184條」「違約金」等法律術語完全匹配
  Vector 語意：「提早結束合約要賠多少」→ 能找到「違約賠償條款」
  RRF    合併：兩邊 ranking 不需要分數正規化，直接以名次融合，穩定不需調參
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

from utils.db import DB_PATH
from utils.embedding import get_embedding

CHROMA_PATH = str(Path(__file__).resolve().parent.parent / "data" / "chroma_db")
COLLECTION_NAME = "legal_clauses"


# ─── BM25 via SQLite FTS5 ────────────────────────────────────────────────────

def bm25_search(
    query: str,
    top_k: int = 10,
    doc_type: str | None = None,
) -> list[dict]:
    """
    SQLite FTS5 內建 BM25（rank 隱藏欄），負分、越小越相關。
    MATCH 先過濾候選集，WHERE doc_type 再縮小範圍，效率高。
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # FTS5 MATCH 用雙引號包住，避免中文標點被解析為特殊語法
    fts_query = '"' + query.replace('"', '""') + '"'

    if doc_type:
        sql = (
            "SELECT chunk_id, doc_id, doc_type, doc_title, article_num, "
            "       clause_type, clause_text, rank AS bm25_score "
            "FROM clauses_fts "
            "WHERE clause_text MATCH ? AND doc_type = ? "
            "ORDER BY rank LIMIT ?"
        )
        rows = conn.execute(sql, (fts_query, doc_type, top_k)).fetchall()
    else:
        sql = (
            "SELECT chunk_id, doc_id, doc_type, doc_title, article_num, "
            "       clause_type, clause_text, rank AS bm25_score "
            "FROM clauses_fts "
            "WHERE clause_text MATCH ? "
            "ORDER BY rank LIMIT ?"
        )
        rows = conn.execute(sql, (fts_query, top_k)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


# ─── Vector Search via ChromaDB ──────────────────────────────────────────────

def vector_search(
    query: str,
    top_k: int = 10,
    doc_type: str | None = None,
    doc_id: str | None = None,
) -> list[dict]:
    """
    ChromaDB cosine similarity。
    doc_type / doc_id 可單獨或組合使用做 metadata 過濾。
    """
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    q_vec = get_embedding(query)

    if doc_type and doc_id:
        where: dict | None = {"$and": [
            {"doc_type": {"$eq": doc_type}},
            {"doc_id":   {"$eq": doc_id}},
        ]}
    elif doc_type:
        where = {"doc_type": {"$eq": doc_type}}
    elif doc_id:
        where = {"doc_id": {"$eq": doc_id}}
    else:
        where = None

    results = collection.query(
        query_embeddings=[q_vec],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    out = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({
            "chunk_id": meta.get("chunk_id"),
            "doc_id": meta.get("doc_id"),
            "doc_type": meta.get("doc_type"),
            "doc_title": meta.get("doc_title"),
            "article_num": meta.get("article_num"),
            "clause_type": meta.get("clause_type"),
            "clause_text": doc,
            "vector_distance": dist,
        })
    return out


# ─── RRF Fusion ──────────────────────────────────────────────────────────────

def rrf_fusion(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion：score = Σ 1/(k + rank)
    k=60 是學術論文建議預設值，不需要調整。
    兩個 list 的分數量綱完全不同（BM25 負值 vs cosine 距離），
    RRF 以名次取代原始分數，天然解決正規化問題。
    """
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, item in enumerate(bm25_results):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        docs[cid] = item

    for rank, item in enumerate(vector_results):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        if cid not in docs:
            docs[cid] = item

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"rrf_score": round(score, 6), **docs[cid]} for cid, score in ranked]


# ─── Hybrid Entry Point ───────────────────────────────────────────────────────

def hybrid_search(
    query: str,
    top_k: int = 5,
    doc_type: str | None = None,
) -> list[dict]:
    """主要搜尋入口。BM25 + Vector 各取 top_k*2，RRF 合併後取前 top_k。"""
    bm25 = bm25_search(query, top_k=top_k * 2, doc_type=doc_type)
    vector = vector_search(query, top_k=top_k * 2, doc_type=doc_type)
    return rrf_fusion(bm25, vector)[:top_k]
