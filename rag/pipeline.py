"""
RAG Pipeline：hybrid_search 取回相關條款 → LLM 生成答案 + 出處引用

LLM 使用 Ollama（本地，免費），與 fin-intel-query-core 相同設計。
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from rag.retriever import hybrid_search

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:latest")

_PROMPT_TEMPLATE = """\
你是一位專業的法律顧問助理，協助使用者理解合約條款。
請根據以下【相關條款】回答使用者的問題。

【相關條款】
{context}

【使用者問題】
{question}

回答要求：
1. 以繁體中文作答。
2. 直接引用條款原文（用「」括起來）。
3. 標明出自哪份文件的第幾條（例如：保密協議 第五條）。
4. 若條款不足以完整回答，請明確說明「現有條款未涵蓋此情形」。

【回答】"""


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        title = c.get("doc_title", "")
        art = c.get("article_num", "")
        source_tag = f"[{title} {art}]"
        parts.append(f"{source_tag}\n{c['clause_text']}")
    return "\n\n---\n\n".join(parts)


def _call_ollama_llm(prompt: str) -> str:
    import requests
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def rag_query(
    question: str,
    doc_type: str | None = None,
    top_k: int = 5,
) -> dict:
    """
    完整 RAG 流程：
      1. hybrid_search 召回相關條款
      2. 組成 context 字串
      3. 呼叫 LLM 生成答案
      4. 回傳答案 + 出處清單（方便前端顯示引用來源）
    """
    chunks = hybrid_search(question, top_k=top_k, doc_type=doc_type)

    if not chunks:
        return {
            "question": question,
            "answer": "資料庫中未找到相關條款，請確認已執行 ETL Pipeline。",
            "sources": [],
        }

    context = _build_context(chunks)
    prompt = _PROMPT_TEMPLATE.format(context=context, question=question)

    try:
        answer = _call_ollama_llm(prompt)
    except Exception as e:
        answer = f"[LLM 暫時不可用：{e}]\n\n相關條款已召回，請直接參閱下方出處。"

    sources = [
        {
            "doc_title": c.get("doc_title", ""),
            "article_num": c.get("article_num", ""),
            "doc_type": c.get("doc_type", ""),
            "clause_type": c.get("clause_type", ""),
            "rrf_score": c.get("rrf_score", 0),
            "snippet": c["clause_text"][:200] + ("..." if len(c["clause_text"]) > 200 else ""),
        }
        for c in chunks
    ]

    return {"question": question, "answer": answer, "sources": sources}
