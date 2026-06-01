"""
共用文件讀取工具，支援 .txt 和 .pdf。
ETL Step 01 和 Step 02 都從這裡 import，避免重複邏輯。
"""
from __future__ import annotations
import re
from pathlib import Path


def _normalize_pdf_text(text: str) -> str:
    """
    勞動基準法 PDF 的條文格式是「第 1 條」（有空格），
    正規化成「第1條」讓 chunker 的 regex 能正確切分。
    """
    text = re.sub(
        r'第\s+([一二三四五六七八九十百零千\d]+)\s+條',
        r'第\1條',
        text,
    )
    text = re.sub(r'條\s+之\s+', r'條之', text)
    return text


def read_file_text(fp: Path) -> str:
    """讀取 .txt 或 .pdf，統一回傳 str。"""
    if fp.suffix.lower() == ".pdf":
        try:
            import pdfminer.high_level  # type: ignore[import]
            text = pdfminer.high_level.extract_text(str(fp))
        except ImportError:
            from pypdf import PdfReader  # type: ignore[import]
            reader = PdfReader(str(fp))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return _normalize_pdf_text(text)
    return fp.read_text(encoding="utf-8")
