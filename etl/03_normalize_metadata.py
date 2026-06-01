"""
ETL Step 3 — Metadata 正規化

對每個 clause 進行：
  1. clause_type 分類（保密義務、違約條款、不可抗力...）
  2. risk_level 評估（HIGH / MEDIUM / LOW）

資料治理意義：
  - 把非結構化法律文字轉成結構化欄位
  - 讓 API 支援按 clause_type / risk_level 過濾
  - 為 compliance_check 提供語意分類依據
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db import connect

CLAUSE_TYPE_RULES: list[tuple[str, str, list[str]]] = [
    # (clause_type, risk_level, [patterns...])
    ("定義條款",   "LOW",    [r"定義", r"係指", r"以下稱"]),
    ("保密義務",   "MEDIUM", [r"保密", r"不得.*揭露", r"保守.*秘密", r"機密"]),
    ("違約責任",   "HIGH",   [r"違約.*賠償", r"賠償.*損害", r"損害賠償", r"違約金"]),
    ("終止條款",   "HIGH",   [r"終止.*合約", r"合約.*終止", r"立即終止", r"資遣"]),
    ("逾期罰款",   "HIGH",   [r"逾期.*罰款", r"罰款", r"遲延.*損害"]),
    ("不可抗力",   "MEDIUM", [r"不可抗力", r"天災", r"戰爭", r"政府命令"]),
    ("競業禁止",   "HIGH",   [r"競業禁止", r"不得.*任職", r"不得.*服務"]),
    ("智財歸屬",   "MEDIUM", [r"著作人", r"專利.*申請", r"智慧財產", r"發明"]),
    ("付款條款",   "MEDIUM", [r"給付.*款項", r"付款", r"合約金額", r"報酬"]),
    ("爭議解決",   "LOW",    [r"管轄法院", r"仲裁", r"爭議.*解決", r"訴訟"]),
    ("驗收程序",   "MEDIUM", [r"驗收", r"查驗", r"確認.*完成"]),
    ("工時工資",   "MEDIUM", [r"工作時間", r"工資", r"薪資", r"加班"]),
    ("特別休假",   "LOW",    [r"特別休假", r"例假", r"休假"]),
]


def _classify(text: str) -> tuple[str, str]:
    for clause_type, risk_level, patterns in CLAUSE_TYPE_RULES:
        if any(re.search(p, text) for p in patterns):
            return clause_type, risk_level
    return "一般條款", "LOW"


def normalize_all():
    with connect() as conn:
        rows = conn.execute("SELECT chunk_id, clause_text FROM clauses").fetchall()

    if not rows:
        print("[03] clauses 表為空，請先執行 02_extract_clauses.py")
        return

    updates = []
    for row in rows:
        clause_type, risk_level = _classify(row["clause_text"])
        updates.append((clause_type, risk_level, row["chunk_id"]))

    with connect() as conn:
        conn.executemany(
            "UPDATE clauses SET clause_type = ?, risk_level = ? WHERE chunk_id = ?",
            updates,
        )
        # 同步更新 FTS5 表的 clause_type（BM25 排序時的輔助過濾欄位）
        for clause_type, _, chunk_id in updates:
            conn.execute(
                "UPDATE clauses_fts SET clause_type = ? WHERE chunk_id = ?",
                (clause_type, chunk_id),
            )

    type_counts: dict[str, int] = {}
    for clause_type, _, _ in updates:
        type_counts[clause_type] = type_counts.get(clause_type, 0) + 1

    print("[03] 條款分類結果：")
    for ctype, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"      {ctype}: {cnt}")
    print(f"[03] 完成，共更新 {len(updates)} 個 chunk。")


if __name__ == "__main__":
    normalize_all()
