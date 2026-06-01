"""
ETL Step 4 — 向量索引建立

從 clauses 表讀取所有 chunk，embed 後寫入 ChromaDB。
與 fin-intel-query-core Embedding/ 相同設計：
  - 使用 Ollama bge-m3（或 sentence-transformers fallback）
  - full_article + sub_item 全部進索引
  - metadata 存入 ChromaDB，支援 where 過濾

注意：full_article 和 sub_item 都進索引，有助於：
  - full_article：跨條款語意對比（哪一條最相關）
  - sub_item：精準定位到具體子項
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from utils.db import connect
from utils.embedding import get_embeddings_batch

CHROMA_PATH = str(Path(__file__).resolve().parent.parent / "data" / "chroma_db")
COLLECTION_NAME = "legal_clauses"
BATCH_SIZE = 16


def build_index():
    import chromadb

    with connect() as conn:
        rows = conn.execute(
            "SELECT c.chunk_id, c.doc_id, c.article_num, c.article_title, "
            "       c.clause_text, c.clause_type, c.risk_level, c.chunk_type, "
            "       d.title AS doc_title, d.doc_type "
            "FROM clauses c "
            "JOIN documents d ON c.doc_id = d.id"
        ).fetchall()

    if not rows:
        print("[04] clauses 表為空，請先執行前三步 ETL。")
        return

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # 重建 collection（幂等）
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"[04] 開始 embedding {len(rows)} 個 chunk（model: bge-m3 or fallback）")

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i: i + BATCH_SIZE]
        texts = [r["clause_text"] for r in batch]
        embeddings = get_embeddings_batch(texts)

        collection.add(
            ids=[r["chunk_id"] for r in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["doc_id"],
                    "doc_type": r["doc_type"],
                    "doc_title": r["doc_title"],
                    "article_num": r["article_num"],
                    "article_title": r["article_title"],
                    "clause_type": r["clause_type"],
                    "risk_level": r["risk_level"],
                    "chunk_type": r["chunk_type"],
                }
                for r in batch
            ],
        )
        print(f"[04]   {min(i + BATCH_SIZE, len(rows))}/{len(rows)} chunks indexed")

    print(f"[04] 完成，ChromaDB collection '{COLLECTION_NAME}' 共 {collection.count()} 筆。")


if __name__ == "__main__":
    build_index()
