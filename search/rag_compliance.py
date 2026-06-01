"""
RAG-based Compliance Checker（取代 hardcoded regex rules）

架構說明：
  傳統做法 → regex 掃描合約關鍵字，判斷是否「有提到」某條款
  本模組    → 把勞基法（法規）和合約都 ingest 進 ChromaDB，
              讓 LLM 對照法條內容判斷合約是否「符合」法律要求

Flow：
  1. 對每個合規維度，vector_search 各取 2 塊：
     a. doc_type="法規"  → 找到最相關的勞基法條文
     b. doc_id=合約id    → 找到合約中最相關的條款
  2. 組成 prompt，請 LLM 給出：符合 / 不符合 / 條款缺失 / 無法判斷
  3. 回傳結構化結果（verdict + reasoning + 兩邊原文 evidence）
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from utils.db import DB_PATH
from rag.retriever import vector_search

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL  = os.getenv("LLM_MODEL",  "qwen2.5:3b")

# ─── 合規維度定義 ──────────────────────────────────────────────────────────────
# 每個維度定義：
#   law_query      → 用來從「法規」文件搜法條的關鍵字
#   contract_query → 用來從「合約」文件搜對應條款的關鍵字

COMPLIANCE_DIMENSIONS = [
    {
        "id":             "LSA-38",
        "category":       "特別休假",
        "question":       "勞動契約是否依勞動基準法第38條明確規定特別休假天數？",
        "law_query":      "特別休假天數規定",
        "contract_query": "特別休假",
    },
    {
        "id":             "LSA-9-1",
        "category":       "競業禁止補償",
        "question":       "若合約訂有競業禁止條款，是否依勞動基準法第9條之1附有合理補償金？",
        "law_query":      "競業禁止合理補償金",
        "contract_query": "競業禁止補償",
    },
    {
        "id":             "LSA-30",
        "category":       "正常工時",
        "question":       "合約是否符合勞動基準法第30條每週正常工時不超過40小時的規定？",
        "law_query":      "正常工作時間每週四十小時",
        "contract_query": "工作時間每週小時",
    },
    {
        "id":             "LSA-26",
        "category":       "禁止預扣工資",
        "question":       "合約是否符合勞動基準法第26條，未以預扣工資作違約金或賠償？",
        "law_query":      "禁止預扣工資違約金賠償",
        "contract_query": "工資違約金預扣",
    },
    {
        "id":             "LSA-16",
        "category":       "終止預告期",
        "question":       "合約是否依勞動基準法第16條規定雇主終止契約前應有預告期？",
        "law_query":      "雇主預告終止契約期間",
        "contract_query": "資遣預告終止契約",
    },
    {
        "id":             "LSA-50",
        "category":       "產假保護",
        "question":       "合約是否提及或未違反勞動基準法第50條女工產假權利？",
        "law_query":      "產假女工分娩停止工作",
        "contract_query": "產假休假女工",
    },
    {
        "id":             "LSA-17",
        "category":       "資遣費",
        "question":       "合約是否依勞動基準法第17條規定計算並給付資遣費？",
        "law_query":      "資遣費計算給付勞動基準法",
        "contract_query": "資遣費",
    },
]

# ─── Prompt ──────────────────────────────────────────────────────────────────

_PROMPT = """\
你是法律合規審查助理。請根據【相關法規條文】，判斷【合約條款】是否符合法律要求。

【審查問題】：{question}

【相關法規條文】：
{law_context}

【合約相關條款】：
{contract_context}

請嚴格按照以下格式回覆（不要加其他文字）：
判斷結果：符合 / 不符合 / 條款缺失 / 無法判斷
理由：（一段話，直接引用法規條文與合約條款中的具體文字）"""


def _call_llm(prompt: str) -> str:
    import requests
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _parse_verdict(text: str) -> tuple[str, str]:
    verdict = "無法判斷"
    for v in ["不符合", "條款缺失", "符合", "無法判斷"]:
        if v in text:
            verdict = v
            break
    reasoning = text
    for sep in ["理由：", "理由:"]:
        if sep in text:
            reasoning = text.split(sep, 1)[1].strip()
            break
    return verdict, reasoning


# ─── 主函式 ──────────────────────────────────────────────────────────────────

def rag_compliance_check(doc_id: str) -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()

    if not row:
        raise ValueError(f"找不到文件：{doc_id}")

    doc = dict(row)
    doc_type = doc["doc_type"]
    results = []

    for dim in COMPLIANCE_DIMENSIONS:
        # 1. 搜法規條文（doc_type="法規"）
        try:
            law_chunks = vector_search(dim["law_query"], top_k=2, doc_type="法規")
            law_context = "\n\n---\n\n".join(
                c["clause_text"][:500] for c in law_chunks
            ) or "（法規索引尚未建立，請先 ingest labor_law.pdf 並執行 ETL）"
        except Exception as e:
            law_context = f"（法規索引不可用：{e}）"
            law_chunks = []

        # 2. 搜合約條款（限定 doc_id）
        try:
            contract_chunks = vector_search(
                dim["contract_query"], top_k=2, doc_id=doc_id
            )
            contract_context = "\n\n---\n\n".join(
                c["clause_text"][:500] for c in contract_chunks
            ) or "（合約中未找到相關條款）"
        except Exception as e:
            contract_context = f"（合約索引不可用：{e}）"
            contract_chunks = []

        # 3. LLM 判斷
        prompt = _PROMPT.format(
            question=dim["question"],
            law_context=law_context,
            contract_context=contract_context,
        )
        try:
            raw = _call_llm(prompt)
            verdict, reasoning = _parse_verdict(raw)
        except Exception as e:
            verdict   = "無法判斷"
            reasoning = f"LLM 不可用：{e}"

        results.append({
            "id":                dim["id"],
            "category":          dim["category"],
            "question":          dim["question"],
            "verdict":           verdict,
            "reasoning":         reasoning,
            "law_evidence":      [c["clause_text"][:250] for c in law_chunks],
            "contract_evidence": [c["clause_text"][:250] for c in contract_chunks],
        })

    return {
        "doc_id":    doc_id,
        "doc_title": doc["title"],
        "doc_type":  doc_type,
        "method":    "rag",
        "total":     len(results),
        "passed":    sum(1 for r in results if r["verdict"] == "符合"),
        "failed":    sum(1 for r in results if r["verdict"] in ("不符合", "條款缺失")),
        "results":   results,
    }
