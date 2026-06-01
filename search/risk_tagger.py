"""
合約風險條款自動標記（對應面試題二：律師事務所實務經驗）

律師事務所審閱合約的第一步是找出「高風險條款」。
這個模組模擬該流程：對合約所有條款做 rule-based 風險掃描，
輸出結構化的風險清單，供律師快速聚焦。

實務說明（面試時可講）：
  在事務所時審閱合約，違約賠償、免責條款、競業禁止是最常
  需要逐字審查的段落。自動標記可讓律師把時間集中在高風險條款，
  低風險的定義條款、管轄條款可快速帶過。
"""
from __future__ import annotations
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from utils.db import DB_PATH


@dataclass
class RiskItem:
    chunk_id: str
    article_num: str
    article_title: str
    risk_level: str        # HIGH | MEDIUM | LOW
    risk_type: str         # 違約賠償 | 競業禁止 | ...
    matched_text: str      # 觸發規則的文字片段
    clause_snippet: str    # 條款前 150 字（預覽用）


_HIGH: list[tuple[str, str]] = [
    ("違約賠償",   r"違約.*賠償|損害賠償|賠償.*損害"),
    ("終止合約",   r"立即終止|終止.*合約|合約.*終止"),
    ("逾期罰款",   r"逾期.*罰款|罰款.*逾期|違約金"),
    ("競業禁止",   r"競業禁止"),
    ("免責條款",   r"不負.*責任|免除.*責任|不得.*請求.*賠償"),
]

_MEDIUM: list[tuple[str, str]] = [
    ("保密義務",   r"保密.*義務|不得.*揭露|保守.*秘密"),
    ("智財歸屬",   r"著作人|專利.*申請|智慧財產"),
    ("單方終止",   r"不附理由.*終止|得.*書面.*終止"),
    ("分包限制",   r"分包.*同意|分包.*比例|轉包"),
    ("付款條件",   r"逾期.*利息|付款.*期限"),
]

_LOW: list[tuple[str, str]] = [
    ("管轄條款",   r"管轄法院|第一審管轄"),
    ("準據法",     r"準據法|適用.*法律"),
    ("通知義務",   r"書面通知|應.*通知"),
    ("可分條款",   r"條款如經.*無效|其餘條款.*有效"),
]


def tag_risks(clauses: list[dict]) -> list[RiskItem]:
    results: list[RiskItem] = []
    for clause in clauses:
        text = clause.get("clause_text", "")
        chunk_id = clause.get("chunk_id", "")
        article_num = clause.get("article_num", "")
        article_title = clause.get("article_title", "")
        snippet = text[:150]

        for risk_type, pattern in _HIGH:
            m = re.search(pattern, text)
            if m:
                results.append(RiskItem(chunk_id, article_num, article_title,
                                        "HIGH", risk_type, m.group(0), snippet))

        for risk_type, pattern in _MEDIUM:
            m = re.search(pattern, text)
            if m:
                results.append(RiskItem(chunk_id, article_num, article_title,
                                        "MEDIUM", risk_type, m.group(0), snippet))

        for risk_type, pattern in _LOW:
            m = re.search(pattern, text)
            if m:
                results.append(RiskItem(chunk_id, article_num, article_title,
                                        "LOW", risk_type, m.group(0), snippet))

    _ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(results, key=lambda x: _ORDER[x.risk_level])


def analyze_document(doc_id: str) -> dict:
    """給定文件 ID，回傳完整風險分析報告。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT chunk_id, article_num, article_title, clause_text "
        "FROM clauses WHERE doc_id = ? AND chunk_type = 'full_article'",
        (doc_id,),
    ).fetchall()
    conn.close()

    clauses = [dict(r) for r in rows]
    risks = tag_risks(clauses)

    return {
        "doc_id": doc_id,
        "total_articles": len(clauses),
        "risk_summary": {
            "HIGH":   sum(1 for r in risks if r.risk_level == "HIGH"),
            "MEDIUM": sum(1 for r in risks if r.risk_level == "MEDIUM"),
            "LOW":    sum(1 for r in risks if r.risk_level == "LOW"),
        },
        "risk_items": [
            {
                "article_num":   r.article_num,
                "article_title": r.article_title,
                "risk_level":    r.risk_level,
                "risk_type":     r.risk_type,
                "matched_text":  r.matched_text,
                "snippet":       r.clause_snippet,
            }
            for r in risks
        ],
    }
