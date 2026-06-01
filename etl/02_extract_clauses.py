"""
ETL Step 2 — 條款擷取與分塊

從 documents 表讀取已登錄文件，用法律專用 Chunker 切分條款，
寫入 clauses 表（結構化 metadata）與 clauses_fts 表（BM25 索引）。

法律 Chunking 策略（對應面試題一）：
  - full_article chunk：整條條文，確保跨子項目語意完整
  - sub_item chunk：一、二、三各自切分，提升精準召回
  - 兩種 chunk 都進 FTS5 索引，避免資訊遺漏
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db import connect
from utils.io import read_file_text
from rag.chunker import chunk_legal_document


def extract_all():
    with connect() as conn:
        docs = conn.execute("SELECT id, title, doc_type, file_path FROM documents").fetchall()

    if not docs:
        print("[02] documents 表為空，請先執行 01_ingest_raw_docs.py")
        return

    total_chunks = 0

    for doc in docs:
        doc_id = doc["id"]
        file_path = Path(doc["file_path"])

        if not file_path.exists():
            print(f"[02] 檔案不存在，跳過：{file_path}")
            continue

        text = read_file_text(file_path)
        chunks = chunk_legal_document(doc_id, text)

        with connect() as conn:
            for chunk in chunks:
                # 1. clauses 表（結構化，供 risk_tagger / compliance_check 使用）
                conn.execute(
                    "INSERT OR REPLACE INTO clauses "
                    "(chunk_id, doc_id, article_num, article_title, clause_text, chunk_type) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        chunk.article_num,
                        chunk.article_title,
                        chunk.clause_text,
                        chunk.chunk_type,
                    ),
                )

                # 2. clauses_fts 表（全文索引，供 BM25 搜尋使用）
                conn.execute(
                    "DELETE FROM clauses_fts WHERE chunk_id = ?", (chunk.chunk_id,)
                )
                conn.execute(
                    "INSERT INTO clauses_fts "
                    "(chunk_id, doc_id, doc_type, doc_title, article_num, clause_type, clause_text) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        doc["doc_type"],
                        doc["title"],
                        chunk.article_num,
                        "一般條款",
                        chunk.clause_text,
                    ),
                )

        print(f"[02] {doc_id}：{len(chunks)} 個 chunk")
        total_chunks += len(chunks)

    print(f"[02] 完成，共 {total_chunks} 個 chunk 寫入索引。")


if __name__ == "__main__":
    extract_all()
