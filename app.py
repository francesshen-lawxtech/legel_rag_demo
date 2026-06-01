"""
Legal RAG Demo — FastAPI 主程式
架構鏡射 fin-intel-query-core/app.py，方便面試說明設計一致性。

API 端點：
  GET  /health
  GET  /documents                              - 列出所有文件
  GET  /search?q=...&doc_type=...&mode=...    - Hybrid 搜尋（可切換模式對比）
  POST /ask                                    - RAG 問答（含 LLM 生成答案）
  GET  /risk/{doc_id}                          - 合約風險分析
  GET  /compliance/{doc_id}                    - 合規檢查
"""
import sqlite3
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.db import DB_PATH
from search.clause_search import search_clauses
from search.risk_tagger import analyze_document
from search.compliance_check import check_compliance

app = FastAPI(
    title="Legal RAG Demo",
    description="法律文件 RAG 系統 Demo — Hybrid BM25 + Vector Search",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# ─── Documents ───────────────────────────────────────────────────────────────

@app.get("/documents")
def list_documents():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, doc_type, jurisdiction, effective_date, created_at "
        "FROM documents ORDER BY effective_date DESC"
    ).fetchall()
    conn.close()
    return {"total": len(rows), "documents": [dict(r) for r in rows]}


# ─── Search ──────────────────────────────────────────────────────────────────

@app.get("/search")
def search(
    q: str = Query(..., description="搜尋查詢，例如：保密義務終止後還存在嗎"),
    doc_type: str | None = Query(None, description="限定文件類型：NDA / 勞動契約 / 採購合約"),
    mode: str = Query("hybrid", description="搜尋模式：hybrid | bm25 | vector"),
    top_k: int = Query(5, ge=1, le=20),
):
    """
    Hybrid 搜尋端點。
    面試示範時可對同一個查詢分別用 mode=bm25 / mode=vector / mode=hybrid，
    比較三種結果的差異，說明為什麼 hybrid 最好。
    """
    try:
        results = search_clauses(q, doc_type=doc_type, top_k=top_k, mode=mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": q,
        "mode": mode,
        "doc_type_filter": doc_type,
        "total": len(results),
        "results": [
            {
                "rank": i + 1,
                "doc_title": r.get("doc_title", r.get("doc_title", "")),
                "article_num": r.get("article_num", ""),
                "clause_type": r.get("clause_type", ""),
                "doc_type": r.get("doc_type", ""),
                "rrf_score": r.get("rrf_score"),
                "bm25_score": r.get("bm25_score"),
                "vector_distance": r.get("vector_distance"),
                "clause_text": r.get("clause_text", "")[:300],
            }
            for i, r in enumerate(results)
        ],
    }


# ─── RAG Ask ─────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    doc_type: str | None = None
    top_k: int = 5


@app.post("/ask")
def ask(req: AskRequest):
    """
    RAG 問答：hybrid_search 召回相關條款 → Ollama LLM 生成答案 → 回傳答案 + 出處。
    如果 Ollama 未啟動，仍回傳召回的條款（答案欄位會說明 LLM 不可用）。
    """
    from rag.pipeline import rag_query
    try:
        result = rag_query(req.question, doc_type=req.doc_type, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


# ─── Risk Analysis ───────────────────────────────────────────────────────────

@app.get("/risk/{doc_id}")
def risk_analysis(doc_id: str):
    """合約風險條款自動標記，模擬律師事務所合約審閱第一步。"""
    try:
        return analyze_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Compliance Check ────────────────────────────────────────────────────────

@app.get("/compliance/{doc_id}")
def compliance(doc_id: str):
    """法規合規檢查，對照勞基法、採購法、營業秘密法等強制規定。"""
    try:
        return check_compliance(doc_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── RAG Compliance Check ────────────────────────────────────────────────────

@app.get("/compliance/rag/{doc_id}")
def compliance_rag(doc_id: str):
    """
    RAG-based 合規檢查：
    將勞基法（法規）與合約條款同時 ingest 進 ChromaDB，
    由 LLM 對照法條內容自動判斷合約是否符合，取代 hardcoded regex rules。
    """
    from search.rag_compliance import rag_compliance_check
    try:
        return rag_compliance_check(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Compare Modes ───────────────────────────────────────────────────────────

@app.get("/compare")
def compare_modes(
    q: str = Query(...),
    doc_type: str | None = None,
    top_k: int = 3,
):
    """
    同一個查詢同時跑三種模式，方便面試時並排展示 Hybrid 的優勢。
    回傳 bm25 / vector / hybrid 三個結果集。
    """
    def _run(mode):
        try:
            return search_clauses(q, doc_type=doc_type, top_k=top_k, mode=mode)
        except Exception:
            return []

    def _fmt(results):
        return [
            {
                "article_num": r.get("article_num", ""),
                "clause_type": r.get("clause_type", ""),
                "snippet": r.get("clause_text", "")[:150],
            }
            for r in results
        ]

    return {
        "query": q,
        "bm25":   _fmt(_run("bm25")),
        "vector": _fmt(_run("vector")),
        "hybrid": _fmt(_run("hybrid")),
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8088, reload=False)
