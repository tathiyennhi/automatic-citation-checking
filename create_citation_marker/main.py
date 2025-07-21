#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Configuration
PDF = Path("paper.pdf")
OUT = Path("./in_files")
MIN_PARAGRAPH_LENGTH = 40

# Citation Patterns
CITATION_PATTERNS = [
    # APA Style - Parenthetical
    r'\((?:[A-Z][A-Za-z\'\-]+(?:\s*[,&]\s*[A-Z][A-Za-z\'\-]+)*(?:\s+et\s+al\.)?\s*,?\s*\d{4}[a-z]?(?:\s*[,;]\s*[A-Z][A-Za-z\'\-]+(?:\s*[,&]\s*[A-Z][A-Za-z\'\-]+)*(?:\s+et\s+al\.)?\s*,?\s*\d{4}[a-z]?)*)\)',
    # APA Style - Narrative
    r'[A-Z][A-Za-z\'\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\'\-]+)*(?:\s+et\s+al\.)?\s+\(\d{4}[a-z]?\)',
    # IEEE Style - [1] or [1,2,3] or [1-3]
    r'\[\d+(?:[,\s]*\d+)*\]|\[\d+\s*-\s*\d+\]',
    # Harvard style
    r'\((?:[A-Z][A-Za-z\'\-]+(?:\s+and\s+[A-Z][A-Za-z\'\-]+)*\s+\d{4}(?:\s*:\s*\d+(?:-\d+)?)?)\)',
    # Multiple citations with semicolon
    r'\((?:[^()]+\d{4}[^()]*(?:;\s*[^()]+\d{4}[^()]*)+)\)',
]

REFERENCES_REGEX = re.compile(
    r'^\s*(?:References?|Bibliography|Works?\s+Cited|Literature\s+Cited|Citations?)\s*$', 
    re.IGNORECASE | re.MULTILINE
)

# Paragraph indicators
SECTION_HEADERS = re.compile(
    r'^(?:'
    r'(?:\d+(?:\.\d+)*\.?\s+)?'
    r'(?:'
    r'Abstract|Introduction|Background|Literature\s+Review|'
    r'Methods?|Methodology|Materials?\s+and\s+Methods?|'
    r'Results?|Findings?|Discussion|Analysis|'
    r'Conclusion|Conclusions?|Summary|'
    r'Acknowledg[e]?ments?|References?|Bibliography|'
    r'Research\s+Questions?|Objectives?|Hypothes[ei]s'
    r')'
    r'|[A-Z][A-Z\s]{2,30}'
    r')$',
    re.MULTILINE | re.IGNORECASE
)

LIST_ITEMS = re.compile(
    r'^(?:'
    r'[•▪▫◦‣⁃]\s+|'
    r'[-*+]\s+|'
    r'\d+[\.)]\s+|'
    r'[a-z][\.)]\s+|'
    r'[ivxIVX]+[\.)]\s+|'
    r'(?:RQ|H)\d+[:.)]\s*'
    r')',
    re.MULTILINE
)

# PDF extraction functions
def extract_with_pdfplumber(path: Path) -> Optional[str]:
    """Extract text using pdfplumber."""
    try:
        import pdfplumber
        text_pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
        return "\n\n".join(text_pages) if text_pages else None
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")
        return None

def extract_with_pypdf2(path: Path) -> Optional[str]:
    """Extract text using PyPDF2."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(path)
        text_pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_pages.append(text)
        return "\n\n".join(text_pages) if text_pages else None
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")
        return None

def extract_with_pdfminer(path: Path) -> Optional[str]:
    """Extract text using pdfminer."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(str(path))
    except Exception as e:
        logger.warning(f"pdfminer failed: {e}")
        return None

def pdf_to_text(path: Path) -> str:
    """Extract text from PDF using available libraries."""
    extractors = [
        ("pdfplumber", extract_with_pdfplumber),
        ("PyPDF2", extract_with_pypdf2),
        ("pdfminer", extract_with_pdfminer),
    ]
    
    for name, extractor in extractors:
        logger.info(f"Trying {name}...")
        text = extractor(path)
        if text:
            logger.info(f"Successfully extracted with {name}")
            return text
    
    raise RuntimeError("All PDF extraction methods failed")

# Text cleaning functions
def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove hyphenation
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Normalize whitespace
    text = re.sub(r'[\xa0\u2000-\u200a\u202f\u205f\u3000]', ' ', text)
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r' +', ' ', text)
    return text

def strip_references_section(text: str) -> str:
    """Remove references section from the end."""
    match = REFERENCES_REGEX.search(text)
    if match and match.start() > len(text) * 0.6:
        return text[:match.start()].strip()
    return text

# Paragraph detection
def is_paragraph_break(prev_line: str, curr_line: str) -> bool:
    """Check if there's a paragraph break."""
    if not curr_line.strip():
        return True
    
    curr_stripped = curr_line.strip()
    prev_stripped = prev_line.strip() if prev_line else ""
    
    # Check for headers or list items
    if SECTION_HEADERS.match(curr_stripped) or LIST_ITEMS.match(curr_stripped):
        return True
    
    # Check if previous line ends with punctuation and current starts with capital
    if prev_stripped and re.search(r'[.!?]\s*$', prev_stripped):
        if curr_stripped and curr_stripped[0].isupper():
            # Additional checks for paragraph break
            if (len(prev_stripped) < 70 or
                curr_stripped.startswith(('The ', 'This ', 'In ', 'We ', 'Our '))):
                return True
    
    return False

def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    # First try splitting by double newlines
    if '\n\n' in text:
        sections = text.split('\n\n')
    else:
        sections = [text]
    
    all_paragraphs = []
    
    for section in sections:
        lines = section.split('\n')
        current_para = []
        
        for i, line in enumerate(lines):
            prev_line = lines[i-1] if i > 0 else ""
            
            if is_paragraph_break(prev_line, line):
                # Save current paragraph
                if current_para:
                    para_text = ' '.join(current_para)
                    para_text = re.sub(r'\s+', ' ', para_text).strip()
                    if len(para_text) >= MIN_PARAGRAPH_LENGTH:
                        all_paragraphs.append(para_text)
                    current_para = []
                
                # Start new paragraph
                if line.strip() and not SECTION_HEADERS.match(line.strip()):
                    current_para = [line.strip()]
            else:
                if line.strip():
                    current_para.append(line.strip())
        
        # Don't forget last paragraph
        if current_para:
            para_text = ' '.join(current_para)
            para_text = re.sub(r'\s+', ' ', para_text).strip()
            if len(para_text) >= MIN_PARAGRAPH_LENGTH:
                all_paragraphs.append(para_text)
    
    return all_paragraphs

# Citation detection
def is_likely_footnote(text: str, match_start: int, match_text: str) -> bool:
    """Check if a number is likely a footnote."""
    context_start = max(0, match_start - 20)
    context = text[context_start:match_start]
    
    # Check if preceded by punctuation and is 1-2 digits
    if re.search(r'[.,:;!?]\s*$', context) and re.match(r'^\d{1,2}$', match_text):
        # Check what follows
        after_start = match_start + len(match_text)
        after_context = text[after_start:after_start + 5] if after_start < len(text) else ""
        # If followed by comma or dash and more numbers, it's probably a citation
        if re.match(r'^[,\-\d]', after_context):
            return False
        return True
    
    return False

def replace_citations(text: str, start_index: int = 0) -> Tuple[str, int, List[Dict]]:
    """Replace citations with placeholders."""
    citation_count = start_index
    citations_found = []
    result_text = text
    
    # Compile patterns
    citation_regexes = [re.compile(p) for p in CITATION_PATTERNS]
    
    # Find all matches
    all_matches = []
    for regex in citation_regexes:
        for match in regex.finditer(text):
            match_text = match.group()
            
            # Skip if it looks like a footnote
            if is_likely_footnote(text, match.start(), match_text):
                continue
            
            all_matches.append({
                'start': match.start(),
                'end': match.end(),
                'text': match_text
            })
    
    # Remove overlapping matches
    all_matches.sort(key=lambda x: (x['start'], -x['end']))
    non_overlapping = []
    last_end = -1
    
    for match in all_matches:
        if match['start'] >= last_end:
            non_overlapping.append(match)
            last_end = match['end']
    
    # Replace citations in reverse order
    for match in sorted(non_overlapping, key=lambda x: x['start'], reverse=True):
        citation_count += 1
        placeholder = f"[CITATION_{citation_count}]"
        
        citations_found.append({
            'id': citation_count,
            'text': match['text'],
            'start': match['start'],
            'end': match['end']
        })
        
        result_text = result_text[:match['start']] + placeholder + result_text[match['end']:]
    
    return result_text, citation_count, citations_found

# Main processing
def process_pdf(pdf_path: Path, output_dir: Path):
    """Process PDF and extract paragraphs with citations."""
    logger.info(f"Processing {pdf_path}...")
    
    # Extract text
    raw_text = pdf_to_text(pdf_path)
    
    # Clean text
    logger.info("Cleaning text...")
    text = clean_text(raw_text)
    text = strip_references_section(text)
    
    # Split into paragraphs
    logger.info("Detecting paragraphs...")
    paragraphs = split_into_paragraphs(text)
    logger.info(f"Found {len(paragraphs)} paragraphs")
    
    # Process each paragraph
    output_dir.mkdir(exist_ok=True)
    total_citations = 0
    
    for i, paragraph in enumerate(paragraphs, 1):
        # Replace citations
        marked_text, total_citations, citations_list = replace_citations(paragraph, total_citations)
        
        # Save to file
        output_file = output_dir / f"{i}.in"
        data = {
            "original_text": paragraph,
            "marked_text": marked_text,
            "paragraph_number": i,
            "length": len(paragraph),
            "citations_found": len(citations_list),
            "citations": citations_list
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Processed {len(paragraphs)} paragraphs")
    logger.info(f"✓ Found {total_citations} citations")
    logger.info(f"✓ Output saved to {output_dir}")

def main():
    """Main entry point."""
    if not PDF.exists():
        logger.error(f"❌ File not found: {PDF}")
        sys.exit(1)
    
    try:
        process_pdf(PDF, OUT)
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()