"""
ETL Step 1 — 原始文件進入系統

支援 .txt 與 .pdf 兩種格式，自動辨識文件類型：
  - 有標準 metadata header（文件編號、文件類型）→ 直接解析
  - 無 header（如法規 PDF）→ 從檔名與內容推測 doc_type，自動生成 doc_id
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db import connect, init_db
from utils.io import read_file_text

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

DOC_ID_RE   = re.compile(r"文件編號[：:]\s*(\S+)")
DOC_TYPE_RE = re.compile(r"文件類型[：:]\s*(\S+)")
DATE_RE     = re.compile(r"生效日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日")

_FILENAME_TYPE: list[tuple[list[str], str]] = [
    (["勞動基準法", "labor_law", "勞基法", "enforcement"], "法規"),
    (["採購法", "procurement_law"],                        "法規"),
    (["NDA", "保密"],                                      "NDA"),
    (["勞動契約", "labor_contract", "labor_example"],      "勞動契約"),
    (["採購合約", "supply", "procurement"],                "採購合約"),
]


def _guess_doc_type(filename: str, text: str) -> str:
    name = filename.lower()
    for keywords, doc_type in _FILENAME_TYPE:
        if any(kw.lower() in name for kw in keywords):
            return doc_type
    snippet = text[:300]
    for keywords, doc_type in _FILENAME_TYPE:
        if any(kw in snippet for kw in keywords):
            return doc_type
    return "未知"


def _parse_metadata(text: str, file_path: Path) -> dict:
    doc_id_m   = DOC_ID_RE.search(text)
    doc_type_m = DOC_TYPE_RE.search(text)
    date_m     = DATE_RE.search(text)

    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), file_path.stem)
    title    = first_line[:60]
    doc_id   = doc_id_m.group(1)   if doc_id_m   else file_path.stem
    doc_type = doc_type_m.group(1) if doc_type_m else _guess_doc_type(file_path.stem, text)
    effective_date = (
        f"{date_m.group(1)}-{int(date_m.group(2)):02d}-{int(date_m.group(3)):02d}"
        if date_m else None
    )

    return {
        "id":             doc_id,
        "title":          title,
        "doc_type":       doc_type,
        "effective_date": effective_date,
        "file_path":      str(file_path),
    }


def ingest_all():
    init_db()

    files = list(RAW_DIR.glob("*.txt")) + list(RAW_DIR.glob("*.pdf"))
    if not files:
        print(f"[01] 找不到 .txt / .pdf 檔案：{RAW_DIR}")
        return

    with connect() as conn:
        inserted = 0
        for fp in files:
            try:
                text = read_file_text(fp)
            except Exception as e:
                print(f"[01] 無法讀取 {fp.name}：{e}")
                continue

            meta = _parse_metadata(text, fp)

            existing = conn.execute(
                "SELECT id FROM documents WHERE id = ?", (meta["id"],)
            ).fetchone()
            if existing:
                print(f"[01] 跳過（已存在）：{meta['id']}")
                continue

            conn.execute(
                "INSERT INTO documents (id, title, doc_type, effective_date, file_path) "
                "VALUES (:id, :title, :doc_type, :effective_date, :file_path)",
                meta,
            )
            print(f"[01] 匯入：{meta['id']} | {meta['doc_type']} | {meta['title']}")
            inserted += 1

    print(f"[01] 完成，新增 {inserted} 份文件。")


if __name__ == "__main__":
    ingest_all()
