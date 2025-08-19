#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import logging
from pathlib import Path

# ============== CONFIG ==============
PDF_PATH = Path("paper.pdf")         
OUTPUT_DIR = Path("./contexts")      
CONTEXT_SENTENCES = 5                
MIN_SENT_LEN = 20                  
# ====================================

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# --------- Regex: nhóm citation APA trong ngoặc (group) ---------
CITATION_GROUP = re.compile(r"""
    \(
      (?=[^)]*\b(?:19|20)\d{2}[a-z]?\b)                                     # has year
      (?=[^)]*(?:[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)*|et\s+al\.))  # có tác giả/et al.
      (?![^)]*\b(?:Fig(?:\.|ure)?|Table|Tab(?:\.|le)?|Sect(?:\.|ion|ions)?|Eq(?:\.|uation)?|Exp(?:\.|eriment|eriments)?|Alg(?:\.|orithm)?)\b)
      [^)]*
    \)
""", re.VERBOSE)

# --------- Regex: citation APA type narrative (Author ... (1995, 2004)) ---------
CITATION_NARR = re.compile(r"""
    \b
    (?P<authors>
        [A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+
        (?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)*
        |                                    # hoặc
        [A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+et\s+al\.)?
    )
    \s*\(\s*
    (?P<years>(?:19|20)\d{2}[a-z]?(?:\s*,\s*(?:19|20)\d{2}[a-z]?)*)   # 1995 hoặc 1995, 2004
    \s*\)
""", re.VERBOSE)

YEAR_RE = re.compile(r'\b(?:19|20)\d{2}[a-z]?\b')
NOISE_BEFORE = {'fig', 'figure', 'table', 'tab', 'sect', 'section', 'sections',
                'eq', 'equation', 'exp', 'experiment', 'experiments', 'alg', 'algorithm'}

# ============== PDF & Text utils ==============
def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        logger.error("❌ Chưa cài pdfplumber. Cài: pip install pdfplumber")
        sys.exit(1)
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            txt = p.extract_text()
            if txt:
                pages.append(txt)
    return "\n".join(pages)

def clean_text(text: str) -> str:
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)  # nối từ bị ngắt dòng
    text = re.sub(r"[ \t\r\f\v]+", " ", text)             # gọn whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()

def remove_front_matter(text: str) -> str:
    """
    Cắt phần đầu (Keywords, email, DOI...) → bắt đầu từ Abstract/Introduction/Background
    (chọn mốc sớm nhất nếu có).
    """
    anchors = [r"\bAbstract\b", r"\bIntroduction\b", r"\b1\.\s*Introduction\b", r"\bBackground\b"]
    hits = []
    for pat in anchors:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            hits.append(m.start())
    if hits:
        cut = min(hits)
        return text[cut:].lstrip()
    return text

def remove_references_section(text: str) -> str:
    m = re.search(r"\n\s*References?\s*\n", text, flags=re.IGNORECASE)
    if m:
        # chỉ cắt nếu References ở nửa sau tài liệu
        if m.start() > len(text) * 0.5:
            return text[:m.start()].rstrip()
    return text

def split_into_sentences(text: str) -> list:
    raw = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    sents = []
    for s in raw:
        s = re.sub(r"\s+", " ", s).strip()
        if s and len(s) >= MIN_SENT_LEN:
            sents.append(s)
    return sents

# ============== Citation helpers ==============
def _prev_token(s: str) -> str:
    m = re.search(r"(\b[A-Za-z]+)\W*$", s)
    return (m.group(1) if m else "").lower()

def _is_real_group(full_text: str, match: re.Match) -> bool:
    frag = match.group(0)
    if not YEAR_RE.search(frag):
        return False
    if re.fullmatch(r"\([A-Z]{2,}\s*\d{1,3}\)", frag):  # (FIG 12), (EQ 5)...
        return False
    left = full_text[max(0, match.start()-30):match.start()]
    if _prev_token(left) in NOISE_BEFORE:
        return False
    return True

def parse_apa_group(group_text: str) -> list[str]:
    """
    Tách 1 nhóm APA trong ngoặc thành các mục đơn lẻ:
    - split theo ';'
    - nếu mục kiểu "Authors, 1995, 2004" -> expand thành "Authors, 1995" & "Authors, 2004"
    - loại mục chỉ có năm (year-only)
    """
    inner = group_text.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]

    items = [p.strip() for p in inner.split(";") if p.strip()]
    out = []
    author_years_pat = re.compile(
        r"^(?P<authors>.+?),\s*(?P<years>(?:\d{4}[a-z]?)(?:\s*,\s*\d{4}[a-z]?)*)(?:\D.*)?$"
    )

    for it in items:
        m = author_years_pat.match(it)
        if m:
            authors = m.group("authors").strip()
            yrs = re.findall(r"\b(?:19|20)\d{2}[a-z]?\b", m.group("years"))
            for y in yrs:
                out.append(f"{authors}, {y}")
            continue

        m2 = re.search(r"(.+?),\s*((?:19|20)\d{2}[a-z]?)", it)
        if m2:
            out.append(f"{m2.group(1).strip()}, {m2.group(2)}")
            continue

        # year-only -> bỏ
        if YEAR_RE.search(it):
            continue

    return out

def replace_group_citations(text: str, start_from: int) -> tuple[str, int]:
    """Thay nhóm APA trong ngoặc thành các marker; trả (marked_text, next_index)."""
    parts = []
    last = 0
    idx = start_from

    for m in CITATION_GROUP.finditer(text):
        if not _is_real_group(text, m):
            continue
        s, e = m.span()
        parts.append(text[last:s])

        entries = parse_apa_group(m.group(0))
        parts.append("".join(f"[CITATION_{k}]" for k in range(idx, idx + len(entries))))
        idx += len(entries)
        last = e

    parts.append(text[last:])
    marked = "".join(parts)
    marked = re.sub(r"\s+\[CITATION_", " [CITATION_", marked)
    marked = re.sub(r"\[CITATION_(\d+)\]\s+", r"[CITATION_\1] ", marked)
    return marked.strip(), idx

def replace_narrative_citations(text: str, start_from: int) -> tuple[str, int]:
    """
    Thay citation kiểu narrative: "Authors (1995, 2004)" → "[CITATION_1][CITATION_2]"
    (thay **cả cụm** "Authors (years)" bằng chuỗi marker)
    """
    parts = []
    last = 0
    idx = start_from

    for m in CITATION_NARR.finditer(text):
        s, e = m.span()
        parts.append(text[last:s])

        years = re.findall(r"(?:19|20)\d{2}[a-z]?", m.group("years"))
        parts.append("".join(f"[CITATION_{k}]" for k in range(idx, idx + len(years))))
        idx += len(years)
        last = e

    parts.append(text[last:])
    marked = "".join(parts)
    marked = re.sub(r"\s+\[CITATION_", " [CITATION_", marked)
    marked = re.sub(r"\[CITATION_(\d+)\]\s+", r"[CITATION_\1] ", marked)
    return marked.strip(), idx

def replace_all_citations(text: str, start_from: int = 1) -> tuple[str, int]:
    """
    Áp dụng narrative trước, rồi group (để tránh trùng lặp).
    Trả: (marked_text, next_index)
    """
    t, idx = replace_narrative_citations(text, start_from)
    t, idx = replace_group_citations(t, idx)
    return t, idx

def has_any_citation(sentence: str) -> bool:
    return bool(CITATION_NARR.search(sentence) or CITATION_GROUP.search(sentence))

# ============== Build contexts ==============
def create_contexts(sentences: list) -> list:
    """
    Với MỖI câu có citation:
      - lấy 5 câu trước & 5 câu sau
      - tạo 2 phiên bản: orig_text (gốc), marked_text (đã marker)
      - marker đếm từ 1 cho TỪNG context
    """
    contexts = []
    for i, sent in enumerate(sentences):
        if not has_any_citation(sent):
            continue

        start = max(0, i - CONTEXT_SENTENCES)
        end = min(len(sentences), i + CONTEXT_SENTENCES + 1)
        ctx_sents = sentences[start:end]

        orig_text = " ".join(ctx_sents)

        # reset marker index cho từng context
        marked_sents = []
        next_idx = 1
        for s in ctx_sents:
            marked, next_idx = replace_all_citations(s, start_from=next_idx)
            marked_sents.append(marked)
        marked_text = " ".join(marked_sents)

        contexts.append({
            "context_id": len(contexts) + 1,
            "orig_text": orig_text,
            "marked_text": marked_text,
            "range": [start, end - 1],
            "anchor_index": i
        })
    return contexts

# ============== Save outputs ==============
def save_datasets(contexts: list):
    OUTPUT_DIR.mkdir(exist_ok=True)
    for ctx in contexts:
        base = OUTPUT_DIR / f"context_{ctx['context_id']:03d}"
        # .in = RAW GỐC
        with open(base.with_suffix(".in"), "w", encoding="utf-8") as f_in:
            f_in.write(ctx["orig_text"])
        # .label = CHỈ TEXT ĐÃ MARKER
        with open(base.with_suffix(".label"), "w", encoding="utf-8") as f_lb:
            f_lb.write(ctx["marked_text"])
    logger.info(f"✅ Saved {len(contexts)} contexts to '{OUTPUT_DIR}/'")

# ============== Main ==============
def main():
    if not PDF_PATH.exists():
        logger.error(f"❌ PDF not found: {PDF_PATH}")
        sys.exit(1)

    from_text = extract_text_from_pdf(PDF_PATH)
    text = clean_text(from_text)
    text = remove_front_matter(text)       
    text = remove_references_section(text) 

    sentences = split_into_sentences(text)
    logger.info(f"📄 Total sentences after cleaning: {len(sentences)}")

    contexts = create_contexts(sentences)
    if not contexts:
        logger.warning("⚠️  No APA-style citations found (group or narrative).")
        return

    save_datasets(contexts)

    # log sample
    logger.info("🔍 Sample .in (raw):")
    logger.info(contexts[0]["orig_text"][:300] + ("..." if len(contexts[0]['orig_text']) > 300 else ""))
    logger.info("🔍 Sample .label (markerized):")
    logger.info(contexts[0]["marked_text"][:300] + ("..." if len(contexts[0]['marked_text']) > 300 else ""))

if __name__ == "__main__":
    main()