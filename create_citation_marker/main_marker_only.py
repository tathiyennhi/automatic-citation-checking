#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
import logging

# ---------------- CONFIG ----------------
PDF_PATH = Path("paper.pdf")
OUTPUT_DIR = Path("./contexts")
CONTEXT_SENTENCES = 5  # số câu trước/sau
# ----------------------------------------

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ---------------- Regex citation ----------------
APA_REGEX = re.compile(r"\([A-Z][A-Za-z\-]+.*?\d{4}[a-z]?(?:;.*?\d{4}[a-z]?)*\)")

def extract_text_from_pdf(pdf_path: Path) -> str:
    import pdfplumber
    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_pages.append(page_text)
    return "\n".join(text_pages)

def clean_text(text: str) -> str:
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)  # nối từ bị xuống dòng
    text = re.sub(r"\s+", " ", text)  # gọn whitespace
    return text.strip()

def split_into_sentences(text: str) -> list:
    return re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

def has_citation(sentence: str) -> bool:
    return bool(APA_REGEX.search(sentence))

def replace_citations(sentence: str, citation_counter: int) -> tuple[str, list]:
    """Thay citations trong câu bằng [CITATION_i]."""
    citations = []
    def repl(m):
        nonlocal citation_counter
        citation_counter += 1
        marker = f"[CITATION_{citation_counter}]"
        citations.append({"marker": marker, "original": m.group(0)})
        return marker

    new_sentence = APA_REGEX.sub(repl, sentence)
    return new_sentence, citations, citation_counter

def create_contexts(sentences: list) -> list:
    contexts = []
    citation_counter = 0
    for i, sent in enumerate(sentences):
        if has_citation(sent):
            start = max(0, i - CONTEXT_SENTENCES)
            end = min(len(sentences), i + CONTEXT_SENTENCES + 1)
            context = sentences[start:end]

            # Thay citations trong toàn bộ context
            all_citations = []
            new_context = []
            for s in context:
                replaced, found, citation_counter = replace_citations(s, citation_counter)
                new_context.append(replaced)
                all_citations.extend(found)

            contexts.append({
                "context_id": len(contexts) + 1,
                "text": " ".join(new_context),
                "citations": all_citations
            })
    return contexts

def save_datasets(contexts: list):
    OUTPUT_DIR.mkdir(exist_ok=True)

    for ctx in contexts:
        base = OUTPUT_DIR / f"context_{ctx['context_id']:03d}"
        # file .in
        with open(base.with_suffix(".in"), "w", encoding="utf-8") as f_in:
            f_in.write(ctx["text"])
        # file .label
        with open(base.with_suffix(".label"), "w", encoding="utf-8") as f_lb:
            json.dump(ctx["citations"], f_lb, ensure_ascii=False, indent=2)

    logger.info(f"✅ Saved {len(contexts)} contexts into {OUTPUT_DIR}")

def main():
    if not PDF_PATH.exists():
        logger.error(f"❌ PDF not found: {PDF_PATH}")
        sys.exit(1)

    text = extract_text_from_pdf(PDF_PATH)
    text = clean_text(text)
    sentences = split_into_sentences(text)
    logger.info(f"📄 Found {len(sentences)} sentences")

    contexts = create_contexts(sentences)
    save_datasets(contexts)

    if contexts:
        logger.info("🔍 Sample context with markers:")
        logger.info(contexts[0]["text"])

if __name__ == "__main__":
    main()