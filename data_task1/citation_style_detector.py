# citation_style_detector.py
import re
from typing import List, Tuple

# Optional backends
try:
    import fitz
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except Exception:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except Exception:
    HAS_PYPDF2 = False

import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


def _extract_text(pdf_path: str) -> str:
    if HAS_FITZ:
        try:
            parts = []
            with fitz.open(pdf_path) as doc:
                for p in doc:
                    parts.append(p.get_text("text"))
            txt = "\n".join(parts)
            if txt.strip():
                return txt
        except Exception:
            pass
    if HAS_PDFPLUMBER:
        try:
            parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            txt = "\n".join(parts)
            if txt.strip():
                return txt
        except Exception:
            pass
    if HAS_PYPDF2:
        try:
            out = []
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    out.append((page.extract_text() or "") + "\n")
            return "".join(out)
        except Exception:
            pass
    return ""


def _normalize(s: str) -> str:
    # một số fix spacing cơ bản
    s = re.sub(r'([.,;:!?])([A-Za-z0-9])', r'\1 \2', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = re.sub(r'([A-Za-z])([0-9])', r'\1 \2', s)
    s = re.sub(r'([0-9])([A-Za-z])', r'\1 \2', s)
    s = re.sub(r'\bet\s+al\s+\.', 'et al.', s)
    s = re.sub(r'([A-Za-z0-9])\(', r'\1 (', s)
    s = re.sub(r'\)([A-Za-z0-9])', r') \1', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _split_sentences(text: str) -> List[str]:
    sents = sent_tokenize(text)
    return [s.strip() for s in sents if len(s.strip()) > 10 and not s.strip().isdigit()]


def detect_style(pdf_path: str) -> Tuple[str, str, List[str]]:
    """
    Return (style, cleaned_text, sentences)
    style in {"APA", "IEEE/Numeric", "Unknown/Mixed"}
    """
    raw = _extract_text(pdf_path)
    cleaned = _normalize(raw)
    sentences = _split_sentences(cleaned)

    # APA (author-year)
    apa_regexes = [
        r'\([A-Z][A-Za-z-]+,\s*\d{4}[a-z]?\)',
        r'\([A-Z][A-Za-z-]+\s*&\s*[A-Z][A-Za-z-]+,\s*\d{4}[a-z]?\)',
        r'\([A-Z][A-Za-z-]+\s+et\s+al\.,\s*\d{4}[a-z]?\)',
        r'\b[A-Z][A-Za-z-]+\s+\(\d{4}[a-z]?\)',
        r'\([A-Z][A-Za-z-]+,\s*\d{4}(?:;\s*[A-Z][A-Za-z-]+,\s*\d{4})+\)'
    ]
    apa_hits = sum(sum(len(re.findall(rx, s)) for rx in apa_regexes) for s in sentences)

    # IEEE / Numeric
    ieee_inline = r'\[\s*\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*\s*\]'
    ieee_hits_inline = sum(len(re.findall(ieee_inline, s)) for s in sentences)
    ieee_reflist = len(re.findall(r'(?m)^\s*\[\d+\]\s', cleaned))
    ieee_hits = ieee_hits_inline + ieee_reflist

    margin = 2
    if ieee_hits >= max(2, apa_hits + margin):
        style = "IEEE/Numeric"
    elif apa_hits >= max(2, ieee_hits + margin):
        style = "APA"
    else:
        style = "Unknown/Mixed"

    return style, cleaned, sentences
