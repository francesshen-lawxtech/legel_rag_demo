"""
法律文件專用 Chunker

策略：
  - 以「第X條」或「第X條之Y」為主要切分點
  - 每條再以「一、二、三」為次級切分點
  - 同時保留 full_article chunk 供上下文使用
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# 支援：第一條、第三十八條、第九條之一、第九條之二
ARTICLE_RE = re.compile(
    r"^第([一二三四五六七八九十百零千\d]+)條(之[一二三四五六七八九十]+)?\s*(.*)?$"
)
SUB_ITEM_RE    = re.compile(r"^([一二三四五六七八九十]+)、\s*(.*)$")
SUB_SUB_ITEM_RE = re.compile(r"^（([一二三四五六七八九十]+)）\s*(.*)$")


@dataclass
class LegalChunk:
    doc_id: str
    chunk_id: str
    article_num: str      # e.g. "第五條" / "第九條之一"
    article_title: str
    clause_text: str
    chunk_type: str       # "full_article" | "sub_item"
    source_lines: list[str] = field(default_factory=list)


def chunk_legal_document(doc_id: str, text: str) -> list[LegalChunk]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    chunks: list[LegalChunk] = []

    current_article_num   = ""   # e.g. "九" / "九之一"
    current_article_title = ""
    current_lines: list[str] = []

    def _flush():
        if current_article_num and current_lines:
            chunks.extend(
                _build_article_chunks(
                    doc_id, current_article_num, current_article_title, current_lines
                )
            )

    for line in lines:
        m = ARTICLE_RE.match(line)
        if m:
            _flush()
            base_num  = m.group(1)                   # "九"
            zhi_part  = m.group(2) or ""             # "之一" or ""
            current_article_num   = base_num + zhi_part   # "九" / "九之一"
            current_article_title = (m.group(3) or "").strip()
            current_lines = []
        else:
            current_lines.append(line)

    _flush()
    return chunks


def _build_article_chunks(
    doc_id: str,
    article_num: str,    # "九" or "九之一"
    article_title: str,
    lines: list[str],
) -> list[LegalChunk]:
    chunks: list[LegalChunk] = []

    # 建立顯示標籤："第九條" or "第九條之一"
    if "之" in article_num:
        base, zhi = article_num.split("之", 1)
        label = f"第{base}條之{zhi}"
    else:
        label = f"第{article_num}條"

    header = f"{label} {article_title}".strip()

    # full_article chunk
    full_text = header + "\n" + "\n".join(lines)
    chunks.append(
        LegalChunk(
            doc_id=doc_id,
            chunk_id=f"{doc_id}__{article_num}__full",
            article_num=label,
            article_title=article_title,
            clause_text=full_text,
            chunk_type="full_article",
            source_lines=lines,
        )
    )

    # sub_item chunks（一、二、三）
    current_sub: str | None = None
    sub_lines: dict[str, list[str]] = {}

    for line in lines:
        m = SUB_ITEM_RE.match(line)
        if m:
            current_sub = m.group(1)
            sub_lines[current_sub] = [line]
        elif current_sub:
            sub_lines[current_sub].append(line)

    for sub_num, sl in sub_lines.items():
        sub_text = f"{header}\n" + "\n".join(sl)
        chunks.append(
            LegalChunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}__{article_num}__{sub_num}",
                article_num=label,
                article_title=article_title,
                clause_text=sub_text,
                chunk_type="sub_item",
                source_lines=sl,
            )
        )

    return chunks
