#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Configuration
PDF_PATH = Path("paper.pdf")
OUTPUT_DIR = Path("./text_contexts")
CONTEXT_SENTENCES = 5  # Number of sentences per context chunk

# Citation Patterns (just for detection, not processing)
CITATION_PATTERNS = [
    r'\([A-Z][A-Za-z\'\-]+(?:\s+(?:and|&|et\s+al\.)\s+[A-Z][A-Za-z\'\-]+)*\s*,?\s*\d{4}[a-z]?\)',
    r'\[\d+(?:[,\s]*\d+)*\]|\[\d+\s*-\s*\d+\]',
    r'\([A-Z][A-Za-z\'\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\'\-]+)*\s+\d{4}\)',
    r'\([^()]*\d{4}[^()]*;[^()]*\d{4}[^()]*\)',
]

# ----------------------- APA regex (KHÔNG dùng look-behind) -------------------
# Parenthetical APA: (Author, 1991), (Author & Author, 1991, p. 3), (Author et al., 1991, ...)
# Điều kiện:
#  - bên trong có năm 4 số (19xx|20xx)
#  - có tên tác giả hoặc "et al."
#  - có dấu phẩy trước năm HOẶC "et al." ngay trước năm
#  - không chứa Fig/Table/Sect/Eq/Exp/Alg
#  - không phải acronym kiểu (EEKE2022) hay (ACL 2020)
P_APA_PAREN = (
    r'\('
    r'(?=[^)]*\b(19|20)\d{2}[a-z]?\b)'  # phải có năm
    r'(?=[^)]*(?:[A-Z][A-Za-z\'’\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\'’\-]+)*|et\s+al\.))'  # có tác giả/et al.
    r'(?![^)]*\b(?:Fig(?:\.|ure)?|Table|Tab\.|Sect(?:\.|ion|ions)?|Eq(?:\.|uation)?|Exp(?:\.|eriment|eriments)?|Alg(?:\.|orithm)?)\b)'  # chặn chỉ-mục
    r'(?![^)]*\b[A-Z]{2,}\s*\d{2,}\b)'  # chặn acronym + năm: ACL 2020, EEKE2022
    r'(?=[^)]*(?:,\s*\b(19|20)\d{2}[a-z]?|\bet\s+al\.\s*,?\s*\b(19|20)\d{2}[a-z]?))'  # dấu phẩy trước năm hoặc "et al." trước năm
    r'[^)]*'
    r'\)'
)

# Narrative APA: Author (1991) / Author & Author (1991) / Author et al. (1991)
# Tránh prefix như Figure/Section/... bằng negative look-ahead (an toàn với re Python)
P_APA_NARR = (
    r'\b'
    r'(?!(?:Fig|Figure|Table|Tab|Sect|Section|Sections|Eq|Equation|Exp|Experiment|Experiments|Alg|Algorithm)\b)'
    r'[A-Z][A-Za-z\'’\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\'’\-]+)*(?:\s+et\s+al\.)?'
    r'\s*\(\s*(19|20)\d{2}[a-z]?(?:\s*,[^)]*)?\s*\)'
)

APA_REPLACE_REGEX = re.compile(f'(?:{P_APA_PAREN}|{P_APA_NARR})')
# -----------------------------------------------------------------------------


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber

        logger.info(f"Extracting text from {pdf_path}...")
        text_pages = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                logger.info(f"Processing page {i}/{len(pdf.pages)}")
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)

        if not text_pages:
            raise RuntimeError("No text could be extracted from PDF")

        full_text = "\n\n".join(text_pages)
        logger.info(f"Successfully extracted {len(full_text)} characters")
        return full_text

    except ImportError:
        logger.error("pdfplumber is not installed. Please install it with: pip install pdfplumber")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        sys.exit(1)


def clean_text(text: str) -> str:
    """Basic text cleaning."""
    # Remove hyphenation across lines
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # Normalize whitespace
    text = re.sub(r'[\xa0\u2000-\u200a\u202f\u205f\u3000]', ' ', text)
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r' +', ' ', text)

    # Remove excessive blank lines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()


def split_into_sentences(text: str) -> list:
    """
    Split text into sentences.
    Tránh dùng look-behind biến thiên: tách cơ bản rồi ghép hậu kỳ cho các viết tắt.
    """
    # Bước 1: tách cơ bản
    raw = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    # Bước 2: ghép lại nếu câu trước kết thúc bằng viết tắt dễ nhầm
    keep_together = ('e.g.', 'i.e.', 'et al.', 'Fig.', 'Sec.', 'Sect.', 'Eq.', 'Tab.')
    sentences = []
    for seg in raw:
        seg = re.sub(r'\s+', ' ', seg).strip()
        if not seg:
            continue
        if sentences and any(sentences[-1].endswith(k) for k in keep_together):
            sentences[-1] = (sentences[-1] + ' ' + seg).strip()
        else:
            sentences.append(seg)

    # Bỏ câu quá ngắn
    return [s for s in sentences if len(s) > 20]


def has_citation_pattern(text: str) -> bool:
    """Check if text contains any citation pattern."""
    citation_patterns = [re.compile(pattern) for pattern in CITATION_PATTERNS]
    for pattern in citation_patterns:
        if pattern.search(text):
            return True
    return False


def create_text_contexts(sentences: list) -> list:
    """Create text contexts around sentences with citations."""
    contexts = []
    for i, sentence in enumerate(sentences):
        if has_citation_pattern(sentence):
            start_idx = max(0, i - CONTEXT_SENTENCES + 1)
            context_sentences = sentences[start_idx:i + 1]
            context_text = ' '.join(context_sentences)
            contexts.append({
                'context_id': len(contexts) + 1,
                'text': context_text,
                'sentence_position': i,
                'context_range': f"{start_idx}-{i}",
                'sentence_count': len(context_sentences)
            })
    return contexts


def remove_references_section(text: str) -> str:
    """Remove references section to avoid false citations."""
    references_patterns = [
        r'\n\s*(?:References?)\s*\n',
        r'\n\s*\d+\.\s*References?\s*\n',
    ]
    for pattern in references_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.start() > len(text) * 0.7:
            logger.info("Removing references section")
            return text[:match.start()].strip()
    return text


# ------------------ Hậu kiểm để loại false positives -------------------------
_BLACKLIST_PREV = {
    'fig', 'figure', 'table', 'tab', 'sect', 'section', 'sections',
    'eq', 'equation', 'exp', 'experiment', 'experiments', 'alg', 'algorithm'
}

def _prev_token(s: str) -> str:
    m = re.search(r'(\b[A-Za-z]+)\W*$', s)
    return (m.group(1) if m else '').lower()

def _looks_like_apa(text: str, m: re.Match) -> bool:
    """Kiểm tra bổ sung để chắc chắn đây là trích dẫn APA thật sự."""
    frag = m.group(0)

    # Bắt buộc có năm 4 chữ số (19xx|20xx)
    if not re.search(r'\b(19|20)\d{2}[a-z]?\b', frag):
        return False

    # Bắt buộc dấu phẩy trước năm hoặc 'et al.' trước năm (đặc trưng APA)
    if not re.search(r'[A-Za-z][^)]*,\s*(19|20)\d{2}[a-z]?\b', frag) and not re.search(r'et\s+al\.\s*,?\s*(19|20)\d{2}[a-z]?\b', frag):
        return False

    # Loại acronym/codes kiểu (EEKE2022) / (ACL 2020)
    if re.fullmatch(r'\([A-Z]{2,}\s*\d{2,}\)', frag):
        return False

    # Nếu bên trong có các chỉ mục hình/bảng/sect thì loại
    if re.search(r'\b(Fig(?:\.|ure)?|Table|Tab\.|Sect(?:\.|ion|ions)?|Eq(?:\.|uation)?|Exp(?:\.|eriment|eriments)?|Alg(?:\.|orithm)?)\b', frag):
        return False

    # Kiểm tra từ ngay trước match (tránh "Sects (Author, 2020)")
    left = text[max(0, m.start()-30):m.start()]
    if _prev_token(left) in _BLACKLIST_PREV:
        return False

    return True
# -----------------------------------------------------------------------------


# ------------------ Thay APA citations bằng [CITATION_X] ---------------------
def replace_apa_with_markers(text: str):
    """
    Thay mọi APA citation (parenthetical + narrative) bằng [CITATION_X],
    X đánh số 1..N trong phạm vi 'text' đưa vào hàm.
    Trả về (text_with_marker, candidates).
    """
    parts = []
    last = 0
    idx = 0
    candidates = []

    for m in APA_REPLACE_REGEX.finditer(text):
        if not _looks_like_apa(text, m):
            continue
        s, e = m.span()
        idx += 1
        marker = f"[CITATION_{idx}]"
        parts.append(text[last:s])
        parts.append(marker)
        candidates.append({"marker": marker, "match": m.group(0), "start": s, "end": e})
        last = e

    parts.append(text[last:])
    out = ''.join(parts)
    # dọn khoảng trắng quanh marker
    out = re.sub(r'\s+\[CITATION_', ' [CITATION_', out)
    out = re.sub(r'\[CITATION_(\d+)\]\s+', r'[CITATION_\1] ', out)
    return out.strip(), candidates
# -----------------------------------------------------------------------------


def create_simple_output(context_data: dict) -> dict:
    """Create simple output structure with text + text_with_marker (APA -> [CITATION_X])."""
    text = context_data['text']
    text_with_marker, candidates = replace_apa_with_markers(text)
    return {
        "text": text,
        "citation_candidates": candidates,
        "bib_entries": {}
    }


def main():
    """Main function to extract text contexts."""
    if not PDF_PATH.exists():
        logger.error(f"❌ PDF file not found: {PDF_PATH}")
        sys.exit(1)

    try:
        raw_text = extract_text_from_pdf(PDF_PATH)
        cleaned_text = clean_text(raw_text)
        main_text = remove_references_section(cleaned_text)

        logger.info("Splitting text into sentences...")
        sentences = split_into_sentences(main_text)
        logger.info(f"Found {len(sentences)} sentences")

        logger.info("Creating text contexts...")
        contexts = create_text_contexts(sentences)
        logger.info(f"Found {len(contexts)} text contexts")

        if not contexts:
            logger.warning("⚠️  No citation patterns found in the document")
            return

        OUTPUT_DIR.mkdir(exist_ok=True)

        for context in contexts:
            output_data = create_simple_output(context)
            filename = f"text_{context['context_id']:03d}.json"
            filepath = OUTPUT_DIR / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

        summary = {
            "total_contexts": len(contexts),
            "total_sentences": len(sentences),
            "average_context_length": sum(len(c['text']) for c in contexts) / len(contexts),
            "files_created": [f"text_{i['context_id']:03d}.json" for i in contexts]
        }
        with open(OUTPUT_DIR / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info("✅ Extraction completed successfully!")
        logger.info(f"📄 Total sentences: {len(sentences):,}")
        logger.info(f"📝 Text contexts created: {len(contexts)}")
        logger.info(f"📁 Files saved to: {OUTPUT_DIR}")
        logger.info(f"📊 Summary: {OUTPUT_DIR / 'summary.json'}")

        if contexts:
            sample = create_simple_output(contexts[0])
            sample_text = sample['text_with_marker'][:200] + "..." if len(sample['text_with_marker']) > 200 else sample['text_with_marker']
            logger.info(f"🔍 Sample context (with APA markers): {sample_text}")

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
