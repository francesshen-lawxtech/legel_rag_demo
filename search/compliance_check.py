"""
合規規則引擎（對應面試題二：合規流程自動化）

對已分析之合約，逐一檢查是否符合適用法律的強制規定。
這模擬律師事務所合規審查（Compliance Review）的核心邏輯：
  不只找「條款在哪裡」，而是檢查「條款內容是否合法合規」。

架構說明：
  RULES dict 以 doc_type 為 key，每份規則含：
    - law：依據法條
    - check：接收所有條款文字 list 的 callable，回傳 bool
    - fail_msg：違規說明（面試時說明此為律師審閱意見的自動化）
"""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path

from utils.db import DB_PATH

ComplianceRule = dict  # type alias for readability

RULES: dict[str, list[ComplianceRule]] = {
    "勞動契約": [
        {
            "id": "LAB-001",
            "law": "勞動基準法第38條",
            "desc": "特別休假規定",
            "check": lambda texts: any(re.search(r"特別休假", t) for t in texts),
            "pass_msg": "合約已明確規範特別休假",
            "fail_msg": "合約缺少特別休假條款，違反勞動基準法第38條",
        },
        {
            "id": "LAB-002",
            "law": "勞動基準法第9-1條",
            "desc": "競業禁止應附補償金",
            "check": lambda texts: (
                not any(re.search(r"競業禁止", t) for t in texts)
                or any(re.search(r"競業禁止.{0,50}補償|補償.{0,50}競業", t, re.DOTALL) for t in texts)
            ),
            "pass_msg": "競業禁止條款附有合理補償",
            "fail_msg": "競業禁止條款未附補償金，依勞動基準法第9-1條可能無效",
        },
        {
            "id": "LAB-003",
            "law": "勞動基準法第30條",
            "desc": "每週工時上限",
            "check": lambda texts: any(re.search(r"四十小時|40小時", t) for t in texts),
            "pass_msg": "合約已規範每週工時上限四十小時",
            "fail_msg": "合約未明確規範每週四十小時工時上限",
        },
        {
            "id": "LAB-004",
            "law": "勞動基準法第12條",
            "desc": "資遣程序",
            "check": lambda texts: any(re.search(r"資遣|預告", t) for t in texts),
            "pass_msg": "合約包含資遣預告規定",
            "fail_msg": "合約缺少資遣預告條款",
        },
    ],
    "採購合約": [
        {
            "id": "GOV-001",
            "law": "政府採購法（逾期罰款上限慣例）",
            "desc": "逾期罰款不超過合約金額10%",
            "check": lambda texts: any(re.search(r"百分之十|10%", t) for t in texts),
            "pass_msg": "逾期罰款上限已設定為合約金額的10%",
            "fail_msg": "建議明確設定逾期罰款上限（慣例為合約金額10%）",
        },
        {
            "id": "GOV-002",
            "law": "政府採購法第71條",
            "desc": "驗收程序",
            "check": lambda texts: any(re.search(r"驗收", t) for t in texts),
            "pass_msg": "合約包含驗收程序",
            "fail_msg": "政府採購合約應包含明確驗收程序，違反採購法第71條",
        },
        {
            "id": "GOV-003",
            "law": "政府採購法第63條",
            "desc": "不可抗力條款",
            "check": lambda texts: any(re.search(r"不可抗力", t) for t in texts),
            "pass_msg": "合約已規範不可抗力免責條款",
            "fail_msg": "建議加入不可抗力條款以保障雙方權益",
        },
    ],
    "NDA": [
        {
            "id": "NDA-001",
            "law": "營業秘密法第2條",
            "desc": "保密資訊定義明確性",
            "check": lambda texts: any(re.search(r"保密資訊.*係指|「保密資訊」", t) for t in texts),
            "pass_msg": "保密資訊定義明確",
            "fail_msg": "保密資訊定義不夠明確，可能導致保護範圍爭議",
        },
        {
            "id": "NDA-002",
            "law": "民法第247-1條（定型化契約限制）",
            "desc": "例外情形條款",
            "check": lambda texts: any(re.search(r"例外|不受.*保密", t) for t in texts),
            "pass_msg": "合約已列明保密義務的例外情形",
            "fail_msg": "缺少例外情形條款（如已公開資訊），合約可能失衡",
        },
        {
            "id": "NDA-003",
            "law": "民法第247-1條",
            "desc": "違約賠償範圍合理性",
            "check": lambda texts: any(re.search(r"損害賠償|賠償.*損害", t) for t in texts),
            "pass_msg": "合約已規範違約賠償責任",
            "fail_msg": "缺少違約賠償條款，揭露方保障不足",
        },
    ],
}


def check_compliance(doc_id: str) -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    doc = dict(conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())
    clause_rows = conn.execute(
        "SELECT clause_text FROM clauses WHERE doc_id = ? AND chunk_type = 'full_article'",
        (doc_id,),
    ).fetchall()
    conn.close()

    clause_texts = [r["clause_text"] for r in clause_rows]
    doc_type = doc["doc_type"]
    rules = RULES.get(doc_type, [])

    results = []
    for rule in rules:
        try:
            passed = rule["check"](clause_texts)
        except Exception:
            passed = False

        results.append({
            "rule_id":     rule["id"],
            "law":         rule["law"],
            "description": rule["desc"],
            "passed":      passed,
            "message":     rule["pass_msg"] if passed else rule["fail_msg"],
        })

    return {
        "doc_id":       doc_id,
        "doc_title":    doc["title"],
        "doc_type":     doc_type,
        "total_rules":  len(results),
        "passed":       sum(1 for r in results if r["passed"]),
        "failed":       sum(1 for r in results if not r["passed"]),
        "results":      results,
    }
