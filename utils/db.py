from __future__ import annotations
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "legal_docs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    doc_type        TEXT NOT NULL,
    jurisdiction    TEXT DEFAULT '中華民國',
    effective_date  TEXT,
    file_path       TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS clauses (
    chunk_id        TEXT PRIMARY KEY,
    doc_id          TEXT NOT NULL,
    article_num     TEXT,
    article_title   TEXT,
    clause_text     TEXT NOT NULL,
    chunk_type      TEXT,
    clause_type     TEXT DEFAULT '一般條款',
    risk_level      TEXT DEFAULT 'LOW',
    FOREIGN KEY(doc_id) REFERENCES documents(id)
);

-- FTS5 虛擬表：支援 BM25 全文搜尋
-- UNINDEXED 欄位只儲存、不建索引，用於後續過濾
CREATE VIRTUAL TABLE IF NOT EXISTS clauses_fts USING fts5(
    chunk_id    UNINDEXED,
    doc_id      UNINDEXED,
    doc_type    UNINDEXED,
    doc_title   UNINDEXED,
    article_num UNINDEXED,
    clause_type UNINDEXED,
    clause_text,
    tokenize='unicode61 remove_diacritics 1'
);
"""

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)
    print(f"[db] Initialized: {DB_PATH}")
