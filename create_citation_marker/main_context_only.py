#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
import logging
import itertools

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
PDF_PATH = Path("paper.pdf")
OUTPUT_DIR = Path("./text_contexts")
CONTEXT_SENTENCES = 5  # số câu tối đa trong một context chunk (câu cuối có citation)

# ------------------------------------------------------------------------------
# PDF → text
# ------------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber chưa cài. Chạy: pip install pdfplumber")
        sys.exit(1)

    try:
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
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        sys.exit(1)

# ------------------------------------------------------------------------------
# Clean & trim
# ------------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Basic text cleaning."""
    # Gộp các từ bị ngắt dòng bằng dấu gạch
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # Chuẩn hóa whitespace
    text = re.sub(r'[\xa0\u2000-\u200a\u202f\u205f\u3000]', ' ', text)
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Giảm bớt dòng trống
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()

def remove_references_section(text: str) -> str:
    """Remove references section to avoid false citations (heuristic: near the end)."""
    patterns = [
        r'\n\s*(?:References?|Bibliography|Works Cited)\s*\n',
        r'\n\s*\d+\.\s*References?\s*\n',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.start() > len(text) * 0.6:
            logger.info("Removing references/bibliography section")
            return text[:match.start()].strip()
    return text

# ------------------------------------------------------------------------------
# Sentence split (smart)
# ------------------------------------------------------------------------------
DOTSAFE = "∯"
ABBREV = [
    "e.g.", "i.e.", "etc.", "Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "Sect.", "No.", "Nos.",
    "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Inc.", "Ltd.", "Co.", "Jr.", "Sr.", "cf.", "al."
]

def _protect_dots(s: str) -> str:
    # Bảo vệ số thập phân 3.14
    s = re.sub(r"(?<=\d)\.(?=\d)", DOTSAFE, s)
    # Bảo vệ các viết tắt có dấu chấm
    for ab in ABBREV:
        s = s.replace(ab, ab.replace(".", DOTSAFE))
    # Bảo vệ 'et al.'
    s = re.sub(r"\bet\.\s*al\.", lambda m: m.group(0).replace(".", DOTSAFE), s, flags=re.I)
    return s

def _restore_dots(s: str) -> str:
    return s.replace(DOTSAFE, ".")

def split_into_sentences(text: str) -> list:
    """Smart sentence splitter that respects abbreviations/decimals."""
    t = _protect_dots(text)

    # Boundary: .!? + space + (optional quotes/brackets) + plausible start
    BOUND = "⟐"
    t = re.sub(r'([.!?])\s+(?=(?:["\'\)\]]*\s*)?(?:\(|\[|[A-Z0-9]))', r"\1 " + BOUND + " ", t)

    parts = [seg.strip() for seg in t.split(BOUND)]
    sents = []
    for seg in parts:
        if not seg:
            continue
        seg = _restore_dots(seg).strip()
        if len(seg) >= 3 and not re.fullmatch(r"[^\w]+", seg):
            sents.append(seg)

    # Ghép câu quá ngắn vào câu sau
    merged = []
    i = 0
    while i < len(sents):
        if len(sents[i]) < 25 and i + 1 < len(sents):
            merged.append((sents[i] + " " + sents[i+1]).strip())
            i += 2
        else:
            merged.append(sents[i])
            i += 1
    return merged

# ------------------------------------------------------------------------------
# Citation detection & replacement (protect → detect → unprotect)
# ------------------------------------------------------------------------------
HYPH = r"[-\u2010-\u2015\u2011]"             # -, ‐, ‒, –, —, ―
SURNAME = rf"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’{HYPH}]+"
AND = r"(?:and|&)"
ETAL = rf"(?:et\s+al\.?)"
AUTHOR_SEQ = rf"{SURNAME}(?:\s+{AND}\s+{SURNAME})?(?:\s+{ETAL})?"
YEAR = r"(?:19|20)\d{2}[a-z]?"

MONTHS = "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|" \
         "Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"

# Những span KHÔNG được đụng đến
_PROTECTORS = [
    # URLs / DOIs / emails
    (re.compile(r"https?://\S+"), "URL"),
    (re.compile(r"\b10\.\d{4,9}/\S+\b"), "DOI"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "EMAIL"),

    # (Fig./Table/Sect./Eq./Appendix/Algorithm/...) trong ngoặc
    (re.compile(r"\(\s*(?:fig(?:ure)?s?|fig\.?|table?s?|tab\.?|sec(?:tion)?s?|sect\.?|"
                r"eq(?:uation)?s?|eq\.?|appendix|app\.?|supp(?:lementary)?|algorithm|alg\.?|"
                r"theorem|lemma)\b[^)]*\)", re.I), "REFPAREN"),

    # Meta: (Received/Accepted/Revised …), (© …)
    (re.compile(r"\(\s*(?:received|accepted|revised)\b[^)]*\)", re.I), "METAPAREN"),
    (re.compile(r"\(\s*©[^)]*\)", re.I), "COPYRIGHT"),

    # ALL-CAPS ngắn trong ngoặc: (IND), (GRNB) …
    (re.compile(r"\([A-Z]{2,8}\)"), "ALLCAPS"),

    # Tháng + năm trong ngoặc: (February 2022)
    (re.compile(rf"\(\s*{MONTHS}\s+\d{{4}}[a-z]?\s*\)", re.I), "MONTHPAREN"),

    # Metrics như F1-score, P@10
    (re.compile(r"\bF\d+(?:\.\d+)?\s*[- ]\s*score\b", re.I), "METRIC"),
    (re.compile(r"\bP@\d+\b", re.I), "METRIC"),
]

def _protect(text: str):
    repl = {}
    counter = itertools.count()
    def _sub(m, tag):
        key = f"§§{tag}{next(counter)}§§"
        repl[key] = m.group(0)
        return key
    for rx, tag in _PROTECTORS:
        text = rx.sub(lambda m, t=tag: _sub(m, t), text)
    return text, repl

def _unprotect(text: str, repl: dict) -> str:
    for k in sorted(repl.keys(), key=len, reverse=True):
        text = text.replace(k, repl[k])
    return text

def replace_true_citations(text: str):
    """
    Chỉ thay citation thật bằng [CITATION_i].
    Trả về: (new_text, candidates_list[{'marker','match','start','end'}])
    """
    safe, vault = _protect(text)
    idx = 0
    parts = []
    last = 0
    candidates = []

    # 3 nhóm match ứng viên
    PAREN_AY = re.compile(
        rf"\(\s*{AUTHOR_SEQ}\s*,\s*{YEAR}\s*(?:;\s*{AUTHOR_SEQ}\s*,\s*{YEAR}\s*)*\)", re.U)
    NARR_AY  = re.compile(
        rf"{AUTHOR_SEQ}\s*\(\s*{YEAR}\s*\)", re.U)
    NUMERIC  = re.compile(
        r"\[\s*(?:\d+\s*(?:[-–—]\s*\d+)?)(?:\s*[,;]\s*\d+(?:\s*(?:[-–—]\s*\d+)?)*)?\s*\]")

    # Guard bổ sung
    ACRONYM_YEAR = re.compile(r"\([A-Z]{2,}\s*\d{2,}\)")
    HAS_PLACEHOLDER = re.compile(r"§§\w+\d+§§")

    def next_match(s, start):
        """Lấy match gần nhất trong 3 nhóm."""
        cand = []
        for rx, kind in ((PAREN_AY, "paren"), (NARR_AY, "narr"), (NUMERIC, "num")):
            m = rx.search(s, start)
            if m:
                cand.append((m.start(), m, kind))
        if not cand:
            return None
        cand.sort(key=lambda x: x[0])
        return cand[0][1], cand[0][2]

    pos = 0
    while True:
        nm = next_match(safe, pos)
        if not nm:
            break
        m, kind = nm
        frag = m.group(0)

        # Bỏ qua nếu có placeholder (đang nằm trong vùng protected)
        if HAS_PLACEHOLDER.search(frag):
            pos = m.end()
            continue

        # Bỏ các acronym + năm kiểu (ACL 2020)
        if kind in ("paren", "narr") and ACRONYM_YEAR.fullmatch(frag):
            pos = m.end()
            continue

        # Accept & replace
        s, e = m.span()
        parts.append(safe[last:s])
        idx += 1
        marker = f"[CITATION_{idx}]"
        parts.append(marker)
        candidates.append({"marker": marker, "match": frag, "start": s, "end": e})
        last = e
        pos = e

    parts.append(safe[last:])
    out = ''.join(parts)
    out = _unprotect(out, vault)
    return out, candidates

# ------------------------------------------------------------------------------
# Build contexts sau khi đã mark
# ------------------------------------------------------------------------------
def create_text_contexts_from_marked(sentences: list) -> list:
    """
    Gom context gồm <= CONTEXT_SENTENCES câu; câu cuối chứa [CITATION_x].
    """
    contexts = []
    for i, s in enumerate(sentences):
        if "[CITATION_" in s:
            start_idx = max(0, i - CONTEXT_SENTENCES + 1)
            chunk = ' '.join(sentences[start_idx:i+1])
            contexts.append({
                "context_id": len(contexts) + 1,
                "text": chunk,
                "sentence_position": i,
                "context_range": f"{start_idx}-{i}",
                "sentence_count": i - start_idx + 1
            })
    return contexts

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
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

        # Thay citation theo từng câu (giảm nhiễu so với thay trên toàn văn bản)
        logger.info("Replacing true citations with markers...")
        marked_sentences = []
        for s in sentences:
            s_marked, _ = replace_true_citations(s)
            marked_sentences.append(s_marked)

        logger.info("Creating text contexts...")
        contexts = create_text_contexts_from_marked(marked_sentences)
        logger.info(f"Found {len(contexts)} text contexts")

        OUTPUT_DIR.mkdir(exist_ok=True)

        if not contexts:
            logger.warning("⚠️  No citation patterns found in the document")
            with open(OUTPUT_DIR / "summary.json", 'w', encoding='utf-8') as f:
                json.dump({"total_contexts": 0, "total_sentences": len(sentences)}, f, ensure_ascii=False, indent=2)
            return

        # Ghi từng context: text đã có [CITATION_x], kèm candidates theo context
        for context in contexts:
            context_text = context["text"]
            text_with_markers, candidates = replace_true_citations(context_text)

            out = {
                "text": text_with_markers,
                "citation_candidates": candidates,   # để bạn debug/soi lại match
                "bib_entries": {}                    # giữ schema như code cũ
            }
            filename = f"text_{context['context_id']:03d}.json"
            filepath = OUTPUT_DIR / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)

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

        # Sample log
        sample_text = contexts[0]['text']
        logger.info(f"🔍 Sample context: {sample_text[:300]}{'...' if len(sample_text)>300 else ''}")

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
