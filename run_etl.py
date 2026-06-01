"""
ETL Pipeline Runner — 對應 fin-intel-query-core/run_pipeline.py

依序執行四個 ETL 步驟：
  01 → 文件進入系統（documents 表）
  02 → 條款擷取分塊（clauses + clauses_fts）
  03 → Metadata 正規化（clause_type + risk_level）
  04 → 向量索引建立（ChromaDB）

資料治理重點：每步驟獨立可重跑（幂等設計），
允許個別重建某個索引而不影響其他步驟。
"""
import subprocess
import sys
import time
from pathlib import Path

STEPS = [
    ("etl/01_ingest_raw_docs.py",   "Step 1：原始文件進入系統"),
    ("etl/02_extract_clauses.py",   "Step 2：條款擷取與分塊（法律 Chunking）"),
    ("etl/03_normalize_metadata.py","Step 3：Metadata 正規化（clause_type / risk_level）"),
    ("etl/04_build_vector_index.py","Step 4：向量索引建立（ChromaDB）"),
]

BASE_DIR = Path(__file__).resolve().parent


def run_pipeline():
    print("=" * 60)
    print("  Legal RAG Demo — ETL Pipeline")
    print("=" * 60)

    total_start = time.time()

    for script, desc in STEPS:
        print(f"\n{'─' * 60}")
        print(f"  {desc}")
        print(f"{'─' * 60}")
        t0 = time.time()

        result = subprocess.run(
            [sys.executable, str(BASE_DIR / script)],
            cwd=str(BASE_DIR),
        )

        elapsed = time.time() - t0
        if result.returncode != 0:
            print(f"\n[ERROR] {script} 失敗（returncode={result.returncode}），Pipeline 中止。")
            sys.exit(1)

        print(f"  完成（{elapsed:.1f}s）")

    total = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"  Pipeline 完成！總耗時 {total:.1f}s")
    print(f"  執行 `python app.py` 啟動 API Server")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
