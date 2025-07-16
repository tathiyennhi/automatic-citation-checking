#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_refs.py  –  Trích riêng block References của 1 PDF
bằng 3 thư viện:  pdfplumber, PyMuPDF (fitz), pdfminer.six.

Tạo 3 file txt trong cùng thư mục:
    • refs_pdfplumber.txt
    • refs_pymupdf.txt
    • refs_pdfminer.txt

Thư viện cần:
    pip install pdfplumber pymupdf pdfminer.six
"""

import re
import sys
from pathlib import Path

import pdfplumber
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text


# ---------- 0. Tham số ----------
PDF_PATH = "paper.pdf"           
OUT_TEMPLATE = "refs_{lib}.txt"  
REF_PATTERN = re.compile(r"\bReferences\b", re.IGNORECASE)  


# ---------- 1. Hàm extract text thô ----------
def extract_with_pdfplumber(path: str) -> str:
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pg = page.extract_text()
            if pg:
                text.append(pg)
    return "\n".join(text)


def extract_with_pymupdf(path: str) -> str:
    text = []
    doc = fitz.open(path)
    for page in doc:
        text.append(page.get_text())
    return "\n".join(text)


def extract_with_pdfminer(path: str) -> str:
    return extract_text(path)


# Map lib name → callable
EXTRACTORS = {
    "pdfplumber": extract_with_pdfplumber,
    "pymupdf": extract_with_pymupdf,
    "pdfminer": extract_with_pdfminer,
}


# ---------- 2. Lấy block References ----------
def get_reference_block(full_text: str) -> str:
    """
    Cắt từ tiêu đề 'References' (hoặc 'REFERENCES') tới hết file.
    Nếu không tìm thấy thì trả string rỗng.
    """
    m = REF_PATTERN.search(full_text)
    if not m:
        return ""
    return full_text[m.start():].strip()


def save_text(text: str, libname: str, out_dir: Path):
    out_path = out_dir / OUT_TEMPLATE.format(lib=libname)
    out_path.write_text(text, encoding="utf-8")
    print(f"✔ Đã ghi {out_path.relative_to(Path.cwd())}  "
          f"({len(text):,} ký tự)")


def main(pdf_path: str):
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        sys.exit(f"❌ Không tìm thấy file: {pdf_path}")

    out_dir = pdf_path.parent  

    for lib, extractor in EXTRACTORS.items():
        try:
            full_text = extractor(str(pdf_path))
            ref_block = get_reference_block(full_text)
            if ref_block:
                save_text(ref_block, lib, out_dir)
            else:
                save_text("[Không tìm thấy tiêu đề 'References'...]", lib, out_dir)
        except Exception as e:
            err_msg = f"[Lỗi khi chạy {lib}: {e}]"
            save_text(err_msg, lib, out_dir)


if __name__ == "__main__":
    main(PDF_PATH)
